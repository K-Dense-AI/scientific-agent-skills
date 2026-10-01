"""Shared local-only safety and reporting helpers for GeoPandas CLIs."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

PINNED_STACK = {
    "geopandas": "1.2.0",
    "numpy": "2.5.3",
    "packaging": "26.3",
    "pandas": "3.0.6",
    "pyarrow": "25.0.1",
    "pyogrio": "0.13.0",
    "pyproj": "3.8.0",
    "shapely": "2.1.2",
}
DEFAULT_MAX_INPUT_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_OUTPUT_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_FEATURES = 100_000
ABSOLUTE_MAX_INPUT_BYTES = 512 * 1024 * 1024
ABSOLUTE_MAX_OUTPUT_BYTES = 1024 * 1024 * 1024
ABSOLUTE_MAX_FEATURES = 1_000_000
GDAL_SUFFIXES = {".fgb", ".geojson", ".gpkg", ".json", ".shp"}
PARQUET_SUFFIXES = {".geoparquet", ".parquet"}
FEATHER_SUFFIXES = {".arrow", ".feather"}
ALLOWED_INPUT_SUFFIXES = GDAL_SUFFIXES | PARQUET_SUFFIXES | FEATHER_SUFFIXES
ARCHIVE_SUFFIXES = {
    ".7z",
    ".bz2",
    ".gz",
    ".kmz",
    ".rar",
    ".tar",
    ".tgz",
    ".xz",
    ".zip",
}
SENSITIVE_FIELD_TOKENS = {
    "address",
    "coordinate",
    "email",
    "latitude",
    "location",
    "longitude",
    "parcel",
    "phone",
    "postcode",
    "trajectory",
    "zipcode",
}


class CliError(ValueError):
    """A bounded, user-facing CLI error."""


def positive_int(value: str) -> int:
    """Argparse converter for positive integers."""
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError("must be an integer") from exc
    if number < 1:
        raise ValueError("must be at least 1")
    return number


def bounded_limit(value: int, *, name: str, maximum: int) -> int:
    """Validate a positive resource limit against a hard ceiling."""
    if value < 1:
        raise CliError(f"{name} must be at least 1")
    if value > maximum:
        raise CliError(f"{name} may not exceed {maximum}")
    return value


def finite_number(value: Any, *, name: str) -> float:
    """Return one finite floating-point value."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CliError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise CliError(f"{name} must be finite")
    return number


def reject_nonlocal(value: str, *, label: str) -> None:
    """Reject URLs, GDAL virtual filesystems, archives, and path tricks."""
    lowered = value.casefold().strip()
    if not lowered or "\x00" in value:
        raise CliError(f"{label} is empty or invalid")
    if "://" in lowered or lowered.startswith(("/vsi", "vsi")):
        raise CliError(f"{label} must be a local path, not a URL or GDAL VSI path")
    if "!" in value or lowered.startswith(("zip+", "tar+")):
        raise CliError(f"{label} may not address an archive member")
    suffixes = {suffix.casefold() for suffix in Path(lowered).suffixes}
    if suffixes & ARCHIVE_SUFFIXES:
        raise CliError(f"{label} may not be an archive or compressed file")


def _root_path(value: str | Path) -> Path:
    raw = str(value)
    reject_nonlocal(raw, label="root")
    candidate = Path(raw).expanduser()
    if candidate.is_symlink():
        raise CliError("root may not be a symbolic link")
    try:
        root = candidate.resolve(strict=True)
    except OSError as exc:
        raise CliError("root does not exist or cannot be resolved") from exc
    if not root.is_dir():
        raise CliError("root must be a directory")
    return root


def _reject_symlink_components(candidate: Path, root: Path) -> None:
    current = candidate
    while True:
        if current.is_symlink():
            raise CliError("symbolic-link paths are not accepted")
        if current == root:
            return
        parent = current.parent
        if parent == current:
            raise CliError("path escapes the configured root")
        current = parent


def _candidate_path(value: str | Path, root: Path, *, label: str) -> Path:
    raw = str(value)
    reject_nonlocal(raw, label=label)
    supplied = Path(raw).expanduser()
    if ".." in supplied.parts:
        raise CliError(f"{label} may not contain '..'")
    candidate = supplied if supplied.is_absolute() else root / supplied
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise CliError(f"{label} must remain inside the configured root")
    _reject_symlink_components(candidate, root)
    return candidate


def checked_input_file(
    value: str | Path,
    *,
    root: str | Path = ".",
    max_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    allowed_suffixes: set[str] | None = None,
) -> Path:
    """Resolve one bounded, allowlisted local regular input file."""
    max_bytes = bounded_limit(
        max_bytes,
        name="max_input_bytes",
        maximum=ABSOLUTE_MAX_INPUT_BYTES,
    )
    resolved_root = _root_path(root)
    candidate = _candidate_path(value, resolved_root, label="input")
    try:
        path = candidate.resolve(strict=True)
    except OSError as exc:
        raise CliError("input does not exist or cannot be resolved") from exc
    if not path.is_file():
        raise CliError("input must be a regular file")
    suffixes = allowed_suffixes or ALLOWED_INPUT_SUFFIXES
    if path.suffix.casefold() not in suffixes:
        raise CliError("input suffix is not on the vector-data allowlist")
    size = path.stat().st_size
    if size > max_bytes:
        raise CliError(f"input exceeds the {max_bytes}-byte limit")
    return path


def checked_output_file(
    value: str | Path,
    *,
    root: str | Path = ".",
    allowed_suffixes: set[str],
) -> Path:
    """Resolve a new local output path without creating or overwriting it."""
    resolved_root = _root_path(root)
    candidate = _candidate_path(value, resolved_root, label="output")
    if candidate.suffix.casefold() not in allowed_suffixes:
        raise CliError("output suffix is not allowed for this operation")
    if candidate.exists() or candidate.is_symlink():
        raise CliError("output already exists; choose a new path")
    parent = candidate.parent
    if parent.is_symlink() or not parent.exists() or not parent.is_dir():
        raise CliError("output parent must be an existing non-symlink directory")
    return candidate.resolve(strict=False)


def sha256_file(path: Path) -> str:
    """Hash a bounded local file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def package_versions() -> dict[str, str | None]:
    """Return distribution versions without importing optional packages."""
    found: dict[str, str | None] = {}
    for name in PINNED_STACK:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            found[name] = None
    return found


def native_versions() -> dict[str, str | None]:
    """Return native-library versions after callers have accepted the boundary."""
    try:
        import pyogrio
        import pyproj
        import shapely
    except ImportError as exc:
        raise CliError(
            "runtime analysis requires the pinned GeoPandas stack from SKILL.md"
        ) from exc
    gdal_geos = getattr(pyogrio, "__gdal_geos_version__", None)
    return {
        "gdal": ".".join(str(part) for part in pyogrio.__gdal_version__),
        "gdal_geos": (
            ".".join(str(part) for part in gdal_geos) if gdal_geos else None
        ),
        "geos": str(shapely.geos_version_string),
        "proj": str(pyproj.proj_version_str),
    }


def disable_proj_network() -> None:
    """Disable PROJ network access for this process."""
    try:
        from pyproj import network
    except ImportError as exc:
        raise CliError("pyproj is required for CRS analysis") from exc
    network.set_network_enabled(False)


def crs_summary(value: Any) -> dict[str, Any]:
    """Summarize CRS semantics without serializing sensitive data extents."""
    try:
        from pyproj import CRS
    except ImportError as exc:
        raise CliError("pyproj is required for CRS analysis") from exc
    if value is None:
        return {
            "present": False,
            "authority": None,
            "geographic": None,
            "projected": None,
            "axes": [],
        }
    try:
        crs = CRS.from_user_input(value)
    except (TypeError, ValueError) as exc:
        raise CliError("CRS metadata cannot be parsed") from exc
    authority = crs.to_authority()
    axes = []
    for axis in crs.axis_info:
        factor = axis.unit_conversion_factor
        axes.append(
            {
                "abbreviation": axis.abbrev,
                "direction": axis.direction,
                "unit": axis.unit_name,
                "unit_to_si": float(factor) if factor is not None else None,
            }
        )
    return {
        "present": True,
        "authority": f"{authority[0]}:{authority[1]}" if authority else None,
        "geographic": bool(crs.is_geographic),
        "projected": bool(crs.is_projected),
        "axes": axes,
    }


def _json_scalar(value: Any) -> Any:
    """Convert common array scalars to strict JSON values."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        return _json_scalar(value.item())
    return str(value)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CliError(f"duplicate JSON metadata key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise CliError(f"non-finite JSON metadata value is not allowed: {value}")


def inspect_geoparquet(path: Path) -> dict[str, Any]:
    """Inspect Parquet metadata without reading feature coordinates."""
    try:
        from pyarrow import parquet
    except ImportError as exc:
        raise CliError("PyArrow is required to inventory GeoParquet") from exc
    try:
        parquet_file = parquet.ParquetFile(path)
    except (OSError, ValueError) as exc:
        raise CliError("PyArrow could not read Parquet metadata") from exc
    file_metadata = parquet_file.metadata
    key_values = file_metadata.metadata or {}
    raw_geo = key_values.get(b"geo")
    geo: dict[str, Any] | None = None
    if raw_geo is not None:
        try:
            decoded = raw_geo.decode("utf-8")
            parsed = json.loads(
                decoded,
                object_pairs_hook=_strict_object,
                parse_constant=_reject_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CliError("GeoParquet geo metadata is invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise CliError("GeoParquet geo metadata must be an object")
        geo = parsed
    columns = geo.get("columns", {}) if geo else {}
    if columns is not None and not isinstance(columns, dict):
        raise CliError("GeoParquet columns metadata must be an object")
    if geo is not None:
        if not isinstance(geo.get("version"), str):
            raise CliError("GeoParquet metadata requires a version string")
        primary = geo.get("primary_column")
        if not isinstance(primary, str) or not columns or primary not in columns:
            raise CliError("GeoParquet metadata requires a declared primary geometry column")
        if any(name not in parquet_file.schema_arrow.names for name in columns):
            raise CliError("GeoParquet geometry metadata refers to an absent column")
    crs_states = {"missing": 0, "null": 0, "present": 0}
    covering_columns = 0
    geometry_types: dict[str, int] = {}
    for metadata in (columns or {}).values():
        if not isinstance(metadata, dict):
            raise CliError("GeoParquet geometry column metadata must be an object")
        if "crs" not in metadata:
            crs_states["missing"] += 1
        elif metadata["crs"] is None:
            crs_states["null"] += 1
        else:
            crs_states["present"] += 1
        if metadata.get("covering") is not None:
            covering_columns += 1
        for geometry_type in metadata.get("geometry_types", []):
            key = str(geometry_type)
            geometry_types[key] = geometry_types.get(key, 0) + 1
    arrow_types: dict[str, int] = {}
    for field in parquet_file.schema_arrow:
        key = str(field.type)
        arrow_types[key] = arrow_types.get(key, 0) + 1
    return {
        "kind": "geoparquet" if geo else "parquet_without_geo_metadata",
        "declared_features": int(file_metadata.num_rows),
        "row_groups": int(file_metadata.num_row_groups),
        "field_count": len(parquet_file.schema_arrow),
        "field_type_counts": dict(sorted(arrow_types.items())),
        "geometry_column_count": len(columns or {}),
        "primary_geometry_declared": bool(geo and geo.get("primary_column")),
        "schema_version": _json_scalar(geo.get("version")) if geo else None,
        "crs_metadata_states": crs_states,
        "geometry_type_metadata_counts": dict(sorted(geometry_types.items())),
        "covering_geometry_columns": covering_columns,
        "bounds_redacted": True,
        "feature_data_loaded": False,
        "dataframe_attrs_present": b"PANDAS_ATTRS" in key_values,
    }


def inspect_gdal_vector(path: Path, *, layer: str | None = None) -> dict[str, Any]:
    """Inspect one GDAL vector layer without reading feature coordinates."""
    try:
        import pyogrio
    except ImportError as exc:
        raise CliError("pyogrio is required to inventory this vector format") from exc
    try:
        layers = pyogrio.list_layers(path)
    except (OSError, RuntimeError, ValueError) as exc:
        raise CliError("GDAL could not enumerate local vector layers") from exc
    layer_count = len(layers)
    if layer_count > 1 and layer is None:
        raise CliError("multi-layer input requires an explicit --layer")
    try:
        info = pyogrio.read_info(
            path,
            layer=layer,
            force_feature_count=False,
            force_total_bounds=False,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise CliError("GDAL could not inspect the selected local layer") from exc
    fields = [str(item) for item in info.get("fields", [])]
    dtypes: dict[str, int] = {}
    for dtype in info.get("dtypes", []):
        key = str(dtype)
        dtypes[key] = dtypes.get(key, 0) + 1
    sensitive_names = 0
    for field in fields:
        normalized = re.sub(r"[^a-z0-9]+", "_", field.casefold())
        if any(token in normalized for token in SENSITIVE_FIELD_TOKENS):
            sensitive_names += 1
    declared = info.get("features", -1)
    try:
        declared_features = int(declared)
    except (TypeError, ValueError):
        declared_features = -1
    return {
        "kind": "gdal_vector",
        "driver": _json_scalar(info.get("driver")),
        "layer_count": layer_count,
        "layer_explicitly_selected": layer is not None,
        "declared_features": declared_features if declared_features >= 0 else None,
        "field_count": len(fields),
        "field_type_counts": dict(sorted(dtypes.items())),
        "sensitive_field_name_count": sensitive_names,
        "geometry_type": _json_scalar(info.get("geometry_type")),
        "encoding": _json_scalar(info.get("encoding")),
        "crs": crs_summary(info.get("crs")),
        "bounds_available": info.get("total_bounds") is not None,
        "bounds_redacted": True,
        "feature_data_loaded": False,
    }


def inspect_local_vector(path: Path, *, layer: str | None = None) -> dict[str, Any]:
    """Dispatch to a metadata-only local vector inventory."""
    suffix = path.suffix.casefold()
    if suffix in PARQUET_SUFFIXES:
        if layer is not None:
            raise CliError("--layer is not valid for GeoParquet")
        return inspect_geoparquet(path)
    if suffix in FEATHER_SUFFIXES:
        raise CliError("Feather/Arrow inventory is not implemented; convert a vetted copy")
    return inspect_gdal_vector(path, layer=layer)


def load_geodataframe(
    path: Path,
    *,
    layer: str | None,
    max_features: int,
) -> Any:
    """Load at most max_features local geometries from an allowlisted format."""
    max_features = bounded_limit(
        max_features,
        name="max_features",
        maximum=ABSOLUTE_MAX_FEATURES,
    )
    if path.suffix.casefold() not in GDAL_SUFFIXES:
        raise CliError("this analysis accepts only allowlisted GDAL vector files")
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise CliError("GeoPandas is required for geometry analysis") from exc
    info = inspect_gdal_vector(path, layer=layer)
    declared = info["declared_features"]
    if declared is not None and declared > max_features:
        raise CliError(f"input declares more than {max_features} features")
    try:
        frame = gpd.read_file(
            path,
            layer=layer,
            engine="pyogrio",
            rows=slice(0, max_features + 1),
            use_arrow=True,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise CliError("GeoPandas could not read the bounded local layer") from exc
    if not isinstance(frame, gpd.GeoDataFrame):
        raise CliError("selected layer has no geometry column")
    if not frame.columns.is_unique:
        raise CliError("duplicate input column names are not accepted")
    if len(frame) > max_features:
        raise CliError(f"input exceeds the {max_features}-feature limit")
    return frame


def geometry_state(frame: Any) -> dict[str, Any]:
    """Return aggregate geometry state without values, IDs, or coordinates."""
    geometry = frame.geometry
    missing = geometry.isna()
    empty = geometry.is_empty
    invalid = (~missing) & (~empty) & (~geometry.is_valid)
    type_counts: dict[str, int] = {}
    for value in geometry.geom_type:
        key = "missing" if value is None else str(value)
        type_counts[key] = type_counts.get(key, 0) + 1
    reason_counts: dict[str, int] = {}
    if bool(invalid.any()):
        for reason in geometry[invalid].is_valid_reason():
            category = str(reason).split("[", 1)[0].strip()[:120]
            reason_counts[category] = reason_counts.get(category, 0) + 1
    has_m = getattr(geometry, "has_m", None)
    return {
        "features": len(frame),
        "missing": int(missing.sum()),
        "empty": int(empty.sum()),
        "invalid": int(invalid.sum()),
        "valid_nonempty": int((~missing & ~empty & ~invalid).sum()),
        "geometry_type_counts": dict(sorted(type_counts.items())),
        "validity_reason_categories": dict(sorted(reason_counts.items())),
        "has_z": int(geometry.has_z.fillna(False).sum()),
        "has_m": int(has_m.fillna(False).sum()) if has_m is not None else None,
        "duplicate_index_rows": int(frame.index.duplicated(keep=False).sum()),
        "coordinates_emitted": False,
        "identifiers_emitted": False,
    }


def duplicate_column_state(frame: Any, name: str | None) -> dict[str, Any]:
    """Report null/duplicate counts for an optional ID without emitting values."""
    if name is None:
        return {"provided": False, "null_rows": None, "duplicate_rows": None}
    if name not in frame.columns:
        raise CliError("requested ID column is not present")
    values = frame[name]
    return {
        "provided": True,
        "null_rows": int(values.isna().sum()),
        "duplicate_rows": int(values.duplicated(keep=False).sum()),
    }


def write_new_geopackage(
    frame: Any,
    destination: Path,
    *,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> None:
    """Write a single-layer GeoPackage and link it atomically to a new path."""
    max_output_bytes = bounded_limit(
        max_output_bytes,
        name="max_output_bytes",
        maximum=ABSOLUTE_MAX_OUTPUT_BYTES,
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".geopandas-repair-",
        suffix=".gpkg",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.unlink()
        frame.to_file(
            temporary,
            layer="repaired",
            driver="GPKG",
            engine="pyogrio",
            index=False,
            use_arrow=True,
        )
        if temporary.stat().st_size > max_output_bytes:
            raise CliError(f"derived output exceeds the {max_output_bytes}-byte limit")
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise CliError("output appeared concurrently; nothing was overwritten") from exc
    finally:
        temporary.unlink(missing_ok=True)


def json_text(payload: Any) -> str:
    """Serialize strict, deterministic JSON."""
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def emit_json(payload: Any) -> None:
    """Print a strict JSON report."""
    print(json_text(payload))


def fail_json(tool: str, exc: BaseException) -> int:
    """Emit a redacted error and return the CLI usage/data error status."""
    if isinstance(exc, CliError):
        message = str(exc)
    else:
        message = f"{type(exc).__name__}: operation failed; details redacted"
    emit_json(
        {
            "ok": False,
            "tool": tool,
            "error": message[:500],
            "network_accessed": False,
            "coordinates_emitted": False,
            "identifiers_emitted": False,
        }
    )
    return 2
