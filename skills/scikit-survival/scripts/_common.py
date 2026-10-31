#!/usr/bin/env python3
"""Shared, standard-library-first helpers for the bundled survival CLIs."""

from __future__ import annotations

import csv
import io
import json
import math
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Iterable


MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_ROWS = 20_000
MAX_FEATURES = 256
MAX_TIME_POINTS = 512
DEFAULT_SEED = 20_260_723
PINNED_INSTALL = (
    'uv pip install "scikit-survival==0.28.0" "scikit-learn==1.9.1" '
    '"numpy==2.5.1" "pandas==3.0.6" "scipy==1.18.1"'
)


class CliError(ValueError):
    """An expected command-line validation error."""


def bounded_int(minimum: int, maximum: int):
    """Return an argparse converter for a bounded integer."""

    def convert(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise CliError(f"expected an integer, got {value!r}") from exc
        if not minimum <= parsed <= maximum:
            raise CliError(
                f"expected an integer from {minimum} through {maximum}, got {parsed}"
            )
        return parsed

    return convert


def finite_float(value: str) -> float:
    """Parse a finite floating-point value."""

    try:
        parsed = float(value)
    except ValueError as exc:
        raise CliError(f"expected a number, got {value!r}") from exc
    if not math.isfinite(parsed):
        raise CliError("value must be finite")
    return parsed


def positive_float(value: str) -> float:
    """Parse a finite positive floating-point value."""

    parsed = finite_float(value)
    if parsed <= 0:
        raise CliError("value must be greater than zero")
    return parsed


def probability(value: str) -> float:
    """Parse a probability strictly between zero and one."""

    parsed = finite_float(value)
    if not 0 < parsed < 1:
        raise CliError("value must be strictly between zero and one")
    return parsed


def parse_names(value: str | None) -> list[str]:
    """Parse a comma-separated list of unique, non-empty column names."""

    if value is None:
        return []
    names = [item.strip() for item in value.split(",")]
    if not names or any(not item for item in names):
        raise CliError("column lists must contain non-empty comma-separated names")
    if len(names) != len(set(names)):
        raise CliError("column lists must not contain duplicates")
    if len(names) > MAX_FEATURES:
        raise CliError(f"at most {MAX_FEATURES} columns are allowed")
    return names


def parse_floats(value: str | None) -> list[float]:
    """Parse a comma-separated list of finite floating-point values."""

    if value is None:
        return []
    items = [item.strip() for item in value.split(",")]
    if not items or any(not item for item in items):
        raise CliError("expected non-empty comma-separated numbers")
    values = [finite_float(item) for item in items]
    if len(values) > MAX_TIME_POINTS:
        raise CliError(f"at most {MAX_TIME_POINTS} values are allowed")
    return values


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
        raise CliError(f"input is {info.st_size} bytes; limit is {max_bytes} bytes")
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

    destination = checked_output_file(path, suffixes={path.suffix.lower()}, force=force)
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


def _json_bytes(document: Any) -> bytes:
    """Serialize deterministic strict JSON."""

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

    payload = _json_bytes(document)
    if output is None:
        print(payload.decode("utf-8"), end="")
        return
    destination = checked_output_file(output, suffixes={".json"}, force=force)
    atomic_write_bytes(destination, payload, force=force)


def emit_text(
    text: str,
    *,
    output: str | os.PathLike[str] | None = None,
    force: bool = False,
) -> None:
    """Print text or write it atomically to Markdown."""

    payload = text.encode("utf-8")
    if len(payload) > MAX_REPORT_BYTES:
        raise CliError(
            f"report is {len(payload)} bytes; limit is {MAX_REPORT_BYTES} bytes"
        )
    if output is None:
        print(text, end="" if text.endswith("\n") else "\n")
        return
    destination = checked_output_file(output, suffixes={".md"}, force=force)
    atomic_write_bytes(destination, payload, force=force)


def load_json(value: str | os.PathLike[str]) -> Any:
    """Load bounded strict JSON from a local file."""

    path = checked_input_file(value, suffixes={".json"})

    def reject_constant(constant: str) -> None:
        raise CliError(f"non-standard JSON constant is not allowed: {constant}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, parse_constant=reject_constant)
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"cannot read valid JSON from {path.name}: {exc}") from exc


def read_csv(value: str | os.PathLike[str]):
    """Load a bounded local CSV with pandas, rejecting excessive dimensions."""

    path = checked_input_file(value, suffixes={".csv"})
    try:
        import pandas as pd
    except ImportError as exc:
        raise CliError(
            f"pandas is unavailable; install with `{PINNED_INSTALL}`"
        ) from exc
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            header = next(csv.reader(handle), [])
        if not header or any(not name.strip() for name in header):
            raise CliError("CSV column names must be non-empty")
        if len(header) != len(set(header)):
            raise CliError("CSV column names must be unique before parsing")
        frame = pd.read_csv(path, nrows=MAX_ROWS + 1)
    except Exception as exc:
        raise CliError(f"cannot parse CSV {path.name}: {exc}") from exc
    validate_frame_bounds(frame)
    return frame, path.name


def validate_frame_bounds(frame: Any) -> None:
    """Reject empty or oversized tabular inputs."""

    rows, columns = frame.shape
    if rows == 0:
        raise CliError("input contains no rows")
    if rows > MAX_ROWS:
        raise CliError(f"input has {rows} rows; limit is {MAX_ROWS}")
    if columns > MAX_FEATURES + 2:
        raise CliError(f"input has {columns} columns; limit is {MAX_FEATURES + 2}")
    if not frame.columns.is_unique:
        raise CliError("column names must be unique")


def normalize_binary_event(values: Any):
    """Return a strict boolean event vector from bool or 0/1 values."""

    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise CliError(
            f"scientific stack unavailable; install with `{PINNED_INSTALL}`"
        ) from exc
    series = pd.Series(values)
    if series.isna().any():
        raise CliError("event indicator contains missing values")
    if pd.api.types.is_bool_dtype(series.dtype):
        result = series.astype(bool).to_numpy()
    elif pd.api.types.is_numeric_dtype(series.dtype):
        numeric = pd.to_numeric(series, errors="raise").to_numpy(dtype=float)
        if not np.isfinite(numeric).all() or not np.isin(numeric, [0.0, 1.0]).all():
            raise CliError("event indicator must contain only boolean or 0/1 values")
        result = numeric.astype(bool)
    else:
        normalized = series.astype(str).str.strip().str.casefold()
        mapping = {"true": True, "false": False, "1": True, "0": False}
        if not normalized.isin(mapping).all():
            raise CliError(
                "event indicator strings must be one of true, false, 1, or 0"
            )
        result = normalized.map(mapping).to_numpy(dtype=bool)
    if not result.any():
        raise CliError("at least one observed event is required")
    return result


def normalize_positive_times(values: Any, *, label: str = "time"):
    """Return a finite, strictly positive float time vector."""

    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise CliError(
            f"scientific stack unavailable; install with `{PINNED_INSTALL}`"
        ) from exc
    try:
        times = np.asarray(pd.to_numeric(values, errors="raise"), dtype=float)
    except (TypeError, ValueError) as exc:
        raise CliError(f"{label} must contain only numeric values") from exc
    if times.ndim != 1:
        raise CliError(f"{label} must be one-dimensional")
    if not np.isfinite(times).all():
        raise CliError(f"{label} contains missing or non-finite values")
    if (times <= 0).any():
        raise CliError(f"{label} must be strictly positive")
    return times


def structured_survival(
    event: Any,
    time: Any,
    *,
    event_name: str = "event",
    time_name: str = "time",
):
    """Create scikit-survival's two-field structured outcome lazily."""

    if event_name == time_name:
        raise CliError("event and time field names must differ")
    try:
        from sksurv.util import Surv
    except ImportError as exc:
        raise CliError(
            f"scikit-survival is unavailable; install with `{PINNED_INSTALL}`"
        ) from exc
    return Surv.from_arrays(
        event=normalize_binary_event(event),
        time=normalize_positive_times(time),
        name_event=event_name,
        name_time=time_name,
    )


def atomic_save_npy(
    value: Any, output: str | os.PathLike[str], *, force: bool = False
) -> None:
    """Write a NumPy array with pickle disabled."""

    try:
        import numpy as np
    except ImportError as exc:
        raise CliError(
            f"NumPy is unavailable; install with `{PINNED_INSTALL}`"
        ) from exc
    destination = checked_output_file(output, suffixes={".npy"}, force=force)
    buffer = io.BytesIO()
    np.save(buffer, value, allow_pickle=False)
    atomic_write_bytes(destination, buffer.getvalue(), force=force)


def atomic_save_npz(
    arrays: dict[str, Any],
    output: str | os.PathLike[str],
    *,
    force: bool = False,
) -> None:
    """Write named NumPy arrays to a compressed archive without object arrays."""

    try:
        import numpy as np
    except ImportError as exc:
        raise CliError(
            f"NumPy is unavailable; install with `{PINNED_INSTALL}`"
        ) from exc
    if not arrays:
        raise CliError("at least one array is required")
    for name, value in arrays.items():
        array = np.asarray(value)
        if array.dtype.hasobject:
            raise CliError(f"array {name!r} has object dtype, which is not allowed")
    destination = checked_output_file(output, suffixes={".npz"}, force=force)
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    atomic_write_bytes(destination, buffer.getvalue(), force=force)


def synthetic_survival_frame(
    *, rows: int = 240, seed: int = DEFAULT_SEED
) -> tuple[Any, list[str], list[str]]:
    """Create deterministic, non-clinical right-censored tabular data."""

    if not 40 <= rows <= MAX_ROWS:
        raise CliError(f"synthetic rows must be between 40 and {MAX_ROWS}")
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise CliError(
            f"scientific stack unavailable; install with `{PINNED_INSTALL}`"
        ) from exc
    rng = np.random.default_rng(seed)
    x_linear = rng.normal(size=rows)
    x_noise = rng.normal(size=rows)
    segment = rng.choice(["alpha", "beta", "gamma"], size=rows, p=[0.4, 0.35, 0.25])
    segment_effect = np.select(
        [segment == "beta", segment == "gamma"], [0.35, -0.25], default=0.0
    )
    linear_predictor = 0.8 * x_linear + segment_effect
    event_time = rng.exponential(scale=8.0 * np.exp(-linear_predictor))
    censor_time = rng.exponential(scale=11.0, size=rows)
    event = event_time <= censor_time
    observed_time = np.minimum(event_time, censor_time) + 0.05
    x_linear = x_linear.astype(float)
    x_linear[::29] = np.nan
    segment = segment.astype(object)
    segment[::37] = np.nan
    frame = pd.DataFrame(
        {
            "event": event,
            "time": observed_time,
            "x_linear": x_linear,
            "x_noise": x_noise,
            "segment": segment,
        }
    )
    return frame, ["x_linear", "x_noise"], ["segment"]
