#!/usr/bin/env python3
"""Validate bounded queue or replication JSON without running a simulation."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Any

from _common import CliError, emit_json, load_json_object
from basic_simulation_template import QueueConfig
from replication_runner import (
    MAX_TOTAL_ENTITY_BUDGET,
    MAX_TOTAL_EVENT_BUDGET,
    ExperimentConfig,
)


def infer_schema(document: dict[str, Any]) -> str:
    """Infer only the two bundled schemas; never resolve a plugin or import path."""

    replication_markers = {"model", "replications", "confidence"}
    return "replication" if set(document) & replication_markers else "queue"


def validate_document(
    document: dict[str, Any], *, schema: str = "auto"
) -> dict[str, Any]:
    """Return normalized validated configuration metadata."""

    if schema not in {"auto", "queue", "replication"}:
        raise CliError("schema must be auto, queue, or replication")
    resolved = infer_schema(document) if schema == "auto" else schema
    if resolved == "queue":
        queue = QueueConfig.from_mapping(document)
        normalized: dict[str, Any] = asdict(queue)
        budgets = {
            "entities": queue.max_entities,
            "events": queue.max_events,
            "replications": 1,
            "time": queue.horizon,
        }
    else:
        experiment = ExperimentConfig.from_mapping(document)
        normalized = {
            "confidence": experiment.confidence,
            "model": asdict(experiment.model),
            "replications": experiment.replications,
        }
        budgets = {
            "entities": experiment.model.max_entities
            * experiment.replications,
            "events": experiment.model.max_events * experiment.replications,
            "replications": experiment.replications,
            "time_per_replication": experiment.model.horizon,
        }
    return {
        "budgets": budgets,
        "limits": {
            "total_entities_for_replication_schema": MAX_TOTAL_ENTITY_BUDGET,
            "total_events_for_replication_schema": MAX_TOTAL_EVENT_BUDGET,
        },
        "network_used": False,
        "normalized": normalized,
        "schema": resolved,
        "schema_version": "1.1",
        "validation": {
            "config_allowlist": True,
            "finite_numeric_values": True,
            "no_code_execution": True,
            "valid": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and normalize an allowlisted local queue or replication "
            "JSON configuration. This command does not execute a simulation."
        )
    )
    parser.add_argument("config", help="Local .json input; URLs and symlinks rejected")
    parser.add_argument(
        "--schema",
        choices=("auto", "queue", "replication"),
        default="auto",
        help="Configuration schema (default: auto)",
    )
    parser.add_argument("--output", help="Optional local .json validation report")
    parser.add_argument("--force", action="store_true", help="Replace explicit output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        document = load_json_object(args.config)
        emit_json(
            validate_document(document, schema=args.schema),
            output=args.output,
            force=args.force,
        )
    except CliError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
