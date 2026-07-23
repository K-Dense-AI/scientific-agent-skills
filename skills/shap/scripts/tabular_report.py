#!/usr/bin/env python3
"""Generate a validated SHAP 0.52 tabular report from a built-in dataset.

The script is intentionally self-contained: it downloads no data and loads no
serialized model. Use it as a modern template for Explanation slicing,
probability-space TreeExplainer output, additivity validation, and figure
export.
"""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import sklearn
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split


def positive_int(value: str) -> int:
    """Parse a strictly positive integer."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def nonnegative_int(value: str) -> int:
    """Parse a non-negative integer."""
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be zero or greater")
    return parsed


def positive_float(value: str) -> float:
    """Parse a strictly positive float."""
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Train a deterministic random forest on scikit-learn's breast "
            "cancer dataset and export a validated probability-space SHAP report."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("shap-report"),
        help="Directory for CSV, JSON, and PNG outputs (default: shap-report).",
    )
    parser.add_argument(
        "--class-index",
        type=nonnegative_int,
        default=1,
        help="Class probability to explain (default: 1).",
    )
    parser.add_argument(
        "--background-size",
        type=positive_int,
        default=100,
        help="Maximum number of training rows in the background (default: 100).",
    )
    parser.add_argument(
        "--explain-size",
        type=positive_int,
        default=100,
        help="Maximum number of held-out rows to explain (default: 100).",
    )
    parser.add_argument(
        "--max-display",
        type=positive_int,
        default=15,
        help="Maximum features displayed in plots (default: 15).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Random seed for splitting, fitting, and background sampling.",
    )
    parser.add_argument(
        "--atol",
        type=positive_float,
        default=1e-6,
        help="Absolute tolerance for additive reconstruction (default: 1e-6).",
    )
    parser.add_argument(
        "--rtol",
        type=positive_float,
        default=1e-5,
        help="Relative tolerance for additive reconstruction (default: 1e-5).",
    )
    return parser.parse_args()


def select_output(
    explanation: shap.Explanation,
    class_index: int,
) -> shap.Explanation:
    """Select one output from a tabular Explanation."""
    values = np.asarray(explanation.values)

    if values.ndim == 2:
        if class_index != 0:
            raise ValueError(
                "The explainer produced one output; use --class-index 0 or "
                "configure a model output with multiple classes."
            )
        return explanation

    if values.ndim != 3:
        raise ValueError(
            "Expected tabular values shaped (samples, features) or "
            f"(samples, features, outputs), received {values.shape}."
        )

    output_count = values.shape[-1]
    if class_index >= output_count:
        raise ValueError(
            f"--class-index {class_index} is outside {output_count} outputs."
        )

    return explanation[..., class_index]


def save_axis(axis: Any, path: Path) -> None:
    """Save and close the figure associated with a SHAP plot axis."""
    figure = axis.figure if axis is not None else plt.gcf()
    figure.tight_layout()
    figure.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def output_name(explanation: shap.Explanation, class_index: int) -> str:
    """Return a stable display name for the selected output."""
    name = explanation.output_names
    if name is None:
        return f"class_{class_index}"
    if isinstance(name, str):
        return name
    if np.ndim(name) == 0:
        return str(name)
    return f"class_{class_index}"


def main() -> int:
    """Run the complete example and return a process exit code."""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    X, y = load_breast_cancer(as_frame=True, return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        stratify=y,
        random_state=args.seed,
    )

    model = RandomForestClassifier(
        n_estimators=200,
        min_samples_leaf=3,
        random_state=args.seed,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    if args.class_index >= len(model.classes_):
        raise ValueError(
            f"--class-index {args.class_index} is outside model classes "
            f"{model.classes_.tolist()}."
        )

    background_size = min(args.background_size, len(X_train))
    background = shap.sample(
        X_train,
        background_size,
        random_state=args.seed,
    )
    X_explain = X_test.iloc[: min(args.explain_size, len(X_test))].copy()

    explainer = shap.TreeExplainer(
        model,
        data=background,
        feature_perturbation="interventional",
        model_output="probability",
    )
    all_outputs = explainer(X_explain)
    explanation = select_output(all_outputs, args.class_index)

    values = np.asarray(explanation.values, dtype=float)
    base_values = np.asarray(explanation.base_values, dtype=float)
    predictions = model.predict_proba(X_explain)[:, args.class_index]
    reconstructed = base_values + values.sum(axis=1)
    errors = reconstructed - predictions
    max_abs_error = float(np.max(np.abs(errors)))

    np.testing.assert_allclose(
        reconstructed,
        predictions,
        rtol=args.rtol,
        atol=args.atol,
    )

    feature_names = (
        list(explanation.feature_names)
        if explanation.feature_names is not None
        else X_explain.columns.tolist()
    )
    importance = pd.DataFrame(
        {
            "feature": feature_names,
            "mean_abs_shap": np.abs(values).mean(axis=0),
            "mean_signed_shap": values.mean(axis=0),
        }
    ).sort_values("mean_abs_shap", ascending=False, ignore_index=True)
    importance.to_csv(args.output_dir / "feature_importance.csv", index=False)

    local_order = np.argsort(np.abs(values[0]))[::-1]
    local = pd.DataFrame(
        {
            "feature": np.asarray(feature_names)[local_order],
            "feature_value": X_explain.iloc[0].to_numpy()[local_order],
            "shap_value": values[0, local_order],
        }
    )
    local.to_csv(args.output_dir / "first_row_contributions.csv", index=False)

    predictions_frame = pd.DataFrame(
        {
            "row_index": X_explain.index.astype(str),
            "prediction": predictions,
            "base_value": base_values,
            "reconstructed_output": reconstructed,
            "reconstruction_error": errors,
        }
    )
    predictions_frame.to_csv(
        args.output_dir / "prediction_reconstruction.csv",
        index=False,
    )

    axis = shap.plots.bar(
        explanation,
        max_display=args.max_display,
        show=False,
    )
    save_axis(axis, args.output_dir / "bar.png")

    axis = shap.plots.beeswarm(
        explanation,
        max_display=args.max_display,
        show=False,
    )
    save_axis(axis, args.output_dir / "beeswarm.png")

    axis = shap.plots.waterfall(
        explanation[0],
        max_display=args.max_display,
        show=False,
    )
    save_axis(axis, args.output_dir / "waterfall-first-row.png")

    top_feature = str(importance.loc[0, "feature"])
    axis = shap.plots.scatter(
        explanation[:, top_feature],
        color=explanation,
        alpha=0.6,
        show=False,
    )
    save_axis(axis, args.output_dir / "scatter-top-feature.png")

    metadata = {
        "python_version": platform.python_version(),
        "shap_version": shap.__version__,
        "numpy_version": np.__version__,
        "scikit_learn_version": sklearn.__version__,
        "model": type(model).__name__,
        "model_score": float(model.score(X_test, y_test)),
        "seed": args.seed,
        "background_rows": len(background),
        "explained_rows": len(X_explain),
        "feature_count": X_explain.shape[1],
        "all_output_shape": list(np.shape(all_outputs.values)),
        "selected_output_shape": list(values.shape),
        "selected_class_index": args.class_index,
        "selected_class_label": str(model.classes_[args.class_index]),
        "selected_output_name": output_name(explanation, args.class_index),
        "output_units": "class probability",
        "feature_perturbation": "interventional",
        "max_abs_additivity_error": max_abs_error,
        "additivity_atol": args.atol,
        "additivity_rtol": args.rtol,
        "top_feature": top_feature,
    }
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(metadata, indent=2))
    print(f"Report written to {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
