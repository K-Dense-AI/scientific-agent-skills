#!/usr/bin/env python3
"""Validate bounded multimodal stream schemas and temporal alignment."""

from __future__ import annotations

import argparse
import math
import re
import statistics
from itertools import pairwise
from pathlib import Path
from typing import Any

from _common import (
    MAX_CSV_BYTES,
    MAX_ROWS,
    CliError,
    checked_input_file,
    checked_root,
    emit_json,
    finite_float,
    load_json_object,
    read_numeric_columns,
    require_deidentified,
    run_cli,
    validate_keys,
)

MAX_STREAMS = 16
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
SYNC_METHODS = {
    "hardware_trigger",
    "shared_clock",
    "timestamp",
    "validated_manual",
}


def _stream_profile(
    stream: dict[str, Any],
    *,
    root: Path,
    max_rows: int,
) -> tuple[dict[str, Any], list[str], list[str], list[float]]:
    validate_keys(
        stream,
        allowed={
            "name",
            "path",
            "value_column",
            "time_column",
            "sampling_rate_hz",
            "unit",
            "start_time_s",
        },
        required={"name", "path", "value_column", "sampling_rate_hz", "unit"},
        context="stream",
    )
    name = stream["name"]
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise CliError("stream name must be a short identifier beginning with a letter")
    for key in ("path", "value_column", "unit"):
        if not isinstance(stream[key], str) or not stream[key].strip():
            raise CliError(f"stream {name!r} {key} must be a nonempty string")
    if len(stream["unit"]) > 32:
        raise CliError(f"stream {name!r} unit is too long")
    time_column = stream.get("time_column")
    if time_column is not None and (
        not isinstance(time_column, str) or not time_column.strip()
    ):
        raise CliError(f"stream {name!r} time_column must be a nonempty string")
    if time_column is not None and "start_time_s" in stream:
        raise CliError(
            f"stream {name!r} must not combine time_column with start_time_s"
        )
    declared_rate = finite_float(
        stream["sampling_rate_hz"],
        name=f"{name}.sampling_rate_hz",
        minimum=0.01,
        maximum=1_000_000.0,
    )
    start_time = (
        finite_float(stream["start_time_s"], name=f"{name}.start_time_s")
        if "start_time_s" in stream
        else 0.0
    )
    path = checked_input_file(
        stream["path"],
        root=root,
        suffixes={".csv"},
        max_bytes=MAX_CSV_BYTES,
    )
    columns = [stream["value_column"]]
    if time_column is not None:
        columns.append(time_column)
    values, _, row_count = read_numeric_columns(
        path,
        columns,
        max_rows=max_rows,
        allow_missing=True,
    )
    signal = values[stream["value_column"]]
    missing_count = sum(value is None for value in signal)
    finite_pairs = [
        (previous, current) for previous, current in pairwise(signal)
        if previous is not None and current is not None
    ]
    flat_count = sum(current == previous for previous, current in finite_pairs)
    flat_fraction = (
        flat_count / len(finite_pairs) if finite_pairs else None
    )
    errors: list[str] = []
    warnings: list[str] = []
    observed_rate: float | None = None
    interval_jitter: float | None = None

    if time_column is not None:
        raw_times = values[time_column]
        if any(value is None for value in raw_times):
            errors.append("time column contains missing values")
            times = [float(value) for value in raw_times if value is not None]
        else:
            times = [float(value) for value in raw_times]
        if len(times) >= 2:
            deltas = [current - previous for previous, current in pairwise(times)]
            if any(delta <= 0 for delta in deltas):
                errors.append("timestamps are not strictly increasing")
            positive = [delta for delta in deltas if delta > 0]
            if positive:
                median_delta = statistics.median(positive)
                observed_rate = 1.0 / median_delta
                interval_jitter = max(
                    abs(delta - median_delta) / median_delta for delta in positive
                )
            start_time = times[0]
            end_time = times[-1]
        else:
            errors.append("fewer than two valid timestamps")
            end_time = start_time
    else:
        end_time = start_time + (row_count - 1) / declared_rate
        times = [start_time + index / declared_rate for index in range(row_count)]

    grid_error_samples = (
        max(abs((time - start_time) * declared_rate - index)
            for index, time in enumerate(times))
        if len(times) == row_count else None
    )

    if observed_rate is not None:
        relative_rate_error = abs(observed_rate - declared_rate) / declared_rate
        if relative_rate_error > 0.01:
            errors.append(
                "observed timestamp rate differs from declared rate by more than 1%"
            )
    if interval_jitter is not None and interval_jitter > 0.01:
        warnings.append("timestamp interval jitter exceeds 1% of the median")
    if grid_error_samples is not None and grid_error_samples > 0.5:
        warnings.append("timestamps deviate more than half a sample from the declared grid")
    if missing_count:
        warnings.append(f"{missing_count} signal values are missing")
    if flat_fraction is not None and flat_fraction > 0.20:
        warnings.append("more than 20% of adjacent finite signal values are identical")

    profile = {
        "declared_sampling_rate_hz": declared_rate,
        "duration_s": max(0.0, end_time - start_time),
        "end_time_s": end_time,
        "flat_transition_fraction": flat_fraction,
        "missing_count": missing_count,
        "name": name,
        "observed_sampling_rate_hz": observed_rate,
        "path_redacted": True,
        "row_count": row_count,
        "start_time_s": start_time,
        "timestamp_maximum_relative_jitter": interval_jitter,
        "timestamp_maximum_grid_error_samples": grid_error_samples,
        "time_basis": "observed" if time_column is not None else "declared_uniform_grid",
        "unit": stream["unit"],
    }
    return profile, errors, warnings, times


def validate_manifest(
    document: dict[str, Any],
    *,
    root: Path,
    max_rows: int,
) -> dict[str, Any]:
    validate_keys(
        document,
        allowed={"schema_version", "streams", "alignment"},
        required={"schema_version", "streams", "alignment"},
        context="manifest",
    )
    if document["schema_version"] != "1.0":
        raise CliError("schema_version must be '1.0'")
    streams = document["streams"]
    if not isinstance(streams, list) or not 1 <= len(streams) <= MAX_STREAMS:
        raise CliError(f"streams must contain 1 to {MAX_STREAMS} objects")
    if any(not isinstance(stream, dict) for stream in streams):
        raise CliError("every stream must be an object")
    alignment = document["alignment"]
    if not isinstance(alignment, dict):
        raise CliError("alignment must be an object")
    validate_keys(
        alignment,
        allowed={
            "reference_stream",
            "synchronization",
            "max_start_offset_ms",
            "minimum_overlap_s",
        },
        required={
            "reference_stream",
            "synchronization",
            "max_start_offset_ms",
            "minimum_overlap_s",
        },
        context="alignment",
    )
    if alignment["synchronization"] not in SYNC_METHODS:
        raise CliError(
            "alignment.synchronization must be one of: "
            + ", ".join(sorted(SYNC_METHODS))
        )
    max_offset_ms = finite_float(
        alignment["max_start_offset_ms"],
        name="alignment.max_start_offset_ms",
        minimum=0.0,
        maximum=60_000.0,
    )
    minimum_overlap_s = finite_float(
        alignment["minimum_overlap_s"],
        name="alignment.minimum_overlap_s",
        minimum=0.0,
        maximum=31_536_000.0,
    )

    profiles: list[dict[str, Any]] = []
    timestamps: dict[str, list[float]] = {}
    errors: list[str] = []
    warnings: list[str] = []
    for index, stream in enumerate(streams, start=1):
        try:
            profile, stream_errors, stream_warnings, stream_times = _stream_profile(
                stream, root=root, max_rows=max_rows
            )
        except CliError as exc:
            raise CliError(f"stream {index}: {exc}") from exc
        profiles.append(profile)
        timestamps[profile["name"]] = stream_times
        errors.extend(f"{profile['name']}: {message}" for message in stream_errors)
        warnings.extend(f"{profile['name']}: {message}" for message in stream_warnings)

    names = [profile["name"] for profile in profiles]
    if len(names) != len(set(names)):
        raise CliError("stream names must be unique")
    reference_name = alignment["reference_stream"]
    if reference_name not in names:
        raise CliError("alignment.reference_stream is not a stream name")
    reference = next(
        profile for profile in profiles if profile["name"] == reference_name
    )

    start_offsets_ms: dict[str, float] = {}
    for profile in profiles:
        offset_ms = (profile["start_time_s"] - reference["start_time_s"]) * 1000.0
        start_offsets_ms[profile["name"]] = offset_ms
        if abs(offset_ms) > max_offset_ms:
            errors.append(
                f"{profile['name']}: start offset {offset_ms:.6g} ms exceeds "
                f"{max_offset_ms:.6g} ms"
            )
    overlap_start = max(profile["start_time_s"] for profile in profiles)
    overlap_end = min(profile["end_time_s"] for profile in profiles)
    overlap_s = max(0.0, overlap_end - overlap_start)
    if overlap_s < minimum_overlap_s:
        errors.append(
            f"common overlap {overlap_s:.6g} s is below {minimum_overlap_s:.6g} s"
        )

    rates = [profile["declared_sampling_rate_hz"] for profile in profiles]
    counts = [profile["row_count"] for profile in profiles]
    same_rate = all(
        math.isclose(rate, rates[0], rel_tol=1e-9, abs_tol=1e-12) for rate in rates[1:]
    )
    same_count = all(count == counts[0] for count in counts[1:])
    no_missing = all(profile["missing_count"] == 0 for profile in profiles)
    starts_within_sample = all(
        abs(start_offsets_ms[profile["name"]])
        <= (500.0 / profile["declared_sampling_rate_hz"])
        for profile in profiles
    )
    maximum_sample_offsets_ms: dict[str, float | None] = {}
    reference_times = timestamps[reference_name]
    for profile in profiles:
        times = timestamps[profile["name"]]
        maximum_sample_offsets_ms[profile["name"]] = (
            max(abs(time - reference_time) * 1000.0
                for time, reference_time in zip(times, reference_times))
            if same_rate and same_count and len(times) == len(reference_times)
            and len(times) == profile["row_count"] else None
        )
    all_samples_aligned = all(
        offset is not None and offset <= 500.0 / rates[0]
        for offset in maximum_sample_offsets_ms.values()
    )
    uniform_grids = all(
        profile["timestamp_maximum_grid_error_samples"] is not None
        and profile["timestamp_maximum_grid_error_samples"] <= 0.5
        for profile in profiles
    )
    bio_process_compatible = (
        same_rate and same_count and no_missing and starts_within_sample and not errors
        and all_samples_aligned and uniform_grids
    )
    if not same_rate:
        warnings.append(
            "native sampling rates differ; process at native rates, align clocks, "
            "then resample continuous channels to an explicit common grid"
        )
    if not bio_process_compatible:
        warnings.append(
            "do not pass these streams directly to bio_process(); NeuroKit2 "
            "0.2.13 does not synchronize or automatically resample inputs"
        )

    return {
        "alignment": {
            "common_overlap_s": overlap_s,
            "max_start_offset_ms": max_offset_ms,
            "minimum_overlap_s": minimum_overlap_s,
            "reference_stream": reference_name,
            "start_offsets_ms": start_offsets_ms,
            "maximum_sample_offsets_ms": maximum_sample_offsets_ms,
            "grid_tolerance_samples": 0.5,
            "synchronization": alignment["synchronization"],
        },
        "bio_process_direct_input_compatible": bio_process_compatible,
        "errors": errors,
        "path_redacted": True,
        "schema_version": "1.0",
        "streams": profiles,
        "valid": not errors,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a strict JSON manifest of bounded local biosignal CSV "
            "streams, units, clocks, rates, starts, overlap, and missingness."
        )
    )
    parser.add_argument("--manifest", required=True, help="local .json manifest")
    parser.add_argument("--root", default=".", help="existing local I/O boundary")
    parser.add_argument("--max-rows", type=int, default=MAX_ROWS)
    parser.add_argument(
        "--deidentified",
        action="store_true",
        help="confirm direct and reviewed quasi-identifiers were removed",
    )
    parser.add_argument("--output", help="optional local .json report")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    require_deidentified(args.deidentified)
    if not 1 <= args.max_rows <= MAX_ROWS:
        raise CliError(f"--max-rows must be between 1 and {MAX_ROWS}")
    root = checked_root(args.root)
    document = load_json_object(args.manifest, root=root)
    report = validate_manifest(document, root=root, max_rows=args.max_rows)
    emit_json(report, output=args.output, root=root, force=args.force)
    if not report["valid"]:
        raise CliError(
            f"multimodal validation failed with {len(report['errors'])} error(s)"
        )


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
