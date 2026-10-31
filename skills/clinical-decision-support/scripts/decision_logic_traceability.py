#!/usr/bin/env python3
"""Validate and export research/governance decision-logic traceability."""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from typing import Any

from _common import (
    InputError,
    IssueLog,
    load_json_object,
    require_list,
    require_nonempty_text,
    source_ids,
    validate_references,
    write_text,
)

MAX_NODES = 200
NODE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
ALLOWED_NODE_TYPES = {
    "input_check",
    "data_quality_gate",
    "evidence_rule",
    "validation_gate",
    "documentation_gate",
    "human_review",
    "release_gate",
    "monitoring_gate",
}
ALLOWED_OUTPUT_KINDS = {
    "include_evidence",
    "exclude_evidence",
    "flag_for_review",
    "validation_status",
    "documentation_status",
    "release_hold",
    "monitoring_status",
}
PROHIBITED_LOGIC = (
    "diagnose",
    "prescribe",
    "administer",
    "dose ",
    "dosing",
    "triage",
    "urgent",
    "alarm",
    "alert clinician",
    "treatment selection",
    "therapy recommendation",
    "bedside",
    "patient-specific",
)


def _safe_csv(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _has_cycle(edges: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dependency in edges[node]:
            if visit(dependency):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in edges)


def validate_matrix(
    document: dict[str, Any]
) -> tuple[IssueLog, list[dict[str, str]]]:
    log = IssueLog()
    normalized: list[dict[str, str]] = []
    try:
        require_nonempty_text(document.get("schema_version"), "schema_version")
        known_sources = source_ids(document)
        metadata = document.get("metadata")
        if not isinstance(metadata, dict):
            raise InputError("metadata must be an object")
        for field in (
            "logic_id",
            "title",
            "version",
            "status",
            "owner",
            "purpose",
            "change_summary",
            "monitoring_plan",
            "retirement_criteria",
        ):
            require_nonempty_text(metadata.get(field), f"metadata.{field}")
        if metadata.get("decision_role") != "research_governance_only":
            log.errors.append(
                "metadata.decision_role must be research_governance_only"
            )
        if not isinstance(metadata.get("data_level"), str) or metadata.get("data_level") not in {"aggregate", "synthetic", "metadata_only"}:
            log.errors.append(
                "metadata.data_level must be aggregate, synthetic, or metadata_only"
            )
        if metadata.get("patient_care_use") is not False:
            log.errors.append("metadata.patient_care_use must be false")
        if metadata.get("executable_logic") is not False:
            log.errors.append("metadata.executable_logic must be false")

        nodes = require_list(document.get("nodes"), "nodes", maximum=MAX_NODES)
        if not nodes:
            raise InputError("At least one traceability node is required")
        node_ids: set[str] = set()
        for index, node in enumerate(nodes):
            field = f"nodes[{index}]"
            if not isinstance(node, dict):
                raise InputError(f"{field} must be an object")
            node_id = require_nonempty_text(
                node.get("id"), f"{field}.id", max_length=64
            )
            if not NODE_ID.fullmatch(node_id):
                raise InputError(f"{field}.id has an unsafe or invalid format")
            if node_id in node_ids:
                raise InputError(f"Duplicate node id: {node_id}")
            node_ids.add(node_id)

        edges: dict[str, list[str]] = {}
        for index, node in enumerate(nodes):
            field = f"nodes[{index}]"
            node_id = require_nonempty_text(node["id"], f"{field}.id", max_length=64)
            node_type = require_nonempty_text(node.get("type"), f"{field}.type")
            if node_type not in ALLOWED_NODE_TYPES:
                log.errors.append(f"{field}.type is unsupported")
            precondition = require_nonempty_text(
                node.get("precondition"), f"{field}.precondition"
            )
            statement = require_nonempty_text(
                node.get("logic_statement"), f"{field}.logic_statement"
            )
            output_kind = require_nonempty_text(
                node.get("output_kind"), f"{field}.output_kind"
            )
            if output_kind not in ALLOWED_OUTPUT_KINDS:
                log.errors.append(f"{field}.output_kind is unsupported")
            output_value = require_nonempty_text(
                node.get("output_value"), f"{field}.output_value"
            )
            rationale = require_nonempty_text(
                node.get("rationale"), f"{field}.rationale"
            )
            owner = require_nonempty_text(node.get("owner"), f"{field}.owner")
            reviewer = require_nonempty_text(
                node.get("reviewer_role"), f"{field}.reviewer_role"
            )
            status = require_nonempty_text(node.get("status"), f"{field}.status")
            if status not in {"draft", "validated", "retired"}:
                log.errors.append(f"{field}.status is unsupported")
            combined = f"{precondition} {statement} {output_value}".lower()
            found = [phrase for phrase in PROHIBITED_LOGIC if phrase in combined]
            if found:
                log.errors.append(
                    f"{field} contains prohibited clinical logic: {', '.join(found)}"
                )

            dependencies = require_list(
                node.get("dependency_ids", []),
                f"{field}.dependency_ids",
                maximum=30,
            )
            normalized_dependencies: list[str] = []
            for dep_index, dependency in enumerate(dependencies):
                dep = require_nonempty_text(
                    dependency,
                    f"{field}.dependency_ids[{dep_index}]",
                    max_length=64,
                )
                if dep not in node_ids:
                    log.errors.append(f"{field} references unknown dependency: {dep}")
                if dep == node_id:
                    log.errors.append(f"{field} cannot depend on itself")
                if dep in node_ids and dep != node_id:
                    normalized_dependencies.append(dep)
            edges[node_id] = normalized_dependencies

            source_refs = validate_references(
                node.get("source_ids"), known_sources, f"{field}.source_ids"
            )
            tests = require_list(
                node.get("validation_tests"), f"{field}.validation_tests", maximum=30
            )
            if not tests:
                log.errors.append(f"{field} requires at least one validation test")
            normalized_tests = [
                require_nonempty_text(test, f"{field}.validation_tests[{test_index}]")
                for test_index, test in enumerate(tests)
            ]
            normalized.append(
                {
                    "node_id": node_id,
                    "type": node_type,
                    "dependencies": "; ".join(normalized_dependencies),
                    "precondition": precondition,
                    "logic_statement": statement,
                    "output_kind": output_kind,
                    "output_value": output_value,
                    "source_ids": "; ".join(source_refs),
                    "rationale": rationale,
                    "validation_tests": "; ".join(normalized_tests),
                    "owner": owner,
                    "reviewer_role": reviewer,
                    "status": status,
                }
            )

        if _has_cycle(edges):
            log.errors.append("Dependency graph contains a cycle")

        review = document.get("human_review")
        if not isinstance(review, dict):
            raise InputError("human_review must be an object")
        if review.get("required") is not True:
            log.errors.append("human_review.required must be true")
        require_nonempty_text(
            review.get("approval_boundary"), "human_review.approval_boundary"
        )
        if metadata.get("status") == "validated" and review.get("completed") is not True:
            log.errors.append(
                "Validated matrix status requires completed human review"
            )
        elif review.get("completed") is not True:
            log.warnings.append("Human review is not recorded as complete")
    except InputError as exc:
        log.errors.append(str(exc))

    if log.ok:
        log.info.append("Research/governance traceability matrix is structurally valid")
    else:
        normalized = []
    return log, normalized


def _csv_text(rows: list[dict[str, str]]) -> str:
    fieldnames = [
        "node_id",
        "type",
        "dependencies",
        "precondition",
        "logic_statement",
        "output_kind",
        "output_value",
        "source_ids",
        "rationale",
        "validation_tests",
        "owner",
        "reviewer_role",
        "status",
    ]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _safe_csv(row[key]) for key in fieldnames})
    return stream.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate research/governance decision logic and emit a CSV traceability "
            "matrix. The tool never executes logic."
        )
    )
    parser.add_argument("input", help="Local matrix JSON")
    parser.add_argument("-o", "--output", help="Optional local CSV output")
    parser.add_argument(
        "--strict", action="store_true", help="Return failure when warnings are present"
    )
    args = parser.parse_args()

    try:
        document = load_json_object(args.input)
        log, rows = validate_matrix(document)
        for message in log.errors:
            print(f"ERROR: {message}", file=sys.stderr)
        for message in log.warnings:
            print(f"WARNING: {message}", file=sys.stderr)
        if not log.ok or (args.strict and log.warnings):
            return 1
        if args.output:
            write_text(args.output, _csv_text(rows), {".csv"})
        else:
            print(_csv_text(rows), end="")
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not log.ok or (args.strict and log.warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
