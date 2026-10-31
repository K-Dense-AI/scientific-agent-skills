#!/usr/bin/env python3
"""Estimate DL and QL with supported approaches from ICH Q2(R2) 3.2.3.

Supported estimates can disagree because they use different response-variation
data. Reporting one number without naming the approach is the finding an
assessor raises, so this script computes all of the applicable ones side by side
and checks the answer against the reporting threshold it has to serve.

    # sigma from the calibration line, slope from the same fit
    python3 check_detection_limits.py --calibration calib.csv

    # sigma from blank responses
    python3 check_detection_limits.py --calibration calib.csv --blanks blanks.csv

    # confirm an estimated QL with real data at that level
    python3 check_detection_limits.py --calibration calib.csv \
        --confirm-ql 0.05 --confirm-data ql_check.csv --reporting-threshold 0.05 \
        --confirm-accuracy-limit 10 --confirm-rsd-limit 10

Input:
  --calibration  CSV with `level` and `response` (low-range calibration curve)
  --blanks       CSV with `response` (blank measurements)
  --intercepts   CSV with `intercept` (independent low-range calibration curves)
  --confirm-data CSV with `measured` (results at or near the claimed QL)

Exit codes: 0 no findings, 1 findings raised, 2 bad input.
"""

from __future__ import annotations

import argparse
import math
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from _catalog import DL_QL_APPROACHES  # noqa: E402
from _common import (  # noqa: E402
    EXIT_FINDINGS,
    EXIT_OK,
    InputError,
    add_common_args,
    emit,
    finding,
    finite_float,
    fit_linear,
    mean,
    note,
    parse_rows,
    read_input,
    require_columns,
    rsd_percent,
    run_cli,
    sample_sd,
    to_float,
)

DL_FACTOR = 3.3
QL_FACTOR = 10.0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estimate detection and quantitation limits per ICH Q2(R2) 3.2.3."
    )
    parser.add_argument("--calibration", required=True,
                        help="CSV/TSV/JSON with `level` and `response`")
    parser.add_argument("--blanks", help="CSV/TSV/JSON with `response` for blank samples")
    parser.add_argument("--intercepts", help="CSV/TSV/JSON with `intercept` from independent low-range calibration curves")
    parser.add_argument("--signal-to-noise", type=finite_float, default=None,
                        help="measured S/N at a stated concentration (use with --sn-level)")
    parser.add_argument("--sn-level", type=finite_float, default=None,
                        help="the concentration at which --signal-to-noise was measured")
    parser.add_argument("--confirm-ql", type=finite_float, default=None,
                        help="the QL being claimed, to be confirmed with --confirm-data")
    parser.add_argument("--confirm-data", help="CSV/TSV/JSON with `measured` at/near the QL")
    parser.add_argument("--confirm-accuracy-limit", type=finite_float, default=None,
                        help="pre-stated max %% bias for QL confirmation; no guideline default")
    parser.add_argument("--confirm-rsd-limit", type=finite_float, default=None,
                        help="pre-stated max %%RSD for QL confirmation; no guideline default")
    parser.add_argument("--reporting-threshold", type=finite_float, default=None,
                        help="impurity reporting threshold the QL must be at or below")
    parser.add_argument("--weight", choices=("none", "1/x", "1/x2"), default="none")
    add_common_args(parser)
    args = parser.parse_args()
    for name in ("signal_to_noise", "sn_level", "confirm_ql", "reporting_threshold",
                 "confirm_accuracy_limit", "confirm_rsd_limit"):
        value = getattr(args, name)
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise InputError(f"--{name.replace('_', '-')} must be finite and > 0")
    if args.weight != "none":
        raise InputError("DL/QL sigma-and-slope estimates require an unweighted low-range fit; "
                         "weighted residual scale is not a response SD")
    if args.confirm_data and (args.confirm_accuracy_limit is None or args.confirm_rsd_limit is None):
        raise InputError("QL confirmation needs pre-stated --confirm-accuracy-limit and --confirm-rsd-limit")

    rows = parse_rows(read_input(args.calibration), args.calibration)
    require_columns(rows, ["level", "response"])
    xs = [to_float(r["level"], "level", i) for i, r in enumerate(rows)]
    ys = [to_float(r["response"], "response", i) for i, r in enumerate(rows)]
    fit = fit_linear(xs, ys)
    slope = fit.slope
    if slope == 0:
        raise InputError("calibration slope is zero; DL/QL cannot be computed")

    findings: list[str] = []
    results: list[dict] = []

    # Approach 3.2.3.3, sigma = residual SD of the regression line.
    results.append(
        {
            "approach": "sd-and-slope (sigma = residual SD of regression)",
            "sigma": fit.residual_sd,
            "slope": slope,
            "DL": DL_FACTOR * fit.residual_sd / abs(slope),
            "QL": QL_FACTOR * fit.residual_sd / abs(slope),
            "reference": "Q2(R2) 3.2.3.3",
        }
    )

    # Q2 refers to SD across regression-line intercepts, not the standard error
    # of the intercept from one line. Do not silently substitute the latter.
    if args.intercepts:
        irows = parse_rows(read_input(args.intercepts), args.intercepts)
        require_columns(irows, ["intercept"])
        intercepts = [to_float(r["intercept"], "intercept", i) for i, r in enumerate(irows)]
        if len(intercepts) < 3:
            raise InputError("intercept SD needs at least 3 independent calibration curves (tool minimum)")
        sigma = sample_sd(intercepts)
        results.append({"approach": "sd-and-slope (sigma = SD of independent y-intercepts)",
                        "sigma": sigma, "slope": slope,
                        "DL": DL_FACTOR * sigma / abs(slope),
                        "QL": QL_FACTOR * sigma / abs(slope),
                        "reference": "Q2(R2) 3.2.3.3"})

    # Approach 3.2.3.3, sigma = SD of blank responses.
    if args.blanks:
        brows = parse_rows(read_input(args.blanks), args.blanks)
        require_columns(brows, ["response"])
        blanks = [to_float(r["response"], "response", i) for i, r in enumerate(brows)]
        if len(blanks) < 3:
            raise InputError("blank SD needs at least 3 blank measurements")
        bsd = sample_sd(blanks)
        results.append(
            {
                "approach": f"sd-and-slope (sigma = SD of {len(blanks)} blanks)",
                "sigma": bsd,
                "slope": slope,
                "DL": DL_FACTOR * bsd / abs(slope),
                "QL": QL_FACTOR * bsd / abs(slope),
                "reference": "Q2(R2) 3.2.3.3",
            }
        )
        note(f"blank mean response {mean(blanks):.6g}, SD {bsd:.6g}, n={len(blanks)}")

    # Approach 3.2.3.2, signal-to-noise.
    if args.signal_to_noise is not None:
        if args.sn_level is None:
            raise InputError("--signal-to-noise needs --sn-level")
        if args.signal_to_noise <= 0 or args.sn_level <= 0:
            raise InputError("--signal-to-noise and --sn-level must be > 0")
        per_unit = args.signal_to_noise / args.sn_level
        results.append(
            {
                "approach": f"signal-to-noise (S/N {args.signal_to_noise:g} at {args.sn_level:g})",
                "sigma": float("nan"),
                "slope": slope,
                "DL": 3.0 / per_unit,
                "QL": 10.0 / per_unit,
                "reference": "Q2(R2) 3.2.3.2",
            }
        )
        note(
            "signal-to-noise DL uses the 3:1 ratio and QL the 10:1 ratio from Q2(R2) 3.2.3.2, "
            "scaled linearly from the measured S/N. Linear scaling of noise is an assumption -- "
            "confirm at the resulting level"
        )

    if any(result["QL"] <= 0 for result in results):
        findings.append("zero estimated response variation cannot establish a physical detection/quantitation limit")

    # Spread across approaches: the point of computing all of them.
    qls = [r["QL"] for r in results if math.isfinite(r["QL"])]
    spread_note = ""
    if len(qls) >= 2:
        ratio = max(qls) / min(qls) if min(qls) > 0 else float("inf")
        spread_note = (
            f"QL estimates span {min(qls):.6g} to {max(qls):.6g} ({ratio:.2f}x) across "
            f"{len(qls)} approaches"
        )
        if ratio > 2.0:
            findings.append(
                spread_note
                + ": name the approach used in the report, and confirm the claimed limit with "
                "real data at that level (Q2(R2) 3.2.3.5)"
            )

    # QL confirmation with real data (Q2(R2) 3.2.3.4 / 3.2.3.5).
    confirm_rows: list[dict] = []
    if args.confirm_data:
        if args.confirm_ql is None:
            raise InputError("--confirm-data needs --confirm-ql")
        crows = parse_rows(read_input(args.confirm_data), args.confirm_data)
        require_columns(crows, ["measured"])
        measured = [to_float(r["measured"], "measured", i) for i, r in enumerate(crows)]
        if len(measured) < 3:
            raise InputError("QL confirmation needs at least 3 determinations")
        m = mean(measured)
        bias = 100.0 * (m - args.confirm_ql) / args.confirm_ql
        rsd = rsd_percent(measured)
        confirm_rows = [
            {"metric": "claimed QL", "value": args.confirm_ql},
            {"metric": "n determinations", "value": len(measured)},
            {"metric": "mean measured", "value": m},
            {"metric": "bias vs claimed QL (%)", "value": bias},
            {"metric": "RSD (%)", "value": rsd},
            {"metric": "accuracy limit (%)", "value": args.confirm_accuracy_limit},
            {"metric": "RSD limit (%)", "value": args.confirm_rsd_limit},
        ]
        if abs(bias) > args.confirm_accuracy_limit:
            findings.append(
                f"QL confirmation: bias {bias:+.2f}% at the claimed QL exceeds "
                f"+/-{args.confirm_accuracy_limit:g}%"
            )
        if not math.isfinite(rsd):
            findings.append("QL confirmation: RSD is undefined; precision was not demonstrated")
        elif rsd > args.confirm_rsd_limit:
            findings.append(
                f"QL confirmation: {rsd:.2f}% RSD at the claimed QL exceeds "
                f"{args.confirm_rsd_limit:g}%"
            )
    elif args.confirm_ql is not None:
        findings.append(
            "a QL was claimed but no confirmation data supplied. Q2(R2) 3.2.3.5 asks that an "
            "estimated limit be validated by analysing samples at or near it"
        )

    # The requirement that actually gates an impurity method.
    if args.reporting_threshold is not None:
        # With no claimed QL, use the LARGEST estimate. Taking the smallest would
        # let the check pass on the most flattering choice of sigma, which is the
        # wrong direction to err on a compliance requirement.
        conservative = max(qls) if qls else float("nan")
        claimed = args.confirm_ql if args.confirm_ql is not None else conservative
        if args.confirm_ql is None and qls:
            note(
                f"no --confirm-ql given, so the reporting-threshold check uses the most "
                f"conservative estimate ({conservative:.6g}), not the most favourable "
                f"({min(qls):.6g})"
            )
            if min(qls) <= args.reporting_threshold < conservative:
                findings.append(
                    f"the QL estimates straddle the reporting threshold "
                    f"{args.reporting_threshold:.6g}: {min(qls):.6g} would pass and "
                    f"{conservative:.6g} would not. Whether this procedure meets Q2(R2) "
                    "3.2.3.5 depends on which approach is chosen, so choose it, justify it, "
                    "and confirm the claimed limit with data at that level"
                )
        if math.isfinite(claimed) and claimed > args.reporting_threshold:
            findings.append(
                f"QL {claimed:.6g} is above the reporting threshold "
                f"{args.reporting_threshold:.6g}. Q2(R2) 3.2.3.5 requires the QL for an "
                "impurity procedure to be at or below the reporting threshold"
            )
        elif math.isfinite(claimed):
            ratio = args.reporting_threshold / claimed if claimed > 0 else float("inf")
            if math.isclose(ratio, 1.0, rel_tol=1e-9):
                note(
                    f"QL {claimed:.6g} sits exactly at the reporting threshold "
                    f"{args.reporting_threshold:.6g}, which satisfies Q2(R2) 3.2.3.5 with no "
                    "margin -- any drift puts the procedure out of compliance"
                )
            else:
                note(
                    f"QL {claimed:.6g} is {ratio:.1f}x below the reporting threshold "
                    f"{args.reporting_threshold:.6g}"
                )
            if ratio >= 10:
                note(
                    "the QL is roughly 10x or more below the reporting limit, so Q2(R2) 3.2.3.5 "
                    "allows the confirmatory validation to be omitted with justification"
                )

    if args.format == "json":
        emit(
            [
                {
                    "calibration": {
                        "n": fit.n,
                        "slope": slope,
                        "intercept": fit.intercept,
                        "residual_sd": fit.residual_sd,
                        "weighting": args.weight,
                    },
                    "estimates": results,
                    "confirmation": confirm_rows,
                    "findings": findings,
                }
            ],
            "json",
        )
    else:
        emit(results, args.format)
        if confirm_rows:
            print()
            emit(confirm_rows, args.format)

    if not args.confirm_data:
        note(
            f"approach 'accuracy-precision' ({DL_QL_APPROACHES['accuracy-precision']['note']}) "
            "validates the QL directly rather than estimating it -- supply --confirm-data "
            "to use it"
        )
    if spread_note and not any(spread_note in f for f in findings):
        note(spread_note)
    note("Q2(R2) 3.2.3.5: report the limit AND the approach used to determine it")
    for f in findings:
        finding(f)
    if not findings:
        note("no findings against the checks that were run")
    note("this tool does not decide that a detection or quantitation limit is acceptable")
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    run_cli(main)
