#!/usr/bin/env python3
"""Shared bounded-I/O helpers for the PathML skill CLIs."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


PATHML_VERSION = "3.0.8"
PINNED_INSTALL = 'uv pip install "pathml==3.0.8"'
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_CSV_BYTES = 64 * 1024 * 1024
MAX_IMAGE_BYTES = 256 * 1024 * 1024
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_ROWS = 1_000_000
MAX_PIXELS = 16_000_000
MAX_DIMENSION = 1_000_000_000


class CliError(ValueError):
    """An expected, concise command-line validation error."""


def _reject_constant(value: str) -> None:
    raise CliError(f"non-standard JSON constant is not allowed: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CliError(f"duplicate JSON key is not allowed: {key!r}")
        result[key] = value
    return result


def _reject_url(value: str) -> None:
    lowered = value.strip().lower()
    if "://" in lowered or lowered.startswith(
        ("http:", "https:", "ftp:", "s3:", "gs:", "file:")
    ):
        raise CliError("URLs are not accepted; provide a bounded local path")
    if "\x00" in value:
        raise CliError("paths must not contain a NUL byte")


def _absolute_lexical(path: Path) -> Path:
    """Make a path absolute and collapse dot segments without following links."""

    return Path(os.path.abspath(os.fspath(path)))


def _reject_symlink_components(path: Path) -> None:
    """Reject an existing symlink anywhere in an absolute path."""

    absolute = _absolute_lexical(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                raise CliError(f"symlink paths are not accepted: {current.name}")
        except OSError as exc:
            raise CliError(f"cannot inspect path component {current.name}: {exc}") from exc


def checked_root(value: str | os.PathLike[str]) -> Path:
    """Return an existing non-symlink directory used as an I/O boundary."""

    raw = os.fspath(value)
    _reject_url(raw)
    supplied = _absolute_lexical(Path(raw).expanduser())
    if supplied.is_symlink():
        raise CliError("root directory must not itself be a symlink")
    try:
        root = supplied.resolve(strict=True)
        info = root.stat()
    except OSError as exc:
        raise CliError(f"cannot access root directory: {exc}") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CliError("root must be an existing directory")
    _reject_symlink_components(root)
    return root


def _within_root(candidate: Path, root: Path) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise CliError("path escapes the declared root directory") from exc


def _reject_links_below_root(path: Path, root: Path) -> None:
    """Inspect requested components before resolution hides directory links.

    OS aliases above the declared boundary (for example macOS /tmp) are allowed.
    """
    current = path
    while current != current.parent:
        if current.is_symlink():
            raise CliError(f"symlink paths are not accepted: {current.name}")
        if current.resolve() == root:
            return
        current = current.parent


def _suffix_matches(path: Path, suffixes: Iterable[str]) -> bool:
    name = path.name.lower()
    return any(name.endswith(suffix.lower()) for suffix in suffixes)


def checked_input_file(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    suffixes: Iterable[str] | None = None,
    max_bytes: int,
) -> Path:
    """Return a bounded regular local file within root, rejecting symlinks."""

    raw = os.fspath(value)
    _reject_url(raw)
    root_path = checked_root(root)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = root_path / path
    path = _absolute_lexical(path)
    if path.is_symlink():
        raise CliError(f"input must not be a symlink: {path.name!r}")
    _reject_links_below_root(path, root_path)
    try:
        resolved = path.resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        raise CliError(f"cannot access input file {path.name!r}: {exc}") from exc
    _within_root(resolved, root_path)
    _reject_symlink_components(resolved)
    if not stat.S_ISREG(info.st_mode):
        raise CliError(f"input is not a regular file: {path.name!r}")
    if info.st_size > max_bytes:
        raise CliError(
            f"input {path.name!r} is {info.st_size} bytes; limit is {max_bytes}"
        )
    if suffixes is not None and not _suffix_matches(path, suffixes):
        allowed = ", ".join(sorted({suffix.lower() for suffix in suffixes}))
        raise CliError(f"input suffix must be one of: {allowed}")
    return resolved


def checked_output_file(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    suffixes: Iterable[str],
    force: bool = False,
) -> Path:
    """Return a local output path within root without following symlinks."""

    raw = os.fspath(value)
    _reject_url(raw)
    root_path = checked_root(root)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = root_path / path
    path = _absolute_lexical(path)
    if path.name in {"", ".", ".."}:
        raise CliError("output must name a file")
    if not _suffix_matches(path, suffixes):
        allowed = ", ".join(sorted({suffix.lower() for suffix in suffixes}))
        raise CliError(f"output suffix must be one of: {allowed}")
    if path.is_symlink():
        raise CliError(f"output must not be a symlink: {path.name!r}")
    if path.parent.is_symlink():
        raise CliError("output parent must not be a symlink")
    _reject_links_below_root(path.parent, root_path)
    try:
        resolved_parent = path.parent.resolve(strict=True)
        parent_info = resolved_parent.stat()
    except OSError as exc:
        raise CliError(f"cannot access output parent: {exc}") from exc
    _within_root(resolved_parent, root_path)
    _reject_symlink_components(resolved_parent)
    path = resolved_parent / path.name
    if not stat.S_ISDIR(parent_info.st_mode):
        raise CliError("output parent must be an existing directory")
    if path.exists():
        if not path.is_file():
            raise CliError("output exists and is not a regular file")
        if not force:
            raise CliError(f"refusing to overwrite existing output: {path.name!r}")
    return path


def strict_json_bytes(document: Any) -> bytes:
    """Serialize deterministic RFC-compatible JSON with a size cap."""

    try:
        payload = (
            json.dumps(
                document,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CliError(f"report is not strict JSON: {exc}") from exc
    if len(payload) > MAX_REPORT_BYTES:
        raise CliError(
            f"report is {len(payload)} bytes; limit is {MAX_REPORT_BYTES}"
        )
    return payload


def atomic_write_bytes(
    destination: Path,
    payload: bytes,
    *,
    root: str | os.PathLike[str] = ".",
    suffixes: Iterable[str],
    force: bool = False,
) -> Path:
    """Atomically write a private file in an existing local directory."""

    destination = checked_output_file(
        destination, root=root, suffixes=suffixes, force=force
    )
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
            raise CliError(f"refusing to overwrite existing output: {destination.name!r}")
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
    """Print strict JSON or atomically write it with private permissions."""

    payload = strict_json_bytes(document)
    if output is None:
        print(payload.decode("utf-8"), end="")
        return
    atomic_write_bytes(
        Path(output),
        payload,
        root=root,
        suffixes={".json"},
        force=force,
    )


def load_json_object(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    max_bytes: int = MAX_JSON_BYTES,
) -> dict[str, Any]:
    """Load a bounded strict JSON object from a local regular file."""

    path = checked_input_file(
        value,
        root=root,
        suffixes={".json"},
        max_bytes=max_bytes,
    )
    try:
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(
                handle,
                parse_constant=_reject_constant,
                object_pairs_hook=_unique_object,
            )
    except CliError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CliError(f"cannot read valid JSON from {path.name!r}: {exc}") from exc
    if not isinstance(document, dict):
        raise CliError("JSON root must be an object")
    return document


def validate_keys(
    value: Mapping[str, Any],
    *,
    allowed: Iterable[str],
    required: Iterable[str] = (),
    context: str,
) -> None:
    """Reject unknown keys and report required keys."""

    allowed_set = set(allowed)
    required_set = set(required)
    unknown = sorted(set(value) - allowed_set)
    missing = sorted(required_set - set(value))
    if unknown:
        raise CliError(f"{context} has unknown keys: {', '.join(unknown)}")
    if missing:
        raise CliError(f"{context} is missing keys: {', '.join(missing)}")


def bounded_int(
    value: Any,
    *,
    name: str,
    minimum: int,
    maximum: int,
) -> int:
    """Validate an integer, excluding booleans."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise CliError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise CliError(f"{name} must be between {minimum} and {maximum}")
    return value


def finite_float(
    value: Any,
    *,
    name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    """Validate a finite real number, excluding booleans."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CliError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise CliError(f"{name} must be finite")
    if minimum is not None and number < minimum:
        raise CliError(f"{name} must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise CliError(f"{name} must be at most {maximum}")
    return number


def parse_name_list(value: str | None, *, name: str) -> list[str]:
    """Parse a comma-separated list without empty or duplicate names."""

    if value is None:
        return []
    names = [item.strip() for item in value.split(",")]
    if not names or any(not item for item in names):
        raise CliError(f"{name} must be a comma-separated list of nonempty names")
    if len(names) != len(set(names)):
        raise CliError(f"{name} must not contain duplicates")
    return names


def sha256_file(path: Path, *, max_bytes: int) -> str:
    """Hash a bounded regular file using fixed-size streaming reads."""

    size = path.stat().st_size
    if size > max_bytes:
        raise CliError(f"file is {size} bytes; hashing limit is {max_bytes}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
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
