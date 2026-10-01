#!/usr/bin/env python3
"""Check units, currency, base year, taxonomy, and denominator consistency."""

from __future__ import annotations

import argparse
import re
from typing import Any

from _common import (
    ValidationError,
    error_exit,
    parse_currency,
    parse_iso_date,
    parse_number,
    parse_year,
    read_csv_records,
    require_identifier,
    require_text,
    require_unique_identifiers,
    write_json_report,
)

REQUIRED_FIELDS = (
    "record_id",
    "comparison_group",
    "value",
    "unit",
    "currency",
    "base_year",
    "price_basis",
    "measure_type",
    "geography",
    "period",
    "taxonomy",
    "taxonomy_version",
    "denominator_id",
    "source_id",
)
PRICE_BASES = {
    "nominal",
    "real",
    "current",
    "constant",
    "chained",
    "not-applicable",
}
MEASURE_TYPES = {"stock", "flow", "index", "share", "count", "rate", "price"}
PERIOD_RE = re.compile(
    r"^(?:\d{4}|\d{4}-Q[1-4]|\d{4}-M(?:0[1-9]|1[0-2])|\d{4}-\d{2}-\d{2})$"
)
CONSISTENCY_FIELDS = (
    "unit",
    "currency",
    "base_year",
    "price_basis",
    "measure_type",
    "geography",
    "taxonomy",
    "taxonomy_version",
    "denominator_id",
)


def check(rows: list[dict[str, str]]) -> dict[str, Any]:
    errors: list[str] = []
    record_ids: list[str] = []
    groups: dict[str, dict[str, set[str]]] = {}

    for row_number, row in enumerate(rows, start=2):
        context = f"row {row_number}"
        try:
            record_id = require_identifier(row["record_id"], f"{context}.record_id")
            record_ids.append(record_id)
            group = require_identifier(
                row["comparison_group"], f"{context}.comparison_group"
            )
            parse_number(
                row["value"],
                f"{context}.value",
                minimum=-1e18,
                maximum=1e18,
            )
            unit = require_text(row["unit"], f"{context}.unit", maximum=80)
            currency = parse_currency(
                row["currency"], f"{context}.currency", allow_empty=True
            )
            base_year = require_text(
                row["base_year"],
                f"{context}.base_year",
                allow_empty=True,
                maximum=4,
            )
            if base_year:
                parse_year(base_year, f"{context}.base_year")
            price_basis = require_text(
                row["price_basis"], f"{context}.price_basis", maximum=20
            )
            if price_basis not in PRICE_BASES:
                raise ValidationError(
                    f"{context}.price_basis must be one of "
                    f"{', '.join(sorted(PRICE_BASES))}"
                )
            if currency and (not base_year or price_basis == "not-applicable"):
                raise ValidationError(
                    f"{context}: monetary rows require base_year and price_basis"
                )
            if not currency and price_basis != "not-applicable":
                raise ValidationError(
                    f"{context}: non-monetary rows must use price_basis "
                    "'not-applicable'"
                )

            measure_type = require_text(
                row["measure_type"], f"{context}.measure_type", maximum=20
            )
            if measure_type not in MEASURE_TYPES:
                raise ValidationError(
                    f"{context}.measure_type must be one of "
                    f"{', '.join(sorted(MEASURE_TYPES))}"
                )
            geography = require_text(
                row["geography"], f"{context}.geography", maximum=200
            )
            period = require_text(row["period"], f"{context}.period", maximum=10)
            if not PERIOD_RE.fullmatch(period):
                raise ValidationError(
                    f"{context}.period must be YYYY, YYYY-Qn, YYYY-Mnn, "
                    "or YYYY-MM-DD"
                )
            parse_year(period[:4], f"{context}.period year")
            if len(period) == 10:
                parse_iso_date(period, f"{context}.period")
            taxonomy = require_text(
                row["taxonomy"], f"{context}.taxonomy", allow_empty=True
            )
            taxonomy_version = require_text(
                row["taxonomy_version"],
                f"{context}.taxonomy_version",
                allow_empty=True,
            )
            denominator_id = require_identifier(
                row["denominator_id"], f"{context}.denominator_id"
            )
            require_identifier(row["source_id"], f"{context}.source_id")

            normalized = {
                "unit": unit,
                "currency": currency,
                "base_year": base_year,
                "price_basis": price_basis,
                "measure_type": measure_type,
                "geography": geography,
                "taxonomy": taxonomy,
                "taxonomy_version": taxonomy_version,
                "denominator_id": denominator_id,
            }
            group_values = groups.setdefault(
                group, {field: set() for field in CONSISTENCY_FIELDS}
            )
            for field, value in normalized.items():
                group_values[field].add(value)
        except ValidationError as exc:
            errors.append(str(exc))

    try:
        require_unique_identifiers(record_ids, "record IDs")
    except ValidationError as exc:
        errors.append(str(exc))

    mismatches: dict[str, dict[str, list[str]]] = {}
    for group, values in sorted(groups.items()):
        group_mismatches = {
            field: sorted(observed)
            for field, observed in values.items()
            if len(observed) > 1
        }
        if group_mismatches:
            mismatches[group] = group_mismatches
            errors.append(
                f"comparison group {group!r} mixes: "
                + ", ".join(sorted(group_mismatches))
            )

    return {
        "valid": not errors,
        "record_count": len(rows),
        "comparison_group_count": len(groups),
        "mismatches": mismatches,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check a local CSV for internally comparable units, currencies, base "
            "years, price bases, measure types, geographies, taxonomies, and "
            "denominators."
        )
    )
    parser.add_argument("input", help="Local .csv consistency input")
    parser.add_argument("--output", help="Optional local .json report")
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing --output file"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = check(read_csv_records(args.input, required_fields=REQUIRED_FIELDS))
        write_json_report(report, args.output, force=args.force)
        return 0 if report["valid"] else 1
    except ValidationError as exc:
        return error_exit(exc)


if __name__ == "__main__":
    raise SystemExit(main())
