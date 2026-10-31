#!/usr/bin/env python3
"""Bounded metadata-only DICOM technical inventory and structural checks."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from typing import Any

from _common import (
    DEFAULT_MAX_DECOMPRESSED_BYTES,
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_FRAMES,
    DEFAULT_MAX_INPUT_BYTES,
    HARD_MAX_DECOMPRESSED_BYTES,
    HARD_MAX_FILES,
    HARD_MAX_FRAMES,
    HARD_MAX_INPUT_BYTES,
    SCHEMA_VERSION,
    TECHNICAL_KEYWORDS,
    ToolError,
    atomic_write,
    bounded_int,
    checked_input,
    checked_output,
    collect_local_files,
    counter_dict,
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

TOOL = "dicom_inventory"
INVENTORY_TAGS = list(TECHNICAL_KEYWORDS) + [
    "SOPInstanceUID",
    "PatientIdentityRemoved",
]


def _issue(code: str, message: str, severity: str = "error") -> dict[str, str]:
    return {"code": code, "message": message, "severity": severity}


def inspect_dataset(
    dataset: Any,
    *,
    file_id: str,
    file_size: int,
    max_frames: int,
    max_decompressed_bytes: int,
    forced_read: bool,
) -> dict[str, Any]:
    pydicom = require_pydicom()
    issues: list[dict[str, str]] = []
    file_meta = dataset.file_meta
    try:
        pydicom.dataset.validate_file_meta(file_meta, enforce_standard=True)
    except Exception:  # noqa: BLE001 - any validation failure becomes a finding
        issues.append(
            _issue(
                "file_meta_invalid",
                "Required DICOM File Meta Information is missing, empty, or invalid.",
            )
        )

    transfer_value = str(file_meta.get("TransferSyntaxUID", ""))
    transfer = None
    if not valid_uid(transfer_value):
        issues.append(
            _issue(
                "transfer_syntax_invalid", "Transfer Syntax UID is absent or invalid."
            )
        )
    else:
        transfer = pydicom.uid.UID(transfer_value)
        if not transfer.is_transfer_syntax:
            issues.append(_issue("transfer_syntax_unknown", "UID is not a recognized transfer syntax."))
            transfer = None

    sop_class = str(dataset.get("SOPClassUID", ""))
    sop_instance = str(dataset.get("SOPInstanceUID", ""))
    if not valid_uid(sop_class):
        issues.append(
            _issue("sop_class_invalid", "SOP Class UID is absent or invalid.")
        )
    if not valid_uid(sop_instance):
        issues.append(
            _issue("sop_instance_invalid", "SOP Instance UID is absent or invalid.")
        )
    media_class = str(file_meta.get("MediaStorageSOPClassUID", ""))
    media_instance = str(file_meta.get("MediaStorageSOPInstanceUID", ""))
    if sop_class and media_class and sop_class != media_class:
        issues.append(
            _issue(
                "media_sop_class_mismatch",
                "Media Storage SOP Class UID does not match the dataset SOP Class UID.",
            )
        )
    if sop_instance and media_instance and sop_instance != media_instance:
        issues.append(
            _issue(
                "media_sop_instance_mismatch",
                "Media Storage SOP Instance UID does not match the dataset SOP Instance UID.",
            )
        )

    image_plan: dict[str, Any] | None = None
    if "Rows" in dataset or "Columns" in dataset:
        try:
            image_plan = pixel_plan(
                dataset,
                max_frames=max_frames,
                max_decompressed_bytes=max_decompressed_bytes,
            )
            bits_allocated = image_plan["bits_allocated"]
            bits_stored = int(dataset.get("BitsStored", bits_allocated))
            high_bit = int(dataset.get("HighBit", bits_stored - 1))
            if bits_stored < 1 or bits_stored > bits_allocated:
                issues.append(
                    _issue(
                        "bits_stored_invalid",
                        "Bits Stored must be positive and no greater than Bits Allocated.",
                    )
                )
            if high_bit != bits_stored - 1:
                issues.append(
                    _issue(
                        "high_bit_unexpected",
                        "High Bit does not equal Bits Stored minus one.",
                        "warning",
                    )
                )
            representation = dataset.get("PixelRepresentation")
            if representation is None:
                issues.append(
                    _issue(
                        "pixel_representation_absent",
                        "Pixel Representation is absent; review whether integer or float pixel data is used.",
                        "warning",
                    )
                )
            elif int(representation) not in {0, 1}:
                issues.append(
                    _issue(
                        "pixel_representation_invalid",
                        "Pixel Representation must be 0 or 1 for integer Pixel Data.",
                    )
                )
            samples = image_plan["samples_per_pixel"]
            if samples > 1 and "PlanarConfiguration" not in dataset:
                issues.append(
                    _issue(
                        "planar_configuration_missing",
                        "Planar Configuration is required for multi-sample native pixel data.",
                        "warning",
                    )
                )
            if not dataset.get("PhotometricInterpretation"):
                issues.append(
                    _issue(
                        "photometric_interpretation_missing",
                        "Photometric Interpretation is absent.",
                    )
                )
        except ToolError as exc:
            issues.append(_issue("pixel_metadata_invalid", str(exc)))

    if forced_read:
        issues.append(
            _issue(
                "forced_read",
                "Dataset was parsed without requiring a DICOM File Format header.",
                "warning",
            )
        )
    errors = sum(issue["severity"] == "error" for issue in issues)
    warnings = sum(issue["severity"] == "warning" for issue in issues)
    return {
        "errors": errors,
        "file_id": file_id,
        "file_size_bytes": file_size,
        "forced_read": forced_read,
        "image": image_plan,
        "issues": issues,
        "modality": str(dataset.get("Modality", "UNSPECIFIED")),
        "ok": errors == 0,
        "patient_identity_removed_claim": str(
            dataset.get("PatientIdentityRemoved", "ABSENT")
        ).upper(),
        "photometric_interpretation": str(
            dataset.get("PhotometricInterpretation", "UNSPECIFIED")
        ),
        "sop_class": {
            "name": pydicom.uid.UID(sop_class).name if valid_uid(sop_class) else None,
            "uid": sop_class or None,
        },
        "transfer_syntax": {
            "compressed": bool(transfer.is_compressed) if transfer else None,
            "name": transfer.name if transfer else None,
            "uid": transfer_value or None,
        },
        "warnings": warnings,
    }


def inventory(args: argparse.Namespace) -> dict[str, Any]:
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
    max_files = bounded_int(
        args.max_files,
        name="max_files",
        minimum=1,
        maximum=HARD_MAX_FILES,
    )
    max_frames = bounded_int(
        args.max_frames,
        name="max_frames",
        minimum=1,
        maximum=HARD_MAX_FRAMES,
    )
    source = checked_input(
        args.input,
        root=args.root,
        kind="any",
        max_bytes=max_input_bytes,
    )
    files = collect_local_files(
        source,
        max_files=max_files,
        max_bytes=max_input_bytes,
        recursive=args.recursive,
    )
    records: list[dict[str, Any]] = []
    parse_failures = 0
    for index, path in enumerate(files, start=1):
        file_id = f"file-{index:06d}"
        try:
            dataset = safe_dcmread(
                path,
                stop_before_pixels=True,
                force=args.force_dicom_read,
                specific_tags=INVENTORY_TAGS,
            )
            records.append(
                inspect_dataset(
                    dataset,
                    file_id=file_id,
                    file_size=path.stat().st_size,
                    max_frames=max_frames,
                    max_decompressed_bytes=max_decompressed_bytes,
                    forced_read=args.force_dicom_read,
                )
            )
        except ToolError:
            parse_failures += 1
            records.append(
                {
                    "errors": 1,
                    "file_id": file_id,
                    "file_size_bytes": path.stat().st_size,
                    "issues": [
                        _issue(
                            "parse_failed",
                            "File could not be parsed as bounded DICOM metadata.",
                        )
                    ],
                    "ok": False,
                    "warnings": 0,
                }
            )
    issue_codes: Counter[str] = Counter()
    for record in records:
        for issue in record["issues"]:
            issue_codes[issue["code"]] += 1
    error_files = sum(not record["ok"] for record in records)
    return {
        "aggregate": {
            "error_files": error_files,
            "files_examined": len(records),
            "issue_codes": counter_dict(issue_codes),
            "parse_failures": parse_failures,
            "warning_files": sum(bool(record["warnings"]) for record in records),
        },
        "file_names_emitted": False,
        "metadata_only": True,
        "network_accessed": False,
        "ok": error_files == 0 and bool(records),
        "records": records,
        "schema_version": SCHEMA_VERSION,
        "technical_checks_only": True,
        "tool": TOOL,
        "warnings": [
            "No pixel data was loaded or decompressed.",
            "This is not complete IOD validation, clinical validation, or a diagnostic claim.",
            "Patient Identity Removed=YES, if present, is reported but not trusted as proof.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Perform bounded metadata-only DICOM File Format and image-pixel "
            "technical checks without printing PHI values."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Local authorized data only. Metadata and pixels may contain PHI. This tool does
not load pixels, validate every IOD rule, establish de-identification, or make
diagnostic claims.

Examples:
  python dicom_inventory.py image.dcm
  python dicom_inventory.py dicom-dir --recursive --output inventory.json
""",
    )
    parser.add_argument("input", help="Local DICOM file or directory")
    parser.add_argument("--root", default=".", help="Existing local I/O root")
    parser.add_argument(
        "--recursive", action="store_true", help="Recursively inspect directories"
    )
    parser.add_argument("--output", "-o", help="Private JSON report path")
    parser.add_argument(
        "--force-dicom-read",
        action="store_true",
        help="Parse missing File Format headers; records a warning",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help=f"Maximum files (default: {DEFAULT_MAX_FILES})",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=DEFAULT_MAX_FRAMES,
        help=f"Maximum declared frames (default: {DEFAULT_MAX_FRAMES})",
    )
    parser.add_argument(
        "--max-input-bytes",
        default=str(DEFAULT_MAX_INPUT_BYTES),
        help="Maximum bytes per input file",
    )
    parser.add_argument(
        "--max-decompressed-bytes",
        default=str(DEFAULT_MAX_DECOMPRESSED_BYTES),
        help="Maximum estimated full uncompressed pixel bytes",
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite an existing report only"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = inventory(args)
        if args.output:
            destination = checked_output(args.output, root=args.root, force=args.force)
            source = checked_input(
                args.input,
                root=args.root,
                kind="any",
                max_bytes=parse_size(
                    args.max_input_bytes,
                    name="max_input_bytes",
                    maximum=HARD_MAX_INPUT_BYTES,
                ),
            )
            if source.is_file() and paths_overlap(source, destination):
                raise ToolError("report must not overwrite its input")
            atomic_write(destination, json_bytes(report), force=args.force)
            emit_json(
                {
                    "ok": report["ok"],
                    "report_written": True,
                    "tool": TOOL,
                }
            )
        else:
            emit_json(report)
        return 0 if report["ok"] else 1
    except Exception as exc:  # noqa: BLE001 - sanitize unexpected library errors
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
