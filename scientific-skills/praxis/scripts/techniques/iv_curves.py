"""I-V curve characterisation for electronics and photovoltaics.

General I-V analysis, solar cell J-V curves, diode fitting (Shockley),
and four-point probe resistivity measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
from scipy.optimize import curve_fit

from scripts.core.utils import validate_xy, validate_array
from scripts.analysis.fitting import fit_curve


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

q = 1.602e-19        # Elementary charge (C)
k_B = 1.381e-23      # Boltzmann constant (J/K)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FourPointResult:
    """Results from four-point probe measurement."""
    sheet_resistance: float       # Ohm/sq
    resistivity: Optional[float] = None  # Ohm.m
    correction_factor: float = 4.532     # pi / ln(2) for semi-infinite

    def table(self) -> str:
        lines = [
            "[Praxis] Four-Point Probe",
            f"  Sheet resistance  = {self.sheet_resistance:.4e} Ohm/sq",
            f"  Correction factor = {self.correction_factor:.4f}",
        ]
        if self.resistivity is not None:
            lines.append(f"  Resistivity       = {self.resistivity:.4e} Ohm.m")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class SolarCellResult:
    """Results from solar cell J-V analysis."""
    voc: float            # Open-circuit voltage (V)
    jsc: float            # Short-circuit current density (mA/cm2 or A/m2)
    fill_factor: float    # Fill factor (0 to 1)
    efficiency: Optional[float] = None  # Power conversion efficiency (%)
    pmax: float = 0.0     # Maximum power density
    v_mpp: float = 0.0    # Voltage at max power point (V)
    j_mpp: float = 0.0    # Current density at max power point

    def table(self) -> str:
        lines = [
            "[Praxis] Solar Cell J-V",
            f"  Voc          = {self.voc:.4f} V",
            f"  Jsc          = {self.jsc:.4f}",
            f"  Fill factor  = {self.fill_factor:.4f}",
            f"  Pmax         = {self.pmax:.4e}",
            f"  V_mpp        = {self.v_mpp:.4f} V",
            f"  J_mpp        = {self.j_mpp:.4f}",
        ]
        if self.efficiency is not None:
            lines.append(f"  PCE          = {self.efficiency:.2f}%")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class DiodeResult:
    """Results from Shockley diode fit."""
    ideality_factor: float        # n
    saturation_current: float     # I0 (A)
    series_resistance: float      # Rs (Ohm)
    r_squared: float              # Goodness of fit

    def table(self) -> str:
        lines = [
            "[Praxis] Diode Fit (Shockley)",
            f"  Ideality factor n = {self.ideality_factor:.4f}",
            f"  Saturation I0     = {self.saturation_current:.4e} A",
            f"  Series Rs         = {self.series_resistance:.4e} Ohm",
            f"  R2                = {self.r_squared:.6f}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# General I-V analysis
# ---------------------------------------------------------------------------

def analyse_iv(
    voltage: Any,
    current: Any,
) -> dict[str, Any]:
    """General I-V curve analysis.

    Performs linear fit to extract resistance. Detects diode-like behaviour
    from asymmetry in forward vs reverse bias.

    Parameters
    ----------
    voltage : array-like
        Voltage in V.
    current : array-like
        Current in A (or mA -- units preserved as-is).

    Returns
    -------
    dict
        Keys: 'resistance' (from linear fit), 'r_squared', 'is_diode'
        (True if significant forward/reverse asymmetry detected).
    """
    v, i = validate_xy(
        np.asarray(voltage, dtype=float),
        np.asarray(current, dtype=float),
        allow_nan=False,
    )

    # Linear fit for resistance
    fit = fit_curve(v, i, model="linear")
    slope = fit.params.get("slope", 0.0)
    resistance = 1.0 / slope if abs(slope) > 1e-30 else float("inf")

    # Detect diode behaviour: compare magnitude of current in forward vs reverse
    forward_mask = v > 0
    reverse_mask = v < 0
    is_diode = False
    if np.any(forward_mask) and np.any(reverse_mask):
        mean_fwd = np.mean(np.abs(i[forward_mask]))
        mean_rev = np.mean(np.abs(i[reverse_mask]))
        ratio = mean_fwd / mean_rev if mean_rev > 0 else float("inf")
        is_diode = ratio > 5.0

    result = {
        "resistance": resistance,
        "r_squared": fit.r_squared,
        "is_diode": is_diode,
    }

    lines = [
        "[Praxis] I-V Analysis",
        f"  Resistance = {resistance:.4e} (from linear fit)",
        f"  R2         = {fit.r_squared:.6f}",
        f"  Diode-like = {is_diode}",
    ]
    print("\n".join(lines))

    return result


# ---------------------------------------------------------------------------
# Solar cell J-V
# ---------------------------------------------------------------------------

def analyse_solar_cell(
    voltage: Any,
    current_density: Any,
    *,
    area: Optional[float] = None,
    illumination: Optional[float] = None,
) -> SolarCellResult:
    """Extract solar cell figures of merit from a J-V curve.

    Expects the photovoltaic convention where photocurrent is negative
    (or positive depending on convention -- the function handles both by
    working with the power = V * J product).

    Parameters
    ----------
    voltage : array-like
        Voltage in V.
    current_density : array-like
        Current density (mA/cm2 or A/m2). If *area* is given and raw
        current (A) is passed, it will be divided by area.
    area : float, optional
        Active area in cm2 (for converting current to current density).
    illumination : float, optional
        Incident power density in mW/cm2 (default 100 for 1-sun AM1.5).
        Used for efficiency calculation.

    Returns
    -------
    SolarCellResult
    """
    v, j = validate_xy(
        np.asarray(voltage, dtype=float),
        np.asarray(current_density, dtype=float),
        allow_nan=False,
    )

    # Convert current to density if area given
    if area is not None and area > 0:
        j = j / area

    # Sort by voltage
    order = np.argsort(v)
    v, j = v[order], j[order]

    # Jsc: current density at V = 0 (interpolate)
    jsc = float(np.interp(0.0, v, j))

    # Voc: voltage at J = 0 (interpolate)
    # Find sign change in j
    sign_changes = np.where(np.diff(np.sign(j)))[0]
    if len(sign_changes) > 0:
        idx = sign_changes[0]
        frac = abs(j[idx]) / (abs(j[idx]) + abs(j[idx + 1])) if (abs(j[idx]) + abs(j[idx + 1])) > 0 else 0.5
        voc = v[idx] + frac * (v[idx + 1] - v[idx])
    else:
        # Fallback: extrapolate
        voc = v[np.argmin(np.abs(j))]

    # Power density curve
    power = v * j
    # For standard PV convention (j negative under illumination), power is negative
    # Max power point is the most negative power (or most positive if j is positive)
    # Work with absolute power in the power-generating quadrant
    if jsc < 0:
        # Photocurrent is negative convention
        idx_mpp = np.argmin(power)  # Most negative power
    else:
        # Photocurrent is positive convention
        idx_mpp = np.argmax(power)

    pmax = abs(power[idx_mpp])
    v_mpp = v[idx_mpp]
    j_mpp = j[idx_mpp]

    # Fill factor
    denom = abs(voc * jsc)
    fill_factor = pmax / denom if denom > 0 else 0.0

    # Efficiency
    efficiency = None
    if illumination is not None and illumination > 0:
        efficiency = (pmax / illumination) * 100.0

    result = SolarCellResult(
        voc=voc,
        jsc=jsc,
        fill_factor=fill_factor,
        efficiency=efficiency,
        pmax=pmax,
        v_mpp=v_mpp,
        j_mpp=j_mpp,
    )

    print(result.table())
    return result


# ---------------------------------------------------------------------------
# Diode fitting (Shockley equation)
# ---------------------------------------------------------------------------

def _shockley_with_rs(v: np.ndarray, I0: float, n: float, Rs: float, T: float) -> np.ndarray:
    """Shockley diode equation with series resistance.

    I = I0 * (exp(q*(V - I*Rs) / (n*kB*T)) - 1)

    For fitting, we use an approximate form assuming Rs is small:
    I ~ I0 * (exp(q*V / (n*kB*T)) - 1) and then refine.
    """
    Vt = k_B * T / q  # Thermal voltage
    exponent = v / (n * Vt)
    # Clip to avoid overflow
    exponent = np.clip(exponent, -500, 500)
    return I0 * (np.exp(exponent) - 1.0)


def analyse_diode(
    voltage: Any,
    current: Any,
    *,
    model: str = "shockley",
    temperature: float = 300.0,
) -> DiodeResult:
    """Fit the Shockley diode equation to I-V data.

    I = I0 * (exp(qV / nkBT) - 1)

    Parameters
    ----------
    voltage : array-like
        Voltage in V (forward bias region preferred).
    current : array-like
        Current in A.
    model : str
        Diode model. Currently only 'shockley' is supported.
    temperature : float
        Temperature in K (default 300 K).

    Returns
    -------
    DiodeResult
    """
    v, i = validate_xy(
        np.asarray(voltage, dtype=float),
        np.asarray(current, dtype=float),
        allow_nan=False,
    )

    if model != "shockley":
        raise ValueError(f"Unknown diode model: {model!r}. Supported: 'shockley'.")

    # Use forward-bias region only (V > 0, I > 0)
    mask = (v > 0) & (i > 0)
    if np.sum(mask) < 3:
        raise ValueError("Need at least 3 forward-bias data points (V > 0, I > 0).")
    v_fwd, i_fwd = v[mask], i[mask]

    Vt = k_B * temperature / q  # Thermal voltage

    # Linear fit to ln(I) vs V for initial guesses
    ln_i = np.log(i_fwd)
    coeffs = np.polyfit(v_fwd, ln_i, 1)
    slope_init = coeffs[0]  # q / (n * kB * T)
    intercept_init = coeffs[1]  # ln(I0)

    n_init = q / (slope_init * k_B * temperature) if abs(slope_init) > 0 else 1.5
    I0_init = np.exp(intercept_init)

    # Nonlinear fit
    def shockley_simple(v_arr: np.ndarray, I0: float, n: float) -> np.ndarray:
        exponent = v_arr / (n * Vt)
        exponent = np.clip(exponent, -500, 500)
        return I0 * (np.exp(exponent) - 1.0)

    try:
        popt, pcov = curve_fit(
            shockley_simple, v_fwd, i_fwd,
            p0=[abs(I0_init), abs(n_init)],
            bounds=([0, 0.1], [1.0, 100.0]),
            maxfev=10000,
        )
        I0_fit, n_fit = popt
    except RuntimeError:
        # Fallback to initial estimates
        I0_fit = abs(I0_init)
        n_fit = abs(n_init)

    # R-squared
    i_pred = shockley_simple(v_fwd, I0_fit, n_fit)
    ss_res = np.sum((i_fwd - i_pred) ** 2)
    ss_tot = np.sum((i_fwd - np.mean(i_fwd)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Estimate series resistance from deviation at high current
    # V_actual = V_applied - I * Rs => Rs ~ (V - n*Vt*ln(I/I0 + 1)) / I
    Rs_estimates = []
    for vi, ii in zip(v_fwd[-5:], i_fwd[-5:]):
        if ii > 0 and I0_fit > 0:
            v_ideal = n_fit * Vt * np.log(ii / I0_fit + 1.0)
            rs_est = (vi - v_ideal) / ii if ii > 0 else 0
            if rs_est > 0:
                Rs_estimates.append(rs_est)
    Rs_fit = float(np.median(Rs_estimates)) if Rs_estimates else 0.0

    result = DiodeResult(
        ideality_factor=n_fit,
        saturation_current=I0_fit,
        series_resistance=Rs_fit,
        r_squared=r2,
    )

    print(result.table())
    return result


# ---------------------------------------------------------------------------
# Four-point probe
# ---------------------------------------------------------------------------

def four_point_probe(
    voltage: Any,
    current: Any,
    *,
    spacing: float,
    thickness: Optional[float] = None,
    correction_factor: Optional[float] = None,
) -> FourPointResult:
    """Calculate sheet resistance and resistivity from four-point probe data.

    Parameters
    ----------
    voltage : array-like
        Measured voltage between inner probes (V).
    current : array-like
        Applied current through outer probes (A).
    spacing : float
        Probe spacing in m.
    thickness : float, optional
        Sample thickness in m. If given, resistivity is calculated.
    correction_factor : float, optional
        Geometric correction factor. Default is pi/ln(2) = 4.532
        for a semi-infinite sheet.

    Returns
    -------
    FourPointResult
    """
    v = validate_array(voltage, "voltage")
    i = validate_array(current, "current")
    if len(v) != len(i):
        raise ValueError(
            f"voltage ({len(v)}) and current ({len(i)}) have different lengths."
        )

    if correction_factor is None:
        correction_factor = np.pi / np.log(2)  # 4.5324...

    # V/I ratio (average over measurements)
    v_over_i = np.mean(v / i)

    # Sheet resistance: Rs = CF * (V / I)
    sheet_resistance = correction_factor * v_over_i

    # Resistivity = Rs * thickness
    resistivity = None
    if thickness is not None:
        resistivity = sheet_resistance * thickness

    result = FourPointResult(
        sheet_resistance=sheet_resistance,
        resistivity=resistivity,
        correction_factor=correction_factor,
    )

    print(result.table())
    return result
