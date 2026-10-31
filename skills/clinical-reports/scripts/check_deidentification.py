#!/usr/bin/env python3
"""Validate de-identification process documentation without scanning patient text."""

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
    require_string,
    write_json_report,
)

TOOL = "check_deidentification"
SAFE_HARBOR_KEYS = (
    "names",
    "geographic_subdivisions",
    "dates_and_ages",
    "telephone_numbers",
    "fax_numbers",
    "email_addresses",
    "social_security_numbers",
    "medical_record_numbers",
    "health_plan_numbers",
    "account_numbers",
    "certificate_and_license_numbers",
    "vehicle_identifiers",
    "device_identifiers",
    "urls",
    "ip_addresses",
    "biometric_identifiers",
    "full_face_images",
    "other_unique_characteristics_or_codes",
)
RESIDUAL_KEYS = (
    "free_text",
    "small_cells_and_rare_cases",
    "images_and_metadata",
    "linked_data_and_quasi_identifiers",
)
METHODS = {
    "safe_harbor",
    "expert_determination",
    "not_applicable_synthetic_or_aggregate",
}
CLEAR_STATUSES = {"cleared_by_authorized_reviewer", "not_present_by_design"}
RESIDUAL_CLEAR_STATUSES = {
    "reviewed_no_unresolved_issue",
    "not_applicable_with_rationale",
}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "artifact_kind",
    "process_status",
    "safety_notice",
    "data_scope",
    "authorized_purpose",
    "authorization_verified",
    "local_only_handling_confirmed",
    "minimum_necessary_reviewed",
    "method",
    "safe_harbor_identifiers",
    "actual_knowledge_review",
    "expert_determination",
    "synthetic_or_aggregate_rationale",
    "residual_risk_review",
    "review",
}


def _required_true(
    data: dict[str, Any],
    field: str,
    errors: list[str],
) -> None:
    try:
        if not require_bool(data.get(field), field):
            errors.append(f"{field} must be true")
    except ValidationError as exc:
        errors.append(str(exc))


def validate_process(data: dict[str, Any]) -> dict[str, Any]:
    """Validate recorded process gates without asserting de-identification."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        require_exact_keys(data, TOP_LEVEL_FIELDS, "checklist")
        if data.get("schema_version") != "2.0":
            raise ValidationError("schema_version must be 2.0")
        if data.get("process_status") != "BLOCKED_NOT_ASSESSED":
            raise ValidationError("process_status must remain BLOCKED_NOT_ASSESSED")
        require_string(data.get("safety_notice"), "safety_notice", max_length=1000)
        require_exact_keys(
            data.get("safe_harbor_identifiers"),
            SAFE_HARBOR_KEYS,
            "safe_harbor_identifiers",
        )
        require_exact_keys(
            data.get("actual_knowledge_review"),
            {"completed_by_authorized_privacy_reviewer", "record_reference"},
            "actual_knowledge_review",
        )
        require_exact_keys(
            data.get("expert_determination"),
            {
                "completed_by_qualified_expert",
                "expert_documentation_reference",
                "anticipated_recipient_and_conditions_documented",
            },
            "expert_determination",
        )
        require_exact_keys(
            data.get("synthetic_or_aggregate_rationale"),
            {"origin_verified", "record_reference"},
            "synthetic_or_aggregate_rationale",
        )
        require_exact_keys(
            data.get("residual_risk_review"),
            RESIDUAL_KEYS,
            "residual_risk_review",
        )
        require_exact_keys(
            data.get("review"),
            {
                "privacy_legal_review",
                "institutional_release_review",
                "release_authorized",
            },
            "review",
        )
    except ValidationError as exc:
        errors.append(str(exc))
    if data.get("artifact_kind") != "deidentification_process_checklist":
        errors.append("artifact_kind must be deidentification_process_checklist")
    try:
        data_scope = require_data_class(data.get("data_scope"))
        require_string(data.get("authorized_purpose"), "authorized_purpose")
    except ValidationError as exc:
        errors.append(str(exc))
        data_scope = ""

    for field in (
        "authorization_verified",
        "local_only_handling_confirmed",
        "minimum_necessary_reviewed",
    ):
        _required_true(data, field, errors)

    method = data.get("method")
    if not isinstance(method, str) or method not in METHODS:
        errors.append(f"method must be one of {sorted(METHODS)}")
    elif method == "safe_harbor":
        statuses = data.get("safe_harbor_identifiers")
        if not isinstance(statuses, dict):
            errors.append("safe_harbor_identifiers must be an object")
        else:
            missing = sorted(set(SAFE_HARBOR_KEYS) - set(statuses))
            extra = sorted(set(statuses) - set(SAFE_HARBOR_KEYS))
            if missing:
                errors.append(f"missing Safe Harbor categories: {missing}")
            if extra:
                errors.append(f"unexpected Safe Harbor categories: {extra}")
            for key in SAFE_HARBOR_KEYS:
                if (
                    not isinstance(statuses.get(key), str)
                    or statuses.get(key) not in CLEAR_STATUSES
                ):
                    errors.append(f"safe_harbor_identifiers.{key} is not cleared")
        actual = data.get("actual_knowledge_review")
        if not isinstance(actual, dict):
            errors.append("actual_knowledge_review must be an object")
        else:
            try:
                if not require_bool(
                    actual.get("completed_by_authorized_privacy_reviewer"),
                    "actual_knowledge_review.completed_by_authorized_privacy_reviewer",
                ):
                    errors.append("authorized actual-knowledge review is required")
                require_string(
                    actual.get("record_reference"),
                    "actual_knowledge_review.record_reference",
                )
            except ValidationError as exc:
                errors.append(str(exc))
    elif method == "expert_determination":
        expert = data.get("expert_determination")
        if not isinstance(expert, dict):
            errors.append("expert_determination must be an object")
        else:
            try:
                if not require_bool(
                    expert.get("completed_by_qualified_expert"),
                    "expert_determination.completed_by_qualified_expert",
                ):
                    errors.append("qualified Expert Determination is required")
                require_string(
                    expert.get("expert_documentation_reference"),
                    "expert_determination.expert_documentation_reference",
                )
                if not require_bool(
                    expert.get("anticipated_recipient_and_conditions_documented"),
                    "expert_determination.anticipated_recipient_and_conditions_documented",
                ):
                    errors.append("anticipated recipient and conditions must be documented")
            except ValidationError as exc:
                errors.append(str(exc))
    elif method == "not_applicable_synthetic_or_aggregate":
        if data_scope not in {"synthetic", "aggregate"}:
            errors.append(
                "not_applicable_synthetic_or_aggregate requires synthetic or aggregate scope"
            )
        rationale = data.get("synthetic_or_aggregate_rationale")
        if not isinstance(rationale, dict):
            errors.append("synthetic_or_aggregate_rationale must be an object")
        else:
            try:
                if not require_bool(
                    rationale.get("origin_verified"),
                    "synthetic_or_aggregate_rationale.origin_verified",
                ):
                    errors.append("synthetic or aggregate origin must be verified")
                require_string(
                    rationale.get("record_reference"),
                    "synthetic_or_aggregate_rationale.record_reference",
                )
            except ValidationError as exc:
                errors.append(str(exc))

    residual = data.get("residual_risk_review")
    if not isinstance(residual, dict):
        errors.append("residual_risk_review must be an object")
    else:
        for key in RESIDUAL_KEYS:
            if (
                not isinstance(residual.get(key), str)
                or residual.get(key) not in RESIDUAL_CLEAR_STATUSES
            ):
                errors.append(f"residual_risk_review.{key} is unresolved")

    review = data.get("review")
    if not isinstance(review, dict):
        errors.append("review must be an object")
    else:
        for field in ("privacy_legal_review", "institutional_release_review"):
            if review.get(field) != "completed":
                warnings.append(f"review.{field} remains required")
        if review.get("release_authorized") is not False:
            errors.append("review.release_authorized must remain false")

    return {
        "tool": TOOL,
        "status": "BLOCKED" if errors else "PROCESS_DOCUMENTED_REVIEW_REQUIRED",
        "method": method,
        "errors": errors,
        "warnings": warnings,
        "limitations": [
            "No patient text or files were scanned.",
            "Does not establish de-identification, no-actual-knowledge, Expert Determination, or HIPAA compliance.",
        ],
        "review_required": True,
        "authorizes_release_or_submission": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check bounded JSON de-identification process documentation. "
            "Never labels data HIPAA-compliant or guaranteed de-identified."
        )
    )
    parser.add_argument("input_file", help="Local process checklist (.json)")
    parser.add_argument("-o", "--output", help="Optional local JSON report")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _, data = load_json_object(args.input_file)
        report = validate_process(data)
    except (OSError, ValidationError) as exc:
        report = error_report(TOOL, exc)
    try:
        write_json_report(report, args.output, overwrite=args.overwrite)
    except (OSError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0 if report["status"] == "PROCESS_DOCUMENTED_REVIEW_REQUIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
