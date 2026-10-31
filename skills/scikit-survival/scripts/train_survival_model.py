#!/usr/bin/env python3
"""Train a leakage-safe Cox or ensemble example on explicit local schema."""

from __future__ import annotations

import argparse
from importlib.metadata import version
from typing import Any

from _common import (
    DEFAULT_SEED,
    MAX_FEATURES,
    CliError,
    atomic_save_npz,
    bounded_int,
    emit_json,
    parse_names,
    probability,
    read_csv,
    structured_survival,
    synthetic_survival_frame,
)


MODEL_CHOICES = (
    "coxph",
    "coxnet",
    "random-forest",
    "extra-trees",
    "gradient-boosting",
)


def resolve_schema(
    frame: Any,
    *,
    event_column: str,
    time_column: str,
    numeric_columns: list[str],
    categorical_columns: list[str],
) -> tuple[Any, Any, dict[str, Any]]:
    """Select explicit features and build a validated structured outcome."""

    if not numeric_columns and not categorical_columns:
        raise CliError(
            "an explicit schema is required: provide --numeric-columns and/or "
            "--categorical-columns"
        )
    feature_columns = numeric_columns + categorical_columns
    if len(feature_columns) > MAX_FEATURES:
        raise CliError(f"at most {MAX_FEATURES} features are allowed")
    if len(feature_columns) != len(set(feature_columns)):
        raise CliError("numeric and categorical feature lists must be disjoint")
    if event_column == time_column:
        raise CliError("event and time columns must differ")
    forbidden = {event_column, time_column}.intersection(feature_columns)
    if forbidden:
        raise CliError(
            "outcomes must not be used as features: " + ", ".join(sorted(forbidden))
        )
    required = [event_column, time_column, *feature_columns]
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise CliError(f"missing schema columns: {', '.join(missing)}")

    y = structured_survival(
        frame[event_column],
        frame[time_column],
        event_name=event_column,
        time_name=time_column,
    )
    X = frame.loc[:, feature_columns].copy()
    schema = {
        "categorical_features": categorical_columns,
        "event": event_column,
        "numeric_features": numeric_columns,
        "time": time_column,
    }
    return X, y, schema


def build_pipeline(
    model_name: str,
    numeric_columns: list[str],
    categorical_columns: list[str],
    *,
    seed: int,
):
    """Build a preprocessing-and-model pipeline without fitting it."""

    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
        from sksurv.ensemble import (
            ExtraSurvivalTrees,
            GradientBoostingSurvivalAnalysis,
            RandomSurvivalForest,
        )
        from sksurv.linear_model import (
            CoxnetSurvivalAnalysis,
            CoxPHSurvivalAnalysis,
        )
    except ImportError as exc:
        from _common import PINNED_INSTALL

        raise CliError(
            f"survival stack unavailable; install with `{PINNED_INSTALL}`"
        ) from exc

    transformers: list[tuple[str, Any, list[str]]] = []
    if numeric_columns:
        numeric = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
            ]
        )
        transformers.append(("numeric", numeric, numeric_columns))
    if categorical_columns:
        categorical = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="most_frequent")),
                (
                    "encode",
                    OneHotEncoder(
                        drop="first",
                        handle_unknown="ignore",
                        sparse_output=False,
                    ),
                ),
            ]
        )
        transformers.append(("categorical", categorical, categorical_columns))
    preprocess = ColumnTransformer(
        transformers,
        remainder="drop",
        sparse_threshold=0.0,
        verbose_feature_names_out=False,
    )

    if model_name == "coxph":
        model = CoxPHSurvivalAnalysis(alpha=0.1, ties="efron")
    elif model_name == "coxnet":
        model = CoxnetSurvivalAnalysis(
            alphas=[0.05],
            l1_ratio=0.5,
            fit_baseline_model=True,
        )
    elif model_name == "random-forest":
        model = RandomSurvivalForest(
            n_estimators=64,
            min_samples_leaf=5,
            n_jobs=1,
            random_state=seed,
        )
    elif model_name == "extra-trees":
        model = ExtraSurvivalTrees(
            n_estimators=64,
            min_samples_leaf=5,
            n_jobs=1,
            random_state=seed,
        )
    elif model_name == "gradient-boosting":
        model = GradientBoostingSurvivalAnalysis(
            n_estimators=64,
            learning_rate=0.05,
            max_depth=2,
            random_state=seed,
        )
    else:
        raise CliError(f"unsupported model: {model_name}")
    return Pipeline([("preprocess", preprocess), ("model", model)])


def parameter_grid(model_name: str) -> dict[str, list[Any]]:
    """Return a deliberately small, bounded tuning grid."""

    if model_name == "coxph":
        return {"model__alpha": [0.01, 0.1, 1.0]}
    if model_name == "coxnet":
        return {"model__alphas": [[0.01], [0.05], [0.2]]}
    if model_name in {"random-forest", "extra-trees"}:
        return {"model__min_samples_leaf": [3, 6, 10]}
    if model_name == "gradient-boosting":
        return {
            "model__learning_rate": [0.03, 0.1],
            "model__max_depth": [1, 2],
        }
    raise CliError(f"unsupported model: {model_name}")


def _event_field(y: Any) -> str:
    return str(y.dtype.names[0])


def _time_field(y: Any) -> str:
    return str(y.dtype.names[1])


def stratified_splits(y: Any, folds: int, *, seed: int) -> list[tuple[Any, Any]]:
    """Create deterministic event-stratified indices."""

    try:
        import numpy as np
        from sklearn.model_selection import StratifiedKFold
    except ImportError as exc:
        raise CliError("scikit-learn and NumPy are required") from exc
    labels = y[_event_field(y)].astype(int)
    counts = np.bincount(labels, minlength=2)
    if counts.min() < folds:
        raise CliError(
            f"{folds}-fold CV requires at least {folds} events and censored rows"
        )
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    return list(splitter.split(np.zeros(len(y)), labels))


def uno_concordance(y_train: Any, y_test: Any, risk: Any) -> dict[str, Any]:
    """Evaluate IPCW concordance using only the training censoring distribution."""

    try:
        import numpy as np
        from sksurv.metrics import concordance_index_ipcw
    except ImportError as exc:
        raise CliError("scikit-survival and NumPy are required") from exc
    time_train = y_train[_time_field(y_train)]
    time_test = y_test[_time_field(y_test)]
    tau = float(min(np.quantile(time_train, 0.8), np.quantile(time_test, 0.8)))
    try:
        score = float(concordance_index_ipcw(y_train, y_test, risk, tau=tau)[0])
    except ValueError as exc:
        return {
            "available": False,
            "reason": str(exc),
            "training_censoring_distribution": True,
            "truncation_time": tau,
        }
    return {
        "available": True,
        "score": score,
        "training_censoring_distribution": True,
        "truncation_time": tau,
    }


def nested_tune(
    X: Any,
    y: Any,
    *,
    model_name: str,
    numeric_columns: list[str],
    categorical_columns: list[str],
    outer_folds: int,
    inner_folds: int,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run nested CV on training data, then tune once on all training rows."""

    try:
        from sklearn.model_selection import GridSearchCV
        from sksurv.metrics import concordance_index_censored
    except ImportError as exc:
        raise CliError("scikit-learn and scikit-survival are required") from exc

    outer_results: list[dict[str, Any]] = []
    for fold, (train_index, validation_index) in enumerate(
        stratified_splits(y, outer_folds, seed=seed), start=1
    ):
        X_outer_train = X.iloc[train_index]
        X_outer_validation = X.iloc[validation_index]
        y_outer_train = y[train_index]
        y_outer_validation = y[validation_index]
        inner = stratified_splits(y_outer_train, inner_folds, seed=seed + fold)
        search = GridSearchCV(
            build_pipeline(
                model_name,
                numeric_columns,
                categorical_columns,
                seed=seed + fold,
            ),
            parameter_grid(model_name),
            cv=inner,
            error_score="raise",
            n_jobs=1,
        )
        search.fit(X_outer_train, y_outer_train)
        risk = search.predict(X_outer_validation)
        harrell = float(
            concordance_index_censored(
                y_outer_validation[_event_field(y_outer_validation)],
                y_outer_validation[_time_field(y_outer_validation)],
                risk,
            )[0]
        )
        outer_results.append(
            {
                "best_params": search.best_params_,
                "fold": fold,
                "harrell_c": harrell,
                "uno_c": uno_concordance(y_outer_train, y_outer_validation, risk),
                "validation_rows": int(len(validation_index)),
            }
        )

    final_inner = stratified_splits(y, inner_folds, seed=seed + 10_000)
    final_search = GridSearchCV(
        build_pipeline(
            model_name,
            numeric_columns,
            categorical_columns,
            seed=seed,
        ),
        parameter_grid(model_name),
        cv=final_inner,
        error_score="raise",
        n_jobs=1,
    )
    final_search.fit(X, y)
    return outer_results, {
        "best_estimator": final_search.best_estimator_,
        "best_params": final_search.best_params_,
    }


def prediction_archive(
    estimator: Any,
    X_test: Any,
    y_train: Any,
    y_test: Any,
    risk: Any,
) -> dict[str, Any]:
    """Build metric-evaluator input without serializing the estimator."""

    import numpy as np

    train_time = y_train[_time_field(y_train)]
    test_time = y_test[_time_field(y_test)]
    lower = float(np.quantile(test_time, 0.2))
    upper = float(
        min(
            np.quantile(test_time, 0.8),
            np.nextafter(train_time.max(), -np.inf),
        )
    )
    if not lower < upper:
        raise CliError("cannot construct a train-supported prediction time grid")
    times = np.linspace(lower, upper, 8)
    arrays: dict[str, Any] = {
        "risk": np.asarray(risk, dtype=float),
        "test_event": y_test[_event_field(y_test)],
        "test_time": test_time,
        "times": times,
        "train_event": y_train[_event_field(y_train)],
        "train_time": train_time,
    }
    if hasattr(estimator, "predict_survival_function"):
        try:
            functions = estimator.predict_survival_function(X_test)
            arrays["survival"] = np.vstack([function(times) for function in functions])
        except (AttributeError, NotImplementedError, ValueError) as exc:
            raise CliError(f"could not export requested survival probabilities: {exc}") from exc
    from evaluate_survival_metrics import validate_predictions

    validate_predictions(arrays)
    return arrays


def train_and_report(
    frame: Any,
    *,
    event_column: str,
    time_column: str,
    numeric_columns: list[str],
    categorical_columns: list[str],
    model_name: str,
    test_fraction: float,
    seed: int,
    tune: bool,
    outer_folds: int,
    inner_folds: int,
) -> tuple[Any, Any, Any, dict[str, Any]]:
    """Split first, then fit all learned preprocessing inside a pipeline."""

    try:
        import numpy as np
        from sklearn.model_selection import train_test_split
        from sksurv.metrics import concordance_index_censored
    except ImportError as exc:
        raise CliError("the pinned survival stack is required") from exc

    X, y, schema = resolve_schema(
        frame,
        event_column=event_column,
        time_column=time_column,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_fraction,
        random_state=seed,
        stratify=y[event_column],
    )

    nested_results: list[dict[str, Any]] | None = None
    best_params: dict[str, Any] | None = None
    if tune:
        nested_results, tuned = nested_tune(
            X_train,
            y_train,
            model_name=model_name,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            outer_folds=outer_folds,
            inner_folds=inner_folds,
            seed=seed,
        )
        estimator = tuned["best_estimator"]
        best_params = tuned["best_params"]
    else:
        estimator = build_pipeline(
            model_name, numeric_columns, categorical_columns, seed=seed
        )
        estimator.fit(X_train, y_train)

    risk = estimator.predict(X_test)
    harrell = float(
        concordance_index_censored(y_test[event_column], y_test[time_column], risk)[0]
    )
    transformed_features = int(
        estimator.named_steps["preprocess"].get_feature_names_out().shape[0]
    )
    nested_harrell = (
        None
        if not nested_results
        else {
            "mean": float(np.mean([item["harrell_c"] for item in nested_results])),
            "standard_deviation": float(
                np.std([item["harrell_c"] for item in nested_results], ddof=1)
            )
            if len(nested_results) > 1
            else 0.0,
        }
    )
    report = {
        "data": {
            "censored_test": int((~y_test[event_column]).sum()),
            "censored_train": int((~y_train[event_column]).sum()),
            "events_test": int(y_test[event_column].sum()),
            "events_train": int(y_train[event_column].sum()),
            "rows_test": int(len(y_test)),
            "rows_train": int(len(y_train)),
        },
        "evaluation": {
            "harrell_c": harrell,
            "nested_cv_harrell_c": nested_harrell,
            "uno_c": uno_concordance(y_train, y_test, risk),
        },
        "leakage_controls": {
            "holdout_used_for_tuning": False,
            "preprocessing_fit_scope": "training folds only",
            "split_before_imputation_encoding_scaling": True,
            "tuning_evaluation": "nested_cv_on_training_split" if tune else "not_run",
        },
        "model": {
            "best_params": best_params,
            "family": model_name,
            "transformed_feature_count": transformed_features,
        },
        "package_versions": {
            "numpy": version("numpy"),
            "pandas": version("pandas"),
            "scikit-learn": version("scikit-learn"),
            "scikit-survival": version("scikit-survival"),
        },
        "schema": schema,
        "schema_version": "1.0",
        "seed": seed,
        "tuning": {
            "inner_folds": inner_folds if tune else None,
            "outer_folds": outer_folds if tune else None,
            "outer_results": nested_results,
            "performed": tune,
        },
        "warning": (
            "Predictive metrics do not establish calibration, transportability, "
            "causal effects, or clinical utility. This tool is not clinical advice."
        ),
    }
    return estimator, (X_train, y_train), (X_test, y_test, risk), report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Train a leakage-safe Cox or ensemble example. Local CSV use requires "
            "an explicit feature schema; no network access is performed."
        )
    )
    parser.add_argument("--input", help="Optional bounded local .csv")
    parser.add_argument("--event-column", default="event")
    parser.add_argument("--time-column", default="time")
    parser.add_argument("--numeric-columns", help="Comma-separated numeric features")
    parser.add_argument(
        "--categorical-columns", help="Comma-separated categorical features"
    )
    parser.add_argument("--model", choices=MODEL_CHOICES, default="coxph")
    parser.add_argument("--test-fraction", type=probability, default=0.25)
    parser.add_argument("--seed", type=bounded_int(0, 2**32 - 1), default=DEFAULT_SEED)
    parser.add_argument(
        "--synthetic-rows",
        type=bounded_int(80, 20_000),
        default=240,
    )
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Run bounded nested CV on training data before final holdout evaluation",
    )
    parser.add_argument("--outer-folds", type=bounded_int(2, 5), default=3)
    parser.add_argument("--inner-folds", type=bounded_int(2, 5), default=3)
    parser.add_argument(
        "--prediction-output",
        help="Optional local .npz for evaluate_survival_metrics.py",
    )
    parser.add_argument("--output", help="Optional local .json summary")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.input:
            frame, source_name = read_csv(args.input)
            numeric = parse_names(args.numeric_columns)
            categorical = parse_names(args.categorical_columns)
            source = {"kind": "local_csv", "name": source_name}
        else:
            frame, default_numeric, default_categorical = synthetic_survival_frame(
                rows=args.synthetic_rows, seed=args.seed
            )
            numeric = parse_names(args.numeric_columns) or default_numeric
            categorical = parse_names(args.categorical_columns) or default_categorical
            source = {
                "kind": "synthetic",
                "network_used": False,
                "seed": args.seed,
            }

        estimator, train_data, test_data, report = train_and_report(
            frame,
            event_column=args.event_column,
            time_column=args.time_column,
            numeric_columns=numeric,
            categorical_columns=categorical,
            model_name=args.model,
            test_fraction=args.test_fraction,
            seed=args.seed,
            tune=args.tune,
            outer_folds=args.outer_folds,
            inner_folds=args.inner_folds,
        )
        report["source"] = source
        if args.prediction_output:
            X_train, y_train = train_data
            X_test, y_test, risk = test_data
            del X_train
            atomic_save_npz(
                prediction_archive(estimator, X_test, y_train, y_test, risk),
                args.prediction_output,
                force=args.force,
            )
            report["prediction_output"] = args.prediction_output
        emit_json(report, output=args.output, force=args.force)
    except CliError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
