#!/usr/bin/env python3
"""Generate a minimized local JSON scaffold for qualified human review."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import _common


def _load_companion(
    report: dict[str, Any] | None,
    *,
    report_type: str,
    rubric_id: str | None = None,
    evaluation_id: str | None = None,
    work_id: str | None = None,
) -> dict[str, Any] | None:
    if report is None:
        return None
    if not isinstance(report, dict) or report.get("schema_version") != _common.SCHEMA_VERSION:
        raise _common.ValidationError("COMPANION_REPORT_INVALID")
    if report.get("report_type") != report_type:
        raise _common.ValidationError("COMPANION_REPORT_TYPE_MISMATCH")
    if rubric_id is not None and report.get("rubric_id") != rubric_id:
        raise _common.ValidationError("COMPANION_RUBRIC_ID_MISMATCH")
    if evaluation_id is not None and report.get("evaluation_id") != evaluation_id:
        raise _common.ValidationError("COMPANION_EVALUATION_ID_MISMATCH")
    if work_id is not None and report.get("work_id") != work_id:
        raise _common.ValidationError("COMPANION_WORK_ID_MISMATCH")
    return report


def generate_scaffold(
    rubric: dict[str, Any],
    evaluation: dict[str, Any],
    *,
    traceability: dict[str, Any] | None = None,
    agreement: dict[str, Any] | None = None,
    sensitivity: dict[str, Any] | None = None,
    process: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rubric_issues = _common.validate_rubric(rubric)
    _common.require_valid(rubric_issues)
    evaluation_issues = _common.validate_evaluation(evaluation, rubric)
    _common.require_valid(evaluation_issues)
    score_report = _common.score_evaluation(rubric, evaluation)
    traceability = _load_companion(
        traceability,
        report_type="evidence_traceability_check",
        evaluation_id=evaluation["evaluation_id"],
        work_id=evaluation["work_id"],
    )
    agreement = _load_companion(
        agreement,
        report_type="inter_rater_agreement_summary",
        rubric_id=rubric["rubric_id"],
    )
    sensitivity = _load_companion(
        sensitivity,
        report_type="weight_sensitivity_and_rank_instability",
        rubric_id=rubric["rubric_id"],
    )
    process = _load_companion(process, report_type="bias_and_process_check")
    expected_record = {
        "evaluation_id": evaluation["evaluation_id"],
        "work_id": evaluation["work_id"],
    }
    for companion in (agreement, sensitivity):
        if companion is not None and (
            not isinstance(companion.get("evaluation_records"), list)
            or expected_record not in companion["evaluation_records"]
        ):
            raise _common.ValidationError("COMPANION_EVALUATION_NOT_INCLUDED")
    if traceability and (
        traceability.get("status") not in ("pass", "fail")
        or not isinstance(traceability.get("error_count"), int)
    ):
        raise _common.ValidationError("COMPANION_REPORT_INVALID")
    agreement_overall = agreement.get("overall") if agreement else None
    if agreement and (
        not isinstance(agreement_overall, dict)
        or not isinstance(agreement_overall.get("pair_observations"), int)
    ):
        raise _common.ValidationError("COMPANION_REPORT_INVALID")
    if sensitivity and not isinstance(
        sensitivity.get("rank_instability_detected"), bool
    ):
        raise _common.ValidationError("COMPANION_REPORT_INVALID")
    if process and process.get("status") not in (
        "invalid",
        "blocked",
        "incomplete",
        "complete_for_low_stakes_process",
    ):
        raise _common.ValidationError("COMPANION_REPORT_INVALID")
    criterion_scaffold = []
    for result in score_report["criteria"]:
        criterion_scaffold.append(
            {
                "criterion_id": result["criterion_id"],
                "status": result["status"],
                "score": result["score"],
                "uncertainty": result["uncertainty"],
                "evidence_finding_refs": [],
                "strength_refs": [],
                "limitation_refs": [],
                "improvement_option_refs": [],
                "qualified_reviewer_comment_ref": "",
            }
        )
    return {
        "schema_version": _common.SCHEMA_VERSION,
        "report_type": "developmental_scholarly_work_report_scaffold",
        "notice": _common.NOTICE,
        "evaluation_id": evaluation["evaluation_id"],
        "work_id": evaluation["work_id"],
        "rubric_id": rubric["rubric_id"],
        "purpose": _common.ALLOWED_PURPOSE,
        "unit_of_assessment": _common.ALLOWED_UNIT,
        "construct": {
            "rubric_record_ref": rubric["rubric_id"],
            "content_validity_status": rubric["provenance"][
                "content_validity_status"
            ],
            "rubric_source_count": len(rubric["provenance"]["source_ids"]),
        },
        "descriptive_score_summary": score_report["aggregates"],
        "criterion_scaffold": criterion_scaffold,
        "quality_assurance": {
            "traceability_status": (
                traceability.get("status") if traceability else "not_provided"
            ),
            "traceability_error_count": (
                traceability.get("error_count") if traceability else None
            ),
            "agreement_pair_observations": (
                agreement_overall.get("pair_observations") if agreement_overall else None
            ),
            "agreement_status": (
                "provided" if agreement else "not_provided"
            ),
            "inter_rater_reliability_status": rubric["rater_protocol"][
                "inter_rater_reliability_status"
            ],
            "weight_sensitivity_status": (
                "provided" if sensitivity else "not_provided"
            ),
            "rank_instability_detected": (
                sensitivity.get("rank_instability_detected")
                if sensitivity
                else None
            ),
            "process_check_status": (
                process.get("status") if process else "not_provided"
            ),
        },
        "human_review": {
            "committee_finding_refs": [],
            "conflict_and_recusal_record_ref": "",
            "disciplinary_context_ref": "",
            "accessibility_accommodation_record_ref": "",
            "subgroup_bias_review_ref": rubric["governance"][
                "subgroup_review_ref"
            ],
            "appeal_process_ref": rubric["governance"]["appeal_process_ref"],
            "final_human_review_record_ref": "",
        },
        "required_limitations": [
            "ScholarEval is an experimental literature-grounded research-idea framework, not validated psychometrics.",
            "This rubric requires separate validity, reliability, fairness, and intended-use evidence.",
            "Missing and not-applicable ratings limit comparability.",
            "Criterion uncertainty intervals are bounded judgment ranges, not confidence intervals.",
            "Journal, citation, prestige, institution, venue, and attention indicators do not establish quality.",
            "Companion identifiers establish membership, not unchanged input content; regenerate checks after edits.",
            "The process checklist is a separate self-attestation, not verification of this work or rubric.",
        ],
        "private_source_content_included": False,
        "person_ranking_provided": False,
        "decision_recommendation_provided": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a local JSON report scaffold containing bounded scores, "
            "quality-control summaries, and empty reference slots for qualified "
            "human findings. No source-document text is copied."
        )
    )
    parser.add_argument("--rubric", required=True, type=Path, help="Local rubric JSON")
    parser.add_argument(
        "--evaluation", required=True, type=Path, help="Local evaluation JSON"
    )
    parser.add_argument(
        "--traceability", type=Path, help="Optional traceability report JSON"
    )
    parser.add_argument(
        "--agreement", type=Path, help="Optional agreement report JSON"
    )
    parser.add_argument(
        "--sensitivity", type=Path, help="Optional sensitivity report JSON"
    )
    parser.add_argument(
        "--process", type=Path, help="Optional process-check report JSON"
    )
    parser.add_argument("--output", type=Path, help="Optional local JSON report")
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing output JSON file"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        optional_paths = {
            "traceability": args.traceability,
            "agreement": args.agreement,
            "sensitivity": args.sensitivity,
            "process": args.process,
        }
        companions = {
            name: _common.read_json(path) if path else None
            for name, path in optional_paths.items()
        }
        report = generate_scaffold(
            _common.read_json(args.rubric),
            _common.read_json(args.evaluation),
            **companions,
        )
        _common.write_json(report, args.output, force=args.force)
        return 0
    except _common.ValidationError as error:
        _common.write_json(_common.failure_report(error), None)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
