#!/usr/bin/env python3
"""Score the same model under several splits and show how far the number moves.

A single metric is not evidence until you know which split produced it.  This
CLI fits one fixed learner on random, scaffold, time, and group splits of the
same table, scores each against a dummy baseline, and prints the comparison
beside the leakage counts that explain any gap.

The point is not that the scaffold number is "the real one".  It answers a
different question -- can the model rank *new chemotypes* -- and a report that
quotes only one of them is making a claim it did not test.  Run this before the
number goes into a paper, a report, or a go/no-go decision, and report the split
name next to the metric.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import _common
from _common import CliError, print_to_stderr


DEFAULT_SEEDS = "0,1,2"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="split_compare.py",
        description=(
            "Compare random, scaffold, time, and group splits of one molecule table "
            "under a fixed model, with a dummy baseline and leakage counts."
        ),
        epilog=(
            "Example: split_compare.py --input actives.csv --target-col pIC50 "
            "--task regression --seeds 0,1,2"
        ),
    )
    parser.add_argument("--input", required=True, help="CSV or TSV molecule table")
    parser.add_argument("--smiles-col", help="structure column (guessed when omitted)")
    parser.add_argument("--target-col", help="activity column (guessed when omitted)")
    parser.add_argument(
        "--task",
        choices=("regression", "classification"),
        default="regression",
        help="regression scores a continuous activity; classification needs --active-threshold",
    )
    parser.add_argument(
        "--active-threshold",
        type=_common.finite_float,
        help="value at or above which a compound counts as active (classification only)",
    )
    parser.add_argument("--time-col", help="date or year column; adds a time split")
    parser.add_argument(
        "--group-col",
        help="series/compound/cluster column; adds a split that keeps each group whole",
    )
    parser.add_argument(
        "--seeds",
        type=_common.seed_list,
        default=_common.seed_list(DEFAULT_SEEDS),
        help=f"comma-separated seeds, repeated over splits (default {DEFAULT_SEEDS})",
    )
    parser.add_argument(
        "--test-size",
        type=_common.fraction,
        default=_common.DEFAULT_TEST_SIZE,
        help="fraction held out (default 0.2)",
    )
    parser.add_argument(
        "--radius",
        type=_common.bounded_int(1, 4),
        default=_common.DEFAULT_FINGERPRINT_RADIUS,
        help="Morgan fingerprint radius (default 2)",
    )
    parser.add_argument(
        "--bits",
        type=_common.bounded_int(64, 16384),
        default=_common.DEFAULT_FINGERPRINT_BITS,
        help="Morgan fingerprint length (default 2048)",
    )
    parser.add_argument(
        "--duplicate-threshold",
        type=_common.fraction,
        default=_common.DEFAULT_DUPLICATE_THRESHOLD,
        help="Tanimoto at or above which a pair counts as a near-duplicate (default 0.8)",
    )
    parser.add_argument(
        "--n-estimators",
        type=_common.bounded_int(16, 2048),
        default=256,
        help="trees in the comparison forest (default 256)",
    )
    parser.add_argument(
        "--bootstrap",
        type=_common.bounded_int(0, 10000),
        default=0,
        help="bootstrap resamples for a 95%% interval on each metric (0 disables)",
    )
    parser.add_argument("--output", help="write the JSON report to this file")
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output file"
    )
    return parser


def prepare_table(arguments: argparse.Namespace) -> dict[str, Any]:
    """Load the table, canonicalize it, and report what was dropped and why."""

    numpy = _common.require_numpy()
    frame = _common.read_table(arguments.input, label="the molecule table")

    smiles_column = _common.resolve_column(
        frame, arguments.smiles_col, kind="smiles", aliases=_common.SMILES_ALIASES
    )
    target_column = _common.resolve_column(
        frame, arguments.target_col, kind="target", aliases=_common.TARGET_ALIASES
    )

    canonical, failures = _common.canonicalize(frame[smiles_column].tolist())
    raw_targets = frame[target_column].tolist()

    keep: list[int] = []
    dropped_unparsed = 0
    dropped_no_target = 0
    for index, structure in enumerate(canonical):
        if structure is None:
            dropped_unparsed += 1
            continue
        value = raw_targets[index]
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            dropped_no_target += 1
            continue
        if not numpy.isfinite(numeric):
            dropped_no_target += 1
            continue
        keep.append(index)

    if len(keep) < 10:
        raise CliError(
            f"only {len(keep)} usable rows remain after parsing structures and targets; "
            "a split comparison needs at least 10"
        )

    smiles = [canonical[index] for index in keep]
    targets = [float(raw_targets[index]) for index in keep]

    time_values = None
    if arguments.time_col:
        if arguments.time_col not in frame.columns:
            raise CliError(f"column {arguments.time_col!r} (--time-col) is not in the table")
        time_values = [frame[arguments.time_col].tolist()[index] for index in keep]

    group_values = None
    if arguments.group_col:
        if arguments.group_col not in frame.columns:
            raise CliError(f"column {arguments.group_col!r} (--group-col) is not in the table")
        group_values = [frame[arguments.group_col].tolist()[index] for index in keep]

    duplicates_removed = 0
    unique_smiles: list[str] = []
    unique_targets: list[float] = []
    unique_times: list[Any] = []
    unique_groups: list[Any] = []
    seen: dict[str, int] = {}
    for position, structure in enumerate(smiles):
        if structure in seen:
            duplicates_removed += 1
            # Repeated measurements of one compound are legitimate data, but a
            # split comparison cannot use them: the same structure on both sides
            # measures memorization.  They are collapsed to their mean and the
            # count is reported rather than hidden.
            previous = seen[structure]
            unique_targets[previous] = (unique_targets[previous] + targets[position]) / 2.0
            continue
        seen[structure] = len(unique_smiles)
        unique_smiles.append(structure)
        unique_targets.append(targets[position])
        if time_values is not None:
            unique_times.append(time_values[position])
        if group_values is not None:
            unique_groups.append(group_values[position])

    if len(unique_smiles) < 10:
        raise CliError(
            f"only {len(unique_smiles)} distinct structures remain; a split comparison "
            "needs at least 10"
        )

    if arguments.task == "classification":
        labels = _common.as_classification_labels(
            unique_targets, threshold=arguments.active_threshold
        )
        targets = [float(label) for label in labels]
    else:
        targets = unique_targets

    return {
        "smiles": unique_smiles,
        "targets": targets,
        "times": unique_times if time_values is not None else None,
        "groups": unique_groups if group_values is not None else None,
        "columns": {
            "smiles": smiles_column,
            "target": target_column,
            "time": arguments.time_col,
            "group": arguments.group_col,
        },
        "cleaning": {
            "rows_in_file": int(len(frame)),
            "rows_used": len(unique_smiles),
            "dropped_unparseable_structure": dropped_unparsed,
            "dropped_missing_target": dropped_no_target,
            "duplicate_structures_collapsed": duplicates_removed,
            "unparseable_examples": failures[:5],
        },
    }


def time_split_indices(times: list[Any], *, test_size: float) -> tuple[list[int], list[int]]:
    """Hold out the latest ``test_size`` fraction, ordered by the time column.

    Ties and unparseable timestamps fall back to string ordering, which keeps the
    split deterministic; the caller is expected to check that the column really
    is chronological before reading anything into the result.
    """

    if len(times) < 2:
        raise CliError("a time split needs at least 2 rows")
    order = sorted(range(len(times)), key=lambda index: (str(times[index]), index))
    cut = max(1, int(round(len(order) * (1.0 - test_size))))
    train = order[:cut]
    test = order[cut:]
    if not train or not test:
        raise CliError("the time split left one side empty; adjust --test-size")
    return sorted(train), sorted(test)


def score_split(
    data: dict[str, Any],
    features: Any,
    train: list[int],
    test: list[int],
    arguments: argparse.Namespace,
    *,
    seed: int,
) -> dict[str, Any]:
    """Fit, score, and describe leakage for one split at one seed."""

    numpy = _common.require_numpy()
    smiles = data["smiles"]
    targets = data["targets"]

    train_smiles = [smiles[index] for index in train]
    test_smiles = [smiles[index] for index in test]
    train_targets = [targets[index] for index in train]
    test_targets = [targets[index] for index in test]

    predictions = _common.fit_predict(
        features[train],
        train_targets,
        features[test],
        task=arguments.task,
        seed=seed,
        n_estimators=arguments.n_estimators,
    )

    if arguments.task == "regression":
        train_mean = float(numpy.mean(train_targets))
        model_metrics = _common.regression_metrics(
            test_targets, predictions["model"], train_mean=train_mean
        )
        baseline_metrics = _common.regression_metrics(
            test_targets, predictions["baseline"], train_mean=train_mean
        )
        headline = "rmse"
    else:
        model_metrics = _common.classification_metrics(test_targets, predictions["model"])
        baseline_metrics = _common.classification_metrics(test_targets, predictions["baseline"])
        headline = "roc_auc"

    if arguments.bootstrap:
        if arguments.task == "regression":
            interval = _common.bootstrap_interval(
                lambda truth, prediction: float(
                    numpy.sqrt(numpy.mean((truth - prediction) ** 2))
                ),
                test_targets,
                predictions["model"],
                resamples=arguments.bootstrap,
                seed=seed,
            )
        else:
            sklearn_metrics = _common.require_sklearn()["metrics"]
            interval = _common.bootstrap_interval(
                lambda truth, prediction: (
                    float(sklearn_metrics.roc_auc_score(truth, prediction))
                    if len(numpy.unique(truth)) > 1
                    else None
                ),
                test_targets,
                predictions["model"],
                resamples=arguments.bootstrap,
                seed=seed,
            )
        model_metrics["interval"] = interval

    return {
        "seed": seed,
        "n_train": len(train),
        "n_test": len(test),
        "headline_metric": headline,
        "model": model_metrics,
        "dummy_baseline": baseline_metrics,
        "leakage": {
            **{
                "exact": _common.duplicate_leakage(train_smiles, test_smiles),
                "near_duplicate": _common.near_duplicate_leakage(
                    train_smiles,
                    test_smiles,
                    threshold=arguments.duplicate_threshold,
                    radius=arguments.radius,
                    bits=arguments.bits,
                ),
            },
            "scaffold": _common.scaffold_overlap(train_smiles, test_smiles),
        },
    }


def summarise(runs: list[dict[str, Any]], *, headline: str) -> dict[str, Any]:
    """Average a metric across seeds and report its spread, not just its mean."""

    numpy = _common.require_numpy()
    values = [
        run["model"][headline] for run in runs if run["model"].get(headline) is not None
    ]
    baseline_values = [
        run["dummy_baseline"][headline]
        for run in runs
        if run["dummy_baseline"].get(headline) is not None
    ]
    summary: dict[str, Any] = {
        "runs": len(runs),
        "headline_metric": headline,
        "n_test_mean": float(numpy.mean([run["n_test"] for run in runs])),
    }
    if values:
        summary["model_mean"] = float(numpy.mean(values))
        summary["model_min"] = float(numpy.min(values))
        summary["model_max"] = float(numpy.max(values))
    else:
        summary["model_mean"] = None
        summary["model_min"] = None
        summary["model_max"] = None
    summary["baseline_mean"] = float(numpy.mean(baseline_values)) if baseline_values else None
    summary["near_duplicate_mean"] = float(
        numpy.mean([run["leakage"]["near_duplicate"]["near_duplicate_compounds"] for run in runs])
    )
    summary["exact_overlap_mean"] = float(
        numpy.mean([run["leakage"]["exact"]["exact_overlap_compounds"] for run in runs])
    )
    summary["shared_scaffold_mean"] = float(
        numpy.mean([run["leakage"]["scaffold"]["shared_scaffolds"] for run in runs])
    )
    return summary


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    """Score every requested split and assemble the comparison report."""

    data = prepare_table(arguments)
    features = _common.morgan_feature_matrix(
        data["smiles"], radius=arguments.radius, bits=arguments.bits
    )

    strategies: list[str] = ["random", "scaffold"]
    if data["times"] is not None:
        strategies.append("time")
    if data["groups"] is not None:
        strategies.append("group")

    results: dict[str, Any] = {}
    for strategy in strategies:
        runs: list[dict[str, Any]] = []
        for seed in arguments.seeds:
            if strategy == "random":
                train, test = _common.random_split_indices(
                    len(data["smiles"]), test_size=arguments.test_size, seed=seed
                )
            elif strategy == "scaffold":
                train, test = _common.scaffold_split_indices(
                    data["smiles"], test_size=arguments.test_size, seed=seed
                )
            elif strategy == "group":
                train, test = _common.group_split_indices(
                    data["groups"], test_size=arguments.test_size, seed=seed
                )
            else:
                train, test = time_split_indices(data["times"], test_size=arguments.test_size)
            runs.append(score_split(data, features, train, test, arguments, seed=seed))
        headline = runs[0]["headline_metric"]
        results[strategy] = {"runs": runs, "summary": summarise(runs, headline=headline)}

    comparison = build_comparison(results, strategies)

    return {
        "input": str(Path(arguments.input)),
        "task": arguments.task,
        "active_threshold": arguments.active_threshold,
        "fingerprint": {"radius": arguments.radius, "bits": arguments.bits},
        "test_size": arguments.test_size,
        "seeds": arguments.seeds,
        "columns": data["columns"],
        "cleaning": data["cleaning"],
        "splits": results,
        "comparison": comparison,
        "reading": reading_notes(comparison),
    }


def build_comparison(results: dict[str, Any], strategies: list[str]) -> dict[str, Any]:
    """Express each split's headline metric relative to the random split."""

    headline = results[strategies[0]]["summary"]["headline_metric"]
    reference = results["random"]["summary"]["model_mean"]
    comparison: dict[str, Any] = {"headline_metric": headline, "reference_split": "random"}
    for strategy in strategies:
        summary = results[strategy]["summary"]
        value = summary["model_mean"]
        entry: dict[str, Any] = {
            "model_mean": value,
            "baseline_mean": summary["baseline_mean"],
            "model_min": summary["model_min"],
            "model_max": summary["model_max"],
            "beats_dummy": (
                None
                if value is None or summary["baseline_mean"] is None
                else bool(value > summary["baseline_mean"])
                if headline in {"roc_auc", "pr_auc", "r2"}
                else bool(value < summary["baseline_mean"])
            ),
        }
        if strategy != "random" and value is not None and reference is not None:
            entry["difference_vs_random"] = value - reference
            if reference != 0:
                entry["relative_to_random"] = (value - reference) / abs(reference)
        comparison[strategy] = entry
    return comparison


def reading_notes(comparison: dict[str, Any]) -> list[str]:
    """State what the numbers do and do not support."""

    notes = [
        "A metric is only interpretable together with the split that produced it; "
        "quote the split name next to every number.",
        "The random split answers whether new compounds of known chemistry can be "
        "ranked. The scaffold split answers whether new chemotypes can be.",
    ]
    scaffold = comparison.get("scaffold") or {}
    difference = scaffold.get("difference_vs_random")
    headline = comparison["headline_metric"]
    if difference is None:
        notes.append("Only one split was scored, so no comparison is available.")
        return notes

    if headline in {"roc_auc", "pr_auc", "r2"}:
        if difference < 0:
            notes.append(
                f"The scaffold split scores {abs(difference):.3f} lower on {headline} than the "
                "random split. Report the scaffold number for any claim about new chemistry."
            )
        else:
            notes.append(
                f"The scaffold split does not score lower on {headline} here. That is worth "
                "checking before believing it: confirm the split really separated scaffolds "
                "(see splits.scaffold.shared_scaffolds) and that the table is large enough."
            )
    else:
        if difference > 0:
            notes.append(
                f"The scaffold split error is {abs(difference):.3f} higher on {headline} than "
                "the random split. Report the scaffold number for any claim about new chemistry."
            )
        else:
            notes.append(
                f"The scaffold split does not score worse on {headline} here. Check "
                "splits.scaffold.shared_scaffolds before believing it."
            )

    for strategy in ("random", "scaffold"):
        entry = comparison.get(strategy) or {}
        if entry.get("beats_dummy") is False:
            notes.append(
                f"On the {strategy} split the model does not beat the dummy baseline, so none "
                "of its metrics support a claim about activity."
            )
    return notes


def print_summary(document: dict[str, Any]) -> None:
    """Print the comparison to stderr, leaving stdout for the JSON document."""

    headline = document["comparison"]["headline_metric"]
    rows: list[list[Any]] = []
    for strategy in ("random", "scaffold", "time", "group"):
        entry = document["comparison"].get(strategy)
        if entry is None:
            continue
        rows.append([
            strategy,
            _common.format_number(entry["model_mean"]),
            _common.format_number(entry["model_min"]),
            _common.format_number(entry["model_max"]),
            _common.format_number(entry["baseline_mean"]),
            "-" if entry.get("difference_vs_random") is None
            else _common.format_number(entry["difference_vs_random"]),
            entry["beats_dummy"],
        ])

    print_to_stderr(f"headline metric: {headline}   rows used: {document['cleaning']['rows_used']}")
    print_to_stderr()
    print_to_stderr(_common.format_table(
        ["split", "model", "min", "max", "dummy", "vs random", "beats dummy"], rows
    ))
    print_to_stderr()
    for note in document["reading"]:
        print_to_stderr(f"- {note}")


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        document = run(arguments)
        print_summary(document)
        _common.emit_json(document, output=arguments.output, force=arguments.force)
    except CliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
