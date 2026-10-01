# Data handling and leakage-safe preprocessing

Verified for scikit-survival 0.28.0 on 2026-10-01.

## Standard right-censored outcome

scikit-survival estimators expect a one-dimensional NumPy structured array with
exactly two fields:

1. a boolean event indicator (`True`=event observed, `False`=right-censored);
2. a floating-point observed time (event or censoring time).

Field names are configurable, but field order and meaning are fixed.

```python
from sksurv.util import Surv

y = Surv.from_arrays(
    event=[True, False, True],
    time=[2.5, 4.0, 7.25],
    name_event="event",
    name_time="time",
)
assert y.dtype.names == ("event", "time")
```

`Surv.from_arrays()` accepts boolean or strict 0/1 event values.
`Surv.from_dataframe(event, time, data)` accepts pandas and, in 0.28, Polars
DataFrames:

```python
y = Surv.from_dataframe("event", "time", frame)
```

Do not use `astype(bool)` on unvalidated strings: `"False"` is a non-empty string
and therefore converts to `True`. Validate accepted values explicitly.

## Competing-risk outcome is different

`Surv` is not the input contract for nonparametric competing-risk cumulative
incidence. Use two arrays:

```python
# 0 = right-censored; 1..K = mutually exclusive causes
event_code = frame["status"].to_numpy(dtype=int)
observed_time = frame["time"].to_numpy(dtype=float)
```

Validate integer cause codes before the integer cast: `.to_numpy(dtype=int)` can
silently truncate fractional labels. Positive cause codes must be understood before modeling. Do not collapse them to
boolean until the estimand explicitly requires all-cause event status or a
cause-specific hazard outcome. See `competing-risks.md`.

## Minimum validation

Before splitting:

- event and time lengths match feature rows;
- standard event values are boolean/0/1;
- competing-risk codes are non-negative integers and 0 means censoring;
- time is numeric, finite, and strictly positive;
- outcomes are not included among predictors;
- feature names are unique and schema roles are explicit;
- repeated entities, temporal ordering, or sites are identified for the split;
- every planned training/CV fold contains events and enough comparable pairs;
  event-stratified CV in the bundled trainer also requires censored rows;
- missingness is described, but imputation is not yet fitted.

The bundled validator checks outcome coding, positive finite times, feature exclusion,
and the local CSV schema. Group independence, fold support, temporal ordering and
missingness interpretation require the study-specific review above. Strictly positive
times are a helper policy; some native nonparametric APIs permit zero.

Validate bounded local CSV input:

```bash
python skills/scikit-survival/scripts/validate_survival_csv.py \
  --input data.csv \
  --event-column event \
  --time-column time \
  --feature-columns x1,x2,group \
  --structured-output outcome.npy
```

The `.npy` file contains a non-object structured array and can be loaded with
`numpy.load(path, allow_pickle=False)`.

## Split before learned preprocessing

This order is mandatory:

1. validate types and outcome coding;
2. split rows;
3. fit imputation, encoding, scaling, and feature selection on training rows;
4. transform validation/test rows with training-fitted state;
5. fit the survival estimator;
6. evaluate once on the held-out rows.

Computing medians, category levels, scaling moments, univariate scores, or
regularization paths on all rows leaks validation/test information.

```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    stratify=y["event"],
    random_state=20260723,
)
```

Event stratification does not guarantee balanced follow-up times. Inspect each
split. Use group-aware splitting for repeated entities and time-respecting
splitting for future-deployment questions. A random split is not automatically
appropriate.

## Explicit heterogeneous pipeline

Use scikit-learn's `ColumnTransformer` when numeric and categorical columns need
different imputers or when unseen categories must be handled explicitly.

```python
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sksurv.linear_model import CoxPHSurvivalAnalysis

numeric_pipe = make_pipeline(
    SimpleImputer(strategy="median"),
    StandardScaler(),
)
categorical_pipe = make_pipeline(
    SimpleImputer(strategy="most_frequent"),
    OneHotEncoder(
        handle_unknown="ignore",
        drop="first",
        sparse_output=False,
    ),
)
preprocess = ColumnTransformer(
    [
        ("numeric", numeric_pipe, numeric_columns),
        ("categorical", categorical_pipe, categorical_columns),
    ],
    sparse_threshold=0.0,
)
pipeline = make_pipeline(
    preprocess,
    CoxPHSurvivalAnalysis(alpha=0.1, ties="efron"),
)
pipeline.fit(X_train, y_train)
```

Keep the estimator in the same pipeline used by cross-validation so each fold
fits its own preprocessing state.

### scikit-survival encoder

`sksurv.preprocessing.OneHotEncoder(allow_drop=True)`:

- treats pandas `category`/`object` and Polars categorical/enum/string columns as
  categorical;
- leaves non-categorical column order in place;
- drops one category per categorical feature;
- returns the same DataFrame library as its input;
- requires `fit` and `transform` to use the same DataFrame library;
- supports `get_feature_names_out()` and pipeline use.

It is convenient for already clean DataFrames:

```python
from sklearn.pipeline import make_pipeline
from sksurv.preprocessing import OneHotEncoder

pipeline = make_pipeline(
    OneHotEncoder(),
    CoxPHSurvivalAnalysis(alpha=0.1),
)
pipeline.fit(X_train, y_train)
```

For custom files, an explicit `ColumnTransformer` usually makes missing-value,
unknown-category, and scaling behavior easier to audit.

`encode_categorical()` is a one-shot transformation, not a fitted train/test
transformer. Do not call it separately on all data or independently on train and
test when category sets can differ.

## Scaling and missing values

- Scale Coxnet, survival SVM, IPC ridge, and other coefficient/penalty models.
- Tree ensembles generally do not require scaling.
- Impute inside the pipeline unless the selected estimator explicitly supports the
  observed missing-value pattern.
- SurvivalTree, RandomSurvivalForest, and ExtraSurvivalTrees support missing-value
  splitting in current releases, but preprocessing may still be needed for
  categorical data and operational consistency.
- Never impute event indicators or event/censoring times as ordinary features.

Missingness can be informative. A convenient imputer does not justify a
missing-at-random assumption or transportability claim.

## Feature selection

Feature selection is learned preprocessing and belongs inside inner CV:

```python
pipeline = make_pipeline(
    preprocess,
    selector,
    estimator,
)
```

Do not use a standard classification `SelectKBest` score with structured survival
outcomes unless the score function explicitly supports censoring. Coxnet or
componentwise boosting can perform embedded selection, but regularization strength
still requires fold-contained tuning.

Fixed "events per variable" thresholds are not universal guarantees. Consider
effective degrees of freedom, censoring, shrinkage, separation, stability, and
external validation instead of declaring a model valid from one ratio.

## Built-in datasets

Current loaders:

- `load_aids(endpoint=...)`
- `load_bmt()`
- `load_cgvhd()`
- `load_breast_cancer()`
- `load_flchain()`
- `load_gbsg2()`
- `load_whas500()`
- `load_veterans_lung_cancer()`
- `load_arff_files_standardized(...)`

`load_bmt()` returns event codes 0, 1, 2 and `load_cgvhd()` returns 0, 1, 2, 3;
these are competing-risk outcomes. The remaining listed study loaders return the
standard boolean right-censored outcome (subject to endpoint options).

These packaged datasets are useful for reproducing documentation, but they are
real study datasets. The bundled CLIs and tests do not use them; they use synthetic
data only. Do not treat examples as clinical advice or a substitute for data-use
review.

`load_arff_files_standardized(..., path_testing=...)` concatenates train/test
features to standardize and harmonize categories. Do not use its default transforms
for independent validation. Read raw ARFF tables with `sksurv.io.loadarff`, extract
outcomes explicitly, and fit preprocessing only on training folds.

In 0.28, dataset loaders accept an `output_type` option where documented, allowing
pandas (default) or Polars feature output.

## Unsupported or specialized structures

Standard estimators do not directly encode:

- interval-censored outcomes;
- ordinary left-censoring;
- time-varying covariates in counting-process form;
- recurrent-event dependence;
- multi-state transitions;
- delayed entry in the two-field `Surv` estimator outcome.

Some nonparametric APIs expose entry-time arguments, but that does not make every
estimator support left truncation. Choose a method whose likelihood and input
contract match the observation process.

## Local-data safeguards

- Use only authorized, appropriately de-identified local data.
- Do not put row-level data in logs or model reports.
- Do not load untrusted pickle/joblib model files.
- Keep feature and row bounds proportionate to available resources.
- Use descriptive script names; never create files named after packages such as
  `sklearn.py` or `sksurv.py`.

## Sources

Official sources checked 2026-10-01:

- [Surv API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.util.Surv.html)
- [OneHotEncoder API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.preprocessing.OneHotEncoder.html)
- [Dataset API](https://scikit-survival.readthedocs.io/en/stable/api/datasets.html)
- [0.28 release notes](https://scikit-survival.readthedocs.io/en/stable/release_notes/v0.28.html)
- [Introduction user guide](https://scikit-survival.readthedocs.io/en/stable/user_guide/00-introduction.html)
