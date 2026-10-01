#!/usr/bin/env python3
"""Bounded local-file and validation helpers for clinical-reports scripts."""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

MAX_JSON_BYTES = 1_000_000
MAX_CSV_BYTES = 5_000_000
MAX_CSV_ROWS = 10_000
MAX_NODES = 25_000
MAX_DEPTH = 24
MAX_TEXT_LENGTH = 2_000

ALLOWED_DATA_CLASSES = {"synthetic", "deidentified", "aggregate"}
IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class ValidationError(ValueError):
    """Raised for fail-closed input validation errors."""


def _reject_nonlocal(raw: str) -> None:
    if not raw or "\x00" in raw:
        raise ValidationError("path must be a non-empty local filesystem path")
    if "://" in raw or raw.startswith(("file:", "\\\\")):
        raise ValidationError("URLs, URI schemes, and network paths are not allowed")


def local_input_path(
    raw: str,
    *,
    suffixes: Iterable[str],
    max_bytes: int,
) -> Path:
    """Resolve a bounded, regular, non-symlink local input file."""
    _reject_nonlocal(raw)
    path = Path(raw).expanduser()
    if path.is_symlink():
        raise ValidationError("symbolic-link inputs are not allowed")
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValidationError(f"input file does not exist: {path}") from exc
    if not resolved.is_file():
        raise ValidationError("input must be a regular file")
    allowed = {suffix.lower() for suffix in suffixes}
    if resolved.suffix.lower() not in allowed:
        raise ValidationError(f"input suffix must be one of: {sorted(allowed)}")
    size = resolved.stat().st_size
    if size <= 0:
        raise ValidationError("input file is empty")
    if size > max_bytes:
        raise ValidationError(f"input exceeds {max_bytes} bytes")
    return resolved


def local_output_path(
    raw: str,
    *,
    suffixes: Iterable[str],
    overwrite: bool,
) -> Path:
    """Resolve a local output whose existing parent directory is trusted."""
    _reject_nonlocal(raw)
    path = Path(raw).expanduser()
    allowed = {suffix.lower() for suffix in suffixes}
    if path.suffix.lower() not in allowed:
        raise ValidationError(f"output suffix must be one of: {sorted(allowed)}")
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file():
            raise ValidationError("existing output must be a regular non-symlink file")
        if not overwrite:
            raise ValidationError("output exists; pass --overwrite to replace it")
    parent = path.parent
    if parent.is_symlink():
        raise ValidationError("symbolic-link output directories are not allowed")
    try:
        resolved_parent = parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValidationError("output parent directory must already exist") from exc
    if not resolved_parent.is_dir():
        raise ValidationError("output parent is not a directory")
    return resolved_parent / path.name


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _check_tree(value: Any, *, depth: int = 0, counter: list[int] | None = None) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_NODES:
        raise ValidationError(f"JSON exceeds {MAX_NODES} nodes")
    if depth > MAX_DEPTH:
        raise ValidationError(f"JSON exceeds maximum depth {MAX_DEPTH}")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or len(key) > 128:
                raise ValidationError("JSON object keys must be strings of at most 128 characters")
            _check_tree(child, depth=depth + 1, counter=counter)
    elif isinstance(value, list):
        for child in value:
            _check_tree(child, depth=depth + 1, counter=counter)
    elif isinstance(value, str):
        if len(value) > MAX_TEXT_LENGTH:
            raise ValidationError(
                f"JSON strings may not exceed {MAX_TEXT_LENGTH} characters"
            )
        if any(ord(char) < 32 and char not in "\t\n\r" for char in value):
            raise ValidationError("JSON strings contain disallowed control characters")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValidationError("non-finite numbers are not allowed")


def load_json_object(raw_path: str) -> tuple[Path, dict[str, Any]]:
    """Load a bounded JSON object with duplicate-key and depth checks."""
    path = local_input_path(
        raw_path,
        suffixes={".json"},
        max_bytes=MAX_JSON_BYTES,
    )
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_object_without_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValidationError(f"invalid JSON number: {token}")
            ),
        )
    except UnicodeDecodeError as exc:
        raise ValidationError("JSON input must be UTF-8") from exc
    except RecursionError as exc:
        raise ValidationError("JSON nesting exceeds the parser limit") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValidationError("top-level JSON value must be an object")
    _check_tree(value)
    return path, value


def write_json_report(
    report: dict[str, Any],
    raw_output: str | None,
    *,
    overwrite: bool,
) -> None:
    """Print JSON or write it to an explicitly bounded local path."""
    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if raw_output is None:
        print(rendered, end="")
        return
    output = local_output_path(
        raw_output,
        suffixes={".json"},
        overwrite=overwrite,
    )
    output.write_text(rendered, encoding="utf-8")


def require_data_class(value: Any) -> str:
    """Require an allowed, explicitly declared data class."""
    if not isinstance(value, str) or value not in ALLOWED_DATA_CLASSES:
        raise ValidationError(
            f"data classification must be one of: {sorted(ALLOWED_DATA_CLASSES)}"
        )
    return str(value)


def require_exact_keys(
    value: Any,
    expected: Iterable[str],
    field: str,
) -> dict[str, Any]:
    """Reject missing and unknown fields in a structured object."""
    if not isinstance(value, dict):
        raise ValidationError(f"{field} must be an object")
    expected_set = set(expected)
    missing = sorted(expected_set - set(value))
    extra = sorted(set(value) - expected_set)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"unknown={extra}")
        raise ValidationError(f"{field} fields are invalid ({'; '.join(details)})")
    return value


def require_identifier(value: Any, field: str) -> str:
    """Require a bounded machine identifier."""
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise ValidationError(f"{field} must match {IDENTIFIER_RE.pattern}")
    return value


def require_string(value: Any, field: str, *, max_length: int = 256) -> str:
    """Require a non-empty bounded string."""
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        raise ValidationError(f"{field} must contain 1-{max_length} characters")
    return normalized


def require_bool(value: Any, field: str) -> bool:
    """Require an actual JSON boolean."""
    if not isinstance(value, bool):
        raise ValidationError(f"{field} must be a boolean")
    return value


def require_nonnegative_int(value: Any, field: str) -> int:
    """Require an integer count without accepting booleans."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{field} must be a non-negative integer")
    return value


def parse_iso_date(value: Any, field: str) -> date:
    """Parse an ISO calendar date without inferring missing precision."""
    text = require_string(value, field, max_length=10)
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        raise ValidationError(f"{field} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{field} must be YYYY-MM-DD") from exc


def parse_iso_datetime(value: Any, field: str) -> datetime:
    """Parse an ISO datetime and require an explicit timezone."""
    text = require_string(value, field, max_length=40)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO 8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{field} must include a timezone")
    return parsed


def error_report(tool: str, exc: Exception) -> dict[str, Any]:
    """Return a non-sensitive machine-readable error."""
    return {
        "tool": tool,
        "status": "BLOCKED_INVALID_INPUT",
        "errors": [str(exc)],
        "review_required": True,
        "authorizes_clinical_use_or_submission": False,
    }
