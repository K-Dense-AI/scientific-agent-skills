#!/usr/bin/env python3
"""Run an explicit, bounded EDA cleaning/decomposition/SCR workflow."""

from __future__ import annotations

import argparse
import statistics
from typing import Any

from _common import (
    MAX_CSV_BYTES,
    MAX_ROWS,
    NEUROKIT2_VERSION,
    PINNED_INSTALL,
    CliError,
    checked_input_file,
    dataframe_rows,
    emit_json,
    finite_float,
    json_number,
    read_numeric_columns,
    require_deidentified,
    run_cli,
    sha256_bytes,
    write_csv,
)

CLEAN_METHODS = ("neurokit", "biosppy", "none")
PHASIC_METHODS = ("highpass", "smoothmedian", "cvxeda", "sparseda")
PEAK_METHODS = ("neurokit", "gamboa2008", "kim2004", "vanhalem2020", "nabian2018")


def _finite_values(values: Any) -> list[float]:
    result: list[float] = []
    for value in values:
        number = json_number(value)
        if number is not None:
            result.append(float(number))
    return result


def _stats(values: Any) -> dict[str, float | int | None]:
    finite = _finite_values(values)
    return {
        "count": len(finite),
        "maximum": max(finite) if finite else None,
        "mean": statistics.fmean(finite) if finite else None,
        "median": statistics.median(finite) if finite else None,
        "minimum": min(finite) if finite else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Clean, explicitly decompose, and detect SCRs in bounded "
            "deidentified EDA CSV data or a reproducible synthetic signal using "
            "NeuroKit2 0.2.13."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="local .csv input")
    source.add_argument("--synthetic", action="store_true")
    parser.add_argument("--column", default="EDA")
    parser.add_argument("--sampling-rate", type=float, required=True, help="Hz")
    parser.add_argument("--clean-method", choices=CLEAN_METHODS, default="neurokit")
    parser.add_argument("--phasic-method", choices=PHASIC_METHODS, default="highpass")
    parser.add_argument("--peak-method", choices=PEAK_METHODS, default="neurokit")
    parser.add_argument(
        "--amplitude-min",
        type=float,
        default=0.1,
        help="relative-to-largest SCR threshold for neurokit/kim2004",
    )
    parser.add_argument(
        "--sympathetic-method",
        choices=("none", "posada", "ghiasi"),
        default="none",
    )
    parser.add_argument("--unit", default="unspecified")
    parser.add_argument(
        "--duration", type=float, default=60.0, help="synthetic seconds"
    )
    parser.add_argument("--scr-number", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--root", default=".")
    parser.add_argument("--max-rows", type=int, default=MAX_ROWS)
    parser.add_argument(
        "--deidentified",
        action="store_true",
        help="required with --input",
    )
    parser.add_argument("--signals-output", help="optional processed local .csv")
    parser.add_argument("--output", help="optional local .json report")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    sampling_rate = finite_float(
        args.sampling_rate,
        name="--sampling-rate",
        minimum=1.0,
        maximum=5000.0,
    )
    amplitude_min = finite_float(
        args.amplitude_min,
        name="--amplitude-min",
        minimum=0.0,
        maximum=1.0,
    )
    if not 1 <= args.max_rows <= MAX_ROWS:
        raise CliError(f"--max-rows must be between 1 and {MAX_ROWS}")
    if not 0 <= args.scr_number <= 10_000:
        raise CliError("--scr-number must be between 0 and 10000")
    if not 0 <= args.seed < 2**32:
        raise CliError("--seed must be an unsigned 32-bit integer")
    if not args.unit or len(args.unit) > 32:
        raise CliError("--unit must be a nonempty string of at most 32 characters")

    import neurokit2 as nk
    import numpy as np
    import pandas as pd

    installed = str(nk.__version__)
    if installed != NEUROKIT2_VERSION:
        raise CliError(
            f"this reproducible workflow requires NeuroKit2 {NEUROKIT2_VERSION}; "
            f"found {installed}. Install with: {PINNED_INSTALL}"
        )

    if args.input:
        require_deidentified(args.deidentified)
        path = checked_input_file(
            args.input,
            root=args.root,
            suffixes={".csv"},
            max_bytes=MAX_CSV_BYTES,
        )
        selected, _, row_count = read_numeric_columns(
            path,
            [args.column],
            max_rows=args.max_rows,
        )
        raw = np.asarray(selected[args.column], dtype=float)
        source = "deidentified_local_csv"
    else:
        duration = finite_float(
            args.duration,
            name="--duration",
            minimum=5.0,
            maximum=3600.0,
        )
        if not sampling_rate.is_integer():
            raise CliError(
                "--sampling-rate must be an integer for NeuroKit2 synthetic EDA"
            )
        row_count = round(duration * sampling_rate)
        if not 1 <= row_count <= args.max_rows:
            raise CliError(f"synthetic row count must be between 1 and {args.max_rows}")
        try:
            raw = nk.eda_simulate(
                duration=row_count / sampling_rate,
                length=row_count,
                sampling_rate=int(sampling_rate),
                scr_number=args.scr_number,
                random_state=args.seed,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            raise CliError(f"synthetic EDA generation failed: {exc}") from exc
        row_count = len(raw)
        source = "neurokit2_synthetic"

    duration_s = len(raw) / sampling_rate
    try:
        clean = nk.eda_clean(
            raw,
            sampling_rate=sampling_rate,
            method=args.clean_method,
        )
        components = nk.eda_phasic(
            clean,
            sampling_rate=sampling_rate,
            method=args.phasic_method,
        )
        peak_signals, peak_info = nk.eda_peaks(
            components["EDA_Phasic"],
            sampling_rate=sampling_rate,
            method=args.peak_method,
            amplitude_min=amplitude_min,
        )
    except (TypeError, ValueError, RuntimeError, IndexError) as exc:
        raise CliError(f"EDA processing failed: {exc}") from exc

    signals = pd.concat(
        [
            pd.DataFrame({"EDA_Raw": raw, "EDA_Clean": clean}),
            components.reset_index(drop=True),
            peak_signals.reset_index(drop=True),
        ],
        axis=1,
    )
    amplitudes = _finite_values(peak_info.get("SCR_Amplitude", []))
    scr_count = len(peak_info.get("SCR_Peaks", []))
    warnings: list[str] = []
    threshold_applied = args.peak_method in {"neurokit", "kim2004"}
    if not threshold_applied:
        warnings.append(
            "--amplitude-min is ignored by the selected NeuroKit2 peak detector"
        )
    if args.phasic_method == "cvxeda":
        warnings.append(
            "cvxEDA requires the optional cvxopt dependency; report its version "
            "and validate decomposition parameters"
        )
    if source == "deidentified_local_csv" and args.unit == "unspecified":
        warnings.append(
            "EDA units were not declared; do not interpret amplitudes as "
            "microsiemens without acquisition metadata"
        )
    if scr_count == 0:
        warnings.append(
            "no SCR peaks were detected; inspect signal orientation and quality"
        )
    sympathetic: dict[str, float | int | None] | None = None
    if args.sympathetic_method != "none":
        if duration_s <= 64:
            warnings.append(
                "EDA sympathetic index skipped: this CLI requires more than 64 seconds"
            )
        else:
            try:
                result = nk.eda_sympathetic(
                    clean,
                    sampling_rate=sampling_rate,
                    method=args.sympathetic_method,
                    show=False,
                )
                sympathetic = {
                    str(key): json_number(value) for key, value in result.items()
                }
            except (TypeError, ValueError, RuntimeError, ZeroDivisionError) as exc:
                warnings.append(f"EDA sympathetic index failed: {exc}")

    report: dict[str, Any] = {
        "duration_s": duration_s,
        "input_unit": args.unit,
        "methods": {
            "clean": args.clean_method,
            "decomposition": args.phasic_method,
            "peak_detection": args.peak_method,
            "peak_threshold_relative_to_largest": (
                amplitude_min if threshold_applied else None
            ),
            "peak_threshold_applied": threshold_applied,
            "peak_threshold_reference": {
                "neurokit": "maximum_candidate_prominence",
                "kim2004": "maximum_candidate_phasic_peak_height",
            }.get(args.peak_method),
            "sympathetic": args.sympathetic_method,
        },
        "neurokit2_version": installed,
        "output_schema_observed": {
            "info_keys": sorted(str(key) for key in peak_info),
            "signal_columns": [str(column) for column in signals.columns],
        },
        "path_redacted": True,
        "research_use_only": True,
        "row_count": row_count,
        "sampling_rate_hz": sampling_rate,
        "scr": {
            "amplitude": _stats(amplitudes),
            "count": scr_count,
        },
        "source": source,
        "sympathetic": sympathetic,
        "tonic": _stats(signals["EDA_Tonic"]),
        "warning": (
            "EDA features are method-, sensor-, site-, unit-, and population-dependent. "
            "This output is not diagnosis, monitoring, or medical-device validation."
        ),
        "warnings": warnings,
    }
    if args.signals_output:
        payload = write_csv(
            args.signals_output,
            [str(column) for column in signals.columns],
            dataframe_rows(signals),
            root=args.root,
            force=args.force,
        )
        report["signals_csv"] = {
            "path_redacted": True,
            "sha256": sha256_bytes(payload),
        }
    emit_json(report, output=args.output, root=args.root, force=args.force)


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
