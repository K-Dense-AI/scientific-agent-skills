#!/usr/bin/env python3
"""Simulate dosing regimens, with or without between-subject variability.

Deterministic and population simulations answer different questions. Target
attainment depends on the supplied population, target, omitted correlations
and uncertainty; a typical profile is not a distribution of patient outcomes.

    python3 simulate_regimen.py --cl 5 --v 40 --dose 500 --interval 12 --n-doses 10
    python3 simulate_regimen.py --cl 5 --v 40 --q 8 --v2 60 --dose 500 --interval 8 \\
        --route oral --ka 1.2 --f 0.7 --n-doses 10
    python3 simulate_regimen.py --cl 5 --v 40 --dose 500 --interval 12 --simulate 2000 \\
        --omega-cl 0.35 --omega-v 0.25 --target-trough 2.0
    python3 simulate_regimen.py --vmax 200 --km 5 --v 40 --dose 300 --interval 24 \\
        --n-doses 7 --nonlinear
    python3 simulate_regimen.py --compare "500@12,750@8,1000@24" --cl 5 --v 40
"""

from __future__ import annotations

import argparse
import math
from typing import Sequence

import numpy as np

from _common import InputError, Report, add_format_argument, main_wrapper

from _models import (
    build_regimen,
    disposition,
    simulate_linear,
    simulate_michaelis_menten,
    steady_state_metrics,
)


def summarise_interval(evaluate, start: float, end: float, points: int = 4001) -> dict[str, float]:
    """Summarise one dosing interval on its own dedicated grid.

    The interval is closed at the start (immediately *after* that dose) and
    open at the end (immediately *before* the next one). Subsetting a shared
    grid instead gets both ends wrong: a point landing exactly on the next dose
    reports that dose's peak as this interval's Cmax, and a point landing on
    this interval's own dose can be read as the previous trough.
    """
    window_t = np.linspace(start, end, points)
    window_t[-1] = end - 1e-9  # pre-dose trough, not the next dose's peak
    window_c = np.asarray(evaluate(window_t), dtype=float)
    auc = float(np.trapezoid(window_c, window_t))
    cmax = float(window_c.max())
    cmin = float(window_c.min())
    cavg = auc / (end - start)
    return {
        "auc_tau": auc,
        "cmax": cmax,
        "tmax": float(window_t[int(np.argmax(window_c))] - start),
        "cmin": cmin,
        "cavg": cavg,
        "peak_trough_fluctuation_pct": 100.0 * (cmax - cmin) / cavg if cavg else float("nan"),
        "swing": (cmax - cmin) / cmin if cmin > 0 else float("nan"),
    }


def _regimen_spec(text: str) -> tuple[float, float]:
    if "@" not in text:
        raise argparse.ArgumentTypeError(f"regimen must look like 500@12 (dose@interval), got {text!r}")
    dose_text, interval_text = text.split("@", 1)
    try:
        return float(dose_text), float(interval_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"could not parse regimen {text!r}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simulate single- and multiple-dose regimens, deterministically or with IIV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--cl", type=float, help="clearance")
    parser.add_argument("--v", type=float, required=True, help="central volume")
    parser.add_argument("--q", type=float, action="append", default=[], help="intercompartmental clearance (repeatable)")
    parser.add_argument("--v2", type=float, action="append", default=[], help="peripheral volume (repeatable, pairs with --q)")
    parser.add_argument("--route", choices=("iv-bolus", "iv-infusion", "oral"), default="iv-bolus")
    parser.add_argument("--ka", type=float, help="absorption rate constant for --route oral")
    parser.add_argument("--f", type=float, default=1.0, help="bioavailable fraction (default: 1.0)")
    parser.add_argument("--tlag", type=float, default=0.0)
    parser.add_argument("--tinf", type=float, default=0.0, help="infusion duration for --route iv-infusion")

    parser.add_argument("--dose", type=float, help="dose amount")
    parser.add_argument("--interval", type=float, help="dosing interval")
    parser.add_argument("--n-doses", type=int, default=1)
    parser.add_argument("--loading", type=float, help="different first dose")
    parser.add_argument("--steady-state", action="store_true", help="report closed-form steady-state metrics")
    parser.add_argument("--compare", help="comma-separated dose@interval regimens to compare")

    parser.add_argument("--nonlinear", action="store_true", help="Michaelis-Menten elimination instead of linear")
    parser.add_argument("--vmax", type=float, help="maximum elimination rate (amount/time) for --nonlinear")
    parser.add_argument("--km", type=float, help="Michaelis constant (concentration) for --nonlinear")

    parser.add_argument("--simulate", type=int, help="number of virtual subjects for a Monte Carlo simulation")
    parser.add_argument("--omega-cl", type=float, default=0.0, help="between-subject CV of clearance")
    parser.add_argument("--omega-v", type=float, default=0.0, help="between-subject CV of volume")
    parser.add_argument("--seed", type=int, default=20260727)
    parser.add_argument("--target-trough", type=float, help="report the fraction of subjects above this trough")
    parser.add_argument("--target-peak-below", type=float, help="report the fraction of subjects with a peak below this")
    parser.add_argument("--target-auc", type=float, help="report the fraction of subjects above this AUC over the interval")

    parser.add_argument("--profile", action="store_true", help="also emit the concentration-time profile")
    parser.add_argument("--profile-points", type=int, default=25)
    add_format_argument(parser)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from _common import validate_numeric_args
    validate_numeric_args(args)
    if len(args.q) != len(args.v2):
        raise InputError(f"{len(args.q)} --q values but {len(args.v2)} --v2 values; they pair up")
    if args.route == "oral" and args.ka is None:
        raise InputError("--route oral needs --ka")
    if args.route == "iv-infusion" and args.tinf <= 0:
        raise InputError("--route iv-infusion needs a positive --tinf")
    if args.nonlinear and (args.vmax is None or args.km is None):
        raise InputError("--nonlinear needs --vmax and --km")
    if not args.nonlinear and args.cl is None:
        raise InputError("--cl is required for a linear model")

    report = Report()
    if any(x <= 0 for x in args.q + args.v2) or (args.loading is not None and args.loading < 0) or args.profile_points < 2:
        raise InputError("peripheral Q/V must be positive, loading non-negative and profile-points >= 2")
    if args.nonlinear and (args.vmax <= 0 or args.km <= 0):
        raise InputError("Vmax and Km must be positive")
    if args.v <= 0 or (args.cl is not None and args.cl <= 0) or not 0 < args.f <= 1:
        raise InputError("CL, V must be positive; F must be in (0,1]")
    if args.n_doses < 1 or (args.dose is not None and args.dose <= 0) or (args.interval is not None and args.interval <= 0):
        raise InputError("dose count, dose and interval must be positive")
    if args.tlag < 0 or args.tinf < 0 or (args.ka is not None and args.ka <= 0):
        raise InputError("lag and infusion must be non-negative; ka positive")
    if args.route != "oral" and args.f != 1:
        raise InputError("IV bioavailability is 1; --f applies only to oral dosing")
    if args.route != "iv-infusion" and args.tinf:
        raise InputError("--tinf applies only to iv-infusion")
    if args.nonlinear and (args.tlag or args.steady_state):
        raise InputError("nonlinear lag/steady-state calculations are not implemented")
    if (args.compare or args.steady_state) and args.route != "iv-bolus":
        raise InputError("closed-form --compare/--steady-state supports iv-bolus only; simulate the actual oral/infusion regimen without those flags")
    if args.steady_state and args.interval is None:
        raise InputError("--steady-state needs --interval")
    if args.simulate is not None and args.simulate <= 0:
        raise InputError("--simulate must be positive")
    if args.omega_cl < 0 or args.omega_v < 0:
        raise InputError("variability CVs must be non-negative")

    # ---- regimen comparison
    if args.compare:
        regimens = [_regimen_spec(chunk.strip()) for chunk in args.compare.split(",")]
        if args.nonlinear:
            raise InputError("--compare currently supports linear models only")
        disp = disposition(args.cl, args.v, args.q, args.v2)
        rows = []
        for dose, interval in regimens:
            metrics = steady_state_metrics(disp, dose, interval, f=args.f)
            rows.append(
                {
                    "regimen": f"{dose:g} q{interval:g}h",
                    "daily_dose": dose * 24.0 / interval,
                    "auc_tau_ss": metrics["auc_tau_ss"],
                    "cavg_ss": metrics["cavg_ss"],
                    "cmax_ss_bolus": metrics["cmax_ss_bolus"],
                    "cmin_ss_bolus": metrics["cmin_ss_bolus"],
                    "ptf_pct": metrics["peak_trough_fluctuation_pct"],
                    "accumulation_ratio_auc": metrics["accumulation_ratio_auc"],
                }
            )
        report.table("steady-state comparison", rows)
        report.note(
            "Cmax and Cmin here are the bolus-equivalent extremes. Average concentration depends only "
            "on the daily dose and clearance, so regimens matched on daily dose differ in fluctuation, "
            "not in Cavg."
        )
        return report.emit(args.format)

    if args.dose is None or (args.n_doses > 1 and not args.interval):
        raise InputError("--dose is required, and a multiple-dose regimen needs --interval")
    interval = args.interval or 0.0

    regimen = build_regimen(
        args.dose,
        interval=args.interval,
        n_doses=args.n_doses,
        duration=args.tinf,
        route="oral" if args.route == "oral" else "iv",
        loading=args.loading,
    )
    horizon = interval * args.n_doses if args.n_doses > 1 else max(interval, 1.0) * 10
    times = np.linspace(0.0, horizon, max(200 * max(args.n_doses, 1), 400) + 1)

    # ---- deterministic profile
    if args.nonlinear:
        def evaluate(grid: np.ndarray) -> np.ndarray:
            return simulate_michaelis_menten(
                grid,
                regimen,
                vmax=args.vmax,
                km=args.km,
                v1=args.v,
                q=args.q,
                vp=args.v2,
                ka=args.ka if args.route == "oral" else None,
                f=args.f,
            )

        conc = evaluate(times)
        report.note(
            "Michaelis-Menten elimination: exposure is not proportional to dose and superposition does "
            "not apply, so multiple-dose behaviour cannot be inferred from a single-dose profile."
        )
        cl_at_steady = args.vmax / (args.km + float(conc.max())) if conc.size else float("nan")
        report.scalar("clearance_at_peak_concentration", cl_at_steady)
    else:
        disp = disposition(args.cl, args.v, args.q, args.v2)

        def evaluate(grid: np.ndarray) -> np.ndarray:
            return simulate_linear(grid, regimen, disp, ka=args.ka, f=args.f, tlag=args.tlag)

        conc = evaluate(times)
        report.scalar("terminal_half_life", disp.terminal_half_life)
        report.scalar("vss", disp.vss)
        report.scalar("mrt_iv", disp.mrt_iv)
        for i, half in enumerate(disp.half_lives, start=1):
            report.scalar(f"t_half_phase{i}", float(half))

    if args.n_doses > 1:
        last = summarise_interval(evaluate, (args.n_doses - 1) * interval, args.n_doses * interval)
        first = summarise_interval(evaluate, 0.0, interval)
        report.table(
            "dosing-interval summary",
            [
                {"interval": "first", **first},
                {"interval": f"last (#{args.n_doses})", **last},
                {
                    "interval": "accumulation (last/first)",
                    "auc_tau": last["auc_tau"] / first["auc_tau"] if first["auc_tau"] else float("nan"),
                    "cmax": last["cmax"] / first["cmax"] if first["cmax"] else float("nan"),
                    "cmin": last["cmin"] / first["cmin"] if first["cmin"] > 0 else float("nan"),
                    "cavg": last["cavg"] / first["cavg"] if first["cavg"] else float("nan"),
                },
            ],
        )
    else:
        report.scalar("cmax", float(conc.max()))
        report.scalar("tmax", float(times[int(np.argmax(conc))]))
        report.scalar("auc_over_horizon", float(np.trapezoid(conc, times)))

    if args.steady_state and not args.nonlinear:
        metrics = steady_state_metrics(disposition(args.cl, args.v, args.q, args.v2), args.dose, interval, f=args.f)
        report.table("closed-form steady state", [{"metric": k, "value": v} for k, v in metrics.items()])
        if args.n_doses > 1 and args.n_doses * interval < metrics["time_to_95pct_ss"]:
            report.finding(
                f"the simulation covers {args.n_doses * interval:g} time units but 95% of steady state "
                f"is not reached until {metrics['time_to_95pct_ss']:.1f}; the last interval shown is not "
                "steady state"
            )

    # ---- Monte Carlo
    if args.simulate:
        if args.nonlinear:
            raise InputError("--simulate currently supports linear models only")
        if args.omega_cl <= 0 and args.omega_v <= 0:
            raise InputError("--simulate needs at least one of --omega-cl or --omega-v above zero")
        rng = np.random.default_rng(args.seed)
        n = args.simulate
        sd_cl = math.sqrt(math.log(1.0 + args.omega_cl**2)) if args.omega_cl > 0 else 0.0
        sd_v = math.sqrt(math.log(1.0 + args.omega_v**2)) if args.omega_v > 0 else 0.0
        cl_draws = args.cl * np.exp(rng.normal(0.0, sd_cl, n)) if sd_cl else np.full(n, args.cl)
        v_draws = args.v * np.exp(rng.normal(0.0, sd_v, n)) if sd_v else np.full(n, args.v)

        start = (args.n_doses - 1) * interval if args.n_doses > 1 else 0.0
        end = args.n_doses * interval if args.n_doses > 1 else horizon
        window = np.linspace(start, end, 401)
        troughs = np.empty(n)
        peaks = np.empty(n)
        aucs = np.empty(n)
        for i in range(n):
            disp_i = disposition(cl_draws[i], v_draws[i], args.q, args.v2)
            profile = simulate_linear(window, regimen, disp_i, ka=args.ka, f=args.f, tlag=args.tlag)
            troughs[i] = profile[-1] if args.n_doses > 1 else profile.min()
            peaks[i] = profile.max()
            aucs[i] = float(np.trapezoid(profile, window))

        def percentiles(values: np.ndarray, label: str) -> dict:
            return {
                "metric": label,
                "p5": float(np.percentile(values, 5)),
                "p25": float(np.percentile(values, 25)),
                "median": float(np.percentile(values, 50)),
                "p75": float(np.percentile(values, 75)),
                "p95": float(np.percentile(values, 95)),
                "geo_mean": float(np.exp(np.mean(np.log(np.maximum(values, 1e-12))))),
            }

        report.table(
            f"simulated population (n = {n})",
            [percentiles(peaks, "peak"), percentiles(troughs, "trough"), percentiles(aucs, "auc_over_interval")],
        )

        attainment = []
        if args.target_trough is not None:
            fraction = float(np.mean(troughs >= args.target_trough))
            attainment.append({"target": f"trough >= {args.target_trough:g}", "fraction_attaining": fraction})
        if args.target_peak_below is not None:
            fraction = float(np.mean(peaks <= args.target_peak_below))
            attainment.append({"target": f"peak <= {args.target_peak_below:g}", "fraction_attaining": fraction})
        if args.target_auc is not None:
            fraction = float(np.mean(aucs >= args.target_auc))
            attainment.append({"target": f"AUC >= {args.target_auc:g}", "fraction_attaining": fraction})
        if args.target_trough is not None and args.target_peak_below is not None:
            both = float(np.mean((troughs >= args.target_trough) & (peaks <= args.target_peak_below)))
            attainment.append({"target": "both trough and peak targets", "fraction_attaining": both})
        if attainment:
            report.table("probability of target attainment", attainment)
            for row in attainment:
                if row["fraction_attaining"] < 0.9:
                    report.finding(
                        f"{row['target']}: only {100 * row['fraction_attaining']:.1f}% of simulated "
                        "subjects attain this target"
                    )
        report.note(
            "Between-subject variability only, with independent CL/V draws and fixed population parameters. Between-occasion variability and parameter uncertainty may raise or lower attainment. Assay noise belongs to observed-level predictions, not latent true exposure."
        )

    if args.profile:
        step = max(len(times) // max(args.profile_points, 1), 1)
        report.table(
            "concentration-time profile",
            [{"time": float(t), "conc": float(c)} for t, c in zip(times[::step], conc[::step])],
        )

    return report.emit(args.format)


if __name__ == "__main__":
    raise SystemExit(main_wrapper(run))
