"""SEM and EDS analysis.

SEM: grain size analysis (line intercept, area method), porosity estimation,
particle size distribution.
EDS: elemental quantification table, line scan profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np
from scipy.signal import find_peaks

from scripts.core.utils import validate_array


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GrainSizeResults:
    """Results from grain size analysis."""
    mean_size: float           # um or nm
    std_size: float
    median_size: float
    min_size: float
    max_size: float
    n_grains: int
    d10: float                 # 10th percentile
    d50: float                 # 50th percentile (= median)
    d90: float                 # 90th percentile
    unit: str = "um"

    def table(self) -> str:
        lines = [
            "[Praxis] Grain Size Analysis",
            f"  N grains   = {self.n_grains}",
            f"  Mean       = {self.mean_size:.2f} {self.unit}",
            f"  Std Dev    = {self.std_size:.2f} {self.unit}",
            f"  Median     = {self.median_size:.2f} {self.unit}",
            f"  Min, Max   = {self.min_size:.2f}, {self.max_size:.2f} {self.unit}",
            f"  D10, D50, D90 = {self.d10:.2f}, {self.d50:.2f}, {self.d90:.2f} {self.unit}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class EDSResults:
    """Results from EDS elemental analysis."""
    elements: list[str] = field(default_factory=list)
    weight_pct: list[float] = field(default_factory=list)
    atomic_pct: list[float] = field(default_factory=list)

    def table(self) -> str:
        lines = [
            "[Praxis] EDS Elemental Composition",
            f"  {'Element':>8}  {'wt%':>8}  {'at%':>8}",
            "  " + "-" * 30,
        ]
        for elem, wt, at in zip(self.elements, self.weight_pct, self.atomic_pct):
            lines.append(f"  {elem:>8}  {wt:>8.2f}  {at:>8.2f}")
        lines.append(f"  {'Total':>8}  {sum(self.weight_pct):>8.2f}  {sum(self.atomic_pct):>8.2f}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Grain size analysis
# ---------------------------------------------------------------------------

def grain_size_line_intercept(
    intercept_lengths: Any,
    *,
    scale_factor: float = 1.0,
    unit: str = "um",
) -> GrainSizeResults:
    """Calculate grain size from line intercept measurements.

    Parameters
    ----------
    intercept_lengths : array-like
        Measured intercept lengths (in image units or real units).
    scale_factor : float
        Multiply lengths by this to convert to real units.
    unit : str
        Unit string for reporting.

    Returns
    -------
    GrainSizeResults
    """
    lengths = validate_array(intercept_lengths, "intercept_lengths") * scale_factor

    d10, d50, d90 = np.percentile(lengths, [10, 50, 90])

    results = GrainSizeResults(
        mean_size=np.mean(lengths),
        std_size=np.std(lengths, ddof=1),
        median_size=np.median(lengths),
        min_size=np.min(lengths),
        max_size=np.max(lengths),
        n_grains=len(lengths),
        d10=d10, d50=d50, d90=d90,
        unit=unit,
    )

    print(results.table())
    return results


def grain_size_area_method(
    areas: Any,
    *,
    scale_factor: float = 1.0,
    unit: str = "um",
) -> GrainSizeResults:
    """Calculate grain size from area measurements.

    Equivalent circular diameter: d = 2 * sqrt(A / pi).

    Parameters
    ----------
    areas : array-like
        Measured grain areas.
    scale_factor : float
        Multiply areas by this to convert to real units squared.
    unit : str
        Unit for diameter.

    Returns
    -------
    GrainSizeResults
    """
    a = validate_array(areas, "areas") * scale_factor
    diameters = 2 * np.sqrt(a / np.pi)

    d10, d50, d90 = np.percentile(diameters, [10, 50, 90])

    results = GrainSizeResults(
        mean_size=np.mean(diameters),
        std_size=np.std(diameters, ddof=1),
        median_size=np.median(diameters),
        min_size=np.min(diameters),
        max_size=np.max(diameters),
        n_grains=len(diameters),
        d10=d10, d50=d50, d90=d90,
        unit=unit,
    )

    print(results.table())
    return results


def estimate_porosity(
    image_data: Any,
    *,
    threshold: Optional[float] = None,
    dark_is_pore: bool = True,
) -> dict[str, float]:
    """Estimate porosity from a greyscale SEM image (as 2D array).

    Parameters
    ----------
    image_data : 2D array-like
        Greyscale image (0-255 or 0-1).
    threshold : float, optional
        Threshold for pore/solid separation. Auto (Otsu) if None.
    dark_is_pore : bool
        If True, values below threshold are pores.

    Returns
    -------
    dict with 'porosity_pct', 'threshold', 'pore_pixels', 'total_pixels'.
    """
    img = np.asarray(image_data, dtype=float)
    if img.ndim != 2:
        raise ValueError(f"Expected 2D image array, got shape {img.shape}")

    # Normalise to 0-255
    if img.max() <= 1.0:
        img = img * 255

    # Otsu threshold
    if threshold is None:
        threshold = _otsu_threshold(img)

    if dark_is_pore:
        pore_mask = img < threshold
    else:
        pore_mask = img > threshold

    pore_pixels = np.sum(pore_mask)
    total_pixels = img.size
    porosity = (pore_pixels / total_pixels) * 100

    result = {
        "porosity_pct": porosity,
        "threshold": threshold,
        "pore_pixels": int(pore_pixels),
        "total_pixels": int(total_pixels),
    }

    print(f"[Praxis] Porosity: {porosity:.1f}% (threshold={threshold:.1f})")
    return result


def _otsu_threshold(img: np.ndarray) -> float:
    """Otsu's method for automatic thresholding."""
    hist, bin_edges = np.histogram(img.ravel(), bins=256, range=(0, 256))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    total = img.size
    sum_total = np.sum(bin_centers * hist)

    sum_bg = 0.0
    weight_bg = 0.0
    max_variance = 0.0
    threshold = 0.0

    for i in range(256):
        weight_bg += hist[i]
        if weight_bg == 0:
            continue

        weight_fg = total - weight_bg
        if weight_fg == 0:
            break

        sum_bg += bin_centers[i] * hist[i]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg

        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2

        if variance > max_variance:
            max_variance = variance
            threshold = bin_centers[i]

    return threshold


# ---------------------------------------------------------------------------
# EDS analysis
# ---------------------------------------------------------------------------

def parse_eds_composition(
    elements: Sequence[str],
    weight_pct: Optional[Sequence[float]] = None,
    atomic_pct: Optional[Sequence[float]] = None,
    atomic_masses: Optional[dict[str, float]] = None,
) -> EDSResults:
    """Parse and validate EDS composition data.

    Provide either weight% or atomic% — the other is calculated.

    Parameters
    ----------
    elements : list of str
        Element symbols.
    weight_pct : list of float, optional
        Weight percentages.
    atomic_pct : list of float, optional
        Atomic percentages.
    atomic_masses : dict, optional
        Custom atomic masses. Uses defaults if not given.

    Returns
    -------
    EDSResults
    """
    # Default atomic masses
    _am = {
        "H": 1.008, "He": 4.003, "Li": 6.941, "Be": 9.012, "B": 10.81,
        "C": 12.01, "N": 14.01, "O": 16.00, "F": 19.00, "Na": 22.99,
        "Mg": 24.31, "Al": 26.98, "Si": 28.09, "P": 30.97, "S": 32.07,
        "Cl": 35.45, "K": 39.10, "Ca": 40.08, "Ti": 47.87, "V": 50.94,
        "Cr": 52.00, "Mn": 54.94, "Fe": 55.85, "Co": 58.93, "Ni": 58.69,
        "Cu": 63.55, "Zn": 65.38, "Ga": 69.72, "Ge": 72.63, "As": 74.92,
        "Se": 78.97, "Br": 79.90, "Sr": 87.62, "Zr": 91.22, "Nb": 92.91,
        "Mo": 95.95, "Ag": 107.87, "Sn": 118.71, "Ba": 137.33, "La": 138.91,
        "Ce": 140.12, "Pb": 207.20, "Bi": 208.98, "Au": 196.97, "Pt": 195.08,
    }
    if atomic_masses:
        _am.update(atomic_masses)

    if weight_pct is not None:
        wt = list(weight_pct)
        # Calculate atomic%
        moles = [w / _am.get(e, 1.0) for e, w in zip(elements, wt)]
        total_moles = sum(moles)
        at = [(m / total_moles) * 100 for m in moles] if total_moles > 0 else [0] * len(elements)
    elif atomic_pct is not None:
        at = list(atomic_pct)
        # Calculate weight%
        masses = [a * _am.get(e, 1.0) for e, a in zip(elements, at)]
        total_mass = sum(masses)
        wt = [(m / total_mass) * 100 for m in masses] if total_mass > 0 else [0] * len(elements)
    else:
        raise ValueError("Provide either weight_pct or atomic_pct.")

    results = EDSResults(elements=list(elements), weight_pct=wt, atomic_pct=at)
    print(results.table())
    return results


def analyse_eds_line_scan(
    position: Any,
    intensities: dict[str, Any],
) -> dict[str, np.ndarray]:
    """Process EDS line scan data.

    Parameters
    ----------
    position : array-like
        Position along the line (um or pixels).
    intensities : dict
        Element -> intensity array mapping.

    Returns
    -------
    dict mapping element -> normalised intensity array.
    """
    pos = np.asarray(position, dtype=float)
    normalised = {}

    for elem, intens in intensities.items():
        arr = np.asarray(intens, dtype=float)
        if len(arr) != len(pos):
            raise ValueError(f"Intensity array for {elem} has wrong length.")
        # Normalise to 0-1
        i_min, i_max = arr.min(), arr.max()
        if i_max > i_min:
            normalised[elem] = (arr - i_min) / (i_max - i_min)
        else:
            normalised[elem] = np.zeros_like(arr)

    print(f"[Praxis] EDS line scan: {len(normalised)} elements, {len(pos)} points")
    return normalised
