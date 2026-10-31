#!/usr/bin/env python3
"""Validate a structured CARE coverage manifest without reading patient narrative."""

from __future__ import annotations

import argparse
import sys
from typing import Any

sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    ValidationError,
    error_report,
    load_json_object,
    require_bool,
    require_data_class,
    require_exact_keys,
    require_identifier,
    require_string,
    write_json_report,
)

TOOL = "validate_case_report"
CARE_ITEMS = (
    "title",
    "key_words",
    "abstract",
    "introduction",
    "patient_information",
    "clinical_findings",
    "timeline",
    "diagnostic_assessment",
    "therapeutic_intervention",
    "follow_up_and_outcomes",
    "discussion",
    "patient_perspective",
    "informed_consent",
)
ALLOWED_ITEM_STATUSES = {
    "verified_present",
    "not_applicable_with_rationale",
    "missing",
    "conflict",
}
NA_ALLOWED = {"patient_perspective"}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "artifact_kind",
    "draft_status",
    "safety_notice",
    "data_classification",
    "authorized_purpose",
    "authorization_verified",
    "provenance_manifest",
    "guidance",
    "care_items",
    "privacy",
    "review",
}
EXPECTED_DRAFT_STATUS = (
    "BLOCKED_INCOMPLETE_DRAFT_NOT_FOR_CLINICAL_USE_OR_SUBMISSION"
)


def _fact_ids(item: dict[str, Any], field: str) -> list[str]:
    value = item.get("source_fact_ids")
    if not isinstance(value, list):
        raise ValidationError(f"{field}.source_fact_ids must be an array")
    return [require_identifier(fact_id, f"{field}.source_fact_ids") for fact_id in value]


def validate_case_manifest(data: dict[str, Any]) -> dict[str, Any]:
    """Return fail-closed structural findings for a CARE manifest."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        require_exact_keys(data, TOP_LEVEL_FIELDS, "manifest")
        if data.get("schema_version") != "2.0":
            raise ValidationError("schema_version must be 2.0")
        if data.get("artifact_kind") != "case_report_draft":
            raise ValidationError("artifact_kind must be case_report_draft")
        if data.get("draft_status") != EXPECTED_DRAFT_STATUS:
            raise ValidationError(
                "draft_status must preserve the blocked non-clinical-use warning"
            )
        require_string(data.get("safety_notice"), "safety_notice", max_length=1000)
        require_data_class(data.get("data_classification"))
        if not require_bool(data.get("authorization_verified"), "authorization_verified"):
            errors.append("authorization_verified must be true")
        require_string(data.get("authorized_purpose"), "authorized_purpose")
        require_string(data.get("provenance_manifest"), "provenance_manifest")
    except ValidationError as exc:
        errors.append(str(exc))

    guidance = data.get("guidance")
    try:
        guidance = require_exact_keys(
            guidance,
            {
                "name",
                "checklist_version",
                "explanation_version",
                "target_journal_instructions_checked",
            },
            "guidance",
        )
        if guidance.get("name") != "CARE":
            errors.append("guidance.name must be CARE")
        if guidance.get("checklist_version") != "2013":
            errors.append("guidance.checklist_version must be 2013")
        if guidance.get("explanation_version") != "2017":
            errors.append("guidance.explanation_version must be 2017")
        if guidance.get("target_journal_instructions_checked") is not True:
            warnings.append("target journal instructions remain to be checked")
    except ValidationError as exc:
        errors.append(str(exc))

    items = data.get("care_items")
    if not isinstance(items, dict):
        errors.append("care_items must be an object")
        items = {}
    missing_keys = sorted(set(CARE_ITEMS) - set(items))
    extra_keys = sorted(set(items) - set(CARE_ITEMS))
    if missing_keys:
        errors.append(f"missing CARE item keys: {missing_keys}")
    if extra_keys:
        errors.append(f"unexpected CARE item keys: {extra_keys}")

    coverage: dict[str, str] = {}
    for key in CARE_ITEMS:
        item = items.get(key)
        if not isinstance(item, dict):
            errors.append(f"care_items.{key} must be an object")
            continue
        try:
            item = require_exact_keys(
                item,
                {"status", "source_fact_ids", "rationale"},
                f"care_items.{key}",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        status = item.get("status")
        coverage[key] = str(status)
        if not isinstance(status, str) or status not in ALLOWED_ITEM_STATUSES:
            errors.append(f"care_items.{key}.status is invalid")
            continue
        try:
            facts = _fact_ids(item, f"care_items.{key}")
        except ValidationError as exc:
            errors.append(str(exc))
            facts = []
        if status == "verified_present" and not facts:
            errors.append(f"care_items.{key} requires at least one verified source fact")
        elif status == "not_applicable_with_rationale":
            if key not in NA_ALLOWED:
                errors.append(f"care_items.{key} cannot be marked not applicable")
            try:
                require_string(
                    item.get("rationale"),
                    f"care_items.{key}.rationale",
                    max_length=500,
                )
            except ValidationError as exc:
                errors.append(str(exc))
        elif status in {"missing", "conflict"}:
            errors.append(f"care_items.{key} is {status}")

    privacy = data.get("privacy")
    try:
        privacy = require_exact_keys(
            privacy,
            {
                "deidentification_process_record",
                "publication_consent_record",
                "image_or_media_included",
                "reidentification_risk_reviewed",
            },
            "privacy",
        )
        for field in ("deidentification_process_record", "publication_consent_record"):
            try:
                require_string(privacy.get(field), f"privacy.{field}")
            except ValidationError as exc:
                errors.append(str(exc))
        try:
            if not require_bool(
                privacy.get("reidentification_risk_reviewed"),
                "privacy.reidentification_risk_reviewed",
            ):
                errors.append("privacy.reidentification_risk_reviewed must be true")
        except ValidationError as exc:
            errors.append(str(exc))
        try:
            require_bool(privacy.get("image_or_media_included"), "privacy.image_or_media_included")
        except ValidationError as exc:
            errors.append(str(exc))
    except ValidationError as exc:
        errors.append(str(exc))

    review = data.get("review")
    try:
        review = require_exact_keys(
            review,
            {
                "qualified_clinical_review",
                "privacy_legal_review",
                "accountable_author_review",
                "submission_authorized",
            },
            "review",
        )
        for field in (
            "qualified_clinical_review",
            "privacy_legal_review",
            "accountable_author_review",
        ):
            if review.get(field) != "completed":
                warnings.append(f"review.{field} remains required")
        if review.get("submission_authorized") is not False:
            errors.append("submission_authorized must remain false in this draft manifest")
    except ValidationError as exc:
        errors.append(str(exc))

    status = "BLOCKED" if errors else "STRUCTURE_COMPLETE_REVIEW_REQUIRED"
    return {
        "tool": TOOL,
        "status": status,
        "guidance": "CARE 2013 with 2017 explanation",
        "coverage": coverage,
        "errors": errors,
        "warnings": warnings,
        "limitations": [
            "Structure and fact-ID shape only; no cross-artifact linkage or clinical-content validation.",
            "Does not establish consent, de-identification, CARE adherence, or journal readiness.",
        ],
        "review_required": True,
        "authorizes_clinical_use_or_submission": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check a bounded JSON CARE coverage manifest. "
            "Does not read patient narrative or claim compliance."
        )
    )
    parser.add_argument("input_file", help="Local case-report manifest (.json)")
    parser.add_argument("-o", "--output", help="Optional local JSON report path")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _, data = load_json_object(args.input_file)
        report = validate_case_manifest(data)
    except (OSError, ValidationError) as exc:
        report = error_report(TOOL, exc)
    try:
        write_json_report(report, args.output, overwrite=args.overwrite)
    except (OSError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0 if report["status"] == "STRUCTURE_COMPLETE_REVIEW_REQUIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
