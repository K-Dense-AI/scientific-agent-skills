#!/usr/bin/env python3
"""Inspect checkpoint file metadata without deserializing checkpoint contents."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
from pathlib import Path
from typing import Any, BinaryIO

try:
    from ._common import (
        UserInputError,
        bounded_int,
        emit_json,
        load_json_object,
        resolve_local_path,
        secret_key_paths,
        validate_sha256,
    )
except ImportError:  # Direct script execution.
    from _common import (
        UserInputError,
        bounded_int,
        emit_json,
        load_json_object,
        resolve_local_path,
        secret_key_paths,
        validate_sha256,
    )

_SIDECAR_FIELDS = {
    "created_at",
    "environment",
    "format",
    "framework",
    "framework_version",
    "license",
    "notes",
    "parent_sha256",
    "policy",
    "schema_version",
    "seed",
    "sha256",
    "source_commit",
    "source_url",
    "training_steps",
}


def _open_regular_no_follow(path: Path) -> tuple[BinaryIO, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise UserInputError(f"cannot open checkpoint safely: {path}") from exc
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise UserInputError("checkpoint must be a regular file")
        return os.fdopen(descriptor, "rb"), file_stat
    except Exception:
        os.close(descriptor)
        raise


def _detect_format(prefix: bytes, suffix: str) -> dict[str, Any]:
    if prefix.startswith(b"PK\x03\x04"):
        return {
            "family": "zip-container",
            "risk": "may contain a torch.save pickle payload; not opened",
        }
    if prefix.startswith(b"\x80"):
        protocol = prefix[1] if len(prefix) > 1 else None
        return {
            "family": "pickle-like",
            "pickle_protocol_byte": protocol,
            "risk": "unsafe to deserialize unless provenance is trusted",
        }
    if suffix.lower() == ".bin":
        return {
            "family": "opaque-bin",
            "risk": "could be PufferLib native weights or another binary format",
        }
    return {
        "family": "opaque",
        "risk": "format not identified; no deserialization attempted",
    }


def _hash_and_prefix(handle: BinaryIO, *, chunk_bytes: int = 1_048_576) -> tuple[str, bytes]:
    digest = hashlib.sha256()
    prefix = b""
    while True:
        chunk = handle.read(chunk_bytes)
        if not chunk:
            break
        if not prefix:
            prefix = chunk[:16]
        digest.update(chunk)
    return digest.hexdigest(), prefix


def _safe_sidecar(
    metadata_path: str | None, *, root: str | Path
) -> tuple[dict[str, Any] | None, list[str]]:
    if metadata_path is None:
        return None, []
    raw = load_json_object(metadata_path, root=root, max_bytes=262_144)
    secret_paths = secret_key_paths(raw)
    if secret_paths:
        raise UserInputError(
            "sidecar contains credential-bearing keys: " + ", ".join(secret_paths)
        )
    safe = {key: raw[key] for key in sorted(raw) if key in _SIDECAR_FIELDS}
    unknown = sorted(set(raw) - _SIDECAR_FIELDS)
    return safe, unknown


def inspect_checkpoint(
    checkpoint_path: str,
    *,
    root: str | Path,
    metadata_path: str | None,
    expected_sha256: str | None,
    max_bytes: int,
) -> dict[str, Any]:
    """Hash and classify one local regular file without importing torch or pickle."""
    resolved = resolve_local_path(
        checkpoint_path,
        root=root,
        must_exist=True,
        reject_symlink=True,
    )
    handle, file_stat = _open_regular_no_follow(resolved)
    with handle:
        if file_stat.st_size > max_bytes:
            raise UserInputError(
                f"checkpoint is {file_stat.st_size} bytes; cap is {max_bytes}"
            )
        digest, prefix = _hash_and_prefix(handle)

    expected = validate_sha256(expected_sha256) if expected_sha256 else None
    sidecar, unknown_fields = _safe_sidecar(metadata_path, root=root)
    sidecar_digest = sidecar.get("sha256") if sidecar else None
    if sidecar_digest is not None:
        validate_sha256(sidecar_digest, name="sidecar sha256")

    return {
        "checkpoint": {
            "format_detection": _detect_format(prefix, resolved.suffix),
            "name": resolved.name,
            "sha256": digest,
            "size_bytes": file_stat.st_size,
        },
        "deserialized": False,
        "expected_sha256_matches": None if expected is None else digest == expected,
        "metadata": sidecar,
        "metadata_sha256_matches": (
            None if sidecar_digest is None else digest == sidecar_digest
        ),
        "network_used": False,
        "sidecar_unknown_fields_omitted": unknown_fields,
        "warning": (
            "Inspection does not establish trust. Verify source, license, signature or "
            "attestation, and checksum before sandboxed loading."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Hash and classify one local checkpoint without torch.load, pickle, "
            "archive extraction, dynamic imports, or network access."
        )
    )
    parser.add_argument("checkpoint", help="Checkpoint path beneath --root")
    parser.add_argument("--root", default=".", help="Allowed local path root")
    parser.add_argument("--metadata", help="Explicit strict-JSON sidecar beneath --root")
    parser.add_argument("--expected-sha256")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=2_147_483_648,
        help="1..68719476736",
    )
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        max_bytes = bounded_int(
            args.max_bytes,
            name="max_bytes",
            minimum=1,
            maximum=68_719_476_736,
        )
        report = inspect_checkpoint(
            args.checkpoint,
            root=args.root,
            metadata_path=args.metadata,
            expected_sha256=args.expected_sha256,
            max_bytes=max_bytes,
        )
    except (UserInputError, OSError, ValueError) as exc:
        report = {
            "deserialized": False,
            "errors": [str(exc)],
            "network_used": False,
            "status": "invalid",
        }
        emit_json(report, pretty=not args.compact)
        return 1
    emit_json(report, pretty=not args.compact)
    # A requested integrity check must fail the CLI when bytes do not match.
    return 1 if (
        report["expected_sha256_matches"] is False
        or report["metadata_sha256_matches"] is False
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
