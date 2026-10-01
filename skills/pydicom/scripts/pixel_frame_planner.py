#!/usr/bin/env python3
"""Plan bounded DICOM frame decoding from metadata without loading pixels."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

from _common import (
    DEFAULT_MAX_DECOMPRESSED_BYTES,
    DEFAULT_MAX_FRAMES,
    DEFAULT_MAX_INPUT_BYTES,
    HARD_MAX_DECOMPRESSED_BYTES,
    HARD_MAX_FRAMES,
    HARD_MAX_INPUT_BYTES,
    SCHEMA_VERSION,
    ToolError,
    atomic_write,
    bounded_int,
    checked_input,
    checked_output,
    emit_json,
    fail_json,
    json_bytes,
    parse_size,
    paths_overlap,
    pixel_plan,
    require_pydicom,
    safe_dcmread,
    valid_uid,
)

TOOL = "pixel_frame_planner"
FRAME_TOKEN = re.compile(r"^(\d+)(?:-(\d+))?$")
PIXEL_TAGS = [
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
    "SharedFunctionalGroupsSequence",
    "PerFrameFunctionalGroupsSequence",
    "RealWorldValueMappingSequence",
    "ICCProfile",
    "BurnedInAnnotation",
    "RecognizableVisualFeatures",
]


def parse_frame_selection(
    specification: str, *, total_frames: int, max_selected: int
) -> list[int]:
    if specification.strip().casefold() == "all":
        if total_frames > max_selected:
            raise ToolError("'all' exceeds the selected-frame limit")
        return list(range(total_frames))
    selected: set[int] = set()
    for token in specification.split(","):
        token = token.strip()
        match = FRAME_TOKEN.fullmatch(token)
        if not match:
            raise ToolError(
                "frames must use comma-separated indices or inclusive ranges"
            )
        start = int(match.group(1))
        stop = int(match.group(2) or start)
        if stop < start:
            raise ToolError("frame ranges must be ascending")
        if stop >= total_frames:
            raise ToolError("selected frame is outside the declared range")
        if stop - start + 1 > max_selected:
            raise ToolError("one frame range exceeds the selected-frame limit")
        selected.update(range(start, stop + 1))
        if len(selected) > max_selected:
            raise ToolError("selected-frame limit exceeded")
    if not selected:
        raise ToolError("at least one frame must be selected")
    return sorted(selected)


def plan(args: argparse.Namespace) -> dict[str, Any]:
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
    max_frames = bounded_int(
        args.max_frames,
        name="max_frames",
        minimum=1,
        maximum=HARD_MAX_FRAMES,
    )
    max_selected = bounded_int(
        args.max_selected_frames,
        name="max_selected_frames",
        minimum=1,
        maximum=100_000,
    )
    source = checked_input(
        args.input,
        root=args.root,
        kind="file",
        max_bytes=max_input_bytes,
    )
    dataset = safe_dcmread(
        source,
        stop_before_pixels=True,
        force=False,
        specific_tags=PIXEL_TAGS,
    )
    metadata_plan = pixel_plan(
        dataset,
        max_frames=max_frames,
        max_decompressed_bytes=max_decompressed_bytes,
    )
    selected = parse_frame_selection(
        args.frames,
        total_frames=metadata_plan["frames"],
        max_selected=max_selected,
    )
    selected_bytes = metadata_plan["bytes_per_frame"] * len(selected)
    if selected_bytes > max_decompressed_bytes:
        raise ToolError("selected decoded frames exceed the configured byte limit")

    pydicom = require_pydicom()
    transfer_value = str(dataset.file_meta.get("TransferSyntaxUID", ""))
    if not valid_uid(transfer_value):
        raise ToolError("Transfer Syntax UID is absent or invalid")
    transfer = pydicom.uid.UID(transfer_value)
    try:
        transfer_compressed = bool(transfer.is_compressed)
    except ValueError as exc:
        raise ToolError("UID is not recognized as a transfer syntax") from exc
    photometric = str(dataset.get("PhotometricInterpretation", ""))
    samples = metadata_plan["samples_per_pixel"]
    one_frame_shape = (
        [metadata_plan["rows"], metadata_plan["columns"]]
        if samples == 1
        else [metadata_plan["rows"], metadata_plan["columns"], samples]
    )
    transforms: list[str] = []
    if (
        "ModalityLUTSequence" in dataset
        or "RescaleSlope" in dataset
        or "RescaleIntercept" in dataset
    ):
        transforms.append("optional modality LUT/rescale")
    if "VOILUTSequence" in dataset or (
        "WindowCenter" in dataset and "WindowWidth" in dataset
    ):
        transforms.append("optional VOI LUT/window after modality transform")
    if photometric in {"YBR_FULL", "YBR_FULL_422"}:
        transforms.append("default pydicom YCbCr-to-RGB conversion unless raw=True")
    elif photometric.startswith("YBR"):
        transforms.append("codec-specific color conversion requires validation")
    if photometric == "PALETTE COLOR":
        transforms.append("palette color LUT required for RGB rendering")
    if photometric == "MONOCHROME1":
        transforms.append("presentation inversion may be required")
    if any(keyword in dataset for keyword in (
        "SharedFunctionalGroupsSequence", "PerFrameFunctionalGroupsSequence",
        "RealWorldValueMappingSequence",
    )):
        transforms.append("frame-specific functional groups/real-world mapping require separate review")

    return {
        "burned_in_annotation": str(
            dataset.get("BurnedInAnnotation", "ABSENT")
        ).upper(),
        "decode_plan": {
            "all_frames_shape": metadata_plan["shape"],
            "bytes_per_frame_estimate": metadata_plan["bytes_per_frame"],
            "frame_indices": selected,
            "one_frame_shape": one_frame_shape,
            "selected_decoded_bytes_estimate": selected_bytes,
            "use_iter_pixels": len(selected) > 1,
            "use_pixel_array_index": len(selected) == 1,
        },
        "metadata": {
            "bits_allocated": metadata_plan["bits_allocated"],
            "columns": metadata_plan["columns"],
            "frames": metadata_plan["frames"],
            "modality": str(dataset.get("Modality", "UNSPECIFIED")),
            "photometric_interpretation": photometric,
            "rows": metadata_plan["rows"],
            "samples_per_pixel": samples,
            "transfer_syntax": {
                "compressed": transfer_compressed,
                "name": transfer.name,
                "uid": str(transfer),
            },
        },
        "network_accessed": False,
        "ok": True,
        "pixel_data_loaded": False,
        "recognizable_visual_features": str(
            dataset.get("RecognizableVisualFeatures", "ABSENT")
        ).upper(),
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "transforms_in_semantic_order": transforms,
        "warnings": [
            *metadata_plan["warnings"],
            "Estimates use metadata and do not prove that the codestream matches it.",
            "Pixel decoding can expose PHI and requires independent correctness checks.",
            "Frame rendering is non-diagnostic unless validated in an appropriate system.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan bounded DICOM pixel frame access, shapes, byte limits, and "
            "display transforms from metadata without decoding pixels."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pixel_frame_planner.py image.dcm
  python pixel_frame_planner.py multi.dcm --frames 0,2-4
  python pixel_frame_planner.py multi.dcm --frames all --max-selected-frames 20

Metadata can be inconsistent with compressed codestreams. This is a resource
and semantics plan, not diagnostic or pixel-correctness validation.
""",
    )
    parser.add_argument("input", help="Local DICOM input file")
    parser.add_argument("--root", default=".", help="Existing local I/O root")
    parser.add_argument(
        "--frames",
        default="0",
        help="Comma-separated zero-based indices/ranges, or 'all' (default: 0)",
    )
    parser.add_argument("--output", "-o", help="Private JSON plan path")
    parser.add_argument(
        "--max-frames",
        type=int,
        default=DEFAULT_MAX_FRAMES,
        help=f"Maximum declared frames (default: {DEFAULT_MAX_FRAMES})",
    )
    parser.add_argument(
        "--max-selected-frames",
        type=int,
        default=100,
        help="Maximum selected frames (default: 100)",
    )
    parser.add_argument(
        "--max-input-bytes",
        default=str(DEFAULT_MAX_INPUT_BYTES),
        help="Maximum DICOM input bytes",
    )
    parser.add_argument(
        "--max-decompressed-bytes",
        default=str(DEFAULT_MAX_DECOMPRESSED_BYTES),
        help="Maximum estimated decoded bytes",
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite an existing plan only"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = plan(args)
        if args.output:
            destination = checked_output(args.output, root=args.root, force=args.force)
            source = checked_input(
                args.input,
                root=args.root,
                kind="file",
                max_bytes=parse_size(
                    args.max_input_bytes,
                    name="max_input_bytes",
                    maximum=HARD_MAX_INPUT_BYTES,
                ),
            )
            if paths_overlap(source, destination):
                raise ToolError("plan must not overwrite its input")
            atomic_write(destination, json_bytes(report), force=args.force)
            emit_json({"ok": True, "plan_written": True, "tool": TOOL})
        else:
            emit_json(report)
        return 0
    except Exception as exc:  # noqa: BLE001 - sanitize unexpected library errors
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
