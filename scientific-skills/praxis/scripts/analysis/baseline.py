"""Baseline correction: polynomial, ALS (asymmetric least squares), Shirley,
Tougaard, SNIP, and rubberband methods.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from scripts.core.utils import validate_xy


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def correct_baseline(
    x: Any,
    y: Any,
    method: str = "als",
    **kwargs: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Remove baseline from y(x) data.

    Parameters
    ----------
    x, y : array-like
    method : str
        'polynomial', 'als', 'snip', 'rubberband', 'shirley'.
    **kwargs
        Method-specific parameters.

    Returns
    -------
    (y_corrected, baseline, x)
    """
    x, y = validate_xy(np.asarray(x, dtype=float), np.asarray(y, dtype=float), allow_nan=False)

    methods = {
        "polynomial": _baseline_polynomial,
        "poly": _baseline_polynomial,
        "als": _baseline_als,
        "snip": _baseline_snip,
        "rubberband": _baseline_rubberband,
        "shirley": _baseline_shirley,
    }

    func = methods.get(method.lower())
    if func is None:
        available = ", ".join(sorted(methods.keys()))
        raise ValueError(f"Unknown baseline method: '{method}'. Available: {available}")

    baseline = func(x, y, **kwargs)
    y_corrected = y - baseline

    print(f"[Praxis] Baseline correction: {method}")
    return y_corrected, baseline, x


# ---------------------------------------------------------------------------
# Polynomial baseline
# ---------------------------------------------------------------------------

def _baseline_polynomial(
    x: np.ndarray,
    y: np.ndarray,
    *,
    order: int = 3,
    regions: Optional[list[tuple[float, float]]] = None,
    n_iter: int = 0,
) -> np.ndarray:
    """Polynomial baseline fit.

    Parameters
    ----------
    order : int
        Polynomial order (1=linear, 2=quadratic, 3=cubic, etc.).
    regions : list of (x_min, x_max) tuples, optional
        Fit only to these x regions (baseline anchor points).
    n_iter : int
        If > 0, iteratively refit excluding points above the baseline.
    """
    if regions is not None:
        mask = np.zeros(len(x), dtype=bool)
        for xmin, xmax in regions:
            mask |= (x >= xmin) & (x <= xmax)
        x_fit, y_fit = x[mask], y[mask]
    else:
        x_fit, y_fit = x, y

    coeffs = np.polyfit(x_fit, y_fit, order)
    baseline = np.polyval(coeffs, x)

    # Iterative refinement: exclude points far above baseline
    for _ in range(n_iter):
        residual = y - baseline
        mask_below = residual <= np.std(residual)
        if regions is not None:
            region_mask = np.zeros(len(x), dtype=bool)
            for xmin, xmax in regions:
                region_mask |= (x >= xmin) & (x <= xmax)
            mask_below &= region_mask
        if mask_below.sum() < order + 1:
            break
        coeffs = np.polyfit(x[mask_below], y[mask_below], order)
        baseline = np.polyval(coeffs, x)

    return baseline


# ---------------------------------------------------------------------------
# Asymmetric Least Squares (ALS) — Eilers & Boelens (2005)
# ---------------------------------------------------------------------------

def _baseline_als(
    x: np.ndarray,
    y: np.ndarray,
    *,
    lam: float = 1e6,
    p: float = 0.01,
    n_iter: int = 10,
) -> np.ndarray:
    """Asymmetric least squares smoothing for baseline estimation.

    Parameters
    ----------
    lam : float
        Smoothness parameter (1e4 to 1e9). Larger = smoother.
    p : float
        Asymmetry parameter (0.001 to 0.05). Smaller = more asymmetric
        (penalises overestimation more).
    n_iter : int
        Number of iterations.
    """
    n = len(y)
    D = sparse.diags([1, -2, 1], [0, 1, 2], shape=(n - 2, n))
    w = np.ones(n)

    for _ in range(n_iter):
        W = sparse.spdiags(w, 0, n, n)
        Z = W + lam * D.T.dot(D)
        baseline = spsolve(Z, w * y)
        w = p * (y > baseline) + (1 - p) * (y <= baseline)

    return baseline


# ---------------------------------------------------------------------------
# SNIP — Statistics-sensitive Non-linear Iterative Peak-clipping
# ---------------------------------------------------------------------------

def _baseline_snip(
    x: np.ndarray,
    y: np.ndarray,
    *,
    n_iter: int = 40,
) -> np.ndarray:
    """SNIP baseline estimation (Ryan et al., 1988).

    Parameters
    ----------
    n_iter : int
        Number of clipping iterations. More = smoother baseline.
    """
    # Work in log-sqrt space for better peak suppression
    y_work = np.log(np.log(np.sqrt(np.maximum(y, 1e-10) + 1) + 1) + 1)

    for i in range(1, n_iter + 1):
        rolled_left = np.roll(y_work, i)
        rolled_right = np.roll(y_work, -i)
        avg = (rolled_left + rolled_right) / 2

        # Handle edges
        avg[:i] = y_work[:i]
        avg[-i:] = y_work[-i:]

        y_work = np.minimum(y_work, avg)

    # Transform back
    baseline = (np.exp(np.exp(y_work) - 1) - 1) ** 2 - 1

    return baseline


# ---------------------------------------------------------------------------
# Rubberband baseline
# ---------------------------------------------------------------------------

def _baseline_rubberband(
    x: np.ndarray,
    y: np.ndarray,
) -> np.ndarray:
    """Rubberband (convex hull) baseline correction.

    Fits a baseline along the lower convex hull of the spectrum.
    """
    from scipy.spatial import ConvexHull

    points = np.column_stack([x, y])

    try:
        hull = ConvexHull(points)
    except Exception:
        # Fallback to linear baseline if hull fails
        return np.linspace(y[0], y[-1], len(y))

    # Find hull vertices on the lower boundary
    hull_vertices = hull.vertices
    hull_x = x[hull_vertices]
    hull_y = y[hull_vertices]

    # Sort by x
    order = np.argsort(hull_x)
    hull_x = hull_x[order]
    hull_y = hull_y[order]

    # Keep only lower hull: vertices where y is below the mean
    mean_y = np.mean(y)
    lower_mask = hull_y <= mean_y
    # Always include first and last points
    lower_mask[0] = True
    lower_mask[-1] = True

    if lower_mask.sum() < 2:
        return np.linspace(y[0], y[-1], len(y))

    # Interpolate baseline through lower hull points
    baseline = np.interp(x, hull_x[lower_mask], hull_y[lower_mask])

    return baseline


# ---------------------------------------------------------------------------
# Shirley baseline (for XPS)
# ---------------------------------------------------------------------------

def _baseline_shirley(
    x: np.ndarray,
    y: np.ndarray,
    *,
    tol: float = 1e-6,
    max_iter: int = 50,
) -> np.ndarray:
    """Iterative Shirley background for XPS spectra.

    Assumes x is binding energy (decreasing) and y is intensity (counts).

    Parameters
    ----------
    tol : float
        Convergence tolerance.
    max_iter : int
        Maximum iterations.
    """
    n = len(y)

    # Ensure x is in decreasing order for Shirley convention
    if x[0] < x[-1]:
        x = x[::-1]
        y = y[::-1]
        reversed_input = True
    else:
        reversed_input = False

    # Background endpoints
    y_left = y[0]   # High BE side
    y_right = y[-1]  # Low BE side

    baseline = np.full(n, y_right)

    for _ in range(max_iter):
        baseline_prev = baseline.copy()

        # Cumulative integral from right
        integral_total = np.trapezoid(y - baseline, x)
        if abs(integral_total) < 1e-30:
            break

        cumulative = np.zeros(n)
        for i in range(n - 2, -1, -1):
            cumulative[i] = cumulative[i + 1] + np.trapezoid(
                (y - baseline)[i:i + 2], x[i:i + 2]
            )

        baseline = y_right + (y_left - y_right) * cumulative / cumulative[0] if cumulative[0] != 0 else baseline

        # Check convergence
        if np.max(np.abs(baseline - baseline_prev)) < tol:
            break

    if reversed_input:
        baseline = baseline[::-1]

    return baseline
