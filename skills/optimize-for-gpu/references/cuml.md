# cuML Reference

cuML is NVIDIA's GPU-accelerated machine learning library within the RAPIDS ecosystem. It provides scikit-learn-compatible APIs for 50+ algorithms, delivering 10-50x faster performance on average, with some algorithms (HDBSCAN, t-SNE, UMAP, KNN) reaching 60-600x speedup. It follows the familiar fit/predict/transform pattern from sklearn.

> **Full documentation:** https://docs.rapids.ai/api/cuml/stable/

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

Always use `uv add` (never `pip install` or `conda install`) in all install instructions, docstrings, comments, and error messages.

```bash
uv add --extra-index-url=https://pypi.nvidia.com cuml-cu12    # For CUDA 12.x
```

**Platform:** Linux and WSL2 only (no native macOS or Windows).
**Requires:** scikit-learn >= 1.4, NVIDIA GPU with CUDA 12.x support.

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
- Accelerates 30+ algorithms across sklearn, umap-learn, and hdbscan.
- Compatible with scikit-learn versions 1.4-1.7.

### Known Fallback Triggers (Runs on CPU Instead)

- Sparse input data (most algorithms)
- Callable parameters (e.g., callable `init` for KMeans)
- Certain parameter values: `n_components="mle"` for PCA, `positive=True` for linear models, warm starts
- Unsupported distance metrics for neighbors algorithms
- Multi-output targets for Random Forest
- String/object dtypes — must pre-encode with LabelEncoder first

### Numerical Precision

GPU results are numerically equivalent but may differ at floating-point precision level due to parallel reduction order. Compare model quality via scores (accuracy, R2, etc.), not raw coefficient values.

---

## Direct cuML API

Replace sklearn imports with cuml imports. The API is identical — fit/predict/transform.

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

For GPU-efficient hyperparameter search, use dask-ml's GridSearchCV/RandomizedSearchCV rather than sklearn's — sklearn's version causes excessive CPU-GPU data transfers per fold.

```python
from dask_ml.model_selection import RandomizedSearchCV
from cuml.ensemble import RandomForestClassifier

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

FIL provides high-performance GPU inference for tree-based models trained in any framework — 80x+ faster than sklearn inference.

```python
from cuml.fil import ForestInference

# Load from XGBoost, LightGBM, or sklearn saved models
fil_model = ForestInference.load("xgboost_model.ubj", is_classifier=True)

# Optional: optimize for specific batch size
fil_model.optimize()

# Predict (80x+ faster than sklearn)
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

- Use float32 instead of float64 when precision allows — halves memory, doubles throughput.
- Keep data on GPU throughout the pipeline — avoid NumPy/pandas round-trips.
- For datasets larger than GPU memory: use Dask multi-GPU or chunk processing.
- Pre-allocate RMM pools to avoid fragmentation.

---

## Performance Optimization

### Expected Speedups by Algorithm

| Category | Typical Speedup | Notes |
|----------|----------------|-------|
| HDBSCAN, t-SNE, UMAP | 60-300x | Complex algorithms benefit most |
| KNN | Up to 600x | Scales dramatically with data size |
| KMeans, Random Forest | 15-80x | RF: 20-45x single GPU |
| FIL inference | 80x+ | Tree model inference from any framework |
| Linear models, PCA, Ridge | 2-10x | Simpler algorithms, lower but consistent gains |

### Key Optimization Tips

1. **Use float32.** GPU float32 throughput is 2x-32x higher than float64. Most ML algorithms don't need double precision.

2. **Keep data on GPU.** Pass CuPy arrays or cuDF DataFrames. Every NumPy/pandas conversion triggers a device-host transfer.

3. **Larger datasets = larger speedup.** GPU parallelism advantage grows with data size. Minimum ~10K rows to see benefit.

4. **Wide data benefits more.** 128-512 features see higher speedups than 8-16 features.

5. **First call has JIT overhead.** Benchmark on subsequent calls, not the first.

6. **Use RMM pools.** Pre-allocated memory pools are 1000x faster than raw cudaMalloc.

7. **Use dask-ml for hyperparameter tuning,** not sklearn's GridSearchCV — it avoids excessive CPU-GPU transfers.

8. **Use FIL for tree model inference.** Even if the model was trained on CPU (XGBoost, LightGBM, sklearn RF), FIL gives 80x+ inference speedup.

---

## Interoperability

- **cuDF:** Zero-copy input. cuDF DataFrames accepted directly by all estimators.
- **CuPy:** Zero-copy via `__cuda_array_interface__`. Most efficient intermediate format.
- **NumPy/pandas:** Accepted as input (auto-transferred to GPU). Output type configurable.
- **PyTorch:** Tensors accepted via array interface.
- **sklearn:** API-compatible. Models interconvertible. cuml.accel for transparent acceleration.
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

All of this runs entirely on GPU — from Parquet read to model evaluation — with zero CPU-GPU transfers.

---

## Key Differences from sklearn

1. **Platform:** Linux and WSL2 only. No native macOS or Windows.

2. **Sparse data:** Most cuML algorithms do not support sparse matrices. Under cuml.accel, sparse inputs fall back to CPU.

3. **String data:** Must be pre-encoded to numeric. No native string column support in estimators.

4. **Multi-output:** Not supported for Random Forest.

5. **Warm starts:** Not supported for most algorithms.

6. **Some sklearn parameters ignored:** `n_jobs` (GPU handles parallelism), `positive=True`, specific solver choices.

7. **Numerical precision:** Results equivalent in quality but may differ at floating-point level. Compare scores, not raw coefficients.

8. **Memory:** Limited by GPU VRAM (typically 8-80 GB). Use managed memory or Dask for larger datasets.

9. **Missing fitted attributes:** Some sklearn attributes not computed under cuml.accel (e.g., HDBSCAN `exemplars_`, LinearRegression `rank_`).

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

# Load XGBoost/LightGBM/sklearn model for 80x+ faster inference
fil_model = ForestInference.load("my_xgboost_model.ubj", is_classifier=True)
predictions = fil_model.predict(X_test)
```
