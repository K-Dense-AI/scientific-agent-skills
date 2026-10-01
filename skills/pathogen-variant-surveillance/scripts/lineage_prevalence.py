#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Weekly prevalence of one or more lineages, with intervals and a coverage flag.

Answers "what is circulating, and is it growing" from live sequence counts
rather than from memory. Every number is a count returned by the instance at
the data version printed in the provenance block.

    python3 lineage_prevalence.py XFG.1.1 XFJ.3 --instance sars-cov-2 --where country=USA
    python3 lineage_prevalence.py XFG --sublineages --weeks 12 --growth
    python3 lineage_prevalence.py 2.3.4.4b --instance h5n1 --where country=USA --weeks 52

Proportions carry Wilson intervals. Low-count/age flags are heuristics, not
measured completeness; reporting_lag.py separately describes observed delays.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from lapis_client import (
    LapisError,
    aggregated,
    bin_weekly,
    count,
    data_version,
    describe_instance,
    emit,
    flag_low_coverage,
    lineage_filter,
    logit_slope,
    pick_date_field,
    pick_lineage_field,
    range_keys,
    resolve_base_url,
    surveillance_filters,
    top_values,
    week_range,
    wilson_interval,
)

COLUMNS = (
    "lineage",
    "week",
    "n",
    "total",
    "proportion",
    "ci_low",
    "ci_high",
    "coverage",
)


def parse_where(pairs: list[str], schema: dict) -> dict[str, str]:
    """Turn ``KEY=VALUE`` arguments into filters, checking keys against the schema."""
    filters: dict[str, str] = {}
    types = schema.get("types", {})
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise LapisError(f"--where expects KEY=VALUE, got {pair!r}")
        base = key.split(".")[0]
        for suffix in ("From", "To"):
            if base.endswith(suffix) and base[: -len(suffix)] in types:
                base = base[: -len(suffix)]
                break
        if base not in types:
            near = sorted(n for n in types if base.lower() in n.lower())
            hint = f" Did you mean: {', '.join(near[:6])}?" if near else ""
            raise LapisError(f"{key!r} is not a field on this instance.{hint}")
        filters[key] = value
    return filters


def weekly_counts(
    base_url: str, filters: dict, date_field: str, weeks: list[str], upper_field: str | None = None
) -> tuple[dict[str, int], int]:
    """Weekly counts over the requested window, zero-filled for empty weeks."""
    rows = aggregated(base_url, filters, [date_field] + ([upper_field] if upper_field else []))
    excluded = sum(int(r.get("count") or 0) for r in rows if upper_field and r.get(upper_field) != r.get(date_field))
    rows = [r for r in rows if not upper_field or r.get(upper_field) == r.get(date_field)]
    binned, undated = bin_weekly(rows, date_field)
    return {week: binned.get(week, 0) for week in weeks}, undated + excluded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Weekly lineage prevalence from a LAPIS instance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("lineages", nargs="*",
                        help="lineage or clade names; 'NAME*' includes descendants. "
                             "Omit to discover them with --top")
    parser.add_argument("--top", type=int, metavar="N",
                        help="discover the N most common lineages in the window instead of "
                             "naming them (default when no names are given)")
    parser.add_argument("--instance", default="sars-cov-2", help="registry name (default: sars-cov-2)")
    parser.add_argument("--base-url", help="any other LAPIS deployment")
    parser.add_argument("--lineage-field", help="override the auto-detected lineage column")
    parser.add_argument("--date-field", help="override the auto-detected collection-date column")
    parser.add_argument("--where", action="append", default=[], metavar="KEY=VALUE",
                        help="extra filter, repeatable (e.g. --where country=USA)")
    parser.add_argument("--weeks", type=int, default=26, help="window length in weeks (default: 26)")
    parser.add_argument("--since", help="window start, YYYY-MM-DD; overrides --weeks")
    parser.add_argument("--until", help="window end, YYYY-MM-DD (default: today)")
    parser.add_argument("--sublineages", action="store_true", help="include descendant lineages")
    parser.add_argument("--growth", action="store_true",
                        help="also fit a descriptive weighted log-odds slope")
    parser.add_argument("--lag-days", type=int, default=0,
                        help="flag weeks ending within this many days of today (set from lag review)")
    parser.add_argument("--include-incomplete", action="store_true",
                        help="let low-coverage weeks into the growth fit")
    parser.add_argument("--coverage-fraction", type=float, default=0.4,
                        help="flag weeks below this fraction of older-half median (default: 0.4)")
    parser.add_argument("--format", choices=("table", "tsv", "json"), default="table")
    parser.add_argument("-o", "--output", help="write to a file instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.weeks < 1 or args.lag_days < 0 or not 0 <= args.coverage_fraction <= 1:
            raise LapisError("--weeks must be positive, --lag-days nonnegative, --coverage-fraction in [0, 1]")
        base_url = resolve_base_url(args.instance, args.base_url)
        schema = describe_instance(base_url)
        lineage_field, has_index = pick_lineage_field(schema, args.lineage_field)
        date_field = pick_date_field(schema, "collection", args.date_field)
        where = surveillance_filters(schema, parse_where(args.where, schema))
        reserved = {date_field, *range_keys(date_field), lineage_field}
        if any(k.split('.')[0] in reserved for k in where):
            raise LapisError("use --since/--until and positional lineages instead of --where date/lineage overrides")
        upper_field = date_field.replace("RangeLower", "RangeUpper") if date_field.endswith("RangeLower") else None
        if upper_field and upper_field not in schema["types"]:
            raise LapisError("collection range lacks an upper bound; cannot identify exact dates")
        requested_until = date.fromisoformat(args.until) if args.until else date.today()
        requested_since = date.fromisoformat(args.since) if args.since else requested_until - timedelta(weeks=args.weeks)
    except (LapisError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if requested_since > requested_until:
        print("error: --since is after --until", file=sys.stderr)
        return 2
    if args.top is not None and args.top < 1:
        print("error: --top must be at least 1", file=sys.stderr)
        return 2

    # Snap both ends to ISO week boundaries. A window that starts mid-week gives
    # a first row covering three days and a last row covering four, and neither
    # is comparable to the full weeks between them -- exactly the kind of
    # silently uneven denominator this skill exists to prevent. Widening to whole
    # weeks keeps every row meaning the same thing; a still-unfilled final week
    # shows up through the coverage flag rather than as a short bar.
    since = requested_since - timedelta(days=requested_since.weekday())
    until = requested_until + timedelta(days=6 - requested_until.weekday())
    snapped = (since, until) != (requested_since, requested_until)

    from_key, to_key = range_keys(date_field)
    window = {from_key: since.isoformat(), to_key: until.isoformat(), **where}
    weeks = week_range(since.isoformat(), until.isoformat())

    try:
        version = data_version(base_url)
        totals, undated = weekly_counts(base_url, window, date_field, weeks, upper_field)

        rows: list[dict] = []
        notes: list[str] = []
        fits: dict[str, dict] = {}
        coverage = flag_low_coverage(totals, args.coverage_fraction)
        recent_boundary = date.today() - timedelta(days=args.lag_days)
        for week in weeks:
            if date.fromisoformat(week) + timedelta(days=6) >= recent_boundary:
                coverage[week] = True
        notes.append("coverage is a count/age heuristic, not measured completeness; choose --lag-days after reviewing reporting lag")

        targets = list(args.lineages)
        if args.top is not None or not targets:
            wanted = args.top or 10
            discovery_fields = [lineage_field] + ([date_field, upper_field] if upper_field else [])
            grouped = aggregated(base_url, window, discovery_fields)
            if upper_field:
                # Rank the same exact-date subset used by weekly denominators.
                by_label: dict[str, int] = {}
                for row in grouped:
                    if row.get(date_field) and row.get(date_field) == row.get(upper_field):
                        label = row.get(lineage_field)
                        by_label[label] = by_label.get(label, 0) + int(row.get("count") or 0)
                grouped = [{lineage_field: label, "count": n} for label, n in by_label.items()]
            discovered = top_values(grouped, lineage_field, wanted)
            if not discovered:
                print(
                    f"error: no sequences in {since} to {until}"
                    + (f" with {where}" if where else "")
                    + ". Widen the window or relax the filters.",
                    file=sys.stderr,
                )
                return 1
            notes.append(
                f"discovered the {len(discovered)} most common {lineage_field} "
                f"value{'s' if len(discovered) != 1 else ''} in the window: "
                f"{', '.join(discovered)}"
            )
            targets = discovered + [t for t in targets if t not in discovered]

        for name in targets:
            value = lineage_filter(name, has_index, args.sublineages)
            counts, _ = weekly_counts(
                base_url, {**window, lineage_field: value}, date_field, weeks, upper_field
            )

            if has_index and not value.endswith("*"):
                # Both sides must come from the same kind of query. Summing the
                # weekly bins would drop sequences with no usable collection
                # date, making every lineage that has some look as though it had
                # descendants it does not.
                exact = count(base_url, {**window, lineage_field: value})
                inclusive = count(base_url, {**window, lineage_field: f"{value}*"})
                if inclusive > exact:
                    notes.append(
                        f"{value}: {exact} sequences named exactly {value}, "
                        f"{inclusive} including descendants. Pass --sublineages "
                        f"or write '{value}*' for the second number."
                    )

            for week in weeks:
                k, n = counts[week], totals[week]
                if k > n:
                    raise LapisError("lineage count exceeds denominator; inconsistent filters or snapshot")
                low, high = wilson_interval(k, n)
                rows.append(
                    {
                        "lineage": value,
                        "week": week,
                        "n": k,
                        "total": n,
                        "proportion": f"{(k / n):.4f}" if n else "",
                        "ci_low": f"{low:.4f}" if n else "",
                        "ci_high": f"{high:.4f}" if n else "",
                        "coverage": "low" if coverage.get(week) else "ok",
                    }
                )

            if args.growth:
                usable = [
                    (i, counts[w], totals[w])
                    for i, w in enumerate(weeks)
                    if args.include_incomplete or not coverage.get(w)
                ]
                fit = logit_slope([(float(t), k, n) for t, k, n in usable])
                if fit:
                    fits[value] = fit
                else:
                    notes.append(
                        f"{value}: too few observations for a growth estimate "
                        f"({sum(k for _, k, _ in usable)} sequences across "
                        f"{sum(1 for _, k, _ in usable if k > 0)} non-empty weeks). "
                        "No slope is reported rather than a slope driven by the denominator."
                    )
    except LapisError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        import json

        payload = {
            "meta": {
                "instance": schema["name"],
                "base_url": base_url,
                "data_version": version,
                "lineage_field": lineage_field,
                "lineage_index": has_index,
                "date_field": date_field,
                "window": [since.isoformat(), until.isoformat()],
                "filters": where,
                "undated_sequences": undated,
                "lag_days": args.lag_days,
                "notes": notes,
            },
            "rows": rows,
            "growth": fits,
        }
        text = json.dumps(payload, indent=2)
    else:
        text = emit(rows, COLUMNS, args.format)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)

    sys.stdout.flush()
    print(
        f"\n# {schema['name']} via {base_url}"
        f"\n# data version {version} | {lineage_field}"
        f"{' (lineage-indexed)' if has_index else ' (no lineage index)'}"
        f" | dates from {date_field}"
        f"\n# window {since} to {until}"
        + (f" (widened from {requested_since}..{requested_until} to whole ISO weeks)"
           if snapped else "")
        + (f" | filters {where}" if where else "")
        + (f"\n# {undated} returned records excluded for missing/imprecise collection date" if undated else ""),
        file=sys.stderr,
    )
    for note in notes:
        print(f"# note: {note}", file=sys.stderr)
    if any(coverage.values()):
        flagged = [w for w, bad in coverage.items() if bad]
        print(
            f"# {len(flagged)} week(s) flagged low by denominator/age heuristic "
            f"(earliest {min(flagged)}). Other weeks are not certified complete.",
            file=sys.stderr,
        )
    for name, fit in fits.items():
        print(
            f"# growth {name}: log-odds slope {fit['slope_per_week']:+.3f}/week "
            f"(95% CI {fit['ci_low']:+.3f} to {fit['ci_high']:+.3f}, "
            f"{int(fit['n_weeks'])} weeks, dispersion {fit['dispersion']:.1f}). "
            f"Descriptive only -- confounded by sampling and reporting changes.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
