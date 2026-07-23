#!/usr/bin/env python3
"""Inspect one IBM Runtime backend without submitting a quantum job."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any


def positive_qubits(value: str) -> int:
    qubits = int(value)
    if qubits < 1:
        raise argparse.ArgumentTypeError("minimum qubits must be positive")
    if qubits > 10_000:
        raise argparse.ArgumentTypeError("minimum qubits is implausibly large")
    return qubits


def distribution_version(distribution: str) -> str | None:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def select_backend(
    service: Any,
    backend_name: str | None,
    min_qubits: int,
    use_fractional_gates: bool | None,
) -> Any:
    feature_kwargs: dict[str, Any] = {}
    if use_fractional_gates is not None:
        feature_kwargs["use_fractional_gates"] = use_fractional_gates

    if backend_name:
        return service.backend(
            backend_name,
            **feature_kwargs,
        )

    return service.least_busy(
        operational=True,
        simulator=False,
        min_num_qubits=min_qubits,
        **feature_kwargs,
    )


def inspect_backend(backend: Any) -> dict[str, Any]:
    status = backend.status()
    operation_names = sorted(backend.operation_names)

    coupling_map = backend.coupling_map
    coupling_edges = list(coupling_map.get_edges()) if coupling_map is not None else []

    control_flow_names = {
        "if_else",
        "while_loop",
        "for_loop",
        "switch_case",
        "store",
    }
    exposed_control_flow = sorted(control_flow_names.intersection(operation_names))

    fractional_candidates = {
        "rx",
        "rzz",
    }
    exposed_fractional_candidates = sorted(
        fractional_candidates.intersection(operation_names)
    )

    target = backend.target
    return {
        "backend": {
            "name": backend.name,
            "num_qubits": backend.num_qubits,
            "operational": getattr(
                status,
                "operational",
                None,
            ),
            "pending_jobs": getattr(
                status,
                "pending_jobs",
                None,
            ),
            "status_message": getattr(
                status,
                "status_msg",
                None,
            ),
            "max_circuits": getattr(
                backend,
                "max_circuits",
                None,
            ),
        },
        "target": {
            "operation_names": operation_names,
            "control_flow_operations": exposed_control_flow,
            "fractional_gate_candidates": (exposed_fractional_candidates),
            "coupling_edge_count": len(coupling_edges),
            "coupling_edges": coupling_edges,
            "dt_seconds": getattr(target, "dt", None),
            "dtm_seconds": getattr(target, "dtm", None),
        },
        "versions": {
            "qiskit": distribution_version("qiskit"),
            "qiskit-ibm-runtime": distribution_version("qiskit-ibm-runtime"),
        },
        "submitted_jobs": 0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Select and inspect one accessible IBM Quantum backend. "
            "Uses saved credentials, performs network reads, and never "
            "submits a job."
        )
    )
    parser.add_argument(
        "--backend",
        help=(
            "Inspect this backend name. If omitted, select the least "
            "busy accessible backend matching --min-qubits."
        ),
    )
    parser.add_argument(
        "--min-qubits",
        type=positive_qubits,
        default=5,
        help="Minimum qubits for automatic selection (default: 5).",
    )
    parser.add_argument(
        "--fractional-gates",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Explicitly request or disable a fractional-gate target. "
            "By default, use the service default."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON.",
    )
    return parser


def print_human(report: dict[str, Any]) -> None:
    backend = report["backend"]
    target = report["target"]

    print("Backend:", backend["name"])
    print("Qubits:", backend["num_qubits"])
    print("Operational:", backend["operational"])
    print("Pending jobs:", backend["pending_jobs"])
    print("Status:", backend["status_message"])
    print("Maximum circuits per job:", backend["max_circuits"])
    print("Coupling edges:", target["coupling_edge_count"])
    print(
        "Control flow operations:",
        target["control_flow_operations"] or "none exposed",
    )
    print(
        "Fractional-gate candidates:",
        target["fractional_gate_candidates"] or "none exposed",
    )
    print("Target operations:")
    print("  " + ", ".join(target["operation_names"]))
    print("Versions:", report["versions"])
    print("Submitted jobs: 0")


def main() -> int:
    args = build_parser().parse_args()

    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ModuleNotFoundError:
        print(
            "qiskit-ibm-runtime is not installed. Install the pinned "
            'package with: uv pip install "qiskit-ibm-runtime==0.48.0"',
            file=sys.stderr,
        )
        return 2

    try:
        service = QiskitRuntimeService()
        backend = select_backend(
            service=service,
            backend_name=args.backend,
            min_qubits=args.min_qubits,
            use_fractional_gates=args.fractional_gates,
        )
        report = inspect_backend(backend)
    except Exception as error:
        # Do not echo request payloads, account details, or credential data.
        print(
            "Runtime inspection failed "
            f"({type(error).__name__}). Verify the saved "
            "ibm_quantum_platform account, instance access, network, "
            "and requested backend.",
            file=sys.stderr,
        )
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
