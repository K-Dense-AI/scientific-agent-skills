#!/usr/bin/env python3
"""Shared local-only, bounded-I/O helpers for the EDA command-line tools."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePath
from typing import Any


SCHEMA_VERSION = "1.1"
MIB = 1024 * 1024
DEFAULT_MAX_FILE_BYTES = 64 * MIB
MAX_FILE_BYTES = 512 * MIB
MAX_JSON_BYTES = 16 * MIB
MAX_REPORT_BYTES = 4 * MIB
MAX_ROWS = 1_000_000
DEFAULT_MAX_ROWS = 100_000
MAX_COLUMNS = 512
MAX_FIELD_CHARS = 100_000
MAX_IDENTIFIER_CHARS = 160
MAX_NPZ_MEMBERS = 128
MAX_NPZ_UNCOMPRESSED_BYTES = 128 * MIB
MAX_COMPRESSION_RATIO = 100.0
MAX_IMAGE_PIXELS = 100_000_000


class CliError(ValueError):
    """An expected command-line validation error with no sensitive values."""


def bounded_integer(
    value: int,
    *,
    name: str,
    minimum: int,
    maximum: int,
) -> int:
    """Validate a non-boolean integer against fixed limits."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise CliError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise CliError(f"{name} must be between {minimum} and {maximum}")
    return value


def bounded_file_limit(value: int) -> int:
    """Validate a caller-selected byte limit against the hard ceiling."""

    return bounded_integer(
        value,
        name="max bytes",
        minimum=1,
        maximum=MAX_FILE_BYTES,
    )


def finite_number(value: str) -> float | None:
    """Parse a finite decimal number without evaluating expressions."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _reject_url_and_traversal(value: str) -> None:
    """Reject URLs, NUL bytes, home expansion, and lexical parent traversal."""

    stripped = value.strip()
    lowered = stripped.lower()
    if not stripped:
        raise CliError("path must not be empty")
    if "\x00" in value:
        raise CliError("path must not contain a NUL byte")
    if "://" in lowered or lowered.startswith(
        ("http:", "https:", "ftp:", "s3:", "gs:", "file:", "data:")
    ):
        raise CliError("URLs are not accepted; provide a local path")
    if stripped.startswith("~"):
        raise CliError("home-directory expansion is not accepted")
    if ".." in PurePath(stripped).parts:
        raise CliError("parent-directory traversal is not accepted")


def _absolute_lexical(path: Path) -> Path:
    """Make a path absolute without intentionally resolving symlinks."""

    return Path(os.path.abspath(os.fspath(path)))


def _reject_symlink_components(path: Path) -> None:
    """Reject an existing symlink at any component of an absolute path."""

    absolute = _absolute_lexical(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                raise CliError("symlink path components are not accepted")
        except OSError as exc:
            raise CliError("a path component could not be inspected") from exc


def checked_root(value: str | os.PathLike[str]) -> Path:
    """Return an existing, non-symlink directory used as the I/O boundary."""

    raw = os.fspath(value)
    _reject_url_and_traversal(raw)
    supplied = _absolute_lexical(Path(raw))
    if supplied.is_symlink():
        raise CliError("the root directory must not be a symlink")
    try:
        root = supplied.resolve(strict=True)
        info = root.stat()
    except OSError as exc:
        raise CliError("the root directory is not accessible") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CliError("the root must be an existing directory")
    _reject_symlink_components(root)
    return root


def _within_root(candidate: Path, root: Path) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise CliError("path escapes the declared root directory") from exc


def _suffix_matches(path: Path, suffixes: Iterable[str]) -> bool:
    name = path.name.casefold()
    return any(name.endswith(suffix.casefold()) for suffix in suffixes)


def checked_input_file(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    suffixes: Iterable[str] | None = None,
    max_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> Path:
    """Return a bounded regular local file inside root, rejecting all symlinks."""

    max_bytes = bounded_file_limit(max_bytes)
    raw = os.fspath(value)
    _reject_url_and_traversal(raw)
    root_path = checked_root(root)
    path = Path(raw)
    if not path.is_absolute():
        path = root_path / path
    path = _absolute_lexical(path)
    if path.is_symlink():
        raise CliError("the input must not be a symlink")
    try:
        resolved = path.resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        raise CliError("the input file is not accessible") from exc
    _within_root(resolved, root_path)
    _reject_symlink_components(resolved)
    if not stat.S_ISREG(info.st_mode):
        raise CliError("the input must be a regular file")
    if info.st_nlink != 1:
        raise CliError("multiply linked input files are not accepted")
    if info.st_size > max_bytes:
        raise CliError(
            f"the input is {info.st_size} bytes; the configured limit is {max_bytes}"
        )
    if suffixes is not None and not _suffix_matches(resolved, suffixes):
        allowed = ", ".join(sorted({item.casefold() for item in suffixes}))
        raise CliError(f"the input suffix must be one of: {allowed}")
    return resolved


def checked_output_file(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    suffixes: Iterable[str],
    force: bool = False,
) -> Path:
    """Return a local output path inside root without following symlinks."""

    raw = os.fspath(value)
    _reject_url_and_traversal(raw)
    root_path = checked_root(root)
    path = Path(raw)
    if not path.is_absolute():
        path = root_path / path
    path = _absolute_lexical(path)
    if path.name in {"", ".", ".."}:
        raise CliError("the output must name a file")
    if not _suffix_matches(path, suffixes):
        allowed = ", ".join(sorted({item.casefold() for item in suffixes}))
        raise CliError(f"the output suffix must be one of: {allowed}")
    if path.is_symlink() or path.parent.is_symlink():
        raise CliError("output symlinks are not accepted")
    try:
        parent = path.parent.resolve(strict=True)
        parent_info = parent.stat()
    except OSError as exc:
        raise CliError("the output parent is not accessible") from exc
    _within_root(parent, root_path)
    _reject_symlink_components(parent)
    if not stat.S_ISDIR(parent_info.st_mode):
        raise CliError("the output parent must be an existing directory")
    destination = parent / path.name
    if destination.exists():
        if destination.is_symlink() or not destination.is_file():
            raise CliError("the output exists but is not a regular file")
        if not force:
            raise CliError("refusing to overwrite an existing output")
    return destination


def _strict_json_bytes(document: Any) -> bytes:
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
        raise CliError("the report could not be serialized as strict JSON") from exc
    if len(payload) > MAX_REPORT_BYTES:
        raise CliError(
            f"the report is {len(payload)} bytes; the limit is {MAX_REPORT_BYTES}"
        )
    return payload


def atomic_write_bytes(
    output: str | os.PathLike[str],
    payload: bytes,
    *,
    root: str | os.PathLike[str] = ".",
    suffixes: Iterable[str],
    force: bool = False,
) -> Path:
    """Write a private file atomically in an existing local directory."""

    destination = checked_output_file(
        output,
        root=root,
        suffixes=suffixes,
        force=force,
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        if destination.exists() and not force:
            raise CliError("refusing to overwrite an existing output")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def emit_json(
    document: Any,
    *,
    output: str | os.PathLike[str] | None = None,
    root: str | os.PathLike[str] = ".",
    force: bool = False,
) -> None:
    """Print strict JSON or write it privately and atomically."""

    payload = _strict_json_bytes(document)
    if output is None:
        print(payload.decode("utf-8"), end="")
        return
    atomic_write_bytes(
        output,
        payload,
        root=root,
        suffixes={".json"},
        force=force,
    )


def emit_markdown(
    text: str,
    *,
    output: str | os.PathLike[str] | None = None,
    root: str | os.PathLike[str] = ".",
    force: bool = False,
) -> None:
    """Print bounded Markdown or write it privately and atomically."""

    payload = text.encode("utf-8")
    if len(payload) > MAX_REPORT_BYTES:
        raise CliError(
            f"the report is {len(payload)} bytes; the limit is {MAX_REPORT_BYTES}"
        )
    if output is None:
        print(text, end="" if text.endswith("\n") else "\n")
        return
    atomic_write_bytes(
        output,
        payload,
        root=root,
        suffixes={".md", ".markdown"},
        force=force,
    )


def stable_token(value: str, *, kind: str) -> str:
    """Return a deterministic pseudonymous token; this is not anonymization."""

    digest = hashlib.blake2s(
        f"eda-v1.1\0{kind}\0{value}".encode("utf-8", errors="surrogatepass"),
        digest_size=8,
    ).hexdigest()
    return f"{kind}_{digest}"


def sanitize_identifier(value: str) -> str:
    """Bound and neutralize an explicitly requested untrusted identifier."""

    cleaned = "".join(
        character if character.isprintable() and character not in "\r\n\t" else " "
        for character in value
    )
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > MAX_IDENTIFIER_CHARS:
        cleaned = cleaned[:MAX_IDENTIFIER_CHARS] + "…"
    return cleaned


def markdown_scalar(value: str) -> str:
    """Return a bounded scalar that cannot introduce Markdown structure."""

    cleaned = sanitize_identifier(value)
    allowed_punctuation = frozenset(" .,_-:()/+")
    return "".join(
        character
        if character.isalnum() or character in allowed_punctuation
        else "�"
        for character in cleaned
    )


def display_identifier(
    value: str,
    *,
    kind: str,
    reveal_identifiers: bool,
) -> str:
    """Reveal a sanitized identifier only after explicit caller opt-in."""

    if reveal_identifiers:
        return sanitize_identifier(value)
    return stable_token(value, kind=kind)


def _reject_json_constant(value: str) -> None:
    raise CliError("non-finite JSON numbers are not accepted")


def _finite_json_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise CliError("JSON number exceeds the finite floating-point range")
    return number


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CliError("duplicate JSON object keys are not accepted")
        result[key] = value
    return result


def load_strict_json(
    path: Path,
    *,
    max_bytes: int = MAX_JSON_BYTES,
) -> Any:
    """Load bounded RFC-style JSON, rejecting duplicate keys and NaN/Infinity."""

    if path.stat().st_size > max_bytes:
        raise CliError(f"JSON input exceeds the {max_bytes}-byte parsing limit")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(
                handle,
                object_pairs_hook=_unique_json_object,
                parse_constant=_reject_json_constant,
                parse_float=_finite_json_float,
            )
    except CliError:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError, MemoryError) as exc:
        raise CliError("the input is not bounded, valid UTF-8 JSON") from exc


def validate_keys(
    value: Mapping[str, Any],
    *,
    allowed: Iterable[str],
    required: Iterable[str] = (),
    context: str,
) -> None:
    """Reject unknown keys and report missing required keys."""

    allowed_set = set(allowed)
    required_set = set(required)
    unknown = set(value) - allowed_set
    missing = required_set - set(value)
    if unknown:
        raise CliError(f"{context} contains unsupported keys")
    if missing:
        raise CliError(f"{context} is missing required keys")


def sha256_file(path: Path, *, max_bytes: int) -> str:
    """Hash a previously checked bounded regular file using streaming reads."""

    if path.stat().st_size > max_bytes:
        raise CliError("the file exceeds the configured hashing limit")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(MIB), b""):
                digest.update(chunk)
    except OSError as exc:
        raise CliError("the input could not be hashed") from exc
    return digest.hexdigest()


def run_cli(function: Any) -> int:
    """Run a CLI body with concise expected-error handling."""

    try:
        function()
    except CliError as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("error: interrupted", file=os.sys.stderr)
        return 130
    return 0
