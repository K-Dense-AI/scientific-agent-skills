#!/usr/bin/env python3
"""Check criterion-to-evidence traceability without copying source content."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import _common

SOURCE_TYPES = (
    "section",
    "table",
    "figure",
    "dataset",
    "code",
    "protocol",
    "registration",
    "other_local_record",
)
ACCESS_STATUSES = ("available", "restricted_authorized", "unavailable")
VERIFICATION_STATUSES = ("verified", "unverified")


def validate_manifest(
    manifest: Any, rubric: dict, evaluation: dict
) -> tuple[list[_common.Issue], dict[str, dict]]:
    issues: list[_common.Issue] = []
    evidence_by_id: dict[str, dict] = {}
    if not _common.exact_keys(
        manifest,
        {
            "schema_version",
            "evaluation_id",
            "work_id",
            "data_classification",
            "evidence",
        },
        "$",
        issues,
    ):
        return issues, evidence_by_id
    if manifest.get("schema_version") != _common.SCHEMA_VERSION:
        issues.append(_common.Issue("SCHEMA_VERSION_UNSUPPORTED", "$.schema_version"))
    if manifest.get("evaluation_id") != evaluation.get("evaluation_id"):
        issues.append(_common.Issue("EVALUATION_ID_MISMATCH", "$.evaluation_id"))
    if manifest.get("work_id") != evaluation.get("work_id"):
        issues.append(_common.Issue("WORK_ID_MISMATCH", "$.work_id"))
    if manifest.get("data_classification") != evaluation.get("data_classification"):
        issues.append(
            _common.Issue("DATA_CLASSIFICATION_MISMATCH", "$.data_classification")
        )
    if manifest.get("data_classification") not in _common.ALLOWED_CLASSIFICATIONS:
        issues.append(
            _common.Issue(
                "DATA_CLASSIFICATION_NOT_ALLOWED", "$.data_classification"
            )
        )
    criterion_ids = {criterion["criterion_id"] for criterion in rubric["criteria"]}
    evidence = manifest.get("evidence")
    if not isinstance(evidence, list) or len(evidence) > 5_000:
        issues.append(_common.Issue("EVIDENCE_LIST_INVALID", "$.evidence"))
        return issues, evidence_by_id
    for index, item in enumerate(evidence):
        path = f"$.evidence[{index}]"
        if not _common.exact_keys(
            item,
            {
                "evidence_id",
                "criterion_ids",
                "source_type",
                "locator_ref",
                "claim_ref",
                "access_status",
                "verification_status",
            },
            path,
            issues,
        ):
            continue
        evidence_id = item.get("evidence_id")
        _common.validate_identifier(
            evidence_id, f"{path}.evidence_id", issues, "EVIDENCE_ID_INVALID"
        )
        if isinstance(evidence_id, str):
            if evidence_id in evidence_by_id:
                issues.append(
                    _common.Issue("EVIDENCE_ID_DUPLICATE", f"{path}.evidence_id")
                )
            evidence_by_id[evidence_id] = item
        linked = item.get("criterion_ids")
        if not isinstance(linked, list) or not 1 <= len(linked) <= 50:
            issues.append(_common.Issue("CRITERION_IDS_INVALID", f"{path}.criterion_ids"))
        else:
            linked_text = [
                criterion_id
                for criterion_id in linked
                if isinstance(criterion_id, str)
            ]
            if len(linked_text) != len(set(linked_text)):
                issues.append(
                    _common.Issue(
                        "CRITERION_ID_DUPLICATE", f"{path}.criterion_ids"
                    )
                )
            for criterion_index, criterion_id in enumerate(linked):
                _common.validate_identifier(
                    criterion_id,
                    f"{path}.criterion_ids[{criterion_index}]",
                    issues,
                )
                if isinstance(criterion_id, str) and criterion_id not in criterion_ids:
                    issues.append(
                        _common.Issue(
                            "CRITERION_UNKNOWN",
                            f"{path}.criterion_ids[{criterion_index}]",
                        )
                    )
        if item.get("source_type") not in SOURCE_TYPES:
            issues.append(_common.Issue("SOURCE_TYPE_INVALID", f"{path}.source_type"))
        _common.validate_reference(item.get("locator_ref"), f"{path}.locator_ref", issues)
        _common.validate_reference(item.get("claim_ref"), f"{path}.claim_ref", issues)
        if item.get("access_status") not in ACCESS_STATUSES:
            issues.append(_common.Issue("ACCESS_STATUS_INVALID", f"{path}.access_status"))
        if item.get("access_status") == "unavailable":
            issues.append(_common.Issue("EVIDENCE_UNAVAILABLE", f"{path}.access_status"))
        if item.get("verification_status") not in VERIFICATION_STATUSES:
            issues.append(
                _common.Issue(
                    "VERIFICATION_STATUS_INVALID", f"{path}.verification_status"
                )
            )
        elif item.get("verification_status") != "verified":
            issues.append(
                _common.Issue("EVIDENCE_UNVERIFIED", f"{path}.verification_status")
            )
    return issues, evidence_by_id


def check_traceability(rubric: dict, evaluation: dict, manifest: dict) -> dict:
    rubric_issues = _common.validate_rubric(rubric)
    _common.require_valid(rubric_issues)
    evaluation_issues = _common.validate_evaluation(evaluation, rubric)
    _common.require_valid(evaluation_issues)
    issues, evidence_by_id = validate_manifest(manifest, rubric, evaluation)
    used_ids: set[str] = set()
    for index, rating in enumerate(evaluation["ratings"]):
        if rating["status"] != "rated":
            continue
        criterion_id = rating["criterion_id"]
        for evidence_index, evidence_id in enumerate(rating["evidence_ids"]):
            used_ids.add(evidence_id)
            path = f"$.ratings[{index}].evidence_ids[{evidence_index}]"
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                issues.append(_common.Issue("EVIDENCE_REFERENCE_UNRESOLVED", path))
            elif not isinstance(evidence.get("criterion_ids"), list) or criterion_id not in evidence["criterion_ids"]:
                issues.append(_common.Issue("EVIDENCE_CRITERION_MISMATCH", path))
    for evidence_id in sorted(set(evidence_by_id) - used_ids):
        issues.append(
            _common.Issue(
                "EVIDENCE_UNUSED",
                f"$.evidence.{evidence_id}",
                "warning",
            )
        )
    errors = _common.error_issues(issues)
    rated_count = sum(
        rating["status"] == "rated" for rating in evaluation["ratings"]
    )
    resolved_count = sum(
        1
        for rating in evaluation["ratings"]
        if rating["status"] == "rated"
        and rating["evidence_ids"]
        and all(evidence_id in evidence_by_id for evidence_id in rating["evidence_ids"])
    )
    return {
        "schema_version": _common.SCHEMA_VERSION,
        "report_type": "evidence_traceability_check",
        "notice": _common.NOTICE,
        "status": "fail" if errors else "pass",
        "evaluation_id": evaluation["evaluation_id"],
        "work_id": evaluation["work_id"],
        "rated_criteria": rated_count,
        "rated_criteria_with_resolved_evidence": resolved_count,
        "evidence_records": len(evidence_by_id),
        "error_count": len(errors),
        "warning_count": len(issues) - len(errors),
        "issues": [issue.as_dict() for issue in issues],
        "source_content_copied_to_output": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify local evidence identifiers and criterion mappings. "
            "The report contains references and counts, never evidence excerpts."
        )
    )
    parser.add_argument("--rubric", required=True, type=Path, help="Local rubric JSON")
    parser.add_argument(
        "--evaluation", required=True, type=Path, help="Local evaluation JSON"
    )
    parser.add_argument(
        "--evidence", required=True, type=Path, help="Local evidence-manifest JSON"
    )
    parser.add_argument("--output", type=Path, help="Optional local JSON report")
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing output JSON file"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = check_traceability(
            _common.read_json(args.rubric),
            _common.read_json(args.evaluation),
            _common.read_json(args.evidence),
        )
        _common.write_json(report, args.output, force=args.force)
        return 0 if report["status"] == "pass" else 2
    except _common.ValidationError as error:
        _common.write_json(_common.failure_report(error), None)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
