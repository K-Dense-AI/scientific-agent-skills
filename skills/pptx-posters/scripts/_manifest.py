#!/usr/bin/env python3
"""Strict poster-manifest validation shared by generation and audit tools."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from _common import (
    PPTX_MAX_INCHES,
    PPTX_MIN_INCHES,
    CliError,
    canonical_json_hash,
    contrast_ratio,
    finite_number,
    has_placeholder,
    load_json_file,
    parse_aware_datetime,
    parse_hex_color,
    positive_int,
    reject_unknown_keys,
    require_bool,
    require_string,
    resolve_local_asset,
    sha256_file,
)

MANIFEST_SCHEMA_VERSION = "2.0"
REPORT_SCHEMA_VERSION = "1.0"
MAX_ELEMENTS = 250
MAX_SOURCES = 500
MAX_ASSETS = 100
ASSET_SUFFIXES = {".png", ".jpg", ".jpeg"}

_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RELATIVE_PATH = re.compile(r"^[^:/\\][^:\\]*$")

_TOP_KEYS = {
    "schema_version",
    "document",
    "canvas",
    "physical_output",
    "requirements",
    "quality",
    "palette",
    "sources",
    "assets",
    "elements",
    "approval",
}
_SOURCE_KINDS = {
    "author_content",
    "publication",
    "dataset",
    "asset_license",
    "conference_rule",
    "printer_rule",
    "institutional_rule",
    "other",
}
_FONT_BASES = {
    "heuristic",
    "source_specific",
    "conference_requirement",
    "printer_requirement",
}
_TEXT_ROLES = {
    "title",
    "authors",
    "affiliation",
    "heading",
    "body",
    "caption",
    "reference",
    "acknowledgement",
    "contact",
    "qr_fallback",
    "other",
}


def _identifier(value: Any, *, context: str) -> str:
    text = require_string(value, context=context, maximum=64)
    if not _ID.fullmatch(text):
        raise CliError(
            f"{context} must start with a letter and contain only letters, "
            "digits, period, underscore, or hyphen"
        )
    return text


def _nullable_source_id(value: Any, *, context: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, context=context)


def _string_list(
    value: Any,
    *,
    context: str,
    minimum: int,
    maximum: int,
) -> list[str]:
    if not isinstance(value, list):
        raise CliError(f"{context} must be an array")
    if not minimum <= len(value) <= maximum:
        raise CliError(
            f"{context} must contain between {minimum} and {maximum} values"
        )
    result = [
        require_string(item, context=f"{context}[{index}]", maximum=500)
        for index, item in enumerate(value)
    ]
    if len(set(result)) != len(result):
        raise CliError(f"{context} must not contain duplicates")
    return result


def _source_id_list(value: Any, *, context: str) -> list[str]:
    raw = _string_list(value, context=context, minimum=1, maximum=16)
    return [
        _identifier(item, context=f"{context}[{index}]")
        for index, item in enumerate(raw)
    ]


def manifest_content_hash(document: dict[str, Any]) -> str:
    """Hash all author-controlled manifest content except the approval record."""
    return canonical_json_hash(
        {key: value for key, value in document.items() if key != "approval"}
    )


def _validate_document(value: Any) -> dict[str, Any]:
    document = reject_unknown_keys(
        value,
        context="document",
        allowed={"id", "title", "subject", "language", "authors", "source_ids"},
        required={"id", "title", "subject", "language", "authors", "source_ids"},
    )
    _identifier(document["id"], context="document.id")
    # These strings are written verbatim to python-pptx core properties.
    require_string(document["title"], context="document.title", maximum=255)
    require_string(document["subject"], context="document.subject", maximum=255)
    language = require_string(
        document["language"], context="document.language", maximum=35
    )
    if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", language):
        raise CliError("document.language must be a BCP 47-style language tag")
    authors = _string_list(
        document["authors"],
        context="document.authors",
        minimum=1,
        maximum=50,
    )
    require_string(
        "; ".join(authors),
        context="document.authors joined with '; ' for core metadata",
        maximum=255,
    )
    _source_id_list(document["source_ids"], context="document.source_ids")
    return document


def _validate_canvas(value: Any) -> tuple[dict[str, Any], float, float]:
    canvas = reject_unknown_keys(
        value,
        context="canvas",
        allowed={"width_in", "height_in", "background_color"},
        required={"width_in", "height_in", "background_color"},
    )
    width = finite_number(
        canvas["width_in"],
        context="canvas.width_in",
        minimum=PPTX_MIN_INCHES,
        maximum=PPTX_MAX_INCHES,
    )
    height = finite_number(
        canvas["height_in"],
        context="canvas.height_in",
        minimum=PPTX_MIN_INCHES,
        maximum=PPTX_MAX_INCHES,
    )
    parse_hex_color(canvas["background_color"], context="canvas.background_color")
    return canvas, width, height


def _validate_physical_output(
    value: Any,
) -> tuple[dict[str, Any], float, float, float, float, float, float]:
    physical = reject_unknown_keys(
        value,
        context="physical_output",
        allowed={
            "trim_width_in",
            "trim_height_in",
            "bleed_in",
            "safe_margin_in",
            "orientation",
        },
        required={
            "trim_width_in",
            "trim_height_in",
            "bleed_in",
            "safe_margin_in",
            "orientation",
        },
    )
    trim_width = finite_number(
        physical["trim_width_in"],
        context="physical_output.trim_width_in",
        minimum=1.0,
        maximum=200.0,
    )
    trim_height = finite_number(
        physical["trim_height_in"],
        context="physical_output.trim_height_in",
        minimum=1.0,
        maximum=200.0,
    )
    bleed = finite_number(
        physical["bleed_in"],
        context="physical_output.bleed_in",
        minimum=0.0,
        maximum=2.0,
    )
    safe_margin = finite_number(
        physical["safe_margin_in"],
        context="physical_output.safe_margin_in",
        minimum=0.0,
        maximum=10.0,
    )
    if 2 * safe_margin >= min(trim_width, trim_height):
        raise CliError("physical_output.safe_margin_in consumes the trim area")
    orientation = require_string(
        physical["orientation"],
        context="physical_output.orientation",
        maximum=16,
    )
    expected = (
        "square"
        if abs(trim_width - trim_height) <= 1e-6
        else ("landscape" if trim_width > trim_height else "portrait")
    )
    if orientation != expected:
        raise CliError(
            "physical_output.orientation does not match the trim dimensions "
            f"(expected {expected!r})"
        )
    artboard_width = trim_width + 2 * bleed
    artboard_height = trim_height + 2 * bleed
    return (
        physical,
        trim_width,
        trim_height,
        bleed,
        safe_margin,
        artboard_width,
        artboard_height,
    )


def _validate_sources(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SOURCES:
        raise CliError(f"sources must contain between 1 and {MAX_SOURCES} objects")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(value):
        context = f"sources[{index}]"
        source = reject_unknown_keys(
            item,
            context=context,
            allowed={"id", "kind", "citation", "locator", "author_verified"},
            required={"id", "kind", "citation", "locator", "author_verified"},
        )
        source_id = _identifier(source["id"], context=f"{context}.id")
        if source_id in result:
            raise CliError(f"duplicate source id: {source_id}")
        kind = require_string(source["kind"], context=f"{context}.kind", maximum=32)
        if kind not in _SOURCE_KINDS:
            raise CliError(
                f"{context}.kind must be one of {', '.join(sorted(_SOURCE_KINDS))}"
            )
        require_string(
            source["citation"], context=f"{context}.citation", maximum=2_000
        )
        require_string(source["locator"], context=f"{context}.locator", maximum=2_000)
        if not require_bool(
            source["author_verified"], context=f"{context}.author_verified"
        ):
            raise CliError(f"{context}.author_verified must be true")
        result[source_id] = source
    return result


def _validate_requirements(
    value: Any,
    *,
    trim_width: float,
    trim_height: float,
    bleed: float,
    safe_margin: float,
    print_scale: float,
) -> tuple[dict[str, Any], set[str]]:
    requirements = reject_unknown_keys(
        value,
        context="requirements",
        allowed={"conference", "printer"},
        required={"conference", "printer"},
    )
    conference = reject_unknown_keys(
        requirements["conference"],
        context="requirements.conference",
        allowed={
            "confirmed",
            "source_id",
            "max_width_in",
            "max_height_in",
            "orientation",
            "required_delivery_format",
            "notes",
        },
        required={
            "confirmed",
            "source_id",
            "max_width_in",
            "max_height_in",
            "orientation",
            "required_delivery_format",
            "notes",
        },
    )
    if not require_bool(
        conference["confirmed"], context="requirements.conference.confirmed"
    ):
        raise CliError("requirements.conference.confirmed must be true")
    conference_source = _identifier(
        conference["source_id"], context="requirements.conference.source_id"
    )
    max_width = finite_number(
        conference["max_width_in"],
        context="requirements.conference.max_width_in",
        minimum=1.0,
        maximum=200.0,
    )
    max_height = finite_number(
        conference["max_height_in"],
        context="requirements.conference.max_height_in",
        minimum=1.0,
        maximum=200.0,
    )
    conference_orientation = require_string(
        conference["orientation"],
        context="requirements.conference.orientation",
        maximum=16,
    )
    if conference_orientation not in {"portrait", "landscape", "square", "either"}:
        raise CliError(
            "requirements.conference.orientation must be portrait, landscape, "
            "square, or either"
        )
    physical_orientation = (
        "square"
        if abs(trim_width - trim_height) <= 1e-6
        else ("landscape" if trim_width > trim_height else "portrait")
    )
    if (
        conference_orientation != "either"
        and conference_orientation != physical_orientation
    ):
        raise CliError("physical output violates the confirmed conference orientation")
    if trim_width > max_width + 1e-6 or trim_height > max_height + 1e-6:
        raise CliError("physical output exceeds the confirmed conference dimensions")
    delivery = require_string(
        conference["required_delivery_format"],
        context="requirements.conference.required_delivery_format",
        maximum=32,
    )
    if delivery not in {"PDF", "PPTX", "PDF_AND_PPTX", "OTHER"}:
        raise CliError(
            "requirements.conference.required_delivery_format must be PDF, PPTX, "
            "PDF_AND_PPTX, or OTHER"
        )
    require_string(
        conference["notes"],
        context="requirements.conference.notes",
        minimum=0,
        maximum=2_000,
    )

    printer = reject_unknown_keys(
        requirements["printer"],
        context="requirements.printer",
        allowed={
            "confirmed",
            "source_id",
            "trim_width_in",
            "trim_height_in",
            "bleed_in",
            "safe_margin_in",
            "accepted_color_mode",
            "scaling_allowed",
            "notes",
        },
        required={
            "confirmed",
            "source_id",
            "trim_width_in",
            "trim_height_in",
            "bleed_in",
            "safe_margin_in",
            "accepted_color_mode",
            "scaling_allowed",
            "notes",
        },
    )
    if not require_bool(printer["confirmed"], context="requirements.printer.confirmed"):
        raise CliError("requirements.printer.confirmed must be true")
    printer_source = _identifier(
        printer["source_id"], context="requirements.printer.source_id"
    )
    printer_trim_width = finite_number(
        printer["trim_width_in"],
        context="requirements.printer.trim_width_in",
        minimum=1.0,
        maximum=200.0,
    )
    printer_trim_height = finite_number(
        printer["trim_height_in"],
        context="requirements.printer.trim_height_in",
        minimum=1.0,
        maximum=200.0,
    )
    printer_bleed = finite_number(
        printer["bleed_in"],
        context="requirements.printer.bleed_in",
        minimum=0.0,
        maximum=2.0,
    )
    printer_margin = finite_number(
        printer["safe_margin_in"],
        context="requirements.printer.safe_margin_in",
        minimum=0.0,
        maximum=10.0,
    )
    for actual, required, label in (
        (trim_width, printer_trim_width, "trim width"),
        (trim_height, printer_trim_height, "trim height"),
        (bleed, printer_bleed, "bleed"),
        (safe_margin, printer_margin, "safe margin"),
    ):
        if abs(actual - required) > 1e-6:
            raise CliError(
                f"physical output {label} does not match the confirmed printer rule"
            )
    color_mode = require_string(
        printer["accepted_color_mode"],
        context="requirements.printer.accepted_color_mode",
        maximum=32,
    )
    if color_mode not in {"RGB", "CMYK", "PRINTER_MANAGED"}:
        raise CliError(
            "requirements.printer.accepted_color_mode must be RGB, CMYK, "
            "or PRINTER_MANAGED"
        )
    scaling_allowed = require_bool(
        printer["scaling_allowed"], context="requirements.printer.scaling_allowed"
    )
    if not scaling_allowed and abs(print_scale - 1.0) > 1e-6:
        raise CliError(
            "printer forbids scaling but canvas and physical artboard differ"
        )
    require_string(
        printer["notes"],
        context="requirements.printer.notes",
        minimum=0,
        maximum=2_000,
    )
    return requirements, {conference_source, printer_source}


def _validate_quality(value: Any) -> tuple[dict[str, Any], set[str]]:
    quality = reject_unknown_keys(
        value,
        context="quality",
        allowed={
            "minimum_font_pt_final",
            "font_guidance_basis",
            "font_guidance_source_id",
            "minimum_raster_dpi_final",
            "raster_dpi_basis",
            "raster_dpi_source_id",
        },
        required={
            "minimum_font_pt_final",
            "font_guidance_basis",
            "font_guidance_source_id",
            "minimum_raster_dpi_final",
            "raster_dpi_basis",
            "raster_dpi_source_id",
        },
    )
    finite_number(
        quality["minimum_font_pt_final"],
        context="quality.minimum_font_pt_final",
        minimum=1.0,
        maximum=200.0,
    )
    finite_number(
        quality["minimum_raster_dpi_final"],
        context="quality.minimum_raster_dpi_final",
        minimum=1.0,
        maximum=2_400.0,
    )
    used: set[str] = set()
    for prefix in ("font_guidance", "raster_dpi"):
        basis = require_string(
            quality[f"{prefix}_basis"],
            context=f"quality.{prefix}_basis",
            maximum=32,
        )
        if basis not in _FONT_BASES:
            raise CliError(
                f"quality.{prefix}_basis must be one of "
                f"{', '.join(sorted(_FONT_BASES))}"
            )
        source_id = _nullable_source_id(
            quality[f"{prefix}_source_id"],
            context=f"quality.{prefix}_source_id",
        )
        if basis == "heuristic" and source_id is not None:
            raise CliError(
                f"quality.{prefix}_source_id must be null when basis is heuristic"
            )
        if basis != "heuristic" and source_id is None:
            raise CliError(
                f"quality.{prefix}_source_id is required for basis {basis!r}"
            )
        if source_id is not None:
            used.add(source_id)
    return quality, used


def _validate_palette(
    value: Any,
    *,
    enforce_thresholds: bool = True,
) -> tuple[dict[str, Any], dict[str, str], dict[str, dict[str, Any]]]:
    palette = reject_unknown_keys(
        value,
        context="palette",
        allowed={"colors", "contrast_pairs", "data_series_redundant_encoding"},
        required={"colors", "contrast_pairs", "data_series_redundant_encoding"},
    )
    raw_colors = palette["colors"]
    if not isinstance(raw_colors, dict) or not 2 <= len(raw_colors) <= 64:
        raise CliError("palette.colors must contain between 2 and 64 named colors")
    colors: dict[str, str] = {}
    for raw_id, value in raw_colors.items():
        color_id = _identifier(raw_id, context=f"palette.colors[{raw_id!r}]")
        colors[color_id] = parse_hex_color(
            value, context=f"palette.colors.{color_id}"
        )

    raw_pairs = palette["contrast_pairs"]
    if not isinstance(raw_pairs, list) or not 1 <= len(raw_pairs) <= 128:
        raise CliError("palette.contrast_pairs must contain between 1 and 128 pairs")
    pairs: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw_pairs):
        context = f"palette.contrast_pairs[{index}]"
        pair = reject_unknown_keys(
            item,
            context=context,
            allowed={
                "id",
                "foreground_color_id",
                "background_color_id",
                "usage",
            },
            required={
                "id",
                "foreground_color_id",
                "background_color_id",
                "usage",
            },
        )
        pair_id = _identifier(pair["id"], context=f"{context}.id")
        if pair_id in pairs:
            raise CliError(f"duplicate contrast pair id: {pair_id}")
        foreground_id = _identifier(
            pair["foreground_color_id"],
            context=f"{context}.foreground_color_id",
        )
        background_id = _identifier(
            pair["background_color_id"],
            context=f"{context}.background_color_id",
        )
        if foreground_id not in colors or background_id not in colors:
            raise CliError(f"{context} references an unknown palette color")
        usage = require_string(pair["usage"], context=f"{context}.usage", maximum=24)
        thresholds = {"normal_text": 4.5, "large_text": 3.0, "non_text": 3.0}
        if usage not in thresholds:
            raise CliError(
                f"{context}.usage must be normal_text, large_text, or non_text"
            )
        ratio = contrast_ratio(colors[foreground_id], colors[background_id])
        if enforce_thresholds and ratio + 1e-9 < thresholds[usage]:
            raise CliError(
                f"{context} contrast is {ratio:.2f}:1, below the "
                f"{thresholds[usage]:.1f}:1 threshold for {usage}"
            )
        pairs[pair_id] = pair
    if not require_bool(
        palette["data_series_redundant_encoding"],
        context="palette.data_series_redundant_encoding",
    ):
        raise CliError("palette.data_series_redundant_encoding must be true")
    return palette, colors, pairs


def _validate_asset_path_syntax(value: Any, *, context: str) -> str:
    path = require_string(value, context=context, maximum=512)
    if not _RELATIVE_PATH.fullmatch(path) or path.startswith(("/", "\\")):
        raise CliError(f"{context} must be a relative local path")
    if "\\" in path or any(part in {"", ".", ".."} for part in Path(path).parts):
        raise CliError(f"{context} contains an unsafe path segment")
    if Path(path).suffix.lower() not in ASSET_SUFFIXES:
        raise CliError(
            f"{context} must use one of {', '.join(sorted(ASSET_SUFFIXES))}"
        )
    return path


def _validate_assets(
    value: Any,
    *,
    manifest_path: Path,
    verify_assets: bool,
) -> tuple[dict[str, dict[str, Any]], dict[str, Path], set[str]]:
    if not isinstance(value, list) or len(value) > MAX_ASSETS:
        raise CliError(f"assets must be an array with at most {MAX_ASSETS} objects")
    assets: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    used_sources: set[str] = set()
    used_path_values: set[str] = set()
    for index, item in enumerate(value):
        context = f"assets[{index}]"
        asset = reject_unknown_keys(
            item,
            context=context,
            allowed={
                "id",
                "path",
                "role",
                "sha256",
                "source_id",
                "license",
                "provenance",
                "alt_text",
                "author_approved",
                "qr_target",
            },
            required={
                "id",
                "path",
                "role",
                "sha256",
                "source_id",
                "license",
                "provenance",
                "alt_text",
                "author_approved",
                "qr_target",
            },
        )
        asset_id = _identifier(asset["id"], context=f"{context}.id")
        if asset_id in assets:
            raise CliError(f"duplicate asset id: {asset_id}")
        path_value = _validate_asset_path_syntax(
            asset["path"], context=f"{context}.path"
        )
        if path_value in used_path_values:
            raise CliError(
                f"{context}.path duplicates another asset path: {path_value!r}"
            )
        used_path_values.add(path_value)
        role = require_string(asset["role"], context=f"{context}.role", maximum=16)
        if role not in {"figure", "logo", "qr_code"}:
            raise CliError(f"{context}.role must be figure, logo, or qr_code")
        digest = require_string(
            asset["sha256"], context=f"{context}.sha256", maximum=64
        )
        if not _SHA256.fullmatch(digest):
            raise CliError(f"{context}.sha256 must be 64 lowercase hex characters")
        source_id = _identifier(
            asset["source_id"], context=f"{context}.source_id"
        )
        used_sources.add(source_id)
        require_string(asset["license"], context=f"{context}.license", maximum=500)
        require_string(
            asset["provenance"],
            context=f"{context}.provenance",
            maximum=2_000,
        )
        require_string(
            asset["alt_text"], context=f"{context}.alt_text", maximum=1_000
        )
        if not require_bool(
            asset["author_approved"], context=f"{context}.author_approved"
        ):
            raise CliError(f"{context}.author_approved must be true")
        qr_target = asset["qr_target"]
        if role == "qr_code":
            target = require_string(
                qr_target, context=f"{context}.qr_target", maximum=2_000
            )
            authority = target[len("https://") :].split("/", 1)[0]
            if (
                not target.startswith("https://")
                or not authority
                or "@" in authority
                or any(character.isspace() for character in target)
            ):
                raise CliError(
                    f"{context}.qr_target must be an absolute https:// URL "
                    "without credentials or whitespace"
                )
        elif qr_target is not None:
            raise CliError(f"{context}.qr_target must be null for non-QR assets")
        if verify_assets:
            path = resolve_local_asset(
                manifest_path,
                path_value,
                suffixes=ASSET_SUFFIXES,
            )
            actual_digest = sha256_file(path)
            if actual_digest != digest:
                raise CliError(
                    f"{context}.sha256 mismatch for {path_value!r}: "
                    f"expected {digest}, got {actual_digest}"
                )
            paths[asset_id] = path
        assets[asset_id] = asset
    return assets, paths, used_sources


def _validate_box(
    item: dict[str, Any],
    *,
    context: str,
    canvas_width: float,
    canvas_height: float,
) -> tuple[float, float, float, float]:
    x = finite_number(item["x_in"], context=f"{context}.x_in", minimum=0.0)
    y = finite_number(item["y_in"], context=f"{context}.y_in", minimum=0.0)
    width = finite_number(
        item["width_in"], context=f"{context}.width_in", minimum=0.01
    )
    height = finite_number(
        item["height_in"], context=f"{context}.height_in", minimum=0.01
    )
    if x + width > canvas_width + 1e-6 or y + height > canvas_height + 1e-6:
        raise CliError(f"{context} extends beyond the PowerPoint canvas")
    return x, y, width, height


def _validate_elements(
    value: Any,
    *,
    document: dict[str, Any],
    canvas_width: float,
    canvas_height: float,
    print_scale: float,
    bleed: float,
    safe_margin: float,
    quality: dict[str, Any],
    colors: dict[str, str],
    contrast_pairs: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], set[str], set[str]]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_ELEMENTS:
        raise CliError(f"elements must contain between 1 and {MAX_ELEMENTS} objects")
    elements: dict[str, dict[str, Any]] = {}
    used_sources: set[str] = set()
    used_assets: set[str] = set()
    reading_orders: list[int] = []
    title_matches = 0
    safe_inset_design = (bleed + safe_margin) / print_scale

    common = {
        "id",
        "type",
        "reading_order",
        "x_in",
        "y_in",
        "width_in",
        "height_in",
        "source_ids",
        "author_approved",
        "allow_in_bleed",
    }
    text_keys = common | {
        "role",
        "text",
        "font_size_pt_design",
        "font_face",
        "bold",
        "align",
        "vertical_align",
        "contrast_pair_id",
        "line_color_id",
        "line_width_pt",
        "margin_in",
    }
    image_keys = common | {
        "asset_id",
        "fit",
        "fallback_text_element_id",
        "long_description_element_id",
    }

    for index, item in enumerate(value):
        context = f"elements[{index}]"
        if not isinstance(item, dict):
            raise CliError(f"{context} must be an object")
        element_type = require_string(
            item.get("type"), context=f"{context}.type", maximum=16
        )
        allowed = text_keys if element_type == "text" else image_keys
        if element_type not in {"text", "image"}:
            raise CliError(f"{context}.type must be text or image")
        element = reject_unknown_keys(
            item,
            context=context,
            allowed=allowed,
            required=allowed,
        )
        element_id = _identifier(element["id"], context=f"{context}.id")
        if element_id in elements:
            raise CliError(f"duplicate element id: {element_id}")
        order = positive_int(
            element["reading_order"],
            context=f"{context}.reading_order",
            maximum=MAX_ELEMENTS,
        )
        reading_orders.append(order)
        x, y, width, height = _validate_box(
            element,
            context=context,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
        )
        source_ids = _source_id_list(
            element["source_ids"], context=f"{context}.source_ids"
        )
        used_sources.update(source_ids)
        if not require_bool(
            element["author_approved"], context=f"{context}.author_approved"
        ):
            raise CliError(f"{context}.author_approved must be true")
        allow_in_bleed = require_bool(
            element["allow_in_bleed"], context=f"{context}.allow_in_bleed"
        )
        if not allow_in_bleed:
            if (
                x < safe_inset_design - 1e-6
                or y < safe_inset_design - 1e-6
                or x + width > canvas_width - safe_inset_design + 1e-6
                or y + height > canvas_height - safe_inset_design + 1e-6
            ):
                raise CliError(
                    f"{context} crosses the confirmed final safe margin; "
                    "only intentional bleed imagery may set allow_in_bleed=true"
                )

        if element_type == "text":
            if allow_in_bleed:
                raise CliError(f"{context}: text must not be placed in the bleed area")
            role = require_string(
                element["role"], context=f"{context}.role", maximum=32
            )
            if role not in _TEXT_ROLES:
                raise CliError(
                    f"{context}.role must be one of {', '.join(sorted(_TEXT_ROLES))}"
                )
            text = require_string(
                element["text"], context=f"{context}.text", maximum=20_000
            )
            if role == "title" and text == document["title"]:
                title_matches += 1
            design_font = finite_number(
                element["font_size_pt_design"],
                context=f"{context}.font_size_pt_design",
                minimum=1.0,
                maximum=500.0,
            )
            final_font = design_font * print_scale
            minimum_font = float(quality["minimum_font_pt_final"])
            if final_font + 1e-6 < minimum_font:
                raise CliError(
                    f"{context} final font is {final_font:.2f} pt, below the "
                    f"manifest's {minimum_font:.2f} pt minimum"
                )
            require_string(
                element["font_face"], context=f"{context}.font_face", maximum=100
            )
            bold = require_bool(element["bold"], context=f"{context}.bold")
            align = require_string(
                element["align"], context=f"{context}.align", maximum=16
            )
            if align not in {"left", "center", "right"}:
                raise CliError(f"{context}.align must be left, center, or right")
            vertical = require_string(
                element["vertical_align"],
                context=f"{context}.vertical_align",
                maximum=16,
            )
            if vertical not in {"top", "middle", "bottom"}:
                raise CliError(
                    f"{context}.vertical_align must be top, middle, or bottom"
                )
            pair_id = _identifier(
                element["contrast_pair_id"],
                context=f"{context}.contrast_pair_id",
            )
            if pair_id not in contrast_pairs:
                raise CliError(f"{context} references unknown contrast pair {pair_id!r}")
            pair = contrast_pairs[pair_id]
            usage = pair["usage"]
            if usage == "non_text":
                raise CliError(f"{context} must use a text contrast pair")
            if usage == "large_text":
                is_large = final_font >= 18.0 or (bold and final_font >= 14.0)
                if not is_large:
                    raise CliError(
                        f"{context} uses a large_text contrast pair but is not "
                        "at least 18 pt final, or 14 pt final and bold"
                    )
            line_color_id = element["line_color_id"]
            if line_color_id is not None:
                line_id = _identifier(
                    line_color_id, context=f"{context}.line_color_id"
                )
                if line_id not in colors:
                    raise CliError(f"{context} references unknown line color {line_id!r}")
            line_width = finite_number(
                element["line_width_pt"],
                context=f"{context}.line_width_pt",
                minimum=0.0,
                maximum=72.0,
            )
            if line_color_id is None and line_width != 0:
                raise CliError(
                    f"{context}.line_width_pt must be 0 when line_color_id is null"
                )
            margin = finite_number(
                element["margin_in"],
                context=f"{context}.margin_in",
                minimum=0.0,
                maximum=5.0,
            )
            if 2 * margin >= min(width, height):
                raise CliError(f"{context}.margin_in consumes the text box")
        else:
            asset_id = _identifier(
                element["asset_id"], context=f"{context}.asset_id"
            )
            if asset_id not in assets:
                raise CliError(f"{context} references unknown asset {asset_id!r}")
            used_assets.add(asset_id)
            if assets[asset_id]["source_id"] not in source_ids:
                raise CliError(
                    f"{context}.source_ids must include the asset's exact source_id"
                )
            fit = require_string(element["fit"], context=f"{context}.fit", maximum=16)
            if fit != "contain":
                raise CliError(f"{context}.fit must be contain")
            fallback_id = element["fallback_text_element_id"]
            long_description_id = element["long_description_element_id"]
            if long_description_id is not None:
                _identifier(
                    long_description_id,
                    context=f"{context}.long_description_element_id",
                )
            if assets[asset_id]["role"] == "qr_code":
                _identifier(
                    fallback_id,
                    context=f"{context}.fallback_text_element_id",
                )
                if abs(width - height) > 1e-6:
                    raise CliError(f"{context}: QR placement box must be square")
                if long_description_id is not None:
                    raise CliError(
                        f"{context}.long_description_element_id must be null for "
                        "QR assets; use the required visible fallback text"
                    )
            elif fallback_id is not None:
                raise CliError(
                    f"{context}.fallback_text_element_id must be null for non-QR assets"
                )
        elements[element_id] = element

    expected_order = list(range(1, len(value) + 1))
    if sorted(reading_orders) != expected_order:
        raise CliError(
            "elements.reading_order values must be unique and contiguous from 1"
        )
    if reading_orders != expected_order:
        raise CliError(
            "elements must be listed in ascending reading_order so generation "
            "does not silently reorder approved content"
        )
    if title_matches != 1:
        raise CliError(
            "exactly one title element must match document.title verbatim"
        )
    title = next(
        element
        for element in elements.values()
        if element["type"] == "text"
        and element["role"] == "title"
        and element["text"] == document["title"]
    )
    if title["reading_order"] != 1:
        raise CliError(
            "the exact title element must have reading_order 1 so it can be the "
            "native PowerPoint slide title"
        )

    for element_id, element in elements.items():
        if element["type"] != "image":
            continue
        asset = assets[element["asset_id"]]
        long_description_id = element["long_description_element_id"]
        if long_description_id is not None:
            description = elements.get(long_description_id)
            if description is None or description["type"] != "text":
                raise CliError(
                    f"image {element_id!r} references missing text long description "
                    f"{long_description_id!r}"
                )
            if description["role"] not in {"body", "caption", "other"}:
                raise CliError(
                    f"long description {long_description_id!r} must have role "
                    "'body', 'caption', or 'other'"
                )
            if description["reading_order"] <= element["reading_order"]:
                raise CliError(
                    f"long description {long_description_id!r} must follow image "
                    f"{element_id!r} in reading order"
                )
            if not set(element["source_ids"]).issubset(description["source_ids"]):
                raise CliError(
                    f"long description {long_description_id!r} must include every "
                    f"source_id used by image {element_id!r}"
                )
        if asset["role"] != "qr_code":
            continue
        fallback_id = element["fallback_text_element_id"]
        fallback = elements.get(fallback_id)
        if fallback is None or fallback["type"] != "text":
            raise CliError(
                f"QR image {element_id!r} references missing text fallback "
                f"{fallback_id!r}"
            )
        if fallback["role"] != "qr_fallback":
            raise CliError(
                f"QR fallback {fallback_id!r} must have role 'qr_fallback'"
            )
        if asset["qr_target"] not in fallback["text"]:
            raise CliError(
                f"QR fallback {fallback_id!r} must contain the exact QR target URL"
            )
    return elements, used_sources, used_assets


def _validate_approval(
    value: Any,
    *,
    content_hash: str,
    require_approval: bool,
) -> dict[str, Any]:
    approval = reject_unknown_keys(
        value,
        context="approval",
        allowed={"status", "approved_by", "approved_at", "content_sha256"},
        required={"status", "approved_by", "approved_at", "content_sha256"},
    )
    status = require_string(approval["status"], context="approval.status", maximum=16)
    if status not in {"draft", "approved"}:
        raise CliError("approval.status must be draft or approved")
    if require_approval and status != "approved":
        raise CliError("approval.status must be approved")
    if status == "approved":
        require_string(
            approval["approved_by"],
            context="approval.approved_by",
            maximum=200,
        )
        parse_aware_datetime(approval["approved_at"], context="approval.approved_at")
        digest = require_string(
            approval["content_sha256"],
            context="approval.content_sha256",
            maximum=64,
        )
        if not _SHA256.fullmatch(digest):
            raise CliError(
                "approval.content_sha256 must be 64 lowercase hex characters"
            )
        if digest != content_hash:
            raise CliError(
                "approval.content_sha256 does not match the current manifest content; "
                "author approval must be renewed after every content change"
            )
    else:
        for key in ("approved_by", "approved_at", "content_sha256"):
            if approval[key] is not None:
                raise CliError(f"approval.{key} must be null while status is draft")
    return approval


def validate_manifest_document(
    document: Any,
    *,
    manifest_path: Path,
    verify_assets: bool = True,
    require_approval: bool = True,
    enforce_contrast: bool = True,
) -> dict[str, Any]:
    """Validate a parsed manifest and return a non-content audit report."""
    manifest = reject_unknown_keys(
        document,
        context="manifest",
        allowed=_TOP_KEYS,
        required=_TOP_KEYS,
    )
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise CliError(
            f"schema_version must be {MANIFEST_SCHEMA_VERSION!r}, got "
            f"{manifest['schema_version']!r}"
        )
    placeholder = has_placeholder(manifest)
    if placeholder is not None:
        path, text = placeholder
        raise CliError(f"placeholder content is forbidden at {path}: {text!r}")

    document_record = _validate_document(manifest["document"])
    _, canvas_width, canvas_height = _validate_canvas(manifest["canvas"])
    (
        _,
        trim_width,
        trim_height,
        bleed,
        safe_margin,
        artboard_width,
        artboard_height,
    ) = _validate_physical_output(manifest["physical_output"])
    scale_x = artboard_width / canvas_width
    scale_y = artboard_height / canvas_height
    if abs(scale_x - scale_y) > max(1e-6, scale_x * 0.001):
        raise CliError(
            "PowerPoint canvas and final artboard have different aspect ratios; "
            "nonuniform print scaling is forbidden"
        )
    print_scale = (scale_x + scale_y) / 2.0

    sources = _validate_sources(manifest["sources"])
    requirements, requirement_sources = _validate_requirements(
        manifest["requirements"],
        trim_width=trim_width,
        trim_height=trim_height,
        bleed=bleed,
        safe_margin=safe_margin,
        print_scale=print_scale,
    )
    quality, quality_sources = _validate_quality(manifest["quality"])
    _, colors, contrast_pairs = _validate_palette(
        manifest["palette"],
        enforce_thresholds=enforce_contrast,
    )
    assets, asset_paths, asset_sources = _validate_assets(
        manifest["assets"],
        manifest_path=manifest_path,
        verify_assets=verify_assets,
    )
    elements, element_sources, used_assets = _validate_elements(
        manifest["elements"],
        document=document_record,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        print_scale=print_scale,
        bleed=bleed,
        safe_margin=safe_margin,
        quality=quality,
        colors=colors,
        contrast_pairs=contrast_pairs,
        assets=assets,
    )
    if set(assets) != used_assets:
        unused = sorted(set(assets) - used_assets)
        raise CliError(f"unused assets are forbidden: {', '.join(unused)}")

    used_sources = (
        requirement_sources
        | quality_sources
        | asset_sources
        | element_sources
        | set(document_record["source_ids"])
    )
    unknown_sources = sorted(used_sources - set(sources))
    if unknown_sources:
        raise CliError(
            f"unknown exact source id(s): {', '.join(unknown_sources)}"
        )
    expected_source_kinds = {
        requirements["conference"]["source_id"]: "conference_rule",
        requirements["printer"]["source_id"]: "printer_rule",
    }
    for source_id, expected_kind in expected_source_kinds.items():
        if sources[source_id]["kind"] != expected_kind:
            raise CliError(
                f"source {source_id!r} must have kind {expected_kind!r} for its "
                "declared requirement"
            )
    for prefix, expected_kind in (
        ("font_guidance", "conference_rule"),
        ("raster_dpi", "conference_rule"),
    ):
        basis = quality[f"{prefix}_basis"]
        source_id = quality[f"{prefix}_source_id"]
        if basis == "conference_requirement" and sources[source_id]["kind"] != expected_kind:
            raise CliError(
                f"quality.{prefix}_source_id must reference a conference_rule"
            )
        if (
            basis == "printer_requirement"
            and sources[source_id]["kind"] != "printer_rule"
        ):
            raise CliError(
                f"quality.{prefix}_source_id must reference a printer_rule"
            )
    unused_sources = sorted(set(sources) - used_sources)
    if unused_sources:
        raise CliError(f"unused source records are forbidden: {', '.join(unused_sources)}")

    content_hash = manifest_content_hash(manifest)
    approval = _validate_approval(
        manifest["approval"],
        content_hash=content_hash,
        require_approval=require_approval,
    )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "valid": True,
        "manifest_path": str(manifest_path),
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "content_sha256": content_hash,
        "approval_status": approval["status"],
        "assets_verified": verify_assets,
        "asset_paths": {key: str(value) for key, value in asset_paths.items()},
        "counts": {
            "sources": len(sources),
            "assets": len(assets),
            "elements": len(elements),
            "text_elements": sum(
                element["type"] == "text" for element in elements.values()
            ),
            "image_elements": sum(
                element["type"] == "image" for element in elements.values()
            ),
        },
        "canvas": {
            "width_in": canvas_width,
            "height_in": canvas_height,
        },
        "physical_output": {
            "trim_width_in": trim_width,
            "trim_height_in": trim_height,
            "bleed_in": bleed,
            "safe_margin_in": safe_margin,
            "artboard_width_in": artboard_width,
            "artboard_height_in": artboard_height,
            "print_scale": print_scale,
            "print_scale_percent": print_scale * 100.0,
        },
        "quality_basis": {
            "minimum_font_pt_final": float(quality["minimum_font_pt_final"]),
            "font_guidance_basis": quality["font_guidance_basis"],
            "minimum_raster_dpi_final": float(
                quality["minimum_raster_dpi_final"]
            ),
            "raster_dpi_basis": quality["raster_dpi_basis"],
        },
        "delivery": {
            "conference_format": requirements["conference"][
                "required_delivery_format"
            ],
            "printer_color_mode": requirements["printer"][
                "accepted_color_mode"
            ],
            "printer_scaling_allowed": requirements["printer"]["scaling_allowed"],
        },
    }


def load_and_validate_manifest(
    value: str | Path,
    *,
    verify_assets: bool = True,
    require_approval: bool = True,
    enforce_contrast: bool = True,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """Load strict JSON and validate the complete poster manifest."""
    path, document = load_json_file(value)
    report = validate_manifest_document(
        document,
        manifest_path=path,
        verify_assets=verify_assets,
        require_approval=require_approval,
        enforce_contrast=enforce_contrast,
    )
    return path, document, report
