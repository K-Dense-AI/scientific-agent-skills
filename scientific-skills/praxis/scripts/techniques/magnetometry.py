"""VSM and SQUID magnetometry analysis.

M-H hysteresis loop analysis, Curie temperature extraction,
and Langevin function fitting for superparamagnetic particles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
from scipy.optimize import curve_fit
from scipy.integrate import trapezoid

from scripts.core.utils import validate_xy, validate_array


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

k_B = 1.381e-23   # Boltzmann constant (J/K)
mu_0 = 4e-7 * np.pi  # Vacuum permeability (T.m/A)
mu_B = 9.274e-24   # Bohr magneton (J/T)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MHLoopResult:
    """Results from M-H hysteresis loop analysis."""
    ms: float                      # Saturation magnetisation
    mr: float                      # Remanent magnetisation (positive branch)
    hc: float                      # Coercive field (positive)
    hc_neg: float                  # Coercive field (negative)
    mr_neg: float                  # Remanent magnetisation (negative branch)
    squareness: float              # Mr/Ms ratio
    loop_area: Optional[float] = None  # Hysteresis loss (area of loop)

    def table(self) -> str:
        lines = [
            "[Praxis] M-H Hysteresis Loop",
            f"  Ms          = {self.ms:.4e}",
            f"  Mr (+)      = {self.mr:.4e}",
            f"  Mr (-)      = {self.mr_neg:.4e}",
            f"  Hc (+)      = {self.hc:.4e}",
            f"  Hc (-)      = {self.hc_neg:.4e}",
            f"  Squareness  = {self.squareness:.4f}",
        ]
        if self.loop_area is not None:
            lines.append(f"  Loop area   = {self.loop_area:.4e}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class CurieResult:
    """Results from Curie temperature determination."""
    curie_temp: float   # Curie temperature (same units as input)
    method: str         # 'inflection' or 'arrott'

    def table(self) -> str:
        lines = [
            "[Praxis] Curie Temperature",
            f"  Tc     = {self.curie_temp:.2f}",
            f"  Method = {self.method}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class LangevinResult:
    """Results from Langevin function fit."""
    ms: float              # Saturation magnetisation
    magnetic_moment: float # Magnetic moment per particle (J/T)
    moment_bohr: float     # Magnetic moment in Bohr magnetons
    r_squared: float       # Goodness of fit

    def table(self) -> str:
        lines = [
            "[Praxis] Langevin Fit (Superparamagnetic)",
            f"  Ms             = {self.ms:.4e}",
            f"  Moment (mu)    = {self.magnetic_moment:.4e} J/T",
            f"  Moment         = {self.moment_bohr:.1f} mu_B",
            f"  R2             = {self.r_squared:.6f}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# M-H hysteresis loop analysis
# ---------------------------------------------------------------------------

def analyse_mh_loop(
    field: Any,
    magnetisation: Any,
) -> MHLoopResult:
    """Extract figures of merit from an M-H hysteresis loop.

    Parameters
    ----------
    field : array-like
        Applied magnetic field (Oe, A/m, or T -- units preserved as-is).
    magnetisation : array-like
        Magnetisation (emu, emu/g, A/m, etc. -- units preserved as-is).

    Returns
    -------
    MHLoopResult
    """
    h, m = validate_xy(
        np.asarray(field, dtype=float),
        np.asarray(magnetisation, dtype=float),
        allow_nan=False,
    )

    # Saturation magnetisation: max |M|
    ms = max(abs(m.max()), abs(m.min()))

    # Remanent magnetisation: M at H = 0
    # Find zero crossings in H
    zero_crossings_h = np.where(np.diff(np.sign(h)))[0]

    mr_values = []
    for idx in zero_crossings_h:
        if idx + 1 < len(h):
            denom = abs(h[idx]) + abs(h[idx + 1])
            frac = abs(h[idx]) / denom if denom > 0 else 0.5
            m_at_zero = m[idx] + frac * (m[idx + 1] - m[idx])
            mr_values.append(m_at_zero)

    if mr_values:
        mr_pos = max(mr_values)
        mr_neg = min(mr_values)
    else:
        # Fallback: M at the point closest to H = 0
        idx_zero = np.argmin(np.abs(h))
        mr_pos = abs(m[idx_zero])
        mr_neg = -mr_pos

    # Coercive field: H at M = 0
    zero_crossings_m = np.where(np.diff(np.sign(m)))[0]

    hc_values = []
    for idx in zero_crossings_m:
        if idx + 1 < len(m):
            denom = abs(m[idx]) + abs(m[idx + 1])
            frac = abs(m[idx]) / denom if denom > 0 else 0.5
            h_at_zero = h[idx] + frac * (h[idx + 1] - h[idx])
            hc_values.append(h_at_zero)

    if hc_values:
        hc_pos = max(hc_values)
        hc_neg = min(hc_values)
    else:
        idx_zero = np.argmin(np.abs(m))
        hc_pos = abs(h[idx_zero])
        hc_neg = -hc_pos

    # Squareness ratio
    squareness = abs(mr_pos) / ms if ms > 0 else 0.0

    # Loop area (hysteresis loss)
    try:
        area = abs(trapezoid(m, h))
    except Exception:
        area = None

    result = MHLoopResult(
        ms=ms,
        mr=mr_pos,
        hc=abs(hc_pos),
        hc_neg=hc_neg,
        mr_neg=mr_neg,
        squareness=squareness,
        loop_area=area,
    )

    print(result.table())
    return result


# ---------------------------------------------------------------------------
# Curie temperature
# ---------------------------------------------------------------------------

def curie_temperature(
    temperature: Any,
    magnetisation: Any,
    *,
    method: str = "inflection",
) -> CurieResult:
    """Determine Curie temperature from M vs T data.

    Parameters
    ----------
    temperature : array-like
        Temperature (K or C -- units preserved).
    magnetisation : array-like
        Magnetisation values.
    method : str
        'inflection' -- Tc from the minimum of dM/dT (inflection point).
        'arrott' -- not yet implemented (placeholder).

    Returns
    -------
    CurieResult
    """
    temp, mag = validate_xy(
        np.asarray(temperature, dtype=float),
        np.asarray(magnetisation, dtype=float),
        allow_nan=False,
    )

    # Sort by temperature
    order = np.argsort(temp)
    temp, mag = temp[order], mag[order]

    if method == "inflection":
        # dM/dT
        dmdt = np.gradient(mag, temp)
        # Curie temperature: most negative dM/dT (steepest drop)
        idx_min = np.argmin(dmdt)
        tc = temp[idx_min]

    elif method == "arrott":
        raise NotImplementedError(
            "Arrott plot method is not yet implemented. Use method='inflection'."
        )
    else:
        raise ValueError(f"Unknown method: {method!r}. Supported: 'inflection', 'arrott'.")

    result = CurieResult(curie_temp=tc, method=method)
    print(result.table())
    return result


# ---------------------------------------------------------------------------
# Langevin function fit
# ---------------------------------------------------------------------------

def _langevin(x: np.ndarray) -> np.ndarray:
    """Langevin function: L(x) = coth(x) - 1/x.

    Handles x = 0 gracefully (L(0) = 0).
    """
    result = np.zeros_like(x, dtype=float)
    nonzero = np.abs(x) > 1e-12
    result[nonzero] = 1.0 / np.tanh(x[nonzero]) - 1.0 / x[nonzero]
    return result


def langevin_fit(
    field: Any,
    magnetisation: Any,
    *,
    temperature: float,
) -> LangevinResult:
    """Fit the Langevin function for superparamagnetic particles.

    M = Ms * L(mu * H / (kB * T))

    where L(x) = coth(x) - 1/x is the Langevin function.

    Parameters
    ----------
    field : array-like
        Applied magnetic field in T (SI).
    magnetisation : array-like
        Magnetisation (same units throughout).
    temperature : float
        Temperature in K.

    Returns
    -------
    LangevinResult
    """
    h, m = validate_xy(
        np.asarray(field, dtype=float),
        np.asarray(magnetisation, dtype=float),
        allow_nan=False,
    )

    if temperature <= 0:
        raise ValueError(f"Temperature must be positive, got {temperature} K.")

    # Sort by field
    order = np.argsort(h)
    h, m = h[order], m[order]

    # Model: M = Ms * L(mu * H / (kB * T))
    def model(h_arr: np.ndarray, Ms: float, mu: float) -> np.ndarray:
        x = mu * h_arr / (k_B * temperature)
        return Ms * _langevin(x)

    # Initial guesses
    Ms_init = max(abs(m.max()), abs(m.min()))
    # Rough guess for mu: at high field, L(x) -> 1, so look at intermediate
    mu_init = 1e-20  # ~1000 Bohr magnetons, reasonable starting point

    try:
        popt, pcov = curve_fit(
            model, h, m,
            p0=[Ms_init, mu_init],
            bounds=([0, 1e-30], [Ms_init * 10, 1e-15]),
            maxfev=20000,
        )
        Ms_fit, mu_fit = popt
    except RuntimeError:
        # Fallback
        Ms_fit = Ms_init
        mu_fit = mu_init

    # R-squared
    m_pred = model(h, Ms_fit, mu_fit)
    ss_res = np.sum((m - m_pred) ** 2)
    ss_tot = np.sum((m - np.mean(m)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Convert moment to Bohr magnetons
    moment_bohr = mu_fit / mu_B

    result = LangevinResult(
        ms=Ms_fit,
        magnetic_moment=mu_fit,
        moment_bohr=moment_bohr,
        r_squared=r2,
    )

    print(result.table())
    return result
