#!/usr/bin/env python3
"""Inspect local dxpy symbols and signatures without authentication or network."""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import platform
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Optional


DOCUMENTED_BASELINE = "0.410.0"

SYMBOL_GROUPS: dict[str, list[tuple[str, str]]] = {
    "files": [
        ("dxpy", "upload_local_file"),
        ("dxpy", "download_dxfile"),
        ("dxpy", "open_dxfile"),
        ("dxpy", "upload_string"),
        ("dxpy", "new_dxfile"),
    ],
    "search": [
        ("dxpy", "find_data_objects"),
        ("dxpy", "find_executions"),
        ("dxpy", "find_jobs"),
        ("dxpy", "find_analyses"),
        ("dxpy", "find_projects"),
    ],
    "links_and_objects": [
        ("dxpy", "dxlink"),
        ("dxpy", "get_handler"),
        ("dxpy", "describe"),
        ("dxpy", "new_dxrecord"),
        ("dxpy", "new_dxworkflow"),
    ],
    "handlers": [
        ("dxpy", "DXFile"),
        ("dxpy", "DXRecord"),
        ("dxpy", "DXApplet"),
        ("dxpy", "DXApp"),
        ("dxpy", "DXWorkflow"),
        ("dxpy", "DXJob"),
        ("dxpy", "DXAnalysis"),
        ("dxpy", "DXProject"),
    ],
    "exceptions": [
        ("dxpy.exceptions", "DXError"),
        ("dxpy.exceptions", "DXAPIError"),
        ("dxpy.exceptions", "DXJobFailureError"),
        ("dxpy.exceptions", "DXSearchError"),
        ("dxpy.exceptions", "DXFileError"),
        ("dxpy.exceptions", "DXChecksumMismatchError"),
    ],
}

METHOD_GROUPS: dict[str, tuple[str, str, list[str]]] = {
    "DXFile": (
        "dxpy",
        "DXFile",
        [
            "describe",
            "clone",
            "set_properties",
            "add_tags",
            "rename",
            "move",
            "close",
        ],
    ),
    "DXRecord": (
        "dxpy",
        "DXRecord",
        ["describe", "get_details", "set_details", "close"],
    ),
    "DXApplet": (
        "dxpy",
        "DXApplet",
        ["describe", "run"],
    ),
    "DXApp": (
        "dxpy",
        "DXApp",
        ["describe", "run"],
    ),
    "DXWorkflow": (
        "dxpy",
        "DXWorkflow",
        ["describe", "run", "add_stage", "close"],
    ),
    "DXJob": (
        "dxpy",
        "DXJob",
        ["describe", "wait_on_done", "get_output_ref", "terminate"],
    ),
    "DXAnalysis": (
        "dxpy",
        "DXAnalysis",
        ["describe", "wait_on_done", "get_output_ref", "terminate"],
    ),
    "DXProject": (
        "dxpy",
        "DXProject",
        [
            "describe",
            "list_folder",
            "new_folder",
            "move",
            "remove_objects",
            "remove_folder",
        ],
    ),
}

REQUIRED_SYMBOLS = {
    "dxpy.upload_local_file",
    "dxpy.download_dxfile",
    "dxpy.open_dxfile",
    "dxpy.find_data_objects",
    "dxpy.find_executions",
    "dxpy.dxlink",
    "dxpy.get_handler",
    "dxpy.DXFile",
    "dxpy.DXApplet",
    "dxpy.DXWorkflow",
    "dxpy.DXJob",
    "dxpy.DXAnalysis",
    "dxpy.DXProject",
    "dxpy.exceptions.DXAPIError",
    "dxpy.exceptions.DXJobFailureError",
}


def safe_signature(obj: Any) -> Optional[str]:
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return None


def inspect_symbol(module_name: str, symbol_name: str) -> dict[str, Any]:
    qualified_name = f"{module_name}.{symbol_name}"
    try:
        module = importlib.import_module(module_name)
    except Exception as error:
        return {
            "qualified_name": qualified_name,
            "available": False,
            "error": f"{type(error).__name__}: {error}",
        }

    if not hasattr(module, symbol_name):
        return {
            "qualified_name": qualified_name,
            "available": False,
            "error": "symbol not found",
        }

    obj = getattr(module, symbol_name)
    return {
        "qualified_name": qualified_name,
        "available": True,
        "kind": type(obj).__name__,
        "signature": safe_signature(obj),
    }


def inspect_methods(
    module_name: str,
    class_name: str,
    method_names: list[str],
) -> dict[str, Any]:
    try:
        cls = getattr(importlib.import_module(module_name), class_name)
    except Exception as error:
        return {"error": f"{type(error).__name__}: {error}"}

    methods: dict[str, Any] = {}
    for method_name in method_names:
        method = getattr(cls, method_name, None)
        methods[method_name] = {
            "available": method is not None,
            "signature": safe_signature(method) if method is not None else None,
        }
    return methods


def numeric_version(value: str) -> tuple[int, ...]:
    match = re.match(r"^(\d+(?:\.\d+)*)", value)
    if match is None:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def build_report() -> dict[str, Any]:
    try:
        dxpy_version = version("dxpy")
    except PackageNotFoundError:
        return {
            "schema_version": "1.0",
            "python": platform.python_version(),
            "platform": platform.platform(),
            "documented_baseline": DOCUMENTED_BASELINE,
            "dxpy_version": None,
            "version_meets_baseline": False,
            "symbols": {},
            "methods": {},
            "known_legacy_checks": {},
        }

    symbols = {
        group: [
            inspect_symbol(module_name, symbol_name)
            for module_name, symbol_name in entries
        ]
        for group, entries in SYMBOL_GROUPS.items()
    }
    methods = {
        group: inspect_methods(module_name, class_name, method_names)
        for group, (module_name, class_name, method_names) in METHOD_GROUPS.items()
    }

    try:
        dxpy = importlib.import_module("dxpy")
        legacy_open_file = hasattr(dxpy.DXFile, "open_file")
    except Exception:
        legacy_open_file = None

    return {
        "schema_version": "1.0",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "documented_baseline": DOCUMENTED_BASELINE,
        "dxpy_version": dxpy_version,
        "version_meets_baseline": (
            numeric_version(dxpy_version) >= numeric_version(DOCUMENTED_BASELINE)
        ),
        "symbols": symbols,
        "methods": methods,
        "known_legacy_checks": {
            "DXFile.open_file_available": legacy_open_file,
            "recommended_file_open": "dxpy.open_dxfile",
        },
    }


def missing_required_symbols(report: dict[str, Any]) -> list[str]:
    observed = {
        entry["qualified_name"]: entry["available"]
        for entries in report.get("symbols", {}).values()
        for entry in entries
    }
    return sorted(name for name in REQUIRED_SYMBOLS if not observed.get(name, False))


def missing_required_methods(report: dict[str, Any]) -> list[str]:
    required = {
        "DXFile.describe",
        "DXFile.clone",
        "DXApplet.run",
        "DXWorkflow.run",
        "DXJob.wait_on_done",
        "DXJob.get_output_ref",
        "DXAnalysis.wait_on_done",
        "DXProject.list_folder",
    }
    missing = []
    for qualified_name in sorted(required):
        class_name, method_name = qualified_name.split(".", 1)
        methods = report.get("methods", {}).get(class_name, {})
        if not methods.get(method_name, {}).get("available", False):
            missing.append(qualified_name)
    return missing


def print_text(report: dict[str, Any]) -> None:
    print(f"Python: {report['python']}")
    print(f"Platform: {report['platform']}")
    print(f"dxpy: {report['dxpy_version'] or 'not installed'}")
    print(f"Documented baseline: {report['documented_baseline']}")
    print(f"Meets baseline: {report['version_meets_baseline']}")

    for group, entries in report.get("symbols", {}).items():
        print(f"\n[{group}]")
        for entry in entries:
            status = "ok" if entry["available"] else "missing"
            line = f"- {status}: {entry['qualified_name']}"
            if entry.get("signature"):
                line += entry["signature"]
            if entry.get("error"):
                line += f" ({entry['error']})"
            print(line)

    print("\n[methods]")
    for class_name, methods in report.get("methods", {}).items():
        print(f"- {class_name}")
        if "error" in methods:
            print(f"  error: {methods['error']}")
            continue
        for method_name, details in methods.items():
            status = "ok" if details["available"] else "missing"
            signature = details["signature"] or ""
            print(f"  - {status}: {method_name}{signature}")

    print("\n[legacy checks]")
    for key, value in report.get("known_legacy_checks", {}).items():
        print(f"- {key}: {value}")

    missing_symbols = missing_required_symbols(report)
    missing_methods = missing_required_methods(report)
    if missing_symbols:
        print("\nMissing required symbols:")
        for name in missing_symbols:
            print(f"- {name}")
    if missing_methods:
        print("\nMissing required methods:")
        for name in missing_methods:
            print(f"- {name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if baseline symbols or methods are unavailable",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report()

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)

    if report["dxpy_version"] is None:
        return 2

    if args.strict:
        if not report["version_meets_baseline"]:
            return 1
        if missing_required_symbols(report):
            return 1
        if missing_required_methods(report):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
