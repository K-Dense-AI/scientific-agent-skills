#!/usr/bin/env python3
"""Validate intended use and governance fields for research-only CDS artifacts."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import (
    InputError,
    IssueLog,
    load_json_object,
    print_report,
    require_list,
    require_nonempty_text,
    source_ids,
    write_json,
)

ALLOWED_TYPES = {
    "aggregate_cohort_evaluation",
    "evidence_profile",
    "model_biomarker_evaluation",
    "research_analysis_plan",
    "governance_traceability",
    "privacy_process_checklist",
}
ALLOWED_STATUSES = {"draft", "evaluation_only", "retired"}
ALLOWED_DATA_LEVELS = {"aggregate", "synthetic", "aggregate_and_synthetic"}
REQUIRED_PROHIBITIONS = {
    "patient-specific",
    "diagnosis",
    "treatment recommendation",
    "dosing",
    "triage",
    "autonomous decision",
    "alarm",
    "bedside",
    "live clinical",
    "regulatory compliance",
    "hipaa compliance",
}
UNSAFE_OUTPUT_KEYS = {
    "alarm",
    "care_plan",
    "clinical_action",
    "diagnosis",
    "dose",
    "dosing",
    "patient_class",
    "patient_prediction",
    "recommendation",
    "treatment_recommendation",
    "triage",
    "urgency",
}
PLACEHOLDER_MARKERS = ("REPLACE_", "REQUIRES_", "YYYY-MM-DD")


def _find_unsafe_keys(value: Any, location: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if normalized in UNSAFE_OUTPUT_KEYS:
                findings.append(f"{location}.{key}")
            findings.extend(_find_unsafe_keys(nested, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            findings.extend(_find_unsafe_keys(nested, f"{location}[{index}]"))
    return findings


def _find_placeholders(value: Any, location: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            findings.extend(_find_placeholders(nested, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            findings.extend(_find_placeholders(nested, f"{location}[{index}]"))
    elif isinstance(value, str) and any(marker in value for marker in PLACEHOLDER_MARKERS):
        findings.append(location)
    return findings


def validate_artifact(document: dict[str, Any]) -> IssueLog:
    log = IssueLog()
    try:
        require_nonempty_text(document.get("schema_version"), "schema_version", max_length=20)
        known_sources = source_ids(document)
        if not known_sources:
            log.errors.append("At least one source is required")

        artifact = document.get("artifact")
        if not isinstance(artifact, dict):
            raise InputError("artifact must be an object")
        for field in ("id", "title", "version", "owner", "date", "change_summary"):
            require_nonempty_text(artifact.get(field), f"artifact.{field}")
        artifact_type = require_nonempty_text(
            artifact.get("type"), "artifact.type", max_length=100
        )
        if artifact_type not in ALLOWED_TYPES:
            log.errors.append(f"artifact.type is not allowed: {artifact_type}")
        status = require_nonempty_text(
            artifact.get("status"), "artifact.status", max_length=30
        )
        if status not in ALLOWED_STATUSES:
            log.errors.append(
                "artifact.status must be draft, evaluation_only, or retired"
            )

        intended = document.get("intended_use")
        if not isinstance(intended, dict):
            raise InputError("intended_use must be an object")
        require_nonempty_text(intended.get("purpose"), "intended_use.purpose")
        users = require_list(
            intended.get("intended_users"), "intended_use.intended_users", maximum=20
        )
        if not users:
            log.errors.append("At least one intended user role is required")
        for index, user in enumerate(users):
            require_nonempty_text(user, f"intended_use.intended_users[{index}]")
        if intended.get("population_scope") != "aggregate_or_synthetic_only":
            log.errors.append(
                "intended_use.population_scope must be aggregate_or_synthetic_only"
            )
        if intended.get("decision_role") != "research_evaluation_governance_only":
            log.errors.append(
                "intended_use.decision_role must be "
                "research_evaluation_governance_only"
            )
        boundary = require_nonempty_text(
            intended.get("boundary_statement"), "intended_use.boundary_statement"
        ).lower()
        if "not for patient care or live clinical use" not in boundary:
            log.errors.append(
                "Boundary statement must say: Not for patient care or live clinical use"
            )

        prohibited = require_list(
            document.get("prohibited_uses"), "prohibited_uses", maximum=40
        )
        prohibited_text = " ".join(
            require_nonempty_text(item, f"prohibited_uses[{index}]")
            for index, item in enumerate(prohibited)
        ).lower()
        missing = sorted(
            phrase for phrase in REQUIRED_PROHIBITIONS if phrase not in prohibited_text
        )
        if missing:
            log.errors.append(
                "prohibited_uses is missing required concepts: " + ", ".join(missing)
            )

        data = document.get("data_governance")
        if not isinstance(data, dict):
            raise InputError("data_governance must be an object")
        if not isinstance(data.get("data_level"), str) or data.get("data_level") not in ALLOWED_DATA_LEVELS:
            log.errors.append("data_governance.data_level must be aggregate or synthetic")
        if data.get("phi_supplied") is not False:
            log.errors.append("data_governance.phi_supplied must be false")
        if data.get("raw_rows_supplied") is not False:
            log.errors.append("data_governance.raw_rows_supplied must be false")
        for field in ("provenance", "data_cut_date", "disclosure_policy"):
            require_nonempty_text(data.get(field), f"data_governance.{field}")

        limitations = require_list(
            document.get("limitations"), "limitations", maximum=40
        )
        if len(limitations) < 3:
            log.errors.append("At least three limitations are required")
        for index, limitation in enumerate(limitations):
            require_nonempty_text(limitation, f"limitations[{index}]")

        review = document.get("human_review")
        if not isinstance(review, dict):
            raise InputError("human_review must be an object")
        if review.get("required") is not True:
            log.errors.append("human_review.required must be true")
        roles = require_list(review.get("roles"), "human_review.roles", maximum=20)
        if not roles:
            log.errors.append("At least one human review role is required")
        for index, role in enumerate(roles):
            require_nonempty_text(role, f"human_review.roles[{index}]")
        require_nonempty_text(
            review.get("approval_boundary"), "human_review.approval_boundary"
        )
        if review.get("completed") is not True:
            log.warnings.append("Human review is not recorded as complete")

        validation = document.get("validation")
        if not isinstance(validation, dict):
            raise InputError("validation must be an object")
        for field in (
            "external_validation",
            "calibration",
            "subgroup_fairness",
            "uncertainty",
            "human_factors",
        ):
            require_nonempty_text(validation.get(field), f"validation.{field}")

        lifecycle = document.get("lifecycle")
        if not isinstance(lifecycle, dict):
            raise InputError("lifecycle must be an object")
        for field in (
            "monitoring_plan",
            "change_control",
            "audit_plan",
            "retirement_criteria",
        ):
            require_nonempty_text(lifecycle.get(field), f"lifecycle.{field}")

        if document.get("compliance_claims") is not False:
            log.errors.append("compliance_claims must be false")

        unsafe_locations = _find_unsafe_keys(document)
        if unsafe_locations:
            log.errors.append(
                "Unsafe clinical-output keys are prohibited: "
                + ", ".join(unsafe_locations[:10])
            )
        placeholders = _find_placeholders(document)
        if placeholders:
            log.errors.append(
                "Unresolved template placeholders remain: "
                + ", ".join(placeholders[:10])
            )
    except InputError as exc:
        log.errors.append(str(exc))

    if log.ok:
        log.info.append("Required intended-use and governance fields are complete")
    return log


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a bounded local JSON metadata artifact. Structural checks only; "
            "never a clinical or compliance determination."
        )
    )
    parser.add_argument("input", help="Local JSON artifact")
    parser.add_argument("-o", "--output", help="Optional local JSON report")
    parser.add_argument(
        "--strict", action="store_true", help="Return failure when warnings are present"
    )
    args = parser.parse_args()

    try:
        document = load_json_object(args.input)
        result = validate_artifact(document).as_dict()
        if args.output:
            write_json(args.output, result)
        print_report(result)
    except InputError as exc:
        result = IssueLog(errors=[str(exc)]).as_dict()
        print_report(result)
        return 2
    if result["status"] != "pass" or (args.strict and result["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
