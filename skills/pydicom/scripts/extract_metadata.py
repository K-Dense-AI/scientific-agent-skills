#!/usr/bin/env python3
"""Emit a redacted, allowlisted technical DICOM metadata inventory."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from typing import Any

from _common import (
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_INPUT_BYTES,
    HARD_MAX_FILES,
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
    frame_count,
    json_bytes,
    parse_size,
    paths_overlap,
    require_pydicom,
    safe_dcmread,
)

TOOL = "extract_metadata"


def _uid_description(value: Any) -> dict[str, str] | None:
    if not value:
        return None
    pydicom = require_pydicom()
    uid = pydicom.uid.UID(str(value))
    return {"name": uid.name, "uid": str(uid)}


def _status(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return "ABSENT"
    if text in {"YES", "NO"}:
        return text
    return "OTHER"


def _lossy_status(value: Any) -> str:
    # PS3.3 C.7.6.1.1.5 uses CS values 00/01, not YES/NO.
    text = str(value or "").strip()
    return text if text in {"00", "01"} else "ABSENT" if not text else "OTHER"


def allowlisted_record(dataset: Any, *, file_id: str) -> dict[str, Any]:
    """Return only non-identifying technical fields from a metadata-only read."""

    pydicom = require_pydicom()
    transfer = dataset.file_meta.get("TransferSyntaxUID")
    transfer_info = _uid_description(transfer)
    sop_info = _uid_description(dataset.get("SOPClassUID"))
    frames, frame_warnings = frame_count(dataset)
    record: dict[str, Any] = {
        "bits_allocated": (
            int(dataset.BitsAllocated) if "BitsAllocated" in dataset else None
        ),
        "bits_stored": int(dataset.BitsStored) if "BitsStored" in dataset else None,
        "burned_in_annotation": _status(dataset.get("BurnedInAnnotation")),
        "columns": int(dataset.Columns) if "Columns" in dataset else None,
        "file_id": file_id,
        "frames": frames,
        "has_modality_transform": bool(
            "ModalityLUTSequence" in dataset
            or "RescaleSlope" in dataset
            or "RescaleIntercept" in dataset
        ),
        "has_voi_transform": bool(
            "VOILUTSequence" in dataset
            or "WindowCenter" in dataset
            or "WindowWidth" in dataset
        ),
        "high_bit": int(dataset.HighBit) if "HighBit" in dataset else None,
        "lossy_image_compression": _lossy_status(dataset.get("LossyImageCompression")),
        "modality": str(dataset.get("Modality", "UNSPECIFIED")),
        "photometric_interpretation": str(
            dataset.get("PhotometricInterpretation", "UNSPECIFIED")
        ),
        "pixel_representation": (
            int(dataset.PixelRepresentation)
            if "PixelRepresentation" in dataset
            else None
        ),
        "recognizable_visual_features": _status(
            dataset.get("RecognizableVisualFeatures")
        ),
        "rows": int(dataset.Rows) if "Rows" in dataset else None,
        "samples_per_pixel": (
            int(dataset.SamplesPerPixel) if "SamplesPerPixel" in dataset else None
        ),
        "sop_class": sop_info,
        "transfer_syntax": transfer_info,
        "warnings": frame_warnings,
    }
    if transfer_info is not None:
        uid = pydicom.uid.UID(transfer_info["uid"])
        record["transfer_syntax"]["compressed"] = (
            bool(uid.is_compressed) if uid.is_transfer_syntax else None
        )
        if not uid.is_transfer_syntax:
            record["warnings"].append("Transfer Syntax UID is not recognized.")
    return record


def aggregate_records(
    records: list[dict[str, Any]], *, read_failures: int
) -> dict[str, Any]:
    modalities: Counter[str] = Counter()
    sop_classes: Counter[str] = Counter()
    transfer_syntaxes: Counter[str] = Counter()
    photometric: Counter[str] = Counter()
    burned_in: Counter[str] = Counter()
    recognizable: Counter[str] = Counter()
    compressed = 0
    image_like = 0
    total_frames = 0
    for record in records:
        modalities[record["modality"]] += 1
        photometric[record["photometric_interpretation"]] += 1
        burned_in[record["burned_in_annotation"]] += 1
        recognizable[record["recognizable_visual_features"]] += 1
        if record["sop_class"]:
            sop_classes[record["sop_class"]["name"]] += 1
        if record["transfer_syntax"]:
            transfer_syntaxes[record["transfer_syntax"]["name"]] += 1
            compressed += int(record["transfer_syntax"].get("compressed", False))
        if record["rows"] is not None and record["columns"] is not None:
            image_like += 1
        total_frames += record["frames"]
    return {
        "burned_in_annotation": counter_dict(burned_in),
        "compressed_files": compressed,
        "image_like_files": image_like,
        "modalities": counter_dict(modalities),
        "photometric_interpretations": counter_dict(photometric),
        "read_failures": read_failures,
        "recognizable_visual_features": counter_dict(recognizable),
        "sop_classes": counter_dict(sop_classes),
        "successful_files": len(records),
        "total_frames_declared": total_frames,
        "transfer_syntaxes": counter_dict(transfer_syntaxes),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    max_bytes = parse_size(
        args.max_input_bytes,
        name="max_input_bytes",
        maximum=HARD_MAX_INPUT_BYTES,
    )
    max_files = bounded_int(
        args.max_files,
        name="max_files",
        minimum=1,
        maximum=HARD_MAX_FILES,
    )
    source = checked_input(
        args.input,
        root=args.root,
        kind="any",
        max_bytes=max_bytes,
    )
    files = collect_local_files(
        source,
        max_files=max_files,
        max_bytes=max_bytes,
        recursive=args.recursive,
    )
    records: list[dict[str, Any]] = []
    read_failures = 0
    tags = list(TECHNICAL_KEYWORDS) + ["ModalityLUTSequence", "VOILUTSequence"]
    for index, path in enumerate(files, start=1):
        try:
            dataset = safe_dcmread(
                path,
                stop_before_pixels=True,
                force=args.force_dicom_read,
                specific_tags=tags,
            )
            records.append(allowlisted_record(dataset, file_id=f"file-{index:06d}"))
        except ToolError:
            read_failures += 1
    aggregate = aggregate_records(records, read_failures=read_failures)
    report: dict[str, Any] = {
        "aggregate": aggregate,
        "allowlist_only": True,
        "file_names_emitted": False,
        "full_metadata_dump_supported": False,
        "network_accessed": False,
        "ok": bool(records),
        "phi_values_emitted": False,
        "schema_version": SCHEMA_VERSION,
        "technical_inventory_only": True,
        "tool": TOOL,
        "warnings": [
            "DICOM metadata and pixels may contain PHI.",
            "This report omits patient, study, series, instance, date, and free-text identifiers.",
            "Technical inventory is not DICOM conformance or diagnostic validation.",
        ],
    }
    if args.per_file:
        report["records"] = records
    return report


def render_text(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "Redacted DICOM technical inventory",
        f"Successful files: {aggregate['successful_files']}",
        f"Read failures: {aggregate['read_failures']}",
        f"Image-like files: {aggregate['image_like_files']}",
        f"Compressed files: {aggregate['compressed_files']}",
        f"Declared frames: {aggregate['total_frames_declared']}",
        "No file names, patient/study/series/instance identifiers, dates, or free text emitted.",
        "Not a DICOM conformance or diagnostic report.",
    ]
    for heading, key in (
        ("Modalities", "modalities"),
        ("SOP classes", "sop_classes"),
        ("Transfer syntaxes", "transfer_syntaxes"),
    ):
        lines.append(f"{heading}:")
        values = aggregate[key]
        if not values:
            lines.append("  (none)")
        for name, count in values.items():
            lines.append(f"  {name}: {count}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a redacted allowlisted technical DICOM inventory; never "
            "prints a full metadata dump or known PHI fields."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Local authorized data only. DICOM metadata and pixels may contain PHI.
The default is aggregate JSON with no file names or per-instance identifiers.

Examples:
  python extract_metadata.py image.dcm
  python extract_metadata.py dicom-dir --recursive --output inventory.json
  python extract_metadata.py image.dcm --per-file --format text
""",
    )
    parser.add_argument("input", help="Local DICOM file or directory")
    parser.add_argument("--root", default=".", help="Existing local I/O root")
    parser.add_argument(
        "--recursive", action="store_true", help="Recursively inspect a directory"
    )
    parser.add_argument(
        "--per-file",
        action="store_true",
        help="Include allowlisted records keyed by synthetic file IDs",
    )
    parser.add_argument(
        "--format", choices=("json", "text"), default="json", help="Output format"
    )
    parser.add_argument("--output", "-o", help="Private local report file")
    parser.add_argument(
        "--force-dicom-read",
        action="store_true",
        help="Parse datasets lacking a File Format header; does not validate them",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help=f"Maximum files to inspect (default: {DEFAULT_MAX_FILES})",
    )
    parser.add_argument(
        "--max-input-bytes",
        default=str(DEFAULT_MAX_INPUT_BYTES),
        help="Maximum bytes per input file (integer or B/KiB/MiB/GiB)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite an existing report only"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = build_report(args)
        if args.format == "json":
            payload = json_bytes(report)
        else:
            payload = render_text(report).encode("utf-8")
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
            atomic_write(destination, payload, force=args.force)
            emit_json(
                {
                    "network_accessed": False,
                    "ok": report["ok"],
                    "report_written": True,
                    "tool": TOOL,
                }
            )
        else:
            sys.stdout.buffer.write(payload)
        return 0 if report["ok"] else 1
    except Exception as exc:  # noqa: BLE001 - sanitize unexpected library errors
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
