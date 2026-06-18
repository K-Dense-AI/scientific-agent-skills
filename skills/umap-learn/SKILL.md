---
name: umap-learn
description: Use UMAP-learn for nonlinear dimensionality reduction, 2D/3D embeddings, clustering preprocessing, supervised or semi-supervised UMAP, DensMAP, AlignedUMAP, and Parametric UMAP workflows.
license: BSD-3-Clause license
metadata: {"version": "1.1", "skill-author": "K-Dense Inc."}
---

# UMAP-Learn

## Overview

UMAP (Uniform Manifold Approximation and Projection) is a dimensionality reduction technique for visualization and general non-linear dimensionality reduction. Apply this skill for fast, scalable embeddings that preserve local and global structure, supervised learning, and clustering preprocessing.

## Quick Start

### Installation

Current stable release: **umap-learn 0.5.12** (released April 2026). Requires Python 3.9+ and depends on `scikit-learn>=1.6`, `numba`, `pynndescent`, `numpy`, and `scipy`. Pin to a verified release:

```bash
uv pip install umap-learn==0.5.12
```

### Basic Usage

UMAP follows scikit-learn conventions and can be used as a drop-in replacement for t-SNE or PCA.

```python
import umap
from sklearn.preprocessing import StandardScaler

# Prepare data (standardization is essential)
scaled_data = StandardScaler().fit_transform(data)

# Method 1: Single step (fit and transform)
embedding = umap.UMAP().fit_transform(scaled_data)

# Method 2: Separate steps (for reusing trained model)
reducer = umap.UMAP(random_state=42)
reducer.fit(scaled_data)
embedding = reducer.embedding_  # Access the trained embedding
```

**Preprocessing requirement:** Match preprocessing to the metric. For numeric Euclidean-style metrics, scale features before fitting so high-variance columns do not dominate. For cosine, binary, precomputed-distance, or mixed-feature workflows, choose preprocessing that matches the metric instead of blindly standardizing every column.

### Typical Workflow

```python
import umap
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler

# 1. Preprocess data
scaler = StandardScaler()
scaled_data = scaler.fit_transform(raw_data)

# 2. Create and fit UMAP
reducer = umap.UMAP(
    n_neighbors=15,
    min_dist=0.1,
    n_components=2,
    metric='euclidean',
    random_state=42
)
embedding = reducer.fit_transform(scaled_data)

# 3. Visualize
plt.scatter(embedding[:, 0], embedding[:, 1], c=labels, cmap='Spectral', s=5)
plt.colorbar()
plt.title('UMAP Embedding')
plt.show()
```

## Parameter Tuning Guide

UMAP has four primary parameters that control the embedding behavior. Understanding these is crucial for effective usage.

### n_neighbors (default: 15)

**Purpose:** Balances local versus global structure in the embedding.

**How it works:** Controls the size of the local neighborhood UMAP examines when learning manifold structure.

**Effects by value:**
- **Low values (2-5):** Emphasizes fine local detail but may fragment data into disconnected components
- **Medium values (15-20):** Balanced view of both local structure and global relationships (recommended starting point)
- **High values (50-200):** Prioritizes broad topological structure at the expense of fine-grained details

**Recommendation:** Start with 15 and adjust based on results. Increase for more global structure, decrease for more local detail.

### min_dist (default: 0.1)

**Purpose:** Controls how tightly points cluster in the low-dimensional space.

**How it works:** Sets the minimum distance apart that points are allowed to be in the output representation.

**Effects by value:**
- **Low values (0.0-0.1):** Creates clumped embeddings useful for clustering; reveals fine topological details
- **High values (0.5-0.99):** Prevents tight packing; emphasizes broad topological preservation over local structure

**Recommendation:** Use 0.0 for clustering applications, 0.1-0.3 for visualization, 0.5+ for loose structure.

### n_components (default: 2)

**Purpose:** Determines the dimensionality of the embedded output space.

**Key feature:** Unlike t-SNE, UMAP scales well in the embedding dimension, enabling use beyond visualization.

**Common uses:**
- **2-3 dimensions:** Visualization
- **5-10 dimensions:** Clustering preprocessing (better preserves density than 2D)
- **10-50 dimensions:** Feature engineering for downstream ML models

**Recommendation:** Use 2 for visualization, 5-10 for clustering, higher for ML pipelines.

### metric (default: 'euclidean')

**Purpose:** Specifies how distance is calculated between input data points.

**Supported metrics:**
- **Minkowski variants:** euclidean, manhattan, chebyshev
- **Spatial metrics:** canberra, braycurtis, haversine
- **Correlation metrics:** cosine, correlation (good for text/document embeddings)
- **Binary data metrics:** hamming, jaccard, dice, russellrao, kulsinski, rogerstanimoto, sokalmichener, sokalsneath, yule
- **Custom metrics:** User-defined distance functions via Numba

**Recommendation:** Use euclidean for numeric data, cosine for text/document vectors, hamming for binary data.

### Parameter Tuning Example

```python
# For visualization with emphasis on local structure
umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=2, metric='euclidean')

# For clustering preprocessing
umap.UMAP(n_neighbors=30, min_dist=0.0, n_components=10, metric='euclidean')

# For document embeddings
umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=2, metric='cosine')

# For preserving global structure
umap.UMAP(n_neighbors=100, min_dist=0.5, n_components=2, metric='euclidean')
```

## Supervised and Semi-Supervised Dimension Reduction

UMAP supports incorporating label information to guide the embedding process, enabling class separation while preserving internal structure.

### Supervised UMAP

Pass target labels via the `y` parameter when fitting:

```python
# Supervised dimension reduction
embedding = umap.UMAP().fit_transform(data, y=labels)
```

**Key benefits:**
- Achieves cleanly separated classes
- Preserves internal structure within each class
- Maintains global relationships between classes

### Semi-Supervised UMAP

For partial labels, mark unlabeled points with `-1` following scikit-learn convention:

```python
# Create semi-supervised labels
semi_labels = labels.copy()
semi_labels[unlabeled_indices] = -1

# Fit with partial labels
embedding = umap.UMAP().fit_transform(data, y=semi_labels)
```

**When to use:** When labeling is expensive or you have more data than labels available.

## UMAP for Clustering

UMAP serves as effective preprocessing for density-based clustering algorithms like HDBSCAN, overcoming the curse of dimensionality.

### Best Practices for Clustering

**Key principle:** Configure UMAP differently for clustering than for visualization.

**Recommended parameters:**
- **n_neighbors:** Increase to ~30 (default 15 is too local and can create artificial fine-grained clusters)
- **min_dist:** Set to 0.0 (pack points densely within clusters for clearer boundaries)
- **n_components:** Use 5-10 dimensions (maintains performance while improving density preservation vs. 2D)

### Clustering Workflow

Install HDBSCAN separately for density-based clustering:

```bash
uv pip install hdbscan
```

```python
import umap
import hdbscan
from sklearn.preprocessing import StandardScaler

# 1. Preprocess data
scaled_data = StandardScaler().fit_transform(data)

# 2. UMAP with clustering-optimized parameters
reducer = umap.UMAP(
    n_neighbors=30,
    min_dist=0.0,
    n_components=10,  # Higher than 2 for better density preservation
    metric='euclidean',
    random_state=42
)
embedding = reducer.fit_transform(scaled_data)

# 3. Apply HDBSCAN clustering
clusterer = hdbscan.HDBSCAN(
    min_cluster_size=15,
    min_samples=5,
    metric='euclidean'
)
labels = clusterer.fit_predict(embedding)

# 4. Evaluate
from sklearn.metrics import adjusted_rand_score
score = adjusted_rand_score(true_labels, labels)
print(f"Adjusted Rand Score: {score:.3f}")
print(f"Number of clusters: {len(set(labels)) - (1 if -1 in labels else 0)}")
print(f"Noise points: {sum(labels == -1)}")
```

### Visualization After Clustering

```python
# Create 2D embedding for visualization (separate from clustering)
vis_reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=2, random_state=42)
vis_embedding = vis_reducer.fit_transform(scaled_data)

# Plot with cluster labels
import matplotlib.pyplot as plt
plt.scatter(vis_embedding[:, 0], vis_embedding[:, 1], c=labels, cmap='Spectral', s=5)
plt.colorbar()
plt.title('UMAP Visualization with HDBSCAN Clusters')
plt.show()
```

**Important caveat:** UMAP does not completely preserve density and can create artificial cluster divisions. Always validate and explore resulting clusters.

## Transforming New Data

UMAP enables preprocessing of new data through its `transform()` method, allowing trained models to project unseen data into the learned embedding space.

### Basic Transform Usage

```python
# Train on training data
trans = umap.UMAP(n_neighbors=15, random_state=42).fit(X_train)

# Transform test data
test_embedding = trans.transform(X_test)
```

### Integration with Machine Learning Pipelines

```python
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import umap

# Split data
X_train, X_test, y_train, y_test = train_test_split(data, labels, test_size=0.2)

# Preprocess
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train UMAP
reducer = umap.UMAP(n_components=10, random_state=42)
X_train_embedded = reducer.fit_transform(X_train_scaled)
X_test_embedded = reducer.transform(X_test_scaled)

# Train classifier on embeddings
clf = SVC()
clf.fit(X_train_embedded, y_train)
accuracy = clf.score(X_test_embedded, y_test)
print(f"Test accuracy: {accuracy:.3f}")
```

### Important Considerations

**Data consistency:** The transform method assumes the overall distribution in the higher-dimensional space is consistent between training and test data. When this assumption fails, consider using Parametric UMAP instead.

**Performance:** Transform operations are efficient (typically <1 second), though initial calls may be slower due to Numba JIT compilation.

**Scikit-learn compatibility:** UMAP follows standard sklearn conventions and works in pipelines. Recent 0.5.x releases also improved feature-name support and compatibility with current scikit-learn validation APIs:

```python
from sklearn.pipeline import Pipeline

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('umap', umap.UMAP(n_components=10)),
    ('classifier', SVC())
])

pipeline.fit(X_train, y_train)
predictions = pipeline.predict(X_test)
feature_names = pipeline.named_steps['umap'].get_feature_names_out()
```

## Advanced Features

### Parametric UMAP

Parametric UMAP replaces direct embedding optimization with a learned neural network mapping function.

**Key differences from standard UMAP:**
- Uses TensorFlow/Keras to train encoder networks
- Enables efficient transformation of new data
- Supports reconstruction via decoder networks (inverse transform)
- Allows custom architectures (CNNs for images, RNNs for sequences)

**Installation:**
```bash
uv pip install "umap-learn[parametric-umap]==0.5.12"
# Installs the TensorFlow-backed Parametric UMAP extra.
```

**Basic usage:**
```python
from umap.parametric_umap import ParametricUMAP

# Default architecture (3-layer 100-neuron fully-connected network)
embedder = ParametricUMAP()
embedding = embedder.fit_transform(data)

# Transform new data efficiently
new_embedding = embedder.transform(new_data)
```

**Custom architecture:**
```python
import tensorflow as tf

# Define custom encoder
encoder = tf.keras.Sequential([
    tf.keras.layers.InputLayer(shape=(input_dim,)),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dense(64, activation='relu'),
    tf.keras.layers.Dense(2)  # Output dimension
])

embedder = ParametricUMAP(encoder=encoder, dims=(input_dim,))
embedding = embedder.fit_transform(data)
```

**Persistence:** Save Parametric UMAP with its built-in Keras-aware methods rather than plain pickle:

```python
embedder.save("parametric_umap_model", exclude_raw_data=True)

from umap.parametric_umap import load_ParametricUMAP
loaded = load_ParametricUMAP("parametric_umap_model")
new_embedding = loaded.transform(new_data)
```

Recent 0.5.12 fixes include Parametric UMAP retraining stability improvements and metric-gradient fixes, so prefer the pinned current release for neural-network workflows.

**When to use Parametric UMAP:**
- Need efficient transformation of new data after training
- Require reconstruction capabilities (inverse transforms)
- Want to combine UMAP with autoencoders
- Working with complex data types (images, sequences) benefiting from specialized architectures

### Inverse Transforms

Inverse transforms enable reconstruction of high-dimensional data from low-dimensional embeddings.

**Basic usage:**
```python
reducer = umap.UMAP()
embedding = reducer.fit_transform(data)

# Reconstruct high-dimensional data from embedding coordinates
reconstructed = reducer.inverse_transform(embedding)
```

**Important limitations:**
- Computationally expensive operation
- Works poorly outside the convex hull of the embedding
- Accuracy decreases in regions with gaps between clusters

**Example: Exploring embedding space:**
```python
import numpy as np

# Create grid of points in embedding space
x = np.linspace(embedding[:, 0].min(), embedding[:, 0].max(), 10)
y = np.linspace(embedding[:, 1].min(), embedding[:, 1].max(), 10)
xx, yy = np.meshgrid(x, y)
grid_points = np.c_[xx.ravel(), yy.ravel()]

# Reconstruct samples from grid
reconstructed_samples = reducer.inverse_transform(grid_points)
```

### AlignedUMAP

For analyzing temporal or related datasets (e.g., time-series experiments, batch data):

```python
from umap import AlignedUMAP

# List of related datasets
datasets = [day1_data, day2_data, day3_data]

# Relations map matching sample indices between consecutive datasets.
relations = [
    {day1_idx: day2_idx for day1_idx, day2_idx in matched_day1_to_day2},
    {day2_idx: day3_idx for day2_idx, day3_idx in matched_day2_to_day3},
]

# Create aligned embeddings
mapper = AlignedUMAP().fit(datasets, relations=relations)
aligned_embeddings = mapper.embeddings_  # List of embeddings
```

**When to use:** Comparing embeddings across related datasets while maintaining consistent coordinate systems. `relations` is required for meaningful alignment; each dictionary describes how samples in one dataset correspond to samples in the next.

## Reproducibility

To ensure reproducible results, always set the `random_state` parameter:

```python
reducer = umap.UMAP(random_state=42)
```

UMAP uses stochastic optimization, so results will vary slightly between runs without a fixed random state.

Setting `random_state` prioritizes deterministic output. Leave it unset when throughput matters more than exact repeatability, because UMAP can use more parallelism without a fixed seed.

## Common Issues and Solutions

**Issue:** Disconnected components or fragmented clusters
- **Solution:** Increase `n_neighbors` to emphasize more global structure

**Issue:** Clusters too spread out or not well separated
- **Solution:** Decrease `min_dist` to allow tighter packing

**Issue:** Poor clustering results
- **Solution:** Use clustering-specific parameters (n_neighbors=30, min_dist=0.0, n_components=5-10)

**Issue:** Transform results differ significantly from training
- **Solution:** Ensure test data distribution matches training, or use Parametric UMAP

**Issue:** Slow performance on large datasets
- **Solution:** Set `low_memory=True` (default), or consider dimensionality reduction with PCA first

**Issue:** NaN or inf values in input data
- **Solution:** Impute or drop invalid rows before fitting. Current UMAP uses scikit-learn-style finite-value checks (`ensure_all_finite`) in `fit()` and `update()`, so clean numeric input is the safest default

**Issue:** All points collapsed to single cluster
- **Solution:** Check data preprocessing (ensure proper scaling), increase `min_dist`

**Issue:** Imports resolve to a local file instead of the real package
- **Solution:** Do not keep project files named `umap.py`, `sklearn.py`, `hdbscan.py`, or `tensorflow.py` beside notebooks or scripts. Those names can shadow installed packages and break or poison examples.

## Resources

### Official documentation

- [UMAP user guide](https://umap-learn.readthedocs.io/en/latest/)
- [Release notes](https://umap-learn.readthedocs.io/en/latest/release_notes.html)
- [PyPI package](https://pypi.org/project/umap-learn/) (current stable: 0.5.12)
- [GitHub repository](https://github.com/lmcinnes/umap)

### references/

Contains detailed API documentation:
- `api_reference.md`: Complete UMAP class parameters and methods

Load these references when detailed parameter information or advanced method usage is needed.

