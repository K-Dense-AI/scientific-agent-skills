"""XPS (X-ray Photoelectron Spectroscopy) analysis.

Survey scan, high-resolution peak fitting (Gaussian-Lorentzian),
Shirley/Tougaard background, chemical state identification,
atomic %, binding energy calibration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np

from scripts.core.utils import validate_xy
from scripts.analysis.baseline import correct_baseline
from scripts.analysis.peaks import find_peaks_auto, deconvolve_peaks


# ---------------------------------------------------------------------------
# Sensitivity factors (Scofield cross-sections, relative to C 1s = 1.0)
# Common elements — approximate values for Al Ka or Mg Ka
# ---------------------------------------------------------------------------

SENSITIVITY_FACTORS = {
    "C 1s": 1.00,
    "O 1s": 2.93,
    "N 1s": 1.80,
    "Si 2p": 0.87,
    "Al 2p": 0.54,
    "Fe 2p": 16.42,
    "Ti 2p": 7.81,
    "Ca 2p": 5.07,
    "Na 1s": 8.52,
    "K 2p": 5.29,
    "S 2p": 1.68,
    "P 2p": 1.19,
    "Cl 2p": 2.29,
    "F 1s": 4.43,
    "Zn 2p": 18.92,
    "Cu 2p": 16.73,
    "Ag 3d": 18.04,
    "Au 4f": 17.12,
    "Pt 4f": 16.63,
    "Ba 3d": 20.78,
    "Mg 1s": 9.80,
    "Li 1s": 0.06,
    "B 1s": 0.49,
}

# C 1s reference binding energy for calibration
C1S_REFERENCE = 284.8  # eV (adventitious carbon)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class XPSPeak:
    """A fitted XPS peak."""
    binding_energy: float  # eV
    intensity: float       # counts or CPS
    fwhm: Optional[float] = None
    area: Optional[float] = None
    element: Optional[str] = None
    orbital: Optional[str] = None
    chemical_state: Optional[str] = None
    atomic_pct: Optional[float] = None


@dataclass
class XPSResults:
    """Full XPS analysis results."""
    peaks: list[XPSPeak] = field(default_factory=list)
    be_shift: float = 0.0  # Binding energy calibration shift
    composition: dict[str, float] = field(default_factory=dict)

    def table(self) -> str:
        lines = ["[Praxis] XPS Analysis"]
        if self.be_shift != 0:
            lines.append(f"  BE calibration shift: {self.be_shift:+.2f} eV")

        if self.composition:
            lines.append("\n  Elemental Composition:")
            for elem, pct in sorted(self.composition.items(), key=lambda x: -x[1]):
                lines.append(f"    {elem:>8}: {pct:>6.1f} at%")

        if self.peaks:
            lines.append(f"\n  {'#':>3}  {'BE (eV)':>8}  {'Element':>8}  {'FWHM':>6}  {'Area':>12}  {'at%':>6}  {'State'}")
            lines.append("  " + "-" * 65)
            for i, p in enumerate(self.peaks, 1):
                elem = p.element or "--"
                fwhm = f"{p.fwhm:.2f}" if p.fwhm else "--"
                area = f"{p.area:.1f}" if p.area else "--"
                at_pct = f"{p.atomic_pct:.1f}" if p.atomic_pct else "--"
                state = p.chemical_state or "--"
                lines.append(
                    f"  {i:>3}  {p.binding_energy:>8.2f}  {elem:>8}  {fwhm:>6}  {area:>12}  {at_pct:>6}  {state}"
                )

        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Survey scan analysis
# ---------------------------------------------------------------------------

def analyse_survey(
    binding_energy: Any,
    intensity: Any,
    *,
    elements: Optional[Sequence[str]] = None,
    min_peak_height_pct: float = 3.0,
) -> XPSResults:
    """Analyse an XPS survey scan.

    Parameters
    ----------
    binding_energy : array-like
        Binding energy in eV.
    intensity : array-like
        Counts or CPS.
    elements : list of str, optional
        Elements to quantify, e.g. ['C 1s', 'O 1s', 'N 1s'].
        If None, auto-detects peaks.
    min_peak_height_pct : float
        Minimum peak height for detection.

    Returns
    -------
    XPSResults
    """
    be, intens = validate_xy(
        np.asarray(binding_energy, dtype=float),
        np.asarray(intensity, dtype=float),
        allow_nan=False,
    )

    # Sort by binding energy (descending)
    order = np.argsort(be)[::-1]
    be, intens = be[order], intens[order]

    peak_results = find_peaks_auto(be, intens, min_height_pct=min_peak_height_pct)

    peaks = []
    for p in peak_results.peaks:
        xps_peak = XPSPeak(
            binding_energy=p.position,
            intensity=p.height,
            fwhm=p.fwhm,
            area=p.area,
        )
        # Try to identify element
        elem, orbital = _identify_element(p.position)
        xps_peak.element = elem
        xps_peak.orbital = orbital
        peaks.append(xps_peak)

    results = XPSResults(peaks=peaks)

    # Calculate atomic percentages
    _calc_atomic_pct(results)

    print(results.table())
    return results


# ---------------------------------------------------------------------------
# High-resolution peak fitting
# ---------------------------------------------------------------------------

def fit_highres(
    binding_energy: Any,
    intensity: Any,
    *,
    n_peaks: Optional[int] = None,
    peak_positions: Optional[Sequence[float]] = None,
    background: str = "shirley",
    peak_model: str = "pseudo_voigt",
    element: Optional[str] = None,
) -> XPSResults:
    """Fit a high-resolution XPS region.

    Parameters
    ----------
    binding_energy : array-like
        Binding energy in eV.
    intensity : array-like
        Counts or CPS.
    n_peaks : int, optional
        Number of peaks to fit. Auto-detected if None.
    peak_positions : list of float, optional
        Approximate peak centres in eV.
    background : str
        Background type: 'shirley', 'linear', 'polynomial'.
    peak_model : str
        Peak shape: 'gaussian', 'lorentzian', 'voigt', 'pseudo_voigt'.
    element : str, optional
        Element label for the region (e.g. 'C 1s').

    Returns
    -------
    XPSResults
    """
    be, intens = validate_xy(
        np.asarray(binding_energy, dtype=float),
        np.asarray(intensity, dtype=float),
        allow_nan=False,
    )

    # Background subtraction
    if background == "shirley":
        intens_corr, bg, _ = correct_baseline(be, intens, method="shirley")
    elif background in ("linear", "polynomial"):
        intens_corr, bg, _ = correct_baseline(be, intens, method=background)
    else:
        intens_corr = intens
        bg = np.zeros_like(intens)

    # Deconvolve peaks
    result = deconvolve_peaks(
        be, intens_corr,
        n_peaks=n_peaks,
        peak_positions=peak_positions,
        model=peak_model,
        background="constant",
    )

    # Extract peak parameters
    peaks = []
    for name, par in result.params.items():
        if name.endswith("center"):
            prefix = name.replace("center", "")
            peak = XPSPeak(
                binding_energy=par.value,
                intensity=result.params.get(f"{prefix}amplitude", par).value,
                element=element,
            )
            if f"{prefix}sigma" in result.params:
                sigma = result.params[f"{prefix}sigma"].value
                peak.fwhm = 2.355 * sigma  # Approximate FWHM for Gaussian

            # Calculate area from component
            peaks.append(peak)

    results = XPSResults(peaks=peaks)
    print(results.table())
    return results


# ---------------------------------------------------------------------------
# Binding energy calibration
# ---------------------------------------------------------------------------

def calibrate_be(
    binding_energy: Any,
    *,
    c1s_measured: Optional[float] = None,
    reference_peak: Optional[float] = None,
    reference_value: float = C1S_REFERENCE,
) -> tuple[np.ndarray, float]:
    """Calibrate binding energy scale.

    Parameters
    ----------
    binding_energy : array-like
        Original BE values.
    c1s_measured : float, optional
        Measured C 1s position. Shift is calculated to move it to 284.8 eV.
    reference_peak : float, optional
        Any measured reference peak position.
    reference_value : float
        Target value for the reference peak.

    Returns
    -------
    (calibrated_be, shift)
    """
    be = np.asarray(binding_energy, dtype=float)

    if c1s_measured is not None:
        shift = reference_value - c1s_measured
    elif reference_peak is not None:
        shift = reference_value - reference_peak
    else:
        raise ValueError("Provide c1s_measured or reference_peak.")

    calibrated = be + shift
    print(f"[Praxis] BE calibration: shift = {shift:+.2f} eV")
    return calibrated, shift


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Common XPS peak positions (approximate, eV)
_PEAK_DB = [
    (284.8, "C", "1s"), (532.0, "O", "1s"), (399.0, "N", "1s"),
    (102.0, "Si", "2p"), (74.0, "Al", "2p"), (711.0, "Fe", "2p"),
    (459.0, "Ti", "2p"), (347.0, "Ca", "2p"), (1071.0, "Na", "1s"),
    (293.0, "K", "2p"), (164.0, "S", "2p"), (133.0, "P", "2p"),
    (199.0, "Cl", "2p"), (685.0, "F", "1s"), (1022.0, "Zn", "2p"),
    (933.0, "Cu", "2p"), (368.0, "Ag", "3d"), (84.0, "Au", "4f"),
    (71.0, "Pt", "4f"), (780.0, "Ba", "3d"),
    (1303.0, "Mg", "1s"), (55.0, "Li", "1s"), (188.0, "B", "1s"),
]


def _identify_element(be: float, tolerance: float = 5.0) -> tuple[Optional[str], Optional[str]]:
    """Identify element from binding energy."""
    best_match = None
    best_dist = tolerance

    for ref_be, element, orbital in _PEAK_DB:
        dist = abs(be - ref_be)
        if dist < best_dist:
            best_dist = dist
            best_match = (element, orbital)

    if best_match:
        return f"{best_match[0]} {best_match[1]}", best_match[1]
    return None, None


def _calc_atomic_pct(results: XPSResults) -> None:
    """Calculate atomic percentages from peak areas and sensitivity factors."""
    # Normalise areas by sensitivity factors
    normalised = []
    for p in results.peaks:
        if p.area and p.element and p.element in SENSITIVITY_FACTORS:
            sf = SENSITIVITY_FACTORS[p.element]
            normalised.append((p, p.area / sf))

    total = sum(n for _, n in normalised)
    if total > 0:
        for p, n in normalised:
            p.atomic_pct = (n / total) * 100
            elem = p.element.split()[0] if p.element else "?"
            results.composition[elem] = results.composition.get(elem, 0) + p.atomic_pct
