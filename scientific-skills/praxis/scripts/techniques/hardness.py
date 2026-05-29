"""Macro and micro hardness testing: Vickers, Brinell, Rockwell, and Knoop.

Includes inter-scale conversion (ASTM E140 approximate) and statistical
analysis of indent arrays.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np

from scripts.core.utils import validate_array


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Gravity for kgf -> N conversion
G = 9.80665  # m/s^2


# ---------------------------------------------------------------------------
# ASTM E140 approximate conversion table (for steels)
# Format: (HV, HRC, HRB, HBW)
# None = no valid conversion at that level.
# ---------------------------------------------------------------------------

_CONVERSION_TABLE: list[tuple[float, Optional[float], Optional[float], Optional[float]]] = [
    (940, 68.0, None, None),
    (900, 67.0, None, None),
    (865, 66.0, None, None),
    (832, 65.0, None, None),
    (800, 64.0, None, None),
    (772, 63.0, None, None),
    (746, 62.0, None, None),
    (720, 61.0, None, None),
    (697, 60.0, None, None),
    (674, 59.0, None, None),
    (653, 58.0, None, None),
    (633, 57.0, None, None),
    (613, 56.0, None, None),
    (595, 55.0, None, None),
    (577, 54.0, None, None),
    (560, 53.0, None, None),
    (544, 52.0, None, None),
    (528, 51.0, None, None),
    (513, 50.0, None, None),
    (498, 49.0, None, None),
    (484, 48.0, None, None),
    (471, 47.0, None, None),
    (458, 46.0, None, None),
    (446, 45.0, None, None),
    (434, 44.0, None, None),
    (423, 43.0, None, None),
    (412, 42.0, None, None),
    (402, 41.0, None, None),
    (392, 40.0, None, None),
    (382, 39.0, None, None),
    (372, 38.0, None, None),
    (363, 37.0, None, None),
    (354, 36.0, None, None),
    (345, 35.0, None, None),
    (336, 34.0, None, None),
    (327, 33.0, None, None),
    (318, 32.0, None, None),
    (310, 31.0, None, None),
    (302, 30.0, None, None),
    (294, 29.0, None, None),
    (286, 28.0, None, None),
    (279, 27.0, None, None),
    (272, 26.0, None, None),
    (266, 25.0, None, None),
    (260, 24.0, 100.0, 247),
    (254, 23.0, 99.0, 243),
    (248, 22.0, 98.5, 237),
    (243, 21.0, 97.8, 232),
    (238, 20.0, 97.0, 228),
    (228, 18.0, 95.5, 219),
    (219, 16.0, 93.5, 212),
    (209, 14.0, 91.5, 203),
    (200, 12.0, 89.5, 195),
    (190, 10.0, 87.0, 185),
    (181, 8.0, 85.0, 176),
    (171, 6.0, 82.0, 167),
    (162, 4.0, 79.0, 158),
    (153, 2.0, 76.0, 149),
    (144, 0.0, 72.0, 140),
    (137, None, 69.0, 133),
    (131, None, 67.0, 127),
    (126, None, 65.0, 122),
    (121, None, 63.0, 117),
    (116, None, 60.0, 113),
    (111, None, 57.5, 108),
    (107, None, 55.0, 104),
    (103, None, 52.0, 100),
    (99, None, 49.0, 96),
    (95, None, 46.0, 92),
]

# Build lookup dicts for interpolation
_HV_VALUES = np.array([row[0] for row in _CONVERSION_TABLE], dtype=float)
_HRC_VALUES = np.array([row[1] if row[1] is not None else np.nan for row in _CONVERSION_TABLE])
_HRB_VALUES = np.array([row[2] if row[2] is not None else np.nan for row in _CONVERSION_TABLE])
_HBW_VALUES = np.array([row[3] if row[3] is not None else np.nan for row in _CONVERSION_TABLE])

_SCALE_ARRAYS: dict[str, np.ndarray] = {
    "HV": _HV_VALUES,
    "HRC": _HRC_VALUES,
    "HRB": _HRB_VALUES,
    "HBW": _HBW_VALUES,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class HardnessResult:
    """Result of a single hardness measurement."""
    value: float
    scale: str  # e.g. "HV", "HRC", "HBW", "HK"
    load: float  # test load (kgf or N, as provided)
    method_details: str = ""

    def __repr__(self) -> str:
        return f"{self.value:.1f} {self.scale} (load={self.load}, {self.method_details})"


@dataclass
class HardnessStatsResult:
    """Statistical summary of multiple hardness measurements."""
    mean: float
    std: float
    cv_pct: float  # coefficient of variation (%)
    n: int
    min: float
    max: float
    outliers: list[float] = field(default_factory=list)

    def table(self) -> str:
        lines = [
            f"[Praxis] Hardness Statistics -- n = {self.n}",
            "  " + "-" * 40,
            f"  Mean:   {self.mean:.1f}",
            f"  Std:    {self.std:.1f}",
            f"  CV:     {self.cv_pct:.1f}%",
            f"  Min:    {self.min:.1f}",
            f"  Max:    {self.max:.1f}",
        ]
        if self.outliers:
            out_str = ", ".join(f"{v:.1f}" for v in self.outliers)
            lines.append(f"  Outliers ({len(self.outliers)}): {out_str}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Hardness calculations
# ---------------------------------------------------------------------------

def vickers_hardness(
    load_kgf: float,
    diagonal_mm: float,
    *,
    load_in_newtons: bool = False,
) -> HardnessResult:
    """Calculate Vickers hardness number.

    HV = 1.8544 * F / d^2

    Parameters
    ----------
    load_kgf : float
        Test load in kgf (or N if load_in_newtons=True).
    diagonal_mm : float
        Mean diagonal length of the indent in mm.
    load_in_newtons : bool
        If True, load is in Newtons (converted to kgf internally).

    Returns
    -------
    HardnessResult
    """
    if diagonal_mm <= 0:
        raise ValueError(f"Diagonal must be positive, got {diagonal_mm}.")

    load = load_kgf
    if load_in_newtons:
        load = load_kgf / G

    hv = 1.8544 * load / (diagonal_mm ** 2)

    result = HardnessResult(
        value=float(hv),
        scale="HV",
        load=load,
        method_details=f"d = {diagonal_mm:.4f} mm",
    )
    print(f"[Praxis] Vickers: {hv:.1f} HV (load = {load:.2f} kgf, d = {diagonal_mm:.4f} mm)")
    return result


def brinell_hardness(
    load_kgf: float,
    ball_diameter_mm: float,
    indent_diameter_mm: float,
) -> HardnessResult:
    """Calculate Brinell hardness number.

    HBW = 2F / (pi * D * (D - sqrt(D^2 - d^2)))

    Parameters
    ----------
    load_kgf : float
        Test load in kgf.
    ball_diameter_mm : float
        Ball indenter diameter (mm).
    indent_diameter_mm : float
        Indent diameter (mm).

    Returns
    -------
    HardnessResult
    """
    D = ball_diameter_mm
    d = indent_diameter_mm

    if d <= 0 or D <= 0:
        raise ValueError("Diameters must be positive.")
    if d >= D:
        raise ValueError(f"Indent diameter ({d}) must be less than ball diameter ({D}).")

    inner = math.sqrt(D ** 2 - d ** 2)
    denominator = math.pi * D * (D - inner)

    if denominator <= 0:
        raise ValueError("Invalid geometry: denominator is zero or negative.")

    hbw = (2.0 * load_kgf) / denominator

    result = HardnessResult(
        value=float(hbw),
        scale="HBW",
        load=load_kgf,
        method_details=f"D = {D:.2f} mm, d = {d:.3f} mm",
    )
    print(f"[Praxis] Brinell: {hbw:.1f} HBW (load = {load_kgf:.1f} kgf, D = {D:.2f} mm, d = {d:.3f} mm)")
    return result


def rockwell_hardness(
    depth_mm: float,
    *,
    scale: str = "C",
) -> HardnessResult:
    """Convert penetration depth to Rockwell hardness number.

    Scale C (150 kgf, diamond cone):  HRC = 100 - depth_mm / 0.002
    Scale A (60 kgf, diamond cone):   HRA = 100 - depth_mm / 0.002
    Scale B (100 kgf, 1/16" ball):    HRB = 130 - depth_mm / 0.002

    Here depth_mm is the residual depth increment (in mm) beyond the
    minor-load reference.

    Parameters
    ----------
    depth_mm : float
        Residual penetration depth increment in mm.
    scale : str
        Rockwell scale: 'A', 'B', or 'C'.

    Returns
    -------
    HardnessResult
    """
    scale = scale.upper()

    # Each unit of Rockwell = 0.002 mm of depth
    depth_units = depth_mm / 0.002

    if scale in ("C", "A"):
        hr = 100.0 - depth_units
        load = 150.0 if scale == "C" else 60.0
    elif scale == "B":
        hr = 130.0 - depth_units
        load = 100.0
    else:
        raise ValueError(f"Unknown Rockwell scale: {scale}. Use A, B, or C.")

    scale_name = f"HR{scale}"
    result = HardnessResult(
        value=float(hr),
        scale=scale_name,
        load=load,
        method_details=f"depth = {depth_mm:.4f} mm",
    )
    print(f"[Praxis] Rockwell: {hr:.1f} {scale_name} (depth = {depth_mm:.4f} mm)")
    return result


def knoop_hardness(
    load_kgf: float,
    long_diagonal_mm: float,
) -> HardnessResult:
    """Calculate Knoop hardness number.

    HK = 14.229 * F / d^2

    Parameters
    ----------
    load_kgf : float
        Test load in kgf.
    long_diagonal_mm : float
        Long diagonal of the Knoop indent in mm.

    Returns
    -------
    HardnessResult
    """
    if long_diagonal_mm <= 0:
        raise ValueError(f"Diagonal must be positive, got {long_diagonal_mm}.")

    hk = 14.229 * load_kgf / (long_diagonal_mm ** 2)

    result = HardnessResult(
        value=float(hk),
        scale="HK",
        load=load_kgf,
        method_details=f"d = {long_diagonal_mm:.4f} mm",
    )
    print(f"[Praxis] Knoop: {hk:.1f} HK (load = {load_kgf:.3f} kgf, d = {long_diagonal_mm:.4f} mm)")
    return result


# ---------------------------------------------------------------------------
# Hardness conversion (ASTM E140 approximate, for steels)
# ---------------------------------------------------------------------------

def convert_hardness(
    value: float,
    from_scale: str,
    to_scale: str,
) -> float:
    """Approximate hardness conversion between scales.

    Uses ASTM E140 conversion table with linear interpolation.
    Supported scales: HV, HRC, HRB, HBW.

    Parameters
    ----------
    value : float
        Hardness value in the source scale.
    from_scale : str
        Source scale (e.g. 'HV', 'HRC').
    to_scale : str
        Target scale.

    Returns
    -------
    float
        Converted hardness value.
    """
    from_scale = from_scale.upper()
    to_scale = to_scale.upper()

    if from_scale == to_scale:
        return value

    if from_scale not in _SCALE_ARRAYS:
        raise ValueError(f"Unknown scale: {from_scale}. Use HV, HRC, HRB, or HBW.")
    if to_scale not in _SCALE_ARRAYS:
        raise ValueError(f"Unknown scale: {to_scale}. Use HV, HRC, HRB, or HBW.")

    src = _SCALE_ARRAYS[from_scale]
    dst = _SCALE_ARRAYS[to_scale]

    # Find valid entries (not NaN in both source and destination)
    valid = ~(np.isnan(src) | np.isnan(dst))
    src_valid = src[valid]
    dst_valid = dst[valid]

    if len(src_valid) < 2:
        raise ValueError(f"Not enough conversion data for {from_scale} -> {to_scale}.")

    # Check range
    src_min, src_max = float(np.nanmin(src_valid)), float(np.nanmax(src_valid))
    if value < src_min or value > src_max:
        raise ValueError(
            f"{value} {from_scale} is outside conversion range [{src_min:.0f}, {src_max:.0f}]."
        )

    # Interpolate (src may be in descending order, so sort first)
    order = np.argsort(src_valid)
    converted = float(np.interp(value, src_valid[order], dst_valid[order]))

    print(f"[Praxis] Hardness conversion: {value:.1f} {from_scale} -> {converted:.1f} {to_scale}")
    return converted


# ---------------------------------------------------------------------------
# Statistical analysis of indent arrays
# ---------------------------------------------------------------------------

def analyse_indent_array(
    values: Any,
    *,
    scale: str = "HV",
) -> HardnessStatsResult:
    """Statistical analysis of multiple hardness measurements.

    Calculates mean, standard deviation, coefficient of variation,
    and detects outliers using Chauvenet's criterion.

    Parameters
    ----------
    values : array-like
        Array of hardness values.
    scale : str
        Hardness scale label (for reporting).

    Returns
    -------
    HardnessStatsResult
    """
    arr = validate_array(np.asarray(values, dtype=float), "hardness values")

    n = len(arr)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    cv = (std_val / mean_val * 100.0) if mean_val != 0 else 0.0

    # Chauvenet's criterion for outlier detection
    outliers: list[float] = []
    if n >= 4 and std_val > 0:
        from scipy.special import erfc
        # Maximum allowed deviation: P(|x - mean| > d) < 1/(2n)
        threshold_prob = 1.0 / (2.0 * n)
        for v in arr:
            z = abs(v - mean_val) / std_val
            # Two-tailed probability
            prob = erfc(z / math.sqrt(2.0))
            if prob < threshold_prob:
                outliers.append(float(v))

    result = HardnessStatsResult(
        mean=mean_val,
        std=std_val,
        cv_pct=cv,
        n=n,
        min=float(np.min(arr)),
        max=float(np.max(arr)),
        outliers=outliers,
    )

    print(result.table())
    return result
