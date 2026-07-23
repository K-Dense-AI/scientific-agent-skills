#!/usr/bin/env python3
"""Run a parameterized circuit with Qiskit V2 local primitives."""

from __future__ import annotations

import argparse
import json
import math
from importlib.metadata import PackageNotFoundError, version
from typing import Any


MAX_SHOTS = 1_000_000


def positive_bounded_shots(value: str) -> int:
    shots = int(value)
    if shots < 1:
        raise argparse.ArgumentTypeError("shots must be positive")
    if shots > MAX_SHOTS:
        raise argparse.ArgumentTypeError(f"shots must not exceed {MAX_SHOTS:,}")
    return shots


def finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError("theta must be finite")
    return parsed


def qiskit_version() -> str:
    try:
        return version("qiskit")
    except PackageNotFoundError:
        return "not installed"


def run_workflow(
    shots: int,
    seed: int,
    theta_value: float,
) -> dict[str, Any]:
    import numpy as np
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter
    from qiskit.primitives import (
        StatevectorEstimator,
        StatevectorSampler,
    )
    from qiskit.quantum_info import SparsePauliOp

    theta = Parameter("theta")
    circuit = QuantumCircuit(2, name="parameterized_bell")
    circuit.ry(theta, 0)
    circuit.cx(0, 1)

    parameter_values = [[theta_value]]
    parameter_order = [parameter.name for parameter in circuit.parameters]

    observable = SparsePauliOp.from_list(
        [
            ("ZI", 1.0),
            ("XX", 0.5),
        ]
    )
    estimator = StatevectorEstimator(seed=seed)
    estimator_result = estimator.run(
        [(circuit, observable, parameter_values)]
    ).result()[0]

    expectation_value = float(np.asarray(estimator_result.data.evs).reshape(-1)[0])
    standard_deviation = float(np.asarray(estimator_result.data.stds).reshape(-1)[0])
    analytic_expectation = math.cos(theta_value) + 0.5 * math.sin(theta_value)

    measured_circuit = circuit.copy()
    measured_circuit.measure_all()
    sampler = StatevectorSampler(seed=seed)
    sampler_result = sampler.run(
        [(measured_circuit, parameter_values)],
        shots=shots,
    ).result()[0]
    counts = sampler_result.data.meas.get_counts(0)

    observed_shots = sum(counts.values())
    probabilities = {
        bitstring: count / observed_shots for bitstring, count in sorted(counts.items())
    }
    expected_probabilities = {
        "00": math.cos(theta_value / 2) ** 2,
        "11": math.sin(theta_value / 2) ** 2,
    }

    return {
        "qiskit_version": qiskit_version(),
        "seed": seed,
        "shots": shots,
        "theta": theta_value,
        "parameter_order": parameter_order,
        "observable": "1.0 * ZI + 0.5 * XX",
        "estimator": {
            "expectation_value": expectation_value,
            "standard_deviation": standard_deviation,
            "analytic_expectation": analytic_expectation,
            "absolute_error": abs(expectation_value - analytic_expectation),
        },
        "sampler": {
            "counts": dict(sorted(counts.items())),
            "probabilities": probabilities,
            "expected_probabilities": expected_probabilities,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a two-qubit parameterized circuit with "
            "StatevectorSampler and StatevectorEstimator."
        )
    )
    parser.add_argument(
        "--shots",
        type=positive_bounded_shots,
        default=1024,
        help=f"Sampler shots (1-{MAX_SHOTS:,}; default: 1024).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Local sampler and estimator seed (default: 7).",
    )
    parser.add_argument(
        "--theta",
        type=finite_float,
        default=math.pi / 2,
        help="Circuit angle in radians (default: pi/2).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )
    return parser


def print_human(result: dict[str, Any]) -> None:
    print("Qiskit:", result["qiskit_version"])
    print(
        "Inputs:",
        f"theta={result['theta']:.8f}",
        f"shots={result['shots']}",
        f"seed={result['seed']}",
    )
    print("Parameter order:", result["parameter_order"])
    print("Observable:", result["observable"])

    estimator = result["estimator"]
    print(
        "Estimator:",
        f"{estimator['expectation_value']:.12f}",
        "(analytic",
        f"{estimator['analytic_expectation']:.12f},",
        "absolute error",
        f"{estimator['absolute_error']:.3e})",
    )

    sampler = result["sampler"]
    print("Sampler counts:", sampler["counts"])
    print("Sampler probabilities:", sampler["probabilities"])
    print(
        "Expected probabilities:",
        sampler["expected_probabilities"],
    )


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run_workflow(
            shots=args.shots,
            seed=args.seed,
            theta_value=args.theta,
        )
    except ModuleNotFoundError as error:
        raise SystemExit(
            "Qiskit is not installed. Install the pinned core package "
            'with: uv pip install "qiskit==2.5.0"'
        ) from error

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
