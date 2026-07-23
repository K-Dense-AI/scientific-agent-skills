#!/usr/bin/env python3
"""Shared safety utilities for the bundled OMERO client helpers."""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import tempfile
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from itertools import islice
from pathlib import Path
from typing import Any


NAMED_ENV_VARS = (
    "OMERO_HOST",
    "OMERO_PORT",
    "OMERO_USER",
    "OMERO_PASSWORD",
    "OMERO_SESSION_KEY",
    "OMERO_SECURE",
)

TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_VALUES = frozenset({"0", "false", "no", "off"})


class ConfigError(ValueError):
    """Raised when named OMERO configuration is invalid."""


class OutputPathError(ValueError):
    """Raised when an output path is unsafe or ambiguous."""


class DependencyError(RuntimeError):
    """Raised when an optional runtime dependency is unavailable."""


@dataclass(frozen=True)
class ConnectionConfig:
    """Validated connection material. Never serialize this dataclass."""

    host: str
    port: int
    secure: bool
    username: str | None
    password: str | None
    session_key: str | None

    @property
    def authentication_mode(self) -> str:
        if self.session_key:
            return "session_key"
        if self.username and self.password:
            return "username_password"
        return "missing"


@dataclass(frozen=True)
class BoundedResult:
    """A bounded materialization with explicit truncation state."""

    items: list[Any]
    truncated: bool


def parse_bool(value: str, *, variable: str) -> bool:
    """Parse a strict environment boolean."""

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    allowed = ", ".join(sorted(TRUE_VALUES | FALSE_VALUES))
    raise ConfigError(f"{variable} must be one of: {allowed}")


def validate_host(value: str) -> str:
    """Validate a hostname without resolving or connecting."""

    host = value.strip()
    if not host:
        raise ConfigError("OMERO_HOST is required")
    if "\x00" in host:
        raise ConfigError("OMERO_HOST contains a NUL byte")
    if any(character.isspace() for character in host):
        raise ConfigError("OMERO_HOST must not contain whitespace")
    if "://" in host:
        raise ConfigError("OMERO_HOST must be a hostname, not a URL")
    if "/" in host or "\\" in host:
        raise ConfigError("OMERO_HOST must not contain a path")
    if host.startswith("-"):
        raise ConfigError("OMERO_HOST must not begin with '-'")
    if len(host) > 255:
        raise ConfigError("OMERO_HOST is too long")
    return host


def parse_port(value: str | None) -> int:
    """Parse OMERO_PORT with the documented SSL-router default."""

    raw = "4064" if value is None or not value.strip() else value.strip()
    try:
        port = int(raw, 10)
    except ValueError as exc:
        raise ConfigError("OMERO_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ConfigError("OMERO_PORT must be between 1 and 65535")
    return port


def load_connection_config(
    *,
    require_auth: bool,
    environ: Mapping[str, str] | None = None,
) -> ConnectionConfig:
    """Read only the named OMERO_* variables and validate them."""

    source = os.environ if environ is None else environ
    values = {name: source.get(name) for name in NAMED_ENV_VARS}

    host = validate_host(values["OMERO_HOST"] or "")
    port = parse_port(values["OMERO_PORT"])
    secure_raw = values["OMERO_SECURE"]
    secure = True if secure_raw is None else parse_bool(
        secure_raw,
        variable="OMERO_SECURE",
    )

    username = (values["OMERO_USER"] or "").strip() or None
    password = values["OMERO_PASSWORD"]
    if password == "":
        password = None
    session_key = (values["OMERO_SESSION_KEY"] or "").strip() or None

    # An explicit session is the sole credential in use. Stale password
    # variables are deliberately ignored and never surfaced.
    if session_key:
        username = None
        password = None
    elif bool(username) != bool(password):
        raise ConfigError(
            "OMERO_USER and OMERO_PASSWORD must be set together, "
            "or use OMERO_SESSION_KEY"
        )

    config = ConnectionConfig(
        host=host,
        port=port,
        secure=secure,
        username=username,
        password=password,
        session_key=session_key,
    )
    if require_auth and config.authentication_mode == "missing":
        raise ConfigError(
            "Authentication requires OMERO_SESSION_KEY or both "
            "OMERO_USER and OMERO_PASSWORD"
        )
    return config


def config_summary(
    config: ConnectionConfig,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a credential-safe configuration summary."""

    source = os.environ if environ is None else environ
    return {
        "endpoint": {
            "host": config.host,
            "port": config.port,
            "secure_transport": config.secure,
        },
        "authentication_mode": config.authentication_mode,
        "named_variables_present": {
            name: bool(source.get(name))
            for name in NAMED_ENV_VARS
        },
        "credential_values_included": False,
    }


def require_secure_transport(
    config: ConnectionConfig,
    *,
    allow_insecure_transport: bool,
) -> None:
    """Refuse post-login cleartext unless explicitly overridden."""

    if not config.secure and not allow_insecure_transport:
        raise ConfigError(
            "OMERO_SECURE is false; pass --allow-insecure-transport only "
            "after reviewing the server transport policy"
        )


@contextlib.contextmanager
def gateway_session(
    config: ConnectionConfig,
    *,
    allow_insecure_transport: bool,
) -> Iterator[Any]:
    """Open and always close a BlitzGateway connection."""

    require_secure_transport(
        config,
        allow_insecure_transport=allow_insecure_transport,
    )
    if config.authentication_mode == "missing":
        raise ConfigError("Remote execution requires authentication")

    try:
        from omero.gateway import BlitzGateway
    except ImportError as exc:
        raise DependencyError(
            "omero-py and a matching ZeroC IcePy wheel are required "
            "for --execute"
        ) from exc

    connection = None
    try:
        if config.session_key:
            connection = BlitzGateway(
                host=config.host,
                port=config.port,
                secure=config.secure,
            )
            connected = connection.connect(sUuid=config.session_key)
        else:
            connection = BlitzGateway(
                config.username,
                config.password,
                host=config.host,
                port=config.port,
                secure=config.secure,
            )
            connected = connection.connect()

        if not connected:
            raise RuntimeError("OMERO connection failed")
        yield connection
    finally:
        if connection is not None:
            with contextlib.suppress(Exception):
                connection.close()


def take_bounded(iterable: Iterable[Any], limit: int) -> BoundedResult:
    """Materialize at most limit values and detect one additional value."""

    if limit < 0:
        raise ValueError("limit must be non-negative")
    items = list(islice(iterable, limit + 1))
    return BoundedResult(items=items[:limit], truncated=len(items) > limit)


def unwrap_omero(value: Any) -> Any:
    """Unwrap a generated OMERO rtype when possible."""

    if value is None:
        return None
    getter = getattr(value, "getValue", None)
    if callable(getter):
        return getter()
    if hasattr(value, "val"):
        return value.val
    return value


def json_safe(
    value: Any,
    *,
    max_string_length: int = 512,
    max_collection_length: int = 1000,
    _depth: int = 0,
) -> Any:
    """Convert known values to bounded JSON without unsafe repr output."""

    if _depth > 8:
        return {"omitted": "maximum nesting depth exceeded"}
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return {"non_finite_float": str(value)}
    if isinstance(value, str):
        if len(value) <= max_string_length:
            return value
        return value[:max_string_length] + "…[truncated]"
    if isinstance(value, bytes):
        return {"bytes_omitted": len(value)}
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    unwrapped = unwrap_omero(value)
    if unwrapped is not value:
        return json_safe(
            unwrapped,
            max_string_length=max_string_length,
            max_collection_length=max_collection_length,
            _depth=_depth + 1,
        )
    if isinstance(value, Mapping):
        total_items = len(value)
        converted = {
            str(key)[:max_string_length]: json_safe(
                item,
                max_string_length=max_string_length,
                max_collection_length=max_collection_length,
                _depth=_depth + 1,
            )
            for key, item in islice(
                value.items(),
                max_collection_length,
            )
        }
        if total_items > max_collection_length:
            converted["__truncated_items__"] = (
                total_items - max_collection_length
            )
        return converted
    if isinstance(value, (list, tuple)):
        converted = [
            json_safe(
                item,
                max_string_length=max_string_length,
                max_collection_length=max_collection_length,
                _depth=_depth + 1,
            )
            for item in value[:max_collection_length]
        ]
        if len(value) > max_collection_length:
            converted.append(
                {
                    "truncated_items": (
                        len(value) - max_collection_length
                    )
                }
            )
        return converted
    return {"unsupported_type": type(value).__name__}


def positive_int(value: str) -> int:
    """Argparse-compatible positive integer parser."""

    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise ValueError("expected an integer") from exc
    if parsed <= 0:
        raise ValueError("expected a positive integer")
    return parsed


def bounded_int(
    value: int,
    *,
    name: str,
    minimum: int,
    maximum: int,
) -> int:
    """Validate an integer bound with a stable message."""

    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return value


def atomic_write_json(
    output: str | os.PathLike[str],
    payload: Any,
    *,
    overwrite: bool,
) -> Path:
    """Atomically write JSON to an existing directory with mode 0600."""

    requested = Path(output).expanduser()
    if requested.name in {"", ".", ".."}:
        raise OutputPathError("output must name a JSON file")
    if requested.suffix.lower() != ".json":
        raise OutputPathError("output filename must end in .json")
    if requested.is_symlink():
        raise OutputPathError("refusing to write through an output symlink")

    try:
        parent = requested.parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise OutputPathError("output parent directory does not exist") from exc
    if not parent.is_dir():
        raise OutputPathError("output parent is not a directory")

    target = parent / requested.name
    if target.is_symlink():
        raise OutputPathError("refusing to replace an output symlink")
    if target.exists():
        if not target.is_file():
            raise OutputPathError("output exists and is not a regular file")
        if not overwrite:
            raise FileExistsError(f"output already exists: {target}")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            json.dump(
                payload,
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()
        raise
    return target


def emit_json(
    payload: Any,
    *,
    output: str | os.PathLike[str] | None,
    overwrite: bool,
) -> Path | None:
    """Write to a safe file or emit bounded JSON to stdout."""

    if output is None:
        print(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
        )
        return None
    return atomic_write_json(output, payload, overwrite=overwrite)


def scrubbed_error(error: BaseException) -> str:
    """Describe an error without serializing its potentially sensitive text."""

    return (
        f"{type(error).__name__}: operation failed; "
        "credential values were not logged"
    )


def main(argv: list[str] | None = None) -> int:
    """Expose module documentation without loading optional OMERO packages."""

    parser = argparse.ArgumentParser(
        description=(
            "Shared local safety utilities for the bundled OMERO helpers. "
            "This module does not connect to OMERO when invoked directly."
        )
    )
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
