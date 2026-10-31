#!/usr/bin/env python3
"""Validate or deterministically diff resource snapshots."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
from typing import Any, Mapping, Sequence

from _common import (
    MAX_BYTES,
    SCHEMA_VERSION,
    ResourceToolError,
    bounded_number,
    cli_error,
    emit_json,
    read_json_file,
)

MAX_DIFFS = 512


def _is_optional_nonnegative_number(value: Any) -> bool:
    return value is None or bounded_number(value, maximum=float(MAX_BYTES)) is not None


def _expect_mapping(
    parent: Mapping[str, Any],
    key: str,
    path: str,
    errors: list[dict[str, str]],
) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        errors.append(
            {
                "code": "TYPE",
                "message": "must be an object",
                "path": f"{path}.{key}",
            }
        )
        return {}
    return value


def _check_optional_number(
    parent: Mapping[str, Any],
    key: str,
    path: str,
    errors: list[dict[str, str]],
) -> None:
    if key not in parent or not _is_optional_nonnegative_number(parent.get(key)):
        errors.append(
            {
                "code": "NUMBER",
                "message": "required field must be null or a finite nonnegative bounded number",
                "path": f"{path}.{key}",
            }
        )


def validate_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the stable 1.1 resource snapshot contract."""
    errors: list[dict[str, str]] = []
    notes: list[dict[str, str]] = []
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            {
                "code": "SCHEMA_VERSION",
                "message": f"must equal {SCHEMA_VERSION}",
                "path": "$.schema_version",
            }
        )
    if snapshot.get("snapshot_kind") != "effective_resource_snapshot":
        errors.append(
            {
                "code": "SNAPSHOT_KIND",
                "message": "must equal effective_resource_snapshot",
                "path": "$.snapshot_kind",
            }
        )
    observed_at = snapshot.get("observed_at")
    try:
        valid_time = (isinstance(observed_at, str) and observed_at.endswith("Z")
                      and dt.datetime.fromisoformat(observed_at[:-1] + "+00:00").utcoffset()
                      == dt.timedelta(0))
    except ValueError:
        valid_time = False
    if not valid_time:
        errors.append(
            {
                "code": "TIMESTAMP",
                "message": "must be a UTC string ending in Z",
                "path": "$.observed_at",
            }
        )

    platform = _expect_mapping(snapshot, "platform", "$", errors)
    for key in ("system", "machine", "python_version"):
        if not isinstance(platform.get(key), str) or not platform.get(key):
            errors.append(
                {
                    "code": "PLATFORM",
                    "message": "must be a nonempty string",
                    "path": f"$.platform.{key}",
                }
            )

    cpu = _expect_mapping(snapshot, "cpu", "$", errors)
    host_cpu = _expect_mapping(cpu, "host", "$.cpu", errors)
    process_cpu = _expect_mapping(cpu, "process", "$.cpu", errors)
    cpu_cgroup = _expect_mapping(cpu, "cgroup_v2", "$.cpu", errors)
    effective_cpu = _expect_mapping(cpu, "effective", "$.cpu", errors)
    for key in ("logical", "physical"):
        _check_optional_number(host_cpu, key, "$.cpu.host", errors)
    for key in ("affinity_logical", "python_available_logical"):
        _check_optional_number(process_cpu, key, "$.cpu.process", errors)
    for key in ("cpuset_logical", "quota_cores"):
        _check_optional_number(cpu_cgroup, key, "$.cpu.cgroup_v2", errors)
    _check_optional_number(
        effective_cpu, "capacity_cores", "$.cpu.effective", errors
    )
    worker_ceiling = effective_cpu.get("worker_ceiling")
    if (
        isinstance(worker_ceiling, bool)
        or not isinstance(worker_ceiling, int)
        or not 1 <= worker_ceiling <= 1024
    ):
        errors.append(
            {
                "code": "WORKER_CEILING",
                "message": "must be an integer between 1 and 1024",
                "path": "$.cpu.effective.worker_ceiling",
            }
        )
    if not isinstance(effective_cpu.get("limiting_sources"), list):
        errors.append(
            {
                "code": "LIMIT_SOURCES",
                "message": "must be an array",
                "path": "$.cpu.effective.limiting_sources",
            }
        )

    memory = _expect_mapping(snapshot, "memory", "$", errors)
    host_memory = _expect_mapping(memory, "host", "$.memory", errors)
    effective_memory = _expect_mapping(memory, "effective", "$.memory", errors)
    memory_cgroup = _expect_mapping(memory, "cgroup_v2", "$.memory", errors)
    swap = _expect_mapping(memory, "swap", "$.memory", errors)
    for key in ("available_bytes", "total_bytes"):
        _check_optional_number(host_memory, key, "$.memory.host", errors)
    for key in (
        "available_bytes",
        "hard_limit_bytes",
        "pressure_threshold_bytes",
    ):
        _check_optional_number(effective_memory, key, "$.memory.effective", errors)
    for key in ("available_bytes", "current_bytes", "high_bytes", "max_bytes"):
        _check_optional_number(memory_cgroup, key, "$.memory.cgroup_v2", errors)
    for key in ("free_bytes", "total_bytes"):
        _check_optional_number(swap, key, "$.memory.swap", errors)
    available = effective_memory.get("available_bytes")
    hard_limit = effective_memory.get("hard_limit_bytes")
    if (
        isinstance(available, (int, float))
        and not isinstance(available, bool)
        and isinstance(hard_limit, (int, float))
        and not isinstance(hard_limit, bool)
        and available > hard_limit
    ):
        errors.append(
            {
                "code": "MEMORY_ORDER",
                "message": "available memory cannot exceed the effective hard limit",
                "path": "$.memory.effective.available_bytes",
            }
        )

    disk = _expect_mapping(snapshot, "disk", "$", errors)
    for key in ("capacity_bytes", "free_bytes", "user_available_bytes"):
        _check_optional_number(disk, key, "$.disk", errors)
    if disk.get("writable") is not None and not isinstance(
        disk.get("writable"), bool
    ):
        errors.append(
            {
                "code": "DISK_WRITABLE",
                "message": "must be boolean or null",
                "path": "$.disk.writable",
            }
        )
    free = disk.get("free_bytes")
    user_available = disk.get("user_available_bytes")
    capacity = disk.get("capacity_bytes")
    if all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in (free, user_available, capacity)
    ):
        if not 0 <= user_available <= free <= capacity:
            errors.append(
                {
                    "code": "DISK_ORDER",
                    "message": "expected user_available <= free <= capacity",
                    "path": "$.disk",
                }
            )

    accelerators = _expect_mapping(snapshot, "accelerators", "$", errors)
    for key in ("candidate_counts", "candidate_upper_bounds"):
        counts = _expect_mapping(accelerators, key, "$.accelerators", errors)
        for backend in ("cuda", "metal", "rocm"):
            value = counts.get(backend)
            if (backend not in counts or
                (value is None and key == "candidate_counts") or
                (value is not None and (isinstance(value, bool) or not isinstance(value, int)
                                       or not 0 <= value <= 256))):
                errors.append({"code": "ACCELERATOR_COUNT", "message": "invalid candidate count",
                               "path": f"$.accelerators.{key}.{backend}"})
    devices = accelerators.get("devices")
    if not isinstance(devices, list) or len(devices) > 256:
        errors.append(
            {
                "code": "ACCELERATOR_DEVICES",
                "message": "must be an array with at most 256 entries",
                "path": "$.accelerators.devices",
            }
        )
    else:
        for index, device in enumerate(devices):
            if not isinstance(device, dict):
                errors.append(
                    {
                        "code": "ACCELERATOR_DEVICE",
                        "message": "must be an object",
                        "path": f"$.accelerators.devices[{index}]",
                    }
                )
                continue
            backend = device.get("backend_candidate")
            if not isinstance(backend, str) or backend not in {"cuda", "metal", "rocm"}:
                errors.append(
                    {
                        "code": "ACCELERATOR_BACKEND",
                        "message": "must be cuda, metal, or rocm",
                        "path": (
                            f"$.accelerators.devices[{index}].backend_candidate"
                        ),
                    }
                )
            if device.get("device_permission") != "not_tested":
                notes.append(
                    {
                        "code": "PERMISSION_ASSERTION",
                        "message": (
                            "device permission differs from the detector's "
                            "conservative not_tested default"
                        ),
                        "path": (
                            f"$.accelerators.devices[{index}].device_permission"
                        ),
                    }
                )
            if device.get("runtime_compatibility") != "not_tested":
                notes.append(
                    {
                        "code": "RUNTIME_ASSERTION",
                        "message": (
                            "runtime compatibility differs from the detector's "
                            "conservative not_tested default"
                        ),
                        "path": (
                            f"$.accelerators.devices[{index}].runtime_compatibility"
                        ),
                    }
                )

    scheduler = _expect_mapping(snapshot, "scheduler", "$", errors)
    if not isinstance(scheduler.get("fields_read"), list):
        errors.append(
            {
                "code": "SCHEDULER_FIELDS",
                "message": "must be an array",
                "path": "$.scheduler.fields_read",
            }
        )
    privacy = _expect_mapping(snapshot, "privacy", "$", errors)
    for key in (
        "absolute_paths_included",
        "environment_values_included",
        "hostnames_included",
        "identifiers_redacted_by_default",
    ):
        if not isinstance(privacy.get(key), bool):
            errors.append(
                {
                    "code": "PRIVACY",
                    "message": "must be boolean",
                    "path": f"$.privacy.{key}",
                }
            )
    if any(
        privacy.get(key) is True
        for key in (
            "absolute_paths_included",
            "environment_values_included",
            "hostnames_included",
        )
    ):
        notes.append(
            {
                "code": "PRIVACY_EXPANDED",
                "message": "snapshot includes fields normally redacted",
                "path": "$.privacy",
            }
        )

    warning_items = snapshot.get("warnings")
    if not isinstance(warning_items, list) or len(warning_items) > 512:
        errors.append(
            {
                "code": "WARNINGS",
                "message": "must be an array with at most 512 entries",
                "path": "$.warnings",
            }
        )
    provenance = snapshot.get("provenance")
    if not isinstance(provenance, list) or len(provenance) > 512:
        errors.append(
            {
                "code": "PROVENANCE",
                "message": "must be an array with at most 512 entries",
                "path": "$.provenance",
            }
        )

    errors.sort(key=lambda item: (item["path"], item["code"], item["message"]))
    notes.sort(key=lambda item: (item["path"], item["code"], item["message"]))
    return {
        "errors": errors,
        "kind": "snapshot_validation",
        "notes": notes,
        "schema_version": SCHEMA_VERSION,
        "valid": not errors,
    }


def _strip_volatile(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    cleaned = copy.deepcopy(dict(snapshot))
    cleaned.pop("observed_at", None)
    return cleaned


def _diff_values(
    before: Any,
    after: Any,
    path: str,
    changes: list[dict[str, Any]],
) -> None:
    if len(changes) >= MAX_DIFFS:
        return
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child_path = f"{path}.{key}"
            if key not in before:
                changes.append(
                    {
                        "after": after[key],
                        "before": None,
                        "change": "added",
                        "path": child_path,
                    }
                )
            elif key not in after:
                changes.append(
                    {
                        "after": None,
                        "before": before[key],
                        "change": "removed",
                        "path": child_path,
                    }
                )
            else:
                _diff_values(before[key], after[key], child_path, changes)
            if len(changes) >= MAX_DIFFS:
                return
        return
    if isinstance(before, list) and isinstance(after, list):
        maximum = max(len(before), len(after))
        for index in range(maximum):
            child_path = f"{path}[{index}]"
            if index >= len(before):
                changes.append(
                    {
                        "after": after[index],
                        "before": None,
                        "change": "added",
                        "path": child_path,
                    }
                )
            elif index >= len(after):
                changes.append(
                    {
                        "after": None,
                        "before": before[index],
                        "change": "removed",
                        "path": child_path,
                    }
                )
            else:
                _diff_values(before[index], after[index], child_path, changes)
            if len(changes) >= MAX_DIFFS:
                return
        return
    if before != after:
        changes.append(
            {
                "after": after,
                "before": before,
                "change": "changed",
                "path": path,
            }
        )


def diff_snapshots(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    include_volatile: bool = False,
) -> dict[str, Any]:
    """Return a bounded, stable structural diff."""
    before_validation = validate_snapshot(before)
    after_validation = validate_snapshot(after)
    if not before_validation["valid"] or not after_validation["valid"]:
        raise ResourceToolError("both snapshots must validate before diffing")
    try:
        left = dict(before) if include_volatile else _strip_volatile(before)
        right = dict(after) if include_volatile else _strip_volatile(after)
        changes: list[dict[str, Any]] = []
        _diff_values(left, right, "$", changes)
    except RecursionError as exc:
        raise ResourceToolError("snapshot nesting exceeds the diff safety bound") from exc
    return {
        "change_count": len(changes),
        "changes": changes,
        "ignored_paths": [] if include_volatile else ["$.observed_at"],
        "kind": "snapshot_diff",
        "schema_version": SCHEMA_VERSION,
        "truncated": len(changes) >= MAX_DIFFS,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or structurally diff resource snapshot JSON"
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
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate one snapshot")
    validate.add_argument("snapshot", help="snapshot JSON file")
    diff = commands.add_parser("diff", help="diff two valid snapshots")
    diff.add_argument("before", help="earlier snapshot JSON file")
    diff.add_argument("after", help="later snapshot JSON file")
    diff.add_argument(
        "--include-volatile",
        action="store_true",
        help="include observed_at in the diff",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.force and not args.output:
        parser.error("--force requires --output")
    try:
        if args.command == "validate":
            report = validate_snapshot(read_json_file(args.snapshot))
            emit_json(report, args.output, force=args.force)
            return 0 if report["valid"] else 1
        report = diff_snapshots(
            read_json_file(args.before),
            read_json_file(args.after),
            include_volatile=args.include_volatile,
        )
        emit_json(report, args.output, force=args.force)
        return 0
    except ResourceToolError as exc:
        return cli_error(parser, exc)


if __name__ == "__main__":
    raise SystemExit(main())
