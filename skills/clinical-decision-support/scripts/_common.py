#!/usr/bin/env python3
"""Shared bounded local-file utilities for research-only CDS helpers."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

MAX_INPUT_BYTES = 1_000_000
MAX_TEXT_LENGTH = 4_000
MAX_SOURCES = 200

PERSON_LEVEL_KEYS = {
    "address",
    "date_of_birth",
    "dob",
    "email",
    "full_name",
    "individual_record",
    "individual_records",
    "medical_record_number",
    "mrn",
    "note_text",
    "person_name",
    "patient",
    "patient_data",
    "patient_id",
    "patient_record",
    "patient_records",
    "phone",
    "raw_data",
    "raw_rows",
    "record_id",
    "social_security_number",
    "ssn",
}


class InputError(ValueError):
    """Raised for unsafe, malformed, or out-of-bounds input."""


@dataclass
class IssueLog:
    """Deterministic validation findings."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "pass" if self.ok else "fail",
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "disclaimer": (
                "Not for patient care or live clinical use. "
                "Structural checks only; not a clinical, privacy, regulatory, "
                "legal, or compliance determination."
            ),
        }


def _reject_nonlocal_path(raw: str) -> None:
    lowered = raw.strip().lower()
    if not lowered:
        raise InputError("Path must not be empty")
    if "\x00" in raw or "://" in lowered or lowered.startswith("\\\\"):
        raise InputError("Only local filesystem paths are allowed")


def local_input_path(raw: str, suffixes: Iterable[str] | None = None) -> Path:
    """Resolve a bounded, regular, non-symlink local input file."""

    _reject_nonlocal_path(raw)
    path = Path(raw).expanduser()
    if path.is_symlink():
        raise InputError("Symlink inputs are not allowed")
    resolved = path.resolve()
    if not resolved.is_file():
        raise InputError(f"Input is not a regular file: {path}")
    if suffixes and resolved.suffix.lower() not in {s.lower() for s in suffixes}:
        raise InputError(f"Unsupported input suffix: {resolved.suffix}")
    size = resolved.stat().st_size
    if size > MAX_INPUT_BYTES:
        raise InputError(f"Input exceeds {MAX_INPUT_BYTES} bytes")
    return resolved


def local_output_path(raw: str, suffixes: Iterable[str] | None = None) -> Path:
    """Resolve a local output whose parent already exists."""

    _reject_nonlocal_path(raw)
    path = Path(raw).expanduser()
    if path.is_symlink():
        raise InputError("Symlink outputs are not allowed")
    resolved = path.resolve()
    if not resolved.parent.is_dir():
        raise InputError("Output parent directory must already exist")
    if suffixes and resolved.suffix.lower() not in {s.lower() for s in suffixes}:
        raise InputError(f"Unsupported output suffix: {resolved.suffix}")
    return resolved


def load_json_object(raw_path: str) -> dict[str, Any]:
    """Load one bounded UTF-8 JSON object."""

    path = local_input_path(raw_path, {".json"})
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise InputError("Top-level JSON value must be an object")
        ensure_no_person_level_keys(value)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise InputError(f"Invalid UTF-8 JSON: {exc}") from exc
    return value


def ensure_no_person_level_keys(value: Any, location: str = "$") -> None:
    """Reject common person-level fields anywhere in a JSON document."""

    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if normalized in PERSON_LEVEL_KEYS:
                raise InputError(
                    f"Person-level or raw-data key is prohibited at {location}.{key}"
                )
            ensure_no_person_level_keys(nested, f"{location}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            ensure_no_person_level_keys(nested, f"{location}[{index}]")


def write_json(raw_path: str, payload: dict[str, Any]) -> None:
    path = local_output_path(raw_path, {".json"})
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def write_text(raw_path: str, text: str, suffixes: Iterable[str]) -> None:
    path = local_output_path(raw_path, suffixes)
    path.write_text(text, encoding="utf-8")


def require_nonempty_text(
    value: Any, field_name: str, *, max_length: int = MAX_TEXT_LENGTH
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{field_name} must be non-empty text")
    text = value.strip()
    if len(text) > max_length:
        raise InputError(f"{field_name} exceeds {max_length} characters")
    return text


def require_list(value: Any, field_name: str, *, maximum: int) -> list[Any]:
    if not isinstance(value, list):
        raise InputError(f"{field_name} must be a list")
    if len(value) > maximum:
        raise InputError(f"{field_name} exceeds {maximum} entries")
    return value


def finite_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{field_name} must be numeric")
    try:
        result = float(value)
    except OverflowError as exc:
        raise InputError(f"{field_name} must be representable as a finite number") from exc
    if not math.isfinite(result):
        raise InputError(f"{field_name} must be finite")
    return result


def nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InputError(f"{field_name} must be a non-negative integer")
    return value


def source_ids(document: dict[str, Any]) -> set[str]:
    sources = require_list(document.get("sources"), "sources", maximum=MAX_SOURCES)
    identifiers: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise InputError(f"sources[{index}] must be an object")
        identifier = require_nonempty_text(
            source.get("id"), f"sources[{index}].id", max_length=100
        )
        require_nonempty_text(
            source.get("citation"), f"sources[{index}].citation", max_length=1_000
        )
        if identifier in identifiers:
            raise InputError(f"Duplicate source id: {identifier}")
        identifiers.add(identifier)
    return identifiers


def validate_references(
    references: Any, known_sources: set[str], field_name: str
) -> list[str]:
    values = require_list(references, field_name, maximum=50)
    normalized: list[str] = []
    for index, value in enumerate(values):
        identifier = require_nonempty_text(
            value, f"{field_name}[{index}]", max_length=100
        )
        if identifier not in known_sources:
            raise InputError(f"{field_name} references unknown source id: {identifier}")
        normalized.append(identifier)
    if not normalized:
        raise InputError(f"{field_name} must cite at least one source")
    return normalized


def print_report(report: dict[str, Any]) -> None:
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
