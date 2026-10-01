#!/usr/bin/env python3
"""Inventory bounded MAT/HDF5 metadata without deserializing object values."""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from _common import (
    CliError,
    bounded_int,
    checked_input,
    checked_root,
    emit_json,
    fail_json,
    relative_id,
    sha256_file,
)

TOOL = "inventory_mat_file"
HDF5_SIGNATURE = b"\x89HDF\r\n\x1a\n"
OBJECT_LIKE_CLASSES = {
    "cell",
    "function",
    "java",
    "object",
    "opaque",
    "struct",
    "table",
    "timetable",
}


def identify_header(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            prefix = handle.read(8192)
    except OSError as exc:
        raise CliError(f"cannot read MAT header: {path}") from exc
    signature_offset = next(
        (
            offset
            for offset in (0, 512, 1024, 2048, 4096)
            if prefix[offset : offset + 8] == HDF5_SIGNATURE
        ),
        None,
    )
    header = prefix[:128]
    if header.startswith(b"MATLAB 7.3 MAT-file"):
        kind = "matlab_v7_3_hdf5"
    elif header.startswith(b"MATLAB 5.0 MAT-file"):
        kind = "matlab_level5_v6_or_v7"
    elif signature_offset is not None:
        kind = "hdf5_not_confirmed_matlab_v7_3"
    elif prefix.startswith(b"\x80"):
        kind = "python_pickle_signature_refused"
    else:
        kind = "unknown_or_mat_v4"
    return {
        "detected_kind": kind,
        "hdf5_signature_offset": signature_offset,
        "matlab_text_header_present": header.startswith(b"MATLAB "),
    }


def _redacted_name(name: str, index: int, kind: str) -> dict[str, Any]:
    return {
        "id": f"{kind}-{index:06d}",
        "name_emitted": False,
        "name_sha256": hashlib.sha256(name.encode("utf-8", "surrogatepass")).hexdigest(),
    }


def scipy_inventory(
    path: Path, *, max_nodes: int
) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        from scipy import io as scipy_io
    except ImportError as exc:
        raise CliError(
            "SciPy is optional and not installed; use --backend header or "
            "install a pinned scipy in an approved environment"
        ) from exc
    try:
        entries = scipy_io.whosmat(str(path), appendmat=False)
    except Exception as exc:
        raise CliError(f"SciPy could not inventory MAT metadata: {exc}") from exc
    if len(entries) > max_nodes:
        raise CliError(f"MAT file has more than {max_nodes} variables")
    output: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, (name, shape, class_name) in enumerate(entries, start=1):
        class_text = str(class_name)
        record = {
            **_redacted_name(str(name), index, "variable"),
            "class": class_text,
            "object_like": class_text.casefold() in OBJECT_LIKE_CLASSES,
            "shape": [int(value) for value in shape],
            "values_loaded": False,
        }
        if record["object_like"]:
            warnings.append(
                f"{record['id']} has object-like class {class_text!r}; "
                "do not load without expert review"
            )
        output.append(record)
    return output, warnings


def hdf5_inventory(
    path: Path, *, max_nodes: int, max_depth: int
) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
    try:
        import h5py
    except ImportError as exc:
        raise CliError(
            "h5py is optional and not installed; use --backend header or "
            "install a pinned h5py in an approved environment"
        ) from exc

    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    link_counts: Counter[str] = Counter()
    seen_objects: set[int] = set()

    def append_record(path_name: str, kind: str, details: dict[str, Any]) -> None:
        if len(records) >= max_nodes:
            raise CliError(f"HDF5 object/link count exceeds {max_nodes}")
        records.append(
            {
                **_redacted_name(path_name, len(records) + 1, "hdf5-node"),
                "kind": kind,
                **details,
            }
        )

    def walk(group: Any, prefix: str, depth: int) -> None:
        if depth > max_depth:
            raise CliError(f"HDF5 group depth exceeds {max_depth}")
        try:
            names = sorted(group.keys())
        except Exception as exc:
            raise CliError(f"cannot enumerate HDF5 group metadata: {exc}") from exc
        for name in names:
            full_name = f"{prefix}/{name}" if prefix else f"/{name}"
            try:
                link = group.get(name, getlink=True)
            except Exception as exc:
                raise CliError(f"cannot inspect HDF5 link metadata: {exc}") from exc
            if isinstance(link, h5py.SoftLink):
                link_counts["soft"] += 1
                append_record(
                    full_name,
                    "soft_link",
                    {"followed": False, "target_emitted": False},
                )
                warnings.append("soft HDF5 link found and not followed")
                continue
            if isinstance(link, h5py.ExternalLink):
                link_counts["external"] += 1
                append_record(
                    full_name,
                    "external_link",
                    {"followed": False, "target_emitted": False},
                )
                warnings.append("external HDF5 link found and not followed")
                continue
            link_counts["hard"] += 1
            try:
                obj = group[name]
                object_key = hash(obj.id)
            except Exception as exc:
                raise CliError(f"cannot inspect HDF5 object metadata: {exc}") from exc
            attribute_names = sorted(str(key) for key in obj.attrs.keys())
            if len(attribute_names) > 1000:
                raise CliError("HDF5 object has more than 1000 attributes")
            base = {
                "attribute_count": len(attribute_names),
                "attribute_names_emitted": False,
                "attribute_name_hashes": [
                    hashlib.sha256(name.encode("utf-8")).hexdigest()
                    for name in attribute_names
                ],
                "hard_link_revisited": object_key in seen_objects,
                "values_loaded": False,
            }
            if isinstance(obj, h5py.Dataset):
                dtype_text = str(obj.dtype)
                if len(dtype_text) > 500:
                    dtype_text = dtype_text[:500] + "..."
                reference_dtype = h5py.check_dtype(ref=obj.dtype) is not None
                object_like = bool(reference_dtype or obj.dtype.kind == "O")
                append_record(
                    full_name,
                    "dataset",
                    {
                        **base,
                        "chunks": list(obj.chunks) if obj.chunks is not None else None,
                        "compression": obj.compression,
                        "dtype": dtype_text,
                        "object_like": object_like,
                        "shape": (
                            [int(value) for value in obj.shape]
                            if obj.shape is not None else None
                        ),
                        "null_dataspace": obj.shape is None,
                    },
                )
                if object_like:
                    warnings.append(
                        "HDF5 object/reference dtype found; values were not read"
                    )
                seen_objects.add(object_key)
            elif isinstance(obj, h5py.Group):
                append_record(full_name, "group", base)
                if object_key not in seen_objects:
                    seen_objects.add(object_key)
                    walk(obj, full_name, depth + 1)
            else:
                append_record(full_name, "unknown_hdf5_object", base)
                warnings.append("unknown HDF5 object type found")

    try:
        with h5py.File(path, "r") as handle:
            walk(handle, "", 0)
    except CliError:
        raise
    except Exception as exc:
        raise CliError(f"h5py could not inventory HDF5 metadata: {exc}") from exc
    return records, warnings, dict(sorted(link_counts.items()))


def inventory(args: argparse.Namespace) -> dict[str, Any]:
    root = checked_root(args.root)
    max_file_bytes = bounded_int(
        args.max_file_bytes,
        name="max_file_bytes",
        minimum=1,
        maximum=512 * 1024 * 1024,
    )
    max_nodes = bounded_int(
        args.max_nodes, name="max_nodes", minimum=1, maximum=100_000
    )
    max_depth = bounded_int(
        args.max_depth, name="max_depth", minimum=1, maximum=128
    )
    path = checked_input(
        args.input,
        root=root,
        suffixes={".mat"},
        max_bytes=max_file_bytes,
    )
    header = identify_header(path)
    warnings = [
        "Inventory is metadata triage, not a safety certificate; do not load "
        "untrusted MAT/HDF5 content."
    ]
    backend_used = "header"
    records: list[dict[str, Any]] = []
    link_counts: dict[str, int] = {}
    backend = args.backend
    if backend == "auto":
        backend = (
            "hdf5"
            if header["detected_kind"]
            in {"matlab_v7_3_hdf5", "hdf5_not_confirmed_matlab_v7_3"}
            else "scipy"
        )
    if backend == "scipy":
        if header["detected_kind"] in {
            "matlab_v7_3_hdf5",
            "hdf5_not_confirmed_matlab_v7_3",
        }:
            raise CliError("SciPy metadata backend is not used for HDF5/v7.3")
        records, extra = scipy_inventory(path, max_nodes=max_nodes)
        warnings.extend(extra)
        backend_used = "scipy.io.whosmat"
    elif backend == "hdf5":
        if header["hdf5_signature_offset"] is None:
            raise CliError("HDF5 signature was not found at a recognized userblock offset")
        records, extra, link_counts = hdf5_inventory(
            path, max_nodes=max_nodes, max_depth=max_depth
        )
        warnings.extend(extra)
        backend_used = "h5py-metadata"
    elif backend != "header":
        raise CliError(f"unsupported backend: {backend}")
    if header["detected_kind"] == "python_pickle_signature_refused":
        warnings.append(
            "Python pickle signature found under .mat suffix; never deserialize it"
        )
    object_like_count = sum(bool(record.get("object_like")) for record in records)
    return {
        "backend": backend_used,
        "deserializes_objects": False,
        "executes": False,
        "file": relative_id(path, root),
        "file_name_emitted": True,
        "file_sha256": sha256_file(path, max_bytes=max_file_bytes),
        "file_size_bytes": path.stat().st_size,
        "header": header,
        "hdf5_links": link_counts,
        "name_values_emitted": False,
        "network_accessed": False,
        "object_like_count": object_like_count,
        "ok": (
            header["detected_kind"] != "python_pickle_signature_refused"
            and object_like_count == 0
            and link_counts.get("external", 0) == 0
        ),
        "records": records,
        "records_count": len(records),
        "safe_to_load": False,
        "tool": TOOL,
        "values_loaded": False,
        "warnings": sorted(set(warnings)),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Inventory local MAT technical metadata without MATLAB, loadmat, "
            "pickle, dataset reads, or object deserialization. Header-only is default."
        )
    )
    result.add_argument("input", help="local .mat file")
    result.add_argument("--root", default=".", help="allowed local root")
    result.add_argument(
        "--backend",
        choices=("header", "auto", "scipy", "hdf5"),
        default="header",
        help="optional metadata backend; header is dependency-free and safest",
    )
    result.add_argument("--max-file-bytes", default=64 * 1024 * 1024)
    result.add_argument("--max-nodes", default=5000)
    result.add_argument("--max-depth", default=24)
    return result


def main() -> int:
    try:
        report = inventory(parser().parse_args())
        emit_json(report)
        return 0 if report["ok"] else 1
    except CliError as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
