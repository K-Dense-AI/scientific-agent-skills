# cuML Reference

> Review: 2026-10-01. Code below is illustrative unless explicitly described as CPU-tested.
> GPU execution, performance, GDS, and multi-GPU behavior require validation on target hardware.

cuML is NVIDIA's GPU-accelerated machine learning library within the RAPIDS ecosystem. It
provides scikit-learn-compatible APIs for classification, regression, clustering, dimensionality
reduction, preprocessing, and model selection. Performance depends on algorithm, shape, dtype,
fallback behavior, and transfer cost; benchmark the complete pipeline on representative data.

> **Full documentation:** https://docs.nvidia.com/cuml/26.08/

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Two Usage Modes](#two-usage-modes)
3. [cuml.accel Accelerator Mode](#cumlaccel-accelerator-mode)
4. [Direct cuML API](#direct-cuml-api)
5. [Algorithm Catalog](#algorithm-catalog)
6. [Input/Output Type Handling](#inputoutput-type-handling)
7. [Preprocessing](#preprocessing)
8. [Feature Extraction](#feature-extraction)
9. [Model Selection and Tuning](#model-selection-and-tuning)
10. [Forest Inference Library (FIL)](#forest-inference-library)
11. [Multi-GPU with Dask](#multi-gpu-with-dask)
12. [Model Serialization](#model-serialization)
13. [Memory Management](#memory-management)
14. [Performance Optimization](#performance-optimization)
15. [Interoperability](#interoperability)
16. [Key Differences from sklearn](#key-differences-from-sklearn)
17. [Common Migration Patterns](#common-migration-patterns)

---

## Installation and Setup

Use `uv add` in standalone examples; follow the user's existing project package manager when one
is already configured.

```bash
uv add "cuml-cu12==26.8.*"    # For CUDA 12.x
uv add "cuml-cu13==26.8.*"    # For CUDA 13.x
```

cuML wheels are published directly to PyPI (since RAPIDS 25.10) — the `--extra-index-url=https://pypi.nvidia.com` extra index is no longer required.

**Platform:** Linux and WSL2 only (no native macOS or Windows).
**Requires:** Python >= 3.11, scikit-learn >= 1.6, NVIDIA GPU with CUDA 12.x or 13.x support.

Verify:
```python
import cuml
print(cuml.__version__)

from cuml.datasets import make_blobs
X, y = make_blobs(n_samples=1000, n_features=10)
print(f"Generated {X.shape[0]} samples on GPU")
```

---

## Two Usage Modes

### 1. cuml.accel (Zero-Code-Change)
Transparently intercepts sklearn, umap-learn, and hdbscan calls and routes them to GPU. Falls back to CPU for unsupported operations. Best for: quick acceleration of existing sklearn code, mixed codebases, prototyping.

### 2. Direct cuML API
Replace `from sklearn` with `from cuml`. Maximum performance, explicit control over GPU execution. Best for: production pipelines, maximum performance, new GPU-first code.

---

## cuml.accel Accelerator Mode

The fastest path from sklearn to GPU — no code changes required. Similar to `cudf.pandas` for pandas.

### Activation

```python
# Jupyter/IPython (MUST be the first cell, before any sklearn import)
%load_ext cuml.accel

import sklearn  # Now GPU-accelerated
from sklearn.cluster import KMeans  # Runs on GPU transparently
```

```bash
# Command line
python -m cuml.accel script.py
python -m cuml.accel -v script.py     # With info logging
python -m cuml.accel -vv script.py    # With debug logging
```

```python
# Programmatic (call BEFORE importing sklearn)
import cuml
cuml.accel.install()

from sklearn.cluster import KMeans  # Now GPU-accelerated
```

```bash
# Environment variable
CUML_ACCEL_ENABLED=1 python script.py
```

### How It Works

- Intercepts sklearn/umap-learn/hdbscan imports and replaces estimators with GPU versions.
- If an operation isn't supported on GPU, it silently falls back to CPU sklearn.
- Uses managed memory by default — host RAM augments GPU VRAM.
- Models pickled under cuml.accel load as standard sklearn objects in non-GPU environments.
- Accelerates 30+ algorithms across sklearn, umap-learn, and hdbscan. Recent releases (26.04-26.06) expanded coverage to preprocessing estimators (StandardScaler, MinMaxScaler, MaxAbsScaler, PolynomialFeatures, LabelEncoder) and SpectralClustering.
- 26.08 requires scikit-learn >=1.6; specific accelerated preprocessors require >=1.8. Check the [26.08 compatibility page](https://docs.nvidia.com/cuml/26.08/cuml-accel/compatibility/) for method and parameter restrictions.

### Known Fallback Triggers (Runs on CPU Instead)

- Sparse input data (most algorithms)
- Callable parameters (e.g., callable `init` for KMeans)
- Certain parameter values: `n_components="mle"` for PCA, `positive=True` for linear models, warm starts
- Unsupported distance metrics for neighbors algorithms
- Multi-output targets for Random Forest
- String/object dtypes — must pre-encode with LabelEncoder first

### Numerical Precision

GPU estimators can use different algorithms, solvers, tree-split approximations, defaults, and random streams. Differences can exceed roundoff. Compare held-out quality, prediction agreement, class/feature order and calibration; use sign/subspace-aware checks for decompositions. A matching seed does not imply matching models.

---

## Direct cuML API

The API follows fit/predict/transform conventions, but signatures, defaults and supported inputs differ. Consult the chosen estimator before replacing imports.

```python
from cuml.cluster import DBSCAN
from cuml.datasets import make_blobs

# Create data directly on GPU
X, y = make_blobs(n_samples=100_000, centers=5, n_features=10, random_state=42)

# Fit — runs on GPU
model = DBSCAN(eps=1.0, min_samples=5)
model.fit(X)
print(model.labels_)
```

```python
from cuml import LinearRegression
from cuml.datasets import make_regression
from cuml.model_selection import train_test_split

X, y = make_regression(n_samples=100_000, n_features=50, noise=0.1)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = LinearRegression()
model.fit(X_train, y_train)
predictions = model.predict(X_test)
score = model.score(X_test, y_test)
print(f"R2 score: {score:.4f}")
```

---

## Algorithm Catalog

### Clustering

| cuML | sklearn Equivalent | Multi-GPU |
|------|-------------------|-----------|
| `cuml.KMeans` | `sklearn.cluster.KMeans` | Yes |
| `cuml.DBSCAN` | `sklearn.cluster.DBSCAN` | Yes |
| `cuml.AgglomerativeClustering` | `sklearn.cluster.AgglomerativeClustering` | No |
| `cuml.cluster.hdbscan.HDBSCAN` | `hdbscan.HDBSCAN` | No |
| `cuml.cluster.SpectralClustering` | `sklearn.cluster.SpectralClustering` | No |

### Regression

| cuML | sklearn Equivalent | Multi-GPU |
|------|-------------------|-----------|
| `cuml.LinearRegression` | `sklearn.linear_model.LinearRegression` | Yes |
| `cuml.Ridge` | `sklearn.linear_model.Ridge` | Yes |
| `cuml.Lasso` | `sklearn.linear_model.Lasso` | Yes |
| `cuml.ElasticNet` | `sklearn.linear_model.ElasticNet` | Yes |
| `cuml.SVR` | `sklearn.svm.SVR` | No |
| `cuml.KernelRidge` | `sklearn.kernel_ridge.KernelRidge` | No |
| `cuml.ensemble.RandomForestRegressor` | `sklearn.ensemble.RandomForestRegressor` | Yes |
| `cuml.MBSGDRegressor` | `sklearn.linear_model.SGDRegressor` | No |

### Classification

| cuML | sklearn Equivalent | Multi-GPU |
|------|-------------------|-----------|
| `cuml.LogisticRegression` | `sklearn.linear_model.LogisticRegression` | No |
| `cuml.ensemble.RandomForestClassifier` | `sklearn.ensemble.RandomForestClassifier` | Yes |
| `cuml.svm.SVC` | `sklearn.svm.SVC` | No |
| `cuml.svm.LinearSVC` | `sklearn.svm.LinearSVC` | No |
| `cuml.naive_bayes.GaussianNB` | `sklearn.naive_bayes.GaussianNB` | No |
| `cuml.naive_bayes.MultinomialNB` | `sklearn.naive_bayes.MultinomialNB` | Yes |
| `cuml.naive_bayes.BernoulliNB` | `sklearn.naive_bayes.BernoulliNB` | No |
| `cuml.naive_bayes.CategoricalNB` | `sklearn.naive_bayes.CategoricalNB` | No |
| `cuml.naive_bayes.ComplementNB` | `sklearn.naive_bayes.ComplementNB` | No |
| `cuml.neighbors.KNeighborsClassifier` | `sklearn.neighbors.KNeighborsClassifier` | Yes |
| `cuml.neighbors.KNeighborsRegressor` | `sklearn.neighbors.KNeighborsRegressor` | Yes |
| `cuml.MBSGDClassifier` | `sklearn.linear_model.SGDClassifier` | No |
| `cuml.multiclass.OneVsOneClassifier` | `sklearn.multiclass.OneVsOneClassifier` | No |
| `cuml.multiclass.OneVsRestClassifier` | `sklearn.multiclass.OneVsRestClassifier` | No |

### Dimensionality Reduction and Manifold Learning

| cuML | sklearn/Library Equivalent | Multi-GPU |
|------|---------------------------|-----------|
| `cuml.PCA` | `sklearn.decomposition.PCA` | Yes |
| `cuml.IncrementalPCA` | `sklearn.decomposition.IncrementalPCA` | No |
| `cuml.TruncatedSVD` | `sklearn.decomposition.TruncatedSVD` | Yes |
| `cuml.UMAP` | `umap.UMAP` | Yes (inference) |
| `cuml.TSNE` | `sklearn.manifold.TSNE` | No |
| `cuml.random_projection.GaussianRandomProjection` | `sklearn.random_projection.GaussianRandomProjection` | No |
| `cuml.random_projection.SparseRandomProjection` | `sklearn.random_projection.SparseRandomProjection` | No |

### Nearest Neighbors

| cuML | sklearn Equivalent | Multi-GPU |
|------|-------------------|-----------|
| `cuml.neighbors.NearestNeighbors` | `sklearn.neighbors.NearestNeighbors` | Yes |
| `cuml.neighbors.KNeighborsClassifier` | `sklearn.neighbors.KNeighborsClassifier` | Yes |
| `cuml.neighbors.KNeighborsRegressor` | `sklearn.neighbors.KNeighborsRegressor` | Yes |
| `cuml.neighbors.KernelDensity` | `sklearn.neighbors.KernelDensity` | No |

### Time Series

| cuML | Description |
|------|-------------|
| `cuml.ExponentialSmoothing` | Holt-Winters exponential smoothing |
| `cuml.tsa.ARIMA` | ARIMA/SARIMA models (batched — fits multiple series simultaneously) |
| `cuml.tsa.auto_arima.AutoARIMA` | Automatic ARIMA order selection |

### Metrics (GPU-Accelerated)

**Regression:** `r2_score`, `mean_squared_error`, `mean_absolute_error`, `mean_squared_log_error`, `median_absolute_error`

**Classification:** `accuracy_score`, `log_loss`, `roc_auc_score`, `precision_recall_curve`, `confusion_matrix`

**Clustering:** `adjusted_rand_score`, `silhouette_score`, `silhouette_samples`, `homogeneity_score`, `completeness_score`, `v_measure_score`, `mutual_info_score`

**Other:** `trustworthiness`, `pairwise_distances`, `pairwise_kernels`

### Model Explainability

| cuML | Description |
|------|-------------|
| `cuml.explainer.KernelExplainer` | SHAP Kernel Explainer |
| `cuml.explainer.PermutationExplainer` | SHAP Permutation Explainer |
| `cuml.explainer.TreeExplainer` | SHAP Tree Explainer |

---

## Input/Output Type Handling

### Supported Input Types

cuML accepts: NumPy arrays, CuPy arrays, cuDF DataFrames/Series, pandas DataFrames/Series, Numba device arrays, PyTorch tensors (via `__cuda_array_interface__`).

NumPy and pandas inputs are automatically transferred to GPU. For best performance, pass CuPy arrays or cuDF DataFrames to avoid transfers.

### Controlling Output Type

```python
import cuml

# Global setting
cuml.set_global_output_type('cupy')  # Options: 'input', 'cupy', 'numpy', 'cudf', 'pandas'

# Context manager
with cuml.using_output_type('cudf'):
    result = model.predict(X)  # Returns cudf Series

# Per-estimator
model = cuml.KMeans(output_type='cupy')
```

**Performance ranking** (fastest to slowest output type):
1. `cupy` — no host transfers, most efficient
2. `cudf` — slight overhead for some shapes
3. `numpy` / `pandas` — device-to-host transfer cost

**Best practice:** Use `cupy` or `cudf` for intermediate results. Only convert to `numpy`/`pandas` at the end for visualization or export.

---

## Preprocessing

cuML provides GPU-accelerated versions of all common sklearn preprocessors.

### Scalers and Transformers

```python
from cuml.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from cuml.preprocessing import Normalizer, PowerTransformer, QuantileTransformer
from cuml.preprocessing import Binarizer, PolynomialFeatures, KBinsDiscretizer

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
```

### Encoders

```python
from cuml.preprocessing import LabelEncoder, OneHotEncoder, LabelBinarizer, TargetEncoder

le = LabelEncoder()
y_encoded = le.fit_transform(y)

ohe = OneHotEncoder(sparse_output=False)
X_encoded = ohe.fit_transform(X_categorical)
```

### Imputers

```python
from cuml.preprocessing import SimpleImputer, MissingIndicator

imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)
```

### Pipeline and Composition

```python
from cuml.compose import ColumnTransformer, make_column_transformer
from cuml.preprocessing import StandardScaler, OneHotEncoder

preprocessor = make_column_transformer(
    (StandardScaler(), ['age', 'income']),
    (OneHotEncoder(), ['category', 'region']),
)
X_processed = preprocessor.fit_transform(df)
```

### Preprocessing Functions

`scale()`, `minmax_scale()`, `maxabs_scale()`, `robust_scale()`, `normalize()`, `binarize()`, `add_dummy_feature()`, `label_binarize()`

---

## Feature Extraction

```python
from cuml.feature_extraction.text import TfidfVectorizer, CountVectorizer, HashingVectorizer

tfidf = TfidfVectorizer(max_features=10000)
X_tfidf = tfidf.fit_transform(corpus)
```

---

## Model Selection and Tuning

### Train/Test Split

```python
from cuml.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
```

### Cross-Validation

```python
from cuml.model_selection import KFold

kf = KFold(n_splits=5, shuffle=True, random_state=42)
for train_idx, test_idx in kf.split(X):
    X_train, X_test = X[train_idx], X[test_idx]
    # ...
```

### Hyperparameter Tuning

For an existing sklearn workflow, use `cuml.accel` with sklearn search first and inspect fallback. Bound concurrency per GPU to avoid memory oversubscription. Dask-ML is an optional distributed design, not a guarantee of fewer transfers.

```python
import cuml
cuml.accel.install()  # Before sklearn imports, in a fresh process
from sklearn.model_selection import RandomizedSearchCV
from sklearn.ensemble import RandomForestClassifier

param_distributions = {
    'max_depth': [8, 12, 16, 20],
    'n_estimators': [100, 200, 500],
    'max_features': [0.5, 0.75, 1.0],
}

search = RandomizedSearchCV(
    RandomForestClassifier(),
    param_distributions,
    n_iter=25,
    cv=5,
    random_state=42,
    n_jobs=1,  # One GPU: start with bounded concurrency
)
search.fit(X_train, y_train)
print(f"Best score: {search.best_score_:.4f}")
print(f"Best params: {search.best_params_}")
```

### Dataset Generators

```python
from cuml.datasets import make_blobs, make_classification, make_regression

X, y = make_blobs(n_samples=100_000, centers=5, n_features=20, random_state=42)
X, y = make_classification(n_samples=100_000, n_features=50, n_informative=25)
X, y = make_regression(n_samples=100_000, n_features=50, noise=0.1)
```

---

## Forest Inference Library

`cuml.fil.ForestInference` remains a deprecated compatibility API in 26.08. New forest
inference work should evaluate [nvForest](https://docs.nvidia.com/nvforest/latest/)
and its [migration guide](https://docs.nvidia.com/nvforest/latest/fil_migration/).
Do not infer its removal from a moving cuML `latest` page while using 26.08.

FIL provides GPU inference for supported tree-based models trained in other frameworks. Its value
depends on model structure and inference batch size, so compare warm and end-to-end latency with
the deployment baseline.

```python
from cuml.fil import ForestInference

# Load an XGBoost model file; use load_from_sklearn for a fitted sklearn estimator
fil_model = ForestInference.load("xgboost_model.ubj", is_classifier=True)

# Optional: optimize for specific batch size
fil_model.optimize()

# Predict on GPU
predictions = fil_model.predict(X_test)
probas = fil_model.predict_proba(X_test)
```

**Supports:** XGBoost, LightGBM, sklearn Random Forests, any Treelite-compatible model.

This is especially valuable when you have a model already trained on CPU and want to speed up inference without retraining.

---

## Multi-GPU with Dask

For datasets too large for a single GPU or when you want to use multiple GPUs.

```python
from dask.distributed import Client
from dask_cuda import LocalCUDACluster

# One Dask worker per GPU
cluster = LocalCUDACluster(
    rmm_pool_size="12GB",
    enable_cudf_spill=True,
)
client = Client(cluster)

# Create distributed data
from cuml.dask.datasets import make_blobs
X, y = make_blobs(
    n_samples=1_000_000,
    n_features=20,
    centers=5,
    n_parts=len(client.scheduler_info()['workers']) * 2,  # 2 partitions per worker
)

# Use Dask estimator
from cuml.dask.cluster import KMeans
kmeans = KMeans(n_clusters=5)
kmeans.fit(X)
labels = kmeans.predict(X)

# Convert to single-GPU model for serialization
single_model = kmeans.get_combined_model()

client.close()
cluster.close()
```

### Available Multi-GPU Estimators (`cuml.dask`)

- **Clustering:** KMeans, DBSCAN
- **Linear models:** LinearRegression, Ridge, Lasso, ElasticNet
- **Ensemble:** RandomForestClassifier, RandomForestRegressor
- **Decomposition:** PCA, TruncatedSVD
- **Manifold:** UMAP (inference only)
- **Neighbors:** NearestNeighbors, KNeighborsClassifier, KNeighborsRegressor
- **Naive Bayes:** MultinomialNB
- **Preprocessing:** LabelEncoder, LabelBinarizer, OneHotEncoder

---

## Model Serialization

```python
import pickle

# Save cuML model
with open("model.pkl", "wb") as f:
    pickle.dump(model, f, protocol=5)

# Load cuML model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)
```

- Models trained under cuml.accel can be pickled and loaded as standard sklearn objects in non-GPU environments.
- Dask distributed models must be converted first: `single_model = dask_model.get_combined_model()`.
- joblib also works for serialization.

---

## Memory Management

### RMM (RAPIDS Memory Manager)

```python
import rmm

# Pre-allocate a memory pool for faster allocation
rmm.reinitialize(pool_allocator=True, initial_pool_size=2**32)  # 4 GB pool
```

### Aligning with cuDF and CuPy

When using cuML alongside cuDF and CuPy, align all libraries on the same RMM allocator:

```python
import rmm
from rmm.allocators.cupy import rmm_cupy_allocator
import cupy
cupy.cuda.set_allocator(rmm_cupy_allocator)
```

### cuml.accel Memory

cuml.accel uses managed memory by default (host RAM augments GPU VRAM). Disable with `--disable-uvm` flag if experiencing slowdowns. Managed memory does NOT work on WSL2 or when RMM is externally configured.

### Best Practices

- float32 halves array storage relative to float64; throughput gains depend on hardware and algorithm.
- Keep data on GPU throughout the pipeline — avoid NumPy/pandas round-trips.
- For datasets larger than GPU memory: use Dask multi-GPU or chunk processing.
- Pre-allocate RMM pools to avoid fragmentation.

---

## Performance Optimization

### Benchmarking

1. Verify whether `cuml.accel` used a GPU implementation or fell back to scikit-learn.
2. Compare the same estimator parameters, train/test split, random seed, and output semantics.
3. Warm the CUDA context and any lazy compilation before timed repetitions.
4. Report fit, transform/predict, and end-to-end times separately, including conversion and
   transfer costs paid by the application.
5. Record rows, features, sparsity, dtype, estimator parameters, CPU/GPU models, and software
   versions.
6. For stochastic or approximate algorithms, compare quality metrics as well as time.

### Key Optimization Tips

1. **Use float32 when the model's accuracy and stability permit it.** Validate metrics after
changing precision; architecture-specific throughput ratios are not a correctness argument.

2. **Keep data on GPU.** Pass CuPy arrays or cuDF DataFrames. Every NumPy/pandas conversion triggers a device-host transfer.

3. **Use enough work to amortize setup and transfer.** Do not rely on a fixed row threshold;
features, sparsity, estimator, batch size, and reuse all matter.

4. **Benchmark the actual feature shape.** Width affects compute, memory traffic, and temporary
storage differently for each estimator.

5. **First call has JIT overhead.** Benchmark on subsequent calls, not the first.

6. **Use RMM pools when allocation overhead or fragmentation is visible in profiling.** Pools
amortize allocator costs but reserve device memory and should be sized deliberately.

7. **Bound search concurrency per GPU** and measure transfer/fallback behavior. The search scheduler alone does not ensure device residency.

8. **Evaluate FIL for supported tree-model inference.** Benchmark the target model and production
batch sizes against the existing serving path.

---

## Interoperability

- **cuDF:** Accepted by many estimators; assembling dense matrices or changing dtype can copy.
- **CuPy:** Zero-copy via `__cuda_array_interface__`. Most efficient intermediate format.
- **NumPy/pandas:** Accepted as input (auto-transferred to GPU). Output type configurable.
- **PyTorch:** Tensors accepted via array interface.
- **sklearn:** Similar estimator interfaces. Interconversion is estimator-specific; use cuml.accel for supported transparent acceleration.
- **XGBoost/LightGBM:** FIL provides GPU inference for externally-trained tree models.
- **Dask:** Native distributed support via `cuml.dask` module.

### End-to-End RAPIDS Pipeline

```python
import cudf
import cuml
from cuml.preprocessing import StandardScaler
from cuml.ensemble import RandomForestClassifier
from cuml.model_selection import train_test_split

# Load data on GPU
df = cudf.read_parquet("data.parquet")
X = df.drop("target", axis=1)
y = df["target"]

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Preprocess
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Train
model = RandomForestClassifier(n_estimators=100, max_depth=16)
model.fit(X_train, y_train)

# Evaluate
score = model.score(X_test, y_test)
print(f"Accuracy: {score:.4f}")
```

The main tabular and estimator stages use GPU data. I/O, setup, scalar scoring/printing, internal conversions, and unsupported operations can still involve the CPU or transfers.

---

## Key Differences from sklearn

1. **Platform:** Linux and WSL2 only. No native macOS or Windows.

2. **Sparse data:** Coverage is estimator-specific; do not densify a large sparse matrix blindly or assume all sparse inputs fall back. Check the pinned compatibility page.

3. **String data:** Must be pre-encoded to numeric. No native string column support in estimators.

4. **Multi-output:** Not supported for Random Forest.

5. **Warm starts:** Not supported for most algorithms.

6. **Unsupported parameters:** May trigger fallback or raise; never silently drop a constraint such as `positive=True` merely to obtain GPU execution.

7. **Model equivalence:** Different algorithms can change fitted models substantially. Validate scientific conclusions and held-out quality; do not promise equivalent quality.

8. **Memory:** Limited by GPU VRAM (typically 8-80 GB). Use managed memory or Dask for larger datasets.

9. **Missing fitted attributes:** Some proxy attributes remain unavailable; inspect the estimator-specific compatibility list before using diagnostics.

---

## Common Migration Patterns

### Pattern 1: Zero-Effort (cuml.accel)

```python
# Add one line at top of notebook:
%load_ext cuml.accel

from sklearn.cluster import KMeans  # Now GPU-accelerated
from sklearn.decomposition import PCA  # Now GPU-accelerated
# Everything else stays exactly the same
```

### Pattern 2: Direct Import Swap

```python
# Before
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# After
from cuml.ensemble import RandomForestClassifier
from cuml.preprocessing import StandardScaler
from cuml.model_selection import train_test_split
```

### Pattern 3: Full RAPIDS Pipeline (cuDF + cuML)

```python
import cudf
from cuml.preprocessing import StandardScaler, LabelEncoder
from cuml.ensemble import RandomForestClassifier
from cuml.model_selection import train_test_split

# Load and preprocess entirely on GPU
df = cudf.read_parquet("data.parquet")
le = LabelEncoder()
df["category_encoded"] = le.fit_transform(df["category"])

X = df[["feature1", "feature2", "category_encoded"]].to_cupy()
y = df["target"].to_cupy()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

model = RandomForestClassifier(n_estimators=200, max_depth=16)
model.fit(X_train, y_train)
print(f"Accuracy: {model.score(X_test, y_test):.4f}")
```

### Pattern 4: GPU Inference for CPU-Trained Models

```python
from cuml.fil import ForestInference

# Load a supported XGBoost/LightGBM/sklearn model for GPU inference
fil_model = ForestInference.load("my_xgboost_model.ubj", is_classifier=True)
predictions = fil_model.predict(X_test)
```
