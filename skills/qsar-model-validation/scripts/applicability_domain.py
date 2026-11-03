#!/usr/bin/env python3
"""Flag test compounds that fall outside the chemistry the model was trained on.

A QSAR or ADMET model is only defined over the region of chemical space its
training set covers.  Outside that region it does not extrapolate gracefully; it
returns a number with the same confident formatting as an interpolation and no
indication that anything is wrong.  This CLI marks each test compound against a
training set, then -- when the test targets are known -- scores the model
separately inside and outside the domain, which is the only honest way to say
how much the outside predictions are worth.

The similarity threshold defaults to a value derived from the training set
itself rather than a hardcoded constant, because "how similar is similar enough"
depends on how diverse the training chemistry is.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import _common
from _common import CliError, print_to_stderr


#: Percentile of the training set's own nearest-neighbour similarity distribution
#: used as the default cut.  A test compound less similar to training than the
#: least-similar 5% of training compounds are to each other is outside the domain
#: by the training set's own standard.
DEFAULT_PERCENTILE = 5.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="applicability_domain.py",
        description=(
            "Mark test compounds as inside or outside the model's applicability domain, "
            "and score the model separately on each side."
        ),
        epilog=(
            "Example: applicability_domain.py --train train.csv --test test.csv "
            "--target-col pIC50 --method similarity"
        ),
    )
    parser.add_argument("--train", required=True, help="CSV or TSV with the training compounds")
    parser.add_argument("--test", required=True, help="CSV or TSV with the compounds to judge")
    parser.add_argument("--smiles-col", help="structure column (guessed when omitted)")
    parser.add_argument("--target-col", help="activity column, when the test set carries one")
    parser.add_argument(
        "--prediction-col",
        help=(
            "predicted activity column in the test table; with --target-col this adds "
            "performance scored separately inside and outside the domain"
        ),
    )
    parser.add_argument(
        "--train-target-col",
        help="activity column in the training table, when it differs from --target-col",
    )
    parser.add_argument(
        "--method",
        choices=("similarity", "descriptor-range", "consensus"),
        default="similarity",
        help=(
            "similarity: nearest-neighbour Tanimoto to training; descriptor-range: outside the "
            "training min/max box on any descriptor; consensus: flagged by either (default similarity)"
        ),
    )
    parser.add_argument(
        "--threshold",
        type=_common.fraction,
        help=(
            "similarity at or below which a compound is out of domain; default is the "
            f"{DEFAULT_PERCENTILE:.0f}th percentile of the training set's own similarity distribution"
        ),
    )
    parser.add_argument(
        "--percentile",
        type=_common.finite_float,
        default=DEFAULT_PERCENTILE,
        help=f"percentile used when --threshold is omitted (default {DEFAULT_PERCENTILE})",
    )
    parser.add_argument(
        "--task",
        choices=("regression", "classification"),
        default="regression",
        help="only used when a target column is available (default regression)",
    )
    parser.add_argument(
        "--active-threshold",
        type=_common.finite_float,
        help="value at or above which a compound counts as active (classification only)",
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
        "--list-out",
        type=_common.bounded_int(0, 500),
        default=20,
        help="how many out-of-domain compounds to list in the report (default 20)",
    )
    parser.add_argument("--output", help="write the JSON report to this file")
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output file"
    )
    return parser


def _numeric_column(frame: Any, column: str | None, *, kind: str) -> list[float] | None:
    """Return a column coerced to floats, or None when no column was asked for."""

    if column is None:
        return None
    resolved = _common.resolve_column(frame, column, kind=kind, aliases=_common.TARGET_ALIASES)
    values: list[float] = []
    for value in frame[resolved].tolist():
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            values.append(float("nan"))
    return values


def load_structures(
    path: str,
    arguments: argparse.Namespace,
    *,
    label: str,
    target_column: str | None,
    prediction_column: str | None = None,
) -> dict[str, Any]:
    """Read one table and return its canonical structures, targets, and predictions."""

    numpy = _common.require_numpy()
    frame = _common.read_table(path, label=label)
    smiles_column = _common.resolve_column(
        frame, arguments.smiles_col, kind="smiles", aliases=_common.SMILES_ALIASES
    )

    targets = _numeric_column(frame, target_column, kind="target")
    predictions = _numeric_column(frame, prediction_column, kind="prediction")
    if predictions is not None and targets is None:
        raise CliError(
            "--prediction-col needs --target-col as well, otherwise there is nothing to "
            "score the predictions against"
        )

    canonical, failures = _common.canonicalize(frame[smiles_column].tolist())
    keep = [index for index, structure in enumerate(canonical) if structure is not None]
    if not keep:
        raise CliError(f"{label} has no parseable structures")
    for name, column in (("target", targets), ("prediction", predictions)):
        if column is not None:
            keep = [index for index in keep if numpy.isfinite(column[index])]
            if not keep:
                raise CliError(
                    f"{label} has no rows with a structure and a numeric {name}; "
                    "drop the missing values before judging the domain"
                )

    return {
        "smiles": [canonical[index] for index in keep],
        "targets": [targets[index] for index in keep] if targets is not None else None,
        "predictions": (
            [predictions[index] for index in keep] if predictions is not None else None
        ),
        "rejected": len(failures),
        "rejected_examples": failures[:5],
        "rows_used": len(keep),
    }


def max_similarity_to_train(train_smiles: list[str], test_smiles: list[str],
                            *, radius: int, bits: int) -> list[float]:
    """Return each test compound's highest Tanimoto similarity to any training compound."""

    from rdkit.Chem import DataStructs  # noqa: PLC0415 - deliberately lazy

    train_fingerprints = _common.morgan_fingerprints(train_smiles, radius=radius, bits=bits)
    test_fingerprints = _common.morgan_fingerprints(test_smiles, radius=radius, bits=bits)
    return [
        max(DataStructs.BulkTanimotoSimilarity(fingerprint, train_fingerprints))
        for fingerprint in test_fingerprints
    ]


def training_self_similarity(train_smiles: list[str], *, radius: int, bits: int) -> list[float]:
    """Each training compound's nearest neighbour among the *other* training compounds.

    This is what makes the default threshold data-driven: it is a statement about
    how internally diverse this particular training set is, not an arbitrary 0.5.
    A set of close analogues yields a high cut; a broad set yields a low one.
    """

    from rdkit.Chem import DataStructs  # noqa: PLC0415 - deliberately lazy

    fingerprints = _common.morgan_fingerprints(train_smiles, radius=radius, bits=bits)
    scores: list[float] = []
    for position, fingerprint in enumerate(fingerprints):
        others = fingerprints[:position] + fingerprints[position + 1:]
        if not others:
            scores.append(1.0)
            continue
        scores.append(max(DataStructs.BulkTanimotoSimilarity(fingerprint, others)))
    return scores


def descriptor_range_flags(
    train_smiles: list[str],
    test_smiles: list[str],
) -> list[bool]:
    """Flag test compounds outside the training min/max box on any descriptor.

    Eight cheap physicochemical descriptors stand in for the model's feature
    space.  This is coarser than a similarity cut and it will flag legitimate
    analogues that happen to sit just outside one range, which is why the default
    method is similarity; use this as a second opinion, not a verdict.
    """

    numpy = _common.require_numpy()
    Chem = _common.require_rdkit()
    from rdkit.Chem import Descriptors  # noqa: PLC0415 - deliberately lazy

    functions = [
        Descriptors.MolWt,
        Descriptors.MolLogP,
        Descriptors.NumHDonors,
        Descriptors.NumHAcceptors,
        Descriptors.TPSA,
        Descriptors.NumRotatableBonds,
        Descriptors.RingCount,
        Descriptors.FractionCSP3,
    ]

    def describe(smiles: str) -> list[float]:
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            raise CliError(f"RDKit could not parse {smiles[:60]!r} while describing it")
        return [float(function(molecule)) for function in functions]

    train_matrix = numpy.asarray([describe(smiles) for smiles in train_smiles], dtype=float)
    test_matrix = numpy.asarray([describe(smiles) for smiles in test_smiles], dtype=float)
    lower = train_matrix.min(axis=0)
    upper = train_matrix.max(axis=0)
    outside = (test_matrix < lower) | (test_matrix > upper)
    return [bool(row.any()) for row in outside]


def stratified_score(
    targets: list[float],
    predictions: list[float],
    inside: list[bool],
    arguments: argparse.Namespace,
) -> dict[str, Any]:
    """Score the model separately inside and outside the domain.

    This is the payoff of the whole exercise: a single headline metric averaged
    over both groups hides the fact that the model is usually much worse on the
    extrapolation half, which is the half a real screening library consists of.
    """

    if arguments.task == "classification":
        labels = _common.as_classification_labels(
            targets, threshold=arguments.active_threshold
        )
    else:
        labels = targets

    groups: dict[str, Any] = {}
    for name, mask in (
        ("inside_domain", inside),
        ("outside_domain", [not flag for flag in inside]),
    ):
        truth = [value for value, keep in zip(labels, mask) if keep]
        predicted = [value for value, keep in zip(predictions, mask) if keep]
        if len(truth) < 2:
            groups[name] = {"n": len(truth)}
            continue
        if arguments.task == "classification":
            groups[name] = _common.classification_metrics(truth, predicted)
        else:
            groups[name] = _common.regression_metrics(truth, predicted)
    return groups


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    numpy = _common.require_numpy()

    train = load_structures(
        arguments.train,
        arguments,
        label="the training table",
        target_column=arguments.train_target_col or arguments.target_col,
    )
    test = load_structures(
        arguments.test,
        arguments,
        label="the test table",
        target_column=arguments.target_col,
        prediction_column=arguments.prediction_col,
    )

    similarities = max_similarity_to_train(
        train["smiles"], test["smiles"], radius=arguments.radius, bits=arguments.bits
    )

    threshold = arguments.threshold
    threshold_source = "supplied with --threshold"
    if threshold is None:
        self_similarity = training_self_similarity(
            train["smiles"], radius=arguments.radius, bits=arguments.bits
        )
        threshold = float(numpy.percentile(self_similarity, arguments.percentile))
        threshold_source = (
            f"{arguments.percentile:.0f}th percentile of the training set's own "
            "nearest-neighbour similarity distribution"
        )

    similarity_out = [score <= threshold for score in similarities]

    descriptor_out = None
    if arguments.method in {"descriptor-range", "consensus"}:
        descriptor_out = descriptor_range_flags(train["smiles"], test["smiles"])

    if arguments.method == "similarity":
        outside = similarity_out
    elif arguments.method == "descriptor-range":
        outside = descriptor_out or []
    else:
        outside = [
            bool(similar or described)
            for similar, described in zip(similarity_out, descriptor_out or [])
        ]

    inside = [not flag for flag in outside]
    out_of_domain = [position for position, flag in enumerate(outside) if flag]

    document: dict[str, Any] = {
        "train": {
            "input": str(Path(arguments.train)),
            "rows_used": train["rows_used"],
            "structures_rejected": train["rejected"],
        },
        "test": {
            "input": str(Path(arguments.test)),
            "rows_used": test["rows_used"],
            "structures_rejected": test["rejected"],
        },
        "method": arguments.method,
        "threshold": threshold,
        "threshold_source": threshold_source,
        "fingerprint": {"radius": arguments.radius, "bits": arguments.bits},
        "summary": {
            "n_test": len(test["smiles"]),
            "inside_domain": int(sum(inside)),
            "outside_domain": int(len(out_of_domain)),
            "outside_fraction": len(out_of_domain) / len(test["smiles"]) if test["smiles"] else None,
            "similarity_quantiles": {
                "min": float(numpy.min(similarities)),
                "median": float(numpy.median(similarities)),
                "max": float(numpy.max(similarities)),
            },
        },
        "out_of_domain_examples": [
            {"index": position, "smiles": test["smiles"][position],
             "max_similarity": similarities[position]}
            for position in out_of_domain[: arguments.list_out]
        ],
        "per_compound": [
            {
                "index": position,
                "smiles": test["smiles"][position],
                "max_similarity_to_train": similarities[position],
                "outside_domain": bool(outside[position]),
                "outside_by_similarity": (
                    bool(similarity_out[position]) if arguments.method != "descriptor-range" else None
                ),
                "outside_by_descriptor_range": (
                    bool(descriptor_out[position]) if descriptor_out is not None else None
                ),
            }
            for position in range(len(test["smiles"]))
        ],
    }

    if test["targets"] is not None and test["predictions"] is not None:
        document["performance_by_domain"] = stratified_score(
            test["targets"], test["predictions"], inside, arguments
        )
        document["reading"] = reading_notes(
            document["summary"], document["performance_by_domain"]
        )
    else:
        document["reading"] = reading_notes(document["summary"])

    return document


def reading_notes(
    summary: dict[str, Any],
    by_domain: dict[str, Any] | None = None,
) -> list[str]:
    """Say what an out-of-domain fraction does and does not imply."""

    notes = [
        "An out-of-domain flag means the training set does not cover this chemistry. "
        "It is not a prediction that the compound is inactive or unsafe.",
        "Model error is usually much larger outside the domain. Report performance "
        "for the two groups separately, or the headline metric hides the split.",
    ]

    if by_domain:
        outside = by_domain.get("outside_domain") or {}
        inside = by_domain.get("inside_domain") or {}
        if outside.get("n", 0) < 2:
            notes.append(
                "Too few out-of-domain compounds carry a target to score that group, so the "
                "size of the extrapolation penalty is still unknown. Predictions on such "
                "compounds should not be acted on."
            )
        elif inside.get("roc_auc") is not None and outside.get("roc_auc") is not None:
            gap = inside["roc_auc"] - outside["roc_auc"]
            notes.append(
                f"ROC-AUC is {inside['roc_auc']:.3f} inside the domain and "
                f"{outside['roc_auc']:.3f} outside ({gap:+.3f}). Quote both, or the headline "
                "number describes chemistry the model was trained on."
            )
        elif inside.get("rmse") is not None and outside.get("rmse") is not None:
            ratio = outside["rmse"] / inside["rmse"] if inside["rmse"] else None
            notes.append(
                f"RMSE is {inside['rmse']:.3f} inside the domain and {outside['rmse']:.3f} "
                f"outside"
                + (f" ({ratio:.1f}x)" if ratio else "")
                + ". Quote both, or the headline number describes chemistry the model was "
                "trained on."
            )
    fraction = summary.get("outside_fraction")
    if fraction is not None and fraction > 0.5:
        notes.append(
            f"{fraction:.0%} of the test compounds are outside the domain, so the headline "
            "metric is mostly a statement about extrapolation. Retrain on a training set "
            "that covers the intended screening library before quoting a number for it."
        )
    elif fraction is not None and fraction == 0.0:
        notes.append(
            "No test compound fell outside the domain. Check that the test set is not a "
            "subset of the training chemistry, which would make this check vacuous."
        )
    return notes


def print_summary(document: dict[str, Any]) -> None:
    """Print the summary to stderr, leaving stdout for the JSON document."""

    summary = document["summary"]
    print_to_stderr(f"method: {document['method']}   threshold: {document['threshold']:.3f} "
          f"({document['threshold_source']})")
    print_to_stderr()
    print_to_stderr(_common.format_table(
        ["", "n", "share"],
        [
            ["inside domain", summary["inside_domain"],
             _common.format_number(1.0 - (summary["outside_fraction"] or 0.0))],
            ["outside domain", summary["outside_domain"],
             _common.format_number(summary["outside_fraction"])],
        ],
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
