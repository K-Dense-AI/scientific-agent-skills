---
name: xdflow
description: Builds leakage-safe, cross-validated machine learning pipelines for trial-structured experimental data (EEG, MEG, LFP, spikes, wearables, behavior) with xdflow on labeled xarray data. Use when decoding or classifying trials across subjects, sessions, or animals; when cross-validating a scikit-learn model with grouped or leave-subject-out splits; when auditing an existing split for subject or session leakage; when learned steps (scalers, CSP, PCA) must be refit inside each fold while expensive per-trial feature extraction runs once; when tuning pipeline structure with Optuna; when wrapping MNE Epochs; or when code imports xdflow.
license: MIT
compatibility: Requires Python 3.11+ and xdflow 0.4.0 (numpy, xarray, pandas, scikit-learn). Optional extras - tuning (Optuna), mne (CSPTransform), all. Network needed only for installation.
metadata:
  version: "1.0"
  last-reviewed: "2026-10-27"
  skill-author: General Sense
---

# xdflow: Leakage-Safe ML Pipelines for Experimental Data

## Overview

[xdflow](https://github.com/general-sense/xdflow) runs scikit-learn-style pipelines on `xarray.DataArray`
data whose dimensions (`trial`, `channel`, `time`) and trial coordinates (`label`, `subject`, `session`)
travel with the values through preprocessing, cross-validation, tuning, and prediction. Because every step
declares whether it learns from data, validators cut the pipeline before its first learned step: the prefix
runs once on all trials, and the rest is cloned and refit inside each training fold. Splits are defined by
coordinate name (`groups="subject"`), so no side arrays have to be kept aligned.

**Version note:** Reviewed against **xdflow 0.4.0** on Python 3.12 with synthetic data. Every code block in
this skill and its references was executed except those marked *illustrative* (MNE `Epochs`, which need a
real recording). See the [changelog](https://github.com/general-sense/xdflow/blob/main/CHANGELOG.md) and
[docs](https://xdflow.readthedocs.io/en/latest/).

## When to Use This Skill

- Decoding or classifying trials where samples are correlated within subject, session, animal, or recording
- Reporting a score for **new subjects** (or sessions) rather than new trials from known subjects
- Checking whether an existing `cross_val_score` / `StratifiedKFold` split leaks subjects or sessions
- Pipelines mixing expensive per-trial features (filtering, spectra, band power) with learned steps
- Hyperparameter or architecture search where feature extraction should not be recomputed per trial
- Per-subject or per-session models and normalization (`GroupApplyTransform`)

Prefer other skills for: generic tabular ML without grouped structure (`scikit-learn`), forecasting
(`aeon`, `timesfm-forecasting`), raw signal processing itself (MNE-Python, `neurokit2`), and out-of-core
data (xdflow works on in-memory arrays).

## Installation

```bash
uv pip install "xdflow==0.4.0"            # core
uv pip install "xdflow[tuning]==0.4.0"    # + Optuna Tuner
uv pip install "xdflow[mne]==0.4.0"       # + CSPTransform (MNE-Python)
```

## Choose the Entry Point

| Situation | Use |
|---|---|
| Have arrays / DataArray / MNE `Epochs` and a scikit-learn model; want a trustworthy score | `xdflow.evaluate` |
| Already have a split and want to know if it leaks subjects, sessions, or duplicates | `xdflow.check_split` |
| Need a holdout set, per-group models, custom validators, or out-of-fold predictions with metadata | `Pipeline` + a validator |
| Search over parameters or pipeline structure | `Tuner` (see [references/pipelines-and-tuning.md](references/pipelines-and-tuning.md)) |
| Need a scikit-learn estimator (`GridSearchCV`, MOABB) | `xdflow.to_sklearn` |
| Own preprocessing or feature code | `@xdflow.step` (see [references/custom-steps.md](references/custom-steps.md)) |

## Step 1: Decide What the Score Must Generalize To

This is the scientific decision; xdflow only enforces it. Ask which unit a deployed model will meet for the
first time, and keep that unit on one side of every split:

- **New trials from known subjects** (within-subject decoding): fold over trials, `groups=None`.
- **New subjects / animals**: `groups="subject"` or `LeaveGroupOutValidator(group_coord="subject")`.
- **New sessions of known subjects**: group by session. Session numbers usually restart per subject, so
  build a combined trial coordinate first (for example `subject_session=[f"{a}/{b}" for a, b in
  zip(subject, session)]` in `from_numpy`) and group by that.
- **Windows cut from longer trials**: store the source trial as an `orig_trial` coordinate so all windows of
  one trial stay together.

Report which choice was made next to every score. A within-subject score is not evidence of cross-subject
generalization.

## Step 2: Put the Data in a Container

Data must have a `trial` dimension with **unique** trial labels; targets and groups are trial coordinates.

```python
import numpy as np
import xdflow

rng = np.random.default_rng(0)
subject = np.repeat([f"s{i}" for i in range(6)], 40)
session = np.tile(np.repeat([1, 2], 20), 6)
label = rng.choice(["left", "right"], size=subject.size)
X = rng.normal(size=(subject.size, 4, 50))  # trial x channel x time
X[label == "right", 1, :] *= 1.5  # synthetic effect: more variance on channel Cz

data = xdflow.from_numpy(
    X,
    ("trial", "channel", "time"),
    coords={"channel": ["C3", "Cz", "C4", "Pz"], "time": np.linspace(0.0, 1.0, 50, endpoint=False)},
    label=label,
    subject=subject,
    session=session,
)
print(data.data)  # an xarray.DataArray with label/subject/session attached to trial
```

Other sources (*illustrative*):

```python
data = xdflow.from_mne_epochs(epochs)  # event names -> "label"; epochs.metadata columns -> trial coords
data = xdflow.from_mne_epochs(epochs, subject=3)  # add a constant or per-trial coordinate
data = xdflow.DataContainer(my_dataarray)  # any DataArray with a "trial" dim
```

When concatenating sessions or subjects, renumber `trial` afterwards: duplicate trial labels raise in
cross-validation.

## Step 3: Quick Path with `evaluate`

```python
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


@xdflow.step
def log_var(data):  # per-trial feature: depends on that trial only, so it runs once
    return np.log(data.var("time"))


model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))  # learned: refit per fold
result = xdflow.evaluate([log_var(), model], data, "label", groups="subject")
print(result)
```

```text
accuracy 0.970 ± 0.019 (mean ± sd over 5 folds, 240 trials)
Split: 5-fold, grouped by subject (6 values), stratified by class
Computed once: log_var. Refit in each fold: pipeline (standardscaler, logisticregression).
...
Split check: nothing shared between training and test sets (subject, session (within subject), identical samples).
```

Read the printed `Computed once` / `Refit in each fold` lines and the split check before trusting the score.

- `result.score`, `result.fold_scores`: mean and per-fold scores
- `result.by("subject")`: score and trial count per subject (or any trial coordinate)
- `result.predictions`: pandas DataFrame, one row per trial with its coordinates, `y_true`, `y_pred`, `fold`
- `result.pipeline`: the xdflow pipeline that was run (step names are used for tuning)
- `result.fit_final()`: refit on all trials for inference; `predict` needs no labels

Plain NumPy works too: `xdflow.evaluate(model, X2d, y, groups=subject_ids)`. A scikit-learn model that
expects 2-D input needs a feature step first when `X` is `trial x channel x time`; N-D input is passed
sample-first unchanged.

Arguments that change the question being answered:

- `cv=5` (default) or any scikit-learn splitter (`GroupKFold(5)`, `TimeSeriesSplit(4)`) or an xdflow validator
- `scoring=` takes scikit-learn metric names (`"balanced_accuracy"`, `"f1_macro"`, `"r2"`); probability
  metrics such as ROC AUC need a validator with `scoring_needs_proba=True` (see the pipelines reference)
- without `groups`, `evaluate` warns when the data carries a subject or session coordinate that is shared
  across folds

## Step 4: Audit a Split You Already Use

```python
import pandas as pd
from sklearn.model_selection import StratifiedKFold

report = xdflow.check_split(
    X.reshape(len(X), -1),
    StratifiedKFold(5, shuffle=True, random_state=0),
    y=label,
    metadata=pd.DataFrame({"subject": subject, "session": session}),
)
print(report)
```

```text
Split check over 5 folds: shared data found.
  - The same 'subject' values appear in training and test sets in 5 of 5 folds: ...
```

Coordinates are recognized by name (`subject`, `participant`, `session`, `run`, `block`, `orig_trial`, ...);
pass `groups=` to audit anything else. A validator that has run `cross_validate` can be audited with
`xdflow.check_split(data, validator)`.

## Step 5: Full Pipeline with a Validator

Use this path for a holdout set, out-of-fold predictions as a labeled container, per-group models, or tuning.

```python
from sklearn.metrics import balanced_accuracy_score

from xdflow import LeaveGroupOutValidator, Pipeline, SKLearnPredictor
from xdflow.transforms import ZScoreTransform

pipeline = Pipeline(
    "logvar_lr",
    [
        ("log_var", log_var()),  # stateless: computed once for all folds
        ("zscore", ZScoreTransform(per_dim="channel", use_fit=True)),  # learned: refit per fold
        ("clf", SKLearnPredictor(LogisticRegression, sample_dim="trial", target_coord="label", max_iter=1000)),
    ],
)

cv = LeaveGroupOutValidator(
    group_coord="subject",
    test_group_ids=["s5"],  # holdout subject: never used in CV fits or scores
    scoring=balanced_accuracy_score,  # validators take metric functions or a fixed set of names
    verbose=False,
)
cv.set_pipeline(pipeline)
cv_score = cv.cross_validate(data)  # one fold per remaining subject

oof = cv.oof_predictions_container_.data  # predictions keep trial, subject, session, fold coordinates
per_subject = (oof == oof["label"]).groupby("subject").mean()

holdout_score = cv.score_on_holdout(data)  # fit on all non-holdout subjects, score on s5
final_model = cv.finalize_pipeline(data)  # refit on everything passed in, for inference only
new_predictions = final_model.predict(data).data  # DataArray of labels along trial
print(f"CV {cv_score:.3f}, holdout {holdout_score:.3f}")
```

Score the holdout **before** finalizing: `finalize_pipeline` fits on the whole container it receives,
including holdout trials, so its outputs are not a test score.

### Validators

| Validator | Splits | Keeps groups apart? | Holdout argument |
|---|---|---|---|
| `LeaveGroupOutValidator(group_coord=...)` | one group per fold (`n_splits` to subsample) | yes | `test_group_ids=[...]` |
| `LeaveSessionOutValidator` / `LeaveAnimalOutValidator` | presets on `session` / `animal` | yes | `test_session_ids=` / `test_animal_ids=` |
| `SplitterValidator(GroupKFold(5), group_coord=...)` | any scikit-learn splitter or index pairs | if the splitter does | none |
| `KFoldValidator(n_splits, stratify_coord=...)` | trials; windows of one `orig_trial` stay together | no | `test_size=0.2` |
| `GroupedKFoldValidator(group_coord=..., n_splits)` | trials stratified by group x label, so **every group is in every fold**; `train_groups`/`val_groups` restrict sides | **no** | `test_size=` (+ `test_groups=[...]`) |
| `SampledDomainKFoldValidator` | source/target domain sampling for domain adaptation | see API docs | see API docs |

For new-subject generalization use `LeaveGroupOutValidator` or `SplitterValidator` with a group splitter,
not `GroupedKFoldValidator`.

Shared options: `scoring` (default weighted F1 for classifiers, R² for regressors; pass the metric you will
report). Validators accept a fixed set of names (`"accuracy"`, `"f1_macro"`, `"f1_weighted"`, `"r2"`,
`"mae"`, ...; an unknown name raises and lists them) or any `(y_true, y_pred) -> float` function such as
`sklearn.metrics.balanced_accuracy_score`; `evaluate` additionally accepts every scikit-learn scorer name.
Other options: `stratify_coord`, `verbose`. Fitted fold pipelines are not cached by default
(`use_stateful_fit_cache=False`) so estimators without a `random_state` vary across seeds as they should.

## Leakage Rules: Stateless vs Stateful

The validator trusts each step's declaration. A step that computes statistics across trials but is declared
stateless runs before the split and leaks.

| Runs once (stateless) | Refit per fold (stateful) |
|---|---|
| `BandpassFilterTransform`, `CropTimeTransform`, `MultiTaperTransform`, `CARTransform` | `CSPTransform`, `GlobalFeaturePCA`, `ZCATransform` |
| `ZScoreTransform(per_dim="trial")` (each trial against itself) | `ZScoreTransform(..., use_fit=True)` |
| `FlattenTransform`, `AverageTransform`, `RenameDimsTransform` | `SKLearnTransformer`, `SKLearnPredictor`, `LGBMPredictor` |
| `@xdflow.step` without `fit` (independence is checked on every call) | `@xdflow.step(fit=...)` |

Composite steps (`Pipeline`, `SwitchTransform`, `GroupApplyTransform`) are stateful if any child is.
Everything after the first stateful step is refit per fold, even stateless steps.

Built-in transforms import from `xdflow.transforms`. Spectral transforms take an explicit `fs`; they warn when
it disagrees with `attrs["sfreq"]` or the time-coordinate spacing, so check units (seconds vs ms) of `time`.

## Validation Checklist Before Reporting a Score

1. The grouping unit matches the claim (new trials vs new subjects vs new sessions), and the printed split
   check shows nothing shared that should not be.
2. Every step that estimates anything across trials appears under "Refit in each fold".
3. `scoring` is the metric being reported; use `balanced_accuracy` or `f1_macro` with unbalanced classes and
   compare against the chance level for the class balance.
4. Per-group results (`result.by("subject")`) are inspected; a mean can hide subjects at chance.
5. Tuned scores are optimistic: report a holdout (`test_group_ids`, `test_size`) or an outer split that the
   search never saw.
6. Trial labels are unique and target values are not read inside any step.

## Common Pitfalls

- **Positional side arrays.** Do not keep `y` or `groups` as separate arrays once data is in a container;
  attach them as trial coordinates so filtering and reordering cannot misalign them.
- **Fitting before CV.** Do not call `fit_transform` on a learned step and then cross-validate the output;
  put the step in the pipeline.
- **Hand-written split loops.** Use a validator; custom split policies subclass `CrossValidator`
  (see [references/custom-steps.md](references/custom-steps.md)).
- **Reading the target in a step.** `data["label"]` is present during CV, and the independence check cannot
  detect that a step uses it.
- **Channel order.** Fitted steps align channels and features by label; a missing channel raises instead
  of silently mis-mapping. Keep channel names consistent across recordings.
- **Disk cache and user code.** Results from `@step` functions and lambdas are not reused from the disk cache
  unless `XDFLOW_CACHE_USER_CODE=1`; cache keys do not cover files or environment variables a step reads.

## References

- [references/pipelines-and-tuning.md](references/pipelines-and-tuning.md): composition (`SwitchTransform`,
  `OptionalTransform`, `TransformUnion`, `GroupApplyTransform`), wrapping existing scikit-learn models,
  probability metrics, `Tuner`, and `to_sklearn`
- [references/custom-steps.md](references/custom-steps.md): `@step` functions, `Transform` subclasses, and
  custom cross-validators, with their contracts and tests
- Upstream docs: [xdflow.readthedocs.io](https://xdflow.readthedocs.io/en/latest/), including the
  [EEG motor imagery](https://xdflow.readthedocs.io/en/latest/tutorials/eeg-motor-imagery/) and
  [activity recognition](https://xdflow.readthedocs.io/en/latest/tutorials/har-activity/) walkthroughs
