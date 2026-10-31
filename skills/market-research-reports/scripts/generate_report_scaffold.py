#!/usr/bin/env python3
"""Generate a bounded local evidence-first market-report workspace."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from _common import (
    ValidationError,
    error_exit,
    parse_currency,
    parse_iso_date,
    parse_year,
    read_json,
    require_identifier,
    require_list,
    require_object,
    require_text,
    write_json_report,
)
from forecast_sensitivity import MAX_HORIZON

PERIOD_RE = re.compile(r"^\d{4}-\d{4}$")
SOURCE_FIELDS = (
    "source_id",
    "title",
    "publisher",
    "url",
    "source_type",
    "publication_date",
    "retrieval_date",
    "geography",
    "currency",
    "base_year",
    "price_basis",
    "measure_type",
    "unit",
    "taxonomy",
    "taxonomy_version",
    "revision_status",
    "method",
    "sample",
    "limitations",
    "license_or_terms",
    "archive_path",
)
CLAIM_FIELDS = (
    "claim_id",
    "claim_text",
    "claim_type",
    "source_ids",
    "calculation_id",
    "assumption_ids",
    "location",
    "as_of_date",
    "geography",
    "currency",
    "base_year",
    "price_basis",
    "measure_type",
    "unit",
    "taxonomy",
    "taxonomy_version",
    "revision_status",
    "confidence",
    "notes",
)
COMPETITOR_FIELDS = (
    "competitor_id",
    "competitor_name",
    "feature_id",
    "feature_name",
    "status",
    "evidence_source_ids",
    "as_of_date",
    "geography",
    "product_scope",
    "notes",
)
CONSISTENCY_FIELDS = (
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
ASSUMPTION_FIELDS = (
    "assumption_id",
    "description",
    "downside_value",
    "base_value",
    "upside_value",
    "unit",
    "source_ids",
    "rationale",
)


def _string_list(value: Any, context: str) -> list[str]:
    items = require_list(value, context, minimum=1, maximum=100)
    return [
        require_text(item, f"{context}[{index}]", maximum=500)
        for index, item in enumerate(items)
    ]


def _period(value: Any, context: str) -> str:
    text = require_text(value, context, maximum=9)
    if not PERIOD_RE.fullmatch(text):
        raise ValidationError(f"{context} must be YYYY-YYYY")
    start, end = (int(part) for part in text.split("-"))
    if start > end:
        raise ValidationError(f"{context} start year must not exceed end year")
    parse_year(start, context)
    parse_year(end, context)
    return text


def validate_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    required = (
        "schema_version",
        "report_id",
        "title",
        "subtitle",
        "prepared_for",
        "prepared_by",
        "classification",
        "market_definition",
        "inclusions",
        "exclusions",
        "geography",
        "currency",
        "base_year",
        "price_basis",
        "taxonomy",
        "taxonomy_version",
        "historical_period",
        "forecast_period",
        "retrieval_cutoff",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValidationError(f"manifest is missing: {', '.join(missing)}")
    if require_text(payload["schema_version"], "schema_version", maximum=10) != "1.0":
        raise ValidationError("schema_version must be '1.0'")
    classification = require_text(
        payload["classification"], "classification", maximum=20
    )
    if classification not in {"public", "internal", "confidential"}:
        raise ValidationError(
            "classification must be public, internal, or confidential"
        )
    price_basis = require_text(payload["price_basis"], "price_basis", maximum=20)
    if price_basis not in {"nominal", "real", "current", "constant"}:
        raise ValidationError(
            "price_basis must be nominal, real, current, or constant"
        )
    historical = _period(payload["historical_period"], "historical_period")
    forecast = _period(payload["forecast_period"], "forecast_period")
    historical_end = int(historical.split("-")[1])
    forecast_start, forecast_end = (int(year) for year in forecast.split("-"))
    if forecast_start != historical_end + 1:
        raise ValidationError(
            "forecast_period must begin the year after historical_period ends; "
            "include any bridge estimates explicitly in the historical input"
        )
    if forecast_end - historical_end > MAX_HORIZON:
        raise ValidationError(f"forecast horizon must not exceed {MAX_HORIZON} years")
    return {
        "schema_version": "1.0",
        "report_id": require_identifier(payload["report_id"], "report_id"),
        "title": require_text(payload["title"], "title", maximum=200),
        "subtitle": require_text(payload["subtitle"], "subtitle", maximum=300),
        "prepared_for": require_text(
            payload["prepared_for"], "prepared_for", maximum=200
        ),
        "prepared_by": require_text(
            payload["prepared_by"], "prepared_by", maximum=200
        ),
        "classification": classification,
        "market_definition": require_text(
            payload["market_definition"], "market_definition", maximum=2_000
        ),
        "inclusions": _string_list(payload["inclusions"], "inclusions"),
        "exclusions": _string_list(payload["exclusions"], "exclusions"),
        "geography": require_text(payload["geography"], "geography", maximum=200),
        "currency": parse_currency(payload["currency"], "currency"),
        "base_year": parse_year(payload["base_year"], "base_year"),
        "price_basis": price_basis,
        "taxonomy": require_text(payload["taxonomy"], "taxonomy", maximum=100),
        "taxonomy_version": require_text(
            payload["taxonomy_version"], "taxonomy_version", maximum=100
        ),
        "historical_period": historical,
        "forecast_period": forecast,
        "retrieval_cutoff": parse_iso_date(
            payload["retrieval_cutoff"], "retrieval_cutoff"
        ),
    }


def _safe_new_directory(raw_path: str | Path) -> Path:
    path = Path(raw_path).expanduser()
    if path.exists() or path.is_symlink():
        raise ValidationError(f"output directory already exists: {path}")
    try:
        parent = path.parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValidationError(f"output parent does not exist: {path.parent}") from exc
    if not parent.is_dir():
        raise ValidationError(f"output parent is not a directory: {parent}")
    if path.name in {"", ".", ".."}:
        raise ValidationError("output directory name is invalid")
    return parent / path.name


def _write_csv_header(path: Path, fields: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow(fields)


def _one_line(value: str) -> str:
    return " ".join(value.split())


def generate(manifest: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    destination = _safe_new_directory(output_dir)
    destination.mkdir(mode=0o755)
    (destination / "data").mkdir()
    (destination / "analysis").mkdir()
    (destination / "sources").mkdir()

    with (destination / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")

    inclusions = "\n".join(f"- {item}" for item in manifest["inclusions"])
    exclusions = "\n".join(f"- {item}" for item in manifest["exclusions"])
    report = f"""# {_one_line(manifest["title"])}

{_one_line(manifest["subtitle"])}

Prepared for: {_one_line(manifest["prepared_for"])}
Prepared by: {_one_line(manifest["prepared_by"])}
Retrieval cutoff: {manifest["retrieval_cutoff"]}
Classification: {manifest["classification"]}

> This report separates sourced facts, calculations, assumptions, forecasts, and
> recommendations. Inline claim IDs map to `data/claims.csv`; source IDs map to
> `data/source_ledger.csv`. It is not investment, legal, or financial advice.

## Executive synopsis

State only findings supported by claim IDs. Present market-size and forecast
results as scenario ranges, not as a single certain value.

## 1. Scope and market definition

**Definition:** {manifest["market_definition"]}

**Geography:** {manifest["geography"]}
**Currency/base:** {manifest["currency"]}, {manifest["price_basis"]},
base year {manifest["base_year"]}
**Taxonomy:** {manifest["taxonomy"]} {manifest["taxonomy_version"]}
**Historical period:** {manifest["historical_period"]}
**Forecast period:** {manifest["forecast_period"]}

### Included
{inclusions}

### Excluded
{exclusions}

## 2. Evidence and methodology

Describe source hierarchy, retrieval dates, revisions, conflicts, conversions,
survey methods, and limitations.

## 3. Market sizing and reconciliation

Report top-down and bottom-up TAM estimates separately. Show denominator,
coverage keys, excluded categories, SAM filters, SOM capture assumptions,
scenario range, sensitivity, and reconciliation gap.

## 4. Demand and customer evidence

Separate observed demand, survey estimates, interview themes, and analyst
interpretation. Do not generalize qualitative interviews to a population.

## 5. Competitive landscape

Define product and geographic scope before calculating shares or concentration.
Use the evidence-linked competitor matrix; label unknowns.

## 6. Forecast scenarios

Describe each conditional scenario, rate path, assumptions, drivers, inhibitors,
and sensitivity. Do not label scenario ranges as confidence intervals.

## 7. Regulation, risks, and uncertainties

Distinguish enacted rules, proposed rules, analyst judgments, and legal advice.

## 8. Implications and options

Keep recommendations distinct from sourced findings. State dependencies,
decision thresholds, and disconfirming evidence.

## Limitations

List missing data, source conflicts, taxonomy breaks, revisions, sampling and
nonresponse issues, model limitations, and residual uncertainty.

## References

Render references from `data/source_ledger.csv`; do not cite unmapped sources.
"""
    (destination / "report.md").write_text(report, encoding="utf-8")

    _write_csv_header(destination / "data" / "source_ledger.csv", SOURCE_FIELDS)
    _write_csv_header(destination / "data" / "claims.csv", CLAIM_FIELDS)
    _write_csv_header(
        destination / "data" / "competitor_feature_matrix.csv", COMPETITOR_FIELDS
    )
    _write_csv_header(
        destination / "data" / "consistency_input.csv", CONSISTENCY_FIELDS
    )
    _write_csv_header(destination / "data" / "assumptions.csv", ASSUMPTION_FIELDS)

    sizing = {
        "schema_version": "1.0",
        "metadata": {
            "market_id": manifest["report_id"],
            "market_definition": manifest["market_definition"],
            "geography": manifest["geography"],
            "currency": manifest["currency"],
            "base_year": manifest["base_year"],
            "price_basis": manifest["price_basis"],
            "unit": f"{manifest['currency']} per year",
            "taxonomy": manifest["taxonomy"],
            "taxonomy_version": manifest["taxonomy_version"],
            "denominator_id": "define-denominator",
            "as_of_date": manifest["retrieval_cutoff"],
        },
        "top_down": {"components": []},
        "bottom_up": {"components": []},
        "scenarios": [],
        "reconciliation_tolerance_percent": 20.0,
    }
    forecast = {
        "schema_version": "1.0",
        "metadata": {
            "series_id": "define-series",
            "description": "Replace with the forecast measure",
            "geography": manifest["geography"],
            "currency": manifest["currency"],
            "base_year": str(manifest["base_year"]),
            "price_basis": manifest["price_basis"],
            "unit": f"{manifest['currency']} per year",
            "measure_type": "flow",
            "as_of_date": manifest["retrieval_cutoff"],
            "source_ids": [],
        },
        "start_year": int(manifest["historical_period"].split("-")[1]),
        "start_value": 0,
        "horizon_years": (
            int(manifest["forecast_period"].split("-")[1])
            - int(manifest["historical_period"].split("-")[1])
        ),
        "scenarios": [],
        "sensitivity": {
            "base_scenario_id": "base",
            "growth_rate_shifts": [-0.02, 0.0, 0.02],
        },
    }
    for name, payload in (
        ("market_sizing.json", sizing),
        ("forecast_sensitivity.json", forecast),
    ):
        with (destination / "analysis" / name).open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")

    checklist = """# Review checklist

- [ ] Scope, inclusions, exclusions, geography, period, taxonomy, and denominator are explicit.
- [ ] Every factual or quantitative claim maps to source IDs.
- [ ] Publication and retrieval dates, revisions, units, currencies, and base years are recorded.
- [ ] Top-down and bottom-up sizing use compatible definitions and disjoint coverage keys.
- [ ] TAM/SAM/SOM are presented as conditional scenarios with sensitivity.
- [ ] Forecast ranges are labeled as scenarios, not confidence intervals.
- [ ] Survey sample, frame, mode, field dates, weighting, response, and limitations are disclosed.
- [ ] Competitor claims use public, lawful evidence and identify unknowns.
- [ ] No PII, trade secrets, deceptive collection, or unsupported paid-market figures appear.
- [ ] Findings, assumptions, calculations, forecasts, opinions, and recommendations remain distinct.
- [ ] The report states that it is not investment, legal, or financial advice.
"""
    (destination / "review_checklist.md").write_text(checklist, encoding="utf-8")

    created = sorted(
        str(path.relative_to(destination))
        for path in destination.rglob("*")
        if path.is_file()
    )
    return {
        "created": True,
        "output_directory": str(destination),
        "files": created,
        "next_step": (
            "Populate the empty ledgers and scenario files, then run the bundled "
            "validators before drafting conclusions."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a new local Markdown market-report scaffold and strict "
            "evidence/analysis input files. Existing directories are never overwritten."
        )
    )
    parser.add_argument("manifest", help="Local .json report manifest")
    parser.add_argument("output_dir", help="New local output directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = validate_manifest(require_object(read_json(args.manifest), "root"))
        write_json_report(generate(manifest, args.output_dir), None)
        return 0
    except ValidationError as exc:
        return error_exit(exc)


if __name__ == "__main__":
    raise SystemExit(main())
