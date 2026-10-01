#!/usr/bin/env python3
"""Render a bounded Markdown model card from local aggregate JSON summaries."""

from __future__ import annotations

import argparse
import math
from typing import Any

from _common import CliError, emit_text, load_json


COMPETING_RISK_CHOICES = ("not-assessed", "absent", "present")


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CliError(f"{label} must be a JSON object")
    return value


def _scalar(value: Any, default: str = "not supplied") -> str:
    """Render a bounded scalar without accepting row-level structures."""

    if value is None:
        return default
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CliError("report values must be finite")
        return f"{value:.4g}"
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        if len(cleaned) > 160:
            raise CliError("report strings must be at most 160 characters")
        return cleaned.replace("`", "'")
    raise CliError("model report accepts aggregate scalar values only")


def synthetic_training_summary() -> dict[str, Any]:
    """Return a deterministic aggregate example with no person-level data."""

    return {
        "data": {
            "censored_test": 18,
            "censored_train": 54,
            "events_test": 42,
            "events_train": 126,
            "rows_test": 60,
            "rows_train": 180,
        },
        "evaluation": {
            "harrell_c": 0.71,
            "uno_c": {
                "available": True,
                "score": 0.69,
                "training_censoring_distribution": True,
                "truncation_time": 8.0,
            },
        },
        "leakage_controls": {
            "holdout_used_for_tuning": False,
            "preprocessing_fit_scope": "training folds only",
            "split_before_imputation_encoding_scaling": True,
            "tuning_evaluation": "not_run",
        },
        "model": {
            "best_params": None,
            "family": "coxph",
            "transformed_feature_count": 4,
        },
        "package_versions": {
            "numpy": "2.5.1",
            "pandas": "3.0.6",
            "scikit-learn": "1.9.1",
            "scikit-survival": "0.28.0",
        },
        "schema": {
            "categorical_features": ["segment"],
            "event": "event",
            "numeric_features": ["x_linear", "x_noise"],
            "time": "time",
        },
        "seed": 20_260_723,
        "source": {"kind": "synthetic"},
        "tuning": {"performed": False},
    }


def synthetic_metric_summary() -> dict[str, Any]:
    """Return deterministic aggregate metric examples."""

    return {
        "assumptions": {
            "censoring_distribution_fit_on_training_only": True,
            "independent_censoring_from_features": "required_by_IPCW_estimator",
            "test_follow_up_within_training_support": True,
            "time_grid_within_test_follow_up": True,
        },
        "metrics": {
            "cumulative_dynamic_auc": {
                "mean": 0.70,
                "times": [2.0, 4.0, 6.0],
                "values": [0.68, 0.70, 0.72],
            },
            "harrell_c": 0.71,
            "uno_c": 0.69,
            "integrated_brier_score": 0.18,
        },
        "source": {"kind": "synthetic"},
    }


def _feature_list(schema: dict[str, Any], key: str) -> str:
    value = schema.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise CliError(f"schema.{key} must be a list of strings")
    if len(value) > 256:
        raise CliError("too many feature names in model summary")
    return ", ".join(f"`{_scalar(item)}`" for item in value) or "none"


def render_report(
    training: dict[str, Any],
    metrics: dict[str, Any],
    *,
    competing_risks: str,
    title: str,
) -> str:
    """Render aggregate summaries while preserving metric distinctions."""

    training = _mapping(training, "training summary")
    metrics = _mapping(metrics, "metrics summary")
    data = _mapping(training.get("data", {}), "training.data")
    model = _mapping(training.get("model", {}), "training.model")
    schema = _mapping(training.get("schema", {}), "training.schema")
    leakage = _mapping(
        training.get("leakage_controls", {}), "training.leakage_controls"
    )
    versions = _mapping(
        training.get("package_versions", {}), "training.package_versions"
    )
    metric_values = _mapping(metrics.get("metrics", {}), "metrics.metrics")
    assumptions = _mapping(metrics.get("assumptions", {}), "metrics.assumptions")
    dynamic_auc = metric_values.get("cumulative_dynamic_auc")
    dynamic_auc_mean = (
        _mapping(dynamic_auc, "cumulative_dynamic_auc").get("mean")
        if dynamic_auc is not None
        else None
    )

    if competing_risks == "present":
        competing_note = (
            "Competing causes are present. Standard all-event metrics are not "
            "cause-specific CIF validation; report each cause separately."
        )
    elif competing_risks == "absent":
        competing_note = "No competing cause was declared for this analysis."
    else:
        competing_note = (
            "Competing risks were not assessed; this must be resolved before "
            "interpreting cause-specific event probability."
        )

    lines = [
        f"# {_scalar(title)}",
        "",
        "## Scope",
        "",
        "- Aggregate, local report only; no person-level rows are embedded.",
        "- Supplied summaries must refer to the same fitted model and held-out cohort; "
        "this renderer does not verify that provenance.",
        "- Predictive performance does not establish causal effects or clinical utility.",
        "- This report is not clinical advice.",
        "",
        "## Data and split",
        "",
        f"- Training rows: {_scalar(data.get('rows_train'))}",
        f"- Test rows: {_scalar(data.get('rows_test'))}",
        f"- Training events / censored: {_scalar(data.get('events_train'))} / "
        f"{_scalar(data.get('censored_train'))}",
        f"- Test events / censored: {_scalar(data.get('events_test'))} / "
        f"{_scalar(data.get('censored_test'))}",
        f"- Deterministic seed: {_scalar(training.get('seed'))}",
        "",
        "## Explicit schema",
        "",
        f"- Event column: `{_scalar(schema.get('event'))}`",
        f"- Time column: `{_scalar(schema.get('time'))}`",
        f"- Numeric features: {_feature_list(schema, 'numeric_features')}",
        f"- Categorical features: {_feature_list(schema, 'categorical_features')}",
        "",
        "## Model and leakage controls",
        "",
        f"- Model family: `{_scalar(model.get('family'))}`",
        f"- Transformed features: {_scalar(model.get('transformed_feature_count'))}",
        "- Split before fitting imputation/encoding/scaling: "
        f"{_scalar(leakage.get('split_before_imputation_encoding_scaling'))}",
        f"- Preprocessing fit scope: {_scalar(leakage.get('preprocessing_fit_scope'))}",
        f"- Holdout used for tuning: {_scalar(leakage.get('holdout_used_for_tuning'))}",
        f"- Tuning evaluation: {_scalar(leakage.get('tuning_evaluation'))}",
        "",
        "## Performance",
        "",
        f"- Harrell C (rank discrimination): {_scalar(metric_values.get('harrell_c'))}",
        f"- Uno C (IPCW rank discrimination): {_scalar(metric_values.get('uno_c'))}",
        "- Mean cumulative/dynamic AUC (time-specific discrimination): "
        f"{_scalar(dynamic_auc_mean)}",
        "- Integrated Brier score (probability prediction error; lower is better): "
        f"{_scalar(metric_values.get('integrated_brier_score'))}",
        "- A Brier score mixes discrimination and calibration; it is not a "
        "standalone calibration curve.",
        "",
        "## Censoring and competing risks",
        "",
        "- IPCW censoring distribution fit on training data: "
        f"{_scalar(assumptions.get('censoring_distribution_fit_on_training_only'))}",
        "- Independent censoring from features: "
        f"{_scalar(assumptions.get('independent_censoring_from_features'))}",
        "- Evaluation grid within train/test support: "
        f"{_scalar(assumptions.get('test_follow_up_within_training_support'))} / "
        f"{_scalar(assumptions.get('time_grid_within_test_follow_up'))}",
        f"- {competing_note}",
        "",
        "## Runtime snapshot",
        "",
        f"- scikit-survival: {_scalar(versions.get('scikit-survival'))}",
        f"- scikit-learn: {_scalar(versions.get('scikit-learn'))}",
        f"- NumPy: {_scalar(versions.get('numpy'))}",
        f"- pandas: {_scalar(versions.get('pandas'))}",
        "",
        "## Required follow-up",
        "",
        "- Check proportional-hazards assumptions when interpreting Cox effects.",
        "- Inspect horizon-specific calibration on independent validation data.",
        "- Use nested CV for performance claims made during hyperparameter tuning.",
        "- Evaluate transportability, subgroup behavior, and decision consequences "
        "separately; these metrics alone do not establish utility.",
        "",
    ]
    training_source = _mapping(training.get("source", {}), "training.source")
    metrics_source = _mapping(metrics.get("source", {}), "metrics.source")
    if training_source.get("kind") == "synthetic" and metrics_source.get("kind") == "synthetic":
        lines[4:4] = ["- Synthetic example: metric values may be illustrative; this report alone is not fit evidence."]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render a Markdown model report from aggregate local JSON summaries. "
            "No inputs produces a deterministic synthetic example."
        )
    )
    parser.add_argument("--training-summary", help="Optional local training .json")
    parser.add_argument("--metrics-summary", help="Optional local metrics .json")
    parser.add_argument(
        "--competing-risks",
        choices=COMPETING_RISK_CHOICES,
        default="not-assessed",
    )
    parser.add_argument("--title", default="Survival model report")
    parser.add_argument("--output", help="Optional local .md output")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if bool(args.training_summary) != bool(args.metrics_summary):
            raise CliError(
                "provide both --training-summary and --metrics-summary, or neither "
                "for the fully synthetic example"
            )
        training = (
            load_json(args.training_summary)
            if args.training_summary
            else synthetic_training_summary()
        )
        metrics = (
            load_json(args.metrics_summary)
            if args.metrics_summary
            else synthetic_metric_summary()
        )
        report = render_report(
            training,
            metrics,
            competing_risks=args.competing_risks,
            title=args.title,
        )
        emit_text(report, output=args.output, force=args.force)
    except CliError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
