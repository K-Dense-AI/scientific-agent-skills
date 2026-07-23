#!/usr/bin/env python3
"""Shared bounded-I/O and statistical helpers for the SimPy CLIs."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from statistics import fmean, stdev
from typing import Any


SIMPY_VERSION = "4.1.2"
PINNED_INSTALL = 'uv pip install "simpy==4.1.2"'
DEFAULT_SEED = 20_260_723
MAX_CONFIG_BYTES = 64 * 1024
MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_SIM_TIME = 1_000_000.0
MAX_EVENTS = 1_000_000
MAX_ENTITIES = 100_000
MAX_REPLICATIONS = 1_000
MAX_QUEUE_CAPACITY = 100_000
MAX_TRACE_RECORDS = 1_000_000


class CliError(ValueError):
    """An expected validation or command-line error."""


def load_simpy(*, required: bool = True) -> Any | None:
    """Import SimPy on demand or raise a concise installation error."""

    try:
        import simpy
    except ModuleNotFoundError as exc:
        if exc.name != "simpy":
            raise
        if not required:
            return None
        raise CliError(
            f"SimPy {SIMPY_VERSION} is required for simulation execution; "
            f"install it with `{PINNED_INSTALL}`"
        ) from exc
    return simpy


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
    suffixes: Iterable[str],
    max_bytes: int = MAX_INPUT_BYTES,
) -> Path:
    """Return a bounded regular local file, rejecting URLs and symlinks."""

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
    suffixes: Iterable[str],
    force: bool = False,
) -> Path:
    """Validate an explicit local output without following symlinks."""

    raw = os.fspath(value)
    if "://" in raw:
        raise CliError("network URLs are not accepted as output paths")
    path = Path(raw).expanduser()
    if path.name in {"", ".", ".."}:
        raise CliError("output must name a file")
    if path.is_symlink():
        raise CliError(f"output must not be a symlink: {path}")
    allowed = {suffix.lower() for suffix in suffixes}
    if path.suffix.lower() not in allowed:
        raise CliError(f"output suffix must be one of: {', '.join(sorted(allowed))}")
    parent = path.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise CliError(f"output parent must be an existing regular directory: {parent}")
    if path.exists():
        if not path.is_file():
            raise CliError(f"output exists and is not a regular file: {path}")
        if not force:
            raise CliError(f"refusing to overwrite existing output: {path}")
    return parent.resolve() / path.name


def atomic_write_bytes(path: Path, payload: bytes, *, force: bool = False) -> None:
    """Write bytes through a private same-directory temporary file."""

    destination = checked_output_file(path, suffixes={path.suffix}, force=force)
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
            raise CliError(f"refusing to overwrite existing output: {destination}")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


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
            f"report is {len(payload)} bytes; limit is {MAX_REPORT_BYTES} bytes"
        )
    return payload


def emit_json(
    document: Any,
    *,
    output: str | os.PathLike[str] | None = None,
    force: bool = False,
) -> None:
    """Print deterministic JSON or write it atomically."""

    payload = strict_json_bytes(document)
    if output is None:
        print(payload.decode("utf-8"), end="")
        return
    destination = checked_output_file(output, suffixes={".json"}, force=force)
    atomic_write_bytes(destination, payload, force=force)


def emit_text(
    text: str,
    *,
    output: str | os.PathLike[str],
    suffixes: Iterable[str],
    force: bool = False,
) -> Path:
    """Write bounded text atomically and return its destination."""

    payload = text.encode("utf-8")
    if len(payload) > MAX_REPORT_BYTES:
        raise CliError(
            f"output is {len(payload)} bytes; limit is {MAX_REPORT_BYTES} bytes"
        )
    destination = checked_output_file(output, suffixes=suffixes, force=force)
    atomic_write_bytes(destination, payload, force=force)
    return destination


def load_json_object(value: str | os.PathLike[str]) -> dict[str, Any]:
    """Load a bounded strict JSON object from a local file."""

    path = checked_input_file(
        value, suffixes={".json"}, max_bytes=MAX_CONFIG_BYTES
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
        raise CliError(f"cannot read valid JSON from {path.name}: {exc}") from exc
    if not isinstance(document, dict):
        raise CliError("configuration root must be a JSON object")
    return document


def parse_json_line(line: str, *, line_number: int) -> dict[str, Any]:
    """Parse one strict JSON object from a JSON Lines input."""

    try:
        value = json.loads(
            line,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except CliError:
        raise
    except json.JSONDecodeError as exc:
        raise CliError(f"invalid JSON on line {line_number}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise CliError(f"line {line_number} must contain a JSON object")
    return value


def validate_keys(
    value: Mapping[str, Any],
    *,
    allowed: Iterable[str],
    required: Iterable[str] = (),
    context: str = "configuration",
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


def integer(
    value: Any,
    *,
    name: str,
    minimum: int,
    maximum: int,
) -> int:
    """Validate a bounded JSON integer, rejecting booleans."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise CliError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise CliError(f"{name} must be from {minimum} through {maximum}")
    return value


def finite_number(
    value: Any,
    *,
    name: str,
    minimum: float | None = None,
    maximum: float | None = None,
    minimum_inclusive: bool = True,
) -> float:
    """Validate a finite JSON number with optional bounds."""

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


def derive_seed(base_seed: int, replication: int, stream: str) -> int:
    """Derive a stable 64-bit seed for one replication and random stream."""

    integer(base_seed, name="base_seed", minimum=0, maximum=2**63 - 1)
    integer(
        replication,
        name="replication",
        minimum=0,
        maximum=MAX_REPLICATIONS - 1,
    )
    if not stream or len(stream) > 64 or not stream.isascii():
        raise CliError("stream label must be 1-64 ASCII characters")
    payload = f"simpy-skill-v1|{base_seed}|{replication}|{stream}".encode("ascii")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """Evaluate the continued fraction used by regularized incomplete beta."""

    maximum_iterations = 250
    epsilon = 3.0e-14
    minimum = 1.0e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < minimum:
        d = minimum
    d = 1.0 / d
    result = d
    for iteration in range(1, maximum_iterations + 1):
        doubled = 2 * iteration
        coefficient = (
            iteration
            * (b - iteration)
            * x
            / ((qam + doubled) * (a + doubled))
        )
        d = 1.0 + coefficient * d
        if abs(d) < minimum:
            d = minimum
        c = 1.0 + coefficient / c
        if abs(c) < minimum:
            c = minimum
        d = 1.0 / d
        result *= d * c
        coefficient = -(
            (a + iteration)
            * (qab + iteration)
            * x
            / ((a + doubled) * (qap + doubled))
        )
        d = 1.0 + coefficient * d
        if abs(d) < minimum:
            d = minimum
        c = 1.0 + coefficient / c
        if abs(c) < minimum:
            c = minimum
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) <= epsilon:
            return result
    raise CliError("Student-t calculation did not converge")


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    if not 0.0 <= x <= 1.0:
        raise CliError("internal beta argument is outside [0, 1]")
    if x in {0.0, 1.0}:
        return x
    log_term = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    term = math.exp(log_term)
    if x < (a + 1.0) / (a + b + 2.0):
        return term * _beta_continued_fraction(a, b, x) / a
    return 1.0 - term * _beta_continued_fraction(b, a, 1.0 - x) / b


def student_t_cdf(value: float, degrees_of_freedom: int) -> float:
    """Return the Student-t CDF using the incomplete-beta identity."""

    integer(
        degrees_of_freedom,
        name="degrees_of_freedom",
        minimum=1,
        maximum=MAX_REPLICATIONS - 1,
    )
    if not math.isfinite(value):
        return 0.0 if value < 0 else 1.0
    if value == 0:
        return 0.5
    ratio = degrees_of_freedom / (degrees_of_freedom + value * value)
    tail = 0.5 * _regularized_incomplete_beta(
        degrees_of_freedom / 2.0, 0.5, ratio
    )
    return 1.0 - tail if value > 0 else tail


def student_t_quantile(probability: float, degrees_of_freedom: int) -> float:
    """Numerically invert the Student-t CDF for 0.5 < p < 1."""

    if not 0.5 < probability < 1.0:
        raise CliError("Student-t probability must be between 0.5 and 1")
    integer(
        degrees_of_freedom,
        name="degrees_of_freedom",
        minimum=1,
        maximum=MAX_REPLICATIONS - 1,
    )
    lower = 0.0
    upper = 1.0
    while student_t_cdf(upper, degrees_of_freedom) < probability:
        upper *= 2.0
        if upper > 1_000_000:
            raise CliError("Student-t quantile could not be bracketed")
    for _ in range(90):
        midpoint = (lower + upper) / 2.0
        if student_t_cdf(midpoint, degrees_of_freedom) < probability:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


def mean_confidence_interval(
    values: Iterable[float], *, confidence: float = 0.95
) -> dict[str, float | int]:
    """Return a two-sided Student-t interval across independent estimates."""

    observations = [float(value) for value in values]
    if len(observations) < 2:
        raise CliError(
            "a confidence interval requires at least two independent replications"
        )
    if len(observations) > MAX_REPLICATIONS:
        raise CliError(f"at most {MAX_REPLICATIONS} replications are allowed")
    if any(not math.isfinite(value) for value in observations):
        raise CliError("confidence-interval observations must be finite")
    confidence = finite_number(
        confidence,
        name="confidence",
        minimum=0.50,
        maximum=0.999,
        minimum_inclusive=False,
    )
    count = len(observations)
    estimate = fmean(observations)
    standard_deviation = stdev(observations)
    standard_error = standard_deviation / math.sqrt(count)
    critical = student_t_quantile(
        0.5 + confidence / 2.0, degrees_of_freedom=count - 1
    )
    half_width = critical * standard_error
    return {
        "confidence": confidence,
        "degrees_of_freedom": count - 1,
        "half_width": half_width,
        "lower": estimate - half_width,
        "mean": estimate,
        "replications": count,
        "standard_deviation": standard_deviation,
        "standard_error": standard_error,
        "upper": estimate + half_width,
    }
