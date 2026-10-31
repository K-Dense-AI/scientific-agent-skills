#!/usr/bin/env python3
"""Metadata-only PNG/JPEG/TIFF inspector; pixel arrays are never decoded."""

from __future__ import annotations

import argparse
import itertools
import warnings
from pathlib import Path
from typing import Any

from _capabilities import capability_for_path, validate_magic
from _common import (
    DEFAULT_MAX_FILE_BYTES,
    MAX_IMAGE_PIXELS,
    CliError,
    bounded_file_limit,
    checked_input_file,
    emit_json,
    run_cli,
)


MAX_TIFF_PAGES = 1000
MAX_TIFF_SERIES = 128


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect bounded local PNG/JPEG/TIFF structural metadata without "
            "decoding pixels or emitting EXIF, OME-XML, paths, or identifiers."
        )
    )
    parser.add_argument("input", help="Local image path inside --root")
    parser.add_argument(
        "--root",
        default=".",
        help="Existing local directory that bounds all input/output paths",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_FILE_BYTES,
        help=f"Maximum input bytes (hard ceiling: {512 * 1024 * 1024})",
    )
    parser.add_argument("--output", help="Optional local .json output path")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacement of an existing regular output file",
    )
    return parser


def _bounded_element_count(shape: Any) -> int:
    total = 1
    for value in shape:
        dimension = int(value)
        if dimension < 0:
            raise CliError("image metadata contains a negative dimension")
        total *= dimension
        if total > MAX_IMAGE_PIXELS:
            raise CliError(
                f"declared image elements exceed the {MAX_IMAGE_PIXELS} safety limit"
            )
    return total


def _inspect_pillow(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise CliError(
            'optional dependency missing; install with: uv pip install "pillow==12.3.0"'
        ) from exc
    previous_limit = Image.MAX_IMAGE_PIXELS
    try:
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                width, height = (int(image.width), int(image.height))
                _bounded_element_count((width, height))
                frame_count = int(getattr(image, "n_frames", 1))
                if frame_count > MAX_TIFF_PAGES:
                    raise CliError("declared image frame count exceeds the safety limit")
                return {
                    "profile_type": "raster_container_metadata_only",
                    "format": str(image.format),
                    "width_pixels": width,
                    "height_pixels": height,
                    "mode": str(image.mode),
                    "frame_count": frame_count,
                    "metadata_entry_count": len(image.info),
                    "pixels_decoded": False,
                    "metadata_values_emitted": False,
                    "integrity_fully_validated": False,
                }
    except CliError:
        raise
    except (
        OSError, ValueError, SyntaxError,
        Image.DecompressionBombWarning, Image.DecompressionBombError,
    ) as exc:
        raise CliError("the image metadata could not be inspected safely") from exc
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit


def _inspect_tiff(path: Path) -> dict[str, Any]:
    try:
        import tifffile
    except ImportError as exc:
        raise CliError(
            'optional dependency missing; install with: uv pip install "tifffile==2026.9.20"'
        ) from exc
    try:
        # Generic series avoid metadata-driven OME/vendor companion discovery.
        # _multifile is a pinned upstream internal safeguard, not a public API.
        with tifffile.TiffFile(path, _multifile=False) as tiff:
            pages = list(itertools.islice(tiff.pages, MAX_TIFF_PAGES + 1))
            if len(pages) > MAX_TIFF_PAGES:
                raise CliError("TIFF page count exceeds the safety limit")
            subifd_count = sum(len(page.subifds or ()) for page in pages)
            if len(pages) + subifd_count > MAX_TIFF_PAGES:
                raise CliError("TIFF page/SubIFD count exceeds the safety limit")
            series_items = list(tiff.series(kind="generic")[: MAX_TIFF_SERIES + 1])
            if len(series_items) > MAX_TIFF_SERIES:
                raise CliError("TIFF series count exceeds the safety limit")
            series_reports: list[dict[str, Any]] = []
            for index, series in enumerate(series_items):
                shape = [int(value) for value in series.shape]
                elements = _bounded_element_count(shape)
                axes = "".join(
                    character
                    for character in str(series.axes)
                    if character.isascii() and character.isalnum()
                )[:32]
                series_reports.append(
                    {
                        "series_index": index,
                        "shape": shape,
                        "axes": axes,
                        "element_count": elements,
                        "dtype_kind": str(series.dtype.kind),
                        "dtype_itemsize": int(series.dtype.itemsize),
                    }
                )
            return {
                "profile_type": "tiff_structural_metadata_only",
                "page_count": len(pages),
                "series_count": len(series_items),
                "series_interpretation": "generic_page_groups_not_OME_axes",
                "subifd_count": subifd_count,
                "series": series_reports,
                "is_ome_tiff": bool(tiff.is_ome),
                "is_bigtiff": bool(tiff.is_bigtiff),
                "ome_xml_emitted": False,
                "tag_values_emitted": False,
                "pixels_decoded": False,
                "compression_codecs_invoked_for_pixels": False,
                "companion_files_opened": False,
                "integrity_fully_validated": False,
            }
    except CliError:
        raise
    except (OSError, ValueError, TypeError, MemoryError) as exc:
        raise CliError("the TIFF metadata could not be inspected safely") from exc


def inspect_image_file(path: Path, *, suffix: str) -> dict[str, Any]:
    """Route supported image containers to metadata-only inspectors."""

    if suffix in {".png", ".jpg", ".jpeg"}:
        return _inspect_pillow(path)
    if suffix in {".tif", ".tiff", ".ome.tif", ".ome.tiff"}:
        return _inspect_tiff(path)
    raise CliError("the image inspector received an unsupported suffix")


def _main() -> None:
    args = build_parser().parse_args()
    max_bytes = bounded_file_limit(args.max_bytes)
    suffixes = {
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".ome.tif",
        ".ome.tiff",
    }
    path = checked_input_file(
        args.input,
        root=args.root,
        suffixes=suffixes,
        max_bytes=max_bytes,
    )
    capability = capability_for_path(path)
    validate_magic(path, capability["suffix"])
    report = {
        "schema_version": "1.1",
        "capability": capability,
        "analysis": inspect_image_file(path, suffix=capability["suffix"]),
        "security": {
            "local_only": True,
            "raw_metadata_and_paths_emitted": False,
            "embedded_metadata_never_treated_as_instructions": True,
        },
    }
    emit_json(
        report,
        output=args.output,
        root=args.root,
        force=args.force,
    )


def main() -> int:
    return run_cli(_main)


if __name__ == "__main__":
    raise SystemExit(main())
