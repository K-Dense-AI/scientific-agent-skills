#!/usr/bin/env python3
"""foRcast — ARIMA forecasting of RELSA severity trajectories.

Independent nonseasonal approximation of the published foRcast methodology
(Lutscher et al., 2026, Front. Physiol. 17:1869563), using statsmodels SARIMAX.
Predicts a score at a specified future observation time, not time-to-endpoint.
Interpolation adds no independent information and may understate uncertainty.
A forecast cannot override observed welfare signs or approved humane endpoints.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    ID_COL,
    TIME_COL,
    ForecastMetrics,
    forecast_metrics,
    parse_list,
    read_relsa_table,
    validate,
)

DEFAULT_STEP = 0.1
MIN_TRAIN_POINTS = 4


def _trajectory(times, values) -> tuple[np.ndarray, np.ndarray]:
    t, y = np.asarray(list(times), dtype=float), np.asarray(list(values), dtype=float)
    if t.ndim != 1 or t.shape != y.shape or not np.isfinite(t).all() or np.isinf(y).any():
        raise ValueError("times/values must be matching vectors; times finite, values finite or NaN")
    order = np.argsort(t)
    t, y = t[order], y[order]
    if np.any(np.diff(t) <= 0):
        raise ValueError("duplicate observation times")
    return t, y


# --------------------------------------------------------------------------- #
# interpolation
# --------------------------------------------------------------------------- #
def interpolate_series(
    times: Iterable[float],
    values: Iterable[float],
    step: float = DEFAULT_STEP,
) -> tuple[np.ndarray, np.ndarray]:
    """Linearly interpolate a sparse trajectory onto a regular ``step`` grid.

    Leading and trailing missing values are dropped rather than extrapolated.
    Returns the grid times and interpolated values.
    """
    t, y = _trajectory(times, values)
    if not np.isfinite(step) or step <= 0:
        raise ValueError("interpolation step must be finite and positive")
    ok = np.isfinite(t) & np.isfinite(y)
    t, y = t[ok], y[ok]
    if t.size < 2:
        raise ValueError("need at least 2 observed points to interpolate")
    order = np.argsort(t)
    t, y = t[order], y[order]
    offsets = (t - t[0]) / step
    if not np.allclose(offsets, np.round(offsets), rtol=0, atol=1e-7):
        raise ValueError("observation times must align with the interpolation grid")
    if offsets[-1] > 100000:
        raise ValueError("interpolation grid exceeds 100000 steps")
    grid = t[0] + np.arange(int(round(offsets[-1])) + 1) * step
    return grid, np.interp(grid, t, y)


# --------------------------------------------------------------------------- #
# automatic ARIMA
# --------------------------------------------------------------------------- #
@dataclass
class ArimaFit:
    """A selected ARIMA model and the information criterion that chose it."""

    order: tuple[int, int, int]
    drift: bool
    aicc: float
    aic: float
    n_obs: int
    results: object = field(repr=False, default=None)

    def label(self) -> str:
        p, d, q = self.order
        term = " with intercept" if d == 0 else " with drift"
        return f"ARIMA({p},{d},{q})" + (term if self.drift else "")


def _select_d(y: np.ndarray, max_d: int) -> int:
    """Choose the differencing order by successive KPSS tests, as auto.arima does."""
    from statsmodels.tsa.stattools import kpss

    series = np.asarray(y, dtype=float)
    for d in range(max_d + 1):
        if series.size < 8 or np.allclose(series, series[0]):
            return d
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                p_value = kpss(series, regression="c", nlags="auto")[1]
        except Exception:
            return d
        if p_value > 0.05:  # KPSS null is stationarity -> stop differencing
            return d
        series = np.diff(series)
    return max_d


def _fit_one(
    y: np.ndarray, order: tuple[int, int, int], drift: bool
) -> ArimaFit | None:
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    k = sum(order[::2]) + (1 if drift else 0) + 1
    if y.size - order[1] <= k + 2:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = SARIMAX(
                y,
                order=order,
                trend="c" if drift else "n",
                enforce_stationarity=True,
                enforce_invertibility=True,
            )
            res = model.fit(disp=False, maxiter=200)
    except Exception:
        return None
    aic, aicc = float(res.aic), float(res.aicc)
    if not res.mle_retvals.get("converged", False) or not np.isfinite([aic, aicc]).all():
        return None
    n = int(res.nobs)
    return ArimaFit(order=order, drift=drift, aicc=aicc, aic=aic,
                    n_obs=n, results=res)


def auto_arima(
    y: Iterable[float],
    max_p: int = 5,
    max_q: int = 5,
    max_d: int = 2,
    d: int | None = None,
    allow_drift: bool = True,
    stepwise: bool = True,
) -> ArimaFit:
    """Select an ARIMA model by minimising AICc (Hyndman–Khandakar stepwise).

    Approximates the nonseasonal search in ``forecast::auto.arima``: KPSS, then
    four seed models — (2,d,2), (0,d,0), (1,d,0), (0,d,1) — followed by a
    hill-climb over neighbouring (p, q) and the drift term. ``stepwise=False``
    searches the full grid, which is slower and rarely changes the answer.

    The best model found is not guaranteed to be the globally best one: the
    search covers a bounded range of p, d, q, which the paper notes as a
    limitation of the approach rather than of one implementation.
    """
    series = np.asarray(list(y), dtype=float)
    if series.ndim != 1 or not np.isfinite(series).all():
        raise ValueError("ARIMA input must be a finite, regular series")
    if any(int(v) != v or v < 0 for v in (max_p, max_q, max_d)):
        raise ValueError("ARIMA maximum orders must be nonnegative integers")
    if d is not None and (int(d) != d or d < 0 or d > max_d):
        raise ValueError("d must be an integer between zero and max_d")
    if series.size < MIN_TRAIN_POINTS:
        raise ValueError(
            f"need at least {MIN_TRAIN_POINTS} finite points to fit ARIMA, got {series.size}"
        )

    order_d = _select_d(series, max_d) if d is None else int(d)
    drifts = (True, False) if allow_drift and order_d <= 1 else (False,)

    tried: dict[tuple[tuple[int, int, int], bool], ArimaFit | None] = {}

    def attempt(order: tuple[int, int, int], drift: bool) -> ArimaFit | None:
        if order[0] > max_p or order[2] > max_q or min(order[0], order[2]) < 0:
            return None
        key = (order, drift)
        if key not in tried:
            tried[key] = _fit_one(series, order, drift)
        return tried[key]

    candidates: list[ArimaFit] = []
    if not stepwise:
        for p in range(max_p + 1):
            for q in range(max_q + 1):
                for drift in drifts:
                    fit = attempt((p, order_d, q), drift)
                    if fit:
                        candidates.append(fit)
    else:
        seeds = [(2, order_d, 2), (0, order_d, 0), (1, order_d, 0), (0, order_d, 1)]
        for seed in seeds:
            for drift in drifts:
                fit = attempt(seed, drift)
                if fit:
                    candidates.append(fit)
        if candidates:
            best = min(candidates, key=lambda f: f.aicc)
            improved = True
            while improved:
                improved = False
                p, dd, q = best.order
                neighbours = [
                    ((p + 1, dd, q), best.drift),
                    ((p - 1, dd, q), best.drift),
                    ((p, dd, q + 1), best.drift),
                    ((p, dd, q - 1), best.drift),
                    ((p + 1, dd, q + 1), best.drift),
                    ((p - 1, dd, q - 1), best.drift),
                    ((p, dd, q), not best.drift),
                ]
                for order, drift in neighbours:
                    if drift and (not allow_drift or order_d > 1):
                        continue
                    fit = attempt(order, drift)
                    if fit and fit.aicc < best.aicc - 1e-8:
                        best, improved = fit, True
                        break
            candidates.append(best)

    if not candidates:
        # Nothing converged (usually a near-constant or very short series):
        # Try the simplest model at the selected differencing order.
        fit = _fit_one(series, (0, order_d, 0), False)
        if fit is None:
            raise RuntimeError("no ARIMA model could be fitted to this series")
        return fit
    return min(candidates, key=lambda f: f.aicc)


# --------------------------------------------------------------------------- #
# forecasting one animal
# --------------------------------------------------------------------------- #
@dataclass
class Forecast:
    """A forecast of one animal's RELSA trajectory."""

    animal: str
    fit: ArimaFit
    times: np.ndarray
    predicted: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    actual: np.ndarray | None = None
    train_times: np.ndarray | None = None
    train_values: np.ndarray | None = None
    interpolated: bool = True
    alpha: float = 0.05
    warnings: list[str] = field(default_factory=list)

    def metrics(self) -> ForecastMetrics:
        if self.actual is None:
            raise ValueError("no actual values to score this forecast against")
        return forecast_metrics(self.actual, self.predicted, self.lower, self.upper)

    def to_frame(self) -> pd.DataFrame:
        data = {
            ID_COL: self.animal,
            TIME_COL: self.times,
            "predicted": self.predicted,
            "lower": self.lower,
            "upper": self.upper,
            "model": self.fit.label(),
            "alpha": self.alpha,
            "interpolated": self.interpolated,
            "n_observed": len(self.train_times) if self.train_times is not None else None,
            "notes": "; ".join(self.warnings),
        }
        if self.actual is not None:
            data["actual"] = self.actual
        return pd.DataFrame(data)


def forecast_animal(
    times: Iterable[float],
    values: Iterable[float],
    target_times: Iterable[float] | None = None,
    animal: str = "",
    interpolate_step: float | None = DEFAULT_STEP,
    alpha: float = 0.05,
    clip_at_zero: bool = True,
    **arima_kwargs,
) -> Forecast:
    """Fit ARIMA to one RELSA trajectory and forecast the requested time points.

    ``target_times`` defaults to one observation-spacing step beyond the last
    training point. With ``interpolate_step`` set, the model is fitted on the
    interpolated grid and the horizon is converted to grid steps, so targets
    must lie exactly on that grid.

    ``clip_at_zero`` floors the forecast and its interval at 0, since RELSA is
    non-negative by construction; the raw Gaussian interval can dip below.
    """
    t, y = _trajectory(times, values)
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be between zero and one")
    if clip_at_zero and np.any(y < 0):
        raise ValueError("observed RELSA scores must be nonnegative")
    if interpolate_step is not None and (not np.isfinite(interpolate_step) or interpolate_step <= 0):
        raise ValueError("interpolate_step must be positive or None")
    ok = np.isfinite(t) & np.isfinite(y)
    t, y = t[ok], y[ok]
    order = np.argsort(t)
    t, y = t[order], y[order]
    notes: list[str] = []

    if t.size < 2:
        raise ValueError(f"animal {animal!r}: fewer than 2 observed RELSA scores")

    spacing = float(np.median(np.diff(t))) if t.size > 1 else 1.0
    if target_times is None:
        targets = np.array([t[-1] + spacing], dtype=float)
    else:
        targets = np.asarray(list(target_times), dtype=float)
    if targets.ndim != 1 or not targets.size or not np.isfinite(targets).all():
        raise ValueError("target times must be a nonempty finite vector")
    if np.any(targets <= t[-1]):
        raise ValueError(
            f"animal {animal!r}: target times must be after the last training point "
            f"({t[-1]}); got {targets.tolist()}"
        )

    if interpolate_step:
        grid, series = interpolate_series(t, y, step=interpolate_step)
        step = interpolate_step
        origin = grid[-1]
        notes.append(
            f"fitted on {series.size} points interpolated at {interpolate_step} "
            f"time units from {t.size} observations; prediction intervals are "
            "conditional on the interpolated series, not independent observations"
        )
    else:
        if not np.allclose(np.diff(t), spacing, rtol=1e-6, atol=1e-9):
            raise ValueError("uneven observation times require an explicit regular interpolation grid")
        series = y
        step = spacing
        origin = t[-1]

    if t.size < MIN_TRAIN_POINTS:
        notes.append(
            f"only {t.size} observed points before the forecast — the paper's "
            "own weakest predictions come from exactly this situation; treat the "
            "interval, not the point estimate, as the message"
        )

    offsets = (targets - origin) / step
    if not np.allclose(offsets, np.round(offsets), rtol=0, atol=1e-7):
        raise ValueError("target times must align exactly with forecast grid steps")
    steps = int(round(offsets.max()))
    if steps > 100000:
        raise ValueError("forecast horizon exceeds 100000 steps")
    fit = auto_arima(series, **arima_kwargs)
    forecast = fit.results.get_forecast(steps=steps)  # type: ignore[union-attr]
    mean = np.asarray(forecast.predicted_mean, dtype=float)
    conf = np.asarray(forecast.conf_int(alpha=alpha), dtype=float)

    idx = np.round(offsets).astype(int) - 1
    predicted, lower, upper = mean[idx], conf[idx, 0], conf[idx, 1]
    if clip_at_zero:
        predicted = np.clip(predicted, 0.0, None)
        lower = np.clip(lower, 0.0, None)
        upper = np.clip(upper, 0.0, None)

    return Forecast(
        animal=animal,
        fit=fit,
        times=targets,
        predicted=predicted,
        lower=lower,
        upper=upper,
        train_times=t,
        train_values=y,
        interpolated=bool(interpolate_step),
        alpha=alpha,
        warnings=notes,
    )


# --------------------------------------------------------------------------- #
# endpoint prediction across a cohort
# --------------------------------------------------------------------------- #
def predict_endpoint(
    scores: pd.DataFrame,
    endpoints: dict[str, float] | None = None,
    score_col: str = "relsa",
    **kwargs,
) -> list[Forecast]:
    """Predict each animal's RELSA score at its humane endpoint.

    This is the paper's primary evaluation: every measurement *up to the time
    point immediately before* the endpoint trains the model, which then predicts
    the score at the endpoint itself, where the actual score is known and can be
    compared. ``endpoints`` maps animal id to endpoint time; omit it to use each
    animal's last observed time point.
    """
    validate(scores, [score_col])
    if endpoints is not None:
        unknown = set(endpoints) - set(scores[ID_COL].astype(str))
        if unknown or not np.isfinite(list(endpoints.values())).all():
            raise ValueError("endpoint IDs must exist and endpoint times must be finite")
    else:
        warnings.warn("using last observed times as evaluation targets; these are not verified humane endpoints", stacklevel=2)
    out: list[Forecast] = []
    for animal, block in scores.groupby(ID_COL, sort=False):
        block = block.dropna(subset=[score_col]).sort_values(TIME_COL)
        if block.empty:
            warnings.warn(f"animal {animal}: no finite RELSA scores", stacklevel=2)
            continue
        endpoint = (
            float(block[TIME_COL].iloc[-1])
            if endpoints is None
            else endpoints.get(str(animal))
        )
        if endpoint is None:
            continue
        train = block[block[TIME_COL] < endpoint]
        truth = block[block[TIME_COL] == endpoint]
        if len(train) < 2:
            warnings.warn(
                f"animal {animal}: only {len(train)} points before the endpoint, skipping",
                stacklevel=2,
            )
            continue
        forecast = forecast_animal(
            train[TIME_COL], train[score_col], target_times=[endpoint],
            animal=str(animal), **kwargs,
        )
        if not truth.empty:
            forecast.actual = np.array([float(truth[score_col].iloc[0])])
        out.append(forecast)
    return out


def forecast_indirect(
    prepared: pd.DataFrame,
    reference,
    target_time: float,
    animal: str = "",
    score_col: str = "relsa",
    **kwargs,
) -> dict[str, object]:
    """The *indirect* prediction: forecast each variable, then score the forecasts.

    ``prepared`` is the normalized measurement table for one animal (percent
    scale) and ``reference`` a ``relsa_score.ReferenceModel``. Each variable is
    forecast to ``target_time`` independently, and the RELSA score is computed
    from those forecasts.

    The paper found this worse than forecasting RELSA directly (median deviation
    -0.240 vs -0.002, d = 1.42): each variable's forecast error propagates into
    the score, whereas the direct forecast carries only its own error. Use this
    to reproduce that comparison, not as the working method.
    """
    from relsa_score import relsa_scores

    validate(prepared, list(reference.variables))
    if prepared[ID_COL].nunique() != 1:
        raise ValueError("indirect forecasting requires exactly one animal")
    block = prepared.sort_values(TIME_COL)
    animal = animal or str(block[ID_COL].iloc[0])
    train = block[block[TIME_COL] < target_time]
    row: dict[str, object] = {ID_COL: animal, TIME_COL: target_time}
    predicted_row = {ID_COL: animal, TIME_COL: target_time}
    for var in reference.variables:
        series = train[[TIME_COL, var]].dropna()
        if len(series) < 2:
            predicted_row[var] = np.nan
            continue
        try:
            forecast = forecast_animal(
                series[TIME_COL], series[var], target_times=[target_time],
                animal=f"{animal}:{var}", clip_at_zero=False, **kwargs,
            )
            predicted_row[var] = float(forecast.predicted[0])
        except Exception as exc:
            warnings.warn(f"indirect variable {var!r} failed: {exc}", stacklevel=2)
            predicted_row[var] = np.nan
    scored = relsa_scores(pd.DataFrame([predicted_row]), reference, keep_meta=False)
    row["predicted"] = float(scored[score_col].iloc[0])
    row.update({f"pred_{k}": v for k, v in predicted_row.items()
                if k not in (ID_COL, TIME_COL)})
    truth = block[np.isclose(block[TIME_COL], target_time)]
    if not truth.empty:
        actual = relsa_scores(truth, reference, keep_meta=False)
        row["actual"] = float(actual[score_col].iloc[0])
    return row


def rolling_forecast(
    times: Iterable[float],
    values: Iterable[float],
    min_train: int = 3,
    animal: str = "",
    **kwargs,
) -> pd.DataFrame:
    """One-step-ahead forecast at every time point, refitting as data accrue.

    This is how the paper compares predictability across outcome measures
    (Figure 2): at each time point, forecast the next one and record the
    deviation from what actually happened.
    """
    t, y = _trajectory(times, values)
    if min_train < 2:
        raise ValueError("min_train must be at least two")
    rows: list[dict[str, object]] = []
    for cut in range(min_train, len(t)):
        train_t, train_y = t[:cut], y[:cut]
        if np.isfinite(train_y).sum() < 2:
            continue
        try:
            forecast = forecast_animal(
                train_t, train_y, target_times=[t[cut]], animal=animal, **kwargs
            )
        except Exception as exc:  # a single failed refit must not stop the sweep
            rows.append({ID_COL: animal, TIME_COL: t[cut], "predicted": np.nan,
                         "lower": np.nan, "upper": np.nan, "actual": y[cut],
                         "model": f"failed: {type(exc).__name__}"})
            continue
        rows.append({
            ID_COL: animal,
            TIME_COL: float(t[cut]),
            "predicted": float(forecast.predicted[0]),
            "lower": float(forecast.lower[0]),
            "upper": float(forecast.upper[0]),
            "actual": float(y[cut]),
            "model": forecast.fit.label(),
            "alpha": forecast.alpha,
            "interpolated": forecast.interpolated,
            "n_observed": len(forecast.train_times) if forecast.train_times is not None else cut,
            "notes": "; ".join(forecast.warnings),
        })
    return pd.DataFrame(rows)


def summarize(forecasts: Sequence[Forecast], group: dict[str, str] | None = None) -> pd.DataFrame:
    """Per-animal and overall RMSE / PICP / MPIW, in the layout of the paper's Table 1."""
    rows: list[dict[str, object]] = []
    actual: list[float] = []
    predicted: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    for forecast in forecasts:
        if forecast.actual is None:
            continue
        metrics = forecast.metrics()
        rows.append({
            "group": (group or {}).get(forecast.animal, ""),
            ID_COL: forecast.animal,
            "model": forecast.fit.label(),
            "n": metrics.n, "n_interval": metrics.n_interval,
            "rmse": round(metrics.rmse, 4),
            "picp": round(metrics.picp, 1),
            "mpiw": round(metrics.mpiw, 3),
        })
        actual.extend(forecast.actual.tolist())
        predicted.extend(forecast.predicted.tolist())
        lower.extend(forecast.lower.tolist())
        upper.extend(forecast.upper.tolist())

    frame = pd.DataFrame(rows)
    if not actual:
        return frame
    overall = forecast_metrics(actual, predicted, lower, upper)
    if not frame.empty and frame["group"].astype(bool).any():
        for label, block in frame.groupby("group"):
            if not label:
                continue
            sub = [f for f in forecasts if f.animal in set(block[ID_COL])]
            agg = forecast_metrics(
                np.concatenate([f.actual for f in sub]),  # type: ignore[arg-type]
                np.concatenate([f.predicted for f in sub]),
                np.concatenate([f.lower for f in sub]),
                np.concatenate([f.upper for f in sub]),
            )
            frame = pd.concat([frame, pd.DataFrame([{
                "group": label, ID_COL: f"-- {label} --", "model": "",
                "n": agg.n, "n_interval": agg.n_interval, "rmse": round(agg.rmse, 4),
                "picp": round(agg.picp, 1), "mpiw": round(agg.mpiw, 3),
            }])], ignore_index=True)
    return pd.concat([frame, pd.DataFrame([{
        "group": "", ID_COL: "OVERALL", "model": "",
        "n": overall.n, "n_interval": overall.n_interval, "rmse": round(overall.rmse, 4),
        "picp": round(overall.picp, 1), "mpiw": round(overall.mpiw, 3),
    }])], ignore_index=True)


def plot_forecast(
    forecast: Forecast,
    path: str | Path,
    endpoint_threshold: float | None = None,
    zones: Sequence[float] = (),
    title: str | None = None,
) -> Path:
    """Trajectory, forecast, and interval in the style of the paper's Figure 1."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5.6, 3.8), constrained_layout=True)
    if forecast.train_times is not None:
        ax.plot(forecast.train_times, forecast.train_values, "-o", color="black",
                ms=4, lw=1.3, label="actual RELSA")
    ax.fill_between(
        np.concatenate([[forecast.train_times[-1]], forecast.times]),
        np.concatenate([[forecast.train_values[-1]], forecast.lower]),
        np.concatenate([[forecast.train_values[-1]], forecast.upper]),
        color="#4fc3c7", alpha=0.45,
        label=f"{100 * (1 - forecast.alpha):.0f}% prediction interval",
    )
    ax.plot(forecast.times, forecast.predicted, "o--", color="#1f7a7d", ms=5,
            label="predicted RELSA")
    if forecast.actual is not None:
        ax.plot(forecast.times, forecast.actual, "o", color="black", ms=5)
    if endpoint_threshold is not None:
        ax.axhline(endpoint_threshold, ls="--", color="#c1453b", lw=1.2)
        ax.annotate("user-supplied comparison line", xy=(0.02, endpoint_threshold),
                    xycoords=("axes fraction", "data"), xytext=(0, 4),
                    textcoords="offset points", color="#c1453b", fontsize=8)
    for zone in zones:
        ax.axhline(zone, ls=":", color="#666666", lw=1.0)
    ax.set_xlabel("time")
    ax.set_ylabel("RELSA score")
    ax.set_title(title or f"{forecast.animal}  —  {forecast.fit.label()}", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    path = Path(path)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Explore RELSA forecasts with nonseasonal ARIMA (foRcast-style).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("scores", help="CSV of RELSA scores (output of relsa_score.py)")
    parser.add_argument("--score-col", default="relsa")
    parser.add_argument(
        "--mode", choices=("endpoint", "rolling"), default="endpoint",
        help="endpoint: predict the score at each animal's endpoint; "
        "rolling: one-step-ahead forecast at every time point",
    )
    parser.add_argument(
        "--endpoints", metavar="ID=TIME", action="append", default=[],
        help="humane-endpoint time per animal, repeatable "
        "(default: last-observation evaluation only, not a verified endpoint)",
    )
    parser.add_argument("--animals", help="comma-separated ids to restrict to")
    parser.add_argument(
        "--interpolate-step", type=float, default=DEFAULT_STEP,
        help="grid for linear interpolation before fitting; 0 disables it",
    )
    parser.add_argument("--alpha", type=float, default=0.05,
                        help="1 - alpha is the prediction interval level")
    parser.add_argument("--max-p", type=int, default=5)
    parser.add_argument("--max-q", type=int, default=5)
    parser.add_argument("--max-d", type=int, default=2)
    parser.add_argument("--full-grid", action="store_true",
                        help="exhaustive p/q search instead of the stepwise hill-climb")
    parser.add_argument("--group-col", help="column labelling model/intervention, for the summary")
    parser.add_argument("--out", help="write per-forecast rows to this CSV")
    parser.add_argument("--summary-out", help="write the metric summary to this CSV")
    parser.add_argument("--plot-dir", help="write one figure per animal into this directory")
    parser.add_argument("--endpoint-line", type=float, default=None,
                        help="user-supplied comparison line; not an automatically inferred endpoint")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    frame = read_relsa_table(args.scores)
    for col in (ID_COL, TIME_COL):
        if col not in frame.columns:
            raise SystemExit(f"column {col!r} missing from {args.scores}")
    if args.score_col not in frame.columns:
        raise SystemExit(f"score column {args.score_col!r} missing from {args.scores}")
    validate(frame, [args.score_col])

    keep = parse_list(args.animals)
    if keep:
        frame = frame[frame[ID_COL].astype(str).isin(keep)]
        if frame.empty:
            raise SystemExit(f"no rows for animals {keep}")

    endpoints: dict[str, float] | None = None
    if args.endpoints:
        endpoints = {}
        for pair in args.endpoints:
            if "=" not in pair:
                raise SystemExit(f"--endpoints expects ID=TIME, got {pair!r}")
            animal, value = pair.split("=", 1)
            endpoints[animal] = float(value)

    groups = None
    if args.group_col:
        if args.group_col not in frame.columns:
            raise SystemExit(f"--group-col {args.group_col!r} not in data")
        groups = (
            frame.groupby(ID_COL)[args.group_col].first().astype(str).to_dict()
        )
        groups = {str(k): v for k, v in groups.items()}

    step = args.interpolate_step or None
    arima_kwargs = dict(
        interpolate_step=step,
        alpha=args.alpha,
        max_p=args.max_p,
        max_q=args.max_q,
        max_d=args.max_d,
        stepwise=not args.full_grid,
    )

    if args.mode == "rolling":
        rows = []
        for animal, block in frame.groupby(ID_COL, sort=False):
            block = block.dropna(subset=[args.score_col]).sort_values(TIME_COL)
            rows.append(
                rolling_forecast(
                    block[TIME_COL], block[args.score_col], animal=str(animal),
                    **arima_kwargs,
                )
            )
        table = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
        if table.empty:
            raise SystemExit("no forecasts could be produced")
        metrics = forecast_metrics(
            table["actual"], table["predicted"], table["lower"], table["upper"]
        )
        print(table.to_string(index=False))
        print(
            f"\nrolling one-step-ahead: n={metrics.n} n_interval={metrics.n_interval}  RMSE={metrics.rmse:.4f}  "
            f"PICP={metrics.picp:.1f}%  MPIW={metrics.mpiw:.3f}"
        )
        if args.out:
            table.to_csv(args.out, index=False)
            print(f"wrote {args.out}", file=sys.stderr)
        return 0

    forecasts = predict_endpoint(
        frame, endpoints=endpoints, score_col=args.score_col, **arima_kwargs
    )
    if not forecasts:
        raise SystemExit("no animal had enough data to forecast")

    detail = pd.concat([f.to_frame() for f in forecasts], ignore_index=True)
    print(detail.to_string(index=False))
    summary = summarize(forecasts, group=groups)
    print("\n" + summary.to_string(index=False))

    for forecast in forecasts:
        for note in forecast.warnings:
            print(f"note [{forecast.animal}]: {note}", file=sys.stderr)

    if args.out:
        detail.to_csv(args.out, index=False)
        print(f"wrote {args.out}", file=sys.stderr)
    if args.summary_out:
        summary.to_csv(args.summary_out, index=False)
        print(f"wrote {args.summary_out}", file=sys.stderr)
    if args.plot_dir:
        directory = Path(args.plot_dir)
        directory.mkdir(parents=True, exist_ok=True)
        for index, forecast in enumerate(forecasts, 1):
            safe_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in forecast.animal)
            written = plot_forecast(
                forecast, directory / f"{index}-{safe_id}.png",
                endpoint_threshold=args.endpoint_line,
            )
            print(f"wrote {written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
