#!/usr/bin/env python3
"""Conventional average bioequivalence and numerical sample-size planning.

The CLI supports complete RT/TR 2x2 crossover and independent parallel data.
It rejects replicate/reference-scaled analysis, which requires a design-specific
model. Retained scalar scaling functions are arithmetic aids only.

    python3 bioequivalence.py -i be.csv --design 2x2 --metric auc
    python3 bioequivalence.py --power --cv 0.30 --gmr 0.95 --target-power 0.80

Input: subject,treatment(T/R),value, plus sequence and period for crossover.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
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
    from scipy.stats import chi2, norm
    from scipy.stats import t as t_dist
except ImportError as exc:  # pragma: no cover
    raise SystemExit("bioequivalence.py needs scipy: uv pip install scipy") from exc


# The FDA regulatory constant: ln(1.25) / 0.25, the point at which the scaled
# criterion coincides with the conventional limits at sigma_w0 = 0.25.
THETA_FDA = math.log(1.25) / 0.25
# EMA's ABEL widening coefficient, and the CVwR at which widening is capped.
K_ABEL = 0.760
CV_ABEL_CAP = 0.50
SWR_ABEL_CAP = math.sqrt(math.log(1.0 + CV_ABEL_CAP**2))
CV_SCALING_THRESHOLD = 0.30


def cv_from_s2(s2: float) -> float:
    return math.sqrt(math.exp(s2) - 1.0)


def s2_from_cv(cv: float) -> float:
    return math.log(1.0 + cv**2)


# ------------------------------------------------------------------ average BE


@dataclass
class AverageBE:
    gmr: float
    ci_low: float
    ci_high: float
    df: int
    se: float
    cv_within: float | None
    n_subjects: int
    method: str


def crossover_2x2(records: list[dict], design: str = "2x2") -> AverageBE:
    """Crossover analysis via within-subject period differences.

    Averaging the sequence-specific mean differences cancels the period effect
    exactly, which is the whole reason a crossover is run. The estimate and its
    standard error are identical to what a sequence/subject(sequence)/period/
    treatment ANOVA gives on balanced or unbalanced data, without building the
    design matrix.

    Replicate designs are rejected; repeated treatments need a different model.
    """
    if design != "2x2":
        raise InputError("replicate designs need a design-specific period/sequence model; use FDA Appendix G or validated replicateBE tooling")
    by_subject: dict[str, dict[str, list[float]]] = {}
    sequences: dict[str, str] = {}
    for row in records:
        by_subject.setdefault(row["subject"], {}).setdefault(row["treatment"], []).append(row["logvalue"])
        if row.get("sequence"):
            sequences[row["subject"]] = row["sequence"]

    for subject, treatments in by_subject.items():
        if set(treatments) != {"T", "R"} or any(len(v) != 1 for v in treatments.values()):
            raise InputError(f"subject {subject}: 2x2 analysis requires exactly one T and one R; handle incomplete records explicitly")
        if sequences.get(subject) not in {"RT", "TR"}:
            raise InputError("2x2 analysis requires RT/TR sequence and periods 1/2")
        subject_rows = [r for r in records if r["subject"] == subject]
        if {str(r.get("period")) for r in subject_rows} != {"1", "2"}:
            raise InputError(f"subject {subject}: expected periods 1 and 2")
        if any(r.get("sequence") != sequences[subject] or r["treatment"] != sequences[subject][int(r["period"])-1] for r in subject_rows):
            raise InputError(f"subject {subject}: treatment, period and sequence disagree")
    if set(sequences.values()) != {"RT", "TR"}:
        raise InputError("both RT and TR sequences are required to separate period and treatment")
    differences: dict[str, list[float]] = {}
    for subject, treatments in by_subject.items():
        if "T" not in treatments or "R" not in treatments:
            continue  # incomplete subject: dropped, as in the standard analysis
        diff = float(np.mean(treatments["T"])) - float(np.mean(treatments["R"]))
        sequence = sequences.get(subject, "?")
        differences.setdefault(sequence, []).append(diff)

    total = sum(len(v) for v in differences.values())
    if total < 3:
        raise InputError("fewer than 3 subjects completed both treatments")

    means = {seq: float(np.mean(v)) for seq, v in differences.items()}
    estimate = float(np.mean(list(means.values())))
    pooled_num = sum(float(np.var(v, ddof=1)) * (len(v) - 1) for v in differences.values() if len(v) > 1)
    pooled_den = sum(len(v) - 1 for v in differences.values())
    s2d = pooled_num / pooled_den
    se = math.sqrt(s2d / 4.0 * sum(1.0 / len(v) for v in differences.values()))
    df = pooled_den
    s2w = s2d / 2.0
    method = "2x2 crossover (period effect removed)"

    crit = float(t_dist.ppf(0.95, df))
    return AverageBE(
        gmr=math.exp(estimate),
        ci_low=math.exp(estimate - crit * se),
        ci_high=math.exp(estimate + crit * se),
        df=df,
        se=se,
        cv_within=cv_from_s2(s2w) if s2w > 0 else None,
        n_subjects=total,
        method=method,
    )


def parallel_design(records: list[dict]) -> AverageBE:
    if len({r["subject"] for r in records}) != len(records):
        raise InputError("parallel analysis requires one independent record per subject")
    test = np.asarray([r["logvalue"] for r in records if r["treatment"] == "T"])
    ref = np.asarray([r["logvalue"] for r in records if r["treatment"] == "R"])
    if len(test) < 2 or len(ref) < 2:
        raise InputError("a parallel design needs at least 2 subjects per arm")
    n1, n2 = len(test), len(ref)
    pooled = ((n1 - 1) * test.var(ddof=1) + (n2 - 1) * ref.var(ddof=1)) / (n1 + n2 - 2)
    se = math.sqrt(pooled * (1.0 / n1 + 1.0 / n2))
    df = n1 + n2 - 2
    estimate = float(test.mean() - ref.mean())
    crit = float(t_dist.ppf(0.95, df))
    return AverageBE(
        gmr=math.exp(estimate),
        ci_low=math.exp(estimate - crit * se),
        ci_high=math.exp(estimate + crit * se),
        df=df,
        se=se,
        cv_within=cv_from_s2(float(pooled)),  # total, not within-subject
        n_subjects=n1 + n2,
        method="parallel (pooled variance; the CV shown is total, not within-subject)",
    )


# -------------------------------------------------------------- scaled BE


@dataclass
class ReferenceVariability:
    s2wr: float
    df: int
    n_subjects: int

    @property
    def swr(self) -> float:
        return math.sqrt(self.s2wr)

    @property
    def cvwr(self) -> float:
        return cv_from_s2(self.s2wr)


def reference_variability(records: list[dict]) -> ReferenceVariability:
    """Descriptive unadjusted replicate variance; NOT design-adjusted BE variance.

    Period/sequence effects contaminate this quantity. Do not supply it to a
    regulatory scaled analysis; the CLI rejects that unsupported workflow.
    """
    numerator = 0.0
    df = 0
    subjects = 0
    for subject in {r["subject"] for r in records}:
        values = [r["logvalue"] for r in records if r["subject"] == subject and r["treatment"] == "R"]
        if len(values) < 2:
            continue
        numerator += float(np.var(values, ddof=1)) * (len(values) - 1)
        df += len(values) - 1
        subjects += 1
    if df == 0:
        raise InputError(
            "no subject received the reference more than once. Reference-scaling requires a replicate "
            "design (partial replicate RRT/RTR/TRR or full replicate RTRT/TRTR) - it cannot be applied "
            "to a 2x2 study whatever the observed variability."
        )
    return ReferenceVariability(s2wr=numerator / df, df=df, n_subjects=subjects)


def abel_limits(rv: ReferenceVariability) -> tuple[float, float, bool]:
    """EMA widened acceptance limits. Returns (low, high, widened)."""
    if rv.cvwr <= CV_SCALING_THRESHOLD:
        return 0.80, 1.25, False
    swr = min(rv.swr, SWR_ABEL_CAP)
    return math.exp(-K_ABEL * swr), math.exp(K_ABEL * swr), True


def rsabe_bound(estimate: float, se: float, df_point: int, rv: ReferenceVariability) -> dict[str, float]:
    """Scalar FDA 2026 Appendix G bound; inputs must come from its design model.

    This does not establish the HVD applicability threshold, point-estimate
    constraint or validity of externally supplied variance/degrees of freedom.
    """
    if not all(math.isfinite(v) for v in (estimate, se, df_point, rv.s2wr, rv.df)) or se < 0 or df_point <= 0 or rv.s2wr < 0 or rv.df <= 0:
        raise InputError("scaled bound requires finite contrast, non-negative SE/variance and positive degrees of freedom")
    e_point = estimate**2 - se**2
    e_bound = (abs(estimate) + float(t_dist.ppf(0.95, df_point)) * se) ** 2
    h_point = -(THETA_FDA**2) * rv.s2wr
    h_bound = -(THETA_FDA**2) * rv.s2wr * rv.df / float(chi2.ppf(0.95, rv.df))
    upper = e_point + h_point + math.sqrt((e_bound - e_point) ** 2 + (h_bound - h_point) ** 2)
    return {
        "criterion_point_estimate": e_point + h_point,
        "criterion_95_upper_bound": upper,
        "passes_scaled_criterion": float(upper <= 0.0),
    }


# ------------------------------------------------------------- power / N


def tost_power(n_total: int, cv: float, gmr: float, design: str = "2x2", limits: tuple[float, float] = (0.80, 1.25)) -> float:
    """Approximate TOST power by a finite quantile grid over estimated variance.

    Equal allocation and normal log-endpoints are assumed. This is not an
    exact Owen-Q routine; verify borderline planning decisions independently.
    """
    if design not in {"2x2", "parallel"}:
        raise InputError("replicate power needs a specified sequence design and variance model; use PowerTOST")
    if not math.isfinite(cv) or cv <= 0 or not math.isfinite(gmr) or gmr <= 0:
        raise InputError("CV and GMR must be positive and finite")
    if n_total < 4 or n_total % 2:
        raise InputError("power calculation requires an even total N >= 4 for equal allocation")
    sigma = math.sqrt(s2_from_cv(cv))
    delta = math.log(gmr)
    theta_low, theta_high = math.log(limits[0]), math.log(limits[1])

    if design == "parallel":
        df = n_total - 2
        factor = math.sqrt(2.0 / (n_total / 2.0))  # equal arms
    elif design == "2x2":
        df = n_total - 2
        factor = math.sqrt(2.0 / n_total)
    if df < 1:
        return 0.0

    crit = float(t_dist.ppf(0.95, df))
    # s^2 * df / sigma^2 ~ chi2_df
    grid = np.linspace(1e-6, 1 - 1e-6, 2001)
    chi_values = chi2.ppf(grid, df)
    s_values = np.sqrt(chi_values / df) * sigma
    se_values = s_values * factor
    upper = (theta_high - crit * se_values - delta) / (sigma * factor)
    lower = (theta_low + crit * se_values - delta) / (sigma * factor)
    conditional = np.clip(norm.cdf(upper) - norm.cdf(lower), 0.0, 1.0)
    return float(np.mean(conditional))


def sample_size(cv: float, gmr: float, target: float, design: str = "2x2", limits: tuple[float, float] = (0.80, 1.25)) -> tuple[int, float]:
    if not 0 < target < 1:
        raise InputError("target power must be in (0,1)")
    step = 2
    for n in range(4, 5002, step):
        power = tost_power(n, cv, gmr, design, limits)
        if power >= target:
            return n, power
    raise InputError("no sample size below 5000 reaches the target power; the GMR is too far from 1")


# --------------------------------------------------------------------- CLI


def load_records(args: argparse.Namespace) -> list[dict]:
    rows = read_table(args.input)
    require_columns(rows, [args.subject_column, args.treatment_column, args.value_column], str(args.input))
    records = []
    for index, row in enumerate(rows, start=1):
        treatment = row[args.treatment_column].strip().upper()
        if treatment in {"T", "TEST"}:
            treatment = "T"
        elif treatment in {"R", "REF", "REFERENCE"}:
            treatment = "R"
        else:
            raise InputError(f"row {index}: treatment must be T or R, got {row[args.treatment_column]!r}")
        value = parse_float(row[args.value_column], f"{args.value_column} (row {index})")
        if value is None or value <= 0:
            raise InputError(f"row {index}: value must be positive to log-transform, got {value!r}")
        records.append(
            {
                "subject": row[args.subject_column].strip(),
                "treatment": treatment,
                "value": value,
                "logvalue": math.log(value),
                "sequence": (row.get("sequence") or "").strip().upper(),
                "period": (row.get("period") or "").strip(),
            }
        )
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Average, reference-scaled, and prospective bioequivalence calculations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-i", "--input")
    parser.add_argument("--design", choices=("2x2", "parallel", "replicate"), default="2x2")
    parser.add_argument("--metric", default="", help="label for the metric being tested, used in output only")
    parser.add_argument("--subject-column", default="subject")
    parser.add_argument("--treatment-column", default="treatment")
    parser.add_argument("--value-column", default="value")
    parser.add_argument(
        "--scaling",
        choices=("none", "abel", "rsabe", "both"),
        default="none",
        help="unsupported: requires external design-specific analysis",
    )
    parser.add_argument("--limits", default="0.80,1.25", help="acceptance limits for average BE (default: 0.80,1.25)")
    parser.add_argument("--nti", action="store_true", help="narrow therapeutic index: apply 90.00-111.11%% limits")
    parser.add_argument("--power", action="store_true", help="prospective power / sample size instead of an analysis")
    parser.add_argument("--cv", type=float, help="assumed within-subject CV (as a fraction) for --power")
    parser.add_argument("--gmr", type=float, default=0.95, help="assumed true GMR for --power (default: 0.95)")
    parser.add_argument("--target-power", type=float, default=0.80)
    parser.add_argument("--n", type=int, help="compute power at this N instead of solving for N")
    add_format_argument(parser)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from _common import validate_numeric_args
    validate_numeric_args(args)
    report = Report()

    limits = (0.90, 1.1111) if args.nti else tuple(parse_float(x, "acceptance limit") for x in args.limits.split(","))
    if len(limits) != 2 or not all(math.isfinite(x) and x > 0 for x in limits) or limits[0] >= limits[1]:
        raise InputError(f"--limits must be low,high with low < high; got {args.limits!r}")

    if args.design == "replicate" or args.scaling != "none":
        raise InputError("replicate/reference-scaling requires a design-specific validated analysis (FDA 2026 Appendix G, replicateBE); this CLI supports 2x2 and parallel ABE only")
    if args.power:
        if args.cv is None:
            raise InputError("--power needs --cv")
        if args.n:
            power = tost_power(args.n, args.cv, args.gmr, args.design, limits)
            report.scalar("n_total", args.n)
            report.scalar("power", power)
        else:
            n, power = sample_size(args.cv, args.gmr, args.target_power, args.design, limits)
            report.scalar("n_total_required", n)
            report.scalar("achieved_power", power)
        report.scalar("assumed_cv_within", args.cv)
        report.scalar("assumed_gmr", args.gmr)
        report.scalar("acceptance_limits", f"{limits[0]:.4f}-{limits[1]:.4f}")
        report.note(
            "Power is approximated by numerical integration over the sampling distribution of the estimated "
            "standard deviation; the normal approximation overstates it at these sample sizes."
        )
        report.note(
            "Planning depends jointly on GMR, CV, allocation and dropout. Assess plausible GMR/CV scenarios and inflate for dropout; the returned N is evaluable subjects."
        )
        return report.emit(args.format)

    if not args.input:
        raise InputError("give -i INPUT for an analysis, or --power for a sample-size calculation")

    records = load_records(args)
    label = args.metric or args.value_column

    result = parallel_design(records) if args.design == "parallel" else crossover_2x2(records, args.design)
    passes = limits[0] <= result.ci_low and result.ci_high <= limits[1]

    report.scalar("metric", label)
    report.scalar("design", args.design)
    report.scalar("analysis", result.method)
    report.scalar("n_subjects", result.n_subjects)
    report.scalar("gmr_pct", 100.0 * result.gmr)
    report.scalar("ci90_low_pct", 100.0 * result.ci_low)
    report.scalar("ci90_high_pct", 100.0 * result.ci_high)
    report.scalar("acceptance_limits_pct", f"{100 * limits[0]:.2f}-{100 * limits[1]:.2f}")
    report.scalar("average_be_met", passes)
    report.scalar("degrees_of_freedom", result.df)
    if result.cv_within is not None:
        report.scalar(
            "cv_within_pct",
            100.0 * result.cv_within,
        )

    if not passes:
        report.finding(
            f"{label}: the 90% CI ({100 * result.ci_low:.2f}-{100 * result.ci_high:.2f}%) is not contained "
            f"in {100 * limits[0]:.2f}-{100 * limits[1]:.2f}%; average bioequivalence is not demonstrated"
        )
    if args.nti:
        report.note("narrow therapeutic index limits applied (90.00-111.11%)")

    report.note("all statistics computed on the natural-log scale; ratios are geometric means")
    return report.emit(args.format)


if __name__ == "__main__":
    raise SystemExit(main_wrapper(run))
