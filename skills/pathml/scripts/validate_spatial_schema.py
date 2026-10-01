#!/usr/bin/env python3
"""Validate bounded graph JSON and multiplex cell-table CSV schemas."""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from _common import (
    CliError,
    MAX_CSV_BYTES,
    MAX_JSON_BYTES,
    checked_input_file,
    checked_root,
    emit_json,
    finite_float,
    load_json_object,
    parse_name_list,
    run_cli,
    validate_keys,
)


ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
COORDINATE_UNITS = {"level_pixels", "level0_pixels", "um"}


def _identifier(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise CliError(
            f"{context} must use 1-128 letters, digits, dots, underscores, "
            "colons, or hyphens"
        )
    return value


def validate_graph(args: argparse.Namespace) -> dict[str, Any]:
    root = checked_root(args.root)
    document = load_json_object(
        args.input,
        root=root,
        max_bytes=args.max_input_bytes,
    )
    validate_keys(
        document,
        allowed={
            "schema_version",
            "slide_id",
            "coordinate_unit",
            "level",
            "nodes",
            "edges",
            "metadata",
        },
        required={"schema_version", "slide_id", "coordinate_unit", "nodes", "edges"},
        context="graph",
    )
    if document["schema_version"] != "1.0":
        raise CliError("graph schema_version must be '1.0'")
    _identifier(document["slide_id"], context="slide_id")
    coordinate_unit = document["coordinate_unit"]
    if not isinstance(coordinate_unit, str) or coordinate_unit not in COORDINATE_UNITS:
        raise CliError(
            "coordinate_unit must be one of: "
            + ", ".join(sorted(COORDINATE_UNITS))
        )
    if "level" in document:
        level = document["level"]
        if isinstance(level, bool) or not isinstance(level, int) or level < 0:
            raise CliError("level must be a nonnegative integer")
    elif coordinate_unit == "level_pixels":
        raise CliError("level is required for level_pixels coordinates")
    nodes = document["nodes"]
    edges = document["edges"]
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise CliError("nodes and edges must be arrays")
    if not 1 <= len(nodes) <= args.max_nodes:
        raise CliError(f"node count must be in [1, {args.max_nodes}]")
    if len(edges) > args.max_edges:
        raise CliError(f"edge count exceeds --max-edges={args.max_edges}")

    node_ids: set[str] = set()
    feature_length: int | None = None
    features_present: bool | None = None
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise CliError(f"node {index} must be an object")
        validate_keys(
            node,
            allowed={"id", "x", "y", "features", "label"},
            required={"id", "x", "y"},
            context=f"node {index}",
        )
        node_id = _identifier(node["id"], context=f"node {index} id")
        if node_id in node_ids:
            raise CliError(f"duplicate node id: {node_id!r}")
        node_ids.add(node_id)
        finite_float(node["x"], name=f"node {index} x", minimum=0, maximum=1e12)
        finite_float(node["y"], name=f"node {index} y", minimum=0, maximum=1e12)
        if features_present is None:
            features_present = "features" in node
        elif features_present != ("features" in node):
            raise CliError("features must be present for all nodes or none")
        if "features" in node:
            features = node["features"]
            if not isinstance(features, list):
                raise CliError(f"node {index} features must be an array")
            if len(features) > args.max_features:
                raise CliError(
                    f"node {index} has more than {args.max_features} features"
                )
            if feature_length is None:
                feature_length = len(features)
            elif len(features) != feature_length:
                raise CliError("all feature arrays must have the same length")
            for feature_index, value in enumerate(features):
                finite_float(
                    value,
                    name=f"node {index} feature {feature_index}",
                    minimum=-1e15,
                    maximum=1e15,
                )

    seen_edges: set[tuple[str, str]] = set()
    self_loops = 0
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise CliError(f"edge {index} must be an object")
        validate_keys(
            edge,
            allowed={"source", "target", "weight", "edge_type"},
            required={"source", "target"},
            context=f"edge {index}",
        )
        source = _identifier(edge["source"], context=f"edge {index} source")
        target = _identifier(edge["target"], context=f"edge {index} target")
        if source not in node_ids or target not in node_ids:
            raise CliError(f"edge {index} references an unknown node")
        if source == target:
            self_loops += 1
            if not args.allow_self_loops:
                raise CliError(f"edge {index} is a self-loop")
        key = tuple(sorted((source, target))) if args.undirected else (source, target)
        if key in seen_edges:
            raise CliError(f"edge {index} duplicates an existing edge")
        seen_edges.add(key)
        if "weight" in edge:
            finite_float(
                edge["weight"],
                name=f"edge {index} weight",
                minimum=-1e15,
                maximum=1e15,
            )

    return {
        "command": "graph",
        "valid": True,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "feature_count": feature_length or 0,
        "coordinate_unit": coordinate_unit,
        "directed_edge_keys": not args.undirected,
        "self_loop_count": self_loops,
        "checks": {
            "strict_json": True,
            "bounded": True,
            "unique_node_ids": True,
            "finite_coordinates": True,
            "uniform_feature_shape": True,
            "valid_edge_endpoints": True,
            "unique_edges": True,
        },
        "path_redacted": True,
    }


def _parse_csv_float(
    raw: str,
    *,
    name: str,
    minimum: float | None = None,
) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise CliError(f"{name} must be numeric") from exc
    if not math.isfinite(value):
        raise CliError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise CliError(f"{name} must be at least {minimum}")
    return value


def validate_multiplex(args: argparse.Namespace) -> dict[str, Any]:
    root = checked_root(args.root)
    path = checked_input_file(
        args.input,
        root=root,
        suffixes={".csv"},
        max_bytes=args.max_input_bytes,
    )
    requested_markers = parse_name_list(
        args.marker_columns, name="--marker-columns"
    )
    keys: set[tuple[str, str]] = set()
    slide_units: dict[str, str] = {}
    slide_levels: dict[str, int] = {}
    patient_splits: dict[str, str] = {}
    unit_counts: Counter[str] = Counter()
    marker_missing: Counter[str] = Counter()
    slide_ids: set[str] = set()
    patient_ids: set[str] = set()

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames
            if headers is None:
                raise CliError("multiplex CSV has no header")
            headers = [header.strip() for header in headers]
            if len(headers) != len(set(headers)):
                raise CliError("multiplex CSV header contains duplicates")
            required = {"cell_id", "slide_id", "x", "y", "coordinate_unit"}
            missing = sorted(required - set(headers))
            if missing:
                raise CliError(
                    "multiplex CSV is missing required columns: "
                    + ", ".join(missing)
                )
            marker_columns = requested_markers or [
                header for header in headers if header.startswith("marker:")
            ]
            if not marker_columns:
                raise CliError(
                    "provide --marker-columns or use at least one marker:* column"
                )
            missing_markers = sorted(set(marker_columns) - set(headers))
            if missing_markers:
                raise CliError(
                    "requested marker columns are absent: "
                    + ", ".join(missing_markers)
                )

            row_count = 0
            for row_count, raw_row in enumerate(reader, start=1):
                if row_count > args.max_rows:
                    raise CliError(f"CSV exceeds --max-rows={args.max_rows}")
                row_number = row_count + 1
                if None in raw_row or any(value is None for value in raw_row.values()):
                    raise CliError(f"row {row_number}: CSV field count does not match header")
                row = {
                    key.strip(): (value or "").strip()
                    for key, value in raw_row.items()
                    if key is not None
                }
                slide_id = _identifier(
                    row["slide_id"], context=f"row {row_number} slide_id"
                )
                cell_id = _identifier(
                    row["cell_id"], context=f"row {row_number} cell_id"
                )
                key = (slide_id, cell_id)
                if key in keys:
                    raise CliError(
                        f"row {row_number}: duplicate (slide_id, cell_id)"
                    )
                keys.add(key)
                slide_ids.add(slide_id)
                _parse_csv_float(
                    row["x"], name=f"row {row_number} x", minimum=0
                )
                _parse_csv_float(
                    row["y"], name=f"row {row_number} y", minimum=0
                )
                unit = row["coordinate_unit"]
                if unit not in COORDINATE_UNITS:
                    raise CliError(
                        f"row {row_number}: coordinate_unit must be one of "
                        + ", ".join(sorted(COORDINATE_UNITS))
                    )
                previous_unit = slide_units.setdefault(slide_id, unit)
                if previous_unit != unit:
                    raise CliError(
                        f"row {row_number}: slide has inconsistent coordinate units"
                    )
                unit_counts[unit] += 1

                level_raw = row.get("level", "")
                if (unit == "level_pixels" or "level" in headers) and not level_raw:
                    raise CliError(f"row {row_number}: level must be supplied")
                if level_raw:
                    try:
                        level = int(level_raw)
                    except ValueError as exc:
                        raise CliError(
                            f"row {row_number}: level must be an integer"
                        ) from exc
                    if level < 0:
                        raise CliError(
                            f"row {row_number}: level must be nonnegative"
                        )
                    previous_level = slide_levels.setdefault(slide_id, level)
                    if previous_level != level:
                        raise CliError(
                            f"row {row_number}: slide has inconsistent levels"
                        )

                patient_id = row.get("patient_id", "")
                split = row.get("split", "")
                if patient_id:
                    patient_id = _identifier(
                        patient_id, context=f"row {row_number} patient_id"
                    )
                    patient_ids.add(patient_id)
                if split and patient_id:
                    previous_split = patient_splits.setdefault(patient_id, split)
                    if previous_split != split:
                        raise CliError(
                            f"row {row_number}: patient appears in multiple splits"
                        )

                for marker in marker_columns:
                    raw_value = row.get(marker, "")
                    if raw_value == "":
                        marker_missing[marker] += 1
                        if not args.allow_missing_markers:
                            raise CliError(
                                f"row {row_number}: marker {marker!r} is missing"
                            )
                        continue
                    _parse_csv_float(
                        raw_value,
                        name=f"row {row_number} marker {marker}",
                    )

            if row_count == 0:
                raise CliError("multiplex CSV contains no rows")
    except CliError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise CliError(f"cannot parse multiplex CSV: {exc}") from exc

    return {
        "command": "multiplex",
        "valid": True,
        "row_count": len(keys),
        "slide_count": len(slide_ids),
        "patient_count": len(patient_ids),
        "marker_columns": marker_columns,
        "missing_marker_values": dict(sorted(marker_missing.items())),
        "coordinate_unit_counts": dict(sorted(unit_counts.items())),
        "checks": {
            "bounded": True,
            "unique_slide_cell_ids": True,
            "finite_nonnegative_coordinates": True,
            "per_slide_coordinate_units": True,
            "per_slide_levels": True,
            "finite_marker_values": True,
            "patient_split_isolation_when_present": True,
        },
        "path_redacted": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate bounded local graph JSON or multiplex cell CSV without "
            "loading PathML, Torch, models, or checkpoints."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    graph = subparsers.add_parser("graph", help="validate graph JSON")
    graph.add_argument("--input", required=True)
    graph.add_argument("--root", default=".")
    graph.add_argument("--max-input-bytes", type=int, default=MAX_JSON_BYTES)
    graph.add_argument("--max-nodes", type=int, default=100_000)
    graph.add_argument("--max-edges", type=int, default=1_000_000)
    graph.add_argument("--max-features", type=int, default=4096)
    graph.add_argument("--undirected", action="store_true")
    graph.add_argument("--allow-self-loops", action="store_true")
    graph.add_argument("--output")
    graph.add_argument("--force", action="store_true")

    multiplex = subparsers.add_parser(
        "multiplex", help="validate a cell-by-marker CSV"
    )
    multiplex.add_argument("--input", required=True)
    multiplex.add_argument("--root", default=".")
    multiplex.add_argument("--max-input-bytes", type=int, default=MAX_CSV_BYTES)
    multiplex.add_argument("--max-rows", type=int, default=100_000)
    multiplex.add_argument("--marker-columns")
    multiplex.add_argument("--allow-missing-markers", action="store_true")
    multiplex.add_argument("--output")
    multiplex.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "graph":
        if not 1 <= args.max_input_bytes <= MAX_JSON_BYTES:
            raise CliError(
                f"--max-input-bytes must be between 1 and {MAX_JSON_BYTES}"
            )
        if not 1 <= args.max_nodes <= 10_000_000:
            raise CliError("--max-nodes must be between 1 and 10000000")
        if not 0 <= args.max_edges <= 100_000_000:
            raise CliError("--max-edges must be between 0 and 100000000")
        if not 0 <= args.max_features <= 100_000:
            raise CliError("--max-features must be between 0 and 100000")
        report = validate_graph(args)
    else:
        if not 1 <= args.max_input_bytes <= MAX_CSV_BYTES:
            raise CliError(
                f"--max-input-bytes must be between 1 and {MAX_CSV_BYTES}"
            )
        if not 1 <= args.max_rows <= 1_000_000:
            raise CliError("--max-rows must be between 1 and 1000000")
        report = validate_multiplex(args)
    emit_json(report, output=args.output, root=args.root, force=args.force)


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
