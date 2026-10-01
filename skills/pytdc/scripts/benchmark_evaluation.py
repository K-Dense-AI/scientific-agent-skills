#!/usr/bin/env python3
"""Plan or explicitly evaluate user-supplied TDC benchmark predictions."""

from __future__ import annotations

import argparse
import importlib
import math
import sys
from pathlib import Path
from typing import Any

from _common import (
    CliError,
    bounded_int,
    canonical_name,
    emit_json,
    load_pytdc_metadata,
    read_json_file,
    safe_directory,
    safe_input_file,
)


# Docking is intentionally excluded: its evaluation can invoke specialized oracles.
GROUPS: dict[str, tuple[str, str]] = {
    "admet_group": ("tdc.benchmark_group", "admet_group"),
    "drugcombo_group": ("tdc.benchmark_group", "drugcombo_group"),
    "dti_dg_group": ("tdc.benchmark_group", "dti_dg_group"),
}

MAX_PREDICTION_FILE_BYTES = 50 * 1024 * 1024
MAX_PREDICTION_VALUES = 5_000_000
MAX_RUNS = 100


def benchmark_names(metadata: Any, group: str) -> list[str]:
    return [
        name
        for names in metadata.benchmark_names[group].values()
        for name in names
    ]


def validate_seeds(seeds: list[int]) -> list[int]:
    if not seeds:
        raise CliError("at least one seed is required")
    if len(seeds) > MAX_RUNS:
        raise CliError(f"at most {MAX_RUNS} seeds are allowed")
    if len(set(seeds)) != len(seeds):
        raise CliError("seeds must be unique")
    if any(seed < 0 for seed in seeds):
        raise CliError("seeds must be non-negative")
    return seeds


def _validate_values(values: Any, dataset: str) -> list[float]:
    if not isinstance(values, list) or not values:
        raise CliError(f"predictions for {dataset} must be a non-empty JSON array")
    checked: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CliError(f"predictions for {dataset} must contain only numbers")
        number = float(value)
        if not math.isfinite(number):
            raise CliError(f"predictions for {dataset} must be finite")
        checked.append(number)
    return checked


def normalize_prediction_mapping(
    value: Any,
    *,
    available: list[str],
    selected_dataset: str | None,
) -> tuple[dict[str, list[float]], int]:
    if not isinstance(value, dict) or not value:
        raise CliError("each prediction run must be a non-empty JSON object")
    normalized: dict[str, list[float]] = {}
    total = 0
    for query, predictions in value.items():
        if not isinstance(query, str):
            raise CliError("benchmark names in prediction objects must be strings")
        dataset = canonical_name(query, available, "benchmark")
        if dataset in normalized:
            raise CliError(f"duplicate benchmark after name normalization: {dataset!r}")
        if selected_dataset is not None and dataset != selected_dataset:
            raise CliError(
                f"prediction object contains {dataset!r}, but --dataset selects "
                f"{selected_dataset!r}"
            )
        checked = _validate_values(predictions, dataset)
        normalized[dataset] = checked
        total += len(checked)
    if selected_dataset is not None and selected_dataset not in normalized:
        raise CliError(f"prediction object is missing {selected_dataset!r}")
    return normalized, total


def normalize_predictions(
    payload: Any,
    *,
    mode: str,
    available: list[str],
    selected_dataset: str | None,
) -> tuple[dict[str, list[float]] | list[dict[str, list[float]]], list[int | None]]:
    """Validate the documented single-run or evaluate_many JSON shape."""

    if mode == "single":
        if isinstance(payload, dict) and "predictions" in payload:
            payload = payload["predictions"]
        mapping, total = normalize_prediction_mapping(
            payload, available=available, selected_dataset=selected_dataset
        )
        if total > MAX_PREDICTION_VALUES:
            raise CliError("prediction value limit exceeded")
        return mapping, [None]

    runs = payload.get("runs") if isinstance(payload, dict) else payload
    if not isinstance(runs, list):
        raise CliError(
            "many-run JSON must be a list or an object with a `runs` list"
        )
    if not 5 <= len(runs) <= MAX_RUNS:
        raise CliError(
            "evaluate_many requires at least five and at most "
            f"{MAX_RUNS} prediction runs"
        )

    normalized_runs: list[dict[str, list[float]]] = []
    run_seeds: list[int | None] = []
    total = 0
    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            raise CliError(f"run {index} must be a JSON object")
        if "predictions" in run:
            predictions = run["predictions"]
            seed = run.get("seed")
            if seed is not None and (
                isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            ):
                raise CliError(f"run {index} seed must be a non-negative integer")
        else:
            predictions = run
            seed = None
        mapping, count = normalize_prediction_mapping(
            predictions, available=available, selected_dataset=selected_dataset
        )
        if normalized_runs:
            if mapping.keys() != normalized_runs[0].keys():
                raise CliError("every run must contain the same benchmarks")
            if any(len(mapping[name]) != len(normalized_runs[0][name]) for name in mapping):
                raise CliError("each benchmark must have the same prediction count in every run")
        normalized_runs.append(mapping)
        run_seeds.append(seed)
        total += count
        if total > MAX_PREDICTION_VALUES:
            raise CliError("prediction value limit exceeded")

    supplied_seeds = [seed for seed in run_seeds if seed is not None]
    if supplied_seeds and len(supplied_seeds) != len(run_seeds):
        raise CliError("either provide a seed for every run or for none")
    if len(set(supplied_seeds)) != len(supplied_seeds):
        raise CliError("run seeds must be unique")
    return normalized_runs, run_seeds


def build_plan(
    *,
    group: str,
    dataset: str | None,
    seeds: list[int],
    data_dir: Path,
    package_version: str,
    metric: str | None,
    prediction_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "action": "plan",
        "acknowledgement_required": "--execute",
        "benchmark_group": group,
        "data_directory": str(data_dir),
        "dataset": dataset,
        "download_performed": False,
        "metric_from_package_metadata": metric,
        "network_and_storage": (
            "Constructing a BenchmarkGroup downloads/extracts the group archive "
            "under data_directory if no local copy is found."
        ),
        "package": "PyTDC",
        "package_version": package_version,
        "prediction_input": prediction_summary,
        "protocol_note": (
            "TDC documents at least five independent runs for leaderboard "
            "mean/standard-deviation reporting; these seeds label the plan only."
        ),
        "seeds": seeds,
    }


def execute_evaluation(
    *,
    group: str,
    dataset: str | None,
    mode: str,
    predictions: dict[str, list[float]] | list[dict[str, list[float]]],
    run_seeds: list[int | None],
    data_dir: Path,
    package_version: str,
) -> dict[str, Any]:
    module_name, class_name = GROUPS[group]
    group_class = getattr(importlib.import_module(module_name), class_name)
    benchmark_group = group_class(path=str(data_dir))
    runs = [predictions] if mode == "single" else predictions
    for name, values in runs[0].items():
        expected = len(benchmark_group.get(name)["test"])
        if any(len(run[name]) != expected for run in runs):
            raise CliError(
                f"{name} requires {expected} test predictions in exact test-row order"
            )
    if mode == "single":
        results = benchmark_group.evaluate(predictions)
        run_count = 1
    else:
        results = benchmark_group.evaluate_many(predictions)
        run_count = len(predictions)
    if isinstance(results, Exception):
        raise CliError(str(results))
    return {
        "action": "executed",
        "benchmark_group": group,
        "data_directory": str(data_dir),
        "dataset": dataset,
        "download_acknowledged": True,
        "mode": mode,
        "package": "PyTDC",
        "package_version": package_version,
        "results": results,
        "run_count": run_count,
        "run_seeds": run_seeds,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan a non-docking TDC BenchmarkGroup evaluation, or pass --execute "
            "with bounded JSON predictions to acknowledge group download/cache use. "
            "No dummy labels or predictions are generated."
        )
    )
    parser.add_argument(
        "--group",
        choices=tuple(GROUPS),
        default="admet_group",
        help="benchmark group (default: admet_group)",
    )
    parser.add_argument("--dataset", help="optional exact benchmark name")
    parser.add_argument(
        "--mode",
        choices=("single", "many"),
        default="many",
        help="call evaluate or evaluate_many (default: many)",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=bounded_int(0, 4_294_967_295),
        default=[1, 2, 3, 4, 5],
        help="independent run seeds for the plan (default: 1 2 3 4 5)",
    )
    parser.add_argument(
        "--predictions",
        help=(
            "bounded JSON input. Single mode: {dataset: [values]}. Many mode: "
            "[{dataset: [values]}, ...] or {runs: [{seed, predictions}, ...]}"
        ),
    )
    parser.add_argument(
        "--data-dir",
        default=".pytdc-benchmarks",
        help="relative benchmark cache directory (default: .pytdc-benchmarks)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="acknowledge network/storage use and evaluate supplied predictions",
    )
    parser.add_argument("--output", help="write JSON to a relative workspace path")
    parser.add_argument(
        "--force", action="store_true", help="replace an existing --output file"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.execute and not args.predictions:
        parser.error("--execute requires --predictions")

    try:
        seeds = validate_seeds(args.seeds)
        metadata, package_version = load_pytdc_metadata()
        group = canonical_name(args.group, GROUPS, "benchmark group")
        registry_group = canonical_name(
            group, metadata.benchmark_names, "package benchmark group"
        )
        available = benchmark_names(metadata, registry_group)
        dataset = (
            canonical_name(args.dataset, available, "benchmark")
            if args.dataset
            else None
        )
        metric = (
            metadata.bm_metric_names.get(registry_group, {}).get(dataset)
            if dataset
            else None
        )
        data_dir = safe_directory(
            args.data_dir,
            label="benchmark data directory",
            create=args.execute,
        )

        normalized: (
            dict[str, list[float]] | list[dict[str, list[float]]] | None
        ) = None
        run_seeds: list[int | None] = []
        prediction_summary: dict[str, Any] | None = None
        if args.predictions:
            prediction_path = safe_input_file(
                args.predictions,
                max_bytes=MAX_PREDICTION_FILE_BYTES,
                label="prediction input",
            )
            payload = read_json_file(prediction_path)
            normalized, run_seeds = normalize_predictions(
                payload,
                mode=args.mode,
                available=available,
                selected_dataset=dataset,
            )
            prediction_summary = {
                "mode": args.mode,
                "path": str(prediction_path),
                "run_count": 1 if args.mode == "single" else len(normalized),
                "validated": True,
            }

        if args.execute:
            if normalized is None:
                raise CliError("--execute requires validated predictions")
            result = execute_evaluation(
                group=group,
                dataset=dataset,
                mode=args.mode,
                predictions=normalized,
                run_seeds=run_seeds,
                data_dir=data_dir,
                package_version=package_version,
            )
        else:
            result = build_plan(
                group=group,
                dataset=dataset,
                seeds=seeds,
                data_dir=data_dir,
                package_version=package_version,
                metric=metric,
                prediction_summary=prediction_summary,
            )
        emit_json(result, args.output, force=args.force)
    except (CliError, ImportError, OSError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
