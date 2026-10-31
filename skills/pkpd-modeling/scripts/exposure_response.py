#!/usr/bin/env python3
"""Exposure-response analysis: Emax, logistic, concentration-QTc, and exposure quartiles.

Exposure-response is where dose selection is actually decided, and where the
most consequential statistical mistakes are made. Two dominate. The first is
fitting Emax to data that never approached the plateau, which produces an Emax
and EC50 that are individually meaningless but jointly reproduce the observed
slope. The second is reading an exposure-response relationship causally when
exposure is itself a consequence of the patient's condition — sicker patients
clear drug differently, so a flat or inverted E-R curve can be confounding
rather than pharmacology.

    python3 exposure_response.py --emax -i er.csv
    python3 exposure_response.py --logistic -i er.csv --response-column responder
    python3 exposure_response.py --cqtc -i qt.csv --cmax 250
    python3 exposure_response.py --quartiles -i er.csv --response-column response

Default columns are ``exposure`` and ``response``.
"""

from __future__ import annotations

import argparse
import math
from typing import Sequence

import numpy as np

from _common import (
    InputError,
    Report,
    add_format_argument,
    main_wrapper,
    parse_float,
    read_table,
    require_columns,
)

try:
    from scipy.optimize import least_squares, minimize
    from scipy.stats import norm
    from scipy.stats import t as t_dist
except ImportError as exc:  # pragma: no cover
    raise SystemExit("exposure_response.py needs scipy: uv pip install scipy") from exc

# ICH E14's threshold of regulatory concern: an upper bound of the two-sided
# 90% confidence interval for placebo-corrected change-from-baseline QTc above
# 10 ms.
QTC_THRESHOLD_MS = 10.0


def fit_emax(exposure: np.ndarray, response: np.ndarray, sigmoid: bool) -> dict:
    """Fit E0 + Emax*C^h/(EC50^h + C^h) by least squares on the log of positive parameters."""
    if len(exposure) <= (4 if sigmoid else 3) or np.ptp(exposure) <= 0:
        raise InputError("Emax needs more observations than parameters and varied exposures")
    e0_init = float(np.min(response))
    emax_init = float(np.max(response) - np.min(response)) or 1.0
    ec50_init = float(np.median(exposure[exposure > 0])) if np.any(exposure > 0) else 1.0

    def unpack(theta: np.ndarray) -> tuple[float, float, float, float]:
        e0 = theta[0]
        emax_value = theta[1]
        ec50 = math.exp(theta[2])
        hill = math.exp(theta[3]) if sigmoid else 1.0
        return e0, emax_value, ec50, hill

    def predict(theta: np.ndarray, x: np.ndarray) -> np.ndarray:
        e0, emax_value, ec50, hill = unpack(theta)
        # Logistic evaluation avoids overflow of C**hill and EC50**hill.
        z = hill * (np.log(np.maximum(x, np.finfo(float).tiny)) - math.log(ec50))
        fraction = np.exp(-np.logaddexp(0.0, -z))
        return e0 + emax_value * np.where(x > 0, fraction, 0.0)

    start = [e0_init, emax_init, math.log(max(ec50_init, 1e-9))] + ([0.0] if sigmoid else [])
    result = least_squares(lambda th: predict(th, exposure) - response, start, max_nfev=20000)
    e0, emax_value, ec50, hill = unpack(result.x)

    n, p = len(exposure), len(result.x)
    residuals = response - predict(result.x, exposure)
    ssr = float(np.sum(residuals**2))
    sigma2 = ssr / max(n - p, 1)
    try:
        _, s, vt = np.linalg.svd(result.jac, full_matrices=False)
        threshold = np.finfo(float).eps * max(result.jac.shape) * s[0]
        if np.count_nonzero(s > threshold) < p:
            raise np.linalg.LinAlgError("rank-deficient Emax sensitivity")
        s_inv = 1.0 / s
        cov = (vt.T * s_inv**2) @ vt * sigma2
        se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    except np.linalg.LinAlgError:  # pragma: no cover
        se = np.full(p, np.nan)

    max_observed = float(np.max(exposure))
    return {
        "converged": bool(result.success),
        "identifiable_local_covariance": bool(np.all(np.isfinite(se))),
        "e0": e0,
        "emax": emax_value,
        "ec50": ec50,
        "hill": hill,
        "se_e0": float(se[0]),
        "se_emax": float(se[1]),
        "rse_ec50_pct": 100.0 * float(se[2]),
        "rse_hill_pct": 100.0 * float(se[3]) if sigmoid else float("nan"),
        "residual_sd": math.sqrt(sigma2),
        "n": n,
        "max_observed_exposure": max_observed,
        "ec50_over_max_exposure": ec50 / max_observed if max_observed else float("nan"),
        "predicted_effect_at_max_exposure": float(predict(result.x, np.array([max_observed]))[0]),
        "fraction_of_emax_reached": float(
            (predict(result.x, np.array([max_observed]))[0] - e0) / emax_value
        )
        if emax_value
        else float("nan"),
    }


def fit_logistic(exposure: np.ndarray, response: np.ndarray) -> dict:
    """Maximum-likelihood logistic regression of a binary response on exposure."""
    unique = set(np.unique(response).tolist())
    if not unique <= {0.0, 1.0}:
        raise InputError("logistic exposure-response needs a 0/1 response column")

    if unique != {0.0, 1.0} or np.ptp(exposure) <= 0:
        raise InputError("logistic regression needs both outcomes and varied exposures")
    zero, one = exposure[response == 0], exposure[response == 1]
    if zero.max() <= one.min() or one.max() <= zero.min():
        raise InputError("complete or quasi-complete separation: unpenalized logistic slope is not finite")

    def neg_loglik(theta: np.ndarray) -> float:
        eta = theta[0] + theta[1] * exposure
        # log(1+exp(eta)) computed stably
        return float(np.sum(np.logaddexp(0.0, eta) - response * eta))

    result = minimize(neg_loglik, np.array([0.0, 0.0]), method="BFGS")
    intercept, slope = result.x
    try:
        cov = result.hess_inv
        se = np.sqrt(np.maximum(np.diag(np.asarray(cov)), 0.0))
    except (ValueError, TypeError):  # pragma: no cover
        se = np.array([float("nan"), float("nan")])

    ec50 = -intercept / slope if slope else float("nan")
    return {
        "converged": bool(result.success),
        "intercept": float(intercept),
        "slope": float(slope),
        "se_slope": float(se[1]),
        "slope_z": float(slope / se[1]) if se[1] else float("nan"),
        "slope_p": float(2 * (1 - norm.cdf(abs(slope / se[1])))) if se[1] else float("nan"),
        "odds_ratio_per_unit": float(math.exp(slope)),
        "exposure_at_50pct_probability": float(ec50),
        "n": len(exposure),
        "n_responders": int(response.sum()),
        "neg_loglik": float(result.fun),
    }


def fit_cqtc(conc: np.ndarray, delta_qtc: np.ndarray, cmax: float | None) -> dict:
    """Linear concentration-QTc model with the two-sided 90% CI of the predicted effect.

    ICH E14 asks whether the **upper bound of the two-sided 90% confidence
    interval** for placebo-corrected change-from-baseline QTc is below 10 ms at
    the clinically relevant exposure. Reporting the point estimate, or a 95%
    interval, answers a different question than the guideline asks.
    """
    n = len(conc)
    if n < 4:
        raise InputError("concentration-QTc analysis needs at least 4 observations")
    if np.ptp(conc) <= 0:
        raise InputError("concentration-QTc needs varied concentrations")
    design = np.column_stack([np.ones(n), conc])
    coefficients, *_ = np.linalg.lstsq(design, delta_qtc, rcond=None)
    fitted = design @ coefficients
    residuals = delta_qtc - fitted
    dof = n - 2
    sigma2 = float(residuals @ residuals) / dof
    xtx_inv = np.linalg.inv(design.T @ design)
    se = np.sqrt(np.diag(xtx_inv) * sigma2)
    crit = float(t_dist.ppf(0.95, dof))  # two-sided 90%

    out = {
        "intercept_ms": float(coefficients[0]),
        "slope_ms_per_conc": float(coefficients[1]),
        "se_slope": float(se[1]),
        "slope_ci90_low": float(coefficients[1] - crit * se[1]),
        "slope_ci90_high": float(coefficients[1] + crit * se[1]),
        "residual_sd_ms": math.sqrt(sigma2),
        "n": n,
        "degrees_of_freedom": dof,
    }
    if cmax is not None:
        x0 = np.array([1.0, cmax])
        prediction = float(x0 @ coefficients)
        se_mean = math.sqrt(float(x0 @ xtx_inv @ x0) * sigma2)
        out.update(
            {
                "exposure_evaluated": cmax,
                "predicted_delta_delta_qtc_ms": prediction,
                "ci90_low_ms": prediction - crit * se_mean,
                "ci90_high_ms": prediction + crit * se_mean,
                "upper_bound_exceeds_10ms": float((prediction + crit * se_mean) >= QTC_THRESHOLD_MS),
            }
        )
        if cmax > float(np.max(conc)) or cmax < float(np.min(conc)):
            out["extrapolated_beyond_observed"] = 1.0
    return out


def quartile_summary(exposure: np.ndarray, response: np.ndarray, n_bins: int) -> list[dict]:
    edges = np.quantile(exposure, np.linspace(0, 1, n_bins + 1))
    edges[-1] = np.nextafter(edges[-1], np.inf)
    rows = []
    for i in range(n_bins):
        mask = (exposure >= edges[i]) & (exposure < edges[i + 1])
        if not np.any(mask):
            continue
        values = response[mask]
        rows.append(
            {
                "bin": i + 1,
                "exposure_range": f"{edges[i]:.4g} - {edges[i + 1]:.4g}",
                "n": int(mask.sum()),
                "median_exposure": float(np.median(exposure[mask])),
                "mean_response": float(values.mean()),
                "sd_response": float(values.std(ddof=1)) if len(values) > 1 else float("nan"),
                "responder_fraction": float(values.mean()) if set(np.unique(values).tolist()) <= {0.0, 1.0} else float("nan"),
            }
        )
    return rows


# --------------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exposure-response modelling: Emax, logistic, concentration-QTc, quartiles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--emax", action="store_true")
    parser.add_argument("--sigmoid", action="store_true", help="estimate the Hill coefficient too")
    parser.add_argument("--logistic", action="store_true")
    parser.add_argument("--cqtc", action="store_true")
    parser.add_argument("--quartiles", action="store_true")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("--exposure-column", default="exposure")
    parser.add_argument("--response-column", default="response")
    parser.add_argument("--cmax", type=float, help="exposure at which to evaluate the C-QTc prediction")
    parser.add_argument("--bins", type=int, default=4)
    add_format_argument(parser)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from _common import validate_numeric_args
    validate_numeric_args(args)
    if args.bins < 1 or (args.cmax is not None and args.cmax < 0):
        raise InputError("--bins must be positive and --cmax non-negative")
    modes = [m for m in ("emax", "logistic", "cqtc", "quartiles") if getattr(args, m)]
    if len(modes) != 1:
        raise InputError("choose exactly one of --emax, --logistic, --cqtc, --quartiles")

    rows = read_table(args.input)
    require_columns(rows, [args.exposure_column, args.response_column], str(args.input))
    exposure = np.asarray([parse_float(r[args.exposure_column], "exposure") for r in rows], dtype=float)
    response = np.asarray([parse_float(r[args.response_column], "response") for r in rows], dtype=float)
    if np.any(exposure < 0):
        raise InputError("exposure must not be negative")

    report = Report()
    report.note(
        "Exposure-response is observational even inside a randomised trial: patients are randomised to "
        "dose, not to exposure. Differences across exposure quantiles can reflect the covariates that "
        "drive clearance rather than the drug."
    )

    if args.emax:
        fit = fit_emax(exposure, response, args.sigmoid)
        report.table("Emax model", [{"parameter": k, "value": v} for k, v in fit.items()])
        if fit["fraction_of_emax_reached"] < 0.5:
            report.finding(
                f"the highest observed exposure reaches only {100 * fit['fraction_of_emax_reached']:.0f}% "
                "of the estimated Emax. Emax and EC50 are then extrapolations, strongly correlated with "
                "each other, and should not be quoted as independent estimates."
            )
        if fit["ec50_over_max_exposure"] > 1.0:
            report.finding(
                f"EC50 ({fit['ec50']:.4g}) exceeds the highest observed exposure "
                f"({fit['max_observed_exposure']:.4g}); the plateau is entirely outside the data"
            )
        if math.isfinite(fit["rse_ec50_pct"]) and fit["rse_ec50_pct"] > 50:
            report.finding(f"EC50 has {fit['rse_ec50_pct']:.0f}% relative standard error")
        report.note("a linear-looking E-R relationship is the low-concentration limb of an Emax curve; the two are not distinguishable without data near the plateau")

    elif args.logistic:
        fit = fit_logistic(exposure, response)
        report.table("logistic exposure-response", [{"parameter": k, "value": v} for k, v in fit.items()])
        if fit["n_responders"] < 10 or fit["n"] - fit["n_responders"] < 10:
            report.finding(
                f"{fit['n_responders']} responders out of {fit['n']}; with fewer than about 10 events "
                "per covariate the slope estimate is unstable and its confidence interval unreliable"
            )
        if math.isfinite(fit["slope_p"]) and fit["slope_p"] > 0.05:
            report.note(f"the exposure slope is not statistically distinguishable from zero (p = {fit['slope_p']:.3f})")

    elif args.cqtc:
        fit = fit_cqtc(exposure, response, args.cmax)
        report.table("concentration-QTc", [{"parameter": k, "value": v} for k, v in fit.items()])
        report.note(
            "ICH E14 evaluates the upper bound of the two-sided 90% confidence interval for "
            "placebo-corrected change-from-baseline QTc against a 10 ms threshold. The response column "
            "must already be that placebo-corrected change; this script does not compute it."
        )
        if fit.get("upper_bound_exceeds_10ms"):
            report.finding(
                f"the 90% upper bound at the evaluated exposure is {fit['ci90_high_ms']:.2f} ms, above "
                "the 10 ms threshold of regulatory concern"
            )
        if fit.get("extrapolated_beyond_observed"):
            report.finding(
                f"the evaluated exposure ({fit['exposure_evaluated']:.4g}) is above the highest observed "
                "concentration; the prediction is an extrapolation and the interval understates its uncertainty"
            )
        report.note(
            "This is an ordinary linear model. A regulatory C-QTc analysis uses a mixed model with a "
            "random intercept and slope per subject and a treatment-specific intercept; use this for "
            "screening and exploration, not for submission."
        )

    else:
        rows_out = quartile_summary(exposure, response, args.bins)
        report.table(f"exposure {args.bins}-quantile summary", rows_out)
        if len(rows_out) >= 2:
            first, last = rows_out[0]["mean_response"], rows_out[-1]["mean_response"]
            report.scalar("response_change_across_range", last - first)
        report.note(
            "Quantile summaries are descriptive. They do not adjust for the covariates that determine "
            "exposure, and a monotone trend across quantiles is not by itself evidence of a causal "
            "dose-response relationship."
        )

    if (args.emax or args.logistic) and not fit["converged"]:
        report.finding("optimizer did not converge; estimates and Wald intervals are unreliable")
    if args.emax and not fit["identifiable_local_covariance"]:
        report.finding("rank-deficient Emax sensitivity; covariance unavailable, use profile likelihood or a simpler model")
    return report.emit(args.format)


if __name__ == "__main__":
    raise SystemExit(main_wrapper(run))
