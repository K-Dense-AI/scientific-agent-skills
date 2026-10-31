#!/usr/bin/env python3
"""Validate structured ICH E3, CONSORT 2025, or SPIRIT 2025 coverage."""

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

TOOL = "validate_trial_report"
ALLOWED_STATUSES = {
    "verified_present",
    "not_applicable_with_rationale",
    "missing",
    "conflict",
}
E3_SECTIONS = (
    "title_page",
    "synopsis",
    "table_of_contents",
    "abbreviations_and_definitions",
    "ethics",
    "investigators_and_administration",
    "introduction",
    "study_objectives",
    "investigational_plan",
    "study_patients",
    "efficacy_evaluation",
    "safety_evaluation",
    "discussion_and_conclusions",
    "tables_figures_graphs_not_in_text",
    "reference_list",
    "appendices",
)
COMMON_TOP_FIELDS = {
    "schema_version",
    "artifact_kind",
    "draft_status",
    "safety_notice",
    "data_classification",
    "authorized_purpose",
    "authorization_verified",
    "guidance",
    "provenance_manifest",
    "review",
}
ROUTES = {
    "clinical_study_report_draft": {
        "container": "sections",
        "keys": E3_SECTIONS,
        "guidance": "ICH E3 Step 4 1995-11-30 with Q&A R1 2012-07-06",
        "review_fields": (
            "medical_review",
            "statistical_review",
            "safety_review",
            "privacy_legal_review",
            "quality_review",
            "regulatory_review",
        ),
        "authorization_field": "submission_authorized",
        "draft_status": "BLOCKED_INCOMPLETE_DRAFT_NOT_FOR_FILING_OR_SUBMISSION",
        "top_fields": COMMON_TOP_FIELDS | {"study_metadata", "sections"},
        "metadata_name": "study_metadata",
        "item_fields": {"status", "source_fact_ids", "rationale"},
    },
    "randomized_trial_results_draft": {
        "container": "checklist_items",
        "keys": tuple(f"C{number:02d}" for number in range(1, 31)),
        "guidance": "CONSORT 2025",
        "review_fields": (
            "accountable_author_review",
            "methodologist_review",
            "statistical_review",
            "safety_review",
        ),
        "authorization_field": "publication_authorized",
        "draft_status": (
            "BLOCKED_INCOMPLETE_DRAFT_NOT_FOR_PUBLICATION_OR_SUBMISSION"
        ),
        "top_fields": COMMON_TOP_FIELDS
        | {
            "study_metadata",
            "checklist_items",
            "not_applicable_rationales",
            "participant_flow_source_fact_ids",
        },
        "metadata_name": "study_metadata",
        "item_fields": {"status", "source_fact_ids", "official_item_locator"},
    },
    "randomized_trial_protocol_reporting_manifest": {
        "container": "checklist_items",
        "keys": tuple(f"S{number:02d}" for number in range(1, 35)),
        "guidance": "SPIRIT 2025",
        "review_fields": (
            "investigator_sponsor_review",
            "methodologist_review",
            "statistical_review",
            "safety_review",
            "ethics_regulatory_review",
        ),
        "authorization_field": "protocol_approved",
        "draft_status": (
            "BLOCKED_INCOMPLETE_REPORTING_CHECKLIST_NOT_A_PROTOCOL_OR_ETHICS_APPROVAL"
        ),
        "top_fields": COMMON_TOP_FIELDS
        | {
            "protocol_metadata",
            "checklist_items",
            "not_applicable_rationales",
            "participant_timeline_source_fact_ids",
        },
        "metadata_name": "protocol_metadata",
        "item_fields": {"status", "source_fact_ids", "official_item_locator"},
    },
}


def _validate_guidance(
    artifact_kind: str,
    guidance: Any,
    errors: list[str],
) -> None:
    if not isinstance(guidance, dict):
        errors.append("guidance must be an object")
        return
    if artifact_kind == "clinical_study_report_draft":
        try:
            guidance = require_exact_keys(
                guidance,
                {
                    "base",
                    "base_version",
                    "qa_version",
                    "gcp_version_considered",
                    "regional_adoption_verified",
                },
                "guidance",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            return
        if guidance.get("base") != "ICH E3":
            errors.append("CSR guidance.base must be ICH E3")
        if guidance.get("base_version") != "Step 4 1995-11-30":
            errors.append("CSR base_version is not the supported ICH E3 version")
        if guidance.get("qa_version") != "R1 2012-07-06":
            errors.append("CSR qa_version is not the supported E3 Q&A version")
        if (
            guidance.get("gcp_version_considered")
            != "ICH E6(R3) consolidated 2026-06-16"
        ):
            errors.append("CSR must record consideration of current ICH E6(R3)")
        if guidance.get("regional_adoption_verified") is not True:
            errors.append("CSR regional adoption/version review is required")
    elif artifact_kind == "randomized_trial_results_draft":
        try:
            guidance = require_exact_keys(
                guidance,
                {
                    "base",
                    "item_count",
                    "statement_and_explanation_checked",
                    "applicable_extensions",
                    "applicable_extensions_reviewed",
                    "extension_conflicts_resolved_by_methodologist",
                },
                "guidance",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            return
        if guidance.get("base") != "CONSORT 2025" or guidance.get("item_count") != 30:
            errors.append("results manifest must declare CONSORT 2025 with 30 items")
        if guidance.get("statement_and_explanation_checked") is not True:
            errors.append("CONSORT statement and explanation must be checked")
        if guidance.get("applicable_extensions_reviewed") is not True:
            errors.append("applicable CONSORT extensions must be reviewed")
        extensions = guidance.get("applicable_extensions")
        if not isinstance(extensions, list):
            errors.append("guidance.applicable_extensions must be an array")
        else:
            for index, extension in enumerate(extensions):
                try:
                    require_string(
                        extension,
                        f"guidance.applicable_extensions[{index}]",
                        max_length=200,
                    )
                except ValidationError as exc:
                    errors.append(str(exc))
        try:
            conflicts_resolved = require_bool(
                guidance.get("extension_conflicts_resolved_by_methodologist"),
                "guidance.extension_conflicts_resolved_by_methodologist",
            )
            if extensions and not conflicts_resolved:
                errors.append("extension conflicts require methodologist resolution")
        except ValidationError as exc:
            errors.append(str(exc))
    elif artifact_kind == "randomized_trial_protocol_reporting_manifest":
        try:
            guidance = require_exact_keys(
                guidance,
                {
                    "base",
                    "item_count",
                    "statement_and_explanation_checked",
                    "applicable_extensions",
                    "applicable_extensions_reviewed",
                    "extension_conflicts_resolved_by_methodologist",
                },
                "guidance",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            return
        if guidance.get("base") != "SPIRIT 2025" or guidance.get("item_count") != 34:
            errors.append("protocol manifest must declare SPIRIT 2025 with 34 items")
        if guidance.get("statement_and_explanation_checked") is not True:
            errors.append("SPIRIT statement and explanation must be checked")
        if guidance.get("applicable_extensions_reviewed") is not True:
            errors.append("applicable SPIRIT extensions must be reviewed")
        extensions = guidance.get("applicable_extensions")
        if not isinstance(extensions, list):
            errors.append("guidance.applicable_extensions must be an array")
        else:
            for index, extension in enumerate(extensions):
                try:
                    require_string(
                        extension,
                        f"guidance.applicable_extensions[{index}]",
                        max_length=200,
                    )
                except ValidationError as exc:
                    errors.append(str(exc))
        try:
            conflicts_resolved = require_bool(
                guidance.get("extension_conflicts_resolved_by_methodologist"),
                "guidance.extension_conflicts_resolved_by_methodologist",
            )
            if extensions and not conflicts_resolved:
                errors.append("extension conflicts require methodologist resolution")
        except ValidationError as exc:
            errors.append(str(exc))


def _validate_metadata(
    artifact_kind: str,
    value: Any,
    errors: list[str],
    warnings: list[str],
) -> None:
    if artifact_kind == "clinical_study_report_draft":
        fields = {
            "protocol_reference",
            "sap_reference",
            "data_cut_reference",
            "analysis_output_reference",
            "coding_dictionary_versions",
        }
        try:
            metadata = require_exact_keys(value, fields, "study_metadata")
            for field in fields - {"coding_dictionary_versions"}:
                require_string(metadata.get(field), f"study_metadata.{field}")
            versions = metadata.get("coding_dictionary_versions")
            if not isinstance(versions, list) or not versions:
                raise ValidationError(
                    "study_metadata.coding_dictionary_versions must be non-empty"
                )
            for index, version in enumerate(versions):
                require_string(
                    version,
                    f"study_metadata.coding_dictionary_versions[{index}]",
                    max_length=100,
                )
        except ValidationError as exc:
            errors.append(str(exc))
    elif artifact_kind == "randomized_trial_results_draft":
        fields = {
            "protocol_reference",
            "sap_reference",
            "registry_reference",
            "data_cut_reference",
            "analysis_output_reference",
        }
        try:
            metadata = require_exact_keys(value, fields, "study_metadata")
            for field in fields:
                require_string(metadata.get(field), f"study_metadata.{field}")
        except ValidationError as exc:
            errors.append(str(exc))
    else:
        fields = {
            "authorized_protocol_reference",
            "protocol_version",
            "registry_reference",
            "ethics_record_reference",
        }
        try:
            metadata = require_exact_keys(value, fields, "protocol_metadata")
            for field in fields - {"ethics_record_reference"}:
                require_string(metadata.get(field), f"protocol_metadata.{field}")
            if metadata.get("ethics_record_reference") is None:
                warnings.append("protocol_metadata.ethics_record_reference remains pending")
            else:
                require_string(
                    metadata.get("ethics_record_reference"),
                    "protocol_metadata.ethics_record_reference",
                )
        except ValidationError as exc:
            errors.append(str(exc))


def _validated_fact_ids(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be an array")
    return [require_identifier(item, field) for item in value]


def validate_trial_manifest(data: dict[str, Any]) -> dict[str, Any]:
    """Return structural findings without evaluating trial content."""
    errors: list[str] = []
    warnings: list[str] = []
    artifact_kind = data.get("artifact_kind")
    route = ROUTES.get(artifact_kind) if isinstance(artifact_kind, str) else None
    if route is None:
        return {
            "tool": TOOL,
            "status": "BLOCKED",
            "errors": [f"unsupported artifact_kind: {artifact_kind!r}"],
            "warnings": [],
            "review_required": True,
            "authorizes_clinical_use_or_submission": False,
        }

    try:
        require_exact_keys(data, route["top_fields"], "manifest")
        if data.get("schema_version") != "2.0":
            raise ValidationError("schema_version must be 2.0")
        if data.get("draft_status") != route["draft_status"]:
            raise ValidationError(
                "draft_status must preserve the blocked non-use/non-submission warning"
            )
        require_string(data.get("safety_notice"), "safety_notice", max_length=1000)
        require_data_class(data.get("data_classification"))
        require_string(data.get("authorized_purpose"), "authorized_purpose")
        if not require_bool(data.get("authorization_verified"), "authorization_verified"):
            errors.append("authorization_verified must be true")
        require_string(data.get("provenance_manifest"), "provenance_manifest")
    except ValidationError as exc:
        errors.append(str(exc))

    _validate_guidance(str(artifact_kind), data.get("guidance"), errors)
    _validate_metadata(
        str(artifact_kind),
        data.get(route["metadata_name"]),
        errors,
        warnings,
    )

    container_name = str(route["container"])
    expected_keys = tuple(route["keys"])
    container = data.get(container_name)
    if not isinstance(container, dict):
        errors.append(f"{container_name} must be an object")
        container = {}
    missing_keys = sorted(set(expected_keys) - set(container))
    extra_keys = sorted(set(container) - set(expected_keys))
    if missing_keys:
        errors.append(f"missing {container_name} keys: {missing_keys}")
    if extra_keys:
        errors.append(f"unexpected {container_name} keys: {extra_keys}")

    coverage: dict[str, str] = {}
    rationale_map = data.get("not_applicable_rationales", {})
    if container_name == "checklist_items" and not isinstance(rationale_map, dict):
        errors.append("not_applicable_rationales must be an object")
        rationale_map = {}
    for key in expected_keys:
        item = container.get(key)
        if not isinstance(item, dict):
            errors.append(f"{container_name}.{key} must be an object")
            continue
        try:
            item = require_exact_keys(
                item,
                route["item_fields"],
                f"{container_name}.{key}",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        status = item.get("status")
        coverage[key] = str(status)
        if not isinstance(status, str) or status not in ALLOWED_STATUSES:
            errors.append(f"{container_name}.{key}.status is invalid")
            continue
        try:
            facts = _validated_fact_ids(
                item.get("source_fact_ids"),
                f"{container_name}.{key}.source_fact_ids",
            )
        except ValidationError as exc:
            errors.append(str(exc))
            facts = []
        if status == "verified_present":
            if not facts:
                errors.append(f"{container_name}.{key} requires a verified source fact")
            if container_name == "checklist_items":
                try:
                    require_string(
                        item.get("official_item_locator"),
                        f"{container_name}.{key}.official_item_locator",
                    )
                except ValidationError as exc:
                    errors.append(str(exc))
        elif status == "not_applicable_with_rationale":
            try:
                require_string(
                    (
                        item.get("rationale")
                        if container_name == "sections"
                        else rationale_map.get(key)
                    ),
                    (
                        f"{container_name}.{key}.rationale"
                        if container_name == "sections"
                        else f"not_applicable_rationales.{key}"
                    ),
                    max_length=500,
                )
            except ValidationError as exc:
                errors.append(str(exc))
        else:
            errors.append(f"{container_name}.{key} is {status}")

    if artifact_kind == "randomized_trial_results_draft":
        try:
            flow_facts = _validated_fact_ids(
                data.get("participant_flow_source_fact_ids"),
                "participant_flow_source_fact_ids",
            )
            if not flow_facts:
                errors.append("participant flow requires verified source facts")
        except ValidationError as exc:
            errors.append(str(exc))
    elif artifact_kind == "randomized_trial_protocol_reporting_manifest":
        try:
            timeline_facts = _validated_fact_ids(
                data.get("participant_timeline_source_fact_ids"),
                "participant_timeline_source_fact_ids",
            )
            if not timeline_facts:
                errors.append("participant timeline requires verified source facts")
        except ValidationError as exc:
            errors.append(str(exc))

    review = data.get("review")
    try:
        review = require_exact_keys(
            review,
            {*route["review_fields"], route["authorization_field"]},
            "review",
        )
        for field in route["review_fields"]:
            if review.get(field) != "completed":
                warnings.append(f"review.{field} remains required")
        authorization_field = str(route["authorization_field"])
        if review.get(authorization_field) is not False:
            errors.append(f"review.{authorization_field} must remain false")
    except ValidationError as exc:
        errors.append(str(exc))

    return {
        "tool": TOOL,
        "artifact_kind": artifact_kind,
        "guidance": route["guidance"],
        "status": "BLOCKED" if errors else "STRUCTURE_COMPLETE_REVIEW_REQUIRED",
        "coverage": coverage,
        "errors": errors,
        "warnings": warnings,
        "limitations": [
            "Checks item keys, statuses, and fact-ID shape; does not check cross-artifact linkage.",
            "Does not validate conduct, analyses, clinical content, compliance, or submission format.",
        ],
        "review_required": True,
        "authorizes_clinical_use_or_submission": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check a bounded JSON ICH E3, CONSORT 2025, or SPIRIT 2025 "
            "coverage manifest; never claims compliance."
        )
    )
    parser.add_argument("input_file", help="Local trial-report manifest (.json)")
    parser.add_argument("-o", "--output", help="Optional local JSON report path")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _, data = load_json_object(args.input_file)
        report = validate_trial_manifest(data)
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
