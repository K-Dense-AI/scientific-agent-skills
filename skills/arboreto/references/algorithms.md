# GRN inference algorithms

Use the pinned runtime and pre-import Dask configuration in `SKILL.md`. Calls
below assume prepared inputs and a managed `client`; wrap process creation and
inference in a main guard. Signatures were checked against PyPI 0.1.6 and current
[upstream algorithm source](https://github.com/aertslab/arboreto/blob/master/arboreto/algo.py).

## Choose the estimator

| Property | GRNBoost2 | GENIE3 |
| --- | --- | --- |
| Regressor | Stochastic gradient boosting | Random forest |
| Typical purpose | Efficient initial analysis of large matrices | Method comparison or published GENIE3 reproduction |
| Default maximum trees | 5000, often stopped earlier | 1000 |
| Early stopping | Out-of-bag improvement window | None |
| Score scale | Feature importance multiplied by fitted tree count | Normalized tree feature importance |

Both fit a regression for each target, exclude that target from its predictors,
and emit positive-importance TF-target pairs. GRNBoost2 is not restricted to
one-level decision stumps: its default kwargs leave scikit-learn's tree depth
default in effect. GENIE3 uses one random forest per target, not an ensemble of
random forests. Timing depends on observations, targets, candidate TFs, tree
settings, and workers; there is no fixed 10,000-observation applicability cutoff.

Agreement between algorithms measures sensitivity to estimator choice. It does
not independently validate regulatory causality. Scores across algorithms should
not be compared with one shared numerical threshold.

## Public signatures

```python
grnboost2(expression_data, gene_names=None, tf_names="all",
          client_or_address="local", early_stop_window_length=25,
          limit=None, seed=None, verbose=False)

genie3(expression_data, gene_names=None, tf_names="all",
       client_or_address="local", limit=None, seed=None, verbose=False)
```

- `gene_names`: required for ndarray/CSC input; ignored in favor of DataFrame columns.
- `tf_names`: list of predictor names, or `None`/`"all"` for all genes.
- `client_or_address`: existing `distributed.Client`, scheduler address, or
  `None`/`"local"` to create a local cluster. Existing clients remain caller-owned.
- `limit`: top N links globally. Choose a positive integer or `None`.
- `seed`: regressor seed; record it and all dependency versions.
- `early_stop_window_length`: positive window size for mean out-of-bag improvement;
  this is not a held-out experimental validation set.

```python
from arboreto.algo import grnboost2, genie3

network = grnboost2(expression_data=expression_matrix, tf_names=tf_names,
                    seed=42, limit=5000, client_or_address=client)
# Prefer a fresh managed client for each run if repeated runs cancel futures.
comparison = genie3(expression_data=expression_matrix, tf_names=tf_names,
                     seed=42, client_or_address=other_client)
```

## Explicit estimator settings

`grnboost2` and `genie3` do not accept arbitrary scikit-learn kwargs. Use `diy`
with `regressor_type="GBM"`, `"RF"`, or `"ET"` and a parameter dictionary:

```python
from arboreto.algo import diy
from arboreto.core import SGBM_KWARGS, RF_KWARGS

custom_gbm = diy(
    expression_data=expression_matrix,
    regressor_type="GBM",
    regressor_kwargs={**SGBM_KWARGS, "n_estimators": 100,
                      "max_depth": 5, "learning_rate": 0.1},
    tf_names=tf_names, seed=42, client_or_address=client,
)
custom_rf = diy(
    expression_data=expression_matrix,
    regressor_type="RF",
    regressor_kwargs={**RF_KWARGS, "n_estimators": 1000, "max_features": "sqrt"},
    tf_names=tf_names, seed=42, client_or_address=other_client,
)
```

Both custom profiles ran on the synthetic fixture. ExtraTrees is source-verified
but was not separately executed. Copy default dictionaries before overriding;
do not mutate module globals. An XGBoost helper exists in core source, but
XGBoost is not an implemented supported estimator here.

Arboreto uses scikit-learn's `GradientBoostingRegressor.fit(..., monitor=...)`
and `oob_improvement_`; the current official API still documents these, but the
executed compatibility matrix here is scikit-learn 1.5.2, not all newer releases.
See [current estimator API](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingRegressor.html)
and [Arboreto core](https://github.com/aertslab/arboreto/blob/master/arboreto/core.py).
