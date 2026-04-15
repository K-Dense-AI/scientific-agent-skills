"""AFM (Atomic Force Microscopy) surface analysis.

Surface roughness (Ra, Rq, Rz), height profiles, grain analysis,
and 3D surface plotting helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from scripts.core.utils import validate_array


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RoughnessResults:
    """Surface roughness parameters."""
    ra: float     # Arithmetic average roughness
    rq: float     # RMS roughness
    rz: float     # Average maximum height
    rmax: float   # Maximum peak-to-valley height
    rsk: float    # Skewness
    rku: float    # Kurtosis
    sa: Optional[float] = None   # Areal Ra (for 2D surfaces)
    sq: Optional[float] = None   # Areal Rq
    unit: str = "nm"

    def table(self) -> str:
        lines = [
            "[Praxis] Surface Roughness",
            f"  Ra   = {self.ra:.3f} {self.unit}",
            f"  Rq   = {self.rq:.3f} {self.unit}",
            f"  Rz   = {self.rz:.3f} {self.unit}",
            f"  Rmax = {self.rmax:.3f} {self.unit}",
            f"  Rsk  = {self.rsk:.4f}",
            f"  Rku  = {self.rku:.4f}",
        ]
        if self.sa is not None:
            lines.append(f"  Sa   = {self.sa:.3f} {self.unit} (areal)")
        if self.sq is not None:
            lines.append(f"  Sq   = {self.sq:.3f} {self.unit} (areal)")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# 1D Profile Roughness
# ---------------------------------------------------------------------------

def profile_roughness(
    heights: Any,
    *,
    unit: str = "nm",
    detrend: bool = True,
) -> RoughnessResults:
    """Calculate roughness parameters from a 1D height profile.

    Parameters
    ----------
    heights : array-like
        Height values along a line profile.
    unit : str
        Height unit for reporting.
    detrend : bool
        Remove linear trend (tilt) before calculation.

    Returns
    -------
    RoughnessResults
    """
    h = validate_array(heights, "heights").copy()

    if detrend:
        x = np.arange(len(h))
        coeffs = np.polyfit(x, h, 1)
        h = h - np.polyval(coeffs, x)

    mean_h = np.mean(h)
    deviations = h - mean_h

    ra = np.mean(np.abs(deviations))
    rq = np.sqrt(np.mean(deviations ** 2))
    rmax = np.max(h) - np.min(h)

    # Rz: average of 5 highest peaks and 5 deepest valleys
    n_extrema = min(5, len(h) // 10)
    if n_extrema > 0:
        sorted_dev = np.sort(deviations)
        rz = np.mean(sorted_dev[-n_extrema:]) - np.mean(sorted_dev[:n_extrema])
    else:
        rz = rmax

    # Skewness and kurtosis
    if rq > 0:
        rsk = np.mean(deviations ** 3) / rq ** 3
        rku = np.mean(deviations ** 4) / rq ** 4
    else:
        rsk = 0.0
        rku = 0.0

    results = RoughnessResults(
        ra=ra, rq=rq, rz=rz, rmax=rmax,
        rsk=rsk, rku=rku, unit=unit,
    )

    print(results.table())
    return results


# ---------------------------------------------------------------------------
# 2D Surface Roughness
# ---------------------------------------------------------------------------

def surface_roughness(
    height_map: Any,
    *,
    pixel_size: float = 1.0,
    unit: str = "nm",
    detrend: bool = True,
    detrend_order: int = 1,
) -> RoughnessResults:
    """Calculate areal roughness parameters from a 2D height map.

    Parameters
    ----------
    height_map : 2D array-like
        Height values (matrix).
    pixel_size : float
        Physical size of one pixel (for length calculations).
    unit : str
        Height unit.
    detrend : bool
        Remove polynomial surface tilt.
    detrend_order : int
        Order of polynomial for detrending (1 = plane, 2 = quadratic).

    Returns
    -------
    RoughnessResults
    """
    h = np.asarray(height_map, dtype=float)
    if h.ndim != 2:
        raise ValueError(f"Expected 2D height map, got shape {h.shape}")

    if detrend:
        h = _detrend_surface(h, order=detrend_order)

    mean_h = np.mean(h)
    deviations = h - mean_h

    sa = np.mean(np.abs(deviations))
    sq = np.sqrt(np.mean(deviations ** 2))
    rmax = np.max(h) - np.min(h)

    # Rz from line profiles (average of row-wise Rz values)
    rz_values = []
    for row in deviations:
        n_ext = min(5, len(row) // 10)
        if n_ext > 0:
            s = np.sort(row)
            rz_values.append(np.mean(s[-n_ext:]) - np.mean(s[:n_ext]))
    rz = np.mean(rz_values) if rz_values else rmax

    # Profile roughness from the central row
    central_row = h[h.shape[0] // 2, :]
    dev_central = central_row - np.mean(central_row)
    ra = np.mean(np.abs(dev_central))
    rq = np.sqrt(np.mean(dev_central ** 2))

    # Skewness and kurtosis
    if sq > 0:
        rsk = np.mean(deviations ** 3) / sq ** 3
        rku = np.mean(deviations ** 4) / sq ** 4
    else:
        rsk = 0.0
        rku = 0.0

    results = RoughnessResults(
        ra=ra, rq=rq, rz=rz, rmax=rmax,
        rsk=rsk, rku=rku,
        sa=sa, sq=sq, unit=unit,
    )

    print(results.table())
    return results


def _detrend_surface(h: np.ndarray, order: int = 1) -> np.ndarray:
    """Remove polynomial surface tilt from a 2D height map."""
    rows, cols = h.shape
    y_coords, x_coords = np.mgrid[:rows, :cols]
    x_flat = x_coords.ravel()
    y_flat = y_coords.ravel()
    z_flat = h.ravel()

    if order == 1:
        # Fit a plane: z = ax + by + c
        A = np.column_stack([x_flat, y_flat, np.ones_like(x_flat)])
    elif order == 2:
        # Fit quadratic: z = ax^2 + by^2 + cxy + dx + ey + f
        A = np.column_stack([
            x_flat ** 2, y_flat ** 2, x_flat * y_flat,
            x_flat, y_flat, np.ones_like(x_flat),
        ])
    else:
        raise ValueError("Detrend order must be 1 or 2.")

    coeffs, _, _, _ = np.linalg.lstsq(A, z_flat, rcond=None)
    trend = (A @ coeffs).reshape(rows, cols)

    return h - trend


# ---------------------------------------------------------------------------
# Height profile extraction
# ---------------------------------------------------------------------------

def extract_profile(
    height_map: Any,
    *,
    row: Optional[int] = None,
    col: Optional[int] = None,
    start: Optional[tuple[int, int]] = None,
    end: Optional[tuple[int, int]] = None,
    pixel_size: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract a height profile from a 2D map.

    Parameters
    ----------
    height_map : 2D array
    row : int, optional
        Extract a horizontal profile at this row.
    col : int, optional
        Extract a vertical profile at this column.
    start, end : (row, col), optional
        Extract an arbitrary line profile between two points.
    pixel_size : float
        Physical size per pixel.

    Returns
    -------
    (position, height) arrays.
    """
    h = np.asarray(height_map, dtype=float)

    if row is not None:
        profile = h[row, :]
        position = np.arange(len(profile)) * pixel_size
    elif col is not None:
        profile = h[:, col]
        position = np.arange(len(profile)) * pixel_size
    elif start is not None and end is not None:
        # Bresenham-like line sampling
        r0, c0 = start
        r1, c1 = end
        n_points = max(abs(r1 - r0), abs(c1 - c0)) + 1
        rows = np.linspace(r0, r1, n_points).astype(int)
        cols = np.linspace(c0, c1, n_points).astype(int)
        rows = np.clip(rows, 0, h.shape[0] - 1)
        cols = np.clip(cols, 0, h.shape[1] - 1)
        profile = h[rows, cols]
        # Distance
        dr = (rows - rows[0]) * pixel_size
        dc = (cols - cols[0]) * pixel_size
        position = np.sqrt(dr ** 2 + dc ** 2)
    else:
        # Default: central horizontal profile
        row = h.shape[0] // 2
        profile = h[row, :]
        position = np.arange(len(profile)) * pixel_size

    return position, profile
