"""FTIR, Raman, and UV-Vis spectroscopy analysis.

FTIR: peak assignment, functional group ID, ATR correction, baseline
correction, spectral subtraction.
Raman: peak fitting, depolarisation ratio.
UV-Vis: Beer-Lambert, band gap (Tauc plot), absorbance/transmittance conversion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np
from scipy.integrate import trapezoid

from scripts.core.utils import validate_xy
from scripts.analysis.peaks import find_peaks_auto, PeakResults
from scripts.analysis.baseline import correct_baseline


# ---------------------------------------------------------------------------
# Common IR functional group assignments (wavenumber ranges)
# ---------------------------------------------------------------------------

IR_ASSIGNMENTS = [
    (3200, 3600, "O-H stretch", "Alcohol, carboxylic acid, water"),
    (3250, 3400, "N-H stretch", "Amine, amide"),
    (2850, 3000, "C-H stretch (sp3)", "Alkane"),
    (3000, 3100, "C-H stretch (sp2)", "Alkene, aromatic"),
    (3300, 3320, "C-H stretch (sp)", "Alkyne"),
    (2100, 2260, "C=C or C=N triple bond", "Alkyne, nitrile"),
    (1650, 1750, "C=O stretch", "Carbonyl (ester, ketone, aldehyde, amide, acid)"),
    (1600, 1680, "C=C stretch", "Alkene, aromatic"),
    (1500, 1600, "Aromatic C=C stretch", "Aromatic ring"),
    (1350, 1480, "C-H bend", "Alkane deformation"),
    (1180, 1360, "C-N stretch", "Amine"),
    (1000, 1300, "C-O stretch", "Alcohol, ether, ester"),
    (800, 1000, "C-H out-of-plane bend", "Aromatic, alkene"),
    (600, 800, "C-Cl stretch", "Halide"),
    (500, 600, "C-Br stretch", "Halide"),
    (400, 500, "Metal-O stretch", "Inorganic oxide"),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SpectralPeak:
    """A peak in a spectrum with optional assignment."""
    position: float           # Wavenumber (cm-1) or wavelength (nm)
    intensity: float
    fwhm: Optional[float] = None
    area: Optional[float] = None
    assignment: Optional[str] = None
    functional_group: Optional[str] = None


@dataclass
class SpectroscopyResults:
    """Results from spectroscopic analysis."""
    peaks: list[SpectralPeak] = field(default_factory=list)
    technique: str = "FTIR"
    band_gap: Optional[float] = None  # eV (for UV-Vis Tauc)

    def table(self) -> str:
        lines = [f"[Praxis] {self.technique} Analysis — {len(self.peaks)} peak(s)"]
        if self.band_gap is not None:
            lines.append(f"  Band gap = {self.band_gap:.2f} eV")

        if self.peaks:
            lines.append(f"\n  {'#':>3}  {'Position':>10}  {'Intensity':>12}  {'FWHM':>8}  {'Assignment'}")
            lines.append("  " + "-" * 65)
            for i, p in enumerate(self.peaks, 1):
                fwhm = f"{p.fwhm:.1f}" if p.fwhm else "--"
                assign = p.assignment or "--"
                fg = f" ({p.functional_group})" if p.functional_group else ""
                lines.append(
                    f"  {i:>3}  {p.position:>10.1f}  {p.intensity:>12.4e}  {fwhm:>8}  {assign}{fg}"
                )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# FTIR Analysis
# ---------------------------------------------------------------------------

def analyse_ftir(
    wavenumber: Any,
    absorbance: Any,
    *,
    baseline_method: Optional[str] = None,
    min_peak_height_pct: float = 5.0,
    assign_peaks: bool = True,
) -> SpectroscopyResults:
    """Analyse FTIR spectrum.

    Parameters
    ----------
    wavenumber : array-like
        Wavenumber in cm-1.
    absorbance : array-like
        Absorbance or transmittance values.
    baseline_method : str, optional
        Baseline correction method. None = no correction.
    min_peak_height_pct : float
        Minimum peak height as % of max.
    assign_peaks : bool
        Attempt automatic functional group assignment.

    Returns
    -------
    SpectroscopyResults
    """
    wn, absorb = validate_xy(
        np.asarray(wavenumber, dtype=float),
        np.asarray(absorbance, dtype=float),
        allow_nan=False,
    )

    # Sort by wavenumber (descending is conventional for IR)
    order = np.argsort(wn)[::-1]
    wn, absorb = wn[order], absorb[order]

    # Baseline correction if requested
    if baseline_method:
        absorb, _, _ = correct_baseline(wn, absorb, method=baseline_method)

    # Peak detection
    peak_results = find_peaks_auto(wn, absorb, min_height_pct=min_peak_height_pct)

    peaks = []
    for p in peak_results.peaks:
        sp = SpectralPeak(
            position=p.position,
            intensity=p.height,
            fwhm=p.fwhm,
            area=p.area,
        )
        if assign_peaks:
            sp.assignment, sp.functional_group = _assign_ir_peak(p.position)
        peaks.append(sp)

    results = SpectroscopyResults(peaks=peaks, technique="FTIR")
    print(results.table())
    return results


def _assign_ir_peak(wavenumber: float) -> tuple[Optional[str], Optional[str]]:
    """Assign a functional group to an IR peak based on wavenumber."""
    for low, high, bond, group in IR_ASSIGNMENTS:
        if low <= wavenumber <= high:
            return bond, group
    return None, None


# ---------------------------------------------------------------------------
# Raman Analysis
# ---------------------------------------------------------------------------

def analyse_raman(
    raman_shift: Any,
    intensity: Any,
    *,
    baseline_method: Optional[str] = "als",
    min_peak_height_pct: float = 5.0,
) -> SpectroscopyResults:
    """Analyse Raman spectrum.

    Parameters
    ----------
    raman_shift : array-like
        Raman shift in cm-1.
    intensity : array-like
        Intensity (counts or a.u.).
    baseline_method : str, optional
        Baseline correction method.
    min_peak_height_pct : float
        Minimum peak height.

    Returns
    -------
    SpectroscopyResults
    """
    rs, intens = validate_xy(
        np.asarray(raman_shift, dtype=float),
        np.asarray(intensity, dtype=float),
        allow_nan=False,
    )

    order = np.argsort(rs)
    rs, intens = rs[order], intens[order]

    if baseline_method:
        intens, _, _ = correct_baseline(rs, intens, method=baseline_method)

    peak_results = find_peaks_auto(rs, intens, min_height_pct=min_peak_height_pct)

    peaks = [
        SpectralPeak(
            position=p.position, intensity=p.height,
            fwhm=p.fwhm, area=p.area,
        )
        for p in peak_results.peaks
    ]

    results = SpectroscopyResults(peaks=peaks, technique="Raman")
    print(results.table())
    return results


# ---------------------------------------------------------------------------
# UV-Vis Analysis
# ---------------------------------------------------------------------------

def absorbance_to_transmittance(absorbance: Any) -> np.ndarray:
    """Convert absorbance to transmittance (%).

    T = 10^(-A) * 100
    """
    a = np.asarray(absorbance, dtype=float)
    return np.power(10, -a) * 100


def transmittance_to_absorbance(transmittance: Any) -> np.ndarray:
    """Convert transmittance (%) to absorbance.

    A = -log10(T/100)
    """
    t = np.asarray(transmittance, dtype=float)
    t = np.clip(t, 1e-10, 100)
    return -np.log10(t / 100)


def beer_lambert(
    absorbance: float,
    molar_absorptivity: Optional[float] = None,
    path_length: float = 1.0,
    concentration: Optional[float] = None,
) -> dict[str, float]:
    """Beer-Lambert law: A = epsilon * l * c.

    Provide two of three parameters to calculate the third.

    Parameters
    ----------
    absorbance : float
        Measured absorbance.
    molar_absorptivity : float, optional
        Molar absorptivity (L/(mol*cm)).
    path_length : float
        Path length (cm). Default 1 cm.
    concentration : float, optional
        Concentration (mol/L).

    Returns
    -------
    dict with all three values.
    """
    if molar_absorptivity is not None and concentration is None:
        concentration = absorbance / (molar_absorptivity * path_length)
    elif concentration is not None and molar_absorptivity is None:
        molar_absorptivity = absorbance / (path_length * concentration)
    elif molar_absorptivity is not None and concentration is not None:
        absorbance = molar_absorptivity * path_length * concentration

    result = {
        "absorbance": absorbance,
        "molar_absorptivity": molar_absorptivity,
        "path_length": path_length,
        "concentration": concentration,
    }
    print(f"[Praxis] Beer-Lambert: A={absorbance:.4f}, eps={molar_absorptivity}, l={path_length} cm, c={concentration}")
    return result


def tauc_plot(
    wavelength_nm: Any,
    absorbance: Any,
    *,
    n: float = 0.5,
    thickness: Optional[float] = None,
) -> tuple[np.ndarray, np.ndarray, Optional[float]]:
    """Generate a Tauc plot for band gap determination.

    Parameters
    ----------
    wavelength_nm : array-like
        Wavelength in nm.
    absorbance : array-like
        Absorbance values.
    n : float
        Exponent: 0.5 for direct allowed, 2 for indirect allowed,
        1.5 for direct forbidden, 3 for indirect forbidden.
    thickness : float, optional
        Film thickness (cm) for calculating absorption coefficient.
        If None, uses absorbance directly.

    Returns
    -------
    (energy_eV, tauc_y, estimated_band_gap)
        energy is photon energy in eV
        tauc_y is (alpha*h*nu)^(1/n)
        estimated_band_gap is from linear extrapolation (eV), or None
    """
    wl = np.asarray(wavelength_nm, dtype=float)
    absorb = np.asarray(absorbance, dtype=float)

    # Convert wavelength to energy
    energy_eV = 1240.0 / wl  # E = hc/lambda

    # Absorption coefficient
    if thickness is not None and thickness > 0:
        alpha = 2.303 * absorb / thickness  # cm-1
    else:
        alpha = absorb  # Use absorbance as proxy

    # Tauc plot: (alpha * h * nu)^(1/n) vs h*nu
    tauc_y = (alpha * energy_eV) ** (1.0 / n)

    # Sort by energy
    order = np.argsort(energy_eV)
    energy_eV = energy_eV[order]
    tauc_y = tauc_y[order]

    # Estimate band gap by finding the steepest linear region
    band_gap = _estimate_band_gap(energy_eV, tauc_y)

    if band_gap is not None:
        print(f"[Praxis] Tauc plot: estimated band gap = {band_gap:.2f} eV (n={n})")
    else:
        print(f"[Praxis] Tauc plot generated (n={n}). Manual linear fit recommended.")

    return energy_eV, tauc_y, band_gap


def _estimate_band_gap(energy: np.ndarray, tauc_y: np.ndarray) -> Optional[float]:
    """Estimate band gap from the steepest linear region of a Tauc plot."""
    # Find the steepest region
    dy = np.gradient(tauc_y, energy)
    dy_smooth = np.convolve(dy, np.ones(5) / 5, mode="same")

    # Find region with maximum slope
    max_slope_idx = np.argmax(dy_smooth)

    # Fit a line around this region
    window = max(10, len(energy) // 10)
    left = max(0, max_slope_idx - window // 2)
    right = min(len(energy), max_slope_idx + window // 2)

    if right - left < 3:
        return None

    e_region = energy[left:right]
    t_region = tauc_y[left:right]

    coeffs = np.polyfit(e_region, t_region, 1)
    slope, intercept = coeffs

    if slope <= 0:
        return None

    # x-intercept: where Tauc_y = 0
    band_gap = -intercept / slope

    if band_gap < 0 or band_gap > 10:
        return None

    return float(band_gap)


# ---------------------------------------------------------------------------
# Spectral operations
# ---------------------------------------------------------------------------

def spectral_subtraction(
    x: Any,
    sample: Any,
    reference: Any,
    *,
    scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Subtract a reference spectrum from a sample spectrum.

    Parameters
    ----------
    x : array-like
        Wavenumber or wavelength.
    sample : array-like
        Sample spectrum.
    reference : array-like
        Reference spectrum.
    scale : float
        Scaling factor for the reference before subtraction.

    Returns
    -------
    (x, difference_spectrum)
    """
    x_arr = np.asarray(x, dtype=float)
    s = np.asarray(sample, dtype=float)
    r = np.asarray(reference, dtype=float)

    if len(s) != len(r):
        # Interpolate reference to match sample x values
        from scripts.analysis.interpolation import interpolate
        _, r = interpolate(x_arr, r, x_arr)

    diff = s - scale * r
    print(f"[Praxis] Spectral subtraction (scale={scale})")
    return x_arr, diff


def atr_correction(
    wavenumber: Any,
    absorbance: Any,
    *,
    n_sample: float = 1.5,
    n_crystal: float = 2.4,
    angle: float = 45.0,
) -> tuple[np.ndarray, np.ndarray]:
    """ATR correction for FTIR spectra.

    Corrects for wavelength-dependent penetration depth in ATR mode.

    Parameters
    ----------
    wavenumber : array-like
        Wavenumber in cm-1.
    absorbance : array-like
        ATR absorbance.
    n_sample : float
        Refractive index of sample.
    n_crystal : float
        Refractive index of ATR crystal (2.4 for diamond, 4.0 for Ge).
    angle : float
        Angle of incidence (degrees).

    Returns
    -------
    (wavenumber, corrected_absorbance)
    """
    wn = np.asarray(wavenumber, dtype=float)
    a = np.asarray(absorbance, dtype=float)

    theta = np.radians(angle)
    # Penetration depth is proportional to 1/wavenumber
    # ATR correction: multiply absorbance by wavenumber
    dp_factor = wn / wn.max()  # normalised correction factor
    corrected = a * dp_factor

    print("[Praxis] ATR correction applied")
    return wn, corrected
