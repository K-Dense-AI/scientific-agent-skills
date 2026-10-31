#!/usr/bin/env python3
"""Generate, but never execute, a read-only accelerator diagnostic plan."""

from __future__ import annotations

import argparse
from typing import Any, Mapping, Sequence

from _common import (
    SCHEMA_VERSION,
    ResourceToolError,
    cli_error,
    emit_json,
    read_json_file,
)
from snapshot_tools import validate_snapshot

FIXED_COMMANDS: dict[str, list[list[str]]] = {
    "cuda": [
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.total,memory.free,driver_version,compute_cap",
            "--format=csv,noheader,nounits",
        ]
    ],
    "metal": [["system_profiler", "SPDisplaysDataType", "-json"]],
    "rocm": [
        ["amd-smi", "static", "--asic", "--vram", "--json"],
        [
            "rocm-smi",
            "--showproductname",
            "--showmeminfo",
            "vram",
            "--json",
        ],
    ],
}


def build_diagnostic_plan(
    snapshot: Mapping[str, Any],
    *,
    backend: str = "auto",
) -> dict[str, Any]:
    """Return fixed read-only probes and interpretation gates."""
    validation = validate_snapshot(snapshot)
    if not validation["valid"]:
        raise ResourceToolError("snapshot does not satisfy schema 1.1")
    if backend not in {"auto", "cuda", "metal", "rocm"}:
        raise ResourceToolError("backend must be auto, cuda, metal, or rocm")

    counts = snapshot["accelerators"].get("candidate_counts", {})
    if backend == "auto":
        selected = [
            candidate
            for candidate in ("cuda", "rocm", "metal")
            if isinstance(counts.get(candidate), int) and counts[candidate] > 0
        ]
    else:
        selected = [backend]

    checks: list[dict[str, Any]] = []
    for candidate in selected:
        checks.append(
            {
                "backend": candidate,
                "commands": FIXED_COMMANDS[candidate],
                "management_visibility_gate": (
                    "A successful query confirms only management-tool visibility."
                ),
                "permission_gate": (
                    "Verify the allocation/container exposes the intended device; "
                    "do not broaden device permissions automatically."
                ),
                "runtime_gate": (
                    "Run the target framework's documented availability check in "
                    "the exact environment and verify driver/runtime compatibility."
                ),
            }
        )

    if not selected:
        status = "no_management_visible_candidate"
    elif any(
        snapshot["accelerators"]
        .get("candidate_upper_bounds", {})
        .get(candidate)
        == 0
        for candidate in selected
    ):
        status = "visibility_or_allocation_restriction_present"
    else:
        status = "manual_runtime_validation_required"
    return {
        "checks": checks,
        "execution": "not_performed",
        "kind": "accelerator_diagnostic_plan",
        "prohibited_actions": [
            "driver installation or mutation",
            "device reset, clock, power, or persistence changes",
            "stress tests or large allocations",
            "broad environment dumps",
        ],
        "schema_version": SCHEMA_VERSION,
        "selected_backends": selected,
        "status": status,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Produce a read-only accelerator diagnostic plan; run nothing"
    )
    parser.add_argument("snapshot", help="validated snapshot JSON file")
    parser.add_argument(
        "--backend",
        choices=("auto", "cuda", "rocm", "metal"),
        default="auto",
        help="backend to plan; default: auto from snapshot candidates",
    )
    parser.add_argument(
        "--output",
        metavar="FILE.json",
        help="write a private local JSON file instead of stdout",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing explicit output file",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.force and not args.output:
        parser.error("--force requires --output")
    try:
        report = build_diagnostic_plan(
            read_json_file(args.snapshot),
            backend=args.backend,
        )
        emit_json(report, args.output, force=args.force)
    except ResourceToolError as exc:
        return cli_error(parser, exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
