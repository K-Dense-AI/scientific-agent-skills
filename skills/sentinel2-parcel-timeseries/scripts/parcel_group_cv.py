#!/usr/bin/env python3
"""Parcel-level validation for models trained on pixels with parcel (weak) labels.

When every pixel inherits its parcel's label, pixels of one parcel are not
independent samples: they share soil, management, sowing date and label.
Splitting pixels at random puts the same parcel in train and test, and the
model scores well by recognising the parcel, not the condition. This script
applies the protocol that avoids it:

1. leave one parcel out: each parcel is predicted by a model that never saw
   any of its pixels;
2. pixel probabilities are averaged per parcel;
3. the AUC is computed over parcels, the real sample size;
4. optionally, a permutation test shuffles labels between parcels and reports
   how often a random labelling does as well;
5. optionally, the leaky random pixel split is computed side by side, to show
   how much it inflates the score.

Input is a CSV with one row per pixel (or per any sub-parcel unit): a parcel
column, a binary label column and numeric feature columns. ``--features`` is a
regular expression that selects feature columns, which is how a negative
control is run (for example, only features from before sowing).

Example
-------
    python parcel_group_cv.py pixels.csv --group-col parcel_id --label-col infected \\
        --model rf --permutations 200 --compare-leaky
    python parcel_group_cv.py --demo
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Callable, Sequence

import numpy as np

FitPredict = Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]


# ----------------------------------------------------------------- core logic
def parcel_table(prob: np.ndarray, y: np.ndarray, groups: np.ndarray):
    """Mean pixel probability and label per parcel, as three aligned arrays.

    Raises if a parcel carries more than one label: weak labels are parcel
    labels, so a mixed parcel means the table was built wrongly.
    """
    prob, y, groups = np.asarray(prob, float), np.asarray(y), np.asarray(groups)
    names = np.unique(groups)
    score, label = np.empty(len(names)), np.empty(len(names), dtype=y.dtype)
    for i, g in enumerate(names):
        mask = groups == g
        values = np.unique(y[mask])
        if len(values) != 1:
            raise ValueError(f"parcel {g!r} has several labels {values.tolist()}")
        score[i] = np.nanmean(prob[mask])
        label[i] = values[0]
    return names, score, label


def parcel_auc(prob: np.ndarray, y: np.ndarray, groups: np.ndarray) -> float:
    """AUC over parcels after averaging pixel probabilities per parcel."""
    from sklearn.metrics import roc_auc_score

    _, score, label = parcel_table(prob, y, groups)
    if len(np.unique(label)) < 2:
        raise ValueError("parcel AUC needs at least one parcel of each class")
    return float(roc_auc_score(label, score))


def leave_one_parcel_out(X: np.ndarray, y: np.ndarray, groups: np.ndarray,
                         fit_predict: FitPredict) -> np.ndarray:
    """Out-of-parcel probability for every pixel (LeaveOneGroupOut)."""
    from sklearn.model_selection import LeaveOneGroupOut

    prob = np.full(len(y), np.nan)
    for train, test in LeaveOneGroupOut().split(X, y, groups):
        assert not set(groups[train]) & set(groups[test])
        prob[test] = fit_predict(X[train], y[train], X[test])
    return prob


def random_pixel_cv(X: np.ndarray, y: np.ndarray, fit_predict: FitPredict,
                    n_splits: int = 5, seed: int = 0) -> np.ndarray:
    """Leaky baseline: stratified random folds over pixels, ignoring parcels."""
    from sklearn.model_selection import StratifiedKFold

    prob = np.full(len(y), np.nan)
    for train, test in StratifiedKFold(n_splits, shuffle=True, random_state=seed).split(X, y):
        prob[test] = fit_predict(X[train], y[train], X[test])
    return prob


def permutation_pvalue(X: np.ndarray, y: np.ndarray, groups: np.ndarray,
                       fit_predict: FitPredict, observed: float,
                       n_permutations: int = 100, seed: int = 0) -> tuple[float, np.ndarray]:
    """Shuffle labels between parcels (never between pixels) and refit.

    Returns the p-value (with the +1 correction) and the null AUCs.
    """
    rng = np.random.default_rng(seed)
    names, _, label = parcel_table(np.zeros(len(y)), y, groups)
    index = {g: i for i, g in enumerate(names)}
    parcel_of_pixel = np.array([index[g] for g in groups])
    null = np.empty(n_permutations)
    for b in range(n_permutations):
        shuffled = rng.permutation(label)
        y_perm = shuffled[parcel_of_pixel]
        null[b] = parcel_auc(leave_one_parcel_out(X, y_perm, groups, fit_predict), y_perm, groups)
    return float((1 + np.sum(null >= observed)) / (1 + n_permutations)), null


def make_model(name: str, seed: int = 0) -> FitPredict:
    """fit_predict closure for a random forest or a standardised logistic regression."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    def fit_predict(X_train, y_train, X_test):
        if name == "rf":
            model = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                           min_samples_leaf=5, n_jobs=1, random_state=seed)
        elif name == "logistic":
            model = make_pipeline(StandardScaler(),
                                  LogisticRegression(max_iter=2000, class_weight="balanced"))
        else:
            raise ValueError(f"unknown model {name!r}")
        return model.fit(X_train, y_train).predict_proba(X_test)[:, 1]

    return fit_predict


def synthetic_parcels(n_parcels: int = 16, pixels: int = 60, n_features: int = 6, seed: int = 0):
    """Pixels whose features carry a strong parcel signature but no label signal.

    Labels are assigned to parcels at random, so an honest protocol should find
    parcel AUC near 0.5, while a random pixel split recognises the parcels.
    """
    rng = np.random.default_rng(seed)
    signature = rng.normal(0, 1, (n_parcels, n_features))
    parcel_label = rng.permutation(np.arange(n_parcels) % 2)
    groups = np.repeat([f"P{i:02d}" for i in range(n_parcels)], pixels)
    X = np.repeat(signature, pixels, axis=0) + rng.normal(0, 0.3, (n_parcels * pixels, n_features))
    y = np.repeat(parcel_label, pixels)
    return X, y, groups


# ------------------------------------------------------------------------- CLI
def load_csv(path: str, group_col: str, label_col: str, features: str | None):
    import pandas as pd

    table = pd.read_csv(path)
    for col in (group_col, label_col):
        if col not in table.columns:
            raise SystemExit(f"column {col!r} not in {list(table.columns)}")
    candidates = [c for c in table.columns if c not in (group_col, label_col)
                  and pd.api.types.is_numeric_dtype(table[c])]
    if features:
        pattern = re.compile(features)
        candidates = [c for c in candidates if pattern.search(c)]
    if not candidates:
        raise SystemExit("no numeric feature column selected")
    X = table[candidates].to_numpy(float)
    X = np.where(np.isfinite(X), X, np.nanmedian(X, axis=0))   # simple, fold-independent fill
    return X, table[label_col].to_numpy(), table[group_col].astype(str).to_numpy(), candidates


def report(X, y, groups, model: str, permutations: int, compare_leaky: bool, seed: int) -> dict:
    fit_predict = make_model(model, seed)
    n_parcels = len(np.unique(groups))
    _, _, parcel_labels = parcel_table(np.zeros(len(y)), y, groups)
    per_class = {int(c): int((parcel_labels == c).sum()) for c in np.unique(parcel_labels)}
    if len(per_class) < 2 or min(per_class.values()) < 2:
        raise SystemExit(f"need at least 2 parcels of each class, got {per_class}: with one parcel "
                         "of a class, leaving it out leaves a training set with a single class")
    prob = leave_one_parcel_out(X, y, groups, fit_predict)
    result = {"pixels": len(y), "parcels": n_parcels, "model": model,
              "parcel_auc_leave_one_parcel_out": round(parcel_auc(prob, y, groups), 3)}
    if compare_leaky:
        leaky = random_pixel_cv(X, y, fit_predict, seed=seed)
        result["parcel_auc_random_pixel_split_LEAKY"] = round(parcel_auc(leaky, y, groups), 3)
    if permutations:
        p, null = permutation_pvalue(X, y, groups, fit_predict,
                                     result["parcel_auc_leave_one_parcel_out"], permutations, seed)
        result["permutation_p_value"] = round(p, 4)
        result["null_auc_95th_percentile"] = round(float(np.quantile(null, 0.95)), 3)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Leave-one-parcel-out validation with parcel-level AUC, permutation test "
                    "and leaky-split comparison.")
    parser.add_argument("csv", nargs="?", help="one row per pixel: parcel, label, features")
    parser.add_argument("--group-col", default="parcel_id", help="parcel identifier column")
    parser.add_argument("--label-col", default="label", help="binary label column (0/1)")
    parser.add_argument("--features", help="regular expression selecting feature columns")
    parser.add_argument("--model", choices=("rf", "logistic"), default="rf")
    parser.add_argument("--permutations", type=int, default=0,
                        help="parcel-label permutations for a p-value (0 = skip)")
    parser.add_argument("--compare-leaky", action="store_true",
                        help="also report the (inflated) random pixel split")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--demo", action="store_true",
                        help="run on synthetic parcels where labels carry no signal")
    args = parser.parse_args(argv)

    if args.demo:
        X, y, groups = synthetic_parcels(seed=args.seed)
        print("synthetic parcels: features identify the parcel, labels are random")
        result = report(X, y, groups, args.model, args.permutations, True, args.seed)
    else:
        if not args.csv:
            parser.error("give a CSV or --demo")
        X, y, groups, used = load_csv(args.csv, args.group_col, args.label_col, args.features)
        print(f"{len(used)} feature columns: {', '.join(used[:8])}{' ...' if len(used) > 8 else ''}")
        result = report(X, y, groups, args.model, args.permutations, args.compare_leaky, args.seed)
    for key, value in result.items():
        print(f"{key}: {value}")
    if result["parcels"] < 20:
        print(f"warning: {result['parcels']} parcels; one parcel moves the AUC by a large step, "
              "report the permutation p-value and treat the AUC as indicative")
    return 0


if __name__ == "__main__":
    sys.exit(main())
