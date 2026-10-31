#!/usr/bin/env python3
"""Validate an estimand-led survival-analysis plan without reading subject rows."""

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
    validate_references,
    write_json,
)

ALLOWED_METHODS = {
    "kaplan_meier",
    "cox_proportional_hazards",
    "flexible_parametric",
    "restricted_mean_survival_time",
    "accelerated_failure_time",
    "cumulative_incidence",
    "cause_specific_hazard",
    "fine_gray",
    "multi_state",
    "other_justified",
}
COMPETING_METHODS = {
    "cumulative_incidence",
    "cause_specific_hazard",
    "fine_gray",
    "multi_state",
    "other_justified",
}


def validate_plan(document: dict[str, Any]) -> IssueLog:
    log = IssueLog()
    try:
        require_nonempty_text(document.get("schema_version"), "schema_version")
        known_sources = source_ids(document)

        metadata = document.get("metadata")
        if not isinstance(metadata, dict):
            raise InputError("metadata must be an object")
        for field in ("plan_id", "title", "version", "status", "purpose", "data_cut_date"):
            require_nonempty_text(metadata.get(field), f"metadata.{field}")
        if not isinstance(metadata.get("data_level"), str) or metadata.get("data_level") not in {"aggregate", "synthetic", "plan_only"}:
            log.errors.append("metadata.data_level must be aggregate, synthetic, or plan_only")
        if metadata.get("raw_rows_supplied") is not False:
            log.errors.append("metadata.raw_rows_supplied must be false")
        if metadata.get("patient_care_use") is not False:
            log.errors.append("metadata.patient_care_use must be false")
        if metadata.get("human_review_required") is not True:
            log.errors.append("metadata.human_review_required must be true")

        estimand = document.get("estimand")
        if not isinstance(estimand, dict):
            raise InputError("estimand must be an object")
        for field in (
            "population",
            "condition_or_comparison",
            "endpoint_variable",
            "population_summary",
            "time_horizon",
            "rationale",
        ):
            require_nonempty_text(estimand.get(field), f"estimand.{field}")
        intercurrent = require_list(
            estimand.get("intercurrent_events"),
            "estimand.intercurrent_events",
            maximum=30,
        )
        if not intercurrent:
            log.errors.append(
                "estimand.intercurrent_events must document events or explicitly state none"
            )
        for index, item in enumerate(intercurrent):
            if not isinstance(item, dict):
                raise InputError(f"estimand.intercurrent_events[{index}] must be an object")
            require_nonempty_text(
                item.get("event"), f"estimand.intercurrent_events[{index}].event"
            )
            require_nonempty_text(
                item.get("strategy"), f"estimand.intercurrent_events[{index}].strategy"
            )
            require_nonempty_text(
                item.get("rationale"), f"estimand.intercurrent_events[{index}].rationale"
            )

        endpoint = document.get("endpoint")
        if not isinstance(endpoint, dict):
            raise InputError("endpoint must be an object")
        for field in (
            "time_zero",
            "event_definition",
            "time_scale",
            "ascertainment",
            "follow_up_end",
            "delayed_entry",
            "same_time_rules",
        ):
            require_nonempty_text(endpoint.get(field), f"endpoint.{field}")
        censoring = require_list(
            endpoint.get("censoring_rules"), "endpoint.censoring_rules", maximum=30
        )
        if not censoring:
            log.errors.append("At least one censoring rule is required")
        for index, rule in enumerate(censoring):
            require_nonempty_text(rule, f"endpoint.censoring_rules[{index}]")
        competing = require_list(
            endpoint.get("competing_events"), "endpoint.competing_events", maximum=20
        )
        for index, event in enumerate(competing):
            require_nonempty_text(event, f"endpoint.competing_events[{index}]")

        analysis = document.get("analysis")
        if not isinstance(analysis, dict):
            raise InputError("analysis must be an object")
        primary_method = require_nonempty_text(
            analysis.get("primary_method"), "analysis.primary_method"
        )
        if primary_method not in ALLOWED_METHODS:
            log.errors.append(f"Unsupported analysis.primary_method: {primary_method}")
        for field in (
            "effect_measure",
            "analysis_population",
            "covariate_strategy",
            "missing_data",
            "multiplicity",
            "uncertainty",
            "software_and_version",
            "model_diagnostics",
        ):
            require_nonempty_text(analysis.get(field), f"analysis.{field}")

        ph_assessment = require_nonempty_text(
            analysis.get("proportional_hazards_assessment"),
            "analysis.proportional_hazards_assessment",
        )
        non_ph_strategy = require_nonempty_text(
            analysis.get("non_proportional_hazards_strategy"),
            "analysis.non_proportional_hazards_strategy",
        )
        effect_measure = str(analysis.get("effect_measure", "")).lower()
        if (
            primary_method == "cox_proportional_hazards"
            or "hazard ratio" in effect_measure
        ):
            if ph_assessment.lower() in {"none", "not applicable", "n/a"}:
                log.errors.append(
                    "A proportional-hazards assessment is required for a hazard-ratio plan"
                )
            if non_ph_strategy.lower() in {"none", "not applicable", "n/a"}:
                log.errors.append(
                    "Pre-specify an alternative if proportional hazards is not supported"
                )

        competing_method = require_nonempty_text(
            analysis.get("competing_risk_method"),
            "analysis.competing_risk_method",
        )
        if competing:
            if competing_method not in COMPETING_METHODS:
                log.errors.append(
                    "A competing-risk method is required when competing events are listed"
                )
            if (
                primary_method == "kaplan_meier"
                and "absolute" in effect_measure
            ):
                log.errors.append(
                    "Kaplan-Meier with competing events cannot be the sole absolute-incidence method"
                )
        elif competing_method not in {"not_applicable", "none"}:
            log.warnings.append(
                "A competing-risk method is named but no competing events are listed"
            )

        bias = document.get("bias_controls")
        if not isinstance(bias, dict):
            raise InputError("bias_controls must be an object")
        for field in (
            "informative_censoring",
            "immortal_time",
            "time_dependent_confounding",
            "outcome_misclassification",
            "informative_visits",
        ):
            require_nonempty_text(bias.get(field), f"bias_controls.{field}")

        sensitivity = require_list(
            document.get("sensitivity_analyses"),
            "sensitivity_analyses",
            maximum=30,
        )
        if len(sensitivity) < 2:
            log.warnings.append("Fewer than two sensitivity analyses are specified")
        for index, item in enumerate(sensitivity):
            require_nonempty_text(item, f"sensitivity_analyses[{index}]")

        subgroups = document.get("subgroups")
        if not isinstance(subgroups, dict):
            raise InputError("subgroups must be an object")
        for field in (
            "prespecification",
            "interaction_testing",
            "multiplicity",
            "precision_and_disclosure",
        ):
            require_nonempty_text(subgroups.get(field), f"subgroups.{field}")

        validation = document.get("validation")
        if not isinstance(validation, dict):
            raise InputError("validation must be an object")
        for field in (
            "internal_validation",
            "external_validation",
            "calibration",
            "subgroup_performance",
        ):
            require_nonempty_text(validation.get(field), f"validation.{field}")
        if "not performed" in str(validation.get("external_validation")).lower():
            log.warnings.append("External validation is documented as not performed")

        review = document.get("human_review")
        if not isinstance(review, dict):
            raise InputError("human_review must be an object")
        roles = require_list(review.get("roles"), "human_review.roles", maximum=20)
        if not roles:
            log.errors.append("At least one human-review role is required")
        for index, role in enumerate(roles):
            require_nonempty_text(role, f"human_review.roles[{index}]")
        require_nonempty_text(review.get("approval_boundary"), "human_review.approval_boundary")
        if review.get("completed") is not True:
            log.warnings.append("Human review is not recorded as complete")

        governance = document.get("governance")
        if not isinstance(governance, dict):
            raise InputError("governance must be an object")
        for field in (
            "owner",
            "change_control",
            "auditability",
            "monitoring",
            "retirement",
        ):
            require_nonempty_text(governance.get(field), f"governance.{field}")

        validate_references(document.get("source_ids"), known_sources, "source_ids")
    except InputError as exc:
        log.errors.append(str(exc))

    if log.ok:
        log.info.append("Survival plan contains the required estimand and analysis fields")
    return log


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a local survival-analysis plan. No subject-level data are read "
            "and no survival model is fitted."
        )
    )
    parser.add_argument("input", help="Local plan JSON")
    parser.add_argument("-o", "--output", help="Optional local JSON report")
    parser.add_argument(
        "--strict", action="store_true", help="Return failure when warnings are present"
    )
    args = parser.parse_args()

    try:
        document = load_json_object(args.input)
        report = validate_plan(document).as_dict()
        if args.output:
            write_json(args.output, report)
        print_report(report)
    except InputError as exc:
        print_report(IssueLog(errors=[str(exc)]).as_dict())
        return 2
    if report["status"] != "pass" or (args.strict and report["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
