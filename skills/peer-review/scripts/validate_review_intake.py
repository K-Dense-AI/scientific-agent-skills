#!/usr/bin/env python3
"""Validate peer-review scope, authorization, conflicts, and handling controls."""

from __future__ import annotations

import argparse
from typing import Any

from _common import (
    ValidationError,
    error_exit,
    issue,
    read_json,
    require_bool,
    require_enum,
    require_exact_keys,
    require_identifier,
    require_identifier_list,
    require_object,
    require_text_list,
    write_json_report,
)

MATERIAL_STATUSES = {
    "unpublished_confidential",
    "public_preprint",
    "published",
    "synthetic",
}
AUTHORIZATION_BASES = {
    "journal_invitation",
    "editor_assignment",
    "author_request",
    "public_material",
    "synthetic_training",
}
CAPACITIES = {
    "assigned_reviewer",
    "disclosed_co_reviewer",
    "author_requested_reader",
    "editorial_support",
    "training",
}
CONFLICT_STATUSES = {
    "not_assessed",
    "none_identified",
    "disclosed_to_editor",
    "editor_cleared",
    "unresolved",
}
PEER_REVIEW_MODELS = {
    "single_anonymized",
    "double_anonymized",
    "open",
    "transparent",
    "post_publication",
    "unknown",
}
AI_POLICIES = {
    "prohibited",
    "permission_required",
    "permitted_with_disclosure",
    "not_stated",
}
AI_PLANS = {"none", "local_deterministic_tools", "approved_ai_assistance"}
RETENTION_RULES = {
    "delete_after_review",
    "delete_after_editor_confirmation",
    "retain_per_venue_policy",
    "public_material",
}


def validate_intake(payload: Any) -> dict[str, Any]:
    """Return a content-free intake report; never echo manuscript text."""
    root = require_object(payload, "intake")
    require_exact_keys(
        root,
        required={
            "schema_version",
            "review_id",
            "material",
            "authorization",
            "reviewer",
            "venue_policy",
            "ai_use",
            "handling",
            "scope",
        },
        context="intake",
    )
    schema_version = require_enum(
        root["schema_version"], {"2.0"}, "intake.schema_version"
    )
    review_id = require_identifier(root["review_id"], "intake.review_id")

    material = require_object(root["material"], "intake.material")
    require_exact_keys(
        material,
        required={"status", "contains_personal_or_sensitive_data"},
        context="intake.material",
    )
    material_status = require_enum(
        material["status"], MATERIAL_STATUSES, "intake.material.status"
    )
    sensitive = require_bool(
        material["contains_personal_or_sensitive_data"],
        "intake.material.contains_personal_or_sensitive_data",
    )

    authorization = require_object(root["authorization"], "intake.authorization")
    require_exact_keys(
        authorization,
        required={
            "basis",
            "documented",
            "local_processing_authorized",
            "external_processing_authorized",
        },
        context="intake.authorization",
    )
    authorization_basis = require_enum(
        authorization["basis"],
        AUTHORIZATION_BASES,
        "intake.authorization.basis",
    )
    authorization_documented = require_bool(
        authorization["documented"], "intake.authorization.documented"
    )
    local_authorized = require_bool(
        authorization["local_processing_authorized"],
        "intake.authorization.local_processing_authorized",
    )
    external_authorized = require_bool(
        authorization["external_processing_authorized"],
        "intake.authorization.external_processing_authorized",
    )

    reviewer = require_object(root["reviewer"], "intake.reviewer")
    require_exact_keys(
        reviewer,
        required={
            "capacity",
            "human_accountable",
            "competence_areas",
            "competence_limits",
            "conflict_status",
            "conflicts",
        },
        context="intake.reviewer",
    )
    capacity = require_enum(
        reviewer["capacity"], CAPACITIES, "intake.reviewer.capacity"
    )
    human_accountable = require_bool(
        reviewer["human_accountable"], "intake.reviewer.human_accountable"
    )
    competence_areas = require_identifier_list(
        reviewer["competence_areas"],
        "intake.reviewer.competence_areas",
        minimum=1,
    )
    competence_limits = require_text_list(
        reviewer["competence_limits"], "intake.reviewer.competence_limits"
    )
    conflict_status = require_enum(
        reviewer["conflict_status"],
        CONFLICT_STATUSES,
        "intake.reviewer.conflict_status",
    )
    conflicts = require_text_list(
        reviewer["conflicts"], "intake.reviewer.conflicts", maximum=50
    )

    venue = require_object(root["venue_policy"], "intake.venue_policy")
    require_exact_keys(
        venue,
        required={
            "checked",
            "peer_review_model",
            "confidential_editor_notes_supported",
        },
        context="intake.venue_policy",
    )
    venue_checked = require_bool(venue["checked"], "intake.venue_policy.checked")
    peer_review_model = require_enum(
        venue["peer_review_model"],
        PEER_REVIEW_MODELS,
        "intake.venue_policy.peer_review_model",
    )
    confidential_notes_supported = require_bool(
        venue["confidential_editor_notes_supported"],
        "intake.venue_policy.confidential_editor_notes_supported",
    )

    ai_use = require_object(root["ai_use"], "intake.ai_use")
    require_exact_keys(
        ai_use,
        required={
            "policy",
            "planned",
            "permission_confirmed",
            "disclosure_planned",
        },
        context="intake.ai_use",
    )
    ai_policy = require_enum(
        ai_use["policy"], AI_POLICIES, "intake.ai_use.policy"
    )
    ai_plan = require_enum(ai_use["planned"], AI_PLANS, "intake.ai_use.planned")
    ai_permission = require_bool(
        ai_use["permission_confirmed"], "intake.ai_use.permission_confirmed"
    )
    ai_disclosure = require_bool(
        ai_use["disclosure_planned"], "intake.ai_use.disclosure_planned"
    )

    handling = require_object(root["handling"], "intake.handling")
    require_exact_keys(
        handling,
        required={
            "local_only",
            "external_service_use",
            "data_reuse_permitted",
            "retention_rule",
            "deletion_or_retention_record_planned",
        },
        context="intake.handling",
    )
    local_only = require_bool(handling["local_only"], "intake.handling.local_only")
    external_service_use = require_bool(
        handling["external_service_use"],
        "intake.handling.external_service_use",
    )
    data_reuse = require_bool(
        handling["data_reuse_permitted"],
        "intake.handling.data_reuse_permitted",
    )
    retention_rule = require_enum(
        handling["retention_rule"],
        RETENTION_RULES,
        "intake.handling.retention_rule",
    )
    handling_record = require_bool(
        handling["deletion_or_retention_record_planned"],
        "intake.handling.deletion_or_retention_record_planned",
    )

    scope = require_object(root["scope"], "intake.scope")
    require_exact_keys(
        scope,
        required={
            "manuscript_type",
            "requested_focus",
            "out_of_scope",
            "specialist_review_needed",
        },
        context="intake.scope",
    )
    manuscript_type = require_identifier(
        scope["manuscript_type"], "intake.scope.manuscript_type"
    )
    requested_focus = require_identifier_list(
        scope["requested_focus"], "intake.scope.requested_focus", minimum=1
    )
    out_of_scope = require_identifier_list(
        scope["out_of_scope"], "intake.scope.out_of_scope"
    )
    specialist_review_needed = require_identifier_list(
        scope["specialist_review_needed"],
        "intake.scope.specialist_review_needed",
    )

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not authorization_documented:
        errors.append(issue("AUTHORIZATION_NOT_DOCUMENTED", "authorization.documented"))
    if not local_authorized:
        errors.append(
            issue(
                "LOCAL_PROCESSING_NOT_AUTHORIZED",
                "authorization.local_processing_authorized",
            )
        )
    if material_status == "unpublished_confidential" and authorization_basis in {
        "public_material",
        "synthetic_training",
    }:
        errors.append(
            issue("AUTHORIZATION_BASIS_MISMATCH", "authorization.basis")
        )
    if material_status in {"public_preprint", "published"} and authorization_basis not in {
        "public_material",
        "author_request",
    }:
        warnings.append(
            issue("PUBLIC_MATERIAL_BASIS_REVIEW", "authorization.basis")
        )
    if material_status == "synthetic" and authorization_basis != "synthetic_training":
        warnings.append(
            issue("SYNTHETIC_MATERIAL_BASIS_REVIEW", "authorization.basis")
        )

    if not human_accountable:
        errors.append(
            issue("HUMAN_ACCOUNTABILITY_REQUIRED", "reviewer.human_accountable")
        )
    if conflict_status == "not_assessed":
        errors.append(issue("CONFLICTS_NOT_ASSESSED", "reviewer.conflict_status"))
    elif conflict_status == "unresolved":
        errors.append(issue("CONFLICT_UNRESOLVED", "reviewer.conflict_status"))
    elif conflict_status == "none_identified" and conflicts:
        errors.append(issue("CONFLICT_STATUS_MISMATCH", "reviewer.conflicts"))
    elif conflict_status == "disclosed_to_editor":
        errors.append(
            issue("EDITOR_CONFLICT_CLEARANCE_REQUIRED", "reviewer.conflict_status")
        )

    if not venue_checked:
        errors.append(issue("VENUE_POLICY_NOT_CHECKED", "venue_policy.checked"))
    if peer_review_model == "unknown":
        errors.append(
            issue("PEER_REVIEW_MODEL_UNKNOWN", "venue_policy.peer_review_model")
        )
    if not confidential_notes_supported:
        warnings.append(
            issue(
                "CONFIDENTIAL_NOTES_CHANNEL_UNAVAILABLE",
                "venue_policy.confidential_editor_notes_supported",
            )
        )

    if ai_plan == "approved_ai_assistance":
        if ai_policy in {"prohibited", "not_stated"}:
            errors.append(issue("AI_POLICY_DOES_NOT_PERMIT_USE", "ai_use.policy"))
        if not ai_permission:
            errors.append(
                issue("AI_PERMISSION_NOT_CONFIRMED", "ai_use.permission_confirmed")
            )
        if not ai_disclosure:
            errors.append(
                issue("AI_DISCLOSURE_NOT_PLANNED", "ai_use.disclosure_planned")
            )
    elif ai_plan in {"none", "local_deterministic_tools"}:
        if ai_permission or ai_disclosure:
            warnings.append(issue("AI_FIELDS_REQUIRE_REVIEW", "ai_use"))

    if not local_only:
        errors.append(issue("LOCAL_ONLY_REQUIRED", "handling.local_only"))
    if external_service_use:
        errors.append(
            issue("EXTERNAL_SERVICE_NOT_SUPPORTED", "handling.external_service_use")
        )
    if external_authorized and not external_service_use:
        warnings.append(
            issue(
                "EXTERNAL_AUTHORIZATION_NOT_USED",
                "authorization.external_processing_authorized",
            )
        )
    if data_reuse:
        errors.append(issue("DATA_REUSE_PROHIBITED", "handling.data_reuse_permitted"))
    if not handling_record:
        errors.append(
            issue(
                "DELETION_OR_RETENTION_RECORD_REQUIRED",
                "handling.deletion_or_retention_record_planned",
            )
        )
    if retention_rule == "public_material" and material_status not in {
        "public_preprint",
        "published",
        "synthetic",
    }:
        errors.append(issue("RETENTION_RULE_MISMATCH", "handling.retention_rule"))
    if sensitive:
        warnings.append(
            issue(
                "MINIMUM_NECESSARY_HANDLING_REQUIRED",
                "material.contains_personal_or_sensitive_data",
            )
        )
    if competence_limits:
        warnings.append(
            issue("COMPETENCE_LIMITS_MUST_BE_DISCLOSED", "reviewer.competence_limits")
        )
    if specialist_review_needed:
        warnings.append(
            issue(
                "SPECIALIST_REVIEW_NEEDED",
                "scope.specialist_review_needed",
            )
        )

    valid = not errors
    return {
        "schema_version": schema_version,
        "review_id": review_id,
        "valid": valid,
        "status": "READY_FOR_LOCAL_REVIEW" if valid else "BLOCKED",
        "errors": errors,
        "warnings": warnings,
        "normalized_scope": {
            "capacity": capacity,
            "competence_areas": competence_areas,
            "manuscript_type": manuscript_type,
            "requested_focus": requested_focus,
            "out_of_scope": out_of_scope,
            "peer_review_model": peer_review_model,
            "ai_plan": ai_plan,
        },
        "handling_assertions": {
            "bundled_tools_are_local_only": True,
            "external_service_use_authorized_by_this_report": False,
            "data_reuse_authorized": False,
            "author_and_editor_channels_must_remain_separate": True,
        },
        "notice": (
            "This validates declared process controls only. It does not establish "
            "reviewer competence, resolve conflicts, authorize external processing, "
            "or assess manuscript quality."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a local peer-review intake JSON without reading or echoing "
            "manuscript content."
        )
    )
    parser.add_argument("intake", help="Local review intake JSON")
    parser.add_argument("-o", "--output", help="Optional local JSON report")
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing output file"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = validate_intake(read_json(args.intake))
        write_json_report(report, args.output, force=args.force)
        return 0 if report["valid"] else 1
    except ValidationError as exc:
        return error_exit(exc)


if __name__ == "__main__":
    raise SystemExit(main())
