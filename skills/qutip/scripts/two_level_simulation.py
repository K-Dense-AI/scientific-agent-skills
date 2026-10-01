#!/usr/bin/env python3
"""Run a bounded synthetic two-level open-system simulation."""

from __future__ import annotations

import argparse
import math
from dataclasses import asdict, dataclass
from typing import Any

from _common import (
    DEFAULT_SEED,
    MAX_ABS_FREQUENCY,
    MAX_RATE,
    MAX_TIME,
    MAX_TIME_POINTS,
    MAX_TRAJECTORIES,
    QUTIP_VERSION,
    CliError,
    add_output_arguments,
    bounded_int,
    emit_json,
    finite_float,
    load_qutip,
    run_cli,
    to_jsonable,
)


METHODS = {"adams", "bdf", "lsoda", "dop853", "vern7", "vern9"}
INITIAL_STATES = {"excited", "ground", "plus"}


@dataclass(frozen=True)
class SimulationConfig:
    solver: str
    initial_state: str
    omega: float
    drive: float
    decay_rate: float
    dephasing_rate: float
    t_final: float
    time_points: int
    trajectories: int
    seed: int
    method: str
    atol: float
    rtol: float

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "SimulationConfig":
        solver = str(args.solver)
        if solver not in {"mesolve", "mcsolve"}:
            raise CliError("solver must be mesolve or mcsolve")
        initial_state = str(args.initial_state)
        if initial_state not in INITIAL_STATES:
            raise CliError(
                f"initial_state must be one of: {', '.join(sorted(INITIAL_STATES))}"
            )
        method = str(args.method)
        if method not in METHODS:
            raise CliError(f"method must be one of: {', '.join(sorted(METHODS))}")
        config = cls(
            solver=solver,
            initial_state=initial_state,
            omega=finite_float(
                args.omega,
                name="omega",
                minimum=-MAX_ABS_FREQUENCY,
                maximum=MAX_ABS_FREQUENCY,
            ),
            drive=finite_float(
                args.drive,
                name="drive",
                minimum=-MAX_ABS_FREQUENCY,
                maximum=MAX_ABS_FREQUENCY,
            ),
            decay_rate=finite_float(
                args.decay_rate,
                name="decay_rate",
                minimum=0.0,
                maximum=MAX_RATE,
            ),
            dephasing_rate=finite_float(
                args.dephasing_rate,
                name="dephasing_rate",
                minimum=0.0,
                maximum=MAX_RATE,
            ),
            t_final=finite_float(
                args.t_final,
                name="t_final",
                minimum=0.0,
                maximum=MAX_TIME,
                minimum_inclusive=False,
            ),
            time_points=bounded_int(
                args.time_points,
                name="time_points",
                minimum=2,
                maximum=MAX_TIME_POINTS,
            ),
            trajectories=bounded_int(
                args.trajectories,
                name="trajectories",
                minimum=1,
                maximum=MAX_TRAJECTORIES,
            ),
            seed=bounded_int(
                args.seed,
                name="seed",
                minimum=0,
                maximum=2**63 - 1,
            ),
            method=method,
            atol=finite_float(
                args.atol,
                name="atol",
                minimum=1.0e-14,
                maximum=1.0e-2,
            ),
            rtol=finite_float(
                args.rtol,
                name="rtol",
                minimum=1.0e-14,
                maximum=1.0e-2,
            ),
        )
        if config.atol > config.rtol:
            raise CliError("atol must be no greater than rtol")
        if (
            config.solver == "mcsolve"
            and config.decay_rate == 0.0
            and config.dephasing_rate == 0.0
        ):
            raise CliError("mcsolve requires at least one nonzero collapse rate")
        return config


def _initial_state(qutip: Any, label: str) -> Any:
    excited = qutip.basis(2, 0)
    ground = qutip.basis(2, 1)
    if label == "excited":
        return excited
    if label == "ground":
        return ground
    return (excited + ground).unit()


def _state_audit(state: Any, tolerance: float) -> dict[str, Any]:
    if state is None:
        return {"available": False}
    if state.isket:
        norm = float(state.norm())
        return {
            "available": True,
            "representation": "ket",
            "norm": norm,
            "normalization_error": abs(norm - 1.0),
            "valid_within_tolerance": abs(norm - 1.0) <= tolerance,
        }
    trace = complex(state.tr())
    hermitian = bool(state.isherm)
    minimum_eigenvalue = (
        min(float(value) for value in state.eigenenergies())
        if hermitian
        else None
    )
    valid = (
        hermitian
        and abs(trace - 1.0) <= tolerance
        and minimum_eigenvalue is not None
        and minimum_eigenvalue >= -tolerance
    )
    return {
        "available": True,
        "representation": "density_matrix",
        "is_hermitian": hermitian,
        "trace": trace,
        "trace_error": abs(trace - 1.0),
        "minimum_eigenvalue": minimum_eigenvalue,
        "valid_within_tolerance": valid,
    }


def _seed_manifest(seeds: Any) -> list[Any] | None:
    if seeds is None:
        return None
    manifest: list[Any] = []
    for seed in seeds:
        if isinstance(seed, int):
            manifest.append(seed)
            continue
        manifest.append(
            {
                "entropy": to_jsonable(getattr(seed, "entropy", None)),
                "spawn_key": list(getattr(seed, "spawn_key", ())),
            }
        )
    return manifest


def run_simulation(
    config: SimulationConfig,
    qutip_module: Any | None = None,
) -> dict[str, Any]:
    """Execute one bounded model and return a strict-JSON-ready report."""

    qutip = qutip_module or load_qutip()
    import numpy as np

    times = np.linspace(0.0, config.t_final, config.time_points)
    excited = qutip.basis(2, 0)
    psi0 = _initial_state(qutip, config.initial_state)
    H = 0.5 * config.omega * qutip.sigmaz() + 0.5 * config.drive * qutip.sigmax()
    c_ops = []
    if config.decay_rate > 0.0:
        c_ops.append(np.sqrt(config.decay_rate) * qutip.sigmam())
    if config.dephasing_rate > 0.0:
        c_ops.append(
            np.sqrt(config.dephasing_rate / 2.0) * qutip.sigmaz()
        )
    e_ops = [excited.proj(), qutip.sigmax(), qutip.sigmay(), qutip.sigmaz()]
    options = {
        "method": config.method,
        "atol": config.atol,
        "rtol": config.rtol,
        "store_final_state": True,
        "progress_bar": "",
    }

    if config.solver == "mesolve":
        # Default output normalization can conceal norm/trace integration drift.
        options["normalize_output"] = False
        result = qutip.mesolve(
            H,
            psi0,
            times,
            c_ops=c_ops,
            e_ops=e_ops,
            options=options,
        )
        trajectories_run = None
        trajectory_std = None
        standard_error = None
        seed_manifest = None
    else:
        result = qutip.mcsolve(
            H,
            psi0,
            times,
            c_ops,
            e_ops=e_ops,
            ntraj=config.trajectories,
            seeds=config.seed,
            options={**options, "keep_runs_results": False},
        )
        trajectories_run = int(
            getattr(result, "num_trajectories", config.trajectories)
        )
        trajectory_std = np.asarray(result.std_expect[0], dtype=float)
        standard_error = trajectory_std / math.sqrt(trajectories_run)
        seed_manifest = _seed_manifest(getattr(result, "seeds", None))

    population = np.asarray(result.expect[0], dtype=float)
    sigma_x = np.asarray(result.expect[1], dtype=float)
    sigma_y = np.asarray(result.expect[2], dtype=float)
    sigma_z = np.asarray(result.expect[3], dtype=float)

    initial_population = {
        "excited": 1.0,
        "ground": 0.0,
        "plus": 0.5,
    }[config.initial_state]
    analytic_applicable = config.drive == 0.0
    analytic_population = (
        initial_population * np.exp(-config.decay_rate * times)
        if analytic_applicable
        else None
    )
    max_abs_analytic_error = (
        float(np.max(np.abs(population - analytic_population)))
        if analytic_population is not None
        else None
    )
    lower_violation = max(0.0, float(-np.min(population)))
    upper_violation = max(0.0, float(np.max(population) - 1.0))
    probability_violation = max(lower_violation, upper_violation)
    invariant_tolerance = max(10.0 * config.atol, 10.0 * config.rtol)
    final_state_audit = _state_audit(
        getattr(result, "final_state", None),
        invariant_tolerance,
    )

    return {
        "report_type": "qutip.two_level_simulation",
        "schema_version": 1,
        "qutip_version": QUTIP_VERSION,
        "unit_convention": "hbar=1; angular-frequency and reciprocal-time units",
        "configuration": asdict(config),
        "model": {
            "hilbert_dimension": 2,
            "basis_labels": "excited=basis(2,0); ground=basis(2,1); fixed sigma_z basis, not dressed energy order",
            "hamiltonian": "0.5 * omega * sigma_z + 0.5 * drive * sigma_x",
            "amplitude_decay": "sqrt(decay_rate) * sigma_minus",
            "pure_dephasing": "sqrt(dephasing_rate / 2) * sigma_z",
            "initial_population": initial_population,
            "assumptions": [
                "finite two-level model",
                "time-independent Hamiltonian",
                "Markovian Lindblad channels",
                "dephasing_rate denotes off-diagonal coherence decay",
            ],
        },
        "times": times,
        "expectations": {
            "excited_population": population,
            "sigma_x": sigma_x,
            "sigma_y": sigma_y,
            "sigma_z": sigma_z,
        },
        "analytic_reference": {
            "applicable": analytic_applicable,
            "excited_population": analytic_population,
            "max_abs_error": max_abs_analytic_error,
            "reason_if_not_applicable": (
                None
                if analytic_applicable
                else "nonzero transverse drive changes the population equation"
            ),
        },
        "trajectory_statistics": {
            "uncertainty_note": (
                "Independent-trajectory spread/sqrt(n); one trajectory or no "
                "observed rare jumps cannot establish sampling precision."
                if config.solver == "mcsolve" else None
            ),
            "trajectories_requested": (
                config.trajectories if config.solver == "mcsolve" else None
            ),
            "trajectories_run": trajectories_run,
            "seeds": seed_manifest,
            "excited_population_std": trajectory_std,
            "excited_population_standard_error_estimate": standard_error,
        },
        "checks": {
            "time_grid_strictly_increasing": True,
            "maximum_population_bound_violation": probability_violation,
            "population_within_tolerance": probability_violation
            <= invariant_tolerance,
            "final_state": final_state_audit,
        },
        "solver": {
            "name": getattr(result, "solver", config.solver),
            "options_requested": options,
            "stats": getattr(result, "stats", {}),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a bounded two-level Lindblad or quantum-jump simulation and "
            "emit strict JSON with analytic and physical checks."
        )
    )
    parser.add_argument("--solver", choices=("mesolve", "mcsolve"), default="mesolve")
    parser.add_argument(
        "--initial-state",
        choices=tuple(sorted(INITIAL_STATES)),
        default="excited",
    )
    parser.add_argument("--omega", type=float, default=1.0)
    parser.add_argument("--drive", type=float, default=0.0)
    parser.add_argument("--decay-rate", type=float, default=0.2)
    parser.add_argument("--dephasing-rate", type=float, default=0.0)
    parser.add_argument("--t-final", type=float, default=10.0)
    parser.add_argument("--time-points", type=int, default=201)
    parser.add_argument("--trajectories", type=int, default=400)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--method", choices=tuple(sorted(METHODS)), default="adams")
    parser.add_argument("--atol", type=float, default=1.0e-10)
    parser.add_argument("--rtol", type=float, default=1.0e-8)
    add_output_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = SimulationConfig.from_namespace(args)
    report = run_simulation(config)
    emit_json(report, output=args.output, force=args.force)
    checks = report["checks"]
    return 0 if (
        checks["population_within_tolerance"]
        and checks["final_state"].get("valid_within_tolerance", False)
    ) else 1


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
