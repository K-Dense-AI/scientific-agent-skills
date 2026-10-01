#!/usr/bin/env python3
"""
Visualize TimesFM forecast results for global temperature anomaly.

Generates a publication-quality figure showing:
- Historical data (2022-2024)
- Point forecast (2025)
- 60% and 80% nominal prediction intervals (fan chart)

Usage:
    python visualize_forecast.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Configuration
EXAMPLE_DIR = Path(__file__).parent
INPUT_FILE = EXAMPLE_DIR / "temperature_anomaly.csv"
FORECAST_FILE = EXAMPLE_DIR / "output" / "forecast_output.json"
OUTPUT_FILE = EXAMPLE_DIR / "output" / "forecast_visualization.png"


def main() -> None:
    global FORECAST_FILE, OUTPUT_FILE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    FORECAST_FILE = args.output_dir / "forecast_output.json"
    OUTPUT_FILE = args.output_dir / "forecast_visualization.png"
    # Load historical data
    df = pd.read_csv(INPUT_FILE, parse_dates=["date"])

    # Load forecast results
    with open(FORECAST_FILE) as f:
        forecast = json.load(f)
    if forecast.get("schema_version") != "2.5-deciles-v1":
        raise ValueError("Regenerate legacy output with the corrected forecast script")

    # Extract forecast data
    dates = pd.to_datetime(forecast["forecast"]["dates"])
    point = np.array(forecast["forecast"]["point"])
    q10 = np.array(forecast["forecast"]["quantiles"]["10%"])
    q20 = np.array(forecast["forecast"]["quantiles"]["20%"])
    q80 = np.array(forecast["forecast"]["quantiles"]["80%"])
    q90 = np.array(forecast["forecast"]["quantiles"]["90%"])

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot historical data
    ax.plot(
        df["date"],
        df["anomaly_c"],
        color="#2563eb",
        linewidth=1.5,
        marker="o",
        markersize=3,
        label="Illustrative history (unverified source)",
    )

    # Plot Nominal 80% PI (outer band)
    ax.fill_between(dates, q10, q90, alpha=0.2, color="#dc2626", label="Nominal 80% PI")

    # Plot Nominal 60% PI (inner band)
    ax.fill_between(dates, q20, q80, alpha=0.3, color="#dc2626", label="Nominal 60% PI")

    # Plot point forecast
    ax.plot(
        dates,
        point,
        color="#dc2626",
        linewidth=2,
        marker="s",
        markersize=4,
        label="TimesFM Forecast",
    )

    # Add vertical line at forecast boundary
    ax.axvline(
        x=df["date"].max(), color="#6b7280", linestyle="--", linewidth=1, alpha=0.7
    )

    # Formatting
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Temperature Anomaly (°C)", fontsize=12)
    ax.set_title(
        f"TimesFM Forecast Example\n{len(df)}-month Illustrative History → {len(dates)}-month Forecast",
        fontsize=14,
        fontweight="bold",
    )

    # Add annotations
    ax.annotate(
        f"Mean forecast: {forecast['summary']['forecast_mean_c']:.2f}°C\n"
        f"vs last 12 observations: {forecast['summary']['vs_last_year_mean']:+.2f}°C",
        xy=(dates[len(dates)//2], point[len(dates)//2]),
        xytext=(0.53, 0.9),
        textcoords="axes fraction",
        fontsize=10,
        arrowprops=dict(arrowstyle="->", color="#6b7280", lw=1),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#6b7280"),
    )

    # Grid and legend
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=10)


    # Rotate x-axis labels
    plt.xticks(rotation=45, ha="right")

    # Tight layout
    plt.tight_layout()

    # Save
    fig.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
    print(f"[OK] Saved visualization to: {OUTPUT_FILE}")

    plt.close()


if __name__ == "__main__":
    main()
