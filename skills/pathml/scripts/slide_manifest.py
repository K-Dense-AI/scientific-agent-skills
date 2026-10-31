#!/usr/bin/env python3
"""Validate local slide manifests and inspect allowlisted technical metadata."""

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
    MAX_ROWS,
    PINNED_INSTALL,
    checked_input_file,
    checked_root,
    emit_json,
    parse_name_list,
    run_cli,
    sha256_file,
)


SLIDE_SUFFIXES = {
    ".svs",
    ".tif",
    ".tiff",
    ".ome.tif",
    ".ome.tiff",
    ".bif",
    ".ndpi",
    ".vms",
    ".vmu",
    ".scn",
    ".mrxs",
    ".svslide",
    ".qptiff",
    ".dcm",
    ".dicom",
    ".czi",
    ".vsi",
    ".zvi",
    ".h5",
    ".h5path",
}
OPENSLIDE_SUFFIXES = {
    ".svs",
    ".tif",
    ".tiff",
    ".bif",
    ".ndpi",
    ".vms",
    ".vmu",
    ".scn",
    ".mrxs",
    ".svslide",
}
DICOM_SUFFIXES = {".dcm", ".dicom"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _matched_suffix(path: Path) -> str:
    lowered = path.name.lower()
    matches = [suffix for suffix in SLIDE_SUFFIXES if lowered.endswith(suffix)]
    if not matches:
        raise CliError(f"unsupported slide suffix: {path.suffix.lower() or '<none>'}")
    return max(matches, key=len)


def _validate_identifier(value: str, *, field: str, row_number: int) -> str:
    clean = value.strip()
    if not ID_PATTERN.fullmatch(clean):
        raise CliError(
            f"row {row_number}: {field} must be a pseudonymous identifier "
            "using 1-128 letters, digits, dots, underscores, or hyphens"
        )
    return clean


def validate_manifest(args: argparse.Namespace) -> dict[str, Any]:
    root = checked_root(args.root)
    manifest = checked_input_file(
        args.manifest,
        root=root,
        suffixes={".csv"},
        max_bytes=args.max_manifest_bytes,
    )
    allowed_splits = set(parse_name_list(args.splits, name="--splits"))
    max_slide_bytes = int(args.max_slide_gib * 1024**3)

    slide_ids: set[str] = set()
    resolved_paths: set[Path] = set()
    patient_splits: dict[str, str] = {}
    split_counts: Counter[str] = Counter()
    suffix_counts: Counter[str] = Counter()
    patient_ids: set[str] = set()

    try:
        with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames
            if headers is None:
                raise CliError("manifest has no header")
            normalized_headers = [header.strip() for header in headers]
            if len(normalized_headers) != len(set(normalized_headers)):
                raise CliError("manifest header contains duplicate column names")
            required = {"slide_id", "patient_id", "path"}
            missing = sorted(required - set(normalized_headers))
            if missing:
                raise CliError(
                    f"manifest is missing required columns: {', '.join(missing)}"
                )

            row_count = 0
            for row_count, raw_row in enumerate(reader, start=1):
                if row_count > args.max_rows:
                    raise CliError(f"manifest exceeds --max-rows={args.max_rows}")
                row_number = row_count + 1
                if None in raw_row or any(value is None for value in raw_row.values()):
                    raise CliError(f"row {row_number}: CSV field count does not match header")
                row = {
                    key.strip(): (value or "").strip()
                    for key, value in raw_row.items()
                    if key is not None
                }
                slide_id = _validate_identifier(
                    row["slide_id"], field="slide_id", row_number=row_number
                )
                patient_id = _validate_identifier(
                    row["patient_id"], field="patient_id", row_number=row_number
                )
                if slide_id in slide_ids:
                    raise CliError(f"row {row_number}: duplicate slide_id")
                slide_ids.add(slide_id)
                patient_ids.add(patient_id)

                path_value = row["path"]
                if not path_value:
                    raise CliError(f"row {row_number}: path is empty")
                slide_path = checked_input_file(
                    path_value,
                    root=root,
                    suffixes=SLIDE_SUFFIXES,
                    max_bytes=max_slide_bytes,
                )
                if slide_path in resolved_paths:
                    raise CliError(f"row {row_number}: duplicate resolved slide path")
                resolved_paths.add(slide_path)
                suffix_counts[_matched_suffix(slide_path)] += 1

                split = row.get("split", "")
                if "split" in normalized_headers and not split:
                    raise CliError(f"row {row_number}: split column must not contain blanks")
                if split:
                    if allowed_splits and split not in allowed_splits:
                        raise CliError(
                            f"row {row_number}: split must be one of "
                            f"{', '.join(sorted(allowed_splits))}"
                        )
                    previous = patient_splits.setdefault(patient_id, split)
                    if previous != split:
                        raise CliError(
                            f"row {row_number}: patient_id appears in multiple splits: "
                            f"{previous!r} and {split!r}"
                        )
                    split_counts[split] += 1

            if row_count == 0:
                raise CliError("manifest contains no data rows")
    except CliError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise CliError(f"cannot parse manifest CSV: {exc}") from exc

    return {
        "command": "validate",
        "valid": True,
        "row_count": len(slide_ids),
        "patient_count": len(patient_ids),
        "split_counts": dict(sorted(split_counts.items())),
        "suffix_counts": dict(sorted(suffix_counts.items())),
        "checks": {
            "local_regular_files": True,
            "no_urls": True,
            "no_symlinks": True,
            "unique_slide_ids": True,
            "unique_slide_paths": True,
            "patient_split_isolation": bool(patient_splits),
        },
        "privacy_note": (
            "Identifiers were validated syntactically only; confirm they are "
            "pseudonyms and keep the linkage key outside the analysis workspace."
        ),
    }


def _inspect_openslide(path: Path) -> dict[str, Any]:
    try:
        import openslide
    except ModuleNotFoundError as exc:
        raise CliError(
            f"technical OpenSlide metadata requires PathML dependencies; {PINNED_INSTALL}"
        ) from exc

    slide = openslide.OpenSlide(str(path))
    try:
        properties = slide.properties
        technical = {
            "backend": "openslide",
            "level_count": int(slide.level_count),
            "level_dimensions_xy": [
                [int(width), int(height)] for width, height in slide.level_dimensions
            ],
            "level_downsamples": [float(value) for value in slide.level_downsamples],
        }
        allowlist = {
            "openslide.vendor": "vendor",
            "openslide.objective-power": "objective_power",
            "openslide.mpp-x": "mpp_x",
            "openslide.mpp-y": "mpp_y",
            "openslide.comment": None,
        }
        for source, destination in allowlist.items():
            if destination is not None and source in properties:
                value: Any = properties[source]
                if destination in {"objective_power", "mpp_x", "mpp_y"}:
                    try:
                        value = float(value)
                        if not math.isfinite(value) or value <= 0:
                            value = None
                    except (TypeError, ValueError):
                        value = None
                technical[destination] = value
        return technical
    finally:
        slide.close()


def _inspect_dicom(path: Path) -> dict[str, Any]:
    try:
        import pydicom
    except ModuleNotFoundError as exc:
        raise CliError(
            f"technical DICOM metadata requires PathML dependencies; {PINNED_INSTALL}"
        ) from exc

    fields = (
        "Rows",
        "Columns",
        "TotalPixelMatrixRows",
        "TotalPixelMatrixColumns",
        "NumberOfFrames",
        "SamplesPerPixel",
        "PhotometricInterpretation",
        "BitsAllocated",
    )
    try:
        dataset = pydicom.dcmread(
            path,
            stop_before_pixels=True,
            specific_tags=list(fields),
            force=False,
        )
    except Exception as exc:
        raise CliError(f"cannot parse allowlisted DICOM metadata: {exc}") from exc
    output: dict[str, Any] = {"backend": "dicom"}
    for field in fields:
        if hasattr(dataset, field):
            value = getattr(dataset, field)
            if field == "PhotometricInterpretation":
                output[field] = str(value)
            else:
                try:
                    output[field] = int(value)
                except (TypeError, ValueError):
                    output[field] = str(value)
    return output


def _inspect_raster(path: Path, max_pixels: int) -> dict[str, Any]:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise CliError(
            f"technical raster metadata requires PathML/Pillow dependencies; {PINNED_INSTALL}"
        ) from exc

    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with Image.open(path) as image:
            width, height = image.size
            if width * height > max_pixels:
                raise CliError(
                    f"image has {width * height} pixels; limit is {max_pixels}"
                )
            return {
                "backend": "pillow",
                "width": int(width),
                "height": int(height),
                "mode": str(image.mode),
                "frame_count": int(getattr(image, "n_frames", 1)),
                "format": str(image.format or "unknown"),
            }
    except CliError:
        raise
    except Exception as exc:
        raise CliError(f"cannot parse allowlisted raster metadata: {exc}") from exc


def inspect_slide(args: argparse.Namespace) -> dict[str, Any]:
    root = checked_root(args.root)
    max_slide_bytes = int(args.max_slide_gib * 1024**3)
    slide = checked_input_file(
        args.slide,
        root=root,
        suffixes=SLIDE_SUFFIXES,
        max_bytes=max_slide_bytes,
    )
    suffix = _matched_suffix(slide)
    report: dict[str, Any] = {
        "command": "inspect",
        "local_regular_file": True,
        "symlink": False,
        "size_bytes": slide.stat().st_size,
        "suffix": suffix,
        "technical_metadata_included": False,
        "path_redacted": True,
    }
    if args.sha256:
        report["sha256"] = sha256_file(
            slide, max_bytes=int(args.max_hash_gib * 1024**3)
        )
    if args.technical_metadata:
        if suffix in DICOM_SUFFIXES:
            technical = _inspect_dicom(slide)
        elif suffix in OPENSLIDE_SUFFIXES:
            technical = _inspect_openslide(slide)
        else:
            technical = _inspect_raster(slide, args.max_pixels)
        report["technical_metadata"] = technical
        report["technical_metadata_included"] = True
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate local pseudonymous slide manifests or inspect only "
            "allowlisted technical metadata. No network access."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate", help="validate a bounded local CSV manifest"
    )
    validate.add_argument("--manifest", required=True)
    validate.add_argument("--root", default=".")
    validate.add_argument("--splits", default="train,validation,test")
    validate.add_argument("--max-rows", type=int, default=100_000)
    validate.add_argument(
        "--max-manifest-bytes", type=int, default=MAX_CSV_BYTES
    )
    validate.add_argument("--max-slide-gib", type=float, default=1024.0)
    validate.add_argument("--output")
    validate.add_argument("--force", action="store_true")

    inspect = subparsers.add_parser(
        "inspect", help="inspect one local slide without emitting its path"
    )
    inspect.add_argument("--slide", required=True)
    inspect.add_argument("--root", default=".")
    inspect.add_argument("--max-slide-gib", type=float, default=1024.0)
    inspect.add_argument("--technical-metadata", action="store_true")
    inspect.add_argument("--max-pixels", type=int, default=16_000_000)
    inspect.add_argument("--sha256", action="store_true")
    inspect.add_argument("--max-hash-gib", type=float, default=64.0)
    inspect.add_argument("--output")
    inspect.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "validate":
        if not 1 <= args.max_rows <= MAX_ROWS:
            raise CliError(f"--max-rows must be between 1 and {MAX_ROWS}")
        if not 0 < args.max_manifest_bytes <= MAX_CSV_BYTES:
            raise CliError(
                f"--max-manifest-bytes must be between 1 and {MAX_CSV_BYTES}"
            )
        if not math.isfinite(args.max_slide_gib) or not 0 < args.max_slide_gib <= 4096:
            raise CliError("--max-slide-gib must be finite and in (0, 4096]")
        report = validate_manifest(args)
    else:
        if not math.isfinite(args.max_slide_gib) or not 0 < args.max_slide_gib <= 4096:
            raise CliError("--max-slide-gib must be finite and in (0, 4096]")
        if not math.isfinite(args.max_hash_gib) or not 0 < args.max_hash_gib <= 4096:
            raise CliError("--max-hash-gib must be finite and in (0, 4096]")
        if not 1 <= args.max_pixels <= 100_000_000:
            raise CliError("--max-pixels must be between 1 and 100000000")
        report = inspect_slide(args)
    emit_json(report, output=args.output, root=args.root, force=args.force)


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
