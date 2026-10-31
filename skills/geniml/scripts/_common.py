#!/usr/bin/env python3
"""Shared, dependency-free safety helpers for local Geniml skill CLIs."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any, Iterator


HARD_MAX_FILES = 100_000
HARD_MAX_BYTES = 8 * 1024**3
HARD_MAX_RECORDS = 10_000_000
HARD_MAX_LINE_BYTES = 1024 * 1024
HARD_MAX_WORKERS = 256
HARD_MAX_EPOCHS = 100_000
MAX_COORDINATE = 2**63 - 1

_SCHEMES = (
    "http:",
    "https:",
    "ftp:",
    "file:",
    "s3:",
    "gs:",
    "hf:",
    "ssh:",
)
_INTEGER = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
_FLOAT = re.compile(
    r"^-?(?:(?:0|[1-9][0-9]*)\.[0-9]+|(?:0|[1-9][0-9]*)(?:[eE][+-]?[0-9]+))$"
)
_YAML_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


class SafetyError(ValueError):
    """Raised when a local-input safety contract is violated."""


def bounded_int(
    value: str,
    *,
    minimum: int = 0,
    maximum: int,
    label: str,
) -> int:
    """Parse an integer while enforcing an explicit hard bound."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise SafetyError(f"{label} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise SafetyError(f"{label} must be between {minimum} and {maximum}")
    return parsed


def int_type(*, minimum: int = 0, maximum: int, label: str):
    """Return an argparse-compatible bounded integer parser."""

    def parse(value: str) -> int:
        try:
            return bounded_int(
                value,
                minimum=minimum,
                maximum=maximum,
                label=label,
            )
        except SafetyError as exc:
            raise ValueError(str(exc)) from exc

    return parse


def _reject_unsafe_text_path(raw: str) -> None:
    if not raw or "\x00" in raw:
        raise SafetyError("path must be a nonempty string without NUL bytes")
    lowered = raw.strip().lower()
    if lowered.startswith(_SCHEMES) or "://" in lowered:
        raise SafetyError("URLs and URI-like paths are not allowed")
    if raw.startswith("~"):
        raise SafetyError("home expansion is not allowed; pass an explicit path")
    if ".." in Path(raw).parts:
        raise SafetyError("parent traversal ('..') is not allowed")


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise SafetyError("symlink path component is not allowed")


def local_path(
    raw: str,
    *,
    must_exist: bool = True,
    kind: str = "any",
) -> Path:
    """Resolve a strict local path without following symlinks."""
    _reject_unsafe_text_path(raw)
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    candidate = Path(os.path.abspath(candidate))
    _reject_symlink_components(candidate)

    try:
        mode = candidate.lstat().st_mode
    except FileNotFoundError:
        if must_exist:
            raise SafetyError("required local path does not exist")
        parent = candidate.parent
        try:
            parent_mode = parent.lstat().st_mode
        except FileNotFoundError as exc:
            raise SafetyError("output parent does not exist") from exc
        if not stat.S_ISDIR(parent_mode):
            raise SafetyError("output parent is not a directory")
        return candidate

    if stat.S_ISLNK(mode):
        raise SafetyError("symlinks are not allowed")
    if kind == "file" and not stat.S_ISREG(mode):
        raise SafetyError("expected a regular file")
    if kind == "dir" and not stat.S_ISDIR(mode):
        raise SafetyError("expected a directory")
    if kind == "any" and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        raise SafetyError("only regular files and directories are allowed")
    return candidate


def _open_binary_nofollow(path: Path):
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    mode = os.fstat(descriptor).st_mode
    if not stat.S_ISREG(mode):
        os.close(descriptor)
        raise SafetyError("expected a regular file")
    return os.fdopen(descriptor, "rb")


def iter_text_lines(
    path: Path,
    *,
    max_bytes: int,
    max_records: int,
    max_line_bytes: int = HARD_MAX_LINE_BYTES,
) -> Iterator[tuple[int, str]]:
    """Yield UTF-8 text lines with compressed and expanded bounds."""
    if max_bytes < 1 or max_bytes > HARD_MAX_BYTES:
        raise SafetyError("max_bytes is outside the hard safety bound")
    if max_records < 1 or max_records > HARD_MAX_RECORDS:
        raise SafetyError("max_records is outside the hard safety bound")
    if max_line_bytes < 1 or max_line_bytes > HARD_MAX_LINE_BYTES:
        raise SafetyError("max_line_bytes is outside the hard safety bound")
    if path.stat().st_size > max_bytes:
        raise SafetyError("compressed/input file exceeds byte limit")

    expanded_bytes = 0
    with _open_binary_nofollow(path) as raw_handle:
        if path.name.lower().endswith(".gz"):
            stream = gzip.GzipFile(fileobj=raw_handle, mode="rb")
        else:
            stream = raw_handle
        try:
            line_number = 0
            while raw_line := stream.readline(max_line_bytes + 1):
                line_number += 1
                if line_number > max_records:
                    raise SafetyError("record limit exceeded")
                if len(raw_line) > max_line_bytes:
                    raise SafetyError(f"line {line_number} exceeds line-size limit")
                expanded_bytes += len(raw_line)
                if expanded_bytes > max_bytes:
                    raise SafetyError("expanded text exceeds byte limit")
                if b"\x00" in raw_line:
                    raise SafetyError(f"NUL byte found at line {line_number}")
                try:
                    text = raw_line.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise SafetyError(
                        f"file is not valid UTF-8 near line {line_number}"
                    ) from exc
                yield line_number, text.rstrip("\r\n")
        finally:
            if stream is not raw_handle:
                stream.close()


def sha256_file(path: Path, *, max_bytes: int) -> tuple[str, int]:
    """Hash a bounded regular file without following symlinks."""
    if max_bytes < 1 or max_bytes > HARD_MAX_BYTES:
        raise SafetyError("max_bytes is outside the hard safety bound")
    digest = hashlib.sha256()
    total = 0
    with _open_binary_nofollow(path) as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise SafetyError("file exceeds hash byte limit")
            digest.update(chunk)
    return digest.hexdigest(), total


def display_path(path: Path, index: int, mode: str) -> str:
    """Render a path using the requested disclosure level."""
    if mode == "redacted":
        return f"file_{index:04d}"
    if mode == "basename":
        return path.name
    if mode == "full":
        return str(path)
    raise SafetyError(f"unknown path display mode: {mode}")


def add_path_mode_argument(parser) -> None:
    parser.add_argument(
        "--path-mode",
        choices=("redacted", "basename", "full"),
        default="redacted",
        help="Path disclosure in output (default: redacted).",
    )


def print_json(payload: dict[str, Any]) -> None:
    """Print deterministic JSON with no non-finite values."""
    json.dump(payload, sys.stdout, indent=2, sort_keys=True, allow_nan=False)
    sys.stdout.write("\n")


def read_delimited_manifest(
    path: Path,
    *,
    delimiter_name: str,
    max_bytes: int,
    max_rows: int,
) -> tuple[list[str], list[dict[str, str]]]:
    """Read a bounded UTF-8 CSV/TSV manifest."""
    delimiter = "\t" if delimiter_name == "tsv" else ","
    lines = [
        line
        for _, line in iter_text_lines(
            path,
            max_bytes=max_bytes,
            max_records=max_rows + 1,
        )
    ]
    if not lines:
        raise SafetyError("manifest is empty")
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delimiter)
    if not reader.fieldnames:
        raise SafetyError("manifest has no header")
    raw_fieldnames = [field if field is not None else "" for field in reader.fieldnames]
    if any(field != field.strip() for field in raw_fieldnames):
        raise SafetyError("manifest column names must not have surrounding whitespace")
    fieldnames = raw_fieldnames
    if any(not field for field in fieldnames):
        raise SafetyError("manifest contains an empty column name")
    if len(set(fieldnames)) != len(fieldnames):
        raise SafetyError("manifest contains duplicate column names")
    if len(fieldnames) > 1_000:
        raise SafetyError("manifest exceeds the 1,000-column safety bound")

    rows: list[dict[str, str]] = []
    for row_number, row in enumerate(reader, start=2):
        if len(rows) >= max_rows:
            raise SafetyError("manifest row limit exceeded")
        if None in row:
            raise SafetyError(f"manifest row {row_number} has extra fields")
        normalized = {
            key.strip(): (value.strip() if value is not None else "")
            for key, value in row.items()
        }
        rows.append(normalized)
    return fieldnames, rows


def delimiter_from_path(path: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    return "csv" if path.suffix.lower() == ".csv" else "tsv"


def load_chrom_sizes(
    path: Path,
    *,
    max_bytes: int,
    max_records: int,
) -> tuple[dict[str, int], list[str]]:
    """Load a strict two-column chromosome-sizes file."""
    sizes: dict[str, int] = {}
    order: list[str] = []
    for line_number, line in iter_text_lines(
        path,
        max_bytes=max_bytes,
        max_records=max_records,
    ):
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 2:
            raise SafetyError(
                f"chromosome-sizes line {line_number} must have two tab-separated fields"
            )
        chrom, size_text = fields
        if not chrom or any(character.isspace() for character in chrom):
            raise SafetyError(f"invalid contig name at line {line_number}")
        if chrom in sizes:
            raise SafetyError(f"duplicate contig in chromosome sizes: {chrom}")
        if not _INTEGER.fullmatch(size_text):
            raise SafetyError(f"invalid contig size at line {line_number}")
        size = int(size_text)
        if size <= 0 or size > MAX_COORDINATE:
            raise SafetyError(f"contig size out of bounds at line {line_number}")
        sizes[chrom] = size
        order.append(chrom)
    if not sizes:
        raise SafetyError("chromosome-sizes file has no records")
    return sizes, order


def simple_yaml_mapping(
    path: Path,
    *,
    max_bytes: int,
    max_records: int = 10_000,
) -> dict[str, Any]:
    """Parse a conservative top-level scalar YAML mapping without PyYAML."""
    result: dict[str, Any] = {}
    for line_number, line in iter_text_lines(
        path,
        max_bytes=max_bytes,
        max_records=max_records,
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            continue
        if line[:1].isspace():
            raise SafetyError("nested YAML is not supported by the safe inspector")
        if ":" not in line:
            raise SafetyError(f"unsupported YAML at line {line_number}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not _YAML_KEY.fullmatch(key):
            raise SafetyError(f"invalid YAML key at line {line_number}")
        if key in result:
            raise SafetyError(f"duplicate YAML key: {key}")
        if any(marker in raw_value for marker in ("!", "&", "*", "{", "[", "|", ">")):
            raise SafetyError(f"complex YAML is not supported at line {line_number}")
        if not raw_value or raw_value in {"null", "Null", "NULL", "~"}:
            value: Any = None
        elif raw_value in {"true", "True", "TRUE"}:
            value = True
        elif raw_value in {"false", "False", "FALSE"}:
            value = False
        elif _INTEGER.fullmatch(raw_value):
            try:
                value = int(raw_value)
            except ValueError as exc:
                raise SafetyError("YAML integer exceeds the supported size") from exc
        elif _FLOAT.fullmatch(raw_value):
            value = float(raw_value)
            if not math.isfinite(value):
                raise SafetyError("YAML numeric metadata must be finite")
        elif (
            len(raw_value) >= 2
            and raw_value[0] == raw_value[-1]
            and raw_value[0] in {"'", '"'}
        ):
            value = raw_value[1:-1]
        else:
            value = raw_value
        result[key] = value
    return result


def fail_json(tool: str, exc: Exception) -> int:
    """Emit a bounded machine-readable error."""
    print_json(
        {
            "ok": False,
            "tool": tool,
            "error": type(exc).__name__,
            "message": str(exc)[:500],
        }
    )
    return 2
