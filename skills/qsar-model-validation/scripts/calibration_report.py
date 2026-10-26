#!/usr/bin/env python3
"""Check whether a predicted probability means what it says, and fix it if not.

ROC-AUC only measures ranking.  A model can order every compound correctly and
still be badly wrong about magnitude, and magnitude is what a decision uses: a
predicted 0.8 that is right 55% of the time will produce confident, wrong
go/no-go calls at scale.  This CLI reports the reliability curve, expected
calibration error, and Brier score, and optionally fits a correction.

The correction is fitted on a calibration slice that is held out from the slice
being reported on.  Fitting a calibrator on the same rows you then evaluate is
the mistake this whole skill exists to catch -- it makes the calibration look
excellent and means nothing -- so the script refuses to do it silently.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import _common
from _common import CliError, print_to_stderr


DEFAULT_BINS = 10
DEFAULT_CALIBRATION_SIZE = 0.5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calibration_report.py",
        description=(
            "Report the reliability curve, expected calibration error, and Brier score of "
            "predicted probabilities, optionally fitting a Platt or isotonic correction "
            "on a held-out calibration slice."
        ),
        epilog=(
            "Example: calibration_report.py --input preds.csv --probability-col prob "
            "--label-col active --method platt"
        ),
    )
    parser.add_argument("--input", required=True, help="CSV or TSV with predictions")
    parser.add_argument("--probability-col", required=True, help="column of probabilities in [0, 1]")
    parser.add_argument(
        "--label-col",
        required=True,
        help="column of observed 0/1 outcomes (see --active-threshold for a numeric column)",
    )
    parser.add_argument(
        "--active-threshold",
        type=_common.finite_float,
        help="treat the label column as numeric and threshold it, instead of requiring 0/1",
    )
    parser.add_argument(
        "--calibration-col",
        help=(
            "column marking rows reserved for fitting the correction (truthy = calibration "
            "row); when omitted, the input is split by --calibration-size"
        ),
    )
    parser.add_argument(
        "--calibration-size",
        type=_common.fraction,
        default=DEFAULT_CALIBRATION_SIZE,
        help=f"share of rows used to fit the correction when --calibration-col is absent "
             f"(default {DEFAULT_CALIBRATION_SIZE})",
    )
    parser.add_argument(
        "--method",
        choices=("none", "platt", "isotonic"),
        default="none",
        help="fit a correction and report it alongside the uncorrected numbers (default none)",
    )
    parser.add_argument(
        "--bins",
        type=_common.bounded_int(2, 100),
        default=DEFAULT_BINS,
        help=f"reliability-curve bins (default {DEFAULT_BINS})",
    )
    parser.add_argument(
        "--seed",
        type=_common.finite_float,
        default=float(_common.DEFAULT_SEED),
        help="seed for the calibration/evaluation split",
    )
    parser.add_argument("--output", help="write the JSON report to this file")
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output file"
    )
    return parser


#: Spellings accepted for the optional calibration-row marker.  A blank cell is
#: the most common way to write "not a calibration row", and pandas reads blanks
#: as NaN -- which is truthy in Python, so an unguarded `bool(value)` would
#: silently claim every row for the calibration slice and leave nothing to
#: evaluate.  The marker is parsed explicitly for that reason.
FALSE_MARKERS = frozenset({"", "nan", "none", "null", "0", "0.0", "false", "no", "n", "-"})
TRUE_MARKERS = frozenset({"1", "1.0", "true", "yes", "y", "calibration", "cal"})


def parse_marker(value: Any, *, column: str) -> bool:
    """Interpret one calibration-marker cell, refusing anything ambiguous."""

    pandas = _common.require_pandas()
    if value is None or (not isinstance(value, str) and pandas.isna(value)):
        return False
    text = str(value).strip().lower()
    if text in TRUE_MARKERS:
        return True
    if text in FALSE_MARKERS:
        return False
    raise CliError(
        f"column {column!r} has the value {value!r}, which is not a yes/no marker; "
        "use one of: " + ", ".join(sorted(TRUE_MARKERS)) + " for calibration rows and "
        "leave the rest blank"
    )


def load_predictions(arguments: argparse.Namespace) -> dict[str, Any]:
    """Read probabilities, outcomes, and the calibration-row marker."""

    numpy = _common.require_numpy()
    frame = _common.read_table(arguments.input, label="the prediction table")

    for column, flag in ((arguments.probability_col, "--probability-col"),
                         (arguments.label_col, "--label-col")):
        if column not in frame.columns:
            raise CliError(
                f"column {column!r} ({flag}) is not in the table; "
                f"available: {', '.join(map(str, frame.columns))}"
            )

    probabilities: list[float] = []
    labels: list[int] = []
    markers: list[bool] = []
    dropped = 0
    raw_labels = frame[arguments.label_col].tolist()
    raw_probabilities = frame[arguments.probability_col].tolist()
    raw_markers = (
        frame[arguments.calibration_col].tolist() if arguments.calibration_col else None
    )

    numeric_labels: list[float] = []
    for value in raw_labels:
        if arguments.active_threshold is not None:
            try:
                numeric_labels.append(float(value))
            except (TypeError, ValueError):
                numeric_labels.append(float("nan"))
        else:
            text = str(value).strip().lower()
            if text in {"1", "1.0", "true", "yes", "active", "positive"}:
                numeric_labels.append(1.0)
            elif text in {"0", "0.0", "false", "no", "inactive", "negative"}:
                numeric_labels.append(0.0)
            else:
                numeric_labels.append(float("nan"))

    for position, raw_probability in enumerate(raw_probabilities):
        try:
            probability = float(raw_probability)
        except (TypeError, ValueError):
            dropped += 1
            continue
        if not numpy.isfinite(probability) or not 0.0 <= probability <= 1.0:
            dropped += 1
            continue
        if not numpy.isfinite(numeric_labels[position]):
            dropped += 1
            continue
        probabilities.append(probability)
        if arguments.active_threshold is not None:
            labels.append(int(numeric_labels[position] >= arguments.active_threshold))
        else:
            labels.append(int(numeric_labels[position]))
        markers.append(
            parse_marker(raw_markers[position], column=arguments.calibration_col)
            if raw_markers is not None
            else False
        )

    if len(probabilities) < 20:
        raise CliError(
            f"only {len(probabilities)} usable rows remain; a calibration report needs at "
            "least 20"
        )
    if len(set(labels)) < 2:
        raise CliError(
            "the label column has only one distinct outcome; calibration is undefined "
            "without both positives and negatives"
        )

    return {
        "probabilities": probabilities,
        "labels": labels,
        "markers": markers,
        "dropped": dropped,
        "rows_in_file": int(len(frame)),
    }


def split_rows(data: dict[str, Any], arguments: argparse.Namespace) -> tuple[list[int], list[int]]:
    """Return ``(calibration_rows, evaluation_rows)``, never the same rows twice."""

    numpy = _common.require_numpy()
    if arguments.calibration_col:
        calibration = [index for index, flag in enumerate(data["markers"]) if flag]
        evaluation = [index for index, flag in enumerate(data["markers"]) if not flag]
        if not calibration or not evaluation:
            raise CliError(
                f"--calibration-col {arguments.calibration_col!r} left one side empty "
                f"({len(calibration)} calibration rows, {len(evaluation)} evaluation rows)"
            )
        return calibration, evaluation

    count = len(data["probabilities"])
    generator = numpy.random.default_rng(int(arguments.seed))
    order = generator.permutation(count)
    cut = max(1, min(count - 1, int(round(count * arguments.calibration_size))))
    calibration = sorted(int(index) for index in order[:cut])
    evaluation = sorted(int(index) for index in order[cut:])
    return calibration, evaluation


def fit_correction(
    data: dict[str, Any],
    calibration: list[int],
    arguments: argparse.Namespace,
) -> Any:
    """Fit the requested calibrator on the calibration slice only."""

    numpy = _common.require_numpy()
    _common.require_sklearn()

    probabilities = numpy.asarray([data["probabilities"][index] for index in calibration])
    labels = numpy.asarray([data["labels"][index] for index in calibration])

    if arguments.method == "platt":
        from sklearn.linear_model import LogisticRegression  # noqa: PLC0415 - deliberately lazy

        # Platt scaling is logistic regression on the raw score.  The score is
        # pushed through a logit first so the fit is linear in log-odds rather
        # than in probability, which is what makes it a one-parameter correction.
        clipped = numpy.clip(probabilities, 1e-6, 1 - 1e-6)
        logits = numpy.log(clipped / (1 - clipped)).reshape(-1, 1)
        model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
        model.fit(logits, labels)
        return lambda values: model.predict_proba(
            numpy.log(numpy.clip(values, 1e-6, 1 - 1e-6)
                      / (1 - numpy.clip(values, 1e-6, 1 - 1e-6))).reshape(-1, 1)
        )[:, 1]

    if arguments.method == "isotonic":
        from sklearn.isotonic import IsotonicRegression  # noqa: PLC0415 - deliberately lazy

        model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        model.fit(probabilities, labels)
        return lambda values: model.predict(numpy.asarray(values))

    raise CliError(f"no correction is defined for method {arguments.method!r}")


def evaluate(
    data: dict[str, Any],
    rows: list[int],
    probabilities: list[float],
    arguments: argparse.Namespace,
) -> dict[str, Any]:
    """Score one set of probabilities against the observed outcomes."""

    labels = [data["labels"][index] for index in rows]
    subset = [probabilities[index] for index in rows]
    metrics = _common.classification_metrics(labels, subset)
    calibration = _common.expected_calibration_error(labels, subset, bins=arguments.bins)
    return {
        "n": len(rows),
        "n_positive": metrics["n_positive"],
        "prevalence": metrics["prevalence"],
        "roc_auc": metrics["roc_auc"],
        "pr_auc": metrics["pr_auc"],
        "brier": metrics["brier"],
        "ece": calibration["ece"],
        "reliability_curve": calibration["curve"],
    }


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    data = load_predictions(arguments)
    calibration_rows, evaluation_rows = split_rows(data, arguments)

    raw_evaluation = evaluate(
        data, evaluation_rows, data["probabilities"], arguments
    )
    evaluation: dict[str, Any] = {"uncorrected": raw_evaluation}

    raw_calibration = evaluate(data, calibration_rows, data["probabilities"], arguments)

    if arguments.method != "none":
        correct = fit_correction(data, calibration_rows, arguments)
        corrected_all = [float(value) for value in correct(data["probabilities"])]
        evaluation["corrected"] = evaluate(data, evaluation_rows, corrected_all, arguments)
        evaluation["corrected"]["method"] = arguments.method
        evaluation["corrected"]["fitted_on_rows"] = len(calibration_rows)
        evaluation["ece_change"] = (
            evaluation["corrected"]["ece"] - raw_evaluation["ece"]
        )
        evaluation["brier_change"] = (
            evaluation["corrected"]["brier"] - raw_evaluation["brier"]
        )

    document = {
        "input": str(Path(arguments.input)),
        "rows_in_file": data["rows_in_file"],
        "rows_dropped": data["dropped"],
        "bins": arguments.bins,
        "method": arguments.method,
        "split": {
            "calibration_rows": len(calibration_rows),
            "evaluation_rows": len(evaluation_rows),
            "source": (
                f"--calibration-col {arguments.calibration_col!r}"
                if arguments.calibration_col
                else f"random {arguments.calibration_size:.0%} calibration split, "
                     f"seed {int(arguments.seed)}"
            ),
            "calibration_slice_metrics": raw_calibration,
        },
        "evaluation": evaluation,
    }
    document["reading"] = reading_notes(document)
    return document


def reading_notes(document: dict[str, Any]) -> list[str]:
    """Interpret the numbers, including the case where calibration is the wrong fix."""

    evaluation = document["evaluation"]
    uncorrected = evaluation["uncorrected"]
    notes = [
        "Calibration is reported on the evaluation slice only; the calibration slice is "
        "never scored, because a calibrator fitted and graded on the same rows is always "
        "excellent and always meaningless.",
        "Calibration changes the magnitude of probabilities, never their order. If ROC-AUC "
        "is poor, calibration will not help -- improve discrimination first.",
    ]

    ece = uncorrected["ece"]
    if ece <= 0.05:
        notes.append(
            f"Expected calibration error is {ece:.3f}, so the probabilities are already close "
            "to the observed frequencies; a correction is unlikely to be worth the complexity."
        )
    elif ece <= 0.15:
        notes.append(
            f"Expected calibration error is {ece:.3f}. Usable for ranking, but state the "
            "uncertainty before any probability is read as an absolute risk."
        )
    else:
        notes.append(
            f"Expected calibration error is {ece:.3f}, which is large: a predicted probability "
            "should not be quoted as a risk without a correction."
        )

    corrected = evaluation.get("corrected")
    if corrected:
        change = evaluation["ece_change"]
        if change < 0:
            notes.append(
                f"{corrected['method']} reduced expected calibration error by {abs(change):.3f} "
                f"on the evaluation slice, fitted on {corrected['fitted_on_rows']} separate rows."
            )
        else:
            notes.append(
                f"{corrected['method']} did not reduce expected calibration error "
                f"({change:+.3f}) on this evaluation slice. Keep the uncorrected probabilities "
                "and report the raw calibration error instead."
            )
        if abs(corrected["roc_auc"] - uncorrected["roc_auc"]) > 1e-9:
            notes.append(
                "ROC-AUC changed between the uncorrected and corrected rows, which should not "
                "happen for a monotone calibrator; check the correction for ties in the scores."
            )

    prevalence = uncorrected["prevalence"]
    if prevalence is not None and (prevalence < 0.1 or prevalence > 0.9):
        notes.append(
            f"Prevalence is {prevalence:.2f}. Calibration error is dominated by the majority "
            "class, so also read PR-AUC, and consider reporting calibration within the minority "
            "class separately."
        )
    return notes


def print_summary(document: dict[str, Any]) -> None:
    """Print the summary to stderr, leaving stdout for the JSON document."""

    evaluation = document["evaluation"]
    rows = []
    for name in ("uncorrected", "corrected"):
        entry = evaluation.get(name)
        if entry is None:
            continue
        rows.append([
            name,
            entry["n"],
            _common.format_number(entry["ece"]),
            _common.format_number(entry["brier"]),
            _common.format_number(entry["roc_auc"]),
            _common.format_number(entry["prevalence"]),
        ])
    print_to_stderr(f"method: {document['method']}   {document['split']['source']}")
    print_to_stderr()
    print_to_stderr(_common.format_table(["slice", "n", "ECE", "Brier", "ROC-AUC", "prevalence"], rows))
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
