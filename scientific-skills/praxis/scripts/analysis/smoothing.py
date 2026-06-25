"""Data smoothing and noise reduction.

Savitzky-Golay, moving average, Gaussian, median, and Whittaker smoothing.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from scipy.signal import savgol_filter, medfilt
from scipy.ndimage import gaussian_filter1d
from scipy import sparse
from scipy.sparse.linalg import spsolve

from scripts.core.utils import validate_array


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def smooth(
    y: Any,
    method: str = "savgol",
    **kwargs: Any,
) -> np.ndarray:
    """Smooth a 1-D signal.

    Parameters
    ----------
    y : array-like
        Input signal.
    method : str
        'savgol', 'moving_average', 'gaussian', 'median', 'whittaker'.
    **kwargs
        Method-specific parameters.

    Returns
    -------
    np.ndarray
        Smoothed signal.
    """
    y = validate_array(y, "y")

    methods = {
        "savgol": _smooth_savgol,
        "savitzky_golay": _smooth_savgol,
        "moving_average": _smooth_moving_average,
        "ma": _smooth_moving_average,
        "gaussian": _smooth_gaussian,
        "median": _smooth_median,
        "whittaker": _smooth_whittaker,
    }

    func = methods.get(method.lower())
    if func is None:
        available = ", ".join(sorted(methods.keys()))
        raise ValueError(f"Unknown smoothing method: '{method}'. Available: {available}")

    result = func(y, **kwargs)
    print(f"[Praxis] Smoothing: {method} ({len(y)} points)")
    return result


# ---------------------------------------------------------------------------
# Savitzky-Golay
# ---------------------------------------------------------------------------

def _smooth_savgol(
    y: np.ndarray,
    *,
    window: int = 11,
    order: int = 3,
    deriv: int = 0,
) -> np.ndarray:
    """Savitzky-Golay filter.

    Parameters
    ----------
    window : int
        Window length (must be odd, > order).
    order : int
        Polynomial order.
    deriv : int
        Derivative order (0 = smoothing only).
    """
    # Ensure window is odd
    if window % 2 == 0:
        window += 1
    if window < order + 2:
        window = order + 2
        if window % 2 == 0:
            window += 1

    return savgol_filter(y, window_length=window, polyorder=order, deriv=deriv)


# ---------------------------------------------------------------------------
# Moving average
# ---------------------------------------------------------------------------

def _smooth_moving_average(
    y: np.ndarray,
    *,
    window: int = 5,
    mode: str = "same",
) -> np.ndarray:
    """Simple moving average.

    Parameters
    ----------
    window : int
        Number of points to average.
    mode : str
        'same' (output length = input), 'valid' (no edge effects).
    """
    kernel = np.ones(window) / window
    if mode == "valid":
        return np.convolve(y, kernel, mode="valid")
    # 'same' mode with edge handling
    smoothed = np.convolve(y, kernel, mode="same")
    return smoothed


# ---------------------------------------------------------------------------
# Gaussian
# ---------------------------------------------------------------------------

def _smooth_gaussian(
    y: np.ndarray,
    *,
    sigma: float = 2.0,
) -> np.ndarray:
    """Gaussian smoothing.

    Parameters
    ----------
    sigma : float
        Standard deviation of the Gaussian kernel (in data points).
    """
    return gaussian_filter1d(y, sigma=sigma)


# ---------------------------------------------------------------------------
# Median
# ---------------------------------------------------------------------------

def _smooth_median(
    y: np.ndarray,
    *,
    window: int = 5,
) -> np.ndarray:
    """Median filter (good for spike removal).

    Parameters
    ----------
    window : int
        Kernel size (must be odd).
    """
    if window % 2 == 0:
        window += 1
    return medfilt(y, kernel_size=window)


# ---------------------------------------------------------------------------
# Whittaker
# ---------------------------------------------------------------------------

def _smooth_whittaker(
    y: np.ndarray,
    *,
    lam: float = 1e4,
    d: int = 2,
) -> np.ndarray:
    """Whittaker smoother (penalised least squares).

    Parameters
    ----------
    lam : float
        Smoothness parameter. Larger = smoother.
    d : int
        Order of differences (2 = penalise curvature).
    """
    n = len(y)
    E = sparse.eye(n, format="csc")
    D = _diff_matrix(n, d)
    W = E  # uniform weights
    Z = W + lam * D.T.dot(D)
    return np.array(spsolve(Z, y))


def _diff_matrix(n: int, d: int) -> sparse.csc_matrix:
    """Create a d-th order difference matrix of size (n-d) x n."""
    D = sparse.eye(n, format="csc")
    for _ in range(d):
        m = D.shape[0]
        D = D[1:, :] - D[:-1, :]
    return D
