#!/usr/bin/env python3
"""Estimate bounded FluidSim grid memory and output storage envelopes."""

from __future__ import annotations

import argparse
import math
from typing import Any

try:
    from ._common import (
        GIB,
        MAX_RECORDS,
        ToolError,
        bounded_int,
        checked_input,
        emit_json,
        fail_json,
        finite_float,
        load_json,
    )
    from ._schema import (
        CONFIG_SOLVER_DIMENSIONS,
        STATE_FIELD_COUNTS,
        normalized_copy,
    )
except ImportError:  # Direct script execution.
    from _common import (
        GIB,
        MAX_RECORDS,
        ToolError,
        bounded_int,
        checked_input,
        emit_json,
        fail_json,
        finite_float,
        load_json,
    )
    from _schema import (
        CONFIG_SOLVER_DIMENSIONS,
        STATE_FIELD_COUNTS,
        normalized_copy,
    )


TOOL = "fluidsim-grid-resource-estimator"


def _records(t_end: float, period: float) -> int:
    if period <= 0:
        return 0
    ratio = t_end / period
    if not math.isfinite(ratio) or ratio > MAX_RECORDS - 2:
        raise ToolError("predicted output records exceed the planning limit; reduce duration or save frequency")
    return int(math.floor(ratio + 1e-12)) + 2


def estimate(
    config: dict[str, Any],
    *,
    precision_bytes: int,
    workspace_factor: float,
    safety_factor: float,
    compression_ratio: float,
) -> dict[str, Any]:
    solver = config["solver"]
    dimension = CONFIG_SOLVER_DIMENSIONS[solver]
    parameters = config["parameters"]
    oper = parameters["oper"]
    axes = ("x", "y", "z")[:dimension]
    shape = [int(oper[f"n{axis}"]) for axis in axes]
    grid_points = math.prod(shape)
    # Sequential FluidFFT stores physical (y, x) / (z, y, x) and reduces x.
    spectral_shape = [*reversed(shape[1:]), shape[0] // 2 + 1]
    spectral_points = math.prod(spectral_shape)

    real_fields, complex_fields = STATE_FIELD_COUNTS[solver]
    real_state_bytes = grid_points * real_fields * precision_bytes
    complex_state_bytes = spectral_points * complex_fields * 2 * precision_bytes
    resident_state_bytes = real_state_bytes + complex_state_bytes
    peak_bytes = math.ceil(
        resident_state_bytes * workspace_factor * safety_factor
    )

    output = parameters.get("output", {})
    periods = output.get("periods_save", {})
    time = parameters["time_stepping"]
    t_end = float(time["t_end"])
    state_records = (
        _records(t_end, float(periods.get("phys_fields", 0.0)))
        if output.get("HAS_TO_SAVE")
        else 0
    )
    spectra_records = (
        _records(t_end, float(periods.get("spectra", 0.0)))
        if output.get("HAS_TO_SAVE")
        else 0
    )
    budget_records = (
        _records(
            t_end,
            float(periods.get("spect_energy_budg", 0.0)),
        )
        if output.get("HAS_TO_SAVE")
        else 0
    )
    scalar_records = (
        _records(t_end, float(periods.get("spatial_means", 0.0)))
        if output.get("HAS_TO_SAVE")
        else 0
    )

    snapshot_bytes = math.ceil(real_state_bytes / compression_ratio)
    state_storage = state_records * snapshot_bytes
    bins = sum(size // 2 + 1 for size in shape)
    spectra_storage = math.ceil(
        spectra_records * max(1, bins) * max(4, real_fields) * 8
        / compression_ratio
    )
    budget_storage = math.ceil(
        budget_records * max(1, bins) * max(6, complex_fields) * 8
        / compression_ratio
    )
    scalar_storage = scalar_records * 16 * 32
    metadata_storage = 4 * 1024**2 if output.get("HAS_TO_SAVE") else 0
    storage_bytes = (
        state_storage
        + spectra_storage
        + budget_storage
        + scalar_storage
        + metadata_storage
    )
    estimated_files = (
        state_records
        + (2 if spectra_records else 0)
        + (1 if budget_records else 0)
        + (1 if scalar_records else 0)
        + (4 if output.get("HAS_TO_SAVE") else 0)
    )

    resources = config["resources"]
    ram_bytes = float(resources["ram_gib"]) * GIB
    disk_bytes = float(resources["disk_gib"]) * GIB
    ranks = int(resources["mpi_ranks"])
    memory_ok = peak_bytes <= ram_bytes
    storage_ok = storage_bytes <= disk_bytes
    files_ok = estimated_files <= int(resources["max_output_files"])
    unmodeled = sorted(
        name for name, period in periods.items()
        if period > 0 and name not in {"phys_fields", "spectra", "spect_energy_budg", "spatial_means"}
    ) if output.get("HAS_TO_SAVE") else []
    time_bounded = bool(time["USE_T_END"])
    return {
        "assumptions": {
            "compression_ratio": compression_ratio,
            "complex_fields": complex_fields,
            "precision_bytes": precision_bytes,
            "real_fields": real_fields,
            "safety_factor": safety_factor,
            "spectra_and_budget_layout_is_approximate": True,
            "workspace_factor": workspace_factor,
            "unmodeled_enabled_outputs": unmodeled,
        },
        "declared_bounds": {
            "cpu_cores": resources["cpu_cores"],
            "disk_gib": resources["disk_gib"],
            "max_output_files": resources["max_output_files"],
            "mpi_ranks": ranks,
            "ram_gib": resources["ram_gib"],
            "threads_per_rank": resources["threads_per_rank"],
            "wall_time_minutes": resources["wall_time_minutes"],
        },
        "estimates": {
            "estimated_output_files": estimated_files,
            "idealized_peak_bytes_per_rank": math.ceil(peak_bytes / ranks),
            "peak_memory_bytes": peak_bytes,
            "peak_memory_gib": peak_bytes / GIB,
            "resident_state_bytes": resident_state_bytes,
            "state_snapshot_bytes": snapshot_bytes,
            "state_snapshots": state_records,
            "storage_bytes": storage_bytes,
            "storage_gib": storage_bytes / GIB,
        },
        "grid": {
            "dimensions": dimension,
            "points": grid_points,
            "shape": shape,
            "spectral_points_estimate": spectral_points,
            "spectral_shape_estimate": spectral_shape,
        },
        "limits": {
            "files_within_bound": files_ok,
            "memory_within_bound": memory_ok,
            "storage_within_bound": storage_ok,
        },
        "notes": [
            "This is an approximate planning model, not a hard memory or storage bound.",
            "FFT decomposition, backend buffers, Python overhead, diagnostics, and MPI imbalance are backend-specific.",
            "Runtime is not inferred from grid size; benchmark a tiny representative pilot on the target machine.",
            "A resource fit does not establish numerical convergence or physical validity.",
        ],
        "ok": memory_ok and storage_ok and files_ok and time_bounded and not unmodeled,
        "coverage": {
            "output_model_complete": not unmodeled,
            "time_horizon_bounded": time_bounded,
        },
        "runtime_estimated": False,
        "solver": solver,
        "tool": TOOL,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate an approximate FluidSim memory/storage envelope from strict "
            "local JSON. No arrays are allocated and no package is imported."
        )
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--precision-bytes",
        type=int,
        choices=(4, 8),
        default=8,
        help="Real scalar bytes in planning model (default: 8).",
    )
    parser.add_argument(
        "--workspace-factor",
        type=float,
        default=8.0,
        help="Resident-state multiplier, 2..64 (default: 8).",
    )
    parser.add_argument(
        "--safety-factor",
        type=float,
        default=1.5,
        help="Additional margin, 1..10 (default: 1.5).",
    )
    parser.add_argument(
        "--compression-ratio",
        type=float,
        default=1.0,
        help="Optimistic output compression ratio, 1..20 (default: 1).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bounded_int(
            args.precision_bytes,
            name="precision_bytes",
            minimum=4,
            maximum=8,
        )
        workspace = finite_float(
            args.workspace_factor,
            name="workspace_factor",
            minimum=2.0,
            maximum=64.0,
        )
        safety = finite_float(
            args.safety_factor,
            name="safety_factor",
            minimum=1.0,
            maximum=10.0,
        )
        compression = finite_float(
            args.compression_ratio,
            name="compression_ratio",
            minimum=1.0,
            maximum=20.0,
        )
        path = checked_input(
            args.config,
            root=args.root,
            kind="file",
            suffixes={".json"},
        )
        config = normalized_copy(load_json(path))
        report = estimate(
            config,
            precision_bytes=args.precision_bytes,
            workspace_factor=float(workspace),
            safety_factor=float(safety),
            compression_ratio=float(compression),
        )
        report["commands_executed"] = False
        report["arrays_allocated"] = False
        emit_json(report)
        return 0 if report["ok"] else 2
    except (OSError, ToolError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    raise SystemExit(main())
