#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Describe collection-to-submission/release delays among currently visible records.

This is a conditional empirical CDF, not an estimate of eventual completeness.
Monthly cohorts are grouped by both dates. Partial collection dates, negative
lags, missing dates and submissions after the analysis anchor are excluded.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from lapis_client import (
    LapisError, aggregated, data_version, describe_instance, emit,
    pick_date_field, range_keys, resolve_base_url, surveillance_filters,
)

COLUMNS = ("lag_days", "mean_observed", "min_observed", "max_observed", "cohorts")
OFFSETS = (7, 14, 21, 30, 45, 60, 90, 120, 180)


def month_window(anchor: date, months_back: int) -> tuple[date, date]:
    """First and last day of the month ``months_back`` before ``anchor``."""
    total = anchor.year * 12 + (anchor.month - 1) - months_back
    year, month = divmod(total, 12)
    first = date(year, month + 1, 1)
    nxt = date(year + 1, 1, 1) if month == 11 else date(year, month + 2, 1)
    return first, nxt - timedelta(days=1)


def cohort_curve(base_url: str, filters: dict, submission_field: str,
                 collection_field: str, collection_upper: str | None = None,
                 anchor: date | None = None) -> tuple[dict[int, float], int, int] | None:
    """Return (observed delay CDF, eligible count, excluded count) for a cohort.

    A range-lower collection field requires a matching upper bound to retain
    only exact dates. No month-end approximation or negative-lag clamping.
    """
    fields = [collection_field, submission_field]
    if collection_upper:
        fields.append(collection_upper)
    rows = aggregated(base_url, filters, fields)
    lags: list[tuple[int, int]] = []
    dated = excluded = 0
    for row in rows:
        n = int(row.get("count") or 0)
        try:
            submitted = date.fromisoformat(str(row.get(submission_field) or ""))
            collected = date.fromisoformat(str(row.get(collection_field) or ""))
        except ValueError:
            excluded += n
            continue
        if ((collection_upper and row.get(collection_upper) != row.get(collection_field))
                or submitted < collected or (anchor and submitted > anchor)):
            excluded += n
            continue
        lags.append(((submitted - collected).days, n))
        dated += n
    if not dated:
        return ({}, 0, excluded) if excluded else None
    curve = {offset: sum(n for lag, n in lags if lag <= offset) / dated for offset in OFFSETS}
    return curve, dated, excluded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observed collection-to-release delays; not completeness.")
    parser.add_argument("--instance", default="sars-cov-2")
    parser.add_argument("--base-url", help="another trusted public LAPIS deployment")
    parser.add_argument("--date-field", help="collection-date column")
    parser.add_argument("--submission-field", help="submission/release-date column")
    parser.add_argument("--where", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--cohorts", type=int, default=6, help="monthly cohorts (default: 6)")
    parser.add_argument("--skip-months", type=int, default=3, help="youngest cohort in months back (default: 3)")
    parser.add_argument("--target", type=float, default=0.9, help="target observed CDF fraction (default: 0.9)")
    parser.add_argument("--until", help="analysis anchor YYYY-MM-DD, not a historical database snapshot")
    parser.add_argument("--format", choices=("table", "tsv", "json"), default="table")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cohorts < 1 or args.skip_months < 1 or not 0 < args.target <= 1:
            raise LapisError("--cohorts/--skip-months must be positive; --target must be in (0, 1]")
        anchor = date.fromisoformat(args.until) if args.until else date.today()
        base_url = resolve_base_url(args.instance, args.base_url)
        schema = describe_instance(base_url)
        collection = pick_date_field(schema, "collection", args.date_field)
        submission = pick_date_field(schema, "submission", args.submission_field)
        if collection == submission:
            raise LapisError("collection and submission fields must differ")
        upper = collection.replace("RangeLower", "RangeUpper") if collection.endswith("RangeLower") else None
        if upper and upper not in schema["types"]:
            raise LapisError("collection range lacks an upper bound; cannot identify exact dates")
        where = {}
        for pair in args.where:
            key, sep, value = pair.partition("=")
            if not sep or key.split(".")[0] not in schema["types"]:
                raise LapisError(f"bad --where {pair!r}")
            if key.split(".")[0] in {collection, submission, upper}:
                raise LapisError("--where cannot replace collection/submission date selection")
            where[key] = value
        where = surveillance_filters(schema, where)
        version = data_version(base_url)
        from_key, to_key = range_keys(collection)
        curves, sizes, excluded_total = [], [], 0
        for back in range(args.skip_months, args.skip_months + args.cohorts):
            start, end = month_window(anchor, back)
            result = cohort_curve(base_url, {**where, from_key: start.isoformat(), to_key: end.isoformat()},
                                  submission, collection, upper, anchor)
            if result:
                curve, dated, excluded = result
                excluded_total += excluded
                # Cohorts with shorter follow-up cannot contribute long offsets.
                eligible = {o: v for o, v in curve.items() if o <= (anchor - end).days}
                if eligible:
                    curves.append(eligible)
                    sizes.append(dated)
        if not curves:
            print(f"error: no eligible cohort; {excluded_total} records excluded for date quality", file=sys.stderr)
            return 1
        rows, means = [], {}
        for offset in OFFSETS:
            values = [c[offset] for c in curves if offset in c]
            if not values:
                continue
            means[offset] = sum(values) / len(values)
            rows.append({"lag_days": offset, "mean_observed": f"{means[offset]:.3f}",
                         "min_observed": f"{min(values):.3f}", "max_observed": f"{max(values):.3f}",
                         "cohorts": len(values)})
    except (LapisError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(emit(rows, COLUMNS, args.format))
    reached = [o for o, v in means.items() if v >= args.target]
    print(f"\n# {schema['name']} via {base_url} | data version {version}"
          f"\n# collection {collection}; submission/release {submission}; filters {where}"
          f"\n# anchor {anchor}; cohorts {args.skip_months}..{args.skip_months + args.cohorts - 1} months back"
          f"\n# {sum(sizes)} eligible records; {excluded_total} excluded: missing/imprecise/reversed/post-anchor dates"
          "\n# Equal cohort weighting; cohort count may differ by offset, so the mean need not be monotonic.",
          file=sys.stderr)
    if reached:
        cutoff = anchor - timedelta(days=reached[0])
        print(f"# Mean observed CDF reaches {args.target:.0%} by {reached[0]} days; heuristic date {cutoff}."
              "\n# This does not establish completeness or make any collection week trustworthy.", file=sys.stderr)
    else:
        print(f"# No observed offset reaches target {args.target:.0%}; no heuristic date reported.", file=sys.stderr)
    print("# Conditional on records visible now: future submissions can lengthen delays."
          "\n# Release date need not equal first appearance here; historical snapshots are not reconstructed.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
