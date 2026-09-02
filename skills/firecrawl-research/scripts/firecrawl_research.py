#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["firecrawl-py>=4.41.0"]
# ///
"""Query the Firecrawl Research Index and write results to JSON.

Uses the Firecrawl Python SDK. Auth via the FIRECRAWL_API_KEY environment
variable; the index also answers unauthenticated requests at a much lower rate
limit, so the key is recommended rather than required.

Examples:
    uv run firecrawl_research.py search-papers "CRISPR base editing off-target" --limit 20
    uv run firecrawl_research.py read-paper arxiv:1706.03762 --question "What is the attention mechanism?"
    uv run firecrawl_research.py related-papers arxiv:1706.03762 --intent "efficient transformers" --mode citers
    uv run firecrawl_research.py search-github "flash attention implementation notes"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable

try:
    import requests
    # The top-level `Firecrawl` wrapper eagerly builds a legacy v1 client and
    # raises ValueError("No API key provided") when there is no key, so it
    # cannot serve the index's anonymous access. The v2 client can.
    from firecrawl.v2 import FirecrawlClient
except ImportError:
    print(
        "firecrawl-py is not installed. Run: uv pip install 'firecrawl-py>=4.41.0'"
        "  (or invoke with: uv run --with 'firecrawl-py>=4.41.0')",
        file=sys.stderr,
    )
    sys.exit(2)


#: Status codes Firecrawl asks clients to retry.
RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})
MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 1.0
#: Ceiling on an honoured Retry-After, so a pathological header cannot hang the run.
MAX_BACKOFF_SECONDS = 60.0
#: The SDK runs its own retry loop over transport errors and 502. Left at its
#: default it would multiply with the loop below -- a persistent 502 would cost
#: MAX_ATTEMPTS x 3 requests and stacked sleeps. Setting it to 1 disables that
#: inner loop so this module is the only retry owner and MAX_ATTEMPTS is real.
SDK_INTERNAL_RETRIES = 1


def _split_csv(value: str | None) -> list[str] | None:
    """Comma-separated CLI value to a list, or None when nothing usable."""
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def _client() -> FirecrawlClient:
    """Build a client, warning when running keyless.

    The key is optional because the Research Index serves anonymous requests at
    a reduced rate limit, but a missing key is worth surfacing rather than
    turning into a rate-limit failure further along.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print(
            "FIRECRAWL_API_KEY is not set -- continuing unauthenticated at a reduced "
            "rate limit.",
            file=sys.stderr,
        )
    return FirecrawlClient(api_key=api_key or None, max_retries=SDK_INTERNAL_RETRIES)


def _retry_after_seconds(exc: Exception) -> float | None:
    """Seconds to wait per the response's `Retry-After` header, when usable.

    The header comes in two forms: delta-seconds and an HTTP-date. Both are
    accepted; anything unparseable falls back to the caller's backoff.
    """
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    raw = headers.get("Retry-After") if hasattr(headers, "get") else None
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        pass
    try:
        deadline = parsedate_to_datetime(str(raw))
    except (TypeError, ValueError):
        return None
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds())


def _call_with_retries(operation: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Invoke an SDK method, retrying transient failures.

    This is the only retry loop in play -- the client is built with the SDK's
    own retries switched off -- so the bound here is the real request budget.
    Retryable: the status codes above, plus transport errors, which the SDK
    would otherwise have absorbed. `Retry-After` wins over the exponential
    backoff when the response carries a usable one.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return operation(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 -- re-raised unless retryable
            status = getattr(exc, "status_code", None)
            retryable = status in RETRYABLE_STATUS or (
                status is None and isinstance(exc, requests.RequestException)
            )
            if not retryable or attempt == MAX_ATTEMPTS:
                raise
            delay = _retry_after_seconds(exc)
            if delay is None:
                delay = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            delay = min(delay, MAX_BACKOFF_SECONDS)
            reason = f"HTTP {status}" if status else type(exc).__name__
            print(
                f"Firecrawl request failed ({reason}); retrying in {delay:.1f}s "
                f"(attempt {attempt}/{MAX_ATTEMPTS}).",
                file=sys.stderr,
            )
            time.sleep(delay)
    raise AssertionError("unreachable: the loop either returns or raises")


def _as_plain(value: Any) -> Any:
    """Normalise an SDK response to JSON-serialisable data.

    The research endpoints return plain dicts today, but the SDK returns
    pydantic models elsewhere, so handle both rather than assuming.
    """
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def cmd_search_papers(args: argparse.Namespace, client: FirecrawlClient) -> dict[str, Any]:
    response = _call_with_retries(
        client.search_papers,
        args.query,
        k=args.limit,
        authors=_split_csv(args.authors),
        categories=_split_csv(args.categories),
        from_date=args.from_date,
        to_date=args.to_date,
    )
    return _as_plain(response)


def cmd_inspect_paper(args: argparse.Namespace, client: FirecrawlClient) -> dict[str, Any]:
    return _as_plain(_call_with_retries(client.inspect_paper, args.paper_id))


def cmd_read_paper(args: argparse.Namespace, client: FirecrawlClient) -> dict[str, Any]:
    response = _as_plain(
        _call_with_retries(client.read_paper, args.paper_id, args.question, k=args.limit)
    )
    # `success: true` with no passages means the index holds metadata but no
    # full text for this paper -- absence of evidence, not evidence of absence.
    if isinstance(response, dict) and not response.get("passages"):
        print(
            f"No full-text passages indexed for {args.paper_id}; only metadata is "
            "available. Do not read this as the paper lacking the answer.",
            file=sys.stderr,
        )
    return response


def cmd_related_papers(args: argparse.Namespace, client: FirecrawlClient) -> dict[str, Any]:
    response = _call_with_retries(
        client.related_papers,
        args.paper_id,
        args.intent,
        mode=args.mode,
        k=args.limit,
    )
    return _as_plain(response)


def cmd_search_github(args: argparse.Namespace, client: FirecrawlClient) -> dict[str, Any]:
    return _as_plain(_call_with_retries(client.search_github, args.query, k=args.limit))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query the Firecrawl Research Index (papers, passages, related work, GitHub history).",
    )
    # `-o` lives on the subparsers, not here: declaring it in both places makes
    # argparse reset it to None when it appears before the subcommand, which
    # would silently drop the destination file.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-o",
        "--output",
        default=None,
        help="Write JSON to this file (default: stdout). Must follow the subcommand.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser(
        "search-papers",
        parents=[common],
        help="Search paper abstracts with a natural-language query.",
    )
    search.add_argument("query", help="Natural-language query.")
    search.add_argument("--limit", type=int, default=10, help="Number of papers to return.")
    search.add_argument("--authors", default=None, help="Comma-separated author substrings; all must match.")
    search.add_argument("--categories", default=None, help="Comma-separated category filter, e.g. cs.LG.")
    search.add_argument("--from-date", default=None, help="Inclusive lower bound, YYYY-MM-DD.")
    search.add_argument("--to-date", default=None, help="Inclusive upper bound, YYYY-MM-DD.")
    search.set_defaults(func=cmd_search_papers)

    inspect = sub.add_parser(
        "inspect-paper", parents=[common], help="Fetch canonical metadata for one paper."
    )
    inspect.add_argument("paper_id", help="Canonical paperId or source id, e.g. arxiv:1706.03762, pmid:34515826.")
    inspect.set_defaults(func=cmd_inspect_paper)

    read = sub.add_parser(
        "read-paper",
        parents=[common],
        help="Retrieve the full-text passages that answer a question.",
    )
    read.add_argument("paper_id", help="Canonical paperId or source id.")
    read.add_argument("--question", required=True, help="The question to retrieve passages for.")
    read.add_argument("--limit", type=int, default=4, help="Number of passages to return.")
    read.set_defaults(func=cmd_read_paper)

    related = sub.add_parser(
        "related-papers", parents=[common], help="Expand from a seed paper to related work."
    )
    related.add_argument("paper_id", help="Seed paper id.")
    related.add_argument("--intent", required=True, help="Natural-language intent used to rank candidates.")
    related.add_argument(
        "--mode",
        default="similar",
        choices=["similar", "citers", "references"],
        help="Expansion mode: co-citation neighbourhood, papers citing the seed, or papers it cites.",
    )
    related.add_argument("--limit", type=int, default=20, help="Number of papers to return.")
    related.set_defaults(func=cmd_related_papers)

    github = sub.add_parser(
        "search-github",
        parents=[common],
        help="Search GitHub issues, PRs, discussions, and READMEs.",
    )
    github.add_argument("query", help="Natural-language query.")
    github.add_argument("--limit", type=int, default=10, help="Number of results to return.")
    github.set_defaults(func=cmd_search_github)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = args.func(args, _client())
    except Exception as exc:  # noqa: BLE001 -- a CLI should not print a traceback
        status = getattr(exc, "status_code", None)
        detail = f" (HTTP {status})" if status else ""
        print(f"Firecrawl request failed{detail}: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Wrote {args.command} results to {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
