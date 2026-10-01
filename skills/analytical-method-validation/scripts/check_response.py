#!/usr/bin/env python3
"""Evaluate a calibration response (linearity) the way ICH Q2(R2) 3.2.2 asks.

Reports what the guideline asks to be reported -- slope, intercept, coefficient
of determination, and an analysis of the deviation of points from the line --
and adds the diagnostics that actually detect an unsuitable model: a lack-of-fit
F test against pure error, a runs test on residual signs, back-calculated
relative error per level, and a heteroscedasticity check that tells you whether
weighting is needed.

    python3 check_response.py --input calib.csv
    python3 check_response.py --input calib.csv --weight 1/x2 --levels-required 5
    python3 check_response.py --input calib.csv --max-back-calc-error 5 --format json

Input columns: `level` (nominal concentration or %) and `response` (signal).
An optional `replicate` column is ignored -- replicates are simply repeated rows
at the same level, which is what enables the lack-of-fit test.

Exit codes: 0 no findings, 1 findings raised, 2 bad input.
"""

from __future__ import annotations

import argparse
import math
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    EXIT_FINDINGS,
    EXIT_OK,
    InputError,
    add_common_args,
    emit,
    finding,
    finite_float,
    fit_linear,
    heteroscedasticity,
    lack_of_fit,
    mean,
    note,
    parse_rows,
    read_input,
    require_columns,
    run_cli,
    runs_test,
    to_float,
)

WEIGHT_SCHEMES = {
    "none": lambda x: 1.0,
    "1/x": lambda x: 1.0 / abs(x) if x != 0 else 0.0,
    "1/x2": lambda x: 1.0 / (x * x) if x != 0 else 0.0,
}


def build_weights(xs: list[float], scheme: str) -> list[float] | None:
    if scheme == "none":
        return None
    fn = WEIGHT_SCHEMES[scheme]
    if any(x == 0 for x in xs):
        raise InputError(f"weighting {scheme} needs non-zero levels; a zero level was supplied")
    return [fn(x) for x in xs]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a calibration response for linearity.")
    parser.add_argument("--input", "-i", help="CSV/TSV/JSON file, or '-' for stdin")
    parser.add_argument("--weight", choices=sorted(WEIGHT_SCHEMES), default="none",
                        help="calibration weighting (default: none)")
    parser.add_argument("--levels-required", type=int, default=5,
                        help="minimum distinct levels expected (Q2(R2) recommends 5)")
    parser.add_argument("--max-back-calc-error", type=finite_float, default=None,
                        help="flag any level whose mean back-calculated error exceeds this %%")
    parser.add_argument("--alpha", type=finite_float, default=0.05,
                        help="significance level for lack-of-fit and runs tests")
    parser.add_argument("--through-origin-tolerance", type=finite_float, default=None,
                        help="flag when the intercept exceeds this %% of the response at the "
                             "highest level (a proxy for the y-intercept significance check)")
    add_common_args(parser)
    args = parser.parse_args()

    if not 0 < args.alpha < 1:
        raise InputError("--alpha must be between 0 and 1")
    if args.levels_required < 3:
        raise InputError("--levels-required must be at least 3")
    for value in (args.max_back_calc_error, args.through_origin_tolerance):
        if value is not None and value < 0:
            raise InputError("error/intercept limits must be non-negative")

    rows = parse_rows(read_input(args.input), args.input)
    require_columns(rows, ["level", "response"])
    xs = [to_float(r["level"], "level", i) for i, r in enumerate(rows)]
    ys = [to_float(r["response"], "response", i) for i, r in enumerate(rows)]

    weights = build_weights(xs, args.weight)
    fit = fit_linear(xs, ys, weights)
    distinct = sorted({round(x, 12) for x in xs})

    findings: list[str] = []

    # Q2(R2) 3.2.2.1: a minimum of five concentrations is recommended.
    if len(distinct) < args.levels_required:
        findings.append(
            f"{len(distinct)} distinct levels; Q2(R2) 3.2.2.1 recommends at least "
            f"{args.levels_required} appropriately distributed across the range"
        )

    lof = lack_of_fit(xs, ys, fit)
    runs = runs_test([r for _, r in sorted(zip(xs, fit.residuals), key=lambda pair: pair[0])])
    het = heteroscedasticity(xs, fit.residuals)

    if lof.get("applicable") and lof["p_value"] < args.alpha:
        findings.append(
            f"lack-of-fit F={lof['f_statistic']:.3f} on {lof['df_lack_of_fit']}/"
            f"{lof['df_pure_error']} df, p={lof['p_value']:.4g}: the straight line does not "
            "describe the data beyond replicate scatter"
        )
    if math.isfinite(runs.get("p_value", float("nan"))) and runs["p_value"] < args.alpha:
        findings.append(
            f"residual signs are non-random (runs={runs['runs']}, expected "
            f"{runs['expected_runs']:.1f}, p={runs['p_value']:.4g}): inspect the residual plot "
            "for curvature"
        )
    if het.get("applicable") and het["variance_ratio_high_over_low"] > 10 and args.weight == "none":
        findings.append(
            f"residual variance is {het['variance_ratio_high_over_low']:.1f}x larger in the top "
            "third of the range than the bottom, and the fit is unweighted: back-calculated "
            "results at the low end may be imprecise. Investigate a justified variance model"
        )

    # Back-calculated relative error per level -- the practical test of the model.
    level_rows = []
    by_level: dict[float, list[float]] = {}
    for x, y in zip(xs, ys):
        by_level.setdefault(round(x, 12), []).append(y)
    for level in distinct:
        responses = by_level[level]
        back = [
            (r - fit.intercept) / fit.slope if fit.slope != 0 else float("nan")
            for r in responses
        ]
        mean_back = mean(back)
        rel_err = 100.0 * (mean_back - level) / level if level != 0 else float("nan")
        level_rows.append(
            {
                "level": level,
                "n": len(responses),
                "mean_response": mean(responses),
                "mean_back_calculated": mean_back,
                "relative_error_pct": rel_err,
            }
        )
        if (
            args.max_back_calc_error is not None
            and math.isfinite(rel_err)
            and abs(rel_err) > args.max_back_calc_error
        ):
            findings.append(
                f"level {level:g}: back-calculated mean deviates {rel_err:+.2f}% from nominal, "
                f"outside the stated +/-{args.max_back_calc_error:g}%"
            )

    if args.through_origin_tolerance is not None:
        top_response = fit.predict(max(distinct))
        if top_response != 0:
            pct = 100.0 * abs(fit.intercept) / abs(top_response)
            if pct > args.through_origin_tolerance:
                findings.append(
                    f"intercept is {pct:.2f}% of the response at the highest level, above the "
                    f"stated {args.through_origin_tolerance:g}% tolerance"
                )

    slope_lo, slope_hi = fit.slope_ci()
    int_lo, int_hi = fit.intercept_ci()
    summary = [
        {"statistic": "n points", "value": fit.n},
        {"statistic": "distinct levels", "value": len(distinct)},
        {"statistic": "weighting", "value": args.weight},
        {"statistic": "slope", "value": fit.slope},
        {"statistic": "slope 95% CI", "value": f"{slope_lo:.6g} to {slope_hi:.6g}"},
        {"statistic": "intercept", "value": fit.intercept},
        {"statistic": "intercept 95% CI", "value": f"{int_lo:.6g} to {int_hi:.6g}"},
        {"statistic": "intercept CI includes 0", "value": int_lo <= 0.0 <= int_hi},
        {"statistic": "coefficient of determination (r2)", "value": fit.r_squared},
        {"statistic": "correlation coefficient (r)", "value": fit.r},
        {"statistic": "residual SD", "value": fit.residual_sd},
        {"statistic": "residual df", "value": fit.df},
    ]
    if lof.get("applicable"):
        summary += [
            {"statistic": "lack-of-fit F", "value": lof["f_statistic"]},
            {"statistic": "lack-of-fit p", "value": lof["p_value"]},
        ]
    else:
        summary.append(
            {"statistic": "lack-of-fit test", "value": f"not run ({lof.get('reason', '')})"}
        )
    summary += [
        {"statistic": "runs test p", "value": runs.get("p_value", float("nan"))},
        {
            "statistic": "residual SD ratio (high/low third)",
            "value": het.get("sd_ratio", float("nan")),
        },
    ]

    if args.format == "json":
        emit(
            [
                {
                    "summary": {r["statistic"]: r["value"] for r in summary},
                    "levels": level_rows,
                    "findings": findings,
                }
            ],
            "json",
        )
    else:
        emit(summary, args.format)
        print()
        emit(level_rows, args.format)

    note(
        "Q2(R2) 3.2.2.1 asks for the plot, r or r-squared, intercept, slope, and an analysis of "
        "the deviation of points from the line"
    )
    note(
        "r-squared alone does not demonstrate linearity: it rises with range and is insensitive "
        "to curvature. The lack-of-fit test and the residual pattern are the evidence"
    )
    if args.weight != "none" and lof.get("applicable"):
        note(
            f"weighted lack-of-fit uses {args.weight} in both residual and pure-error sums; "
            "its F reference assumes independent normal errors with variance proportional "
            "to inverse weight. The weights need independent scientific justification"
        )
    if not lof.get("applicable"):
        note(
            f"lack-of-fit was not assessed: {lof.get('reason', 'unavailable')}"
        )
    for f in findings:
        finding(f)
    if not findings:
        note("no findings against the checks that were run")
    note("this tool does not decide that the calibration model is acceptable")
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    run_cli(main)
