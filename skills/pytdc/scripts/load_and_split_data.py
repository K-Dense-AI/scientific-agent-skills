#!/usr/bin/env python3
"""Plan or explicitly execute one bounded PyTDC dataset split."""

from __future__ import annotations

import argparse
import importlib
import itertools
import sys
from pathlib import Path
from typing import Any

from _common import (
    CliError,
    bounded_int,
    canonical_name,
    emit_json,
    load_pytdc_metadata,
    safe_directory,
    truncate_value,
    validate_fractions,
)


# Public imports verified against the PyTDC 1.1.15 source distribution.
TASKS: dict[str, tuple[str, str, str]] = {
    "ADME": ("tdc.single_pred", "ADME", "ADME"),
    "CRISPROutcome": ("tdc.single_pred", "CRISPROutcome", "CRISPROutcome"),
    "Develop": ("tdc.single_pred", "Develop", "Develop"),
    "Epitope": ("tdc.single_pred", "Epitope", "Epitope"),
    "HTS": ("tdc.single_pred", "HTS", "HTS"),
    "Paratope": ("tdc.single_pred", "Paratope", "Paratope"),
    "QM": ("tdc.single_pred", "QM", "QM"),
    "Tox": ("tdc.single_pred", "Tox", "Tox"),
    "Yields": ("tdc.single_pred", "Yields", "Yields"),
    "AntibodyAff": ("tdc.multi_pred", "AntibodyAff", "AntibodyAff"),
    "Catalyst": ("tdc.multi_pred", "Catalyst", "Catalyst"),
    "DDI": ("tdc.multi_pred", "DDI", "DDI"),
    "DrugRes": ("tdc.multi_pred", "DrugRes", "DrugRes"),
    "DrugSyn": ("tdc.multi_pred", "DrugSyn", "DrugSyn"),
    "DTI": ("tdc.multi_pred", "DTI", "DTI"),
    "GDA": ("tdc.multi_pred", "GDA", "GDA"),
    "MTI": ("tdc.multi_pred", "MTI", "MTI"),
    "PeptideMHC": ("tdc.multi_pred", "PeptideMHC", "PeptideMHC"),
    "PPI": ("tdc.multi_pred", "PPI", "PPI"),
    "ProteinPeptide": ("tdc.multi_pred", "ProteinPeptide", "ProteinPeptide"),
    "TCREpitopeBinding": (
        "tdc.multi_pred",
        "TCREpitopeBinding",
        "TCREpitopeBinding",
    ),
    "TrialOutcome": ("tdc.multi_pred", "TrialOutcome", "TrialOutcome"),
    "MolGen": ("tdc.generation", "MolGen", "MolGen"),
    "Reaction": ("tdc.generation", "Reaction", "Reaction"),
    "RetroSyn": ("tdc.generation", "RetroSyn", "RetroSyn"),
}

SPLIT_METHODS = ("random", "scaffold", "cold_split", "combination", "time")


def normalize_columns(values: list[str] | None) -> list[str]:
    columns: list[str] = []
    for value in values or []:
        columns.extend(part.strip() for part in value.split(",") if part.strip())
    columns = list(dict.fromkeys(columns))
    if len(columns) > 8:
        raise CliError("at most eight cold-split columns may be specified")
    return columns


def validate_label(task: str, dataset: str, label: str | None) -> str | None:
    """Resolve multi-label targets from the download-free upstream registry."""
    from tdc.utils import dataset2target_lists

    choices = dataset2target_lists.get(dataset, [])
    if choices:
        if TASKS[task][0] == "tdc.generation" or task in {"DrugSyn", "TCREpitopeBinding"}:
            raise CliError(f"{task}/{dataset} has no supported label-selecting constructor")
        if label is None:
            raise CliError(f"{dataset} requires --label-name; available: {', '.join(choices[:20])}")
        return canonical_name(label, choices, "label")
    if label is not None:
        raise CliError(f"{dataset} has no target list in the reviewed package registry")
    return None


def validate_request(
    *,
    task_query: str,
    dataset_query: str,
    method: str,
    columns: list[str],
    time_column: str | None,
    metadata: Any,
) -> tuple[str, str]:
    """Resolve exact registry names and reject unsupported split combinations."""

    task = canonical_name(task_query, TASKS, "task")
    module_name, _, registry_key = TASKS[task]
    registry_key = canonical_name(registry_key, metadata.dataset_names, "task registry")
    dataset = canonical_name(
        dataset_query, metadata.dataset_names[registry_key], f"{task} dataset"
    )

    if method == "scaffold" and task not in {"ADME", "Tox", "HTS"}:
        raise CliError(
            "the official generic scaffold-split documentation limits this method "
            "to the molecule-based ADME, Tox, and HTS single-instance tasks"
        )
    if method == "cold_split":
        if module_name != "tdc.multi_pred":
            raise CliError("cold_split is only exposed by multi-instance loaders")
        if not columns:
            raise CliError("cold_split requires one or more --column values")
    elif columns:
        raise CliError("--column is only valid with --method cold_split")

    if method == "combination" and task != "DrugSyn":
        raise CliError(
            "the built-in combination split is documented for DrugSyn combination data"
        )

    if method == "time":
        if not (
            task == "DTI"
            and dataset.casefold() == "bindingdb_patent"
            and time_column
        ):
            raise CliError(
                "the verified built-in temporal case is DTI/BindingDB_Patent and "
                "requires --time-column (normally Year)"
            )
    elif time_column:
        raise CliError("--time-column is only valid with --method time")

    if module_name == "tdc.generation" and method != "random":
        raise CliError("the verified MolGen/Reaction/RetroSyn loaders expose random split")
    return task, dataset


def build_plan(
    *,
    task: str,
    dataset: str,
    method: str,
    seed: int,
    fractions: tuple[float, float, float],
    columns: list[str],
    time_column: str | None,
    data_dir: Path,
    package_version: str,
    label_name: str | None = None,
) -> dict[str, Any]:
    return {
        "action": "plan",
        "acknowledgement_required": "--execute",
        "data_directory": str(data_dir),
        "dataset": dataset,
        "label_name": label_name,
        "download_performed": False,
        "network_and_storage": (
            "Constructing the loader may contact TDC/Harvard Dataverse and write "
            "the complete dataset under data_directory."
        ),
        "package": "PyTDC",
        "package_version": package_version,
        "split": {
            "cold_columns": columns,
            "fractions": list(fractions),
            "method": method,
            "seed": seed,
            "time_column": time_column,
        },
        "task": task,
    }


def _summarize_frame(frame: Any, preview: int) -> dict[str, Any]:
    summary: dict[str, Any] = {"rows": len(frame)}
    if hasattr(frame, "columns"):
        summary["columns"] = [str(column) for column in list(frame.columns)[:100]]
    if preview and hasattr(frame, "head") and hasattr(frame, "to_dict"):
        records = frame.head(preview).to_dict(orient="records")
        summary["preview"] = truncate_value(records)
    return summary


def _audit_cold_columns(
    split: dict[str, Any], columns: list[str]
) -> dict[str, Any]:
    """Report exact-value overlap; this is not a general leakage proof."""

    audit: dict[str, Any] = {}
    partitions = ("train", "valid", "test")
    for column in columns:
        missing = [
            name
            for name in partitions
            if not hasattr(split[name], "columns") or column not in split[name].columns
        ]
        if missing:
            audit[column] = {"missing_from": missing}
            continue
        values = {
            name: set(str(value) for value in split[name][column].dropna().unique())
            for name in partitions
        }
        audit[column] = {
            "distinct_values": {name: len(items) for name, items in values.items()},
            "pairwise_overlap_counts": {
                f"{left}:{right}": len(values[left] & values[right])
                for left, right in itertools.combinations(partitions, 2)
            },
        }
    return audit


def execute_split(
    *,
    task: str,
    dataset: str,
    method: str,
    seed: int,
    fractions: tuple[float, float, float],
    columns: list[str],
    time_column: str | None,
    data_dir: Path,
    preview: int,
    package_version: str,
    label_name: str | None = None,
) -> dict[str, Any]:
    """Instantiate a loader only after the caller acknowledges the download."""

    module_name, class_name, _ = TASKS[task]
    task_class = getattr(importlib.import_module(module_name), class_name)
    constructor_kwargs = {"label_name": label_name} if label_name is not None else {}
    loader = task_class(name=dataset, path=str(data_dir), **constructor_kwargs)

    split_kwargs: dict[str, Any] = {
        "method": method,
        "seed": seed,
        "frac": list(fractions),
    }
    if method == "cold_split":
        split_kwargs["column_name"] = columns
    if method == "time":
        split_kwargs["time_column"] = time_column
    split = loader.get_split(**split_kwargs)

    expected = {"train", "valid", "test"}
    if not isinstance(split, dict) or not expected.issubset(split):
        raise CliError("PyTDC returned an unexpected split structure")

    result: dict[str, Any] = {
        "action": "executed",
        "data_directory": str(data_dir),
        "dataset": dataset,
        "label_name": label_name,
        "download_acknowledged": True,
        "package": "PyTDC",
        "package_version": package_version,
        "partitions": {
            name: _summarize_frame(split[name], preview)
            for name in ("train", "valid", "test")
        },
        "split": {
            "cold_columns": columns,
            "fractions": list(fractions),
            "method": method,
            "seed": seed,
            "time_column": time_column,
        },
        "task": task,
    }
    if method == "cold_split":
        result["cold_column_audit"] = _audit_cold_columns(split, columns)
        result["cold_column_audit_note"] = (
            "Counts cover exact values in requested columns only; zero overlap is "
            "not a blanket claim that all biological or chemical leakage is absent."
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and plan a PyTDC dataset split. The default is download-free; "
            "pass --execute to acknowledge that loader construction may download "
            "and cache the full dataset."
        )
    )
    parser.add_argument("--task", required=True, help="exact public PyTDC task class")
    parser.add_argument("--dataset", required=True, help="exact package-registry name")
    parser.add_argument("--label-name", help="required target for a multi-label dataset")
    parser.add_argument(
        "--method",
        choices=SPLIT_METHODS,
        default="random",
        help="split method (default: random)",
    )
    parser.add_argument(
        "--column",
        action="append",
        help="cold-split column; repeat or pass comma-separated values",
    )
    parser.add_argument("--time-column", help="time column for --method time")
    parser.add_argument(
        "--frac",
        nargs=3,
        type=float,
        metavar=("TRAIN", "VALID", "TEST"),
        default=(0.7, 0.1, 0.2),
        help="split fractions summing to 1 (default: 0.7 0.1 0.2)",
    )
    parser.add_argument(
        "--seed",
        type=bounded_int(0, 4_294_967_295),
        default=42,
        help="non-negative split seed (default: 42)",
    )
    parser.add_argument(
        "--data-dir",
        default=".pytdc-data",
        help="relative cache directory (default: .pytdc-data)",
    )
    parser.add_argument(
        "--preview",
        type=bounded_int(0, 10),
        default=0,
        help="include at most this many bounded rows per partition (default: 0)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="acknowledge network/storage use and construct the loader",
    )
    parser.add_argument("--output", help="write JSON to a relative workspace path")
    parser.add_argument(
        "--force", action="store_true", help="replace an existing --output file"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        fractions = validate_fractions(args.frac)
        columns = normalize_columns(args.column)
        metadata, package_version = load_pytdc_metadata()
        task, dataset = validate_request(
            task_query=args.task,
            dataset_query=args.dataset,
            method=args.method,
            columns=columns,
            time_column=args.time_column,
            metadata=metadata,
        )
        label_name = validate_label(task, dataset, args.label_name)
        data_dir = safe_directory(
            args.data_dir,
            label="data directory",
            create=args.execute,
        )
        if args.execute:
            result = execute_split(
                task=task,
                dataset=dataset,
                method=args.method,
                seed=args.seed,
                fractions=fractions,
                columns=columns,
                time_column=args.time_column,
                data_dir=data_dir,
                preview=args.preview,
                package_version=package_version,
                label_name=label_name,
            )
        else:
            result = build_plan(
                task=task,
                dataset=dataset,
                method=args.method,
                seed=args.seed,
                fractions=fractions,
                columns=columns,
                time_column=args.time_column,
                data_dir=data_dir,
                package_version=package_version,
                label_name=label_name,
            )
        emit_json(result, args.output, force=args.force)
    except (CliError, ImportError, OSError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
