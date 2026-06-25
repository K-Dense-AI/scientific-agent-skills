"""NMR spectroscopy analysis (1H and 13C focus).

Peak detection, integration, referencing, and multiplicity estimation
for NMR spectra.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np
from scipy.signal import find_peaks as scipy_find_peaks
from scipy.integrate import trapezoid

from scripts.core.utils import validate_xy, validate_array


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Common solvent residual peaks (1H chemical shift in ppm)
SOLVENT_PEAKS_1H = {
    "CDCl3": 7.26,
    "DMSO-d6": 2.50,
    "D2O": 4.79,
    "CD3OD": 3.31,
    "acetone-d6": 2.05,
    "C6D6": 7.16,
    "CD2Cl2": 5.32,
    "THF-d8": 3.58,
    "toluene-d8": 2.09,
}

# Common solvent residual peaks (13C chemical shift in ppm)
SOLVENT_PEAKS_13C = {
    "CDCl3": 77.16,
    "DMSO-d6": 39.52,
    "CD3OD": 49.00,
    "acetone-d6": 29.84,
    "C6D6": 128.06,
    "CD2Cl2": 53.84,
    "THF-d8": 67.21,
    "toluene-d8": 20.43,
}

# Multiplicity labels
MULTIPLICITY_LABELS = {
    1: "s",   # singlet
    2: "d",   # doublet
    3: "t",   # triplet
    4: "q",   # quartet
    5: "quint",
    6: "sext",
    7: "sept",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class NMRPeak:
    """A peak in an NMR spectrum."""
    chemical_shift: float         # ppm
    integral: float               # Normalised integral
    multiplicity: str = "m"       # s, d, t, q, m, etc.
    assignment: Optional[str] = None
    j_coupling: Optional[float] = None  # Hz

    def label(self) -> str:
        """Short label for display."""
        parts = [f"{self.chemical_shift:.2f} ppm"]
        parts.append(f"({self.multiplicity})")
        if self.j_coupling is not None:
            parts.append(f"J={self.j_coupling:.1f} Hz")
        return " ".join(parts)


@dataclass
class NMRResults:
    """Full NMR analysis results."""
    peaks: list[NMRPeak] = field(default_factory=list)
    nucleus: str = "1H"
    solvent: Optional[str] = None
    reference: float = 0.0  # Reference shift applied (ppm)

    def table(self) -> str:
        """Formatted results table."""
        lines = [
            f"[Praxis] NMR Analysis -- {self.nucleus}",
        ]
        if self.solvent:
            lines.append(f"  Solvent: {self.solvent}")
        lines.append(f"  Reference shift: {self.reference:.3f} ppm")
        lines.append(f"  Peaks found: {len(self.peaks)}")

        if self.peaks:
            lines.append("")
            lines.append(
                f"  {'#':>3}  {'Shift (ppm)':>12}  {'Integral':>10}  "
                f"{'Mult':>6}  {'J (Hz)':>8}  {'Assignment'}"
            )
            lines.append("  " + "-" * 65)
            for i, p in enumerate(self.peaks, 1):
                j_str = f"{p.j_coupling:.1f}" if p.j_coupling is not None else "--"
                assign = p.assignment or "--"
                lines.append(
                    f"  {i:>3}  {p.chemical_shift:>12.3f}  {p.integral:>10.2f}  "
                    f"{p.multiplicity:>6}  {j_str:>8}  {assign}"
                )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Main analysis functions
# ---------------------------------------------------------------------------

def analyse_nmr(
    chemical_shift: Any,
    intensity: Any,
    *,
    nucleus: str = "1H",
    solvent: Optional[str] = None,
    reference_shift: float = 0.0,
) -> NMRResults:
    """Analyse an NMR spectrum: peak detection, integration, multiplicity.

    Parameters
    ----------
    chemical_shift : array-like
        Chemical shift in ppm.
    intensity : array-like
        Signal intensity.
    nucleus : str
        Nucleus type ('1H', '13C', etc.).
    solvent : str, optional
        Solvent name (e.g. 'CDCl3'). Used for annotation.
    reference_shift : float
        Shift to apply to the chemical shift axis (ppm). For example,
        if TMS is not at 0, set this to correct the offset.

    Returns
    -------
    NMRResults
    """
    cs = np.asarray(chemical_shift, dtype=float)
    intens = np.asarray(intensity, dtype=float)
    cs, intens = validate_xy(cs, intens, allow_nan=False)

    # Apply reference shift
    cs = cs - reference_shift

    # Sort by chemical shift (descending, conventional for NMR)
    order = np.argsort(cs)[::-1]
    cs = cs[order]
    intens = intens[order]

    # Peak detection
    # For NMR, we work on the absolute intensity
    intens_pos = np.clip(intens, 0, None)
    threshold = np.max(intens_pos) * 0.02  # 2% of max

    # scipy find_peaks works on ascending index, so reverse for descending ppm
    peaks_idx, props = scipy_find_peaks(
        intens_pos, height=threshold, distance=3, prominence=threshold * 0.5
    )

    # Integrate and characterise each peak
    nmr_peaks = []
    peak_regions = _detect_peak_regions(cs, intens_pos, peaks_idx)

    for idx, (left, right) in zip(peaks_idx, peak_regions):
        region_cs = cs[left:right + 1]
        region_int = intens_pos[left:right + 1]

        # Integration (area under peak)
        if len(region_cs) > 1:
            area = float(np.abs(trapezoid(region_int, region_cs)))
        else:
            area = float(region_int[0])

        # Estimate multiplicity from sub-peaks
        mult, j_hz = _estimate_multiplicity(region_cs, region_int)

        nmr_peaks.append(NMRPeak(
            chemical_shift=float(cs[idx]),
            integral=area,
            multiplicity=mult,
            j_coupling=j_hz,
        ))

    # Normalise integrals (smallest non-zero = 1)
    if nmr_peaks:
        integrals = [p.integral for p in nmr_peaks if p.integral > 0]
        if integrals:
            min_integral = min(integrals)
            for p in nmr_peaks:
                p.integral = p.integral / min_integral if min_integral > 0 else p.integral

    results = NMRResults(
        peaks=nmr_peaks,
        nucleus=nucleus,
        solvent=solvent,
        reference=reference_shift,
    )
    print(results.table())
    return results


def integrate_peaks(
    chemical_shift: Any,
    intensity: Any,
    *,
    regions: Optional[list[tuple[float, float]]] = None,
) -> list[dict[str, float]]:
    """Integrate NMR peaks over specified ppm regions.

    Parameters
    ----------
    chemical_shift : array-like
        Chemical shift in ppm.
    intensity : array-like
        Signal intensity.
    regions : list of (low_ppm, high_ppm), optional
        PPM regions to integrate. If None, auto-detect peak regions.

    Returns
    -------
    list of dict
        Each dict has 'center_ppm', 'integral', 'normalised_integral'.
        Normalised so the smallest integral = 1.0.
    """
    cs = np.asarray(chemical_shift, dtype=float)
    intens = np.asarray(intensity, dtype=float)
    cs, intens = validate_xy(cs, intens, allow_nan=False)

    # Sort ascending for integration
    order = np.argsort(cs)
    cs = cs[order]
    intens = intens[order]

    if regions is None:
        regions = _auto_detect_regions(cs, intens)

    results = []
    for low, high in regions:
        mask = (cs >= low) & (cs <= high)
        if np.sum(mask) < 2:
            continue
        region_cs = cs[mask]
        region_int = intens[mask]
        area = float(trapezoid(region_int, region_cs))
        center = float((low + high) / 2.0)
        results.append({
            "center_ppm": center,
            "range": (low, high),
            "integral": abs(area),
        })

    # Normalise: smallest non-zero integral = 1
    integrals = [r["integral"] for r in results if r["integral"] > 0]
    min_int = min(integrals) if integrals else 1.0
    for r in results:
        r["normalised_integral"] = r["integral"] / min_int if min_int > 0 else 0.0

    # Print summary
    lines = [f"[Praxis] NMR Integration -- {len(results)} region(s)"]
    for i, r in enumerate(results, 1):
        lines.append(
            f"  {i:>3}  {r['range'][0]:.2f}-{r['range'][1]:.2f} ppm  "
            f"integral={r['normalised_integral']:.2f}"
        )
    print("\n".join(lines))

    return results


def reference_spectrum(
    chemical_shift: Any,
    intensity: Any,
    *,
    reference_peak_ppm: float,
    target_ppm: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Shift the spectrum so a reference peak aligns to target_ppm.

    Parameters
    ----------
    chemical_shift : array-like
        Chemical shift in ppm.
    intensity : array-like
        Signal intensity.
    reference_peak_ppm : float
        Current ppm position of the reference peak (e.g. TMS).
    target_ppm : float
        Desired position for the reference peak (default 0.0).

    Returns
    -------
    (shifted_chemical_shift, intensity)
    """
    cs = np.asarray(chemical_shift, dtype=float)
    intens = np.asarray(intensity, dtype=float)
    cs, intens = validate_xy(cs, intens, allow_nan=False)

    shift = target_ppm - reference_peak_ppm
    cs_shifted = cs + shift

    print(f"[Praxis] Spectrum referenced: shifted by {shift:+.4f} ppm")
    return cs_shifted, intens


def predict_multiplicity(
    chemical_shift: Any,
    intensity: Any,
    *,
    peaks: Optional[list[int]] = None,
) -> list[dict[str, Any]]:
    """Estimate splitting pattern from peak shape analysis.

    Counts sub-peaks within each major peak region to determine
    singlet, doublet, triplet, quartet, or multiplet.

    Parameters
    ----------
    chemical_shift : array-like
        Chemical shift in ppm.
    intensity : array-like
        Signal intensity.
    peaks : list of int, optional
        Indices of major peaks to analyse. If None, auto-detect.

    Returns
    -------
    list of dict
        Each dict: 'chemical_shift', 'multiplicity', 'sub_peak_count',
        'estimated_j_hz'.
    """
    cs = np.asarray(chemical_shift, dtype=float)
    intens = np.asarray(intensity, dtype=float)
    cs, intens = validate_xy(cs, intens, allow_nan=False)

    # Sort descending (NMR convention)
    order = np.argsort(cs)[::-1]
    cs = cs[order]
    intens = intens[order]

    intens_pos = np.clip(intens, 0, None)
    threshold = np.max(intens_pos) * 0.02

    if peaks is None:
        peaks_idx, _ = scipy_find_peaks(
            intens_pos, height=threshold, distance=5, prominence=threshold * 0.5
        )
    else:
        peaks_idx = np.array(peaks)

    peak_regions = _detect_peak_regions(cs, intens_pos, peaks_idx)

    results = []
    for idx, (left, right) in zip(peaks_idx, peak_regions):
        region_cs = cs[left:right + 1]
        region_int = intens_pos[left:right + 1]

        mult, j_hz = _estimate_multiplicity(region_cs, region_int)

        results.append({
            "chemical_shift": float(cs[idx]),
            "multiplicity": mult,
            "sub_peak_count": _count_sub_peaks(region_int),
            "estimated_j_hz": j_hz,
        })

    # Print summary
    lines = [f"[Praxis] Multiplicity Analysis -- {len(results)} peak(s)"]
    for i, r in enumerate(results, 1):
        j_str = f"J={r['estimated_j_hz']:.1f} Hz" if r["estimated_j_hz"] else "--"
        lines.append(
            f"  {i:>3}  {r['chemical_shift']:.3f} ppm  {r['multiplicity']:>6}  "
            f"({r['sub_peak_count']} sub-peaks)  {j_str}"
        )
    print("\n".join(lines))

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_peak_regions(
    cs: np.ndarray, intens: np.ndarray, peaks_idx: np.ndarray
) -> list[tuple[int, int]]:
    """Find left and right boundaries for each peak."""
    baseline = np.max(intens) * 0.01
    regions = []
    for idx in peaks_idx:
        # Walk left
        left = idx
        while left > 0 and intens[left - 1] > baseline:
            left -= 1
        # Walk right
        right = idx
        while right < len(intens) - 1 and intens[right + 1] > baseline:
            right += 1
        regions.append((left, right))
    return regions


def _count_sub_peaks(intens: np.ndarray) -> int:
    """Count sub-peaks in a peak region."""
    if len(intens) < 3:
        return 1
    # Use local maxima
    threshold = np.max(intens) * 0.1
    sub_peaks, _ = scipy_find_peaks(intens, height=threshold)
    return max(1, len(sub_peaks))


def _estimate_multiplicity(
    cs: np.ndarray, intens: np.ndarray
) -> tuple[str, Optional[float]]:
    """Estimate multiplicity and J-coupling from a peak region."""
    n_sub = _count_sub_peaks(intens)

    if n_sub <= 0:
        n_sub = 1

    if n_sub in MULTIPLICITY_LABELS:
        mult = MULTIPLICITY_LABELS[n_sub]
    else:
        mult = "m"

    # Estimate J-coupling from sub-peak spacing
    j_hz = None
    if n_sub >= 2 and len(cs) >= 3:
        threshold = np.max(intens) * 0.1
        sub_idx, _ = scipy_find_peaks(intens, height=threshold)
        if len(sub_idx) >= 2:
            # J-coupling from spacing between sub-peaks
            sub_ppm = cs[sub_idx]
            spacings = np.abs(np.diff(np.sort(sub_ppm)))
            if len(spacings) > 0:
                # Convert ppm spacing to Hz (assume 400 MHz spectrometer)
                mean_spacing_ppm = float(np.mean(spacings))
                j_hz = mean_spacing_ppm * 400.0  # Approximate

    return mult, j_hz


def _auto_detect_regions(
    cs: np.ndarray, intens: np.ndarray
) -> list[tuple[float, float]]:
    """Auto-detect integration regions from the spectrum."""
    threshold = np.max(intens) * 0.02
    above = intens > threshold

    regions = []
    in_region = False
    start = 0

    for i in range(len(above)):
        if above[i] and not in_region:
            start = i
            in_region = True
        elif not above[i] and in_region:
            if i - start >= 2:
                regions.append((float(cs[start]), float(cs[i - 1])))
            in_region = False

    if in_region and len(cs) - start >= 2:
        regions.append((float(cs[start]), float(cs[-1])))

    # Ensure each region has low < high
    regions = [(min(a, b), max(a, b)) for a, b in regions]
    return regions
