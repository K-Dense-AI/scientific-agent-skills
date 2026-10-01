#!/usr/bin/env python3
"""Bounded inspectors for JSON, NumPy containers, and HDF5 metadata."""

from __future__ import annotations

import itertools
import math
from pathlib import Path
from typing import Any

from _capabilities import preflight_npz
from _common import (
    MAX_JSON_BYTES,
    CliError,
    display_identifier,
    load_strict_json,
)
from _tabular import profile_json_structure


MAX_ARRAY_SAMPLE = 4096
MAX_HDF5_OBJECTS = 1000
MAX_HDF5_DEPTH = 16


def inspect_json(
    path: Path,
    *,
    reveal_identifiers: bool = False,
) -> dict[str, Any]:
    """Strictly parse bounded JSON and emit structure, never scalar values."""

    document = load_strict_json(path, max_bytes=MAX_JSON_BYTES)
    return profile_json_structure(
        document,
        reveal_identifiers=reveal_identifiers,
    )


def _dtype_report(
    dtype: Any,
    *,
    reveal_identifiers: bool,
) -> dict[str, Any]:
    fields = getattr(dtype, "fields", None)
    report: dict[str, Any] = {
        "kind": str(dtype.kind),
        "itemsize": int(dtype.itemsize),
        "byteorder": str(dtype.byteorder),
        "contains_python_objects": bool(dtype.hasobject),
        "structured": fields is not None,
    }
    if fields is not None:
        names = list(dtype.names or ())
        report["field_count"] = len(names)
        report["field_ids"] = [
            display_identifier(
                name,
                kind="field",
                reveal_identifiers=reveal_identifiers,
            )
            for name in names[:128]
        ]
        report["field_ids_truncated"] = len(names) > 128
    else:
        report["dtype"] = str(dtype)
    return report


def _sample_array(array: Any, np: Any) -> Any:
    size = int(array.size)
    if size <= MAX_ARRAY_SAMPLE:
        return np.asarray(array).reshape(-1)
    positions = np.linspace(
        0,
        size - 1,
        num=MAX_ARRAY_SAMPLE,
        dtype=np.int64,
    )
    # ndarray.flat indexes in C order without materializing a full C-order
    # copy of a Fortran-contiguous memory map.
    return np.asarray(array.flat[positions])


def _array_report(
    array: Any,
    np: Any,
    *,
    array_id: str | None,
    reveal_identifiers: bool,
) -> dict[str, Any]:
    if bool(array.dtype.hasobject):
        raise CliError("NumPy object arrays are not accepted because they require pickle")
    report: dict[str, Any] = {
        "shape": [int(value) for value in array.shape],
        "dimension_count": int(array.ndim),
        "element_count": int(array.size),
        "dtype": _dtype_report(
            array.dtype,
            reveal_identifiers=reveal_identifiers,
        ),
    }
    if array_id is not None:
        report["array_id"] = array_id
    if int(array.size) == 0:
        report["numeric_sample"] = {"sample_count": 0}
        return report
    if np.issubdtype(array.dtype, np.bool_):
        sample = _sample_array(array, np)
        report["boolean_sample"] = {
            "sample_count": int(sample.size),
            "true_count": int(np.count_nonzero(sample)),
            "sample_is_bounded": int(sample.size) < int(array.size),
        }
        return report
    if np.issubdtype(array.dtype, np.number):
        sample = _sample_array(array, np)
        if np.iscomplexobj(sample):
            finite = np.isfinite(sample.real) & np.isfinite(sample.imag)
            magnitudes = np.abs(sample[finite])
            report["numeric_sample"] = {
                "sample_count": int(sample.size),
                "finite_count": int(np.count_nonzero(finite)),
                "complex_values_summarized_by_magnitude": True,
                "magnitude_mean": (
                    float(np.mean(magnitudes)) if magnitudes.size else None
                ),
                "magnitude_minimum": (
                    float(np.min(magnitudes)) if magnitudes.size else None
                ),
                "magnitude_maximum": (
                    float(np.max(magnitudes)) if magnitudes.size else None
                ),
                "sample_is_bounded": int(sample.size) < int(array.size),
            }
        else:
            finite = np.isfinite(sample)
            finite_values = sample[finite]
            report["numeric_sample"] = {
                "sample_count": int(sample.size),
                "finite_count": int(np.count_nonzero(finite)),
                "nan_count": int(np.count_nonzero(np.isnan(sample)))
                if np.issubdtype(sample.dtype, np.inexact)
                else 0,
                "infinite_count": int(np.count_nonzero(np.isinf(sample)))
                if np.issubdtype(sample.dtype, np.inexact)
                else 0,
                "mean": (
                    float(np.mean(finite_values)) if finite_values.size else None
                ),
                "minimum": (
                    float(np.min(finite_values)) if finite_values.size else None
                ),
                "maximum": (
                    float(np.max(finite_values)) if finite_values.size else None
                ),
                "sample_is_bounded": int(sample.size) < int(array.size),
            }
    return report


def inspect_numpy(
    path: Path,
    *,
    suffix: str,
    reveal_identifiers: bool = False,
) -> dict[str, Any]:
    """Inspect NPY/NPZ with pickle disabled and bounded decompression."""

    try:
        import numpy as np
    except ImportError as exc:
        raise CliError(
            'optional dependency missing; install with: uv pip install "numpy==2.5.3"'
        ) from exc
    if suffix == ".npy":
        try:
            array = np.load(
                path,
                mmap_mode="r",
                allow_pickle=False,
                max_header_size=10_000,
            )
        except (OSError, ValueError, TypeError, MemoryError) as exc:
            raise CliError(
                "the NPY file could not be inspected safely; object arrays are rejected"
            ) from exc
        return {
            "profile_type": "numpy_npy_bounded_profile",
            "pickle_allowed": False,
            "array": _array_report(
                array,
                np,
                array_id=None,
                reveal_identifiers=reveal_identifiers,
            ),
            "raw_values_emitted": False,
        }
    if suffix != ".npz":
        raise CliError("the NumPy inspector received an unsupported suffix")
    preflight = preflight_npz(path)
    arrays: list[dict[str, Any]] = []
    try:
        with np.load(
            path,
            allow_pickle=False,
            max_header_size=10_000,
        ) as archive:
            for name in archive.files:
                array = archive[name]
                arrays.append(
                    _array_report(
                        array,
                        np,
                        array_id=display_identifier(
                            name,
                            kind="array",
                            reveal_identifiers=reveal_identifiers,
                        ),
                        reveal_identifiers=reveal_identifiers,
                    )
                )
                del array
    except (OSError, ValueError, TypeError, MemoryError) as exc:
        raise CliError(
            "the NPZ arrays could not be inspected safely; object arrays are rejected"
        ) from exc
    return {
        "profile_type": "numpy_npz_bounded_profile",
        "pickle_allowed": False,
        "archive_preflight": preflight,
        "arrays": arrays,
        "raw_values_emitted": False,
    }


def _shape_elements(shape: Any) -> int | None:
    if shape is None:
        return None
    total = 1
    for value in shape:
        total *= int(value)
        if total > 2**63 - 1:
            return None
    return total


def inspect_hdf5(
    path: Path,
    *,
    reveal_identifiers: bool = False,
) -> dict[str, Any]:
    """Inspect HDF5 links and metadata without reading dataset values."""

    try:
        import h5py
    except ImportError as exc:
        raise CliError(
            'optional dependency missing; install with: uv pip install "h5py==3.16.0"'
        ) from exc
    objects: list[dict[str, Any]] = []
    link_counts = {"hard": 0, "soft_not_followed": 0, "external_not_followed": 0}
    object_limit_reached = False
    depth_limit_reached = False
    seen_addresses: set[int] = set()
    try:
        with h5py.File(path, "r") as handle:
            stack: list[tuple[Any, str, int]] = [(handle, "/", 0)]
            while stack:
                group, logical_path, depth = stack.pop()
                if len(objects) >= MAX_HDF5_OBJECTS:
                    object_limit_reached = True
                    break
                for name in itertools.islice(
                    group.keys(),
                    MAX_HDF5_OBJECTS - len(objects) + 1,
                ):
                    if len(objects) >= MAX_HDF5_OBJECTS:
                        object_limit_reached = True
                        break
                    link = group.get(name, getlink=True)
                    child_path = (
                        f"/{name}" if logical_path == "/" else f"{logical_path}/{name}"
                    )
                    object_id = display_identifier(
                        child_path,
                        kind="hdf_object",
                        reveal_identifiers=reveal_identifiers,
                    )
                    if isinstance(link, h5py.ExternalLink):
                        link_counts["external_not_followed"] += 1
                        objects.append(
                            {
                                "object_id": object_id,
                                "type": "external_link",
                                "followed": False,
                            }
                        )
                        continue
                    if isinstance(link, h5py.SoftLink):
                        link_counts["soft_not_followed"] += 1
                        objects.append(
                            {
                                "object_id": object_id,
                                "type": "soft_link",
                                "followed": False,
                            }
                        )
                        continue
                    if not isinstance(link, h5py.HardLink):
                        raise CliError("the HDF5 file contains an unsupported link type")
                    link_counts["hard"] += 1
                    child = group.get(name)
                    if child is None:
                        raise CliError("the HDF5 file contains an unresolved hard link")
                    address = int(h5py.h5o.get_info(child.id).addr)
                    already_seen = address in seen_addresses
                    seen_addresses.add(address)
                    if isinstance(child, h5py.Dataset):
                        compression = child.compression
                        external_count = len(child.external or ())
                        objects.append(
                            {
                                "object_id": object_id,
                                "type": "dataset",
                                "hard_link_alias": already_seen,
                                "shape": [int(value) for value in child.shape]
                                if child.shape is not None
                                else None,
                                "element_count": _shape_elements(child.shape),
                                "dtype": _dtype_report(
                                    child.dtype,
                                    reveal_identifiers=reveal_identifiers,
                                ),
                                "attribute_count": len(child.attrs),
                                "chunked": child.chunks is not None,
                                "chunk_shape": [int(value) for value in child.chunks]
                                if child.chunks is not None
                                else None,
                                "compressed": compression is not None,
                                "compression_id": display_identifier(
                                    str(compression),
                                    kind="compression",
                                    reveal_identifiers=reveal_identifiers,
                                )
                                if compression is not None
                                else None,
                                "external_storage_file_count": external_count,
                                "virtual_dataset": bool(child.is_virtual),
                                "values_read": False,
                            }
                        )
                    elif isinstance(child, h5py.Group):
                        objects.append(
                            {
                                "object_id": object_id,
                                "type": "group",
                                "hard_link_alias": already_seen,
                                "attribute_count": len(child.attrs),
                            }
                        )
                        if already_seen:
                            continue
                        if depth >= MAX_HDF5_DEPTH:
                            depth_limit_reached = True
                        else:
                            stack.append((child, child_path, depth + 1))
                    else:
                        raise CliError("the HDF5 file contains an unsupported object type")
    except CliError:
        raise
    except (OSError, RuntimeError, ValueError, TypeError, MemoryError) as exc:
        raise CliError("the HDF5 metadata could not be inspected safely") from exc
    return {
        "profile_type": "hdf5_metadata_only",
        "object_count_reported": len(objects),
        "object_limit_reached": object_limit_reached,
        "depth_limit_reached": depth_limit_reached,
        "links": link_counts,
        "objects": objects,
        "dataset_values_read": False,
        "attributes_values_read": False,
        "soft_links_followed": False,
        "external_links_followed": False,
        "external_dataset_storage_read": False,
        "filter_plugins_invoked_for_data": False,
        "raw_values_emitted": False,
        "limitations": [
            "Generic hierarchy inspection is not semantic validation of H5AD, Loom, or other HDF5 conventions.",
            "Dataset payloads are intentionally not read, so value-level statistics are unavailable.",
        ],
    }
