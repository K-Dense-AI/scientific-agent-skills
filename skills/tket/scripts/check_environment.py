#!/usr/bin/env python3
"""Report whether the local environment matches what this skill was verified against.

Read-only: it imports packages, builds a two-qubit circuit, and prints a report. It never
writes files, contacts the network, or reads credentials.

Usage:
    python scripts/check_environment.py
    python scripts/check_environment.py --require-simulator --strict
    python scripts/check_environment.py --json
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import re
import struct
import sys
from collections.abc import Iterable
from importlib import metadata
from typing import Any

# Distributions this skill was verified against (PyPI, 2026-09-30).
VERIFIED_VERSIONS: dict[str, str] = {
    "pytket": "2.18.4",
    "pytket-qiskit": "0.78.0",
    "qiskit-aer": "0.17.2",
    "pytket-quantinuum": "0.59.3",
    "qermit": "0.9.3",
}

# Distribution name -> module to import in order to prove it is usable.
IMPORT_NAMES: dict[str, str] = {
    "pytket": "pytket.circuit",
    "pytket-qiskit": "pytket.extensions.qiskit",
    "pytket-quantinuum": "pytket.extensions.quantinuum",
    "pytket-braket": "pytket.extensions.braket",
    "pytket-iqm": "pytket.extensions.iqm",
    "pytket-qir": "pytket.extensions.qir",
    "pytket-cutensornet": "pytket.extensions.cutensornet",
    "pytket-qulacs": "pytket.extensions.qulacs",
    "pytket-qujax": "pytket.extensions.qujax",
    "qermit": "qermit",
    "qiskit": "qiskit",
    "qiskit-aer": "qiskit_aer",
    "numpy": "numpy",
    "scipy": "scipy",
    "sympy": "sympy",
}

# Everything without a simulator: circuits, compilation, QASM 2, ZX.
CORE_DISTRIBUTIONS: tuple[str, ...] = ("pytket",)

# Needed only for local sampling / noise models / IBM hardware.
SIMULATOR_DISTRIBUTIONS: tuple[str, ...] = ("pytket-qiskit", "qiskit-aer")

# Never required; report if present.
OPTIONAL_DISTRIBUTIONS: tuple[str, ...] = (
    "pytket-quantinuum",
    "pytket-braket",
    "pytket-iqm",
    "pytket-qir",
    "pytket-cutensornet",
    "pytket-qulacs",
    "pytket-qujax",
    "qermit",
)

MINIMUM_PYTHON = (3, 10)

# Packages that look like they should exist but do not, or that break a 2.x install.
BOGUS_DISTRIBUTIONS: dict[str, str] = {
    "pytket-aer": (
        "no such package; AerBackend/AerStateBackend/AerUnitaryBackend ship in "
        "pytket-qiskit behind the [aer] extra"
    ),
    "pytket-terra": "no such package; this is a Qiskit name",
    "qiskit-terra": "legacy Qiskit 0.x metapackage; conflicts with the pytket-qiskit pin",
    "pytket-qsharp": "pins pytket ~=1.26 and cannot be installed beside pytket 2.x",
}

# Known mutually-exclusive combinations, read out of each wheel's METADATA on 2026-10-01.
# Every released qermit pins pytket-qiskit<0.78 and pytket-quantinuum<0.59, while this skill
# verifies against pytket-qiskit 0.78.0 and pytket-quantinuum 0.59.3. pip does NOT error on
# that set - it silently backtracks to qermit 0.7.1, which predates the documented API.
# Each entry: name -> (the distribution it conflicts with, the specifier it demands).
KNOWN_PIN_CONFLICTS: dict[str, tuple[tuple[str, str], ...]] = {
    "qermit": (
        ("pytket-qiskit", "<0.78"),
        ("pytket-quantinuum", "<0.59"),
    ),
}


def _version_tuple(value: str) -> tuple[int, ...]:
    """Parse the numeric prefix of a PEP 440 version into a comparable tuple.

    Stops at the first non-numeric chunk, so ``"0.8.0.dev8"`` and ``"1.2.3rc1"`` both
    truncate to their release segment (``(0, 8, 0)`` / ``(1, 2, 3)``). Pre-release and
    local-version ordering is therefore NOT modelled; that is acceptable here because the
    only comparisons this script makes are against plain ``<X.Y`` pins.
    """
    parts: list[int] = []
    for chunk in re.split(r"[.\-+]", value):
        match = re.match(r"\d+", chunk)
        if match is None:
            break
        parts.append(int(match.group()))
    return tuple(parts)


def version_satisfies(version: str, specifier: str) -> bool | None:
    """Evaluate a simple version specifier such as ``"<0.78"`` or ``">=2.11,<3.0"``.

    Returns ``None`` for any form this helper does not model, so the caller can report
    "unknown" rather than guess. Refused forms: environment markers (``;``), wildcards
    (``*``), and anything that is not a plain comparison. ``~=X.Y`` follows PEP 440
    (``>=X.Y, ==X.*``), so ``1.34.0`` does satisfy ``~=1.26`` while ``2.18.4`` does not.

    Deliberately hand-rolled: this script imports only the standard library at module
    level so that ``--help`` works in an environment where pytket is not installed.
    """
    version_parts = _version_tuple(version)
    if not version_parts:
        return None
    for clause in specifier.split(","):
        clause = clause.strip()
        if not clause:
            continue
        # Environment markers and wildcards need a full PEP 440/508 evaluator.
        if ";" in clause or "*" in clause:
            return None
        match = re.match(r"^(~=|===|==|!=|>=|<=|>|<)\s*(.+)$", clause)
        if match is None:
            return None
        operator, target_text = match.group(1), match.group(2).strip()
        target_parts = _version_tuple(target_text)
        if not target_parts or not re.fullmatch(r"[0-9.\-+]+", target_text):
            return None
        if operator in ("==", "==="):
            if version_parts != target_parts:
                return False
        elif operator == "!=":
            if version_parts == target_parts:
                return False
        elif operator == ">":
            if not version_parts > target_parts:
                return False
        elif operator == ">=":
            if not version_parts >= target_parts:
                return False
        elif operator == "<":
            if not version_parts < target_parts:
                return False
        elif operator == "<=":
            if not version_parts <= target_parts:
                return False
        elif operator == "~=":
            # ~=X.Y means >=X.Y and ==X.* ; ~=X.Y.Z means >=X.Y.Z and ==X.Y.*
            if not version_parts >= target_parts:
                return False
            prefix_length = max(len(target_parts) - 1, 1)
            if version_parts[:prefix_length] != target_parts[:prefix_length]:
                return False
    return True


def check_pin_conflicts(installed: Iterable[str]) -> list[str]:
    """Return a warning per installed package whose pins the other installed versions break."""
    present = {name: installed_version(name) for name in installed}
    messages: list[str] = []
    for name, conflicts in KNOWN_PIN_CONFLICTS.items():
        own = present.get(name)
        if own is None:
            continue
        for other, specifier in conflicts:
            other_version = present.get(other)
            if other_version is None:
                continue
            satisfied = version_satisfies(other_version, specifier)
            if satisfied is False:
                messages.append(
                    f"{name} {own} requires {other}{specifier} but {other} {other_version} is "
                    f"installed; these cannot be used together. Give {name} its own "
                    "environment, or install a compatible older set (see references/setup.md)."
                )
    return messages


def installed_version(distribution: str) -> str | None:
    """Return the installed version of *distribution*, or None if it is absent."""
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def import_status(module_name: str) -> dict[str, Any]:
    """Try to import *module_name* and describe the outcome without raising."""
    try:
        module = importlib.import_module(module_name)
    except Exception as error:  # noqa: BLE001 - any import failure is data, not a crash
        return {"ok": False, "module_file": None, "error": f"{type(error).__name__}: {error}"}
    return {"ok": True, "module_file": getattr(module, "__file__", None), "error": None}


def core_api_smoke() -> dict[str, Any]:
    """Execute the invariants this skill depends on. Returns name -> observed value.

    Every key here is a behaviour quoted in SKILL.md or references/, so a mismatch means
    the documentation is stale for the installed release.
    """
    result: dict[str, Any] = {}
    try:
        from pytket.circuit import Circuit, OpType
        from pytket.passes import DecomposeBoxes, FullPeepholeOptimise, SequencePass
        from pytket.predicates import GateSetPredicate, NoSymbolsPredicate
    except Exception as error:  # noqa: BLE001
        result["error"] = f"{type(error).__name__}: {error}"
        return result

    try:
        bell = Circuit(2, 2).H(0).CX(0, 1)
        bell.measure_all()
        result["bell_n_qubits"] = bell.n_qubits
        result["bell_n_bits"] = bell.n_bits
        result["bell_n_gates"] = bell.n_gates
        result["bell_cx_count"] = bell.n_gates_of_type(OpType.CX)

        # Angles are half-turns (multiples of pi), not radians, and stay unnormalised on read.
        rx = Circuit(1).Rx(0.5, 0)
        result["rx_half_turn_params"] = list(rx.get_commands()[0].op.params)

        # Passes mutate in place and return a bool; nothing hands back a new circuit.
        clone = rx.copy()
        result["optimise_returns_bool"] = isinstance(FullPeepholeOptimise().apply(clone), bool)

        combo = SequencePass([DecomposeBoxes(), FullPeepholeOptimise()])
        target = Circuit(2).H(0).CX(0, 1)
        combo.apply(target)
        result["sequence_pass_applies"] = target.n_gates >= 1

        result["predicates_verify"] = bool(
            NoSymbolsPredicate().verify(bell)
            and GateSetPredicate({OpType.H, OpType.CX, OpType.Measure}).verify(
                Circuit(2).H(0).CX(0, 1).measure_all()
            )
        )
    except Exception as error:  # noqa: BLE001
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def simulator_smoke() -> dict[str, Any]:
    """Prove the local sampler works and report its capability flags."""
    result: dict[str, Any] = {}
    try:
        from pytket.circuit import Circuit
        from pytket.extensions.qiskit import AerBackend
    except Exception as error:  # noqa: BLE001
        result["error"] = f"{type(error).__name__}: {error}"
        return result

    try:
        backend = AerBackend()
        result["backend_name"] = backend.backend_info.name
        result["supports_shots"] = backend.supports_shots
        result["supports_counts"] = backend.supports_counts
        result["supports_state"] = backend.supports_state
        result["supports_expectation"] = backend.supports_expectation
        result["default_compilation_pass"] = type(
            backend.default_compilation_pass(optimisation_level=2)
        ).__name__

        ghz = Circuit(3, 3).H(0).CX(0, 1).CX(1, 2)
        ghz.measure_all()
        counts = backend.run_circuit(ghz, n_shots=200, seed=7).get_counts()
        result["ghz_distinct_outcomes"] = sorted(counts)
        result["ghz_total_shots"] = sum(counts.values())
    except Exception as error:  # noqa: BLE001
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def collect_report(
    require_simulator: bool = False,
    strict: bool = False,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Build the full report. Returns (report, errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    python_version = platform.python_version()
    bits = struct.calcsize("P") * 8

    if sys.version_info < MINIMUM_PYTHON:
        errors.append(
            f"Python {python_version} is below the pytket floor "
            f"{'.'.join(str(part) for part in MINIMUM_PYTHON)}"
        )
    if bits != 64:
        errors.append(f"{bits}-bit interpreter detected; pytket ships 64-bit wheels only")
    if "conda" in sys.version.lower() or "Anaconda" in platform.python_compiler():
        warnings.append(
            "conda interpreter detected; Quantinuum/tket#926 caps pytket at 1.11.0 in some "
            "conda setups - prefer an official Python distribution"
        )

    required: list[str] = list(CORE_DISTRIBUTIONS)
    if require_simulator:
        required.extend(SIMULATOR_DISTRIBUTIONS)

    packages: dict[str, Any] = {}
    for distribution in sorted(
        set(required) | set(SIMULATOR_DISTRIBUTIONS) | set(OPTIONAL_DISTRIBUTIONS)
    ):
        version = installed_version(distribution)
        expected = VERIFIED_VERSIONS.get(distribution)
        entry: dict[str, Any] = {
            "installed": version,
            "verified": expected,
            "required": distribution in required,
            "import": None,
        }
        if version is not None:
            entry["import"] = import_status(IMPORT_NAMES.get(distribution, distribution))
            if not entry["import"]["ok"]:
                message = (
                    f"{distribution} {version} is installed but "
                    f"{IMPORT_NAMES.get(distribution, distribution)} failed to import: "
                    f"{entry['import']['error']}"
                )
                if distribution in required:
                    errors.append(message)
                else:
                    warnings.append(message)
        elif distribution in required:
            errors.append(
                f"{distribution} is not installed "
                f"(verified version {expected or 'unspecified'})"
            )

        if version is not None and expected is not None and version != expected:
            message = (
                f"{distribution} {version} differs from the verified {expected}; "
                "re-check the snippets in this skill"
            )
            if strict and distribution in required:
                errors.append(message)
            else:
                warnings.append(message)

        packages[distribution] = entry

    for distribution, reason in BOGUS_DISTRIBUTIONS.items():
        if installed_version(distribution) is not None:
            errors.append(f"{distribution} is installed but is unusable here: {reason}")

    conflict_warnings = check_pin_conflicts(
        set(KNOWN_PIN_CONFLICTS)
        | {other for conflicts in KNOWN_PIN_CONFLICTS.values() for other, _ in conflicts}
    )
    warnings.extend(conflict_warnings)

    core = core_api_smoke() if installed_version("pytket") else {"skipped": "pytket absent"}
    if "error" in core:
        errors.append(f"core API smoke check failed: {core['error']}")

    if require_simulator:
        simulator = (
            simulator_smoke() if installed_version("pytket-qiskit") else {"skipped": "absent"}
        )
        if "error" in simulator:
            errors.append(f"simulator smoke check failed: {simulator['error']}")
    else:
        simulator = {"skipped": "pass --require-simulator to run it"}

    report: dict[str, Any] = {
        "ok": not errors,  # main() turns this into the process exit code
        "python": python_version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "bits": bits,
        "strict": strict,
        "require_simulator": require_simulator,
        "packages": packages,
        "core_api": core,
        "simulator": simulator,
    }
    return report, errors, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_environment.py",
        description=(
            "Check the interpreter, the installed pytket distributions, and the core API "
            "invariants this skill relies on."
        ),
    )
    parser.add_argument(
        "--require-simulator",
        action="store_true",
        help="treat pytket-qiskit and qiskit-aer as required and run the AerBackend smoke check",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="turn version drift on required distributions into errors",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the report as JSON instead of a human-readable table",
    )
    return parser


def print_human_report(report: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    print(f"Python {report['python']} ({report['bits']}-bit) on {report['platform']}")
    print(f"Interpreter: {report['executable']}")
    print()
    print("Distributions:")
    for name in sorted(report["packages"]):
        entry = report["packages"][name]
        flag = "required" if entry["required"] else "optional"
        installed = entry["installed"] or "NOT INSTALLED"
        line = f"  {name:<22} {installed:<12} (verified {entry['verified'] or 'n/a'}, {flag})"
        if entry["import"] is not None and not entry["import"]["ok"]:
            line += "  IMPORT FAILED"
        print(line)
    print()
    print("Core API smoke check:")
    for key in sorted(report["core_api"]):
        print(f"  {key} = {report['core_api'][key]!r}")
    print()
    print("Simulator smoke check:")
    for key in sorted(report["simulator"]):
        print(f"  {key} = {report['simulator'][key]!r}")
    print()
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")
        print()
    if errors:
        print(f"Errors ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
    else:
        print("No errors. Environment matches the verified baseline." if not warnings else "No errors.")


def main() -> int:
    args = build_parser().parse_args()
    report, errors, warnings = collect_report(
        require_simulator=args.require_simulator,
        strict=args.strict,
    )
    if args.json:
        print(json.dumps({"report": report, "errors": errors, "warnings": warnings}, indent=2))
    else:
        print_human_report(report, errors, warnings)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
