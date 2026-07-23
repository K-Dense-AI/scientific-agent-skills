#!/usr/bin/env python3
"""Inspect the installed Latch SDK without authentication or network access."""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import platform
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any


SYMBOL_GROUPS: dict[str, list[tuple[str, str]]] = {
    "core": [
        ("latch", "workflow"),
        ("latch", "map_task"),
        ("latch", "create_conditional_section"),
        ("latch", "workflow_reference"),
    ],
    "tasks": [
        ("latch.resources.tasks", "small_task"),
        ("latch.resources.tasks", "medium_task"),
        ("latch.resources.tasks", "large_task"),
        ("latch.resources.tasks", "small_gpu_task"),
        ("latch.resources.tasks", "large_gpu_task"),
        ("latch.resources.tasks", "custom_task"),
        ("latch.resources.tasks", "custom_memory_optimized_task"),
        ("latch.resources.tasks", "v100_x1_task"),
        ("latch.resources.tasks", "v100_x4_task"),
        ("latch.resources.tasks", "v100_x8_task"),
        ("latch.resources.tasks", "g6e_xlarge_task"),
        ("latch.resources.tasks", "g6e_2xlarge_task"),
        ("latch.resources.tasks", "g6e_4xlarge_task"),
        ("latch.resources.tasks", "g6e_8xlarge_task"),
        ("latch.resources.tasks", "g6e_12xlarge_task"),
        ("latch.resources.tasks", "g6e_16xlarge_task"),
        ("latch.resources.tasks", "g6e_24xlarge_task"),
        ("latch.resources.tasks", "g6e_48xlarge_task"),
    ],
    "data": [
        ("latch.ldata.path", "LPath"),
        ("latch.types", "LatchFile"),
        ("latch.types", "LatchDir"),
        ("latch.types", "LatchOutputFile"),
        ("latch.types", "LatchOutputDir"),
        ("latch.types", "file_glob"),
    ],
    "metadata": [
        ("latch.types.metadata", "LatchMetadata"),
        ("latch.types.metadata", "LatchParameter"),
        ("latch.resources.launch_plan", "LaunchPlan"),
        ("latch.types.samplesheet_item", "SamplesheetItem"),
    ],
    "registry": [
        ("latch.account", "Account"),
        ("latch.registry.project", "Project"),
        ("latch.registry.table", "Table"),
        ("latch.registry.record", "Record"),
    ],
    "execution": [
        ("latch_cli.services.launch.launch_v2", "launch"),
        ("latch_cli.services.launch.launch_v2", "launch_from_launch_plan"),
        ("latch_cli.services.launch.launch_v2", "Execution"),
        ("latch_cli.services.launch.launch_v2", "CompletedExecution"),
    ],
    "verified": [
        ("latch.verified", "rnaseq"),
        ("latch.verified", "deseq2_wf"),
        ("latch.verified", "gene_ontology_pathway_analysis"),
        ("latch.verified", "mafft"),
        ("latch.verified", "trim_galore"),
    ],
}


METHODS: dict[str, tuple[str, str, list[str]]] = {
    "LPath": (
        "latch.ldata.path",
        "LPath",
        [
            "exists",
            "iterdir",
            "mkdirp",
            "copy_to",
            "upload_from",
            "download",
            "rmr",
            "fetch_metadata",
        ],
    ),
    "Table": (
        "latch.registry.table",
        "Table",
        ["load", "list_records", "get_dataframe", "update"],
    ),
    "Execution": (
        "latch_cli.services.launch.launch_v2",
        "Execution",
        ["poll", "wait", "abort"],
    ),
}

OBJECT_REPR = re.compile(r"<(?P<name>[^<>]+) object at 0x[0-9a-fA-F]+>")
ADDRESS_REPR = re.compile(r"0x[0-9a-fA-F]+")


def normalize_repr(value: str) -> str:
    """Remove process-specific memory addresses from introspection output."""
    value = OBJECT_REPR.sub(lambda match: f"<{match.group('name')}>", value)
    return ADDRESS_REPR.sub("0x<address>", value)


def safe_signature(obj: Any) -> str | None:
    try:
        return normalize_repr(str(inspect.signature(obj)))
    except (TypeError, ValueError):
        return None


def inspect_symbol(module_name: str, symbol_name: str) -> dict[str, Any]:
    qualified_name = f"{module_name}.{symbol_name}"
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # Import failures are the diagnostic output.
        return {
            "qualified_name": qualified_name,
            "available": False,
            "error": normalize_repr(f"{type(exc).__name__}: {exc}"),
        }

    if not hasattr(module, symbol_name):
        return {
            "qualified_name": qualified_name,
            "available": False,
            "error": "symbol not found",
        }

    obj = getattr(module, symbol_name)
    result = {
        "qualified_name": qualified_name,
        "available": True,
        "kind": type(obj).__name__,
        "signature": safe_signature(obj),
    }

    python_interface = getattr(obj, "python_interface", None)
    if python_interface is not None:
        result["python_interface"] = {
            "inputs": {
                name: normalize_repr(inspect.formatannotation(annotation))
                for name, annotation in python_interface.inputs.items()
            },
            "outputs": {
                name: normalize_repr(inspect.formatannotation(annotation))
                for name, annotation in python_interface.outputs.items()
            },
        }

    return result


def inspect_methods(
    module_name: str,
    class_name: str,
    method_names: list[str],
) -> dict[str, Any]:
    try:
        cls = getattr(importlib.import_module(module_name), class_name)
    except Exception as exc:
        return {"error": normalize_repr(f"{type(exc).__name__}: {exc}")}

    result: dict[str, Any] = {}
    for method_name in method_names:
        method = getattr(cls, method_name, None)
        result[method_name] = {
            "available": method is not None,
            "signature": safe_signature(method) if method is not None else None,
        }
    return result


def build_report() -> dict[str, Any]:
    try:
        latch_version = version("latch")
    except PackageNotFoundError:
        latch_version = None

    symbols = {
        group: [
            inspect_symbol(module_name, symbol_name)
            for module_name, symbol_name in entries
        ]
        for group, entries in SYMBOL_GROUPS.items()
    }

    methods = {
        label: inspect_methods(module_name, class_name, method_names)
        for label, (module_name, class_name, method_names) in METHODS.items()
    }

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "latch_version": latch_version,
        "symbols": symbols,
        "methods": methods,
    }


def print_text(report: dict[str, Any]) -> None:
    print(f"Python: {report['python']}")
    print(f"Platform: {report['platform']}")
    print(f"Latch SDK: {report['latch_version'] or 'not installed'}")

    for group, entries in report["symbols"].items():
        print(f"\n[{group}]")
        for entry in entries:
            status = "ok" if entry["available"] else "missing"
            line = f"- {status}: {entry['qualified_name']}"
            if entry.get("signature"):
                line += entry["signature"]
            if entry.get("error"):
                line += f" ({entry['error']})"
            print(line)
            if entry.get("python_interface"):
                print(f"  inputs: {entry['python_interface']['inputs']}")
                print(f"  outputs: {entry['python_interface']['outputs']}")

    print("\n[methods]")
    for class_name, methods in report["methods"].items():
        print(f"- {class_name}")
        if "error" in methods:
            print(f"  error: {methods['error']}")
            continue
        for method_name, details in methods.items():
            status = "ok" if details["available"] else "missing"
            signature = details["signature"] or ""
            print(f"  - {status}: {method_name}{signature}")


def has_required_failures(report: dict[str, Any]) -> bool:
    required = {
        "latch.workflow",
        "latch.resources.tasks.small_task",
        "latch.resources.tasks.custom_task",
        "latch.ldata.path.LPath",
        "latch.registry.table.Table",
        "latch_cli.services.launch.launch_v2.launch",
    }
    observed = {
        entry["qualified_name"]: entry["available"]
        for entries in report["symbols"].values()
        for entry in entries
    }
    return any(not observed.get(name, False) for name in required)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when a core symbol is missing.",
    )
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)

    if report["latch_version"] is None:
        return 2
    if args.strict and has_required_failures(report):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
