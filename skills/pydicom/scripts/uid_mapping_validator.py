#!/usr/bin/env python3
"""Validate bounded DICOM UID mapping consistency without printing UIDs."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from _common import (
    MAX_JSON_BYTES,
    SCHEMA_VERSION,
    ToolError,
    atomic_write,
    bounded_int,
    checked_input,
    checked_output,
    counter_dict,
    derive_uid,
    emit_json,
    fail_json,
    json_bytes,
    load_json,
    paths_overlap,
    require_text,
    sha256_text,
    valid_uid,
)

TOOL = "uid_mapping_validator"
STANDARD_ROOT = "1.2.840.10008"


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
        raise ToolError("UID key must contain at least 32 bytes")
    return payload[:128]


def validate_mapping(
    document: Any,
    *,
    max_entries: int,
    require_2_25: bool,
    key: bytes | None = None,
    scope: str | None = None,
) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise ToolError("mapping document must be a JSON object")
    allowed = {"entries", "schema_version", "scope_sha256", "sensitive", "tool"}
    unknown = sorted(set(document) - allowed)
    if unknown:
        raise ToolError(f"mapping document has unsupported keys: {', '.join(unknown)}")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise ToolError("mapping entries must be a JSON array")
    bounded_int(
        len(entries),
        name="mapping entry count",
        minimum=0,
        maximum=max_entries,
    )
    if (key is None) != (scope is None):
        raise ToolError("deterministic verification requires both key and scope")
    if scope is not None:
        expected_scope_hash = sha256_text(scope)
        stored_scope_hash = document.get("scope_sha256")
        if stored_scope_hash and stored_scope_hash != expected_scope_hash:
            raise ToolError("mapping scope digest does not match the supplied scope")

    errors: Counter[str] = Counter()
    originals: dict[str, str] = {}
    replacements: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != {
            "original",
            "replacement",
        }:
            errors["entry_schema_invalid"] += 1
            continue
        original = entry.get("original")
        replacement = entry.get("replacement")
        if not valid_uid(original):
            errors["original_uid_invalid"] += 1
            continue
        if not valid_uid(replacement):
            errors["replacement_uid_invalid"] += 1
            continue
        if original == replacement:
            errors["unchanged_uid"] += 1
        if original == STANDARD_ROOT or original.startswith(STANDARD_ROOT + "."):
            errors["standard_uid_mapped"] += 1
        if require_2_25 and not replacement.startswith("2.25."):
            errors["replacement_not_2_25"] += 1
        previous = originals.get(original)
        if previous is not None and previous != replacement:
            errors["one_original_to_multiple_replacements"] += 1
        originals[original] = replacement
        previous_original = replacements.get(replacement)
        if previous_original is not None and previous_original != original:
            errors["replacement_collision"] += 1
        replacements[replacement] = original
        if key is not None and scope is not None:
            expected = derive_uid(original, key=key, scope=scope)
            if replacement != expected:
                errors["deterministic_mapping_mismatch"] += 1
    return {
        "deterministic_mapping_verified": key is not None,
        "duplicate_entries": len(entries) - len(originals),
        "entries": len(entries),
        "error_codes": counter_dict(errors),
        "errors": sum(errors.values()),
        "network_accessed": False,
        "ok": not errors,
        "original_uids_emitted": False,
        "replacement_uids_emitted": False,
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "unique_originals": len(originals),
        "unique_replacements": len(replacements),
        "warnings": [
            "UID maps contain identifiers and must be stored as sensitive data.",
            "Mapping consistency does not establish de-identification or referential completeness.",
            "Structural UIDs such as SOP Class and Transfer Syntax UIDs must not be remapped.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate UID syntax, one-to-one mapping, collisions, standard-UID "
            "protection, and optional keyed deterministic derivation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The mapping file is sensitive because it contains original identifiers. This
tool emits aggregate findings only and performs no network access.

Examples:
  python uid_mapping_validator.py uid-map.json
  python uid_mapping_validator.py uid-map.json --uid-key-file project.key \\
    --uid-scope study-export-v1
""",
    )
    parser.add_argument("mapping", help="Local sensitive UID mapping JSON")
    parser.add_argument("--root", default=".", help="Existing local I/O root")
    parser.add_argument("--uid-key-file", help="Optional local deterministic key")
    parser.add_argument("--uid-scope", help="Scope paired with --uid-key-file")
    parser.add_argument(
        "--allow-non-2-25",
        action="store_true",
        help="Allow valid replacement UIDs outside the 2.25 UUID-derived root",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=100_000,
        help="Maximum mapping entries (default: 100000)",
    )
    parser.add_argument("--output", "-o", help="Private aggregate JSON report")
    parser.add_argument(
        "--force", action="store_true", help="Overwrite an existing report only"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        max_entries = bounded_int(
            args.max_entries,
            name="max_entries",
            minimum=1,
            maximum=1_000_000,
        )
        mapping_path = checked_input(
            args.mapping,
            root=args.root,
            kind="file",
            max_bytes=MAX_JSON_BYTES,
        )
        key: bytes | None = None
        scope: str | None = None
        if args.uid_key_file or args.uid_scope:
            if not args.uid_key_file or not args.uid_scope:
                raise ToolError("--uid-key-file and --uid-scope must be used together")
            key_path = checked_input(
                args.uid_key_file,
                root=args.root,
                kind="file",
                max_bytes=4 * 1024,
            )
            key = _load_key(key_path)
            scope = require_text(args.uid_scope, name="uid_scope", maximum=128)
        report = validate_mapping(
            load_json(mapping_path),
            max_entries=max_entries,
            require_2_25=not args.allow_non_2_25,
            key=key,
            scope=scope,
        )
        if args.output:
            destination = checked_output(args.output, root=args.root, force=args.force)
            if paths_overlap(mapping_path, destination):
                raise ToolError("report must not overwrite the sensitive mapping")
            if args.uid_key_file and paths_overlap(key_path, destination):
                raise ToolError("report must not overwrite the UID key")
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
