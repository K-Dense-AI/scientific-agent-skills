"""Shared I/O, validation, and variable-preparation helpers for the RELSA workflow.

The RELSA long format is one row per animal per time point:

    id   treatment   condition   time   var_1 ... var_n

``id`` and ``time`` are required; ``treatment`` and ``condition`` are optional
grouping labels carried through untouched. Time may be days, hours, or minutes
as long as it increases monotonically per animal. The RELSA convention codes the
baseline time point as -1, but any value works when it is named explicitly.
"""

from __future__ import annotations

import warnings
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

ID_COL = "id"
TIME_COL = "time"
META_COLS = ("treatment", "condition")

# Time-column aliases accepted on input; all are renamed to ``time`` internally.
TIME_ALIASES = ("time", "day", "days", "hour", "hours", "timepoint", "t")


class RelsaDataError(ValueError):
    """Raised when input data cannot support a RELSA calculation."""


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def read_relsa_table(
    path: str | Path,
    sep: str | None = None,
    id_col: str = ID_COL,
    time_col: str | None = None,
) -> pd.DataFrame:
    """Read a RELSA-format table from CSV/TSV and return it with canonical names.

    ``sep=None`` chooses tab for .txt/.tsv/.tab, comma otherwise. An unnamed index column (as written
    by R's ``write.table``, and present in the published RELSA raw data) is
    dropped. The time column is detected from ``TIME_ALIASES`` unless named.
    """
    path = Path(path)
    if sep is None:
        sep = "\t" if path.suffix.lower() in {".txt", ".tsv", ".tab"} else ","
    with path.open(newline="") as handle:
        header = next(csv.reader(handle, delimiter=sep))
    if len(header) != len(set(header)):
        raise RelsaDataError("duplicate column names in input")
    frame = pd.read_csv(path, sep=sep, dtype={id_col: "string"},
                        keep_default_na=False, na_values=[""])

    unnamed = [c for c in frame.columns if str(c).startswith("Unnamed:")]
    frame = frame.drop(columns=unnamed)

    return canonicalize(frame, id_col=id_col, time_col=time_col)


def canonicalize(
    frame: pd.DataFrame,
    id_col: str = ID_COL,
    time_col: str | None = None,
) -> pd.DataFrame:
    """Rename the id/time columns to ``id``/``time`` and sort by animal and time."""
    frame = frame.copy()
    if not frame.columns.is_unique:
        raise RelsaDataError("duplicate column names")

    if id_col != ID_COL:
        if id_col not in frame.columns:
            raise RelsaDataError(f"id column {id_col!r} not in {list(frame.columns)}")
        if ID_COL in frame.columns:
            raise RelsaDataError("renaming the id column would overwrite 'id'")
        frame = frame.rename(columns={id_col: ID_COL})
    if ID_COL not in frame.columns:
        raise RelsaDataError(f"no {ID_COL!r} column in {list(frame.columns)}")

    if time_col is None:
        found = [c for c in frame.columns if str(c).lower() in TIME_ALIASES]
        if not found:
            raise RelsaDataError(
                "no time column found; expected one of "
                f"{TIME_ALIASES} or an explicit time_col"
            )
        if len(found) != 1:
            raise RelsaDataError("multiple time columns; specify time_col explicitly")
        time_col = found[0]
    elif time_col not in frame.columns:
        raise RelsaDataError(f"time column {time_col!r} not in {list(frame.columns)}")
    if time_col != TIME_COL:
        if TIME_COL in frame.columns:
            raise RelsaDataError("renaming the time column would overwrite 'time'")
        frame = frame.rename(columns={time_col: TIME_COL})

    frame[TIME_COL] = pd.to_numeric(frame[TIME_COL], errors="coerce")
    if not np.isfinite(frame[TIME_COL]).all():
        raise RelsaDataError("time column must contain finite numeric values")
    if frame[ID_COL].isna().any() or frame[ID_COL].astype(str).str.strip().eq("").any():
        raise RelsaDataError("animal IDs must be nonempty")

    return frame.sort_values([ID_COL, TIME_COL], kind="stable").reset_index(drop=True)


def variable_columns(frame: pd.DataFrame) -> list[str]:
    """Every numeric measurement column: not id, time, or a metadata label."""
    reserved = {ID_COL, TIME_COL, *META_COLS}
    return [c for c in frame.columns if c not in reserved]


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def validate(frame: pd.DataFrame, variables: Sequence[str]) -> None:
    """Check the invariants RELSA depends on, raising or warning as appropriate.

    Duplicate (id, time) rows are fatal: normalization and forecasting both
    assume one measurement per animal per time point. Everything else is a
    warning, because RELSA is explicitly designed to tolerate missing data.
    """
    if not frame.columns.is_unique or not frame.index.is_unique:
        raise RelsaDataError("column names and row index must be unique")
    if not variables or len(set(variables)) != len(variables):
        raise RelsaDataError("variables must be nonempty and unique")
    if ID_COL not in frame or TIME_COL not in frame:
        raise RelsaDataError("id and time columns are required")
    if frame[ID_COL].isna().any() or frame[ID_COL].astype(str).str.strip().eq("").any():
        raise RelsaDataError("animal IDs must be nonempty")
    if not np.isfinite(pd.to_numeric(frame[TIME_COL], errors="coerce")).all():
        raise RelsaDataError("time column must contain finite numeric values")
    missing = [v for v in variables if v not in frame.columns]
    if missing:
        raise RelsaDataError(f"variables not in data: {missing}")

    dup = frame.duplicated([ID_COL, TIME_COL], keep=False)
    if dup.any():
        offenders = (
            frame.loc[dup, [ID_COL, TIME_COL]].astype(str).agg(" @ ".join, axis=1).unique()
        )
        raise RelsaDataError(
            "multiple rows share an (id, time) pair, so normalization would be "
            f"ambiguous: {list(offenders)[:5]}. Aggregate per time point first "
            "(the published models average hourly telemetry to one value per day)."
        )

    for var in variables:
        col = pd.to_numeric(frame[var], errors="coerce")
        if (frame[var].notna() & col.isna()).any() or np.isinf(col).any():
            raise RelsaDataError(f"variable {var!r} has nonnumeric or infinite measurements")
        if col.notna().sum() == 0:
            warnings.warn(f"variable {var!r} is entirely missing", stacklevel=2)

    per_animal = frame.groupby(ID_COL)[TIME_COL].size()
    if per_animal.nunique() > 1:
        warnings.warn(
            "animals have different numbers of time points; RELSA handles this, "
            "but check that gaps are genuinely missing data and not misaligned time axes",
            stacklevel=2,
        )


# --------------------------------------------------------------------------- #
# variable preparation
# --------------------------------------------------------------------------- #
def score_to_percent(
    values: Iterable[float],
    max_score: float,
    baseline_score: float = 0.0,
) -> np.ndarray:
    """Map an ordinal severity score onto the RELSA percent scale.

    RELSA normalizes by dividing each measurement by its own baseline, which is
    undefined for a clinical score whose healthy baseline is 0. This maps the
    score's *scale* instead of its ratio: ``baseline_score`` becomes 100 and
    ``max_score`` becomes 200, so the variable behaves like any other "turned"
    parameter (rises above 100 as the animal worsens) and one full score point
    is worth ``100 / |max_score - baseline_score|`` percent.

    ``max_score`` may lie *below* ``baseline_score`` for scales where a lower
    number is worse — a nesting score where a well-built nest scores 5 and no
    nest scores 0 is ``score_to_percent(nesting, max_score=0,
    baseline_score=5)``. Either way the mapped variable is "turned".

    Pass the resulting column straight to the RELSA calculation, list it in
    ``turned``, and leave it out of ``normalize`` — it is already normalized.
    """
    values = np.asarray(list(values), dtype=float)
    span = float(max_score) - float(baseline_score)
    if not np.isfinite([max_score, baseline_score]).all() or span == 0:
        raise RelsaDataError(
            f"max_score ({max_score}) must differ from baseline_score ({baseline_score})"
        )
    finite = values[np.isfinite(values)]
    lo, hi = sorted((float(max_score), float(baseline_score)))
    if np.isinf(values).any() or np.any((finite < lo) | (finite > hi)):
        raise RelsaDataError("ordinal score lies outside its declared scale")
    return 100.0 + 100.0 * (values - float(baseline_score)) / span


def percent_of_baseline(
    frame: pd.DataFrame,
    variables: Sequence[str],
    baseline_time: float | Sequence[float] | None = None,
) -> pd.DataFrame:
    """Express each variable as a percentage of that animal's own baseline.

    ``baseline_time`` selects the baseline: a single time value, several time
    values (averaged, i.e. a baseline window), or ``None`` for each animal's
    first time point. Animals whose baseline is missing or zero yield all-NaN
    for that variable, with a warning — a zero baseline makes the ratio
    undefined, which is what ``score_to_percent`` exists to avoid.
    """
    validate(frame, variables)
    out = frame.copy()
    if baseline_time is None:
        window: list[float] | None = None
    elif np.isscalar(baseline_time):
        window = [float(baseline_time)]  # type: ignore[arg-type]
    else:
        window = [float(t) for t in baseline_time]  # type: ignore[union-attr]
    if window is not None and (not window or not np.isfinite(window).all()):
        raise RelsaDataError("baseline window must contain finite times")

    for var in variables:
        out[var] = pd.to_numeric(out[var], errors="raise").astype(float)

    problems: list[str] = []
    for animal, block in out.groupby(ID_COL, sort=False):
        if window is None:
            rows = block.index[block[TIME_COL] == block[TIME_COL].min()]
        else:
            rows = block.index[block[TIME_COL].isin(window)]
            if len(rows) == 0:
                problems.append(f"{animal} (no baseline time point)")
                out.loc[block.index, list(variables)] = np.nan
                continue
        for var in variables:
            window_values = out.loc[rows, var].to_numpy(dtype=float)
            finite = window_values[np.isfinite(window_values)]
            base = float(finite.mean()) if finite.size else np.nan
            if not np.isfinite(base) or base <= 0:
                problems.append(f"{animal}/{var} (baseline {base})")
                out.loc[block.index, var] = np.nan
                continue
            out.loc[block.index, var] = out.loc[block.index, var] / base * 100.0

    if problems:
        warnings.warn(
            "baseline missing or nonpositive, variable set to NaN for: "
            + ", ".join(problems[:8])
            + ("..." if len(problems) > 8 else "")
            + ". For scores whose healthy baseline is 0, use score_to_percent().",
            stacklevel=2,
        )
    return out


def parse_list(value: str | None) -> list[str]:
    """Split a comma-separated CLI option into a clean list."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# --------------------------------------------------------------------------- #
# metrics
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ForecastMetrics:
    """The three error metrics reported in Lutscher et al. (2026), Table 1."""

    n: int
    rmse: float
    picp: float
    mpiw: float
    n_interval: int = 0

    def as_dict(self) -> dict[str, float]:
        return {"n": self.n, "n_interval": self.n_interval,
                "rmse": self.rmse, "picp": self.picp, "mpiw": self.mpiw}


def forecast_metrics(
    actual: Iterable[float],
    predicted: Iterable[float],
    lower: Iterable[float] | None = None,
    upper: Iterable[float] | None = None,
) -> ForecastMetrics:
    """RMSE, prediction-interval coverage probability, and mean interval width.

    RMSE and PICP answer different questions and are reported together on
    purpose: a model can widen its intervals until PICP hits 100% without
    predicting anything, which is why MPIW (the mean width, in RELSA units)
    has to be read alongside the coverage.
    """
    a = np.asarray(list(actual), dtype=float)
    p = np.asarray(list(predicted), dtype=float)
    if a.ndim != 1 or a.shape != p.shape:
        raise ValueError(f"actual {a.shape} and predicted {p.shape} differ in length")

    ok = np.isfinite(a) & np.isfinite(p)
    rmse = float(np.sqrt(np.mean((a[ok] - p[ok]) ** 2))) if ok.any() else float("nan")

    picp = float("nan")
    mpiw = float("nan")
    n_interval = 0
    if (lower is None) != (upper is None):
        raise ValueError("supply both lower and upper intervals")
    if lower is not None and upper is not None:
        lo = np.asarray(list(lower), dtype=float)
        hi = np.asarray(list(upper), dtype=float)
        if lo.shape != a.shape or hi.shape != a.shape:
            raise ValueError("interval arrays must match actual and predicted")
        if np.any(lo > hi):
            raise ValueError("lower interval exceeds upper interval")
        band = ok & np.isfinite(lo) & np.isfinite(hi)
        n_interval = int(band.sum())
        if band.any():
            mpiw = float(np.mean(hi[band] - lo[band]))
        cov = band & np.isfinite(a)
        if cov.any():
            inside = (a[cov] >= lo[cov]) & (a[cov] <= hi[cov])
            picp = float(100.0 * np.mean(inside))

    return ForecastMetrics(n=int(ok.sum()), rmse=rmse, picp=picp, mpiw=mpiw,
                           n_interval=n_interval)
