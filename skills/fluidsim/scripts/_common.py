#!/usr/bin/env python3
"""Shared dependency-free safety and JSON helpers for FluidSim skill CLIs."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import sys
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePath
from typing import Any


SCHEMA_VERSION = "1.1"
MIB = 1024**2
GIB = 1024**3
MAX_JSON_BYTES = 4 * MIB
MAX_REPORT_BYTES = 8 * MIB
MAX_TEXT_BYTES = 256 * MIB
MAX_HDF5_BYTES = 8 * 1024 * GIB
MAX_FILES = 10_000
MAX_DATASETS = 100_000
MAX_ATTRIBUTES = 100_000
MAX_RECORDS = 2_000_000
MAX_GRID_POINTS = 2**48
MAX_DIMENSION = 131_072
MAX_OUTPUT_FILES = 1_000_000
MAX_CPU_CORES = 1_048_576
MAX_WALL_MINUTES = 10 * 365 * 24 * 60

_URI_PREFIXES = (
    "http:",
    "https:",
    "ftp:",
    "file:",
    "s3:",
    "gs:",
    "ssh:",
    "data:",
)
_SAFE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ToolError(ValueError):
    """Expected validation or local-I/O failure."""


def bounded_int(
    value: Any, *, name: str, minimum: int, maximum: int
) -> int:
    """Validate a non-boolean integer against fixed limits."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ToolError(f"{name} must be between {minimum} and {maximum}")
    return value


def finite_float(
    value: Any,
    *,
    name: str,
    minimum: float | None = None,
    maximum: float | None = None,
    allow_none: bool = False,
) -> float | None:
    """Validate a finite JSON number."""

    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ToolError(f"{name} must be a finite number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ToolError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ToolError(f"{name} must be a finite number")
    if minimum is not None and number < minimum:
        raise ToolError(f"{name} must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise ToolError(f"{name} must be at most {maximum}")
    return number


def validate_keys(
    value: Mapping[str, Any],
    *,
    allowed: Iterable[str],
    required: Iterable[str] = (),
    context: str,
) -> None:
    """Reject unknown keys and require declared keys."""

    allowed_set = set(allowed)
    required_set = set(required)
    unknown = sorted(set(value) - allowed_set)
    missing = sorted(required_set - set(value))
    if unknown:
        raise ToolError(f"{context} contains unsupported keys: {', '.join(unknown)}")
    if missing:
        raise ToolError(f"{context} is missing keys: {', '.join(missing)}")


def require_mapping(value: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ToolError(f"{context} must be a JSON object")
    return value


def require_text(
    value: Any, *, name: str, minimum: int = 1, maximum: int = 2_000
) -> str:
    if not isinstance(value, str):
        raise ToolError(f"{name} must be a string")
    if not minimum <= len(value) <= maximum:
        raise ToolError(f"{name} length must be between {minimum} and {maximum}")
    if any(ord(character) < 32 and character not in "\t" for character in value):
        raise ToolError(f"{name} contains control characters")
    return value


def require_text_list(
    value: Any, *, name: str, minimum: int = 1, maximum: int = 100
) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ToolError(f"{name} must contain {minimum}..{maximum} strings")
    return [
        require_text(item, name=f"{name} item", minimum=1, maximum=1_000)
        for item in value
    ]


def safe_slug(value: Any, *, name: str) -> str:
    """Validate one local path component."""

    text = require_text(value, name=name, maximum=128)
    if not _SAFE_SLUG.fullmatch(text) or text in {".", ".."}:
        raise ToolError(
            f"{name} must use only letters, digits, '.', '_', or '-'"
        )
    return text


def safe_relative_path(
    value: Any,
    *,
    name: str,
    suffixes: Iterable[str] | None = None,
    allow_nested: bool = False,
) -> str:
    """Validate a local relative path without traversal or URI syntax."""

    text = require_text(value, name=name, maximum=512).strip()
    lowered = text.casefold()
    if (
        text.startswith(("~", "/", "\\"))
        or "://" in lowered
        or lowered.startswith(_URI_PREFIXES)
    ):
        raise ToolError(f"{name} must be a local relative path")
    path = PurePath(text)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ToolError(f"{name} must not contain traversal")
    if not allow_nested and len(path.parts) != 1:
        raise ToolError(f"{name} must be one path component")
    for part in path.parts:
        safe_slug(part, name=name)
    if suffixes is not None and not any(
        text.casefold().endswith(suffix.casefold()) for suffix in suffixes
    ):
        raise ToolError(f"{name} has an unsupported suffix")
    return text


def _reject_unsafe_path_text(value: str) -> None:
    stripped = value.strip()
    lowered = stripped.casefold()
    if not stripped or "\x00" in value:
        raise ToolError("path must be nonempty and contain no NUL byte")
    if (
        stripped.startswith("~")
        or "://" in lowered
        or lowered.startswith(_URI_PREFIXES)
    ):
        raise ToolError("only local filesystem paths are accepted")
    if ".." in PurePath(stripped).parts:
        raise ToolError("parent traversal is not accepted")


def _absolute_lexical(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _reject_symlink_components(path: Path) -> None:
    absolute = _absolute_lexical(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ToolError("a path component could not be inspected") from exc
        if stat.S_ISLNK(mode):
            raise ToolError("symlink path components are not accepted")


def checked_root(value: str | os.PathLike[str]) -> Path:
    """Resolve an existing, non-symlink local directory."""

    raw = os.fspath(value)
    _reject_unsafe_path_text(raw)
    supplied = _absolute_lexical(Path(raw))
    _reject_symlink_components(supplied)
    try:
        resolved = supplied.resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        raise ToolError("root directory is not accessible") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise ToolError("root must be a directory")
    return resolved


def _within_root(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ToolError("path escapes the declared root") from exc


def checked_input(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    kind: str = "file",
    suffixes: Iterable[str] | None = None,
    max_bytes: int = MAX_HDF5_BYTES,
) -> Path:
    """Resolve a bounded local file or directory without following symlinks."""

    raw = os.fspath(value)
    _reject_unsafe_path_text(raw)
    root_path = checked_root(root)
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    candidate = _absolute_lexical(candidate)
    _reject_symlink_components(candidate)
    try:
        resolved = candidate.resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        raise ToolError("input path is not accessible") from exc
    _within_root(resolved, root_path)
    if kind == "file" and not stat.S_ISREG(info.st_mode):
        raise ToolError("input must be a regular file")
    if kind == "dir" and not stat.S_ISDIR(info.st_mode):
        raise ToolError("input must be a directory")
    if kind == "any" and not (
        stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)
    ):
        raise ToolError("input must be a regular file or directory")
    if stat.S_ISREG(info.st_mode):
        if info.st_nlink != 1:
            raise ToolError("multiply linked input files are not accepted")
        if not 0 <= info.st_size <= max_bytes:
            raise ToolError("input file exceeds the configured byte limit")
        if suffixes is not None and not any(
            resolved.name.casefold().endswith(suffix.casefold())
            for suffix in suffixes
        ):
            raise ToolError("input file has an unsupported suffix")
    return resolved


def checked_output(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    suffixes: Iterable[str],
    force: bool = False,
) -> Path:
    """Resolve a safe local output file within root."""

    relative = safe_relative_path(
        os.fspath(value),
        name="output",
        suffixes=suffixes,
        allow_nested=True,
    )
    root_path = checked_root(root)
    candidate = _absolute_lexical(root_path / relative)
    parent = candidate.parent
    _reject_symlink_components(parent)
    try:
        parent = parent.resolve(strict=True)
    except OSError as exc:
        raise ToolError("output parent must already exist") from exc
    _within_root(parent, root_path)
    destination = parent / candidate.name
    if destination.exists():
        if destination.is_symlink() or not destination.is_file():
            raise ToolError("existing output is not a regular file")
        if not force:
            raise ToolError("refusing to overwrite existing output")
    return destination


def atomic_write(
    destination: Path, payload: bytes, *, force: bool = False
) -> None:
    """Write a private file atomically without creating parent directories."""

    if len(payload) > MAX_REPORT_BYTES:
        raise ToolError("generated output exceeds the hard report-size limit")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        if destination.exists() and not force:
            raise ToolError("refusing to overwrite existing output")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _reject_json_constant(value: str) -> None:
    raise ToolError(f"non-finite JSON number is not accepted: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ToolError(f"duplicate JSON key is not accepted: {key}")
        result[key] = value
    return result


def load_json(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> Any:
    """Load bounded strict UTF-8 JSON."""

    if path.stat().st_size > max_bytes:
        raise ToolError("JSON input exceeds the parsing limit")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(
                handle,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_json_constant,
            )
    except ToolError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ToolError("input is not bounded, valid UTF-8 JSON") from exc


def strict_json_loads(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except ToolError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ToolError("record is not strict JSON") from exc


def json_bytes(document: Any) -> bytes:
    try:
        payload = (
            json.dumps(
                document,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ToolError("report cannot be serialized as strict JSON") from exc
    if len(payload) > MAX_REPORT_BYTES:
        raise ToolError("report exceeds the hard report-size limit")
    return payload


def emit_json(document: Any) -> None:
    sys.stdout.buffer.write(json_bytes(document))


def fail_json(tool: str, exc: Exception) -> int:
    emit_json(
        {
            "error": type(exc).__name__,
            "message": str(exc)[:500],
            "ok": False,
            "tool": tool,
        }
    )
    return 2


def sha256_file(path: Path, *, max_bytes: int) -> str | None:
    """Hash a regular file when it is within an explicit bound."""

    size = path.stat().st_size
    if size > max_bytes:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(MIB), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_local_files(
    path: Path,
    *,
    suffixes: Iterable[str] | None,
    max_files: int,
    recursive: bool = True,
) -> list[Path]:
    """List bounded regular files without traversing symlinks."""

    bounded_int(max_files, name="max_files", minimum=1, maximum=MAX_FILES)
    if path.is_file():
        candidates = [path]
    else:
        candidates = []
        stack = [path]
        while stack:
            directory = stack.pop()
            try:
                entries = sorted(
                    os.scandir(directory), key=lambda entry: entry.name.casefold()
                )
            except OSError as exc:
                raise ToolError("directory cannot be scanned") from exc
            for entry in entries:
                try:
                    if entry.is_symlink():
                        raise ToolError("symlinks in scanned directories are rejected")
                    if entry.is_dir(follow_symlinks=False):
                        if recursive:
                            stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        file_path = Path(entry.path)
                        info = file_path.stat()
                        if info.st_nlink != 1:
                            raise ToolError(
                                "multiply linked files in scanned directories are rejected"
                            )
                        candidates.append(file_path)
                        if len(candidates) > max_files:
                            raise ToolError("file-count limit exceeded")
                except OSError as exc:
                    raise ToolError("directory entry cannot be inspected") from exc
    if suffixes is None:
        return candidates
    lowered = tuple(suffix.casefold() for suffix in suffixes)
    return [
        candidate
        for candidate in candidates
        if candidate.name.casefold().endswith(lowered)
    ]


def relative_display(path: Path, root: Path) -> str:
    """Return a bounded path relative to the caller-declared root."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        return "<outside-root>"
    text = relative.as_posix()
    return text[:512]
