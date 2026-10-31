#!/usr/bin/env python3
"""Validated regular-grid CSV forecasting using the Apache-licensed TimesFM 2.5.

Targets timesfm==3.0.2. Forecasts are nominal quantiles, not calibrated intervals.
No model is downloaded until CSV validation and the resource preflight complete.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

MODEL_ID = "google/timesfm-2.5-200m-pytorch"
MODEL_REVISION = "1d952420fba87f3c6dee4f240de0f1a0fbc790e3"


def run_preflight() -> dict:
    """Run the advisory resource check; stop on a failed resource threshold."""
    from check_system import run_checks
    report = run_checks("v2.5")
    if not report.passed:
        print(f"[ERROR] System check FAILED: {report.verdict_detail}")
        sys.exit(1)
    return report.to_dict()


def forecast_config(horizon: int = 256, max_context: int = 1024,
                    batch_size: int = 1, nonnegative: bool = False,
                    return_backcast: bool = False):
    """Validate and construct the release's supported quantile-head config."""
    if not 1 <= horizon <= 1024:
        raise ValueError("horizon must be 1..1024 with the 2.5 continuous quantile head")
    if max_context < 1 or batch_size < 1:
        raise ValueError("max_context and batch_size must be positive")
    context = ((max_context + 31) // 32) * 32
    max_horizon = ((horizon + 127) // 128) * 128
    if context + max_horizon > 16384:
        raise ValueError("patch-rounded context + horizon must be <= 16384")
    import timesfm
    return timesfm.ForecastConfig(
        max_context=context, max_horizon=max_horizon,
        normalize_inputs=True, per_core_batch_size=batch_size,
        use_continuous_quantile_head=True, force_flip_invariance=True,
        infer_is_positive=nonnegative, fix_quantile_crossing=True,
        return_backcast=return_backcast,
    )


def load_model(batch_size: int = 1, horizon: int = 256, max_context: int = 1024,
               nonnegative: bool = False, revision: str = MODEL_REVISION,
               return_backcast: bool = False):
    """Load pinned safetensors, without torch.compile startup overhead."""
    import timesfm
    config = forecast_config(horizon, max_context, batch_size, nonnegative, return_backcast)
    print(f"Loading {MODEL_ID} at {revision}...")
    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
        MODEL_ID, revision=revision, torch_compile=False,
    )
    model.compile(config)
    return model


def regular_frequency(dates: pd.Series, freq: str | None = None) -> str:
    """Require a sorted unique complete grid; never invent a missing timestamp."""
    idx = pd.DatetimeIndex(dates)
    if idx.empty or idx.hasnans or not idx.is_unique or not idx.is_monotonic_increasing:
        raise ValueError("dates must be nonempty, finite, unique, and increasing")
    if freq is None:
        freq = pd.infer_freq(idx) if len(idx) >= 3 else None
    if freq is None:
        raise ValueError("cannot infer a regular time grid; supply --freq and repair gaps")
    expected = pd.date_range(idx[0], periods=len(idx), freq=freq)
    if not idx.equals(expected):
        raise ValueError("dates do not match the declared regular grid")
    return pd.tseries.frequencies.to_offset(freq).freqstr


def load_csv(path: str, date_col: str | None = None,
             value_cols: list[str] | None = None, freq: str | None = None
             ) -> tuple[pd.DataFrame, list[str], str | None]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle), [])
    if len(header) != len(set(header)):
        raise ValueError("duplicate CSV column names are not allowed")
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("CSV has no observations")
    if date_col:
        if date_col not in df:
            raise ValueError(f"date column {date_col!r} not found")
        df[date_col] = pd.to_datetime(df[date_col], errors="raise")
        df = df.sort_values(date_col, kind="stable").reset_index(drop=True)
        df.attrs["frequency"] = regular_frequency(df[date_col], freq)
    elif freq:
        raise ValueError("--freq requires --date-col")
    if value_cols is None:
        value_cols = [c for c in df.select_dtypes(include=[np.number]) if c != date_col]
    if not value_cols or len(value_cols) != len(set(value_cols)):
        raise ValueError("select at least one unique numeric value column")
    for col in value_cols:
        if col not in df or col == date_col:
            raise ValueError(f"value column {col!r} is missing or is the date column")
        df[col] = pd.to_numeric(df[col], errors="raise")
    return df, value_cols, date_col


def prepare_inputs(df: pd.DataFrame, value_cols: list[str], missing: str = "error") -> list[np.ndarray]:
    """Preserve grid positions. Optional interpolation stays inside each history."""
    if missing not in {"error", "interpolate"}:
        raise ValueError("missing must be error or interpolate")
    inputs = []
    for col in value_cols:
        series = pd.to_numeric(df[col], errors="raise")
        values = series.to_numpy(dtype=np.float32, copy=True)
        if values.size == 0 or np.isinf(values).any():
            raise ValueError(f"{col}: empty series or infinite values")
        if np.isnan(values).any():
            if missing == "error":
                raise ValueError(f"{col}: missing values; choose an explicit missing-data policy")
            if np.isnan(values[0]) or np.isnan(values[-1]):
                raise ValueError(f"{col}: leading/trailing missing values change the forecast origin")
            values = pd.Series(values).interpolate(limit_area="inside").to_numpy(dtype=np.float32)
        if not np.isfinite(values).all():
            raise ValueError(f"{col}: nonfinite input after preprocessing")
        inputs.append(values)
    return inputs


def validate_forecast(point, quantiles, batch: int, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    point, quantiles = np.asarray(point), np.asarray(quantiles)
    if point.shape != (batch, horizon) or quantiles.shape != (batch, horizon, 10):
        raise ValueError("unexpected TimesFM 2.5 output shape; check return_backcast and model version")
    if not np.isfinite(point).all() or not np.isfinite(quantiles).all():
        raise ValueError("nonfinite model output")
    if np.any(np.diff(quantiles[..., 1:], axis=-1) < 0):
        raise ValueError("crossed quantiles")
    if not np.allclose(point, quantiles[..., 5]):
        raise ValueError("point forecast does not match q50")
    return point, quantiles


def forecast_series(model, df: pd.DataFrame, value_cols: list[str], horizon: int,
                    missing: str = "error") -> dict[str, dict]:
    if horizon < 1:
        raise ValueError("horizon must be positive")
    inputs = prepare_inputs(df, value_cols, missing)
    # The upstream 2.5 batching code appends padding series to the input list.
    point, quantiles = model.forecast(horizon=horizon, inputs=list(inputs))
    point, quantiles = validate_forecast(point, quantiles, len(value_cols), horizon)
    return {
        col: {"forecast": point[i].tolist(), "lower_80": quantiles[i, :, 1].tolist(),
              "lower_60": quantiles[i, :, 2].tolist(), "median": quantiles[i, :, 5].tolist(),
              "upper_60": quantiles[i, :, 8].tolist(), "upper_80": quantiles[i, :, 9].tolist()}
        for i, col in enumerate(value_cols)
    }


def write_csv_output(results, output_path, df, date_col, horizon) -> None:
    future_dates = None
    if date_col:
        freq = regular_frequency(df[date_col], df.attrs.get("frequency"))
        future_dates = pd.date_range(df[date_col].iloc[-1], periods=horizon + 1, freq=freq)[1:]
    rows = []
    for col, data in results.items():
        for h in range(horizon):
            row = {"series": col, "step": h + 1, **{key: values[h] for key, values in data.items()}}
            if future_dates is not None:
                row["date"] = future_dates[h]
            rows.append(row)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    print(f"[OK] Wrote {len(rows)} forecast rows to {output_path}")


def write_json_output(results, output_path) -> None:
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, allow_nan=False)
    print(f"[OK] Wrote forecasts for {len(results)} series to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Input CSV")
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--date-col")
    parser.add_argument("--freq", help="Pandas frequency, e.g. MS, D, h; required for <3 dates")
    parser.add_argument("--value-cols", help="Comma-separated numeric columns")
    parser.add_argument("--output", default="forecasts.csv")
    parser.add_argument("--format", choices=["csv", "json"])
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-context", type=int, default=1024)
    parser.add_argument("--missing", choices=["error", "interpolate"], default="error")
    parser.add_argument("--nonnegative", action="store_true", help="Use only for a truly nonnegative target domain")
    parser.add_argument("--revision", default=MODEL_REVISION, help="Immutable HF revision for reproducibility")
    parser.add_argument("--skip-check", action="store_true")
    args = parser.parse_args()
    try:
        cols = [c.strip() for c in args.value_cols.split(",")] if args.value_cols else None
        df, cols, date_col = load_csv(args.input, args.date_col, cols, args.freq)
        prepare_inputs(df, cols, args.missing)
        config = forecast_config(args.horizon, args.max_context, args.batch_size, args.nonnegative)
        if Path(args.input).resolve() == Path(args.output).resolve():
            raise ValueError("output must differ from input")
        if not args.skip_check:
            run_preflight()
        model = load_model(args.batch_size, args.horizon, args.max_context, args.nonnegative, args.revision)
        results = forecast_series(model, df, cols, args.horizon, args.missing)
        out_format = args.format or ("json" if args.output.lower().endswith(".json") else "csv")
        if out_format == "json":
            write_json_output(results, args.output)
        else:
            write_csv_output(results, args.output, df, date_col, args.horizon)
        import dataclasses
        metadata = {
            "model": MODEL_ID, "revision": args.revision, "package": version("timesfm"),
            "config": dataclasses.asdict(config), "horizon": args.horizon,
            "frequency": df.attrs.get("frequency"), "missing_policy": args.missing,
            "forecast_origin": str(df[date_col].iloc[-1]) if date_col else None,
            "intervals": "nominal q10-q90 (80%) and q20-q80 (60%); calibration unverified",
        }
        Path(args.output + ".metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
