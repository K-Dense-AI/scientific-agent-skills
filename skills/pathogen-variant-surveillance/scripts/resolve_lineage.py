#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Resolve a lineage name against the live nomenclature before trusting it.

Pango names are not stable identifiers. They are minted continuously, aliased
through a key that must be fetched to be read, and **withdrawn or redesignated
after the fact** -- so a remembered lineage fact is not merely stale, it can be
actively wrong. This script answers, for each name: does it still exist, what
does it expand to, what is it descended from, and how many sequences carry it.

    python3 resolve_lineage.py XFG.23.1.3 PQ.17 PC.2
    python3 resolve_lineage.py XFG --descendants
    python3 resolve_lineage.py 2.3.4.4b --instance h5n1

Exit code is 1 when any name is withdrawn, unknown or unverified, so it gates
a manuscript's lineage list.
"""
from __future__ import annotations

import argparse
import re
import sys

from lapis_client import (
    LapisError,
    SnapshotChanged,
    children_map,
    count,
    data_version,
    descendants,
    describe_instance,
    emit,
    fetch_lineage_notes,
    fetch_pango_aliases,
    lineage_definition,
    lineage_field_candidates,
    parent_chain,
    pango_provenance,
    pick_lineage_field,
    recombinant_parents,
    resolve_base_url,
    surveillance_filters,
    unalias_full,
)

COLUMNS = (
    "query",
    "status",
    "unaliased",
    "parent",
    "recombinant_of",
    "descendants",
    "sequences",
    "detail",
)
PANGO_FIELDS = {"pangoLineage", "nextcladePangoLineage"}
REDESIGNATED = re.compile(r"[Rr]edesignated as ([A-Za-z][A-Za-z0-9.]*)")


def normalise(name: str) -> str:
    """Uppercase the alphabetic head so ``xfg.1`` matches ``XFG.1``."""
    head, sep, tail = name.strip().partition(".")
    return f"{head.upper()}{sep}{tail}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check lineage names against the live nomenclature.",
    )
    parser.add_argument("names", nargs="+", help="lineage or clade names to resolve")
    parser.add_argument("--instance", default="sars-cov-2", help="registry name (default: sars-cov-2)")
    parser.add_argument("--base-url", help="any other LAPIS deployment")
    parser.add_argument("--lineage-field", help="override the auto-detected lineage column")
    parser.add_argument("--descendants", action="store_true",
                        help="list every descendant lineage instead of counting them")
    parser.add_argument("--no-counts", action="store_true",
                        help="skip the sequence counts (one fewer request per name)")
    parser.add_argument("--format", choices=("table", "tsv", "json"), default="table")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        base_url = resolve_base_url(args.instance, args.base_url)
        schema = describe_instance(base_url)
        lineage_field, has_index = pick_lineage_field(schema, args.lineage_field)
        # Fetched here, not inside the provenance f-string: a network failure at
        # print time would raise after the table had already been written.
        version = data_version(base_url)
    except LapisError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    definition: dict = {}
    if has_index:
        try:
            definition = lineage_definition(base_url, lineage_field)
        except LapisError as exc:
            print(f"error: no lineage definition for {lineage_field}: {exc}", file=sys.stderr)
            return 2

    aliases: dict = {}
    notes: dict = {}
    if lineage_field in PANGO_FIELDS:
        try:
            aliases = fetch_pango_aliases()
            notes = fetch_lineage_notes()
        except LapisError as exc:
            print(f"error: pango-designation unreachable: {exc}", file=sys.stderr)
            return 2

    # Inverted once: the SARS-CoV-2 definition holds thousands of entries, so
    # rebuilding it per name makes a list of lineages quadratic.
    children = children_map(definition)

    rows: list[dict] = []
    failures = 0
    for raw in args.names:
        name = normalise(raw) if lineage_field in PANGO_FIELDS else raw.strip()
        note = notes.get(name, {})
        in_definition = name in definition

        if note.get("status") == "withdrawn":
            status = "withdrawn"
        elif note.get("status") == "designated" or (in_definition and lineage_field not in PANGO_FIELDS):
            status = "current"
        elif notes or definition:
            status = "unknown"
        else:
            status = "unverified"
        if status in {"withdrawn", "unknown", "unverified"}:
            failures += 1

        detail = note.get("note", "")
        successor = REDESIGNATED.search(detail)
        if successor:
            detail = f"now {successor.group(1)}; {detail}"
        elif status == "unknown":
            detail = "no such name in the live nomenclature for this instance"

        chain = parent_chain(name, definition) if definition else []
        kids = descendants(name, definition, children) if definition else []

        sequences: object = ""
        if not args.no_counts:
            try:
                query = f"{name}*" if has_index else name
                sequences = count(base_url, surveillance_filters(schema, {lineage_field: query}))
            except SnapshotChanged as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
            except LapisError as exc:
                # An indexed column rejects an unknown lineage outright rather
                # than answering 0 -- which is the one place a typo is caught
                # for you. An unindexed column would have returned 0 instead.
                sequences = "n/a" if "not a valid lineage" in str(exc) else "error"
                if sequences == "error":
                    failures += 1

        rows.append(
            {
                "query": raw,
                "status": status,
                "unaliased": unalias_full(name, aliases) if aliases else "",
                "parent": chain[0] if chain else "",
                "recombinant_of": "+".join(recombinant_parents(unalias_full(name, aliases), aliases)) if aliases else "",
                "descendants": ", ".join(kids) if args.descendants else len(kids),
                "sequences": sequences,
                "detail": detail,
            }
        )

    print(emit(rows, COLUMNS, args.format))
    sys.stdout.flush()

    print(
        f"\n# {schema['name']} via {base_url} | data version {version}"
        f"\n# lineage column {lineage_field}"
        f"{' with a lineage index' if has_index else ' with no lineage index'}"
        + (
            f"\n# nomenclature from pango-designation ({len(notes)} names, "
            f"{sum(1 for v in notes.values() if v['status'] == 'withdrawn')} withdrawn)"
            f"\n# source content {pango_provenance()}"
            if notes
            else ""
        )
        + ("\n# 'sequences' counts the lineage and its descendants" if has_index else "")
        + f"\n# record filters {surveillance_filters(schema, {})}",
        file=sys.stderr,
    )
    others = [n for n, _ in lineage_field_candidates(schema) if n != lineage_field]
    if others:
        print(
            f"# other lineage-like columns here: {', '.join(others)} "
            f"(select one with --lineage-field)",
            file=sys.stderr,
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
