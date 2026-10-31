#!/usr/bin/env python3
"""Inspect figure/image metadata and screen it against explicit constraints.

The tool is network-free. Pillow is loaded only for raster inputs and pypdf is
loaded only for PDF inputs. A successful screen is not a journal-compliance
claim.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

from _common import (
    MAX_INPUT_BYTES,
    CliError,
    checked_input_file,
    emit_json,
    positive_float,
    positive_int,
)

SCHEMA_VERSION = "1.0"
DEFAULT_MAX_PIXELS = 100_000_000
MAX_XML_ELEMENTS = 100_000
MAX_SVG_BYTES = 20 * 1024 * 1024
FORMAT_ALIASES = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "tif": "TIFF",
    "tiff": "TIFF",
    "svg": "SVG",
    "pdf": "PDF",
    "eps": "EPS",
    "ps": "PS",
    "png": "PNG",
    "webp": "WEBP",
}
VECTOR_SUFFIXES = {".svg", ".pdf", ".eps", ".ps"}
LENGTH_RE = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"\s*(px|pt|pc|in|cm|mm)?\s*$"
)


def _finite_number(value: Any) -> float | None:
    """Convert a scalar or rational-like value to a finite float."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _dpi_pair(value: Any) -> tuple[float | None, float | None]:
    """Normalize common Pillow DPI metadata representations."""
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        return _finite_number(value[0]), _finite_number(value[1])
    scalar = _finite_number(value)
    return scalar, scalar


def _length_to_inches(value: str | None) -> tuple[float | None, str | None]:
    """Parse an SVG/CSS absolute length using the CSS 96 px/in convention."""
    if value is None:
        return None, None
    match = LENGTH_RE.match(value)
    if not match:
        return None, None
    number = float(match.group(1))
    unit = (match.group(2) or "px").lower()
    factors = {
        "px": 1.0 / 96.0,
        "pt": 1.0 / 72.0,
        "pc": 1.0 / 6.0,
        "in": 1.0,
        "cm": 1.0 / 2.54,
        "mm": 1.0 / 25.4,
    }
    if not math.isfinite(number) or number <= 0:
        raise CliError("SVG dimensions must be finite and greater than zero")
    return number * factors[unit], unit


def _base_metadata(path: Path) -> dict[str, Any]:
    info = path.stat()
    return {
        "path": str(path),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "size_bytes": info.st_size,
    }


def inspect_raster(path: Path, *, max_pixels: int) -> dict[str, Any]:
    """Inspect a raster image with Pillow without decoding all pixel data."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise CliError(
            "Pillow is required for raster metadata; "
            "run with --with 'pillow==12.3.0'"
        ) from exc

    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                width, height = image.size
                if width * height > max_pixels:
                    raise CliError(
                        f"image has {width * height} pixels; "
                        f"limit is {max_pixels}"
                    )
                dpi_x, dpi_y = _dpi_pair(image.info.get("dpi"))
                icc = image.info.get("icc_profile")
                metadata = {
                    "format": (image.format or path.suffix.lstrip(".")).upper(),
                    "kind": "raster",
                    "width_px": int(width),
                    "height_px": int(height),
                    "pixel_count": int(width * height),
                    "mode": image.mode,
                    "bands": list(image.getbands()),
                    "has_alpha": "A" in image.getbands()
                    or "transparency" in image.info,
                    "frames": int(getattr(image, "n_frames", 1)),
                    "dpi_x": dpi_x,
                    "dpi_y": dpi_y,
                    "width_mm_from_metadata": (
                        width / dpi_x * 25.4 if dpi_x and dpi_x > 0 else None
                    ),
                    "height_mm_from_metadata": (
                        height / dpi_y * 25.4 if dpi_y and dpi_y > 0 else None
                    ),
                    "icc_profile_present": bool(icc),
                    "icc_profile_bytes": len(icc) if isinstance(icc, bytes) else 0,
                    "compression": image.info.get("compression"),
                    "exif_present": bool(image.info.get("exif")),
                }
                image.verify()
                return metadata
    except Image.DecompressionBombWarning as exc:
        raise CliError(f"image exceeds safe pixel limits: {exc}") from exc
    except Image.DecompressionBombError as exc:
        raise CliError(f"image exceeds safe pixel limits: {exc}") from exc
    except OSError as exc:
        raise CliError(f"Pillow could not inspect {path}: {exc}") from exc
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit


def inspect_svg(path: Path) -> dict[str, Any]:
    """Inspect SVG dimensions and resource types with bounded XML parsing."""
    if path.stat().st_size > MAX_SVG_BYTES:
        raise CliError(
            f"SVG is {path.stat().st_size} bytes; limit is {MAX_SVG_BYTES} bytes"
        )
    try:
        payload = path.read_bytes()
        if re.search(br"<!ENTITY\b", payload, flags=re.IGNORECASE) or re.search(
            br"<!DOCTYPE[^>]*\[", payload, flags=re.IGNORECASE | re.DOTALL
        ):
            raise CliError("SVG internal DTD/entity declarations are not allowed")
        root = ET.fromstring(payload)
    except (ET.ParseError, OSError) as exc:
        raise CliError(f"invalid SVG/XML input: {exc}") from exc

    if root.tag not in {"svg", "{http://www.w3.org/2000/svg}svg"}:
        raise CliError("XML root must be an SVG element")
    width_raw = root.get("width")
    height_raw = root.get("height")
    width_in, width_unit = _length_to_inches(width_raw)
    height_in, height_unit = _length_to_inches(height_raw)
    viewbox_raw = root.get("viewBox")
    viewbox: list[float] | None = None
    if viewbox_raw:
        try:
            values = [float(item) for item in re.split(r"[\s,]+", viewbox_raw.strip())]
        except ValueError:
            values = []
        if len(values) == 4 and all(math.isfinite(item) for item in values):
            viewbox = values

    element_count = 0
    text_count = 0
    image_count = 0
    external_images = 0
    for element in root.iter():
        element_count += 1
        if element_count > MAX_XML_ELEMENTS:
            raise CliError(
                f"SVG has more than {MAX_XML_ELEMENTS} elements; refusing input"
            )
        local_name = element.tag.rsplit("}", 1)[-1].lower()
        if local_name == "text":
            text_count += 1
        elif local_name == "image":
            image_count += 1
            href = (
                element.get("href")
                or element.get("{http://www.w3.org/1999/xlink}href")
                or ""
            )
            if href and not href.startswith("data:"):
                external_images += 1

    return {
        "format": "SVG",
        "kind": "vector",
        "width_raw": width_raw,
        "height_raw": height_raw,
        "width_unit": width_unit,
        "height_unit": height_unit,
        "width_mm": width_in * 25.4 if width_in is not None else None,
        "height_mm": height_in * 25.4 if height_in is not None else None,
        "viewbox": viewbox,
        "dpi_x": None,
        "dpi_y": None,
        "mode": None,
        "element_count": element_count,
        "text_element_count": text_count,
        "image_element_count": image_count,
        "external_image_count": external_images,
        "note": (
            "SVG is resolution-independent except for embedded raster images; "
            "external image resources were counted but not fetched."
        ),
    }


def _pdf_font_report(page: Any) -> dict[str, Any]:
    """Return a conservative first-page PDF font resource report."""
    try:
        resources = page.get("/Resources")
        resources = resources.get_object() if resources else None
        fonts = resources.get("/Font") if resources else None
        fonts = fonts.get_object() if fonts else None
    except Exception:
        fonts = None
    if not fonts:
        return {
            "resource_count": 0,
            "embedded_count": 0,
            "unembedded_count": 0,
            "unknown_count": 0,
            "all_embedded": None,
            "fonts": [],
        }

    def embedded_status(font: Any) -> bool | None:
        try:
            subtype = str(font.get("/Subtype", ""))
            if subtype == "/Type3":
                # Type 3 glyph programs live in the PDF CharProcs dictionary.
                return True if font.get("/CharProcs") else None
            candidates = [font]
            descendants = font.get("/DescendantFonts")
            if descendants:
                candidates.extend(
                    reference.get_object() for reference in descendants
                )
            saw_descriptor = False
            for candidate in candidates:
                descriptor = candidate.get("/FontDescriptor")
                descriptor = descriptor.get_object() if descriptor else None
                if descriptor:
                    saw_descriptor = True
                    if any(
                        descriptor.get(key)
                        for key in ("/FontFile", "/FontFile2", "/FontFile3")
                    ):
                        return True
            return False if saw_descriptor else None
        except Exception:
            return None

    records: list[dict[str, Any]] = []
    for resource_name, reference in fonts.items():
        try:
            font = reference.get_object()
            embedded = embedded_status(font)
            records.append(
                {
                    "resource": str(resource_name),
                    "base_font": str(font.get("/BaseFont", "")),
                    "subtype": str(font.get("/Subtype", "")),
                    "embedded": embedded,
                }
            )
        except Exception:
            records.append(
                {
                    "resource": str(resource_name),
                    "base_font": "",
                    "subtype": "",
                    "embedded": None,
                }
            )
    definite = [item["embedded"] for item in records if item["embedded"] is not None]
    unknown_count = sum(item["embedded"] is None for item in records)
    return {
        "resource_count": len(records),
        "embedded_count": sum(item is True for item in definite),
        "unembedded_count": sum(item is False for item in definite),
        "unknown_count": unknown_count,
        "all_embedded": (
            None
            if not definite or unknown_count
            else all(item is True for item in definite)
        ),
        "fonts": records,
        "scope": "first page resource dictionary only",
    }


def inspect_pdf(path: Path) -> dict[str, Any]:
    """Inspect PDF page dimensions and first-page font resources with pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise CliError(
            "pypdf is required for PDF metadata; "
            "run with --with 'pypdf==6.19.0'"
        ) from exc
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            try:
                unlocked = reader.decrypt("")
            except Exception:
                unlocked = 0
            if not unlocked:
                return {
                    "format": "PDF",
                    "kind": "vector-container",
                    "encrypted": True,
                    "page_count": None,
                    "width_mm": None,
                    "height_mm": None,
                    "dpi_x": None,
                    "dpi_y": None,
                    "mode": None,
                    "font_resources": None,
                    "note": "Encrypted PDF could not be inspected without a password.",
                }
        page_count = len(reader.pages)
        if page_count < 1:
            raise CliError("PDF has no pages")
        page = reader.pages[0]
        width_pt = float(page.mediabox.width)
        height_pt = float(page.mediabox.height)
        user_unit = float(page.user_unit)
        rotation = int(page.rotation) % 360
        crop_width = float(page.cropbox.width)
        crop_height = float(page.cropbox.height)
        if rotation not in {0, 90, 180, 270} or not all(
            math.isfinite(value) and value > 0
            for value in (width_pt, height_pt, crop_width, crop_height, user_unit)
        ):
            raise CliError("PDF page dimensions, UserUnit, or rotation are invalid")
        display_width, display_height = width_pt * user_unit, height_pt * user_unit
        crop_width, crop_height = crop_width * user_unit, crop_height * user_unit
        if rotation in {90, 270}:
            display_width, display_height = display_height, display_width
            crop_width, crop_height = crop_height, crop_width
        return {
            "format": "PDF",
            "kind": "vector-container",
            "encrypted": bool(reader.is_encrypted),
            "page_count": page_count,
            "first_page_width_pt": width_pt,
            "first_page_height_pt": height_pt,
            "user_unit": user_unit,
            "rotation_degrees": rotation,
            "width_mm": display_width / 72.0 * 25.4,
            "height_mm": display_height / 72.0 * 25.4,
            "crop_width_mm": crop_width / 72.0 * 25.4,
            "crop_height_mm": crop_height / 72.0 * 25.4,
            "cropbox_differs_from_mediabox": list(page.cropbox) != list(page.mediabox),
            "dpi_x": None,
            "dpi_y": None,
            "mode": None,
            "font_resources": _pdf_font_report(page),
            "note": (
                "Dimensions use first-page MediaBox with UserUnit and rotation; "
                "CropBox dimensions are reported separately. Raw first_page_*_pt "
                "values are unscaled user coordinates. Page size and fonts do not establish the "
                "resolution of embedded raster images."
            ),
        }
    except CliError:
        raise
    except Exception as exc:
        raise CliError(f"pypdf could not inspect {path}: {exc}") from exc


def inspect_eps(path: Path) -> dict[str, Any]:
    """Inspect an EPS/PS bounding box without invoking PostScript."""
    size = path.stat().st_size
    with path.open("rb") as handle:
        prefix = handle.read(min(size, 128 * 1024))
        suffix = b""
        if size > len(prefix):
            handle.seek(max(0, size - 128 * 1024))
            suffix = handle.read(128 * 1024)
    text = (prefix + b"\n" + suffix).decode("latin-1", errors="replace")
    matches = re.findall(
        r"^%%(?:HiRes)?BoundingBox:\s+"
        r"([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*$",
        text,
        flags=re.MULTILINE,
    )
    bbox = [float(value) for value in matches[-1]] if matches else None
    width_pt = bbox[2] - bbox[0] if bbox else None
    height_pt = bbox[3] - bbox[1] if bbox else None
    return {
        "format": "EPS" if path.suffix.lower() == ".eps" else "PS",
        "kind": "vector-container",
        "bounding_box_pt": bbox,
        "width_mm": width_pt / 72.0 * 25.4 if width_pt is not None else None,
        "height_mm": (
            height_pt / 72.0 * 25.4 if height_pt is not None else None
        ),
        "dpi_x": None,
        "dpi_y": None,
        "mode": None,
        "note": "PostScript was not executed; only DSC bounding-box text was read.",
    }


def inspect_file(
    value: str | Path,
    *,
    max_bytes: int = MAX_INPUT_BYTES,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> dict[str, Any]:
    """Inspect a supported local figure/image and return structured metadata."""
    path = checked_input_file(value, max_bytes=max_bytes)
    suffix = path.suffix.lower()
    if suffix == ".svg":
        metadata = inspect_svg(path)
    elif suffix == ".pdf":
        metadata = inspect_pdf(path)
    elif suffix in {".eps", ".ps"}:
        metadata = inspect_eps(path)
    else:
        metadata = inspect_raster(path, max_pixels=max_pixels)
    return {
        "schema_version": SCHEMA_VERSION,
        "input": _base_metadata(path),
        "metadata": metadata,
    }


def _normalize_formats(values: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        for item in value.split(","):
            name = item.strip().lower().lstrip(".")
            if not name:
                continue
            normalized.append(FORMAT_ALIASES.get(name, name.upper()))
    return sorted(set(normalized))


def _check(
    name: str,
    status: str,
    *,
    actual: Any,
    expected: Any,
    detail: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "actual": actual,
        "expected": expected,
        "detail": detail,
    }


def screen_metadata(
    report: dict[str, Any],
    *,
    expected_formats: Iterable[str] = (),
    expected_modes: Iterable[str] = (),
    min_dpi: float | None = None,
    max_dpi: float | None = None,
    min_width_px: int | None = None,
    max_width_px: int | None = None,
    min_height_px: int | None = None,
    max_height_px: int | None = None,
    max_file_bytes: int | None = None,
    target_width_mm: float | None = None,
    alpha_policy: str | None = None,
) -> dict[str, Any]:
    """Apply only caller-supplied constraints to an inspection report."""
    metadata = report["metadata"]
    checks: list[dict[str, Any]] = []

    formats = _normalize_formats(expected_formats)
    if formats:
        actual = str(metadata.get("format", "")).upper()
        checks.append(
            _check(
                "format",
                "pass" if actual in formats else "fail",
                actual=actual,
                expected=formats,
                detail="File format is compared with the explicit allow-list.",
            )
        )

    modes = sorted(
        {
            item.strip().upper()
            for value in expected_modes
            for item in value.split(",")
            if item.strip()
        }
    )
    if modes:
        actual_mode = metadata.get("mode")
        status = (
            "unknown"
            if actual_mode is None
            else ("pass" if str(actual_mode).upper() in modes else "fail")
        )
        checks.append(
            _check(
                "mode",
                status,
                actual=actual_mode,
                expected=modes,
                detail="Vector containers generally do not expose one image mode.",
            )
        )

    width_px = metadata.get("width_px")
    height_px = metadata.get("height_px")
    for name, actual, minimum, maximum in (
        ("width_px", width_px, min_width_px, max_width_px),
        ("height_px", height_px, min_height_px, max_height_px),
    ):
        if minimum is None and maximum is None:
            continue
        if actual is None:
            status = "unknown"
        elif minimum is not None and actual < minimum:
            status = "fail"
        elif maximum is not None and actual > maximum:
            status = "fail"
        else:
            status = "pass"
        checks.append(
            _check(
                name,
                status,
                actual=actual,
                expected={"min": minimum, "max": maximum},
                detail="Pixel dimensions are available for raster inputs.",
            )
        )

    dpi_x = metadata.get("dpi_x")
    dpi_y = metadata.get("dpi_y")
    effective_dpi = None
    if target_width_mm is not None and width_px is not None:
        effective_dpi = width_px / (target_width_mm / 25.4)
    actual_dpi = effective_dpi
    dpi_basis = "effective at target width"
    if actual_dpi is None and dpi_x and dpi_y:
        actual_dpi = min(float(dpi_x), float(dpi_y))
        dpi_basis = "embedded metadata"
    if min_dpi is not None or max_dpi is not None:
        if actual_dpi is None:
            status = "unknown"
        elif (
            min_dpi is not None
            and actual_dpi < min_dpi
            and not math.isclose(actual_dpi, min_dpi, rel_tol=1e-12, abs_tol=1e-9)
        ):
            status = "fail"
        elif (
            max_dpi is not None
            and actual_dpi > max_dpi
            and not math.isclose(actual_dpi, max_dpi, rel_tol=1e-12, abs_tol=1e-9)
        ):
            status = "fail"
        else:
            status = "pass"
        checks.append(
            _check(
                "dpi",
                status,
                actual=actual_dpi,
                expected={"min": min_dpi, "max": max_dpi},
                detail=(
                    f"DPI basis: {dpi_basis}. Metadata DPI is not a quality "
                    "measure; effective DPI depends on final physical size."
                ),
            )
        )

    if max_file_bytes is not None:
        actual_bytes = report["input"]["size_bytes"]
        checks.append(
            _check(
                "file_size",
                "pass" if actual_bytes <= max_file_bytes else "fail",
                actual=actual_bytes,
                expected={"max": max_file_bytes},
                detail="File size is measured from the local input.",
            )
        )

    if alpha_policy is not None:
        if alpha_policy not in {"allow", "forbid", "require"}:
            raise CliError("alpha_policy must be allow, forbid, or require")
        has_alpha = metadata.get("has_alpha")
        if has_alpha is None:
            alpha_status = "unknown"
        elif alpha_policy == "allow":
            alpha_status = "pass"
        elif alpha_policy == "forbid":
            alpha_status = "pass" if not has_alpha else "fail"
        else:
            alpha_status = "pass" if has_alpha else "fail"
        checks.append(
            _check(
                "alpha",
                alpha_status,
                actual=has_alpha,
                expected=alpha_policy,
                detail=(
                    "Alpha is detected for raster modes/transparency metadata. "
                    "Vector transparency requires rendered-content inspection."
                ),
            )
        )

    counts = {
        status: sum(item["status"] == status for item in checks)
        for status in ("pass", "fail", "warning", "unknown")
    }
    screened = dict(report)
    screened["checks"] = checks
    screened["screening_summary"] = counts
    screened["notice"] = (
        "This deterministic metadata screen checks only the supplied constraints. "
        "It does not verify visual quality, scientific integrity, accessibility, "
        "embedded-raster resolution in vector files, or journal compliance."
    )
    return screened


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect local raster, SVG, PDF, EPS, or PS metadata and optionally "
            "screen it against explicit constraints. No network access is used."
        )
    )
    parser.add_argument("input", help="local figure/image file (symlinks rejected)")
    parser.add_argument(
        "--format",
        dest="formats",
        action="append",
        default=[],
        help="allowed format; repeat or use comma-separated values",
    )
    parser.add_argument(
        "--mode",
        dest="modes",
        action="append",
        default=[],
        help="allowed raster mode (for example RGB,L); repeat as needed",
    )
    parser.add_argument("--min-dpi", type=positive_float)
    parser.add_argument("--max-dpi", type=positive_float)
    parser.add_argument(
        "--target-width-mm",
        type=positive_float,
        help="calculate effective raster DPI at this final width",
    )
    parser.add_argument("--min-width-px", type=positive_int)
    parser.add_argument("--max-width-px", type=positive_int)
    parser.add_argument("--min-height-px", type=positive_int)
    parser.add_argument("--max-height-px", type=positive_int)
    parser.add_argument("--max-file-bytes", type=positive_int)
    parser.add_argument(
        "--alpha-policy",
        choices=("allow", "forbid", "require"),
        help="optional raster alpha/transparency screen",
    )
    parser.add_argument(
        "--max-input-bytes",
        type=positive_int,
        default=MAX_INPUT_BYTES,
        help=f"input byte limit (default: {MAX_INPUT_BYTES})",
    )
    parser.add_argument(
        "--max-pixels",
        type=positive_int,
        default=DEFAULT_MAX_PIXELS,
        help=f"raster pixel limit (default: {DEFAULT_MAX_PIXELS})",
    )
    parser.add_argument("--output", help="optional JSON report path")
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing JSON report"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        report = inspect_file(
            args.input,
            max_bytes=args.max_input_bytes,
            max_pixels=args.max_pixels,
        )
        report = screen_metadata(
            report,
            expected_formats=args.formats,
            expected_modes=args.modes,
            min_dpi=args.min_dpi,
            max_dpi=args.max_dpi,
            min_width_px=args.min_width_px,
            max_width_px=args.max_width_px,
            min_height_px=args.min_height_px,
            max_height_px=args.max_height_px,
            max_file_bytes=args.max_file_bytes,
            target_width_mm=args.target_width_mm,
            alpha_policy=args.alpha_policy,
        )
        emit_json(report, output=args.output, force=args.force)
        return 1 if report["screening_summary"]["fail"] else 0
    except CliError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
