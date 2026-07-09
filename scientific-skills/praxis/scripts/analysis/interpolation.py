"""Interpolation and resampling: linear, spline, cubic, Akima."""

from __future__ import annotations

from typing import Any, Optional, Union

import numpy as np
from scipy.interpolate import (
    interp1d,
    CubicSpline,
    Akima1DInterpolator,
    UnivariateSpline,
    PchipInterpolator,
)

from scripts.core.utils import validate_xy


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def interpolate(
    x: Any,
    y: Any,
    x_new: Optional[Any] = None,
    *,
    method: str = "cubic",
    n_points: int = 500,
    fill_value: Union[str, float] = "extrapolate",
    smoothing: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Interpolate y(x) onto new x values.

    Parameters
    ----------
    x, y : array-like
        Original data (must be sorted by x).
    x_new : array-like, optional
        New x values. If None, generates *n_points* evenly spaced values
        over the original x range.
    method : str
        'linear', 'cubic', 'cubic_spline', 'akima', 'pchip',
        'quadratic', 'spline'.
    n_points : int
        Number of interpolation points if x_new is None.
    fill_value : str or float
        How to handle x_new outside the original range.
        'extrapolate' or a numeric fill value.
    smoothing : float
        Smoothing factor for UnivariateSpline (0 = exact interpolation).

    Returns
    -------
    (x_new, y_new)
    """
    x, y = validate_xy(np.asarray(x, dtype=float), np.asarray(y, dtype=float), allow_nan=False)

    # Sort by x
    sort_idx = np.argsort(x)
    x = x[sort_idx]
    y = y[sort_idx]

    # Generate x_new if needed
    if x_new is None:
        x_new = np.linspace(x.min(), x.max(), n_points)
    else:
        x_new = np.asarray(x_new, dtype=float)

    method = method.lower()

    if method == "linear":
        f = interp1d(x, y, kind="linear", fill_value=fill_value,
                     bounds_error=False if fill_value != "extrapolate" else False)
        if fill_value == "extrapolate":
            f = interp1d(x, y, kind="linear", fill_value="extrapolate", bounds_error=False)
        y_new = f(x_new)

    elif method in ("cubic", "cubic_spline"):
        cs = CubicSpline(x, y, extrapolate=True)
        y_new = cs(x_new)

    elif method == "akima":
        ak = Akima1DInterpolator(x, y)
        y_new = ak(x_new)
        # Akima doesn't extrapolate by default; fill NaNs with edge values
        mask = np.isnan(y_new)
        if mask.any():
            y_new[x_new < x.min()] = y[0]
            y_new[x_new > x.max()] = y[-1]

    elif method == "pchip":
        pc = PchipInterpolator(x, y, extrapolate=True)
        y_new = pc(x_new)

    elif method == "quadratic":
        f = interp1d(x, y, kind="quadratic", fill_value="extrapolate", bounds_error=False)
        y_new = f(x_new)

    elif method == "spline":
        s = smoothing if smoothing > 0 else None
        sp = UnivariateSpline(x, y, s=s)
        y_new = sp(x_new)

    else:
        raise ValueError(
            f"Unknown interpolation method: '{method}'. "
            "Use linear, cubic, akima, pchip, quadratic, or spline."
        )

    print(f"[Praxis] Interpolation: {method}, {len(x)} -> {len(x_new)} points")
    return x_new, y_new


def resample(
    x: Any,
    y: Any,
    *,
    n_points: Optional[int] = None,
    dx: Optional[float] = None,
    method: str = "cubic",
) -> tuple[np.ndarray, np.ndarray]:
    """Resample data to uniform spacing.

    Parameters
    ----------
    x, y : array-like
    n_points : int, optional
        Number of output points.
    dx : float, optional
        Desired x spacing. Ignored if *n_points* is given.
    method : str
        Interpolation method.

    Returns
    -------
    (x_uniform, y_resampled)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    x_min, x_max = x.min(), x.max()

    if n_points is not None:
        x_new = np.linspace(x_min, x_max, n_points)
    elif dx is not None:
        x_new = np.arange(x_min, x_max + dx / 2, dx)
    else:
        # Default: same number of points, uniform spacing
        x_new = np.linspace(x_min, x_max, len(x))

    return interpolate(x, y, x_new, method=method)


def derivative(
    x: Any,
    y: Any,
    *,
    order: int = 1,
    method: str = "gradient",
    smoothing_window: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Numerical derivative dy/dx.

    Parameters
    ----------
    x, y : array-like
    order : int
        Derivative order (1st, 2nd, etc.).
    method : str
        'gradient' (numpy gradient), 'diff' (finite differences),
        'spline' (cubic spline derivative).
    smoothing_window : int
        If > 0, apply Savitzky-Golay smoothing before differentiating.

    Returns
    -------
    (x, dy_dx)
    """
    x, y = validate_xy(np.asarray(x, dtype=float), np.asarray(y, dtype=float), allow_nan=False)

    if smoothing_window > 0:
        from scripts.analysis.smoothing import smooth
        y = smooth(y, method="savgol", window=smoothing_window)

    if method == "gradient":
        result = y.copy()
        for _ in range(order):
            result = np.gradient(result, x)
        return x, result

    elif method == "diff":
        result = y.copy()
        x_out = x.copy()
        for _ in range(order):
            result = np.diff(result) / np.diff(x_out)
            x_out = (x_out[:-1] + x_out[1:]) / 2
        return x_out, result

    elif method == "spline":
        cs = CubicSpline(x, y)
        return x, cs(x, nu=order)

    else:
        raise ValueError(f"Unknown method: {method}. Use 'gradient', 'diff', or 'spline'.")


def integrate(
    x: Any,
    y: Any,
    *,
    method: str = "trapezoid",
    x_range: Optional[tuple[float, float]] = None,
    cumulative: bool = False,
) -> Union[float, np.ndarray]:
    """Numerical integration.

    Parameters
    ----------
    x, y : array-like
    method : str
        'trapezoid' or 'simpson'.
    x_range : (x_min, x_max), optional
        Integrate only over this range.
    cumulative : bool
        If True, return cumulative integral array.

    Returns
    -------
    float (total) or np.ndarray (cumulative)
    """
    from scipy.integrate import trapezoid, simpson, cumulative_trapezoid

    x, y = validate_xy(np.asarray(x, dtype=float), np.asarray(y, dtype=float), allow_nan=False)

    # Restrict range
    if x_range is not None:
        mask = (x >= x_range[0]) & (x <= x_range[1])
        x, y = x[mask], y[mask]

    if cumulative:
        result = cumulative_trapezoid(y, x, initial=0)
        print(f"[Praxis] Cumulative integration: {len(result)} points")
        return result

    if method == "trapezoid":
        val = trapezoid(y, x)
    elif method == "simpson":
        val = simpson(y, x=x)
    else:
        raise ValueError(f"Unknown method: {method}. Use 'trapezoid' or 'simpson'.")

    print(f"[Praxis] Integration ({method}): {val:.6g}")
    return float(val)
