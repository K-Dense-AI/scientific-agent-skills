#!/usr/bin/env python3
"""Shared, standard-library-first helpers for the bundled pymatgen CLIs."""

from __future__ import annotations

import hashlib
import json
import math
import os
import warnings
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


PYMATGEN_VERSION = "2026.9.24"
PYMATGEN_CORE_VERSION = "2026.9.23"
MP_API_VERSION = "0.46.5"
DEFAULT_MAX_INPUT_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_OUTPUT_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_SITES = 10_000
ABSOLUTE_MAX_INPUT_BYTES = 512 * 1024 * 1024
ABSOLUTE_MAX_OUTPUT_BYTES = 100 * 1024 * 1024
ABSOLUTE_MAX_SITES = 100_000
ABSOLUTE_MAX_PAIRWISE_SITES = 1_000


class CliError(ValueError):
    """A user-facing validation or safety error."""


def reject_url(value: str, label: str = "path") -> None:
    """Reject URL-like values where a local path is required."""
    if "://" in value:
        raise CliError(f"{label} must be a local path, not a URL")


def checked_input_file(
    value: str | Path,
    *,
    max_bytes: int = DEFAULT_MAX_INPUT_BYTES,
) -> Path:
    """Return a resolved, bounded regular input file."""
    if max_bytes > ABSOLUTE_MAX_INPUT_BYTES:
        raise CliError(
            f"input byte limit may not exceed {ABSOLUTE_MAX_INPUT_BYTES}"
        )
    raw = str(value)
    reject_url(raw, "input")
    path = Path(raw).expanduser()
    if path.is_symlink():
        raise CliError("symbolic-link inputs are not accepted")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CliError("input file does not exist or cannot be resolved") from exc
    if not resolved.is_file():
        raise CliError("input path is not a regular file")
    size = resolved.stat().st_size
    if size > max_bytes:
        raise CliError(f"input exceeds the {max_bytes}-byte limit")
    return resolved


def checked_output_file(
    value: str | Path,
    *,
    input_paths: tuple[Path, ...] = (),
) -> Path:
    """Validate a new output path without creating or overwriting it."""
    raw = str(value)
    reject_url(raw, "output")
    path = Path(raw).expanduser()
    if ".." in path.parts:
        raise CliError("output path may not contain '..'")
    if path.exists() or path.is_symlink():
        raise CliError("output already exists; choose a new path")
    parent = path.parent.resolve(strict=False)
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise CliError("output parent must be an existing, non-symlink directory")
    resolved = path.resolve(strict=False)
    for input_path in input_paths:
        if resolved == input_path.resolve(strict=True):
            raise CliError("output may not overwrite an input")
    return resolved


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CliError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise CliError(f"non-finite JSON number is not allowed: {value}")


def load_strict_json(
    value: str | Path,
    *,
    max_bytes: int = DEFAULT_MAX_INPUT_BYTES,
) -> tuple[Any, Path]:
    """Load bounded JSON while rejecting duplicate keys and NaN/Infinity."""
    path = checked_input_file(value, max_bytes=max_bytes)
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise CliError("JSON input must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise CliError(f"invalid JSON at line {exc.lineno}, column {exc.colno}") from exc
    return payload, path


def json_text(payload: Any, *, pretty: bool = True) -> str:
    """Serialize strict JSON with stable ordering."""
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=True,
    )


def emit_json(payload: Any) -> None:
    """Print a strict JSON report."""
    print(json_text(payload))


def write_text_new(
    path: Path,
    text: str,
    *,
    max_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> None:
    """Create a UTF-8 text file exclusively after enforcing a byte bound."""
    if max_bytes > ABSOLUTE_MAX_OUTPUT_BYTES:
        raise CliError(
            f"output byte limit may not exceed {ABSOLUTE_MAX_OUTPUT_BYTES}"
        )
    encoded = text.encode("utf-8")
    if len(encoded) > max_bytes:
        raise CliError(f"output exceeds the {max_bytes}-byte limit")
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            if text and not text.endswith("\n"):
                handle.write("\n")
    except FileExistsError as exc:
        raise CliError("output appeared concurrently; nothing was overwritten") from exc


def write_json_new(
    path: Path,
    payload: Any,
    *,
    max_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> None:
    """Create a strict JSON file exclusively."""
    write_text_new(path, json_text(payload), max_bytes=max_bytes)


def finite_float(value: Any, label: str) -> float:
    """Parse a finite float."""
    if isinstance(value, bool):
        raise CliError(f"{label} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CliError(f"{label} must be a finite number") from exc
    if not math.isfinite(number):
        raise CliError(f"{label} must be finite")
    return number


def positive_int(value: str) -> int:
    """Argparse converter for positive integers."""
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError("must be an integer") from exc
    if number < 1:
        raise ValueError("must be at least 1")
    return number


def package_versions(names: tuple[str, ...]) -> dict[str, str | None]:
    """Return installed distribution versions without importing packages."""
    result: dict[str, str | None] = {}
    for name in names:
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = None
    return result


def sha256_file(path: Path, *, chunk_bytes: int = 1024 * 1024) -> str:
    """Hash a local file without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_bytes):
            digest.update(chunk)
    return digest.hexdigest()


def structure_oxidation_summary(structure: Any) -> dict[str, Any]:
    """Summarize oxidation-state decoration without guessing states."""
    decorated = 0
    total = 0
    values: set[float] = set()
    for site in structure:
        for specie in site.species:
            total += 1
            if hasattr(specie, "oxi_state"):
                decorated += 1
                values.add(float(specie.oxi_state))
    return {
        "decorated_species_components": decorated,
        "species_components": total,
        "all_decorated": bool(total) and decorated == total,
        "partially_decorated": 0 < decorated < total,
        "oxidation_states": sorted(values),
        "guessed": False,
    }


def load_structure_json(path: Path, *, max_bytes: int, max_sites: int) -> Any:
    """Read plain Structure JSON without allowing nested dynamic MSON objects."""
    from pymatgen.core import Structure

    payload, _ = load_strict_json(path, max_bytes=max_bytes)
    if not isinstance(payload, dict):
        raise CliError("structure JSON must be an object")
    if payload.get("@module", "pymatgen.core.structure") != "pymatgen.core.structure":
        raise CliError("structure JSON has an unsupported @module")
    if payload.get("@class", "Structure") not in {"Structure", "IStructure"}:
        raise CliError("structure JSON must describe Structure or IStructure")
    sites = payload.get("sites")
    if not isinstance(sites, list) or not sites or len(sites) > max_sites:
        raise CliError("structure JSON must contain a non-empty, bounded sites array")
    lattice = payload.get("lattice")
    if not isinstance(lattice, dict) or "matrix" not in lattice:
        raise CliError("structure JSON requires a lattice matrix")

    # PeriodicSite.from_dict invokes MontyDecoder on site properties. Only plain
    # JSON values are accepted there; metadata at the root is checked above.
    pending = [(value, 1) for key, value in payload.items() if not key.startswith("@")]
    visited = 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if depth > 30 or visited > 1_000_000:
            raise CliError("structure JSON exceeds nesting or value-count limits")
        if isinstance(value, dict):
            if any(key.startswith("@") for key in value):
                raise CliError("nested MSON metadata is not accepted in structure JSON")
            pending.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
        elif isinstance(value, float) and not math.isfinite(value):
            raise CliError("structure JSON contains a non-finite number")
    try:
        return Structure.from_dict(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise CliError(f"invalid Structure JSON: {exc}") from exc


def load_structure(
    value: str | Path,
    *,
    structure_index: int = 0,
    max_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    max_sites: int = DEFAULT_MAX_SITES,
) -> tuple[Any, Path, dict[str, Any]]:
    """Load one bounded structure and preserve all parser warnings."""
    if max_sites > ABSOLUTE_MAX_SITES:
        raise CliError(f"site limit may not exceed {ABSOLUTE_MAX_SITES}")
    path = checked_input_file(value, max_bytes=max_bytes)
    warning_messages: list[str] = []
    parser_messages: list[str] = []
    structure_count = 1
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            lower_name = path.name.casefold()
            if ".yaml" in lower_name or ".yml" in lower_name:
                raise CliError("bundled intake does not accept YAML; supply CIF or plain Structure JSON")
            if ".json" in lower_name or ".mson" in lower_name:
                if path.suffix.casefold() not in {".json", ".mson"}:
                    raise CliError("decompress Structure JSON to a bounded plain .json file first")
                if structure_index != 0:
                    raise CliError("JSON intake exposes one structure; use index 0")
                structure = load_structure_json(path, max_bytes=max_bytes, max_sites=max_sites)
            elif lower_name.endswith((".cif", ".cif.gz", ".cif.bz2", ".mcif")):
                from pymatgen.io.cif import CifParser

                parser = CifParser(path)
                structures = parser.parse_structures(
                    primitive=False,
                    check_occu=True,
                    on_error="raise",
                )
                parser_messages = [str(item) for item in parser.warnings]
                structure_count = len(structures)
                if not 0 <= structure_index < structure_count:
                    raise CliError(
                        f"structure index {structure_index} is outside "
                        f"0..{structure_count - 1}"
                    )
                structure = structures[structure_index]
            else:
                from pymatgen.core import Structure

                if structure_index != 0:
                    raise CliError(
                        "non-CIF readers expose one structure; use index 0"
                    )
                structure = Structure.from_file(path, primitive=False, sort=False)
            warning_messages = [
                f"{item.category.__name__}: {item.message}" for item in caught
            ]
    except CliError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise CliError(
            f"pymatgen could not parse {path.name}: {type(exc).__name__}: {exc}"
        ) from exc
    if len(structure) > max_sites:
        raise CliError(
            f"structure has {len(structure)} sites, above the {max_sites}-site limit"
        )
    report = {
        "input_name": path.name,
        "input_bytes": path.stat().st_size,
        "structure_index": structure_index,
        "structures_in_file": structure_count,
        "python_warnings": warning_messages,
        "parser_warnings": parser_messages,
        "warnings_acknowledged": False,
    }
    return structure, path, report


def safe_error_message(exc: BaseException, *, secret: str | None = None) -> str:
    """Return a bounded error message with a known secret redacted."""
    message = f"{type(exc).__name__}: {exc}"
    if secret:
        message = message.replace(secret, "[REDACTED]")
    return message[:1000]


def atomic_link_from_temp(temp_path: Path, output_path: Path) -> None:
    """Link a completed temporary artifact into place without overwriting."""
    try:
        os.link(temp_path, output_path)
    except FileExistsError as exc:
        raise CliError("output appeared concurrently; nothing was overwritten") from exc
