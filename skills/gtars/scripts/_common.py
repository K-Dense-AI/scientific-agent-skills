#!/usr/bin/env python3
"""Shared dependency-free safety helpers for local Gtars skill CLIs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterator


HARD_MAX_BYTES = 8 * 1024**3
HARD_MAX_RECORDS = 10_000_000
HARD_MAX_FILES = 100_000
HARD_MAX_WORKERS = 256
HARD_MAX_LINE_BYTES = 1024 * 1024
MAX_COORDINATE = 2**32 - 1

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
_INTEGER = re.compile(r"^(?:0|[1-9][0-9]*)$")
_VALID_STRANDS = {"+", "-", "."}


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
        raise argparse.ArgumentTypeError(f"{label} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise argparse.ArgumentTypeError(
            f"{label} must be between {minimum} and {maximum}"
        )
    return parsed


def int_type(*, minimum: int = 0, maximum: int, label: str):
    """Return an argparse-compatible bounded integer parser."""

    def parse(value: str) -> int:
        return bounded_int(
            value,
            minimum=minimum,
            maximum=maximum,
            label=label,
        )

    return parse


def _reject_unsafe_text_path(raw: str) -> None:
    if not raw or "\x00" in raw:
        raise SafetyError("path must be nonempty and contain no NUL byte")
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
    """Yield bounded UTF-8 lines from a local plain-text or gzip file."""
    if not 1 <= max_bytes <= HARD_MAX_BYTES:
        raise SafetyError("max_bytes is outside the hard safety bound")
    if not 1 <= max_records <= HARD_MAX_RECORDS:
        raise SafetyError("max_records is outside the hard safety bound")
    if not 1 <= max_line_bytes <= HARD_MAX_LINE_BYTES:
        raise SafetyError("max_line_bytes is outside the hard safety bound")
    if path.stat().st_size > max_bytes:
        raise SafetyError("compressed/input file exceeds byte limit")

    expanded = 0
    with _open_binary_nofollow(path) as raw_handle:
        stream = (
            gzip.GzipFile(fileobj=raw_handle, mode="rb")
            if path.name.lower().endswith(".gz")
            else raw_handle
        )
        try:
            # Bound the read itself: iteration would allocate an entire malformed
            # or decompressed line before the length check could reject it.
            lines = iter(lambda: stream.readline(max_line_bytes + 1), b"")
            for line_number, raw_line in enumerate(lines, start=1):
                if line_number > max_records:
                    raise SafetyError("record limit exceeded")
                if len(raw_line) > max_line_bytes:
                    raise SafetyError(f"line {line_number} exceeds line-size limit")
                expanded += len(raw_line)
                if expanded > max_bytes:
                    raise SafetyError("expanded text exceeds byte limit")
                if b"\x00" in raw_line:
                    raise SafetyError(f"NUL byte found at line {line_number}")
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise SafetyError(
                        f"input is not UTF-8 near line {line_number}"
                    ) from exc
                yield line_number, line.rstrip("\r\n")
        finally:
            if stream is not raw_handle:
                stream.close()


def sha256_file(path: Path, *, max_bytes: int) -> tuple[str, int]:
    """Hash a bounded regular file without following symlinks."""
    if not 1 <= max_bytes <= HARD_MAX_BYTES:
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


def prefix_collision_count(prefix: Path) -> int:
    """Conservatively reserve a complete output prefix, including derived files."""
    collisions = 0
    with os.scandir(prefix.parent) as entries:
        for index, entry in enumerate(entries, start=1):
            if index > HARD_MAX_FILES:
                raise SafetyError("output directory exceeds file-count inspection limit")
            if entry.name.startswith(prefix.name):
                collisions += 1
    return collisions


def load_json(path: Path, *, max_bytes: int) -> Any:
    """Load strict bounded JSON, rejecting duplicate keys and non-finite values."""
    text = "\n".join(
        line
        for _, line in iter_text_lines(
            path,
            max_bytes=max_bytes,
            max_records=min(HARD_MAX_RECORDS, 1_000_000),
        )
    )

    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise SafetyError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value: str):
        raise SafetyError(f"non-finite JSON number is not allowed: {value}")

    try:
        return json.loads(
            text,
            object_pairs_hook=object_pairs,
            parse_constant=invalid_constant,
        )
    except json.JSONDecodeError as exc:
        raise SafetyError("invalid JSON") from exc


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
                f"chromosome-sizes line {line_number} must have two tab fields"
            )
        chrom, size_text = fields
        if (
            not chrom
            or any(character.isspace() or ord(character) < 32 for character in chrom)
            or chrom in sizes
        ):
            raise SafetyError(f"invalid or duplicate contig at line {line_number}")
        if not _INTEGER.fullmatch(size_text):
            raise SafetyError(f"invalid contig size at line {line_number}")
        size = int(size_text)
        if not 1 <= size <= MAX_COORDINATE:
            raise SafetyError(f"contig size out of bounds at line {line_number}")
        sizes[chrom] = size
        order.append(chrom)
    if not sizes:
        raise SafetyError("chromosome-sizes file contains no records")
    return sizes, order


def inspect_bed(
    path: Path,
    *,
    max_bytes: int,
    max_records: int,
    chrom_sizes: dict[str, int] | None = None,
    chrom_order: list[str] | None = None,
    max_examples: int = 10,
) -> dict[str, Any]:
    """Inspect BED-like records without returning genomic coordinates."""
    errors: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    examples: list[dict[str, int | str]] = []
    seen: set[tuple[str, int, int]] = set()
    max_end: dict[str, int] = {}
    records = 0
    skipped = 0
    contigs: set[str] = set()
    min_columns: int | None = None
    max_columns = 0
    unsorted = 0
    duplicates = 0
    overlap_observations = 0
    bed6_rows = 0
    previous_key: tuple[int | str, int, int] | None = None
    order_map = (
        {chrom: index for index, chrom in enumerate(chrom_order)}
        if chrom_order is not None
        else None
    )

    def issue(kind: str, code: str, line_number: int) -> None:
        target = errors if kind == "error" else warnings
        target[code] += 1
        if len(examples) < max_examples:
            examples.append({"severity": kind, "code": code, "line": line_number})

    for line_number, line in iter_text_lines(
        path,
        max_bytes=max_bytes,
        max_records=max_records,
    ):
        if not line:
            skipped += 1
            warnings["blank_line"] += 1
            continue
        if line.startswith(("#", "track", "browser")):
            skipped += 1
            continue
        fields = line.split("\t")
        if len(fields) < 3:
            issue("error", "fewer_than_three_columns", line_number)
            continue
        records += 1
        min_columns = len(fields) if min_columns is None else min(min_columns, len(fields))
        max_columns = max(max_columns, len(fields))
        chrom = fields[0]
        if not chrom or any(
            character.isspace() or ord(character) < 32 for character in chrom
        ):
            issue("error", "invalid_contig", line_number)
            continue
        if not _INTEGER.fullmatch(fields[1]) or not _INTEGER.fullmatch(fields[2]):
            issue("error", "non_unsigned_decimal_coordinate", line_number)
            continue
        start, end = int(fields[1]), int(fields[2])
        if start > MAX_COORDINATE or end > MAX_COORDINATE:
            issue("error", "coordinate_exceeds_gtars_u32", line_number)
            continue
        if end <= start:
            issue(
                "error",
                "zero_length_interval" if end == start else "end_before_start",
                line_number,
            )
            continue
        if chrom_sizes is not None:
            if chrom not in chrom_sizes:
                issue("error", "unknown_contig", line_number)
                continue
            if end > chrom_sizes[chrom]:
                issue("error", "end_beyond_contig", line_number)
                continue
        if len(fields) >= 6:
            bed6_rows += 1
            if fields[5] not in _VALID_STRANDS:
                issue("error", "invalid_bed6_strand", line_number)

        contigs.add(chrom)
        key = (chrom, start, end)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
        prior_end = max_end.get(chrom)
        if prior_end is not None and start < prior_end:
            overlap_observations += 1
        max_end[chrom] = max(end, prior_end or end)

        sort_key: tuple[int | str, int, int]
        if order_map is None:
            sort_key = (chrom, start, end)
        else:
            sort_key = (order_map[chrom], start, end)
        if previous_key is not None and sort_key < previous_key:
            unsorted += 1
        previous_key = sort_key

    if duplicates:
        warnings["duplicate_intervals"] = duplicates
    if overlap_observations:
        warnings["overlapping_intervals"] = overlap_observations
    if unsorted:
        warnings["out_of_order_records"] = unsorted
    if chrom_sizes is None:
        warnings["bounds_not_checked_without_chrom_sizes"] += 1

    digest, size = sha256_file(path, max_bytes=max_bytes)
    return {
        "sha256": digest,
        "size_bytes": size,
        "records": records,
        "skipped_records": skipped,
        "contig_count": len(contigs),
        "minimum_columns": min_columns,
        "maximum_columns": max_columns if records else None,
        "bed6_or_wider_rows": bed6_rows,
        "duplicate_intervals": duplicates,
        "overlap_observations": overlap_observations,
        "out_of_order_records": unsorted,
        "errors": dict(sorted(errors.items())),
        "warnings": dict(sorted(warnings.items())),
        "issue_examples": examples,
    }


def add_path_mode_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--path-mode",
        choices=("redacted", "basename", "full"),
        default="redacted",
        help="Path disclosure in output (default: redacted).",
    )


def display_path(path: Path, index: int, mode: str) -> str:
    """Render a path using the requested disclosure level."""
    if mode == "redacted":
        return f"file_{index:04d}"
    if mode == "basename":
        return path.name
    if mode == "full":
        return str(path)
    raise SafetyError(f"unknown path mode: {mode}")


def print_json(payload: dict[str, Any]) -> None:
    """Print deterministic JSON with no non-finite values."""
    json.dump(payload, sys.stdout, indent=2, sort_keys=True, allow_nan=False)
    sys.stdout.write("\n")


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
