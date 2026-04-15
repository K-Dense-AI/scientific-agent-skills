"""DSC and TGA analysis.

DSC: glass transition (Tg), melting (Tm), crystallisation (Tc), enthalpy,
crystallinity percentage.
TGA: onset/endset temperatures, derivative thermogravimetry (DTG),
residue percentage, multi-step decomposition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np
from scipy.signal import find_peaks, argrelextrema
from scipy.integrate import trapezoid

from scripts.core.utils import validate_xy
from scripts.analysis.smoothing import smooth


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DSCTransition:
    """A thermal transition detected in DSC data."""
    kind: str            # 'Tg', 'Tm', 'Tc', 'endotherm', 'exotherm'
    temperature: float   # Peak or midpoint temperature (C)
    onset: Optional[float] = None    # Onset temperature (C)
    endset: Optional[float] = None   # Endset temperature (C)
    enthalpy: Optional[float] = None # J/g (integrated area)
    height: Optional[float] = None   # Peak height


@dataclass
class DSCResults:
    """Full DSC analysis results."""
    transitions: list[DSCTransition] = field(default_factory=list)
    tg: Optional[float] = None
    tm: Optional[float] = None
    tc: Optional[float] = None
    crystallinity: Optional[float] = None

    def table(self) -> str:
        lines = ["[Praxis] DSC Analysis"]
        if self.tg is not None:
            lines.append(f"  Tg = {self.tg:.1f} C")
        if self.tm is not None:
            lines.append(f"  Tm = {self.tm:.1f} C")
        if self.tc is not None:
            lines.append(f"  Tc = {self.tc:.1f} C")
        if self.crystallinity is not None:
            lines.append(f"  Crystallinity = {self.crystallinity:.1f}%")

        if self.transitions:
            lines.append(f"\n  {'#':>3}  {'Type':>10}  {'T (C)':>8}  {'Onset':>8}  {'Endset':>8}  {'dH (J/g)':>10}")
            lines.append("  " + "-" * 58)
            for i, t in enumerate(self.transitions, 1):
                onset = f"{t.onset:.1f}" if t.onset else "--"
                endset = f"{t.endset:.1f}" if t.endset else "--"
                dh = f"{t.enthalpy:.2f}" if t.enthalpy else "--"
                lines.append(f"  {i:>3}  {t.kind:>10}  {t.temperature:>8.1f}  {onset:>8}  {endset:>8}  {dh:>10}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class TGAStep:
    """A decomposition step in TGA data."""
    onset: float         # Onset temperature (C)
    endset: float        # Endset temperature (C)
    dtg_peak: float      # DTG peak temperature (C)
    mass_loss: float     # Mass loss (%)
    mass_loss_rate: float  # Maximum rate of mass loss (%/C)


@dataclass
class TGAResults:
    """Full TGA analysis results."""
    steps: list[TGAStep] = field(default_factory=list)
    residue: float = 0.0     # Final residue (%)
    total_loss: float = 0.0  # Total mass loss (%)

    def table(self) -> str:
        lines = [
            "[Praxis] TGA Analysis",
            f"  Total mass loss: {self.total_loss:.1f}%",
            f"  Final residue:   {self.residue:.1f}%",
        ]
        if self.steps:
            lines.append(f"\n  {'#':>3}  {'Onset (C)':>10}  {'Endset (C)':>10}  {'DTG peak':>10}  {'Loss (%)':>10}  {'Rate (%/C)':>10}")
            lines.append("  " + "-" * 62)
            for i, s in enumerate(self.steps, 1):
                lines.append(
                    f"  {i:>3}  {s.onset:>10.1f}  {s.endset:>10.1f}  {s.dtg_peak:>10.1f}  {s.mass_loss:>10.1f}  {s.mass_loss_rate:>10.4f}"
                )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# DSC Analysis
# ---------------------------------------------------------------------------

def analyse_dsc(
    temperature: Any,
    heat_flow: Any,
    *,
    endotherm_down: bool = True,
    tg_range: Optional[tuple[float, float]] = None,
    dh_reference: Optional[float] = None,
    smoothing_window: int = 0,
    min_peak_height_pct: float = 10.0,
) -> DSCResults:
    """Analyse DSC data.

    Parameters
    ----------
    temperature : array-like
        Temperature in C.
    heat_flow : array-like
        Heat flow in mW or W/g. Convention set by *endotherm_down*.
    endotherm_down : bool
        If True, endothermic events are negative (TA Instruments convention).
    tg_range : (T_min, T_max), optional
        Temperature range to search for Tg.
    dh_reference : float, optional
        Reference enthalpy of fusion (J/g) for crystallinity calculation.
    smoothing_window : int
        Savitzky-Golay window for pre-smoothing (0 = no smoothing).
    min_peak_height_pct : float
        Minimum peak height as % of range.

    Returns
    -------
    DSCResults
    """
    temp, hf = validate_xy(
        np.asarray(temperature, dtype=float),
        np.asarray(heat_flow, dtype=float),
        allow_nan=False,
    )

    # Sort by temperature
    order = np.argsort(temp)
    temp, hf = temp[order], hf[order]

    if smoothing_window > 0:
        hf = smooth(hf, method="savgol", window=smoothing_window)

    # For peak detection, we need endotherms as negative
    if not endotherm_down:
        hf_detect = -hf
    else:
        hf_detect = hf

    results = DSCResults()
    transitions = []

    # Detect Tg (glass transition) -- look for step change in heat flow
    tg = _detect_tg(temp, hf_detect, tg_range)
    if tg is not None:
        results.tg = tg
        transitions.append(DSCTransition(kind="Tg", temperature=tg))

    # Detect endothermic peaks (melting) -- negative in hf_detect
    hf_range = np.ptp(hf_detect)
    threshold = np.min(hf_detect) + min_peak_height_pct / 100 * hf_range

    # Endothermic: peaks in -hf_detect (i.e. valleys in hf_detect)
    endo_indices, _ = find_peaks(-hf_detect, height=-threshold, distance=max(5, len(temp) // 50))

    for idx in endo_indices:
        t = DSCTransition(kind="Tm", temperature=temp[idx], height=abs(hf_detect[idx]))
        # Estimate onset/endset and enthalpy
        onset, endset = _find_peak_bounds(temp, hf_detect, idx)
        t.onset = onset
        t.endset = endset
        if onset is not None and endset is not None:
            mask = (temp >= onset) & (temp <= endset)
            baseline = np.interp(temp[mask], [onset, endset],
                                 [hf_detect[mask][0], hf_detect[mask][-1]])
            t.enthalpy = abs(trapezoid(hf_detect[mask] - baseline, temp[mask]))
        transitions.append(t)

    # Detect exothermic peaks (crystallisation) -- peaks in hf_detect
    exo_indices, _ = find_peaks(hf_detect, height=np.max(hf_detect) * min_peak_height_pct / 100,
                                distance=max(5, len(temp) // 50))

    for idx in exo_indices:
        t = DSCTransition(kind="Tc", temperature=temp[idx], height=abs(hf_detect[idx]))
        onset, endset = _find_peak_bounds(temp, -hf_detect, idx)
        t.onset = onset
        t.endset = endset
        transitions.append(t)

    # Assign Tm and Tc from transitions
    melting = [t for t in transitions if t.kind == "Tm"]
    if melting:
        results.tm = max(melting, key=lambda t: (t.height or 0)).temperature

    cryst = [t for t in transitions if t.kind == "Tc"]
    if cryst:
        results.tc = max(cryst, key=lambda t: (t.height or 0)).temperature

    # Crystallinity
    if dh_reference is not None and melting:
        total_enthalpy = sum(t.enthalpy for t in melting if t.enthalpy)
        results.crystallinity = (total_enthalpy / dh_reference) * 100

    results.transitions = transitions
    print(results.table())
    return results


def _detect_tg(
    temp: np.ndarray,
    hf: np.ndarray,
    tg_range: Optional[tuple[float, float]] = None,
) -> Optional[float]:
    """Detect glass transition as the midpoint of a step change in heat flow."""
    if tg_range is not None:
        mask = (temp >= tg_range[0]) & (temp <= tg_range[1])
        t, h = temp[mask], hf[mask]
    else:
        t, h = temp, hf

    if len(t) < 10:
        return None

    # Derivative of heat flow
    dhdt = np.gradient(h, t)
    dhdt_smooth = smooth(dhdt, method="savgol", window=max(11, len(dhdt) // 20 | 1))

    # Tg: peak in derivative (inflection point)
    peaks, props = find_peaks(np.abs(dhdt_smooth), height=np.max(np.abs(dhdt_smooth)) * 0.3,
                              distance=max(3, len(t) // 20))

    if len(peaks) == 0:
        return None

    # Take the first significant peak as Tg
    idx = peaks[0]
    return float(t[idx])


def _find_peak_bounds(
    temp: np.ndarray,
    signal: np.ndarray,
    peak_idx: int,
) -> tuple[Optional[float], Optional[float]]:
    """Find onset and endset of a peak using derivative method."""
    search = max(5, len(temp) // 20)
    left = max(0, peak_idx - search)
    right = min(len(temp) - 1, peak_idx + search)

    # Onset: steepest descent on the left side
    left_deriv = np.gradient(signal[left:peak_idx], temp[left:peak_idx])
    if len(left_deriv) > 0:
        onset_idx = left + np.argmin(left_deriv)
        onset = temp[onset_idx]
    else:
        onset = None

    # Endset: steepest ascent on the right side
    right_deriv = np.gradient(signal[peak_idx:right], temp[peak_idx:right])
    if len(right_deriv) > 0:
        endset_idx = peak_idx + np.argmax(right_deriv)
        endset = temp[endset_idx]
    else:
        endset = None

    return onset, endset


# ---------------------------------------------------------------------------
# TGA Analysis
# ---------------------------------------------------------------------------

def analyse_tga(
    temperature: Any,
    mass: Any,
    *,
    mass_unit: str = "percent",
    smoothing_window: int = 11,
    min_loss_pct: float = 2.0,
) -> TGAResults:
    """Analyse TGA data.

    Parameters
    ----------
    temperature : array-like
        Temperature in C.
    mass : array-like
        Mass (in % or mg).
    mass_unit : str
        'percent' or 'mg'. If 'mg', converts to %.
    smoothing_window : int
        Window for DTG smoothing.
    min_loss_pct : float
        Minimum mass loss to count as a decomposition step.

    Returns
    -------
    TGAResults
    """
    temp, m = validate_xy(
        np.asarray(temperature, dtype=float),
        np.asarray(mass, dtype=float),
        allow_nan=False,
    )

    order = np.argsort(temp)
    temp, m = temp[order], m[order]

    # Convert to percent if needed
    if mass_unit == "mg":
        m = (m / m[0]) * 100

    # DTG (derivative)
    dtg = np.gradient(m, temp)
    if smoothing_window > 0:
        dtg = smooth(dtg, method="savgol", window=smoothing_window)

    # Find decomposition steps as valleys in DTG (mass loss = negative derivative)
    peaks, props = find_peaks(-dtg, height=0.01, distance=max(5, len(temp) // 30),
                              prominence=0.005)

    results = TGAResults()
    results.residue = m[-1]
    results.total_loss = m[0] - m[-1]

    for idx in peaks:
        # Find onset/endset for each step
        search = max(10, len(temp) // 15)
        left = max(0, idx - search)
        right = min(len(temp) - 1, idx + search)

        # Onset: where mass starts dropping significantly
        onset_idx = left
        for i in range(idx, left, -1):
            if abs(dtg[i]) < 0.1 * abs(dtg[idx]):
                onset_idx = i
                break

        # Endset: where mass stabilises
        endset_idx = right
        for i in range(idx, right):
            if abs(dtg[i]) < 0.1 * abs(dtg[idx]):
                endset_idx = i
                break

        mass_loss = m[onset_idx] - m[endset_idx]

        if mass_loss >= min_loss_pct:
            step = TGAStep(
                onset=temp[onset_idx],
                endset=temp[endset_idx],
                dtg_peak=temp[idx],
                mass_loss=mass_loss,
                mass_loss_rate=abs(dtg[idx]),
            )
            results.steps.append(step)

    print(results.table())
    return results
