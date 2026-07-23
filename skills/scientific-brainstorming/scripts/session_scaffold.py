"""Generate a deterministic JSON scaffold for a brainstorming session."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from _common import (
    CliError,
    bounded_strings,
    emit_json,
    require_identifier,
    require_iso_date,
    require_text,
)

WORKFLOW_STAGES = [
    "scope",
    "independent-generation",
    "structured-sharing",
    "clustering",
    "criteria-definition",
    "independent-evaluation",
    "adversarial-review",
    "literature-check",
    "feasibility-and-ethics-gate",
    "decision-log",
]


def build_scaffold(
    *,
    session_id: str,
    title: str,
    question: str,
    participant_ids: Sequence[str],
    session_date: str | None = None,
    in_scope: Sequence[str] = (),
    out_of_scope: Sequence[str] = (),
    constraints: Sequence[str] = (),
    perspectives: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a reproducible, empty session register from explicit inputs."""

    clean_session_id = require_identifier(session_id, "session ID")
    clean_title = require_text(title, "title", maximum=200)
    clean_question = require_text(question, "question", maximum=2_000)
    participants = [
        require_identifier(value, f"participant ID {index + 1}")
        for index, value in enumerate(participant_ids)
    ]
    if not participants:
        raise CliError("at least one participant ID is required")
    if len(participants) > 100:
        raise CliError("participant count exceeds the limit of 100")
    if len(set(participants)) != len(participants):
        raise CliError("participant IDs must be unique")

    clean_date = (
        require_iso_date(session_date, "session date")
        if session_date is not None
        else None
    )
    clean_in_scope = bounded_strings(in_scope, "in-scope items")
    clean_out_of_scope = bounded_strings(out_of_scope, "out-of-scope items")
    clean_constraints = bounded_strings(constraints, "constraints")
    clean_perspectives = bounded_strings(perspectives, "perspectives")

    return {
        "schema_version": "1.1",
        "session": {
            "id": clean_session_id,
            "title": clean_title,
            "question": clean_question,
            "date": clean_date,
            "decision_owner_id": None,
            "facilitator_id": None,
            "participant_ids": participants,
            "represented_perspectives": clean_perspectives,
            "missing_perspectives": [],
            "conflicts_or_power_dynamics": [],
        },
        "scope": {
            "in_scope": clean_in_scope,
            "out_of_scope": clean_out_of_scope,
            "constraints": [
                {
                    "statement": statement,
                    "classification": "unclassified",
                }
                for statement in clean_constraints
            ],
            "prohibited_outputs": [],
        },
        "information_governance": {
            "classification": "not-assessed",
            "approved_record_location": None,
            "contains_personal_or_sensitive_data": False,
            "contains_unpublished_or_proprietary_data": False,
            "contains_controlled_or_security_sensitive_data": False,
            "external_ai_use_permitted": "not-assessed",
        },
        "workflow": [
            {
                "order": index + 1,
                "stage": stage,
                "status": "pending",
                "method_or_deviation": None,
            }
            for index, stage in enumerate(WORKFLOW_STAGES)
        ],
        "ideas": [],
        "assumptions": [],
        "clusters": [],
        "criteria": [],
        "adversarial_reviews": [],
        "literature_checks": [],
        "feasibility_and_ethics_reviews": [],
        "decision_log": [],
        "templates": {
            "idea": {
                "id": "I001",
                "statement": "Replace with a concise candidate direction.",
                "provenance": {
                    "origin": "human",
                    "contributor_ids": [participants[0]],
                    "recorded_stage": "independent",
                    "source_refs": [],
                    "ai_tool": None,
                },
                "assumption_ids": ["A001"],
                "predicted_observations": [],
                "uncertainties": [],
                "evidence_status": "not-checked",
                "status": "candidate",
            },
            "assumption": {
                "id": "A001",
                "statement": "Replace with one explicit assumption.",
                "category": "measurement",
                "status": "untested",
                "test_or_check": "Describe how this could be checked.",
                "owner_id": participants[0],
                "evidence_refs": [],
            },
        },
        "notices": [
            "Ideas and scores are not evidence or scientific conclusions.",
            (
                "Clinical, ethics, biosafety, dual-use, regulatory, and "
                "institutional review remain separate."
            ),
            (
                "Do not store sensitive prompt content or restricted information "
                "in this register."
            ),
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Generate a deterministic JSON session scaffold for evidence-aware "
            "scientific brainstorming. No network or LLM calls are made."
        )
    )
    parser.add_argument("--session-id", required=True, help="Stable session ID")
    parser.add_argument("--title", required=True, help="Session title")
    parser.add_argument("--question", required=True, help="One focal question")
    parser.add_argument(
        "--participant",
        action="append",
        required=True,
        dest="participants",
        help="Pseudonymous participant ID; repeat for multiple participants",
    )
    parser.add_argument(
        "--date",
        dest="session_date",
        help="Optional explicit ISO date (YYYY-MM-DD); no date is invented",
    )
    parser.add_argument(
        "--in-scope",
        action="append",
        default=[],
        help="In-scope item; repeat as needed",
    )
    parser.add_argument(
        "--out-of-scope",
        action="append",
        default=[],
        help="Out-of-scope item; repeat as needed",
    )
    parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="Constraint to classify later; repeat as needed",
    )
    parser.add_argument(
        "--perspective",
        action="append",
        default=[],
        help="Represented perspective; repeat as needed",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Destination .json file in an existing directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Explicitly replace an existing regular output file",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the scaffold generator."""

    args = build_parser().parse_args(argv)
    try:
        payload = build_scaffold(
            session_id=args.session_id,
            title=args.title,
            question=args.question,
            participant_ids=args.participants,
            session_date=args.session_date,
            in_scope=args.in_scope,
            out_of_scope=args.out_of_scope,
            constraints=args.constraint,
            perspectives=args.perspective,
        )
        emit_json(payload, args.output, force=args.force)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
