# Pipelines, Existing Models, and Tuning

Examples continue from the `data`, `log_var`, and `LogisticRegression` imports defined in SKILL.md
Steps 2-3. Reviewed against xdflow 0.4.0.

## Composition

Every composite is itself a step, so composites nest and can be passed anywhere a step is expected.

| Composite | Use when |
|---|---|
| `Pipeline(name, [(step_name, step), ...])` | steps run in sequence; `xdflow.make_pipeline(*steps)` names them automatically |
| `SwitchTransform(choices=[(name, step), ...], choose=name)` | one position has alternative implementations (tunable) |
| `OptionalTransform(step, use=True)` | a step can be skipped (tunable) |
| `TransformUnion(transforms_list, from_dims, to_dim)` | independent feature branches concatenated along `to_dim` |
| `UnionWithInput(transform_template, join_dim)` | original input concatenated with a transformed version |
| `GroupApplyTransform(group_coord, transform_template)` | a separate clone fitted per subject, session, or device |
| `EnsemblePredictor` | combine predictors; `weighting_strategy="score_based"` needs a `calibration_container` |

```python
from xdflow import GroupApplyTransform, OptionalTransform, Pipeline, SKLearnPredictor, SwitchTransform
from xdflow.transforms import AverageTransform, ZScoreTransform

features = SwitchTransform(
    choices=[
        ("log_var", log_var()),
        ("mean_amplitude", AverageTransform(dims="time")),
    ],
    choose="log_var",
)

pipeline = Pipeline(
    "switchable",
    [
        ("features", features),
        ("per_subject_norm", GroupApplyTransform(  # z-score fitted per subject, inside each fold
            group_coord="subject",
            transform_template=ZScoreTransform(per_dim="channel", use_fit=True),
        )),
        ("maybe_trial_zscore", OptionalTransform(ZScoreTransform(per_dim="trial"), use=False)),
        ("clf", SKLearnPredictor(LogisticRegression, sample_dim="trial", target_coord="label", max_iter=1000)),
    ],
)

pipeline.set_params(features__choose="mean_amplitude", clf__C=0.5)  # nested names, as in scikit-learn
```

`pipeline.get_expected_output_dims(("trial", "channel", "time"), print_steps=True)` prints the dimension flow
without data, but only when every step declares its output dims; an `@xdflow.step` function needs
`@xdflow.step(output_dims=(...))` for this, otherwise the call raises `NotImplementedError`.

`GroupApplyTransform` raises `TransformError` on a group unseen at fit time (`unseen_policy="error"`, the
default), so the pipeline above fails under leave-subject-out CV. `unseen_policy="average"` or
`"weighted_average"` applies every fitted clone and averages their outputs; that is a different model for new
subjects (other subjects' statistics, not the new subject's own), so state it when reporting.
`group_coord` also accepts a list (`["subject", "session"]`) to combine coordinates into one key.

## Wrapping scikit-learn Models

```python
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge

from xdflow import SKLearnTransformer

pca = SKLearnTransformer(PCA, sample_dim="trial", n_components=3)  # estimator class + its kwargs
clf = SKLearnPredictor(LogisticRegression, sample_dim="trial", target_coord="label", max_iter=1000)
reg = SKLearnPredictor(Ridge, sample_dim="trial", target_coord="session", alpha=1.0)  # regression target
```

- `target_coord` names the trial coordinate holding the target; a list gives multi-target regression, and
  `is_multilabel=True` is only for classifiers over several binary target coordinates.
- `sample_weight_coord="w"` passes a trial coordinate as `sample_weight`.
- Existing estimator **instances** or scikit-learn `Pipeline`s wrap unchanged; their parameters stay tunable
  (`"lda__solver"`), and N-D input is passed sample-first:

```python
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

existing = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
wrapped = SKLearnPredictor.from_estimator(existing, sample_dim="trial", target_coord="label")
```

- In `SKLearnPredictor`, class-indexed parameters such as a `class_weight` dict refer to label codes
  `0, 1, 2...` of the sorted classes unless `fit_on_labels=True`; `evaluate` sets this for models it wraps.

### Probability Metrics

ROC AUC and log loss need probabilities, which a validator provides:

```python
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

import xdflow

auc_cv = xdflow.SplitterValidator(
    GroupKFold(3),
    group_coord="subject",
    scoring=lambda y_true, proba: roc_auc_score(y_true, proba[:, 1]),  # columns in sorted class order
    scoring_needs_proba=True,
    verbose=False,
)
auc_result = xdflow.evaluate([log_var(), existing], data, "label", cv=auc_cv)
```

## Tuning (requires `xdflow[tuning]`)

The `Tuner` clones the pipeline per Optuna trial, applies sampled parameters, and scores through the
validator. With `use_cache=True` (default) the prefix before the first tunable or stateful step is computed
once for all trials.

```python
from sklearn.metrics import balanced_accuracy_score

from xdflow import LeaveGroupOutValidator, Tuner

tunable = Pipeline(
    "tunable",
    [
        ("log_var", log_var()),
        ("maybe_zscore", OptionalTransform(ZScoreTransform(per_dim="channel", use_fit=True), use=True)),
        ("clf", SKLearnPredictor(LogisticRegression, sample_dim="trial", target_coord="label", max_iter=1000)),
    ],
)

search_cv = LeaveGroupOutValidator(
    group_coord="subject", test_group_ids=["s5"], scoring=balanced_accuracy_score, verbose=False
)

tuner = Tuner(
    pipelines_to_tune=tunable,
    cv_strategy=search_cv,
    param_grid={
        "tunable": {  # pipeline name -> step name -> parameter -> space
            "clf": {"C": ("log", 1e-3, 10.0), "class_weight": [None, "balanced"]},
        },
    },
    initial_data_container=data,
    random_seed=0,
    verbose=0,
)
best_params, best_score = tuner.tune(n_trials=10)
holdout = tuner.score_best_pipeline_on_holdout()  # s5 was never seen by the search
final = tuner.finalize_best_pipeline()  # refit for inference after the holdout is scored
```

Search space formats: list (categorical), `(int, int)` (integer range), `(float, float)` (float range),
`("log", low, high)` (log-scaled float). `SwitchTransform` and `OptionalTransform` positions are sampled
automatically; parameters of the wrapped step in `OptionalTransform` live under its lowercase class name
(`{"maybe_zscore": {"zscoretransform": {"per_dim": [...]}}}`). Pass a list of pipelines with distinct names
to compare architectures; each gets its own entry in `param_grid`.

`best_score` is selected over many trials and is optimistic. Report the holdout score (or an outer split),
not `best_score`. MLflow logging is off by default (`use_mlflow=True` with `xdflow[mlflow]`).

For a model first run through `evaluate`, `result.pipeline` is a pipeline named `"model"` whose steps are named
after their class or function (`"log_var"`, and `"pipeline"` for a scikit-learn `Pipeline`, whose own steps
follow as `"pipeline__logisticregression__C"`). Print it to see the names.

## Using xdflow Inside scikit-learn

`to_sklearn` turns an xdflow pipeline into a scikit-learn estimator over sample-first NumPy arrays, for
`cross_val_score`, `GridSearchCV` (`"pipeline__<step>__<param>"`), or MOABB:

```python
from sklearn.model_selection import cross_val_score

estimator = xdflow.to_sklearn(
    tunable,
    dims=("trial", "channel", "time"),
    coords={"channel": ["C3", "Cz", "C4", "Pz"]},  # needed for steps that select by label
)
scores = cross_val_score(
    estimator, data.data.values, data.data["label"].values, groups=data.data["subject"].values, cv=GroupKFold(3)
)
```

Inside scikit-learn, every step is refit per fold (scikit-learn has no stateless prefix), so the
compute-once savings apply only when xdflow runs the validation.
