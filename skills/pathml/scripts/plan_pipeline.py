#!/usr/bin/env python3
"""Plan bounded PathML tiling and pipeline work without opening a slide."""

from __future__ import annotations

import argparse
import math
from typing import Any

from _common import CliError, emit_json, parse_name_list, run_cli


TRANSFORM_KINDS = {
    "AdaptiveHistogramEqualization": "image",
    "BinaryThreshold": "mask",
    "BoxBlur": "image",
    "CollapseRunsCODEX": "image",
    "CollapseRunsVectra": "image",
    "ForegroundDetection": "mask",
    "GaussianBlur": "image",
    "HistogramEqualization": "image",
    "LabelArtifactTileHE": "label",
    "LabelWhiteSpaceHE": "label",
    "MedianBlur": "image",
    "MorphClose": "mask",
    "MorphOpen": "mask",
    "NucleusDetectionHE": "mask",
    "QuantifyMIF": "counts",
    "RescaleIntensity": "image",
    "SegmentMIF": "two_instance_masks_deprecated",
    "SegmentMIFRemote": "two_instance_masks_network_download",
    "StainNormalizationHE": "image",
    "SuperpixelInterpolation": "image",
    "TissueDetectionHE": "mask",
}


def _stable_pathml_count(
    dimension: int,
    tile_extent: int,
    stride: int,
    pad: bool,
) -> int:
    """Match PathML 3.0.8 OpenSlide/Bio-Formats tile-count arithmetic."""

    if pad and dimension % stride != 0:
        return dimension // stride + 1
    if dimension < tile_extent:
        return 0
    return (dimension - tile_extent) // stride + 1


def _parse_pipeline(value: str | None) -> list[str]:
    stages = parse_name_list(value, name="--pipeline")
    unknown = sorted(set(stages) - set(TRANSFORM_KINDS))
    if unknown:
        raise CliError(
            "unknown PathML 3.0.8 transform names: " + ", ".join(unknown)
        )
    return stages


def make_plan(args: argparse.Namespace) -> dict[str, Any]:
    if not 1 <= args.width <= 1_000_000_000:
        raise CliError("--width must be between 1 and 1000000000")
    if not 1 <= args.height <= 1_000_000_000:
        raise CliError("--height must be between 1 and 1000000000")
    if not 1 <= args.tile_size <= 8192:
        raise CliError("--tile-size must be between 1 and 8192")
    if not 1 <= args.stride <= 8192:
        raise CliError("--stride must be between 1 and 8192")
    if not math.isfinite(args.level_downsample) or not (
        1.0 <= args.level_downsample <= 1_000_000.0
    ):
        raise CliError("--level-downsample must be finite and in [1, 1000000]")
    if not 1 <= args.channels <= 4096:
        raise CliError("--channels must be between 1 and 4096")
    if args.bytes_per_channel not in {1, 2, 4, 8}:
        raise CliError("--bytes-per-channel must be one of 1, 2, 4, or 8")
    if not 1 <= args.max_tiles <= 100_000_000:
        raise CliError("--max-tiles must be between 1 and 100000000")
    if not math.isfinite(args.max_output_gib) or not (
        0 < args.max_output_gib <= 1_000_000
    ):
        raise CliError("--max-output-gib must be finite and positive")
    if args.mpp_x is not None and (
        not math.isfinite(args.mpp_x) or not 0 < args.mpp_x <= 1000
    ):
        raise CliError("--mpp-x must be finite and in (0, 1000]")
    if args.mpp_y is not None and (
        not math.isfinite(args.mpp_y) or not 0 < args.mpp_y <= 1000
    ):
        raise CliError("--mpp-y must be finite and in (0, 1000]")

    stages = _parse_pipeline(args.pipeline)
    if (args.level_width is None) != (args.level_height is None):
        raise CliError("provide both --level-width and --level-height")
    measured_shape = args.level_width is not None
    if measured_shape:
        if not 1 <= args.level_width <= args.width or not 1 <= args.level_height <= args.height:
            raise CliError("selected-level dimensions must be positive and no larger than level 0")
        level_width, level_height = args.level_width, args.level_height
    else:
        level_width = math.ceil(args.width / args.level_downsample)
        level_height = math.ceil(args.height / args.level_downsample)
    tiles_i = _stable_pathml_count(
        level_height, args.tile_size, args.stride, args.pad
    )
    tiles_j = _stable_pathml_count(
        level_width, args.tile_size, args.stride, args.pad
    )
    tile_count = tiles_i * tiles_j
    if tile_count > args.max_tiles:
        raise CliError(
            f"planned tile count {tile_count} exceeds --max-tiles={args.max_tiles}"
        )

    image_bytes_per_tile = (
        args.tile_size
        * args.tile_size
        * args.channels
        * args.bytes_per_channel
    )
    mask_outputs = sum(
        2 if TRANSFORM_KINDS[stage].startswith("two_instance_masks") else 1
        for stage in stages
        if TRANSFORM_KINDS[stage] in {"mask", "two_instance_masks_deprecated",
                                     "two_instance_masks_network_download"}
    )
    label_outputs = sum(
        TRANSFORM_KINDS[stage] == "label" for stage in stages
    )
    count_outputs = sum(
        TRANSFORM_KINDS[stage] == "counts" for stage in stages
    )
    # h5pathManager.add_tile casts both tile arrays and masks to float16.
    # The input dtype can differ from the stored dtype.
    storage_image_bytes_per_tile = args.tile_size * args.tile_size * args.channels * 2
    mask_bytes_per_tile = args.tile_size * args.tile_size * mask_outputs * 2
    estimated_payload_bytes = tile_count * (
        storage_image_bytes_per_tile + mask_bytes_per_tile
    )
    estimated_payload_gib = estimated_payload_bytes / 1024**3
    if estimated_payload_gib > args.max_output_gib:
        raise CliError(
            f"estimated uncompressed payload {estimated_payload_gib:.3f} GiB "
            f"exceeds --max-output-gib={args.max_output_gib}"
        )

    overlap = max(0, args.tile_size - args.stride)
    gap = max(0, args.stride - args.tile_size)
    warnings: list[str] = []
    if args.level_downsample != 1 and not measured_shape:
        warnings.append(
            "Selected-level shape is estimated from downsample; provide exact "
            "--level-width and --level-height from the backend for tile counts."
        )
    if not args.level_downsample.is_integer():
        warnings.append(
            "PathML 3.0.8 OpenSlideBackend truncates the region-origin downsample "
            "to int; use level 0 or an integral-downsample level for extraction."
        )
    if mask_outputs:
        warnings.append(
            "h5path casts masks to float16; instance IDs above 2048 can lose "
            "identity. Keep authoritative integer masks separately. Mask-stage "
            "counts may overestimate stored masks when stages reuse a name."
        )
    if count_outputs:
        warnings.append("AnnData/count storage is not included in the payload estimate.")
    if args.pad:
        warnings.append(
            "PathML 3.0.8 padding uses backend-specific count arithmetic and "
            "zero-filled edges; verify a synthetic case."
        )
    if overlap:
        warnings.append(
            "Overlapping tiles duplicate pixels/objects; define stitching and "
            "deduplication before counting."
        )
    if gap:
        warnings.append("Stride exceeds tile size, leaving unprocessed gaps.")
    if "SegmentMIF" in stages:
        warnings.append("SegmentMIF is deprecated and needs a separate DeepCell stack.")
    if "SegmentMIFRemote" in stages:
        warnings.append(
            "SegmentMIFRemote downloads Mesmer ONNX from Hugging Face at construction; "
            "explicit network consent is required."
        )
    if args.level_downsample != 1:
        warnings.append(
            "Area thresholds and morphology kernels are in selected-level pixels."
        )

    physical_tile_um: list[float] | None = None
    if args.mpp_x is not None and args.mpp_y is not None:
        physical_tile_um = [
            args.tile_size * args.level_downsample * args.mpp_y,
            args.tile_size * args.level_downsample * args.mpp_x,
        ]

    return {
        "pathml_version_modelled": "3.0.8",
        "input_level0_shape_hw": [args.height, args.width],
        "level_downsample": args.level_downsample,
        "planned_level_shape_hw": [level_height, level_width],
        "level_shape_source": "supplied_backend_dimensions" if measured_shape else "downsample_estimate",
        "tile_size_hw": [args.tile_size, args.tile_size],
        "stride_ij": [args.stride, args.stride],
        "pad": args.pad,
        "tiles_ij": [tiles_i, tiles_j],
        "tile_count": tile_count,
        "overlap_pixels_per_axis": overlap,
        "gap_pixels_per_axis": gap,
        "pipeline": [
            {"name": stage, "kind": TRANSFORM_KINDS[stage]} for stage in stages
        ],
        "expected_mask_outputs_per_tile": mask_outputs,
        "expected_label_outputs_per_tile": label_outputs,
        "expected_count_outputs_per_tile": count_outputs,
        "input_image_bytes_per_tile": image_bytes_per_tile,
        "storage_image_bytes_per_tile": storage_image_bytes_per_tile,
        "storage_mask_bytes_per_tile": mask_bytes_per_tile,
        "storage_dtype": "float16",
        "estimated_uncompressed_payload_gib": round(estimated_payload_gib, 6),
        "physical_tile_size_um_yx": physical_tile_um,
        "within_bounds": True,
        "warnings": warnings,
        "note": (
            "This is a dry-run estimate. It does not open a slide, import PathML, "
            "measure compression, or predict transform/model workspace memory. "
            "Payload models h5path float16 images/masks at the supplied channel "
            "count; counts, labels, metadata, and channel/shape changes are excluded."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate PathML 3.0.8 tile counts and payload bounds without "
            "opening a slide or importing PathML."
        )
    )
    parser.add_argument("--width", type=int, required=True, help="level-0 width")
    parser.add_argument("--height", type=int, required=True, help="level-0 height")
    parser.add_argument("--level-downsample", type=float, default=1.0)
    parser.add_argument("--level-width", type=int, help="exact selected-level backend width")
    parser.add_argument("--level-height", type=int, help="exact selected-level backend height")
    parser.add_argument("--tile-size", type=int, default=256)
    parser.add_argument("--stride", type=int, default=256)
    parser.add_argument("--pad", action="store_true")
    parser.add_argument("--channels", type=int, default=3)
    parser.add_argument("--bytes-per-channel", type=int, default=1)
    parser.add_argument(
        "--pipeline",
        help="comma-separated stable transform class names in execution order",
    )
    parser.add_argument("--mpp-x", type=float)
    parser.add_argument("--mpp-y", type=float)
    parser.add_argument("--max-tiles", type=int, default=1_000_000)
    parser.add_argument("--max-output-gib", type=float, default=1024.0)
    parser.add_argument("--output")
    parser.add_argument("--root", default=".")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = make_plan(args)
    emit_json(report, output=args.output, root=args.root, force=args.force)


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
