#!/usr/bin/env python3
"""Summarize inter-rater agreement from pseudonymous local CSV ratings."""

from __future__ import annotations

import argparse
import csv
import io
import itertools
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import _common

CSV_FIELDS = [
    "evaluation_id",
    "work_id",
    "rater_id",
    "criterion_id",
    "status",
    "score",
]


def read_rows(path: Path, rubric: dict[str, Any]) -> list[dict[str, Any]]:
    text = _common.read_csv_text(path)
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != CSV_FIELDS:
        raise _common.ValidationError("CSV_HEADER_INVALID")
    accepted_scores = _common.scale_values(rubric)
    criterion_ids = {criterion["criterion_id"] for criterion in rubric["criteria"]}
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    evaluation_works: dict[str, str] = {}
    for index, row in enumerate(reader, start=2):
        if len(rows) >= _common.MAX_CSV_ROWS:
            raise _common.ValidationError("CSV_TOO_MANY_ROWS")
        path_prefix = f"$.rows[{index}]"
        if set(row) != set(CSV_FIELDS) or any(
            not isinstance(row.get(field), str) for field in CSV_FIELDS
        ):
            raise _common.ValidationError("CSV_ROW_SHAPE_INVALID", path_prefix)
        for field in ("evaluation_id", "work_id", "rater_id", "criterion_id"):
            if not _common.is_identifier(row.get(field)):
                raise _common.ValidationError(
                    "CSV_IDENTIFIER_INVALID", f"{path_prefix}.{field}"
                )
        if row["criterion_id"] not in criterion_ids:
            raise _common.ValidationError(
                "CRITERION_UNKNOWN", f"{path_prefix}.criterion_id"
            )
        if row["status"] not in _common.RATING_STATUSES:
            raise _common.ValidationError(
                "RATING_STATUS_INVALID", f"{path_prefix}.status"
            )
        key = (
            row["evaluation_id"],
            row["work_id"],
            row["rater_id"],
            row["criterion_id"],
        )
        if key in seen:
            raise _common.ValidationError("CSV_RATING_DUPLICATE", path_prefix)
        seen.add(key)
        previous_work = evaluation_works.setdefault(row["evaluation_id"], row["work_id"])
        if previous_work != row["work_id"]:
            raise _common.ValidationError("EVALUATION_WORK_MISMATCH", path_prefix)
        score: float | None
        if row["status"] == "rated":
            try:
                score = float(row["score"])
            except ValueError as error:
                raise _common.ValidationError(
                    "CSV_SCORE_INVALID", f"{path_prefix}.score"
                ) from error
            if not math.isfinite(score) or score not in accepted_scores:
                raise _common.ValidationError(
                    "SCORE_NOT_ON_SCALE", f"{path_prefix}.score"
                )
        else:
            if row["score"].strip():
                raise _common.ValidationError(
                    "UNRATED_SCORE_MUST_BE_BLANK", f"{path_prefix}.score"
                )
            score = None
        rows.append({**row, "score": score})
    if not rows:
        raise _common.ValidationError("CSV_NO_ROWS")
    return rows


def _summary(differences: Counter[float], step: float) -> dict[str, Any]:
    if not differences:
        return {
            "pair_observations": 0,
            "exact_agreement_rate": None,
            "within_one_scale_step_rate": None,
            "mean_absolute_difference": None,
        }
    pair_count = sum(differences.values())
    return {
        "pair_observations": pair_count,
        "exact_agreement_rate": _common.rounded(
            sum(count for difference, count in differences.items() if difference == 0)
            / pair_count
        ),
        "within_one_scale_step_rate": _common.rounded(
            sum(
                count for difference, count in differences.items()
                if difference <= step or math.isclose(difference, step, rel_tol=1e-9, abs_tol=0.0)
            )
            / pair_count
        ),
        "mean_absolute_difference": _common.rounded(
            sum(difference * count for difference, count in differences.items()) / pair_count
        ),
    }


def summarize(rubric: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    rubric_issues = _common.validate_rubric(rubric)
    _common.require_valid(rubric_issues)
    grouped: dict[str, dict[tuple[str, str], dict[str, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    status_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"rated": 0, "missing": 0, "not_applicable": 0}
    )
    raters_by_criterion: dict[str, set[str]] = defaultdict(set)
    works_by_criterion: dict[str, set[str]] = defaultdict(set)
    all_raters: set[str] = set()
    all_works: set[str] = set()
    evaluation_works: dict[str, str] = {}
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        key = tuple(row[field] for field in CSV_FIELDS[:4])
        if key in seen:
            raise _common.ValidationError("CSV_RATING_DUPLICATE")
        seen.add(key)
        previous_work = evaluation_works.setdefault(row["evaluation_id"], row["work_id"])
        if previous_work != row["work_id"]:
            raise _common.ValidationError("EVALUATION_WORK_MISMATCH")
        criterion_id = row["criterion_id"]
        status_counts[criterion_id][row["status"]] += 1
        raters_by_criterion[criterion_id].add(row["rater_id"])
        works_by_criterion[criterion_id].add(row["work_id"])
        all_raters.add(row["rater_id"])
        all_works.add(row["work_id"])
        if row["status"] == "rated":
            unit = (row["evaluation_id"], row["work_id"])
            grouped[criterion_id][unit][row["rater_id"]] = row["score"]

    minimum_raters = int(rubric["rater_protocol"]["minimum_raters"])
    if len(all_raters) < minimum_raters:
        raise _common.ValidationError("MINIMUM_RATERS_NOT_MET")
    step = float(rubric["scale"]["step"])
    criterion_reports: list[dict[str, Any]] = []
    overall_differences: Counter[float] = Counter()
    insufficient: list[str] = []
    for criterion in rubric["criteria"]:
        criterion_id = criterion["criterion_id"]
        differences: Counter[float] = Counter()
        overlap_works: set[str] = set()
        overlap_evaluation_count = 0
        below_minimum_count = 0
        for (_, work_id), work_ratings in grouped.get(criterion_id, {}).items():
            if len(work_ratings) >= 2:
                overlap_works.add(work_id)
                overlap_evaluation_count += 1
            if len(work_ratings) < minimum_raters:
                below_minimum_count += 1
            counts = Counter(work_ratings.values())
            # At most 21 scale anchors: do not materialize O(raters**2) pairs.
            for score, count in counts.items():
                if count >= 2:
                    differences[0.0] += count * (count - 1) // 2
            for (first, first_count), (second, second_count) in itertools.combinations(counts.items(), 2):
                differences[abs(first - second)] += first_count * second_count
        if not differences:
            insufficient.append(criterion_id)
        overall_differences.update(differences)
        criterion_reports.append(
            {
                "criterion_id": criterion_id,
                "rater_count": len(raters_by_criterion.get(criterion_id, set())),
                "work_count": len(works_by_criterion.get(criterion_id, set())),
                "works_with_rater_overlap": len(overlap_works),
                "evaluations_with_rater_overlap": overlap_evaluation_count,
                "rated_evaluations_below_minimum_raters": below_minimum_count,
                "rated_rows": status_counts[criterion_id]["rated"],
                "missing_rows": status_counts[criterion_id]["missing"],
                "not_applicable_rows": status_counts[criterion_id][
                    "not_applicable"
                ],
                **_summary(differences, step),
            }
        )
    warnings = []
    if insufficient:
        warnings.append("INSUFFICIENT_OVERLAP_FOR_SOME_CRITERIA")
    if any(item["rated_evaluations_below_minimum_raters"] for item in criterion_reports):
        warnings.append("MINIMUM_RATERS_NOT_MET_FOR_SOME_CRITERIA_EVALUATIONS")
    if any(
        counts["missing"] or counts["not_applicable"]
        for counts in status_counts.values()
    ):
        warnings.append("MISSING_OR_NOT_APPLICABLE_RATINGS_PRESENT")
    return {
        "schema_version": _common.SCHEMA_VERSION,
        "report_type": "inter_rater_agreement_summary",
        "notice": _common.NOTICE,
        "rubric_id": rubric["rubric_id"],
        "rater_count": len(all_raters),
        "work_count": len(all_works),
        "row_count": len(rows),
        "evaluation_records": [
            {"evaluation_id": evaluation_id, "work_id": work_id}
            for evaluation_id, work_id in sorted(evaluation_works.items())
        ],
        "aggregation_unit": "criterion within one evaluation_id and work_id",
        "aggregation_weighting": "pooled rater pairs; units with more rated raters contribute more pairs",
        "scale_step": step,
        "overall": _summary(overall_differences, step),
        "criteria": criterion_reports,
        "criteria_with_insufficient_overlap": insufficient,
        "warnings": warnings,
        "rater_identifiers_in_output": False,
        "limitations": [
            "Percent agreement and mean absolute difference are descriptive.",
            "These summaries are not a psychometric validation or reliability coefficient.",
            "Select a construct- and design-appropriate reliability model with qualified measurement expertise.",
            "Repeated rounds are kept separate; pooled pairs are dependent observations, not independent samples.",
            "Omitted CSV rows have unknown status and are not counted as missing.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize exact agreement, within-step agreement, and mean "
            "absolute difference from pseudonymous local CSV ratings."
        )
    )
    parser.add_argument("--rubric", required=True, type=Path, help="Local rubric JSON")
    parser.add_argument(
        "--ratings", required=True, type=Path, help="Local ratings CSV"
    )
    parser.add_argument("--output", type=Path, help="Optional local JSON report")
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing output JSON file"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        rubric = _common.read_json(args.rubric)
        _common.require_valid(_common.validate_rubric(rubric))
        report = summarize(rubric, read_rows(args.ratings, rubric))
        _common.write_json(report, args.output, force=args.force)
        return 0
    except _common.ValidationError as error:
        _common.write_json(_common.failure_report(error), None)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
