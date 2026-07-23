#!/usr/bin/env python3
"""Run a bounded finite-horizon queue scenario from allowlisted JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from _common import (
    MAX_TRACE_RECORDS,
    CliError,
    emit_json,
    emit_text,
    integer,
    load_json_object,
)
from basic_simulation_template import QueueConfig, run_simulation


def _trace_text(records: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(
            record,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n"
        for record in records
    )


def run_scenario(
    config: QueueConfig,
    *,
    trace_max_records: int | None = None,
) -> dict[str, Any]:
    """Run the built-in loss/queue scenario; no plugin or Python code is loaded."""

    return run_simulation(
        config,
        replication=0,
        trace_max_records=trace_max_records,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the built-in bounded M/M/c/K-style queue scenario. The local "
            "JSON configuration has a fixed allowlist; no code, plugin, eval, "
            "network resource, or unbounded simulation is accepted."
        )
    )
    parser.add_argument(
        "--config",
        help="Optional local .json queue configuration; URLs and symlinks are rejected",
    )
    parser.add_argument("--output", help="Optional local .json scenario report")
    parser.add_argument(
        "--trace-output",
        help="Optional local .jsonl deterministic event trace",
    )
    parser.add_argument(
        "--trace-max-records",
        type=int,
        default=100_000,
        help="Trace cap from 1 through 1,000,000 (default: 100000)",
    )
    parser.add_argument("--force", action="store_true", help="Replace explicit outputs")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = QueueConfig.from_mapping(
            load_json_object(args.config) if args.config else None
        )
        trace_limit = (
            integer(
                args.trace_max_records,
                name="trace_max_records",
                minimum=1,
                maximum=MAX_TRACE_RECORDS,
            )
            if args.trace_output
            else None
        )
        report = run_scenario(config, trace_max_records=trace_limit)
        trace = report.pop("event_trace", None)
        if trace is not None:
            records = trace["records"]
            emit_text(
                _trace_text(records),
                output=args.trace_output,
                suffixes={".jsonl"},
                force=args.force,
            )
            report["trace"] = {
                "file": Path(args.trace_output).name,
                "records": len(records),
                "truncated": trace["truncated"],
            }
        else:
            report["trace"] = None
        report["safety"] = {
            "config_allowlist": True,
            "entity_limit": config.max_entities,
            "event_limit": config.max_events,
            "network_used": False,
            "plugin_loading": False,
            "time_limit": config.horizon,
        }
        emit_json(report, output=args.output, force=args.force)
    except CliError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
