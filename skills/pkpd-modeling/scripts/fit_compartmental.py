#!/usr/bin/env python3
"""Fit compartmental PK models to concentration-time data, with identifiability diagnostics.

The fit itself is the easy part. What decides whether the result means anything
is: was the residual error model right, is the extra compartment actually
supported, and are the parameters identifiable from these data at all. This
script reports all three, and flags the cases where a converged fit is still
uninterpretable.

    python3 fit_compartmental.py -i profile.csv --dose 100 --route iv-bolus --model 2cmt
    python3 fit_compartmental.py -i profile.csv --dose 100 --route oral --compare 1cmt,2cmt
    python3 fit_compartmental.py -i profile.csv --dose 500 --route iv-infusion --tinf 1 \
        --model 2cmt --weight 1/y2

Input columns default to ``time`` and ``conc``; an ``id`` column fits each
subject separately. Parameters are estimated on the log scale, so they cannot
go negative and their confidence intervals come out asymmetric, which is the
honest shape for a clearance or a volume.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from _common import (
    EXIT_INPUT,
    InputError,
    Report,
    add_format_argument,
    group_by,
    main_wrapper,
    parse_float,
    read_table,
    require_columns,
)
from _models import Dose, build_regimen, disposition, simulate_linear

try:
    from scipy.optimize import least_squares
    from scipy.stats import f as f_dist
    from scipy.stats import t as t_dist
except ImportError as exc:  # pragma: no cover
    raise SystemExit("fit_compartmental.py needs scipy: uv pip install scipy") from exc


MODELS = {
    "1cmt": ["CL", "V1"],
    "2cmt": ["CL", "V1", "Q2", "V2"],
    "3cmt": ["CL", "V1", "Q2", "V2", "Q3", "V3"],
}

WEIGHTS = {
    "uniform": "constant variance (additive error)",
    "1/y": "variance proportional to the observation",
    "1/y2": "constant CV (proportional error) - the usual PK default",
    "1/yhat": "variance proportional to the prediction",
    "1/yhat2": "constant CV against the prediction",
}


# ------------------------------------------------------------------- model


@dataclass
class FitSpec:
    model: str
    route: str
    dose: float
    tinf: float | None
    interval: float | None
    n_doses: int
    absorption: str
    estimate_lag: bool

    @property
    def parameter_names(self) -> list[str]:
        names = list(MODELS[self.model])
        if self.route == "oral":
            names = [f"{n}/F" for n in names]
            names.append("MTT" if self.absorption == "transit" else "ka")
            if self.absorption == "transit":
                names.append("Ntr")
            if self.estimate_lag:
                names.append("tlag")
        return names


def _regimen(spec: FitSpec) -> list[Dose]:
    return build_regimen(
        spec.dose,
        interval=spec.interval,
        n_doses=spec.n_doses,
        duration=spec.tinf or 0.0,
        route="oral" if spec.route == "oral" else "iv",
    )


def predictor(spec: FitSpec) -> Callable[[np.ndarray, np.ndarray], np.ndarray]:
    """Return f(times, theta) -> predicted concentration."""
    regimen = _regimen(spec)
    n_disp = len(MODELS[spec.model])

    def predict(times: np.ndarray, theta: np.ndarray) -> np.ndarray:
        cl, v1 = theta[0], theta[1]
        q = tuple(theta[2:n_disp:2])
        vp = tuple(theta[3:n_disp:2])
        disp = disposition(cl, v1, q, vp)
        if spec.route != "oral":
            return simulate_linear(times, regimen, disp)
        extra = theta[n_disp:]
        if spec.absorption == "transit":
            mtt, ntr = extra[0], extra[1]
            tlag = extra[2] if spec.estimate_lag else 0.0
            from _models import conc_transit  # local: only this branch needs it

            total = np.zeros_like(times, dtype=float)
            for dose in regimen:
                total += conc_transit(np.maximum(times - dose.time - tlag, 0.0), dose.amount, mtt, ntr, disp)
            return total
        ka = extra[0]
        tlag = extra[1] if spec.estimate_lag else 0.0
        return simulate_linear(times, regimen, disp, ka=ka, f=1.0, tlag=tlag)

    return predict


# ------------------------------------------------------------------ fitting


@dataclass
class FitResult:
    theta: np.ndarray
    names: list[str]
    se_log: np.ndarray
    wssr: float
    n: int
    p: int
    correlation: np.ndarray
    condition: float
    predicted: np.ndarray
    residuals: np.ndarray
    weighted_residuals: np.ndarray
    sigma: float
    success: bool
    message: str

    @property
    def aic(self) -> float:
        return self.n * math.log(max(self.wssr / self.n, np.finfo(float).tiny)) + 2 * self.p

    @property
    def bic(self) -> float:
        return self.n * math.log(max(self.wssr / self.n, np.finfo(float).tiny)) + self.p * math.log(self.n)


def _weights(y: np.ndarray, yhat: np.ndarray, scheme: str) -> np.ndarray:
    floor = 1e-12
    if scheme == "uniform":
        return np.ones_like(y)
    if scheme == "1/y":
        return 1.0 / np.maximum(np.abs(y), floor)
    if scheme == "1/y2":
        return 1.0 / np.maximum(y**2, floor)
    if scheme == "1/yhat":
        return 1.0 / np.maximum(np.abs(yhat), floor)
    if scheme == "1/yhat2":
        return 1.0 / np.maximum(yhat**2, floor)
    raise InputError(f"unknown weighting scheme {scheme!r}")


def initial_estimates(spec: FitSpec, time: np.ndarray, conc: np.ndarray) -> np.ndarray:
    """Heuristic starting values from the shape of the data.

    Bad initial estimates are the usual cause of a 'model that will not fit'.
    These come from the same quantities NCA would give: the terminal slope sets
    the slow disposition, the AUC sets clearance, and the peak sets the central
    volume.
    """
    positive = conc > 0
    t, c = time[positive], conc[positive]
    if len(t) < 3:
        raise InputError("need at least 3 positive concentrations to fit")
    tail = slice(max(len(t) - 3, 0), len(t))
    slope = np.polyfit(t[tail], np.log(c[tail]), 1)[0]
    lam = max(-slope, 1e-4)
    auc = float(np.trapezoid(c, t)) + c[-1] / lam
    cl = spec.dose / max(auc, 1e-9)
    cmax = float(c.max())
    v1 = spec.dose / cmax if spec.route == "iv-bolus" else cl / lam
    v1 = max(v1, 1e-6)

    theta = [cl, v1]
    if spec.model in {"2cmt", "3cmt"}:
        theta += [cl, v1 * 2.0]
    if spec.model == "3cmt":
        theta += [cl / 3.0, v1 * 5.0]
    if spec.route == "oral":
        tmax = float(t[int(np.argmax(c))])
        if spec.absorption == "transit":
            theta += [max(tmax * 0.7, 1e-3), 3.0]
        else:
            theta += [max(2.0 / max(tmax, 1e-3), 1e-3)]
        if spec.estimate_lag:
            theta += [max(float(t.min()) * 0.5, 1e-3)]
    return np.asarray(theta, dtype=float)


def fit_one(
    spec: FitSpec,
    time: np.ndarray,
    conc: np.ndarray,
    scheme: str,
    starts: int = 5,
    seed: int = 20260727,
) -> FitResult:
    predict = predictor(spec)
    names = spec.parameter_names
    p = len(names)
    n = len(time)
    if n <= p:
        raise InputError(f"{n} observations cannot support {p} parameters")

    base = initial_estimates(spec, time, conc)
    rng = np.random.default_rng(seed)

    def residual(log_theta: np.ndarray) -> np.ndarray:
        theta = np.exp(log_theta)
        try:
            yhat = predict(time, theta)
        except (ValueError, np.linalg.LinAlgError):
            return np.full(n, 1e6)
        if not np.all(np.isfinite(yhat)):
            return np.full(n, 1e6)
        w = _weights(conc, yhat, scheme)
        return np.sqrt(w) * (conc - yhat)

    best = None
    for attempt in range(max(1, starts)):
        start = base if attempt == 0 else base * np.exp(rng.normal(0.0, 0.5, size=p))
        try:
            candidate = least_squares(
                residual,
                np.log(np.maximum(start, 1e-12)),
                method="trf",
                x_scale="jac",
                max_nfev=5000 * p,
            )
        except (ValueError, np.linalg.LinAlgError):
            continue
        if best is None or candidate.cost < best.cost:
            best = candidate
    if best is None:  # pragma: no cover - every start failed
        raise InputError("optimiser failed from every starting point; check dose, units and route")

    theta = np.exp(best.x)
    yhat = predict(time, theta)
    weights = _weights(conc, yhat, scheme)
    residuals = conc - yhat
    weighted = np.sqrt(weights) * residuals
    wssr = float(np.sum(weighted**2))
    dof = n - p
    sigma2 = wssr / dof

    jac = best.jac
    try:
        # Covariance on the log scale from the Gauss-Newton approximation.
        _, s, vt = np.linalg.svd(jac, full_matrices=False)
        threshold = np.finfo(float).eps * max(jac.shape) * (s[0] if s.size else 0.0)
        if np.count_nonzero(s > threshold) < p:
            raise np.linalg.LinAlgError("rank-deficient sensitivity matrix; covariance is not identifiable")
        s_inv = 1.0 / s
        cov = (vt.T * s_inv**2) @ vt * sigma2
        se_log = np.sqrt(np.maximum(np.diag(cov), 0.0))
        outer = np.outer(se_log, se_log)
        with np.errstate(divide="ignore", invalid="ignore"):
            corr = np.where(outer > 0, cov / np.where(outer > 0, outer, 1.0), np.nan)
        # NONMEM's condition number: largest over smallest eigenvalue of the
        # *correlation* matrix of the estimates. Reported this way so the
        # familiar ">1000 is ill-conditioned" rule of thumb actually applies;
        # the condition number of the Jacobian is a different quantity on a
        # different scale, and the two get confused constantly.
        if np.all(np.isfinite(corr)):
            eigenvalues = np.linalg.eigvalsh(corr)
            smallest = float(eigenvalues.min())
            condition = float(eigenvalues.max() / smallest) if smallest > 0 else float("inf")
        else:
            condition = float("inf")
    except np.linalg.LinAlgError:  # pragma: no cover
        se_log = np.full(p, np.nan)
        corr = np.full((p, p), np.nan)
        condition = float("inf")

    return FitResult(
        theta=theta,
        names=names,
        se_log=se_log,
        wssr=wssr,
        n=n,
        p=p,
        correlation=corr,
        condition=condition,
        predicted=yhat,
        residuals=residuals,
        weighted_residuals=weighted,
        sigma=math.sqrt(sigma2),
        success=bool(best.success),
        message=str(best.message),
    )


# -------------------------------------------------------------- derivations


def secondary_parameters(spec: FitSpec, theta: np.ndarray) -> dict[str, float]:
    n_disp = len(MODELS[spec.model])
    cl, v1 = theta[0], theta[1]
    q = tuple(theta[2:n_disp:2])
    vp = tuple(theta[3:n_disp:2])
    disp = disposition(cl, v1, q, vp)
    suffix = "/F" if spec.route == "oral" else ""
    out = {
        f"Vss{suffix}": disp.vss,
        "MRT_iv": disp.mrt_iv,
        "terminal_t_half": disp.terminal_half_life,
    }
    for i, half in enumerate(disp.half_lives, start=1):
        out[f"t_half_phase{i}"] = float(half)
    if spec.route == "oral" and spec.absorption != "transit":
        ka = theta[n_disp]
        out["absorption_t_half"] = math.log(2.0) / ka
        if ka < 1.0 / disp.terminal_half_life * math.log(2.0):
            out["flip_flop_suspected"] = 1.0
    if spec.interval:
        from _models import steady_state_metrics

        out.update({k: v for k, v in steady_state_metrics(disp, spec.dose, spec.interval).items()})
    return out


def runs_test_p(residuals: np.ndarray) -> float:
    """Two-sided Wald-Wolfowitz runs test on residual signs."""
    signs = np.sign(residuals)
    signs = signs[signs != 0]
    n = len(signs)
    if n < 8:
        return float("nan")
    n_pos = int(np.sum(signs > 0))
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.0
    runs = 1 + int(np.sum(signs[1:] != signs[:-1]))
    mean = 2.0 * n_pos * n_neg / n + 1.0
    var = (mean - 1.0) * (mean - 2.0) / (n - 1.0)
    if var <= 0:
        return float("nan")
    z = (runs - mean) / math.sqrt(var)
    return float(2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))))


# --------------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fit 1/2/3-compartment models with identifiability and model-selection diagnostics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("--dose", type=float, required=True)
    parser.add_argument("--route", choices=("iv-bolus", "iv-infusion", "oral"), default="iv-bolus")
    parser.add_argument("--model", choices=sorted(MODELS), default="1cmt")
    parser.add_argument("--compare", help="comma-separated models to compare, e.g. 1cmt,2cmt,3cmt")
    parser.add_argument("--tinf", type=float, help="infusion duration for --route iv-infusion")
    parser.add_argument("--interval", type=float, help="dosing interval for a multiple-dose profile")
    parser.add_argument("--n-doses", type=int, default=1)
    parser.add_argument("--absorption", choices=("first-order", "transit"), default="first-order")
    parser.add_argument("--lag", action="store_true", help="estimate an absorption lag time")
    parser.add_argument("--weight", choices=sorted(WEIGHTS), default="1/y2")
    parser.add_argument("--starts", type=int, default=5, help="random restarts (default: 5)")
    parser.add_argument("--time-column", default="time")
    parser.add_argument("--conc-column", default="conc")
    parser.add_argument("--subject-column", default="id")
    parser.add_argument("--max-rse", type=float, default=50.0, help="flag %%RSE above this (default: 50)")
    parser.add_argument("--max-corr", type=float, default=0.95, help="flag |correlation| above this (default: 0.95)")
    parser.add_argument("--predictions", action="store_true", help="also emit the observed/predicted table")
    add_format_argument(parser)
    return parser


def _fit_and_report(spec: FitSpec, args, subject: str, time, conc, report: Report) -> FitResult:
    result = fit_one(spec, time, conc, args.weight, starts=args.starts)
    label = f"subject {subject}" if subject else "fit"

    rows = []
    crit = t_dist.ppf(0.975, max(result.n - result.p, 1))
    for i, name in enumerate(result.names):
        se = result.se_log[i]
        rows.append(
            {
                "parameter": name,
                "estimate": result.theta[i],
                "rse_pct": 100.0 * se if math.isfinite(se) else float("nan"),
                "ci95_low": result.theta[i] * math.exp(-crit * se) if math.isfinite(se) else float("nan"),
                "ci95_high": result.theta[i] * float(np.exp(min(crit * se, 709.0))) if math.isfinite(se) else float("nan"),
            }
        )
        if math.isfinite(se) and 100.0 * se > args.max_rse:
            report.finding(
                f"{label}: {name} has {100 * se:.0f}% RSE - not estimable from these data at this model size"
            )
    report.table(f"{label}: {spec.model} {spec.route} parameters", rows)

    secondary = secondary_parameters(spec, result.theta)
    report.table(f"{label}: secondary parameters", [{"parameter": k, "value": v} for k, v in secondary.items()])
    if secondary.get("flip_flop_suspected"):
        report.finding(
            f"{label}: ka is slower than the terminal disposition rate - the fit is in the flip-flop "
            "branch, where ka and k are numerically exchangeable. Without IV data the assignment is a "
            "modelling assumption, not an estimate."
        )

    report.table(
        f"{label}: fit statistics",
        [
            {
                "statistic": "observations",
                "value": result.n,
            },
            {"statistic": "parameters", "value": result.p},
            {"statistic": "weighted SSR", "value": result.wssr},
            {"statistic": "residual SD", "value": result.sigma},
            {"statistic": "AIC", "value": result.aic},
            {"statistic": "BIC", "value": result.bic},
            {"statistic": "condition number", "value": result.condition},
            {"statistic": "runs-test p (residual signs)", "value": runs_test_p(result.weighted_residuals)},
            {"statistic": "converged", "value": result.success},
        ],
    )

    with np.errstate(invalid="ignore"):
        for i in range(result.p):
            for j in range(i + 1, result.p):
                rho = result.correlation[i, j]
                if math.isfinite(rho) and abs(rho) > args.max_corr:
                    report.finding(
                        f"{label}: {result.names[i]} and {result.names[j]} are correlated at "
                        f"{rho:+.3f} - the data cannot separate them; consider a simpler model"
                    )
    if not math.isfinite(result.condition) or result.condition > 1000:
        report.finding(
            f"{label}: condition number {result.condition:.0f} exceeds 1000 - the model is "
            "ill-conditioned or rank deficient; standard errors do not establish identifiability"
        )
    runs_p = runs_test_p(result.weighted_residuals)
    if math.isfinite(runs_p) and runs_p < 0.05:
        report.finding(
            f"{label}: residual signs are not random (runs test p = {runs_p:.4f}) - a structural "
            "pattern needing review of structure, time ordering, serial dependence and error model"
        )
    if not result.success:
        report.finding(f"{label}: optimiser did not report convergence ({result.message})")

    if args.predictions:
        report.table(
            f"{label}: observed vs predicted",
            [
                {
                    "time": float(t),
                    "observed": float(o),
                    "predicted": float(p),
                    "residual": float(r),
                    "weighted_residual": float(w),
                }
                for t, o, p, r, w in zip(time, conc, result.predicted, result.residuals, result.weighted_residuals)
            ],
        )
    return result


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from _common import validate_numeric_args
    validate_numeric_args(args)
    if args.weight in {"1/yhat", "1/yhat2"}:
        raise InputError("prediction-dependent WLS omits the likelihood variance term; use a full likelihood/error-model tool")
    if args.dose <= 0 or args.n_doses < 1 or (args.interval is not None and args.interval <= 0):
        raise InputError("dose, dose count and interval must be positive")
    if args.route == "iv-infusion" and (args.tinf is None or args.tinf <= 0):
        print("error: --route iv-infusion needs --tinf", file=sys.stderr)
        return EXIT_INPUT

    rows = read_table(args.input)
    require_columns(rows, [args.time_column, args.conc_column], str(args.input))
    subjects = group_by(rows, args.subject_column) if args.subject_column in rows[0] else {"": rows}

    report = Report()
    report.note(f"weighting: {args.weight} ({WEIGHTS[args.weight]})")
    report.note("parameters estimated on the log scale; intervals are local Gauss-Newton approximations, not profile likelihood intervals")
    report.note("Observed-concentration weights can bias estimates; compare error models. AIC/BIC here are weighted-SSR scores, conditional on fixed weights. Compartment F p-values are exploratory: boundary/nonidentifiability invalidate a general nominal F-test.")
    if args.route == "oral":
        report.note(
            "extravascular data alone identify CL/F and V/F, never CL and V separately. "
            "Bioavailability requires an intravenous reference."
        )

    models = [m.strip() for m in args.compare.split(",")] if args.compare else [args.model]
    for name in models:
        if name not in MODELS:
            raise InputError(f"unknown model {name!r}; choose from {', '.join(sorted(MODELS))}")

    for subject, subject_rows in subjects.items():
        time = np.asarray([parse_float(r[args.time_column], "time") for r in subject_rows], dtype=float)
        conc = np.asarray([parse_float(r[args.conc_column], "conc") for r in subject_rows], dtype=float)
        order = np.argsort(time)
        time, conc = time[order], conc[order]
        keep = conc > 0
        if np.sum(keep) < len(conc):
            report.note(f"subject {subject or '1'}: dropped {int(np.sum(~keep))} non-positive concentration(s)")
        time, conc = time[keep], conc[keep]

        fits = {}
        for name in models:
            spec = FitSpec(
                model=name,
                route=args.route,
                dose=args.dose,
                tinf=args.tinf,
                interval=args.interval,
                n_doses=args.n_doses,
                absorption=args.absorption,
                estimate_lag=args.lag,
            )
            fits[name] = _fit_and_report(spec, args, subject, time, conc, report)

        if len(models) > 1:
            comparison = []
            ordered = sorted(fits.items(), key=lambda kv: kv[1].p)
            for index, (name, fit) in enumerate(ordered):
                entry = {"model": name, "parameters": fit.p, "wssr": fit.wssr, "aic": fit.aic, "bic": fit.bic}
                if index > 0:
                    simpler_name, simpler = ordered[index - 1]
                    d_p = fit.p - simpler.p
                    if d_p > 0 and fit.wssr > 0 and fit.n - fit.p > 0:
                        f_stat = ((simpler.wssr - fit.wssr) / d_p) / (fit.wssr / (fit.n - fit.p))
                        entry["f_vs_simpler"] = f_stat
                        entry["f_p_value"] = float(1.0 - f_dist.cdf(f_stat, d_p, fit.n - fit.p)) if f_stat > 0 else 1.0
                        entry["compared_with"] = simpler_name
                comparison.append(entry)
            report.table(f"subject {subject or '1'}: model comparison", comparison)
            best = min(fits.items(), key=lambda kv: kv[1].aic)[0]
            report.note(
                f"subject {subject or '1'}: lowest AIC is {best}. AIC and BIC are comparable here only "
                "because every candidate was fitted to the same observations with the same weighting."
            )

    return report.emit(args.format)


if __name__ == "__main__":
    raise SystemExit(main_wrapper(run))
