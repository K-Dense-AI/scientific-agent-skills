#!/usr/bin/env python3
"""Shared bounded-I/O and validation helpers for the QuTiP CLIs."""

from __future__ import annotations

import json
import math
import os
import stat
import sys
import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any


QUTIP_VERSION = "5.3.1"
PINNED_INSTALL = 'uv pip install "qutip==5.3.1"'
DEFAULT_SEED = 20_260_723

MAX_INPUT_BYTES = 1024 * 1024
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_HILBERT_DIMENSION = 64
MAX_SUBSYSTEMS = 8
MAX_MODEL_OBJECTS = 32
MAX_TIME_POINTS = 5_001
MAX_TRAJECTORIES = 2_000
MAX_SWEEP_RUNS = 6
MAX_TOTAL_SWEEP_TRAJECTORIES = 4_000
MAX_FREQUENCY_POINTS = 10_001
MAX_ABS_FREQUENCY = 100_000.0
MAX_RATE = 10_000.0
MAX_TIME = 100_000.0


class CliError(ValueError):
    """An expected command-line, schema, or numerical validation error."""


def load_qutip() -> Any:
    """Import the exact supported QuTiP release on demand."""

    try:
        import qutip
    except ModuleNotFoundError as exc:
        if exc.name != "qutip":
            raise
        raise CliError(
            f"QuTiP {QUTIP_VERSION} is required; install it with "
            f"`{PINNED_INSTALL}`"
        ) from exc
    installed = str(getattr(qutip, "__version__", "unknown"))
    if installed != QUTIP_VERSION:
        raise CliError(
            f"this snapshot requires QuTiP {QUTIP_VERSION}, found {installed}; "
            f"install it with `{PINNED_INSTALL}`"
        )
    return qutip


def _reject_constant(value: str) -> None:
    raise CliError(f"non-standard JSON constant is not allowed: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CliError(f"duplicate JSON key is not allowed: {key!r}")
        result[key] = value
    return result


def checked_input_file(
    value: str | os.PathLike[str],
    *,
    suffixes: Iterable[str] = (".json",),
    max_bytes: int = MAX_INPUT_BYTES,
) -> Path:
    """Return a bounded regular local input, rejecting URLs and symlinks."""

    raw = os.fspath(value)
    if "://" in raw:
        raise CliError("network URLs are not accepted; provide a local file")
    path = Path(raw).expanduser()
    if path.is_symlink():
        raise CliError(f"input must not be a symlink: {path}")
    try:
        info = path.stat()
    except OSError as exc:
        raise CliError(f"cannot access input file {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise CliError(f"input is not a regular file: {path}")
    if info.st_size > max_bytes:
        raise CliError(f"input is {info.st_size} bytes; limit is {max_bytes}")
    allowed = {suffix.lower() for suffix in suffixes}
    if path.suffix.lower() not in allowed:
        raise CliError(f"input suffix must be one of: {', '.join(sorted(allowed))}")
    return path.resolve()


def checked_output_file(
    value: str | os.PathLike[str],
    *,
    force: bool = False,
) -> Path:
    """Validate an explicit local JSON destination without following symlinks."""

    raw = os.fspath(value)
    if "://" in raw:
        raise CliError("network URLs are not accepted as output paths")
    path = Path(raw).expanduser()
    if path.suffix.lower() != ".json":
        raise CliError("output path must end in .json")
    if path.is_symlink():
        raise CliError(f"output must not be a symlink: {path}")
    parent = path.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise CliError(f"output parent must be an existing regular directory: {parent}")
    if path.exists():
        if not path.is_file():
            raise CliError(f"output exists and is not a regular file: {path}")
        if not force:
            raise CliError(f"refusing to overwrite existing output: {path}")
    return parent.resolve() / path.name


def load_json_object(value: str | os.PathLike[str]) -> dict[str, Any]:
    """Load a bounded strict-JSON object from a local file."""

    path = checked_input_file(value)
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
        raise CliError(f"cannot read valid JSON from {path.name}: {exc}") from exc
    if not isinstance(document, dict):
        raise CliError("JSON root must be an object")
    return document


def validate_keys(
    value: Mapping[str, Any],
    *,
    allowed: Iterable[str],
    required: Iterable[str] = (),
    context: str = "object",
) -> None:
    """Reject unknown keys and report missing required keys."""

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
    """Validate a bounded integer, rejecting booleans."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise CliError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise CliError(f"{name} must be from {minimum} through {maximum}")
    return value


def finite_float(
    value: Any,
    *,
    name: str,
    minimum: float | None = None,
    maximum: float | None = None,
    minimum_inclusive: bool = True,
) -> float:
    """Validate a finite number with optional bounds."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CliError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise CliError(f"{name} must be finite")
    if minimum is not None:
        valid = result >= minimum if minimum_inclusive else result > minimum
        if not valid:
            qualifier = "at least" if minimum_inclusive else "greater than"
            raise CliError(f"{name} must be {qualifier} {minimum}")
    if maximum is not None and result > maximum:
        raise CliError(f"{name} must be no greater than {maximum}")
    return result


def bounded_dimensions(value: Any, *, name: str = "dims") -> list[int]:
    """Validate subsystem dimensions and their bounded product."""

    if not isinstance(value, list) or not value:
        raise CliError(f"{name} must be a non-empty JSON array")
    if len(value) > MAX_SUBSYSTEMS:
        raise CliError(f"{name} may contain at most {MAX_SUBSYSTEMS} subsystems")
    dimensions = [
        bounded_int(item, name=f"{name}[{index}]", minimum=1, maximum=64)
        for index, item in enumerate(value)
    ]
    product = math.prod(dimensions)
    if product > MAX_HILBERT_DIMENSION:
        raise CliError(
            f"{name} product is {product}; limit is {MAX_HILBERT_DIMENSION}"
        )
    return dimensions


def parse_csv_ints(
    value: str,
    *,
    name: str,
    minimum: int,
    maximum: int,
    max_items: int = MAX_SWEEP_RUNS,
) -> list[int]:
    """Parse a short comma-separated list of unique increasing integers."""

    pieces = [piece.strip() for piece in value.split(",")]
    if not pieces or any(not piece for piece in pieces):
        raise CliError(f"{name} must be a comma-separated integer list")
    if len(pieces) > max_items:
        raise CliError(f"{name} may contain at most {max_items} values")
    try:
        values = [int(piece, 10) for piece in pieces]
    except ValueError as exc:
        raise CliError(f"{name} must contain only base-10 integers") from exc
    checked = [
        bounded_int(item, name=name, minimum=minimum, maximum=maximum)
        for item in values
    ]
    if checked != sorted(set(checked)):
        raise CliError(f"{name} values must be unique and strictly increasing")
    return checked


def ensure_strictly_increasing(values: Sequence[float], *, name: str) -> None:
    """Require finite strictly increasing values."""

    if len(values) < 2:
        raise CliError(f"{name} must contain at least two values")
    previous = finite_float(values[0], name=f"{name}[0]")
    for index, value in enumerate(values[1:], start=1):
        current = finite_float(value, name=f"{name}[{index}]")
        if current <= previous:
            raise CliError(f"{name} must be strictly increasing")
        previous = current


def to_jsonable(value: Any) -> Any:
    """Convert trusted result scalars/arrays into strict-JSON-compatible values."""

    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CliError("report contains a non-finite float")
        return value
    if isinstance(value, complex):
        if not math.isfinite(value.real) or not math.isfinite(value.imag):
            raise CliError("report contains a non-finite complex value")
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "tolist"):
        return to_jsonable(value.tolist())
    if hasattr(value, "item"):
        return to_jsonable(value.item())
    return str(value)


def strict_json_bytes(document: Any) -> bytes:
    """Serialize deterministic RFC-compatible JSON with a size cap."""

    normalized = to_jsonable(document)
    try:
        payload = (
            json.dumps(
                normalized,
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


def emit_json(
    document: Any,
    *,
    output: str | os.PathLike[str] | None = None,
    force: bool = False,
) -> None:
    """Print strict JSON or atomically write a private local JSON file."""

    payload = strict_json_bytes(document)
    if output is None:
        print(payload.decode("utf-8"), end="")
        return
    destination = checked_output_file(output, force=force)
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
            raise CliError(f"refusing to overwrite existing output: {destination}")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def add_output_arguments(parser: Any) -> None:
    """Add common explicit JSON output controls to an ArgumentParser."""

    parser.add_argument(
        "--output",
        help="write strict JSON to this local .json path (default: stdout)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow replacing an existing regular output file",
    )


def run_cli(action: Callable[[], int | None]) -> int:
    """Run one CLI action with concise expected-error reporting."""

    try:
        status = action()
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0 if status is None else int(status)
