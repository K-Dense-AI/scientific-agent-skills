#!/usr/bin/env python3
"""Shared, dependency-free validation helpers for local market-research CLIs."""

from __future__ import annotations

import csv
import json
import math
import os
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Iterable

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
MAX_CELL_CHARS = 20_000
MAX_IDENTIFIER_CHARS = 96

IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{0,95}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class ValidationError(ValueError):
    """A deterministic, user-correctable input validation error."""


def safe_input_path(raw_path: str | Path, suffixes: Iterable[str]) -> Path:
    """Resolve a bounded regular local file and reject symlink inputs."""
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
        raise ValidationError(f"expected one of [{choices}], got: {resolved.suffix}")
    size = resolved.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValidationError(
            f"input exceeds {MAX_FILE_BYTES} bytes: {resolved} ({size} bytes)"
        )
    return resolved


def safe_output_path(
    raw_path: str | Path, suffix: str, *, force: bool = False
) -> Path:
    """Resolve an output in an existing directory without implicit overwrites."""
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
    """Read one bounded UTF-8 JSON document."""
    path = safe_input_path(raw_path, {".json"})
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except UnicodeDecodeError as exc:
        raise ValidationError(f"JSON must be UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def read_csv_records(
    raw_path: str | Path,
    *,
    required_fields: Iterable[str],
    max_rows: int = MAX_ROWS,
) -> list[dict[str, str]]:
    """Read strict UTF-8 CSV records with unique headers and bounded cells."""
    path = safe_input_path(raw_path, {".csv"})
    required = tuple(required_fields)
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames
            if not headers:
                raise ValidationError(f"CSV has no header: {path}")
            normalized = [header.strip() for header in headers]
            if any(not header for header in normalized):
                raise ValidationError("CSV headers must not be blank")
            if len(normalized) != len(set(normalized)):
                raise ValidationError("CSV headers must be unique")
            missing = sorted(set(required) - set(normalized))
            if missing:
                raise ValidationError(
                    f"CSV is missing required columns: {', '.join(missing)}"
                )
            reader.fieldnames = normalized
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


def require_list(
    value: Any,
    context: str,
    *,
    minimum: int = 0,
    maximum: int = MAX_ROWS,
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
    maximum: int = MAX_CELL_CHARS,
) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{context} must be a string")
    text = value.strip()
    if not allow_empty and not text:
        raise ValidationError(f"{context} must not be empty")
    if len(text) > maximum:
        raise ValidationError(f"{context} exceeds {maximum} characters")
    if "\x00" in text:
        raise ValidationError(f"{context} contains a NUL byte")
    return text


def require_identifier(value: Any, context: str) -> str:
    identifier = require_text(
        value, context, maximum=MAX_IDENTIFIER_CHARS, allow_empty=False
    )
    if not IDENTIFIER_RE.fullmatch(identifier):
        raise ValidationError(
            f"{context} must match {IDENTIFIER_RE.pattern}: {identifier!r}"
        )
    return identifier


def require_unique_identifiers(values: Iterable[str], context: str) -> None:
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


def parse_iso_date(value: Any, context: str) -> str:
    text = require_text(value, context, maximum=10)
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        raise ValidationError(f"{context} must be YYYY-MM-DD: {text!r}")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{context} must be YYYY-MM-DD: {text!r}") from exc
    return text


def parse_year(value: Any, context: str) -> int:
    if type(value) is int:
        parsed = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]{4}", value.strip()):
        parsed = int(value.strip())
    else:
        raise ValidationError(f"{context} must be an integer year")
    if not 1800 <= parsed <= 2200:
        raise ValidationError(f"{context} must be between 1800 and 2200")
    return parsed


def parse_number(
    value: Any,
    context: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool):
        raise ValidationError(f"{context} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{context} must be numeric") from exc
    if not math.isfinite(number):
        raise ValidationError(f"{context} must be finite")
    if not minimum <= number <= maximum:
        raise ValidationError(
            f"{context} must be between {minimum} and {maximum}: {number}"
        )
    return number


def parse_fraction(value: Any, context: str) -> float:
    return parse_number(value, context, minimum=0.0, maximum=1.0)


def parse_currency(value: Any, context: str, *, allow_empty: bool = False) -> str:
    text = require_text(value, context, allow_empty=allow_empty, maximum=3).upper()
    if not text and allow_empty:
        return ""
    if not CURRENCY_RE.fullmatch(text):
        raise ValidationError(f"{context} must be a three-letter currency code")
    return text


def split_ids(value: Any, context: str, *, allow_empty: bool = False) -> list[str]:
    text = require_text(value, context, allow_empty=allow_empty)
    if not text:
        return []
    identifiers = [part.strip() for part in text.split(";")]
    if any(not part for part in identifiers):
        raise ValidationError(f"{context} contains an empty semicolon-delimited ID")
    parsed = [require_identifier(part, context) for part in identifiers]
    require_unique_identifiers(parsed, context)
    return parsed


def write_json_report(
    data: Any, output: str | Path | None, *, force: bool = False
) -> None:
    """Print JSON or atomically write it to an explicitly selected local file."""
    serialized = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output is None:
        print(serialized, end="")
        return
    destination = safe_output_path(output, ".json", force=force)
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
            handle.write(serialized)
            temporary_name = handle.name
        os.replace(temporary_name, destination)
    finally:
        if temporary_name and Path(temporary_name).exists():
            Path(temporary_name).unlink()


def error_exit(exc: ValidationError) -> int:
    print(f"ERROR: {exc}", file=os.sys.stderr)
    return 2
