#!/usr/bin/env python3
"""Generate successive-origin forecasts using only each origin's history."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from forecast_csv import MODEL_ID, MODEL_REVISION, load_csv, load_model, prepare_inputs, run_preflight, validate_forecast

INPUT_FILE = Path(__file__).parent / "temperature_anomaly.csv"


def run(output_dir: Path, min_context: int = 12, final_horizon: int = 12):
    df, cols, _ = load_csv(str(INPUT_FILE), "date", ["anomaly_c"], "MS")
    values = prepare_inputs(df, cols)[0]
    if not 1 <= min_context <= len(values) or final_horizon < 1:
        raise ValueError("invalid minimum context or final horizon")
    total = len(values) + final_horizon
    run_preflight()
    model = load_model(horizon=total - min_context, nonnegative=False)
    steps = []
    for n in range(min_context, len(values) + 1):
        horizon = total - n
        point, q = model.forecast(horizon=horizon, inputs=[values[:n].copy()])
        point, q = validate_forecast(point, q, 1, horizon)
        future = pd.date_range(df.date.iloc[n - 1], periods=horizon + 1, freq="MS")[1:]
        steps.append({"step": len(steps) + 1, "n_points": n, "horizon": horizon,
                      "last_historical_date": df.date.iloc[n - 1].strftime("%Y-%m"),
                      "historical_dates": df.date.iloc[:n].dt.strftime("%Y-%m").tolist(),
                      "historical_values": values[:n].tolist(), "forecast_dates": future.strftime("%Y-%m").tolist(),
                      "point_forecast": point[0].tolist(),
                      **{f"q{i * 10}": q[0, :, i].tolist() for i in (1, 2, 8, 9)}})
    payload = {"schema_version": "2.5-deciles-v1",
               "metadata": {"model": MODEL_ID, "revision": MODEL_REVISION,
                            "data_source": "Illustrative values; provenance unverified", "total_steps": len(steps)},
               "actual_data": {"dates": df.date.dt.strftime("%Y-%m").tolist(), "values": values.tolist()},
               "animation_steps": steps}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "animation_data.json").write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--min-context", type=int, default=12)
    args = parser.parse_args()
    run(args.output_dir, args.min_context)


if __name__ == "__main__":
    main()
