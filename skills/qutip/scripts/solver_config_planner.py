#!/usr/bin/env python3
"""Create a bounded QuTiP 5 solver and validation plan without simulation."""

from __future__ import annotations

import argparse
from typing import Any

from _common import (
    DEFAULT_SEED,
    MAX_TIME,
    MAX_TIME_POINTS,
    MAX_TRAJECTORIES,
    QUTIP_VERSION,
    CliError,
    add_output_arguments,
    bounded_int,
    emit_json,
    finite_float,
    run_cli,
)


MODELS = (
    "closed",
    "lindblad",
    "quantum-jump",
    "bloch-redfield",
    "diffusive",
    "periodic-closed",
    "periodic-open",
    "heom",
    "piqs",
)


def create_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Select a current solver and produce a model-specific checklist."""

    t_final = finite_float(
        args.t_final,
        name="t_final",
        minimum=0.0,
        maximum=MAX_TIME,
        minimum_inclusive=False,
    )
    time_points = bounded_int(
        args.time_points,
        name="time_points",
        minimum=2,
        maximum=MAX_TIME_POINTS,
    )
    trajectories = bounded_int(
        args.trajectories,
        name="trajectories",
        minimum=1,
        maximum=MAX_TRAJECTORIES,
    )
    seed = bounded_int(args.seed, name="seed", minimum=0, maximum=2**63 - 1)
    collapse_channels = bounded_int(
        args.collapse_channels,
        name="collapse_channels",
        minimum=0,
        maximum=64,
    )
    period = None
    if args.period is not None:
        period = finite_float(
            args.period,
            name="period",
            minimum=0.0,
            maximum=MAX_TIME,
            minimum_inclusive=False,
        )

    method = "bdf" if args.stiff else "adams"
    options: dict[str, Any] = {
        "method": method,
        "atol": 1.0e-10,
        "rtol": 1.0e-8,
        "store_states": bool(args.store_states),
        "store_final_state": True,
        "progress_bar": "",
    }
    required_inputs = [
        "unit convention and hbar convention",
        "ordered subsystem dimensions",
        "initial-state norm/trace/positivity audit",
        "Hamiltonian Hermiticity audit",
        "time-grid scale justification",
    ]
    convergence = [
        "tighten atol and rtol",
        "compare at least one alternative integrator",
        "increase output-grid density",
        "sweep every Hilbert-space truncation",
    ]
    warnings: list[str] = []
    call_arguments: dict[str, Any] = {
        "tlist": {"start": 0.0, "stop": t_final, "points": time_points},
        "options": options,
    }

    if args.model == "closed":
        solver = "sesolve"
        required_inputs.append("evidence that no dissipative channel is modeled")
        if args.initial_state != "ket":
            warnings.append(
                "sesolve requires a ket; use mesolve for a density-matrix initial state"
            )
        if collapse_channels:
            warnings.append("closed model conflicts with nonzero collapse_channels")
    elif args.model == "lindblad":
        solver = "mesolve"
        required_inputs.extend(
            [
                "Markovian Lindblad approximation",
                "each collapse operator written as sqrt(rate) times its operator",
            ]
        )
        if collapse_channels == 0:
            warnings.append("no collapse channels supplied; mesolve may defer to sesolve")
    elif args.model == "quantum-jump":
        solver = "mcsolve"
        required_inputs.extend(
            [
                "physical meaning of the jump unravelling",
                "nonzero collapse-operator list",
            ]
        )
        convergence.extend(["increase ntraj", "repeat or pair seeds deliberately"])
        call_arguments.update({"ntraj": trajectories, "seeds": seed})
        options["keep_runs_results"] = bool(args.store_states)
        if collapse_channels == 0:
            warnings.append("mcsolve requires a nonzero jump channel for this plan")
    elif args.model == "bloch-redfield":
        solver = "brmesolve"
        required_inputs.extend(
            [
                "Hermitian bath-coupling operators",
                "angular-frequency bath spectra including negative-frequency behavior",
                "Born-Markov and bath-stationarity assumptions",
                "justified sec_cutoff",
            ]
        )
        convergence.extend(
            ["vary sec_cutoff", "track minimum density-matrix eigenvalue over time"]
        )
        call_arguments["sec_cutoff"] = 0.1
        if not args.weak_coupling_confirmed:
            warnings.append("weak-coupling assumption has not been confirmed")
    elif args.model == "diffusive":
        # Unmonitored channels mix an initially pure state; SSE has no c_ops.
        solver = (
            "ssesolve"
            if args.initial_state == "ket" and collapse_channels == 0
            else "smesolve"
        )
        options.pop("atol")
        options.pop("rtol")
        options["method"] = "platen"
        convergence = [
            "decrease stochastic dt",
            "compare an alternative stochastic integrator",
            "increase output-grid density",
            "sweep every Hilbert-space truncation",
            "increase ntraj",
        ]
        required_inputs.extend(
            [
                "separate monitored sc_ops from unmonitored c_ops",
                "homodyne versus heterodyne measurement model",
                "measurement efficiency and record convention",
            ]
        )
        options["dt"] = t_final / max(time_points - 1, 1) / 2.0
        options["store_measurement"] = False
        options["keep_runs_results"] = bool(args.store_states)
        call_arguments.update(
            {"ntraj": trajectories, "seeds": seed, "heterodyne": False}
        )
    elif args.model == "periodic-closed":
        solver = "FloquetBasis + fsesolve"
        call_arguments["floquet_basis_options"] = {
            key: options.pop(key) for key in ("method", "atol", "rtol")
        }
        required_inputs.append(
            "pass floquet_basis_options to FloquetBasis, not fsesolve result options"
        )
        required_inputs.extend(
            [
                "verified H(t + T) equals H(t)",
                "quasi-energy branch convention",
            ]
        )
        convergence.extend(
            ["compare one-period propagator with direct evolution", "sweep precompute grid"]
        )
        call_arguments["T"] = period
        if period is None:
            warnings.append("a positive --period is required")
    elif args.model == "periodic-open":
        solver = "FloquetBasis + fmmesolve"
        required_inputs.extend(
            [
                "verified H(t + T) equals H(t)",
                "paired coupling operators and bath spectrum callbacks",
                "weak-coupling Floquet-Markov assumptions",
                "temperature/frequency unit convention",
            ]
        )
        convergence.extend(
            [
                "sweep Floquet precompute grid",
                "compare with direct mesolve in a valid limit",
            ]
        )
        call_arguments["T"] = period
        if period is None:
            warnings.append("a positive --period is required")
        if not args.weak_coupling_confirmed:
            warnings.append("weak-coupling assumption has not been confirmed")
    elif args.model == "heom":
        solver = "qutip.solver.heom.HEOMSolver"
        required_inputs.extend(
            [
                "bath correlation expansion and coupling operator",
                "temperature, cutoff, and energy units",
                "factorized or continued ADO initial condition",
            ]
        )
        convergence.extend(
            [
                "increase hierarchy max_depth",
                "increase bath expansion terms",
                "compare Matsubara and Pade/environment approximations",
            ]
        )
        call_arguments.update({"max_depth": "model-specific", "bath": "required"})
    else:
        solver = "qutip.piqs.Dicke.liouvillian + mesolve"
        required_inputs.extend(
            [
                "permutation symmetry of constituents and dynamics",
                "Dicke versus uncoupled basis",
                "separate local and collective rates",
            ]
        )
        convergence.extend(
            ["compare a small-N full-space model", "verify symmetry-sector assumptions"]
        )

    if args.time_dependent:
        required_inputs.extend(
            [
                "QobjEvo with trusted Pythonic callables or numeric arrays",
                "coefficient sampling/envelope convergence",
            ]
        )
    if args.stiff and args.model == "diffusive":
        warnings.append(
            "--stiff does not select bdf for stochastic dynamics; reduce dt and "
            "review a supported implicit stochastic method"
        )
    elif args.stiff:
        convergence.append("compare bdf with lsoda on representative observables")

    return {
        "report_type": "qutip.solver_config_plan",
        "schema_version": 1,
        "qutip_version": QUTIP_VERSION,
        "model": args.model,
        "initial_state": args.initial_state,
        "recommended_solver": solver,
        "call_configuration": call_arguments,
        "required_inputs_and_assumptions": required_inputs,
        "convergence_plan": convergence,
        "warnings": warnings,
        "status": "needs_review" if warnings else "ready_for_model_construction",
        "safety": {
            "network": False,
            "model_code_loaded": False,
            "planner_only": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan a QuTiP 5 solver configuration and model-specific numerical "
            "checks without importing QuTiP or running a simulation."
        )
    )
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument(
        "--initial-state",
        choices=("ket", "density"),
        default="ket",
    )
    parser.add_argument(
        "--collapse-channels", type=int, default=0,
        help="number of c_ops (unmonitored channels for diffusive models)",
    )
    parser.add_argument("--time-dependent", action="store_true")
    parser.add_argument("--stiff", action="store_true")
    parser.add_argument("--weak-coupling-confirmed", action="store_true")
    parser.add_argument("--period", type=float)
    parser.add_argument("--t-final", type=float, default=10.0)
    parser.add_argument("--time-points", type=int, default=201)
    parser.add_argument("--trajectories", type=int, default=400)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--store-states", action="store_true")
    add_output_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = create_plan(args)
    emit_json(report, output=args.output, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
