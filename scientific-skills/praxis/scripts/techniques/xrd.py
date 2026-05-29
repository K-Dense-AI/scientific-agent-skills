"""XRD analysis: peak indexing, Scherrer crystallite size, d-spacing,
Williamson-Hall analysis, and peak deconvolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np

from scripts.core.utils import validate_xy
from scripts.analysis.peaks import find_peaks_auto, PeakResults
from scripts.analysis.fitting import fit_curve


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Common X-ray wavelengths (Å)
WAVELENGTHS = {
    "Cu_Ka": 1.5406,
    "Cu_Ka1": 1.54056,
    "Cu_Ka2": 1.54439,
    "Co_Ka": 1.7889,
    "Mo_Ka": 1.7107,
    "Cr_Ka": 2.2897,
    "Fe_Ka": 1.9373,
    "Ag_Ka": 0.5594,
}

# Scherrer constant (typically 0.89–0.94)
SCHERRER_K = 0.9


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class XRDPeak:
    """An indexed XRD peak."""
    two_theta: float
    d_spacing: float  # Å
    intensity: float
    fwhm: Optional[float] = None  # degrees
    fwhm_rad: Optional[float] = None  # radians
    crystallite_size: Optional[float] = None  # nm (Scherrer)
    hkl: Optional[str] = None
    area: Optional[float] = None


@dataclass
class XRDResults:
    """Full XRD analysis results."""
    peaks: list[XRDPeak] = field(default_factory=list)
    wavelength: float = WAVELENGTHS["Cu_Ka"]
    wavelength_name: str = "Cu Kα"
    wh_slope: Optional[float] = None  # Williamson-Hall strain
    wh_intercept: Optional[float] = None  # Williamson-Hall size
    wh_r_squared: Optional[float] = None

    def table(self) -> str:
        """Formatted results table."""
        lines = [
            f"[Praxis] XRD Analysis -- wavelength = {self.wavelength:.4f} A ({self.wavelength_name})",
            f"  {'#':>3}  {'2th (deg)':>10}  {'d (A)':>10}  {'FWHM (deg)':>10}  {'Size (nm)':>10}  {'Intensity':>12}  {'hkl':>6}",
            "  " + "-" * 72,
        ]
        for i, p in enumerate(self.peaks, 1):
            fwhm = f"{p.fwhm:.4f}" if p.fwhm else "—"
            size = f"{p.crystallite_size:.1f}" if p.crystallite_size else "—"
            hkl = p.hkl or "—"
            lines.append(
                f"  {i:>3}  {p.two_theta:>10.4f}  {p.d_spacing:>10.4f}  {fwhm:>10}  {size:>10}  {p.intensity:>12.1f}  {hkl:>6}"
            )

        if self.wh_slope is not None:
            lines.append("")
            lines.append(f"  Williamson-Hall: strain = {self.wh_slope:.4e}, D = {self.wh_intercept:.1f} nm, R2 = {self.wh_r_squared:.4f}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------

def analyse_xrd(
    two_theta: Any,
    intensity: Any,
    *,
    wavelength: str | float = "Cu_Ka",
    min_height_pct: float = 5.0,
    instrument_broadening: float = 0.0,
    calc_williamson_hall: bool = True,
) -> XRDResults:
    """Full XRD analysis pipeline.

    Parameters
    ----------
    two_theta : array-like
        2θ values in degrees.
    intensity : array-like
        Intensity values.
    wavelength : str or float
        X-ray wavelength. Use name (e.g. 'Cu_Ka') or value in Å.
    min_height_pct : float
        Minimum peak height as % of max intensity.
    instrument_broadening : float
        Instrument contribution to FWHM in degrees (subtracted in quadrature).
    calc_williamson_hall : bool
        Perform Williamson-Hall analysis if enough peaks found.

    Returns
    -------
    XRDResults
    """
    two_theta = np.asarray(two_theta, dtype=float)
    intensity = np.asarray(intensity, dtype=float)
    two_theta, intensity = validate_xy(two_theta, intensity, allow_nan=False)

    # Resolve wavelength
    if isinstance(wavelength, str):
        wl_name = wavelength
        wl = WAVELENGTHS.get(wavelength)
        if wl is None:
            raise ValueError(f"Unknown wavelength: {wavelength}. Available: {', '.join(WAVELENGTHS.keys())}")
    else:
        wl = float(wavelength)
        wl_name = f"{wl:.4f} Å"

    # Detect peaks
    peak_results = find_peaks_auto(
        two_theta, intensity,
        min_height_pct=min_height_pct,
        calc_fwhm=True,
        calc_area=True,
    )

    # Build XRD peaks with d-spacing and crystallite size
    xrd_peaks = []
    for p in peak_results.peaks:
        theta_rad = np.radians(p.position / 2)
        d = calc_d_spacing(p.position, wl)

        xrd_peak = XRDPeak(
            two_theta=p.position,
            d_spacing=d,
            intensity=p.height,
            fwhm=p.fwhm,
            area=p.area,
        )

        if p.fwhm is not None and p.fwhm > 0:
            fwhm_corrected = p.fwhm
            if instrument_broadening > 0:
                fwhm_corrected = np.sqrt(max(p.fwhm**2 - instrument_broadening**2, 0))

            xrd_peak.fwhm_rad = np.radians(fwhm_corrected)

            if fwhm_corrected > 0:
                xrd_peak.crystallite_size = scherrer_size(
                    fwhm_corrected, p.position, wl
                )

        xrd_peaks.append(xrd_peak)

    results = XRDResults(peaks=xrd_peaks, wavelength=wl, wavelength_name=wl_name)

    # Williamson-Hall analysis
    if calc_williamson_hall and len(xrd_peaks) >= 3:
        valid = [p for p in xrd_peaks if p.fwhm_rad is not None and p.fwhm_rad > 0]
        if len(valid) >= 3:
            wh = williamson_hall(valid, wl)
            results.wh_slope = wh["strain"]
            results.wh_intercept = wh["size_nm"]
            results.wh_r_squared = wh["r_squared"]

    print(results.table())
    return results


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def calc_d_spacing(two_theta_deg: float, wavelength: float = WAVELENGTHS["Cu_Ka"]) -> float:
    """Calculate d-spacing from 2θ using Bragg's law: d = λ / (2 sin θ).

    Parameters
    ----------
    two_theta_deg : float
        2θ angle in degrees.
    wavelength : float
        X-ray wavelength in Å.

    Returns
    -------
    float
        d-spacing in Å.
    """
    theta_rad = np.radians(two_theta_deg / 2)
    sin_theta = np.sin(theta_rad)
    if sin_theta <= 0:
        raise ValueError(f"Invalid 2θ = {two_theta_deg}°: sin(θ) must be positive.")
    return wavelength / (2 * sin_theta)


def scherrer_size(
    fwhm_deg: float,
    two_theta_deg: float,
    wavelength: float = WAVELENGTHS["Cu_Ka"],
    K: float = SCHERRER_K,
) -> float:
    """Scherrer crystallite size: D = Kλ / (β cos θ).

    Parameters
    ----------
    fwhm_deg : float
        Peak FWHM in degrees.
    two_theta_deg : float
        Peak position (2θ) in degrees.
    wavelength : float
        X-ray wavelength in Å.
    K : float
        Scherrer constant (0.89–0.94).

    Returns
    -------
    float
        Crystallite size in nm.
    """
    beta_rad = np.radians(fwhm_deg)
    theta_rad = np.radians(two_theta_deg / 2)
    cos_theta = np.cos(theta_rad)

    if beta_rad <= 0 or cos_theta <= 0:
        return 0.0

    # Result in Å, convert to nm
    size_angstrom = (K * wavelength) / (beta_rad * cos_theta)
    return size_angstrom / 10.0  # Å → nm


def williamson_hall(
    peaks: Sequence[XRDPeak],
    wavelength: float = WAVELENGTHS["Cu_Ka"],
    K: float = SCHERRER_K,
) -> dict[str, float]:
    """Williamson-Hall analysis: β cos θ vs 4 sin θ.

    Separates size and strain broadening:
        β cos θ = Kλ/D + 4ε sin θ

    Parameters
    ----------
    peaks : list of XRDPeak
        Peaks with fwhm_rad set.
    wavelength : float
        X-ray wavelength in Å.
    K : float
        Scherrer constant.

    Returns
    -------
    dict with 'strain', 'size_nm', 'r_squared', 'x' (4sinθ), 'y' (βcosθ).
    """
    x_vals = []  # 4 sin θ
    y_vals = []  # β cos θ

    for p in peaks:
        if p.fwhm_rad is None or p.fwhm_rad <= 0:
            continue
        theta = np.radians(p.two_theta / 2)
        x_vals.append(4 * np.sin(theta))
        y_vals.append(p.fwhm_rad * np.cos(theta))

    x = np.array(x_vals)
    y = np.array(y_vals)

    if len(x) < 2:
        raise ValueError("Need at least 2 peaks for Williamson-Hall analysis.")

    # Linear fit: y = slope * x + intercept
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs

    # R²
    y_fit = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_fit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Extract parameters
    strain = slope  # ε = slope / 4, but convention varies
    size_angstrom = K * wavelength / intercept if intercept > 0 else 0
    size_nm = size_angstrom / 10.0

    return {
        "strain": strain,
        "size_nm": size_nm,
        "r_squared": r_squared,
        "x": x,
        "y": y,
    }
