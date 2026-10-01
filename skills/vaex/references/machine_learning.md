# Machine learning and state transfer

Targets vaex-ml 0.19.0, core 4.19.0. See [official tutorial](https://vaex.io/docs/tutorial_ml.html)
and [released ML source](https://github.com/vaexio/vaex/tree/v4.19.0/packages/vaex-ml/vaex/ml).
Current package wheels are the runtime authority when the website or repository differs.

## Fit only on training observations

Split by the scientific sampling unit (participant, batch, site, or time) before any
imputation, scaling, feature selection, encoder fitting or resampling. Vaex's
`df.ml.train_test_split` slices an already shuffled frame; it does not guarantee a
random, stratified, grouped or temporal split. Model selection needs validation data
separate from the final test set. Target encoding on the same rows used to estimate
target means leaks labels; use out-of-fold training encodings and training-only
mappings for held-out rows. No Vaex target encoder here automatically cross-fits.

The following is a deterministic mechanics example, not an accuracy benchmark:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import vaex
import vaex.ml
from vaex.ml.sklearn import Predictor, IncrementalPredictor
from sklearn.linear_model import LinearRegression, SGDRegressor

x = np.linspace(-1, 1, 60)
df = vaex.from_arrays(x=x, x2=x**2, target=3*x-2,
                      category=np.array(['A', 'B', 'C'] * 20),
                      binary=(x > 0).astype(int))
train, test = df[:40], df[40:]  # illustrative chronological split
scaler = vaex.ml.StandardScaler(features=['x'], prefix='scaled_')
train_scaled = scaler.fit_transform(train)
test_scaled = scaler.transform(test)
assert np.isclose(train_scaled.scaled_x.mean(), 0, atol=1e-12)
assert np.isclose(scaler.mean_[0], train.x.mean())
assert not np.isclose(test_scaled.scaled_x.mean(), 0)
model = Predictor(model=LinearRegression(), features=['scaled_x'], target='target',
                  prediction_name='prediction')
model.fit(train_scaled)
scored = model.transform(test_scaled)
assert np.allclose(scored.prediction.to_numpy(), test.target.to_numpy())
```

`Predictor.fit()` materializes the full feature matrix and target; wrapping sklearn
in Vaex does not make its fit out of core. `transform()` attaches a lazy prediction
expression; evaluating all predictions still allocates their full result. For
incremental training, choose an estimator whose `partial_fit` genuinely supports the
problem and configure batches/epochs explicitly:

```python
incremental = IncrementalPredictor(
    model=SGDRegressor(random_state=7, learning_rate='constant', eta0=0.01),
    features=['scaled_x'], target='target', batch_size=8, num_epochs=2,
    prediction_name='online_prediction', shuffle=False,
)
incremental.fit(train_scaled)
assert np.isfinite(incremental.transform(test_scaled).online_prediction.to_numpy()).all()
```

A classifier usually needs `partial_fit_kwargs={'classes': ...}` with the fixed
class set. Vaex's `shuffle=True` shuffles within a batch, not necessarily across the
whole dataset. Batch training can differ from a single full fit; assess convergence,
ordering effects and held-out calibration rather than merely checking finite predictions.

## Transformers: current classes and behavior

Transformations generally return a shallow copy with virtual output columns. Fitting
still computes statistics/mappings, and these may allocate substantial state. Explicit
prefixes make feature references unambiguous; inspect actual output names.

```python
for transformer in [
    vaex.ml.MinMaxScaler(features=['x'], feature_range=(-1, 1)),
    vaex.ml.MaxAbsScaler(features=['x']),
    vaex.ml.RobustScaler(features=['x']),
    vaex.ml.LabelEncoder(features=['category']),
    vaex.ml.OneHotEncoder(features=['category']),
    vaex.ml.FrequencyEncoder(features=['category'], unseen='nan'),
    vaex.ml.KBinsDiscretizer(features=['x'], n_bins=3, strategy='uniform'),
]:
    transformed_train = transformer.fit_transform(train)
    transformed_test = transformer.transform(test)
    assert len(transformed_train) == len(train)
    assert len(transformed_test) == len(test)
    assert len(transformed_test.get_column_names()) > len(test.get_column_names())
# One scalar period per transformer, not a list of periods.
cycle = vaex.ml.CycleTransformer(features=['x'], n=24)
cyclic = cycle.fit_transform(train)
assert np.allclose(cyclic.x_x.to_numpy()**2 + cyclic.x_y.to_numpy()**2, 1)
pca = vaex.ml.PCA(features=['x', 'x2'], n_components=2)
pca.fit(train)
projected = pca.transform(test)
assert projected[['PCA_0', 'PCA_1']].values.shape == (20, 2)
assert np.isclose(sum(pca.explained_variance_ratio_), 1)
random_projection = vaex.ml.RandomProjections(features=['x', 'x2'], n_components=2)
assert len(random_projection.fit_transform(train)) == len(train)
```

- `RandomProjections` is plural; `KBinsDiscretizer` replaces the nonexistent `Discretizer` example.
- `MaxAbsScaler` uses the default `absmax_scaled_` prefix. One-hot outputs depend on
  fitted category values; do not infer a fixed naming/schema contract from a toy example.
- Labels encode categories as integers without establishing a scientific order.
  One-hot state can be very large for high cardinality; define unseen/missing policy.
- `BayesianTargetEncoder(features=[...], target=..., weight=..., unseen='nan')`
  is the current class. Unseen choices are `'nan'` or `'zero'`, not automatically
  the global mean. `WeightOfEvidenceEncoder` requires a meaningful binary target
  and training-only estimates. Neither repairs label leakage.
- Standard scaling divides by standard deviation, not variance. Check zero/near-zero
  dispersion, missingness and nonfinite results before model fitting.
- RobustScaler and quantile discretization use approximate percentile machinery;
  their boundaries need independent scientific checks. PCA covariance state is
  quadratic in feature count; scale comparable quantities when appropriate and
  retain loadings/explained variance. Component signs may flip without changing the subspace.

## K-means

```python
from vaex.ml.cluster import KMeans
clusterer = KMeans(features=['x', 'x2'], n_clusters=2, max_iter=10,
                   random_state=7, prediction_label='cluster')
clusterer.fit(train)
clusters = clusterer.transform(test)
assert len(clusterer.cluster_centers) == 2
assert set(clusters.cluster.tolist()) <= {0, 1}
```

The class lives in `vaex.ml.cluster`; fitted centers are `cluster_centers`, without
an underscore. Default prediction name is `prediction_kmeans`. It uses Numba kernels
and repeated passes. Empty clusters, scaling, seeds and convergence require checking;
finite labels in a toy test do not demonstrate useful clusters or biological subtypes.

## Boosting adapters

Current classes live in `vaex.ml.xgboost.XGBoostModel`,
`vaex.ml.lightgbm.LightGBMModel`, and `vaex.ml.catboost.CatBoostModel`.
`params` and `num_boost_round` belong in the constructor, not as duplicate keywords
to `.fit`. Tiny native fits were run with XGBoost 3.4.1, LightGBM 4.7.0 and CatBoost
1.2.10; these establish API execution only.

```python
from vaex.ml.xgboost import XGBoostModel
booster = XGBoostModel(
    features=['x'], target='target', prediction_name='boost_prediction',
    params={'objective': 'reg:squarederror', 'max_depth': 2, 'nthread': 2},
    num_boost_round=3,
)
booster.fit(train)
boosted = booster.transform(test)
assert np.isfinite(boosted.boost_prediction.to_numpy()).all()
```

XGBoost and LightGBM adapters construct full in-memory training matrices; their
Vaex wrappers do not imply external-memory learning. LightGBM fit accepts
`valid_sets`/`valid_names` and converts its callback options internally. CatBoost
accepts `evals` and optional `batch_size`; its batch mechanism trains/sums models,
which is not interchangeable with one full-data fit. Set prediction semantics
explicitly: CatBoost defaults to `prediction_type='Probability'`; labels and probabilities
are different outputs. For regression set `prediction_type='RawFormulaVal'`; the
default probability mode can produce two columns even for an RMSE-trained model. For sklearn use `prediction_type='predict_proba'` when needed,
and choose the desired class column using the fitted estimator's `classes_`.

## TensorFlow: source-verified only

There is no `vaex.ml.keras` module in 0.19.0. `vaex.ml.tensorflow.KerasModel` wraps a
**fitted** model for inference; its `.fit()` deliberately raises `NotImplementedError`.
Train with TensorFlow's own API or the optional `df.ml.tensorflow.to_keras_generator`
after checking that integration against the actual TensorFlow/Keras version. TensorFlow
was not installed or executed for this review. Do not promise a `target`/`epochs`
training interface on this wrapper or model serialization portability across Keras versions.

## Save attached predictions and preserve target rows

```python
# Fitting alone does not attach prediction expressions to the frame being saved.
train_with_prediction = model.transform(train_scaled)
with TemporaryDirectory() as directory:
    state = Path(directory) / 'pipeline.json'
    train_with_prediction.state_write(str(state))
    fresh = df[40:].copy()
    fresh.state_load(str(state), set_filter=False, trusted=True)
    assert len(fresh) == len(test)
    assert fresh.x.tolist() == test.x.tolist()
    assert np.allclose(fresh.prediction.to_numpy(), scored.prediction.to_numpy())
```

Only load trusted state: models/functions can use pickle-like executable serialization.
State restores transformations, not raw data or experimental provenance. Confirm names,
types, units, row membership, class order and package versions on load; a training
filter must not silently become an inference filter. Evaluate with design-appropriate
held-out metrics and uncertainty; fold standard deviation is not a confidence interval.
Resampling/weights and feature selection belong inside training folds, never on the test
population. Exact row alignment must be preserved between targets and predictions.
