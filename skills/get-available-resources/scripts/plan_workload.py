#!/usr/bin/env python3
"""Build a conservative worker and memory plan from a validated snapshot."""

from __future__ import annotations

import argparse
import math
from typing import Any, Mapping, Sequence

from _common import (
    MAX_BYTES,
    MAX_TASKS,
    MAX_WORKERS,
    SCHEMA_VERSION,
    ResourceToolError,
    argparse_nonnegative_int,
    argparse_positive_int,
    bounded_number,
    cli_error,
    emit_json,
    read_json_file,
)
from snapshot_tools import validate_snapshot

MIB = 1024**2


def _optional_number(value: Any) -> float | None:
    return bounded_number(value, maximum=float(MAX_BYTES))


def _accelerator_decision(
    snapshot: Mapping[str, Any],
    requested: str,
) -> dict[str, Any]:
    if requested == "none":
        return {
            "candidate_count_upper_bound": 0,
            "requested": "none",
            "status": "not_requested",
        }
    accelerators = snapshot["accelerators"]
    bounds = accelerators.get("candidate_upper_bounds", {})
    counts = accelerators.get("candidate_counts", {})
    if requested == "any":
        candidates = [
            value
            for backend, value in bounds.items()
            if backend in {"cuda", "metal", "rocm"} and isinstance(value, int)
        ]
        query_count = sum(
            value
            for backend, value in counts.items()
            if backend in {"cuda", "metal", "rocm"} and isinstance(value, int)
        )
        upper_bound = sum(candidates) if candidates else None
    else:
        query_count = counts.get(requested, 0)
        upper_bound = bounds.get(requested)
    if not query_count:
        status = "no_management_visible_candidate"
    elif upper_bound == 0:
        status = "restricted_by_allocation_or_visibility"
    else:
        status = "diagnostic_required"
    return {
        "candidate_count_upper_bound": upper_bound,
        "management_query_count": query_count,
        "requested": requested,
        "status": status,
        "usability": "not_verified",
    }


def build_plan(
    snapshot: Mapping[str, Any],
    *,
    workload: str = "cpu",
    task_count: int | None = None,
    requested_workers: int | None = None,
    memory_per_worker_mib: int | None = None,
    reserve_memory_mib: int | None = None,
    accelerator: str = "none",
) -> dict[str, Any]:
    """Return a bounded deterministic plan without executing work."""
    validation = validate_snapshot(snapshot)
    if not validation["valid"]:
        raise ResourceToolError("snapshot does not satisfy schema 1.1")
    if workload not in {"cpu", "io", "mixed"}:
        raise ResourceToolError("workload must be cpu, io, or mixed")
    if accelerator not in {"none", "any", "cuda", "metal", "rocm"}:
        raise ResourceToolError(
            "accelerator must be none, any, cuda, metal, or rocm"
        )
    for label, value, maximum in (
        ("task_count", task_count, MAX_TASKS),
        ("requested_workers", requested_workers, MAX_WORKERS),
        ("memory_per_worker_mib", memory_per_worker_mib, 1_048_576),
    ):
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= maximum
        ):
            raise ResourceToolError(f"{label} is outside its safe range")
    if reserve_memory_mib is not None and (
        isinstance(reserve_memory_mib, bool)
        or not isinstance(reserve_memory_mib, int)
        or not 0 <= reserve_memory_mib <= 1_048_576
    ):
        raise ResourceToolError("reserve_memory_mib is outside its safe range")

    effective_cpu = snapshot["cpu"]["effective"]
    cpu_capacity = _optional_number(effective_cpu.get("capacity_cores"))
    cpu_ceiling = effective_cpu.get("worker_ceiling", 1)
    if not isinstance(cpu_ceiling, int):
        cpu_ceiling = 1
    cpu_ceiling = max(1, min(MAX_WORKERS, cpu_ceiling))
    if cpu_capacity is not None:
        cpu_ceiling = min(cpu_ceiling, max(1, math.floor(cpu_capacity)))
    if workload == "io":
        workload_ceiling = min(MAX_WORKERS, 32, max(2, cpu_ceiling * 2))
    else:
        workload_ceiling = cpu_ceiling

    available_memory = _optional_number(
        snapshot["memory"]["effective"].get("available_bytes")
    )
    if reserve_memory_mib is None and available_memory is not None:
        reserve_bytes = min(
            int(available_memory * 0.5),
            max(256 * MIB, int(available_memory * 0.1)),
        )
    elif reserve_memory_mib is not None:
        reserve_bytes = reserve_memory_mib * MIB
    else:
        reserve_bytes = None

    memory_ceiling: int | None = None
    planner_warnings: list[dict[str, str]] = []
    if memory_per_worker_mib is not None:
        per_worker_bytes = memory_per_worker_mib * MIB
        if available_memory is None or reserve_bytes is None:
            memory_ceiling = 1
            planner_warnings.append(
                {
                    "code": "MEMORY_UNKNOWN",
                    "message": (
                        "Memory per worker was supplied but effective available "
                        "memory is unknown; one worker is recommended."
                    ),
                }
            )
        else:
            usable = max(0, int(available_memory) - reserve_bytes)
            memory_ceiling = min(MAX_WORKERS, usable // per_worker_bytes)
            if usable < per_worker_bytes:
                planner_warnings.append(
                    {
                        "code": "MEMORY_REQUIREMENT_EXCEEDS_BUDGET",
                        "message": (
                            "No worker fits the post-reserve memory budget; "
                            "reduce the requirement or use out-of-core processing."
                        ),
                    }
                )

    ceilings: list[tuple[str, int]] = [("workload_cpu", workload_ceiling)]
    if memory_ceiling is not None:
        ceilings.append(("memory", memory_ceiling))
    if task_count is not None:
        ceilings.append(("tasks", min(task_count, MAX_WORKERS)))
    if requested_workers is not None:
        ceilings.append(("user_request", requested_workers))
    suggested = min(value for _, value in ceilings)
    binding = sorted(source for source, value in ceilings if value == suggested)

    if workload == "io":
        planner_warnings.append(
            {
                "code": "IO_OVERSUBSCRIPTION_HEURISTIC",
                "message": (
                    "The I/O worker count is a bounded heuristic; benchmark the "
                    "real workload without exceeding allocations."
                ),
            }
        )
    if snapshot["scheduler"].get("detected"):
        planner_warnings.append(
            {
                "code": "SCHEDULER_SCOPE",
                "message": (
                    "Remain inside the scheduler allocation even when host "
                    "inventory is larger."
                ),
            }
        )
    if cpu_capacity is None:
        planner_warnings.append(
            {
                "code": "CPU_CAPACITY_UNKNOWN",
                "message": "Effective CPU capacity is unknown; the plan remains conservative.",
            }
        )

    threads_per_worker = 1 if suggested else 0
    if suggested and workload in {"cpu", "mixed"} and cpu_capacity is not None:
        threads_per_worker = max(1, math.floor(cpu_capacity / suggested))
    planner_warnings.sort(key=lambda item: (item["code"], item["message"]))
    return {
        "accelerator": _accelerator_decision(snapshot, accelerator),
        "inputs": {
            "accelerator": accelerator,
            "memory_per_worker_bytes": (
                memory_per_worker_mib * MIB
                if memory_per_worker_mib is not None
                else None
            ),
            "requested_workers": requested_workers,
            "reserve_memory_bytes": reserve_bytes,
            "task_count": task_count,
            "workload": workload,
        },
        "kind": "workload_plan",
        "limits": {
            "cpu_capacity_cores": cpu_capacity,
            "cpu_worker_ceiling": cpu_ceiling,
            "memory_worker_ceiling": memory_ceiling,
            "workload_worker_ceiling": workload_ceiling,
        },
        "recommendation": {
            "binding_limits": binding,
            "status": (
                "insufficient_memory" if not suggested else
                "review_required" if cpu_capacity is None or available_memory is None else
                "provisional"
            ),
            "suggested_workers": suggested,
            "threads_per_worker": threads_per_worker,
        },
        "schema_version": SCHEMA_VERSION,
        "warnings": planner_warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan bounded workers and memory from a resource snapshot"
    )
    parser.add_argument("snapshot", help="validated snapshot JSON file")
    parser.add_argument(
        "--workload",
        choices=("cpu", "io", "mixed"),
        default="cpu",
        help="workload shape; default: cpu",
    )
    parser.add_argument(
        "--tasks",
        type=argparse_positive_int,
        help="number of independent tasks",
    )
    parser.add_argument(
        "--workers",
        type=lambda value: argparse_positive_int(value, maximum=MAX_WORKERS),
        help="explicit upper bound on workers",
    )
    parser.add_argument(
        "--memory-per-worker-mib",
        type=lambda value: argparse_positive_int(value, maximum=1_048_576),
        help="estimated MiB required by each worker",
    )
    parser.add_argument(
        "--reserve-memory-mib",
        type=lambda value: argparse_nonnegative_int(value, maximum=1_048_576),
        help="explicit MiB to keep outside the worker budget",
    )
    parser.add_argument(
        "--accelerator",
        choices=("none", "any", "cuda", "rocm", "metal"),
        default="none",
        help="request a candidate backend without assuming runtime usability",
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
        plan = build_plan(
            read_json_file(args.snapshot),
            workload=args.workload,
            task_count=args.tasks,
            requested_workers=args.workers,
            memory_per_worker_mib=args.memory_per_worker_mib,
            reserve_memory_mib=args.reserve_memory_mib,
            accelerator=args.accelerator,
        )
        emit_json(plan, args.output, force=args.force)
    except ResourceToolError as exc:
        return cli_error(parser, exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
