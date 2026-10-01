#!/usr/bin/env python3
"""Render one bounded DICOM frame for non-diagnostic review."""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Any

from _common import (
    DEFAULT_MAX_DECOMPRESSED_BYTES,
    DEFAULT_MAX_INPUT_BYTES,
    DEFAULT_MAX_OUTPUT_BYTES,
    HARD_MAX_DECOMPRESSED_BYTES,
    HARD_MAX_INPUT_BYTES,
    HARD_MAX_OUTPUT_BYTES,
    SCHEMA_VERSION,
    ToolError,
    atomic_write,
    checked_input,
    checked_output,
    emit_json,
    fail_json,
    frame_count,
    parse_size,
    paths_overlap,
    pixel_plan,
    require_pixel_stack,
    safe_dcmread,
    safe_plugin_name,
)

TOOL = "dicom_to_image"
METADATA_TAGS = [
    "SOPClassUID",
    "Modality",
    "Rows",
    "Columns",
    "NumberOfFrames",
    "SamplesPerPixel",
    "PhotometricInterpretation",
    "PlanarConfiguration",
    "BitsAllocated",
    "BitsStored",
    "HighBit",
    "PixelRepresentation",
    "ModalityLUTSequence",
    "RescaleIntercept",
    "RescaleSlope",
    "RescaleType",
    "VOILUTSequence",
    "WindowCenter",
    "WindowWidth",
    "VOILUTFunction",
    "PresentationLUTShape",
    "PresentationLUTSequence",
    "SharedFunctionalGroupsSequence",
    "PerFrameFunctionalGroupsSequence",
    "RealWorldValueMappingSequence",
    "RedPaletteColorLookupTableDescriptor",
    "GreenPaletteColorLookupTableDescriptor",
    "BluePaletteColorLookupTableDescriptor",
    "RedPaletteColorLookupTableData",
    "GreenPaletteColorLookupTableData",
    "BluePaletteColorLookupTableData",
    "SegmentedRedPaletteColorLookupTableData",
    "SegmentedGreenPaletteColorLookupTableData",
    "SegmentedBluePaletteColorLookupTableData",
    "ICCProfile",
    "BurnedInAnnotation",
    "RecognizableVisualFeatures",
]


def _infer_format(path: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    suffix = Path(path).suffix.casefold()
    mapping = {
        ".png": "PNG",
        ".tif": "TIFF",
        ".tiff": "TIFF",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
    }
    if suffix not in mapping:
        raise ToolError("output extension must be .png, .tif, .tiff, .jpg, or .jpeg")
    return mapping[suffix]


def _normalize(array: Any, *, numpy: Any, bit_depth: int) -> tuple[Any, dict[str, Any]]:
    maximum = 255 if bit_depth == 8 else 65535
    dtype = numpy.uint8 if bit_depth == 8 else numpy.uint16
    work = numpy.asarray(array)
    finite = numpy.isfinite(work)
    finite_count = int(finite.sum())
    if finite_count == 0:
        raise ToolError("decoded frame contains no finite pixel values")
    finite_values = work[finite]
    low = float(finite_values.min())
    high = float(finite_values.max())
    converted = work.astype(numpy.float64, copy=True)
    converted[~finite] = low
    if high > low:
        converted = (converted - low) / (high - low)
    else:
        converted.fill(0)
    converted = numpy.clip(converted * maximum, 0, maximum).astype(dtype)
    return converted, {
        "finite_values": finite_count,
        "input_max": high,
        "input_min": low,
        "mapping": "per-frame linear min-max",
    }


def _apply_grayscale_transforms(
    array: Any,
    dataset: Any,
    *,
    modality_transform: str,
    voi: str,
    voi_index: int,
) -> tuple[Any, list[str]]:
    from pydicom.pixels import (
        apply_modality_lut,
        apply_voi,
        apply_voi_lut,
        apply_windowing,
    )

    applied: list[str] = []
    if ("RescaleSlope" in dataset) != ("RescaleIntercept" in dataset):
        raise ToolError("Rescale Slope and Intercept must be supplied together")
    if modality_transform == "none" and voi != "none" and (
        "ModalityLUTSequence" in dataset or "RescaleSlope" in dataset
    ):
        raise ToolError("VOI requires the modality transform; use --voi none to bypass both")
    if modality_transform == "auto" and (
        "ModalityLUTSequence" in dataset
        or "RescaleSlope" in dataset
        or "RescaleIntercept" in dataset
    ):
        array = apply_modality_lut(array, dataset)
        applied.append("modality LUT/rescale")
    if voi == "none":
        return array, applied
    if voi == "auto":
        if "VOILUTSequence" in dataset or (
            "WindowCenter" in dataset and "WindowWidth" in dataset
        ):
            array = apply_voi_lut(array, dataset, index=voi_index)
            applied.append("VOI LUT/window")
        return array, applied
    if voi == "window":
        if "WindowCenter" not in dataset or "WindowWidth" not in dataset:
            raise ToolError("window VOI requested but Window Center/Width is absent")
        array = apply_windowing(array, dataset, index=voi_index)
        applied.append("window")
        return array, applied
    if "VOILUTSequence" not in dataset:
        raise ToolError("VOI LUT requested but VOI LUT Sequence is absent")
    array = apply_voi(array, dataset, index=voi_index)
    applied.append("VOI LUT")
    return array, applied


def render_frame(args: argparse.Namespace) -> dict[str, Any]:
    if not args.acknowledge_pixel_phi:
        raise ToolError(
            "conversion requires --acknowledge-pixel-phi because pixels may identify a person"
        )
    max_input_bytes = parse_size(
        args.max_input_bytes,
        name="max_input_bytes",
        maximum=HARD_MAX_INPUT_BYTES,
    )
    max_decompressed_bytes = parse_size(
        args.max_decompressed_bytes,
        name="max_decompressed_bytes",
        maximum=HARD_MAX_DECOMPRESSED_BYTES,
    )
    max_output_bytes = parse_size(
        args.max_output_bytes,
        name="max_output_bytes",
        maximum=HARD_MAX_OUTPUT_BYTES,
    )
    source = checked_input(
        args.input,
        root=args.root,
        kind="file",
        max_bytes=max_input_bytes,
    )
    destination = checked_output(args.output, root=args.root, force=args.force)
    if paths_overlap(source, destination):
        raise ToolError("image output must not overwrite its DICOM input")
    image_format = _infer_format(args.output, args.format)
    if image_format == "JPEG" and not args.allow_lossy_output:
        raise ToolError("JPEG output requires --allow-lossy-output")
    if image_format == "JPEG" and args.bit_depth != 8:
        raise ToolError("JPEG output supports only --bit-depth 8")

    metadata = safe_dcmread(
        source,
        stop_before_pixels=True,
        force=False,
        specific_tags=METADATA_TAGS,
    )
    if any(keyword in metadata for keyword in (
        "SharedFunctionalGroupsSequence", "PerFrameFunctionalGroupsSequence",
        "RealWorldValueMappingSequence",
    )):
        raise ToolError(
            "functional-group or real-world-value mapping objects require a "
            "validated frame-specific pipeline; this preview helper supports top-level transforms only"
        )
    frames, frame_warnings = frame_count(metadata)
    if not 0 <= args.frame < frames:
        raise ToolError("requested frame is outside the declared frame range")
    plan = pixel_plan(
        metadata,
        max_frames=max(frames, 1),
        max_decompressed_bytes=HARD_MAX_DECOMPRESSED_BYTES,
    )
    photometric = str(metadata.get("PhotometricInterpretation", ""))
    if photometric not in {
        "MONOCHROME1", "MONOCHROME2", "RGB", "YBR_FULL", "YBR_FULL_422", "PALETTE COLOR"
    }:
        raise ToolError("photometric interpretation is not supported by this preview helper")
    processing_samples = (
        3 if photometric == "PALETTE COLOR" else plan["samples_per_pixel"]
    )
    # Processing can require a float64 working copy in addition to the decoded
    # frame, masks, and output. Bound peak working memory conservatively.
    working_estimate = plan["bytes_per_frame"] + (
        plan["rows"] * plan["columns"] * processing_samples * 40
    )
    if working_estimate > max_decompressed_bytes:
        raise ToolError(
            "estimated one-frame working memory exceeds the configured limit"
        )

    _, numpy, Image = require_pixel_stack()
    from pydicom.pixels import apply_color_lut, apply_presentation_lut, pixel_array

    decoding_plugin = (
        safe_plugin_name(args.decoding_plugin) if args.decoding_plugin else ""
    )
    try:
        array = pixel_array(
            source,
            index=args.frame,
            raw=False,
            decoding_plugin=decoding_plugin,
        )
    except Exception as exc:
        raise ToolError(
            "selected frame could not be decoded with installed pixel plugins"
        ) from exc
    if int(array.nbytes) > max_decompressed_bytes:
        raise ToolError("decoded frame exceeds the configured byte limit")

    samples = int(metadata.get("SamplesPerPixel", 1))
    transforms: list[str] = []
    color_output = samples > 1 or photometric == "PALETTE COLOR"
    if photometric == "PALETTE COLOR":
        try:
            array = apply_color_lut(array, metadata)
        except Exception as exc:
            raise ToolError("palette color LUT could not be applied") from exc
        transforms.append("palette color LUT")
    elif not color_output:
        try:
            array, grayscale_transforms = _apply_grayscale_transforms(
                array,
                metadata,
                modality_transform=args.modality_transform,
                voi=args.voi,
                voi_index=args.voi_index,
            )
        except Exception as exc:
            if isinstance(exc, ToolError):
                raise
            raise ToolError(
                "requested grayscale transform could not be applied"
            ) from exc
        transforms.extend(grayscale_transforms)

    if color_output:
        if array.ndim != 3 or array.shape[-1] not in {3, 4}:
            raise ToolError("decoded color frame has an unexpected shape")
        if array.dtype == numpy.uint8 and bool(numpy.isfinite(array).all()):
            normalized = numpy.asarray(array)
            scale_report = {
                "finite_values": int(array.size),
                "input_max": int(array.max()),
                "input_min": int(array.min()),
                "mapping": "identity uint8",
            }
        else:
            normalized, scale_report = _normalize(array, numpy=numpy, bit_depth=8)
        image = Image.fromarray(normalized)
        if image_format == "JPEG" and image.mode == "RGBA":
            image = image.convert("RGB")
            transforms.append("alpha channel removed for JPEG")
        output_bit_depth = 8
        if photometric.startswith("YBR"):
            transforms.append("pydicom YCbCr-to-RGB decoding")
    else:
        if array.ndim != 2:
            raise ToolError("decoded grayscale frame has an unexpected shape")
        has_presentation = (
            "PresentationLUTSequence" in metadata or "PresentationLUTShape" in metadata
        )
        if has_presentation:
            array = apply_presentation_lut(array, metadata)
            transforms.append("presentation LUT/shape")
        normalized, scale_report = _normalize(
            array, numpy=numpy, bit_depth=args.bit_depth
        )
        if photometric == "MONOCHROME1" and not has_presentation:
            maximum = 255 if args.bit_depth == 8 else 65535
            normalized = maximum - normalized
            transforms.append("MONOCHROME1 inversion")
        image = Image.fromarray(normalized)
        output_bit_depth = args.bit_depth

    buffer = io.BytesIO()
    save_options: dict[str, Any] = {}
    if image_format == "JPEG":
        save_options = {"quality": args.jpeg_quality, "subsampling": 0}
    try:
        image.save(buffer, format=image_format, **save_options)
    except Exception as exc:
        raise ToolError("rendered image could not be encoded") from exc
    payload = buffer.getvalue()
    atomic_write(
        destination,
        payload,
        force=args.force,
        max_bytes=max_output_bytes,
    )

    return {
        "burned_in_annotation": str(
            metadata.get("BurnedInAnnotation", "ABSENT")
        ).upper(),
        "color_output": color_output,
        "decoded_frame_bytes": int(array.nbytes),
        "diagnostic_use": False,
        "frame": args.frame,
        "frames_declared": frames,
        "image_format": image_format,
        "modality": str(metadata.get("Modality", "UNSPECIFIED")),
        "network_accessed": False,
        "ok": True,
        "original_preserved": True,
        "output_bit_depth": output_bit_depth,
        "output_bytes": len(payload),
        "photometric_interpretation": photometric,
        "recognizable_visual_features": str(
            metadata.get("RecognizableVisualFeatures", "ABSENT")
        ).upper(),
        "scale": scale_report,
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "transforms_applied_in_order": transforms,
        "warnings": [
            *frame_warnings,
            "Rendered output is for non-diagnostic review only.",
            "Per-frame min-max scaling is not quantitative and is not comparable across frames.",
            "Pixels may contain burned-in PHI or recognizable visual features.",
            "ICC/presentation-state behavior is not fully reproduced by this helper.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render one bounded DICOM frame to PNG, TIFF, or explicit lossy JPEG "
            "for non-diagnostic review."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Local authorized data only. Pixel data may contain PHI, burned-in annotations,
or recognizable anatomy. This helper is not a diagnostic viewer and does not
establish clinical fidelity.

Examples:
  python dicom_to_image.py input.dcm frame.png --acknowledge-pixel-phi
  python dicom_to_image.py multi.dcm frame5.tiff --frame 5 \\
    --voi window --acknowledge-pixel-phi
  python dicom_to_image.py input.dcm frame.jpg --allow-lossy-output \\
    --acknowledge-pixel-phi
""",
    )
    parser.add_argument("input", help="Local DICOM input file")
    parser.add_argument("output", help="New .png, .tif/.tiff, or .jpg/.jpeg file")
    parser.add_argument("--root", default=".", help="Existing local I/O root")
    parser.add_argument("--format", choices=("PNG", "TIFF", "JPEG"))
    parser.add_argument("--frame", type=int, default=0, help="Zero-based frame index")
    parser.add_argument(
        "--modality-transform",
        choices=("auto", "none"),
        default="auto",
        help="Apply Modality LUT/rescale before VOI when present",
    )
    parser.add_argument(
        "--voi",
        choices=("auto", "none", "window", "lut"),
        default="auto",
        help="VOI policy after modality transformation",
    )
    parser.add_argument(
        "--voi-index",
        type=int,
        default=0,
        help="Index for multi-valued windows or VOI LUTs",
    )
    parser.add_argument(
        "--bit-depth",
        type=int,
        choices=(8, 16),
        default=8,
        help="Grayscale PNG/TIFF output depth (color and JPEG are 8-bit)",
    )
    parser.add_argument(
        "--decoding-plugin",
        default="",
        help="Optional installed pydicom decoding plugin name",
    )
    parser.add_argument(
        "--allow-lossy-output",
        action="store_true",
        help="Required for JPEG output",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        choices=range(1, 96),
        default=95,
        metavar="1..95",
        help="JPEG quality when lossy output is explicitly enabled",
    )
    parser.add_argument(
        "--acknowledge-pixel-phi",
        action="store_true",
        help="Required acknowledgement that pixel data may identify a person",
    )
    parser.add_argument(
        "--max-input-bytes",
        default=str(DEFAULT_MAX_INPUT_BYTES),
        help="Maximum DICOM file bytes (integer or B/KiB/MiB/GiB)",
    )
    parser.add_argument(
        "--max-decompressed-bytes",
        default=str(DEFAULT_MAX_DECOMPRESSED_BYTES),
        help="Maximum estimated one-frame working bytes",
    )
    parser.add_argument(
        "--max-output-bytes",
        default=str(DEFAULT_MAX_OUTPUT_BYTES),
        help="Maximum encoded image bytes",
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite image output, never input"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.frame < 0 or args.voi_index < 0:
            raise ToolError("frame and VOI index must be non-negative")
        report = render_frame(args)
        emit_json(report)
        return 0
    except Exception as exc:  # noqa: BLE001 - sanitize unexpected library errors
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
