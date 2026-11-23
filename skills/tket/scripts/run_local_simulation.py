#!/usr/bin/env python3
"""Run local pytket simulations and print shots, statevectors, and expectation values.

Everything executes against a local simulator - no hardware, no credentials, no network.
Requires pytket and pytket-qiskit with the [aer] extra (see references/setup.md).

Usage:
    python scripts/run_local_simulation.py
    python scripts/run_local_simulation.py --shots 4000 --seed 7
    python scripts/run_local_simulation.py --qasm circuit.qasm --shots 1000
    python scripts/run_local_simulation.py --json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

# Angles in pytket are half-turns (multiples of pi), never radians.
HALF_TURNS_PER_RADIAN = 1.0 / math.pi


def ghz_circuit(n_qubits: int) -> Any:
    """n-qubit GHZ state, fully measured."""
    from pytket.circuit import Circuit

    circuit = Circuit(n_qubits, n_qubits).H(0)
    for index in range(n_qubits - 1):
        circuit.CX(index, index + 1)
    circuit.measure_all()
    return circuit


def bell_circuit() -> Any:
    """Bell pair with measurements - the smallest circuit that shows ILO-BE ordering."""
    from pytket.circuit import Circuit

    return Circuit(2, 2).H(0).CX(0, 1).measure_all()


def parameterised_ansatz(theta: float) -> Any:
    """Two-qubit ansatz with a concrete angle substituted in (theta is in half-turns)."""
    from pytket.circuit import Circuit

    return Circuit(2).Ry(theta, 0).CX(0, 1).Rz(theta, 1)


def load_qasm(path: Path) -> Any:
    """Load an OpenQASM 2 circuit. pytket has no OpenQASM 3 support."""
    from pytket.qasm import circuit_from_qasm

    return circuit_from_qasm(str(path))


def counts_summary(result: Any) -> dict[str, Any]:
    """Summarise a BackendResult's counts. Keys are bit-tuples ordered ILO-BE."""
    counts = result.get_counts()
    total = sum(counts.values())
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    return {
        "total_shots": total,
        "distinct_outcomes": len(counts),
        "top_outcomes": [
            {"bits": list(bits), "count": count, "probability": count / total}
            for bits, count in top
        ],
    }


def statevector_summary(backend: Any, circuit: Any) -> dict[str, Any]:
    """Exact statevector for an unmeasured circuit, reported as magnitudes.

    get_state() is a method on BackendResult, not on Backend: you must run the circuit
    through a state-simulating backend first. The circuit must have no measurements.
    """
    if not backend.supports_state:
        return {"skipped": "backend does not support state simulation"}
    if circuit.n_bits:
        return {"skipped": "circuit contains measurements; use an unmeasured copy"}
    compiled = backend.get_compiled_circuit(circuit)
    state = backend.run_circuit(compiled, seed=1).get_state()
    magnitudes = [float(abs(amplitude)) for amplitude in state]
    significant = [
        {"index": index, "magnitude": magnitude}
        for index, magnitude in enumerate(magnitudes)
        if magnitude > 1e-9
    ]
    return {"n_qubits": circuit.n_qubits, "significant_amplitudes": significant}


def _real(value: Any) -> float:
    """Coerce an expectation value to float. The API is typed as returning complex."""
    return float(value.real if isinstance(value, complex) else value)


def expectation_report(backend: Any, theta: float, n_shots: int) -> dict[str, Any]:
    """Compare the exact and shot-based routes for <Z0 Z1> on the ansatz.

    Two type traps, both worth knowing:
      * Backend.get_operator_expectation_value takes NO n_shots keyword (the Aer override
        is (state_circuit, operator, valid_check=True)); passing one raises TypeError.
      * It requires a QubitPauliOperator. Feeding it a bare QubitPauliString fails deep in
        the Aer extension with "AttributeError: 'QubitPauliString' object has no attribute
        '_dict'". Use get_pauli_expectation_value for a string.
    """
    from pytket.pauli import Pauli, QubitPauliString
    from pytket.utils import (
        QubitPauliOperator,
        expectation_from_counts,
        get_operator_expectation_value,
    )

    state_circuit = backend.get_compiled_circuit(parameterised_ansatz(theta))
    zz = QubitPauliString(
        [state_circuit.qubits[0], state_circuit.qubits[1]], [Pauli.Z, Pauli.Z]
    )
    operator = QubitPauliOperator({zz: 1.0})

    # These are typed as returning complex, so take .real rather than calling float(),
    # which raises TypeError on a complex value.
    exact = _real(backend.get_operator_expectation_value(state_circuit, operator))
    exact_pauli = _real(backend.get_pauli_expectation_value(state_circuit, zz))
    sampled = _real(
        get_operator_expectation_value(state_circuit, operator, backend, n_shots=n_shots)
    )

    # A measured circuit plus counts gives the same number with no backend support needed.
    measured = state_circuit.copy()
    measured.measure_all()
    from_counts = _real(
        expectation_from_counts(
            backend.run_circuit(measured, n_shots=n_shots, seed=11).get_counts()
        )
    )

    return {
        "observable": "<Z0 Z1>",
        "theta_half_turns": theta,
        "exact_operator": exact,
        "exact_pauli_string": exact_pauli,
        "shot_based_operator_helper": sampled,
        "from_counts": from_counts,
        "shots": n_shots,
    }


def batch_report(backend: Any, n_shots: int) -> dict[str, Any]:
    """Submit several circuits in one batch and read the results back in order."""
    circuits = [bell_circuit(), ghz_circuit(3), ghz_circuit(4)]
    results = backend.run_circuits(circuits, n_shots=n_shots, seed=13)
    return {
        "circuits_submitted": len(circuits),
        "results_returned": len(results),
        "counts_per_circuit": [counts_summary(result) for result in results],
    }


def run(qasm_path: Path | None, n_shots: int, n_qubits: int, theta: float, seed: int) -> dict[str, Any]:
    """Execute every check and collect a JSON-serialisable report."""
    from pytket.extensions.qiskit import AerBackend, AerStateBackend

    shot_backend = AerBackend()
    state_backend = AerStateBackend()

    report: dict[str, Any] = {
        "backend": shot_backend.backend_info.name,
        "capabilities": {
            "supports_shots": shot_backend.supports_shots,
            "supports_counts": shot_backend.supports_counts,
            "supports_state": shot_backend.supports_state,
            "supports_unitary": shot_backend.supports_unitary,
            "supports_expectation": shot_backend.supports_expectation,
            "supports_contextual_optimisation": shot_backend.supports_contextual_optimisation,
        },
        "n_shots": n_shots,
        "seed": seed,
    }

    if qasm_path is not None:
        circuit = load_qasm(qasm_path)
        report["qasm_source"] = str(qasm_path)
        report["qasm_n_qubits"] = circuit.n_qubits
        report["qasm_counts"] = counts_summary(
            shot_backend.run_circuit(circuit, n_shots=n_shots, seed=seed)
        )
        return report

    report["bell_counts"] = counts_summary(
        shot_backend.run_circuit(bell_circuit(), n_shots=n_shots, seed=seed)
    )
    report["ghz_counts"] = counts_summary(
        shot_backend.run_circuit(ghz_circuit(n_qubits), n_shots=n_shots, seed=seed)
    )
    report["n_qubits"] = n_qubits
    report["bell_statevector"] = statevector_summary(state_backend, _bell_unmeasured())
    report["shots_shape"] = _shots_shape(shot_backend, n_shots, seed)
    report["expectation"] = expectation_report(shot_backend, theta, n_shots)
    report["batch"] = batch_report(shot_backend, min(n_shots, 500))
    report["ordering_note"] = (
        "counts keys are bit-tuples in ILO-BE order (qubit 0 first); Qiskit prints them "
        "reversed, so the same circuit gives '01' here and '10' in Qiskit"
    )
    return report


def _bell_unmeasured() -> Any:
    from pytket.circuit import Circuit

    return Circuit(2).H(0).CX(0, 1)


def _shots_shape(backend: Any, n_shots: int, seed: int) -> dict[str, Any]:
    shots = backend.run_circuit(ghz_circuit(3), n_shots=n_shots, seed=seed).get_shots()
    return {"shape": list(shots.shape), "dtype": str(shots.dtype)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_local_simulation.py",
        description="Run local pytket simulations: shots, statevector, expectation values, batching.",
    )
    parser.add_argument("--shots", type=int, default=1000, help="number of shots (default 1000)")
    parser.add_argument("--qubits", type=int, default=3, help="GHZ width for the demo (default 3)")
    parser.add_argument(
        "--theta",
        type=float,
        default=0.25,
        help="ansatz angle in HALF-TURNS for the expectation demo (default 0.25 = pi/4)",
    )
    parser.add_argument("--seed", type=int, default=7, help="simulator seed for reproducibility")
    parser.add_argument(
        "--qasm",
        type=Path,
        default=None,
        help="run an OpenQASM 2 file instead of the built-in demos",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    return parser


def print_human_report(report: dict[str, Any]) -> None:
    print(f"Backend: {report['backend']}")
    print("Capabilities:")
    for key, value in report["capabilities"].items():
        print(f"  {key}: {value}")
    print()
    if "qasm_source" in report:
        print(f"Loaded {report['qasm_source']} ({report['qasm_n_qubits']} qubits)")
        _print_counts("QASM circuit", report["qasm_counts"])
        return
    _print_counts("Bell pair", report["bell_counts"])
    _print_counts(f"GHZ ({report.get('n_qubits', '')})", report["ghz_counts"])
    print()
    print("Bell statevector (exact):")
    for entry in report["bell_statevector"]["significant_amplitudes"]:
        print(f"  |{entry['index']:0>2b}> magnitude {entry['magnitude']:.6f}")
    print()
    print(f"get_shots() -> shape {report['shots_shape']['shape']}, "
          f"dtype {report['shots_shape']['dtype']}")
    print()
    expectation = report["expectation"]
    print(f"Expectation {expectation['observable']} at theta={expectation['theta_half_turns']}"
          f" half-turns ({expectation['shots']} shots):")
    print(f"  exact, Backend.get_operator_expectation_value: {expectation['exact_operator']:.6f}")
    print(f"  exact, Backend.get_pauli_expectation_value:    {expectation['exact_pauli_string']:.6f}")
    print(f"  pytket.utils helper (n_shots=...):        "
          f"{expectation['shot_based_operator_helper']:.6f}")
    print(f"  expectation_from_counts:                  {expectation['from_counts']:.6f}")
    print()
    batch = report["batch"]
    print(f"Batch submission: {batch['circuits_submitted']} circuits -> "
          f"{batch['results_returned']} results")
    print()
    print(report["ordering_note"])


def _print_counts(title: str, summary: dict[str, Any]) -> None:
    print(f"{title}: {summary['total_shots']} shots, "
          f"{summary['distinct_outcomes']} distinct outcome(s)")
    for entry in summary["top_outcomes"]:
        bits = "".join(str(bit) for bit in entry["bits"])
        print(f"  |{bits}> {entry['count']:>5} ({entry['probability']:.3f})")


def main() -> int:
    args = build_parser().parse_args()
    if args.qasm is not None and not args.qasm.is_file():
        raise SystemExit(f"QASM file not found: {args.qasm}")
    try:
        report = run(args.qasm, args.shots, args.qubits, args.theta, args.seed)
    except ImportError as error:
        raise SystemExit(
            f"Missing dependency: {error}\n"
            "Install with: python -m pip install pytket \"pytket-qiskit[aer]\""
        ) from error
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_human_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
