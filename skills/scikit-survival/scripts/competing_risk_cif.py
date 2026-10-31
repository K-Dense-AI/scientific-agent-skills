#!/usr/bin/env python3
"""Estimate nonparametric competing-risk cumulative incidence from local data."""

from __future__ import annotations

import argparse
from typing import Any

from _common import (
    DEFAULT_SEED,
    CliError,
    atomic_save_npz,
    bounded_int,
    emit_json,
    parse_floats,
    probability,
    read_csv,
)


VARIANCE_CHOICES = ("Aalen", "Dinse", "Dinse_Approx")
MAX_CIF_ROWS = 5_000
MAX_CAUSES = 32


def synthetic_competing_risks(
    *, rows: int = 300, seed: int = DEFAULT_SEED
) -> tuple[Any, Any]:
    """Create deterministic, non-clinical outcomes with three competing causes."""

    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise CliError("NumPy and pandas are required") from exc
    rng = np.random.default_rng(seed)
    latent = rng.normal(size=rows)
    cause_times = np.column_stack(
        [
            rng.exponential(scale=7.0 * np.exp(-0.25 * latent)),
            rng.exponential(scale=10.0 * np.exp(0.15 * latent)),
            rng.exponential(scale=14.0, size=rows),
        ]
    )
    censor_time = rng.exponential(scale=16.0, size=rows)
    cause = np.argmin(cause_times, axis=1) + 1
    event_time = cause_times[np.arange(rows), cause - 1]
    event = np.where(event_time <= censor_time, cause, 0)
    time = np.minimum(event_time, censor_time) + 0.05
    for cause_code in (1, 2, 3):
        event[cause_code - 1] = cause_code
        time[cause_code - 1] = float(cause_code)
    frame = pd.DataFrame({"status": event, "time": time})
    return frame, {"kind": "synthetic", "network_used": False, "seed": seed}


def normalize_competing_event(values: Any):
    """Return non-negative contiguous integer cause codes."""

    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise CliError("NumPy and pandas are required") from exc
    series = pd.Series(values)
    if series.isna().any():
        raise CliError("competing-risk event codes contain missing values")
    try:
        numeric = pd.to_numeric(series, errors="raise").to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise CliError("event codes must be integers") from exc
    if not np.isfinite(numeric).all() or (numeric < 0).any():
        raise CliError("event codes must be finite non-negative integers")
    if not np.equal(numeric, np.floor(numeric)).all():
        raise CliError("event codes must be integers")
    if (numeric > MAX_CAUSES).any():
        raise CliError(f"cause codes must not exceed {MAX_CAUSES}")
    event = numeric.astype(int)
    causes = sorted(set(event.tolist()) - {0})
    if len(causes) < 2:
        raise CliError("at least two competing causes are required")
    if len(causes) > MAX_CAUSES:
        raise CliError(f"at most {MAX_CAUSES} competing causes are allowed")
    expected = list(range(1, max(causes) + 1))
    if causes != expected:
        raise CliError(
            "positive cause codes must be contiguous and every cause must occur"
        )
    return event


def normalize_times(values: Any):
    """Return a finite, strictly positive time vector."""

    from _common import normalize_positive_times

    return normalize_positive_times(values, label="competing-risk time")


def horizon_values(
    unique_times: Any,
    cumulative_incidence: Any,
    horizons: list[float],
) -> list[dict[str, Any]]:
    """Evaluate right-continuous step estimates at requested horizons."""

    import numpy as np

    records: list[dict[str, Any]] = []
    for horizon in horizons:
        if horizon <= 0 or not np.isfinite(horizon):
            raise CliError("horizons must be finite and strictly positive")
        if horizon > unique_times[-1]:
            raise CliError("report horizons must not exceed observed follow-up")
        index = int(np.searchsorted(unique_times, horizon, side="right") - 1)
        values = (
            np.zeros(cumulative_incidence.shape[0], dtype=float)
            if index < 0
            else cumulative_incidence[:, index]
        )
        records.append(
            {
                "cause_specific": {
                    str(cause): float(values[cause])
                    for cause in range(1, cumulative_incidence.shape[0])
                },
                "horizon": float(horizon),
                "total_risk": float(values[0]),
            }
        )
    return records


def estimate_cif(
    event: Any,
    time: Any,
    *,
    horizons: list[float] | None = None,
    confidence: bool = False,
    confidence_level: float = 0.95,
    variance_type: str = "Aalen",
    time_min: float | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Estimate CIF curves and return a bounded summary plus numeric arrays."""

    try:
        import numpy as np
        from sksurv.nonparametric import (
            cumulative_incidence_competing_risks,
            kaplan_meier_estimator,
        )
    except ImportError as exc:
        raise CliError("the pinned scikit-survival stack is required") from exc
    checked_event = normalize_competing_event(event)
    checked_time = normalize_times(time)
    if len(checked_event) != len(checked_time):
        raise CliError("event and time arrays must have equal length")
    if len(checked_event) > MAX_CIF_ROWS:
        raise CliError(f"CIF estimation is limited to {MAX_CIF_ROWS} rows")
    if confidence and variance_type == "Dinse" and len(checked_event) > 2_000:
        raise CliError("Dinse variance is limited to 2,000 rows")
    if time_min is not None and (
        not np.isfinite(time_min) or time_min < 0 or time_min >= checked_time.max()
    ):
        raise CliError("time_min must be finite, non-negative, and below max time")
    if time_min is not None and time_min > checked_time.min():
        raise CliError(
            "scikit-survival 0.28.0 has a conditional CIF shape defect; "
            "time_min that removes observed times is unsupported"
        )
    if not np.isfinite(confidence_level) or not 0 < confidence_level < 1:
        raise CliError("confidence_level must be strictly between zero and one")

    result = cumulative_incidence_competing_risks(
        checked_event,
        checked_time,
        time_min=time_min,
        conf_level=confidence_level,
        conf_type="log-log" if confidence else None,
        var_type=variance_type,
    )
    if confidence:
        unique_times, cumulative_incidence, intervals = result
        # 0.28.0 reverses the total-CIF endpoints and ignores conf_level for
        # that row. Reconstruct it from the public all-event KM estimator.
        km_times, _, km_intervals = kaplan_meier_estimator(
            checked_event > 0,
            checked_time,
            conf_type="log-log",
            conf_level=confidence_level,
        )
        if not np.array_equal(km_times, unique_times):
            raise CliError("total-risk confidence grid differs from the CIF grid")
        intervals[0] = 1.0 - km_intervals[::-1]
        if not np.isfinite(intervals).all() or (intervals[:, 0] > intervals[:, 1]).any():
            raise CliError("CIF confidence intervals are non-finite or reversed")
    else:
        unique_times, cumulative_incidence = result
        intervals = None
    if not np.isfinite(cumulative_incidence).all() or (
        (cumulative_incidence < -1e-10) | (cumulative_incidence > 1 + 1e-10)
    ).any():
        raise CliError("CIF estimates must be finite probabilities")
    if (np.diff(cumulative_incidence, axis=1) < -1e-10).any():
        raise CliError("estimated cumulative incidence unexpectedly decreased")
    if not np.allclose(
        cumulative_incidence[0],
        cumulative_incidence[1:].sum(axis=0),
        rtol=1e-8,
        atol=1e-10,
    ):
        raise CliError("cause-specific CIFs do not sum to total risk")

    if horizons is None:
        horizons = [
            float(value) for value in np.quantile(checked_time, [0.25, 0.5, 0.75])
        ]
    if len(horizons) > 32:
        raise CliError("at most 32 reporting horizons are allowed")
    summary = {
        "cause_counts": {
            str(code): int((checked_event == code).sum())
            for code in range(0, int(checked_event.max()) + 1)
        },
        "confidence": {
            "enabled": confidence,
            "level": confidence_level if confidence else None,
            "type": "log-log" if confidence else None,
            "variance_type": variance_type if confidence else None,
        },
        "event_coding": "0=censored; positive contiguous integers=causes",
        "horizons": horizon_values(
            unique_times, cumulative_incidence, sorted(horizons)
        ),
        "n_causes": int(checked_event.max()),
        "rows": int(len(checked_event)),
        "schema_version": "1.0",
        "time_min": time_min,
        "warning": (
            "Cumulative incidence is cause-specific absolute event probability, "
            "not a cause-specific hazard or proof of treatment benefit."
        ),
    }
    arrays = {
        "cumulative_incidence": cumulative_incidence,
        "time": unique_times,
    }
    if intervals is not None:
        arrays["confidence_interval"] = intervals
    return summary, arrays


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate nonparametric cumulative incidence for competing causes. "
            "No input uses deterministic synthetic data; no network is used."
        )
    )
    parser.add_argument("--input", help="Optional bounded local .csv")
    parser.add_argument("--event-column", default="status")
    parser.add_argument("--time-column", default="time")
    parser.add_argument("--horizons", help="Optional comma-separated report horizons")
    parser.add_argument("--time-min", type=float)
    parser.add_argument("--confidence", action="store_true")
    parser.add_argument("--confidence-level", type=probability, default=0.95)
    parser.add_argument("--variance-type", choices=VARIANCE_CHOICES, default="Aalen")
    parser.add_argument("--seed", type=bounded_int(0, 2**32 - 1), default=DEFAULT_SEED)
    parser.add_argument("--synthetic-rows", type=bounded_int(80, 20_000), default=300)
    parser.add_argument(
        "--curve-output", help="Optional local .npz containing full CIF arrays"
    )
    parser.add_argument("--output", help="Optional local .json summary")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.input:
            frame, name = read_csv(args.input)
            source = {"kind": "local_csv", "name": name}
        else:
            frame, source = synthetic_competing_risks(
                rows=args.synthetic_rows, seed=args.seed
            )
        missing = [
            name
            for name in (args.event_column, args.time_column)
            if name not in frame.columns
        ]
        if missing:
            raise CliError(f"missing columns: {', '.join(missing)}")
        horizons = parse_floats(args.horizons) or None
        summary, arrays = estimate_cif(
            frame[args.event_column],
            frame[args.time_column],
            horizons=horizons,
            confidence=args.confidence,
            confidence_level=args.confidence_level,
            variance_type=args.variance_type,
            time_min=args.time_min,
        )
        summary["source"] = source
        if args.curve_output:
            atomic_save_npz(arrays, args.curve_output, force=args.force)
            summary["curve_output"] = args.curve_output
        emit_json(summary, output=args.output, force=args.force)
    except CliError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
