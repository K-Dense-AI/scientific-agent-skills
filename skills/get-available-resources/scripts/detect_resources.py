#!/usr/bin/env python3
"""Collect a conservative, privacy-preserving resource snapshot.

The script performs only bounded, read-only probes. It never stress-tests the
machine, allocates a large buffer, changes affinity, or changes accelerator
state. JSON is written to stdout unless a private local filename is explicitly
requested.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib
import io
import json
import math
import os
import platform
import re
import shutil
import subprocess
import threading
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from _common import (
    MAX_BYTES,
    SCHEMA_VERSION,
    ResourceToolError,
    cli_error,
    emit_json,
)

MAX_PROBE_OUTPUT = 65_536
MAX_KERNEL_TEXT = 524_288
MAX_CGROUP_LEVELS = 64
MAX_CPU_ID = 1_048_575
MAX_DEVICES = 256
MIB = 1024**2
GIB = 1024**3
_AUTO = object()

NVIDIA_QUERY = (
    "nvidia-smi",
    "--query-gpu=index,name,memory.total,memory.free,driver_version,compute_cap",
    "--format=csv,noheader,nounits",
)
NVIDIA_QUERY_FALLBACK = (
    "nvidia-smi",
    "--query-gpu=index,name,memory.total,memory.free,driver_version",
    "--format=csv,noheader,nounits",
)
AMD_SMI_QUERY = ("amd-smi", "static", "--asic", "--vram", "--json")
ROCM_SMI_QUERY = (
    "rocm-smi",
    "--showproductname",
    "--showmeminfo",
    "vram",
    "--json",
)
APPLE_DISPLAY_QUERY = ("system_profiler", "SPDisplaysDataType", "-json")
APPLE_SYSCTL_QUERY = (
    "sysctl",
    "-n",
    "hw.logicalcpu",
    "hw.physicalcpu",
    "hw.memsize",
    "machdep.cpu.brand_string",
)

ACCELERATOR_ENV_KEYS = (
    "CUDA_VISIBLE_DEVICES",
    "HIP_VISIBLE_DEVICES",
    "NVIDIA_VISIBLE_DEVICES",
    "ROCR_VISIBLE_DEVICES",
)
SLURM_ENV_KEYS = (
    "SLURM_JOB_ID",
    "SLURM_JOBID",
    "SLURM_CPUS_ON_NODE",
    "SLURM_CPUS_PER_TASK",
    "SLURM_JOB_CPUS_PER_NODE",
    "SLURM_MEM_PER_CPU",
    "SLURM_MEM_PER_NODE",
    "SLURM_NTASKS",
    "SLURM_NTASKS_PER_NODE",
    "SLURM_TASKS_PER_NODE",
    "SLURM_NODEID",
    "SLURM_GPUS",
    "SLURM_GPUS_ON_NODE",
    "SLURM_GPUS_PER_TASK",
    "SLURM_JOB_GPUS",
    "SLURM_STEP_GPUS",
)


def _warning(
    warnings: list[dict[str, str]],
    code: str,
    component: str,
    message: str,
    *,
    severity: str = "warning",
) -> None:
    warnings.append(
        {
            "code": code,
            "component": component,
            "message": message,
            "severity": severity,
        }
    )


def _provenance(
    records: list[dict[str, str]],
    component: str,
    source: str,
    status: str,
) -> None:
    records.append(
        {"component": component, "source": source, "status": status}
    )


def _safe_text(value: Any, maximum: int = 128) -> str | None:
    if not isinstance(value, (str, int, float)):
        return None
    rendered = " ".join(str(value).split())
    rendered = "".join(character for character in rendered if character.isprintable())
    return rendered[:maximum] or None


def _read_bounded_text(path: Path, maximum: int = MAX_KERNEL_TEXT) -> str:
    with path.open("rb") as stream:
        payload = stream.read(maximum + 1)
    if len(payload) > maximum:
        raise ValueError("bounded text input exceeded")
    return payload.decode("utf-8", errors="replace")


def _try_read(
    read_text: Callable[[Path], str],
    path: Path,
) -> str | None:
    try:
        return read_text(path)
    except (OSError, ValueError, UnicodeError):
        return None


def _bounded_nonnegative(value: str | int | None) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = int(str(value).strip(), 10)
    except (TypeError, ValueError):
        return None
    return parsed if 0 <= parsed <= MAX_BYTES else None


def parse_cpu_list(value: str) -> int | None:
    """Count CPUs in a Linux range list without expanding it."""
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        return None
    intervals: list[tuple[int, int]] = []
    for token in value.strip().split(","):
        token = token.strip()
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", token)
        if not match:
            return None
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start > end or end > MAX_CPU_ID:
            return None
        intervals.append((start, end))
    intervals.sort()
    total = 0
    current_start, current_end = intervals[0]
    for start, end in intervals[1:]:
        if start <= current_end + 1:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start + 1
            current_start, current_end = start, end
    total += current_end - current_start + 1
    return total if total <= MAX_CPU_ID + 1 else None


def _parse_cpu_max(value: str) -> float | None:
    fields = value.strip().split()
    if len(fields) != 2 or fields[0] == "max":
        return None
    quota = _bounded_nonnegative(fields[0])
    period = _bounded_nonnegative(fields[1])
    if quota is None or period in (None, 0) or quota == 0:
        return None
    capacity = quota / period
    if not math.isfinite(capacity) or capacity <= 0:
        return None
    return round(capacity, 6)


def _run_bounded_command(
    argv: Sequence[str],
    *,
    timeout: float = 4.0,
    maximum: int = MAX_PROBE_OUTPUT,
) -> dict[str, Any]:
    """Run a fixed argv with bounded stdout/stderr and no shell."""
    if not isinstance(argv, tuple) or not argv or not all(
        isinstance(item, str) and item for item in argv
    ):
        raise ValueError("internal command must be a fixed nonempty tuple")
    try:
        process = subprocess.Popen(
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except FileNotFoundError:
        return {"status": "not_found", "stdout": "", "stderr": ""}
    except OSError:
        return {"status": "start_error", "stdout": "", "stderr": ""}

    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    truncated = threading.Event()

    def drain(name: str, stream: Any) -> None:
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                remaining = maximum - len(buffers[name])
                if remaining > 0:
                    buffers[name].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated.set()
                    try:
                        process.kill()
                    except OSError:
                        pass
        finally:
            try:
                stream.close()
            except OSError:
                pass

    threads = [
        threading.Thread(
            target=drain,
            args=("stdout", process.stdout),
            daemon=True,
        ),
        threading.Thread(
            target=drain,
            args=("stderr", process.stderr),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    timed_out = False
    try:
        return_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            process.kill()
        except OSError:
            pass
        return_code = process.wait()
    for thread in threads:
        thread.join(timeout=1.0)

    status = "ok" if return_code == 0 else "error"
    if timed_out:
        status = "timeout"
    elif truncated.is_set():
        status = "truncated"
    return {
        "returncode": return_code,
        "status": status,
        "stderr": buffers["stderr"].decode("utf-8", errors="replace"),
        "stdout": buffers["stdout"].decode("utf-8", errors="replace"),
    }


def _load_psutil(
    warnings: list[dict[str, str]],
    provenance: list[dict[str, str]],
) -> Any | None:
    try:
        module = importlib.import_module("psutil")
    except (ImportError, OSError):
        _warning(
            warnings,
            "PSUTIL_UNAVAILABLE",
            "inventory",
            "Optional psutil is unavailable; standard-library fallbacks were used.",
            severity="info",
        )
        _provenance(provenance, "inventory.psutil", "optional_import", "unavailable")
        return None
    _provenance(provenance, "inventory.psutil", "optional_import", "ok")
    return module


def _linux_physical_cores(
    read_text: Callable[[Path], str],
) -> int | None:
    payload = _try_read(read_text, Path("/proc/cpuinfo"))
    if not payload:
        return None
    pairs: set[tuple[str, str]] = set()
    for block in payload.split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip().lower()] = value.strip()
        if "physical id" in fields and "core id" in fields:
            pairs.add((fields["physical id"], fields["core id"]))
    count = len(pairs)
    return count if 0 < count <= MAX_CPU_ID + 1 else None


def _mac_sysctl_values(
    run_command: Callable[..., dict[str, Any]],
    warnings: list[dict[str, str]],
    provenance: list[dict[str, str]],
) -> dict[str, Any]:
    result = run_command(APPLE_SYSCTL_QUERY, timeout=2.0)
    if result["status"] != "ok":
        _warning(
            warnings,
            "APPLE_SYSCTL_UNAVAILABLE",
            "platform",
            "Apple sysctl inventory was unavailable; other sources were retained.",
            severity="info",
        )
        _provenance(provenance, "platform.apple_sysctl", "sysctl", result["status"])
        return {}
    lines = result["stdout"].splitlines()
    if len(lines) < 4:
        _warning(
            warnings,
            "APPLE_SYSCTL_PARSE_FAILED",
            "platform",
            "Apple sysctl returned an unexpected bounded response.",
        )
        _provenance(provenance, "platform.apple_sysctl", "sysctl", "parse_error")
        return {}
    _provenance(provenance, "platform.apple_sysctl", "sysctl", "ok")
    return {
        "logical": _bounded_nonnegative(lines[0]),
        "physical": _bounded_nonnegative(lines[1]),
        "memory": _bounded_nonnegative(lines[2]),
        "brand": _safe_text(lines[3]),
    }


def _detect_cpu_inventory(
    *,
    system: str,
    psutil_module: Any | None,
    mac_sysctl: Mapping[str, Any],
    read_text: Callable[[Path], str],
    warnings: list[dict[str, str]],
    provenance: list[dict[str, str]],
) -> dict[str, int | None]:
    host_logical = None
    logical_source = "os.cpu_count"
    if psutil_module is not None:
        try:
            host_logical = psutil_module.cpu_count(logical=True)
            logical_source = "psutil.cpu_count"
        except (AttributeError, OSError, RuntimeError, ValueError,
                getattr(psutil_module, "Error", OSError)):
            pass
    if host_logical is None and system == "Darwin":
        host_logical = mac_sysctl.get("logical")
        logical_source = "sysctl"
    if host_logical is None:
        try:
            candidate = os.sysconf("SC_NPROCESSORS_ONLN")
            if candidate > 0:
                host_logical = candidate
                logical_source = "os.sysconf"
        except (AttributeError, OSError, ValueError):
            pass
    if host_logical is None:
        host_logical = os.cpu_count()
        logical_source = "os.cpu_count"
        _warning(warnings, "PYTHON_CPU_COUNT_FALLBACK", "cpu",
                 "Host CPU fallback can reflect Python's configured CPU-count override.",
                 severity="info")
    if (
        not isinstance(host_logical, int)
        or isinstance(host_logical, bool)
        or not 1 <= host_logical <= MAX_CPU_ID + 1
    ):
        host_logical = None
        _warning(
            warnings,
            "HOST_LOGICAL_CPU_UNKNOWN",
            "cpu",
            "Host logical CPU count could not be determined.",
        )
        _provenance(provenance, "cpu.host.logical", logical_source, "unavailable")
    else:
        _provenance(provenance, "cpu.host.logical", logical_source, "ok")

    host_physical: int | None = None
    if psutil_module is not None:
        try:
            candidate = psutil_module.cpu_count(logical=False)
            if (
                isinstance(candidate, int)
                and not isinstance(candidate, bool)
                and 0 < candidate <= MAX_CPU_ID + 1
            ):
                host_physical = candidate
                _provenance(
                    provenance, "cpu.host.physical", "psutil.cpu_count", "ok"
                )
        except (AttributeError, OSError, RuntimeError, ValueError,
                getattr(psutil_module, "Error", OSError)):
            pass
    if host_physical is None and system == "Darwin":
        candidate = mac_sysctl.get("physical")
        if isinstance(candidate, int) and 0 < candidate <= MAX_CPU_ID + 1:
            host_physical = candidate
            _provenance(provenance, "cpu.host.physical", "sysctl", "ok")
    if host_physical is None and system == "Linux":
        host_physical = _linux_physical_cores(read_text)
        if host_physical is not None:
            _provenance(provenance, "cpu.host.physical", "proc_cpuinfo", "ok")
    if host_physical is None:
        _warning(
            warnings,
            "HOST_PHYSICAL_CPU_UNKNOWN",
            "cpu",
            "Physical core count is unknown and was not inferred from logical CPUs.",
            severity="info",
        )
        _provenance(provenance, "cpu.host.physical", "platform_fallbacks", "unavailable")
    return {"logical": host_logical, "physical": host_physical}


def _detect_process_cpu_count(
    *,
    psutil_module: Any | None,
    warnings: list[dict[str, str]],
    provenance: list[dict[str, str]],
) -> dict[str, int | None]:
    affinity_count: int | None = None
    affinity_source: str | None = None
    get_affinity = getattr(os, "sched_getaffinity", None)
    if callable(get_affinity):
        try:
            affinity = get_affinity(0)
            if affinity and len(affinity) <= MAX_CPU_ID + 1:
                affinity_count = len(affinity)
                affinity_source = "os.sched_getaffinity"
        except (OSError, TypeError, ValueError):
            pass
    if affinity_count is None and psutil_module is not None:
        try:
            affinity = psutil_module.Process().cpu_affinity()
            if affinity and len(affinity) <= MAX_CPU_ID + 1:
                affinity_count = len(affinity)
                affinity_source = "psutil.Process.cpu_affinity"
        except (AttributeError, OSError, RuntimeError, ValueError,
                getattr(psutil_module, "Error", OSError)):
            pass
    if affinity_count is not None:
        _provenance(provenance, "cpu.process.affinity_logical", affinity_source or "", "ok")
    else:
        _provenance(
            provenance, "cpu.process.affinity_logical", "affinity_apis", "unavailable"
        )

    process_count: int | None = None
    process_cpu_count = getattr(os, "process_cpu_count", None)
    if callable(process_cpu_count):
        try:
            candidate = process_cpu_count()
            if (
                isinstance(candidate, int)
                and not isinstance(candidate, bool)
                and 0 < candidate <= MAX_CPU_ID + 1
            ):
                process_count = candidate
                _provenance(
                    provenance,
                    "cpu.process.python_available_logical",
                    "os.process_cpu_count",
                    "ok",
                )
        except (OSError, ValueError):
            pass
    if affinity_count is None and process_count is None:
        _warning(
            warnings,
            "PROCESS_CPU_SCOPE_UNKNOWN",
            "cpu",
            "No process-aware CPU count API was available.",
            severity="info",
        )
    return {
        "affinity_logical": affinity_count,
        "python_available_logical": process_count,
    }


def _cgroup_relative_path(payload: str) -> tuple[str, ...] | None:
    for line in payload.splitlines():
        fields = line.split(":", 2)
        if len(fields) == 3 and fields[0] == "0" and fields[1] == "":
            raw = PurePosixPath(fields[2])
            if not raw.is_absolute():
                return None
            parts = tuple(part for part in raw.parts if part not in {"/", ""})
            if any(part in {".", ".."} for part in parts):
                return None
            return parts
    return None


def _resolve_cgroup_mount(
    payload: str, parts: tuple[str, ...]
) -> tuple[Path, tuple[str, ...]] | None:
    """Map namespace membership through a cgroup2 mount's root and mountpoint."""
    matches = []
    for line in payload.splitlines():
        fields = line.split()
        try:
            separator = fields.index("-")
        except ValueError:
            continue
        if len(fields) <= separator + 1 or fields[separator + 1] != "cgroup2" or separator < 6:
            continue
        decoded = [re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), field)
                   for field in fields[3:5]]
        mount_root, mountpoint = map(PurePosixPath, decoded)
        if any(not p.is_absolute() or ".." in p.parts for p in (mount_root, mountpoint)):
            continue
        prefix = mount_root.parts[1:]
        if parts[:len(prefix)] == prefix:
            matches.append((len(prefix), Path(str(mountpoint)), parts[len(prefix):]))
    if not matches:
        return None
    # A broader visible mount retains ancestors that a nested bind mount hides.
    _, mountpoint, relative = min(matches, key=lambda item: item[0])
    return mountpoint, relative


def detect_cgroup_v2(
    *,
    read_text: Callable[[Path], str] = _read_bounded_text,
    root: Path = Path("/sys/fs/cgroup"),
    proc_self_cgroup: Path = Path("/proc/self/cgroup"),
    proc_self_mountinfo: Path = Path("/proc/self/mountinfo"),
    warnings: list[dict[str, str]] | None = None,
    provenance: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Read current and ancestor cgroup v2 limits without exposing paths."""
    warning_records = warnings if warnings is not None else []
    provenance_records = provenance if provenance is not None else []
    membership = _try_read(read_text, proc_self_cgroup)
    parts = _cgroup_relative_path(membership or "")
    mountinfo = _try_read(read_text, proc_self_mountinfo)
    if parts is not None and mountinfo is not None:
        resolved = _resolve_cgroup_mount(mountinfo, parts)
        if resolved is not None:
            root, parts = resolved
        else:
            parts = None
    empty = {
        "detected": False, "cpu_quota_cores": None, "cpuset_logical": None,
        "memory_available_bytes": None, "memory_current_bytes": None,
        "memory_high_bytes": None, "memory_max_bytes": None, "scope": "unknown",
    }
    if _try_read(read_text, root / "cgroup.controllers") is None:
        _provenance(
            provenance_records, "cgroup_v2", "cgroup.controllers", "unavailable"
        )
        _warning(warning_records, "CGROUP_V2_UNAVAILABLE", "cgroup",
                 "cgroup v2 limits are unavailable; cgroup v1 and hidden limits are not measured.")
        return empty

    if parts is None:
        _warning(
            warning_records,
            "CGROUP_MEMBERSHIP_UNKNOWN",
            "cgroup",
            "cgroup v2 was detected but current membership could not be parsed.",
        )
        return {**empty, "detected": True}
    current = root.joinpath(*parts)
    if _try_read(read_text, current / "cgroup.controllers") is None:
        _warning(warning_records, "CGROUP_CURRENT_UNAVAILABLE", "cgroup",
                 "Current cgroup could not be read; visible root limits were not substituted.")
        return {**empty, "detected": True}
    chain: list[Path] = []
    cursor = current
    for _ in range(MAX_CGROUP_LEVELS):
        chain.append(cursor)
        if cursor == root:
            break
        parent = cursor.parent
        if parent == cursor or (parent != root and root not in parent.parents):
            break
        cursor = parent
    else:
        _warning(
            warning_records,
            "CGROUP_DEPTH_BOUNDED",
            "cgroup",
            "cgroup ancestor traversal reached its safety bound.",
        )

    quota_candidates: list[float] = []
    memory_max_candidates: list[int] = []
    memory_high_candidates: list[int] = []
    memory_available_candidates: list[int] = []
    current_memory: int | None = None

    for index, directory in enumerate(chain):
        cpu_max_text = _try_read(read_text, directory / "cpu.max")
        if cpu_max_text is not None:
            quota = _parse_cpu_max(cpu_max_text)
            if quota is not None:
                quota_candidates.append(quota)
            elif not re.fullmatch(r"max\s+[1-9][0-9]*", cpu_max_text.strip()):
                _warning(warning_records, "CGROUP_CPU_MAX_INVALID", "cgroup",
                         "A cgroup CPU quota could not be interpreted.")

        memory_max_text = _try_read(read_text, directory / "memory.max")
        memory_current_text = _try_read(read_text, directory / "memory.current")
        memory_high_text = _try_read(read_text, directory / "memory.high")
        memory_current = _bounded_nonnegative(memory_current_text)
        if index == 0:
            current_memory = memory_current
        memory_max = (
            None
            if memory_max_text is None or memory_max_text.strip() == "max"
            else _bounded_nonnegative(memory_max_text)
        )
        memory_high = (
            None
            if memory_high_text is None or memory_high_text.strip() == "max"
            else _bounded_nonnegative(memory_high_text)
        )
        if memory_max is not None:
            memory_max_candidates.append(memory_max)
            if memory_current is not None:
                memory_available_candidates.append(max(0, memory_max - memory_current))
        if memory_high is not None:
            memory_high_candidates.append(memory_high)
        for text, parsed in ((memory_max_text, memory_max), (memory_high_text, memory_high)):
            if text is not None and text.strip() != "max" and parsed is None:
                _warning(warning_records, "CGROUP_MEMORY_LIMIT_INVALID", "cgroup",
                         "A cgroup memory boundary could not be interpreted.")
        if memory_max is not None and memory_current is None:
            _warning(warning_records, "CGROUP_MEMORY_USAGE_UNKNOWN", "cgroup",
                     "A finite memory limit has unknown usage; remaining memory is only an upper bound.")

    cpuset_text = _try_read(read_text, current / "cpuset.cpus.effective")
    cpuset_count = parse_cpu_list(cpuset_text) if cpuset_text else None
    if cpuset_text and cpuset_count is None:
        _warning(
            warning_records,
            "CGROUP_CPUSET_PARSE_FAILED",
            "cgroup",
            "cpuset.cpus.effective had an unexpected bounded value.",
        )

    _provenance(provenance_records, "cgroup_v2", "procfs_and_cgroupfs", "ok")
    return {
        "detected": True,
        "cpu_quota_cores": min(quota_candidates) if quota_candidates else None,
        "cpuset_logical": cpuset_count,
        "memory_available_bytes": (
            min(memory_available_candidates)
            if memory_available_candidates
            else None
        ),
        "memory_current_bytes": current_memory,
        "memory_high_bytes": (
            min(memory_high_candidates) if memory_high_candidates else None
        ),
        "memory_max_bytes": (
            min(memory_max_candidates) if memory_max_candidates else None
        ),
        "scope": "non_root" if parts else "root",
    }


def _parse_slurm_count(value: str | None) -> int | None:
    if value is None or not 0 < len(value) <= 128:
        return None
    stripped = value.strip()
    if stripped.isdigit():
        count = int(stripped)
        return count if 0 <= count <= 1_000_000 else None
    match = re.fullmatch(r"(?:[A-Za-z0-9_.+-]+:)+(\d+)", stripped)
    if match:
        count = int(match.group(1))
        return count if count <= 1_000_000 else None
    return None


def _parse_slurm_memory(value: str | None) -> int | None:
    if value is None or not 0 < len(value) <= 128:
        return None
    match = re.fullmatch(r"\s*(\d+)\s*([KkMmGgTt]?)\s*", value)
    if not match:
        return None
    amount = int(match.group(1))
    if amount == 0:
        return None
    suffix = match.group(2).upper()
    multiplier = {"K": 1024, "M": MIB, "G": GIB, "T": 1024**4, "": MIB}[suffix]
    result = amount * multiplier
    return result if result <= MAX_BYTES else None


def _parse_first_repeated_count(value: str | None) -> int | None:
    return _parse_node_count(value, 0)


def _parse_node_count(value: str | None, node_index: int | None) -> int | None:
    """Resolve compressed Slurm node counts without expanding the list."""
    if value is None or not value or len(value) > 4096:
        return None
    groups = []
    for token in value.split(","):
        match = re.fullmatch(r"\s*(\d+)(?:\(x(\d+)\))?\s*", token)
        if not match:
            return None
        count, repeats = int(match.group(1)), int(match.group(2) or 1)
        if count > 1_000_000 or not 1 <= repeats <= 1_000_000:
            return None
        groups.append((count, repeats))
    if node_index is None:
        counts = {count for count, _ in groups}
        return next(iter(counts)) if len(counts) == 1 else None
    for count, repeats in groups:
        if node_index < repeats:
            return count
        node_index -= repeats
    return None


def detect_scheduler(
    environ: Mapping[str, str],
    *,
    warnings: list[dict[str, str]] | None = None,
    provenance: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Interpret only an allowlist of Slurm allocation variables."""
    warning_records = warnings if warnings is not None else []
    provenance_records = provenance if provenance is not None else []
    present = {
        key: environ[key]
        for key in SLURM_ENV_KEYS
        if key in environ and isinstance(environ[key], str)
    }
    detected = bool(present)
    if not detected:
        _provenance(provenance_records, "scheduler", "named_slurm_environment", "absent")
        return {
            "allocation": {
                "cpu_per_process": None,
                "cpus_on_node": None,
                "gpus_per_process": None,
                "gpus_on_node": None,
                "memory_effective_bytes": None,
                "memory_scope": None,
                "tasks": None,
            },
            "detected": False,
            "enforcement": "not_applicable",
            "fields_read": [],
            "kind": None,
        }

    cpus_per_task = _parse_slurm_count(present.get("SLURM_CPUS_PER_TASK"))
    cpus_on_node = _parse_slurm_count(present.get("SLURM_CPUS_ON_NODE"))
    tasks = _parse_slurm_count(present.get("SLURM_NTASKS"))
    node_index = _parse_slurm_count(present.get("SLURM_NODEID"))
    tasks_per_node = _parse_node_count(present.get("SLURM_TASKS_PER_NODE"), node_index)
    if "SLURM_TASKS_PER_NODE" not in present:
        tasks_per_node = _parse_slurm_count(present.get("SLURM_NTASKS_PER_NODE"))
    first_job_cpus = _parse_first_repeated_count(
        present.get("SLURM_JOB_CPUS_PER_NODE")
    )
    cpu_per_process = cpus_per_task
    if cpu_per_process is None and cpus_on_node is not None and tasks_per_node == 1:
        cpu_per_process = cpus_on_node

    memory_per_cpu = _parse_slurm_memory(present.get("SLURM_MEM_PER_CPU"))
    memory_per_node = _parse_slurm_memory(present.get("SLURM_MEM_PER_NODE"))
    memory_effective: int | None = None
    memory_scope: str | None = None
    if memory_per_cpu is not None and cpu_per_process is not None:
        memory_effective = min(MAX_BYTES, memory_per_cpu * cpu_per_process)
        memory_scope = "per_task_from_per_cpu"
    elif memory_per_node is not None:
        memory_effective = memory_per_node
        memory_scope = "shared_per_node"
        if tasks_per_node is None or tasks_per_node > 1:
            _warning(
                warning_records,
                "SLURM_MEMORY_SHARED",
                "scheduler",
                "Slurm per-node memory is shared; it is only an upper bound for this process.",
                severity="info",
            )

    gpus_per_task = _parse_slurm_count(present.get("SLURM_GPUS_PER_TASK"))
    gpus_on_node = _parse_slurm_count(present.get("SLURM_GPUS_ON_NODE"))
    requested_gpus = _parse_slurm_count(present.get("SLURM_GPUS"))

    _warning(
        warning_records,
        "SLURM_ENFORCEMENT_UNKNOWN",
        "scheduler",
        "Allocation variables do not prove task affinity or cgroup enforcement.",
        severity="info",
    )
    if cpus_per_task is None and cpus_on_node is not None and tasks_per_node != 1:
        _warning(
            warning_records,
            "SLURM_CPU_SCOPE_SHARED",
            "scheduler",
            "Node CPU allocation was not treated as a per-process limit.",
            severity="info",
        )
    _provenance(provenance_records, "scheduler", "named_slurm_environment", "ok")
    return {
        "allocation": {
            "cpu_per_process": cpu_per_process,
            "cpus_on_node": cpus_on_node,
            "first_job_cpus_per_node": first_job_cpus,
            "gpus_per_process": gpus_per_task,
            "gpus_on_node": gpus_on_node,
            "gpus_requested": requested_gpus,
            "memory_effective_bytes": memory_effective,
            "memory_scope": memory_scope,
            "tasks": tasks,
            "tasks_per_node": tasks_per_node,
        },
        "detected": True,
        "enforcement": "unknown",
        "fields_read": sorted(present),
        "kind": "slurm",
    }


def _effective_cpu(
    host: Mapping[str, int | None],
    process: Mapping[str, int | None],
    cgroup: Mapping[str, Any],
    scheduler: Mapping[str, Any],
) -> dict[str, Any]:
    candidates: list[tuple[str, float]] = []
    for source, value in (
        ("host_logical", host.get("logical")),
        ("process_affinity", process.get("affinity_logical")),
        ("python_process_count", process.get("python_available_logical")),
        ("cgroup_cpuset", cgroup.get("cpuset_logical")),
        ("cgroup_quota", cgroup.get("cpu_quota_cores")),
        (
            "scheduler_per_process",
            scheduler.get("allocation", {}).get("cpu_per_process"),
        ),
    ):
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            candidates.append((source, float(value)))
    if not candidates:
        return {
            "capacity_cores": None,
            "limiting_sources": [],
            "worker_ceiling": 1,
        }
    capacity = min(value for _, value in candidates)
    limiting = sorted(
        source for source, value in candidates if abs(value - capacity) < 1e-9
    )
    return {
        "capacity_cores": round(capacity, 6),
        "limiting_sources": limiting,
        "worker_ceiling": max(1, min(1024, math.floor(capacity))),
    }


def _parse_linux_meminfo(payload: str) -> dict[str, int | None]:
    values: dict[str, int] = {}
    for line in payload.splitlines():
        match = re.fullmatch(r"([A-Za-z_()]+):\s+(\d+)\s+kB", line.strip())
        if match:
            values[match.group(1)] = int(match.group(2)) * 1024
    return {
        "available": values.get("MemAvailable"),
        "swap_free": values.get("SwapFree"),
        "swap_total": values.get("SwapTotal"),
        "total": values.get("MemTotal"),
    }


def _detect_memory(
    *,
    system: str,
    machine: str,
    psutil_module: Any | None,
    mac_sysctl: Mapping[str, Any],
    cgroup: Mapping[str, Any],
    scheduler: Mapping[str, Any],
    read_text: Callable[[Path], str],
    warnings: list[dict[str, str]],
    provenance: list[dict[str, str]],
) -> dict[str, Any]:
    host_total: int | None = None
    host_available: int | None = None
    swap_total: int | None = None
    swap_free: int | None = None
    if psutil_module is not None:
        try:
            memory = psutil_module.virtual_memory()
            host_total = _bounded_nonnegative(memory.total)
            host_available = _bounded_nonnegative(memory.available)
            _provenance(provenance, "memory.host", "psutil.virtual_memory", "ok")
        except (AttributeError, OSError, RuntimeError, ValueError,
                getattr(psutil_module, "Error", OSError)):
            pass
        try:
            swap = psutil_module.swap_memory()
            swap_total = _bounded_nonnegative(swap.total)
            swap_free = _bounded_nonnegative(swap.free)
            _provenance(provenance, "memory.swap", "psutil.swap_memory", "ok")
        except (AttributeError, OSError, RuntimeError, ValueError,
                getattr(psutil_module, "Error", OSError)):
            pass

    if system == "Linux" and (host_total is None or host_available is None):
        payload = _try_read(read_text, Path("/proc/meminfo"))
        if payload:
            parsed = _parse_linux_meminfo(payload)
            host_total = host_total or parsed["total"]
            host_available = (
                host_available
                if host_available is not None
                else parsed["available"]
            )
            swap_total = swap_total if swap_total is not None else parsed["swap_total"]
            swap_free = swap_free if swap_free is not None else parsed["swap_free"]
            _provenance(provenance, "memory.host", "proc_meminfo", "ok")
    if system == "Darwin" and host_total is None:
        candidate = mac_sysctl.get("memory")
        if isinstance(candidate, int) and candidate > 0:
            host_total = candidate
            _provenance(provenance, "memory.host.total", "sysctl", "ok")
    if host_total is None:
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            candidate = pages * page_size
            if 0 < candidate <= MAX_BYTES:
                host_total = candidate
                _provenance(provenance, "memory.host.total", "os.sysconf", "ok")
        except (AttributeError, OSError, TypeError, ValueError):
            pass

    if host_total is None:
        _warning(
            warnings,
            "HOST_MEMORY_TOTAL_UNKNOWN",
            "memory",
            "Host memory total could not be determined.",
        )
    if host_available is None:
        _warning(
            warnings,
            "HOST_MEMORY_AVAILABLE_UNKNOWN",
            "memory",
            "Host available memory could not be determined without an allocation probe.",
            severity="info",
        )

    limit_candidates: list[tuple[str, int]] = []
    available_candidates: list[tuple[str, int]] = []
    for source, value in (
        ("host_total", host_total),
        ("cgroup_memory_max", cgroup.get("memory_max_bytes")),
        (
            "scheduler_memory",
            scheduler.get("allocation", {}).get("memory_effective_bytes"),
        ),
    ):
        if isinstance(value, int) and value >= 0:
            limit_candidates.append((source, value))
    for source, value in (
        ("host_available", host_available),
        ("cgroup_memory_remaining", cgroup.get("memory_available_bytes")),
        (
            "scheduler_memory_upper_bound",
            scheduler.get("allocation", {}).get("memory_effective_bytes"),
        ),
    ):
        if isinstance(value, int) and value >= 0:
            available_candidates.append((source, value))

    effective_limit = (
        min(value for _, value in limit_candidates) if limit_candidates else None
    )
    effective_available = (
        min(value for _, value in available_candidates)
        if available_candidates
        else None
    )
    if (
        effective_limit is not None
        and effective_available is not None
        and effective_available > effective_limit
    ):
        effective_available = effective_limit
    limiting_sources = (
        sorted(
            source
            for source, value in limit_candidates
            if value == effective_limit
        )
        if effective_limit is not None
        else []
    )
    available_sources = (
        sorted(
            source
            for source, value in available_candidates
            if value == effective_available
        )
        if effective_available is not None
        else []
    )
    unified = system == "Darwin" and (
        machine.lower() in {"arm64", "aarch64"}
        or str(mac_sysctl.get("brand", "")).startswith("Apple ")
    )
    return {
        "cgroup_v2": {
            "available_bytes": cgroup.get("memory_available_bytes"),
            "current_bytes": cgroup.get("memory_current_bytes"),
            "high_bytes": cgroup.get("memory_high_bytes"),
            "max_bytes": cgroup.get("memory_max_bytes"),
        },
        "effective": {
            "available_bytes": effective_available,
            "available_limiting_sources": available_sources,
            "hard_limit_bytes": effective_limit,
            "hard_limit_sources": limiting_sources,
            "pressure_threshold_bytes": cgroup.get("memory_high_bytes"),
        },
        "host": {
            "available_bytes": host_available,
            "total_bytes": host_total,
        },
        "model": "unified_cpu_gpu" if unified else "system_ram",
        "swap": {"free_bytes": swap_free, "total_bytes": swap_total},
    }


def _detect_disk(
    warnings: list[dict[str, str]],
    provenance: list[dict[str, str]],
) -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(Path.cwd())
        total = _bounded_nonnegative(usage.total)
        free = _bounded_nonnegative(usage.free)
        if total is None or free is None or free > total:
            raise ValueError("invalid bounded disk values")
        _provenance(provenance, "disk", "shutil.disk_usage", "ok")
    except (OSError, ValueError):
        _warning(
            warnings,
            "DISK_CAPACITY_UNKNOWN",
            "disk",
            "Working filesystem capacity could not be read.",
        )
        _provenance(provenance, "disk", "shutil.disk_usage", "unavailable")
        return {
            "capacity_bytes": None,
            "free_bytes": None,
            "scope": "working_filesystem_path_redacted",
            "user_available_bytes": None,
            "writable": None,
            "writability_check": "not_performed",
        }

    user_available = free
    if hasattr(os, "statvfs"):
        try:
            statvfs = os.statvfs(Path.cwd())
            candidate = _bounded_nonnegative(
                statvfs.f_bavail * statvfs.f_frsize
            )
            filesystem_free = _bounded_nonnegative(statvfs.f_bfree * statvfs.f_frsize)
            if filesystem_free is not None and filesystem_free <= total:
                free = filesystem_free
            if candidate is not None:
                user_available = candidate
                _provenance(
                    provenance, "disk.user_available", "os.statvfs", "ok"
                )
        except (AttributeError, OSError, TypeError, ValueError):
            pass
    writable = os.access(Path.cwd(), os.W_OK)
    if not writable:
        _warning(
            warnings,
            "WORKING_DIRECTORY_NOT_WRITABLE",
            "disk",
            "The working directory failed the non-writing access check.",
        )
    return {
        "capacity_bytes": total,
        "free_bytes": free,
        "scope": "working_filesystem_path_redacted",
        "user_available_bytes": max(0, min(free, user_available)),
        "writable": bool(writable),
        "writability_check": "os_access_only_no_write_probe",
    }


def _mib_to_bytes(value: str) -> int | None:
    try:
        amount = float(value)
    except ValueError:
        return None
    if not math.isfinite(amount) or not 0 <= amount <= MAX_BYTES / MIB:
        return None
    result = round(amount * MIB)
    return result if result <= MAX_BYTES else None


def parse_nvidia_csv(payload: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    try:
        rows = csv.reader(io.StringIO(payload))
        for row in rows:
            if len(row) not in {5, 6}:
                continue
            index = _bounded_nonnegative(row[0])
            if index is None or index > 4096:
                continue
            devices.append(
                {
                    "backend_candidate": "cuda",
                    "compute_capability": (
                        _safe_text(row[5], 16) if len(row) == 6 else None
                    ),
                    "device_class": "gpu",
                    "device_permission": "not_tested",
                    "driver_version": _safe_text(row[4], 64),
                    "local_index": index,
                    "management_query": "visible",
                    "memory": {
                        "dedicated_free_bytes": _mib_to_bytes(row[3].strip()),
                        "dedicated_total_bytes": _mib_to_bytes(row[2].strip()),
                        "model": "dedicated",
                    },
                    "name": _safe_text(row[1]) or "NVIDIA GPU",
                    "runtime_compatibility": "not_tested",
                    "vendor": "nvidia",
                }
            )
    except csv.Error:
        return []
    return sorted(devices, key=lambda item: item["local_index"])


def _recursive_scalar(
    value: Any,
    accepted_keys: set[str],
) -> tuple[str, Any] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
            if normalized in accepted_keys and isinstance(child, (str, int, float)):
                return normalized, child
        for child in value.values():
            found = _recursive_scalar(child, accepted_keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _recursive_scalar(child, accepted_keys)
            if found is not None:
                return found
    return None


def _amd_entries(data: Any) -> list[tuple[int, dict[str, Any]]]:
    entries: list[tuple[int, dict[str, Any]]] = []
    if isinstance(data, list):
        for index, item in enumerate(data):
            if isinstance(item, dict) and (
                "gpu" in {str(key).lower() for key in item}
                or "asic" in {str(key).lower() for key in item}
            ):
                gpu_value = next(
                    (
                        value
                        for key, value in item.items()
                        if str(key).lower() == "gpu"
                    ),
                    index,
                )
                gpu_index = _bounded_nonnegative(gpu_value)
                entries.append((gpu_index if gpu_index is not None else index, item))
    elif isinstance(data, dict):
        for key, item in data.items():
            normalized = re.sub(
                r"[^a-z0-9]+", "_", str(key).lower()
            ).strip("_")
            if normalized in {"gpu_data", "gpu_devices", "gpus"}:
                entries.extend(_amd_entries(item))
        for key, item in data.items():
            match = re.fullmatch(r"(?:card|gpu)\s*(\d+)", str(key), re.IGNORECASE)
            if match and isinstance(item, dict):
                entries.append((int(match.group(1)), item))
        if not entries and "gpu" in {str(key).lower() for key in data}:
            gpu_value = next(
                value for key, value in data.items() if str(key).lower() == "gpu"
            )
            if not isinstance(gpu_value, (dict, list)):
                gpu_index = _bounded_nonnegative(gpu_value)
                entries.append((gpu_index or 0, data))
    deduplicated: dict[int, dict[str, Any]] = {}
    for index, entry in entries:
        deduplicated.setdefault(index, entry)
    return sorted(deduplicated.items())


def _amd_memory_bytes(entry: Mapping[str, Any], *, in_vram: bool = False) -> int | None:
    for key, value in entry.items():
        normalized = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
        if (
            ("vram" in normalized or in_vram)
            and ("total" in normalized or "size" in normalized)
        ):
            # AMD SMI JSON uses SIZE: {value: ..., unit: MB}; legacy ROCm
            # SMI reports a flat "VRAM Total Memory (B)" integer string.
            if isinstance(value, dict):
                fields = {str(key).lower(): item for key, item in value.items()}
                raw = fields.get("value")
                unit_context = str(fields.get("unit", "")).lower()
            else:
                raw = value
                unit_context = f"{normalized} {str(value).lower()}"
            match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:[A-Za-z]+)?\s*", str(raw))
            if not match:
                continue
            amount = float(match.group(1))
            if not math.isfinite(amount):
                continue
            if "gib" in unit_context or "gb" in unit_context:
                multiplier = GIB
            elif "mib" in unit_context or "mb" in unit_context:
                multiplier = MIB
            elif "byte" in unit_context or unit_context == "b" or normalized.endswith("_b"):
                multiplier = 1
            else:
                continue
            if amount > MAX_BYTES / multiplier:
                continue
            result = round(amount * multiplier)
            if 0 <= result <= MAX_BYTES:
                return result
        if isinstance(value, dict):
            nested = _amd_memory_bytes(value, in_vram=in_vram or normalized == "vram")
            if nested is not None:
                return nested
    return None


def parse_amd_json(payload: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(payload)
        entries = _amd_entries(data)
    except (json.JSONDecodeError, RecursionError):
        return []
    devices: list[dict[str, Any]] = []
    name_keys = {
        "asic_market_name",
        "card_model",
        "card_series",
        "market_name",
        "product_name",
    }
    for index, entry in entries:
        try:
            found = _recursive_scalar(entry, name_keys)
            total_memory = _amd_memory_bytes(entry)
        except RecursionError:
            continue
        name = _safe_text(found[1]) if found else None
        devices.append(
            {
                "backend_candidate": "rocm",
                "compute_capability": None,
                "device_class": "gpu",
                "device_permission": "not_tested",
                "driver_version": None,
                "local_index": index,
                "management_query": "visible",
                "memory": {
                    "dedicated_free_bytes": None,
                    "dedicated_total_bytes": None,
                    "reported_total_bytes": total_memory,
                    "model": "device_reported_pool",
                },
                "name": name or "AMD GPU",
                "runtime_compatibility": "not_tested",
                "vendor": "amd",
            }
        )
    return sorted(devices, key=lambda item: item["local_index"])


def parse_apple_profiler_json(
    payload: str,
    *,
    machine: str,
) -> list[dict[str, Any]]:
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, RecursionError):
        return []
    entries = data.get("SPDisplaysDataType") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    devices: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        name = _safe_text(entry.get("sppci_model") or entry.get("_name"))
        vendor_text = f"{entry.get('spdisplays_vendor', '')} {name or ''}".lower()
        vendor = next((item for item in ("apple", "amd", "nvidia", "intel")
                       if item in vendor_text), "unknown")
        unified = vendor == "apple" and (
            machine.lower() in {"arm64", "aarch64"} or (name or "").startswith("Apple M")
        )
        core_value = (
            entry.get("sppci_cores")
            or entry.get("spdisplays_gpu_cores")
            or entry.get("_spdisplays_gpu_cores")
        )
        devices.append(
            {
                "backend_candidate": "metal",
                "compute_capability": None,
                "device_class": "integrated_gpu" if unified else "gpu",
                "device_permission": "not_tested",
                "driver_version": None,
                "gpu_cores": _bounded_nonnegative(core_value),
                "local_index": index,
                "management_query": "visible",
                "memory": {
                    "dedicated_free_bytes": None,
                    "dedicated_total_bytes": None,
                    "model": "unified" if unified else "unknown",
                },
                "name": name or "Apple display accelerator",
                "runtime_compatibility": "not_tested",
                "vendor": vendor,
            }
        )
    return devices


def _visibility_summary(environ: Mapping[str, str]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in ACCELERATOR_ENV_KEYS:
        if key not in environ:
            summary[key] = {
                "entry_count": None,
                "set": False,
                "state": "unset",
                "value_redacted": True,
            }
            continue
        raw = environ[key] if isinstance(environ[key], str) else ""
        if len(raw) > 4096:
            summary[key] = {
                "entry_count": None,
                "set": True,
                "state": "invalid_or_oversized",
                "value_redacted": True,
            }
            continue
        stripped = raw.strip()
        lowered = stripped.lower()
        if lowered in {"", "-1", "none", "void"}:
            state, count = "none", 0
        elif lowered == "all":
            state, count = "all", None
        else:
            entries = {
                item.strip() for item in stripped.split(",") if item.strip()
            }
            state = "restricted" if entries else "none"
            count = min(len(entries), 4096)
        summary[key] = {
            "entry_count": count,
            "set": True,
            "state": state,
            "value_redacted": True,
        }
    return summary


def _accelerator_upper_bounds(
    devices: Sequence[Mapping[str, Any]],
    visibility: Mapping[str, Mapping[str, Any]],
    scheduler: Mapping[str, Any],
) -> dict[str, int | None]:
    result: dict[str, int | None] = {}
    scheduler_count = scheduler.get("allocation", {}).get("gpus_per_process")
    if scheduler_count is None:
        scheduler_count = scheduler.get("allocation", {}).get("gpus_on_node")
    environment_keys = {
        "cuda": ("CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES"),
        "rocm": ("ROCR_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES", "CUDA_VISIBLE_DEVICES"),
        "metal": (),
    }
    for backend, keys in environment_keys.items():
        query_count = sum(
            1 for device in devices if device.get("backend_candidate") == backend
        )
        if query_count == 0:
            result[backend] = None
            continue
        limits = [query_count]
        if isinstance(scheduler_count, int):
            limits.append(scheduler_count)
        for key in keys:
            item = visibility.get(key, {})
            if item.get("state") == "none":
                limits.append(0)
            elif (
                item.get("state") == "restricted"
                and isinstance(item.get("entry_count"), int)
            ):
                limits.append(item["entry_count"])
        result[backend] = min(limits)
    return result


def _record_probe_failure(
    result: Mapping[str, Any],
    *,
    code: str,
    component: str,
    tool: str,
    warnings: list[dict[str, str]],
    provenance: list[dict[str, str]],
) -> None:
    status = str(result.get("status", "error"))
    _provenance(provenance, component, tool, status)
    if status != "not_found":
        _warning(
            warnings,
            code,
            component,
            f"{tool} read-only query did not complete successfully ({status}).",
            severity="info" if status in {"start_error", "error"} else "warning",
        )


def _detect_accelerators(
    *,
    system: str,
    machine: str,
    environ: Mapping[str, str],
    scheduler: Mapping[str, Any],
    run_command: Callable[..., dict[str, Any]],
    warnings: list[dict[str, str]],
    provenance: list[dict[str, str]],
) -> dict[str, Any]:
    devices: list[dict[str, Any]] = []

    nvidia = run_command(NVIDIA_QUERY, timeout=4.0)
    nvidia_devices = parse_nvidia_csv(nvidia.get("stdout", "")) if nvidia["status"] == "ok" else []
    if nvidia["status"] == "error":
        fallback = run_command(NVIDIA_QUERY_FALLBACK, timeout=4.0)
        if fallback["status"] == "ok":
            nvidia = fallback
            nvidia_devices = parse_nvidia_csv(fallback.get("stdout", ""))
    if nvidia["status"] == "ok":
        _provenance(provenance, "accelerators.nvidia", "nvidia-smi", "ok")
        if nvidia.get("stdout", "").strip() and not nvidia_devices:
            _warning(
                warnings,
                "NVIDIA_OUTPUT_PARSE_FAILED",
                "accelerators",
                "nvidia-smi returned an unexpected bounded CSV response.",
            )
    else:
        _record_probe_failure(
            nvidia,
            code="NVIDIA_QUERY_FAILED",
            component="accelerators.nvidia",
            tool="nvidia-smi",
            warnings=warnings,
            provenance=provenance,
        )
    devices.extend(nvidia_devices)

    amd = run_command(AMD_SMI_QUERY, timeout=4.0)
    amd_devices = parse_amd_json(amd.get("stdout", "")) if amd["status"] == "ok" else []
    amd_tool = "amd-smi"
    if not amd_devices and amd["status"] in {"not_found", "error", "start_error"}:
        amd = run_command(ROCM_SMI_QUERY, timeout=4.0)
        amd_tool = "rocm-smi"
        amd_devices = parse_amd_json(amd.get("stdout", "")) if amd["status"] == "ok" else []
    if amd["status"] == "ok":
        _provenance(provenance, "accelerators.amd", amd_tool, "ok")
        if amd.get("stdout", "").strip() and not amd_devices:
            _warning(
                warnings,
                "AMD_OUTPUT_PARSE_FAILED",
                "accelerators",
                f"{amd_tool} returned an unexpected bounded JSON response.",
            )
    else:
        _record_probe_failure(
            amd,
            code="AMD_QUERY_FAILED",
            component="accelerators.amd",
            tool=amd_tool,
            warnings=warnings,
            provenance=provenance,
        )
    devices.extend(amd_devices)

    if system == "Darwin":
        apple = run_command(APPLE_DISPLAY_QUERY, timeout=5.0)
        apple_devices = (
            parse_apple_profiler_json(apple.get("stdout", ""), machine=machine)
            if apple["status"] == "ok"
            else []
        )
        if apple["status"] == "ok":
            _provenance(
                provenance, "accelerators.apple", "system_profiler", "ok"
            )
        else:
            _record_probe_failure(
                apple,
                code="APPLE_ACCELERATOR_QUERY_FAILED",
                component="accelerators.apple",
                tool="system_profiler",
                warnings=warnings,
                provenance=provenance,
            )
        if (
            not apple_devices
            and machine.lower() in {"arm64", "aarch64"}
        ):
            apple_devices = [
                {
                    "backend_candidate": "metal",
                    "compute_capability": None,
                    "device_class": "integrated_gpu",
                    "device_permission": "not_tested",
                    "driver_version": None,
                    "gpu_cores": None,
                    "local_index": 0,
                    "management_query": "inferred_from_apple_silicon_platform",
                    "memory": {
                        "dedicated_free_bytes": None,
                        "dedicated_total_bytes": None,
                        "model": "unified",
                    },
                    "name": "Apple silicon integrated GPU",
                    "runtime_compatibility": "not_tested",
                    "vendor": "apple",
                }
            ]
        devices.extend(apple_devices)

    devices.sort(
        key=lambda item: (
            str(item.get("backend_candidate")),
            int(item.get("local_index", 0)),
            str(item.get("name")),
        )
    )
    if len(devices) > MAX_DEVICES:
        devices = devices[:MAX_DEVICES]
        _warning(
            warnings,
            "ACCELERATOR_DEVICE_LIST_BOUNDED",
            "accelerators",
            f"Accelerator output was limited to {MAX_DEVICES} devices.",
        )
    visibility = _visibility_summary(environ)
    if devices:
        _warning(
            warnings,
            "ACCELERATOR_RUNTIME_NOT_TESTED",
            "accelerators",
            "Management visibility does not prove permission or framework/runtime compatibility.",
            severity="info",
        )
    counts = {
        backend: sum(
            1 for device in devices if device.get("backend_candidate") == backend
        )
        for backend in ("cuda", "metal", "rocm")
    }
    return {
        "candidate_counts": counts,
        "candidate_upper_bounds": _accelerator_upper_bounds(
            devices, visibility, scheduler
        ),
        "devices": devices,
        "runtime_usable_devices": None,
        "visibility_environment": visibility,
    }


def _container_context(
    *,
    cgroup: Mapping[str, Any],
    exists: Callable[[Path], bool] = Path.exists,
) -> dict[str, Any]:
    evidence: list[str] = []
    for marker, label in (
        (Path("/.dockerenv"), "docker_marker"),
        (Path("/run/.containerenv"), "containerenv_marker"),
    ):
        try:
            if exists(marker):
                evidence.append(label)
        except OSError:
            pass
    if cgroup.get("detected") and any(
        cgroup.get(key) is not None
        for key in ("cpu_quota_cores", "cpuset_logical", "memory_max_bytes")
    ):
        evidence.append("cgroup_limit")
    return {
        "detected": bool(
            {"docker_marker", "containerenv_marker"}.intersection(evidence)
        ),
        "evidence": sorted(evidence),
        "runtime": (
            "docker_or_compatible"
            if "docker_marker" in evidence
            else "oci_compatible"
            if "containerenv_marker" in evidence
            else None
        ),
    }


def _observed_at() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def collect_snapshot(
    *,
    skip_accelerators: bool = False,
    observed_at: str | None = None,
    environ: Mapping[str, str] | None = None,
    psutil_module: Any = _AUTO,
    read_text: Callable[[Path], str] = _read_bounded_text,
    run_command: Callable[..., dict[str, Any]] = _run_bounded_command,
) -> dict[str, Any]:
    """Collect one snapshot; individual probe failures remain warnings."""
    warnings: list[dict[str, str]] = []
    provenance: list[dict[str, str]] = []
    environment = os.environ if environ is None else environ
    system = _safe_text(platform.system(), 64) or "Unknown"
    machine = _safe_text(platform.machine(), 64) or "unknown"

    if psutil_module is _AUTO:
        psutil_module = _load_psutil(warnings, provenance)
    elif psutil_module is None:
        _provenance(provenance, "inventory.psutil", "injected", "unavailable")

    mac_sysctl: dict[str, Any] = {}
    if system == "Darwin":
        mac_sysctl = _mac_sysctl_values(run_command, warnings, provenance)
    host_cpu = _detect_cpu_inventory(
        system=system,
        psutil_module=psutil_module,
        mac_sysctl=mac_sysctl,
        read_text=read_text,
        warnings=warnings,
        provenance=provenance,
    )
    process_cpu = _detect_process_cpu_count(
        psutil_module=psutil_module,
        warnings=warnings,
        provenance=provenance,
    )
    cgroup = (
        detect_cgroup_v2(
            read_text=read_text,
            warnings=warnings,
            provenance=provenance,
        )
        if system == "Linux"
        else {
            "detected": False,
            "cpu_quota_cores": None,
            "cpuset_logical": None,
            "memory_available_bytes": None,
            "memory_current_bytes": None,
            "memory_high_bytes": None,
            "memory_max_bytes": None,
            "scope": "not_applicable",
        }
    )
    scheduler = detect_scheduler(
        environment,
        warnings=warnings,
        provenance=provenance,
    )
    cpu = {
        "cgroup_v2": {
            "cpuset_logical": cgroup.get("cpuset_logical"),
            "quota_cores": cgroup.get("cpu_quota_cores"),
        },
        "effective": _effective_cpu(host_cpu, process_cpu, cgroup, scheduler),
        "host": host_cpu,
        "process": process_cpu,
    }
    memory = _detect_memory(
        system=system,
        machine=machine,
        psutil_module=psutil_module,
        mac_sysctl=mac_sysctl,
        cgroup=cgroup,
        scheduler=scheduler,
        read_text=read_text,
        warnings=warnings,
        provenance=provenance,
    )
    if skip_accelerators:
        accelerators = {
            "candidate_counts": {"cuda": 0, "metal": 0, "rocm": 0},
            "candidate_upper_bounds": {
                "cuda": None,
                "metal": None,
                "rocm": None,
            },
            "devices": [],
            "runtime_usable_devices": None,
            "visibility_environment": _visibility_summary(environment),
        }
        _provenance(provenance, "accelerators", "user_option", "skipped")
    else:
        accelerators = _detect_accelerators(
            system=system,
            machine=machine,
            environ=environment,
            scheduler=scheduler,
            run_command=run_command,
            warnings=warnings,
            provenance=provenance,
        )

    disk = _detect_disk(warnings, provenance)
    warnings.sort(
        key=lambda item: (
            item["component"],
            item["code"],
            item["message"],
        )
    )
    provenance.sort(
        key=lambda item: (item["component"], item["source"], item["status"])
    )
    completeness = (
        "partial"
        if any(item["severity"] == "warning" for item in warnings)
        else "complete_with_informational_notes"
        if warnings
        else "complete"
    )
    return {
        "accelerators": accelerators,
        "cgroup_v2": {
            "detected": cgroup.get("detected"),
            "scope": cgroup.get("scope"),
        },
        "completeness": completeness,
        "container": _container_context(cgroup=cgroup),
        "cpu": cpu,
        "disk": disk,
        "memory": memory,
        "observed_at": observed_at or _observed_at(),
        "platform": {
            "machine": machine,
            "python_version": _safe_text(platform.python_version(), 64) or "unknown",
            "system": system,
        },
        "privacy": {
            "absolute_paths_included": False,
            "environment_values_included": False,
            "hostnames_included": False,
            "identifiers_redacted_by_default": True,
        },
        "provenance": provenance,
        "scheduler": scheduler,
        "schema_version": SCHEMA_VERSION,
        "snapshot_kind": "effective_resource_snapshot",
        "warnings": warnings,
    }


def detect_all_resources(output_path: str | None = None) -> dict[str, Any]:
    """Compatibility API: collect a snapshot and optionally write it safely."""
    snapshot = collect_snapshot()
    if output_path is not None:
        emit_json(snapshot, output_path)
    return snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report host inventory and effective process limits as deterministic JSON"
        )
    )
    parser.add_argument(
        "--output",
        metavar="FILE.json",
        help=(
            "write a private JSON file in the current directory; default: stdout"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing explicit output file",
    )
    parser.add_argument(
        "--skip-accelerators",
        action="store_true",
        help="skip bounded accelerator management queries",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.force and not args.output:
        parser.error("--force requires --output")
    try:
        snapshot = collect_snapshot(skip_accelerators=args.skip_accelerators)
        emit_json(snapshot, args.output, force=args.force)
    except ResourceToolError as exc:
        return cli_error(parser, exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
