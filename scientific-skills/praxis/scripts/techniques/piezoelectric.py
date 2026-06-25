"""Piezoelectric characterisation.

d33/d31 measurements, P-E hysteresis loops, S-E butterfly curves,
impedance-based resonance (kp, kt, Qm), temperature-dependent depolarisation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
from scipy.signal import find_peaks

from scripts.core.utils import validate_xy, validate_array


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PELoopResults:
    """Results from P-E hysteresis loop analysis."""
    pr: float              # Remanent polarisation (uC/cm2)
    ec: float              # Coercive field (kV/cm)
    ps: Optional[float] = None  # Saturation polarisation
    pr_neg: Optional[float] = None  # Negative remanent
    ec_neg: Optional[float] = None  # Negative coercive
    area: Optional[float] = None    # Loop area (energy loss per cycle)
    e_max: Optional[float] = None   # Maximum applied field

    def table(self) -> str:
        lines = [
            "[Praxis] P-E Hysteresis Loop",
            f"  Pr  = {self.pr:.2f} uC/cm2",
            f"  Ec  = {self.ec:.2f} kV/cm",
        ]
        if self.ps is not None:
            lines.append(f"  Ps  = {self.ps:.2f} uC/cm2")
        if self.pr_neg is not None:
            lines.append(f"  -Pr = {self.pr_neg:.2f} uC/cm2")
        if self.ec_neg is not None:
            lines.append(f"  -Ec = {self.ec_neg:.2f} kV/cm")
        if self.area is not None:
            lines.append(f"  Loop area = {self.area:.4f} (energy loss)")
        if self.e_max is not None:
            lines.append(f"  E_max = {self.e_max:.2f} kV/cm")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class SECurveResults:
    """Results from S-E butterfly curve analysis."""
    d33_eff: Optional[float] = None   # Effective d33 (pm/V)
    s_max: Optional[float] = None     # Maximum strain (%)
    s_neg: Optional[float] = None     # Negative strain
    asymmetry: Optional[float] = None # Strain asymmetry

    def table(self) -> str:
        lines = ["[Praxis] S-E Butterfly Curve"]
        if self.d33_eff is not None:
            lines.append(f"  d33_eff = {self.d33_eff:.1f} pm/V")
        if self.s_max is not None:
            lines.append(f"  S_max   = {self.s_max:.4f}%")
        if self.s_neg is not None:
            lines.append(f"  S_neg   = {self.s_neg:.4f}%")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


@dataclass
class ResonanceResults:
    """Results from impedance resonance analysis."""
    fr: float              # Resonance frequency (Hz)
    fa: float              # Anti-resonance frequency (Hz)
    kp: Optional[float] = None   # Planar coupling factor
    kt: Optional[float] = None   # Thickness coupling factor
    qm: Optional[float] = None   # Mechanical quality factor
    z_min: Optional[float] = None  # Minimum impedance at resonance
    z_max: Optional[float] = None  # Maximum impedance at anti-resonance

    def table(self) -> str:
        lines = [
            "[Praxis] Piezoelectric Resonance",
            f"  fr = {self.fr:.2f} Hz",
            f"  fa = {self.fa:.2f} Hz",
        ]
        if self.kp is not None:
            lines.append(f"  kp = {self.kp:.4f}")
        if self.kt is not None:
            lines.append(f"  kt = {self.kt:.4f}")
        if self.qm is not None:
            lines.append(f"  Qm = {self.qm:.1f}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.table()


# ---------------------------------------------------------------------------
# P-E Hysteresis Loop
# ---------------------------------------------------------------------------

def analyse_pe_loop(
    electric_field: Any,
    polarisation: Any,
) -> PELoopResults:
    """Analyse a polarisation-electric field (P-E) hysteresis loop.

    Parameters
    ----------
    electric_field : array-like
        Electric field in kV/cm.
    polarisation : array-like
        Polarisation in uC/cm2.

    Returns
    -------
    PELoopResults
    """
    e, p = validate_xy(
        np.asarray(electric_field, dtype=float),
        np.asarray(polarisation, dtype=float),
        allow_nan=False,
    )

    # Find positive remanent polarisation (P at E=0, positive branch)
    # Look for zero crossings in E
    zero_crossings_e = np.where(np.diff(np.sign(e)))[0]

    pr_values = []
    ec_values = []

    for idx in zero_crossings_e:
        # Interpolate P at E=0
        if idx + 1 < len(e):
            frac = abs(e[idx]) / (abs(e[idx]) + abs(e[idx + 1])) if (abs(e[idx]) + abs(e[idx + 1])) > 0 else 0.5
            p_at_zero = p[idx] + frac * (p[idx + 1] - p[idx])
            pr_values.append(p_at_zero)

    # Find coercive field (E at P=0)
    zero_crossings_p = np.where(np.diff(np.sign(p)))[0]

    for idx in zero_crossings_p:
        if idx + 1 < len(p):
            frac = abs(p[idx]) / (abs(p[idx]) + abs(p[idx + 1])) if (abs(p[idx]) + abs(p[idx + 1])) > 0 else 0.5
            e_at_zero = e[idx] + frac * (e[idx + 1] - e[idx])
            ec_values.append(e_at_zero)

    # Remanent polarisation: positive and negative
    pr_pos = max(pr_values) if pr_values else abs(p[np.argmin(np.abs(e))])
    pr_neg = min(pr_values) if pr_values else -pr_pos

    # Coercive field: positive and negative
    ec_pos = max(ec_values) if ec_values else 0
    ec_neg = min(ec_values) if ec_values else 0

    # Saturation polarisation
    ps = max(abs(p.max()), abs(p.min()))

    # Loop area (energy dissipated per cycle)
    from scipy.integrate import trapezoid
    area = abs(trapezoid(p, e))

    results = PELoopResults(
        pr=abs(pr_pos),
        ec=abs(ec_pos),
        ps=ps,
        pr_neg=pr_neg,
        ec_neg=ec_neg,
        area=area,
        e_max=abs(e).max(),
    )

    print(results.table())
    return results


# ---------------------------------------------------------------------------
# S-E Butterfly Curve
# ---------------------------------------------------------------------------

def analyse_se_curve(
    electric_field: Any,
    strain: Any,
    *,
    thickness: Optional[float] = None,
) -> SECurveResults:
    """Analyse a strain-electric field (S-E) butterfly curve.

    Parameters
    ----------
    electric_field : array-like
        Electric field in kV/cm.
    strain : array-like
        Strain in % or ppm.
    thickness : float, optional
        Sample thickness in mm (for d33 calculation).

    Returns
    -------
    SECurveResults
    """
    e, s = validate_xy(
        np.asarray(electric_field, dtype=float),
        np.asarray(strain, dtype=float),
        allow_nan=False,
    )

    results = SECurveResults()
    results.s_max = s.max()
    results.s_neg = s.min()

    # Effective d33 from slope at high field
    # d33 = dS/dE (in the linear unipolar region)
    if thickness is not None:
        # d33 = S_max * thickness / E_max (approximate)
        e_max = np.max(np.abs(e))
        if e_max > 0:
            # Convert: strain (%) * thickness (mm) / field (kV/cm) -> pm/V
            results.d33_eff = (results.s_max / 100) * (thickness * 1e6) / (e_max * 1e5)

    # Asymmetry
    if results.s_max and results.s_neg:
        results.asymmetry = abs(results.s_max) / abs(results.s_neg) if results.s_neg != 0 else None

    print(results.table())
    return results


# ---------------------------------------------------------------------------
# Impedance Resonance Analysis
# ---------------------------------------------------------------------------

def analyse_resonance(
    frequency: Any,
    impedance: Any,
    *,
    phase: Optional[Any] = None,
    capacitance_free: Optional[float] = None,
    density: Optional[float] = None,
    dimensions: Optional[dict[str, float]] = None,
) -> ResonanceResults:
    """Analyse impedance resonance for piezoelectric parameters.

    Parameters
    ----------
    frequency : array-like
        Frequency in Hz.
    impedance : array-like
        |Z| in ohms.
    phase : array-like, optional
        Phase angle in degrees.
    capacitance_free : float, optional
        Free capacitance (F) for coupling factor calculation.
    density : float, optional
        Density (kg/m3) for elastic constant calculation.
    dimensions : dict, optional
        Sample dimensions {'diameter': mm, 'thickness': mm} or similar.

    Returns
    -------
    ResonanceResults
    """
    freq = validate_array(frequency, "frequency")
    z = validate_array(impedance, "impedance")

    # Find resonance (impedance minimum) and anti-resonance (impedance maximum)
    z_min_idx = np.argmin(z)
    z_max_idx = np.argmax(z)

    # Ensure fr < fa
    fr_idx = min(z_min_idx, z_max_idx)
    fa_idx = max(z_min_idx, z_max_idx)

    # Refine: fr is minimum, fa is maximum in the resonance region
    if z[fr_idx] > z[fa_idx]:
        fr_idx, fa_idx = fa_idx, fr_idx

    fr = freq[fr_idx]
    fa = freq[fa_idx]

    results = ResonanceResults(
        fr=fr, fa=fa,
        z_min=z[fr_idx],
        z_max=z[fa_idx],
    )

    # Planar coupling factor (for disc)
    # kp^2 = (fa^2 - fr^2) / fa^2 * correction
    # Simplified: kp = sqrt(2 * (fa - fr) / fr) * correction factor
    if fa > fr:
        delta_f = fa - fr
        # IEEE standard approximation
        kp_sq = 2.51 * (fa - fr) / fr  # Approximate for thin disc
        if 0 < kp_sq < 1:
            results.kp = np.sqrt(kp_sq)

        # Thickness coupling
        kt_sq = (np.pi / 2) * (fr / fa) * np.tan((np.pi / 2) * (1 - fr / fa))
        if 0 < kt_sq < 1:
            results.kt = np.sqrt(kt_sq)

    # Mechanical quality factor
    # Qm = fr / (fa - fr) * fa / (2 * Z_min * capacitance * omega_r) approximately
    if capacitance_free and fa > fr:
        omega_r = 2 * np.pi * fr
        results.qm = fa**2 / (2 * np.pi * fr * z[fr_idx] * capacitance_free * (fa**2 - fr**2))

    print(results.table())
    return results


# ---------------------------------------------------------------------------
# Depolarisation analysis
# ---------------------------------------------------------------------------

def analyse_depolarisation(
    temperature: Any,
    d33: Any,
) -> dict[str, Optional[float]]:
    """Analyse temperature-dependent depolarisation (d33 vs T).

    Parameters
    ----------
    temperature : array-like
        Temperature in C.
    d33 : array-like
        d33 coefficient values (pC/N).

    Returns
    -------
    dict with 'Td' (depolarisation temperature), 'd33_initial', 'd33_final'.
    """
    temp, d = validate_xy(
        np.asarray(temperature, dtype=float),
        np.asarray(d33, dtype=float),
        allow_nan=False,
    )

    order = np.argsort(temp)
    temp, d = temp[order], d[order]

    d_initial = d[0]
    d_final = d[-1]

    # Depolarisation temperature: where d33 drops to 50% of initial
    threshold = d_initial * 0.5
    crossings = np.where(d < threshold)[0]

    Td = None
    if len(crossings) > 0:
        idx = crossings[0]
        if idx > 0:
            # Interpolate
            frac = (threshold - d[idx - 1]) / (d[idx] - d[idx - 1]) if d[idx] != d[idx - 1] else 0
            Td = temp[idx - 1] + frac * (temp[idx] - temp[idx - 1])

    result = {
        "Td": Td,
        "d33_initial": d_initial,
        "d33_final": d_final,
        "retention": (d_final / d_initial * 100) if d_initial != 0 else 0,
    }

    if Td is not None:
        print(f"[Praxis] Depolarisation: Td = {Td:.1f} C (50% loss)")
    print(f"[Praxis] d33: {d_initial:.1f} -> {d_final:.1f} pC/N ({result['retention']:.1f}% retention)")

    return result
