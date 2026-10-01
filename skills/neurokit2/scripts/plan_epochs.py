#!/usr/bin/env python3
"""Plan sample-exact event epochs without loading NeuroKit2."""

from __future__ import annotations

import argparse
import math
from typing import Any

from _common import (
    MAX_CSV_BYTES,
    MAX_ROWS,
    CliError,
    checked_input_file,
    emit_json,
    finite_float,
    read_numeric_columns,
    require_deidentified,
    run_cli,
)

MAX_EVENTS = 100_000


def _parse_events(value: str) -> list[float]:
    pieces = [piece.strip() for piece in value.split(",")]
    if not pieces or any(not piece for piece in pieces):
        raise CliError("--events must be a comma-separated numeric list")
    if len(pieces) > MAX_EVENTS:
        raise CliError(f"event count exceeds {MAX_EVENTS}")
    events: list[float] = []
    for index, piece in enumerate(pieces, start=1):
        try:
            event = float(piece)
        except ValueError as exc:
            raise CliError(f"event {index} is not numeric") from exc
        if not math.isfinite(event) or event < 0:
            raise CliError(f"event {index} must be finite and nonnegative")
        events.append(event)
    return events


def _sample_offset(seconds: float, sampling_rate: float, *, name: str) -> int:
    exact = seconds * sampling_rate
    if not math.isfinite(exact):
        raise CliError(f"{name} must map to a finite sample offset")
    rounded = round(exact)
    if not math.isclose(exact, rounded, rel_tol=0.0, abs_tol=1e-8):
        raise CliError(
            f"{name}={seconds} s is not sample-aligned at {sampling_rate} Hz "
            f"({exact} samples)"
        )
    return int(rounded)


def _event_samples(
    values: list[float],
    *,
    unit: str,
    sampling_rate: float,
) -> list[int]:
    samples: list[int] = []
    for index, value in enumerate(values, start=1):
        if not math.isfinite(value) or value < 0:
            raise CliError(f"event {index} must be finite and nonnegative")
        if unit == "samples":
            rounded = round(value)
            if not math.isclose(value, rounded, rel_tol=0.0, abs_tol=1e-9):
                raise CliError(f"event {index} is not an integer sample index: {value}")
            sample = int(rounded)
        else:
            sample = _sample_offset(value, sampling_rate, name=f"event {index} onset")
        samples.append(sample)
    return samples


def plan(
    events: list[int],
    *,
    recording_samples: int,
    sampling_rate: float,
    epoch_start_s: float,
    epoch_end_s: float,
    baseline_start_s: float | None,
    baseline_end_s: float | None,
    boundary_policy: str,
) -> dict[str, Any]:
    start_offset = _sample_offset(epoch_start_s, sampling_rate, name="--epoch-start")
    end_offset = _sample_offset(epoch_end_s, sampling_rate, name="--epoch-end")
    if end_offset <= start_offset:
        raise CliError("--epoch-end must be after --epoch-start")
    if recording_samples < 1 or recording_samples > MAX_ROWS:
        raise CliError(f"--recording-samples must be between 1 and {MAX_ROWS}")

    baseline: dict[str, Any] | None = None
    if (baseline_start_s is None) != (baseline_end_s is None):
        raise CliError("provide both --baseline-start and --baseline-end")
    if baseline_start_s is not None and baseline_end_s is not None:
        baseline_start = _sample_offset(
            baseline_start_s, sampling_rate, name="--baseline-start"
        )
        baseline_end = _sample_offset(
            baseline_end_s, sampling_rate, name="--baseline-end"
        )
        if not start_offset <= baseline_start < baseline_end <= end_offset:
            raise CliError("baseline must be a nonempty subset of the epoch")
        if baseline_end > 0:
            raise CliError("baseline must not extend after event onset")
        baseline = {
            "end_offset_samples_exclusive": baseline_end,
            "end_s_exclusive": baseline_end_s,
            "sample_count": baseline_end - baseline_start,
            "start_offset_samples": baseline_start,
            "start_s": baseline_start_s,
        }

    rows: list[dict[str, Any]] = []
    invalid = 0
    for ordinal, onset in enumerate(events, start=1):
        if isinstance(onset, bool) or not isinstance(onset, int):
            raise CliError("event onsets must be integer sample indices")
        if not 0 <= onset < recording_samples:
            raise CliError(f"event {ordinal} onset is outside the recording")
        start = onset + start_offset
        end = onset + end_offset
        window_samples = end_offset - start_offset
        before = min(window_samples, max(0, -start))
        after = min(window_samples, max(0, end - recording_samples))
        complete = before == 0 and after == 0
        if not complete:
            invalid += 1
        if boundary_policy == "drop" and not complete:
            continue
        rows.append(
            {
                "complete": complete,
                "end_sample_exclusive": end,
                "event_ordinal": ordinal,
                "onset_sample": onset,
                "pad_after_samples": after,
                "pad_before_samples": before,
                "start_sample": start,
            }
        )
    if boundary_policy == "error" and invalid:
        raise CliError(f"{invalid} event(s) would cross recording boundaries")

    warnings: list[str] = []
    if events != sorted(events):
        warnings.append("event onsets are not sorted")
    if len(events) != len(set(events)):
        warnings.append("duplicate event onsets are present")
    if invalid:
        warnings.append(
            f"{invalid} event(s) cross a boundary; NeuroKit2 0.2.13 pads "
            "non-integer signal columns with NaN"
        )

    return {
        "baseline": baseline,
        "boundary_policy": boundary_policy,
        "event_count_input": len(events),
        "event_count_output": len(rows),
        "events": rows,
        "indexing": {
            "event_onsets": "zero-based sample indices",
            "window": "[start_sample, end_sample_exclusive)",
        },
        "neurokit2_epoch_note": (
            "epochs_create() slices the end sample exclusively but labels its "
            "floating time index with an inclusive epochs_end endpoint. Its "
            "baseline_correction=True subtracts the mean from epoch start through "
            "t=0; use manual correction for a narrower baseline."
        ),
        "recording_samples": recording_samples,
        "sampling_rate_hz": sampling_rate,
        "window": {
            "end_offset_samples_exclusive": end_offset,
            "end_s_exclusive": epoch_end_s,
            "sample_count": end_offset - start_offset,
            "start_offset_samples": start_offset,
            "start_s": epoch_start_s,
        },
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan zero-based, sample-exact event epochs and boundary handling. "
            "No signal values or NeuroKit2 imports are required."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--events", help="comma-separated onsets")
    source.add_argument("--events-csv", help="bounded local CSV containing onsets")
    parser.add_argument("--onset-column", default="onset")
    parser.add_argument(
        "--event-unit", choices=("samples", "seconds"), default="samples"
    )
    parser.add_argument("--sampling-rate", type=float, required=True, help="Hz")
    parser.add_argument("--recording-samples", type=int, required=True)
    parser.add_argument("--epoch-start", type=float, required=True, help="seconds")
    parser.add_argument("--epoch-end", type=float, required=True, help="seconds")
    parser.add_argument("--baseline-start", type=float, help="seconds")
    parser.add_argument("--baseline-end", type=float, help="seconds")
    parser.add_argument(
        "--boundary-policy",
        choices=("report", "drop", "error"),
        default="report",
    )
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--deidentified",
        action="store_true",
        help="required with --events-csv",
    )
    parser.add_argument("--max-events", type=int, default=MAX_EVENTS)
    parser.add_argument("--output", help="optional local .json report")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    sampling_rate = finite_float(
        args.sampling_rate,
        name="--sampling-rate",
        minimum=0.01,
        maximum=1_000_000.0,
    )
    epoch_start = finite_float(args.epoch_start, name="--epoch-start")
    epoch_end = finite_float(args.epoch_end, name="--epoch-end")
    baseline_start = (
        finite_float(args.baseline_start, name="--baseline-start")
        if args.baseline_start is not None
        else None
    )
    baseline_end = (
        finite_float(args.baseline_end, name="--baseline-end")
        if args.baseline_end is not None
        else None
    )
    if not 1 <= args.max_events <= MAX_EVENTS:
        raise CliError(f"--max-events must be between 1 and {MAX_EVENTS}")

    if args.events_csv:
        require_deidentified(args.deidentified)
        path = checked_input_file(
            args.events_csv,
            root=args.root,
            suffixes={".csv"},
            max_bytes=MAX_CSV_BYTES,
        )
        data, _, row_count = read_numeric_columns(
            path,
            [args.onset_column],
            max_rows=args.max_events,
        )
        if row_count > args.max_events:
            raise CliError(f"event count exceeds {args.max_events}")
        values = [float(value) for value in data[args.onset_column]]
    else:
        values = _parse_events(args.events)
        if len(values) > args.max_events:
            raise CliError(f"event count exceeds {args.max_events}")

    event_samples = _event_samples(
        values,
        unit=args.event_unit,
        sampling_rate=sampling_rate,
    )
    report = plan(
        event_samples,
        recording_samples=args.recording_samples,
        sampling_rate=sampling_rate,
        epoch_start_s=epoch_start,
        epoch_end_s=epoch_end,
        baseline_start_s=baseline_start,
        baseline_end_s=baseline_end,
        boundary_policy=args.boundary_policy,
    )
    report["input_event_unit"] = args.event_unit
    report["path_redacted"] = True
    emit_json(report, output=args.output, root=args.root, force=args.force)


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
