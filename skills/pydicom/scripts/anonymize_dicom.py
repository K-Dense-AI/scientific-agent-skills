#!/usr/bin/env python3
"""Create a bounded, pseudonymized DICOM derivative without compliance claims.

This local-only helper preserves the source file and writes a new output. DICOM
metadata, file names, private elements, overlays, structured content, and pixel
data may contain PHI. The starter profile is deliberately incomplete: select a
profile for the intended context and obtain privacy/DICOM expert verification.
"""

from __future__ import annotations

import argparse
import os
import secrets
import stat
import sys
from collections import Counter
from collections.abc import Sequence as SequenceValue
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from _common import (
    DEFAULT_MAX_ELEMENTS,
    DEFAULT_MAX_INPUT_BYTES,
    DEFAULT_MAX_OUTPUT_BYTES,
    HARD_MAX_ELEMENTS,
    HARD_MAX_INPUT_BYTES,
    HARD_MAX_OUTPUT_BYTES,
    MAX_SEQUENCE_DEPTH,
    SCHEMA_VERSION,
    STRUCTURAL_UID_KEYWORDS,
    TEXT_VRS,
    UID_REMAP_KEYWORDS,
    ToolError,
    atomic_generated_file,
    atomic_write,
    bounded_int,
    checked_input,
    checked_output,
    counter_dict,
    derive_token,
    derive_uid,
    element_tag,
    emit_json,
    fail_json,
    json_bytes,
    load_json,
    parse_size,
    paths_overlap,
    require_pydicom,
    require_text,
    safe_dcmread,
    sha256_text,
    starter_profile,
    validate_profile,
)

TOOL = "anonymize_dicom"
PIXEL_KEYWORDS = {"DoubleFloatPixelData", "FloatPixelData", "PixelData"}


def _load_key(path: Path) -> bytes:
    info = path.stat()
    if os.name != "nt":
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise ToolError("UID key permissions must deny group and other access")
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            raise ToolError("UID key must be owned by the current user")
    payload = path.read_bytes()
    if len(payload) == 64:
        try:
            payload = bytes.fromhex(payload.decode("ascii"))
        except (UnicodeError, ValueError):
            pass
    if len(payload) < 32:
        raise ToolError("UID key must contain at least 32 bytes of secret material")
    return payload[:128]


def _map_scalar_uid(
    value: Any, *, key: bytes, scope: str, mapping: dict[str, str]
) -> str:
    original = str(value)
    replacement = mapping.get(original)
    if replacement is None:
        replacement = derive_uid(original, key=key, scope=scope)
        mapping[original] = replacement
    return replacement


def _map_uid_value(
    value: Any, *, key: bytes, scope: str, mapping: dict[str, str]
) -> Any:
    if isinstance(value, SequenceValue) and not isinstance(value, (str, bytes)):
        return [
            _map_scalar_uid(item, key=key, scope=scope, mapping=mapping)
            for item in value
        ]
    return _map_scalar_uid(value, key=key, scope=scope, mapping=mapping)


def _pseudonym_value(value: Any, *, keyword: str, key: bytes, scope: str) -> str:
    token = derive_token(str(value), key=key, scope=scope)
    if keyword == "PatientName":
        return f"PSEUDONYM^{token}"
    return f"P-{token}"


def _shift_date_text(value: Any, days: int) -> tuple[str, bool]:
    text = str(value)
    if len(text) != 8 or not text.isdigit():
        return "", False
    try:
        shifted = date(int(text[:4]), int(text[4:6]), int(text[6:8])) + timedelta(
            days=days
        )
    except (ValueError, OverflowError):
        return "", False
    return shifted.strftime("%Y%m%d"), True


def _shift_datetime_text(value: Any, days: int) -> tuple[str, bool]:
    text = str(value)
    if len(text) < 8 or not text[:8].isdigit():
        return "", False
    shifted, ok = _shift_date_text(text[:8], days)
    return (shifted + text[8:], True) if ok else ("", False)


def _date_action(
    element: Any,
    *,
    date_policy: str,
    date_shift_days: int | None,
    retain_times: bool,
    counters: Counter[str],
) -> None:
    vr = str(element.VR)
    if date_policy == "keep":
        counters["dates_kept"] += 1
        return
    if date_policy == "empty":
        element.value = ""
        counters["dates_or_times_emptied"] += 1
        return
    if date_shift_days is None:
        raise ToolError("date shift policy requires --date-shift-days")
    if vr == "TM":
        if retain_times:
            counters["standalone_times_retained"] += 1
        else:
            element.value = ""
            counters["standalone_times_emptied"] += 1
        return
    if isinstance(element.value, SequenceValue) and not isinstance(
        element.value, (str, bytes)
    ):
        values = list(element.value)
    else:
        values = [element.value]
    shifted_values: list[str] = []
    for value in values:
        if vr == "DA":
            shifted, ok = _shift_date_text(value, date_shift_days)
        else:
            shifted, ok = _shift_datetime_text(value, date_shift_days)
        shifted_values.append(shifted)
        counters["dates_shifted" if ok else "unshiftable_dates_emptied"] += 1
    element.value = shifted_values if len(shifted_values) > 1 else shifted_values[0]


def _looks_instance_uid(keyword: str) -> bool:
    return keyword in UID_REMAP_KEYWORDS or keyword.endswith(
        ("InstanceUID", "FrameOfReferenceUID")
    )


def transform_dataset(
    dataset: Any,
    *,
    profile: dict[str, Any],
    key: bytes,
    scope: str,
    date_shift_days: int | None,
    retain_times: bool,
    allow_private_retention: bool,
    allow_date_retention: bool,
    max_elements: int,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Apply the bounded starter/profile actions in place."""

    actions = profile["actions"]
    private_policy = profile["private_policy"]
    date_policy = profile["date_policy"]
    if private_policy == "keep" and not allow_private_retention:
        raise ToolError(
            "private retention requires --allow-private-retention and expert review"
        )
    if date_policy == "keep" and not allow_date_retention:
        raise ToolError("date retention requires --allow-date-retention")
    if date_policy == "shift" and date_shift_days is None:
        raise ToolError("date shift policy requires --date-shift-days")
    if date_policy != "shift" and date_shift_days is not None:
        raise ToolError("--date-shift-days is only valid with date policy shift")
    if retain_times and date_policy != "shift":
        raise ToolError("--retain-times is only valid with date policy shift")

    counters: Counter[str] = Counter()
    unresolved_text: Counter[str] = Counter()
    unresolved_uids: Counter[str] = Counter()
    uid_mapping: dict[str, str] = {}
    stack: list[tuple[Any, int]] = [(dataset, 0)]
    seen_elements = 0
    pixel_present = False
    burned_in_status = str(dataset.get("BurnedInAnnotation", "")).upper()
    recognizable_status = str(dataset.get("RecognizableVisualFeatures", "")).upper()

    while stack:
        current, depth = stack.pop()
        if depth > MAX_SEQUENCE_DEPTH:
            raise ToolError("sequence nesting exceeds the hard depth limit")
        for element in list(current):
            seen_elements += 1
            if seen_elements > max_elements:
                raise ToolError("data-element limit exceeded")
            keyword = element.keyword or element_tag(element)
            group = int(element.tag.group)

            if keyword in PIXEL_KEYWORDS:
                pixel_present = True
                counters["pixel_elements_preserved"] += 1
                continue

            if element.tag.is_private:
                counters["private_elements_seen"] += 1
                if private_policy == "reject":
                    raise ToolError("private elements present under reject policy")
                if private_policy == "remove":
                    del current[element.tag]
                    counters["private_elements_removed"] += 1
                    continue
                counters["private_elements_retained"] += 1

            if 0x5000 <= group <= 0x50FF or 0x6000 <= group <= 0x60FF:
                del current[element.tag]
                counters["overlay_or_curve_elements_removed"] += 1
                continue

            action = actions.get(keyword, actions.get(element_tag(element)))
            if action == "remove":
                del current[element.tag]
                counters["elements_removed"] += 1
                continue
            if action == "empty":
                element.value = [] if str(element.VR) == "SQ" else ""
                counters["elements_emptied"] += 1
                continue
            if action == "pseudonym":
                if str(element.VR) not in TEXT_VRS or str(element.VR) == "UI":
                    raise ToolError(
                        "pseudonym action is only valid for non-UID text elements"
                    )
                element.value = _pseudonym_value(
                    element.value,
                    keyword=keyword,
                    key=key,
                    scope=scope,
                )
                counters["elements_pseudonymized"] += 1
                continue
            if action == "uid":
                if str(element.VR) != "UI":
                    raise ToolError("uid action is only valid for UI elements")
                if keyword in STRUCTURAL_UID_KEYWORDS:
                    raise ToolError("structural UIDs must not be remapped")
                element.value = _map_uid_value(
                    element.value,
                    key=key,
                    scope=scope,
                    mapping=uid_mapping,
                )
                counters["uid_elements_remapped"] += 1
                continue
            if action == "keep":
                counters["profile_keep_actions"] += 1
                # Keeping a sequence container must not exempt its children
                # from their own privacy actions.
                if str(element.VR) != "SQ":
                    continue

            if str(element.VR) == "SQ":
                for item in reversed(list(element.value)):
                    stack.append((item, depth + 1))
                continue

            if str(element.VR) in {"DA", "DT", "TM"}:
                _date_action(
                    element,
                    date_policy=date_policy,
                    date_shift_days=date_shift_days,
                    retain_times=retain_times,
                    counters=counters,
                )
                continue

            if str(element.VR) == "UI":
                if keyword in STRUCTURAL_UID_KEYWORDS:
                    counters["structural_uid_elements_preserved"] += 1
                elif _looks_instance_uid(keyword):
                    element.value = _map_uid_value(
                        element.value,
                        key=key,
                        scope=scope,
                        mapping=uid_mapping,
                    )
                    counters["uid_elements_remapped"] += 1
                else:
                    unresolved_uids[keyword] += 1
                continue

            if str(element.VR) in TEXT_VRS and action != "keep":
                unresolved_text[keyword] += 1

    # Never assert successful de-identification. These attributes are removed by
    # the starter profile and then set conservatively after processing.
    dataset.PatientIdentityRemoved = "NO"
    if "DeidentificationMethod" in dataset:
        del dataset.DeidentificationMethod
    if "DeidentificationMethodCodeSequence" in dataset:
        del dataset.DeidentificationMethodCodeSequence

    report = {
        "actions": counter_dict(counters),
        "burned_in_annotation": burned_in_status or "ABSENT",
        "date_policy": date_policy,
        "elements_examined": seen_elements,
        "expert_verification_required": True,
        "not_a_compliance_claim": True,
        "patient_identity_removed": "NO",
        "pixel_data_preserved": pixel_present,
        "private_policy": private_policy,
        "recognizable_visual_features": recognizable_status or "ABSENT",
        "residual_text_elements_by_keyword": counter_dict(unresolved_text),
        "unclassified_uid_elements_by_keyword": counter_dict(unresolved_uids),
        "uid_mappings": len(uid_mapping),
    }
    return report, uid_mapping


def _rebuild_file_meta(dataset: Any, *, original_transfer_syntax: Any) -> None:
    require_pydicom()
    from pydicom.dataset import FileMetaDataset
    from pydicom.uid import PYDICOM_IMPLEMENTATION_UID

    if not dataset.get("SOPClassUID") or not dataset.get("SOPInstanceUID"):
        raise ToolError("SOP Class and SOP Instance UIDs are required for safe output")
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationVersion = b"\x00\x01"
    file_meta.MediaStorageSOPClassUID = dataset.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = dataset.SOPInstanceUID
    file_meta.TransferSyntaxUID = original_transfer_syntax
    file_meta.ImplementationClassUID = PYDICOM_IMPLEMENTATION_UID
    dataset.file_meta = file_meta
    dataset.preamble = b"\x00" * 128


def process_file(args: argparse.Namespace) -> dict[str, Any]:
    max_input_bytes = parse_size(
        args.max_input_bytes,
        name="max_input_bytes",
        maximum=HARD_MAX_INPUT_BYTES,
    )
    max_output_bytes = parse_size(
        args.max_output_bytes,
        name="max_output_bytes",
        maximum=HARD_MAX_OUTPUT_BYTES,
    )
    max_elements = bounded_int(
        args.max_elements,
        name="max_elements",
        minimum=1,
        maximum=HARD_MAX_ELEMENTS,
    )
    source = checked_input(
        args.input,
        root=args.root,
        kind="file",
        max_bytes=max_input_bytes,
    )
    destination = checked_output(args.output, root=args.root, force=args.force)
    audit_path = checked_output(args.audit_report, root=args.root, force=args.force)
    key_path = checked_input(
        args.uid_key_file,
        root=args.root,
        kind="file",
        max_bytes=4 * 1024,
    )
    for candidate in (destination, audit_path):
        if paths_overlap(source, candidate):
            raise ToolError("input and output paths must be distinct")
        if paths_overlap(key_path, candidate):
            raise ToolError("UID key and output paths must be distinct")
    if paths_overlap(source, key_path):
        raise ToolError("DICOM input and UID key must be distinct")
    if destination == audit_path:
        raise ToolError("DICOM output and audit report must be distinct")

    mapping_path: Path | None = None
    if args.uid_map_output:
        if not args.acknowledge_sensitive_map:
            raise ToolError("UID map output requires --acknowledge-sensitive-map")
        mapping_path = checked_output(
            args.uid_map_output, root=args.root, force=args.force
        )
        if mapping_path in {destination, audit_path} or paths_overlap(
            source, mapping_path
        ):
            raise ToolError("UID map path must be distinct from all other paths")
        if paths_overlap(key_path, mapping_path):
            raise ToolError("UID map must not overwrite the UID key")

    scope = require_text(args.uid_scope, name="uid_scope", maximum=128)
    key = _load_key(key_path)
    profile = starter_profile()
    profile_source = "built-in"
    if args.profile_json:
        profile_path = checked_input(
            args.profile_json,
            root=args.root,
            kind="file",
            max_bytes=1 * 1024 * 1024,
        )
        if any(
            paths_overlap(profile_path, candidate)
            for candidate in (source, destination, audit_path, key_path)
        ):
            raise ToolError("action profile must use a distinct local file")
        if mapping_path is not None and paths_overlap(profile_path, mapping_path):
            raise ToolError("action profile and UID map paths must be distinct")
        profile = validate_profile(load_json(profile_path))
        profile_source = "local-json"
    if args.private_policy:
        profile["private_policy"] = args.private_policy
    if args.date_policy:
        profile["date_policy"] = args.date_policy
    if args.date_shift_days is not None:
        bounded_int(
            args.date_shift_days,
            name="date_shift_days",
            minimum=-365_000,
            maximum=365_000,
        )

    dataset = safe_dcmread(
        source,
        stop_before_pixels=False,
        force=False,
        defer_size=args.defer_size,
    )
    pydicom = require_pydicom()
    original_transfer_syntax = dataset.file_meta.get("TransferSyntaxUID")
    if original_transfer_syntax is None:
        raise ToolError("Transfer Syntax UID is required for safe output")

    transform_report, uid_mapping = transform_dataset(
        dataset,
        profile=profile,
        key=key,
        scope=scope,
        date_shift_days=args.date_shift_days,
        retain_times=args.retain_times,
        allow_private_retention=args.allow_private_retention,
        allow_date_retention=args.allow_date_retention,
        max_elements=max_elements,
    )
    _rebuild_file_meta(dataset, original_transfer_syntax=original_transfer_syntax)

    def writer(path: Path) -> None:
        pydicom.dcmwrite(
            path,
            dataset,
            enforce_file_format=True,
            overwrite=True,
        )

    def validator(path: Path) -> None:
        check = safe_dcmread(path, stop_before_pixels=True, force=False)
        if str(check.get("PatientIdentityRemoved", "")) != "NO":
            raise ToolError("output verification failed")
        if str(check.file_meta.get("MediaStorageSOPInstanceUID", "")) != str(
            check.get("SOPInstanceUID", "")
        ):
            raise ToolError("output file meta verification failed")

    atomic_generated_file(
        destination,
        writer=writer,
        validator=validator,
        force=args.force,
        max_bytes=max_output_bytes,
    )

    warnings = [
        "This output has not been established as de-identified or compliant.",
        "DICOM metadata and pixels may still contain PHI; expert review is required.",
        "Date/time actions can affect validity and longitudinal utility.",
    ]
    if transform_report["pixel_data_preserved"]:
        warnings.append(
            "Pixel data was not inspected or cleaned for burned-in annotations "
            "or recognizable visual features."
        )
    if transform_report["burned_in_annotation"] != "NO":
        warnings.append("Burned In Annotation is absent, unknown, or not NO.")
    if transform_report["unclassified_uid_elements_by_keyword"]:
        warnings.append("One or more UI elements were not classified for remapping.")
    if transform_report["residual_text_elements_by_keyword"]:
        warnings.append("One or more textual elements remain for profile review.")
    if profile["private_policy"] == "keep":
        warnings.append("Private elements were retained by explicit high-risk policy.")
    if profile["date_policy"] == "keep":
        warnings.append("Dates/times were retained by explicit high-risk policy.")

    audit = {
        "input_files": 1,
        "network_accessed": False,
        "ok": True,
        "original_preserved": True,
        "output_files": 1,
        "profile": {
            "name": profile["name"],
            "source": profile_source,
            "version": profile["version"],
        },
        "schema_version": SCHEMA_VERSION,
        "scope_sha256": sha256_text(scope),
        "tool": TOOL,
        "transform": transform_report,
        "uid_key_sha256": sha256_text(key.hex()),
        "uid_map_written": mapping_path is not None,
        "warnings": warnings,
    }
    atomic_write(audit_path, json_bytes(audit), force=args.force)
    if mapping_path is not None:
        mapping_document = {
            "entries": [
                {"original": original, "replacement": replacement}
                for original, replacement in sorted(uid_mapping.items())
            ],
            "schema_version": SCHEMA_VERSION,
            "scope_sha256": sha256_text(scope),
            "sensitive": True,
            "tool": TOOL,
        }
        atomic_write(mapping_path, json_bytes(mapping_document), force=args.force)
    return audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a bounded pseudonymized DICOM derivative. This is not a "
            "DICOM PS3.15, HIPAA, GDPR, or other compliance claim."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Local authorized data only. Originals are never modified. Metadata, private
elements, file names, overlays, structured content, and pixels may contain PHI.
The output requires profile-specific privacy and DICOM expert verification.
The UID key and optional map are re-identification secrets: keep them separate
from derivatives in approved encrypted/managed storage and never commit them.

Examples:
  python anonymize_dicom.py --generate-uid-key project.key
  python anonymize_dicom.py in.dcm out.dcm --uid-key-file project.key \\
    --uid-scope study-export-v1 --audit-report out.audit.json
  python anonymize_dicom.py in.dcm out.dcm --uid-key-file project.key \\
    --uid-scope study-export-v1 --audit-report out.audit.json \\
    --date-policy shift --date-shift-days 180
""",
    )
    parser.add_argument("input", nargs="?", help="Local source DICOM file")
    parser.add_argument("output", nargs="?", help="New local DICOM output file")
    parser.add_argument(
        "--root",
        default=".",
        help="Existing local root containing every input and output (default: .)",
    )
    parser.add_argument(
        "--generate-uid-key",
        metavar="PATH",
        help="Create a new private 32-byte key and exit; refuses overwrite",
    )
    parser.add_argument(
        "--uid-key-file",
        help="Local secret key used for deterministic scoped pseudonyms and UIDs",
    )
    parser.add_argument(
        "--uid-scope",
        help="Non-PHI scope label; the same key/scope gives consistent mappings",
    )
    parser.add_argument(
        "--profile-json",
        help="Optional bounded local JSON action profile merged over starter actions",
    )
    parser.add_argument(
        "--private-policy",
        choices=("remove", "reject", "keep"),
        help="Override profile private-element policy",
    )
    parser.add_argument(
        "--date-policy",
        choices=("empty", "shift", "keep"),
        help="Override profile DA/DT/TM policy",
    )
    parser.add_argument(
        "--date-shift-days",
        type=int,
        help="Fixed date shift for all DA/DT values; partial/invalid values are emptied",
    )
    parser.add_argument(
        "--retain-times",
        action="store_true",
        help="With date shifting, retain standalone TM values (explicit risk choice)",
    )
    parser.add_argument(
        "--allow-private-retention",
        action="store_true",
        help="Acknowledge that retained private elements may contain PHI",
    )
    parser.add_argument(
        "--allow-date-retention",
        action="store_true",
        help="Acknowledge that retained dates/times may be identifying",
    )
    parser.add_argument(
        "--audit-report",
        help="Required private JSON audit report path; contains no element values",
    )
    parser.add_argument(
        "--uid-map-output",
        help="Optional private JSON mapping; contains sensitive original UIDs",
    )
    parser.add_argument(
        "--acknowledge-sensitive-map",
        action="store_true",
        help="Required to write a UID map containing original identifiers",
    )
    parser.add_argument(
        "--defer-size",
        default="1 MiB",
        help="pydicom deferred-value threshold (default: 1 MiB)",
    )
    parser.add_argument(
        "--max-input-bytes",
        default=str(DEFAULT_MAX_INPUT_BYTES),
        help="Maximum source file size (integer or B/KiB/MiB/GiB)",
    )
    parser.add_argument(
        "--max-output-bytes",
        default=str(DEFAULT_MAX_OUTPUT_BYTES),
        help="Maximum generated DICOM size (integer or B/KiB/MiB/GiB)",
    )
    parser.add_argument(
        "--max-elements",
        type=int,
        default=DEFAULT_MAX_ELEMENTS,
        help=f"Maximum recursive data elements (default: {DEFAULT_MAX_ELEMENTS})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing outputs, never the input",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.generate_uid_key:
            if args.input or args.output:
                raise ToolError("key generation does not accept input/output files")
            destination = checked_output(
                args.generate_uid_key, root=args.root, force=False
            )
            atomic_write(destination, secrets.token_bytes(32), force=False)
            emit_json(
                {
                    "key_bytes": 32,
                    "network_accessed": False,
                    "ok": True,
                    "permissions": "0600",
                    "tool": TOOL,
                }
            )
            return 0
        required = {
            "input": args.input,
            "output": args.output,
            "uid_key_file": args.uid_key_file,
            "uid_scope": args.uid_scope,
            "audit_report": args.audit_report,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ToolError(f"missing required arguments: {', '.join(missing)}")
        audit = process_file(args)
        emit_json(audit)
        return 0
    except Exception as exc:  # noqa: BLE001 - sanitize unexpected library errors
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
