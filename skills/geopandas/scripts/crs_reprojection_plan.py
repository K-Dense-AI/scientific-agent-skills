#!/usr/bin/env python3
"""Plan CRS and datum transformation semantics without transforming coordinates."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import (
    CliError,
    crs_summary,
    disable_proj_network,
    emit_json,
    fail_json,
    finite_number,
    native_versions,
    package_versions,
)

TOOL = "crs_reprojection_plan"
METRIC_OPERATIONS = {"area", "buffer", "distance", "nearest", "precision"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect CRS axes, units, datum-operation candidates, grid availability, "
            "and antimeridian risk without reading data or transforming coordinates."
        ),
        epilog=(
            "PROJ network access is forcibly disabled. Optional bbox values are used "
            "only as a protected area-of-interest hint and are never emitted."
        ),
    )
    parser.add_argument("--source-crs", required=True, help="Authoritative source CRS")
    parser.add_argument("--target-crs", required=True, help="Proposed target CRS")
    parser.add_argument(
        "--operation",
        choices=(
            "reproject",
            "area",
            "buffer",
            "distance",
            "nearest",
            "precision",
            "display",
        ),
        default="reproject",
        help="Purpose used for unit-readiness checks (default: reproject)",
    )
    parser.add_argument(
        "--bbox",
        nargs=4,
        metavar=("WEST_DEG", "SOUTH_DEG", "EAST_DEG", "NORTH_DEG"),
        help=(
            "Optional geographic source bbox in longitude/latitude degrees. "
            "Projected sources are rejected; east < west marks an antimeridian "
            "crossing. Values are not emitted."
        ),
    )
    parser.add_argument(
        "--allow-ballpark",
        action="store_true",
        help="Include ballpark candidates in this plan (not recommended for accuracy work)",
    )
    return parser


def _dynamic(crs: Any) -> bool:
    datum = getattr(crs, "datum", None)
    type_name = str(getattr(datum, "type_name", "")).casefold()
    return "dynamic" in type_name


def _candidate_summary(transformer: Any) -> dict[str, Any]:
    accuracy = float(transformer.accuracy)
    area = transformer.area_of_use
    return {
        "description": str(transformer.description)[:300],
        "accuracy_metres": accuracy if accuracy >= 0 else None,
        "accuracy_known": accuracy >= 0,
        "area_of_use_name": str(area.name)[:200] if area else None,
    }


def plan(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from pyproj import CRS
        from pyproj.aoi import AreaOfInterest
        from pyproj.transformer import TransformerGroup
    except ImportError as exc:
        raise CliError("pyproj is required for CRS planning") from exc

    disable_proj_network()
    try:
        source = CRS.from_user_input(args.source_crs)
        target = CRS.from_user_input(args.target_crs)
    except (TypeError, ValueError) as exc:
        raise CliError("source or target CRS cannot be parsed") from exc

    bbox_values: list[float] | None = None
    crosses_antimeridian = False
    area_of_interest = None
    if args.bbox is not None:
        if not source.is_geographic or not all(
            str(axis.unit_name).casefold() == "degree"
            for axis in source.axis_info[:2]
        ):
            raise CliError(
                "--bbox requires a geographic source CRS with degree axes; "
                "omit it for projected sources rather than treating metres/feet as degrees"
            )
        bbox_values = [
            finite_number(item, name=f"bbox[{index}]")
            for index, item in enumerate(args.bbox)
        ]
        west, south, east, north = bbox_values
        if not (-180 <= west <= 180 and -180 <= east <= 180):
            raise CliError("bbox longitude must be within [-180, 180] degrees")
        if not (-90 <= south <= 90 and -90 <= north <= 90):
            raise CliError("bbox latitude must be within [-90, 90] degrees")
        if south > north:
            raise CliError("bbox south must not exceed north")
        crosses_antimeridian = bool(source.is_geographic and east < west)
        if not crosses_antimeridian:
            try:
                area_of_interest = AreaOfInterest(west, south, east, north)
            except (TypeError, ValueError) as exc:
                raise CliError("bbox is not a valid area of interest") from exc

    try:
        group = TransformerGroup(
            source,
            target,
            always_xy=True,
            area_of_interest=area_of_interest,
            allow_ballpark=args.allow_ballpark,
        )
    except (TypeError, ValueError) as exc:
        raise CliError("PROJ could not construct transformation candidates") from exc

    candidates = [_candidate_summary(item) for item in group.transformers[:5]]
    source_info = crs_summary(source)
    target_info = crs_summary(target)
    linear_target = bool(
        target.is_projected
        and target.axis_info
        and all(
            "degree" not in str(axis.unit_name).casefold() for axis in target.axis_info[:2]
        )
    )
    metric_ready = args.operation not in METRIC_OPERATIONS or linear_target
    warnings: list[str] = []
    if source.is_geographic:
        warnings.append(
            "Source coordinates are angular; GeoPandas segment transforms are vertex-wise, not geodesic."
        )
    if args.operation in METRIC_OPERATIONS and not linear_target:
        warnings.append(
            "Target CRS does not provide projected linear axes for the requested planar operation."
        )
    if crosses_antimeridian:
        warnings.append(
            "The bbox crosses the antimeridian; split/unwrap and densify as justified before to_crs."
        )
    if not group.best_available:
        warnings.append(
            "The best known operation is unavailable, commonly because a transformation grid is absent."
        )
    if not candidates:
        warnings.append("No available transformation candidate satisfies this policy.")
    if _dynamic(source) or _dynamic(target):
        warnings.append(
            "A dynamic CRS is involved; record and validate the coordinate epoch separately."
        )

    return {
        "ok": bool(candidates) and metric_ready and bool(group.best_available),
        "tool": TOOL,
        "source_crs": source_info,
        "target_crs": target_info,
        "purpose": args.operation,
        "coordinate_array_order": "x_y_via_always_xy",
        "source_dynamic_crs": _dynamic(source),
        "target_dynamic_crs": _dynamic(target),
        "bbox": {
            "provided": bbox_values is not None,
            "values_emitted": False,
            "used_as_area_of_interest": area_of_interest is not None,
            "crosses_antimeridian": crosses_antimeridian,
        },
        "operation_policy": {
            "allow_ballpark": bool(args.allow_ballpark),
            "only_best_recommended_for_execution": True,
            "proj_network_enabled": False,
            "metric_operation_ready": metric_ready,
        },
        "candidate_count": len(group.transformers),
        "candidate_summaries_first_five": candidates,
        "best_available": bool(group.best_available),
        "unavailable_operation_count": len(group.unavailable_operations),
        "coordinates_transformed": False,
        "network_accessed": False,
        "coordinates_emitted": False,
        "identifiers_emitted": False,
        "stack": {"packages": package_versions(), "native": native_versions()},
        "warnings": warnings,
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
