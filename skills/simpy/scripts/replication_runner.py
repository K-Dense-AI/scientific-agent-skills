#!/usr/bin/env python3
"""Run independent bounded replications and compute Student-t intervals."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

from _common import (
    MAX_REPLICATIONS,
    CliError,
    emit_json,
    finite_number,
    integer,
    load_json_object,
    mean_confidence_interval,
    validate_keys,
)
from basic_simulation_template import QueueConfig, run_simulation


MAX_TOTAL_EVENT_BUDGET = 5_000_000
MAX_TOTAL_ENTITY_BUDGET = 2_000_000
EXPERIMENT_KEYS = {"confidence", "model", "replications"}


@dataclass(frozen=True)
class ExperimentConfig:
    model: QueueConfig
    replications: int = 20
    confidence: float = 0.95

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "ExperimentConfig":
        value = {} if value is None else dict(value)
        validate_keys(
            value, allowed=EXPERIMENT_KEYS, context="replication configuration"
        )
        model_value = value.get("model", {})
        if not isinstance(model_value, dict):
            raise CliError("model must be a JSON object")
        model = QueueConfig.from_mapping(model_value)
        replications = integer(
            value.get("replications", 20),
            name="replications",
            minimum=2,
            maximum=MAX_REPLICATIONS,
        )
        confidence = finite_number(
            value.get("confidence", 0.95),
            name="confidence",
            minimum=0.50,
            maximum=0.999,
            minimum_inclusive=False,
        )
        if replications * model.max_events > MAX_TOTAL_EVENT_BUDGET:
            raise CliError(
                "replications * model.max_events exceeds the total event budget "
                f"({MAX_TOTAL_EVENT_BUDGET})"
            )
        if replications * model.max_entities > MAX_TOTAL_ENTITY_BUDGET:
            raise CliError(
                "replications * model.max_entities exceeds the total entity budget "
                f"({MAX_TOTAL_ENTITY_BUDGET})"
            )
        return cls(
            model=model,
            replications=replications,
            confidence=confidence,
        )


def _interval_or_unavailable(
    reports: list[dict[str, Any]],
    *,
    metric: str,
    confidence: float,
) -> dict[str, Any]:
    values = [report["metrics"][metric] for report in reports]
    missing = sum(value is None for value in values)
    if missing:
        return {
            "missing_replications": missing,
            "reason": "metric was undefined in one or more replications",
            "status": "unavailable",
        }
    interval = mean_confidence_interval(values, confidence=confidence)
    interval["status"] = "ok"
    return interval


def run_experiment(config: ExperimentConfig) -> dict[str, Any]:
    """Run independent replication streams and summarize replication estimates."""

    reports = [
        run_simulation(config.model, replication=index)
        for index in range(config.replications)
    ]
    metrics = (
        "average_queue_length",
        "average_system_time",
        "average_wait",
        "loss_probability",
        "server_utilization",
        "throughput_per_time_unit",
    )
    intervals = {
        metric: _interval_or_unavailable(
            reports, metric=metric, confidence=config.confidence
        )
        for metric in metrics
    }
    compact_runs = [
        {
            "counters": report["counters"],
            "metrics": report["metrics"],
            "replication": report["replication"],
            "seed_manifest": report["seed_manifest"],
            "warnings": report["warnings"],
        }
        for report in reports
    ]
    return {
        "analysis": {
            "analysis_mode": config.model.analysis_mode,
            "confidence_method": (
                "two-sided Student-t interval across independent "
                "replication-level estimates"
            ),
            "confidence_level": config.confidence,
            "independence_unit": "replication",
            "single_run_interval": False,
            "warm_up": config.model.warm_up,
        },
        "intervals": intervals,
        "model": {
            key: getattr(config.model, key)
            for key in config.model.__dataclass_fields__
        },
        "replications": compact_runs,
        "safety": {
            "network_used": False,
            "replication_limit": MAX_REPLICATIONS,
            "total_entity_budget": MAX_TOTAL_ENTITY_BUDGET,
            "total_event_budget": MAX_TOTAL_EVENT_BUDGET,
        },
        "schema_version": "1.1",
        "warnings": [
            "Intervals quantify Monte Carlo uncertainty under the configured model; "
            "they do not validate the model or establish causality.",
            "For steady-state analysis, warm-up and run length require a separate "
            "transient-bias assessment and sensitivity analysis.",
            "Do not treat within-run customer observations as independent replications.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run 2-1000 deterministic, independent queue replications from an "
            "allowlisted local JSON configuration and report Student-t confidence "
            "intervals across replication estimates."
        )
    )
    parser.add_argument(
        "--config",
        help="Optional local .json experiment configuration; URLs/symlinks rejected",
    )
    parser.add_argument("--output", help="Optional local .json report")
    parser.add_argument("--force", action="store_true", help="Replace explicit output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = ExperimentConfig.from_mapping(
            load_json_object(args.config) if args.config else None
        )
        emit_json(
            run_experiment(config),
            output=args.output,
            force=args.force,
        )
    except CliError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
