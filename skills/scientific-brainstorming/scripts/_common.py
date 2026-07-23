"""Shared standard-library safety helpers for brainstorming CLIs."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
import tempfile
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 10_000
MAX_SHORT_TEXT_CHARS = 500
MAX_ITEMS = 5_000
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class CliError(ValueError):
    """A deterministic, user-facing CLI validation error."""


def bounded_float(minimum: float, maximum: float):
    """Return an argparse converter for a finite bounded float."""

    def convert(raw: str) -> float:
        try:
            value = float(raw)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"expected a number, got {raw!r}") from exc
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise argparse.ArgumentTypeError(
                f"expected a finite number from {minimum} through {maximum}"
            )
        return value

    return convert


def require_identifier(value: Any, label: str) -> str:
    """Validate a stable, bounded identifier."""

    if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
        raise CliError(
            f"{label} must match {IDENTIFIER_PATTERN.pattern} and be at most "
            "64 characters"
        )
    return value


def require_text(
    value: Any,
    label: str,
    *,
    maximum: int = MAX_TEXT_CHARS,
    allow_empty: bool = False,
) -> str:
    """Validate and normalize a bounded text field."""

    if not isinstance(value, str):
        raise CliError(f"{label} must be a string")
    normalized = value.strip()
    if not normalized and not allow_empty:
        raise CliError(f"{label} must not be empty")
    if len(normalized) > maximum:
        raise CliError(f"{label} is {len(normalized)} characters; limit is {maximum}")
    return normalized


def bounded_strings(
    values: Iterable[str],
    label: str,
    *,
    maximum_items: int = 100,
    maximum_length: int = MAX_SHORT_TEXT_CHARS,
) -> list[str]:
    """Validate a bounded sequence of strings."""

    result = list(values)
    if len(result) > maximum_items:
        raise CliError(f"{label} has {len(result)} items; limit is {maximum_items}")
    return [
        require_text(
            value,
            f"{label}[{index}]",
            maximum=maximum_length,
        )
        for index, value in enumerate(result)
    ]


def require_iso_date(value: str, label: str = "date") -> str:
    """Validate an ISO calendar date without inventing a current date."""

    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise CliError(f"{label} must be an ISO date (YYYY-MM-DD)") from exc
    return parsed.isoformat()


def finite_number(value: Any, label: str) -> float:
    """Convert a JSON/CSV value to a finite float, rejecting booleans."""

    if isinstance(value, bool):
        raise CliError(f"{label} must be numeric, not boolean")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise CliError(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise CliError(f"{label} must be finite")
    return result


def read_bounded_text(
    raw_path: str,
    *,
    label: str,
    suffixes: set[str],
    encoding: str = "utf-8",
) -> tuple[Path, str]:
    """Read a bounded regular file without following a final symlink."""

    path = Path(raw_path).expanduser()
    if path.name in {"", ".", ".."}:
        raise CliError(f"{label} must name a file")
    if path.suffix.lower() not in suffixes:
        expected = ", ".join(sorted(suffixes))
        raise CliError(f"{label} must use one of these suffixes: {expected}")
    if path.is_symlink():
        raise CliError(f"refusing to read {label} through a symlink")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CliError(f"cannot open {label} as a regular file: {path}") from exc

    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CliError(f"{label} is not a regular file: {path}")
        if metadata.st_size > MAX_INPUT_BYTES:
            raise CliError(
                f"{label} is {metadata.st_size} bytes; limit is {MAX_INPUT_BYTES}"
            )
        with os.fdopen(descriptor, "r", encoding=encoding, newline="") as handle:
            descriptor = -1
            return path, handle.read()
    except UnicodeDecodeError as exc:
        raise CliError(f"{label} is not valid {encoding} text") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def read_json(raw_path: str, *, label: str = "JSON input") -> tuple[Path, Any]:
    """Read strict, bounded JSON and reject non-standard constants."""

    path, text = read_bounded_text(
        raw_path,
        label=label,
        suffixes={".json"},
    )

    def reject_constant(value: str) -> None:
        raise CliError(f"non-standard JSON constant is not allowed: {value}")

    try:
        return path, json.loads(text, parse_constant=reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise CliError(f"invalid JSON in {path}: {exc}") from exc


def _safe_output_target(raw_path: str, suffix: str) -> Path:
    """Resolve a user-selected output in an existing directory."""

    requested = Path(raw_path).expanduser()
    if requested.name in {"", ".", ".."}:
        raise CliError("output must name a file")
    if requested.suffix.lower() != suffix:
        raise CliError(f"output filename must end in {suffix}")
    if requested.is_symlink():
        raise CliError("refusing to write through an output symlink")
    try:
        parent = requested.parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise CliError("output parent directory does not exist") from exc
    if not parent.is_dir():
        raise CliError("output parent is not a directory")
    target = parent / requested.name
    if target.is_symlink():
        raise CliError("refusing to replace an output symlink")
    if target.exists() and not target.is_file():
        raise CliError("output exists and is not a regular file")
    return target


def write_json(
    raw_path: str,
    payload: Any,
    *,
    force: bool = False,
) -> Path:
    """Write deterministic JSON with private permissions and safe overwrite."""

    target = _safe_output_target(raw_path, ".json")
    try:
        text = (
            json.dumps(
                payload,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise CliError(f"payload cannot be serialized as strict JSON: {exc}") from exc

    if not force:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = -1
        created = False
        try:
            descriptor = os.open(target, flags, 0o600)
            created = True
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                descriptor = -1
                handle.write(text)
        except FileExistsError as exc:
            raise CliError(
                f"output already exists: {target}; pass --force to replace it"
            ) from exc
        except OSError as exc:
            if created:
                target.unlink(missing_ok=True)
            raise CliError(f"could not write output: {target}") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        return target

    if target.exists() and not target.is_file():
        raise CliError("output exists and is not a regular file")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(text)
        if target.is_symlink():
            raise CliError("refusing to replace an output symlink")
        os.replace(temporary, target)
    except OSError as exc:
        raise CliError(f"could not replace output: {target}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return target


def emit_json(
    payload: Any,
    output: str | None,
    *,
    force: bool = False,
) -> Path | None:
    """Print strict JSON or write it to a safe output path."""

    if output is None:
        print(
            json.dumps(
                payload,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return None
    return write_json(output, payload, force=force)


def rounded(value: float) -> float:
    """Return stable display precision without changing the documented formula."""

    return round(value, 6)
