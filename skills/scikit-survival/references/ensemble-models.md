# Survival trees, forests, and boosting

Verified for scikit-survival 0.28.0 on 2026-10-01.

## Model families

- `SurvivalTree`: one log-rank survival tree.
- `RandomSurvivalForest`: bootstrap-aggregated survival trees with random feature
  subsets.
- `ExtraSurvivalTrees`: additional randomization of candidate split thresholds.
- `GradientBoostingSurvivalAnalysis`: regression-tree gradient boosting.
- `ComponentwiseGradientBoostingSurvivalAnalysis`: linear componentwise base
  learners and implicit sparse selection.

Model family does not determine quality in advance. Compare prespecified candidates
with identical outer resamples, censoring assumptions, time grids, and preprocessing.

## Random survival forest

```python
from sksurv.ensemble import RandomSurvivalForest

model = RandomSurvivalForest(
    n_estimators=500,
    min_samples_split=10,
    min_samples_leaf=8,
    max_features="sqrt",
    n_jobs=1,
    random_state=20260723,
)
model.fit(X_train, y_train)
```

Current defaults include `n_estimators=100`, `min_samples_split=6`,
`min_samples_leaf=3`, `max_features="sqrt"`, `bootstrap=True`, and
`low_memory=False`.

Each terminal node estimates:

- a survival function using Kaplan-Meier;
- a cumulative hazard function using Nelson-Aalen;
- a risk score summing the estimated cumulative hazard over the training event
  times; its magnitude is neither a probability nor an expected count at a named horizon.

Forest predictions average tree predictions:

```python
risk = model.predict(X_test)  # (n_test,), higher is riskier
survival = model.predict_survival_function(X_test, return_array=True)
cumulative_hazard = model.predict_cumulative_hazard_function(
    X_test, return_array=True
)
times = model.unique_times_
```

Array predictions use the model's `unique_times_`. For an evaluation grid, returned
step functions are often more convenient:

```python
import numpy as np

functions = model.predict_survival_function(X_test, return_array=False)
survival_on_grid = np.vstack([fn(evaluation_times) for fn in functions])
```

Do not treat the numeric magnitude of `predict()` as an event probability.

### Missing values and memory

Current survival trees and forest split logic supports missing values, with fixes
aligned to scikit-learn 1.8 in scikit-survival 0.27. This does not remove the need
to:

- verify which columns and missingness patterns are supported;
- encode categorical columns consistently;
- keep all learned preprocessing within training folds;
- assess whether missingness itself changes across deployment settings.

`low_memory=True` reduces stored prediction state but disables survival-function
and cumulative-hazard prediction. It is incompatible with Brier-score workflows
that require survival probabilities.

### OOB estimates

With `oob_score=True` and bootstrap sampling, `oob_score_` provides an internal
out-of-bag concordance estimate. It is not a substitute for:

- nested tuning when parameters were selected using OOB results;
- an independent test set;
- censoring-aware probability metrics;
- external validation.

## Extra survival trees

```python
from sksurv.ensemble import ExtraSurvivalTrees

model = ExtraSurvivalTrees(
    n_estimators=500,
    min_samples_leaf=8,
    max_features="sqrt",
    n_jobs=1,
    random_state=20260723,
)
model.fit(X_train, y_train)
```

Extra trees randomize split thresholds in addition to feature selection. They are
not guaranteed to be faster, better regularized, or better calibrated for a given
dataset. Tune and evaluate them as a distinct candidate under the same protocol.

## Permutation importance

Survival forest impurity importance is not implemented as a valid
`feature_importances_` measure. Use held-out permutation importance with an
explicit score:

```python
from sklearn.inspection import permutation_importance

result = permutation_importance(
    fitted_pipeline,
    X_test,
    y_test,
    scoring=None,  # estimator.score: Harrell concordance
    n_repeats=20,
    random_state=20260723,
    n_jobs=1,
)
```

If Harrell C is not the target, wrap the estimator with the appropriate
scikit-survival scorer class before permutation or write a scorer that fits no
state on the test set. Importance depends on:

- the metric and horizon;
- correlated features;
- the held-out population;
- preprocessing and random seed.

It is predictive sensitivity, not causal importance.

## Tree gradient boosting

```python
from sksurv.ensemble import GradientBoostingSurvivalAnalysis

model = GradientBoostingSurvivalAnalysis(
    loss="coxph",
    learning_rate=0.05,
    n_estimators=300,
    max_depth=2,
    subsample=0.8,
    random_state=20260723,
)
model.fit(X_train, y_train)
```

Current losses:

- `"coxph"`: Cox partial-likelihood objective; `predict()` is a higher-is-riskier
  score, and baseline-based survival/cumulative-hazard methods are available.
- `"ipcwls"`: intended IPC-weighted least-squares AFT objective; see the release
  defects below before relying on it.
- `"squared"`: squared-error time-oriented objective.

Time-oriented losses do not make `predict()` a Cox risk score and do not provide
the same baseline survival-function interface. Both non-Cox losses return exponentiated predictions on the original-time scale.
Confirm prediction direction before
using concordance or dynamic AUC; negate a predicted-time output only when that
conversion is explicitly intended and reported.

Released 0.28.0 `ipcwls` has two native/source-confirmed limitations in both
boosting classes: positive times below 1 become negative after the internal log
transform and the censoring-weight estimator rejects them; and the gradient
omits IPC weights even though the reported loss uses them. With fixed iterations,
full subsampling, and default sample weights, changing event/censor labels while
keeping observed times fixed produced identical predictions on the synthetic
fixture. Do not treat a successful `ipcwls` fit as validated IPC-weighted training
or change time units merely to hide the error. Prefer a verified alternative such
as `IPCRidge` when an IPC-weighted AFT fit is required.

Current regularization controls:

- `learning_rate`
- `n_estimators`
- `subsample`
- `dropout_rate`
- tree depth/leaf controls
- `ccp_alpha`
- `validation_fraction`, `n_iter_no_change`, and `tol`
- a custom `monitor` passed to `fit()` for controlled early stopping

The old `criterion` parameter was removed in 0.28. Do not copy it from older
examples.

Use only training data for internal early stopping. The final test set must not be
the monitor or validation fraction.

## Componentwise boosting

```python
from sksurv.ensemble import ComponentwiseGradientBoostingSurvivalAnalysis

model = ComponentwiseGradientBoostingSurvivalAnalysis(
    loss="coxph",
    learning_rate=0.1,
    n_estimators=300,
    subsample=0.8,
    random_state=20260723,
)
model.fit(X_train_scaled, y_train)
```

At each iteration, a componentwise learner updates one encoded feature. The final
model is linear and often sparse. Its `coef_` includes the fitted intercept entry
used by the implementation; align coefficients with transformed feature names
carefully.

Iteration count is a selection parameter. Repeatedly checking test performance
while increasing `n_estimators` leaks the test set. Tune it inside inner CV, and
assess selected-feature stability across outer resamples.

## Leakage-safe nested tuning

```python
from sklearn.model_selection import GridSearchCV

inner_search = GridSearchCV(
    pipeline,
    {
        "model__min_samples_leaf": [3, 8, 16],
        "model__max_features": ["sqrt", 0.5, 1.0],
    },
    cv=inner_splits,
    error_score="raise",
    n_jobs=1,
)
inner_search.fit(X_outer_train, y_outer_train)
risk_outer = inner_search.predict(X_outer_valid)
```

Run this search inside each outer fold when reporting cross-validated tuned
performance. Every outer score must use:

- outer-training preprocessing only;
- outer-training censoring distribution for IPCW metrics;
- an evaluation grid supported by that outer-training fold;
- outer-validation predictions never used in parameter selection.

After protocol assessment, tune on all development data and evaluate once on the
reserved test set.

## Probability prediction and calibration

Forests and Cox-loss boosting can produce survival probabilities. To use Brier
metrics:

```python
functions = fitted_pipeline.predict_survival_function(X_test)
survival_probability = np.vstack([fn(times) for fn in functions])
```

Then verify:

- shape is `(n_test, n_times)`;
- values are within `[0, 1]`;
- each row is non-increasing over time;
- `times` is strictly increasing and train-supported;
- censoring weights are learned from training outcomes.

A lower Brier score does not prove good calibration in every subgroup or horizon.
Use horizon-specific calibration assessment on independent data. Do not claim
clinical utility from concordance, AUC, or Brier score alone.

## Practical selection questions

- Need coefficient-level PH interpretation? Start with a prespecified Cox model.
- Need nonlinear interactions and probability curves? Compare forest and Cox-loss
  boosting.
- Need sparse linear prediction? Compare Coxnet and componentwise boosting.
- Need time-oriented AFT prediction? Consider IPC-weighted losses and state the
  censoring assumptions.
- Need very large data? Benchmark memory and run time; kernel SVM and large
  survival forests can be expensive.

These are candidate-selection prompts, not performance guarantees.

## Sources

Official sources checked 2026-10-01:

- [Released survival losses](https://github.com/sebp/scikit-survival/blob/v0.28.0/sksurv/ensemble/survival_loss.py) and [fit loops](https://github.com/sebp/scikit-survival/blob/v0.28.0/sksurv/ensemble/boosting.py) — IPCW caveats reproduced natively.

- [Random survival forest user guide](https://scikit-survival.readthedocs.io/en/stable/user_guide/random-survival-forest.html)
- [Gradient boosting user guide](https://scikit-survival.readthedocs.io/en/stable/user_guide/boosting.html)
- [RandomSurvivalForest API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.ensemble.RandomSurvivalForest.html)
- [ExtraSurvivalTrees API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.ensemble.ExtraSurvivalTrees.html)
- [GradientBoostingSurvivalAnalysis API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.ensemble.GradientBoostingSurvivalAnalysis.html)
- [ComponentwiseGradientBoostingSurvivalAnalysis API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.ensemble.ComponentwiseGradientBoostingSurvivalAnalysis.html)
- [0.28 release notes](https://scikit-survival.readthedocs.io/en/stable/release_notes/v0.28.html)
- [0.27 release notes](https://scikit-survival.readthedocs.io/en/stable/release_notes/v0.27.html)
