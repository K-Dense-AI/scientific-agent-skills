"""Capacitance-voltage analysis for semiconductors.

C-V profiling, Mott-Schottky analysis (1/C^2 vs V), doping concentration
extraction, flat-band voltage, and depletion width profiling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from scripts.core.utils import validate_xy, validate_array


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

q = 1.602e-19          # Elementary charge (C)
epsilon_0 = 8.854e-12  # Vacuum permittivity (F/m)
k_B = 1.381e-23        # Boltzmann constant (J/K)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MottSchottkyResult:
    """Results from Mott-Schottky analysis."""
    doping_concentration: float     # cm^-3
    flat_band_voltage: float        # V
    built_in_potential: float       # V
    carrier_type: str               # 'n-type' or 'p-type'
    r_squared: float                # Goodness of linear fit

    def table(self) -> str:
        lines = [
            "[Praxis] Mott-Schottky Analysis",
            f"  Doping conc.  = {self.doping_concentration:.4e} cm^-3",
            f"  Flat-band V   = {self.flat_band_voltage:.4f} V",
            f"  Built-in V    = {self.built_in_potential:.4f} V",
            f"  Carrier type  = {self.carrier_type}",
            f"  R2            = {self.r_squared:.6f}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class CVResult:
    """Results from general C-V analysis."""
    flat_band_voltage: Optional[float] = None  # V
    max_capacitance: float = 0.0               # F (or F/cm2)
    min_capacitance: float = 0.0               # F (or F/cm2)

    def table(self) -> str:
        lines = [
            "[Praxis] C-V Analysis",
            f"  Max capacitance = {self.max_capacitance:.4e}",
            f"  Min capacitance = {self.min_capacitance:.4e}",
        ]
        if self.flat_band_voltage is not None:
            lines.append(f"  Flat-band V     = {self.flat_band_voltage:.4f} V")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# General C-V analysis
# ---------------------------------------------------------------------------

def analyse_cv(
    voltage: Any,
    capacitance: Any,
    *,
    area: Optional[float] = None,
    permittivity: Optional[float] = None,
) -> CVResult:
    """Analyse a capacitance-voltage curve.

    Extracts flat-band voltage from the inflection point (maximum of
    dC/dV), plus min/max capacitance.

    Parameters
    ----------
    voltage : array-like
        Applied bias voltage in V.
    capacitance : array-like
        Measured capacitance in F (or F/cm2 if already normalised).
    area : float, optional
        Device area in cm2 for normalisation.
    permittivity : float, optional
        Relative permittivity of the semiconductor (not used here,
        but reserved for depletion width calculations).

    Returns
    -------
    CVResult
    """
    v, c = validate_xy(
        np.asarray(voltage, dtype=float),
        np.asarray(capacitance, dtype=float),
        allow_nan=False,
    )

    # Sort by voltage
    order = np.argsort(v)
    v, c = v[order], c[order]

    # Normalise by area if given
    if area is not None and area > 0:
        c = c / area

    # Flat-band voltage from inflection (max |dC/dV|)
    dcdv = np.gradient(c, v)
    inflection_idx = np.argmax(np.abs(dcdv))
    flat_band_v = v[inflection_idx]

    result = CVResult(
        flat_band_voltage=flat_band_v,
        max_capacitance=float(np.max(c)),
        min_capacitance=float(np.min(c)),
    )

    print(result.table())
    return result


# ---------------------------------------------------------------------------
# Mott-Schottky analysis
# ---------------------------------------------------------------------------

def mott_schottky(
    voltage: Any,
    capacitance: Any,
    *,
    area: float,
    permittivity: float = 11.7,
    frequency: Optional[float] = None,
    temperature: float = 300.0,
    fit_range: Optional[tuple[float, float]] = None,
) -> MottSchottkyResult:
    """Mott-Schottky analysis: extract doping and flat-band voltage.

    Plots 1/C^2 vs V and performs a linear fit in the depletion region.

    The Mott-Schottky equation:
        1/C^2 = (2 / (q * eps * eps0 * N)) * (V - Vfb - kT/q)

    Parameters
    ----------
    voltage : array-like
        Applied bias voltage in V.
    capacitance : array-like
        Measured capacitance in F.
    area : float
        Device area in cm2.
    permittivity : float
        Relative permittivity of the semiconductor (default 11.7 for Si).
    frequency : float, optional
        Measurement frequency in Hz (informational only).
    temperature : float
        Temperature in K (default 300 K).
    fit_range : (V_min, V_max), optional
        Voltage range for the linear fit. If None, the full range is used.

    Returns
    -------
    MottSchottkyResult
    """
    v, c = validate_xy(
        np.asarray(voltage, dtype=float),
        np.asarray(capacitance, dtype=float),
        allow_nan=False,
    )

    # Sort by voltage
    order = np.argsort(v)
    v, c = v[order], c[order]

    # Convert area from cm2 to m2
    area_m2 = area * 1e-4

    # Capacitance per unit area (F/m2)
    c_density = c / area_m2

    # 1/C^2 (per unit area)
    inv_c2 = 1.0 / (c_density ** 2)

    # Select fit range
    if fit_range is not None:
        mask = (v >= fit_range[0]) & (v <= fit_range[1])
        v_fit, inv_c2_fit = v[mask], inv_c2[mask]
    else:
        v_fit, inv_c2_fit = v, inv_c2

    if len(v_fit) < 3:
        raise ValueError("Need at least 3 data points in the fit range.")

    # Linear fit: 1/C^2 = slope * V + intercept
    coeffs = np.polyfit(v_fit, inv_c2_fit, 1)
    slope, intercept = coeffs

    # R-squared
    y_pred = np.polyval(coeffs, v_fit)
    ss_res = np.sum((inv_c2_fit - y_pred) ** 2)
    ss_tot = np.sum((inv_c2_fit - np.mean(inv_c2_fit)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Carrier type from slope sign
    # Positive slope => n-type, negative slope => p-type
    if slope > 0:
        carrier_type = "n-type"
    else:
        carrier_type = "p-type"

    # Doping concentration: N = 2 / (q * eps * eps0 * |slope|)
    eps_total = permittivity * epsilon_0
    N = 2.0 / (q * eps_total * abs(slope))  # in m^-3
    N_cm3 = N * 1e-6  # convert to cm^-3

    # Flat-band voltage: x-intercept of the linear fit, corrected for kT/q
    kT_over_q = k_B * temperature / q
    Vfb = -intercept / slope if abs(slope) > 0 else 0.0
    # The Mott-Schottky intercept gives Vfb + kT/q
    Vfb_corrected = Vfb - kT_over_q

    # Built-in potential ~ Vfb (for Schottky junction, Vbi ~ |Vfb|)
    Vbi = abs(Vfb_corrected)

    result = MottSchottkyResult(
        doping_concentration=N_cm3,
        flat_band_voltage=Vfb_corrected,
        built_in_potential=Vbi,
        carrier_type=carrier_type,
        r_squared=r2,
    )

    print(result.table())
    if frequency is not None:
        print(f"  Frequency     = {frequency:.2e} Hz")
    return result


# ---------------------------------------------------------------------------
# Doping profile
# ---------------------------------------------------------------------------

def doping_profile(
    voltage: Any,
    capacitance: Any,
    *,
    area: float,
    permittivity: float = 11.7,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate doping concentration vs depletion width from C-V data.

    Uses the differential capacitance method:
        N(W) = -2 / (q * eps * eps0 * d(1/C^2)/dV)
        W = eps * eps0 * A / C

    Parameters
    ----------
    voltage : array-like
        Applied bias voltage in V.
    capacitance : array-like
        Measured capacitance in F.
    area : float
        Device area in cm2.
    permittivity : float
        Relative permittivity (default 11.7 for Si).

    Returns
    -------
    (depletion_width, doping) : tuple of np.ndarray
        Depletion width in m and doping concentration in cm^-3.
    """
    v, c = validate_xy(
        np.asarray(voltage, dtype=float),
        np.asarray(capacitance, dtype=float),
        allow_nan=False,
    )

    # Sort by voltage
    order = np.argsort(v)
    v, c = v[order], c[order]

    area_m2 = area * 1e-4
    eps_total = permittivity * epsilon_0

    # Capacitance per unit area
    c_density = c / area_m2

    # Depletion width: W = eps * eps0 / C_density
    W = eps_total / c_density  # m

    # 1/C^2
    inv_c2 = 1.0 / (c_density ** 2)

    # d(1/C^2)/dV
    d_inv_c2_dv = np.gradient(inv_c2, v)

    # Doping: N = -2 / (q * eps * eps0 * d(1/C^2)/dV)
    # Use abs to handle sign (n-type vs p-type)
    with np.errstate(divide="ignore", invalid="ignore"):
        N = 2.0 / (q * eps_total * np.abs(d_inv_c2_dv))  # m^-3
    N_cm3 = N * 1e-6  # cm^-3

    # Filter out infinities/NaNs at edges
    valid = np.isfinite(N_cm3) & np.isfinite(W) & (N_cm3 > 0)
    W_valid = W[valid]
    N_valid = N_cm3[valid]

    print(f"[Praxis] Doping profile: {len(W_valid)} valid points")
    if len(W_valid) > 0:
        print(f"  Depletion width range: {W_valid.min():.4e} to {W_valid.max():.4e} m")
        print(f"  Doping range:          {N_valid.min():.4e} to {N_valid.max():.4e} cm^-3")

    return W_valid, N_valid
