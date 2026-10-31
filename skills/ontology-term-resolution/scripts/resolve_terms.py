#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Resolve free-text labels to ontology terms via EBI OLS4.

Never emit an ontology ID from memory -- run this instead. Each input string is
searched with an escalating strategy and every returned candidate is labelled
with how it actually matched, so a partial hit can never be mistaken for an
exact one.

Strategies, tried in order until one returns candidates:

    exact       exact=true restricted to label and synonym fields
    token       exact=true across all indexed fields (whole-word match)
    fulltext    unrestricted relevance search

Examples:
    # single term, constrained to the ontology that should define it
    uv run resolve_terms.py "liver" --ontology uberon

    # a column of tissue names, requiring anatomical entities only
    uv run resolve_terms.py --input tissues.txt \\
        --ontology uberon --branch UBERON:0000465 --format tsv -o resolved.tsv

    # accept exact matches only; unresolved rows are reported, not guessed
    uv run resolve_terms.py "kidney cortex" "left ventrical" --exact-only
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ols_client import (  # noqa: E402
    OlsError,
    iri_for,
    is_curie,
    rank_candidates,
    search,
)

STRATEGIES = (
    ("exact", {"exact": True, "query_fields": "label,synonym"}),
    ("token", {"exact": True, "query_fields": None}),
    ("fulltext", {"exact": False, "query_fields": None}),
)

TSV_COLUMNS = (
    "query",
    "rank",
    "curie",
    "iri",
    "label",
    "ontology",
    "match_type",
    "strategy",
    "defining_ontology",
)


def read_inputs(args: argparse.Namespace) -> list[str]:
    """Collect query strings from positional args, a file, or stdin."""
    values: list[str] = list(args.text)
    if args.input:
        raw = (
            sys.stdin.read()
            if args.input == "-"
            else Path(args.input).read_text(encoding="utf-8")
        )
        for line in raw.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                values.append(line)
    if not values and not sys.stdin.isatty():
        for line in sys.stdin.read().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                values.append(line)
    # Preserve order, drop duplicates.
    seen: set[str] = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def resolve_one(
    text: str,
    *,
    ontology: str | None,
    subtree_iri: str | None,
    rows: int,
    exact_only: bool,
) -> dict:
    """Run the strategy ladder for one string and return ranked candidates."""
    strategies = STRATEGIES[:1] if exact_only else STRATEGIES
    for name, options in strategies:
        docs = search(
            text,
            ontology=ontology,
            subtree_iri=subtree_iri,
            rows=rows,
            **options,
        )
        ranked = rank_candidates(text, docs)
        if exact_only:
            ranked = [candidate for candidate in ranked
                      if candidate["match_type"] in {"exact_label", "exact_synonym"}]
        if ranked:
            return {"query": text, "strategy": name, "candidates": ranked[:rows]}
    return {"query": text, "strategy": strategies[-1][0], "candidates": []}


def to_rows(results: list[dict]) -> list[dict]:
    """Flatten results into one row per candidate, or one row if unresolved."""
    rows: list[dict] = []
    for result in results:
        if not result["candidates"]:
            rows.append(
                {
                    "query": result["query"],
                    "rank": 1,
                    "curie": "",
                    "iri": "",
                    "label": "",
                    "ontology": "",
                    "match_type": "unresolved",
                    "strategy": result["strategy"],
                    "defining_ontology": "",
                }
            )
            continue
        for position, candidate in enumerate(result["candidates"], start=1):
            rows.append(
                {
                    "query": result["query"],
                    "rank": position,
                    "curie": candidate.get("obo_id", ""),
                    "iri": candidate.get("iri", ""),
                    "label": candidate.get("label", ""),
                    "ontology": candidate.get("ontology_name", ""),
                    "match_type": candidate["match_type"],
                    "strategy": result["strategy"],
                    "defining_ontology": str(
                        bool(candidate.get("is_defining_ontology"))
                    ).lower(),
                }
            )
    return rows


def write_output(results: list[dict], fmt: str, output: str | None) -> None:
    """Emit TSV or JSON to a path or stdout."""
    stream = open(output, "w", encoding="utf-8", newline="") if output else sys.stdout
    try:
        if fmt == "json":
            json.dump(results, stream, indent=2)
            stream.write("\n")
        else:
            writer = csv.DictWriter(
                stream, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(to_rows(results))
    finally:
        if output:
            stream.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve free-text labels to ontology terms via EBI OLS4.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="*", help="strings to resolve")
    parser.add_argument(
        "--input",
        help="file with one string per line ('-' for stdin); # lines are comments",
    )
    parser.add_argument(
        "--ontology",
        help="restrict to OLS ontology ids, comma separated (e.g. uberon,cl)",
    )
    parser.add_argument(
        "--branch",
        help="require candidates to be descendants of this CURIE (e.g. UBERON:0000465)",
    )
    parser.add_argument(
        "--top", type=int, default=5, help="candidates to report per query (default 5)"
    )
    parser.add_argument(
        "--exact-only",
        action="store_true",
        help="only exact label/synonym matches; report anything else as unresolved",
    )
    parser.add_argument(
        "--format", choices=("tsv", "json"), default="tsv", help="output format"
    )
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.top < 1:
        print("--top must be positive.", file=sys.stderr)
        return 2
    queries = read_inputs(args)
    if not queries:
        print("No input strings given. See --help.", file=sys.stderr)
        return 2

    subtree_iri = None
    if args.branch:
        if not is_curie(args.branch):
            print(f"--branch expects a CURIE, got {args.branch!r}", file=sys.stderr)
            return 2
        try:
            subtree_iri = iri_for(args.branch)
        except OlsError as exc:
            print(f"Could not resolve --branch {args.branch}: {exc}", file=sys.stderr)
            return 2
        if not subtree_iri:
            print(f"--branch term not found in OLS: {args.branch}", file=sys.stderr)
            return 2

    results = []
    for query in queries:
        try:
            results.append(
                resolve_one(
                    query,
                    ontology=args.ontology,
                    subtree_iri=subtree_iri,
                    rows=args.top,
                    exact_only=args.exact_only,
                )
            )
        except OlsError as exc:
            print(f"OLS lookup failed for {query!r}: {exc}", file=sys.stderr)
            return 2

    write_output(results, args.format, args.output)

    unresolved = [r["query"] for r in results if not r["candidates"]]
    if unresolved:
        print(
            f"{len(unresolved)}/{len(results)} unresolved: "
            + ", ".join(repr(q) for q in unresolved[:10]),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
