#!/usr/bin/env python3
"""Safely plan PyTDC molecule data access or bounded oracle scoring."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from pathlib import Path
from typing import Any, Iterator

from _common import (
    CliError,
    bounded_int,
    canonical_name,
    emit_json,
    load_pytdc_metadata,
    safe_directory,
    safe_input_file,
    truncate_value,
    validate_fractions,
)


LOCAL_SCALAR_ORACLES = {"qed"}
# LogP and SA are listed as "trivial" upstream, but their 1.1.15 implementation
# lazily downloads the fpscores artifact through calculateScore().
CHECKPOINT_ORACLES = {
    "logp",
    "sa",
    "drd2",
    "gsk3b",
    "jnk3",
    "cyp3a4_veith",
}
MAX_SMILES_FILE_BYTES = 1 * 1024 * 1024


@contextlib.contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    original = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


def classify_oracle(metadata: Any, query: str) -> tuple[str, str]:
    name = canonical_name(query, metadata.oracle_names, "oracle")
    if name in LOCAL_SCALAR_ORACLES:
        return name, "local_scalar"
    if name in CHECKPOINT_ORACLES:
        return name, "checkpoint_download"
    if name in set(metadata.download_oracle_names):
        return name, "unsupported_checkpoint"
    if name in set(metadata.distribution_oracles):
        return name, "distribution_metric"
    if name in set(metadata.download_receptor_oracle_name):
        return name, "receptor_or_docking"
    if name in set(metadata.synthetic_oracle_name):
        return name, "remote_service"
    return name, "specialized_or_composite"


def load_smiles(
    direct: list[str] | None,
    input_path: str | None,
    *,
    max_molecules: int,
) -> list[str]:
    values = list(direct or [])
    if input_path:
        path = safe_input_file(
            input_path,
            max_bytes=MAX_SMILES_FILE_BYTES,
            label="SMILES input",
        )
        with path.open("r", encoding="utf-8") as handle:
            values.extend(line.strip() for line in handle if line.strip())
    if not values:
        raise CliError("provide at least one --smiles or --input line")
    if len(values) > max_molecules:
        raise CliError(
            f"received {len(values)} molecules; --max-molecules is {max_molecules}"
        )
    if any(len(value) > 4096 for value in values):
        raise CliError("each SMILES string is limited to 4096 characters")
    return values


def score_plan(
    *,
    oracle: str,
    category: str,
    smiles_count: int,
    runtime_dir: Path,
    package_version: str,
    download_acknowledged: bool,
) -> dict[str, Any]:
    return {
        "action": "plan",
        "acknowledgement_required": (
            "--execute"
            if category == "local_scalar"
            else "--execute --download (only supported checkpoint oracles)"
        ),
        "download_acknowledged": download_acknowledged,
        "download_performed": False,
        "oracle": oracle,
        "oracle_category": category,
        "package": "PyTDC",
        "package_version": package_version,
        "runtime_directory": str(runtime_dir),
        "score_direction": "not assumed; consult the exact oracle documentation",
        "smiles_count": smiles_count,
    }


def execute_scores(
    *,
    oracle_name: str,
    category: str,
    smiles: list[str],
    runtime_dir: Path,
    download_acknowledged: bool,
    package_version: str,
) -> dict[str, Any]:
    if category == "checkpoint_download" and not download_acknowledged:
        raise CliError(
            f"{oracle_name} may download a model checkpoint; pass --download "
            "together with --execute to acknowledge this"
        )
    if category not in {"local_scalar", "checkpoint_download"}:
        raise CliError(
            "this helper executes only local QED or the explicitly acknowledged "
            "LogP/SA/DRD2/GSK3B/JNK3/CYP3A4_Veith checkpoint-backed oracles; "
            "remote services, docking, distribution, and composite oracles are "
            "intentionally not called"
        )

    from tdc import Oracle  # Lazy optional import.
    from rdkit import Chem

    # Empty SMILES parses as a zero-atom molecule; it is not a scorable structure.
    valid = []
    for value in smiles:
        molecule = Chem.MolFromSmiles(value)
        valid.append(molecule is not None and molecule.GetNumAtoms() > 0)
    valid_smiles = [value for value, ok in zip(smiles, valid) if ok]

    with _working_directory(runtime_dir):
        if valid_smiles:
            oracle = Oracle(name=oracle_name, num_max_call=len(valid_smiles))
            scores = oracle(valid_smiles)
        else:
            scores = []
    if not isinstance(scores, list) or len(scores) != len(valid_smiles):
        raise CliError("PyTDC returned an unexpected oracle result shape")
    score_iter = iter(scores)

    return {
        "action": "executed",
        "download_acknowledged": download_acknowledged,
        "oracle": oracle_name,
        "oracle_category": category,
        "package": "PyTDC",
        "package_version": package_version,
        "results": [
            {
                "index": index,
                "valid": ok,
                "score": truncate_value(next(score_iter)) if ok else None,
                "smiles": truncate_value(smiles_value),
            }
            for index, (smiles_value, ok) in enumerate(zip(smiles, valid))
        ],
        "runtime_directory": str(runtime_dir),
        "score_direction": "not assumed; results preserve input order",
    }


def dataset_plan(
    *,
    dataset: str,
    data_dir: Path,
    seed: int,
    fractions: tuple[float, float, float],
    package_version: str,
    download_acknowledged: bool,
) -> dict[str, Any]:
    return {
        "action": "plan",
        "acknowledgement_required": "--execute --download",
        "data_directory": str(data_dir),
        "dataset": dataset,
        "download_acknowledged": download_acknowledged,
        "download_performed": False,
        "network_and_storage": (
            "MolGen construction may download a complete, potentially very large "
            "molecule corpus to data_directory."
        ),
        "package": "PyTDC",
        "package_version": package_version,
        "split": {
            "fractions": list(fractions),
            "method": "random",
            "seed": seed,
        },
    }


def execute_dataset(
    *,
    dataset: str,
    data_dir: Path,
    seed: int,
    fractions: tuple[float, float, float],
    preview: int,
    package_version: str,
) -> dict[str, Any]:
    from tdc.generation import MolGen  # Lazy optional import.

    loader = MolGen(name=dataset, path=str(data_dir))
    split = loader.get_split(method="random", seed=seed, frac=list(fractions))
    expected = {"train", "valid", "test"}
    if not isinstance(split, dict) or not expected.issubset(split):
        raise CliError("PyTDC returned an unexpected MolGen split structure")

    partitions: dict[str, Any] = {}
    for name in ("train", "valid", "test"):
        frame = split[name]
        summary: dict[str, Any] = {
            "columns": [str(column) for column in list(frame.columns)[:100]],
            "rows": len(frame),
        }
        if preview:
            summary["preview"] = truncate_value(
                frame.head(preview).to_dict(orient="records")
            )
        partitions[name] = summary

    return {
        "action": "executed",
        "data_directory": str(data_dir),
        "dataset": dataset,
        "download_acknowledged": True,
        "package": "PyTDC",
        "package_version": package_version,
        "partitions": partitions,
        "split": {
            "fractions": list(fractions),
            "method": "random",
            "seed": seed,
        },
    }


def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", help="write JSON to a relative workspace path")
    parser.add_argument(
        "--force", action="store_true", help="replace an existing --output file"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or explicitly execute bounded PyTDC molecular workflows. This "
            "helper does not generate molecules and never calls remote-service or "
            "docking oracles."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    score = subparsers.add_parser(
        "score",
        help="plan or run bounded scalar-oracle scoring",
        description=(
            "Score bounded user-supplied SMILES. QED is local. LogP, SA, and four "
            "model-backed oracles require --download because they can fetch an "
            "artifact/checkpoint."
        ),
    )
    score.add_argument("--oracle", default="QED", help="exact package oracle name")
    score.add_argument(
        "--smiles", action="append", help="SMILES string; repeat for multiple inputs"
    )
    score.add_argument(
        "--input", help="relative UTF-8 file with one SMILES string per line"
    )
    score.add_argument(
        "--max-molecules",
        type=bounded_int(1, 500),
        default=100,
        help="maximum accepted molecules (default: 100; max: 500)",
    )
    score.add_argument(
        "--runtime-dir",
        default=".pytdc-oracles",
        help="relative directory for any acknowledged checkpoint (default: .pytdc-oracles)",
    )
    score.add_argument(
        "--execute", action="store_true", help="execute the bounded scoring call"
    )
    score.add_argument(
        "--download",
        action="store_true",
        help="acknowledge a supported model-checkpoint download",
    )
    _add_output_arguments(score)

    dataset = subparsers.add_parser(
        "dataset",
        help="plan or load/split a MolGen corpus",
        description=(
            "Plan a MolGen random split. Execution requires both --execute and "
            "--download because these corpora can be large."
        ),
    )
    dataset.add_argument("--dataset", required=True, help="exact MolGen registry name")
    dataset.add_argument(
        "--frac",
        nargs=3,
        type=float,
        metavar=("TRAIN", "VALID", "TEST"),
        default=(0.7, 0.1, 0.2),
        help="split fractions summing to 1 (default: 0.7 0.1 0.2)",
    )
    dataset.add_argument(
        "--seed",
        type=bounded_int(0, 4_294_967_295),
        default=42,
        help="non-negative random split seed (default: 42)",
    )
    dataset.add_argument(
        "--data-dir",
        default=".pytdc-molgen",
        help="relative dataset cache directory (default: .pytdc-molgen)",
    )
    dataset.add_argument(
        "--preview",
        type=bounded_int(0, 5),
        default=0,
        help="include at most this many bounded rows per partition (default: 0)",
    )
    dataset.add_argument(
        "--execute", action="store_true", help="construct and split the MolGen loader"
    )
    dataset.add_argument(
        "--download",
        action="store_true",
        help="acknowledge potentially large dataset download/storage",
    )
    _add_output_arguments(dataset)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        metadata, package_version = load_pytdc_metadata()
        if args.command == "score":
            smiles = load_smiles(
                args.smiles, args.input, max_molecules=args.max_molecules
            )
            oracle, category = classify_oracle(metadata, args.oracle)
            runtime_dir = safe_directory(
                args.runtime_dir,
                label="oracle runtime directory",
                create=args.execute,
            )
            if args.execute:
                result = execute_scores(
                    oracle_name=oracle,
                    category=category,
                    smiles=smiles,
                    runtime_dir=runtime_dir,
                    download_acknowledged=args.download,
                    package_version=package_version,
                )
            else:
                result = score_plan(
                    oracle=oracle,
                    category=category,
                    smiles_count=len(smiles),
                    runtime_dir=runtime_dir,
                    package_version=package_version,
                    download_acknowledged=args.download,
                )
        else:
            fractions = validate_fractions(args.frac)
            registry_key = canonical_name("MolGen", metadata.dataset_names, "task")
            dataset = canonical_name(
                args.dataset, metadata.dataset_names[registry_key], "MolGen dataset"
            )
            data_dir = safe_directory(
                args.data_dir,
                label="MolGen data directory",
                create=args.execute,
            )
            if args.execute:
                if not args.download:
                    raise CliError(
                        "MolGen execution may download a large corpus; pass "
                        "--download together with --execute to acknowledge it"
                    )
                result = execute_dataset(
                    dataset=dataset,
                    data_dir=data_dir,
                    seed=args.seed,
                    fractions=fractions,
                    preview=args.preview,
                    package_version=package_version,
                )
            else:
                result = dataset_plan(
                    dataset=dataset,
                    data_dir=data_dir,
                    seed=args.seed,
                    fractions=fractions,
                    package_version=package_version,
                    download_acknowledged=args.download,
                )
        emit_json(result, args.output, force=args.force)
    except (CliError, ImportError, OSError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
