"""Thermal conductivity analysis.

Laser flash (thermal diffusivity -> conductivity),
DSC-based specific heat, steady-state methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

import numpy as np

from scripts.core.utils import validate_xy, validate_array
from scripts.analysis.fitting import fit_curve


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ThermalConductivityResult:
    """Thermal conductivity measurement result."""
    conductivity: float        # W/(m*K)
    diffusivity: Optional[float] = None   # m2/s
    specific_heat: Optional[float] = None  # J/(kg*K)
    density: Optional[float] = None       # kg/m3
    temperature: Optional[float] = None   # C or K
    method: str = "laser_flash"

    def table(self) -> str:
        lines = [f"[Praxis] Thermal Conductivity ({self.method})"]
        lines.append(f"  k = {self.conductivity:.4f} W/(m*K)")
        if self.diffusivity is not None:
            lines.append(f"  alpha = {self.diffusivity:.4e} m2/s")
        if self.specific_heat is not None:
            lines.append(f"  Cp = {self.specific_heat:.1f} J/(kg*K)")
        if self.density is not None:
            lines.append(f"  rho = {self.density:.1f} kg/m3")
        if self.temperature is not None:
            lines.append(f"  T = {self.temperature:.1f}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Thermal conductivity from components
# ---------------------------------------------------------------------------

def calc_conductivity(
    diffusivity: float,
    specific_heat: float,
    density: float,
    *,
    temperature: Optional[float] = None,
) -> ThermalConductivityResult:
    """Calculate thermal conductivity: k = alpha * Cp * rho.

    Parameters
    ----------
    diffusivity : float
        Thermal diffusivity in m2/s.
    specific_heat : float
        Specific heat capacity in J/(kg*K).
    density : float
        Density in kg/m3.
    temperature : float, optional
        Measurement temperature.

    Returns
    -------
    ThermalConductivityResult
    """
    k = diffusivity * specific_heat * density

    result = ThermalConductivityResult(
        conductivity=k,
        diffusivity=diffusivity,
        specific_heat=specific_heat,
        density=density,
        temperature=temperature,
    )
    print(result.table())
    return result


# ---------------------------------------------------------------------------
# Laser flash analysis
# ---------------------------------------------------------------------------

def laser_flash_diffusivity(
    time: Any,
    temperature_rise: Any,
    thickness: float,
    *,
    method: str = "parker",
) -> float:
    """Calculate thermal diffusivity from laser flash data.

    Parameters
    ----------
    time : array-like
        Time in seconds.
    temperature_rise : array-like
        Normalised temperature rise (0 to 1) on the rear face.
    thickness : float
        Sample thickness in metres.
    method : str
        'parker' (half-rise time method) or 'cowan' (corrected).

    Returns
    -------
    float
        Thermal diffusivity in m2/s.
    """
    t, dT = validate_xy(
        np.asarray(time, dtype=float),
        np.asarray(temperature_rise, dtype=float),
        allow_nan=False,
    )

    # Normalise temperature rise
    dT_norm = (dT - dT.min()) / (dT.max() - dT.min())

    if method == "parker":
        # Parker method: alpha = 0.1388 * L^2 / t_half
        # t_half = time when temperature reaches 50% of max
        half_idx = np.argmin(np.abs(dT_norm - 0.5))
        t_half = t[half_idx]

        if t_half <= 0:
            raise ValueError("Invalid half-rise time.")

        alpha = 0.1388 * thickness ** 2 / t_half

    elif method == "cowan":
        # Cowan correction for heat loss
        # Uses t_0.25, t_0.5, t_0.75
        t_25 = t[np.argmin(np.abs(dT_norm - 0.25))]
        t_50 = t[np.argmin(np.abs(dT_norm - 0.50))]
        t_75 = t[np.argmin(np.abs(dT_norm - 0.75))]

        # Correction factor based on ratio
        ratio = t_75 / t_25 if t_25 > 0 else 2.0

        # Cowan correction (approximate)
        if ratio < 2.0:
            K_c = 1.0  # No correction needed
        else:
            K_c = 0.9 + 0.1 * (2.0 / ratio)  # Simplified

        alpha = 0.1388 * thickness ** 2 / t_50 * K_c

    else:
        raise ValueError(f"Unknown method: {method}. Use 'parker' or 'cowan'.")

    print(f"[Praxis] Laser flash: alpha = {alpha:.4e} m2/s ({method} method)")
    return alpha


# ---------------------------------------------------------------------------
# Steady-state method
# ---------------------------------------------------------------------------

def steady_state_conductivity(
    heat_flux: float,
    thickness: float,
    delta_T: float,
    *,
    area: float = 1.0,
) -> float:
    """Calculate thermal conductivity from steady-state measurement.

    Fourier's law: k = Q * L / (A * dT)

    Parameters
    ----------
    heat_flux : float
        Heat flow rate Q in Watts.
    thickness : float
        Sample thickness L in metres.
    delta_T : float
        Temperature difference across sample in K.
    area : float
        Cross-sectional area in m2.

    Returns
    -------
    float
        Thermal conductivity in W/(m*K).
    """
    if delta_T <= 0:
        raise ValueError("Temperature difference must be positive.")
    if area <= 0:
        raise ValueError("Area must be positive.")

    k = (heat_flux * thickness) / (area * delta_T)
    print(f"[Praxis] Steady-state: k = {k:.4f} W/(m*K)")
    return k


# ---------------------------------------------------------------------------
# Temperature-dependent conductivity
# ---------------------------------------------------------------------------

def conductivity_vs_temperature(
    temperatures: Sequence[float],
    conductivities: Sequence[float],
) -> dict[str, Any]:
    """Analyse temperature-dependent thermal conductivity.

    Fits common models and returns fit parameters.

    Parameters
    ----------
    temperatures : list of float
        Temperatures (C or K).
    conductivities : list of float
        Thermal conductivity values W/(m*K).

    Returns
    -------
    dict with 'temperatures', 'conductivities', 'fit_type', 'fit_params', 'r_squared'.
    """
    T = np.array(temperatures, dtype=float)
    k = np.array(conductivities, dtype=float)

    # Try polynomial fit (order 2)
    coeffs = np.polyfit(T, k, 2)
    k_fit = np.polyval(coeffs, T)
    ss_res = np.sum((k - k_fit) ** 2)
    ss_tot = np.sum((k - np.mean(k)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    print(f"[Praxis] k(T) polynomial fit: R2 = {r2:.4f}")
    print(f"  k = {coeffs[0]:.4e}*T2 + {coeffs[1]:.4e}*T + {coeffs[2]:.4f}")

    return {
        "temperatures": T,
        "conductivities": k,
        "fit_type": "polynomial_2",
        "fit_params": {"a": coeffs[0], "b": coeffs[1], "c": coeffs[2]},
        "r_squared": r2,
    }
