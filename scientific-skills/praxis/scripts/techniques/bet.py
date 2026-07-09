"""BET (Brunauer-Emmett-Teller) surface area and pore analysis.

BET surface area from nitrogen adsorption isotherms, BJH pore size
distribution, isotherm classification (IUPAC I-VI), and total pore volume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from scripts.core.utils import validate_xy, validate_array


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_A = 6.022e23  # Avogadro's number (mol-1)

# Molar volumes at STP (cm3/mol)
MOLAR_VOLUME_STP = 22414.0

# Default adsorbate cross-sectional areas (m2)
CROSS_SECTIONS = {
    "N2": 0.162e-18,
    "Ar": 0.142e-18,
    "Kr": 0.202e-18,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BETResult:
    """Results from BET surface area analysis."""
    surface_area_m2g: float       # Specific surface area (m2/g)
    bet_constant_c: float         # BET constant C
    monolayer_capacity: float     # Monolayer capacity Wm (cm3/g STP)
    r_squared: float              # R2 of the BET linear fit
    p_p0_range: tuple[float, float]  # P/P0 range used for fitting

    def table(self) -> str:
        """Formatted results table."""
        lines = [
            "[Praxis] BET Surface Area Analysis",
            f"  P/P0 range      : {self.p_p0_range[0]:.3f} - {self.p_p0_range[1]:.3f}",
            f"  Surface area    : {self.surface_area_m2g:.2f} m2/g",
            f"  BET constant C  : {self.bet_constant_c:.1f}",
            f"  Monolayer Wm    : {self.monolayer_capacity:.4f} cm3/g STP",
            f"  R2              : {self.r_squared:.6f}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class PoreDistribution:
    """Results from BJH pore size distribution analysis."""
    diameters: np.ndarray         # Pore diameters (nm)
    dv_dd: np.ndarray             # dV/dD (cm3/g/nm)
    mean_pore_diameter: float     # Mean pore diameter (nm)
    total_pore_volume: float      # Total pore volume (cm3/g)

    def table(self) -> str:
        """Formatted results table."""
        lines = [
            "[Praxis] BJH Pore Size Distribution",
            f"  Mean pore diameter  : {self.mean_pore_diameter:.2f} nm",
            f"  Total pore volume   : {self.total_pore_volume:.4f} cm3/g",
            f"  Diameter range      : {self.diameters.min():.1f} - {self.diameters.max():.1f} nm",
            f"  Number of points    : {len(self.diameters)}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# Main analysis functions
# ---------------------------------------------------------------------------

def analyse_bet(
    relative_pressure: Any,
    quantity_adsorbed: Any,
    *,
    adsorbate: str = "N2",
    temperature: float = 77.35,
    cross_section: float = 0.162e-18,
) -> BETResult:
    """BET analysis: extract specific surface area, BET constant, monolayer capacity.

    Applies the BET equation in the 0.05-0.35 P/P0 range:
        1 / [W((P0/P) - 1)] = 1/(Wm*C) + (C-1)/(Wm*C) * (P/P0)

    Parameters
    ----------
    relative_pressure : array-like
        Relative pressure P/P0 values.
    quantity_adsorbed : array-like
        Quantity adsorbed W (cm3/g STP).
    adsorbate : str
        Adsorbate gas name. Used to look up cross-sectional area if
        cross_section is not explicitly provided.
    temperature : float
        Analysis temperature in K (default 77.35 K for liquid N2).
    cross_section : float
        Adsorbate molecular cross-sectional area in m2.

    Returns
    -------
    BETResult
    """
    p_p0 = np.asarray(relative_pressure, dtype=float)
    w = np.asarray(quantity_adsorbed, dtype=float)
    p_p0, w = validate_xy(p_p0, w, allow_nan=False)

    # Look up cross section from adsorbate name if default
    if adsorbate in CROSS_SECTIONS and cross_section == 0.162e-18:
        cross_section = CROSS_SECTIONS[adsorbate]

    # Select BET range: 0.05 <= P/P0 <= 0.35
    mask = (p_p0 >= 0.05) & (p_p0 <= 0.35)
    p_sel = p_p0[mask]
    w_sel = w[mask]

    if len(p_sel) < 3:
        raise ValueError(
            f"Only {len(p_sel)} points in the 0.05-0.35 P/P0 range. "
            "Need at least 3 for BET analysis."
        )

    # BET transform: y = 1 / [W * ((P0/P) - 1)] vs x = P/P0
    bet_y = 1.0 / (w_sel * (1.0 / p_sel - 1.0))
    bet_x = p_sel

    # Linear fit: y = slope * x + intercept
    coeffs = np.polyfit(bet_x, bet_y, 1)
    slope, intercept = coeffs

    # R2
    y_fit = np.polyval(coeffs, bet_x)
    ss_res = np.sum((bet_y - y_fit) ** 2)
    ss_tot = np.sum((bet_y - np.mean(bet_y)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Extract BET parameters
    # slope = (C - 1) / (Wm * C)
    # intercept = 1 / (Wm * C)
    if intercept <= 0:
        raise ValueError(
            "BET intercept is non-positive. Check data quality or P/P0 range."
        )

    wm_c = 1.0 / intercept
    c = 1.0 + slope / intercept
    wm = wm_c / c  # Monolayer capacity (cm3/g STP)

    # Surface area: S = (Wm * N_A * cross_section) / molar_volume
    surface_area = (wm * N_A * cross_section) / MOLAR_VOLUME_STP  # m2/g

    p_p0_range = (float(p_sel.min()), float(p_sel.max()))

    result = BETResult(
        surface_area_m2g=surface_area,
        bet_constant_c=c,
        monolayer_capacity=wm,
        r_squared=r_squared,
        p_p0_range=p_p0_range,
    )
    print(result.table())
    return result


def bjh_pore_distribution(
    relative_pressure: Any,
    quantity_adsorbed: Any,
    *,
    branch: str = "desorption",
) -> PoreDistribution:
    """BJH method for pore size distribution.

    Calculate dV/dD vs pore diameter from the desorption (or adsorption)
    branch using the Kelvin equation for pore radius.

    Parameters
    ----------
    relative_pressure : array-like
        Relative pressure P/P0 values.
    quantity_adsorbed : array-like
        Quantity adsorbed (cm3/g STP).
    branch : str
        'desorption' or 'adsorption'. For desorption, data should be in
        decreasing P/P0 order.

    Returns
    -------
    PoreDistribution
    """
    p_p0 = np.asarray(relative_pressure, dtype=float)
    w = np.asarray(quantity_adsorbed, dtype=float)
    p_p0, w = validate_xy(p_p0, w, allow_nan=False)

    # Sort by P/P0 descending for desorption
    if branch == "desorption":
        order = np.argsort(p_p0)[::-1]
    else:
        order = np.argsort(p_p0)
    p_p0 = p_p0[order]
    w = w[order]

    # Filter out P/P0 <= 0 or >= 1
    mask = (p_p0 > 0.01) & (p_p0 < 0.999)
    p_p0 = p_p0[mask]
    w = w[mask]

    if len(p_p0) < 3:
        raise ValueError("Need at least 3 valid data points for BJH analysis.")

    # Kelvin equation: rk = -2 * gamma * Vm / (R * T * ln(P/P0))
    # For N2 at 77 K:
    gamma = 8.88e-3  # Surface tension N2 at 77K (N/m)
    v_m = 34.68e-6   # Molar volume liquid N2 (m3/mol)
    R = 8.314         # Gas constant (J/(mol*K))
    T = 77.35          # Temperature (K)

    # Kelvin radius (m) -> convert to nm
    ln_p = np.log(p_p0)
    # Avoid division by zero
    valid = ln_p < -1e-10
    p_valid = p_p0[valid]
    w_valid = w[valid]
    ln_valid = ln_p[valid]

    rk_m = -2.0 * gamma * v_m / (R * T * ln_valid)
    rk_nm = rk_m * 1e9

    # Statistical thickness (Harkins-Jura): t (nm) = [13.99 / (0.034 - log10(P/P0))]^0.5 * 0.1
    log10_p = np.log10(p_valid)
    denom = 0.034 - log10_p
    denom = np.clip(denom, 1e-10, None)
    t_nm = np.sqrt(13.99 / denom) * 0.1

    # Pore radius = Kelvin radius + statistical thickness
    rp_nm = rk_nm + t_nm
    diameters = 2.0 * rp_nm

    # Convert adsorbed volume to liquid volume (cm3/g)
    # 1 cm3 STP gas = 1.547e-3 cm3 liquid N2
    v_liquid = w_valid * 1.547e-3

    # Incremental pore volume: dV
    dv = -np.diff(v_liquid)  # Negative because desorption decreases
    d_mid = (diameters[:-1] + diameters[1:]) / 2.0
    dd = np.abs(np.diff(diameters))

    # Avoid division by zero
    dd = np.clip(dd, 1e-10, None)
    dv_dd = dv / dd

    # Filter out negative or zero values
    pos_mask = (dv_dd > 0) & (d_mid > 0)
    d_mid = d_mid[pos_mask]
    dv_dd_arr = dv_dd[pos_mask]

    if len(d_mid) == 0:
        raise ValueError("BJH analysis produced no valid pore size data.")

    # Sort by diameter ascending
    sort_idx = np.argsort(d_mid)
    d_mid = d_mid[sort_idx]
    dv_dd_arr = dv_dd_arr[sort_idx]

    # Total pore volume
    total_v = float(np.sum(dv[dv > 0]))

    # Mean pore diameter (weighted by dV/dD)
    if np.sum(dv_dd_arr) > 0:
        mean_d = float(np.sum(d_mid * dv_dd_arr) / np.sum(dv_dd_arr))
    else:
        mean_d = float(np.mean(d_mid))

    result = PoreDistribution(
        diameters=d_mid,
        dv_dd=dv_dd_arr,
        mean_pore_diameter=mean_d,
        total_pore_volume=total_v,
    )
    print(result.table())
    return result


def classify_isotherm(
    relative_pressure: Any,
    quantity_adsorbed: Any,
) -> str:
    """Classify adsorption isotherm type (IUPAC I-VI) based on shape analysis.

    Parameters
    ----------
    relative_pressure : array-like
        Relative pressure P/P0 values.
    quantity_adsorbed : array-like
        Quantity adsorbed.

    Returns
    -------
    str
        Isotherm type as string, e.g. 'Type I', 'Type IV'.
    """
    p_p0 = np.asarray(relative_pressure, dtype=float)
    w = np.asarray(quantity_adsorbed, dtype=float)
    p_p0, w = validate_xy(p_p0, w, allow_nan=False)

    # Sort by P/P0
    order = np.argsort(p_p0)
    p_p0 = p_p0[order]
    w = w[order]

    # Normalise quantity adsorbed
    w_norm = (w - w.min()) / (w.max() - w.min()) if w.max() > w.min() else w * 0

    # Compute first and second derivatives
    dw = np.gradient(w_norm, p_p0)
    d2w = np.gradient(dw, p_p0)

    # Feature extraction
    # 1. Plateau at high P/P0: Type I
    high_region = w_norm[p_p0 > 0.7]
    low_region = w_norm[p_p0 < 0.3]
    mid_region = w_norm[(p_p0 >= 0.3) & (p_p0 <= 0.7)]

    has_plateau = False
    if len(high_region) > 2:
        high_slope = np.mean(np.abs(np.gradient(high_region)))
        has_plateau = high_slope < 0.05

    # 2. Steep uptake at low P/P0
    steep_low = False
    if len(low_region) > 2:
        low_slope = np.mean(dw[p_p0 < 0.3])
        steep_low = low_slope > np.mean(dw) * 1.5

    # 3. Inflection point (Type IV, V characteristic)
    has_inflection = np.any(d2w[:-2] * d2w[2:] < 0)

    # 4. Step-wise behaviour (Type VI)
    if len(d2w) > 5:
        sign_changes = np.sum(np.abs(np.diff(np.sign(d2w))) > 1)
        is_stepwise = sign_changes > 6
    else:
        is_stepwise = False

    # 5. Convex shape at low P/P0 (Type III, V)
    convex_low = False
    if len(low_region) > 2:
        d2w_low = d2w[p_p0 < 0.3]
        convex_low = np.mean(d2w_low) > 0

    # Classification logic
    if is_stepwise:
        iso_type = "Type VI"
    elif steep_low and has_plateau:
        iso_type = "Type I"
    elif steep_low and has_inflection and not has_plateau:
        iso_type = "Type IV"
    elif convex_low and has_inflection:
        iso_type = "Type V"
    elif convex_low and not has_inflection:
        iso_type = "Type III"
    elif not steep_low and not convex_low and not has_plateau:
        iso_type = "Type IV"
    else:
        iso_type = "Type II"

    print(f"[Praxis] Isotherm classification: {iso_type}")
    return iso_type


def total_pore_volume(
    relative_pressure: Any,
    quantity_adsorbed: Any,
    *,
    p_p0_max: float = 0.99,
) -> float:
    """Calculate total pore volume at P/P0 near 1.

    Uses the Gurvich rule: V_pore = V_ads(P/P0 ~ 1) * conversion factor.

    Parameters
    ----------
    relative_pressure : array-like
        Relative pressure P/P0.
    quantity_adsorbed : array-like
        Quantity adsorbed (cm3/g STP).
    p_p0_max : float
        Maximum P/P0 value to use (default 0.99).

    Returns
    -------
    float
        Total pore volume in cm3/g.
    """
    p_p0 = np.asarray(relative_pressure, dtype=float)
    w = np.asarray(quantity_adsorbed, dtype=float)
    p_p0, w = validate_xy(p_p0, w, allow_nan=False)

    # Find the adsorbed volume closest to p_p0_max
    idx = np.argmin(np.abs(p_p0 - p_p0_max))
    v_ads = w[idx]  # cm3/g STP

    # Convert STP gas volume to liquid volume
    # For N2: 1 cm3 STP = 1.547e-3 cm3 liquid
    v_pore = v_ads * 1.547e-3  # cm3/g

    print(f"[Praxis] Total pore volume: {v_pore:.4f} cm3/g (at P/P0 = {p_p0[idx]:.4f})")
    return v_pore
