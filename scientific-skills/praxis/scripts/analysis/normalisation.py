"""Data normalisation: min-max, z-score, area, reference, and custom."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from scipy.integrate import trapezoid

from scripts.core.utils import validate_array


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalise(
    y: Any,
    method: str = "minmax",
    *,
    x: Optional[Any] = None,
    reference: Optional[Any] = None,
    target_range: tuple[float, float] = (0.0, 1.0),
) -> np.ndarray:
    """Normalise a 1-D dataset.

    Parameters
    ----------
    y : array-like
        Data to normalise.
    method : str
        'minmax', 'zscore', 'area', 'max', 'reference', 'l2', 'sum'.
    x : array-like, optional
        x values (required for 'area' normalisation).
    reference : array-like or float, optional
        Reference data or value for 'reference' normalisation.
    target_range : (min, max)
        Target range for min-max normalisation.

    Returns
    -------
    np.ndarray
        Normalised data.
    """
    y = validate_array(y, "y").copy().astype(float)

    methods = {
        "minmax": _norm_minmax,
        "min_max": _norm_minmax,
        "zscore": _norm_zscore,
        "z_score": _norm_zscore,
        "area": _norm_area,
        "max": _norm_max,
        "reference": _norm_reference,
        "l2": _norm_l2,
        "sum": _norm_sum,
        "peak": _norm_max,
    }

    func = methods.get(method.lower())
    if func is None:
        available = ", ".join(sorted(set(methods.keys())))
        raise ValueError(f"Unknown normalisation method: '{method}'. Available: {available}")

    kwargs = {}
    if method.lower() in ("minmax", "min_max"):
        kwargs["target_range"] = target_range
    if method.lower() == "area":
        kwargs["x"] = x
    if method.lower() == "reference":
        kwargs["reference"] = reference

    result = func(y, **kwargs)
    print(f"[Praxis] Normalisation: {method}")
    return result


# ---------------------------------------------------------------------------
# Methods
# ---------------------------------------------------------------------------

def _norm_minmax(
    y: np.ndarray,
    *,
    target_range: tuple[float, float] = (0.0, 1.0),
) -> np.ndarray:
    """Min-max normalisation to target range."""
    y_min, y_max = np.nanmin(y), np.nanmax(y)
    if y_max - y_min == 0:
        return np.full_like(y, target_range[0])
    scaled = (y - y_min) / (y_max - y_min)
    return scaled * (target_range[1] - target_range[0]) + target_range[0]


def _norm_zscore(y: np.ndarray) -> np.ndarray:
    """Z-score normalisation: (y - mean) / std."""
    mean = np.nanmean(y)
    std = np.nanstd(y, ddof=1)
    if std == 0:
        return np.zeros_like(y)
    return (y - mean) / std


def _norm_area(y: np.ndarray, *, x: Optional[Any] = None) -> np.ndarray:
    """Area normalisation: divide by total integrated area."""
    if x is not None:
        x = np.asarray(x, dtype=float)
        area = trapezoid(np.abs(y), x)
    else:
        area = trapezoid(np.abs(y))
    if area == 0:
        return y
    return y / area


def _norm_max(y: np.ndarray) -> np.ndarray:
    """Normalise to maximum value (0 to 1)."""
    m = np.nanmax(np.abs(y))
    if m == 0:
        return y
    return y / m


def _norm_reference(
    y: np.ndarray,
    *,
    reference: Optional[Any] = None,
) -> np.ndarray:
    """Normalise by dividing by a reference signal or value."""
    if reference is None:
        raise ValueError("Reference data or value required for reference normalisation.")
    if np.isscalar(reference):
        if reference == 0:
            raise ValueError("Reference value cannot be zero.")
        return y / float(reference)
    ref = np.asarray(reference, dtype=float)
    if len(ref) != len(y):
        raise ValueError(f"Reference length ({len(ref)}) must match data length ({len(y)}).")
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(ref != 0, y / ref, 0.0)
    return result


def _norm_l2(y: np.ndarray) -> np.ndarray:
    """L2 (Euclidean) normalisation: y / ||y||."""
    norm = np.sqrt(np.nansum(y ** 2))
    if norm == 0:
        return y
    return y / norm


def _norm_sum(y: np.ndarray) -> np.ndarray:
    """Sum normalisation: y / sum(y)."""
    s = np.nansum(y)
    if s == 0:
        return y
    return y / s
