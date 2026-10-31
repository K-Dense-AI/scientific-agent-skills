#!/usr/bin/env python3
"""Create a requirement-bound PowerPoint export and print plan."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import CliError, emit_json
from _manifest import load_and_validate_manifest


def build_export_plan(
    document: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    canvas = validation["canvas"]
    physical = validation["physical_output"]
    conference = document["requirements"]["conference"]
    printer = document["requirements"]["printer"]
    delivery = conference["required_delivery_format"]
    color_mode = printer["accepted_color_mode"]
    print_scale = float(physical["print_scale"])
    font_faces = sorted(
        {
            element["font_face"]
            for element in document["elements"]
            if element["type"] == "text"
        }
    )

    blockers: list[dict[str, str]] = []
    manual_actions: list[str] = [
        "Open only the generated, technically inspected .pptx in a fully patched PowerPoint.",
        "Run Review > Check Accessibility, inspect the Reading Order pane, and test keyboard/screen-reader navigation.",
        "Inspect every edge, text box, figure, equation, glyph, and QR fallback at 100% and at final-output scale.",
        "Confirm every declared font is installed and licensed on the review/export workstation; inspect substitution in PowerPoint and the exported PDF.",
    ]
    if color_mode == "CMYK":
        blockers.append(
            {
                "code": "CMYK_CONVERSION_REQUIRED",
                "message": (
                    "PowerPoint is an RGB authoring workflow. The confirmed printer "
                    "requires CMYK, so obtain a printer-approved conversion/profile "
                    "and proof; this tool cannot claim the PPTX or native PDF is "
                    "CMYK-compliant."
                ),
            }
        )
    elif color_mode == "PRINTER_MANAGED":
        manual_actions.append(
            "Ask the printer to document its RGB-to-output conversion/profile and approve a color proof."
        )
    else:
        manual_actions.append(
            "Confirm the printer accepts RGB and approve a physical or contract color proof."
        )

    if delivery in {"PDF", "PDF_AND_PPTX"}:
        manual_actions.extend(
            [
                "In PowerPoint, export a PDF using Standard/high print quality rather than Minimum size.",
                "Record the exporter and settings. On macOS, 'Best for electronic distribution and accessibility' uses Microsoft's online conversion service; use a local route when document transmission is not authorized, then inspect tag/link limitations.",
                "Measure the exported PDF page size against the canvas; the physical artboard is a separate output target. Verify font rendering, tags, links, and image quality independently.",
            ]
        )
    elif delivery == "OTHER":
        blockers.append(
            {
                "code": "DELIVERY_FORMAT_REVIEW",
                "message": (
                    "The conference requires an OTHER format; obtain and record the "
                    "exact organizer workflow before delivery."
                ),
            }
        )

    if float(physical["bleed_in"]) > 0:
        manual_actions.append(
            "The slide maps to the artboard including bleed. Confirm trim/crop handling with the printer; PowerPoint does not make this a press-ready preflight."
        )
    if abs(print_scale - 1.0) > 1e-6:
        manual_actions.append(
            f"Scale uniformly to {print_scale * 100.0:.4f}% at output; do not use nonuniform fit-to-page scaling. If delivery requires a full-size PDF, arrange an approved PDF scaling step and recheck page size, tags, fonts, and effective DPI. This plan does not resize or export a PDF."
        )
    else:
        manual_actions.append("Output at 100% with no fit-to-page rescaling.")

    manual_actions.extend(
        [
            "Run inspect_pptx.py, check_layout.py, inventory_images.py, and check_palette.py on the final source package.",
            "Test-print a reduced-scale proof and obtain author sign-off on scientific content, citations, dimensions, color, and accessibility.",
            "Retain the exact visible URL/text next to each QR code and test the final printed QR code with multiple devices.",
        ]
    )
    return {
        "schema_version": "1.0",
        "manifest": {
            "path": validation["manifest_path"],
            "content_sha256": validation["content_sha256"],
            "approval_status": validation["approval_status"],
        },
        "ready_for_manual_export": not blockers,
        "dimensions": {
            "powerpoint_canvas_width_in": float(canvas["width_in"]),
            "powerpoint_canvas_height_in": float(canvas["height_in"]),
            "final_trim_width_in": float(physical["trim_width_in"]),
            "final_trim_height_in": float(physical["trim_height_in"]),
            "bleed_in_each_edge": float(physical["bleed_in"]),
            "final_artboard_width_in": float(physical["artboard_width_in"]),
            "final_artboard_height_in": float(physical["artboard_height_in"]),
            "safe_margin_in_inside_trim": float(physical["safe_margin_in"]),
            "uniform_print_scale": print_scale,
            "uniform_print_scale_percent": print_scale * 100.0,
        },
        "requirements": {
            "conference_source_id": conference["source_id"],
            "conference_max_width_in": conference["max_width_in"],
            "conference_max_height_in": conference["max_height_in"],
            "conference_orientation": conference["orientation"],
            "conference_delivery_format": delivery,
            "printer_source_id": printer["source_id"],
            "printer_accepted_color_mode": color_mode,
            "printer_scaling_allowed": printer["scaling_allowed"],
        },
        "powerpoint_constraints": {
            "custom_dimension_range_in": [1.0, 56.0],
            "all_slides_same_size": True,
            "color_authoring_mode": "RGB",
            "notice": (
                "Physical trim size, PowerPoint canvas size, and output artboard "
                "size are separate. Conference and printer records in this manifest, "
                "not a generic poster preset, control delivery."
            ),
        },
        "quality_thresholds": {
            "minimum_font_pt_final": document["quality"][
                "minimum_font_pt_final"
            ],
            "font_guidance_basis": document["quality"]["font_guidance_basis"],
            "font_guidance_source_id": document["quality"][
                "font_guidance_source_id"
            ],
            "minimum_raster_dpi_final": document["quality"][
                "minimum_raster_dpi_final"
            ],
            "raster_dpi_basis": document["quality"]["raster_dpi_basis"],
            "raster_dpi_source_id": document["quality"][
                "raster_dpi_source_id"
            ],
        },
        "font_preflight": {
            "declared_font_faces": font_faces,
            "fonts_embedded_by_generator": False,
            "notice": (
                "A font name in PresentationML does not prove availability, "
                "embeddability, or correct rendering. PowerPoint and PDF review "
                "remain required."
            ),
        },
        "pdf_preflight": {
            "exported_by_tool": False,
            "canvas_width_pt": float(canvas["width_in"]) * 72.0,
            "canvas_height_pt": float(canvas["height_in"]) * 72.0,
            "final_artboard_width_pt": float(physical["artboard_width_in"]) * 72.0,
            "final_artboard_height_pt": float(physical["artboard_height_in"]) * 72.0,
            "full_size_pdf_requires_scaling": abs(print_scale - 1.0) > 1e-6,
        },
        "media_profile": {
            "accepted_manifest_assets": ["PNG", "JPEG"],
            "audio_video_or_linked_media_allowed": False,
        },
        "blockers": blockers,
        "manual_actions": manual_actions,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a no-network export/print plan from approved conference and "
            "printer requirements, explicitly separating canvas, trim, bleed, "
            "scaling, RGB/CMYK handling, and final-output quality."
        )
    )
    parser.add_argument("manifest", help="approved local poster manifest JSON")
    parser.add_argument("--output", help="optional new JSON plan path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        _, document, validation = load_and_validate_manifest(
            args.manifest,
            verify_assets=False,
            require_approval=True,
        )
        report = build_export_plan(document, validation)
        emit_json(report, output=args.output)
        return 0 if report["ready_for_manual_export"] else 1
    except CliError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
