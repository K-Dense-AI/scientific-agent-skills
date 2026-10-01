#!/usr/bin/env python3
"""Hash and classify local Gtars artifacts without loading or executing them."""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
from email.parser import Parser
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
)


TOOL = "gtars-artifact-inspector"
_WHEEL = re.compile(r"^gtars-(\d+\.\d+\.\d+)-.+\.whl$")
_CRATE = re.compile(r"^(gtars|gtars-cli)-(\d+\.\d+\.\d+)\.crate$")
_CHECKSUM = re.compile(r"^([0-9a-fA-F]{64})[ \t]+[* ]?([^/\\]+)$")
_ARCHIVES = (".tar.gz", ".tgz", ".zip", ".crate", ".whl")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory, hash, and version-screen local Gtars wheels, crates, "
            "release archives, native extensions, binaries, or METADATA files. "
            "Archives are not extracted and code is never loaded or executed."
        )
    )
    parser.add_argument(
        "--artifact",
        action="append",
        required=True,
        help="Local regular file; repeat for multiple artifacts.",
    )
    parser.add_argument("--checksum-manifest", help="Local SHA256SUMS-style file.")
    parser.add_argument("--expected-python-version", default="0.10.0")
    parser.add_argument("--expected-rust-version", default="0.10.0")
    parser.add_argument("--expected-cli-version", default="0.10.0")
    parser.add_argument(
        "--max-files",
        type=int_type(minimum=1, maximum=HARD_MAX_FILES, label="max-files"),
        default=1_000,
    )
    parser.add_argument(
        "--max-file-bytes",
        type=int_type(
            minimum=1,
            maximum=HARD_MAX_BYTES,
            label="max-file-bytes",
        ),
        default=2 * 1024**3,
    )
    parser.add_argument(
        "--max-total-bytes",
        type=int_type(
            minimum=1,
            maximum=HARD_MAX_BYTES,
            label="max-total-bytes",
        ),
        default=4 * 1024**3,
    )
    add_path_mode_argument(parser)
    return parser


def _read_prefix(path: Path, length: int = 16) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise SafetyError("artifact must be a regular file")
        return os.read(descriptor, length)
    finally:
        os.close(descriptor)


def _native_format(prefix: bytes) -> str | None:
    if prefix.startswith(b"\x7fELF"):
        return "elf"
    if prefix.startswith(b"MZ"):
        return "portable-executable"
    if prefix[:4] in {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
    }:
        return "mach-o"
    return None


def _parse_metadata(path: Path, max_bytes: int) -> dict[str, str | None]:
    text = "\n".join(
        line
        for _, line in iter_text_lines(
            path,
            max_bytes=max_bytes,
            max_records=100_000,
        )
    )
    message = Parser().parsestr(text)
    return {
        "name": message.get("Name"),
        "version": message.get("Version"),
        "requires_python": message.get("Requires-Python"),
    }


def _read_checksums(
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
        match = _CHECKSUM.fullmatch(line)
        if match is None:
            raise SafetyError(f"invalid checksum line {line_number}")
        digest, name = match.groups()
        if name in expected:
            raise SafetyError(f"duplicate checksum entry at line {line_number}")
        expected[name] = digest.lower()
        if len(expected) > max_files:
            raise SafetyError("checksum manifest exceeds max-files")
    return expected


def inspect(args: argparse.Namespace) -> tuple[dict, int]:
    if len(args.artifact) > args.max_files:
        raise SafetyError("artifact count exceeds max-files")
    paths = [local_path(raw, kind="file") for raw in args.artifact]
    if len({str(path) for path in paths}) != len(paths):
        raise SafetyError("duplicate artifact path")

    checksum_path = None
    checksums: dict[str, str] = {}
    checksum_report = None
    if args.checksum_manifest:
        checksum_path = local_path(args.checksum_manifest, kind="file")
        checksums = _read_checksums(
            checksum_path,
            max_bytes=min(args.max_file_bytes, 64 * 1024**2),
            max_files=args.max_files,
        )

    errors: dict[str, int] = {}
    warnings: dict[str, int] = {}
    summaries: list[dict] = []
    total = 0
    verified = 0

    for index, path in enumerate(paths, start=1):
        digest, size = sha256_file(path, max_bytes=args.max_file_bytes)
        total += size
        if total > args.max_total_bytes:
            raise SafetyError("artifacts exceed max-total-bytes")
        name = path.name
        prefix = _read_prefix(path)
        native = _native_format(prefix)
        kind = "data-or-metadata"
        version = None
        package = None
        metadata = None

        wheel_match = _WHEEL.fullmatch(name)
        crate_match = _CRATE.fullmatch(name)
        if wheel_match:
            kind = "python-wheel-native-code"
            package = "gtars"
            version = wheel_match.group(1)
            if version != args.expected_python_version:
                errors["python_version_mismatch"] = (
                    errors.get("python_version_mismatch", 0) + 1
                )
        elif crate_match:
            kind = "cargo-crate-archive"
            package, version = crate_match.groups()
            expected = (
                args.expected_cli_version
                if package == "gtars-cli"
                else args.expected_rust_version
            )
            if version != expected:
                errors[f"{package}_version_mismatch"] = (
                    errors.get(f"{package}_version_mismatch", 0) + 1
                )
        elif name == "METADATA":
            kind = "python-distribution-metadata"
            metadata = _parse_metadata(path, min(args.max_file_bytes, 16 * 1024**2))
            package = metadata["name"]
            version = metadata["version"]
            if package != "gtars":
                errors["metadata_package_name_mismatch"] = 1
            if version != args.expected_python_version:
                errors["metadata_python_version_mismatch"] = 1
            if metadata["requires_python"] != ">=3.10":
                warnings["metadata_requires_python_differs_from_snapshot"] = 1
        elif native is not None:
            kind = "native-executable-code"
            warnings["native_version_not_verified_without_execution"] = (
                warnings.get("native_version_not_verified_without_execution", 0) + 1
            )
        elif name.endswith(_ARCHIVES):
            kind = "archive-not-extracted"
            warnings["archive_contents_not_inspected"] = (
                warnings.get("archive_contents_not_inspected", 0) + 1
            )

        expected_digest = checksums.get(name)
        checksum_ok = expected_digest == digest if expected_digest is not None else None
        if checksum_ok:
            verified += 1
        elif checksum_ok is False:
            errors["checksum_mismatch"] = errors.get("checksum_mismatch", 0) + 1
        elif checksums:
            warnings["artifact_missing_from_checksum_manifest"] = (
                warnings.get("artifact_missing_from_checksum_manifest", 0) + 1
            )

        summaries.append(
            {
                "path": display_path(path, index, args.path_mode),
                "basename": name if args.path_mode != "redacted" else None,
                "sha256": digest,
                "size_bytes": size,
                "kind": kind,
                "native_format": native,
                "package": package,
                "version": version,
                "metadata": metadata,
                "checksum_verified": checksum_ok,
                "loaded": False,
                "executed": False,
                "extracted": False,
            }
        )

    if checksum_path is not None:
        manifest_digest, manifest_size = sha256_file(
            checksum_path,
            max_bytes=min(args.max_file_bytes, 64 * 1024**2),
        )
        checksum_report = {
            "path": display_path(
                checksum_path,
                len(paths) + 1,
                args.path_mode,
            ),
            "sha256": manifest_digest,
            "size_bytes": manifest_size,
            "entries": len(checksums),
            "verified_artifacts": verified,
        }

    report = {
        "ok": not errors,
        "tool": TOOL,
        "contract": {
            "network_used": False,
            "packages_imported": False,
            "native_code_loaded": False,
            "artifacts_executed": False,
            "archives_extracted": False,
            "symlinks_allowed": False,
        },
        "expected_versions": {
            "python": args.expected_python_version,
            "rust_meta_crate": args.expected_rust_version,
            "cli": args.expected_cli_version,
        },
        "summary": {
            "artifact_count": len(paths),
            "total_bytes": total,
            "checksum_verified_count": verified,
        },
        "checksum_manifest": checksum_report,
        "artifacts": summaries,
        "errors": dict(sorted(errors.items())),
        "warnings": dict(sorted(warnings.items())),
        "trust_gate": [
            "accept only an approved official source and immutable release",
            "verify the artifact SHA-256 against an independently obtained value",
            "do not run untrusted binaries or Cargo build scripts",
            "load or execute only in isolation with CPU, RAM, disk, and time limits",
            "after trust approval, verify gtars --version or gtars.__version__",
        ],
    }
    return report, 0 if not errors else 2


def main() -> int:
    args = build_parser().parse_args()
    try:
        report, status = inspect(args)
        print_json(report)
        return status
    except (OSError, SafetyError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
