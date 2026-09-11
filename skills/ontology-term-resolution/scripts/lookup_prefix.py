#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Look up ontology prefixes and check CURIEs against Bioregistry.

Use this when the *shape* of an identifier is in doubt — ``HPO`` vs ``HP``,
a local id that does not match the recorded pattern, or which landing page
to open. It does not say whether the term exists; run ``validate_terms.py``
for that.

Examples:
    uv run lookup_prefix.py HP HPO HP:0001250 HPO:0001250
    uv run lookup_prefix.py --input prefixes.txt --format tsv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from id_client import (  # noqa: E402
    IdError,
    NotFoundError,
    classify_prefix_query,
    compact_id_from_identifiers_url,
    get_reference,
    get_resource,
    is_prefix,
    landing_page_urls,
    resolve_identifiers,
    split_query,
)

TSV_COLUMNS = (
    "query",
    "status",
    "preferred_prefix",
    "canonical_curie",
    "pattern",
    "example",
    "name",
    "default_iri",
    "identifiers_org",
    "ontobee",
    "ols_id",
    "detail",
)

FAIL_STATUSES = {"unknown_prefix", "invalid_local", "malformed"}


def read_inputs(args: argparse.Namespace) -> list[str]:
    """Collect prefix/CURIE strings from positional args, a file, or stdin."""
    values: list[str] = list(args.value)
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


def lookup_one(value: str) -> dict:
    """Resolve one prefix or CURIE through Bioregistry, then Identifiers.org."""
    prefix, local = split_query(value)
    if not is_prefix(prefix) and local is None:
        return {
            "query": value,
            "status": "malformed",
            "preferred_prefix": "",
            "canonical_curie": "",
            "pattern": "",
            "example": "",
            "name": "",
            "default_iri": "",
            "identifiers_org": "",
            "ontobee": "",
            "ols_id": "",
            "detail": "not a prefix or PREFIX:local CURIE",
        }

    resource = None
    reference = None
    reference_detail = None
    try:
        resource = get_resource(prefix)
    except NotFoundError as exc:
        return classify_prefix_query(value, None, local=local, reference_detail=exc.detail)

    if local is not None:
        try:
            reference = get_reference(value)
        except NotFoundError as exc:
            reference_detail = exc.detail

    result = classify_prefix_query(
        value, resource, local=local, reference_detail=reference_detail
    )
    if result["status"] not in {"ok", "synonym_prefix"}:
        return result

    identifiers, ontobee = landing_page_urls(
        resource, reference, result["default_iri"] or None
    )
    result["identifiers_org"] = identifiers
    result["ontobee"] = ontobee

    compact = compact_id_from_identifiers_url(result["identifiers_org"])
    if not compact:
        return result

    try:
        payload = resolve_identifiers(compact)
    except IdError:
        result["identifiers_org"] = ""
        extra = f"Identifiers.org rejected {compact!r}"
        result["detail"] = f"{result['detail']}; {extra}" if result["detail"] else extra
        return result
    if payload.get("errorMessage"):
        result["identifiers_org"] = ""
        extra = f"Identifiers.org rejected {compact!r}: {payload['errorMessage']}"
        result["detail"] = f"{result['detail']}; {extra}" if result["detail"] else extra
    return result


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
            writer.writerows(results)
    finally:
        if output:
            stream.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Look up ontology prefixes and check CURIEs against Bioregistry. "
            "Does not say whether the term exists — use validate_terms.py for that."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("value", nargs="*", help="prefixes or CURIEs")
    parser.add_argument(
        "--input",
        help="file with one prefix or CURIE per line ('-' for stdin); # lines are comments",
    )
    parser.add_argument(
        "--format", choices=("tsv", "json"), default="tsv", help="output format"
    )
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    values = read_inputs(args)
    if not values:
        print("No prefixes or CURIEs given. See --help.", file=sys.stderr)
        return 2

    results = []
    for value in values:
        try:
            results.append(lookup_one(value))
        except IdError as exc:
            print(f"Prefix lookup failed for {value!r}: {exc}", file=sys.stderr)
            return 2

    write_output(results, args.format, args.output)
    failed = [r for r in results if r["status"] in FAIL_STATUSES]
    synonyms = [r for r in results if r["status"] == "synonym_prefix"]
    print(
        f"{len(results)} checked, {len(failed)} failed, {len(synonyms)} synonym prefixes",
        file=sys.stderr,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
