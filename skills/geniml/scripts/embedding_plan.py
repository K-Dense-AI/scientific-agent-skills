#!/usr/bin/env python3
"""Plan a bounded local Geniml embedding run without importing ML packages."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from collections import Counter
from pathlib import Path

from _common import (
    HARD_MAX_BYTES,
    HARD_MAX_EPOCHS,
    HARD_MAX_WORKERS,
    SafetyError,
    add_path_mode_argument,
    display_path,
    fail_json,
    int_type,
    local_path,
    print_json,
    sha256_file,
    simple_yaml_mapping,
)


TOOL = "embedding-run-planner"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate local inputs and emit a redacted Region2Vec, scEmbed, or "
            "BEDspace run plan. No package, model, binary, or network call is executed."
        )
    )
    parser.add_argument("--mode", choices=("region2vec", "scembed", "bedspace"), required=True)
    parser.add_argument("--data", required=True, help="Token Parquet or BED directory.")
    parser.add_argument("--metadata", help="BEDspace metadata CSV.")
    parser.add_argument("--universe", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-dir", help="Optional trusted local model bundle.")
    parser.add_argument("--starspace-dir", help="BEDspace-only local StarSpace directory.")
    parser.add_argument("--assembly", required=True)
    parser.add_argument(
        "--split-unit",
        choices=("patient", "donor", "biological-replicate", "sample", "cell"),
        default="patient",
    )
    parser.add_argument(
        "--embedding-dim",
        type=int_type(minimum=1, maximum=4096, label="embedding-dim"),
        default=100,
    )
    parser.add_argument(
        "--epochs",
        type=int_type(minimum=1, maximum=HARD_MAX_EPOCHS, label="epochs"),
        default=10,
    )
    parser.add_argument(
        "--workers",
        type=int_type(minimum=1, maximum=HARD_MAX_WORKERS, label="workers"),
        default=4,
    )
    parser.add_argument(
        "--window-size",
        type=int_type(minimum=1, maximum=100_000, label="window-size"),
        default=5,
    )
    parser.add_argument(
        "--min-count",
        type=int_type(minimum=1, maximum=10_000_000, label="min-count"),
        default=10,
    )
    parser.add_argument(
        "--batch-size",
        type=int_type(minimum=1, maximum=1_000_000, label="batch-size"),
        default=64,
    )
    parser.add_argument(
        "--seed",
        type=int_type(minimum=0, maximum=2**32 - 1, label="seed"),
        default=42,
    )
    parser.add_argument("--pooling", choices=("mean", "max"), default="mean")
    parser.add_argument("--geniml-version", default="0.8.4")
    parser.add_argument("--gtars-version", default="0.10.0")
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
    add_path_mode_argument(parser)
    return parser


def _parquet_magic(path: Path) -> bool:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size < 8:
            return False
        first = os.read(descriptor, 4)
        os.lseek(descriptor, -4, os.SEEK_END)
        last = os.read(descriptor, 4)
        return first == b"PAR1" and last == b"PAR1"
    finally:
        os.close(descriptor)


def _render(path: Path, label: str, mode: str) -> str:
    if mode == "full":
        return str(path)
    if mode == "basename":
        return path.name
    return f"<{label}>"


def plan(args: argparse.Namespace) -> tuple[dict, int]:
    if not args.assembly.strip() or len(args.assembly) > 200:
        raise SafetyError("assembly must be a nonempty value of at most 200 characters")
    if args.mode != "bedspace" and (args.metadata or args.starspace_dir):
        raise SafetyError("metadata and starspace-dir apply only to bedspace")
    if args.mode == "bedspace" and not args.metadata:
        raise SafetyError("bedspace requires --metadata")
    if args.mode == "bedspace" and args.model_dir:
        raise SafetyError("model-dir applies only to Region2Vec or scEmbed bundles")

    data = local_path(args.data, kind="dir" if args.mode == "bedspace" else "file")
    universe = local_path(args.universe, kind="file")
    output_dir = local_path(args.output_dir, kind="dir")
    model_dir = local_path(args.model_dir, kind="dir") if args.model_dir else None
    metadata = local_path(args.metadata, kind="file") if args.metadata else None
    starspace_dir = (
        local_path(args.starspace_dir, kind="dir") if args.starspace_dir else None
    )

    errors: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    if args.split_unit == "cell":
        errors["nonindependent_split_unit:cell"] += 1
    elif args.split_unit == "sample":
        warnings["verify_samples_are_independent_across_patients"] += 1
    if any(output_dir.iterdir()):
        warnings["output_directory_not_empty"] += 1

    universe_digest, universe_size = sha256_file(
        universe,
        max_bytes=args.max_file_bytes,
    )
    input_summary: dict[str, object] = {
        "data": display_path(data, 1, args.path_mode),
        "universe": display_path(universe, 2, args.path_mode),
        "universe_sha256": universe_digest,
        "universe_size_bytes": universe_size,
        "output_dir": display_path(output_dir, 3, args.path_mode),
    }

    if args.mode in {"region2vec", "scembed"}:
        data_digest, data_size = sha256_file(data, max_bytes=args.max_file_bytes)
        parquet_ok = _parquet_magic(data)
        if not parquet_ok:
            errors["data_not_parquet"] += 1
        input_summary.update(
            {
                "data_sha256": data_digest,
                "data_size_bytes": data_size,
                "parquet_magic_valid": parquet_ok,
                "parquet_schema_inspected": False,
            }
        )
    else:
        bed_entries = list(data.iterdir())
        if len(bed_entries) > 100_000:
            raise SafetyError("BEDspace input directory exceeds 100,000 entries")
        symlinks = sum(1 for entry in bed_entries if entry.is_symlink())
        special = sum(
            1
            for entry in bed_entries
            if not entry.is_symlink() and not entry.is_file()
        )
        if symlinks:
            errors["bedspace_data_symlinks"] = symlinks
        if special:
            errors["bedspace_non_file_entries"] = special
        total_bed_bytes = 0
        oversized_beds = 0
        for entry in bed_entries:
            if entry.is_symlink() or not entry.is_file():
                continue
            size = entry.lstat().st_size
            total_bed_bytes += size
            if size > args.max_file_bytes:
                oversized_beds += 1
            if total_bed_bytes > args.max_total_bytes:
                raise SafetyError("BEDspace input directory exceeds max-total-bytes")
        if oversized_beds:
            errors["bedspace_files_exceed_byte_limit"] = oversized_beds
        metadata_digest, metadata_size = sha256_file(
            metadata,
            max_bytes=args.max_file_bytes,
        )
        input_summary.update(
            {
                "bed_directory_entries": len(bed_entries),
                "bed_directory_bytes": total_bed_bytes,
                "metadata": display_path(metadata, 4, args.path_mode),
                "metadata_sha256": metadata_digest,
                "metadata_size_bytes": metadata_size,
                "metadata_values_emitted": False,
            }
        )

    model_summary = None
    if model_dir:
        config = local_path(str(model_dir / "config.yaml"), kind="file")
        checkpoint = local_path(str(model_dir / "checkpoint.pt"), kind="file")
        bundle_universe = local_path(str(model_dir / "universe.bed"), kind="file")
        config_metadata = simple_yaml_mapping(
            config,
            max_bytes=min(args.max_file_bytes, 16 * 1024**2),
        )
        config_digest, config_size = sha256_file(
            config,
            max_bytes=min(args.max_file_bytes, 16 * 1024**2),
        )
        checkpoint_digest, checkpoint_size = sha256_file(
            checkpoint,
            max_bytes=args.max_file_bytes,
        )
        bundle_digest, bundle_size = sha256_file(
            bundle_universe,
            max_bytes=args.max_file_bytes,
        )
        if bundle_digest != universe_digest:
            errors["model_universe_checksum_mismatch"] += 1
        if config_metadata.get("embedding_dim", config_metadata.get("embedding_size")) != (
            args.embedding_dim
        ):
            warnings["planned_embedding_dim_differs_from_model"] += 1
        model_summary = {
            "path": display_path(model_dir, 5, args.path_mode),
            "config_sha256": config_digest,
            "config_size_bytes": config_size,
            "checkpoint_sha256": checkpoint_digest,
            "checkpoint_size_bytes": checkpoint_size,
            "bundle_universe_sha256": bundle_digest,
            "bundle_universe_size_bytes": bundle_size,
            "metadata": {
                "vocab_size": config_metadata.get("vocab_size"),
                "embedding_dim": config_metadata.get(
                    "embedding_dim",
                    config_metadata.get("embedding_size"),
                ),
                "pooling_method": config_metadata.get("pooling_method"),
            },
            "deserialized": False,
        }

    stages: list[dict] = [
        {
            "stage": "environment",
            "executed": False,
            "requirements": [
                f"geniml=={args.geniml_version}",
                f"gtars=={args.gtars_version}",
                "anndata==0.12.19",
                "scanpy==1.12.4",
                "zarr==2.18.7",
                "torch==2.14.1",
                "gensim==4.4.0",
                "huggingface-hub==2.0.0",
            ],
            "instruction": "resolve with uv and retain the generated lockfile",
        },
        {
            "stage": "data_contract",
            "executed": False,
            "instruction": (
                "verify 0-based half-open coordinates, one assembly/chromosome-sizes "
                "digest, bounded token counts, and patient/donor-grouped splits"
            ),
        },
    ]

    if args.mode == "region2vec":
        stages.extend(
            [
                {
                    "stage": "api_smoke",
                    "executed": False,
                    "imports": [
                        "geniml.region2vec.main.Region2VecExModel",
                        "geniml.region2vec.utils.Region2VecDataset",
                        "gtars.tokenizers.Tokenizer",
                    ],
                    "note": "do not use the broken 0.8.4 top-level region2vec export",
                },
                {
                    "stage": "train",
                    "executed": False,
                    "parameters": {
                        "embedding_dim": args.embedding_dim,
                        "epochs": args.epochs,
                        "window_size": args.window_size,
                        "min_count": args.min_count,
                        "num_cpus": args.workers,
                        "seed": args.seed,
                        "pooling_method": args.pooling,
                    },
                },
            ]
        )
    elif args.mode == "scembed":
        stages.extend(
            [
                {
                    "stage": "api_smoke",
                    "executed": False,
                    "imports": [
                        "geniml.scembed.main.ScEmbed",
                        "geniml.region2vec.utils.Region2VecDataset",
                        "gtars.tokenizers.Tokenizer",
                    ],
                    "note": (
                        "Geniml 0.8.4 ScEmbed.encode/tokenize_anndata fail with Gtars "
                        "0.10.0; use the explicit token/projection recipe in references/scembed.md"
                    ),
                },
                {
                    "stage": "train",
                    "executed": False,
                    "parameters": {
                        "embedding_dim": args.embedding_dim,
                        "epochs": args.epochs,
                        "window_size": args.window_size,
                        "min_count": args.min_count,
                        "num_cpus": args.workers,
                        "seed": args.seed,
                        "pooling_method": args.pooling,
                    },
                },
            ]
        )
    else:
        starspace_summary = None
        if starspace_dir:
            binary = local_path(str(starspace_dir / "starspace"), kind="file")
            binary_digest, binary_size = sha256_file(
                binary,
                max_bytes=args.max_file_bytes,
            )
            starspace_summary = {
                "directory": display_path(starspace_dir, 6, args.path_mode),
                "binary_sha256": binary_digest,
                "binary_size_bytes": binary_size,
                "executed": False,
            }
        else:
            warnings["starspace_binary_required"] += 1
        preprocess_template = [
            "geniml",
            "bedspace",
            "preprocess",
            "--input",
            "<LOCAL_BED_DIRECTORY>",
            "--metadata",
            "<LOCAL_METADATA_CSV>",
            "--universe",
            "<LOCAL_UNIVERSE_BED>",
            "--output",
            "<LOCAL_OUTPUT_DIRECTORY_WITH_TRAILING_SEPARATOR>",
        ]
        train_template = [
            "geniml",
            "bedspace",
            "train",
            "-s",
            "<LOCAL_STARSPACE_DIRECTORY>",
            "--input",
            "<LOCAL_OUTPUT_DIRECTORY>/train_input.txt",
            "--output",
            "<LOCAL_OUTPUT_DIRECTORY>",
            "--dim",
            str(args.embedding_dim),
            "--epochs",
            str(args.epochs),
        ]
        stages.extend(
            [
                {
                    "stage": "legacy_dependency_review",
                    "executed": False,
                    "starspace": starspace_summary,
                    "note": (
                        "StarSpace is archived; Geniml has no compatibility pin and "
                        "hard-codes 20 training threads"
                    ),
                },
                {
                    "stage": "preprocess",
                    "executed": False,
                    "argv_template": preprocess_template,
                },
                {
                    "stage": "train",
                    "executed": False,
                    "argv_template": train_template,
                    "note": "the 0.8.4 bedspace search dispatcher is not usable",
                },
            ]
        )

    stages.append(
        {
            "stage": "export_and_verify",
            "executed": False,
            "instruction": (
                "export to a fresh directory, copy the exact universe.bed, create "
                "SHA-256 provenance, and inspect without deserialization"
            ),
            "expected_local_output": _render(
                output_dir,
                "LOCAL_OUTPUT_DIRECTORY",
                args.path_mode,
            ),
        }
    )

    report = {
        "ok": not errors,
        "ready_to_execute": not errors
        and (args.mode != "bedspace" or starspace_dir is not None),
        "tool": TOOL,
        "contract": {
            "mode": args.mode,
            "assembly": args.assembly,
            "coordinate_system": "0-based-half-open",
            "split_unit": args.split_unit,
            "network_used": False,
            "packages_imported": False,
            "models_deserialized": False,
            "commands_executed": False,
        },
        "inputs": input_summary,
        "existing_model": model_summary,
        "errors": dict(sorted(errors.items())),
        "warnings": dict(sorted(warnings.items())),
        "stages": stages,
        "required_postconditions": [
            "token IDs are within the pinned tokenizer vocabulary",
            "universe bytes/order and special-token IDs match model config",
            "all output artifacts have provenance and SHA-256 checksums",
            "evaluation uses patients/donors excluded from fitting and model selection",
            "logs contain aggregate/redacted values only",
        ],
    }
    return report, 0 if not errors else 2


def main() -> int:
    args = build_parser().parse_args()
    try:
        report, exit_code = plan(args)
        print_json(report)
        return exit_code
    except (OSError, SafetyError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
