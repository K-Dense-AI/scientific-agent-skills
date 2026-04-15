"""Peak detection, fitting, deconvolution, FWHM, and area integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np
from scipy.signal import find_peaks
from scipy.integrate import trapezoid

from scripts.core.utils import validate_xy


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Peak:
    """Represents a detected peak."""
    index: int
    position: float
    height: float
    fwhm: Optional[float] = None
    area: Optional[float] = None
    prominence: Optional[float] = None
    left_base: Optional[float] = None
    right_base: Optional[float] = None


@dataclass
class PeakResults:
    """Collection of detected peaks with summary methods."""
    peaks: list[Peak] = field(default_factory=list)
    x: Optional[np.ndarray] = None
    y: Optional[np.ndarray] = None

    @property
    def positions(self) -> np.ndarray:
        return np.array([p.position for p in self.peaks])

    @property
    def heights(self) -> np.ndarray:
        return np.array([p.height for p in self.peaks])

    @property
    def n_peaks(self) -> int:
        return len(self.peaks)

    def table(self) -> str:
        """Formatted table of peak parameters."""
        lines = [
            f"[Praxis] Found {self.n_peaks} peak(s)",
            f"  {'#':>3}  {'Position':>12}  {'Height':>12}  {'FWHM':>10}  {'Area':>12}  {'Prominence':>12}",
            "  " + "-" * 70,
        ]
        for i, p in enumerate(self.peaks, 1):
            fwhm_str = f"{p.fwhm:.4f}" if p.fwhm is not None else "—"
            area_str = f"{p.area:.4e}" if p.area is not None else "—"
            prom_str = f"{p.prominence:.4e}" if p.prominence is not None else "—"
            lines.append(
                f"  {i:>3}  {p.position:>12.4f}  {p.height:>12.4e}  {fwhm_str:>10}  {area_str:>12}  {prom_str:>12}"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Peak detection
# ---------------------------------------------------------------------------

def find_peaks_auto(
    x: Any,
    y: Any,
    *,
    height: Optional[float] = None,
    threshold: Optional[float] = None,
    distance: Optional[int] = None,
    prominence: Optional[float] = None,
    width: Optional[float] = None,
    rel_height: float = 0.5,
    min_height_pct: float = 5.0,
    calc_fwhm: bool = True,
    calc_area: bool = True,
) -> PeakResults:
    """Detect peaks in y(x) data.

    Parameters
    ----------
    x, y : array-like
        Data arrays.
    height : float, optional
        Minimum peak height (absolute). If None, uses *min_height_pct*.
    threshold : float, optional
        Minimum difference to neighbouring samples.
    distance : int, optional
        Minimum samples between peaks.
    prominence : float, optional
        Minimum prominence.
    width : float, optional
        Minimum peak width in samples.
    rel_height : float
        Relative height at which FWHM is measured (0.5 = half max).
    min_height_pct : float
        Minimum peak height as percentage of data range (used if *height* is None).
    calc_fwhm : bool
        Calculate FWHM for each peak.
    calc_area : bool
        Calculate integrated area for each peak.

    Returns
    -------
    PeakResults
    """
    x, y = validate_xy(np.asarray(x, dtype=float), np.asarray(y, dtype=float), allow_nan=False)

    # Default height threshold
    if height is None:
        y_range = y.max() - y.min()
        height = y.min() + (min_height_pct / 100) * y_range

    # Default distance: at least 3 points
    if distance is None:
        distance = max(3, len(x) // 100)

    indices, properties = find_peaks(
        y,
        height=height,
        threshold=threshold,
        distance=distance,
        prominence=prominence,
        width=width,
        rel_height=rel_height,
    )

    # Build Peak objects
    peaks = []
    for i, idx in enumerate(indices):
        p = Peak(
            index=idx,
            position=x[idx],
            height=y[idx],
        )

        if "prominences" in properties:
            p.prominence = properties["prominences"][i]
        if "left_bases" in properties:
            p.left_base = x[properties["left_bases"][i]]
        if "right_bases" in properties:
            p.right_base = x[properties["right_bases"][i]]

        if calc_fwhm:
            p.fwhm = _calc_fwhm(x, y, idx, rel_height)

        if calc_area:
            p.area = _calc_peak_area(x, y, idx, properties, i)

        peaks.append(p)

    # Sort by position
    peaks.sort(key=lambda p: p.position)

    result = PeakResults(peaks=peaks, x=x, y=y)
    print(result.table())
    return result


# ---------------------------------------------------------------------------
# FWHM calculation
# ---------------------------------------------------------------------------

def _calc_fwhm(
    x: np.ndarray, y: np.ndarray, peak_idx: int, rel_height: float = 0.5
) -> Optional[float]:
    """Calculate FWHM by interpolation at rel_height of peak above baseline."""
    peak_val = y[peak_idx]

    # Estimate local baseline from nearby minima
    search_range = max(5, len(x) // 20)
    left_idx = max(0, peak_idx - search_range)
    right_idx = min(len(x), peak_idx + search_range)
    baseline = min(y[left_idx:peak_idx].min() if peak_idx > left_idx else y[peak_idx],
                   y[peak_idx:right_idx].min() if right_idx > peak_idx else y[peak_idx])

    target = baseline + rel_height * (peak_val - baseline)

    # Search left
    left_x = None
    for i in range(peak_idx, left_idx, -1):
        if y[i] <= target:
            # Interpolate
            if i < peak_idx:
                frac = (target - y[i]) / (y[i + 1] - y[i]) if y[i + 1] != y[i] else 0
                left_x = x[i] + frac * (x[i + 1] - x[i])
            break

    # Search right
    right_x = None
    for i in range(peak_idx, right_idx):
        if y[i] <= target:
            if i > peak_idx:
                frac = (target - y[i]) / (y[i - 1] - y[i]) if y[i - 1] != y[i] else 0
                right_x = x[i] + frac * (x[i - 1] - x[i])
            break

    if left_x is not None and right_x is not None:
        return abs(right_x - left_x)
    return None


# ---------------------------------------------------------------------------
# Peak area integration
# ---------------------------------------------------------------------------

def _calc_peak_area(
    x: np.ndarray,
    y: np.ndarray,
    peak_idx: int,
    properties: dict,
    prop_idx: int,
) -> Optional[float]:
    """Integrate peak area using trapezoidal rule between base points."""
    # Use peak base indices if available
    if "left_bases" in properties and "right_bases" in properties:
        left = properties["left_bases"][prop_idx]
        right = properties["right_bases"][prop_idx]
    else:
        # Estimate: search for local minima either side
        search = max(5, len(x) // 20)
        left = max(0, peak_idx - search)
        right = min(len(x) - 1, peak_idx + search)

    if left >= right:
        return None

    segment_x = x[left:right + 1]
    segment_y = y[left:right + 1]

    # Subtract baseline (linear between endpoints)
    baseline = np.interp(segment_x, [segment_x[0], segment_x[-1]], [segment_y[0], segment_y[-1]])
    corrected = segment_y - baseline

    return float(trapezoid(corrected, segment_x))


# ---------------------------------------------------------------------------
# Peak deconvolution (multi-peak fit)
# ---------------------------------------------------------------------------

def deconvolve_peaks(
    x: Any,
    y: Any,
    n_peaks: Optional[int] = None,
    *,
    peak_positions: Optional[Sequence[float]] = None,
    model: str = "gaussian",
    background: str = "constant",
) -> Any:
    """Fit multiple overlapping peaks by deconvolution.

    Parameters
    ----------
    x, y : array-like
    n_peaks : int, optional
        Number of peaks. Auto-detected if None.
    peak_positions : list of float, optional
        Approximate peak centres.
    model : str
        Peak shape: 'gaussian', 'lorentzian', 'voigt', 'pseudo_voigt'.
    background : str
        Background model: 'constant', 'linear', 'polynomial'.

    Returns
    -------
    lmfit ModelResult
    """
    from lmfit.models import (
        GaussianModel, LorentzianModel, VoigtModel, PseudoVoigtModel,
        ConstantModel, LinearModel, PolynomialModel,
    )

    x, y = validate_xy(np.asarray(x, dtype=float), np.asarray(y, dtype=float), allow_nan=False)

    # Auto-detect peaks if needed
    if peak_positions is None:
        result = find_peaks_auto(x, y, calc_fwhm=False, calc_area=False)
        peak_positions = result.positions.tolist()
        if n_peaks is not None and len(peak_positions) > n_peaks:
            # Keep the n_peaks most prominent
            sorted_peaks = sorted(result.peaks, key=lambda p: p.height, reverse=True)
            peak_positions = [p.position for p in sorted_peaks[:n_peaks]]
    elif n_peaks is not None:
        peak_positions = peak_positions[:n_peaks]

    if not peak_positions:
        raise ValueError("No peaks detected or specified.")

    # Build composite model
    model_classes = {
        "gaussian": GaussianModel,
        "lorentzian": LorentzianModel,
        "voigt": VoigtModel,
        "pseudo_voigt": PseudoVoigtModel,
    }
    PeakModel = model_classes.get(model)
    if PeakModel is None:
        raise ValueError(f"Unknown peak model: {model}. Use gaussian, lorentzian, voigt, pseudo_voigt.")

    # Background
    if background == "constant":
        composite = ConstantModel(prefix="bkg_")
    elif background == "linear":
        composite = LinearModel(prefix="bkg_")
    elif background == "polynomial":
        composite = PolynomialModel(degree=2, prefix="bkg_")
    else:
        composite = ConstantModel(prefix="bkg_")

    # Add peak components
    for i, pos in enumerate(peak_positions):
        prefix = f"p{i}_"
        peak_model = PeakModel(prefix=prefix)
        composite += peak_model

    params = composite.make_params()

    # Initial guesses for peaks
    for i, pos in enumerate(peak_positions):
        prefix = f"p{i}_"
        if f"{prefix}center" in params:
            params[f"{prefix}center"].set(value=pos)
        if f"{prefix}sigma" in params:
            params[f"{prefix}sigma"].set(value=(x.max() - x.min()) / (10 * len(peak_positions)), min=0)
        if f"{prefix}amplitude" in params:
            idx = np.argmin(np.abs(x - pos))
            params[f"{prefix}amplitude"].set(value=max(y[idx] - np.min(y), 1e-10), min=0)

    # Background initial guess
    if "bkg_c" in params:
        params["bkg_c"].set(value=np.min(y))

    result = composite.fit(y, params, x=x)

    n = len(peak_positions)
    print(f"[Praxis] Deconvolved {n} peaks ({model}), R² = {1 - result.residual.var() / y.var():.4f}")

    return result
