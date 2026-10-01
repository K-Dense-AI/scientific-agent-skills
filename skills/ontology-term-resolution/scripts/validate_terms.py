#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Validate ontology CURIEs against EBI OLS4 before they leave the machine.

This is the gate that catches invented IDs. For each term it reports whether the
ID exists at all, whether it has been obsoleted (and what replaced it), whether a
claimed label actually belongs to it, and optionally whether it sits in the
branch and ontology the metadata field requires.

Statuses: ``ok`` and ``matched_synonym`` pass, ``not_found``, ``obsolete``,
``label_mismatch``, ``wrong_branch``, ``wrong_ontology`` fail, and
``not_a_class`` warns. Exit code is 1 if anything failed, 0 otherwise, 2 on
usage or network trouble. ``--strict`` promotes warnings to failures.

Examples:
    # spot-check three IDs
    uv run validate_terms.py UBERON:0002107 CL:0000182 UBERON:9999999

    # verify id/label pairs a pipeline wrote, as a CI gate
    uv run validate_terms.py --input metadata.tsv --strict

    # a tissue column must hold anatomical entities from UBERON
    uv run validate_terms.py --input tissue_ids.tsv \\
        --branch UBERON:0000465 --expect-ontology uberon
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
    ancestor_curies,
    curie_to_ontology_id,
    is_curie,
    iri_to_curie,
    normalize_label,
    synonym_scope,
    term_detail,
)

FAIL_STATUSES = {
    "not_found",
    "obsolete",
    "label_mismatch",
    "wrong_branch",
    "wrong_ontology",
    "malformed_curie",
}
WARN_STATUSES = {"not_a_class", "matched_synonym", "imported_only"}

TSV_COLUMNS = ("id", "status", "actual_label", "ontology", "replacement", "detail")

ID_HEADERS = {"id", "curie", "term_id", "ontology_term_id", "obo_id"}
LABEL_HEADERS = {"label", "term_label", "name", "ontology_term_label"}


def read_pairs(args: argparse.Namespace) -> list[tuple[str, str | None]]:
    """Collect (curie, expected_label) pairs from positional args or a file."""
    pairs: list[tuple[str, str | None]] = [(value, None) for value in args.term]
    if not args.input:
        return pairs

    raw = (
        sys.stdin.read()
        if args.input == "-"
        else Path(args.input).read_text(encoding="utf-8")
    )
    lines = [line for line in raw.splitlines() if line.strip()]
    if not lines:
        return pairs

    delimiter = "\t" if "\t" in lines[0] else ","
    rows = list(csv.reader(lines, delimiter=delimiter))
    header = [cell.strip().lower() for cell in rows[0]]
    id_index, label_index = 0, 1

    if any(cell in ID_HEADERS for cell in header):
        id_index = next(i for i, cell in enumerate(header) if cell in ID_HEADERS)
        label_index = next(
            (i for i, cell in enumerate(header) if cell in LABEL_HEADERS), None
        )
        rows = rows[1:]

    for row in rows:
        if not row or row[0].lstrip().startswith("#"):
            continue
        if len(row) <= id_index or not row[id_index].strip():
            raise ValueError("input row has a missing or empty identifier column")
        curie = row[id_index].strip()
        if curie.startswith("#"):
            continue
        label = None
        if label_index is not None and len(row) > label_index:
            label = row[label_index].strip() or None
        pairs.append((curie, label))
    return pairs


def check_term(
    curie: str,
    expected_label: str | None,
    *,
    branch: str | None,
    expect_ontologies: set[str] | None,
    branch_relation: str = "hierarchical",
) -> dict:
    """Validate one CURIE and return a result record."""
    result = {
        "id": curie,
        "status": "ok",
        "actual_label": "",
        "ontology": "",
        "replacement": "",
        "detail": "",
    }

    if not is_curie(curie):
        result["status"] = "malformed_curie"
        result["detail"] = "not of the form PREFIX:local"
        return result

    term = term_detail(curie)
    if term is None:
        result["status"] = "not_found"
        result["detail"] = "no such term in the ontology this prefix names"
        return result

    result["actual_label"] = term.get("label") or ""
    result["ontology"] = term.get("ontology_name") or ""

    if term.get("is_obsolete"):
        replacements = term.get("term_replaced_by") or []
        if isinstance(replacements, str):
            replacements = [replacements]
        replacement = "; ".join(iri_to_curie(iri) or iri for iri in replacements)
        result["status"] = "obsolete"
        result["replacement"] = replacement
        result["detail"] = (
            f"obsolete; replaced by {replacement}"
            if replacement
            else "obsolete with no stated replacement"
        )
        return result

    namespace_ontology = curie_to_ontology_id(curie)
    if expect_ontologies and namespace_ontology not in expect_ontologies:
        result["status"] = "wrong_ontology"
        result["detail"] = (
            f"identifier namespace maps to {namespace_ontology!r}, expected one of "
            + ",".join(sorted(expect_ontologies))
        )
        return result

    warnings: list[tuple[str, str]] = []

    if expected_label is not None:
        wanted = normalize_label(expected_label)
        if normalize_label(result["actual_label"]) != wanted:
            scope = synonym_scope(expected_label, term)
            if scope:
                warnings.append(
                    (
                        "matched_synonym",
                        f"{expected_label!r} is a {scope} synonym; primary label is "
                        f"{result['actual_label']!r}",
                    )
                )
            else:
                result["status"] = "label_mismatch"
                result["detail"] = (
                    f"claimed {expected_label!r}, actual {result['actual_label']!r}"
                )
                return result

    if branch:
        ancestors = ancestor_curies(curie, relation=branch_relation) if branch != curie else set()
        if branch not in ancestors and branch != curie:
            result["status"] = "wrong_branch"
            result["detail"] = f"not a descendant of {branch}"
            return result

    # Importers can hold stale copies; lack of a defining copy requires review,
    # but does not prove deletion in the source ontology.
    home = term.get("_home_ontology")
    if not term.get("is_defining_ontology"):
        warnings.append(
            (
                "imported_only",
                f"no defining copy verified for {home}; found a copy in "
                f"{result['ontology']!r}",
            )
        )

    if term.get("type") not in (None, "class"):
        warnings.append(
            ("not_a_class", f"term type is {term.get('type')!r}, not a class")
        )

    if warnings:
        order = {"imported_only": 0, "not_a_class": 1, "matched_synonym": 2}
        warnings.sort(key=lambda item: order[item[0]])
        result["status"] = warnings[0][0]
        result["detail"] = "; ".join(detail for _, detail in warnings)

    return result


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
            writer.writerows(results)
    finally:
        if output:
            stream.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate ontology CURIEs against EBI OLS4.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("term", nargs="*", help="CURIEs to validate")
    parser.add_argument(
        "--input",
        help="TSV/CSV with an id column and an optional label column ('-' for stdin)",
    )
    parser.add_argument(
        "--branch", help="require every term to be a descendant of this CURIE"
    )
    parser.add_argument(
        "--branch-relation", choices=("hierarchical", "is-a"), default="hierarchical",
        help="hierarchical includes part-of/develops-from; is-a checks subclass ancestry only",
    )
    parser.add_argument(
        "--expect-ontology",
        help="comma-separated OLS ontology ids every term must come from",
    )
    parser.add_argument(
        "--strict", action="store_true", help="treat warnings as failures"
    )
    parser.add_argument(
        "--format", choices=("tsv", "json"), default="tsv", help="output format"
    )
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        pairs = read_pairs(args)
    except (ValueError, OSError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2
    if not pairs:
        print("No terms given. See --help.", file=sys.stderr)
        return 2

    if args.branch and not is_curie(args.branch):
        print(f"--branch expects a CURIE, got {args.branch!r}", file=sys.stderr)
        return 2
    if args.branch:
        try:
            root = term_detail(args.branch)
        except OlsError as exc:
            print(f"Could not resolve --branch: {exc}", file=sys.stderr)
            return 2
        if not root or root.get("is_obsolete"):
            print("--branch must resolve to a current OLS term.", file=sys.stderr)
            return 2

    expect_ontologies = (
        {value.strip().lower() for value in args.expect_ontology.split(",") if value.strip()}
        if args.expect_ontology
        else None
    )

    results = []
    for curie, label in pairs:
        try:
            results.append(
                check_term(
                    curie,
                    label,
                    branch=args.branch,
                    expect_ontologies=expect_ontologies,
                    branch_relation=args.branch_relation,
                )
            )
        except OlsError as exc:
            print(f"OLS lookup failed for {curie}: {exc}", file=sys.stderr)
            return 2

    write_output(results, args.format, args.output)

    failed = [r for r in results if r["status"] in FAIL_STATUSES]
    warned = [r for r in results if r["status"] in WARN_STATUSES]
    summary = f"{len(results)} checked, {len(failed)} failed, {len(warned)} warned"
    print(summary, file=sys.stderr)
    if failed or (args.strict and warned):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
