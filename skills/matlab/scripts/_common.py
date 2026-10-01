#!/usr/bin/env python3
"""Shared bounded local-only helpers for the MATLAB skill CLIs."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_TEXT_BYTES = 4 * 1024 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_FILES = 500
MAX_JSON_ITEMS = 20_000
MAX_JSON_DEPTH = 24
MAX_PATH_CHARS = 4096
# Conservative helper portability subset, not modern MATLAB's namelengthmax.
MATLAB_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
MATLAB_RELEASE = re.compile(r"^R(20[0-9]{2})([ab])$")
URL_LIKE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


class CliError(ValueError):
    """Expected, user-actionable CLI failure."""


def _raw_path(value: str) -> Path:
    if not value or len(value) > MAX_PATH_CHARS:
        raise CliError("path is empty or exceeds the length limit")
    if "\x00" in value or URL_LIKE.match(value):
        raise CliError("only local filesystem paths are accepted")
    return Path(value)


def _reject_symlink_chain(path: Path) -> None:
    """Reject every existing symlink component without following it."""
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise CliError(f"symlink paths are not accepted: {current}")


def checked_root(value: str | Path) -> Path:
    raw = _raw_path(str(value))
    _reject_symlink_chain(raw)
    try:
        root = raw.resolve(strict=True)
    except OSError as exc:
        raise CliError(f"root does not exist or is inaccessible: {raw}") from exc
    if not root.is_dir():
        raise CliError(f"root is not a directory: {root}")
    return root


def checked_input(
    value: str | Path,
    *,
    root: Path,
    kind: str = "file",
    suffixes: Iterable[str] | None = None,
    max_bytes: int = MAX_INPUT_BYTES,
) -> Path:
    raw = _raw_path(str(value))
    candidate = raw if raw.is_absolute() else root / raw
    _reject_symlink_chain(candidate)
    try:
        path = candidate.resolve(strict=True)
        path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise CliError(f"input must exist within root {root}") from exc
    if kind == "file" and not path.is_file():
        raise CliError(f"input is not a regular file: {path}")
    if kind == "directory" and not path.is_dir():
        raise CliError(f"input is not a directory: {path}")
    if kind == "any" and not (path.is_file() or path.is_dir()):
        raise CliError(f"input is not a regular file or directory: {path}")
    if kind not in {"file", "directory", "any"}:
        raise CliError(f"unsupported input kind: {kind}")
    if suffixes is not None and path.is_file():
        allowed = {suffix.casefold() for suffix in suffixes}
        if path.suffix.casefold() not in allowed:
            raise CliError(
                f"unsupported suffix {path.suffix!r}; expected one of {sorted(allowed)}"
            )
    if path.is_file():
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise CliError(f"cannot stat input: {path}") from exc
        if size > max_bytes:
            raise CliError(f"input is {size} bytes; limit is {max_bytes}")
    return path


def checked_output(
    value: str | Path,
    *,
    root: Path,
    suffixes: Iterable[str] | None = None,
) -> Path:
    raw = _raw_path(str(value))
    candidate = raw if raw.is_absolute() else root / raw
    _reject_symlink_chain(candidate)
    try:
        parent = candidate.parent.resolve(strict=True)
        parent.relative_to(root)
    except (OSError, ValueError) as exc:
        raise CliError(f"output parent must exist within root {root}") from exc
    path = parent / candidate.name
    if path.exists() or path.is_symlink():
        raise CliError(f"refusing to overwrite existing output: {path}")
    if suffixes is not None:
        allowed = {suffix.casefold() for suffix in suffixes}
        if path.suffix.casefold() not in allowed:
            raise CliError(
                f"unsupported output suffix {path.suffix!r}; "
                f"expected one of {sorted(allowed)}"
            )
    return path


def read_bytes(path: Path, *, max_bytes: int = MAX_INPUT_BYTES) -> bytes:
    try:
        size = path.stat().st_size
        if size > max_bytes:
            raise CliError(f"input is {size} bytes; limit is {max_bytes}")
        return path.read_bytes()
    except CliError:
        raise
    except OSError as exc:
        raise CliError(f"cannot read input: {path}") from exc


def read_text(path: Path, *, max_bytes: int = MAX_TEXT_BYTES) -> str:
    payload = read_bytes(path, max_bytes=max_bytes)
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CliError(f"input is not UTF-8 text: {path}") from exc


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise CliError(f"duplicate JSON key: {key!r}")
        output[key] = value
    return output


def _validate_json_shape(value: Any, *, depth: int = 0) -> int:
    if depth > MAX_JSON_DEPTH:
        raise CliError(f"JSON nesting exceeds {MAX_JSON_DEPTH}")
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, str) and len(value) > 100_000:
            raise CliError("JSON string exceeds 100000 characters")
        return 1
    if isinstance(value, list):
        return 1 + sum(_validate_json_shape(item, depth=depth + 1) for item in value)
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise CliError("JSON object keys must be strings")
        return 1 + sum(
            _validate_json_shape(item, depth=depth + 1) for item in value.values()
        )
    raise CliError(f"unsupported JSON value type: {type(value).__name__}")


def parse_json_text(text: str) -> Any:
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except CliError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise CliError(f"invalid JSON: {exc}") from exc
    item_count = _validate_json_shape(value)
    if item_count > MAX_JSON_ITEMS:
        raise CliError(f"JSON has {item_count} values; limit is {MAX_JSON_ITEMS}")
    return value


def load_json(path: Path) -> Any:
    return parse_json_text(read_text(path, max_bytes=MAX_JSON_BYTES))


def bounded_int(
    value: str | int,
    *,
    name: str,
    minimum: int,
    maximum: int,
) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise CliError(f"{name} must be an integer") from exc
    if number < minimum or number > maximum:
        raise CliError(f"{name} must be between {minimum} and {maximum}")
    return number


def validate_identifier(value: str, *, name: str = "identifier") -> str:
    if not MATLAB_IDENTIFIER.fullmatch(value):
        raise CliError(
            f"{name} must use the helper's MATLAB identifier subset (at most 63 characters)"
        )
    return value


def validate_release(value: str) -> str:
    if not MATLAB_RELEASE.fullmatch(value):
        raise CliError("MATLAB release must look like R2026a")
    return value


def sha256_file(path: Path, *, max_bytes: int = MAX_INPUT_BYTES) -> str:
    size = path.stat().st_size
    if size > max_bytes:
        raise CliError(f"input is {size} bytes; hash limit is {max_bytes}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(64 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise CliError(f"cannot hash input: {path}") from exc
    return digest.hexdigest()


def relative_id(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def write_new_text(path: Path, text: str) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except FileExistsError as exc:
        raise CliError(f"refusing to overwrite existing output: {path}") from exc
    except OSError as exc:
        raise CliError(f"cannot write output: {path}") from exc


def emit_json(value: Any) -> None:
    json.dump(value, sys.stdout, indent=2, sort_keys=True, ensure_ascii=False)
    sys.stdout.write("\n")


def fail_json(tool: str, exc: Exception) -> int:
    emit_json(
        {
            "error": str(exc),
            "executes_external_code": False,
            "network_accessed": False,
            "ok": False,
            "tool": tool,
        }
    )
    return 2
