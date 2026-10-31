#!/usr/bin/env python3
"""Stress-test rubric weights and report scholarly-work order instability."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path
from typing import Any

import _common


def _normalized(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {criterion_id: weight / total for criterion_id, weight in weights.items()}


def _scenarios(
    base_weights: dict[str, float], delta: float
) -> list[tuple[str, str | None, float, dict[str, float]]]:
    scenarios = [("base", None, 1.0, dict(base_weights))]
    for criterion_id in sorted(base_weights):
        for label, multiplier in (("decrease", 1.0 - delta), ("increase", 1.0 + delta)):
            changed = dict(base_weights)
            changed[criterion_id] *= multiplier
            scenarios.append(
                (
                    f"{criterion_id}:{label}",
                    criterion_id,
                    multiplier,
                    _normalized(changed),
                )
            )
    return scenarios


def _direction(first: float | None, second: float | None) -> int | None:
    if first is None or second is None:
        return None
    difference = first - second
    if abs(difference) <= 1e-9:
        return 0
    return 1 if difference > 0 else -1


def analyze(
    rubric: dict[str, Any],
    evaluations: list[dict[str, Any]],
    delta: float,
) -> dict[str, Any]:
    rubric_issues = _common.validate_rubric(rubric)
    _common.require_valid(rubric_issues)
    if not 2 <= len(evaluations) <= _common.MAX_EVALUATIONS:
        raise _common.ValidationError("EVALUATION_COUNT_INVALID")
    work_ids: set[str] = set()
    evaluation_ids: set[str] = set()
    for index, evaluation in enumerate(evaluations):
        issues = _common.validate_evaluation(evaluation, rubric)
        _common.require_valid(issues)
        if evaluation["work_id"] in work_ids:
            raise _common.ValidationError(
                "WORK_ID_DUPLICATE", f"$.evaluations[{index}].work_id"
            )
        if evaluation["evaluation_id"] in evaluation_ids:
            raise _common.ValidationError(
                "EVALUATION_ID_DUPLICATE", f"$.evaluations[{index}].evaluation_id"
            )
        work_ids.add(evaluation["work_id"])
        evaluation_ids.add(evaluation["evaluation_id"])
    if not _common.is_number(delta) or not 0 < delta <= 0.5:
        raise _common.ValidationError("DELTA_OUT_OF_RANGE")

    base_weights = _common.weights_by_criterion(rubric)
    scenario_output: list[dict[str, Any]] = []
    score_ranges = {
        work_id: {"minimum": None, "maximum": None} for work_id in sorted(work_ids)
    }
    base_scores: dict[str, float | None] = {}
    pair_changes: set[tuple[str, str]] = set()
    pairs = list(itertools.combinations(sorted(work_ids), 2))
    incomplete_work_ids: set[str] = set()

    for scenario_index, (
        scenario_id,
        criterion_id,
        multiplier,
        weights,
    ) in enumerate(_scenarios(base_weights, delta)):
        item_scores: list[dict[str, Any]] = []
        score_lookup: dict[str, float | None] = {}
        for evaluation in evaluations:
            score_report = _common.score_evaluation(
                rubric, evaluation, weights=weights, round_output=False
            )
            score = score_report["aggregates"]["normalized_score"]
            coverage = score_report["aggregates"]["coverage_of_applicable_weight"]
            if score is None:
                raise _common.ValidationError(
                    "SENSITIVITY_SCORE_UNAVAILABLE", "$.evaluations"
                )
            if coverage is None or coverage < 1:
                incomplete_work_ids.add(evaluation["work_id"])
            score_lookup[evaluation["work_id"]] = score
            current_range = score_ranges[evaluation["work_id"]]
            current_range["minimum"] = (
                score
                if current_range["minimum"] is None
                else min(current_range["minimum"], score)
            )
            current_range["maximum"] = (
                score
                if current_range["maximum"] is None
                else max(current_range["maximum"], score)
            )
            item_scores.append(
                {
                    "work_id": evaluation["work_id"],
                    "normalized_score": _common.rounded(score),
                    "coverage_of_applicable_weight": _common.rounded(coverage),
                }
            )
        if scenario_index == 0:
            base_scores = score_lookup
        else:
            for first, second in pairs:
                if _direction(base_scores[first], base_scores[second]) != _direction(
                    score_lookup[first], score_lookup[second]
                ):
                    pair_changes.add((first, second))
        scenario_output.append(
            {
                "scenario_id": scenario_id,
                "perturbed_criterion_id": criterion_id,
                "weight_multiplier": multiplier,
                "weights": {
                    key: value
                    for key, value in sorted(weights.items())
                },
                "item_scores": sorted(item_scores, key=lambda item: item["work_id"]),
            }
        )

    base_order = [
        work_id
        for work_id, _ in sorted(
            base_scores.items(),
            key=lambda item: (
                -(item[1] if item[1] is not None else float("-inf")),
                item[0],
            ),
        )
    ]
    range_output = [
        {
            "work_id": work_id,
            "minimum_score": _common.rounded(bounds["minimum"]),
            "maximum_score": _common.rounded(bounds["maximum"]),
            "range_width": _common.rounded(
                bounds["maximum"] - bounds["minimum"]
                if bounds["minimum"] is not None and bounds["maximum"] is not None
                else None
            ),
        }
        for work_id, bounds in sorted(score_ranges.items())
    ]
    warnings: list[str] = []
    if incomplete_work_ids:
        warnings.append("INCOMPLETE_COVERAGE_LIMITS_COMPARABILITY")
    if pair_changes:
        warnings.append("ORDINAL_ORDER_CHANGES_UNDER_WEIGHT_PERTURBATION")
    status_patterns = {
        tuple(sorted((rating["criterion_id"], rating["status"]) for rating in evaluation["ratings"]))
        for evaluation in evaluations
    }
    if len(status_patterns) > 1:
        warnings.append("DIFFERENT_CRITERION_STATUS_PATTERNS_LIMIT_COMPARABILITY")
    return {
        "schema_version": _common.SCHEMA_VERSION,
        "report_type": "weight_sensitivity_and_rank_instability",
        "notice": _common.NOTICE,
        "rubric_id": rubric["rubric_id"],
        "evaluation_records": [
            {"evaluation_id": evaluation["evaluation_id"], "work_id": evaluation["work_id"]}
            for evaluation in sorted(evaluations, key=lambda item: item["work_id"])
        ],
        "purpose": _common.ALLOWED_PURPOSE,
        "unit_of_assessment": _common.ALLOWED_UNIT,
        "delta": delta,
        "perturbation_method": (
            "multiply one criterion weight by 1-delta and 1+delta, then "
            "renormalize all weights to sum to one"
        ),
        "scenario_count": len(scenario_output),
        "base_ordinal_order": base_order,
        "base_tied_work_pairs": [
            {"first_work_id": first, "second_work_id": second}
            for first, second in pairs
            if _direction(base_scores[first], base_scores[second]) == 0
        ],
        "order_comparison_absolute_tolerance": 1e-9,
        "order_comparison_uses_unrounded_scores": True,
        "base_order_is_a_decision_recommendation": False,
        "rank_instability_detected": bool(pair_changes),
        "changed_pair_count": len(pair_changes),
        "total_pair_count": len(pairs),
        "changed_work_pairs": [
            {"first_work_id": first, "second_work_id": second}
            for first, second in sorted(pair_changes)
        ],
        "incomplete_coverage_work_ids": sorted(incomplete_work_ids),
        "score_ranges": range_output,
        "scenarios": scenario_output,
        "warnings": warnings,
        "limitations": [
            "This is a deterministic local stress test, not a validity study.",
            "Ordinal order must not be used to rank people or make high-impact decisions.",
            "Results depend on the submitted rubric, ratings, missingness, and perturbation size.",
            "Linear list positions do not order tied pairs.",
            "Different rated/applicable criterion sets do not establish comparable constructs.",
        ],
        "decision_recommendation_provided": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Perturb rubric weights and report score ranges and ordinal-order "
            "changes for scholarly works only. Never use this output to rank people."
        )
    )
    parser.add_argument("--rubric", required=True, type=Path, help="Local rubric JSON")
    parser.add_argument(
        "--evaluation",
        required=True,
        type=Path,
        action="append",
        help="Local evaluation JSON; repeat for 2 to 50 distinct scholarly works",
    )
    parser.add_argument(
        "--delta",
        type=float,
        default=0.2,
        help="Relative one-at-a-time weight change in (0, 0.5] (default: 0.2)",
    )
    parser.add_argument("--output", type=Path, help="Optional local JSON report")
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing output JSON file"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = analyze(
            _common.read_json(args.rubric),
            [_common.read_json(path) for path in args.evaluation],
            args.delta,
        )
        _common.write_json(report, args.output, force=args.force)
        return 0
    except _common.ValidationError as error:
        _common.write_json(_common.failure_report(error), None)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
