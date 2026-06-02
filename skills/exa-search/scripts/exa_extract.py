#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["exa-py>=1.14.0"]
# ///
"""Fetch and extract content from URLs using Exa's /contents endpoint.

Example:
    uv run exa_extract.py \\
        https://arxiv.org/abs/2401.04088 \\
        https://www.nature.com/articles/s41586-024-07566-y \\
        --text \\
        -o extracted.json
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
class ExtractedDocument:
    """Typed view of a single extracted document for JSON export."""

    url: str
    id: str | None
    title: str | None
    author: str | None
    published_date: str | None
    text: str | None = None
    highlights: list[str] = field(default_factory=list)


def _build_contents(text: bool, highlights: bool) -> dict[str, Any]:
    contents: dict[str, Any] = {}
    if text:
        contents["text"] = True
    if highlights:
        contents["highlights"] = True
    if not contents:
        # Default to full text when the caller doesn't pick anything.
        contents["text"] = True
    return contents


def _to_typed(item: Any) -> ExtractedDocument:
    return ExtractedDocument(
        url=getattr(item, "url", ""),
        id=getattr(item, "id", None),
        title=getattr(item, "title", None),
        author=getattr(item, "author", None),
        published_date=getattr(item, "published_date", None),
        text=getattr(item, "text", None),
        highlights=list(getattr(item, "highlights", None) or []),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        print("EXA_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(2)

    client = Exa(api_key=api_key)
    client.headers["x-exa-integration"] = EXA_INTEGRATION_HEADER

    contents = _build_contents(args.text, args.highlights)
    response = client.get_contents(urls=args.urls, **contents)

    typed = [_to_typed(item) for item in getattr(response, "results", []) or []]
    return {
        "urls": list(args.urls),
        "num_results": len(typed),
        "results": [asdict(doc) for doc in typed],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract content from URLs with Exa.")
    parser.add_argument("urls", nargs="+", help="One or more URLs to extract.")
    parser.add_argument("--text", action="store_true", help="Return full-text content.")
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
        print(f"Wrote {len(payload['results'])} documents to {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
