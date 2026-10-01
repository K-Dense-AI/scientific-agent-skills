#!/usr/bin/env python3
"""Compare two analytical procedures for a transfer, bridging, or bias study.

Uses the regressions that belong to method comparison -- Deming and
Passing-Bablok, which allow error in both measurements -- rather than ordinary
least squares, which assumes the comparative procedure is error-free and biases
the slope toward zero. Adds Bland-Altman agreement and, most importantly, a TOST
equivalence test.

The default reflex at a method transfer is a t test, and "p > 0.05, no
significant difference" is then written up as evidence of equivalence. It is not:
failing to detect a difference is not the same as showing there is none, and with
a small transfer dataset that outcome is close to guaranteed. TOST tests the
hypothesis that matters -- that the true difference lies inside a pre-stated
acceptance margin.

    python3 compare_methods.py --input paired.csv --margin 2
    python3 compare_methods.py -i paired.csv --margin 2 --relative --lambda 1.0

Input columns: `reference` and `test` (paired results on the same samples).
An optional `sample` column labels the rows.

Exit codes: 0 equivalence demonstrated at the stated margin, 1 not demonstrated
or other findings, 2 bad input.
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
    bland_altman,
    deming,
    emit,
    finding,
    finite_float,
    fit_linear,
    mean,
    note,
    parse_rows,
    passing_bablok,
    read_input,
    require_columns,
    run_cli,
    t_cdf,
    to_float,
    tost_paired,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two procedures with the statistics method comparison requires."
    )
    parser.add_argument("--input", "-i", help="CSV/TSV/JSON with `reference` and `test`")
    parser.add_argument("--margin", type=finite_float, required=True,
                        help="pre-stated equivalence margin for TOST, in the units of the "
                             "difference (absolute, or %% when --relative is used)")
    parser.add_argument("--relative", action="store_true",
                        help="work in percent differences relative to the pair mean")
    parser.add_argument("--lambda", dest="lambda_ratio", type=finite_float, default=1.0,
                        help="Deming error-variance ratio var(y error)/var(x error) -- test "
                             "procedure over comparative procedure. Default 1.0 means equal "
                             "precision. Estimate it as (SD of y replicates / SD of x "
                             "replicates) squared")
    parser.add_argument("--alpha", type=finite_float, default=0.05,
                        help="one-sided alpha for TOST (default 0.05)")
    parser.add_argument("--slope-tolerance", type=finite_float, default=None,
                        help="flag when the slope CI excludes 1 +/- this amount")
    add_common_args(parser)
    args = parser.parse_args()

    if args.slope_tolerance is not None and args.slope_tolerance < 0:
        raise InputError("--slope-tolerance must be non-negative")
    rows = parse_rows(read_input(args.input), args.input)
    require_columns(rows, ["reference", "test"])
    ref = [to_float(r["reference"], "reference", i) for i, r in enumerate(rows)]
    test = [to_float(r["test"], "test", i) for i, r in enumerate(rows)]
    n = len(ref)
    if n < 3:
        raise InputError("method comparison needs at least 3 paired results")

    findings: list[str] = []

    # Agreement.
    ba = bland_altman(ref, test, relative=args.relative)
    unit = "%" if args.relative else "units"

    # TOST on the differences that Bland-Altman used.
    if args.relative:
        diffs = [
            100.0 * (t - r) / (0.5 * (r + t)) for r, t in zip(ref, test)
        ]
    else:
        diffs = [t - r for r, t in zip(ref, test)]
    tost = tost_paired(diffs, args.margin, args.alpha)

    # The naive test, computed only to show what it does not establish.
    d_mean = mean(diffs)
    sd = ba["sd_differences"]
    se = sd / math.sqrt(n) if sd > 0 else float("nan")
    t_stat = d_mean / se if se and math.isfinite(se) and se > 0 else float("nan")
    p_naive = (
        2.0 * (1.0 - t_cdf(abs(t_stat), n - 1)) if math.isfinite(t_stat) else float("nan")
    )

    # Regressions.
    ols = fit_linear(ref, test)
    dem = deming(ref, test, args.lambda_ratio)
    try:
        pb = passing_bablok(ref, test)
    except InputError as exc:
        pb = None
        note(f"Passing-Bablok not computed: {exc}")

    summary = [
        {"statistic": "n pairs", "value": n},
        {"statistic": f"mean difference ({unit})", "value": ba["bias"]},
        {"statistic": "difference 95% CI", "value":
            f"{ba['bias_ci95'][0]:.6g} to {ba['bias_ci95'][1]:.6g}"},
        {"statistic": f"SD of differences ({unit})", "value": sd},
        {"statistic": "limits of agreement", "value":
            f"{ba['loa_lower']:.6g} to {ba['loa_upper']:.6g}"},
        {"statistic": "LoA 95% CI half-width", "value": ba["loa_ci95_halfwidth"]},
        {"statistic": "--- equivalence ---", "value": ""},
        {"statistic": "TOST margin", "value": args.margin},
        {"statistic": "TOST p-value", "value": tost["p_value"]},
        {"statistic": f"{100 * (1 - 2 * args.alpha):.0f}% CI (TOST)", "value":
            f"{tost['ci_1_minus_2alpha'][0]:.6g} to {tost['ci_1_minus_2alpha'][1]:.6g}"},
        {"statistic": "equivalent at stated margin", "value": tost["equivalent"]},
        {"statistic": "--- for contrast only ---", "value": ""},
        {"statistic": "paired t-test p (NOT equivalence)", "value": p_naive},
        {"statistic": "--- regressions ---", "value": ""},
        {"statistic": "OLS slope (biased here)", "value": ols.slope},
        {"statistic": "Deming slope", "value": dem["slope"]},
        {"statistic": "Deming slope 95% CI", "value":
            f"{dem['slope_ci95'][0]:.6g} to {dem['slope_ci95'][1]:.6g}"},
        {"statistic": "Deming intercept", "value": dem["intercept"]},
    ]
    if pb:
        summary += [
            {"statistic": "Passing-Bablok slope", "value": pb["slope"]},
            {"statistic": "Passing-Bablok slope 95% CI", "value":
                f"{pb['slope_ci95'][0]:.6g} to {pb['slope_ci95'][1]:.6g}"},
            {"statistic": "Passing-Bablok intercept", "value": pb["intercept"]},
        ]

    prop = ba.get("proportional_bias")
    if prop and math.isfinite(prop.get("p_value", float("nan"))):
        summary.append(
            {"statistic": "proportional bias p (difference vs mean)", "value": prop["p_value"]}
        )
        if prop["p_value"] < 0.05:
            findings.append(
                f"the difference trends with concentration (slope {prop['slope']:.4g}, "
                f"p={prop['p_value']:.4g}): a single mean bias does not describe the "
                "disagreement, and limits of agreement are misleading"
            )

    if not tost["equivalent"]:
        findings.append(
            f"equivalence NOT demonstrated at +/-{args.margin:g} {unit}: the "
            f"{100 * (1 - 2 * args.alpha):.0f}% CI "
            f"({tost['ci_1_minus_2alpha'][0]:.4g}, {tost['ci_1_minus_2alpha'][1]:.4g}) is not "
            f"contained in the margin"
        )

    if args.slope_tolerance is not None:
        lo, hi = dem["slope_ci95"]
        target_lo, target_hi = 1.0 - args.slope_tolerance, 1.0 + args.slope_tolerance
        if not (math.isfinite(lo) and math.isfinite(hi)) or lo < target_lo or hi > target_hi:
            findings.append(
                f"Deming slope 95% CI ({lo:.4g}, {hi:.4g}) is not contained in "
                f"({target_lo:g}, {target_hi:g})"
            )

    if args.format == "json":
        emit([{"summary": {r["statistic"]: r["value"] for r in summary
                           if not r["statistic"].startswith("---")},
               "bland_altman": ba, "deming": dem,
               "passing_bablok": pb, "tost": tost,
               "ols_slope": ols.slope, "paired_t_p_value": p_naive,
               "findings": findings}], "json")
    else:
        emit(summary, args.format)

    if math.isfinite(p_naive) and p_naive > 0.05 and not tost["equivalent"]:
        note(
            f"the paired t-test gives p={p_naive:.4g}, which would often be written up as "
            "'no significant difference'. TOST shows equivalence is NOT established at the "
            "stated margin. Absence of a detected difference is not evidence of equivalence"
        )
    note(
        "OLS treats reference values as fixed without error; appreciable reference error can "
        "attenuate the slope. Choose a regression consistent with the error model"
    )
    note(
        "the equivalence margin must be pre-stated from the specification or the analytical "
        "target profile, never chosen after seeing the data"
    )
    for f in findings:
        finding(f)
    if not findings:
        note("no findings against the checks that were run")
    note("this tool does not decide that a transfer or comparison passes")
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    run_cli(main)
