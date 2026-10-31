#!/usr/bin/env python3
"""Check a human-authored GRADE evidence profile without assigning grades."""

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

DOMAINS = (
    "risk_of_bias",
    "inconsistency",
    "indirectness",
    "imprecision",
    "publication_bias",
)
DOMAIN_JUDGMENTS = {"not_serious", "serious", "very_serious", "unassessed"}
UPGRADING = ("large_effect", "dose_response", "residual_confounding")
UPGRADING_JUDGMENTS = {"none", "present", "unassessed", "not_applicable"}
CERTAINTY_LEVELS = {"high", "moderate", "low", "very_low", "unassessed"}
PLACEHOLDER_MARKERS = ("REPLACE_", "REQUIRES_", "YYYY-MM-DD")


def _profile_has_recommendation_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).strip().lower() in {
                "recommendation",
                "recommendation_strength",
                "treatment_recommendation",
            }:
                return True
            if _profile_has_recommendation_key(nested):
                return True
    elif isinstance(value, list):
        return any(_profile_has_recommendation_key(item) for item in value)
    return False


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


def check_profile(document: dict[str, Any]) -> tuple[IssueLog, list[dict[str, str]]]:
    log = IssueLog()
    summaries: list[dict[str, str]] = []
    try:
        require_nonempty_text(document.get("schema_version"), "schema_version")
        require_nonempty_text(document.get("profile_id"), "profile_id")
        require_nonempty_text(document.get("title"), "title")
        if not isinstance(document.get("data_level"), str) or document.get("data_level") not in {"published_aggregate_evidence", "synthetic"}:
            log.errors.append(
                "data_level must be published_aggregate_evidence or synthetic"
            )
        if document.get("human_judgments_required") is not True:
            log.errors.append("human_judgments_required must be true")
        if document.get("auto_grade") is not False:
            log.errors.append("auto_grade must be false")
        if _profile_has_recommendation_key(document):
            log.errors.append(
                "Recommendation fields are outside the evidence-profile checker"
            )
        governance = document.get("governance")
        if not isinstance(governance, dict):
            raise InputError("governance must be an object")
        for field in (
            "version",
            "owner",
            "change_summary",
            "auditability",
            "update_plan",
        ):
            require_nonempty_text(governance.get(field), f"governance.{field}")

        question = document.get("question")
        if not isinstance(question, dict):
            raise InputError("question must be an object")
        for field in ("population", "intervention_or_exposure", "comparator", "setting"):
            require_nonempty_text(question.get(field), f"question.{field}")

        known_sources = source_ids(document)
        outcomes = require_list(document.get("outcomes"), "outcomes", maximum=50)
        if not outcomes:
            log.errors.append("At least one outcome is required")

        names: set[str] = set()
        for index, outcome in enumerate(outcomes):
            prefix = f"outcomes[{index}]"
            if not isinstance(outcome, dict):
                raise InputError(f"{prefix} must be an object")
            name = require_nonempty_text(outcome.get("name"), f"{prefix}.name")
            if name in names:
                log.errors.append(f"Duplicate outcome name: {name}")
            names.add(name)
            importance = require_nonempty_text(
                outcome.get("importance"), f"{prefix}.importance"
            )
            if importance not in {"critical", "important", "not_important"}:
                log.errors.append(f"{prefix}.importance has an unsupported value")
            for field in (
                "effect_measure",
                "effect_estimate",
                "uncertainty_interval",
                "participants",
                "studies",
                "time_horizon",
            ):
                require_nonempty_text(outcome.get(field), f"{prefix}.{field}")

            domains = outcome.get("domains")
            if not isinstance(domains, dict):
                raise InputError(f"{prefix}.domains must be an object")
            for domain_name in DOMAINS:
                domain = domains.get(domain_name)
                field = f"{prefix}.domains.{domain_name}"
                if not isinstance(domain, dict):
                    raise InputError(f"{field} must be an object")
                judgment = require_nonempty_text(
                    domain.get("judgment"), f"{field}.judgment"
                )
                allowed_judgments = DOMAIN_JUDGMENTS
                if domain_name == "imprecision":
                    # Current GRADE Book permits a human three-level downgrade.
                    allowed_judgments = DOMAIN_JUDGMENTS | {"extremely_serious"}
                if judgment not in allowed_judgments:
                    log.errors.append(f"{field}.judgment is unsupported")
                if judgment == "unassessed":
                    log.errors.append(f"{field} requires a human judgment")
                require_nonempty_text(domain.get("rationale"), f"{field}.rationale")
                require_nonempty_text(
                    domain.get("reviewer_role"), f"{field}.reviewer_role"
                )
                validate_references(
                    domain.get("source_ids"), known_sources, f"{field}.source_ids"
                )

            upgrading = outcome.get("upgrading")
            if not isinstance(upgrading, dict):
                raise InputError(f"{prefix}.upgrading must be an object")
            for item_name in UPGRADING:
                item = upgrading.get(item_name)
                field = f"{prefix}.upgrading.{item_name}"
                if not isinstance(item, dict):
                    raise InputError(f"{field} must be an object")
                judgment = require_nonempty_text(
                    item.get("judgment"), f"{field}.judgment"
                )
                if judgment not in UPGRADING_JUDGMENTS:
                    log.errors.append(f"{field}.judgment is unsupported")
                if judgment == "unassessed":
                    log.errors.append(f"{field} requires a human judgment")
                require_nonempty_text(item.get("rationale"), f"{field}.rationale")
                if judgment == "present":
                    validate_references(
                        item.get("source_ids"), known_sources, f"{field}.source_ids"
                    )

            certainty = outcome.get("certainty")
            if not isinstance(certainty, dict):
                raise InputError(f"{prefix}.certainty must be an object")
            if certainty.get("human_judgment") is not True:
                log.errors.append(f"{prefix}.certainty.human_judgment must be true")
            level = require_nonempty_text(
                certainty.get("level"), f"{prefix}.certainty.level"
            )
            if level not in CERTAINTY_LEVELS:
                log.errors.append(f"{prefix}.certainty.level is unsupported")
            if level == "unassessed":
                log.errors.append(f"{prefix}.certainty requires a human judgment")
            require_nonempty_text(
                certainty.get("rationale"), f"{prefix}.certainty.rationale"
            )
            require_nonempty_text(
                certainty.get("reviewer_role"), f"{prefix}.certainty.reviewer_role"
            )
            require_nonempty_text(
                certainty.get("judgment_date"), f"{prefix}.certainty.judgment_date"
            )
            validate_references(
                certainty.get("source_ids"),
                known_sources,
                f"{prefix}.certainty.source_ids",
            )
            summaries.append(
                {
                    "outcome": name,
                    "importance": importance,
                    "human_entered_certainty": level,
                }
            )

        review = document.get("profile_review")
        if not isinstance(review, dict):
            raise InputError("profile_review must be an object")
        for field in ("prepared_by_role", "reviewed_by_role", "review_date"):
            require_nonempty_text(review.get(field), f"profile_review.{field}")
        if review.get("completed") is not True:
            log.errors.append("profile_review.completed must be true")
        placeholders = _find_placeholders(document)
        if placeholders:
            log.errors.append(
                "Unresolved template placeholders remain: "
                + ", ".join(placeholders[:10])
            )
    except InputError as exc:
        log.errors.append(str(exc))

    if log.ok:
        log.info.append(
            "Profile is structurally complete; all certainty labels remain human judgments"
        )
    return log, summaries


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check completeness and citation traceability of a human-authored "
            "GRADE evidence profile. This tool never assigns certainty."
        )
    )
    parser.add_argument("input", help="Local evidence-profile JSON")
    parser.add_argument("-o", "--output", help="Optional local JSON report")
    args = parser.parse_args()

    try:
        document = load_json_object(args.input)
        log, summaries = check_profile(document)
        report = log.as_dict()
        report["outcomes"] = summaries
        report["auto_grade_performed"] = False
        if args.output:
            write_json(args.output, report)
        print_report(report)
    except InputError as exc:
        print_report(IssueLog(errors=[str(exc)]).as_dict())
        return 2
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
