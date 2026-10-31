#!/usr/bin/env python3
"""Check structured dates, units, denominators, percentages, and totals."""

from __future__ import annotations

import argparse
import math
import sys
from typing import Any

sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    ValidationError,
    error_report,
    load_json_object,
    parse_iso_date,
    require_bool,
    require_data_class,
    require_exact_keys,
    require_identifier,
    require_nonnegative_int,
    require_string,
    write_json_report,
)

TOOL = "consistency_checker"
TOP_LEVEL_FIELDS = {
    "schema_version",
    "artifact_kind",
    "manifest_status",
    "safety_notice",
    "data_classification",
    "authorized_purpose",
    "authorization_verified",
    "provenance_manifest",
    "dates",
    "date_ranges",
    "quantities",
    "proportions",
    "totals",
}


def _array(data: dict[str, Any], field: str, errors: list[str]) -> list[Any]:
    value = data.get(field, [])
    if not isinstance(value, list):
        errors.append(f"{field} must be an array")
        return []
    if len(value) > 10_000:
        errors.append(f"{field} may contain at most 10,000 items")
        return value[:10_000]
    return value


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field} must be a number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValidationError(f"{field} must be a finite representable number") from exc
    if not math.isfinite(number):
        raise ValidationError(f"{field} must be finite")
    return number


def _track_id(
    value: Any,
    field: str,
    seen: set[str],
    errors: list[str],
) -> str | None:
    try:
        identifier = require_identifier(value, field)
    except ValidationError as exc:
        errors.append(str(exc))
        return None
    if identifier in seen:
        errors.append(f"duplicate check id: {identifier}")
    seen.add(identifier)
    return identifier


def validate_consistency(data: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic discrepancies without changing any values."""
    errors: list[str] = []
    discrepancies: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    checked = 0

    try:
        require_exact_keys(data, TOP_LEVEL_FIELDS, "manifest")
        if data.get("schema_version") != "2.0":
            raise ValidationError("schema_version must be 2.0")
        if data.get("manifest_status") != "BLOCKED_INCOMPLETE":
            raise ValidationError("manifest_status must remain BLOCKED_INCOMPLETE")
        require_string(data.get("safety_notice"), "safety_notice", max_length=1000)
        require_string(data.get("authorized_purpose"), "authorized_purpose")
        if not require_bool(data.get("authorization_verified"), "authorization_verified"):
            raise ValidationError("authorization_verified must be true")
        require_string(data.get("provenance_manifest"), "provenance_manifest")
    except ValidationError as exc:
        errors.append(str(exc))
    if data.get("artifact_kind") != "consistency_manifest":
        errors.append("artifact_kind must be consistency_manifest")
    try:
        require_data_class(data.get("data_classification"))
    except ValidationError as exc:
        errors.append(str(exc))

    for index, item in enumerate(_array(data, "dates", errors)):
        try:
            item = require_exact_keys(
                item,
                {"id", "date", "source_fact_id"},
                f"dates[{index}]",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        check_id = _track_id(item.get("id"), f"dates[{index}].id", seen_ids, errors)
        try:
            parse_iso_date(item.get("date"), f"dates[{index}].date")
            require_identifier(
                item.get("source_fact_id"),
                f"dates[{index}].source_fact_id",
            )
            checked += 1
        except ValidationError as exc:
            errors.append(str(exc))
        if check_id is None:
            continue

    for index, item in enumerate(_array(data, "date_ranges", errors)):
        try:
            item = require_exact_keys(
                item,
                {"id", "start", "end", "source_fact_id"},
                f"date_ranges[{index}]",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        check_id = _track_id(
            item.get("id"),
            f"date_ranges[{index}].id",
            seen_ids,
            errors,
        )
        try:
            start = parse_iso_date(item.get("start"), f"date_ranges[{index}].start")
            end = parse_iso_date(item.get("end"), f"date_ranges[{index}].end")
            require_identifier(
                item.get("source_fact_id"),
                f"date_ranges[{index}].source_fact_id",
            )
            checked += 1
            if start > end and check_id:
                discrepancies.append(f"{check_id}: start date is after end date")
        except ValidationError as exc:
            errors.append(str(exc))

    series_units: dict[str, str] = {}
    for index, item in enumerate(_array(data, "quantities", errors)):
        try:
            item = require_exact_keys(
                item,
                {
                    "id",
                    "series_id",
                    "value",
                    "unit",
                    "expected_unit",
                    "source_fact_id",
                },
                f"quantities[{index}]",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        check_id = _track_id(
            item.get("id"),
            f"quantities[{index}].id",
            seen_ids,
            errors,
        )
        try:
            series_id = require_identifier(
                item.get("series_id"),
                f"quantities[{index}].series_id",
            )
            _finite_number(item.get("value"), f"quantities[{index}].value")
            unit = require_string(
                item.get("unit"),
                f"quantities[{index}].unit",
                max_length=80,
            )
            require_identifier(
                item.get("source_fact_id"),
                f"quantities[{index}].source_fact_id",
            )
            checked += 1
            prior = series_units.get(series_id)
            if prior is not None and prior != unit and check_id:
                discrepancies.append(
                    f"{check_id}: unit {unit!r} differs from prior series unit {prior!r}"
                )
            else:
                series_units[series_id] = unit
            expected = item.get("expected_unit")
            if expected is not None:
                expected_unit = require_string(
                    expected,
                    f"quantities[{index}].expected_unit",
                    max_length=80,
                )
                if expected_unit != unit and check_id:
                    discrepancies.append(
                        f"{check_id}: unit does not match expected_unit"
                    )
        except ValidationError as exc:
            errors.append(str(exc))

    for index, item in enumerate(_array(data, "proportions", errors)):
        try:
            item = require_exact_keys(
                item,
                {
                    "id",
                    "numerator",
                    "denominator",
                    "reported_percent",
                    "tolerance_percentage_points",
                    "source_fact_id",
                },
                f"proportions[{index}]",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        check_id = _track_id(
            item.get("id"),
            f"proportions[{index}].id",
            seen_ids,
            errors,
        )
        try:
            numerator = require_nonnegative_int(
                item.get("numerator"),
                f"proportions[{index}].numerator",
            )
            denominator = require_nonnegative_int(
                item.get("denominator"),
                f"proportions[{index}].denominator",
            )
            reported = _finite_number(
                item.get("reported_percent"),
                f"proportions[{index}].reported_percent",
            )
            tolerance = _finite_number(
                item.get("tolerance_percentage_points", 0.05),
                f"proportions[{index}].tolerance_percentage_points",
            )
            require_identifier(
                item.get("source_fact_id"),
                f"proportions[{index}].source_fact_id",
            )
            checked += 1
            if denominator == 0:
                errors.append(f"proportions[{index}].denominator must be greater than zero")
            elif numerator > denominator and check_id:
                discrepancies.append(f"{check_id}: numerator exceeds denominator")
            elif not 0 <= reported <= 100 and check_id:
                discrepancies.append(f"{check_id}: reported_percent is outside 0-100")
            elif tolerance < 0:
                errors.append(
                    f"proportions[{index}].tolerance_percentage_points must be non-negative"
                )
            else:
                calculated = numerator / denominator * 100
                if abs(calculated - reported) > tolerance and check_id:
                    discrepancies.append(
                        f"{check_id}: reported_percent differs from n/N beyond tolerance"
                    )
        except ValidationError as exc:
            errors.append(str(exc))

    for index, item in enumerate(_array(data, "totals", errors)):
        try:
            item = require_exact_keys(
                item,
                {"id", "components", "reported_total", "source_fact_ids"},
                f"totals[{index}]",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        check_id = _track_id(
            item.get("id"),
            f"totals[{index}].id",
            seen_ids,
            errors,
        )
        try:
            components = item.get("components")
            if not isinstance(components, list) or not components:
                raise ValidationError(f"totals[{index}].components must be non-empty")
            parsed_components = [
                require_nonnegative_int(value, f"totals[{index}].components")
                for value in components
            ]
            reported_total = require_nonnegative_int(
                item.get("reported_total"),
                f"totals[{index}].reported_total",
            )
            source_fact_ids = item.get("source_fact_ids")
            if not isinstance(source_fact_ids, list) or not source_fact_ids:
                raise ValidationError(
                    f"totals[{index}].source_fact_ids must be non-empty"
                )
            for fact_id in source_fact_ids:
                require_identifier(fact_id, f"totals[{index}].source_fact_ids")
            checked += 1
            if sum(parsed_components) != reported_total and check_id:
                discrepancies.append(f"{check_id}: components do not equal reported_total")
        except ValidationError as exc:
            errors.append(str(exc))

    if checked == 0:
        errors.append("manifest contains no valid checks")
    if not discrepancies and not errors:
        warnings.append("No discrepancy was found within the declared checks and tolerances.")

    status = (
        "BLOCKED_INVALID_SCHEMA"
        if errors
        else "DISCREPANCIES_REQUIRE_RESOLUTION"
        if discrepancies
        else "CONSISTENT_WITHIN_DECLARED_TOLERANCES_REVIEW_REQUIRED"
    )
    return {
        "tool": TOOL,
        "status": status,
        "checks_completed": checked,
        "errors": errors,
        "discrepancies": discrepancies,
        "warnings": warnings,
        "limitations": [
            "No source was chosen as authoritative and no value was changed.",
            "Arithmetic and format checks do not validate clinical or statistical meaning.",
        ],
        "review_required": True,
        "authorizes_clinical_use_or_submission": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check bounded structured dates, units, n/N percentages, and totals. "
            "Does not infer, convert, reconcile, or alter values."
        )
    )
    parser.add_argument("input_file", help="Local consistency manifest (.json)")
    parser.add_argument("-o", "--output", help="Optional local JSON report")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _, data = load_json_object(args.input_file)
        report = validate_consistency(data)
    except (OSError, ValidationError) as exc:
        report = error_report(TOOL, exc)
    try:
        write_json_report(report, args.output, overwrite=args.overwrite)
    except (OSError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return (
        0
        if report["status"]
        == "CONSISTENT_WITHIN_DECLARED_TOLERANCES_REVIEW_REQUIRED"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
