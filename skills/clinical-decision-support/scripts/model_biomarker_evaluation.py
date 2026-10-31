#!/usr/bin/env python3
"""Create a bounded report from aggregate model/biomarker validation counts."""

from __future__ import annotations

import argparse
import math
import sys
from typing import Any

from _common import (
    InputError,
    IssueLog,
    finite_number,
    load_json_object,
    nonnegative_int,
    print_report,
    require_list,
    require_nonempty_text,
    source_ids,
    write_json,
)

MAX_GROUPS = 12
MAX_BINS = 30
MAX_GROUP_N = 10_000_000


def _wilson(successes: int, total: int) -> dict[str, Any]:
    if total <= 0:
        return {"estimate": None, "ci95": [None, None]}
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1.0 + (z * z / total)
    center = (proportion + z * z / (2.0 * total)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return {
        "estimate": round(proportion, 6),
        "ci95": [round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)],
    }


def _small_nonzero(values: list[int], minimum: int) -> bool:
    return any(0 < value < minimum for value in values)


def _metric(successes: int, total: int) -> dict[str, Any]:
    return _wilson(successes, total)


def _calibration_summary(
    bins: list[Any], group_name: str, minimum: int, expected_events: int,
    expected_n: int,
) -> tuple[dict[str, Any], bool]:
    total = 0
    events = 0
    weighted_predicted = 0.0
    weighted_absolute_gap = 0.0
    sensitive = False
    for index, entry in enumerate(bins):
        field = f"groups[{group_name}].calibration_bins[{index}]"
        if not isinstance(entry, dict):
            raise InputError(f"{field} must be an object")
        count = nonnegative_int(entry.get("n"), f"{field}.n")
        observed = nonnegative_int(
            entry.get("observed_events"), f"{field}.observed_events"
        )
        predicted = finite_number(
            entry.get("mean_predicted_probability"),
            f"{field}.mean_predicted_probability",
        )
        if count == 0 or observed > count:
            raise InputError(f"{field} has inconsistent counts")
        if not 0.0 <= predicted <= 1.0:
            raise InputError(f"{field}.mean_predicted_probability must be in [0, 1]")
        observed_rate = observed / count
        total += count
        events += observed
        weighted_predicted += count * predicted
        weighted_absolute_gap += count * abs(predicted - observed_rate)
        sensitive = sensitive or _small_nonzero(
            [count, observed, count - observed], minimum
        )
    if events != expected_events:
        raise InputError(
            f"Calibration observed events for {group_name} do not match confusion counts"
        )
    if total == 0:
        raise InputError(f"Calibration bins for {group_name} are empty")
    if total != expected_n:
        raise InputError(f"Calibration bins for {group_name} must sum to group n")
    if sensitive:
        return (
            {
                "suppressed": True,
                "reason": "One or more calibration cells are below the disclosure threshold",
            },
            True,
        )
    observed_rate = events / total
    mean_predicted = weighted_predicted / total
    return (
        {
            "suppressed": False,
            "n": total,
            "observed_rate": round(observed_rate, 6),
            "mean_predicted_probability": round(mean_predicted, 6),
            "calibration_in_the_large_gap": round(mean_predicted - observed_rate, 6),
            "weighted_absolute_calibration_gap": round(
                weighted_absolute_gap / total, 6
            ),
            "limitations": (
                "Aggregate-bin calibration is approximate and cannot estimate a "
                "calibration slope or replace individual-level validation."
            ),
        },
        False,
    )


def evaluate(
    document: dict[str, Any], minimum: int
) -> tuple[IssueLog, dict[str, Any]]:
    log = IssueLog()
    report: dict[str, Any] = {
        "report_type": "aggregate_model_biomarker_evaluation",
        "individual_output_generated": False,
        "clinical_classification_generated": False,
        "recommendation_generated": False,
        "groups": [],
        "subgroup_performance_differences": {},
    }
    metric_values: dict[str, list[tuple[str, float]]] = {}

    try:
        require_nonempty_text(document.get("schema_version"), "schema_version")
        known_sources = source_ids(document)
        metadata = document.get("metadata")
        if not isinstance(metadata, dict):
            raise InputError("metadata must be an object")
        for field in (
            "evaluation_id",
            "title",
            "evaluation_target",
            "target_version",
            "purpose",
            "population",
            "setting",
            "outcome",
            "outcome_horizon",
            "threshold",
            "threshold_source_id",
            "validation_dataset",
            "data_cut_date",
        ):
            require_nonempty_text(metadata.get(field), f"metadata.{field}")
        if not isinstance(metadata.get("data_level"), str) or metadata.get("data_level") not in {"aggregate", "synthetic"}:
            log.errors.append("metadata.data_level must be aggregate or synthetic")
        if metadata.get("person_level_output") is not False:
            log.errors.append("metadata.person_level_output must be false")
        if metadata.get("threshold_pre_specified") is not True:
            log.errors.append("metadata.threshold_pre_specified must be true")
        if metadata.get("threshold_source_id") not in known_sources:
            log.errors.append("metadata.threshold_source_id must reference sources")
        if metadata.get("external_validation") is not True:
            log.warnings.append("Independent external validation is not documented")
        if metadata.get("human_review_required") is not True:
            log.errors.append("metadata.human_review_required must be true")

        review = document.get("human_review")
        if not isinstance(review, dict):
            raise InputError("human_review must be an object")
        if review.get("required") is not True:
            log.errors.append("human_review.required must be true")
        roles = require_list(review.get("roles"), "human_review.roles", maximum=20)
        if not roles:
            log.errors.append("At least one human-review role is required")
        for index, role in enumerate(roles):
            require_nonempty_text(role, f"human_review.roles[{index}]")
        if review.get("completed") is not True:
            log.warnings.append("Human review is not recorded as complete")

        governance = document.get("governance")
        if not isinstance(governance, dict):
            raise InputError("governance must be an object")
        for field in (
            "owner",
            "version_and_change_control",
            "monitoring",
            "auditability",
            "human_factors",
            "rollback_and_retirement",
        ):
            require_nonempty_text(governance.get(field), f"governance.{field}")

        if not log.ok:
            raise InputError("Evaluation stopped before processing aggregate counts")

        groups = require_list(document.get("groups"), "groups", maximum=MAX_GROUPS)
        if not groups:
            raise InputError("At least one aggregate group is required")
        names: set[str] = set()
        for index, group in enumerate(groups):
            field = f"groups[{index}]"
            if not isinstance(group, dict):
                raise InputError(f"{field} must be an object")
            name = require_nonempty_text(group.get("name"), f"{field}.name", max_length=100)
            if name in names:
                raise InputError(f"Duplicate group name: {name}")
            names.add(name)
            n = nonnegative_int(group.get("n"), f"{field}.n")
            if n == 0 or n > MAX_GROUP_N:
                raise InputError(f"{field}.n must be between 1 and {MAX_GROUP_N}")
            confusion = group.get("confusion")
            if not isinstance(confusion, dict):
                raise InputError(f"{field}.confusion must be an object")
            tp = nonnegative_int(confusion.get("tp"), f"{field}.confusion.tp")
            fp = nonnegative_int(confusion.get("fp"), f"{field}.confusion.fp")
            tn = nonnegative_int(confusion.get("tn"), f"{field}.confusion.tn")
            fn = nonnegative_int(confusion.get("fn"), f"{field}.confusion.fn")
            cells = [tp, fp, tn, fn]
            if sum(cells) != n:
                raise InputError(f"{field}.confusion counts must sum to n")

            group_result: dict[str, Any] = {"name": name}
            if n < minimum or _small_nonzero(cells, minimum):
                group_result.update(
                    {
                        "suppressed": True,
                        "reason": (
                            "Group or contributing confusion cell is below the "
                            "disclosure threshold"
                        ),
                    }
                )
            else:
                metrics = {
                    "sensitivity": _metric(tp, tp + fn),
                    "specificity": _metric(tn, tn + fp),
                    "positive_predictive_value": _metric(tp, tp + fp),
                    "negative_predictive_value": _metric(tn, tn + fn),
                    "accuracy": _metric(tp + tn, n),
                    "prevalence": _metric(tp + fn, n),
                }
                sensitivity = metrics["sensitivity"]["estimate"]
                specificity = metrics["specificity"]["estimate"]
                metrics["balanced_accuracy"] = {
                    "estimate": (
                        round((sensitivity + specificity) / 2.0, 6)
                        if sensitivity is not None and specificity is not None
                        else None
                    ),
                    "ci95": None,
                }
                if sensitivity is None or specificity is None:
                    log.warnings.append(
                        f"Group {name} lacks one observed outcome class; balanced "
                        "accuracy and the corresponding class metric are undefined"
                    )
                group_result.update(
                    {"suppressed": False, "n": n, "metrics": metrics}
                )
                for metric_name, metric in metrics.items():
                    estimate = metric.get("estimate")
                    if estimate is not None:
                        metric_values.setdefault(metric_name, []).append(
                            (name, float(estimate))
                        )

            bins = require_list(
                group.get("calibration_bins"),
                f"{field}.calibration_bins",
                maximum=MAX_BINS,
            )
            calibration, _ = _calibration_summary(
                bins, name, minimum, expected_events=tp + fn, expected_n=n
            )
            group_result["calibration"] = calibration
            report["groups"].append(group_result)

        for metric_name, values in metric_values.items():
            if len(values) < 2:
                continue
            estimates = [value for _, value in values]
            low_name, low = min(values, key=lambda item: item[1])
            high_name, high = max(values, key=lambda item: item[1])
            report["subgroup_performance_differences"][metric_name] = {
                "maximum_absolute_difference": round(high - low, 6),
                "lowest_group": low_name,
                "highest_group": high_name,
                "interpretation": (
                    "Descriptive difference only; it is not a fairness judgment "
                    "and may reflect case mix, measurement, sampling, or model behavior."
                ),
            }
        if len(groups) < 2:
            log.warnings.append("Only one group supplied; subgroup comparisons are unavailable")
        if not report["subgroup_performance_differences"]:
            log.warnings.append(
                "Subgroup differences were not estimable after disclosure suppression"
            )
    except InputError as exc:
        log.errors.append(str(exc))

    if not log.ok:
        report["groups"] = []
        report["subgroup_performance_differences"] = {}

    report["disclosure_threshold"] = minimum
    report["limitations"] = [
        "Input is aggregate and cannot support person-level output.",
        "Metrics do not establish clinical validity, clinical utility, safety, or fairness.",
        "Wilson intervals do not account for clustering, repeated observations, censoring, or verification bias.",
        "Calibration bins are lossy summaries and cannot estimate calibration slope.",
    ]
    if log.ok:
        log.info.append("Aggregate evaluation completed without person-level output")
    return log, report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report bounded descriptive performance from local aggregate counts. "
            "Never emits a person-level class or clinical recommendation."
        )
    )
    parser.add_argument("input", help="Local aggregate JSON")
    parser.add_argument("-o", "--output", help="Optional local JSON report")
    parser.add_argument(
        "--min-cell-size",
        type=int,
        default=11,
        help="Suppress contributing nonzero cells below this value (default: 11)",
    )
    args = parser.parse_args()
    if not 2 <= args.min_cell_size <= 1_000:
        parser.error("--min-cell-size must be between 2 and 1000")

    try:
        document = load_json_object(args.input)
        log, details = evaluate(document, args.min_cell_size)
        result = log.as_dict()
        result["evaluation"] = details
        if args.output:
            write_json(args.output, result)
        print_report(result)
    except InputError as exc:
        print_report(IssueLog(errors=[str(exc)]).as_dict())
        return 2
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
