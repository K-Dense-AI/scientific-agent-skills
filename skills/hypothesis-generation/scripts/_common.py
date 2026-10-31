#!/usr/bin/env python3
"""Shared, dependency-free safety helpers for local hypothesis CLIs."""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Iterable

MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1_000
MAX_CELL_CHARS = 8_000
MAX_TEXT_CHARS = 20_000
MAX_LIST_ITEMS = 500
MAX_JSON_DEPTH = 64

IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{0,95}$")
URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
HTTPS_URL_RE = re.compile(r"^https://[^\s]+$", re.IGNORECASE)
PARTIAL_DATE_RE = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")
ISO_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class ValidationError(ValueError):
    """A deterministic, user-correctable validation failure."""


def _duplicate_safe_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"JSON object contains duplicate key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValidationError(f"JSON contains a nonstandard numeric constant: {value}")


def _reject_url_like_path(raw_path: str | Path, context: str) -> None:
    if URL_SCHEME_RE.match(str(raw_path).strip()):
        raise ValidationError(f"{context} must be a local file path")


def safe_input_path(raw_path: str | Path, suffixes: Iterable[str]) -> Path:
    """Resolve a bounded regular local file and reject symlink inputs."""
    _reject_url_like_path(raw_path, "input")
    path = Path(raw_path).expanduser()
    if path.is_symlink():
        raise ValidationError(f"symlink inputs are not allowed: {path}")
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValidationError(f"input file does not exist: {path}") from exc
    if not resolved.is_file():
        raise ValidationError(f"input path is not a regular file: {resolved}")
    allowed = {suffix.lower() for suffix in suffixes}
    if resolved.suffix.lower() not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValidationError(f"expected one of [{choices}]: {resolved}")
    size = resolved.stat().st_size
    if size > MAX_INPUT_BYTES:
        raise ValidationError(
            f"input exceeds {MAX_INPUT_BYTES} bytes: {resolved} ({size} bytes)"
        )
    return resolved


def safe_output_path(
    raw_path: str | Path, suffix: str, *, force: bool = False
) -> Path:
    """Resolve an output in an existing directory without implicit overwrite."""
    _reject_url_like_path(raw_path, "output")
    path = Path(raw_path).expanduser()
    if path.suffix.lower() != suffix.lower():
        raise ValidationError(f"output must use {suffix}: {path}")
    try:
        parent = path.parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValidationError(f"output parent does not exist: {path.parent}") from exc
    if not parent.is_dir():
        raise ValidationError(f"output parent is not a directory: {parent}")
    resolved = parent / path.name
    if resolved.is_symlink():
        raise ValidationError(f"symlink outputs are not allowed: {resolved}")
    if resolved.exists():
        if not resolved.is_file():
            raise ValidationError(f"output is not a regular file: {resolved}")
        if not force:
            raise ValidationError(
                f"output already exists; pass --force to replace it: {resolved}"
            )
    return resolved


def read_json(raw_path: str | Path) -> Any:
    """Read strict UTF-8 JSON with duplicate-key detection."""
    path = safe_input_path(raw_path, {".json"})
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"JSON must be UTF-8: {path}") from exc
    if "\x00" in text:
        raise ValidationError(f"JSON contains a NUL byte: {path}")
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_duplicate_safe_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except RecursionError as exc:
        raise ValidationError("JSON nesting exceeds the parser limit") from exc
    # The decoder's recursion threshold varies between Python releases.
    # Enforce our own bound without a second recursive walk.
    pending = [(payload, 1)]
    while pending:
        value, depth = pending.pop()
        if isinstance(value, (dict, list)):
            if depth > MAX_JSON_DEPTH:
                raise ValidationError(f"JSON nesting exceeds {MAX_JSON_DEPTH} levels")
            children = value.values() if isinstance(value, dict) else value
            pending.extend((child, depth + 1) for child in children)
    return payload


def read_markdown(raw_path: str | Path) -> str:
    """Read one bounded UTF-8 Markdown file."""
    path = safe_input_path(raw_path, {".md", ".markdown"})
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"Markdown must be UTF-8: {path}") from exc
    if "\x00" in text:
        raise ValidationError(f"Markdown contains a NUL byte: {path}")
    if any(len(line) > MAX_CELL_CHARS for line in text.splitlines()):
        raise ValidationError(
            f"Markdown contains a line longer than {MAX_CELL_CHARS} characters"
        )
    return text


def read_csv_records(
    raw_path: str | Path,
    *,
    fields: Iterable[str],
    max_rows: int = MAX_ROWS,
) -> list[dict[str, str]]:
    """Read strict UTF-8 CSV with an exact ordered header and bounded cells."""
    path = safe_input_path(raw_path, {".csv"})
    expected = tuple(fields)
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames
            if not headers:
                raise ValidationError(f"CSV has no header: {path}")
            normalized = tuple(header.strip() for header in headers)
            if any(not header for header in normalized):
                raise ValidationError("CSV headers must not be blank")
            if len(normalized) != len(set(normalized)):
                raise ValidationError("CSV headers must be unique")
            if normalized != expected:
                raise ValidationError(
                    "CSV header must exactly match: " + ",".join(expected)
                )
            reader.fieldnames = list(normalized)
            records: list[dict[str, str]] = []
            for line_number, row in enumerate(reader, start=2):
                if line_number - 1 > max_rows:
                    raise ValidationError(f"CSV exceeds {max_rows} data rows")
                if None in row:
                    raise ValidationError(
                        f"row {line_number} has more cells than the header"
                    )
                cleaned: dict[str, str] = {}
                for key, value in row.items():
                    cell = "" if value is None else value.strip()
                    if "\x00" in cell:
                        raise ValidationError(
                            f"row {line_number}, column {key} contains a NUL byte"
                        )
                    if len(cell) > MAX_CELL_CHARS:
                        raise ValidationError(
                            f"row {line_number}, column {key} exceeds "
                            f"{MAX_CELL_CHARS} characters"
                        )
                    cleaned[key] = cell
                if any(cleaned.values()):
                    records.append(cleaned)
    except UnicodeDecodeError as exc:
        raise ValidationError(f"CSV must be UTF-8: {path}") from exc
    except csv.Error as exc:
        raise ValidationError(f"invalid CSV: {exc}") from exc
    if not records:
        raise ValidationError("CSV must contain at least one data row")
    return records


def require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{context} must be a JSON object")
    return value


def require_exact_keys(
    value: dict[str, Any],
    *,
    required: Iterable[str],
    optional: Iterable[str] = (),
    context: str,
) -> None:
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        raise ValidationError(f"{context} is missing fields: {', '.join(missing)}")
    if unknown:
        raise ValidationError(f"{context} has unknown fields: {', '.join(unknown)}")


def require_list(
    value: Any,
    context: str,
    *,
    minimum: int = 0,
    maximum: int = MAX_LIST_ITEMS,
) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{context} must be a JSON array")
    if not minimum <= len(value) <= maximum:
        raise ValidationError(
            f"{context} must contain between {minimum} and {maximum} items"
        )
    return value


def require_text(
    value: Any,
    context: str,
    *,
    allow_empty: bool = False,
    minimum: int = 1,
    maximum: int = MAX_TEXT_CHARS,
) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{context} must be a string")
    text = value.strip()
    if not allow_empty and not text:
        raise ValidationError(f"{context} must not be empty")
    if text and len(text) < minimum:
        raise ValidationError(f"{context} must contain at least {minimum} characters")
    if len(text) > maximum:
        raise ValidationError(f"{context} exceeds {maximum} characters")
    if "\x00" in text:
        raise ValidationError(f"{context} contains a NUL byte")
    return text


def require_bool(value: Any, context: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{context} must be true or false")
    return value


def require_enum(value: Any, choices: Iterable[str], context: str) -> str:
    text = require_text(value, context, maximum=96)
    allowed = set(choices)
    if text not in allowed:
        raise ValidationError(
            f"{context} must be one of: {', '.join(sorted(allowed))}"
        )
    return text


def require_identifier(value: Any, context: str) -> str:
    identifier = require_text(value, context, maximum=96)
    if not IDENTIFIER_RE.fullmatch(identifier):
        raise ValidationError(f"{context} has an invalid identifier format")
    return identifier


def require_unique(values: Iterable[str], context: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise ValidationError(
            f"{context} contains duplicate IDs: {', '.join(sorted(duplicates))}"
        )


def require_text_list(
    value: Any,
    context: str,
    *,
    minimum: int = 0,
    maximum: int = 100,
    item_maximum: int = 1_000,
) -> list[str]:
    items = require_list(value, context, minimum=minimum, maximum=maximum)
    return [
        require_text(item, f"{context}[{index}]", maximum=item_maximum)
        for index, item in enumerate(items)
    ]


def require_identifier_list(
    value: Any,
    context: str,
    *,
    minimum: int = 0,
    maximum: int = 100,
) -> list[str]:
    items = require_list(value, context, minimum=minimum, maximum=maximum)
    parsed = [
        require_identifier(item, f"{context}[{index}]")
        for index, item in enumerate(items)
    ]
    require_unique(parsed, context)
    return parsed


def split_identifiers(
    value: Any, context: str, *, allow_empty: bool = False
) -> list[str]:
    text = require_text(value, context, allow_empty=allow_empty, maximum=MAX_CELL_CHARS)
    if not text:
        return []
    parts = [part.strip() for part in text.split(";")]
    if any(not part for part in parts):
        raise ValidationError(f"{context} contains an empty identifier")
    parsed = [require_identifier(part, context) for part in parts]
    require_unique(parsed, context)
    return parsed


def require_iso_date(value: Any, context: str) -> str:
    text = require_text(value, context, maximum=10)
    if not ISO_DATE_RE.fullmatch(text):
        raise ValidationError(f"{context} must be an ISO date (YYYY-MM-DD)")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{context} must be an ISO date (YYYY-MM-DD)") from exc
    return text


def require_partial_date(value: Any, context: str) -> str:
    text = require_text(value, context, maximum=10)
    if not PARTIAL_DATE_RE.fullmatch(text):
        raise ValidationError(f"{context} must be YYYY, YYYY-MM, or YYYY-MM-DD")
    try:
        if len(text) == 4:
            date(int(text), 1, 1)
        elif len(text) == 7:
            date.fromisoformat(f"{text}-01")
        else:
            date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{context} contains an invalid date") from exc
    return text


def require_https_url(value: Any, context: str) -> str:
    text = require_text(value, context, maximum=2_000)
    if not HTTPS_URL_RE.fullmatch(text):
        raise ValidationError(f"{context} must be an https URL")
    return text


def atomic_write_text(
    destination: Path, text: str, *, mode: int = 0o600
) -> Path:
    """Atomically write private local text to a validated destination."""
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            temporary_name = handle.name
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, destination)
        os.chmod(destination, mode)
    finally:
        if temporary_name and Path(temporary_name).exists():
            Path(temporary_name).unlink()
    return destination


def write_json_report(
    data: Any, output: str | Path | None, *, force: bool = False
) -> None:
    """Print JSON or atomically write it to an explicitly selected local file."""
    serialized = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output is None:
        print(serialized, end="")
        return
    destination = safe_output_path(output, ".json", force=force)
    atomic_write_text(destination, serialized)


def write_markdown(
    text: str, output: str | Path, *, force: bool = False
) -> Path:
    destination = safe_output_path(output, ".md", force=force)
    return atomic_write_text(destination, text)


def issue(code: str, field: str) -> dict[str, str]:
    """Create a content-free finding safe for reports."""
    return {"code": code, "field": field}


def error_exit(exc: ValidationError) -> int:
    print(f"ERROR: {exc}", file=sys.stderr)
    return 2
