#!/usr/bin/env python3
"""Summarize bounded FluidSim scalar and spectral diagnostics."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

try:
    from ._common import (
        MAX_FILES,
        MAX_RECORDS,
        MAX_TEXT_BYTES,
        ToolError,
        bounded_int,
        checked_input,
        checked_root,
        emit_json,
        fail_json,
        iter_local_files,
        relative_display,
        strict_json_loads,
    )
except ImportError:  # Direct script execution.
    from _common import (
        MAX_FILES,
        MAX_RECORDS,
        MAX_TEXT_BYTES,
        ToolError,
        bounded_int,
        checked_input,
        checked_root,
        emit_json,
        fail_json,
        iter_local_files,
        relative_display,
        strict_json_loads,
    )


TOOL = "fluidsim-budget-summary"
_ASSIGNMENT = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9_.-]{0,127})\s*=\s*"
    r"([-+]?(?:(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?|nan|inf(?:inity)?))\s*$",
    re.IGNORECASE,
)
_SPECTRAL_PREFIXES = (
    "budget",
    "diss",
    "flux",
    "forcing",
    "spectr",
    "transfer",
)
_HDF5_SUFFIXES = (".h5", ".hdf5", ".nc")


class OnlineStats:
    """Constant-memory finite scalar aggregation."""

    def __init__(self) -> None:
        self.count = 0
        self.first: float | None = None
        self.last: float | None = None
        self.minimum = math.inf
        self.maximum = -math.inf
        self.mean = 0.0
        self.nonfinite_count = 0

    def add(self, value: Any) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return
        try:
            number = float(value)
        except OverflowError:
            self.nonfinite_count += 1
            return
        if not math.isfinite(number):
            self.nonfinite_count += 1
            return
        if self.first is None:
            self.first = number
        self.last = number
        self.minimum = min(self.minimum, number)
        self.maximum = max(self.maximum, number)
        self.count += 1
        # Weighted form avoids overflowing a same-sign finite running sum.
        self.mean = self.mean * ((self.count - 1) / self.count) + number / self.count

    def report(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "first": self.first,
            "last": self.last,
            "max": self.maximum if self.count else None,
            "mean": self.mean if self.count and math.isfinite(self.mean) else None,
            "min": self.minimum if self.count else None,
            "nonfinite_count": self.nonfinite_count,
        }


def _iter_text(path: Path, *, max_records: int):
    if path.stat().st_size > MAX_TEXT_BYTES:
        raise ToolError("scalar diagnostic exceeds the text-size limit")
    consumed = 0
    with path.open("rb") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if line_number > max_records:
                raise ToolError("scalar diagnostic record limit exceeded")
            consumed += len(raw)
            if consumed > MAX_TEXT_BYTES or len(raw) > 1024**2:
                raise ToolError("scalar diagnostic line/byte limit exceeded")
            if b"\x00" in raw:
                raise ToolError("NUL byte in scalar diagnostic")
            try:
                yield line_number, raw.decode("utf-8").rstrip("\r\n")
            except UnicodeDecodeError as exc:
                raise ToolError("scalar diagnostic is not UTF-8") from exc


def summarize_scalar_file(path: Path, *, max_records: int) -> dict[str, Any]:
    metrics: dict[str, OnlineStats] = {}
    parsed_lines = 0
    json_lines = path.name.casefold().endswith(".json")
    for _, line in _iter_text(path, max_records=max_records):
        if not line.strip():
            continue
        if json_lines:
            record = strict_json_loads(line)
            if not isinstance(record, dict):
                raise ToolError("spatial_means JSON line must be an object")
            parsed_lines += 1
            for key, value in record.items():
                if not isinstance(key, str) or not re.fullmatch(
                    r"[A-Za-z][A-Za-z0-9_.-]{0,127}", key
                ):
                    continue
                metrics.setdefault(key, OnlineStats()).add(value)
        else:
            matches = [_ASSIGNMENT.fullmatch(part) for part in line.split(";") if part.strip()]
            if not matches or any(match is None for match in matches):
                continue
            parsed_lines += 1
            for match in matches:
                key, text = match.groups()
                metrics.setdefault(key, OnlineStats()).add(float(text))
        if len(metrics) > 1024:
            raise ToolError("scalar metric-count limit exceeded")
    return {
        "format": "json-lines" if json_lines else "FluidSim key-value text",
        "metrics": {
            key: metrics[key].report()
            for key in sorted(metrics)
            if metrics[key].count or metrics[key].nonfinite_count
        },
        "parsed_lines": parsed_lines,
        "raw_records_emitted": False,
        "averaging": "finite saved-sample mean, not time-weighted or budget closure",
    }


def _bounded_slice(shape: tuple[int, ...], maximum: int) -> tuple[Any, ...]:
    if not shape:
        return ()
    if len(shape) == 1:
        return (slice(0, min(shape[0], maximum)),)
    slices: list[Any] = [slice(max(0, shape[0] - 1), shape[0])]
    remaining = maximum
    for size in shape[1:]:
        take = min(size, max(1, remaining))
        slices.append(slice(0, take))
        remaining = max(1, remaining // max(1, take))
    return tuple(slices)


def _summarize_values(values: Any, *, complete_record: bool) -> dict[str, Any]:
    flat = values.reshape(-1)
    if flat.dtype.kind == "c":
        flat = abs(flat)
        statistic = "magnitude"
    else:
        statistic = "value"
    finite = flat[flat == flat]
    finite = finite[abs(finite) != math.inf]
    count = int(finite.size)

    def converted(operation: str) -> float | None:
        if not count:
            return None
        value = float(getattr(finite, operation)())
        return value if math.isfinite(value) else None

    return {
        "complete_latest_record": complete_record,
        "finite_values": count,
        "max": converted("max"),
        "mean": converted("mean"),
        "min": converted("min"),
        "sampled_values": int(flat.size),
        "statistic": statistic,
        "sum": converted("sum") if complete_record else None,
    }


def summarize_spectral_file(
    path: Path, *, max_datasets: int, max_values: int
) -> dict[str, Any]:
    try:
        import h5py  # Lazy optional dependency.
    except ImportError as exc:
        raise ToolError(
            "spectral summary requires optional h5py from the pinned environment"
        ) from exc

    results: dict[str, Any] = {}
    time_range = None
    external_links = 0
    try:
        with h5py.File(path, "r") as handle:
            times_link = handle.get("times", getlink=True)
            if isinstance(times_link, h5py.HardLink) and isinstance(handle["times"], h5py.Dataset):
                times = handle["times"]
                if times.is_virtual or times.external:
                    raise ToolError("external or virtual dataset storage is not read")
                if times.ndim == 1 and times.shape[0] and times.dtype.kind in "iuf":
                    time_range = [
                        float(times[0]),
                        float(times[times.shape[0] - 1]),
                    ]
                    if not all(math.isfinite(value) for value in time_range):
                        raise ToolError("spectral timestamps must be finite")
            stack = [(handle, "/")]
            seen: set[int] = set()
            while stack:
                group, prefix = stack.pop()
                try:
                    address = int(h5py.h5o.get_info(group.id).addr)
                except (AttributeError, TypeError, ValueError):
                    address = hash(group.id)
                if address in seen:
                    continue
                seen.add(address)
                for name in sorted(group.keys(), reverse=True):
                    link = group.get(name, getlink=True)
                    if isinstance(link, h5py.ExternalLink):
                        external_links += 1
                        continue
                    if isinstance(link, h5py.SoftLink):
                        continue
                    obj = group.get(name, getlink=False)
                    object_path = f"/{name}" if prefix == "/" else f"{prefix}/{name}"
                    if isinstance(obj, h5py.Group):
                        stack.append((obj, object_path))
                        continue
                    if not isinstance(obj, h5py.Dataset):
                        continue
                    leaf = name.casefold()
                    if (
                        obj.dtype.kind not in "iufc"
                        or not leaf.startswith(_SPECTRAL_PREFIXES)
                    ):
                        continue
                    if len(results) >= max_datasets:
                        raise ToolError("spectral dataset-count limit exceeded")
                    if obj.is_virtual or obj.external:
                        raise ToolError("external or virtual dataset storage is not read")
                    shape = tuple(int(size) for size in obj.shape)
                    if not shape or math.prod(shape) == 0:
                        continue
                    selection = _bounded_slice(shape, max_values)
                    values = obj[selection]
                    latest_record_size = (
                        math.prod(shape[1:]) if len(shape) > 1 else shape[0]
                    )
                    results[object_path[:300]] = {
                        "dtype": str(obj.dtype)[:100],
                        "shape": list(shape),
                        **_summarize_values(
                            values,
                            complete_record=latest_record_size <= max_values,
                        ),
                    }
    except OSError as exc:
        return {
            "datasets": {},
            "external_links_followed": False,
            "external_links_not_followed": external_links,
            "hdf5_readable": False,
            "message": str(exc)[:300],
            "time_range": None,
        }
    return {
        "datasets": dict(sorted(results.items())),
        "external_links_followed": False,
        "external_links_not_followed": external_links,
        "hdf5_readable": True,
        "time_range": time_range,
    }


def summarize(
    path: Path,
    *,
    root: Path,
    max_files: int,
    max_records: int,
    max_datasets: int,
    max_values: int,
) -> dict[str, Any]:
    files = iter_local_files(
        path, suffixes=None, max_files=max_files, recursive=True
    )
    scalar: list[dict[str, Any]] = []
    spectra: list[dict[str, Any]] = []
    for file_path in files:
        lowered = file_path.name.casefold()
        if lowered in {"spatial_means.txt", "spatial_means.json"}:
            scalar.append(
                {
                    "path": relative_display(file_path, root),
                    "summary": summarize_scalar_file(
                        file_path, max_records=max_records
                    ),
                }
            )
        elif lowered.endswith(_HDF5_SUFFIXES) and lowered.startswith(
            ("spectra", "spect_energy", "spectra_multidim")
        ):
            spectra.append(
                {
                    "path": relative_display(file_path, root),
                    "summary": summarize_spectral_file(
                        file_path,
                        max_datasets=max_datasets,
                        max_values=max_values,
                    ),
                }
            )
    return {
        "arrays_fully_loaded": False,
        "interpretation": (
            "Descriptive diagnostics only. Budget closure, conservation, spectral "
            "resolution, stationarity, and convergence require solver-aware checks."
        ),
        "network_used": False,
        "numerical_convergence_established": False,
        "ok": bool(scalar or spectra),
        "physical_validity_established": False,
        "scalar_outputs": scalar,
        "spectral_outputs": spectra,
        "tool": TOOL,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize bounded local spatial means and latest spectral/budget "
            "hyperslabs. Large arrays are never loaded in full."
        )
    )
    parser.add_argument("--path", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--max-files", type=int, default=128)
    parser.add_argument("--max-records", type=int, default=200_000)
    parser.add_argument("--max-datasets", type=int, default=256)
    parser.add_argument("--max-values-per-dataset", type=int, default=4_096)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        max_files = bounded_int(
            args.max_files, name="max_files", minimum=1, maximum=MAX_FILES
        )
        max_records = bounded_int(
            args.max_records,
            name="max_records",
            minimum=1,
            maximum=MAX_RECORDS,
        )
        max_datasets = bounded_int(
            args.max_datasets,
            name="max_datasets",
            minimum=1,
            maximum=10_000,
        )
        max_values = bounded_int(
            args.max_values_per_dataset,
            name="max_values_per_dataset",
            minimum=1,
            maximum=65_536,
        )
        root = checked_root(args.root)
        path = checked_input(args.path, root=root, kind="any")
        report = summarize(
            path,
            root=root,
            max_files=max_files,
            max_records=max_records,
            max_datasets=max_datasets,
            max_values=max_values,
        )
        emit_json(report)
        return 0 if report["ok"] else 2
    except (OSError, ToolError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    raise SystemExit(main())
