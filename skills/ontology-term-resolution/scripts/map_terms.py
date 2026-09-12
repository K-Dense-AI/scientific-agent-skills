#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Map lab shorthand to ontology terms via EBI ZOOMA.

Use this after ``resolve_terms.py`` returns ``unresolved`` or only ``partial``
hits on strings like ``PBMC`` or ``WT``. Every HIGH/GOOD hit is still only a
candidate — run ``validate_terms.py`` on the CURIE before writing it down.

``--ontology`` is required. Unfiltered ZOOMA annotate returns FOODON, XAO, and
BTO alongside UBERON for ``liver``, all at HIGH confidence.

Examples:
    uv run map_terms.py PBMC --ontology cl
    uv run map_terms.py liver --ontology uberon --property-type "organism part"
    uv run map_terms.py --input shorthand.txt --ontology uberon,cl --exact-only
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from zooma_client import (  # noqa: E402
    ZoomaError,
    annotate,
    flatten_hit,
)

TSV_COLUMNS = (
    "query",
    "rank",
    "curie",
    "iri",
    "confidence",
    "safe",
    "evidence",
    "source",
    "property_type",
    "match_type",
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
    seen: set[str] = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def map_one(
    text: str,
    *,
    ontologies: list[str],
    property_type: str | None,
    top: int,
    safe_only: bool,
) -> dict:
    """Annotate one string and return ranked, flattened candidates."""
    hits = annotate(text, ontologies=ontologies, property_type=property_type)
    candidates: list[dict] = []
    for hit in hits:
        candidates.extend(flatten_hit(hit))
    if safe_only:
        candidates = [row for row in candidates if row["safe"]]
    # HIGH before GOOD before MEDIUM/LOW; preserve server order within a tier.
    rank = {"HIGH": 0, "GOOD": 1, "MEDIUM": 2, "LOW": 3}
    candidates.sort(key=lambda row: rank.get(row["confidence"], 9))
    return {"query": text, "candidates": candidates[:top]}


def to_rows(results: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for result in results:
        if not result["candidates"]:
            rows.append(
                {
                    "query": result["query"],
                    "rank": 1,
                    "curie": "",
                    "iri": "",
                    "confidence": "",
                    "safe": "",
                    "evidence": "",
                    "source": "",
                    "property_type": "",
                    "match_type": "unresolved",
                }
            )
            continue
        for position, candidate in enumerate(result["candidates"], start=1):
            rows.append(
                {
                    "query": result["query"],
                    "rank": position,
                    "curie": candidate["curie"],
                    "iri": candidate["iri"],
                    "confidence": candidate["confidence"],
                    "safe": str(candidate["safe"]).lower(),
                    "evidence": candidate["evidence"],
                    "source": candidate["source"],
                    "property_type": candidate["property_type"],
                    "match_type": "zooma_safe" if candidate["safe"] else "zooma_weak",
                }
            )
    return rows


def write_output(results: list[dict], fmt: str, output: str | None) -> None:
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
        description=(
            "Map lab shorthand to ontology terms via EBI ZOOMA. "
            "--ontology is required. Validate every CURIE with validate_terms.py "
            "before writing it down."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="*", help="strings to map")
    parser.add_argument(
        "--input",
        help="file with one string per line ('-' for stdin); # lines are comments",
    )
    parser.add_argument(
        "--ontology",
        required=True,
        help="OLS ontology ids to filter on, comma separated (e.g. uberon,cl)",
    )
    parser.add_argument(
        "--property-type",
        help='ZOOMA property type, e.g. "organism part" or "cell type"',
    )
    parser.add_argument(
        "--top", type=int, default=5, help="candidates to report per query (default 5)"
    )
    parser.add_argument(
        "--exact-only",
        action="store_true",
        help="only HIGH/GOOD confidence hits; report anything else as unresolved",
    )
    parser.add_argument(
        "--format", choices=("tsv", "json"), default="tsv", help="output format"
    )
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    queries = read_inputs(args)
    if not queries:
        print("No input strings given. See --help.", file=sys.stderr)
        return 2

    ontologies = [item.strip() for item in args.ontology.split(",") if item.strip()]
    if not ontologies:
        print("--ontology needs at least one OLS ontology id.", file=sys.stderr)
        return 2

    results = []
    for query in queries:
        try:
            results.append(
                map_one(
                    query,
                    ontologies=ontologies,
                    property_type=args.property_type,
                    top=args.top,
                    safe_only=args.exact_only,
                )
            )
        except ZoomaError as exc:
            print(f"ZOOMA lookup failed for {query!r}: {exc}", file=sys.stderr)
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
