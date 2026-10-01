"""Structural PK and PD model library.

Linear mammillary models are solved **analytically**, not numerically. The
disposition of any 1-, 2-, or 3-compartment model is reduced once to a sum of
exponentials by eigendecomposition of the rate matrix, and every input type
(bolus, zero-order infusion, first-order absorption) is then the convolution of
that impulse response with the input function, in closed form. This matters for
three reasons:

* fitting calls the model thousands of times, and a closed form is ~10^3 faster
  than an ODE solve;
* an ODE solver's tolerance shows up as noise in the objective function, which
  makes gradients unreliable and covariance matrices optimistic;
* the singular cases have exact limits (see ``_absorption_term``), whereas a
  solver silently returns whatever the step size gives.

Nonlinear structures — Michaelis-Menten elimination and target-mediated drug
disposition — have no closed form and are integrated with LSODA, which switches
to a stiff method on its own. TMDD is stiff by construction: binding is orders
of magnitude faster than elimination.

Parameterization uses clearances and volumes for interpretation. Microconstants
are also valid parameterizations; neither choice guarantees identifiability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

try:  # pragma: no cover - exercised only when scipy is absent
    from scipy.integrate import solve_ivp
except ImportError:  # pragma: no cover
    solve_ivp = None


# --------------------------------------------------------------- disposition


@dataclass(frozen=True)
class Disposition:
    """Impulse response of a linear mammillary model, in concentration units.

    ``concentration(t)`` for a unit IV bolus is ``sum(coef * exp(lam * t))``.
    ``lam`` are the negative eigenvalues (``-alpha``, ``-beta``, ``-gamma``)
    sorted from fastest to slowest, so ``lam[-1]`` is the terminal slope.
    """

    lam: np.ndarray
    coef: np.ndarray
    cl: float
    v1: float
    q: tuple[float, ...] = ()
    vp: tuple[float, ...] = ()

    @property
    def n_compartments(self) -> int:
        return 1 + len(self.q)

    @property
    def half_lives(self) -> np.ndarray:
        return np.log(2.0) / -self.lam

    @property
    def terminal_half_life(self) -> float:
        return float(np.log(2.0) / -self.lam[-1])

    @property
    def vss(self) -> float:
        return float(self.v1 + sum(self.vp))

    @property
    def auc_unit_dose(self) -> float:
        """AUC(0-inf) after a unit IV bolus; equals 1/CL for any linear model."""
        return float(np.sum(self.coef / -self.lam))

    @property
    def mrt_iv(self) -> float:
        """Mean residence time after an IV bolus; equals Vss/CL."""
        aumc = float(np.sum(self.coef / self.lam**2))
        return aumc / self.auc_unit_dose


def disposition(cl: float, v1: float, q: Sequence[float] = (), vp: Sequence[float] = ()) -> Disposition:
    """Build the impulse response for a mammillary model.

    ``q`` and ``vp`` are the intercompartmental clearances and peripheral
    volumes; pass none for one-compartment, one each for two, two each for
    three. All values are in consistent units (e.g. L/h and L).
    """
    q = tuple(float(x) for x in q)
    vp = tuple(float(x) for x in vp)
    if len(q) != len(vp):
        raise ValueError(f"got {len(q)} intercompartmental clearances but {len(vp)} peripheral volumes")
    if not all(math.isfinite(x) for x in (cl, v1, *q, *vp)):
        raise ValueError("disposition parameters must be finite")
    if cl <= 0 or v1 <= 0:
        raise ValueError("CL and V1 must be positive")
    if any(x <= 0 for x in q + vp):
        raise ValueError("Q and Vp must be positive")

    n = 1 + len(q)
    a = np.zeros((n, n))
    a[0, 0] = -cl / v1
    for j, (qj, vpj) in enumerate(zip(q, vp), start=1):
        k1j = qj / v1
        kj1 = qj / vpj
        a[0, 0] -= k1j
        a[0, j] = kj1
        a[j, 0] = k1j
        a[j, j] = -kj1

    if n == 1:
        lam = np.array([a[0, 0]])
        coef = np.array([1.0 / v1])
    else:
        # A mammillary rate matrix is similar to a symmetric matrix, so its
        # eigenvalues are real and negative. eig() can still return a tiny
        # imaginary part from round-off; discard it rather than propagate a
        # complex concentration.
        values, vectors = np.linalg.eig(a)
        values = np.real(values)
        vectors = np.real(vectors)
        inverse = np.linalg.inv(vectors)
        coef = vectors[0, :] * inverse[:, 0] / v1
        lam = values

    order = np.argsort(lam)  # most negative (fastest) first
    lam, coef = lam[order], coef[order]
    if np.any(lam >= 0):
        raise ValueError("non-negative eigenvalue: parameters do not describe a stable model")
    return Disposition(lam=lam, coef=coef, cl=float(cl), v1=float(v1), q=q, vp=vp)


def micro_constants(d: Disposition) -> dict[str, float]:
    """Micro-constants and macro-constants, for reporting only."""
    out = {"k10": d.cl / d.v1}
    for j, (qj, vpj) in enumerate(zip(d.q, d.vp), start=1):
        out[f"k1{j + 1}"] = qj / d.v1
        out[f"k{j + 1}1"] = qj / vpj
    for i, (lam, coef) in enumerate(zip(d.lam, d.coef)):
        out[f"lambda{i + 1}"] = -lam
        out[f"coef{i + 1}_per_dose"] = coef
        out[f"t_half_{i + 1}"] = math.log(2.0) / -lam
    return out


# --------------------------------------------------------------- input terms


def _absorption_term(lam: np.ndarray, ka: float, t: np.ndarray) -> np.ndarray:
    """(exp(lam t) - exp(-ka t)) / (ka + lam), with the removable singularity handled.

    When ``ka`` approaches ``-lam`` the denominator vanishes. The limit is
    ``t * exp(lam t)``. This is not a corner case: it is exactly the
    flip-flop boundary where absorption and elimination rates coincide, and a
    fitter walking through it produces inf or nan without this branch.
    """
    denom = ka + lam[None, :]
    near = np.abs(denom) < 1e-8
    safe = np.where(near, 1.0, denom)
    regular = (np.exp(lam[None, :] * t[:, None]) - np.exp(-ka * t)[:, None]) / safe
    limit = t[:, None] * np.exp(lam[None, :] * t[:, None])
    return np.where(near, limit, regular)


def conc_bolus(t: np.ndarray, dose: float, d: Disposition) -> np.ndarray:
    t = np.atleast_1d(np.asarray(t, dtype=float))
    out = dose * np.exp(d.lam[None, :] * t[:, None]) @ d.coef
    return np.where(t < 0, 0.0, out)


def conc_infusion(t: np.ndarray, dose: float, duration: float, d: Disposition) -> np.ndarray:
    """Zero-order input of ``dose`` over ``duration``, starting at t = 0."""
    t = np.atleast_1d(np.asarray(t, dtype=float))
    if duration <= 0:
        return conc_bolus(t, dose, d)
    rate = dose / duration
    t_in = np.clip(t, 0.0, duration)          # time spent infusing
    t_post = np.maximum(t - duration, 0.0)    # time since infusion ended
    ramp = (1.0 - np.exp(d.lam[None, :] * t_in[:, None])) / -d.lam[None, :]
    decay = np.exp(d.lam[None, :] * t_post[:, None])
    return np.where(t < 0, 0.0, rate * (ramp * decay) @ d.coef)


def conc_oral(t: np.ndarray, dose: float, ka: float, d: Disposition, f: float = 1.0, tlag: float = 0.0) -> np.ndarray:
    """First-order absorption from a depot with bioavailable fraction ``f``."""
    t = np.atleast_1d(np.asarray(t, dtype=float))
    shifted = np.maximum(t - tlag, 0.0)
    out = f * dose * ka * (_absorption_term(d.lam, ka, shifted) @ d.coef)
    return np.where(t <= tlag, 0.0, out)


def conc_transit(
    t: np.ndarray, dose: float, mtt: float, n: float, d: Disposition, f: float = 1.0, ka: float | None = None
) -> np.ndarray:
    """Savic transit-compartment absorption, evaluated with the log-gamma form.

    The literal factorial form overflows for ``n`` above ~20, and a fitted
    transit number routinely lands there. Using ``lgamma`` keeps it finite.
    ``n`` need not be an integer: it is estimated as a continuous parameter.
    """
    t = np.atleast_1d(np.asarray(t, dtype=float))
    if mtt <= 0 or n < 0:
        raise ValueError("MTT must be positive and n non-negative")
    ktr = (n + 1.0) / mtt
    if ka is not None:
        raise ValueError("conc_transit models gamma input directly into central; a separate depot ka is not implemented")
    # Input rate into the central compartment, convolved numerically with the
    # analytic disposition on a fine grid: the transit chain has no compact
    # closed form once it is combined with a multi-exponential disposition.
    grid = np.linspace(0.0, float(np.max(t)) if np.max(t) > 0 else 1.0, 4096)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_rate = (
            math.log(f * dose) + math.log(ktr) + n * np.log(np.maximum(grid, 1e-300) * ktr) - ktr * grid - math.lgamma(n + 1.0)
        )
    rate = np.where(grid > 0, np.exp(log_rate), 0.0)
    step = grid[1] - grid[0]
    out = np.zeros_like(t)
    for i, ti in enumerate(t):
        if ti <= 0:
            continue
        mask = grid <= ti
        tau = grid[mask]
        response = np.exp(d.lam[None, :] * (ti - tau)[:, None]) @ d.coef
        out[i] = np.trapezoid(rate[mask] * response, dx=step)
    return out


# ------------------------------------------------------------------- dosing


@dataclass(frozen=True)
class Dose:
    """One dosing event.

    ``duration`` of 0 with ``route='iv'`` is a bolus; a positive duration is a
    zero-order infusion. ``route='oral'`` uses first-order absorption and
    applies ``f`` and ``tlag``.
    """

    time: float
    amount: float
    duration: float = 0.0
    route: str = "iv"

    def __post_init__(self) -> None:
        if self.route not in {"iv", "oral"}:
            raise ValueError(f"route must be 'iv' or 'oral', got {self.route!r}")
        if not all(math.isfinite(x) for x in (self.time, self.amount, self.duration)):
            raise ValueError("dose event values must be finite")
        if self.time < 0 or self.duration < 0:
            raise ValueError("dose time and duration must be non-negative")
        if self.route == "oral" and self.duration:
            raise ValueError("oral infusion input is not implemented")
        if self.amount < 0:
            raise ValueError("dose amount must not be negative")


def build_regimen(
    amount: float,
    interval: float | None = None,
    n_doses: int = 1,
    start: float = 0.0,
    duration: float = 0.0,
    route: str = "iv",
    loading: float | None = None,
) -> list[Dose]:
    """Evenly spaced doses, optionally with a different first dose."""
    if n_doses < 1:
        raise ValueError("n_doses must be at least 1")
    if n_doses > 1 and (interval is None or interval <= 0):
        raise ValueError("a multiple-dose regimen needs a positive interval")
    doses = []
    for i in range(n_doses):
        amt = loading if (i == 0 and loading is not None) else amount
        doses.append(Dose(start + i * (interval or 0.0), amt, duration, route))
    return doses


def simulate_linear(
    times: Sequence[float],
    regimen: Sequence[Dose],
    d: Disposition,
    ka: float | None = None,
    f: float = 1.0,
    tlag: float = 0.0,
) -> np.ndarray:
    """Concentration-time profile by superposition.

    Superposition is exact for a linear model and is what makes multiple-dose
    and irregular-interval simulation cheap. It is **not** valid once any
    element of the model is nonlinear — Michaelis-Menten elimination,
    saturable binding, time-varying clearance — which is the single most common
    way a hand-rolled multiple-dose simulation goes wrong.
    """
    times = np.atleast_1d(np.asarray(times, dtype=float))
    total = np.zeros_like(times)
    for dose in regimen:
        offset = times - dose.time
        if dose.route == "oral":
            if ka is None:
                raise ValueError("oral dosing needs ka")
            total += conc_oral(offset, dose.amount, ka, d, f=f, tlag=tlag)
        elif dose.duration > 0:
            total += conc_infusion(offset, dose.amount, dose.duration, d)
        else:
            total += conc_bolus(offset, dose.amount, d)
    return total


def steady_state_metrics(d: Disposition, dose: float, interval: float, f: float = 1.0) -> dict[str, float]:
    """Closed-form steady-state summaries for a linear model.

    Accumulation ratio is computed per exponential rather than from the
    terminal slope alone. For a two-compartment drug given at an interval
    short relative to the distribution phase, the terminal-slope shortcut
    ``1/(1 - exp(-lambda_z tau))`` overstates accumulation, sometimes badly.
    """
    if interval <= 0:
        raise ValueError("interval must be positive")
    auc_tau = f * dose * d.auc_unit_dose
    cavg = auc_tau / interval
    # Cmax/Cmin at steady state for a bolus: sum over exponentials of the
    # geometric series for repeated dosing.
    ss_coef = d.coef / (1.0 - np.exp(d.lam * interval))
    cmax_ss = float(f * dose * np.sum(ss_coef))
    cmin_ss = float(f * dose * np.sum(ss_coef * np.exp(d.lam * interval)))
    single_cmax = float(f * dose * np.sum(d.coef))
    return {
        "auc_tau_ss": auc_tau,
        "cavg_ss": cavg,
        "cmax_ss_bolus": cmax_ss,
        "cmin_ss_bolus": cmin_ss,
        "accumulation_ratio_auc": d.auc_unit_dose / float(np.sum(d.coef * (-np.expm1(d.lam * interval)) / -d.lam)),
        "accumulation_ratio_cmax_bolus": cmax_ss / single_cmax if single_cmax else float("nan"),
        "peak_trough_fluctuation_pct": 100.0 * (cmax_ss - cmin_ss) / cavg if cavg else float("nan"),
        "time_to_90pct_ss": -math.log(0.10) / -d.lam[-1],
        "time_to_95pct_ss": -math.log(0.05) / -d.lam[-1],
    }


# ------------------------------------------------------ nonlinear structures


def _require_scipy(what: str) -> None:
    if solve_ivp is None:  # pragma: no cover
        raise RuntimeError(f"{what} needs scipy; install scipy to use this model")


def _integrate_with_doses(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    y0: np.ndarray,
    times: np.ndarray,
    regimen: Sequence[Dose],
    dose_compartment: int,
    rtol: float = 1e-8,
    atol: float = 1e-10,
) -> np.ndarray:
    """Integrate across dose events by restarting at each one.

    Bolus doses are state discontinuities. Handing them to a solver as part of
    the right-hand side (a narrow spike, or a conditional) is how people get
    doses silently skipped when the adaptive step jumps over them. Restarting
    the integration at every event makes that impossible.
    """
    _require_scipy("ODE-based models")
    if times.ndim != 1 or not times.size or not np.all(np.isfinite(times)) or np.any(times < 0):
        raise ValueError("integration times must be nonempty, finite and non-negative")
    events = sorted(regimen, key=lambda x: x.time)
    infusions = [(e.time, e.time + e.duration, e.amount / e.duration) for e in events if e.duration > 0]

    def rhs_with_infusions(t: float, y: np.ndarray) -> np.ndarray:
        dy = np.asarray(rhs(t, y), dtype=float)
        for start, end, rate in infusions:
            if start <= t < end:
                dy[dose_compartment] += rate
        return dy

    breakpoints = sorted({0.0, *(e.time for e in events), *(e.time + e.duration for e in events if e.duration > 0), float(np.max(times))})
    breakpoints = [b for b in breakpoints if b <= np.max(times) + 1e-12]

    out = np.zeros((len(times), len(y0)))
    state = np.array(y0, dtype=float)
    for index, start in enumerate(breakpoints):
        for event in events:
            if math.isclose(event.time, start, rel_tol=0, abs_tol=1e-12) and event.duration == 0:
                state[dose_compartment] += event.amount
        stop = breakpoints[index + 1] if index + 1 < len(breakpoints) else float(np.max(times))
        window = (times >= start - 1e-12) & (times <= stop + 1e-12)
        if stop <= start:
            out[window] = state
            continue
        solution = solve_ivp(
            rhs_with_infusions,
            (start, stop),
            state,
            method="LSODA",
            rtol=rtol,
            atol=atol,
            dense_output=True,
            max_step=(stop - start),
        )
        if not solution.success:  # pragma: no cover - solver failure path
            raise RuntimeError(f"integration failed between t={start} and t={stop}: {solution.message}")
        if np.any(window):
            out[window] = solution.sol(np.clip(times[window], start, stop)).T
        state = solution.y[:, -1]
    return out


def simulate_michaelis_menten(
    times: Sequence[float],
    regimen: Sequence[Dose],
    vmax: float,
    km: float,
    v1: float,
    q: Sequence[float] = (),
    vp: Sequence[float] = (),
    ka: float | None = None,
    f: float = 1.0,
) -> np.ndarray:
    """Concentration with saturable (Michaelis-Menten) elimination.

    ``vmax`` is an amount per unit time, ``km`` a concentration. Doubling the
    dose of such a drug does not double exposure, and no amount of
    superposition will reproduce that — this must be integrated.
    """
    times = np.atleast_1d(np.asarray(times, dtype=float))
    q = tuple(q)
    vp = tuple(vp)
    if len(q) != len(vp) or any(x <= 0 or not math.isfinite(x) for x in (vmax, km, v1, *q, *vp)):
        raise ValueError("positive finite MM parameters and paired peripherals are required")
    routes = {event.route for event in regimen}
    if routes - {"oral" if ka is not None else "iv"}:
        raise ValueError("MM simulation needs a single route matching ka; mixed routes are not implemented")
    n_periph = len(q)
    depot = 1 if ka is not None else 0
    size = 1 + n_periph + depot

    def rhs(_t: float, y: np.ndarray) -> np.ndarray:
        dy = np.zeros(size)
        central = y[depot]
        conc = central / v1
        elimination = vmax * conc / (km + conc)
        dy[depot] -= elimination
        if depot:
            dy[0] = -ka * y[0]
            dy[depot] += f * ka * y[0]
        for j in range(n_periph):
            idx = depot + 1 + j
            flux = q[j] * (conc - y[idx] / vp[j])
            dy[depot] -= flux
            dy[idx] += flux
        return dy

    y0 = np.zeros(size)
    states = _integrate_with_doses(rhs, y0, times, regimen, dose_compartment=0 if depot else 0)
    return states[:, depot] / v1


def _qss_free(total_drug, total_target, kss):
    """Positive quadratic root without cancellation when target greatly exceeds drug."""
    drug = np.asarray(total_drug, dtype=float)
    b = drug - np.asarray(total_target, dtype=float) - kss
    radical = np.hypot(b, 2.0 * np.sqrt(kss) * np.sqrt(drug))
    direct = 0.5 * (b + radical)
    denominator = radical - b
    stable = np.divide(2.0 * kss * drug, denominator, out=np.zeros_like(drug), where=denominator > 0)
    return np.where(b >= 0, direct, stable)


def simulate_tmdd(
    times: Sequence[float],
    regimen: Sequence[Dose],
    cl: float,
    v1: float,
    kon: float,
    koff: float,
    kint: float,
    ksyn: float,
    kdeg: float,
    q: float | None = None,
    vp: float | None = None,
    approximation: str = "full",
) -> dict[str, np.ndarray]:
    """Target-mediated drug disposition.

    ``approximation`` is ``full`` (Mager-Jusko) or ``qss`` (quasi-steady-state,
    Gibiansky). The system can be stiff; adaptive LSODA integration is used.
    Verify tolerances against the requested output and kinetic timescales.

    Returns free drug, free target, complex, and total drug concentrations. The
    assay must be mapped to its actual analyte. Ligand-binding assays can
    report free, total or operational fractions depending on their design.
    """
    times = np.atleast_1d(np.asarray(times, dtype=float))
    if approximation not in {"full", "qss"}:
        raise ValueError("approximation must be 'full' or 'qss'")
    if any(event.route != "iv" for event in regimen):
        raise ValueError("TMDD helper supports IV doses only")
    if (q is None) != (vp is None):
        raise ValueError("TMDD peripheral clearance and volume must be paired")
    if any(not math.isfinite(x) or x <= 0 for x in (cl, v1, kon, kdeg)) or any(not math.isfinite(x) or x < 0 for x in (koff, kint, ksyn)):
        raise ValueError("invalid TMDD kinetic parameters")
    if approximation == "qss" and koff + kint <= 0:
        raise ValueError("QSS needs a positive Kss")
    if q is not None and (not math.isfinite(q) or not math.isfinite(vp) or q <= 0 or vp <= 0):
        raise ValueError("TMDD peripheral Q and volume must be finite and positive")
    has_periph = q is not None and vp is not None
    kel = cl / v1
    kd_qss = (koff + kint) / kon

    if approximation == "full":
        # y = [free drug amount, free target conc, complex conc, (peripheral amount)]
        size = 4 if has_periph else 3

        def rhs(_t: float, y: np.ndarray) -> np.ndarray:
            drug = max(y[0], 0.0) / v1
            target, complex_ = max(y[1], 0.0), max(y[2], 0.0)
            binding = kon * drug * target - koff * complex_
            dy = np.zeros(size)
            dy[0] = -kel * y[0] - binding * v1
            dy[1] = ksyn - kdeg * target - binding
            dy[2] = binding - kint * complex_
            if has_periph:
                flux = q * (drug - y[3] / vp)
                dy[0] -= flux
                dy[3] = flux
            return dy

        y0 = np.zeros(size)
        y0[1] = ksyn / kdeg
        states = _integrate_with_doses(rhs, y0, times, regimen, dose_compartment=0)
        free = states[:, 0] / v1
        target = states[:, 1]
        complex_ = states[:, 2]
        return {"free_drug": free, "free_target": target, "complex": complex_, "total_drug": free + complex_}

    # QSS: quasi-steady complex relation, solved from the total-drug quadratic.
    size = 3 if has_periph else 2

    def rhs_qss(_t: float, y: np.ndarray) -> np.ndarray:
        total_drug = max(y[0], 0.0) / v1
        total_target = max(y[1], 0.0)
        free = float(_qss_free(total_drug, total_target, kd_qss))
        complex_ = total_target * free / (kd_qss + free) if (kd_qss + free) > 0 else 0.0
        dy = np.zeros(size)
        dy[0] = -kel * free * v1 - kint * complex_ * v1
        dy[1] = ksyn - kdeg * (total_target - complex_) - kint * complex_
        if has_periph:
            flux = q * (free - y[2] / vp)
            dy[0] -= flux
            dy[2] = flux
        return dy

    y0 = np.zeros(size)
    y0[1] = ksyn / kdeg
    states = _integrate_with_doses(rhs_qss, y0, times, regimen, dose_compartment=0)
    total_drug = states[:, 0] / v1
    total_target = states[:, 1]
    free = _qss_free(np.maximum(total_drug, 0.0), np.maximum(total_target, 0.0), kd_qss)
    complex_ = total_target * free / (kd_qss + free)
    return {
        "free_drug": free,
        "free_target": np.maximum(total_target - complex_, 0.0),
        "complex": complex_,
        "total_drug": total_drug,
    }


# ------------------------------------------------------------------- PD models


def emax(conc: np.ndarray, e0: float, emax_value: float, ec50: float, hill: float = 1.0) -> np.ndarray:
    """Sigmoid Emax. ``hill = 1`` is the ordinary Emax model."""
    conc = np.maximum(np.asarray(conc, dtype=float), 0.0)
    if hill == 1.0:
        return e0 + emax_value * conc / (ec50 + conc)
    powered = np.power(conc, hill)
    return e0 + emax_value * powered / (np.power(ec50, hill) + powered)


def imax(conc: np.ndarray, e0: float, imax_value: float, ic50: float, hill: float = 1.0) -> np.ndarray:
    """Inhibitory sigmoid model; ``imax_value`` of 1 permits complete inhibition."""
    conc = np.maximum(np.asarray(conc, dtype=float), 0.0)
    powered = np.power(conc, hill)
    return e0 * (1.0 - imax_value * powered / (np.power(ic50, hill) + powered))


def effect_compartment(times: Sequence[float], conc: Sequence[float], ke0: float) -> np.ndarray:
    """Hysteresis-collapsing effect compartment, integrated on the observed grid.

    Solved exactly per interval under a linear interpolation of plasma
    concentration, so the result does not depend on how densely the profile
    was sampled — the usual explicit-Euler version does, and understates Ce
    peaks on sparse grids.
    """
    times = np.asarray(times, dtype=float)
    conc = np.asarray(conc, dtype=float)
    if times.shape != conc.shape:
        raise ValueError("times and conc must have the same length")
    if not np.all(np.isfinite(times)) or not np.all(np.isfinite(conc)) or np.any(np.diff(times) <= 0):
        raise ValueError("effect-compartment times must increase and inputs must be finite")
    if ke0 <= 0:
        raise ValueError("ke0 must be positive")
    ce = np.zeros_like(times)
    for i in range(1, len(times)):
        dt = times[i] - times[i - 1]
        if dt <= 0:
            ce[i] = ce[i - 1]
            continue
        c0, c1 = conc[i - 1], conc[i]
        slope = (c1 - c0) / dt
        decay = math.exp(-ke0 * dt)
        # Exact solution of dCe/dt = ke0 (c0 + slope*t - Ce) over [0, dt].
        ce[i] = ce[i - 1] * decay + (c0 - slope / ke0) * (1.0 - decay) + slope * dt
    return ce


IDR_TYPES = {
    1: "inhibition of production (kin)",
    2: "inhibition of loss (kout)",
    3: "stimulation of production (kin)",
    4: "stimulation of loss (kout)",
}


def indirect_response(
    times: Sequence[float],
    conc_fn: Callable[[float], float],
    kin: float,
    kout: float,
    idr_type: int,
    max_effect: float,
    c50: float,
    hill: float = 1.0,
) -> np.ndarray:
    """Dayneka-Jusko indirect response models I-IV.

    Baseline is ``kin / kout`` by construction, so the four models differ in
    *how* the drug perturbs turnover, not in where the response starts. This is
    the whole point: a direct Emax fit to a delayed biomarker will absorb the
    delay into a falsely large EC50, and the two are distinguishable only by
    the shape of the return to baseline.

    ``max_effect`` is Imax for types I-II (bounded by 1 for complete
    inhibition) and Emax for types III-IV (unbounded).
    """
    _require_scipy("indirect response models")
    if idr_type not in IDR_TYPES:
        raise ValueError(f"idr_type must be one of {sorted(IDR_TYPES)}")
    if kin <= 0 or kout <= 0 or c50 <= 0:
        raise ValueError("kin, kout and C50 must be positive")

    if max_effect < 0 or hill <= 0 or (idr_type in (1, 2) and max_effect > 1):
        raise ValueError("IDR inhibition must be in [0,1]; stimulation non-negative and Hill positive")

    def drive(t: float) -> float:
        conc = max(float(conc_fn(t)), 0.0)
        powered = conc**hill
        return max_effect * powered / (c50**hill + powered)

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        fraction = drive(t)
        if idr_type == 1:
            return np.array([kin * (1.0 - fraction) - kout * y[0]])
        if idr_type == 2:
            return np.array([kin - kout * (1.0 - fraction) * y[0]])
        if idr_type == 3:
            return np.array([kin * (1.0 + fraction) - kout * y[0]])
        return np.array([kin - kout * (1.0 + fraction) * y[0]])

    times = np.atleast_1d(np.asarray(times, dtype=float))
    span = (float(min(times.min(), 0.0)), float(times.max()))
    solution = solve_ivp(
        rhs, span, [kin / kout], method="LSODA", rtol=1e-8, atol=1e-10, dense_output=True, max_step=max(span[1] / 200.0, 1e-6)
    )
    if not solution.success:  # pragma: no cover
        raise RuntimeError(f"indirect response integration failed: {solution.message}")
    return solution.sol(times)[0]


__all__ = [
    "Disposition",
    "Dose",
    "IDR_TYPES",
    "build_regimen",
    "conc_bolus",
    "conc_infusion",
    "conc_oral",
    "conc_transit",
    "disposition",
    "effect_compartment",
    "emax",
    "imax",
    "indirect_response",
    "micro_constants",
    "simulate_linear",
    "simulate_michaelis_menten",
    "simulate_tmdd",
    "steady_state_metrics",
]
