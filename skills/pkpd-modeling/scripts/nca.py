#!/usr/bin/env python3
"""Non-compartmental analysis of concentration-time data.

NCA looks arithmetically trivial and is not. Essentially every disagreement
between two NCA results traces to one of four choices that are rarely written
down: how lambda_z was selected, which trapezoidal rule was used, what happened
to BLQ values, and whether AUCinf was based on observed or predicted Clast.
This script makes all four explicit, reports the diagnostics that decide
whether the result is reportable, and refuses to hide them behind a default.

    python3 nca.py -i profile.csv --dose 100 --route extravascular
    python3 nca.py -i profile.csv --dose-column dose --route iv-infusion --tinf 1
    python3 nca.py -i ss.csv --dose 50 --route extravascular --tau 12
    python3 nca.py -i profile.csv --dose 100 --partial-auc 0-24 --partial-auc 0-72

Input is a table with subject, time, and concentration columns (default names
``id``, ``time``, ``conc``). Concentrations below the limit of quantification
may be given as the text ``BLQ`` / ``BQL`` / ``<LLOQ``, or as blanks, or as a
separate 0/1 ``blq`` column.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from _common import (
    EXIT_INPUT,
    InputError,
    Report,
    add_format_argument,
    main_wrapper,
    parse_float,
    read_table,
    require_columns,
)

BLQ_TOKENS = {"blq", "bql", "<lloq", "lloq", "bloq", "nq", "<loq"}

ROUTES = {
    "iv-bolus": "intravenous bolus",
    "iv-infusion": "intravenous infusion (zero order)",
    "extravascular": "extravascular (oral, SC, IM, ...)",
}


# ----------------------------------------------------------------- parsing


@dataclass
class Profile:
    subject: str
    time: np.ndarray
    conc: np.ndarray
    is_blq: np.ndarray
    dose: float
    tau: float | None = None
    tinf: float | None = None


def _parse_conc(raw: str, lloq: float | None, rule: str) -> tuple[float | None, bool]:
    """Return (value, is_blq). ``None`` means 'drop this record'."""
    text = (raw or "").strip()
    lowered = text.lower()
    blq = lowered in BLQ_TOKENS or lowered.startswith("<") or lowered == ""
    if blq:
        if rule == "missing":
            return None, True
        if rule == "half-lloq":
            if lloq is None:
                raise InputError("--blq-rule half-lloq needs --lloq")
            return lloq / 2.0, True
        return 0.0, True
    value = parse_float(text, "conc")
    if value is None:
        return None, True
    if lloq is not None and value < lloq:
        if rule == "missing":
            return None, True
        return (lloq / 2.0 if rule == "half-lloq" else 0.0), True
    return value, False


def load_profiles(args: argparse.Namespace) -> list[Profile]:
    rows = read_table(args.input)
    require_columns(rows, [args.time_column, args.conc_column], str(args.input))
    has_subject = args.subject_column in rows[0]
    if args.dose is None and args.dose_column not in rows[0]:
        raise InputError(
            f"give a dose with --dose, or a per-subject '{args.dose_column}' column in the input"
        )

    buckets: dict[str, list[dict]] = {}
    for row in rows:
        subject = row[args.subject_column].strip() if has_subject else "1"
        buckets.setdefault(subject or "1", []).append(row)

    profiles = []
    for subject, subject_rows in buckets.items():
        times, concs, blqs = [], [], []
        for index, row in enumerate(subject_rows):
            time = parse_float(row.get(args.time_column), f"{args.time_column} (row {index + 1})")
            flagged = str(row.get("blq", "")).strip() in {"1", "y", "yes", "true"}
            value, is_blq = _parse_conc(row.get(args.conc_column, ""), args.lloq, args.blq_rule)
            if flagged and not is_blq:
                value, is_blq = _parse_conc("BLQ", args.lloq, args.blq_rule)
            if value is None:
                continue
            times.append(time)
            concs.append(value)
            blqs.append(is_blq)
        if not times:
            raise InputError(f"subject {subject}: no usable concentration records")

        order = np.argsort(np.asarray(times, dtype=float), kind="stable")
        time_array = np.asarray(times, dtype=float)[order]
        conc_array = np.asarray(concs, dtype=float)[order]
        blq_array = np.asarray(blqs, dtype=bool)[order]

        if args.dose is not None:
            dose = args.dose
        else:
            dose = parse_float(subject_rows[0].get(args.dose_column), args.dose_column)
        if dose is None or dose <= 0:
            raise InputError(f"subject {subject}: dose must be positive")

        tau = args.tau
        if args.tau is None and "tau" in subject_rows[0]:
            tau = parse_float(subject_rows[0].get("tau"), "tau", allow_missing=True)
        tinf = args.tinf
        if args.tinf is None and "tinf" in subject_rows[0]:
            tinf = parse_float(subject_rows[0].get("tinf"), "tinf", allow_missing=True)

        profiles.append(Profile(subject, time_array, conc_array, blq_array, float(dose), tau, tinf))
    return profiles


# ------------------------------------------------------------- trapezoidal


def _segment(t0: float, t1: float, c0: float, c1: float, method: str) -> tuple[float, float]:
    """AUC and AUMC over one interval. Returns (auc, aumc)."""
    dt = t1 - t0
    if dt <= 0:
        return 0.0, 0.0
    use_log = (
        method in {"linup-logdown", "log"}
        and c0 > 0
        and c1 > 0
        and (c1 < c0 or method == "log")
        and not math.isclose(c0, c1)
    )
    if not use_log:
        return (c0 + c1) / 2.0 * dt, (t0 * c0 + t1 * c1) / 2.0 * dt
    k = math.log(c0 / c1) / dt
    auc = (c0 - c1) / k
    aumc = (t0 * c0 - t1 * c1) / k + (c0 - c1) / (k * k)
    return auc, aumc


def cumulative_auc(time: np.ndarray, conc: np.ndarray, method: str) -> tuple[np.ndarray, np.ndarray]:
    auc = np.zeros_like(time)
    aumc = np.zeros_like(time)
    for i in range(1, len(time)):
        d_auc, d_aumc = _segment(time[i - 1], time[i], conc[i - 1], conc[i], method)
        auc[i] = auc[i - 1] + d_auc
        aumc[i] = aumc[i - 1] + d_aumc
    return auc, aumc


def interpolate(time: np.ndarray, conc: np.ndarray, target: float, method: str) -> float:
    """Concentration at an arbitrary time, consistent with the AUC rule."""
    if target <= time[0]:
        return float(conc[0])
    if target >= time[-1]:
        return float(conc[-1])
    i = int(np.searchsorted(time, target))
    t0, t1, c0, c1 = time[i - 1], time[i], conc[i - 1], conc[i]
    use_log = method in {"linup-logdown", "log"} and c0 > 0 and c1 > 0 and (c1 < c0 or method == "log")
    if not use_log:
        return float(c0 + (c1 - c0) * (target - t0) / (t1 - t0))
    k = math.log(c0 / c1) / (t1 - t0)
    return float(c0 * math.exp(-k * (target - t0)))


def partial_auc(time: np.ndarray, conc: np.ndarray, start: float, end: float, method: str) -> float:
    inner = [t for t in time if start < t < end]
    knots = [start, *inner, end]
    values = [interpolate(time, conc, t, method) for t in knots]
    total = 0.0
    for i in range(1, len(knots)):
        total += _segment(knots[i - 1], knots[i], values[i - 1], values[i], method)[0]
    return total


# --------------------------------------------------------------- lambda_z


@dataclass
class LambdaZ:
    lam: float | None = None
    intercept: float | None = None
    r2: float | None = None
    r2_adj: float | None = None
    n_points: int = 0
    t_first: float | None = None
    t_last: float | None = None
    clast_pred: float | None = None
    reason: str = ""
    excluded_cmax: bool = True

    @property
    def half_life(self) -> float | None:
        return math.log(2.0) / self.lam if self.lam and self.lam > 0 else None


def _loglinear_fit(t: np.ndarray, c: np.ndarray) -> tuple[float, float, float]:
    """Slope, intercept, r2 of ln(C) on time."""
    y = np.log(c)
    tbar, ybar = t.mean(), y.mean()
    sxx = float(np.sum((t - tbar) ** 2))
    slope = float(np.sum((t - tbar) * (y - ybar)) / sxx)
    intercept = float(ybar - slope * tbar)
    fitted = intercept + slope * t
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - ybar) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return slope, intercept, r2


def estimate_lambda_z(
    time: np.ndarray,
    conc: np.ndarray,
    is_blq: np.ndarray,
    tmax: float,
    min_points: int = 3,
    manual: tuple[float, float] | None = None,
) -> LambdaZ:
    """Select the terminal window by best adjusted r-squared.

    This helper starts from the last three quantifiable points, extends
    backwards, and retains a longer window only when adjusted r-squared
    improves by more than 0.0001. Unlike Phoenix Best Fit, it does not favor
    the longer window when scores are within that tolerance. Neither plain
    nor adjusted r-squared is monotonic as observations are added.

    Points at or before Tmax are never eligible. Including Tmax makes the fit
    describe the tail of absorption rather than elimination, which biases
    lambda_z upward and the half-life, Vz, and AUCinf downward.
    """
    eligible = (~is_blq) & (conc > 0) & (time > tmax)
    idx = np.flatnonzero(eligible)
    if manual is not None:
        lo, hi = manual
        idx = np.flatnonzero((~is_blq) & (conc > 0) & (time >= lo) & (time <= hi))
        if len(idx) < 2:
            return LambdaZ(reason=f"manual window {lo}-{hi} contains {len(idx)} quantifiable points")
        slope, intercept, r2 = _loglinear_fit(time[idx], conc[idx])
        n = len(idx)
        r2_adj = 1.0 - (1.0 - r2) * (n - 1) / (n - 2) if n > 2 else float("nan")
        return LambdaZ(
            lam=-slope,
            intercept=intercept,
            r2=r2,
            r2_adj=r2_adj,
            n_points=n,
            t_first=float(time[idx][0]),
            t_last=float(time[idx][-1]),
            clast_pred=float(math.exp(intercept + slope * time[idx][-1])),
            reason="manual window",
            excluded_cmax=bool(np.all(time[idx] > tmax)),
        )

    if len(idx) < min_points:
        return LambdaZ(reason=f"only {len(idx)} quantifiable points after Tmax; need {min_points}")

    best: LambdaZ | None = None
    for start in range(len(idx) - min_points, -1, -1):
        window = idx[start:]
        n = len(window)
        slope, intercept, r2 = _loglinear_fit(time[window], conc[window])
        if n <= 2 or not math.isfinite(r2):
            continue
        r2_adj = 1.0 - (1.0 - r2) * (n - 1) / (n - 2)
        candidate = LambdaZ(
            lam=-slope,
            intercept=intercept,
            r2=r2,
            r2_adj=r2_adj,
            n_points=n,
            t_first=float(time[window][0]),
            t_last=float(time[window][-1]),
            clast_pred=float(math.exp(intercept + slope * time[window][-1])),
            reason="best adjusted r2",
        )
        if best is None or (candidate.r2_adj or -math.inf) > (best.r2_adj or -math.inf) + 1e-4:
            best = candidate
    if best is None:
        return LambdaZ(reason="no window of at least 3 points could be fitted")
    if best.lam is not None and best.lam <= 0:
        return LambdaZ(reason=f"terminal slope is not negative (lambda_z = {best.lam:.4g})", n_points=best.n_points)
    return best


# ------------------------------------------------------------------- NCA


def analyse(profile: Profile, args: argparse.Namespace) -> tuple[dict, LambdaZ, list[str]]:
    findings: list[str] = []
    time, conc, is_blq = profile.time, profile.conc, profile.is_blq
    quantifiable = (~is_blq) & (conc > 0)

    if not np.any(quantifiable):
        findings.append(f"subject {profile.subject}: every sample is BLQ; no parameters computed")
        return {"id": profile.subject}, LambdaZ(reason="all BLQ"), findings

    peak = int(np.argmax(np.where(quantifiable, conc, -np.inf)))
    cmax, tmax = float(conc[peak]), float(time[peak])
    last = int(np.flatnonzero(quantifiable)[-1])
    clast, tlast = float(conc[last]), float(time[last])

    auc_cum, aumc_cum = cumulative_auc(time, conc, args.auc_method)
    auc_last, aumc_last = float(auc_cum[last]), float(aumc_cum[last])

    lz = estimate_lambda_z(time, conc, is_blq, tmax, args.lambda_z_points, args.lambda_z_window)

    row: dict[str, object] = {
        "id": profile.subject,
        "dose": profile.dose,
        "n_obs": int(len(time)),
        "n_blq": int(np.sum(is_blq)),
        "cmax": cmax,
        "tmax": tmax,
        "clast": clast,
        "tlast": tlast,
        "auc_last": auc_last,
    }
    if profile.tau:
        row["auc_tau"] = partial_auc(time, conc, 0.0, profile.tau, args.auc_method)

    if lz.lam:
        lam = lz.lam
        row["lambda_z"] = lam
        row["t_half"] = lz.half_life
        row["r2_adj"] = lz.r2_adj
        row["lambda_z_n"] = lz.n_points
        auc_inf_obs = auc_last + clast / lam
        auc_inf_pred = auc_last + (lz.clast_pred or clast) / lam
        aumc_inf = aumc_last + tlast * clast / lam + clast / lam**2
        row["auc_inf_obs"] = auc_inf_obs
        row["auc_inf_pred"] = auc_inf_pred
        row["pct_auc_extrap"] = 100.0 * (auc_inf_obs - auc_last) / auc_inf_obs
        row["pct_aumc_extrap"] = 100.0 * (aumc_inf - aumc_last) / aumc_inf if aumc_inf > 0 else float("nan")

        mrt = aumc_inf / auc_inf_obs
        if args.route == "iv-infusion" and profile.tinf:
            mrt -= profile.tinf / 2.0
        row["mrt"] = mrt

        clearance = profile.dose / auc_inf_obs
        row["cl_f" if args.route == "extravascular" else "cl"] = clearance
        row["vz_f" if args.route == "extravascular" else "vz"] = clearance / lam
        if args.route != "extravascular":
            row["vss"] = clearance * mrt

        span = (tlast - (lz.t_first or tlast)) / (lz.half_life or math.inf)
        row["span_ratio"] = span

        prefix = f"subject {profile.subject}"
        if row["pct_auc_extrap"] > args.max_extrap:
            findings.append(
                f"{prefix}: {row['pct_auc_extrap']:.1f}% of AUCinf is extrapolated "
                f"(above {args.max_extrap:.0f}%); AUCinf is driven by the lambda_z fit, not by data"
            )
        if lz.r2_adj is not None and lz.r2_adj < args.min_r2_adj:
            findings.append(
                f"{prefix}: terminal-phase adjusted r2 is {lz.r2_adj:.4f} (below {args.min_r2_adj}); "
                "half-life, Vz and AUCinf inherit that uncertainty"
            )
        if span < args.min_span:
            findings.append(
                f"{prefix}: lambda_z window spans {span:.2f} half-lives (below {args.min_span}); "
                "the terminal phase may not have been reached"
            )
        if lz.n_points < 3:
            findings.append(f"{prefix}: lambda_z estimated from {lz.n_points} points")
    else:
        findings.append(f"subject {profile.subject}: lambda_z not estimable - {lz.reason}")

    if profile.tau:
        tau = profile.tau
        auc_tau = float(row["auc_tau"])
        cmin = float(np.min(conc[(time >= 0) & (time <= tau) & quantifiable])) if np.any(quantifiable) else float("nan")
        cavg = auc_tau / tau
        row["cavg_ss"] = cavg
        row["cmin_ss"] = cmin
        row["ptf_pct"] = 100.0 * (cmax - cmin) / cavg if cavg else float("nan")
        row["swing"] = (cmax - cmin) / cmin if cmin else float("nan")
        row["cl_ss_f" if args.route == "extravascular" else "cl_ss"] = profile.dose / auc_tau
        if lz.lam:
            row["accumulation_index"] = 1.0 / (1.0 - math.exp(-lz.lam * tau))

    for start, end in args.partial_auc:
        if end > tlast:
            findings.append(
                f"subject {profile.subject}: partial AUC {start:g}-{end:g} extends past the last "
                f"quantifiable sample at {tlast:g}; the tail is interpolated from Clast"
            )
        row[f"auc_{start:g}_{end:g}"] = partial_auc(time, conc, start, end, args.auc_method)

    prefix = f"subject {profile.subject}"
    if peak == len(time) - 1:
        findings.append(f"{prefix}: Cmax is the last sample; the peak and the terminal phase are not characterised")
    if peak == 0 and args.route == "extravascular":
        findings.append(f"{prefix}: Cmax is the first sample; the true peak may precede the first draw")
    if is_blq[:peak].any() and args.blq_rule == "zero":
        row["leading_blq_set_to_zero"] = int(np.sum(is_blq[:peak]))

    return row, lz, findings


# --------------------------------------------------------------- summaries


def summarise(rows: Sequence[dict], keys: Sequence[str]) -> list[dict]:
    out = []
    for key in keys:
        values = [float(r[key]) for r in rows if isinstance(r.get(key), (int, float)) and math.isfinite(float(r[key]))]
        if len(values) < 1:
            continue
        arr = np.asarray(values)
        entry: dict[str, object] = {
            "parameter": key,
            "n": len(arr),
            "mean": float(arr.mean()),
            "sd": float(arr.std(ddof=1)) if len(arr) > 1 else float("nan"),
            "cv_pct": float(100.0 * arr.std(ddof=1) / arr.mean()) if len(arr) > 1 and arr.mean() else float("nan"),
            "median": float(np.median(arr)),
            "min": float(arr.min()),
            "max": float(arr.max()),
        }
        if np.all(arr > 0):
            logs = np.log(arr)
            entry["geo_mean"] = float(np.exp(logs.mean()))
            entry["geo_cv_pct"] = (
                float(100.0 * math.sqrt(math.exp(float(logs.var(ddof=1))) - 1.0)) if len(arr) > 1 else float("nan")
            )
        out.append(entry)
    return out


# --------------------------------------------------------------------- CLI


def _partial_spec(text: str) -> tuple[float, float]:
    try:
        start, end = text.split("-", 1)
        lo, hi = float(start), float(end)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"partial AUC must look like 0-24, got {text!r}") from exc
    if hi <= lo:
        raise argparse.ArgumentTypeError(f"partial AUC end must exceed start, got {text!r}")
    return lo, hi


def _window_spec(text: str) -> tuple[float, float]:
    return _partial_spec(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Non-compartmental analysis with explicit lambda_z, BLQ, and trapezoidal choices.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-i", "--input", required=True, help="concentration-time table (CSV/TSV, or - for stdin)")
    parser.add_argument("--dose", type=float, help="dose given to every subject")
    parser.add_argument("--dose-column", default="dose", help="per-subject dose column (default: dose)")
    parser.add_argument("--subject-column", default="id")
    parser.add_argument("--time-column", default="time")
    parser.add_argument("--conc-column", default="conc")
    parser.add_argument(
        "--route",
        choices=sorted(ROUTES),
        default="extravascular",
        help="route; decides whether CL/Vz are apparent (/F) and whether Vss is reported",
    )
    parser.add_argument("--tinf", type=float, help="infusion duration, for --route iv-infusion")
    parser.add_argument("--tau", type=float, help="dosing interval; requests steady-state parameters")
    parser.add_argument(
        "--auc-method",
        choices=("linup-logdown", "linear", "log"),
        default="linup-logdown",
        help="trapezoidal rule (default: linup-logdown, the usual regulatory choice)",
    )
    parser.add_argument("--lloq", type=float, help="lower limit of quantification")
    parser.add_argument(
        "--blq-rule",
        choices=("zero", "half-lloq", "missing"),
        default="zero",
        help="how BLQ samples enter the AUC (default: zero)",
    )
    parser.add_argument("--lambda-z-points", type=int, default=3, help="minimum points in the terminal fit (default: 3)")
    parser.add_argument("--lambda-z-window", type=_window_spec, help="force the terminal window, e.g. 8-48")
    parser.add_argument("--partial-auc", type=_partial_spec, action="append", default=[], help="e.g. --partial-auc 0-24")
    parser.add_argument("--min-r2-adj", type=float, default=0.80, help="flag terminal fits below this (default: 0.80)")
    parser.add_argument("--max-extrap", type=float, default=20.0, help="flag %%AUC extrapolated above this (default: 20)")
    parser.add_argument("--min-span", type=float, default=2.0, help="flag lambda_z spans below this many half-lives (default: 2)")
    parser.add_argument("--no-summary", action="store_true", help="per-subject table only")
    add_format_argument(parser)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.route == "iv-infusion" and args.tinf is None:
        print("error: --route iv-infusion needs --tinf (or a tinf column)", file=sys.stderr)
        return EXIT_INPUT

    profiles = load_profiles(args)
    report = Report()
    report.note(f"route: {ROUTES[args.route]}")
    report.note(f"trapezoidal rule: {args.auc_method}; BLQ rule: {args.blq_rule}")
    report.note(
        "AUCinf_obs uses the observed Clast; AUCinf_pred uses the value predicted by the "
        "lambda_z fit. Report which one you used - they are not interchangeable."
    )

    rows, diagnostics, all_findings = [], [], []
    for profile in profiles:
        row, lz, findings = analyse(profile, args)
        rows.append(row)
        diagnostics.append(
            {
                "id": profile.subject,
                "lambda_z": lz.lam,
                "t_half": lz.half_life,
                "n_points": lz.n_points,
                "window_start": lz.t_first,
                "window_end": lz.t_last,
                "r2": lz.r2,
                "r2_adj": lz.r2_adj,
                "clast_pred": lz.clast_pred,
                "basis": lz.reason,
            }
        )
        all_findings.extend(findings)

    report.table("per-subject parameters", rows)
    report.table("lambda_z diagnostics", diagnostics)

    if not args.no_summary and len(rows) > 1:
        candidates = [
            "cmax",
            "tmax",
            "auc_last",
            "auc_inf_obs",
            "t_half",
            "cl_f",
            "cl",
            "vz_f",
            "vz",
            "vss",
            "mrt",
            "auc_tau",
            "cavg_ss",
        ]
        keys = [k for k in candidates if any(k in r for r in rows)]
        keys += [k for k in rows[0] if k.startswith("auc_") and k not in keys and k not in {"auc_last", "auc_tau"}]
        report.table("summary statistics", summarise(rows, keys))
        report.note(
            "Exposure metrics (AUC, Cmax) are conventionally summarised as geometric mean with "
            "geometric CV%; Tmax as median and range. Arithmetic statistics are shown alongside."
        )

    for finding in all_findings:
        report.finding(finding)
    return report.emit(args.format)


if __name__ == "__main__":
    raise SystemExit(main_wrapper(run))
