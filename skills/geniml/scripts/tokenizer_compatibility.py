#!/usr/bin/env python3
"""Plan local tokenizer/universe/model compatibility checks without imports."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from collections import Counter
from pathlib import Path

from _common import (
    HARD_MAX_BYTES,
    HARD_MAX_RECORDS,
    MAX_COORDINATE,
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


TOOL = "tokenizer-universe-compatibility"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare a local model bundle and universe using checksums and bounded "
            "metadata only. No model is deserialized and no package is imported."
        )
    )
    parser.add_argument("--model-dir", required=True, help="Local model bundle directory.")
    parser.add_argument("--universe", required=True, help="Expected local universe BED.")
    parser.add_argument("--assembly", required=True, help="Declared assembly/accession.")
    parser.add_argument("--config-name", default="config.yaml")
    parser.add_argument("--checkpoint-name", default="checkpoint.pt")
    parser.add_argument("--bundle-universe-name", default="universe.bed")
    parser.add_argument(
        "--token-corpus",
        help="Optional local Parquet token corpus to fingerprint (not parsed).",
    )
    parser.add_argument("--geniml-version", default="0.8.4")
    parser.add_argument("--gtars-version", default="0.10.0")
    parser.add_argument(
        "--special-token-count",
        type=int_type(minimum=0, maximum=100, label="special-token-count"),
        default=7,
        help="Expected Gtars special tokens (0.10.0 default: 7).",
    )
    parser.add_argument(
        "--max-bytes",
        type=int_type(minimum=1, maximum=HARD_MAX_BYTES, label="max-bytes"),
        default=2 * 1024**3,
    )
    parser.add_argument(
        "--max-universe-records",
        type=int_type(
            minimum=1,
            maximum=HARD_MAX_RECORDS,
            label="max-universe-records",
        ),
        default=5_000_000,
    )
    add_path_mode_argument(parser)
    return parser


def _safe_child(directory: Path, name: str) -> Path:
    if not name or Path(name).name != name or name in {".", ".."}:
        raise SafetyError("artifact names must be plain filenames")
    return local_path(str(directory / name), kind="file")


def _count_universe(
    path: Path,
    *,
    max_bytes: int,
    max_records: int,
) -> tuple[int, int, Counter[str]]:
    records = 0
    duplicates = 0
    issues: Counter[str] = Counter()
    seen: set[tuple[str, int, int]] = set()
    for _, line in iter_text_lines(
        path,
        max_bytes=max_bytes,
        max_records=max_records,
    ):
        if not line or line.startswith("#") or line.startswith("track") or line.startswith("browser"):
            continue
        fields = line.split("\t")
        if len(fields) < 3:
            issues["fewer_than_three_columns"] += 1
            continue
        chrom = fields[0]
        try:
            start = int(fields[1])
            end = int(fields[2])
        except ValueError:
            issues["non_integer_coordinate"] += 1
            continue
        if (
            not chrom
            or start < 0
            or end <= start
            or start > MAX_COORDINATE
            or end > MAX_COORDINATE
        ):
            issues["invalid_interval"] += 1
            continue
        records += 1
        key = (chrom, start, end)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return records, duplicates, issues


def _parquet_magic(path: Path) -> bool:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        mode = os.fstat(descriptor).st_mode
        size = os.fstat(descriptor).st_size
        if not stat.S_ISREG(mode) or size < 8:
            return False
        first = os.read(descriptor, 4)
        os.lseek(descriptor, -4, os.SEEK_END)
        last = os.read(descriptor, 4)
        return first == b"PAR1" and last == b"PAR1"
    finally:
        os.close(descriptor)


def inspect(args: argparse.Namespace) -> tuple[dict, int]:
    if not args.assembly.strip() or len(args.assembly) > 200:
        raise SafetyError("assembly must be a nonempty value of at most 200 characters")
    model_dir = local_path(args.model_dir, kind="dir")
    expected_universe = local_path(args.universe, kind="file")
    config_path = _safe_child(model_dir, args.config_name)
    checkpoint_path = _safe_child(model_dir, args.checkpoint_name)
    bundle_universe = _safe_child(model_dir, args.bundle_universe_name)

    errors: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    checks: list[dict[str, str | int | bool | None]] = []

    expected_digest, expected_size = sha256_file(
        expected_universe,
        max_bytes=args.max_bytes,
    )
    bundle_digest, bundle_size = sha256_file(
        bundle_universe,
        max_bytes=args.max_bytes,
    )
    universe_rows, duplicate_rows, universe_issues = _count_universe(
        expected_universe,
        max_bytes=args.max_bytes,
        max_records=args.max_universe_records,
    )
    for code, count in universe_issues.items():
        errors[f"universe:{code}"] = count
    if duplicate_rows:
        errors["universe:duplicate_intervals"] = duplicate_rows
    if universe_rows == 0:
        errors["universe:no_valid_records"] += 1

    universe_match = expected_digest == bundle_digest
    if not universe_match:
        errors["bundle_universe_checksum_mismatch"] += 1
    checks.append(
        {
            "check": "exact_universe_bytes_and_order",
            "passed": universe_match,
            "expected_sha256": expected_digest,
            "bundle_sha256": bundle_digest,
        }
    )

    config = simple_yaml_mapping(
        config_path,
        max_bytes=min(args.max_bytes, 16 * 1024**2),
    )
    vocab_size = config.get("vocab_size")
    embedding_dim = config.get("embedding_dim")
    old_embedding_dim = config.get("embedding_size")
    if embedding_dim is None and old_embedding_dim is not None:
        embedding_dim = old_embedding_dim
        warnings["deprecated_config_key:embedding_size"] += 1
    if type(vocab_size) is not int or vocab_size <= 0:
        errors["config:invalid_vocab_size"] += 1
    if type(embedding_dim) is not int or embedding_dim <= 0:
        errors["config:invalid_embedding_dim"] += 1
    pooling = config.get("pooling_method")
    if pooling is not None and pooling not in {"mean", "max"}:
        errors["config:invalid_pooling_method"] += 1

    expected_vocab_size = universe_rows + args.special_token_count
    vocab_match = type(vocab_size) is int and vocab_size == expected_vocab_size
    if not vocab_match:
        errors["model_tokenizer_vocab_size_mismatch"] += 1
    checks.append(
        {
            "check": "vocab_size_equals_universe_plus_special_tokens",
            "passed": vocab_match,
            "model_vocab_size": vocab_size,
            "universe_records": universe_rows,
            "special_token_count": args.special_token_count,
            "expected_vocab_size": expected_vocab_size,
        }
    )

    config_digest, config_size = sha256_file(
        config_path,
        max_bytes=min(args.max_bytes, 16 * 1024**2),
    )
    checkpoint_digest, checkpoint_size = sha256_file(
        checkpoint_path,
        max_bytes=args.max_bytes,
    )
    if checkpoint_size == 0:
        errors["checkpoint:empty"] += 1

    token_corpus_summary = None
    if args.token_corpus:
        token_path = local_path(args.token_corpus, kind="file")
        token_digest, token_size = sha256_file(token_path, max_bytes=args.max_bytes)
        magic_ok = _parquet_magic(token_path)
        if not magic_ok:
            errors["token_corpus:invalid_parquet_magic"] += 1
        token_corpus_summary = {
            "path": display_path(token_path, 4, args.path_mode),
            "sha256": token_digest,
            "size_bytes": token_size,
            "parquet_magic_valid": magic_ok,
            "schema_inspected": False,
        }

    warnings["assembly_provenance_not_embedded_in_standard_config"] += 1
    report = {
        "ok": not errors,
        "tool": TOOL,
        "contract": {
            "assembly": args.assembly,
            "coordinate_system": "0-based-half-open",
            "geniml_version": args.geniml_version,
            "gtars_version": args.gtars_version,
            "network_used": False,
            "model_deserialized": False,
        },
        "paths": {
            "model_dir": display_path(model_dir, 1, args.path_mode),
            "expected_universe": display_path(expected_universe, 2, args.path_mode),
            "bundle_universe": display_path(bundle_universe, 3, args.path_mode),
        },
        "artifacts": {
            "checkpoint": {
                "name": checkpoint_path.name,
                "sha256": checkpoint_digest,
                "size_bytes": checkpoint_size,
                "deserialized": False,
            },
            "config": {
                "name": config_path.name,
                "sha256": config_digest,
                "size_bytes": config_size,
                "metadata": {
                    "vocab_size": vocab_size,
                    "embedding_dim": embedding_dim,
                    "pooling_method": pooling,
                },
            },
            "expected_universe": {
                "sha256": expected_digest,
                "size_bytes": expected_size,
                "records": universe_rows,
                "duplicate_intervals": duplicate_rows,
            },
            "bundle_universe": {
                "sha256": bundle_digest,
                "size_bytes": bundle_size,
            },
            "token_corpus": token_corpus_summary,
        },
        "checks": checks,
        "errors": dict(sorted(errors.items())),
        "warnings": dict(sorted(warnings.items())),
        "next_checks": [
            "compare assembly accession and chromosome-sizes checksum",
            "instantiate the pinned tokenizer only after this plan passes",
            "verify every special-token name and ID in a synthetic smoke test",
            "verify all token IDs are in range and Parquet has one list-valued tokens column",
            "load the checkpoint only in an isolated, resource-bounded environment",
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
