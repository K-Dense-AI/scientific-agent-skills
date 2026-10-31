#!/usr/bin/env python3
"""Check low-stakes assessment governance and bias-process controls."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import _common

SECTION_FIELDS: dict[str, dict[str, tuple[str, ...]]] = {
    "committee": {
        "booleans": ("qualified_members_confirmed", "training_completed"),
        "references": ("accountable_owner_role", "training_record_ref"),
    },
    "conflicts": {
        "booleans": (
            "disclosure_process_confirmed",
            "recusal_process_confirmed",
        ),
        "references": ("record_ref",),
    },
    "appeals": {
        "booleans": ("process_confirmed",),
        "references": ("process_ref", "notice_ref"),
    },
    "accessibility": {
        "booleans": (
            "accommodations_process_confirmed",
            "accessible_materials_confirmed",
        ),
        "references": ("process_ref",),
    },
    "data_protection": {
        "booleans": (
            "purpose_limitation_confirmed",
            "data_minimisation_confirmed",
            "access_controls_confirmed",
            "retention_schedule_confirmed",
            "raw_private_documents_excluded_from_tool_outputs",
        ),
        "references": ("review_ref",),
    },
    "rubric_quality": {
        "booleans": (
            "construct_documented",
            "rubric_provenance_documented",
            "content_validity_documented",
            "rater_training_documented",
            "agreement_reviewed",
            "inter_rater_reliability_reviewed",
            "uncertainty_recorded",
            "missing_and_not_applicable_supported",
            "evidence_traceability_checked",
            "weight_sensitivity_reviewed",
        ),
        "references": ("quality_record_ref",),
    },
    "fairness": {
        "booleans": (
            "stakeholder_review_completed",
            "disciplinary_context_reviewed",
            "subgroup_bias_review_completed",
            "protected_attributes_excluded_from_scoring",
        ),
        "references": ("bias_review_ref",),
    },
    "decision_controls": {
        "booleans": (
            "no_automated_decision",
            "no_person_ranking",
            "no_decision_recommendation",
            "qualified_human_accountability",
        ),
        "references": (),
    },
    "monitoring": {
        "booleans": (
            "rater_drift_reviewed",
            "unintended_consequences_reviewed",
            "periodic_revision_scheduled",
        ),
        "references": ("review_record_ref", "revision_owner_role"),
    },
}


def validate_process(record: Any) -> list[_common.Issue]:
    issues: list[_common.Issue] = []
    top_fields = {
        "schema_version",
        "process_id",
        "purpose",
        "unit_of_assessment",
        "data_classification",
        "high_impact_use",
        *SECTION_FIELDS,
    }
    if not _common.exact_keys(record, top_fields, "$", issues):
        return issues
    if record.get("schema_version") != _common.SCHEMA_VERSION:
        issues.append(_common.Issue("SCHEMA_VERSION_UNSUPPORTED", "$.schema_version"))
    _common.validate_identifier(record.get("process_id"), "$.process_id", issues)
    if record.get("purpose") != _common.ALLOWED_PURPOSE:
        issues.append(_common.Issue("PURPOSE_NOT_ALLOWED", "$.purpose"))
    if record.get("unit_of_assessment") != _common.ALLOWED_UNIT:
        issues.append(
            _common.Issue(
                "UNIT_OF_ASSESSMENT_NOT_ALLOWED", "$.unit_of_assessment"
            )
        )
    if record.get("data_classification") not in _common.ALLOWED_CLASSIFICATIONS:
        issues.append(
            _common.Issue(
                "DATA_CLASSIFICATION_NOT_ALLOWED", "$.data_classification"
            )
        )
    _common.validate_bool(record.get("high_impact_use"), "$.high_impact_use", issues)
    for section_name, field_groups in SECTION_FIELDS.items():
        section = record.get(section_name)
        expected = set(field_groups["booleans"]) | set(field_groups["references"])
        if not _common.exact_keys(section, expected, f"$.{section_name}", issues):
            continue
        for field in field_groups["booleans"]:
            _common.validate_bool(
                section.get(field), f"$.{section_name}.{field}", issues
            )
        for field in field_groups["references"]:
            _common.validate_reference(
                section.get(field),
                f"$.{section_name}.{field}",
                issues,
                allow_empty=True,
            )
    return issues


def check_process(record: dict[str, Any]) -> dict[str, Any]:
    schema_issues = validate_process(record)
    if _common.error_issues(schema_issues):
        return {
            "schema_version": _common.SCHEMA_VERSION,
            "report_type": "bias_and_process_check",
            "status": "invalid",
            "process_id": record.get("process_id") if isinstance(record, dict) else None,
            "issues": [issue.as_dict() for issue in schema_issues],
        }
    blockers: list[str] = []
    missing_controls: list[str] = []
    if record["high_impact_use"]:
        blockers.append("PROHIBITED_HIGH_IMPACT_USE")
    if record["purpose"] != _common.ALLOWED_PURPOSE:
        blockers.append("PROHIBITED_PURPOSE")
    if record["unit_of_assessment"] != _common.ALLOWED_UNIT:
        blockers.append("PROHIBITED_UNIT_OF_ASSESSMENT")
    for field in SECTION_FIELDS["decision_controls"]["booleans"]:
        if record["decision_controls"][field] is not True:
            blockers.append(f"DECISION_CONTROL_NOT_CONFIRMED:{field}")
    for section_name, field_groups in SECTION_FIELDS.items():
        for field in field_groups["booleans"]:
            if record[section_name][field] is not True:
                missing_controls.append(f"{section_name}.{field}")
        for field in field_groups["references"]:
            if not record[section_name][field]:
                missing_controls.append(f"{section_name}.{field}")
    status = (
        "blocked"
        if blockers
        else "incomplete"
        if missing_controls
        else "complete_for_low_stakes_process"
    )
    confirmed_count = sum(
        record[section_name][field] is True
        for section_name, groups in SECTION_FIELDS.items()
        for field in groups["booleans"]
    )
    boolean_count = sum(
        len(groups["booleans"]) for groups in SECTION_FIELDS.values()
    )
    return {
        "schema_version": _common.SCHEMA_VERSION,
        "report_type": "bias_and_process_check",
        "notice": _common.NOTICE,
        "status": status,
        "process_id": record["process_id"],
        "purpose": record["purpose"],
        "unit_of_assessment": record["unit_of_assessment"],
        "confirmed_boolean_controls": confirmed_count,
        "total_boolean_controls": boolean_count,
        "blockers": blockers,
        "missing_controls": sorted(set(missing_controls)),
        "prohibited_uses": sorted(_common.PROHIBITED_USES),
        "protected_attribute_data_processed": False,
        "decision_recommendation_provided": False,
        "issues": [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check committee, conflict, appeal, accessibility, data-protection, "
            "rubric-quality, fairness, and monitoring attestations for a "
            "low-stakes scholarly-work review process."
        )
    )
    parser.add_argument(
        "--process", required=True, type=Path, help="Local process-checklist JSON"
    )
    parser.add_argument("--output", type=Path, help="Optional local JSON report")
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing output JSON file"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = check_process(_common.read_json(args.process))
        _common.write_json(report, args.output, force=args.force)
        return 0 if report["status"] == "complete_for_low_stakes_process" else 2
    except _common.ValidationError as error:
        _common.write_json(_common.failure_report(error), None)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
