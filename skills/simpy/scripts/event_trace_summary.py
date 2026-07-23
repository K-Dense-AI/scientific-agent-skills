#!/usr/bin/env python3
"""Summarize bounded event-trace JSONL or ResourceMonitor CSV artifacts."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Any

from _common import (
    MAX_TRACE_RECORDS,
    CliError,
    checked_input_file,
    emit_json,
    finite_number,
    integer,
    parse_json_line,
    validate_keys,
)


EVENT_FIELDS = {
    "event_id",
    "event_type",
    "priority",
    "queue_size_before",
    "time",
}
RESOURCE_FIELDS = {
    "count",
    "event",
    "queue_length",
    "time",
    "utilization",
}


def _csv_number(value: str | None, *, name: str) -> float:
    if value is None:
        raise CliError(f"{name} is missing")
    try:
        parsed = float(value)
    except ValueError as exc:
        raise CliError(f"{name} must be numeric") from exc
    return finite_number(parsed, name=name)


def summarize_event_trace(path: Path, *, max_records: int) -> dict[str, Any]:
    """Validate and summarize deterministic JSONL event records."""

    counts: Counter[str] = Counter()
    first_time: float | None = None
    last_time: float | None = None
    previous_key: tuple[float, int, int] | None = None
    ordering_violations = 0
    maximum_queue_size = 0
    records = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    raise CliError(f"blank JSONL record on line {line_number}")
                records += 1
                if records > max_records:
                    raise CliError(
                        f"trace exceeds the configured record limit ({max_records})"
                    )
                record = parse_json_line(raw_line, line_number=line_number)
                validate_keys(
                    record,
                    allowed=EVENT_FIELDS,
                    required=EVENT_FIELDS,
                    context=f"trace line {line_number}",
                )
                time = finite_number(
                    record["time"], name=f"line {line_number} time", minimum=0
                )
                priority = integer(
                    record["priority"],
                    name=f"line {line_number} priority",
                    minimum=-1_000_000,
                    maximum=1_000_000,
                )
                event_id = integer(
                    record["event_id"],
                    name=f"line {line_number} event_id",
                    minimum=0,
                    maximum=2**63 - 1,
                )
                queue_size = integer(
                    record["queue_size_before"],
                    name=f"line {line_number} queue_size_before",
                    minimum=1,
                    maximum=MAX_TRACE_RECORDS,
                )
                event_type = record["event_type"]
                if (
                    not isinstance(event_type, str)
                    or not event_type.isidentifier()
                    or len(event_type) > 128
                ):
                    raise CliError(
                        f"line {line_number} event_type must be a short identifier"
                    )
                key = (time, priority, event_id)
                if previous_key is not None and key < previous_key:
                    ordering_violations += 1
                previous_key = key
                first_time = time if first_time is None else first_time
                last_time = time
                maximum_queue_size = max(maximum_queue_size, queue_size)
                counts[event_type] += 1
    except (OSError, UnicodeError) as exc:
        raise CliError(f"cannot read trace {path.name}: {exc}") from exc
    if records == 0:
        raise CliError("event trace contains no records")
    return {
        "event_type_counts": dict(sorted(counts.items())),
        "first_time": first_time,
        "last_time": last_time,
        "maximum_queue_size_before_step": maximum_queue_size,
        "ordering_violations": ordering_violations,
        "records": records,
        "semantics": (
            "Each row is the next private event-queue entry immediately before "
            "Environment.step(); ordering is checked by (time, priority, event_id)."
        ),
    }


def summarize_resource_csv(path: Path, *, max_records: int) -> dict[str, Any]:
    """Validate and summarize ResourceMonitor state-change samples."""

    samples: list[dict[str, Any]] = []
    event_counts: Counter[str] = Counter()
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise CliError("resource CSV has no header")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise CliError("resource CSV has duplicate columns")
            if set(reader.fieldnames) != RESOURCE_FIELDS:
                raise CliError(
                    "resource CSV columns must be exactly: "
                    + ", ".join(sorted(RESOURCE_FIELDS))
                )
            previous_time: float | None = None
            for row_number, row in enumerate(reader, start=2):
                if len(samples) >= max_records:
                    raise CliError(
                        f"resource CSV exceeds the record limit ({max_records})"
                    )
                time = finite_number(
                    _csv_number(row["time"], name=f"row {row_number} time"),
                    name=f"row {row_number} time",
                    minimum=0,
                )
                if previous_time is not None and time < previous_time:
                    raise CliError("resource sample times must be nondecreasing")
                previous_time = time
                count = integer(
                    int(row["count"]),
                    name=f"row {row_number} count",
                    minimum=0,
                    maximum=MAX_TRACE_RECORDS,
                )
                queue_length = integer(
                    int(row["queue_length"]),
                    name=f"row {row_number} queue_length",
                    minimum=0,
                    maximum=MAX_TRACE_RECORDS,
                )
                utilization = finite_number(
                    _csv_number(
                        row["utilization"],
                        name=f"row {row_number} utilization",
                    ),
                    name=f"row {row_number} utilization",
                    minimum=0,
                    maximum=1,
                )
                event = row["event"]
                if (
                    not event
                    or len(event) > 64
                    or any(character in "\r\n," for character in event)
                ):
                    raise CliError(f"row {row_number} has an invalid event label")
                samples.append(
                    {
                        "count": count,
                        "event": event,
                        "queue_length": queue_length,
                        "time": time,
                        "utilization": utilization,
                    }
                )
                event_counts[event] += 1
    except ValueError as exc:
        raise CliError(f"resource CSV contains an invalid integer: {exc}") from exc
    except (OSError, UnicodeError, csv.Error) as exc:
        raise CliError(f"cannot read resource CSV {path.name}: {exc}") from exc
    if len(samples) < 2:
        raise CliError("resource CSV needs at least an initial and final sample")
    start = samples[0]["time"]
    end = samples[-1]["time"]
    if end <= start:
        raise CliError("resource CSV must span positive simulation time")
    queue_area = 0.0
    utilization_area = 0.0
    for current, following in zip(samples, samples[1:]):
        duration = following["time"] - current["time"]
        queue_area += current["queue_length"] * duration
        utilization_area += current["utilization"] * duration
    return {
        "average_queue_length": queue_area / (end - start),
        "average_utilization": utilization_area / (end - start),
        "end": end,
        "event_counts": dict(sorted(event_counts.items())),
        "maximum_count": max(sample["count"] for sample in samples),
        "maximum_queue_length": max(
            sample["queue_length"] for sample in samples
        ),
        "records": len(samples),
        "start": start,
        "semantics": (
            "Time-weighted values treat each sampled state as left-continuous "
            "until the next sample. Same-time pre/post samples have zero duration."
        ),
    }


def summarize(path: Path, *, max_records: int) -> dict[str, Any]:
    if path.suffix.lower() == ".jsonl":
        kind = "event_trace"
        summary = summarize_event_trace(path, max_records=max_records)
    elif path.suffix.lower() == ".csv":
        kind = "resource_monitor"
        summary = summarize_resource_csv(path, max_records=max_records)
    else:
        raise CliError("input must end in .jsonl or .csv")
    return {
        "input": {"kind": kind, "name": path.name},
        "network_used": False,
        "schema_version": "1.1",
        "summary": summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize a local event-trace .jsonl or ResourceMonitor .csv file. "
            "Inputs are bounded and validated; no model code is executed."
        )
    )
    parser.add_argument("input", help="Local .jsonl or .csv input")
    parser.add_argument(
        "--max-records",
        type=int,
        default=100_000,
        help="Input record cap from 1 through 1,000,000 (default: 100000)",
    )
    parser.add_argument("--output", help="Optional local .json summary")
    parser.add_argument("--force", action="store_true", help="Replace explicit output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        max_records = integer(
            args.max_records,
            name="max_records",
            minimum=1,
            maximum=MAX_TRACE_RECORDS,
        )
        path = checked_input_file(
            args.input, suffixes={".csv", ".jsonl"}
        )
        emit_json(
            summarize(path, max_records=max_records),
            output=args.output,
            force=args.force,
        )
    except CliError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
