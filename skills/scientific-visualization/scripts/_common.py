#!/usr/bin/env python3
"""Shared, network-free safety helpers for visualization command-line tools."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 200 * 1024 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024


class CliError(ValueError):
    """An expected command-line validation error."""


def checked_input_file(
    value: str | os.PathLike[str],
    *,
    max_bytes: int = MAX_INPUT_BYTES,
) -> Path:
    """Return a bounded regular input file, rejecting symlinks."""
    path = Path(value).expanduser()
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
    return path.resolve()


def checked_output_file(
    value: str | os.PathLike[str],
    *,
    force: bool = False,
    mkdir: bool = False,
) -> Path:
    """Validate an explicit output path without following a destination symlink."""
    path = Path(value).expanduser()
    if path.name in {"", ".", ".."}:
        raise CliError("output must name a file")
    if path.is_symlink():
        raise CliError(f"output must not be a symlink: {path}")

    parent = path.parent
    if mkdir:
        parent.mkdir(parents=True, exist_ok=True)
    if not parent.exists() or not parent.is_dir():
        raise CliError(f"output parent directory does not exist: {parent}")
    if parent.is_symlink():
        raise CliError(f"output parent must not be a symlink: {parent}")

    if path.exists():
        if not path.is_file():
            raise CliError(f"output exists and is not a regular file: {path}")
        if not force:
            raise CliError(f"refusing to overwrite existing output: {path}")
    return parent.resolve() / path.name


def atomic_write_bytes(path: Path, payload: bytes, *, force: bool = False) -> None:
    """Write bytes through a same-directory temporary file."""
    destination = checked_output_file(path, force=force)
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
        if force:
            os.replace(temporary, destination)
        else:
            # A second existence check followed by replace still races another
            # writer. Linking a same-filesystem temporary refuses collisions.
            try:
                os.link(temporary, destination)
            except FileExistsError as exc:
                raise CliError(f"refusing to overwrite existing output: {destination}") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def emit_json(
    document: dict[str, Any],
    *,
    output: str | os.PathLike[str] | None = None,
    force: bool = False,
) -> None:
    """Print deterministic JSON or write it safely to an explicit file."""
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
    atomic_write_bytes(Path(output), payload, force=force)


def positive_int(value: str) -> int:
    """Argparse converter for strictly positive integers."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise CliError(f"expected an integer, got {value!r}") from exc
    if parsed <= 0:
        raise CliError("value must be greater than zero")
    return parsed


def positive_float(value: str) -> float:
    """Argparse converter for finite, strictly positive floats."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise CliError(f"expected a number, got {value!r}") from exc
    if not (parsed > 0 and parsed < float("inf")):
        raise CliError("value must be finite and greater than zero")
    return parsed
