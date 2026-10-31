#!/usr/bin/env python3
"""Illustrative temperature-shaped CSV workflow; bundled values have unverified provenance."""
from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from forecast_csv import MODEL_ID, MODEL_REVISION, load_csv, load_model, prepare_inputs, run_preflight, validate_forecast

INPUT_FILE = Path(__file__).parent / "temperature_anomaly.csv"


def run(output_dir: Path, horizon: int = 12):
    df, cols, _ = load_csv(str(INPUT_FILE), "date", ["anomaly_c"], "MS")
    histories = prepare_inputs(df, cols)
    run_preflight()
    model = load_model(horizon=horizon, nonnegative=False)
    point, q = model.forecast(horizon=horizon, inputs=list(histories))
    point, q = validate_forecast(point, q, 1, horizon)
    dates = pd.date_range(df["date"].iloc[-1], periods=horizon + 1, freq="MS")[1:]
    payload = {
        "schema_version": "2.5-deciles-v1",
        "model": MODEL_ID, "revision": MODEL_REVISION, "package": version("timesfm"),
        "input": {"source": "Bundled illustrative values; original source unverified",
                  "n_observations": len(df), "date_range": f"{df.date.iloc[0]:%Y-%m} to {df.date.iloc[-1]:%Y-%m}"},
        "forecast": {"horizon": horizon, "dates": dates.strftime("%Y-%m").tolist(),
                     "point": point[0].tolist(),
                     "quantiles": {f"{i * 10}%": q[0, :, i].tolist() for i in range(1, 10)}},
        "summary": {"forecast_mean_c": float(point.mean()),
                    "vs_last_year_mean": float(point.mean() - df.anomaly_c.iloc[-12:].mean())},
        "limitations": "Nominal intervals; no calibration or climate validation. Not an observed-data publication.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "forecast_output.json").write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    pd.DataFrame({"date": dates, "point_forecast": point[0], "mean": q[0, :, 0],
                  **{f"q{i * 10}": q[0, :, i] for i in range(1, 10)}}).to_csv(output_dir / "forecast_output.csv", index=False)
    print(f"[OK] Wrote illustrative forecast to {output_dir}")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=12)
    args = parser.parse_args()
    run(args.output_dir, args.horizon)


if __name__ == "__main__":
    main()
