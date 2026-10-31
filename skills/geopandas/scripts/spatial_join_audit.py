#!/usr/bin/env python3
"""Run a bounded local spatial join and emit only aggregate cardinality."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from typing import Any

from _common import (
    ABSOLUTE_MAX_FEATURES,
    DEFAULT_MAX_FEATURES,
    DEFAULT_MAX_INPUT_BYTES,
    CliError,
    bounded_limit,
    checked_input_file,
    crs_summary,
    duplicate_column_state,
    emit_json,
    fail_json,
    finite_number,
    geometry_state,
    load_geodataframe,
    native_versions,
    package_versions,
    positive_int,
    sha256_file,
)

TOOL = "spatial_join_audit"
DEFAULT_MAX_PAIRS = 1_000_000
ABSOLUTE_MAX_PAIRS = 10_000_000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit a bounded local binary-predicate or nearest spatial join. "
            "Only aggregate multiplicity is emitted; no pairs, IDs, or coordinates."
        ),
        epilog=(
            "Both inputs must be local allowlisted files under --root. Invalid or "
            "CRS-incompatible inputs block execution. All operations are planar."
        ),
    )
    parser.add_argument("left", help="Local left vector file")
    parser.add_argument("right", help="Local right vector file")
    parser.add_argument("--root", default=".", help="Existing local I/O root")
    parser.add_argument("--left-layer", help="Exact left layer name")
    parser.add_argument("--right-layer", help="Exact right layer name")
    parser.add_argument("--left-id", help="Optional left stable ID column to audit")
    parser.add_argument("--right-id", help="Optional right stable ID column to audit")
    parser.add_argument(
        "--mode",
        choices=("predicate", "nearest"),
        default="predicate",
        help="Join mode (default: predicate)",
    )
    parser.add_argument(
        "--predicate",
        default="intersects",
        help="Spatial-index predicate for predicate mode (default: intersects)",
    )
    parser.add_argument(
        "--distance",
        help="Positive CRS-unit scalar required for predicate=dwithin",
    )
    parser.add_argument(
        "--max-distance",
        help="Optional positive CRS-unit search limit for nearest mode",
    )
    parser.add_argument(
        "--exclusive",
        action="store_true",
        help="Nearest mode: exclude geometrically equal candidates",
    )
    parser.add_argument(
        "--on-attribute",
        action="append",
        default=[],
        help="Additional equality column present on both sides; repeat as needed",
    )
    parser.add_argument(
        "--max-input-bytes",
        type=positive_int,
        default=DEFAULT_MAX_INPUT_BYTES,
        help="Maximum bytes for each primary input file",
    )
    parser.add_argument(
        "--max-features",
        type=positive_int,
        default=DEFAULT_MAX_FEATURES,
        help=f"Maximum features per input (default: {DEFAULT_MAX_FEATURES})",
    )
    parser.add_argument(
        "--max-pairs",
        type=positive_int,
        default=DEFAULT_MAX_PAIRS,
        help=f"Maximum joined pairs before failing closed (default: {DEFAULT_MAX_PAIRS})",
    )
    return parser


def _work_frame(frame: Any, row_column: str, attributes: list[str]) -> Any:
    active = frame.geometry.name
    columns = [active, *attributes]
    work = frame.loc[:, columns].reset_index(drop=True).copy()
    if active != "_audit_geometry":
        work = work.rename_geometry("_audit_geometry")
    work[row_column] = range(len(work))
    return work


def _counter_summary(counter: Counter[int], total_features: int) -> dict[str, int]:
    matched = len(counter)
    return {
        "matched_features": matched,
        "unmatched_features": total_features - matched,
        "features_with_one_match": sum(count == 1 for count in counter.values()),
        "features_with_multiple_matches": sum(
            count > 1 for count in counter.values()
        ),
        "maximum_matches_for_one_feature": max(counter.values(), default=0),
    }


def _run_chunked_join(
    left: Any,
    right: Any,
    *,
    mode: str,
    predicate: str,
    distance: float | None,
    max_distance: float | None,
    exclusive: bool,
    attributes: list[str],
    max_pairs: int,
) -> dict[str, Any]:
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise CliError("GeoPandas is required for join analysis") from exc

    left_work = _work_frame(left, "_audit_left_row", attributes)
    right_work = _work_frame(right, "_audit_right_row", attributes)
    if len(right_work) > max_pairs:
        raise CliError(
            "right feature count exceeds max_pairs; one left feature could match all"
        )
    left_counts: Counter[int] = Counter()
    right_counts: Counter[int] = Counter()
    pair_count = 0
    right_size = max(len(right_work), 1)
    chunk_size = max(1, min(512, max_pairs // right_size or 1))

    for start in range(0, len(left_work), chunk_size):
        chunk = left_work.iloc[start : start + chunk_size]
        if mode == "nearest":
            joined = gpd.sjoin_nearest(
                chunk,
                right_work,
                how="inner",
                max_distance=max_distance,
                exclusive=exclusive,
            )
        else:
            joined = gpd.sjoin(
                chunk,
                right_work,
                how="inner",
                predicate=predicate,
                distance=distance,
                on_attribute=attributes or None,
            )
        pair_count += len(joined)
        if pair_count > max_pairs:
            raise CliError(
                f"joined pair count exceeds the configured {max_pairs}-pair limit"
            )
        left_counts.update(int(value) for value in joined["_audit_left_row"])
        right_counts.update(int(value) for value in joined["_audit_right_row"])

    return {
        "pair_count": pair_count,
        "left": _counter_summary(left_counts, len(left)),
        "right": _counter_summary(right_counts, len(right)),
        "many_to_many_observed": bool(
            any(count > 1 for count in left_counts.values())
            and any(count > 1 for count in right_counts.values())
        ),
        "pairs_emitted": False,
        "chunked": True,
        "chunk_size": chunk_size,
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    max_features = bounded_limit(
        args.max_features,
        name="max_features",
        maximum=ABSOLUTE_MAX_FEATURES,
    )
    max_pairs = bounded_limit(
        args.max_pairs,
        name="max_pairs",
        maximum=ABSOLUTE_MAX_PAIRS,
    )
    left_path = checked_input_file(
        args.left,
        root=args.root,
        max_bytes=args.max_input_bytes,
    )
    right_path = checked_input_file(
        args.right,
        root=args.root,
        max_bytes=args.max_input_bytes,
    )
    if left_path == right_path and args.left_layer == args.right_layer:
        raise CliError("left and right inputs resolve to the same layer")

    left = load_geodataframe(
        left_path,
        layer=args.left_layer,
        max_features=max_features,
    )
    right = load_geodataframe(
        right_path,
        layer=args.right_layer,
        max_features=max_features,
    )
    left_state = geometry_state(left)
    right_state = geometry_state(right)
    left_id = duplicate_column_state(left, args.left_id)
    right_id = duplicate_column_state(right, args.right_id)

    try:
        from pyproj import CRS
    except ImportError as exc:
        raise CliError("pyproj is required for CRS comparison") from exc
    blockers: list[str] = []
    same_crs = False
    if left.crs is None or right.crs is None:
        blockers.append("both inputs require explicit CRS metadata")
    else:
        same_crs = CRS.from_user_input(left.crs).equals(CRS.from_user_input(right.crs))
        if not same_crs:
            blockers.append("input CRS values are not equivalent")
    if left_state["invalid"] or right_state["invalid"]:
        blockers.append("invalid input geometries require separate repair review")
    for attribute in args.on_attribute:
        if attribute not in left.columns or attribute not in right.columns:
            blockers.append("an on_attribute column is absent from one input")
            break
        if attribute in {
            "_audit_geometry", "_audit_left_row", "_audit_right_row",
            left.geometry.name, right.geometry.name,
        }:
            blockers.append("on_attribute must not use geometry or reserved audit columns")
    if len(set(args.on_attribute)) != len(args.on_attribute):
        blockers.append("on_attribute columns must not be repeated")

    distance: float | None = None
    max_distance: float | None = None
    if args.mode == "predicate":
        if args.exclusive or args.max_distance is not None:
            blockers.append("--exclusive/--max-distance apply only to nearest mode")
        if args.predicate == "dwithin":
            if args.distance is None:
                blockers.append("predicate dwithin requires --distance")
            else:
                distance = finite_number(args.distance, name="distance")
                if distance <= 0:
                    blockers.append("distance must be greater than zero")
        elif args.distance is not None:
            blockers.append("--distance is valid only for predicate dwithin")
        if not blockers:
            valid = set(left.sindex.valid_query_predicates) & set(
                right.sindex.valid_query_predicates
            )
            if args.predicate not in valid:
                blockers.append("predicate is not supported by both spatial indexes")
    else:
        if args.distance is not None or args.on_attribute:
            blockers.append("--distance/--on-attribute apply only to predicate mode")
        if args.max_distance is not None:
            max_distance = finite_number(args.max_distance, name="max_distance")
            if max_distance <= 0:
                blockers.append("max_distance must be greater than zero")

    geographic = bool(left.crs is not None and left.crs.is_geographic)
    if args.mode == "nearest" and geographic:
        blockers.append("nearest joins are inaccurate in a geographic CRS")
    if args.predicate == "dwithin" and geographic:
        blockers.append("dwithin distance is angular in a geographic CRS")

    pair_audit = None
    if not blockers:
        pair_audit = _run_chunked_join(
            left,
            right,
            mode=args.mode,
            predicate=args.predicate,
            distance=distance,
            max_distance=max_distance,
            exclusive=args.exclusive,
            attributes=args.on_attribute,
            max_pairs=max_pairs,
        )

    warnings = [
        "intersects includes boundary contact; contains/within and covers/covered_by differ at boundaries.",
        "All GeoPandas joins are planar and ignore Z.",
        "Declare expected cardinality separately and compare it with this aggregate audit.",
    ]
    if args.mode == "nearest":
        warnings.append(
            "Nearest returns every equidistant match and has no k parameter."
        )
    if left_state["missing"] or left_state["empty"]:
        warnings.append("Missing/empty left geometries remain unmatched.")
    if right_state["missing"] or right_state["empty"]:
        warnings.append("Missing/empty right geometries remain unmatched.")

    return {
        "ok": not blockers,
        "tool": TOOL,
        "mode": args.mode,
        "predicate": args.predicate if args.mode == "predicate" else None,
        "distance_provided": distance is not None,
        "max_distance_provided": max_distance is not None,
        "exclusive": bool(args.exclusive),
        "on_attribute_column_count": len(args.on_attribute),
        "crs": {
            "left": crs_summary(left.crs),
            "right": crs_summary(right.crs),
            "equivalent": same_crs,
        },
        "left": {
            "source_sha256": sha256_file(left_path),
            "geometry_state": left_state,
            "stable_id_audit": left_id,
        },
        "right": {
            "source_sha256": sha256_file(right_path),
            "geometry_state": right_state,
            "stable_id_audit": right_id,
        },
        "pair_audit": pair_audit,
        "blockers": blockers,
        "resource_limits": {
            "max_input_bytes_each": args.max_input_bytes,
            "max_features_each": max_features,
            "max_pairs": max_pairs,
        },
        "network_accessed": False,
        "coordinates_emitted": False,
        "identifiers_emitted": False,
        "stack": {"packages": package_versions(), "native": native_versions()},
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit(args)
        emit_json(report)
        return 0 if report["ok"] else 2
    except Exception as exc:  # noqa: BLE001 - errors are redacted at CLI boundary
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
