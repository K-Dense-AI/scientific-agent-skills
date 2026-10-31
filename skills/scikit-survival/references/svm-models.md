# Survival support vector machines

Verified for scikit-survival 0.28.0 on 2026-10-01.

## What survival SVMs predict

Survival SVMs optimize ranking, regression, or a mixture. They generally return a
scalar score, not a baseline survival function or cumulative hazard function.
Therefore:

- use concordance or cumulative/dynamic AUC only after confirming score direction;
- do not pass SVM output to Brier metrics;
- do not convert a margin to event probability without a separately validated
  calibration model and protocol.

## Fast linear survival SVM

```python
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sksurv.svm import FastSurvivalSVM

model = make_pipeline(
    StandardScaler(),
    FastSurvivalSVM(
        alpha=1.0,
        rank_ratio=1.0,
        max_iter=1000,
        tol=1e-5,
        random_state=20260723,
    ),
)
model.fit(X_train, y_train)
risk = model.predict(X_test)
```

Current signature:

```text
FastSurvivalSVM(
    alpha=1, *,
    rank_ratio=1.0,
    fit_intercept=False,
    max_iter=20,
    verbose=False,
    tol=None,
    optimizer=None,
    random_state=None,
    timeit=False,
)
```

Key semantics:

- `rank_ratio=1.0`: ranking-only objective; higher predictions indicate shorter
  survival/higher event risk.
- `0 < rank_ratio < 1`: mixed ranking and regression.
- `rank_ratio=0.0`: regression-only objective.
- When `rank_ratio < 1`, `predict()` exponentiates the log-time predictor and returns
  original-time values: lower prediction means shorter survival. For a metric requiring
  higher event risk, use `-prediction` and document the conversion.
- `alpha` weights the data-fit/ranking objective relative to the penalty, so larger
  values mean less regularization; tune it within inner CV.

Do not use an arbitrary sign simply because a C-index improves. The sign follows
the model objective and target interpretation.

## Fast kernel survival SVM

```python
from sksurv.svm import FastKernelSurvivalSVM

model = FastKernelSurvivalSVM(
    alpha=1.0,
    rank_ratio=1.0,
    kernel="rbf",
    gamma=0.05,
    max_iter=100,
    tol=1e-5,
    random_state=20260723,
)
model.fit(X_train_scaled, y_train)
risk = model.predict(X_test_scaled)
```

Current signature:

```text
FastKernelSurvivalSVM(
    alpha=1, *,
    rank_ratio=1.0,
    fit_intercept=False,
    kernel="rbf",
    gamma=None,
    degree=3,
    coef0=1,
    kernel_params=None,
    max_iter=20,
    verbose=False,
    tol=None,
    optimizer=None,
    random_state=None,
    timeit=False,
)
```

Kernel choices follow scikit-learn pairwise-kernel behavior, including `"linear"`,
`"poly"`, `"rbf"`, `"sigmoid"`, callable kernels, and `"precomputed"` where
supported. Do not copy older examples that use `gamma="scale"` without checking
the current API; the current scikit-survival parameter default is `None`.

Kernel fitting and prediction depend on training rows and can require
quadratic-size kernel matrices. Enforce row/memory bounds before fitting.

## Hinge, Minlip, and naive formulations

Current additional estimators:

- `HingeLossSurvivalSVM(alpha=1.0, solver="ecos", kernel="linear", pairs="all", ...)`
- `MinlipSurvivalAnalysis(alpha=1.0, solver="ecos", kernel="linear",
  pairs="nearest", ...)`
- `NaiveSurvivalSVM(penalty="l2", loss="squared_hinge", dual=False,
  alpha=1.0, ...)`

Important current differences:

- `HingeLossSurvivalSVM` and `MinlipSurvivalAnalysis` do not have a
  `random_state` constructor parameter.
- Their convex optimization defaults to the ECOS solver.
- Pair construction and kernel matrices can become expensive.
- `NaiveSurvivalSVM` uses a linear-SVM-style formulation and is mainly useful for
  small comparisons; it is not the fast implementation.

Use the exact current signature rather than transferring parameters across SVM
classes.

## Scaling and explicit preprocessing

Scale continuous features and fit scaling only on training folds:

```python
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

preprocess = ColumnTransformer(
    [
        (
            "num",
            make_pipeline(SimpleImputer(strategy="median"), StandardScaler()),
            numeric_columns,
        ),
        (
            "cat",
            make_pipeline(
                SimpleImputer(strategy="most_frequent"),
                OneHotEncoder(
                    drop="first",
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
            categorical_columns,
        ),
    ],
    sparse_threshold=0.0,
)
model = make_pipeline(
    preprocess,
    FastSurvivalSVM(rank_ratio=1.0, random_state=20260723),
)
```

Do not call `StandardScaler.fit_transform(X)` before cross-validation. Keeping it
inside the pipeline makes every inner and outer fold independent.

## Kernel preprocessing

For `"precomputed"`, training input must be a square
`(n_train, n_train)` kernel matrix; test input must be
`(n_test, n_train)` with columns in the identical training order.

`sksurv.kernels.ClinicalKernelTransform` and `clinical_kernel()` support mixed
continuous, ordinal, and nominal DataFrame columns, including pandas/Polars in
0.28. They do not accept an ad hoc list of `(clinical, molecular)` tuples as a
special API. Fit the transform on a clearly typed training DataFrame or explicitly
precompute the kernel:

```python
from sksurv.kernels import ClinicalKernelTransform
from sksurv.svm import FastKernelSurvivalSVM

kernel = ClinicalKernelTransform()
kernel_train = kernel.fit_transform(X_train_typed)
kernel_test = kernel.transform(X_test_typed)

model = FastKernelSurvivalSVM(
    kernel="precomputed",
    rank_ratio=1.0,
    random_state=20260723,
)
model.fit(kernel_train, y_train)
risk = model.predict(kernel_test)
```

The one-shot `clinical_kernel(X_test, X_train)` infers numeric ranges from both
arguments, changing normalization with the test cohort. Prefer the fitted transform
above. The released one-shot Cython routine also allocates its range buffer by
row count while writing one value per numeric feature: avoid that routine when
numeric features outnumber rows (source finding; unsafe case not executed).
Put `ClinicalKernelTransform()` inside the pipeline for CV so its ranges
and reference rows are learned afresh in every fold. Out-of-training-range values
can produce negative similarities in the native transform; inspect support and
define any clipping/extrapolation policy before evaluating.

Any data-dependent kernel typing, scaling, or parameter choice belongs inside the
training/CV protocol.

## Nested tuning

Tune at least `alpha`; for kernel models also tune kernel and its parameters.
Keep the grid bounded:

```python
from sklearn.model_selection import GridSearchCV

search = GridSearchCV(
    pipeline,
    {
        "fastkernelsurvivalsvm__alpha": [0.1, 1.0, 10.0],
        "fastkernelsurvivalsvm__gamma": [0.01, 0.05, 0.2],
    },
    cv=inner_splits,
    error_score="raise",
    n_jobs=1,
)
search.fit(X_outer_train, y_outer_train)
```

The actual parameter prefix depends on pipeline step names. Run this search within
each outer fold for a nested-CV performance estimate. Do not:

- fit a scaler or kernel transform before the outer split;
- select the sign, kernel, or horizon on outer-validation results;
- reuse the final test set to choose `alpha`/`gamma`;
- compare SVM Brier scores, because SVMs do not output survival probabilities.

For IPCW metrics, fit the censoring distribution on the corresponding outer
training outcomes and keep the time grid within that fold's support.

## Choosing an SVM candidate

- Linear ranking objective: a scalable margin-based discrimination baseline.
- Kernel ranking objective: nonlinear relationships when row count permits.
- Mixed/regression objective: time-oriented score, with different sign semantics.
- Need absolute survival probability: choose a model with
  `predict_survival_function()` or add a separately validated calibration stage.
- Need coefficient/hazard-ratio interpretation: use an appropriate Cox model,
  not an SVM margin.

These are capability distinctions, not guarantees of performance.

## Interpretation

SVM margins are arbitrary-scale predictions. A high C-index or dynamic AUC says
that orderings discriminate under the chosen censoring estimator and horizon; it
does not establish:

- probability calibration;
- causal or treatment effects;
- transportability;
- subgroup fairness;
- clinical or decision utility.

Report optimization convergence, score direction, kernel, preprocessing, tuning
resamples, and censoring assumptions.

## Sources

Official sources checked 2026-10-01:

- [Released clinical-kernel implementation](https://github.com/sebp/scikit-survival/blob/v0.28.0/sksurv/kernels/clinical.py) and [Cython ranges](https://github.com/sebp/scikit-survival/blob/v0.28.0/sksurv/kernels/_clinical_kernel.pyx).

- [Survival SVM user guide](https://scikit-survival.readthedocs.io/en/stable/user_guide/survival-svm.html)
- [FastSurvivalSVM API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.svm.FastSurvivalSVM.html)
- [FastKernelSurvivalSVM API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.svm.FastKernelSurvivalSVM.html)
- [HingeLossSurvivalSVM API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.svm.HingeLossSurvivalSVM.html)
- [MinlipSurvivalAnalysis API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.svm.MinlipSurvivalAnalysis.html)
- [NaiveSurvivalSVM API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.svm.NaiveSurvivalSVM.html)
- [Clinical kernels API](https://scikit-survival.readthedocs.io/en/stable/api/kernels.html)
