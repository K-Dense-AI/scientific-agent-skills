#!/usr/bin/env python3
"""Inspect local model artifacts and checksums without deserialization."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

from _common import (
    HARD_MAX_BYTES,
    HARD_MAX_FILES,
    SafetyError,
    add_path_mode_argument,
    display_path,
    fail_json,
    int_type,
    iter_text_lines,
    local_path,
    print_json,
    sha256_file,
    simple_yaml_mapping,
)


TOOL = "model-artifact-inspector"
_HASH_LINE = re.compile(r"^([0-9a-fA-F]{64})[ \t]+[* ]?(.+?)$")
_DESERIALIZATION_RISK = {
    ".pt",
    ".pth",
    ".ckpt",
    ".bin",
    ".pkl",
    ".pickle",
    ".joblib",
    ".model",
}
_NATIVE_RISK = {".so", ".dylib", ".dll", ".exe"}
_ARCHIVE_RISK = {".tar", ".zip", ".tgz", ".gz", ".bz2", ".xz"}
_METADATA_KEYS = {
    "architectures",
    "embedding_dim",
    "embedding_size",
    "model_type",
    "pooling_method",
    "vocab_size",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory and hash a local Geniml model bundle without importing "
            "ML libraries, extracting archives, or deserializing model files."
        )
    )
    parser.add_argument("--model-dir", required=True)
    parser.add_argument(
        "--verify-manifest",
        help="Optional local SHA256SUMS-style manifest.",
    )
    parser.add_argument(
        "--max-files",
        type=int_type(minimum=1, maximum=HARD_MAX_FILES, label="max-files"),
        default=1_000,
    )
    parser.add_argument(
        "--max-file-bytes",
        type=int_type(minimum=1, maximum=HARD_MAX_BYTES, label="max-file-bytes"),
        default=2 * 1024**3,
    )
    parser.add_argument(
        "--max-total-bytes",
        type=int_type(minimum=1, maximum=HARD_MAX_BYTES, label="max-total-bytes"),
        default=4 * 1024**3,
    )
    parser.add_argument(
        "--max-output-files",
        type=int_type(minimum=0, maximum=5_000, label="max-output-files"),
        default=200,
    )
    add_path_mode_argument(parser)
    return parser


def _walk_regular_files(root: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
        for entry in ordered:
            path = Path(entry.path)
            if entry.is_symlink():
                raise SafetyError("symlink is not allowed in model bundle")
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
            elif entry.is_file(follow_symlinks=False):
                files.append(path)
                if len(files) > max_files:
                    raise SafetyError("model bundle exceeds max-files")
            else:
                raise SafetyError("special filesystem entry is not allowed")
    return sorted(files)


def _risk_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _DESERIALIZATION_RISK:
        return "deserialization"
    if suffix in _NATIVE_RISK:
        return "native-executable"
    if suffix in _ARCHIVE_RISK:
        return "archive-expansion"
    if suffix == ".safetensors":
        return "bounded-format-still-untrusted"
    return "data-or-metadata"


def _safe_json(path: Path, max_bytes: int):
    lines = [
        line
        for _, line in iter_text_lines(
            path,
            max_bytes=max_bytes,
            max_records=100_000,
        )
    ]
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise SafetyError("JSON numeric metadata must be finite")
        return number

    def reject_constant(value):
        raise SafetyError("JSON numeric metadata must be finite")

    def unique_keys(pairs):
        mapping = {}
        for key, value in pairs:
            if key in mapping:
                raise SafetyError("duplicate JSON metadata key")
            mapping[key] = value
        return mapping

    try:
        return json.loads("\n".join(lines), parse_float=finite_float,
                          parse_constant=reject_constant, object_pairs_hook=unique_keys)
    except (ValueError, RecursionError) as exc:
        raise SafetyError("invalid JSON metadata") from exc


def _read_checksum_manifest(
    path: Path,
    *,
    max_bytes: int,
    max_files: int,
) -> dict[str, str]:
    expected: dict[str, str] = {}
    for line_number, line in iter_text_lines(
        path,
        max_bytes=max_bytes,
        max_records=max_files + 100,
    ):
        if not line or line.startswith("#"):
            continue
        match = _HASH_LINE.fullmatch(line)
        if not match:
            raise SafetyError(f"invalid checksum manifest line {line_number}")
        digest, name = match.groups()
        relative = Path(name)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
            or "://" in name
            or name.startswith("~")
        ):
            raise SafetyError(f"unsafe checksum path at line {line_number}")
        normalized = relative.as_posix()
        if normalized in expected:
            raise SafetyError(f"duplicate checksum entry at line {line_number}")
        expected[normalized] = digest.lower()
        if len(expected) > max_files:
            raise SafetyError("checksum manifest exceeds max-files")
    return expected


def _redacted_metadata(value) -> tuple[dict[str, object], int]:
    if not isinstance(value, dict):
        raise SafetyError("config metadata must be a mapping")
    selected: dict[str, object] = {}
    for key in _METADATA_KEYS:
        if key not in value:
            continue
        item = value[key]
        if isinstance(item, (str, int, float, bool)) or item is None:
            if isinstance(item, str) and len(item) > 200:
                selected[key] = "<redacted-long-string>"
            else:
                selected[key] = item
        elif key == "architectures" and isinstance(item, list):
            selected[key] = [
                entry if isinstance(entry, str) and len(entry) <= 100 else "<redacted>"
                for entry in item[:20]
            ]
    return selected, max(0, len(value) - len(selected))


def inspect(args: argparse.Namespace) -> tuple[dict, int]:
    model_dir = local_path(args.model_dir, kind="dir")
    files = _walk_regular_files(model_dir, args.max_files)
    if not files:
        raise SafetyError("model directory is empty")

    errors: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    computed: dict[str, str] = {}
    summaries: list[dict] = []
    metadata: dict[str, object] = {}
    total_bytes = 0

    for index, path in enumerate(files, start=1):
        relative = path.relative_to(model_dir).as_posix()
        size = path.lstat().st_size
        if size > args.max_file_bytes:
            errors["file_exceeds_byte_limit"] += 1
            continue
        total_bytes += size
        if total_bytes > args.max_total_bytes:
            raise SafetyError("model bundle exceeds max-total-bytes")
        digest, hashed_size = sha256_file(path, max_bytes=args.max_file_bytes)
        computed[relative] = digest
        risk = _risk_for(path)
        risk_counts[risk] += 1
        if risk in {"deserialization", "native-executable", "archive-expansion"}:
            warnings[f"risky_artifact:{risk}"] += 1

        if path.name in {"config.yaml", "config.yml"}:
            parsed = simple_yaml_mapping(
                path,
                max_bytes=min(args.max_file_bytes, 16 * 1024**2),
            )
            selected, omitted = _redacted_metadata(parsed)
            metadata[path.name] = selected
            if omitted:
                warnings["config_metadata_fields_redacted"] += omitted
        elif path.name in {"config.json", "tokenizer_config.json"}:
            parsed = _safe_json(
                path,
                max_bytes=min(args.max_file_bytes, 16 * 1024**2),
            )
            selected, omitted = _redacted_metadata(parsed)
            metadata[path.name] = selected
            if omitted:
                warnings["config_metadata_fields_redacted"] += omitted

        if len(summaries) < args.max_output_files:
            if args.path_mode == "redacted":
                shown_path = f"artifact_{index:04d}"
            elif args.path_mode == "basename":
                shown_path = path.name
            else:
                shown_path = str(path)
            summaries.append(
                {
                    "path": shown_path,
                    "sha256": digest,
                    "size_bytes": hashed_size,
                    "risk_class": risk,
                    "deserialized": False,
                }
            )

    standard = {
        name: name in computed for name in ("checkpoint.pt", "config.yaml", "universe.bed")
    }
    for name, present in standard.items():
        if not present:
            errors[f"missing_standard_artifact:{name}"] += 1

    verification = None
    if args.verify_manifest:
        manifest = local_path(args.verify_manifest, kind="file")
        expected = _read_checksum_manifest(
            manifest,
            max_bytes=min(args.max_file_bytes, 64 * 1024**2),
            max_files=args.max_files,
        )
        missing = sorted(set(expected) - set(computed))
        unlisted = sorted(set(computed) - set(expected))
        mismatched = sorted(
            name
            for name in set(expected) & set(computed)
            if expected[name] != computed[name]
        )
        if missing:
            errors["checksum_manifest_missing_files"] = len(missing)
        if mismatched:
            errors["checksum_mismatches"] = len(mismatched)
        if unlisted:
            warnings["files_not_listed_in_checksum_manifest"] = len(unlisted)
        verification = {
            "manifest": display_path(manifest, 2, args.path_mode),
            "expected_entries": len(expected),
            "missing_count": len(missing),
            "mismatch_count": len(mismatched),
            "unlisted_count": len(unlisted),
            "verified": not missing and not mismatched,
        }

    config = metadata.get("config.yaml")
    if isinstance(config, dict):
        vocab_size = config.get("vocab_size")
        embedding_dim = config.get("embedding_dim", config.get("embedding_size"))
        if type(vocab_size) is not int or vocab_size <= 0:
            errors["config:invalid_vocab_size"] += 1
        if type(embedding_dim) is not int or embedding_dim <= 0:
            errors["config:invalid_embedding_dim"] += 1
        if "embedding_size" in config and "embedding_dim" not in config:
            warnings["config:deprecated_embedding_size_key"] += 1

    report = {
        "ok": not errors,
        "tool": TOOL,
        "contract": {
            "network_used": False,
            "model_deserialized": False,
            "archives_extracted": False,
            "dynamic_imports_used": False,
            "symlinks_allowed": False,
        },
        "model_dir": display_path(model_dir, 1, args.path_mode),
        "summary": {
            "file_count": len(files),
            "hashed_file_count": len(computed),
            "total_bytes": total_bytes,
            "output_file_summaries": len(summaries),
            "omitted_file_summaries": max(0, len(files) - len(summaries)),
            "risk_classes": dict(sorted(risk_counts.items())),
            "standard_artifacts": standard,
        },
        "metadata": metadata,
        "checksum_verification": verification,
        "errors": dict(sorted(errors.items())),
        "warnings": dict(sorted(warnings.items())),
        "files": summaries,
        "loading_policy": [
            "verify provenance and checksums before loading",
            "never inspect .pt/.model/pickle/joblib by deserializing it",
            "load only in an isolated environment with CPU, RAM, disk, and time bounds",
            "compare universe bytes/order, tokenizer special IDs, vocab size, and assembly",
            "treat native binaries and archives as independently untrusted",
        ],
    }
    return report, 0 if not errors else 2


def main() -> int:
    args = build_parser().parse_args()
    try:
        report, exit_code = inspect(args)
        print_json(report)
        return exit_code
    except (OSError, SafetyError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
