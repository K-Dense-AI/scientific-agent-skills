#!/usr/bin/env python3
"""Check a local Gtars tokenizer manifest against its exact universe."""

from __future__ import annotations

import argparse
import re
import sys

from _common import (
    HARD_MAX_BYTES,
    HARD_MAX_RECORDS,
    SafetyError,
    add_path_mode_argument,
    display_path,
    fail_json,
    inspect_bed,
    int_type,
    load_chrom_sizes,
    load_json,
    local_path,
    print_json,
    sha256_file,
)


TOOL = "gtars-tokenizer-manifest"
DEFAULT_GTARS_PYTHON_VERSION = "0.10.0"
SPECIAL_TOKEN_NAMES = {"unk", "pad", "mask", "cls", "bos", "eos", "sep"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare a local JSON tokenizer manifest with a local universe BED. "
            "No tokenizer is imported and no model repository is contacted."
        )
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--universe", required=True)
    parser.add_argument("--assembly", required=True)
    parser.add_argument("--chrom-sizes")
    parser.add_argument(
        "--expected-python-version",
        default=DEFAULT_GTARS_PYTHON_VERSION,
    )
    parser.add_argument(
        "--max-bytes",
        type=int_type(minimum=1, maximum=HARD_MAX_BYTES, label="max-bytes"),
        default=1024**3,
    )
    parser.add_argument(
        "--max-records",
        type=int_type(
            minimum=1,
            maximum=HARD_MAX_RECORDS,
            label="max-records",
        ),
        default=5_000_000,
    )
    add_path_mode_argument(parser)
    return parser


def _mapping(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise SafetyError(f"{label} must be a JSON object")
    return value


def check(args: argparse.Namespace) -> tuple[dict, int]:
    assembly = args.assembly.strip()
    if not assembly or len(assembly) > 200:
        raise SafetyError("assembly must contain 1-200 characters")
    manifest_path = local_path(args.manifest, kind="file")
    universe_path = local_path(args.universe, kind="file")
    manifest = _mapping(
        load_json(manifest_path, max_bytes=min(args.max_bytes, 16 * 1024**2)),
        "manifest",
    )

    chrom_sizes = None
    chrom_order = None
    chrom_digest = None
    chrom_report = None
    if args.chrom_sizes:
        chrom_path = local_path(args.chrom_sizes, kind="file")
        chrom_sizes, chrom_order = load_chrom_sizes(
            chrom_path,
            max_bytes=min(args.max_bytes, 128 * 1024**2),
            max_records=min(args.max_records, 1_000_000),
        )
        chrom_digest, chrom_bytes = sha256_file(
            chrom_path,
            max_bytes=min(args.max_bytes, 128 * 1024**2),
        )
        chrom_report = {
            "path": display_path(chrom_path, 3, args.path_mode),
            "sha256": chrom_digest,
            "size_bytes": chrom_bytes,
        }

    universe = inspect_bed(
        universe_path,
        max_bytes=args.max_bytes,
        max_records=args.max_records,
        chrom_sizes=chrom_sizes,
        chrom_order=chrom_order,
    )
    errors: dict[str, int] = {
        f"universe:{code}": count for code, count in universe["errors"].items()
    }
    warnings: dict[str, int] = {}
    if universe["records"] == 0:
        errors["universe:no_data_records"] = 1
    if universe["duplicate_intervals"]:
        errors["universe:duplicate_intervals"] = universe["duplicate_intervals"]
    if universe["out_of_order_records"]:
        warnings["universe:order_is_part_of_token_ids"] = universe[
            "out_of_order_records"
        ]

    manifest_universe = _mapping(manifest.get("universe"), "manifest.universe")
    tokenizer = _mapping(manifest.get("tokenizer"), "manifest.tokenizer")
    expected_sha = manifest_universe.get("sha256")
    if not isinstance(expected_sha, str) or not _SHA256.fullmatch(expected_sha):
        errors["manifest:invalid_universe_sha256"] = 1
    elif expected_sha != universe["sha256"]:
        errors["manifest:universe_sha256_mismatch"] = 1

    expected_records = manifest_universe.get("records")
    if type(expected_records) is not int or expected_records < 1:
        errors["manifest:invalid_universe_record_count"] = 1
    elif expected_records != universe["records"]:
        errors["manifest:universe_record_count_mismatch"] = 1

    if manifest.get("schema_version") != "1.0":
        errors["manifest:unsupported_schema_version"] = 1
    if manifest.get("assembly") != assembly:
        errors["manifest:assembly_mismatch"] = 1
    if manifest.get("coordinate_system") != "0-based-half-open":
        errors["manifest:coordinate_system_mismatch"] = 1
    if manifest.get("gtars_python_version") != args.expected_python_version:
        errors["manifest:gtars_python_version_mismatch"] = 1
    if chrom_digest is not None:
        if manifest_universe.get("chrom_sizes_sha256") != chrom_digest:
            errors["manifest:chrom_sizes_sha256_mismatch"] = 1

    backend = tokenizer.get("backend")
    if backend not in {"bits", "ailist"}:
        errors["manifest:invalid_backend"] = 1
    vocab_size = tokenizer.get("vocab_size")
    expected_vocab = universe["records"] + len(SPECIAL_TOKEN_NAMES)
    if type(vocab_size) is not int or vocab_size < 1:
        errors["manifest:invalid_vocab_size"] = 1
    elif vocab_size != expected_vocab:
        errors["manifest:vocab_size_mismatch"] = 1

    token_ids = tokenizer.get("special_token_ids")
    if not isinstance(token_ids, dict):
        errors["manifest:missing_special_token_ids"] = 1
        token_ids = {}
    else:
        names = set(token_ids)
        if names != SPECIAL_TOKEN_NAMES:
            errors["manifest:special_token_name_set_mismatch"] = 1
        values = list(token_ids.values())
        if any(type(value) is not int or value < 0 for value in values):
            errors["manifest:invalid_special_token_id"] = 1
        elif len(values) != len(set(values)):
            errors["manifest:duplicate_special_token_ids"] = 1
        elif type(vocab_size) is int and any(value >= vocab_size for value in values):
            errors["manifest:special_token_id_out_of_range"] = 1

    manifest_digest, manifest_bytes = sha256_file(
        manifest_path,
        max_bytes=min(args.max_bytes, 16 * 1024**2),
    )
    report = {
        "ok": not errors,
        "tool": TOOL,
        "contract": {
            "assembly": assembly,
            "coordinate_system": "0-based-half-open",
            "expected_gtars_python_version": args.expected_python_version,
            "network_used": False,
            "packages_imported": False,
            "model_deserialized": False,
            "files_written": False,
            "symlinks_allowed": False,
        },
        "manifest": {
            "path": display_path(manifest_path, 1, args.path_mode),
            "sha256": manifest_digest,
            "size_bytes": manifest_bytes,
            "schema_version": manifest.get("schema_version"),
        },
        "universe": {
            "path": display_path(universe_path, 2, args.path_mode),
            "sha256": universe["sha256"],
            "size_bytes": universe["size_bytes"],
            "records": universe["records"],
            "duplicate_intervals": universe["duplicate_intervals"],
            "out_of_order_records": universe["out_of_order_records"],
        },
        "chromosome_sizes": chrom_report,
        "compatibility": {
            "backend": backend,
            "vocab_size": vocab_size,
            "expected_vocab_size": expected_vocab,
            "special_token_count": len(token_ids),
            "universe_bytes_and_order_match": expected_sha == universe["sha256"],
        },
        "errors": dict(sorted(errors.items())),
        "warnings": dict(sorted(warnings.items())),
        "next_checks": [
            "freeze patient and replicate splits before fitting the universe",
            "instantiate Tokenizer.from_bed only after this local manifest passes",
            "verify a small fixed set of token IDs with gtars==0.10.0",
            "do not use from_pretrained until an immutable snapshot is approved locally",
        ],
    }
    return report, 0 if not errors else 2


def main() -> int:
    args = build_parser().parse_args()
    try:
        report, status = check(args)
        print_json(report)
        return status
    except (OSError, SafetyError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
