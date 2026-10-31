#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Mutations carried by a lineage, or the difference between two lineages.

Use this to answer "what distinguishes this lineage" and "does my assay target
still match" from current sequences, instead of from a lineage's founding
description -- which drifts as sublineages accumulate substitutions.

    python3 mutation_profile.py XFG.1.1 --gene S --min-proportion 0.9
    python3 mutation_profile.py XFG.23.1.3 --versus XFG.1.1 --gene S
    python3 mutation_profile.py 2.3.4.4b --instance h5n1 --gene HA --min-proportion 0.8
    python3 mutation_profile.py XFG --sublineages --nucleotide --since 2026-01-01

``proportion`` is over ``coverage`` -- the sequences that actually resolved that
site -- not over every matching sequence. A site with poor coverage can show a
high proportion on very few sequences, so read the coverage column before quoting a
proportion.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from lapis_client import (
    LapisError,
    count,
    data_version,
    describe_instance,
    emit,
    lineage_filter,
    mutations,
    pick_date_field,
    pick_lineage_field,
    range_keys,
    request,
    resolve_base_url,
    surveillance_filters,
)

PROFILE_COLUMNS = ("mutation", "gene", "position", "from", "to", "proportion", "count", "coverage")
DIFF_COLUMNS = ("mutation", "gene", "position", "verdict", "prop_a", "prop_b", "n_a", "n_b", "coverage_a", "coverage_b")


def parse_where(pairs: list[str], schema: dict) -> dict[str, str]:
    """Turn ``KEY=VALUE`` arguments into filters, checking keys against the schema."""
    filters: dict[str, str] = {}
    types = schema.get("types", {})
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise LapisError(f"--where expects KEY=VALUE, got {pair!r}")
        if key.split(".")[0] not in types:
            raise LapisError(f"{key!r} is not a field on this instance")
        filters[key] = value
    return filters


def profile(base_url: str, filters: dict, *, amino_acid: bool, min_proportion: float,
            gene: str | None) -> dict[str, dict]:
    """Mutation rows keyed by mutation string, optionally restricted to one gene."""
    rows = mutations(base_url, filters, amino_acid=amino_acid, min_proportion=min_proportion)
    keyed: dict[str, dict] = {}
    for row in rows:
        if gene and str(row.get("sequenceName") or "").upper() != gene.upper():
            continue
        keyed[row["mutation"]] = row
    return keyed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mutation profile of a lineage.")
    parser.add_argument("lineage", help="lineage or clade name; 'NAME*' includes descendants")
    parser.add_argument("--versus", help="second lineage to diff against")
    parser.add_argument("--instance", default="sars-cov-2", help="registry name (default: sars-cov-2)")
    parser.add_argument("--base-url", help="any other LAPIS deployment")
    parser.add_argument("--lineage-field", help="override the auto-detected lineage column")
    parser.add_argument("--date-field", help="override the auto-detected collection-date column")
    parser.add_argument("--gene", help="restrict to one gene or segment (e.g. S, HA, seg4)")
    parser.add_argument("--nucleotide", action="store_true",
                        help="nucleotide instead of amino-acid mutations")
    parser.add_argument("--min-proportion", type=float, default=0.8,
                        help="report mutations at or above this proportion (default: 0.8)")
    parser.add_argument("--sublineages", action="store_true", help="include descendant lineages")
    parser.add_argument("--since", help="restrict to sequences collected on or after YYYY-MM-DD")
    parser.add_argument("--where", action="append", default=[], metavar="KEY=VALUE",
                        help="extra filter, repeatable")
    parser.add_argument("--format", choices=("table", "tsv", "json"), default="table")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if not 0 < args.min_proportion <= 1:
            raise LapisError("--min-proportion must be in (0, 1]")
        base_url = resolve_base_url(args.instance, args.base_url)
        schema = describe_instance(base_url)
        lineage_field, has_index = pick_lineage_field(schema, args.lineage_field)
        where = surveillance_filters(schema, parse_where(args.where, schema))
        if lineage_field in where:
            raise LapisError("set the lineage with the positional argument, not --where")
        if args.since:
            date.fromisoformat(args.since)
            date_field = pick_date_field(schema, "collection", args.date_field)
            where[range_keys(date_field)[0]] = args.since
        if args.gene:
            reference = request(base_url, "sample/referenceGenome")
            names = [r["name"] for r in reference["nucleotideSequences" if args.nucleotide else "genes"]]
            matches = [n for n in names if n.upper() == args.gene.upper()]
            if len(matches) != 1:
                raise LapisError(f"unknown {'segment' if args.nucleotide else 'gene'} {args.gene!r}; choose from {names}")
            args.gene = matches[0]

        # Fetch unpruned mutation rows for comparisons. A missing row still
        # has unknown coverage and cannot establish a zero proportion.
        diff_floor = 0.0

        primary = lineage_filter(args.lineage, has_index, args.sublineages)
        base_filters = {**where, lineage_field: primary}
        n_primary = count(base_url, base_filters)
        if n_primary == 0:
            print(
                f"error: no sequences match {lineage_field}={primary}"
                + (f" with {where}" if where else "")
                + ". Check the name with resolve_lineage.py.",
                file=sys.stderr,
            )
            return 1

        first = profile(
            base_url,
            base_filters,
            amino_acid=not args.nucleotide,
            min_proportion=args.min_proportion if not args.versus else diff_floor,
            gene=args.gene,
        )

        if not args.versus:
            rows = [
                {
                    "mutation": m["mutation"],
                    "gene": m.get("sequenceName", ""),
                    "position": m.get("position", ""),
                    "from": m.get("mutationFrom", ""),
                    "to": m.get("mutationTo", ""),
                    "proportion": f"{m['proportion']:.3f}",
                    "count": m.get("count", ""),
                    "coverage": m.get("coverage", ""),
                }
                for m in sorted(
                    first.values(),
                    key=lambda r: (str(r.get("sequenceName")), int(r.get("position") or 0)),
                )
            ]
            summary = (
                f"\n# {schema['name']} via {base_url} | data version {data_version(base_url)}"
                f"\n# {lineage_field}={primary} | {n_primary} sequences"
                f" | {'nucleotide' if args.nucleotide else 'amino acid'} mutations"
                f" at proportion >= {args.min_proportion}"
                f"\n# proportion is over per-site coverage, not over all {n_primary} sequences"
            )
        else:
            secondary = lineage_filter(args.versus, has_index, args.sublineages)
            n_secondary = count(base_url, {**where, lineage_field: secondary})
            if n_secondary == 0:
                print(f"error: no sequences match {lineage_field}={secondary}", file=sys.stderr)
                return 1
            second = profile(
                base_url,
                {**where, lineage_field: secondary},
                amino_acid=not args.nucleotide,
                min_proportion=diff_floor,
                gene=args.gene,
            )

            rows = []
            for mutation in sorted(set(first) | set(second)):
                a = first.get(mutation, {})
                b = second.get(mutation, {})
                pa = float(a["proportion"]) if a and a.get("coverage", 0) > 0 else None
                pb = float(b["proportion"]) if b and b.get("coverage", 0) > 0 else None
                if max(pa or 0.0, pb or 0.0) < args.min_proportion:
                    continue
                if pa is None or pb is None:
                    verdict = "not_comparable"
                elif pa >= args.min_proportion and pb < args.min_proportion:
                    verdict = "above_a_only"
                elif pb >= args.min_proportion and pa < args.min_proportion:
                    verdict = "above_b_only"
                elif pa >= args.min_proportion and pb >= args.min_proportion:
                    verdict = "above_both"
                else:
                    continue
                source = a or b
                rows.append(
                    {
                        "mutation": mutation,
                        "gene": source.get("sequenceName", ""),
                        "position": source.get("position", ""),
                        "verdict": verdict,
                        "prop_a": f"{pa:.3f}" if pa is not None else None,
                        "prop_b": f"{pb:.3f}" if pb is not None else None,
                        "n_a": a.get("count"),
                        "n_b": b.get("count"),
                        "coverage_a": a.get("coverage"),
                        "coverage_b": b.get("coverage"),
                    }
                )
            rows.sort(key=lambda r: (str(r["gene"]), int(r["position"] or 0)))
            summary = (
                f"\n# {schema['name']} via {base_url} | data version {data_version(base_url)}"
                f"\n# A = {primary} ({n_primary} sequences), B = {secondary} ({n_secondary})"
                f"\n# verdict is relative to a {args.min_proportion} proportion threshold; not evolutionary gain/loss"
                f"\n# absent rows have unknown proportion/coverage, never an inferred zero"
            )
        summary += f"\n# filters {where} | gene/segment {args.gene or 'all'} | lineage field {lineage_field}"
    except (LapisError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(emit(rows, DIFF_COLUMNS if args.versus else PROFILE_COLUMNS, args.format))
    sys.stdout.flush()
    print(summary, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
