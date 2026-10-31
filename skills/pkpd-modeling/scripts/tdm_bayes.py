#!/usr/bin/env python3
"""Research MAP fitting for a simple one-compartment prior and fixed IV regimen.

Assumes identical evenly spaced doses, fixed physiology and Gaussian residual
error. The included vancomycin prior is illustrative, not clinically validated.
No posterior interval or patient-specific dose recommendation is provided.

    python3 tdm_bayes.py --custom --cl-pop 5 --v-pop 40 --dose 1000 --interval 12 --level 15@10
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from _common import InputError, Report, add_format_argument, main_wrapper

from _models import build_regimen, disposition, simulate_linear

try:
    from scipy.optimize import minimize
except ImportError as exc:  # pragma: no cover
    raise SystemExit("tdm_bayes.py needs scipy: uv pip install scipy") from exc


@dataclass
class PopulationModel:
    name: str
    description: str
    cl_pop: float          # L/h at the reference covariates
    v_pop: float           # L
    omega_cl: float        # apparent CV of between-subject variability
    omega_v: float
    prop_error: float
    add_error: float
    target: str
    reference: str

    def individualise(self, weight: float | None, crcl: float | None) -> tuple[float, float]:
        return self.cl_pop, self.v_pop


@dataclass
class VancomycinAdult(PopulationModel):
    def individualise(self, weight: float | None, crcl: float | None) -> tuple[float, float]:
        if weight is None or crcl is None:
            raise InputError("the vancomycin model needs --weight and --crcl")
        # A conventional two-covariate adult parameterisation: clearance
        # proportional to creatinine clearance, volume proportional to weight.
        return 0.048 * crcl, 0.72 * weight


LIBRARY: dict[str, PopulationModel] = {
    "vancomycin-adult": VancomycinAdult(
        name="vancomycin-adult",
        description="Adult vancomycin, one compartment, CL from creatinine clearance and V from weight",
        cl_pop=3.6,
        v_pop=58.0,
        omega_cl=0.27,
        omega_v=0.25,
        prop_error=0.15,
        add_error=1.0,
        target="AUC24/MIC 400-600 with an assumed MIC of 1 mg/L (2020 consensus guideline)",
        reference="illustrative parameterisation - substitute the model validated for your population",
    ),
}


def map_estimate(
    model: PopulationModel,
    cl_prior: float,
    v_prior: float,
    dose: float,
    interval: float,
    n_doses: int,
    infusion: float,
    levels: list[tuple[float, float]],
) -> dict:
    """Minimise the MAP objective: weighted residuals plus the prior penalty.

    The objective is ``sum((obs - pred)^2 / var_i) + sum(eta_k^2 / omega_k^2)``.
    The second term is what makes this Bayesian rather than a two-point fit,
    and it is the reason a single trough can still yield a usable individual
    estimate.
    """
    last_dose_time = (n_doses - 1) * interval

    def predict(eta: np.ndarray, times: np.ndarray) -> np.ndarray:
        cl = cl_prior * math.exp(eta[0])
        v = v_prior * math.exp(eta[1])
        disp = disposition(cl, v)
        regimen = build_regimen(dose, interval=interval, n_doses=n_doses, duration=infusion)
        return simulate_linear(times + last_dose_time, regimen, disp)

    times = np.asarray([t for _, t in levels], dtype=float)
    observed = np.asarray([c for c, _ in levels], dtype=float)

    def objective(eta: np.ndarray) -> float:
        predicted = predict(eta, times)
        variance = (model.prop_error * predicted) ** 2 + model.add_error**2
        residual = float(np.sum((observed - predicted) ** 2 / variance + np.log(variance)))
        prior = float((eta[0] / model.omega_cl) ** 2 + (eta[1] / model.omega_v) ** 2)
        return residual + prior

    best = minimize(objective, np.zeros(2), method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
    eta = best.x
    cl = cl_prior * math.exp(eta[0])
    v = v_prior * math.exp(eta[1])
    predicted = predict(eta, times)
    return {
        "cl_individual": cl,
        "v_individual": v,
        "eta_cl": float(eta[0]),
        "eta_v": float(eta[1]),
        "cl_fold_vs_population": cl / cl_prior,
        "v_fold_vs_population": v / v_prior,
        "half_life": math.log(2.0) * v / cl,
        "objective": float(best.fun),
        "predictions": predicted,
        "observed": observed,
        "times": times,
        "converged": bool(best.success),
    }


def exposure_metrics(cl: float, v: float, dose: float, interval: float, infusion: float) -> dict:
    k = cl / v
    accumulation = -math.expm1(-k * interval)
    peak = dose / v / accumulation if infusion == 0 else dose / (infusion * cl) * (-math.expm1(-k * infusion)) / accumulation
    trough = peak * math.exp(-k * (interval - infusion))
    auc_tau = dose / cl
    per_day = 24.0 / interval
    return {
        "auc_tau": auc_tau,
        "auc_24h": auc_tau * per_day,
        "cmax_ss": peak,
        "cmin_ss": trough,
        "cavg_ss": auc_tau / interval,
    }


def recommend_dose(cl: float, target_auc24: float) -> float:
    """Model-implied total daily dose under linear steady-state PK, not clinical advice."""
    return target_auc24 * cl


# --------------------------------------------------------------------- CLI


def _level(text: str) -> tuple[float, float]:
    if "@" not in text:
        raise argparse.ArgumentTypeError(f"--level must look like 18.2@11.5 (conc@time), got {text!r}")
    conc_text, time_text = text.split("@", 1)
    try:
        conc, time = float(conc_text), float(time_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"could not parse --level {text!r}") from exc
    if not math.isfinite(conc) or not math.isfinite(time) or conc <= 0 or time < 0:
        raise argparse.ArgumentTypeError("concentration must be positive and time non-negative")
    return conc, time


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MAP Bayesian individualisation of a population PK model from measured levels.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--model", choices=sorted(LIBRARY), help="a bundled population model")
    parser.add_argument("--custom", action="store_true", help="supply population parameters directly")
    parser.add_argument("--cl-pop", type=float)
    parser.add_argument("--v-pop", type=float)
    parser.add_argument("--omega-cl", type=float, default=0.30)
    parser.add_argument("--omega-v", type=float, default=0.25)
    parser.add_argument("--prop-error", type=float, default=0.15)
    parser.add_argument("--add-error", type=float, default=0.5)
    parser.add_argument("--weight", type=float)
    parser.add_argument("--crcl", type=float, help="creatinine clearance, mL/min")
    parser.add_argument("--dose", type=float, required=True)
    parser.add_argument("--interval", type=float, required=True)
    parser.add_argument("--infusion", type=float, default=1.0, help="infusion duration, h (default: 1)")
    parser.add_argument("--doses-given", type=int, default=20, help="doses administered before the levels (default: 20)")
    parser.add_argument("--level", type=_level, action="append", required=True, help="conc@time-after-last-dose")
    parser.add_argument("--target-auc24", type=float, help="target AUC24 for an illustrative dose calculation")
    add_format_argument(parser)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from _common import validate_numeric_args
    validate_numeric_args(args)
    if bool(args.model) == bool(args.custom):
        raise InputError("choose either --model NAME or --custom")
    if args.custom:
        if args.cl_pop is None or args.v_pop is None:
            raise InputError("--custom needs --cl-pop and --v-pop")
        model = PopulationModel(
            name="custom",
            description="user-supplied population parameters",
            cl_pop=args.cl_pop,
            v_pop=args.v_pop,
            omega_cl=args.omega_cl,
            omega_v=args.omega_v,
            prop_error=args.prop_error,
            add_error=args.add_error,
            target="",
            reference="user supplied",
        )
        cl_prior, v_prior = args.cl_pop, args.v_pop
    else:
        model = LIBRARY[args.model]
        cl_prior, v_prior = model.individualise(args.weight, args.crcl)

    if cl_prior <= 0 or v_prior <= 0 or model.omega_cl <= 0 or model.omega_v <= 0:
        raise InputError("population CL, V and log-scale omega SDs must be positive")
    if model.prop_error < 0 or model.add_error <= 0:
        raise InputError("proportional error must be non-negative and additive SD positive")
    if args.doses_given < 1 or args.infusion < 0 or (args.target_auc24 is not None and args.target_auc24 <= 0):
        raise InputError("invalid dose count, infusion duration or target AUC")
    if args.interval <= 0 or args.dose <= 0:
        raise InputError("dose and interval must be positive")
    if args.infusion >= args.interval:
        raise InputError("infusion duration must be shorter than the dosing interval")
    for _, time in args.level:
        if time > args.interval:
            raise InputError(f"a level at {time} h is beyond the {args.interval} h dosing interval")

    result = map_estimate(
        model, cl_prior, v_prior, args.dose, args.interval, args.doses_given, args.infusion, args.level
    )

    report = Report()
    report.scalar("model", model.name)
    report.scalar("doses_given", args.doses_given)
    report.note("Levels use hours after the latest dose START; history is identical evenly spaced IV doses. Default 20 doses does not guarantee steady state. No posterior intervals or clinical model validation are provided.")
    report.scalar("population_cl", cl_prior)
    report.scalar("population_v", v_prior)
    report.scalar("individual_cl", result["cl_individual"])
    report.scalar("individual_v", result["v_individual"])
    report.scalar("eta_cl", result["eta_cl"])
    report.scalar("eta_v", result["eta_v"])
    report.scalar("individual_half_life", result["half_life"])

    report.table(
        "observed vs individual prediction",
        [
            {
                "time_after_dose": float(t),
                "observed": float(o),
                "predicted": float(p),
                "residual": float(o - p),
                "pct_error": 100.0 * (o - p) / o if o else float("nan"),
            }
            for t, o, p in zip(result["times"], result["observed"], result["predictions"])
        ],
    )

    current = exposure_metrics(result["cl_individual"], result["v_individual"], args.dose, args.interval, args.infusion)
    report.table("predicted exposure on the current regimen", [{"metric": k, "value": v} for k, v in current.items()])

    if args.target_auc24:
        daily = recommend_dose(result["cl_individual"], args.target_auc24)
        per_dose = daily / (24.0 / args.interval)
        report.scalar("target_auc24", args.target_auc24)
        report.scalar("model_target_total_daily_dose", daily)
        report.scalar("model_target_dose_per_interval", per_dose)
        report.note(
            "The model target calculation assumes linear pharmacokinetics, so AUC scales exactly with dose. "
            "It says nothing about whether the target itself is right for this patient."
        )

    if abs(result["eta_cl"]) > 2 * model.omega_cl:
        report.finding(
            f"the individual clearance is {result['cl_fold_vs_population']:.2f}-fold the population "
            f"value (eta = {result['eta_cl']:+.2f}, more than 2 omega). Either this patient is genuinely "
            "atypical, or a level was drawn at a mis-recorded time, or the population model does not "
            "apply to them. Check the sampling times before acting on the estimate."
        )
    if len(args.level) == 1:
        report.finding(
            "a single concentration cannot separate clearance from volume; the estimate of whichever "
            "parameter the sample is uninformative about has simply been pulled back to the population value"
        )
    trough_only = all(time > 0.7 * args.interval for _, time in args.level)
    if trough_only and len(args.level) > 1:
        report.note(
            "all levels are late in the interval, so volume is weakly identified. A peak (1-2 h after "
            "the end of the infusion) plus a trough constrains both parameters."
        )
    if not result["converged"]:
        report.finding("the MAP optimiser did not converge; treat the individual estimates as unreliable")

    if model.target:
        report.note(f"target: {model.target}")
    report.note(f"population model provenance: {model.reference}")
    report.note(
        "This is a modelling aid, not a dosing decision. Any change to a patient's regimen is the "
        "responsibility of the treating clinician and depends on the clinical picture, the assay, the "
        "organism, and local protocol."
    )
    return report.emit(args.format)


if __name__ == "__main__":
    raise SystemExit(main_wrapper(run))
