#!/usr/bin/env python3
"""Check documentation gates without assessing clinical adequacy."""

from __future__ import annotations

import argparse
import sys

from _common import (
    Issue,
    ValidationError,
    error_report,
    load_package,
    print_report,
    report_payload,
    validate_package_structure,
)


def _required_text(value: object, path: str, issues: list[Issue]) -> None:
    if not isinstance(value, str) or not value.strip():
        issues.append(Issue("REQUIRED_VALUE_MISSING", path))


def _required_time(value: object, path: str, issues: list[Issue]) -> None:
    if value is None:
        issues.append(Issue("REQUIRED_TIME_MISSING", path))


def check_completeness(documents: dict[str, dict]) -> dict:
    issues = validate_package_structure(documents)
    if issues:
        return report_payload(
            "documentation_completeness",
            issues,
            counts={"structural_issues": len(issues)},
        )

    for document_type, document in documents.items():
        if "TEMPLATE" in document["document_id"]:
            issues.append(
                Issue(
                    "TEMPLATE_DOCUMENT_ID_UNRESOLVED",
                    f"{document_type}:$.document_id",
                )
            )
        _required_time(
            document["created_at"], f"{document_type}:$.created_at", issues
        )

    facts = documents["source_fact_manifest"]["facts"]
    if not facts:
        issues.append(Issue("SOURCE_FACTS_REQUIRED", "source_fact_manifest:$.facts"))
    for index, fact in enumerate(facts):
        base = f"source_fact_manifest:$.facts[{index}]"
        verification = fact["verification"]
        if verification["status"] != "verified":
            issues.append(
                Issue(
                    "SOURCE_FACT_VERIFICATION_PENDING",
                    f"{base}.verification.status",
                )
            )
        _required_text(
            verification["verified_by_role"],
            f"{base}.verification.verified_by_role",
            issues,
        )
        _required_time(
            verification["verified_at"],
            f"{base}.verification.verified_at",
            issues,
        )

    interventions = documents[
        "clinician_authored_intervention_record"
    ]["interventions"]
    if not interventions:
        issues.append(
            Issue(
                "CLINICIAN_AUTHORED_INTERVENTION_REQUIRED",
                "clinician_authored_intervention_record:$.interventions",
            )
        )
    for index, intervention in enumerate(interventions):
        base = (
            "clinician_authored_intervention_record:"
            f"$.interventions[{index}]"
        )
        if (
            intervention["clinical_decision_status"]
            != "supplied_and_verified_by_authorized_clinician"
        ):
            issues.append(
                Issue(
                    "INTERVENTION_AUTHORIZED_VERIFICATION_PENDING",
                    f"{base}.clinical_decision_status",
                )
            )
        verification = intervention["verification"]
        if verification["status"] != "verified":
            issues.append(
                Issue(
                    "INTERVENTION_VERIFICATION_PENDING",
                    f"{base}.verification.status",
                )
            )
        _required_text(
            verification["verified_by_role"],
            f"{base}.verification.verified_by_role",
            issues,
        )
        _required_time(
            verification["verified_at"],
            f"{base}.verification.verified_at",
            issues,
        )

    planning = documents["goals_monitoring_checkpoint_record"]
    for field, code in (
        ("goals", "GOAL_RECORD_REQUIRED"),
        ("monitoring_items", "MONITORING_RECORD_REQUIRED"),
        ("checkpoints", "CHECKPOINT_RECORD_REQUIRED"),
    ):
        if not planning[field]:
            issues.append(
                Issue(
                    code,
                    f"goals_monitoring_checkpoint_record:$.{field}",
                )
            )

    decisions = documents[
        "informed_preference_shared_decision_record"
    ]["entries"]
    if not decisions:
        issues.append(
            Issue(
                "SHARED_DECISION_RECORD_REQUIRED",
                "informed_preference_shared_decision_record:$.entries",
            )
        )
    for index, decision in enumerate(decisions):
        base = (
            "informed_preference_shared_decision_record:"
            f"$.entries[{index}]"
        )
        if decision["decision_status"] != "documented_by_authorized_clinician":
            issues.append(
                Issue(
                    "SHARED_DECISION_DOCUMENTATION_PENDING",
                    f"{base}.decision_status",
                )
            )
        if not decision["benefits_harms_uncertainty_documented"]:
            issues.append(
                Issue(
                    "SHARED_DECISION_ELEMENTS_NOT_DOCUMENTED",
                    f"{base}.benefits_harms_uncertainty_documented",
                )
            )
        _required_text(
            decision["preference_as_documented"],
            f"{base}.preference_as_documented",
            issues,
        )
        _required_text(
            decision["outcome_as_documented"],
            f"{base}.outcome_as_documented",
            issues,
        )
        _required_text(
            decision["documented_by_role"],
            f"{base}.documented_by_role",
            issues,
        )
        _required_time(
            decision["documented_at"],
            f"{base}.documented_at",
            issues,
        )
        if decision["acknowledgment_status"] == "pending":
            issues.append(
                Issue(
                    "SHARED_DECISION_ACKNOWLEDGMENT_PENDING",
                    f"{base}.acknowledgment_status",
                )
            )

    transition_document = documents["transition_reconciliation_record"]
    transition = transition_document["transition"]
    for field in (
        "from_setting_as_documented",
        "to_setting_as_documented",
        "responsible_sender_role",
        "responsible_receiver_role",
    ):
        _required_text(
            transition[field],
            f"transition_reconciliation_record:$.transition.{field}",
            issues,
        )
    _required_time(
        transition["handoff_date"],
        "transition_reconciliation_record:$.transition.handoff_date",
        issues,
    )

    reconciliation = transition_document["medication_reconciliation"]
    if reconciliation["status"] == "pending_authorized_review":
        issues.append(
            Issue(
                "MEDICATION_RECONCILIATION_PENDING",
                (
                    "transition_reconciliation_record:"
                    "$.medication_reconciliation.status"
                ),
            )
        )
    if reconciliation["status"] == "completed_by_authorized_clinician":
        if not reconciliation["source_list_fact_ids"]:
            issues.append(
                Issue(
                    "RECONCILIATION_SOURCE_LIST_FACTS_REQUIRED",
                    (
                        "transition_reconciliation_record:"
                        "$.medication_reconciliation.source_list_fact_ids"
                    ),
                )
            )
        if not reconciliation["destination_list_fact_ids"]:
            issues.append(
                Issue(
                    "RECONCILIATION_DESTINATION_LIST_FACTS_REQUIRED",
                    (
                        "transition_reconciliation_record:"
                        "$.medication_reconciliation.destination_list_fact_ids"
                    ),
                )
            )
        if reconciliation["discrepancy_status"] == "not_assessed":
            issues.append(
                Issue(
                    "RECONCILIATION_DISCREPANCY_STATUS_PENDING",
                    (
                        "transition_reconciliation_record:"
                        "$.medication_reconciliation.discrepancy_status"
                    ),
                )
            )
    if reconciliation["status"] != "pending_authorized_review":
        _required_text(
            reconciliation["completed_by_role"],
            (
                "transition_reconciliation_record:"
                "$.medication_reconciliation.completed_by_role"
            ),
            issues,
        )
        _required_time(
            reconciliation["completed_at"],
            (
                "transition_reconciliation_record:"
                "$.medication_reconciliation.completed_at"
            ),
            issues,
        )

    if not transition_document["handoff_items"]:
        issues.append(
            Issue(
                "HANDOFF_ITEM_REQUIRED",
                "transition_reconciliation_record:$.handoff_items",
            )
        )
    for index, item in enumerate(transition_document["handoff_items"]):
        if item["acknowledgment_status"] == "pending":
            issues.append(
                Issue(
                    "HANDOFF_ITEM_ACKNOWLEDGMENT_PENDING",
                    (
                        "transition_reconciliation_record:"
                        f"$.handoff_items[{index}].acknowledgment_status"
                    ),
                )
            )
    for index, item in enumerate(transition_document["unresolved_items"]):
        if item["status"] == "open_unrouted":
            issues.append(
                Issue(
                    "UNRESOLVED_ITEM_NOT_ROUTED",
                    (
                        "transition_reconciliation_record:"
                        f"$.unresolved_items[{index}].status"
                    ),
                )
            )
        if item["status"] != "resolved_by_authorized_professional":
            _required_text(
                item["routed_to_local_role"],
                (
                    "transition_reconciliation_record:"
                    f"$.unresolved_items[{index}].routed_to_local_role"
                ),
                issues,
            )

    handoff_document = documents["intended_use_handoff_record"]
    intended = handoff_document["intended_use"]
    if not intended["intended_users"]:
        issues.append(
            Issue(
                "INTENDED_USER_REQUIRED",
                "intended_use_handoff_record:$.intended_use.intended_users",
            )
        )
    _required_text(
        intended["intended_setting"],
        "intended_use_handoff_record:$.intended_use.intended_setting",
        issues,
    )

    privacy = handoff_document["privacy_process"]
    for field in (
        "local_authorization_confirmed",
        "minimum_necessary_confirmed",
        "no_external_tools_confirmed",
        "no_prompt_log_example_copy_confirmed",
    ):
        if not privacy[field]:
            issues.append(
                Issue(
                    "PRIVACY_PROCESS_ATTESTATION_PENDING",
                    f"intended_use_handoff_record:$.privacy_process.{field}",
                )
            )
    _required_text(
        privacy["authorized_environment_reference"],
        (
            "intended_use_handoff_record:"
            "$.privacy_process.authorized_environment_reference"
        ),
        issues,
    )
    _required_text(
        privacy["retention_policy_reference"],
        (
            "intended_use_handoff_record:"
            "$.privacy_process.retention_policy_reference"
        ),
        issues,
    )
    classification = handoff_document["data_classification"]
    expected_review = (
        {"not_applicable_synthetic", "completed_by_qualified_reviewer"}
        if classification == "synthetic"
        else {"completed_by_qualified_reviewer"}
    )
    if privacy["privacy_review_status"] not in expected_review:
        issues.append(
            Issue(
                "QUALIFIED_PRIVACY_REVIEW_PENDING",
                (
                    "intended_use_handoff_record:"
                    "$.privacy_process.privacy_review_status"
                ),
            )
        )
    if privacy["privacy_review_status"] == "completed_by_qualified_reviewer":
        _required_text(
            privacy["privacy_reviewer_role"],
            (
                "intended_use_handoff_record:"
                "$.privacy_process.privacy_reviewer_role"
            ),
            issues,
        )
        _required_time(
            privacy["reviewed_at"],
            "intended_use_handoff_record:$.privacy_process.reviewed_at",
            issues,
        )
    if privacy["data_disposition_status"] == "pending":
        issues.append(
            Issue(
                "DATA_DISPOSITION_PENDING",
                (
                    "intended_use_handoff_record:"
                    "$.privacy_process.data_disposition_status"
                ),
            )
        )

    governance = handoff_document["local_governance"]
    for field in (
        "institution_or_organization_reference",
        "clinical_owner_role",
        "records_owner_role",
        "change_control_owner_role",
    ):
        _required_text(
            governance[field],
            f"intended_use_handoff_record:$.local_governance.{field}",
            issues,
        )
    if not governance["policy_references"]:
        issues.append(
            Issue(
                "LOCAL_POLICY_REFERENCE_REQUIRED",
                (
                    "intended_use_handoff_record:"
                    "$.local_governance.policy_references"
                ),
            )
        )

    emergency = handoff_document["emergency_routing"]
    _required_text(
        emergency["local_process_reference"],
        (
            "intended_use_handoff_record:"
            "$.emergency_routing.local_process_reference"
        ),
        issues,
    )
    _required_text(
        emergency["verified_by_role"],
        (
            "intended_use_handoff_record:"
            "$.emergency_routing.verified_by_role"
        ),
        issues,
    )

    routes = handoff_document["reporting_routes"]
    for field in (
        "local_patient_safety_route",
        "product_event_route",
        "privacy_incident_route",
        "responsible_role",
    ):
        _required_text(
            routes[field],
            f"intended_use_handoff_record:$.reporting_routes.{field}",
            issues,
        )

    handoff = handoff_document["handoff"]
    for field in ("sender_role", "recipient_role"):
        _required_text(
            handoff[field],
            f"intended_use_handoff_record:$.handoff.{field}",
            issues,
        )
    _required_time(
        handoff["sent_at"],
        "intended_use_handoff_record:$.handoff.sent_at",
        issues,
    )
    if handoff["acknowledgment_status"] != "acknowledged":
        issues.append(
            Issue(
                "PACKAGE_HANDOFF_ACKNOWLEDGMENT_PENDING",
                "intended_use_handoff_record:$.handoff.acknowledgment_status",
            )
        )
    if transition_document["unresolved_items"] and not handoff[
        "unresolved_items_routed"
    ]:
        issues.append(
            Issue(
                "UNRESOLVED_ITEM_ROUTING_ATTESTATION_PENDING",
                (
                    "intended_use_handoff_record:"
                    "$.handoff.unresolved_items_routed"
                ),
            )
        )

    signoff = handoff_document["clinician_signoff"]
    if signoff["status"] != "signed":
        issues.append(
            Issue(
                "CLINICIAN_SIGNOFF_PENDING",
                "intended_use_handoff_record:$.clinician_signoff.status",
            )
        )
    for field in ("signer_role", "credential_authority_reference"):
        _required_text(
            signoff[field],
            f"intended_use_handoff_record:$.clinician_signoff.{field}",
            issues,
        )
    _required_time(
        signoff["signed_at"],
        "intended_use_handoff_record:$.clinician_signoff.signed_at",
        issues,
    )

    release = handoff_document["release_gate"]
    if release["status"] != "released_for_authorized_documentation_handoff":
        issues.append(
            Issue(
                "DOCUMENTATION_HANDOFF_RELEASE_BLOCKED",
                "intended_use_handoff_record:$.release_gate.status",
            )
        )
    _required_text(
        release["released_by_role"],
        "intended_use_handoff_record:$.release_gate.released_by_role",
        issues,
    )
    _required_time(
        release["released_at"],
        "intended_use_handoff_record:$.release_gate.released_at",
        issues,
    )
    if release["blocker_codes"]:
        issues.append(
            Issue(
                "RELEASE_BLOCKER_CODES_REMAIN",
                "intended_use_handoff_record:$.release_gate.blocker_codes",
            )
        )

    issues.sort(key=lambda item: (item.path, item.code))
    return report_payload(
        "documentation_completeness",
        issues,
        counts={
            "source_facts": len(facts),
            "interventions": len(interventions),
            "goals": len(planning["goals"]),
            "monitoring_items": len(planning["monitoring_items"]),
            "checkpoints": len(planning["checkpoints"]),
            "shared_decision_entries": len(decisions),
            "handoff_items": len(transition_document["handoff_items"]),
            "unresolved_items": len(
                transition_document["unresolved_items"]
            ),
        },
        extra={
            "documentation_declarations_complete": not issues,
            "handoff_authorized_by_script": False,
            "clinical_completeness_determined": False,
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check required documentation, review, routing, sign-off, and "
            "handoff declarations. No clinical adequacy is assessed."
        )
    )
    parser.add_argument("package", help="Complete local package directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        documents, _ = load_package(args.package)
        report = check_completeness(documents)
    except ValidationError as exc:
        report = error_report("documentation_completeness", exc)
    print_report(report)
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
