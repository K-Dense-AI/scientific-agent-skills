#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["exa-py>=2.23.0,<3"]
# ///
"""Run an Exa web search and write results to JSON.

Uses the Exa Python SDK. Auth via the EXA_API_KEY environment variable.

Example:
    uv run exa_search.py "transformer architectures" \\
        --category publication \\
        --text --highlights \\
        -o results.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

try:
    from exa_py import Exa
except ImportError:
    print(
        "exa_py not installed. Run: uv pip install exa-py  (or invoke with: uv run --with exa-py)",
        file=sys.stderr,
    )
    sys.exit(2)


EXA_INTEGRATION_HEADER = "k-dense-ai--scientific-agent-skills"


@dataclass
class SearchResult:
    """Typed view of a single Exa search result for JSON export."""

    title: str | None
    url: str
    id: str | None
    author: str | None
    published_date: str | None
    score: float | None
    text: str | None = None
    highlights: list[str] = field(default_factory=list)
    highlight_scores: list[float] = field(default_factory=list)


def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def _build_contents(text: bool, highlights: bool) -> dict[str, Any] | None:
    contents: dict[str, Any] = {}
    if text:
        contents["text"] = True
    if highlights:
        contents["highlights"] = True
    return contents or None


def _result_to_typed(item: Any) -> SearchResult:
    highlights = list(getattr(item, "highlights", None) or [])
    scores = list(getattr(item, "highlight_scores", None) or [])
    return SearchResult(
        title=getattr(item, "title", None),
        url=getattr(item, "url", ""),
        id=getattr(item, "id", None),
        author=getattr(item, "author", None),
        published_date=getattr(item, "published_date", None),
        score=getattr(item, "score", None),
        text=getattr(item, "text", None),
        highlights=highlights,
        highlight_scores=scores,
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.query.strip():
        raise ValueError("The query must not be empty.")
    if not 1 <= args.num_results <= 100:
        raise ValueError("--num-results must be between 1 and 100.")
    category = "publication" if args.category == "research paper" else args.category
    if category in {"company", "people"} and (
        args.exclude_domains or args.start_published_date or args.end_published_date
    ):
        raise ValueError("company/people do not support exclude-domains or publication-date filters.")
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        print("EXA_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(2)

    client = Exa(api_key=api_key)
    # Attribute API usage to this skill for integration tracking.
    client.headers["x-exa-integration"] = EXA_INTEGRATION_HEADER

    contents = _build_contents(args.text, args.highlights)

    kwargs: dict[str, Any] = {
        "query": args.query,
        "num_results": args.num_results,
        "type": args.type,
    }
    if category:
        kwargs["category"] = category
    if include := _split_csv(args.include_domains):
        kwargs["include_domains"] = include
    if exclude := _split_csv(args.exclude_domains):
        kwargs["exclude_domains"] = exclude
    if args.start_published_date:
        kwargs["start_published_date"] = args.start_published_date
    if args.end_published_date:
        kwargs["end_published_date"] = args.end_published_date
    if args.user_location:
        kwargs["user_location"] = args.user_location

    # SDK 2.x retrieves text by default; preserve this CLI's explicit content flags.
    response = client.search(**kwargs, contents=contents if contents is not None else False)

    typed = [_result_to_typed(item) for item in getattr(response, "results", []) or []]
    return {
        "query": args.query,
        "type": args.type,
        "num_results": len(typed),
        "autoprompt_string": getattr(response, "autoprompt_string", None),
        "results": [asdict(result) for result in typed],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search the web with Exa.")
    parser.add_argument("query", help="Natural-language search query.")
    parser.add_argument(
        "--type",
        default="auto",
        choices=["auto", "fast", "instant", "deep-lite", "deep", "deep-reasoning"],
        help="Search mode: auto balances speed/quality; instant minimizes latency; deep variants perform multi-step research.",
    )
    parser.add_argument("--num-results", type=int, default=10, help="Number of results (1-100).")
    parser.add_argument(
        "--category",
        default=None,
        help="Category (publication, company, news, personal site, financial report, people) or custom hint. Legacy 'research paper' maps to publication.",
    )
    parser.add_argument("--include-domains", default=None, help="Comma-separated allowlist.")
    parser.add_argument("--exclude-domains", default=None, help="Comma-separated blocklist.")
    parser.add_argument("--start-published-date", default=None, help="ISO 8601 timestamp, e.g. 2026-01-01T00:00:00Z.")
    parser.add_argument("--end-published-date", default=None, help="ISO 8601 timestamp, e.g. 2026-10-01T00:00:00Z.")
    parser.add_argument("--user-location", default=None, help="Two-letter ISO country code.")
    parser.add_argument("--text", action="store_true", help="Return full-text content per result.")
    parser.add_argument("--highlights", action="store_true", help="Return extracted highlight snippets.")
    parser.add_argument("-o", "--output", default=None, help="Write JSON to this file (default: stdout).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = run(args)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Wrote {len(payload['results'])} results to {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
