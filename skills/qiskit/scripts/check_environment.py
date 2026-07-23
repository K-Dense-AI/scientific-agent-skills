#!/usr/bin/env python3
"""Inspect a Qiskit environment without network or credential access."""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import struct
import sys
from importlib import metadata
from typing import Any


VERIFIED_VERSIONS = {
    "qiskit": "2.5.0",
    "qiskit-ibm-runtime": "0.48.0",
    "qiskit-aer": "0.17.2",
    "qiskit-algorithms": "0.4.0",
    "qiskit-nature": "0.8.0",
    "qiskit-machine-learning": "0.9.0",
    "qiskit-optimization": "0.7.0",
}

IMPORT_NAMES = {
    "qiskit": "qiskit",
    "qiskit-ibm-runtime": "qiskit_ibm_runtime",
    "qiskit-aer": "qiskit_aer",
    "qiskit-algorithms": "qiskit_algorithms",
    "qiskit-nature": "qiskit_nature",
    "qiskit-machine-learning": "qiskit_machine_learning",
    "qiskit-optimization": "qiskit_optimization",
}


def installed_version(distribution: str) -> str | None:
    """Return an installed distribution version, or None."""
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def import_status(module_name: str) -> dict[str, str | bool | None]:
    """Import one module and return JSON-safe status details."""
    try:
        module = importlib.import_module(module_name)
    except Exception as error:  # Report broken optional environments clearly.
        return {
            "ok": False,
            "module_file": None,
            "error": f"{type(error).__name__}: {error}",
        }

    return {
        "ok": True,
        "module_file": getattr(module, "__file__", None),
        "error": None,
    }


def collect_report(
    require_runtime: bool,
    require_aer: bool,
    strict: bool,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Collect environment details, errors, and warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    pointer_bits = struct.calcsize("P") * 8
    python_ok = sys.version_info >= (3, 10)
    platform_ok = pointer_bits == 64

    if not python_ok:
        errors.append("Qiskit 2.5 requires Python 3.10 or newer.")
    if not platform_ok:
        errors.append("Qiskit 2.x requires a supported 64-bit platform.")

    required = {"qiskit"}
    if require_runtime:
        required.add("qiskit-ibm-runtime")
    if require_aer:
        required.add("qiskit-aer")

    packages: dict[str, Any] = {}
    for distribution, verified in VERIFIED_VERSIONS.items():
        current = installed_version(distribution)
        module = IMPORT_NAMES[distribution]
        status: dict[str, Any] = {
            "installed_version": current,
            "verified_version": verified,
            "required": distribution in required,
            "version_matches_verified": current == verified,
            "import": None,
        }

        if current is None:
            if distribution in required:
                errors.append(f"Required distribution is missing: {distribution}")
        else:
            status["import"] = import_status(module)
            if not status["import"]["ok"]:
                errors.append(
                    f"{distribution} is installed but cannot be imported: "
                    f"{status['import']['error']}"
                )
            if current != verified:
                message = (
                    f"{distribution}=={current} differs from the verified "
                    f"baseline {verified}."
                )
                if strict and distribution in required:
                    errors.append(message)
                else:
                    warnings.append(message)

        packages[distribution] = status

    terra_version = installed_version("qiskit-terra")
    if terra_version is not None:
        errors.append(
            "Legacy qiskit-terra is installed. Create a clean environment "
            "with the qiskit distribution instead of mixing namespaces."
        )

    core_api: dict[str, Any] = {
        "ok": False,
        "error": None,
    }
    if packages["qiskit"]["installed_version"] is not None:
        try:
            from qiskit import QuantumCircuit
            from qiskit.primitives import (
                StatevectorEstimator,
                StatevectorSampler,
            )
            from qiskit.transpiler import generate_preset_pass_manager

            circuit = QuantumCircuit(1)
            circuit.h(0)
            _ = (
                StatevectorSampler,
                StatevectorEstimator,
                generate_preset_pass_manager,
            )
            core_api["ok"] = circuit.num_qubits == 1
        except Exception as error:
            core_api["error"] = f"{type(error).__name__}: {error}"
            errors.append(f"Core Qiskit API smoke check failed: {error}")

    report: dict[str, Any] = {
        "ok": not errors,
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
            "meets_minimum": python_ok,
        },
        "platform": {
            "description": platform.platform(),
            "pointer_bits": pointer_bits,
            "supported_width": platform_ok,
        },
        "legacy_qiskit_terra": terra_version,
        "packages": packages,
        "core_api_smoke_check": core_api,
        "warnings": warnings,
        "errors": errors,
    }
    return report, errors, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect installed Qiskit distributions. This script performs "
            "no network calls and reads no credentials."
        )
    )
    parser.add_argument(
        "--require-runtime",
        action="store_true",
        help="Fail if qiskit-ibm-runtime is unavailable.",
    )
    parser.add_argument(
        "--require-aer",
        action="store_true",
        help="Fail if qiskit-aer is unavailable.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when required package versions differ from the baseline.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON report.",
    )
    return parser


def print_human_report(report: dict[str, Any]) -> None:
    print(
        "Python:",
        report["python"]["version"],
        f"({report['python']['implementation']})",
    )
    print("Executable:", report["python"]["executable"])
    print(
        "Platform:",
        report["platform"]["description"],
        f"({report['platform']['pointer_bits']}-bit)",
    )
    print("\nDistributions:")

    for distribution, details in report["packages"].items():
        current = details["installed_version"] or "not installed"
        marker = "required" if details["required"] else "optional"
        print(
            f"  {distribution}: {current} "
            f"(verified {details['verified_version']}; {marker})"
        )
        import_details = details["import"]
        if import_details and not import_details["ok"]:
            print(f"    import error: {import_details['error']}")

    if report["warnings"]:
        print("\nWarnings:")
        for warning in report["warnings"]:
            print(f"  - {warning}")

    if report["errors"]:
        print("\nErrors:")
        for error in report["errors"]:
            print(f"  - {error}")

    print("\nStatus:", "OK" if report["ok"] else "FAILED")


def main() -> int:
    args = build_parser().parse_args()
    report, errors, _warnings = collect_report(
        require_runtime=args.require_runtime,
        require_aer=args.require_aer,
        strict=args.strict,
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human_report(report)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
