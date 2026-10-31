#!/usr/bin/env python3
"""Compute bounded synthetic/local image QC and a coarse tissue-like mask."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from _common import (
    CliError,
    MAX_IMAGE_BYTES,
    MAX_PIXELS,
    atomic_write_bytes,
    checked_input_file,
    checked_root,
    emit_json,
    run_cli,
)


IMAGE_SUFFIXES = {".ppm", ".pgm", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
WHITESPACE = b" \t\r\n\f\v"


def _next_token(payload: bytes, offset: int) -> tuple[bytes, int]:
    length = len(payload)
    while offset < length:
        if payload[offset] in WHITESPACE:
            offset += 1
            continue
        if payload[offset] == ord("#"):
            newline = payload.find(b"\n", offset)
            if newline < 0:
                raise CliError("unterminated PNM comment")
            offset = newline + 1
            continue
        break
    start = offset
    while offset < length and payload[offset] not in WHITESPACE:
        if payload[offset] == ord("#"):
            break
        offset += 1
    if start == offset:
        raise CliError("invalid PNM header")
    return payload[start:offset], offset


def _read_pnm(path: Path, max_pixels: int) -> tuple[int, int, bytes]:
    payload = path.read_bytes()
    magic, offset = _next_token(payload, 0)
    width_token, offset = _next_token(payload, offset)
    height_token, offset = _next_token(payload, offset)
    maxval_token, offset = _next_token(payload, offset)
    if magic not in {b"P5", b"P6"}:
        raise CliError("only binary P5/P6 PNM images are supported without Pillow")
    try:
        width = int(width_token)
        height = int(height_token)
        maxval = int(maxval_token)
    except ValueError as exc:
        raise CliError("PNM dimensions and max value must be integers") from exc
    if width <= 0 or height <= 0 or width * height > max_pixels:
        raise CliError(f"PNM pixel count must be in [1, {max_pixels}]")
    if not 1 <= maxval <= 255:
        raise CliError("PNM max value must be between 1 and 255")
    if offset >= len(payload) or payload[offset] not in WHITESPACE:
        raise CliError("PNM header must end with whitespace")
    if payload[offset : offset + 2] == b"\r\n":
        offset += 2
    else:
        offset += 1
    channels = 3 if magic == b"P6" else 1
    expected = width * height * channels
    pixels = payload[offset:]
    if len(pixels) != expected:
        raise CliError(
            f"PNM pixel payload is {len(pixels)} bytes; expected {expected}"
        )
    if pixels and max(pixels) > maxval:
        raise CliError("PNM pixel value exceeds the declared maximum")
    if maxval != 255:
        pixels = bytes(round(value * 255 / maxval) for value in pixels)
    if channels == 1:
        rgb = bytearray(width * height * 3)
        for index, value in enumerate(pixels):
            start = index * 3
            rgb[start : start + 3] = bytes((value, value, value))
        pixels = bytes(rgb)
    return width, height, pixels


def _read_with_pillow(path: Path, max_pixels: int) -> tuple[int, int, bytes]:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise CliError(
            "Pillow is required for PNG/JPEG/TIFF input; use a P5/P6 PNM "
            "file for dependency-free inspection"
        ) from exc
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with Image.open(path) as image:
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > max_pixels:
                raise CliError(f"image pixel count must be in [1, {max_pixels}]")
            rgb = image.convert("RGB")
            return int(width), int(height), rgb.tobytes()
    except CliError:
        raise
    except Exception as exc:
        raise CliError(f"cannot decode bounded image: {exc}") from exc


def read_image(path: Path, max_pixels: int) -> tuple[int, int, bytes]:
    """Read a bounded RGB image with PNM support in the standard library."""

    if path.suffix.lower() in {".ppm", ".pgm"}:
        return _read_pnm(path, max_pixels)
    return _read_with_pillow(path, max_pixels)


def synthetic_image(
    width: int,
    height: int,
    tissue_fraction: float,
) -> bytes:
    """Create a deterministic white image with a centered pink tissue region."""

    if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
        raise CliError(f"synthetic pixel count must be in [1, {MAX_PIXELS}]")
    if not math.isfinite(tissue_fraction) or not 0 <= tissue_fraction <= 1:
        raise CliError("--tissue-fraction must be finite and in [0, 1]")
    pixels = bytearray(bytes((245, 245, 245)) * (width * height))
    scale = math.sqrt(tissue_fraction)
    tissue_width = min(width, round(width * scale))
    tissue_height = min(height, round(height * scale))
    left = (width - tissue_width) // 2
    top = (height - tissue_height) // 2
    for row in range(top, top + tissue_height):
        for column in range(left, left + tissue_width):
            offset = (row * width + column) * 3
            pixels[offset : offset + 3] = bytes((180, 75, 135))
    return bytes(pixels)


def calculate_qc(
    width: int,
    height: int,
    pixels: bytes,
    *,
    saturation_threshold: float,
    brightness_threshold: float,
) -> tuple[dict[str, Any], bytes]:
    """Calculate simple bounded QC metrics and an 8-bit binary mask."""

    if len(pixels) != width * height * 3:
        raise CliError("RGB payload length does not match dimensions")
    if not math.isfinite(saturation_threshold) or not (
        0 <= saturation_threshold <= 1
    ):
        raise CliError("--saturation-threshold must be finite and in [0, 1]")
    if not math.isfinite(brightness_threshold) or not (
        0 <= brightness_threshold <= 1
    ):
        raise CliError("--brightness-threshold must be finite and in [0, 1]")

    count = width * height
    sums = [0, 0, 0]
    tissue = 0
    white = 0
    dark = 0
    saturated_channel = 0
    mask = bytearray(count)
    for pixel_index in range(count):
        offset = pixel_index * 3
        red, green, blue = pixels[offset : offset + 3]
        sums[0] += red
        sums[1] += green
        sums[2] += blue
        high = max(red, green, blue)
        low = min(red, green, blue)
        brightness = high / 255.0
        saturation = 0.0 if high == 0 else (high - low) / high
        is_tissue = (
            saturation >= saturation_threshold
            and brightness <= brightness_threshold
        )
        if is_tissue:
            tissue += 1
            mask[pixel_index] = 255
        if brightness >= 0.90 and saturation <= 0.10:
            white += 1
        if brightness <= 0.15:
            dark += 1
        if high == 255:
            saturated_channel += 1

    report = {
        "width": width,
        "height": height,
        "pixel_count": count,
        "mean_rgb": [round(total / count, 6) for total in sums],
        "tissue_like_fraction": round(tissue / count, 8),
        "white_like_fraction": round(white / count, 8),
        "dark_fraction": round(dark / count, 8),
        "any_channel_clipped_high_fraction": round(saturated_channel / count, 8),
        "mask_rule": {
            "minimum_saturation": saturation_threshold,
            "maximum_brightness": brightness_threshold,
        },
        "clinical_use": False,
        "note": (
            "This coarse RGB heuristic is for synthetic/pilot QC only; it is not "
            "PathML TissueDetectionHE and is not a diagnostic quality decision."
        ),
    }
    return report, bytes(mask)


def _write_mask(
    mask: bytes,
    width: int,
    height: int,
    *,
    destination: str,
    root: str,
    force: bool,
) -> None:
    header = f"P5\n{width} {height}\n255\n".encode("ascii")
    atomic_write_bytes(
        Path(destination),
        header + mask,
        root=root,
        suffixes={".pgm"},
        force=force,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compute bounded synthetic/local RGB QC and a coarse tissue-like "
            "mask. No network access."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    synthetic = subparsers.add_parser(
        "synthetic", help="generate an in-memory synthetic image and report QC"
    )
    synthetic.add_argument("--width", type=int, default=256)
    synthetic.add_argument("--height", type=int, default=256)
    synthetic.add_argument("--tissue-fraction", type=float, default=0.5)
    synthetic.add_argument("--saturation-threshold", type=float, default=0.15)
    synthetic.add_argument("--brightness-threshold", type=float, default=0.95)
    synthetic.add_argument("--mask-output")
    synthetic.add_argument("--output")
    synthetic.add_argument("--root", default=".")
    synthetic.add_argument("--force", action="store_true")

    inspect = subparsers.add_parser(
        "inspect", help="inspect a bounded local raster or P5/P6 PNM image"
    )
    inspect.add_argument("--image", required=True)
    inspect.add_argument("--root", default=".")
    inspect.add_argument("--max-pixels", type=int, default=MAX_PIXELS)
    inspect.add_argument("--max-image-bytes", type=int, default=MAX_IMAGE_BYTES)
    inspect.add_argument("--saturation-threshold", type=float, default=0.15)
    inspect.add_argument("--brightness-threshold", type=float, default=0.95)
    inspect.add_argument("--mask-output")
    inspect.add_argument("--output")
    inspect.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = checked_root(args.root)
    if args.command == "synthetic":
        width = args.width
        height = args.height
        pixels = synthetic_image(width, height, args.tissue_fraction)
        source = "synthetic"
    else:
        if not 1 <= args.max_pixels <= 100_000_000:
            raise CliError("--max-pixels must be between 1 and 100000000")
        if not 1 <= args.max_image_bytes <= MAX_IMAGE_BYTES:
            raise CliError(
                f"--max-image-bytes must be between 1 and {MAX_IMAGE_BYTES}"
            )
        image = checked_input_file(
            args.image,
            root=root,
            suffixes=IMAGE_SUFFIXES,
            max_bytes=args.max_image_bytes,
        )
        width, height, pixels = read_image(image, args.max_pixels)
        source = "local_file"

    report, mask = calculate_qc(
        width,
        height,
        pixels,
        saturation_threshold=args.saturation_threshold,
        brightness_threshold=args.brightness_threshold,
    )
    report["source"] = source
    report["path_redacted"] = True
    if args.mask_output:
        _write_mask(
            mask,
            width,
            height,
            destination=args.mask_output,
            root=str(root),
            force=args.force,
        )
        report["mask_written"] = True
    else:
        report["mask_written"] = False
    emit_json(report, output=args.output, root=root, force=args.force)


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
