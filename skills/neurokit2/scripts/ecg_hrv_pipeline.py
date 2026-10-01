#!/usr/bin/env python3
"""Run a bounded ECG processing and duration-aware HRV workflow."""

from __future__ import annotations

import argparse
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
    parse_name_list,
    read_numeric_columns,
    require_deidentified,
    run_cli,
    sha256_bytes,
    write_csv,
)

ECG_METHODS = (
    "neurokit",
    "pantompkins1985",
    "hamilton2002",
    "elgendi2010",
    "engzeemod2012",
)
HRV_DOMAINS = {"time", "frequency", "nonlinear"}


def _row_to_json(frame: Any) -> dict[str, float | int | None]:
    if len(frame) != 1:
        raise CliError("expected one-row HRV output")
    return {str(column): json_number(frame.iloc[0][column]) for column in frame.columns}


def _summary(values: Any) -> dict[str, float | int | None]:
    finite = values[values.notna()] if hasattr(values, "notna") else values
    if len(finite) == 0:
        return {"count": 0, "maximum": None, "mean": None, "minimum": None}
    return {
        "count": len(finite),
        "maximum": json_number(finite.max()),
        "mean": json_number(finite.mean()),
        "minimum": json_number(finite.min()),
    }


def _artifact_counts(info: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for name in ("ectopic", "missed", "extra", "longshort"):
        value = info.get(f"ECG_fixpeaks_{name}", [])
        try:
            result[name] = len(value)
        except TypeError:
            result[name] = 0
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Process a bounded deidentified ECG CSV or a reproducible synthetic "
            "signal with NeuroKit2 0.2.13, report peak correction and quality, "
            "and gate HRV domains by duration and beat count."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="local .csv input")
    source.add_argument("--synthetic", action="store_true")
    parser.add_argument("--column", default="ECG")
    parser.add_argument("--sampling-rate", type=float, required=True, help="Hz")
    parser.add_argument("--method", choices=ECG_METHODS, default="neurokit")
    parser.add_argument(
        "--domains",
        default="time",
        help="comma-separated subset of time,frequency,nonlinear",
    )
    parser.add_argument(
        "--duration", type=float, default=60.0, help="synthetic seconds"
    )
    parser.add_argument("--heart-rate", type=float, default=70.0, help="synthetic BPM")
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
        minimum=20.0,
        maximum=20_000.0,
    )
    domains = set(parse_name_list(args.domains, name="--domains"))
    unknown = sorted(domains - HRV_DOMAINS)
    if unknown:
        raise CliError(f"unknown HRV domains: {', '.join(unknown)}")
    if not domains:
        raise CliError("select at least one HRV domain")
    if not 1 <= args.max_rows <= MAX_ROWS:
        raise CliError(f"--max-rows must be between 1 and {MAX_ROWS}")
    if not 0 <= args.seed < 2**32:
        raise CliError("--seed must be an unsigned 32-bit integer")

    import neurokit2 as nk
    import numpy as np

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
        ecg = np.asarray(selected[args.column], dtype=float)
        source = "deidentified_local_csv"
    else:
        duration = finite_float(
            args.duration,
            name="--duration",
            minimum=5.0,
            maximum=3600.0,
        )
        heart_rate = finite_float(
            args.heart_rate,
            name="--heart-rate",
            minimum=20.0,
            maximum=240.0,
        )
        if not sampling_rate.is_integer():
            raise CliError(
                "--sampling-rate must be an integer for NeuroKit2 synthetic ECG"
            )
        row_count = round(duration * sampling_rate)
        if not 1 <= row_count <= args.max_rows:
            raise CliError(f"synthetic row count must be between 1 and {args.max_rows}")
        try:
            ecg = nk.ecg_simulate(
                duration=row_count / sampling_rate,
                length=row_count,
                sampling_rate=int(sampling_rate),
                heart_rate=heart_rate,
                random_state=args.seed,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            raise CliError(f"synthetic ECG generation failed: {exc}") from exc
        row_count = len(ecg)
        source = "neurokit2_synthetic"

    duration_s = len(ecg) / sampling_rate
    if duration_s < 5:
        raise CliError("ECG must contain at least 5 seconds for this pipeline")
    try:
        signals, info = nk.ecg_process(
            ecg,
            sampling_rate=sampling_rate,
            method=args.method,
        )
    except (TypeError, ValueError, RuntimeError, IndexError) as exc:
        raise CliError(f"ECG processing failed: {exc}") from exc
    peaks = info.get("ECG_R_Peaks")
    if peaks is None or len(peaks) < 3:
        raise CliError("fewer than three R-peaks were detected")
    beat_count = len(peaks)
    peak_span_s = float(peaks[-1] - peaks[0]) / sampling_rate

    warnings: list[str] = []
    hrv: dict[str, dict[str, float | int | None]] = {}
    if "time" in domains:
        if beat_count < 20:
            warnings.append("time-domain HRV skipped: fewer than 20 detected beats")
        else:
            try:
                hrv["time"] = _row_to_json(
                    nk.hrv_time(info, sampling_rate=sampling_rate)
                )
            except (TypeError, ValueError, RuntimeError, ZeroDivisionError) as exc:
                warnings.append(f"time-domain HRV failed: {exc}")
        if peak_span_s < 300:
            warnings.append(
                "time-domain HRV is shorter than the conventional 5-minute "
                "short-term recording; metric-specific validation is required"
            )
    if "frequency" in domains:
        if peak_span_s < 120 or beat_count < 50:
            warnings.append(
                "frequency-domain HRV skipped: require at least 120 seconds between "
                "first and last corrected peaks and "
                "50 detected beats in this conservative CLI"
            )
        else:
            try:
                hrv["frequency"] = _row_to_json(
                    nk.hrv_frequency(
                        info, sampling_rate=sampling_rate,
                        psd_method="welch", normalize=False, interpolation_rate=4,
                    )
                )
            except (TypeError, ValueError, RuntimeError, ZeroDivisionError) as exc:
                warnings.append(f"frequency-domain HRV failed: {exc}")
            warnings.append(
                "ULF is not validated by this bounded pipeline; VLF interpretation "
                "from short records is uncertain. Frequency band powers use "
                "normalize=False (ms^2), not maximum-PSD normalization."
            )
            if peak_span_s < 300:
                warnings.append(
                    "frequency-domain HRV is below the conventional 5-minute "
                    "short-term window; do not interpret VLF/ULF and justify bands"
                )
    if "nonlinear" in domains:
        if beat_count < 100:
            warnings.append(
                "nonlinear HRV skipped: fewer than 100 detected beats; many "
                "entropy/fractal metrics need substantially more"
            )
        else:
            try:
                hrv["nonlinear"] = _row_to_json(
                    nk.hrv_nonlinear(info, sampling_rate=sampling_rate)
                )
            except (TypeError, ValueError, RuntimeError, ZeroDivisionError) as exc:
                warnings.append(f"nonlinear HRV failed: {exc}")

    artifact_counts = _artifact_counts(info)
    corrected_total = sum(artifact_counts.values())
    if corrected_total:
        warnings.append(
            "R-peak corrections were applied by ecg_process(); inspect the raw "
            "trace, uncorrected peaks, and correction categories"
        )
    if source == "deidentified_local_csv":
        warnings.append(
            "input amplitude units are not inferred; record sensor units, lead, "
            "gain, filters, and clock metadata separately"
        )

    report: dict[str, Any] = {
        "artifact_correction": {
            "algorithm": "Lipponen-Tarvainen via ecg_process(correct_artifacts=True)",
            "category_counts": artifact_counts,
            "corrected_event_count_sum": corrected_total,
            "uncorrected_peak_count": len(info.get("ECG_R_Peaks_Uncorrected", peaks)),
        },
        "detected_r_peaks": beat_count,
        "duration_s": duration_s,
        "hrv_peak_span_s": peak_span_s,
        "hrv_interval_validity": "not established by automatic peak correction",
        "hrv": hrv,
        "hrv_frequency_settings": {
            "psd_method": "welch",
            "normalize": False,
            "interpolation_rate_hz": 4,
        } if "frequency" in domains else None,
        "hrv_requested_domains": sorted(domains),
        "ecg_method": args.method,
        "neurokit2_version": installed,
        "output_schema_observed": {
            "info_keys": sorted(str(key) for key in info),
            "signal_columns": [str(column) for column in signals.columns],
        },
        "path_redacted": True,
        "quality": _summary(signals["ECG_Quality"]),
        "research_use_only": True,
        "row_count": row_count,
        "sampling_rate_hz": sampling_rate,
        "source": source,
        "warning": (
            "This output is for research and education, not diagnosis, patient "
            "monitoring, or medical-device validation. Validate the detector, "
            "sensor, population, protocol, and artifact policy for the intended use."
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
