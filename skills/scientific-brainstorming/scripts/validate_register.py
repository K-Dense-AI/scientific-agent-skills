"""Validate brainstorming idea and assumption registers structurally."""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from _common import (
    MAX_ITEMS,
    CliError,
    emit_json,
    read_json,
    require_identifier,
    require_iso_date,
    require_text,
)

ORIGINS = {"human", "ai-assisted", "literature-inspired", "mixed", "other"}
RECORDED_STAGES = {"independent", "discussion", "post-check"}
EVIDENCE_STATUSES = {
    "not-checked",
    "search-incomplete",
    "support-located",
    "challenge-located",
    "mixed",
    "no-direct-evidence-located",
}
IDEA_STATUSES = {
    "candidate",
    "revised",
    "deferred",
    "paused",
    "stopped",
    "advanced-to-review",
}
ASSUMPTION_CATEGORIES = {
    "causal",
    "mechanistic",
    "measurement",
    "sampling",
    "operational",
    "statistical",
    "feasibility",
    "ethical",
    "value",
    "other",
}
ASSUMPTION_STATUSES = {
    "untested",
    "partially-supported",
    "challenged",
    "refuted",
    "not-applicable",
}


def _issue(path: str, message: str) -> dict[str, str]:
    return {"path": path, "message": message}


def _normalized_statement(value: str) -> str:
    """Normalize only exact text features; this is not semantic matching."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def _list_field(
    record: dict[str, Any],
    field: str,
    path: str,
    errors: list[dict[str, str]],
    *,
    required: bool = True,
) -> list[Any]:
    value = record.get(field)
    if value is None and not required:
        return []
    if not isinstance(value, list):
        errors.append(_issue(f"{path}.{field}", "must be a list"))
        return []
    if len(value) > MAX_ITEMS:
        errors.append(
            _issue(
                f"{path}.{field}",
                f"has {len(value)} items; limit is {MAX_ITEMS}",
            )
        )
        return value[:MAX_ITEMS]
    return value


def _check_text(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
    *,
    maximum: int = 10_000,
    allow_empty: bool = False,
) -> str | None:
    try:
        return require_text(
            value,
            path,
            maximum=maximum,
            allow_empty=allow_empty,
        )
    except CliError as exc:
        errors.append(_issue(path, str(exc)))
        return None


def _check_id(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
) -> str | None:
    try:
        return require_identifier(value, path)
    except CliError as exc:
        errors.append(_issue(path, str(exc)))
        return None


def _check_string_list(
    values: list[Any],
    path: str,
    errors: list[dict[str, str]],
    *,
    identifiers: bool = False,
) -> list[str]:
    result: list[str] = []
    for index, value in enumerate(values):
        item_path = f"{path}[{index}]"
        checked = (
            _check_id(value, item_path, errors)
            if identifiers
            else _check_text(value, item_path, errors, maximum=2_000)
        )
        if checked is not None:
            result.append(checked)
    return result


def validate_register(document: Any) -> dict[str, Any]:
    """Return a deterministic structural validation report."""

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not isinstance(document, dict):
        return {
            "valid": False,
            "errors": [_issue("$", "top-level JSON value must be an object")],
            "warnings": [],
            "statistics": {},
            "limitations": [
                (
                    "Structural validation cannot establish truth, novelty, "
                    "feasibility, ethics approval, or scientific validity."
                )
            ],
        }

    schema_version = document.get("schema_version")
    if schema_version != "1.1":
        warnings.append(
            _issue(
                "$.schema_version",
                "expected schema version '1.1'; unknown fields are not rejected",
            )
        )

    session = document.get("session")
    participant_ids: set[str] = set()
    if not isinstance(session, dict):
        errors.append(_issue("$.session", "must be an object"))
    else:
        _check_id(session.get("id"), "$.session.id", errors)
        _check_text(session.get("title"), "$.session.title", errors, maximum=200)
        _check_text(
            session.get("question"),
            "$.session.question",
            errors,
            maximum=2_000,
        )
        raw_participants = _list_field(
            session,
            "participant_ids",
            "$.session",
            errors,
        )
        participant_list = _check_string_list(
            raw_participants,
            "$.session.participant_ids",
            errors,
            identifiers=True,
        )
        if not participant_list:
            errors.append(
                _issue(
                    "$.session.participant_ids",
                    "must contain at least one participant ID",
                )
            )
        if len(set(participant_list)) != len(participant_list):
            errors.append(
                _issue("$.session.participant_ids", "participant IDs must be unique")
            )
        participant_ids = set(participant_list)
        if session.get("date") is not None:
            try:
                require_iso_date(session["date"], "$.session.date")
            except CliError as exc:
                errors.append(_issue("$.session.date", str(exc)))

    assumptions_raw = document.get("assumptions")
    if not isinstance(assumptions_raw, list):
        errors.append(_issue("$.assumptions", "must be a list"))
        assumptions_raw = []
    elif len(assumptions_raw) > MAX_ITEMS:
        errors.append(
            _issue(
                "$.assumptions",
                f"has {len(assumptions_raw)} items; limit is {MAX_ITEMS}",
            )
        )
        assumptions_raw = assumptions_raw[:MAX_ITEMS]

    assumption_ids: set[str] = set()
    assumption_references: set[str] = set()
    for index, assumption in enumerate(assumptions_raw):
        path = f"$.assumptions[{index}]"
        if not isinstance(assumption, dict):
            errors.append(_issue(path, "must be an object"))
            continue
        assumption_id = _check_id(assumption.get("id"), f"{path}.id", errors)
        if assumption_id is not None:
            if assumption_id in assumption_ids:
                errors.append(_issue(f"{path}.id", "duplicate assumption ID"))
            assumption_ids.add(assumption_id)
        _check_text(assumption.get("statement"), f"{path}.statement", errors)
        category = assumption.get("category")
        if category not in ASSUMPTION_CATEGORIES:
            errors.append(
                _issue(
                    f"{path}.category",
                    f"must be one of {sorted(ASSUMPTION_CATEGORIES)}",
                )
            )
        status = assumption.get("status")
        if status not in ASSUMPTION_STATUSES:
            errors.append(
                _issue(
                    f"{path}.status",
                    f"must be one of {sorted(ASSUMPTION_STATUSES)}",
                )
            )
        _check_text(
            assumption.get("test_or_check"),
            f"{path}.test_or_check",
            errors,
            maximum=2_000,
        )
        owner = _check_id(assumption.get("owner_id"), f"{path}.owner_id", errors)
        if owner is not None and participant_ids and owner not in participant_ids:
            errors.append(_issue(f"{path}.owner_id", "is not listed as a participant"))
        evidence_refs = _list_field(
            assumption,
            "evidence_refs",
            path,
            errors,
        )
        clean_evidence_refs = _check_string_list(
            evidence_refs,
            f"{path}.evidence_refs",
            errors,
        )
        if (
            status not in {None, "untested", "not-applicable"}
            and not clean_evidence_refs
        ):
            warnings.append(
                _issue(
                    f"{path}.evidence_refs",
                    "non-untested status has no recorded evidence reference",
                )
            )

    ideas_raw = document.get("ideas")
    if not isinstance(ideas_raw, list):
        errors.append(_issue("$.ideas", "must be a list"))
        ideas_raw = []
    elif len(ideas_raw) > MAX_ITEMS:
        errors.append(
            _issue(
                "$.ideas",
                f"has {len(ideas_raw)} items; limit is {MAX_ITEMS}",
            )
        )
        ideas_raw = ideas_raw[:MAX_ITEMS]

    idea_ids: set[str] = set()
    statements: defaultdict[str, list[str]] = defaultdict(list)
    ai_assisted_count = 0
    for index, idea in enumerate(ideas_raw):
        path = f"$.ideas[{index}]"
        if not isinstance(idea, dict):
            errors.append(_issue(path, "must be an object"))
            continue
        idea_id = _check_id(idea.get("id"), f"{path}.id", errors)
        if idea_id is not None:
            if idea_id in idea_ids:
                errors.append(_issue(f"{path}.id", "duplicate idea ID"))
            idea_ids.add(idea_id)
        statement = _check_text(idea.get("statement"), f"{path}.statement", errors)
        if statement is not None and idea_id is not None:
            statements[_normalized_statement(statement)].append(idea_id)

        provenance = idea.get("provenance")
        if not isinstance(provenance, dict):
            errors.append(_issue(f"{path}.provenance", "must be an object"))
            provenance = {}
        origin = provenance.get("origin")
        if origin not in ORIGINS:
            errors.append(
                _issue(
                    f"{path}.provenance.origin",
                    f"must be one of {sorted(ORIGINS)}",
                )
            )
        if origin in {"ai-assisted", "mixed"}:
            ai_assisted_count += 1
        stage = provenance.get("recorded_stage")
        if stage not in RECORDED_STAGES:
            errors.append(
                _issue(
                    f"{path}.provenance.recorded_stage",
                    f"must be one of {sorted(RECORDED_STAGES)}",
                )
            )
        contributors_raw = _list_field(
            provenance,
            "contributor_ids",
            f"{path}.provenance",
            errors,
        )
        contributors = _check_string_list(
            contributors_raw,
            f"{path}.provenance.contributor_ids",
            errors,
            identifiers=True,
        )
        if not contributors:
            errors.append(
                _issue(
                    f"{path}.provenance.contributor_ids",
                    "must contain at least one contributor ID",
                )
            )
        for contributor in contributors:
            if participant_ids and contributor not in participant_ids:
                errors.append(
                    _issue(
                        f"{path}.provenance.contributor_ids",
                        f"{contributor!r} is not listed as a participant",
                    )
                )
        source_refs_raw = _list_field(
            provenance,
            "source_refs",
            f"{path}.provenance",
            errors,
        )
        source_refs = _check_string_list(
            source_refs_raw,
            f"{path}.provenance.source_refs",
            errors,
        )
        ai_tool = provenance.get("ai_tool")
        if origin in {"ai-assisted", "mixed"}:
            _check_text(
                ai_tool,
                f"{path}.provenance.ai_tool",
                errors,
                maximum=500,
            )
        elif ai_tool is not None and ai_tool != "":
            warnings.append(
                _issue(
                    f"{path}.provenance.ai_tool",
                    "AI tool is recorded but origin is not AI-assisted or mixed",
                )
            )
        if origin == "literature-inspired" and not source_refs:
            errors.append(
                _issue(
                    f"{path}.provenance.source_refs",
                    "literature-inspired ideas require at least one source reference",
                )
            )

        linked_assumptions_raw = _list_field(
            idea,
            "assumption_ids",
            path,
            errors,
        )
        linked_assumptions = _check_string_list(
            linked_assumptions_raw,
            f"{path}.assumption_ids",
            errors,
            identifiers=True,
        )
        assumption_references.update(linked_assumptions)
        if not linked_assumptions:
            warnings.append(
                _issue(
                    f"{path}.assumption_ids",
                    "idea has no explicit linked assumptions",
                )
            )

        predictions_raw = _list_field(
            idea,
            "predicted_observations",
            path,
            errors,
        )
        _check_string_list(
            predictions_raw,
            f"{path}.predicted_observations",
            errors,
        )
        uncertainties_raw = _list_field(
            idea,
            "uncertainties",
            path,
            errors,
        )
        uncertainties = _check_string_list(
            uncertainties_raw,
            f"{path}.uncertainties",
            errors,
        )
        if not uncertainties:
            warnings.append(
                _issue(
                    f"{path}.uncertainties",
                    "idea has no recorded uncertainty",
                )
            )
        evidence_status = idea.get("evidence_status")
        if evidence_status not in EVIDENCE_STATUSES:
            errors.append(
                _issue(
                    f"{path}.evidence_status",
                    f"must be one of {sorted(EVIDENCE_STATUSES)}",
                )
            )
        status = idea.get("status")
        if status not in IDEA_STATUSES:
            errors.append(
                _issue(
                    f"{path}.status",
                    f"must be one of {sorted(IDEA_STATUSES)}",
                )
            )

    for normalized, duplicate_ids in sorted(statements.items()):
        if normalized and len(duplicate_ids) > 1:
            warnings.append(
                _issue(
                    "$.ideas",
                    "exact-after-case/whitespace/Unicode normalization duplicate "
                    f"text for IDs {sorted(duplicate_ids)}; this is not a claim "
                    "of semantic equivalence",
                )
            )

    for missing_id in sorted(assumption_references - assumption_ids):
        errors.append(
            _issue(
                "$.ideas[*].assumption_ids",
                f"references missing assumption ID {missing_id!r}",
            )
        )
    for unlinked_id in sorted(assumption_ids - assumption_references):
        warnings.append(
            _issue(
                "$.assumptions",
                f"assumption {unlinked_id!r} is not linked from any idea",
            )
        )

    clusters = document.get("clusters", [])
    if not isinstance(clusters, list):
        errors.append(_issue("$.clusters", "must be a list when present"))
    elif len(clusters) > MAX_ITEMS:
        errors.append(_issue("$.clusters", f"limit is {MAX_ITEMS}"))
    else:
        cluster_ids: set[str] = set()
        for index, cluster in enumerate(clusters):
            path = f"$.clusters[{index}]"
            if not isinstance(cluster, dict):
                errors.append(_issue(path, "must be an object"))
                continue
            cluster_id = _check_id(cluster.get("id"), f"{path}.id", errors)
            if cluster_id is not None:
                if cluster_id in cluster_ids:
                    errors.append(_issue(f"{path}.id", "duplicate cluster ID"))
                cluster_ids.add(cluster_id)
            _check_text(cluster.get("relation"), f"{path}.relation", errors)
            members = _check_string_list(
                _list_field(cluster, "idea_ids", path, errors),
                f"{path}.idea_ids",
                errors,
                identifiers=True,
            )
            for member in members:
                if member not in idea_ids:
                    errors.append(
                        _issue(
                            f"{path}.idea_ids",
                            f"references missing idea ID {member!r}",
                        )
                    )

    decisions = document.get("decision_log", [])
    if not isinstance(decisions, list):
        errors.append(_issue("$.decision_log", "must be a list when present"))
    elif len(decisions) > MAX_ITEMS:
        errors.append(_issue("$.decision_log", f"limit is {MAX_ITEMS}"))
    else:
        decision_ids: set[str] = set()
        for index, decision in enumerate(decisions):
            path = f"$.decision_log[{index}]"
            if not isinstance(decision, dict):
                errors.append(_issue(path, "must be an object"))
                continue
            decision_id = _check_id(
                decision.get("decision_id"), f"{path}.decision_id", errors
            )
            if decision_id is not None:
                if decision_id in decision_ids:
                    errors.append(
                        _issue(f"{path}.decision_id", "duplicate decision ID")
                    )
                decision_ids.add(decision_id)
            if decision.get("date") is not None:
                try:
                    require_iso_date(decision["date"], f"{path}.date")
                except CliError as exc:
                    errors.append(_issue(f"{path}.date", str(exc)))
            candidates = _check_string_list(
                _list_field(decision, "candidate_ids", path, errors),
                f"{path}.candidate_ids",
                errors,
                identifiers=True,
            )
            for candidate in candidates:
                if candidate not in idea_ids:
                    errors.append(
                        _issue(
                            f"{path}.candidate_ids",
                            f"references missing idea ID {candidate!r}",
                        )
                    )
            _check_text(decision.get("decision"), f"{path}.decision", errors)
            _check_text(
                decision.get("rationale"),
                f"{path}.rationale",
                errors,
            )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "statistics": {
            "participants": len(participant_ids),
            "ideas": len(ideas_raw),
            "assumptions": len(assumptions_raw),
            "ai_assisted_or_mixed_ideas": ai_assisted_count,
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "limitations": [
            (
                "Validation is structural and deterministic; it does not verify "
                "claims, citations, novelty, feasibility, or scientific validity."
            ),
            (
                "Exact normalized-text duplicate warnings do not assert semantic "
                "equivalence."
            ),
            (
                "A valid register is not ethics, biosafety, regulatory, clinical, "
                "or institutional approval."
            ),
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Validate the structure, provenance, links, and bounded fields in a "
            "brainstorming JSON register. No network or LLM calls are made."
        )
    )
    parser.add_argument("input", help="Session/register .json file")
    parser.add_argument(
        "--output",
        help="Optional validation-report .json file in an existing directory",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit status 1 for warnings as well as errors",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Explicitly replace an existing regular output file",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run register validation."""

    args = build_parser().parse_args(argv)
    try:
        _, document = read_json(args.input, label="register")
        report = validate_register(document)
        emit_json(report, args.output, force=args.force)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not report["valid"] or (args.strict and report["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
