#!/usr/bin/env python3
"""Shared, dependency-free safety and JSON helpers."""

from __future__ import annotations

import argparse
import json
import math
import os
import stat
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.1"
MAX_SNAPSHOT_BYTES = 1_048_576
MAX_WORKERS = 1_024
MAX_TASKS = 1_000_000_000
MAX_BYTES = 1 << 63


class ResourceToolError(ValueError):
    """A concise, user-safe CLI error."""


def json_text(value: Any) -> str:
    """Serialize deterministic, standards-compliant JSON."""
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    except (RecursionError, TypeError, ValueError) as exc:
        raise ResourceToolError("result is not valid JSON data") from exc


def _safe_output_path(raw: str) -> Path:
    """Restrict writes to one explicit JSON filename in the current directory."""
    if not raw or len(raw) > 255:
        raise ResourceToolError("output must be a short JSON filename")
    candidate = Path(raw)
    if candidate.is_absolute() or candidate.drive or len(candidate.parts) != 1:
        raise ResourceToolError(
            "output must be a filename in the current directory, not a path"
        )
    if candidate.name in {".", ".."} or candidate.suffix.lower() != ".json":
        raise ResourceToolError("output filename must end in .json")
    return Path.cwd() / candidate.name


def emit_json(value: Any, output: str | None = None, *, force: bool = False) -> None:
    """Write JSON to stdout or an explicit private local file."""
    payload = json_text(value)
    if output is None:
        sys.stdout.write(payload)
        return

    destination = _safe_output_path(output)
    try:
        if destination.is_symlink():
            raise ResourceToolError("refusing to write through a symbolic link")
        flags = os.O_WRONLY | os.O_CREAT
        if not force:
            flags |= os.O_EXCL
        flags |= getattr(os, "O_NONBLOCK", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(destination, flags, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ResourceToolError("output must be a regular file without hard links")
            if force:
                os.ftruncate(descriptor, 0)
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = -1
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except FileExistsError as exc:
        raise ResourceToolError(
            f"{destination.name} already exists; use --force to replace it"
        ) from exc
    except OSError as exc:
        raise ResourceToolError(
            f"could not write the requested output file ({exc.__class__.__name__})"
        ) from exc


def read_json_file(raw: str) -> dict[str, Any]:
    """Read one bounded regular JSON file without following symlinks."""
    path = Path(raw)
    try:
        if path.is_symlink():
            raise ResourceToolError("refusing to read a symbolic link")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ResourceToolError("snapshot input must be a regular file")
            if info.st_size > MAX_SNAPSHOT_BYTES:
                raise ResourceToolError(f"snapshot input exceeds {MAX_SNAPSHOT_BYTES} bytes")
            payload = stream.read(MAX_SNAPSHOT_BYTES + 1)
        if len(payload) > MAX_SNAPSHOT_BYTES:
            raise ResourceToolError(
                f"snapshot input exceeds {MAX_SNAPSHOT_BYTES} bytes"
            )
    except ResourceToolError:
        raise
    except OSError as exc:
        raise ResourceToolError(
            f"could not read snapshot ({exc.__class__.__name__})"
        ) from exc
    try:
        parsed = json.loads(payload)
    except (RecursionError, UnicodeDecodeError, ValueError) as exc:
        raise ResourceToolError("snapshot is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise ResourceToolError("snapshot JSON root must be an object")
    return parsed


def bounded_int(
    value: Any,
    *,
    minimum: int = 0,
    maximum: int = MAX_BYTES,
) -> int | None:
    """Return a bounded integer without accepting booleans or floats."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and minimum <= value <= maximum:
        return value
    return None


def bounded_number(
    value: Any,
    *,
    minimum: float = 0.0,
    maximum: float = float(MAX_BYTES),
) -> float | None:
    """Return a finite bounded number without accepting booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    if not math.isfinite(number) or not minimum <= number <= maximum:
        return None
    return number


def argparse_positive_int(
    value: str,
    *,
    maximum: int = MAX_TASKS,
) -> int:
    """Argparse converter for bounded positive integers."""
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if not 1 <= parsed <= maximum:
        raise argparse.ArgumentTypeError(f"must be between 1 and {maximum}")
    return parsed


def argparse_nonnegative_int(
    value: str,
    *,
    maximum: int = MAX_BYTES,
) -> int:
    """Argparse converter for bounded nonnegative integers."""
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if not 0 <= parsed <= maximum:
        raise argparse.ArgumentTypeError(f"must be between 0 and {maximum}")
    return parsed


def cli_error(parser: argparse.ArgumentParser, exc: Exception) -> int:
    """Print one safe CLI error without a traceback."""
    parser.exit(2, f"{parser.prog}: error: {exc}\n")
    return 2
