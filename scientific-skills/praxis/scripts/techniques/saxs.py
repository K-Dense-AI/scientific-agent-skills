"""Small-angle X-ray and neutron scattering analysis (SAXS/SANS/WAXS).

Guinier analysis, Porod analysis, Kratky plots, and scattering invariant
calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
from scipy.integrate import trapezoid

from scripts.core.utils import validate_xy
from scripts.analysis.fitting import fit_curve


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GuinierResult:
    """Results from Guinier analysis."""
    rg: float  # radius of gyration (same units as 1/q)
    i_zero: float  # forward scattering intensity I(0)
    r_squared: float  # goodness of fit
    q_range_used: tuple[float, float] = (0.0, 0.0)


@dataclass
class PorodResult:
    """Results from Porod analysis."""
    porod_constant: float  # K_p
    porod_exponent: float  # should be ~4 for sharp interfaces
    specific_surface: float  # estimated specific surface area (a.u.)
    r_squared: float


@dataclass
class SAXSResults:
    """Full SAXS/SANS analysis results."""
    guinier: Optional[GuinierResult] = None
    porod: Optional[PorodResult] = None
    invariant_Q: Optional[float] = None

    def table(self) -> str:
        """Formatted results table."""
        lines = ["[Praxis] SAXS/SANS Analysis"]
        lines.append("  " + "-" * 55)

        if self.guinier is not None:
            g = self.guinier
            lines.append(f"  Guinier analysis:")
            lines.append(f"    Rg            = {g.rg:.4f}")
            lines.append(f"    I(0)          = {g.i_zero:.4e}")
            lines.append(f"    R^2           = {g.r_squared:.6f}")
            lines.append(f"    q range used  = [{g.q_range_used[0]:.4f}, {g.q_range_used[1]:.4f}]")

        if self.porod is not None:
            p = self.porod
            lines.append(f"  Porod analysis:")
            lines.append(f"    Porod const   = {p.porod_constant:.4e}")
            lines.append(f"    Porod exp     = {p.porod_exponent:.2f}")
            lines.append(f"    Spec. surface = {p.specific_surface:.4e}")
            lines.append(f"    R^2           = {p.r_squared:.6f}")

        if self.invariant_Q is not None:
            lines.append(f"  Scattering invariant Q = {self.invariant_Q:.4e}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyse_saxs(
    q: Any,
    intensity: Any,
    *,
    wavelength: float = 1.5406,
) -> SAXSResults:
    """General SAXS analysis with auto-detection of Guinier and Porod regions.

    Parameters
    ----------
    q : array-like
        Scattering vector magnitude (1/A or 1/nm).
    intensity : array-like
        Scattered intensity I(q).
    wavelength : float
        X-ray wavelength in Angstrom (default Cu K-alpha).

    Returns
    -------
    SAXSResults
    """
    q_arr, i_arr = validate_xy(
        np.asarray(q, dtype=float),
        np.asarray(intensity, dtype=float),
        allow_nan=False,
    )

    order = np.argsort(q_arr)
    q_arr, i_arr = q_arr[order], i_arr[order]

    # Remove q=0 if present
    mask = q_arr > 0
    q_arr, i_arr = q_arr[mask], i_arr[mask]

    results = SAXSResults()

    # Guinier analysis on low-q region
    try:
        results.guinier = guinier_analysis(q_arr, i_arr)
    except (ValueError, RuntimeError):
        pass

    # Porod analysis on high-q region
    try:
        results.porod = porod_analysis(q_arr, i_arr)
    except (ValueError, RuntimeError):
        pass

    # Scattering invariant
    try:
        results.invariant_Q = invariant(q_arr, i_arr)
    except (ValueError, RuntimeError):
        pass

    print(results.table())
    return results


# ---------------------------------------------------------------------------
# Guinier analysis
# ---------------------------------------------------------------------------

def guinier_analysis(
    q: Any,
    intensity: Any,
    *,
    q_range: Optional[tuple[float, float]] = None,
) -> GuinierResult:
    """Guinier fit: ln(I) vs q^2 in the low-q region.

    Guinier law: I(q) = I(0) * exp(-q^2 * Rg^2 / 3)
    -> ln(I) = ln(I(0)) - (Rg^2 / 3) * q^2

    Valid for q * Rg < 1.3.

    Parameters
    ----------
    q : array-like
        Scattering vector (1/A or 1/nm).
    intensity : array-like
        Scattered intensity.
    q_range : tuple, optional
        (q_min, q_max) for the fit region. Auto-detected if None.

    Returns
    -------
    GuinierResult
    """
    q_arr, i_arr = validate_xy(
        np.asarray(q, dtype=float),
        np.asarray(intensity, dtype=float),
        allow_nan=False,
    )

    order = np.argsort(q_arr)
    q_arr, i_arr = q_arr[order], i_arr[order]

    # Filter positive intensity values
    mask = (q_arr > 0) & (i_arr > 0)
    q_arr, i_arr = q_arr[mask], i_arr[mask]

    if len(q_arr) < 3:
        raise ValueError("Not enough valid data points for Guinier analysis.")

    # Select q range
    if q_range is not None:
        sel = (q_arr >= q_range[0]) & (q_arr <= q_range[1])
        q_fit = q_arr[sel]
        i_fit = i_arr[sel]
    else:
        # Auto-detect: use the lowest 20% of q range
        q_max_auto = q_arr[0] + 0.2 * (q_arr[-1] - q_arr[0])
        sel = q_arr <= q_max_auto
        q_fit = q_arr[sel]
        i_fit = i_arr[sel]

    if len(q_fit) < 3:
        raise ValueError("Not enough data points in Guinier region.")

    # Linear fit: ln(I) vs q^2
    x = q_fit ** 2
    y = np.log(i_fit)

    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs

    # R^2
    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Extract parameters
    # slope = -Rg^2 / 3  =>  Rg = sqrt(-3 * slope)
    if slope >= 0:
        raise ValueError(f"Guinier slope is positive ({slope:.4e}); cannot extract Rg.")

    rg = np.sqrt(-3.0 * slope)
    i_zero = np.exp(intercept)

    q_range_used = (float(q_fit[0]), float(q_fit[-1]))

    # Validate q*Rg < 1.3
    qrg_max = q_fit[-1] * rg
    if qrg_max > 1.3:
        print(f"  Warning: q*Rg = {qrg_max:.2f} > 1.3 at upper q limit. "
              "Guinier approximation may not be valid.")

    result = GuinierResult(
        rg=float(rg),
        i_zero=float(i_zero),
        r_squared=float(r_sq),
        q_range_used=q_range_used,
    )

    print(f"[Praxis] Guinier: Rg = {rg:.4f}, I(0) = {i_zero:.4e}, R^2 = {r_sq:.6f}")
    return result


# ---------------------------------------------------------------------------
# Porod analysis
# ---------------------------------------------------------------------------

def porod_analysis(
    q: Any,
    intensity: Any,
    *,
    q_range: Optional[tuple[float, float]] = None,
) -> PorodResult:
    """Porod fit in the high-q region.

    Porod law: I(q) -> K_p / q^n (n ~ 4 for sharp interfaces).
    Fit log(I) vs log(q) to extract exponent and Porod constant.

    Parameters
    ----------
    q : array-like
        Scattering vector.
    intensity : array-like
        Scattered intensity.
    q_range : tuple, optional
        (q_min, q_max) for the fit region. Auto-detected if None.

    Returns
    -------
    PorodResult
    """
    q_arr, i_arr = validate_xy(
        np.asarray(q, dtype=float),
        np.asarray(intensity, dtype=float),
        allow_nan=False,
    )

    order = np.argsort(q_arr)
    q_arr, i_arr = q_arr[order], i_arr[order]

    mask = (q_arr > 0) & (i_arr > 0)
    q_arr, i_arr = q_arr[mask], i_arr[mask]

    if len(q_arr) < 3:
        raise ValueError("Not enough valid data points for Porod analysis.")

    # Select q range
    if q_range is not None:
        sel = (q_arr >= q_range[0]) & (q_arr <= q_range[1])
        q_fit = q_arr[sel]
        i_fit = i_arr[sel]
    else:
        # Auto-detect: use the upper 30% of q range
        q_min_auto = q_arr[0] + 0.7 * (q_arr[-1] - q_arr[0])
        sel = q_arr >= q_min_auto
        q_fit = q_arr[sel]
        i_fit = i_arr[sel]

    if len(q_fit) < 3:
        raise ValueError("Not enough data points in Porod region.")

    # Linear fit: log(I) vs log(q)
    # log(I) = log(K_p) - n * log(q)
    x = np.log(q_fit)
    y = np.log(i_fit)

    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs

    # R^2
    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    porod_exponent = -slope
    porod_constant = np.exp(intercept)

    # Specific surface area (proportional to Porod constant / invariant)
    # Here we just report K_p as the surface estimate
    specific_surface = porod_constant

    result = PorodResult(
        porod_constant=float(porod_constant),
        porod_exponent=float(porod_exponent),
        specific_surface=float(specific_surface),
        r_squared=float(r_sq),
    )

    print(f"[Praxis] Porod: K_p = {porod_constant:.4e}, exponent = {porod_exponent:.2f}, R^2 = {r_sq:.6f}")
    return result


# ---------------------------------------------------------------------------
# Kratky plot
# ---------------------------------------------------------------------------

def kratky_plot(
    q: Any,
    intensity: Any,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a Kratky plot: I(q)*q^2 vs q.

    Used to distinguish folded (bell-shaped) from unfolded (plateau)
    particles.

    Parameters
    ----------
    q : array-like
        Scattering vector.
    intensity : array-like
        Scattered intensity.

    Returns
    -------
    (q, I*q^2)
    """
    q_arr, i_arr = validate_xy(
        np.asarray(q, dtype=float),
        np.asarray(intensity, dtype=float),
        allow_nan=False,
    )

    order = np.argsort(q_arr)
    q_arr, i_arr = q_arr[order], i_arr[order]

    kratky_y = i_arr * q_arr ** 2

    print(f"[Praxis] Kratky plot: {len(q_arr)} points, q range [{q_arr[0]:.4f}, {q_arr[-1]:.4f}]")
    return q_arr, kratky_y


# ---------------------------------------------------------------------------
# Scattering invariant
# ---------------------------------------------------------------------------

def invariant(
    q: Any,
    intensity: Any,
) -> float:
    """Calculate the scattering invariant Q = integral(I(q) * q^2 dq).

    Parameters
    ----------
    q : array-like
        Scattering vector.
    intensity : array-like
        Scattered intensity.

    Returns
    -------
    float
        Scattering invariant Q.
    """
    q_arr, i_arr = validate_xy(
        np.asarray(q, dtype=float),
        np.asarray(intensity, dtype=float),
        allow_nan=False,
    )

    order = np.argsort(q_arr)
    q_arr, i_arr = q_arr[order], i_arr[order]

    integrand = i_arr * q_arr ** 2
    Q = float(trapezoid(integrand, q_arr))

    print(f"[Praxis] Scattering invariant Q = {Q:.4e}")
    return Q
