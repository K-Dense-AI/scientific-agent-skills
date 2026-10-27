#!/usr/bin/env python3
"""Compile a circuit for a target connectivity and report what the compilation did.

Reports gate counts before and after, depth, predicate satisfaction, and the initial/final
qubit maps - the two things agents most often forget to check after placement and routing.

Requires pytket. pytket-qiskit[aer] is needed only for --use-backend-pass and
--verify-semantics.

Usage:
    python scripts/compile_and_report.py --demo ghz --qubits 5 --architecture linear:6
    python scripts/compile_and_report.py --qasm circuit.qasm --architecture grid:2x3 --json
    python scripts/compile_and_report.py --demo ghz --qubits 4 --use-backend-pass
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

TOPOLOGY_HELP = (
    "target connectivity: 'none' (no routing constraint), "
    "'linear:N', 'ring:N', 'grid:RxC', or 'star:N' (centre node 0)"
)

TARGET_GATESET = "CX,Rz,H,Measure,Reset,Barrier"


def parse_architecture(spec: str) -> Any:
    """Build a pytket Architecture, or None for 'none', from a compact CLI spec.

    Note: pytket.architecture.FullyConnected is NOT an Architecture subclass, so it cannot be
    fed to a placer or routing pass. 'none' therefore means "skip placement and routing".
    """
    if spec == "none":
        return None

    kind, _, size = spec.partition(":")
    kind = kind.lower()
    if not size:
        raise ValueError(f"{TOPOLOGY_HELP} - got {spec!r} with no size")

    from pytket.architecture import Architecture, RingArch, SquareGrid

    if kind == "linear":
        nodes = int(size)
        if nodes < 2:
            raise ValueError("linear:N needs N >= 2")
        return Architecture([[index, index + 1] for index in range(nodes - 1)])
    if kind == "ring":
        nodes = int(size)
        if nodes < 3:
            raise ValueError("ring:N needs N >= 3")
        return RingArch(nodes)
    if kind == "grid":
        rows, _, cols = size.partition("x")
        if not cols:
            raise ValueError(f"grid needs RxC, got {size!r}")
        return SquareGrid(int(rows), int(cols))
    if kind == "star":
        nodes = int(size)
        if nodes < 3:
            raise ValueError("star:N needs N >= 3 (centre plus N-1 leaves)")
        return Architecture([[0, leaf] for leaf in range(1, nodes)])
    raise ValueError(f"unknown topology {kind!r}; {TOPOLOGY_HELP}")


def target_gateset() -> set:
    from pytket.circuit import OpType

    return {
        OpType.CX,
        OpType.Rz,
        OpType.H,
        OpType.Measure,
        OpType.Reset,
        OpType.Barrier,
    }


def demo_circuit(kind: str, n_qubits: int) -> Any:
    """A small built-in circuit, for smoke-testing the pass pipeline."""
    from pytket.circuit import Circuit

    if kind == "ghz":
        circuit = Circuit(n_qubits, n_qubits).H(0)
        for index in range(n_qubits - 1):
            circuit.CX(index, index + 1)
    elif kind == "bell":
        circuit = Circuit(2, 2).H(0).CX(0, 1)
    elif kind == "adder-ish":
        # Every CX targets the last qubit: not nearest-neighbour on a line, so the
        # router must insert swaps. Good for showing the gate-count cost of routing.
        circuit = Circuit(n_qubits, n_qubits).H(0)
        for index in range(n_qubits - 1):
            circuit.CX(index, n_qubits - 1)
    else:
        raise ValueError(f"unknown demo {kind!r}; choose ghz | bell | adder-ish")

    circuit.measure_all()
    return circuit


def load_qasm(path: Path) -> Any:
    """Load an OpenQASM 2 file. pytket has no OpenQASM 3 support."""
    from pytket.qasm import circuit_from_qasm

    return circuit_from_qasm(str(path))


def build_pipeline(architecture: Any, optimisation_level: int, use_backend_pass: bool) -> tuple[Any, str]:
    """Return (pass, description). One pipeline, applied to a CompilationUnit."""
    from pytket.circuit import OpType
    from pytket.passes import (
        AutoRebase,
        DecomposeBoxes,
        FullMappingPass,
        FullPeepholeOptimise,
        SequencePass,
        SynthesiseTket,
    )

    if use_backend_pass:
        from pytket.extensions.qiskit import AerBackend

        return (
            AerBackend().default_compilation_pass(optimisation_level=optimisation_level),
            f"AerBackend.default_compilation_pass(optimisation_level={optimisation_level})",
        )

    if architecture is not None:
        from pytket.mapping import LexiLabellingMethod, LexiRouteRoutingMethod
        from pytket.placement import GraphPlacement

        return (
            SequencePass(
                [
                    DecomposeBoxes(),
                    FullPeepholeOptimise(allow_swaps=True),
                    FullMappingPass(
                        architecture,
                        GraphPlacement(architecture),
                        [LexiLabellingMethod(), LexiRouteRoutingMethod()],
                    ),
                    AutoRebase(target_gateset()),
                ]
            ),
            "DecomposeBoxes -> FullPeepholeOptimise -> FullMappingPass(GraphPlacement, "
            "[LexiLabellingMethod, LexiRouteRoutingMethod]) -> "
            f"AutoRebase({{{TARGET_GATESET}}})",
        )

    return (
        SequencePass([DecomposeBoxes(), SynthesiseTket(), AutoRebase(target_gateset())]),
        f"DecomposeBoxes -> SynthesiseTket -> AutoRebase({{{TARGET_GATESET}}}) "
        "(no connectivity constraint)",
    )


def gate_mix(circuit: Any) -> dict[str, int]:
    """Gate counts by OpType, using pytket.utils.gate_counts (Circuit has no op_type_counts)."""
    from pytket.utils import gate_counts

    counts = gate_counts(circuit)
    return {str(op_type): int(count) for op_type, count in sorted(counts.items(), key=str)}


def measure_circuit(circuit: Any) -> dict[str, Any]:
    from pytket.circuit import OpType

    return {
        "n_qubits": circuit.n_qubits,
        "n_bits": circuit.n_bits,
        "n_gates": circuit.n_gates,
        "n_1qb_gates": circuit.n_1qb_gates(),
        "n_2qb_gates": circuit.n_2qb_gates(),
        "cx_count": circuit.n_gates_of_type(OpType.CX),
        "depth": circuit.depth(),
        "depth_2q": circuit.depth_2q(),
        "gate_mix": gate_mix(circuit),
    }


def check_predicates(circuit: Any, architecture: Any) -> dict[str, bool]:
    """Report which standard predicates the compiled circuit satisfies."""
    from pytket.predicates import (
        ConnectivityPredicate,
        DefaultRegisterPredicate,
        DirectednessPredicate,
        GateSetPredicate,
        MaxNQubitsPredicate,
        NoBarriersPredicate,
        NoClassicalControlPredicate,
        NoFastFeedforwardPredicate,
        NoMidMeasurePredicate,
        NoSymbolsPredicate,
    )

    checks: dict[str, bool] = {
        "NoSymbolsPredicate": NoSymbolsPredicate().verify(circuit),
        "NoClassicalControlPredicate": NoClassicalControlPredicate().verify(circuit),
        "NoFastFeedforwardPredicate": NoFastFeedforwardPredicate().verify(circuit),
        "NoMidMeasurePredicate": NoMidMeasurePredicate().verify(circuit),
        "NoBarriersPredicate": NoBarriersPredicate().verify(circuit),
        "DefaultRegisterPredicate": DefaultRegisterPredicate().verify(circuit),
        f"MaxNQubitsPredicate({circuit.n_qubits})": MaxNQubitsPredicate(
            circuit.n_qubits
        ).verify(circuit),
        f"GateSetPredicate({{{TARGET_GATESET}}})": GateSetPredicate(
            target_gateset()
        ).verify(circuit),
    }
    if architecture is not None:
        # Both connectivity predicates REQUIRE an Architecture argument; calling either
        # with no arguments raises TypeError from the pybind11 layer.
        checks["ConnectivityPredicate(architecture)"] = ConnectivityPredicate(
            architecture
        ).verify(circuit)
        checks["DirectednessPredicate(architecture)"] = DirectednessPredicate(
            architecture
        ).verify(circuit)
    return {name: bool(value) for name, value in checks.items()}


def verify_semantics(original: Any, compiled: Any) -> dict[str, Any]:
    """Compare unitaries on small unmeasured circuits; skip otherwise."""
    from pytket.utils import compare_unitaries

    if original.n_qubits > 6 or compiled.n_qubits > 6:
        return {"skipped": "get_unitary() is O(4^n); limited to <= 6 qubits"}
    if original.n_bits or compiled.n_bits:
        return {"skipped": "circuits contain measurements; compare an unmeasured copy instead"}
    try:
        equal = compare_unitaries(original.get_unitary(), compiled.get_unitary())
    except Exception as error:  # noqa: BLE001 - report, do not crash
        return {"error": f"{type(error).__name__}: {error}"}
    return {"unitaries_match_ignoring_global_phase": bool(equal)}


def compile_report(
    circuit: Any,
    architecture: Any,
    optimisation_level: int,
    use_backend_pass: bool,
    check_semantics: bool,
) -> dict[str, Any]:
    """Apply one pipeline to a CompilationUnit and describe everything it changed."""
    from pytket.predicates import CompilationUnit

    pass_, description = build_pipeline(architecture, optimisation_level, use_backend_pass)

    unit = CompilationUnit(circuit)
    modified = pass_.apply(unit)
    compiled = unit.circuit  # a property returning a copy; there is no get_circuit()

    report: dict[str, Any] = {
        "pipeline": description,
        "pass_reported_modification": bool(modified),
        "before": measure_circuit(circuit),
        "after": measure_circuit(compiled),
        "predicates": check_predicates(compiled, architecture),
        "initial_map": {str(key): str(value) for key, value in unit.initial_map.items()},
        "final_map": {str(key): str(value) for key, value in unit.final_map.items()},
        "all_predicates_satisfied": bool(unit.check_all_predicates()),
    }

    if architecture is not None:
        report["architecture_nodes"] = [str(node) for node in architecture.nodes]
        report["cx_delta"] = report["after"]["cx_count"] - report["before"]["cx_count"]
        report["depth_delta"] = report["after"]["depth"] - report["before"]["depth"]

    if check_semantics:
        report["semantics"] = verify_semantics(circuit, compiled)

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compile_and_report.py",
        description=(
            "Compile a circuit for a target connectivity and report gate counts, depth, "
            "predicate satisfaction, and the initial/final qubit maps."
        ),
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--qasm", type=Path, help="OpenQASM 2 file to compile")
    source.add_argument(
        "--demo", choices=["ghz", "bell", "adder-ish"], help="use a built-in demo circuit"
    )
    parser.add_argument(
        "--qubits", type=int, default=4, help="qubit count for --demo circuits (default 4)"
    )
    parser.add_argument("--architecture", default="none", help=TOPOLOGY_HELP + " (default 'none')")
    parser.add_argument(
        "--optimisation-level",
        type=int,
        choices=[0, 1, 2],
        default=2,
        help="only meaningful with --use-backend-pass (default 2)",
    )
    parser.add_argument(
        "--use-backend-pass",
        action="store_true",
        help="use AerBackend.default_compilation_pass instead of the explicit pipeline",
    )
    parser.add_argument(
        "--verify-semantics",
        action="store_true",
        help="compare unitaries before/after (unmeasured circuits, <= 6 qubits)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    return parser


def print_human_report(report: dict[str, Any], source: str) -> None:
    print(f"Source:   {source}")
    print(f"Pipeline: {report['pipeline']}")
    print(f"Pass reported modification: {report['pass_reported_modification']}")
    print()
    before, after = report["before"], report["after"]
    print(f"{'metric':<14}{'before':>9}{'after':>9}{'delta':>9}")
    for key in ("n_gates", "n_1qb_gates", "n_2qb_gates", "cx_count", "depth", "depth_2q"):
        print(f"{key:<14}{before[key]:>9}{after[key]:>9}{after[key] - before[key]:>+9}")
    print()
    print("Gate mix after compilation:")
    for op_type, count in after["gate_mix"].items():
        print(f"  {op_type}: {count}")
    print()
    print("Predicates on the compiled circuit:")
    for name, ok in report["predicates"].items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print()
    print("Reading the predicate list: FAIL is not automatically an error. Which ones matter")
    print("depends on the target backend - compare against backend.required_predicates.")
    print("  ConnectivityPredicate FAIL  -> routing violated the coupling graph (real problem)")
    print("  DirectednessPredicate FAIL  -> gates point against some directed arc; most backends")
    print("                                 only require undirected connectivity, so often benign")
    print("  NoMidMeasurePredicate FAIL  -> mid-circuit measurement present; fine for simulators,")
    print("                                 rejected by backends that need all measures at the end")
    print("  DefaultRegisterPredicate FAIL -> placement/routing renamed registers (expected)")
    print()
    if "architecture_nodes" in report:
        print(f"Architecture nodes: {report['architecture_nodes']}")
    print(f"Initial map: {report['initial_map']}")
    print(f"Final map:   {report['final_map']}")
    print()
    print(
        "NOTE: placement renames logical Qubits to physical Nodes and routing can permute them\n"
        "mid-circuit, so logical q[i] may finish on a different node. Read results by the\n"
        "compiled circuit's classical bits and use these maps to translate back."
    )
    if "semantics" in report:
        print(f"\nSemantics: {report['semantics']}")


def main() -> int:
    args = build_parser().parse_args()

    try:
        architecture = parse_architecture(args.architecture)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    try:
        if args.qasm is not None:
            if not args.qasm.is_file():
                raise SystemExit(f"QASM file not found: {args.qasm}")
            circuit = load_qasm(args.qasm)
            source = f"QASM {args.qasm}"
        else:
            circuit = demo_circuit(args.demo, args.qubits)
            source = f"demo {args.demo} ({args.qubits} qubits)"

        report = compile_report(
            circuit,
            architecture,
            args.optimisation_level,
            args.use_backend_pass,
            args.verify_semantics,
        )
    except ImportError as error:
        raise SystemExit(
            f"Missing dependency: {error}\nInstall with: python -m pip install pytket "
            '(add "pytket-qiskit[aer]" for --use-backend-pass and --verify-semantics)'
        ) from error

    if args.json:
        print(json.dumps({"source": source, "report": report}, indent=2))
    else:
        print_human_report(report, source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
