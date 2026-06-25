"""Chromatography peak analysis: GC, HPLC, IC, SEC.

Peak detection, integration, plate count, resolution, asymmetry,
and calibration curves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
from scipy.signal import find_peaks as scipy_find_peaks

from scripts.core.utils import validate_xy, validate_array
from scripts.analysis.fitting import fit_curve


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ChromPeak:
    """A chromatographic peak."""
    retention_time: float         # minutes
    area: float                   # integrated area
    height: float                 # peak height
    width: float                  # peak width at base (min)
    width_half: float             # peak width at half height (min)
    plate_count: float            # theoretical plates (N)
    asymmetry: float              # asymmetry factor
    resolution_next: Optional[float] = None  # resolution to next peak


@dataclass
class ChromResults:
    """Full chromatogram analysis results."""
    peaks: list[ChromPeak] = field(default_factory=list)
    total_area: float = 0.0
    technique: str = "HPLC"

    def table(self) -> str:
        """Formatted results table."""
        lines = [
            f"[Praxis] {self.technique} Chromatogram Analysis -- {len(self.peaks)} peak(s)",
            f"  Total area: {self.total_area:.1f}",
            "",
            f"  {'#':>3}  {'tR (min)':>9}  {'Area':>12}  {'Area%':>7}  "
            f"{'Height':>10}  {'W (min)':>8}  {'W1/2':>8}  {'N':>8}  "
            f"{'As':>6}  {'Rs':>6}",
            "  " + "-" * 95,
        ]
        for i, p in enumerate(self.peaks, 1):
            area_pct = (p.area / self.total_area * 100) if self.total_area > 0 else 0
            rs = f"{p.resolution_next:.2f}" if p.resolution_next is not None else "--"
            lines.append(
                f"  {i:>3}  {p.retention_time:>9.3f}  {p.area:>12.1f}  "
                f"{area_pct:>6.1f}%  {p.height:>10.1f}  {p.width:>8.3f}  "
                f"{p.width_half:>8.3f}  {p.plate_count:>8.0f}  "
                f"{p.asymmetry:>6.2f}  {rs:>6}"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class CalibrationResult:
    """Linear calibration curve result."""
    slope: float
    intercept: float
    r_squared: float
    unknown_concentration: Optional[float] = None

    def table(self) -> str:
        """Formatted results table."""
        lines = [
            "[Praxis] Calibration Curve",
            f"  Slope     : {self.slope:.6e}",
            f"  Intercept : {self.intercept:.6e}",
            f"  R2        : {self.r_squared:.6f}",
        ]
        if self.unknown_concentration is not None:
            lines.append(f"  Unknown   : {self.unknown_concentration:.4e}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Main analysis functions
# ---------------------------------------------------------------------------

def analyse_chromatogram(
    time: Any,
    signal: Any,
    *,
    technique: str = "HPLC",
    min_peak_height_pct: float = 3.0,
) -> ChromResults:
    """Detect and characterise peaks in a chromatogram.

    Parameters
    ----------
    time : array-like
        Retention time (minutes).
    signal : array-like
        Detector signal (mAU, counts, etc.).
    technique : str
        Chromatographic technique ('HPLC', 'GC', 'IC', 'SEC').
    min_peak_height_pct : float
        Minimum peak height as % of the maximum signal.

    Returns
    -------
    ChromResults
    """
    t = np.asarray(time, dtype=float)
    s = np.asarray(signal, dtype=float)
    t, s = validate_xy(t, s, allow_nan=False)

    # Sort by time
    order = np.argsort(t)
    t = t[order]
    s = s[order]

    # Peak detection
    min_height = np.max(s) * (min_peak_height_pct / 100.0)
    # Estimate minimum distance between peaks (at least 5 data points)
    min_dist = max(5, len(t) // 50)

    peak_idx, props = scipy_find_peaks(
        s, height=min_height, distance=min_dist, prominence=min_height * 0.3,
    )

    if len(peak_idx) == 0:
        result = ChromResults(peaks=[], total_area=0.0, technique=technique)
        print(result.table())
        return result

    # Characterise each peak
    chrom_peaks = []
    dt = np.median(np.diff(t))  # Time step

    for idx in peak_idx:
        height = float(s[idx])
        rt = float(t[idx])

        # Find peak boundaries (walk to baseline)
        left, right = _find_peak_boundaries(s, idx)

        # Peak width at base
        w_base = float(t[right] - t[left]) if right > left else dt

        # Peak width at half height
        w_half = _width_at_half_height(t, s, idx, left, right)

        # Integration (trapezoidal)
        if right > left:
            area = float(np.trapezoid(s[left:right + 1], t[left:right + 1]))
        else:
            area = float(height * dt)

        # Plate count
        n_plates = calc_plate_count(rt, w_base)

        # Asymmetry
        asym = calc_asymmetry(t, s, idx)

        chrom_peaks.append(ChromPeak(
            retention_time=rt,
            area=area,
            height=height,
            width=w_base,
            width_half=w_half,
            plate_count=n_plates,
            asymmetry=asym,
        ))

    # Resolution between adjacent peaks
    for i in range(len(chrom_peaks) - 1):
        p1 = chrom_peaks[i]
        p2 = chrom_peaks[i + 1]
        p1.resolution_next = calc_resolution(
            p1.retention_time, p2.retention_time,
            p1.width, p2.width,
        )

    total_area = sum(p.area for p in chrom_peaks)

    result = ChromResults(
        peaks=chrom_peaks,
        total_area=total_area,
        technique=technique,
    )
    print(result.table())
    return result


def calc_resolution(t1: float, t2: float, w1: float, w2: float) -> float:
    """Resolution between two chromatographic peaks.

    Rs = 2 * (t2 - t1) / (w1 + w2)

    Parameters
    ----------
    t1, t2 : float
        Retention times of peaks 1 and 2.
    w1, w2 : float
        Peak widths at base of peaks 1 and 2.

    Returns
    -------
    float
        Resolution Rs.
    """
    denom = w1 + w2
    if denom <= 0:
        return 0.0
    return 2.0 * abs(t2 - t1) / denom


def calc_plate_count(retention_time: float, peak_width: float) -> float:
    """Theoretical plate count from retention time and peak width at base.

    N = 16 * (tR / w)^2

    Parameters
    ----------
    retention_time : float
        Retention time tR.
    peak_width : float
        Peak width at base w.

    Returns
    -------
    float
        Theoretical plate count N.
    """
    if peak_width <= 0:
        return 0.0
    return 16.0 * (retention_time / peak_width) ** 2


def calc_plate_count_half(retention_time: float, width_half: float) -> float:
    """Theoretical plate count from peak width at half height.

    N = 5.54 * (tR / w_half)^2

    Parameters
    ----------
    retention_time : float
        Retention time tR.
    width_half : float
        Peak width at half height w_1/2.

    Returns
    -------
    float
        Theoretical plate count N.
    """
    if width_half <= 0:
        return 0.0
    return 5.54 * (retention_time / width_half) ** 2


def calc_asymmetry(time: Any, signal: Any, peak_idx: int) -> float:
    """Peak asymmetry factor (tailing factor).

    Measured at 10% of peak height. As = b/a where a is the front half-width
    and b is the back half-width.

    Parameters
    ----------
    time : array-like
        Time array.
    signal : array-like
        Signal array.
    peak_idx : int
        Index of the peak apex.

    Returns
    -------
    float
        Asymmetry factor. 1.0 = perfectly symmetric.
    """
    t = np.asarray(time, dtype=float)
    s = np.asarray(signal, dtype=float)

    peak_height = s[peak_idx]
    threshold = peak_height * 0.10  # 10% height

    # Find front crossing (left side)
    front_t = t[peak_idx]
    for i in range(peak_idx, -1, -1):
        if s[i] < threshold:
            # Interpolate
            if i < peak_idx:
                frac = (threshold - s[i]) / (s[i + 1] - s[i]) if s[i + 1] != s[i] else 0
                front_t = t[i] + frac * (t[i + 1] - t[i])
            break

    # Find back crossing (right side)
    back_t = t[peak_idx]
    for i in range(peak_idx, len(s)):
        if s[i] < threshold:
            if i > peak_idx:
                frac = (threshold - s[i]) / (s[i - 1] - s[i]) if s[i - 1] != s[i] else 0
                back_t = t[i] - frac * (t[i] - t[i - 1])
            break

    a = t[peak_idx] - front_t  # Front half-width
    b = back_t - t[peak_idx]   # Back half-width

    if a <= 0:
        return 1.0
    return b / a


def calibration_curve(
    concentrations: Any,
    areas_or_heights: Any,
    *,
    unknown_area: Optional[float] = None,
) -> CalibrationResult:
    """Build a linear calibration curve and optionally calculate unknown concentration.

    Parameters
    ----------
    concentrations : array-like
        Known concentrations of standards.
    areas_or_heights : array-like
        Corresponding peak areas or heights.
    unknown_area : float, optional
        Area/height of unknown sample. If provided, the unknown
        concentration is calculated from the calibration.

    Returns
    -------
    CalibrationResult
    """
    conc = validate_array(np.asarray(concentrations, dtype=float), "concentrations")
    areas = validate_array(np.asarray(areas_or_heights, dtype=float), "areas_or_heights")

    if len(conc) != len(areas):
        raise ValueError(
            f"concentrations ({len(conc)}) and areas ({len(areas)}) must have the same length."
        )

    if len(conc) < 2:
        raise ValueError("Need at least 2 calibration points.")

    # Linear fit: area = slope * concentration + intercept
    fit = fit_curve(conc, areas, model="linear")
    slope = fit.params.get("slope", 0.0)
    intercept = fit.params.get("intercept", 0.0)
    r_sq = fit.r_squared

    unknown_conc = None
    if unknown_area is not None and slope != 0:
        unknown_conc = (unknown_area - intercept) / slope

    result = CalibrationResult(
        slope=slope,
        intercept=intercept,
        r_squared=r_sq,
        unknown_concentration=unknown_conc,
    )
    print(result.table())
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_peak_boundaries(
    signal: np.ndarray, peak_idx: int
) -> tuple[int, int]:
    """Find left and right boundaries of a peak by walking to baseline."""
    n = len(signal)
    peak_height = signal[peak_idx]
    baseline_threshold = peak_height * 0.01  # 1% of peak height

    # Walk left
    left = peak_idx
    while left > 0:
        if signal[left - 1] < baseline_threshold:
            break
        if signal[left - 1] > signal[left]:
            # Rising again: hit adjacent peak
            break
        left -= 1

    # Walk right
    right = peak_idx
    while right < n - 1:
        if signal[right + 1] < baseline_threshold:
            break
        if signal[right + 1] > signal[right]:
            break
        right += 1

    return left, right


def _width_at_half_height(
    t: np.ndarray, s: np.ndarray, peak_idx: int, left: int, right: int
) -> float:
    """Calculate peak width at half height by interpolation."""
    half_h = s[peak_idx] / 2.0

    # Left crossing
    t_left = t[left]
    for i in range(peak_idx, left - 1, -1):
        if s[i] < half_h:
            if i < peak_idx and s[i + 1] != s[i]:
                frac = (half_h - s[i]) / (s[i + 1] - s[i])
                t_left = t[i] + frac * (t[i + 1] - t[i])
            else:
                t_left = t[i]
            break

    # Right crossing
    t_right = t[right]
    for i in range(peak_idx, right + 1):
        if s[i] < half_h:
            if i > peak_idx and s[i - 1] != s[i]:
                frac = (half_h - s[i]) / (s[i - 1] - s[i])
                t_right = t[i] - frac * (t[i] - t[i - 1])
            else:
                t_right = t[i]
            break

    return max(float(t_right - t_left), 0.0)
