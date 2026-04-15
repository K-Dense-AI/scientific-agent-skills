"""Mechanical testing analysis.

Stress-strain: Young's modulus, yield strength (0.2% offset), UTS,
elongation at break, toughness, Poisson's ratio.
DMA: storage/loss modulus, tan delta, Tg from tan delta peak.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
from scipy.integrate import trapezoid

from scripts.core.utils import validate_xy
from scripts.analysis.smoothing import smooth


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TensileResults:
    """Results from tensile / stress-strain analysis."""
    youngs_modulus: Optional[float] = None     # MPa or GPa
    yield_strength: Optional[float] = None     # MPa (0.2% offset)
    uts: Optional[float] = None                # MPa (ultimate tensile strength)
    elongation_at_break: Optional[float] = None  # %
    toughness: Optional[float] = None          # MJ/m3 (area under curve)
    elastic_limit_strain: Optional[float] = None  # % (end of linear region)
    proportional_limit: Optional[float] = None  # MPa
    modulus_unit: str = "MPa"

    def table(self) -> str:
        lines = ["[Praxis] Tensile Analysis"]
        if self.youngs_modulus is not None:
            lines.append(f"  Young's modulus     = {self.youngs_modulus:.2f} {self.modulus_unit}")
        if self.yield_strength is not None:
            lines.append(f"  Yield strength      = {self.yield_strength:.2f} MPa (0.2% offset)")
        if self.uts is not None:
            lines.append(f"  UTS                 = {self.uts:.2f} MPa")
        if self.elongation_at_break is not None:
            lines.append(f"  Elongation at break = {self.elongation_at_break:.2f}%")
        if self.toughness is not None:
            lines.append(f"  Toughness           = {self.toughness:.4f} MJ/m3")
        if self.elastic_limit_strain is not None:
            lines.append(f"  Elastic limit       = {self.elastic_limit_strain:.3f}%")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class DMAResults:
    """Results from DMA (dynamic mechanical analysis)."""
    tg_tan_delta: Optional[float] = None       # C (from tan delta peak)
    tg_loss_modulus: Optional[float] = None    # C (from loss modulus peak)
    storage_modulus_onset: Optional[float] = None  # MPa (glassy plateau)
    tan_delta_peak: Optional[float] = None     # Peak tan delta value

    def table(self) -> str:
        lines = ["[Praxis] DMA Analysis"]
        if self.tg_tan_delta is not None:
            lines.append(f"  Tg (tan delta peak) = {self.tg_tan_delta:.1f} C")
        if self.tg_loss_modulus is not None:
            lines.append(f"  Tg (loss modulus)   = {self.tg_loss_modulus:.1f} C")
        if self.storage_modulus_onset is not None:
            lines.append(f"  Storage modulus     = {self.storage_modulus_onset:.1f} MPa (glassy)")
        if self.tan_delta_peak is not None:
            lines.append(f"  Tan delta peak      = {self.tan_delta_peak:.4f}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Stress-Strain Analysis
# ---------------------------------------------------------------------------

def analyse_tensile(
    strain: Any,
    stress: Any,
    *,
    strain_unit: str = "percent",
    stress_unit: str = "MPa",
    linear_range: Optional[tuple[float, float]] = None,
    offset_yield: float = 0.2,
    smoothing_window: int = 0,
) -> TensileResults:
    """Analyse stress-strain data from tensile testing.

    Parameters
    ----------
    strain : array-like
        Strain values (in % or fraction, set by *strain_unit*).
    stress : array-like
        Stress values (MPa).
    strain_unit : str
        'percent' or 'fraction'. If 'fraction', multiplies by 100.
    stress_unit : str
        For reporting only.
    linear_range : (strain_min, strain_max), optional
        Manual range for modulus calculation. Auto-detected if None.
    offset_yield : float
        Offset for yield strength (0.2% by default).
    smoothing_window : int
        Smooth stress data before analysis.

    Returns
    -------
    TensileResults
    """
    strain_arr, stress_arr = validate_xy(
        np.asarray(strain, dtype=float),
        np.asarray(stress, dtype=float),
        allow_nan=False,
    )

    # Convert strain to percent if needed
    if strain_unit == "fraction":
        strain_arr = strain_arr * 100

    if smoothing_window > 0:
        stress_arr = smooth(stress_arr, method="savgol", window=smoothing_window)

    results = TensileResults(modulus_unit=stress_unit)

    # Young's modulus: slope of the linear region
    if linear_range is not None:
        mask = (strain_arr >= linear_range[0]) & (strain_arr <= linear_range[1])
    else:
        mask = _detect_linear_region(strain_arr, stress_arr)

    if mask.sum() >= 2:
        coeffs = np.polyfit(strain_arr[mask] / 100, stress_arr[mask], 1)  # strain as fraction
        results.youngs_modulus = coeffs[0]
        results.elastic_limit_strain = strain_arr[mask][-1]
        results.proportional_limit = stress_arr[mask][-1]

    # UTS: maximum stress
    uts_idx = np.argmax(stress_arr)
    results.uts = stress_arr[uts_idx]

    # Elongation at break: last point
    results.elongation_at_break = strain_arr[-1]

    # Yield strength (0.2% offset method)
    if results.youngs_modulus is not None:
        yield_stress = _offset_yield(
            strain_arr, stress_arr, results.youngs_modulus, offset_yield
        )
        results.yield_strength = yield_stress

    # Toughness: area under stress-strain curve
    results.toughness = trapezoid(stress_arr, strain_arr / 100) / 1e6  # MPa * fraction -> MJ/m3

    print(results.table())
    return results


def _detect_linear_region(
    strain: np.ndarray,
    stress: np.ndarray,
    r2_threshold: float = 0.999,
) -> np.ndarray:
    """Auto-detect the linear elastic region."""
    n = len(strain)
    best_end = min(10, n)

    for end in range(10, n):
        if end < 3:
            continue
        s = strain[:end] / 100  # fraction
        coeffs = np.polyfit(s, stress[:end], 1)
        y_fit = np.polyval(coeffs, s)
        ss_res = np.sum((stress[:end] - y_fit) ** 2)
        ss_tot = np.sum((stress[:end] - np.mean(stress[:end])) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        if r2 >= r2_threshold:
            best_end = end
        else:
            break

    mask = np.zeros(n, dtype=bool)
    mask[:best_end] = True
    return mask


def _offset_yield(
    strain: np.ndarray,
    stress: np.ndarray,
    modulus: float,
    offset: float = 0.2,
) -> Optional[float]:
    """Calculate yield strength by offset method.

    Draws a line parallel to the elastic region, offset by *offset* %,
    and finds where it intersects the stress-strain curve.
    """
    # Offset line: stress = modulus * (strain/100 - offset/100)
    offset_stress = modulus * (strain / 100 - offset / 100)

    # Find intersection
    diff = stress - offset_stress
    crossings = np.where(np.diff(np.sign(diff)))[0]

    if len(crossings) == 0:
        return None

    # Take the first crossing after the elastic region
    idx = crossings[0]
    # Linear interpolation for exact crossing
    if idx + 1 < len(strain):
        frac = abs(diff[idx]) / (abs(diff[idx]) + abs(diff[idx + 1]))
        yield_stress = stress[idx] + frac * (stress[idx + 1] - stress[idx])
        return float(yield_stress)

    return float(stress[idx])


# ---------------------------------------------------------------------------
# Force-Displacement to Stress-Strain conversion
# ---------------------------------------------------------------------------

def force_to_stress(
    force: Any,
    area: float,
) -> np.ndarray:
    """Convert force (N) to stress (MPa).

    Parameters
    ----------
    force : array-like
        Force in Newtons.
    area : float
        Cross-sectional area in mm2.
    """
    f = np.asarray(force, dtype=float)
    return f / area  # N/mm2 = MPa


def displacement_to_strain(
    displacement: Any,
    gauge_length: float,
    *,
    unit: str = "percent",
) -> np.ndarray:
    """Convert displacement (mm) to strain.

    Parameters
    ----------
    displacement : array-like
        Displacement in mm.
    gauge_length : float
        Original gauge length in mm.
    unit : str
        'percent' or 'fraction'.
    """
    d = np.asarray(displacement, dtype=float)
    strain = d / gauge_length
    if unit == "percent":
        strain = strain * 100
    return strain


# ---------------------------------------------------------------------------
# DMA Analysis
# ---------------------------------------------------------------------------

def analyse_dma(
    temperature: Any,
    storage_modulus: Any,
    loss_modulus: Any,
    *,
    tan_delta: Optional[Any] = None,
    smoothing_window: int = 0,
) -> DMAResults:
    """Analyse DMA (dynamic mechanical analysis) data.

    Parameters
    ----------
    temperature : array-like
        Temperature in C.
    storage_modulus : array-like
        Storage modulus E' (MPa or Pa).
    loss_modulus : array-like
        Loss modulus E'' (MPa or Pa).
    tan_delta : array-like, optional
        Tan delta. Calculated from E''/E' if not provided.
    smoothing_window : int
        Savitzky-Golay window for smoothing.

    Returns
    -------
    DMAResults
    """
    temp = np.asarray(temperature, dtype=float)
    e_storage = np.asarray(storage_modulus, dtype=float)
    e_loss = np.asarray(loss_modulus, dtype=float)

    order = np.argsort(temp)
    temp = temp[order]
    e_storage = e_storage[order]
    e_loss = e_loss[order]

    if tan_delta is not None:
        td = np.asarray(tan_delta, dtype=float)[order]
    else:
        td = e_loss / e_storage

    if smoothing_window > 0:
        td = smooth(td, method="savgol", window=smoothing_window)
        e_loss = smooth(e_loss, method="savgol", window=smoothing_window)

    results = DMAResults()

    # Tg from tan delta peak
    td_peaks, _ = find_peaks(td, distance=max(3, len(temp) // 20))
    if len(td_peaks) > 0:
        main_peak = td_peaks[np.argmax(td[td_peaks])]
        results.tg_tan_delta = temp[main_peak]
        results.tan_delta_peak = td[main_peak]

    # Tg from loss modulus peak
    loss_peaks, _ = find_peaks(e_loss, distance=max(3, len(temp) // 20))
    if len(loss_peaks) > 0:
        main_loss = loss_peaks[np.argmax(e_loss[loss_peaks])]
        results.tg_loss_modulus = temp[main_loss]

    # Glassy plateau storage modulus (value at lowest temperature)
    results.storage_modulus_onset = e_storage[0]

    print(results.table())
    return results
