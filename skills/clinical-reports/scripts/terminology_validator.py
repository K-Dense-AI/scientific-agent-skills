#!/usr/bin/env python3
"""Check terminology-manifest schema and optional caller-supplied local dictionary."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    ValidationError,
    error_report,
    load_json_object,
    parse_iso_date,
    require_bool,
    require_data_class,
    require_exact_keys,
    require_identifier,
    require_string,
    write_json_report,
)

TOOL = "terminology_validator"
CODE_PATTERNS = {
    "MedDRA": re.compile(r"^\d{8}$"),
    "LOINC": re.compile(r"^\d{1,7}-\d$"),
    "SNOMED_CT": re.compile(r"^[1-9]\d{5,17}$"),
    "ICD_10_CM": re.compile(r"^[A-Z][0-9A-Z]{2}(?:\.[0-9A-Z]{1,4})?$"),
    "UCUM": re.compile(r"^[A-Za-z0-9%.\[\]{}()/*^+'_-]{1,80}$"),
}
CODING_STATUSES = {"verified_by_qualified_reviewer", "unverified"}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "artifact_kind",
    "manifest_status",
    "safety_notice",
    "data_classification",
    "authorized_purpose",
    "authorization_verified",
    "provenance_manifest",
    "entries",
}
ENTRY_FIELDS = {
    "system",
    "system_uri",
    "code",
    "display",
    "version",
    "language",
    "source_fact_id",
    "coding_status",
    "verified_by_role",
    "verified_at",
}


def _validate_entry(entry: Any, index: int) -> tuple[str, str, str, str, list[str]]:
    entry = require_exact_keys(entry, ENTRY_FIELDS, f"entries[{index}]")
    system = require_string(entry.get("system"), f"entries[{index}].system", max_length=32)
    if system not in CODE_PATTERNS:
        raise ValidationError(
            f"entries[{index}].system must be one of {sorted(CODE_PATTERNS)}"
        )
    require_string(
        entry.get("system_uri"),
        f"entries[{index}].system_uri",
        max_length=200,
    )
    code = require_string(entry.get("code"), f"entries[{index}].code", max_length=80)
    if not CODE_PATTERNS[system].fullmatch(code):
        raise ValidationError(f"entries[{index}].code fails {system} syntax")
    display = require_string(
        entry.get("display"),
        f"entries[{index}].display",
        max_length=500,
    )
    version = require_string(
        entry.get("version"),
        f"entries[{index}].version",
        max_length=80,
    )
    require_string(entry.get("language"), f"entries[{index}].language", max_length=32)
    require_identifier(
        entry.get("source_fact_id"),
        f"entries[{index}].source_fact_id",
    )
    status = entry.get("coding_status")
    if not isinstance(status, str) or status not in CODING_STATUSES:
        raise ValidationError(f"entries[{index}].coding_status is invalid")
    warnings: list[str] = []
    if status == "verified_by_qualified_reviewer":
        require_string(
            entry.get("verified_by_role"),
            f"entries[{index}].verified_by_role",
            max_length=100,
        )
        parse_iso_date(entry.get("verified_at"), f"entries[{index}].verified_at")
    else:
        warnings.append(f"entries[{index}] remains unverified")
    if system == "MedDRA" and not re.fullmatch(r"\d{1,2}\.\d", version):
        warnings.append(f"entries[{index}] MedDRA version has an unusual format")
    return system, version, code, display, warnings


def _load_dictionary(raw_path: str) -> dict[tuple[str, str, str], str]:
    _, data = load_json_object(raw_path)
    require_exact_keys(
        data,
        {"schema_version", "artifact_kind", "entries"},
        "dictionary",
    )
    if data.get("schema_version") != "2.0":
        raise ValidationError("dictionary schema_version must be 2.0")
    if data.get("artifact_kind") != "terminology_dictionary":
        raise ValidationError("dictionary artifact_kind must be terminology_dictionary")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValidationError("dictionary entries must be a non-empty array")
    if len(entries) > 20_000:
        raise ValidationError("dictionary may contain at most 20,000 entries")
    dictionary: dict[tuple[str, str, str], str] = {}
    for index, entry in enumerate(entries):
        entry = require_exact_keys(
            entry,
            {"system", "version", "code", "display"},
            f"dictionary entries[{index}]",
        )
        system = require_string(
            entry.get("system"),
            f"dictionary entries[{index}].system",
            max_length=32,
        )
        version = require_string(
            entry.get("version"),
            f"dictionary entries[{index}].version",
            max_length=80,
        )
        code = require_string(
            entry.get("code"),
            f"dictionary entries[{index}].code",
            max_length=80,
        )
        display = require_string(
            entry.get("display"),
            f"dictionary entries[{index}].display",
            max_length=500,
        )
        key = (system, version, code)
        if key in dictionary and dictionary[key] != display:
            raise ValidationError(f"dictionary contains conflicting duplicate at index {index}")
        dictionary[key] = display
    return dictionary


def validate_terminology_manifest(
    data: dict[str, Any],
    dictionary: dict[tuple[str, str, str], str] | None = None,
) -> dict[str, Any]:
    """Validate schema and optional exact tuple matches."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        require_exact_keys(data, TOP_LEVEL_FIELDS, "manifest")
        if data.get("schema_version") != "2.0":
            raise ValidationError("schema_version must be 2.0")
        if data.get("manifest_status") != "BLOCKED_INCOMPLETE":
            raise ValidationError("manifest_status must remain BLOCKED_INCOMPLETE")
        require_string(data.get("safety_notice"), "safety_notice", max_length=1000)
        require_string(data.get("authorized_purpose"), "authorized_purpose")
        if not require_bool(data.get("authorization_verified"), "authorization_verified"):
            raise ValidationError("authorization_verified must be true")
        require_string(data.get("provenance_manifest"), "provenance_manifest")
    except ValidationError as exc:
        errors.append(str(exc))
    if data.get("artifact_kind") != "terminology_manifest":
        errors.append("artifact_kind must be terminology_manifest")
    try:
        require_data_class(data.get("data_classification"))
    except ValidationError as exc:
        errors.append(str(exc))

    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("entries must be a non-empty array")
        entries = []
    if len(entries) > 5_000:
        errors.append("entries may contain at most 5,000 items")

    seen: set[tuple[str, str, str]] = set()
    verified_count = 0
    dictionary_match_count = 0
    for index, entry in enumerate(entries[:5_000]):
        try:
            system, version, code, display, entry_warnings = _validate_entry(
                entry,
                index,
            )
            warnings.extend(entry_warnings)
            key = (system, version, code)
            if key in seen:
                errors.append(f"entries[{index}] duplicates a prior system/version/code")
            seen.add(key)
            if entry.get("coding_status") == "verified_by_qualified_reviewer":
                verified_count += 1
            if dictionary is not None:
                expected_display = dictionary.get(key)
                if expected_display is None:
                    errors.append(f"entries[{index}] is absent from the supplied dictionary")
                elif expected_display != display:
                    errors.append(
                        f"entries[{index}] display does not match the supplied dictionary"
                    )
                else:
                    dictionary_match_count += 1
        except ValidationError as exc:
            errors.append(str(exc))

    if dictionary is None:
        warnings.append(
            "No local dictionary supplied; code existence, currency, and display were not checked."
        )
        success_status = "SCHEMA_VALID_SYNTAX_ONLY_REVIEW_REQUIRED"
    else:
        success_status = "SCHEMA_AND_LOCAL_DICTIONARY_MATCH_REVIEW_REQUIRED"

    return {
        "tool": TOOL,
        "status": "BLOCKED" if errors else success_status,
        "entry_count": len(entries),
        "qualified_reviewer_verified_count": verified_count,
        "local_dictionary_match_count": dictionary_match_count,
        "errors": errors,
        "warnings": warnings,
        "limitations": [
            "Syntax or local-dictionary matching does not establish clinical correctness.",
            "Caller is responsible for dictionary authority, version, license, and completeness.",
        ],
        "review_required": True,
        "authorizes_clinical_use_or_submission": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check a bounded terminology JSON manifest. Optional dictionary comparison "
            "uses a caller-supplied local JSON file and never calls a network service."
        )
    )
    parser.add_argument("input_file", help="Local terminology manifest (.json)")
    parser.add_argument("--dictionary", help="Optional authorized local dictionary (.json)")
    parser.add_argument("-o", "--output", help="Optional local JSON report")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _, data = load_json_object(args.input_file)
        dictionary = _load_dictionary(args.dictionary) if args.dictionary else None
        report = validate_terminology_manifest(data, dictionary)
    except (OSError, ValidationError) as exc:
        report = error_report(TOOL, exc)
    try:
        write_json_report(report, args.output, overwrite=args.overwrite)
    except (OSError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0 if report["status"].startswith("SCHEMA_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
