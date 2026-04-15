"""Impedance spectroscopy (EIS): Nyquist plot, Bode plot, equivalent circuit
fitting (Randles, R-CPE, custom), conductivity calculation, and Arrhenius analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence, Union

import numpy as np
from lmfit import Model, Parameters, minimize, report_fit
from lmfit.minimizer import MinimizerResult

from scripts.core.utils import validate_array
from scripts.core.plotter import plot_data, create_subplots


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ImpedanceData:
    """Parsed impedance data."""
    freq: np.ndarray       # Hz
    z_real: np.ndarray     # ohm (Z')
    z_imag: np.ndarray     # ohm (Z'') -- typically negative for capacitive
    z_mod: np.ndarray      # |Z|
    z_phase: np.ndarray    # degrees

    @classmethod
    def from_complex(cls, freq: np.ndarray, z: np.ndarray) -> ImpedanceData:
        """Create from frequency and complex impedance arrays."""
        return cls(
            freq=freq,
            z_real=z.real,
            z_imag=z.imag,
            z_mod=np.abs(z),
            z_phase=np.degrees(np.angle(z)),
        )

    @classmethod
    def from_components(
        cls, freq: np.ndarray, z_real: np.ndarray, z_imag: np.ndarray
    ) -> ImpedanceData:
        """Create from frequency, Z', and Z'' arrays."""
        z = z_real + 1j * z_imag
        return cls(
            freq=freq,
            z_real=z_real,
            z_imag=z_imag,
            z_mod=np.abs(z),
            z_phase=np.degrees(np.angle(z)),
        )

    @property
    def omega(self) -> np.ndarray:
        """Angular frequency (rad/s)."""
        return 2 * np.pi * self.freq

    @property
    def z_complex(self) -> np.ndarray:
        """Complex impedance array."""
        return self.z_real + 1j * self.z_imag


@dataclass
class CircuitFitResult:
    """Result of equivalent circuit fitting."""
    params: dict[str, float]
    uncertainties: dict[str, Optional[float]]
    z_fit: np.ndarray
    residual: float
    r_squared: float
    circuit_name: str
    lmfit_result: Optional[MinimizerResult] = None

    def report(self) -> str:
        lines = [
            f"[Praxis] Circuit fit: {self.circuit_name}",
            f"  R2 = {self.r_squared:.6f}",
            "  Parameters:",
        ]
        for name, val in self.params.items():
            err = self.uncertainties.get(name)
            err_str = f" ± {err:.4e}" if err else ""
            lines.append(f"    {name} = {val:.4e}{err_str}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.report()


# ---------------------------------------------------------------------------
# Data parsing
# ---------------------------------------------------------------------------

def parse_impedance(
    freq: Any,
    z_real: Optional[Any] = None,
    z_imag: Optional[Any] = None,
    z_mod: Optional[Any] = None,
    z_phase: Optional[Any] = None,
) -> ImpedanceData:
    """Parse impedance data from various input formats.

    Provide either (z_real, z_imag) or (z_mod, z_phase).
    """
    freq = validate_array(freq, "frequency")

    if z_real is not None and z_imag is not None:
        z_real = validate_array(z_real, "Z_real")
        z_imag = validate_array(z_imag, "Z_imag")
        return ImpedanceData.from_components(freq, z_real, z_imag)

    if z_mod is not None and z_phase is not None:
        z_mod = validate_array(z_mod, "|Z|")
        z_phase = validate_array(z_phase, "phase")
        # Convert mod + phase to real + imag
        phase_rad = np.radians(z_phase)
        z_real = z_mod * np.cos(phase_rad)
        z_imag = z_mod * np.sin(phase_rad)
        return ImpedanceData.from_components(freq, z_real, z_imag)

    raise ValueError("Provide either (z_real, z_imag) or (z_mod, z_phase).")


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_nyquist(
    data: ImpedanceData,
    *,
    fit: Optional[CircuitFitResult] = None,
    figsize: Optional[tuple[float, float]] = None,
    title: str = "Nyquist Plot",
    **kwargs: Any,
) -> tuple:
    """Create a Nyquist plot (Z' vs -Z'').

    Convention: -Z'' on y-axis (positive up for capacitive response).
    """
    fig, ax = plot_data(
        data.z_real, -data.z_imag,
        kind="scatter",
        xlabel="Z' (ohm)",
        ylabel="-Z'' (ohm)",
        title=title,
        label="Data",
        marker="o",
        figsize=figsize,
        **kwargs,
    )

    if fit is not None:
        ax.plot(fit.z_fit.real, -fit.z_fit.imag, "r-", linewidth=1.5, label="Fit")
        ax.legend(frameon=False)

    # Equal aspect ratio for Nyquist
    ax.set_aspect("equal", adjustable="datalim")

    return fig, ax


def plot_bode(
    data: ImpedanceData,
    *,
    fit: Optional[CircuitFitResult] = None,
    figsize: Optional[tuple[float, float]] = None,
    title: str = "Bode Plot",
) -> tuple:
    """Create a Bode plot (|Z| and phase vs frequency)."""
    fig, (ax1, ax2) = create_subplots(2, 1, figsize=figsize or (6, 7), sharex=True)

    # |Z| vs frequency
    ax1.loglog(data.freq, data.z_mod, "o", markersize=4, label="Data")
    ax1.set_ylabel("|Z| (ohm)")
    ax1.set_title(title)

    # Phase vs frequency
    ax2.semilogx(data.freq, data.z_phase, "o", markersize=4, label="Data")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Phase (°)")

    if fit is not None:
        ax1.loglog(data.freq, np.abs(fit.z_fit), "r-", linewidth=1.5, label="Fit")
        ax2.semilogx(data.freq, np.degrees(np.angle(fit.z_fit)), "r-", linewidth=1.5, label="Fit")

    for ax in (ax1, ax2):
        ax.legend(frameon=False)
        ax.grid(True, alpha=0.3, which="both")

    fig.tight_layout()
    return fig, (ax1, ax2)


# ---------------------------------------------------------------------------
# Equivalent circuit elements
# ---------------------------------------------------------------------------

def _z_resistor(omega: np.ndarray, R: float) -> np.ndarray:
    """Impedance of a resistor: Z = R."""
    return np.full_like(omega, R, dtype=complex)


def _z_capacitor(omega: np.ndarray, C: float) -> np.ndarray:
    """Impedance of a capacitor: Z = 1 / (jωC)."""
    return 1.0 / (1j * omega * C)


def _z_inductor(omega: np.ndarray, L: float) -> np.ndarray:
    """Impedance of an inductor: Z = jωL."""
    return 1j * omega * L


def _z_cpe(omega: np.ndarray, Q: float, n: float) -> np.ndarray:
    """Impedance of a constant phase element: Z = 1 / (Q(jω)^n)."""
    return 1.0 / (Q * (1j * omega) ** n)


def _z_warburg(omega: np.ndarray, Aw: float) -> np.ndarray:
    """Impedance of a Warburg element: Z = Aw / sqrt(ω) * (1 - j)."""
    return Aw / np.sqrt(omega) * (1 - 1j)


# ---------------------------------------------------------------------------
# Circuit models
# ---------------------------------------------------------------------------

def _z_randles(omega: np.ndarray, Rs: float, Rct: float, Cdl: float, Aw: float) -> np.ndarray:
    """Randles circuit: Rs + (Cdl || (Rct + W)).

    Rs: solution resistance
    Rct: charge transfer resistance
    Cdl: double layer capacitance
    Aw: Warburg coefficient
    """
    z_w = _z_warburg(omega, Aw)
    z_faradaic = Rct + z_w
    z_cdl = _z_capacitor(omega, Cdl)
    # Parallel combination
    z_parallel = (z_faradaic * z_cdl) / (z_faradaic + z_cdl)
    return Rs + z_parallel


def _z_randles_cpe(omega: np.ndarray, Rs: float, Rct: float, Q: float, n: float, Aw: float) -> np.ndarray:
    """Randles circuit with CPE: Rs + (CPE || (Rct + W))."""
    z_w = _z_warburg(omega, Aw)
    z_faradaic = Rct + z_w
    z_cpe = _z_cpe(omega, Q, n)
    z_parallel = (z_faradaic * z_cpe) / (z_faradaic + z_cpe)
    return Rs + z_parallel


def _z_rc(omega: np.ndarray, Rs: float, R1: float, C1: float) -> np.ndarray:
    """Simple R-RC circuit: Rs + (R1 || C1)."""
    z_c = _z_capacitor(omega, C1)
    z_r = _z_resistor(omega, R1)
    z_parallel = (z_r * z_c) / (z_r + z_c)
    return Rs + z_parallel


def _z_r_cpe(omega: np.ndarray, Rs: float, R1: float, Q1: float, n1: float) -> np.ndarray:
    """R-(R||CPE) circuit: Rs + (R1 || CPE)."""
    z_cpe = _z_cpe(omega, Q1, n1)
    z_r = _z_resistor(omega, R1)
    z_parallel = (z_r * z_cpe) / (z_r + z_cpe)
    return Rs + z_parallel


CIRCUITS = {
    "randles": (_z_randles, {"Rs": 100, "Rct": 1000, "Cdl": 1e-6, "Aw": 100}),
    "randles_cpe": (_z_randles_cpe, {"Rs": 100, "Rct": 1000, "Q": 1e-6, "n": 0.8, "Aw": 100}),
    "rc": (_z_rc, {"Rs": 100, "R1": 1000, "C1": 1e-6}),
    "r_cpe": (_z_r_cpe, {"Rs": 100, "R1": 1000, "Q1": 1e-6, "n1": 0.8}),
}


# ---------------------------------------------------------------------------
# Circuit fitting
# ---------------------------------------------------------------------------

def fit_circuit(
    data: ImpedanceData,
    circuit: str = "randles",
    *,
    params: Optional[dict[str, Any]] = None,
    method: str = "leastsq",
    max_iter: int = 5000,
) -> CircuitFitResult:
    """Fit an equivalent circuit model to impedance data.

    Parameters
    ----------
    data : ImpedanceData
    circuit : str
        Circuit name: 'randles', 'randles_cpe', 'rc', 'r_cpe'.
    params : dict, optional
        Initial parameter guesses. Override defaults.
    method : str
        lmfit minimisation method.
    max_iter : int
        Maximum iterations.

    Returns
    -------
    CircuitFitResult
    """
    if circuit not in CIRCUITS:
        raise ValueError(f"Unknown circuit: {circuit}. Available: {', '.join(CIRCUITS.keys())}")

    circuit_func, defaults = CIRCUITS[circuit]
    omega = data.omega
    z_data = data.z_complex

    # Build parameters
    p = Parameters()
    for name, default in defaults.items():
        value = params.get(name, default) if params else default
        if isinstance(value, dict):
            p.add(name, **value)
        else:
            # Set sensible bounds
            if name.startswith("R") or name == "Aw":
                p.add(name, value=value, min=0)
            elif name.startswith("C") or name.startswith("Q"):
                p.add(name, value=value, min=1e-15)
            elif name.startswith("n"):
                p.add(name, value=value, min=0, max=1)
            else:
                p.add(name, value=value)

    # Objective function (minimise real and imaginary residuals)
    def residual(params: Parameters) -> np.ndarray:
        z_calc = circuit_func(omega, **{k: v.value for k, v in params.items()})
        diff = z_data - z_calc
        return np.concatenate([diff.real, diff.imag])

    result = minimize(residual, p, method=method, max_nfev=max_iter)

    # Calculate fit impedance
    z_fit = circuit_func(omega, **{k: v.value for k, v in result.params.items()})

    # R² on complex impedance
    ss_res = np.sum(np.abs(z_data - z_fit) ** 2)
    ss_tot = np.sum(np.abs(z_data - np.mean(z_data)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    fit_result = CircuitFitResult(
        params={k: v.value for k, v in result.params.items()},
        uncertainties={k: v.stderr for k, v in result.params.items()},
        z_fit=z_fit,
        residual=float(np.sum(result.residual ** 2)),
        r_squared=r_squared,
        circuit_name=circuit,
        lmfit_result=result,
    )

    print(fit_result.report())
    return fit_result


# ---------------------------------------------------------------------------
# Conductivity calculation
# ---------------------------------------------------------------------------

def calc_conductivity(
    resistance: float,
    thickness: float,
    area: float,
) -> float:
    """Calculate ionic/electronic conductivity: σ = L / (R × A).

    Parameters
    ----------
    resistance : float
        Resistance in Ω (e.g. from Rct or bulk resistance).
    thickness : float
        Sample thickness in cm.
    area : float
        Electrode area in cm².

    Returns
    -------
    float
        Conductivity in S/cm.
    """
    if resistance <= 0:
        raise ValueError("Resistance must be positive.")
    sigma = thickness / (resistance * area)
    print(f"[Praxis] Conductivity: sigma = {sigma:.4e} S/cm")
    return sigma


def arrhenius_conductivity(
    temperatures_c: Sequence[float],
    conductivities: Sequence[float],
) -> dict[str, float]:
    """Arrhenius analysis of conductivity: ln(σT) vs 1000/T.

    Returns activation energy in eV and pre-exponential factor.

    Parameters
    ----------
    temperatures_c : list of float
        Temperatures in °C.
    conductivities : list of float
        Conductivities in S/cm.

    Returns
    -------
    dict with 'Ea_eV', 'sigma_0', 'r_squared', 'x' (1000/T), 'y' (ln(σT)).
    """
    k_B = 8.617e-5  # eV/K

    T_K = np.array(temperatures_c, dtype=float) + 273.15
    sigma = np.array(conductivities, dtype=float)

    x = 1000.0 / T_K  # 1000/T
    y = np.log(sigma * T_K)  # ln(σT)

    # Linear fit
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs

    # Ea = -slope * 1000 * k_B
    Ea = -slope * 1000 * k_B

    # R²
    y_fit = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_fit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    print(f"[Praxis] Arrhenius: Ea = {Ea:.3f} eV, R² = {r_squared:.4f}")

    return {
        "Ea_eV": Ea,
        "sigma_0": np.exp(intercept),
        "r_squared": r_squared,
        "x": x,
        "y": y,
    }
