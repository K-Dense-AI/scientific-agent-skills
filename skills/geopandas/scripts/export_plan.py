#!/usr/bin/env python3
"""Create a non-executing, redacted vector export and GeoParquet plan."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import (
    ABSOLUTE_MAX_FEATURES,
    DEFAULT_MAX_FEATURES,
    DEFAULT_MAX_INPUT_BYTES,
    CliError,
    bounded_limit,
    checked_input_file,
    checked_output_file,
    emit_json,
    fail_json,
    inspect_local_vector,
    native_versions,
    package_versions,
    positive_int,
    sha256_file,
)

TOOL = "export_plan"
FORMAT_SUFFIXES = {
    "flatgeobuf": {".fgb"},
    "geopackage": {".gpkg"},
    "geojson": {".geojson", ".json"},
    "geoparquet": {".geoparquet", ".parquet"},
    "shapefile": {".shp"},
}
SUFFIX_FORMAT = {
    suffix: format_name
    for format_name, suffixes in FORMAT_SUFFIXES.items()
    for suffix in suffixes
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan—but do not execute—a local vector export. Inspect only metadata, "
            "validate a new output path, and emit format/privacy/provenance gates."
        ),
        epilog=(
            "No feature data or coordinates are loaded. URLs, archives, symlinks, "
            "path traversal, and existing output paths are rejected."
        ),
    )
    parser.add_argument("input", help="Allowlisted local vector/GeoParquet input")
    parser.add_argument("output", help="Proposed new local output path")
    parser.add_argument("--root", default=".", help="Existing local I/O root")
    parser.add_argument("--layer", help="Exact input layer name")
    parser.add_argument(
        "--format",
        choices=tuple(sorted(FORMAT_SUFFIXES)),
        help="Target format; default infers from output suffix",
    )
    parser.add_argument(
        "--stable-id-column",
        help="Declared stable feature-ID column (name is not emitted)",
    )
    parser.add_argument(
        "--id-unique-verified",
        action="store_true",
        help="Attest that stable ID is non-null and unique in the planned export",
    )
    parser.add_argument(
        "--index-policy",
        choices=("omit", "include"),
        default="omit",
        help="Whether to serialize the pandas index (default: omit)",
    )
    parser.add_argument(
        "--geometry-encoding",
        choices=("WKB", "geoarrow"),
        default="WKB",
        help="GeoParquet geometry encoding (default: WKB)",
    )
    parser.add_argument(
        "--schema-version",
        choices=("1.0.0", "1.1.0"),
        default="1.1.0",
        help="Stable GeoParquet schema version (default: 1.1.0; 2.0 not planned)",
    )
    parser.add_argument(
        "--write-covering-bbox",
        action="store_true",
        help="Plan a GeoParquet 1.1 per-row bbox covering column",
    )
    parser.add_argument(
        "--public-output",
        action="store_true",
        help="Mark the proposed output as intended for public release",
    )
    parser.add_argument(
        "--sensitive-coordinates",
        action="store_true",
        help="Mark input as containing sensitive exact locations",
    )
    parser.add_argument(
        "--generalized-and-reviewed",
        action="store_true",
        help="Attest that coordinates/attributes were generalized and reviewed",
    )
    parser.add_argument(
        "--max-input-bytes",
        type=positive_int,
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    parser.add_argument(
        "--max-features",
        type=positive_int,
        default=DEFAULT_MAX_FEATURES,
        help="Declared-feature threshold for the downstream export",
    )
    return parser


def _format_risks(format_name: str) -> list[str]:
    risks = {
        "geopackage": [
            "One geometry column per layer; additional geometry columns need separate layers or explicit encoding.",
            "Append/overwrite behavior is driver-specific; this plan requires a new file.",
        ],
        "geojson": [
            "Text output exposes exact coordinates and attributes directly.",
            "CRS/type/datetime/large-integer fidelity is limited; RFC 7946 interoperability normally expects WGS84 longitude/latitude.",
        ],
        "shapefile": [
            "Legacy multi-file output has field-name, null, type, encoding, geometry, and size limitations.",
            "A single hash does not cover the complete sidecar set.",
        ],
        "flatgeobuf": [
            "Driver/version interoperability and field-type support must be roundtrip-tested.",
        ],
        "geoparquet": [
            "GeoParquet readers vary in support for schema 1.1 native encodings and bbox covering.",
            "Stable feature IDs require an explicit project column/metadata contract.",
        ],
    }
    return risks[format_name]


def plan(args: argparse.Namespace) -> dict[str, Any]:
    max_features = bounded_limit(
        args.max_features,
        name="max_features",
        maximum=ABSOLUTE_MAX_FEATURES,
    )
    source = checked_input_file(
        args.input,
        root=args.root,
        max_bytes=args.max_input_bytes,
    )
    suffix = str(args.output).casefold().strip()
    suffix = "." + suffix.rsplit(".", 1)[-1] if "." in suffix else ""
    inferred = SUFFIX_FORMAT.get(suffix)
    format_name = args.format or inferred
    if format_name is None:
        raise CliError("target format cannot be inferred from output suffix")
    destination = checked_output_file(
        args.output,
        root=args.root,
        allowed_suffixes=FORMAT_SUFFIXES[format_name],
    )
    if inferred is not None and inferred != format_name:
        raise CliError("target format conflicts with output suffix")

    technical = inspect_local_vector(source, layer=args.layer)
    declared = technical.get("declared_features")
    blockers: list[str] = []
    warnings = _format_risks(format_name)

    if args.stable_id_column is None:
        blockers.append("declare a stable feature-ID column")
    elif not args.id_unique_verified:
        blockers.append("verify the stable ID is non-null and unique")
    if declared is not None and declared > max_features:
        blockers.append("declared feature count exceeds the downstream limit")
    if (
        args.public_output
        and args.sensitive_coordinates
        and not args.generalized_and_reviewed
    ):
        blockers.append(
            "public sensitive-coordinate output requires generalization and review"
        )
    if args.generalized_and_reviewed and not args.sensitive_coordinates:
        warnings.append(
            "Generalization attestation was supplied without marking coordinates sensitive."
        )

    geoparquet_options_used = (
        args.geometry_encoding != "WKB"
        or args.schema_version != "1.1.0"
        or args.write_covering_bbox
    )
    if format_name != "geoparquet" and geoparquet_options_used:
        blockers.append("GeoParquet options are valid only for geoparquet output")
    if format_name == "geoparquet":
        if args.geometry_encoding == "geoarrow" and args.schema_version != "1.1.0":
            blockers.append("native geoarrow encoding requires schema 1.1.0")
        if args.write_covering_bbox and args.schema_version != "1.1.0":
            blockers.append("bbox covering requires schema 1.1.0")
        if args.write_covering_bbox and args.sensitive_coordinates:
            blockers.append(
                "per-row bbox covering is not approved for sensitive coordinates"
            )
        if args.geometry_encoding == "geoarrow" or args.write_covering_bbox:
            warnings.append(
                "GeoPandas describes native encoding and bbox covering as experimental/interoperability-limited."
            )

    if technical["kind"] == "gdal_vector":
        if not technical["crs"]["present"]:
            blockers.append("source CRS metadata is missing")
    elif technical["kind"] == "geoparquet":
        states = technical["crs_metadata_states"]
        if states["null"]:
            blockers.append("one or more GeoParquet geometry columns have unknown CRS")
        if states["missing"]:
            warnings.append(
                "A missing GeoParquet CRS key means OGC:CRS84, not unknown CRS."
            )
    else:
        blockers.append("input Parquet lacks required GeoParquet metadata")

    return {
        "ok": not blockers,
        "tool": TOOL,
        "executed": False,
        "feature_data_loaded": False,
        "source": {
            "sha256": sha256_file(source),
            "bytes": source.stat().st_size,
            "path_emitted": False,
            "technical_inventory": technical,
        },
        "target": {
            "format": format_name,
            "suffix": destination.suffix.casefold(),
            "path_emitted": False,
            "exists": False,
            "index_policy": args.index_policy,
            "stable_id_declared": args.stable_id_column is not None,
            "stable_id_name_emitted": False,
            "stable_id_unique_verified": bool(args.id_unique_verified),
        },
        "geoparquet": (
            {
                "schema_version": args.schema_version,
                "geometry_encoding": args.geometry_encoding,
                "write_covering_bbox": bool(args.write_covering_bbox),
                "default_stable_contract": bool(
                    args.schema_version == "1.1.0"
                    and args.geometry_encoding == "WKB"
                    and not args.write_covering_bbox
                ),
            }
            if format_name == "geoparquet"
            else None
        ),
        "privacy": {
            "public_output": bool(args.public_output),
            "sensitive_coordinates": bool(args.sensitive_coordinates),
            "generalized_and_reviewed": bool(args.generalized_and_reviewed),
            "coordinates_emitted": False,
        },
        "roundtrip_checks_required": [
            "row count and stable-ID set",
            "CRS and active/additional geometry columns",
            "null, empty, invalid, geometry type, and dimensionality counts",
            "field types, nullability, encoding, and expected format losses",
            "protected coarse bounds and representative attributes",
            "new artifact hash and package/native versions",
        ],
        "format_risks": warnings,
        "blockers": blockers,
        "resource_limits": {
            "max_input_bytes": args.max_input_bytes,
            "max_features_for_execution": max_features,
        },
        "network_accessed": False,
        "coordinates_emitted": False,
        "identifiers_emitted": False,
        "stack": {"packages": package_versions(), "native": native_versions()},
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = plan(args)
        emit_json(report)
        return 0 if report["ok"] else 2
    except Exception as exc:  # noqa: BLE001 - errors are redacted at CLI boundary
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
