#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["exa-py>=1.14.0"]
# ///
"""Run an Exa web search and write results to JSON.

Uses the Exa Python SDK. Auth via the EXA_API_KEY environment variable.

Example:
    uv run exa_search.py "transformer architectures" \\
        --category "research paper" \\
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
    if args.category:
        kwargs["category"] = args.category
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

    if contents is not None:
        response = client.search_and_contents(**kwargs, **contents)
    else:
        response = client.search(**kwargs)

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
        choices=["auto", "fast", "deep"],
        help="Search type. 'auto' is Exa's general-purpose search; 'fast' is lowest latency; 'deep' is highest quality at higher latency.",
    )
    parser.add_argument("--num-results", type=int, default=10, help="Number of results (1-100).")
    parser.add_argument(
        "--category",
        default=None,
        choices=[
            "company",
            "research paper",
            "news",
            "github",
            "personal site",
            "financial report",
            "people",
        ],
        help="Bias results toward a content category.",
    )
    parser.add_argument("--include-domains", default=None, help="Comma-separated allowlist.")
    parser.add_argument("--exclude-domains", default=None, help="Comma-separated blocklist.")
    parser.add_argument("--start-published-date", default=None, help="ISO date, e.g. 2024-01-01.")
    parser.add_argument("--end-published-date", default=None, help="ISO date, e.g. 2024-12-31.")
    parser.add_argument("--user-location", default=None, help="Two-letter ISO country code.")
    parser.add_argument("--text", action="store_true", help="Return full-text content per result.")
    parser.add_argument("--highlights", action="store_true", help="Return extracted highlight snippets.")
    parser.add_argument("-o", "--output", default=None, help="Write JSON to this file (default: stdout).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run(args)
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
