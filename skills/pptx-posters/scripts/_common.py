#!/usr/bin/env python3
"""Shared, dependency-free safety helpers for the poster command-line tools."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_INPUT_BYTES = 512 * 1024 * 1024
MAX_ASSET_BYTES = 128 * 1024 * 1024
MAX_REPORT_BYTES = 8 * 1024 * 1024
PPTX_MIN_INCHES = 1.0
PPTX_MAX_INCHES = 56.0
EMU_PER_INCH = 914_400

_REMOTE_OR_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_PLACEHOLDER_PATTERNS = (
    re.compile(
        r"\b(?:TODO|TBD|TBC|FIXME|LOREM\s+IPSUM|"
        r"REPLACE(?:[_ -]?ME)?(?:[_ -][A-Z0-9]+)*|"
        r"PLACEHOLDER|INSERT[_ -]HERE|YOUR[_ -](?:TITLE|NAME|TEXT|URL))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:<|\[)\s*(?:title|author|affiliation|content|citation|source|"
        r"url|doi|path|value)\s*(?:>|\])",
        re.IGNORECASE,
    ),
)


class CliError(ValueError):
    """An expected validation or command-line error."""


def checked_input_file(
    value: str | os.PathLike[str],
    *,
    max_bytes: int = MAX_INPUT_BYTES,
    suffixes: Iterable[str] | None = None,
) -> Path:
    """Return a bounded regular input file while rejecting a final symlink."""
    path = Path(value)
    if path.is_symlink():
        raise CliError(f"input must not be a symlink: {path}")
    try:
        info = path.stat()
    except OSError as exc:
        raise CliError(f"cannot access input file {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise CliError(f"input is not a regular file: {path}")
    if info.st_size > max_bytes:
        raise CliError(
            f"input is {info.st_size} bytes; limit is {max_bytes} bytes"
        )
    resolved = path.resolve()
    if suffixes is not None:
        allowed = {suffix.lower() for suffix in suffixes}
        if resolved.suffix.lower() not in allowed:
            raise CliError(
                f"input suffix must be one of {', '.join(sorted(allowed))}: {path}"
            )
    return resolved


def checked_output_file(
    value: str | os.PathLike[str],
    *,
    suffix: str | None = None,
) -> Path:
    """Validate a new output path; existing destinations are never overwritten."""
    path = Path(value)
    if path.name in {"", ".", ".."}:
        raise CliError("output must name a file")
    if path.is_symlink():
        raise CliError(f"output must not be a symlink: {path}")
    parent = path.parent
    if not parent.exists() or not parent.is_dir():
        raise CliError(f"output parent directory does not exist: {parent}")
    if parent.is_symlink():
        raise CliError(f"output parent must not be a symlink: {parent}")
    destination = parent.resolve() / path.name
    if destination.exists():
        raise CliError(f"refusing to overwrite existing output: {destination}")
    if suffix is not None and destination.suffix.lower() != suffix.lower():
        raise CliError(f"output must use the {suffix} suffix: {destination}")
    return destination


def private_temp_file(destination: Path, *, suffix: str = ".tmp") -> tuple[int, Path]:
    """Create a private same-directory temporary file for an output."""
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=suffix,
        dir=destination.parent,
    )
    temporary = Path(raw_path)
    os.chmod(temporary, 0o600)
    return descriptor, temporary


def commit_temp_file(temporary: Path, destination: Path) -> None:
    """Publish a temporary file without replacing an existing destination."""
    if destination.exists():
        raise CliError(f"refusing to overwrite existing output: {destination}")
    try:
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise CliError(
            f"refusing to overwrite existing output: {destination}"
        ) from exc
    except OSError as exc:
        raise CliError(f"cannot publish output {destination}: {exc}") from exc
    os.chmod(destination, 0o600)


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Write bytes through a private temporary file without replacement."""
    destination = checked_output_file(path)
    descriptor, temporary = private_temp_file(destination)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        commit_temp_file(temporary, destination)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def emit_json(
    document: dict[str, Any],
    *,
    output: str | os.PathLike[str] | None = None,
) -> None:
    """Print deterministic JSON or safely write it to a new file."""
    payload = (
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    if len(payload) > MAX_REPORT_BYTES:
        raise CliError(
            f"report is {len(payload)} bytes; limit is {MAX_REPORT_BYTES} bytes"
        )
    if output is None:
        print(payload.decode("utf-8"), end="")
        return
    atomic_write_bytes(Path(output), payload)


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CliError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise CliError(f"non-finite JSON number is not allowed: {value}")


def load_json_file(
    value: str | os.PathLike[str],
    *,
    max_bytes: int = MAX_JSON_BYTES,
) -> tuple[Path, Any]:
    """Read strict UTF-8 JSON with duplicate and non-finite values rejected."""
    path = checked_input_file(value, max_bytes=max_bytes, suffixes={".json"})
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CliError(f"JSON must be UTF-8: {path}") from exc
    except OSError as exc:
        raise CliError(f"cannot read JSON {path}: {exc}") from exc
    try:
        document = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_nonfinite_constant,
        )
    except json.JSONDecodeError as exc:
        raise CliError(
            f"invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: "
            f"{exc.msg}"
        ) from exc
    return path, document


def reject_unknown_keys(
    value: Any,
    *,
    context: str,
    allowed: set[str],
    required: set[str],
) -> dict[str, Any]:
    """Return an object after enforcing exact keys."""
    if not isinstance(value, dict):
        raise CliError(f"{context} must be an object")
    unknown = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unknown:
        raise CliError(f"{context} has unknown key(s): {', '.join(unknown)}")
    if missing:
        raise CliError(f"{context} is missing key(s): {', '.join(missing)}")
    return value


def require_string(
    value: Any,
    *,
    context: str,
    minimum: int = 1,
    maximum: int = 10_000,
) -> str:
    """Validate a bounded string without trimming or changing its content."""
    if not isinstance(value, str):
        raise CliError(f"{context} must be a string")
    if not minimum <= len(value) <= maximum:
        raise CliError(
            f"{context} length must be between {minimum} and {maximum} characters"
        )
    if any(ord(character) < 32 and character not in "\t\n\r" for character in value):
        raise CliError(f"{context} contains a forbidden control character")
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise CliError(f"{context} contains an unpaired Unicode surrogate")
    return value


def require_bool(value: Any, *, context: str) -> bool:
    if not isinstance(value, bool):
        raise CliError(f"{context} must be true or false")
    return value


def finite_number(
    value: Any,
    *,
    context: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    """Validate a finite JSON number, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CliError(f"{context} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise CliError(f"{context} must be finite")
    if minimum is not None and number < minimum:
        raise CliError(f"{context} must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise CliError(f"{context} must be at most {maximum}")
    return number


def positive_int(value: Any, *, context: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CliError(f"{context} must be an integer")
    if value < 1 or value > maximum:
        raise CliError(f"{context} must be between 1 and {maximum}")
    return value


def canonical_json_hash(value: Any) -> str:
    """Return SHA-256 for canonical UTF-8 JSON."""
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path, *, max_bytes: int = MAX_ASSET_BYTES) -> str:
    """Hash a bounded regular file without loading it all into memory."""
    checked = checked_input_file(path, max_bytes=max_bytes)
    digest = hashlib.sha256()
    with checked.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def resolve_local_asset(
    manifest_path: Path,
    relative_value: Any,
    *,
    suffixes: set[str],
) -> Path:
    """Resolve a manifest-relative local file while preventing path escape."""
    raw = require_string(relative_value, context="asset.path", maximum=512)
    if _REMOTE_OR_SCHEME.match(raw) or raw.startswith(("/", "\\")):
        raise CliError(f"asset.path must be a relative local path: {raw!r}")
    if "\\" in raw:
        raise CliError("asset.path must use forward slashes")
    relative = Path(raw)
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise CliError(f"asset.path contains an unsafe segment: {raw!r}")
    root = manifest_path.parent.resolve()
    candidate = root / relative
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise CliError(f"asset.path escapes the manifest directory: {raw!r}") from exc
    return checked_input_file(
        candidate,
        max_bytes=MAX_ASSET_BYTES,
        suffixes=suffixes,
    )


def has_placeholder(value: Any) -> tuple[str, str] | None:
    """Return the first JSON path and placeholder string, if present."""

    def walk(item: Any, path: str) -> tuple[str, str] | None:
        if isinstance(item, str):
            for pattern in _PLACEHOLDER_PATTERNS:
                if pattern.search(item):
                    return path, item
            return None
        if isinstance(item, list):
            for index, child in enumerate(item):
                found = walk(child, f"{path}[{index}]")
                if found:
                    return found
            return None
        if isinstance(item, dict):
            for key, child in item.items():
                found = walk(child, f"{path}.{key}")
                if found:
                    return found
        return None

    return walk(value, "$")


def parse_aware_datetime(value: Any, *, context: str) -> str:
    """Validate an ISO 8601 timestamp that includes a UTC offset."""
    text = require_string(value, context=context, maximum=64)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise CliError(f"{context} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CliError(f"{context} must include a UTC offset")
    return text


def parse_hex_color(value: Any, *, context: str) -> str:
    """Validate and normalize an opaque six-digit sRGB color."""
    text = require_string(value, context=context, maximum=7)
    if not _HEX_COLOR.fullmatch(text):
        raise CliError(f"{context} must be a six-digit hex color such as #1A2B3C")
    return text.upper()


def _linear_channel(channel: int) -> float:
    encoded = channel / 255.0
    if encoded <= 0.04045:
        return encoded / 12.92
    return ((encoded + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    channels = tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))
    red, green, blue = (_linear_channel(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    """Return the WCAG contrast ratio of two normalized sRGB colors."""
    first_luminance = relative_luminance(first)
    second_luminance = relative_luminance(second)
    lighter = max(first_luminance, second_luminance)
    darker = min(first_luminance, second_luminance)
    return (lighter + 0.05) / (darker + 0.05)
