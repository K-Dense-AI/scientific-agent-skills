#!/usr/bin/env python3
"""Evaluate censoring-aware survival metrics with strict input contracts."""

from __future__ import annotations

import argparse
import zipfile
from typing import Any

from _common import (
    DEFAULT_SEED,
    MAX_INPUT_BYTES,
    MAX_ROWS,
    MAX_TIME_POINTS,
    CliError,
    bounded_int,
    checked_input_file,
    emit_json,
    structured_survival,
)


REQUIRED_ARRAYS = {
    "risk",
    "test_event",
    "test_time",
    "times",
    "train_event",
    "train_time",
}


def synthetic_metric_inputs(seed: int = DEFAULT_SEED) -> dict[str, Any]:
    """Create deterministic, non-clinical predictions with supported follow-up."""

    try:
        import numpy as np
    except ImportError as exc:
        raise CliError("NumPy is required") from exc
    rng = np.random.default_rng(seed)

    def observed(rows: int) -> tuple[Any, Any, Any]:
        risk = rng.normal(size=rows)
        event_time = rng.exponential(scale=9.0 * np.exp(-0.65 * risk)) + 0.1
        censor_time = rng.exponential(scale=13.0, size=rows) + 0.1
        event = event_time <= censor_time
        time = np.minimum(event_time, censor_time)
        return event, time, risk

    train_event, train_time, _ = observed(220)
    test_event, test_time, risk = observed(90)
    support_limit = float(test_time.max() + 5.0)
    train_event[-1] = False
    train_time[-1] = max(support_limit, float(train_time.max()))
    upper = float(min(np.quantile(test_time, 0.8), train_time.max() - 1e-6))
    lower = float(np.quantile(test_time, 0.2))
    times = np.linspace(lower, upper, 8)
    survival = np.exp(-np.exp(0.65 * risk[:, None]) * times[None, :] / 9.0)
    return {
        "risk": risk,
        "survival": survival,
        "test_event": test_event,
        "test_time": test_time,
        "times": times,
        "train_event": train_event,
        "train_time": train_time,
    }


def load_prediction_archive(value: str) -> tuple[dict[str, Any], str]:
    """Load a bounded NPZ archive without pickle."""

    try:
        import numpy as np
    except ImportError as exc:
        raise CliError("NumPy is required") from exc
    path = checked_input_file(value, suffixes={".npz"})
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > len(REQUIRED_ARRAYS) + 1 or sum(
                member.file_size for member in members
            ) > MAX_INPUT_BYTES:
                raise CliError("prediction archive exceeds expanded array limits")
            if len({member.filename for member in members}) != len(members):
                raise CliError("prediction archive contains duplicate members")
        with np.load(path, allow_pickle=False) as archive:
            names = set(archive.files)
            missing = REQUIRED_ARRAYS - names
            if missing:
                raise CliError(
                    "prediction archive is missing: " + ", ".join(sorted(missing))
                )
            unexpected = names - REQUIRED_ARRAYS - {"survival"}
            if unexpected:
                raise CliError(
                    "prediction archive has unsupported arrays: "
                    + ", ".join(sorted(unexpected))
                )
            arrays = {name: archive[name] for name in archive.files}
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise CliError(f"cannot load safe NPZ archive {path.name}: {exc}") from exc
    return arrays, path.name


def validate_time_grid(
    times: Any,
    y_train: Any,
    y_test: Any,
) -> Any:
    """Validate shape, order, observed support, and censoring support."""

    try:
        import numpy as np
        from sksurv.nonparametric import CensoringDistributionEstimator
    except ImportError as exc:
        raise CliError("the pinned survival stack is required") from exc
    values = np.asarray(times, dtype=float)
    if values.ndim != 1:
        raise CliError("times must be one-dimensional")
    if not 2 <= values.size <= MAX_TIME_POINTS:
        raise CliError(f"times must contain 2 through {MAX_TIME_POINTS} values")
    if not np.isfinite(values).all() or (values <= 0).any():
        raise CliError("times must be finite and strictly positive")
    if not (np.diff(values) > 0).all():
        raise CliError("times must be unique and strictly increasing")

    train_time = y_train[y_train.dtype.names[1]]
    test_time = y_test[y_test.dtype.names[1]]
    if not test_time.max() < train_time.max():
        raise CliError(
            "test follow-up must end before training follow-up for IPCW support"
        )
    if values[0] <= test_time.min() or values[-1] >= test_time.max():
        raise CliError(
            "evaluation times must lie strictly inside the test follow-up range"
        )
    if values[-1] >= train_time.max():
        raise CliError("evaluation times exceed training follow-up support")
    censoring = CensoringDistributionEstimator().fit(y_train)
    try:
        probability = censoring.predict_proba(values)
    except ValueError as exc:
        raise CliError(
            f"censoring distribution is undefined on the grid: {exc}"
        ) from exc
    if not np.isfinite(probability).all() or (probability <= 0).any():
        raise CliError(
            "training censoring survival must remain positive across the time grid"
        )
    try:
        censoring.predict_ipcw(y_test)
    except ValueError as exc:
        raise CliError(f"test event times lack positive censoring support: {exc}") from exc
    test_event = y_test[y_test.dtype.names[0]]
    if not (test_event & (test_time <= values[0])).any():
        raise CliError("dynamic AUC needs an observed case by the first evaluation time")
    if not (test_time > values[-1]).any():
        raise CliError("dynamic AUC needs controls after the final evaluation time")
    return values


def validate_predictions(
    arrays: dict[str, Any],
) -> tuple[Any, Any | None, Any, Any, Any]:
    """Validate risk/survival shapes and return metric-ready arrays."""

    try:
        import numpy as np
    except ImportError as exc:
        raise CliError("NumPy is required") from exc
    for name in ("train_event", "train_time", "test_event", "test_time"):
        value = np.asarray(arrays[name])
        if value.ndim != 1 or not 2 <= value.size <= MAX_ROWS:
            raise CliError(f"{name} must have 2 through {MAX_ROWS} one-dimensional values")
    y_train = structured_survival(arrays["train_event"], arrays["train_time"])
    y_test = structured_survival(arrays["test_event"], arrays["test_time"])
    times = validate_time_grid(arrays["times"], y_train, y_test)
    n_test = len(y_test)

    risk = np.asarray(arrays["risk"], dtype=float)
    valid_risk_shape = risk.shape == (n_test,) or risk.shape == (
        n_test,
        len(times),
    )
    if not valid_risk_shape:
        raise CliError("risk must have shape (n_test,) or (n_test, n_times)")
    if not np.isfinite(risk).all():
        raise CliError("risk contains non-finite values")

    survival: Any | None = None
    if "survival" in arrays:
        survival = np.asarray(arrays["survival"], dtype=float)
        if survival.shape != (n_test, len(times)):
            raise CliError("survival must have shape (n_test, n_times)")
        if not np.isfinite(survival).all():
            raise CliError("survival contains non-finite values")
        if ((survival < 0) | (survival > 1)).any():
            raise CliError("survival probabilities must be within [0, 1]")
        if (np.diff(survival, axis=1) > 1e-10).any():
            raise CliError(
                "each survival-probability row must be non-increasing over time"
            )
    return risk, survival, times, y_train, y_test


def evaluate(arrays: dict[str, Any]) -> dict[str, Any]:
    """Compute discrimination and prediction-error metrics by input type."""

    try:
        import numpy as np
        from sksurv.metrics import (
            brier_score,
            concordance_index_censored,
            concordance_index_ipcw,
            cumulative_dynamic_auc,
            integrated_brier_score,
        )
    except ImportError as exc:
        raise CliError("the pinned survival stack is required") from exc
    risk, survival, times, y_train, y_test = validate_predictions(arrays)
    event_field, time_field = y_test.dtype.names

    auc, mean_auc = cumulative_dynamic_auc(y_train, y_test, risk, times)
    metrics: dict[str, Any] = {
        "cumulative_dynamic_auc": {
            "mean": float(mean_auc),
            "times": times.tolist(),
            "values": np.asarray(auc, dtype=float).tolist(),
        }
    }
    if risk.ndim == 1:
        metrics["harrell_c"] = float(
            concordance_index_censored(y_test[event_field], y_test[time_field], risk)[0]
        )
        metrics["uno_c"] = float(
            concordance_index_ipcw(y_train, y_test, risk, tau=float(times[-1]))[0]
        )
    else:
        metrics["harrell_c"] = None
        metrics["uno_c"] = None
        metrics["concordance_note"] = (
            "Skipped: concordance functions require one risk score per row; "
            "the supplied risk is time-dependent."
        )

    if survival is not None:
        returned_times, scores = brier_score(y_train, y_test, survival, times)
        metrics["brier_score"] = {
            "times": np.asarray(returned_times, dtype=float).tolist(),
            "values": np.asarray(scores, dtype=float).tolist(),
        }
        metrics["integrated_brier_score"] = float(
            integrated_brier_score(y_train, y_test, survival, times)
        )
    else:
        metrics["brier_score"] = None
        metrics["integrated_brier_score"] = None
        metrics["brier_note"] = (
            "Skipped: Brier metrics require survival probabilities, not risk scores."
        )

    if not np.isfinite(auc).all() or not np.isfinite(mean_auc):
        raise CliError("dynamic AUC is undefined for these cases, controls, or weights")
    return {
        "assumptions": {
            "censoring_distribution_fit_on_training_only": True,
            "independent_censoring_from_features": "required_by_IPCW_estimator",
            "test_follow_up_within_training_support": True,
            "time_grid_within_test_follow_up": True,
        },
        "input_contract": {
            "risk": ("higher means greater event risk; 1D or n_test-by-n_times"),
            "survival": ("optional n_test-by-n_times probabilities; never risk scores"),
        },
        "metrics": metrics,
        "schema_version": "1.0",
        "warning": (
            "Discrimination and prediction error do not establish calibration "
            "at every horizon, causal effects, or clinical utility."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate risk scores and optional survival probabilities from a "
            "bounded local NPZ archive. No input uses deterministic synthetic data."
        )
    )
    parser.add_argument("--input", help="Optional local .npz prediction archive")
    parser.add_argument("--seed", type=bounded_int(0, 2**32 - 1), default=DEFAULT_SEED)
    parser.add_argument("--output", help="Optional local .json report")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.input:
            arrays, name = load_prediction_archive(args.input)
            source = {"kind": "local_npz", "name": name}
        else:
            arrays = synthetic_metric_inputs(args.seed)
            source = {
                "kind": "synthetic",
                "network_used": False,
                "seed": args.seed,
            }
        report = evaluate(arrays)
        report["source"] = source
        emit_json(report, output=args.output, force=args.force)
    except CliError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
