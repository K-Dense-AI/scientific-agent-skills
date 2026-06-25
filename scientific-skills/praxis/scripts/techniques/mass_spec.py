"""Mass spectrometry analysis: peak detection, molecular ion identification,
isotope pattern calculation, and mass accuracy.

Supports MS, MALDI, and TOF-MS data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from scripts.core.utils import validate_xy
from scripts.analysis.peaks import find_peaks_auto


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default adduct masses (Da)
DEFAULT_ADDUCTS: dict[str, float] = {
    "[M+H]+": 1.0073,
    "[M+Na]+": 22.9892,
    "[M+K]+": 38.9632,
    "[M-H]-": -1.0073,
}

# Natural isotope abundances: (most abundant %, M+1 fraction, M+2 fraction)
# Fractions are per-atom contributions to M+1 and M+2 relative to M.
ISOTOPE_DATA: dict[str, dict[str, float]] = {
    "C": {"M": 0.989, "M1": 0.011, "M2": 0.0},
    "H": {"M": 0.9999, "M1": 0.0001, "M2": 0.0},
    "N": {"M": 0.9963, "M1": 0.0037, "M2": 0.0},
    "O": {"M": 0.9976, "M1": 0.0004, "M2": 0.0020},
    "S": {"M": 0.9500, "M1": 0.0075, "M2": 0.0425},
}

# Monoisotopic masses
MONOISOTOPIC_MASS: dict[str, float] = {
    "C": 12.0000,
    "H": 1.007940,
    "N": 14.003074,
    "O": 15.994915,
    "S": 31.972071,
    "P": 30.973762,
    "F": 18.998403,
    "Cl": 34.968853,
    "Br": 78.918338,
    "I": 126.904473,
}

# Formula parsing regex: element symbol followed by optional count
_FORMULA_RE = re.compile(r"([A-Z][a-z]?)(\d*)")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MSPeak:
    """A mass spectrum peak."""
    mz: float
    intensity: float
    charge: int = 1
    neutral_mass: float = 0.0
    assignment: Optional[str] = None


@dataclass
class MSResults:
    """Mass spectrometry analysis results."""
    peaks: list[MSPeak] = field(default_factory=list)
    base_peak_mz: float = 0.0
    base_peak_intensity: float = 0.0
    tic: float = 0.0  # total ion count

    def table(self) -> str:
        """Formatted results table."""
        lines = [
            f"[Praxis] Mass Spectrometry Analysis -- {len(self.peaks)} peak(s)",
            f"  Base peak: m/z = {self.base_peak_mz:.4f}, intensity = {self.base_peak_intensity:.1f}",
            f"  TIC: {self.tic:.1f}",
            "",
            f"  {'#':>3}  {'m/z':>12}  {'Intensity':>12}  {'z':>3}  {'Neutral Mass':>14}  {'Assignment'}",
            "  " + "-" * 65,
        ]
        for i, p in enumerate(self.peaks, 1):
            assign = p.assignment or "--"
            lines.append(
                f"  {i:>3}  {p.mz:>12.4f}  {p.intensity:>12.1f}  {p.charge:>3}  {p.neutral_mass:>14.4f}  {assign}"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyse_spectrum(
    mz: Any,
    intensity: Any,
    *,
    min_height_pct: float = 3.0,
    charge: int = 1,
) -> MSResults:
    """Analyse a mass spectrum: detect peaks and calculate neutral masses.

    Parameters
    ----------
    mz : array-like
        Mass-to-charge ratio values.
    intensity : array-like
        Intensity values.
    min_height_pct : float
        Minimum peak height as % of max intensity.
    charge : int
        Default charge state for all peaks.

    Returns
    -------
    MSResults
    """
    mz_arr, int_arr = validate_xy(
        np.asarray(mz, dtype=float),
        np.asarray(intensity, dtype=float),
        allow_nan=False,
    )

    # Sort by m/z
    order = np.argsort(mz_arr)
    mz_arr, int_arr = mz_arr[order], int_arr[order]

    # Total ion count
    tic = float(np.sum(int_arr))

    # Base peak
    base_idx = int(np.argmax(int_arr))
    base_mz = float(mz_arr[base_idx])
    base_int = float(int_arr[base_idx])

    # Detect peaks
    peak_results = find_peaks_auto(
        mz_arr, int_arr,
        min_height_pct=min_height_pct,
    )

    ms_peaks = []
    for p in peak_results.peaks:
        neutral = _neutral_mass(p.position, charge)
        ms_peaks.append(MSPeak(
            mz=p.position,
            intensity=p.height,
            charge=charge,
            neutral_mass=neutral,
        ))

    results = MSResults(
        peaks=ms_peaks,
        base_peak_mz=base_mz,
        base_peak_intensity=base_int,
        tic=tic,
    )
    print(results.table())
    return results


def _neutral_mass(mz: float, charge: int) -> float:
    """Calculate neutral mass from m/z and charge.

    For positive ions: M = (m/z) * z - z * 1.0073
    For negative ions (z < 0): M = (m/z) * |z| + |z| * 1.0073
    """
    proton_mass = 1.007276
    z = abs(charge)
    if charge > 0:
        return mz * z - z * proton_mass
    elif charge < 0:
        return mz * z + z * proton_mass
    return mz


# ---------------------------------------------------------------------------
# Molecular ion identification
# ---------------------------------------------------------------------------

def find_molecular_ion(
    mz: Any,
    intensity: Any,
    *,
    adducts: Optional[dict[str, float]] = None,
    tolerance_da: float = 0.5,
    min_height_pct: float = 3.0,
) -> list[MSPeak]:
    """Identify potential molecular ion peaks ([M+H]+, [M+Na]+, etc.).

    Looks for characteristic adduct patterns in the high-m/z region.

    Parameters
    ----------
    mz : array-like
        Mass-to-charge values.
    intensity : array-like
        Intensity values.
    adducts : dict, optional
        Adduct name -> mass offset. Uses DEFAULT_ADDUCTS if None.
    tolerance_da : float
        Mass tolerance in Da for matching adduct pairs.
    min_height_pct : float
        Minimum peak height as % of max.

    Returns
    -------
    list of MSPeak with assignments.
    """
    if adducts is None:
        adducts = DEFAULT_ADDUCTS

    mz_arr, int_arr = validate_xy(
        np.asarray(mz, dtype=float),
        np.asarray(intensity, dtype=float),
        allow_nan=False,
    )

    order = np.argsort(mz_arr)
    mz_arr, int_arr = mz_arr[order], int_arr[order]

    peak_results = find_peaks_auto(
        mz_arr, int_arr,
        min_height_pct=min_height_pct,
    )

    peak_mzs = np.array([p.position for p in peak_results.peaks])
    peak_heights = np.array([p.height for p in peak_results.peaks])

    assigned: list[MSPeak] = []

    # For each pair of adducts, check if the mass difference matches
    adduct_names = list(adducts.keys())
    adduct_offsets = list(adducts.values())

    for i, mz_i in enumerate(peak_mzs):
        for name, offset in adducts.items():
            # If this peak is [M+X]+, then M = mz_i - offset
            neutral = mz_i - offset
            if neutral <= 0:
                continue

            # Check if other adduct peaks exist for this neutral mass
            matches = 0
            for other_name, other_offset in adducts.items():
                if other_name == name:
                    continue
                expected_mz = neutral + other_offset
                diffs = np.abs(peak_mzs - expected_mz)
                if np.any(diffs < tolerance_da):
                    matches += 1

            if matches >= 1:
                assigned.append(MSPeak(
                    mz=mz_i,
                    intensity=float(peak_heights[i]),
                    charge=1,
                    neutral_mass=neutral,
                    assignment=name,
                ))

    if assigned:
        print(f"[Praxis] Molecular ion candidates: {len(assigned)} assignment(s)")
        for p in assigned:
            print(f"  m/z {p.mz:.4f} -> {p.assignment} (M = {p.neutral_mass:.4f})")
    else:
        print("[Praxis] No molecular ion patterns identified.")

    return assigned


# ---------------------------------------------------------------------------
# Isotope pattern prediction
# ---------------------------------------------------------------------------

def isotope_pattern(formula: str) -> dict[str, float]:
    """Calculate expected isotope pattern from a molecular formula.

    Returns relative intensities for M, M+1, and M+2 peaks using
    natural isotope abundances.

    Parameters
    ----------
    formula : str
        Molecular formula, e.g. "C6H12O6".

    Returns
    -------
    dict with keys 'M', 'M+1', 'M+2' as relative intensities (M = 100).
    Also includes 'monoisotopic_mass'.
    """
    composition = _parse_formula(formula)
    if not composition:
        raise ValueError(f"Could not parse formula: {formula}")

    # Calculate monoisotopic mass
    mono_mass = 0.0
    for element, count in composition.items():
        if element not in MONOISOTOPIC_MASS:
            raise ValueError(f"Unknown element: {element}")
        mono_mass += MONOISOTOPIC_MASS[element] * count

    # Calculate M+1 and M+2 relative probabilities
    # Using the approximation for small natural abundances:
    #   P(M+1)/P(M) ~ sum over atoms of (n_i * M1_fraction_i / M_fraction_i)
    #   P(M+2)/P(M) ~ sum over atoms of (n_i * M2_fraction_i / M_fraction_i)
    #                  + 0.5 * [P(M+1)/P(M)]^2 (combinatorial term)
    m1_ratio = 0.0
    m2_ratio = 0.0

    for element, count in composition.items():
        iso = ISOTOPE_DATA.get(element)
        if iso is None:
            continue
        # Per-atom contribution
        m1_ratio += count * (iso["M1"] / iso["M"])
        m2_ratio += count * (iso["M2"] / iso["M"])

    # Add combinatorial M+2 contribution from pairs of M+1
    m2_ratio += 0.5 * m1_ratio ** 2

    # Express as percentages relative to M = 100
    result = {
        "M": 100.0,
        "M+1": m1_ratio * 100.0,
        "M+2": m2_ratio * 100.0,
        "monoisotopic_mass": mono_mass,
    }

    print(f"[Praxis] Isotope pattern for {formula} (monoisotopic mass = {mono_mass:.4f} Da)")
    print(f"  M:   100.00%")
    print(f"  M+1: {result['M+1']:.2f}%")
    print(f"  M+2: {result['M+2']:.2f}%")

    return result


def _parse_formula(formula: str) -> dict[str, int]:
    """Parse a molecular formula string into element counts.

    E.g. 'C6H12O6' -> {'C': 6, 'H': 12, 'O': 6}
    """
    composition: dict[str, int] = {}
    for match in _FORMULA_RE.finditer(formula):
        element = match.group(1)
        count_str = match.group(2)
        if not element:
            continue
        count = int(count_str) if count_str else 1
        composition[element] = composition.get(element, 0) + count
    return composition


# ---------------------------------------------------------------------------
# Mass accuracy
# ---------------------------------------------------------------------------

def mass_accuracy(measured: float, theoretical: float) -> float:
    """Calculate mass accuracy in parts per million (ppm).

    Parameters
    ----------
    measured : float
        Measured mass (Da).
    theoretical : float
        Theoretical (exact) mass (Da).

    Returns
    -------
    float
        Mass accuracy in ppm.
    """
    if theoretical == 0:
        raise ValueError("Theoretical mass cannot be zero.")
    ppm = (measured - theoretical) / theoretical * 1e6
    print(f"[Praxis] Mass accuracy: {ppm:.2f} ppm (measured={measured:.6f}, theoretical={theoretical:.6f})")
    return ppm
