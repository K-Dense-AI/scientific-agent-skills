"""Dielectric property analysis.

Permittivity vs frequency, loss tangent, Cole-Cole plots,
Curie-Weiss fitting, temperature-dependent permittivity, AC conductivity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np

from scripts.core.utils import validate_xy, validate_array
from scripts.analysis.fitting import fit_curve


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DielectricData:
    """Parsed dielectric measurement data."""
    frequency: np.ndarray       # Hz
    epsilon_r: np.ndarray       # Real permittivity (relative)
    epsilon_i: Optional[np.ndarray] = None   # Imaginary permittivity
    tan_delta: Optional[np.ndarray] = None   # Loss tangent
    ac_conductivity: Optional[np.ndarray] = None  # S/m

    @property
    def omega(self) -> np.ndarray:
        return 2 * np.pi * self.frequency


@dataclass
class DielectricResults:
    """Results from dielectric analysis."""
    epsilon_max: Optional[float] = None       # Peak permittivity
    freq_at_max: Optional[float] = None       # Frequency at peak
    tan_delta_max: Optional[float] = None     # Peak loss tangent
    curie_temp: Optional[float] = None        # Curie temperature (C)
    curie_constant: Optional[float] = None    # Curie-Weiss constant

    def table(self) -> str:
        lines = ["[Praxis] Dielectric Analysis"]
        if self.epsilon_max is not None:
            lines.append(f"  Peak permittivity   = {self.epsilon_max:.1f}")
        if self.freq_at_max is not None:
            lines.append(f"  Frequency at peak   = {self.freq_at_max:.2e} Hz")
        if self.tan_delta_max is not None:
            lines.append(f"  Peak tan delta      = {self.tan_delta_max:.4f}")
        if self.curie_temp is not None:
            lines.append(f"  Curie temperature   = {self.curie_temp:.1f} C")
        if self.curie_constant is not None:
            lines.append(f"  Curie constant      = {self.curie_constant:.2e}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Data parsing
# ---------------------------------------------------------------------------

def parse_dielectric(
    frequency: Any,
    epsilon_r: Any,
    *,
    epsilon_i: Optional[Any] = None,
    tan_delta: Optional[Any] = None,
    capacitance: Optional[Any] = None,
    area: Optional[float] = None,
    thickness: Optional[float] = None,
    epsilon_0: float = 8.854e-12,
) -> DielectricData:
    """Parse dielectric measurement data.

    Can accept direct permittivity values or calculate from capacitance.

    Parameters
    ----------
    frequency : array-like
        Frequency in Hz.
    epsilon_r : array-like
        Real relative permittivity. If None, calculated from capacitance.
    epsilon_i : array-like, optional
        Imaginary permittivity.
    tan_delta : array-like, optional
        Loss tangent. Calculated from epsilon_i/epsilon_r if not given.
    capacitance : array-like, optional
        Capacitance in F (for calculating permittivity from geometry).
    area : float, optional
        Electrode area in m2 (for capacitance conversion).
    thickness : float, optional
        Sample thickness in m (for capacitance conversion).
    epsilon_0 : float
        Vacuum permittivity (F/m).

    Returns
    -------
    DielectricData
    """
    freq = validate_array(frequency, "frequency")
    er = np.asarray(epsilon_r, dtype=float)

    # Calculate from capacitance if needed
    if capacitance is not None and area is not None and thickness is not None:
        cap = np.asarray(capacitance, dtype=float)
        er = cap * thickness / (epsilon_0 * area)

    data = DielectricData(frequency=freq, epsilon_r=er)

    if epsilon_i is not None:
        data.epsilon_i = np.asarray(epsilon_i, dtype=float)

    if tan_delta is not None:
        data.tan_delta = np.asarray(tan_delta, dtype=float)
    elif data.epsilon_i is not None:
        data.tan_delta = data.epsilon_i / data.epsilon_r

    # AC conductivity: sigma = omega * epsilon_0 * epsilon_i
    if data.epsilon_i is not None:
        data.ac_conductivity = data.omega * epsilon_0 * data.epsilon_i

    return data


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyse_dielectric(
    data: DielectricData,
) -> DielectricResults:
    """Analyse frequency-dependent dielectric data.

    Parameters
    ----------
    data : DielectricData

    Returns
    -------
    DielectricResults
    """
    results = DielectricResults()

    # Peak permittivity
    idx_max = np.argmax(data.epsilon_r)
    results.epsilon_max = data.epsilon_r[idx_max]
    results.freq_at_max = data.frequency[idx_max]

    # Peak loss tangent
    if data.tan_delta is not None:
        idx_td = np.argmax(data.tan_delta)
        results.tan_delta_max = data.tan_delta[idx_td]

    print(results.table())
    return results


# ---------------------------------------------------------------------------
# Curie-Weiss fitting
# ---------------------------------------------------------------------------

def curie_weiss_fit(
    temperature: Any,
    permittivity: Any,
    *,
    temp_range: Optional[tuple[float, float]] = None,
) -> dict[str, float]:
    """Fit the Curie-Weiss law: 1/epsilon = (T - Tc) / C.

    Parameters
    ----------
    temperature : array-like
        Temperature in C or K.
    permittivity : array-like
        Relative permittivity.
    temp_range : (T_min, T_max), optional
        Fit only above Tc (paraelectric region).

    Returns
    -------
    dict with 'Tc' (Curie temperature), 'C' (Curie constant), 'r_squared'.
    """
    temp, eps = validate_xy(
        np.asarray(temperature, dtype=float),
        np.asarray(permittivity, dtype=float),
        allow_nan=False,
    )

    # 1/epsilon vs T
    inv_eps = 1.0 / eps

    if temp_range is not None:
        mask = (temp >= temp_range[0]) & (temp <= temp_range[1])
        temp_fit, inv_fit = temp[mask], inv_eps[mask]
    else:
        # Auto: use data above the Curie peak
        tc_idx = np.argmax(eps)
        temp_fit = temp[tc_idx:]
        inv_fit = inv_eps[tc_idx:]

    if len(temp_fit) < 3:
        raise ValueError("Not enough data points for Curie-Weiss fit.")

    # Linear fit: 1/eps = (1/C) * T - Tc/C
    coeffs = np.polyfit(temp_fit, inv_fit, 1)
    slope, intercept = coeffs

    # C = 1/slope, Tc = -intercept/slope
    C = 1.0 / slope if slope != 0 else 0
    Tc = -intercept / slope if slope != 0 else 0

    y_fit = np.polyval(coeffs, temp_fit)
    ss_res = np.sum((inv_fit - y_fit) ** 2)
    ss_tot = np.sum((inv_fit - np.mean(inv_fit)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    print(f"[Praxis] Curie-Weiss: Tc = {Tc:.1f}, C = {C:.2e}, R2 = {r2:.4f}")

    return {"Tc": Tc, "C": C, "r_squared": r2, "slope": slope, "intercept": intercept}


# ---------------------------------------------------------------------------
# Cole-Cole plot
# ---------------------------------------------------------------------------

def cole_cole_data(
    epsilon_r: Any,
    epsilon_i: Any,
) -> tuple[np.ndarray, np.ndarray]:
    """Prepare data for a Cole-Cole plot (epsilon'' vs epsilon').

    Parameters
    ----------
    epsilon_r : array-like
        Real permittivity.
    epsilon_i : array-like
        Imaginary permittivity.

    Returns
    -------
    (epsilon_real, epsilon_imag) ready for plotting.
    """
    er = np.asarray(epsilon_r, dtype=float)
    ei = np.asarray(epsilon_i, dtype=float)
    print(f"[Praxis] Cole-Cole data: {len(er)} points")
    return er, ei
