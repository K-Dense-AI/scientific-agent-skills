# UMAP API Reference

Reference checked 2026-10-01 for **umap-learn 0.5.12** (Python >=3.9; `scikit-learn>=1.6`). The [hosted API guide](https://umap-learn.readthedocs.io/en/latest/api.html) still identifies 0.5.8; use the [released implementation](https://github.com/lmcinnes/umap/blob/release-0.5.12/umap/umap_.py) for exact signatures and return contracts. All calculations run locally; the package has no service endpoint, authentication, or pagination requirement. Examples assume finite numeric arrays with stable sample/feature ordering. Core synthetic checks used native Numba JIT; TensorFlow examples are illustrative and source-checked only.

## UMAP Class

`umap.UMAP(n_neighbors=15, n_components=2, metric='euclidean', metric_kwds=None, output_metric='euclidean', output_metric_kwds=None, n_epochs=None, learning_rate=1.0, init='spectral', min_dist=0.1, spread=1.0, low_memory=True, n_jobs=-1, set_op_mix_ratio=1.0, local_connectivity=1.0, repulsion_strength=1.0, negative_sample_rate=5, transform_queue_size=4.0, a=None, b=None, random_state=None, angular_rp_forest=False, target_n_neighbors=-1, target_metric='categorical', target_metric_kwds=None, target_weight=0.5, transform_seed=42, transform_mode='embedding', force_approximation_algorithm=False, verbose=False, tqdm_kwds=None, unique=False, densmap=False, dens_lambda=2.0, dens_frac=0.3, dens_var_shift=0.1, output_dens=False, disconnection_distance=None, precomputed_knn=(None, None, None))`

Find low-dimensional embedding that approximates the underlying manifold of the data.

### Core Parameters

#### n_neighbors (int, default: 15)
Size of the local neighborhood used for manifold approximation. Larger values result in more global views of the manifold, while smaller values preserve more local structure. Generally in the range 2 to 100.

**Tuning guidance:**
- Use 2-5 for very local structure
- Use 10-20 for balanced local/global structure (typical)
- Use 50-200 for emphasizing global structure

#### n_components (int, default: 2)
Dimension of the embedding space. Unlike t-SNE, UMAP scales well with increasing embedding dimensions.

**Common values:**
- 2-3: Visualization
- 5-10: Clustering preprocessing
- 10-100: Feature engineering for downstream ML

#### metric (str or callable, default: 'euclidean')
Distance metric to use. Accepts:
- Recognized names in UMAP/PyNNDescent; not every SciPy or scikit-learn metric is accepted, and sparse support differs from dense support
- `"precomputed"`: distances, not similarities; see the recipe below
- Custom Numba-compatible callables returning a distance; return `(distance, gradient)` to enable inverse transformation

**Common metrics:**
- `'euclidean'`: Standard Euclidean distance (default)
- `'manhattan'`: L1 distance
- `'cosine'`: Cosine distance (good for text/document vectors)
- `'correlation'`: Correlation distance
- `'hamming'`: Hamming distance (for binary data)
- `'jaccard'`: Jaccard distance (for binary/set data)
- `'dice'`: Dice distance
- `'canberra'`: Canberra distance
- `'braycurtis'`: Bray-Curtis distance
- `'chebyshev'`: Chebyshev distance
- `'minkowski'`: Minkowski distance (specify p with metric_kwds)
- `'precomputed'`: Use precomputed distance matrix

#### output_metric (str or callable, default: 'euclidean')
Distance metric for the embedding space. Most workflows should keep the Euclidean default; advanced workflows can use a supported output metric with `output_metric_kwds`.

#### min_dist (float, default: 0.1)
A parameter of the fitted low-dimensional attraction curve, not a hard pairwise-distance bound. Smaller values favor clumpier embeddings. Require `0 <= min_dist <= spread`.

**Tuning guidance:**
- Use 0.0 for clustering applications
- Use 0.1-0.3 for visualization (balanced)
- Use 0.5-0.99 for loose structure preservation

#### spread (float, default: 1.0)
Effective scale of embedded points. Combined with `min_dist` to control clumped vs. spread-out embeddings. Determines how spread out the clusters are in the embedding space.

### Training Parameters

#### n_epochs (int, list of int, or None; default: None)
Optimization epochs. With `None`, standard UMAP uses 500 epochs up to 10,000 samples and 200 above that; densMAP adds 200. A list requests intermediate embeddings in `embedding_list_`, while `embedding_` is the final result.

**Manual tuning:**
- Smaller datasets may need 500+ epochs
- Larger datasets may converge with 200 epochs
- More epochs increase cost; scientific validity still requires external checks

#### learning_rate (float, default: 1.0)
Initial learning rate for the SGD optimizer. Higher values lead to faster convergence but may overshoot optimal solutions.

#### init (str or np.ndarray, default: 'spectral')
Initialization method for the embedding:
- `'spectral'`: Spectral initialization (default)
- `'random'`: Random initialization
- `'pca'`: Initialize with PCA (TruncatedSVD for sparse input)
- `'tswspectral'`: Truncated-SVD warm start for spectral initialization
- numpy array: Custom initialization (shape: (n_samples, n_components))

### Advanced Structural Parameters

#### local_connectivity (float, default: 1.0)
Number of nearest neighbors assumed to be locally connected. Higher values give more connected manifolds.

#### set_op_mix_ratio (float, default: 1.0)
Interpolation between union and intersection when constructing fuzzy set unions. Value of 1.0 uses pure union, 0.0 uses pure intersection.

#### repulsion_strength (float, default: 1.0)
Weighting applied to negative samples in low-dimensional embedding optimization. Higher values push embedded points further apart.

#### negative_sample_rate (int, default: 5)
Number of negative samples to select per positive sample. Higher values lead to greater repulsion between points and more spread-out embeddings but increase computational cost.

### Supervised Learning Parameters

#### target_n_neighbors (int, default: -1)
Number of nearest neighbors to use when constructing target simplicial set. If -1, uses n_neighbors value.

#### target_metric (str or callable, default: 'categorical')
Distance metric for target values (labels):
- `'categorical'`: For classification tasks
- A supported continuous metric such as `"l2"` for regression targets; `-1` is not a generic missing-value marker

#### target_weight (float, default: 0.5)
Weight applied to target information vs. data structure. Range 0.0 to 1.0:
- Lower values emphasize the feature graph; higher values emphasize target agreement
- 0.5 is the default
- With categorical targets in 0.5.12, even 0.0 changes edges between classes; omit `y` for an unsupervised fit
- 1.0 strongly suppresses cross-class connections; it does not discard the feature graph

### Transform Parameters

#### transform_queue_size (float, default: 4.0)
Size of the nearest neighbor search queue for transform operations. Larger values improve transform accuracy but increase memory usage and computation time.

#### transform_seed (int, default: 42)
Random seed for transform operations; keep query order and software environment fixed when checking reproducibility.

#### transform_mode (str, default: 'embedding')
Method for transforming new data:
- `'embedding'`: Standard approach (default)
- `'graph'`: `fit_transform` returns the sparse training graph `(n_train, n_train)`; `transform` returns a bipartite graph `(n_new, n_train)`, not embedding coordinates

### Performance Parameters

#### low_memory (bool, default: True)
Whether to use a memory-efficient implementation. Set to False only if memory is not a constraint and you want faster performance.

#### n_jobs (int, default: -1)
Number of parallel jobs to use where supported. `-1` uses all available processors. A non-None `random_state` forces `n_jobs=1` in standard UMAP.

#### verbose (bool, default: False)
Whether to print progress messages during fitting.

#### tqdm_kwds (dict, default: None)
Keyword arguments passed to the tqdm progress bar when progress reporting is enabled.

#### unique (bool, default: False)
Fit unique feature rows and map the resulting coordinates back to input rows. Audit duplicate rows with conflicting labels. Unsupported with precomputed distances or precomputed neighbors.

#### force_approximation_algorithm (bool, default: False)
Use approximate search even below the usual small-data threshold. Large inputs already take that path; this is not a general large-data speed switch.

#### angular_rp_forest (bool, default: False)
Whether to use angular random projection forest for nearest neighbor search. Can improve performance for normalized data in high dimensions.

### DensMAP Parameters

densMAP adds a local density correlation objective; it does not guarantee exact density preservation.

#### densmap (bool, default: False)
Whether to use the DensMAP algorithm instead of standard UMAP. Encourages local density relationships as well as neighborhood structure. Only Euclidean output is supported, and new-data transform/inverse transform are unavailable.

#### dens_lambda (float, default: 2.0)
Weight of density preservation term in DensMAP optimization. Higher values emphasize density preservation.

#### dens_frac (float, default: 0.3)
Fraction of optimization epochs using the density objective, after the initial `(1 - dens_frac)` fraction uses the standard UMAP objective.

#### dens_var_shift (float, default: 0.1)
Positive stabilizer added to variance of embedded local radii in the density objective.

#### output_dens (bool, default: False)
Whether to output log-transformed local-radius estimates in addition to the embedding; larger radii indicate sparser neighborhoods. These are not density probabilities. Also supported with `densmap=False`. When enabled, `fit_transform()` returns `(embedding, original_local_radii, embedded_local_radii)` and fitted objects expose density-related attributes such as `rad_orig_` and `rad_emb_`.

### Other Parameters

#### a (float, default: None)
Parameter controlling embedding. If None, determined automatically from min_dist and spread.

#### b (float, default: None)
Parameter controlling embedding. If None, determined automatically from min_dist and spread.

#### random_state (int, RandomState instance, or None, default: None)
Random state for reproducibility within the same environment. Save input ordering, preprocessing and dependency versions; cross-version equality is not guaranteed.

#### metric_kwds (dict, default: None)
Additional keyword arguments for the distance metric.

#### disconnection_distance (float, default: None)
Prunes neighbor edges with distance greater than or equal to this threshold. `None` chooses a built-in cutoff for certain bounded metrics, otherwise infinity. It does not use the observed graph maximum. Inspect disconnected vertices and nonfinite coordinates.

#### precomputed_knn (tuple, default: (None, None, None))
Precomputed neighbors as `(knn_indices, knn_dists, knn_search_index)`, or the two arrays alone. Arrays must correspond to the same input rows/metric and include each row itself first at zero distance. Supply at least `n_neighbors` columns; retain a compatible PyNNDescent `NNDescent` search index for new-data transforms. Without it, `transform(new_data)` is unsupported. Unlike `metric="precomputed"`, `X` remains the feature matrix.

## Methods and outputs

| Method | Released 0.5.12 contract |
| --- | --- |
| `fit(X, y=None, ensure_all_finite=True, **kwargs)` | Returns `self`. `X` is samples by features, or square training distances for a precomputed metric. |
| `fit_transform(X, y=None, ensure_all_finite=True, **kwargs)` | Returns coordinates; with `output_dens=True` returns `(embedding, rad_orig, rad_emb)`; with graph mode returns a sparse graph. |
| `transform(X, ensure_all_finite=True)` | Coordinates for new rows, or bipartite graph in graph mode. Precomputed metrics require new-to-training distances with unchanged training-column order. |
| `inverse_transform(X)` | Approximate reconstruction from coordinates. Requires dense training features and a gradient-capable input metric; unavailable for densMAP, precomputed metric, or graph mode. |
| `update(X, ensure_all_finite=True)` | Mutates the fitted model and returns **None**. Adds feature rows and can move old points. Rejects supervised models and precomputed metrics; not equivalent to transforming new rows. Revalidate after an update. |
| `get_feature_names_out(input_features=None)` | Names such as `umap0`, `umap1`; `input_features` is ignored. |

`ensure_all_finite` accepts `True`, `False`, or `"allow-nan"`, but bypassing the
check does not make distance calculations missing-value aware. Clean or impute
inputs deliberately. Treat nonfinite **outputs** as a failed support check, even
when inputs are finite.

Use `embedding_`, `graph_`, `rad_orig_`/`rad_emb_` (when requested), and
`embedding_list_` (when requested) for results. Graph storage formats can vary;
use `.tocsr()` when CSR operations are required. Attributes beginning with `_`
are implementation details, may be missing on different search paths, and are
not portable persistence contracts. Keep training data, preprocessing, feature
schema, row IDs, metric, and software versions with the model.

A transform is meaningful only for samples supported by the training distribution.
It does not update the trained embedding. Inverse output is in the **preprocessed**
feature space; use the fitted scaler's `inverse_transform` to restore units when
appropriate. Avoid treating interpolated samples between separated groups as
scientifically realizable observations.

## ParametricUMAP Class

`umap.parametric_umap.ParametricUMAP(batch_size=None, dims=None, encoder=None, decoder=None, parametric_reconstruction=False, parametric_reconstruction_loss_fcn=None, parametric_reconstruction_loss_weight=1.0, autoencoder_loss=False, reconstruction_validation=None, global_correlation_loss_weight=0, landmark_loss_fn=None, landmark_loss_weight=1.0, keras_fit_kwargs={}, **kwargs)`

Install with `uv pip install "umap-learn[parametric-umap]==0.5.12"`. The released module imports TensorFlow and Keras 3 (`keras.ops`) even though the package extra only declares `tensorflow>=2.1`; resolve a compatible modern pair. The [parametric source](https://github.com/lmcinnes/umap/blob/release-0.5.12/umap/parametric_umap.py) was reviewed; neural training/persistence was not executed in this audit.

### Additional Parameters (beyond UMAP)

#### encoder (Keras 3 Model, default: None)
Keras model for encoding data to embeddings. If None, uses default 3-layer architecture with 100 neurons per layer.

#### decoder (Keras 3 Model, default: None)
Keras model for decoding embeddings back to data space. Only used if parametric_reconstruction=True.

#### parametric_reconstruction (bool, default: False)
Enable a decoder-based inverse. A default decoder is built when none is supplied.

#### parametric_reconstruction_loss_fcn (callable, default: None)
Custom reconstruction loss. Default is binary cross entropy **from logits**, with targets in `[0, 1]` and a linear decoder output. For continuous standardized features, choose an appropriate loss such as mean squared error; inverse decoder outputs are logits under the default loss.

#### parametric_reconstruction_loss_weight (float, default: 1.0)
Weight applied to the parametric reconstruction loss.

#### autoencoder_loss (bool, default: False)
With `parametric_reconstruction=True`, also backpropagate reconstruction loss through the encoder; otherwise the encoder is trained on the embedding objective.

#### global_correlation_loss_weight (float, default: 0)
Weight for global correlation loss, used to encourage preservation of broad distance relationships.

#### reconstruction_validation (array, default: None)
Held-out feature array `X_val`, not an `(X_val, y_val)` tuple. Preprocess it using training-fitted transforms.

#### dims (tuple, default: None)
Input shape for reshaping features before neural fitting. Inferred for flat features; supply it for a structured input such as images. Encoder output dimension must match `n_components`. At inference, provide the encoder input shape; `transform` does not repeat training-time reshaping.

#### batch_size (int, default: None)
Batch size for neural network training. If None, determined automatically.

#### landmark_loss_fn (callable, default: None)
Loss function used when retraining with landmark positions.

#### landmark_loss_weight (float, default: 1.0)
Weight applied to landmark loss relative to the UMAP loss.

#### keras_fit_kwargs (dict, default: {})
Additional keyword arguments passed to the Keras fit() method.

#### Training epoch attributes
`ParametricUMAP` initializes `n_training_epochs=1` and `loss_report_frequency=10` internally. Set these attributes after construction when you need longer neural-network training.

### Methods

`fit` and `fit_transform` accept `(X, y=None, precomputed_distances=None, landmark_positions=None)`, not the base class finite-check keyword. `transform(X, batch_size=None)` calls the encoder. `inverse_transform(X)` calls a trained decoder only when `parametric_reconstruction=True`; otherwise it falls back to the ordinary approximate inverse. Do not assume every base-class mode or update method is a supported neural workflow.

#### fit(X, y=None, precomputed_distances=None, landmark_positions=None)
Fit the parametric model. `landmark_positions` can be used for landmarked retraining workflows.

#### save(save_location, verbose=True, exclude_raw_data=False)
Create `save_location` first, then save the object and networks. `load_ParametricUMAP(save_location, verbose=True)` reads a pickle and Keras files: load only trusted directories. In released 0.5.12 the saver writes `parametric_model.keras`, but the loader checks `parametric_model`. Validate encoder/decoder predictions after roundtrip and do not claim full training-state restoration. `exclude_raw_data=True` removes selected raw-data attributes during saving, not every possible training-data representation.

## Utility functions

Import these from **`umap.umap_`**, not from the top-level `umap` package.
They expose lower-level implementation details; ordinary workflows should use `UMAP`.

```python
from umap.umap_ import (
    nearest_neighbors, fuzzy_simplicial_set, simplicial_set_embedding, find_ab_params,
)
```

- `nearest_neighbors(X, n_neighbors, metric, metric_kwds, angular, random_state,
  low_memory=True, use_pynndescent=True, n_jobs=-1, verbose=False)` returns
  `(indices, distances, search_index)`. The third value is an NNDescent index on
  the approximate-search path, or `None` for precomputed distances.
- `fuzzy_simplicial_set(X, n_neighbors, random_state, metric, metric_kwds={},
  knn_indices=None, knn_dists=None, angular=False, set_op_mix_ratio=1.0,
  local_connectivity=1.0, apply_set_operations=True, verbose=False,
  return_dists=None)` returns **`(graph, sigmas, rhos)`** when `return_dists=None`.
  Passing `False` or `True` adds a fourth item: `None` or the sparse distances.
- `simplicial_set_embedding(data, graph, n_components, initial_alpha, a, b,
  gamma, negative_sample_rate, n_epochs, init, random_state, metric, metric_kwds,
  densmap, densmap_kwds, output_dens, output_metric=euclidean_grad,
  output_metric_kwds={}, euclidean_output=True, parallel=False, verbose=False,
  tqdm_kwds=None)` returns **`(embedding, auxiliary_data)`**. `euclidean_grad`
  denotes the function in `umap.distances`, not a string metric.
- `find_ab_params(spread, min_dist)` returns `(a, b)` for the embedding curve.

## AlignedUMAP Class

`umap.AlignedUMAP(n_neighbors=15, n_components=2, metric='euclidean', metric_kwds=None, n_epochs=None, learning_rate=1.0, init='spectral', alignment_regularisation=0.01, alignment_window_size=3, min_dist=0.1, spread=1.0, low_memory=False, set_op_mix_ratio=1.0, local_connectivity=1.0, repulsion_strength=1.0, negative_sample_rate=5, transform_queue_size=4.0, a=None, b=None, random_state=None, angular_rp_forest=False, target_n_neighbors=-1, target_metric='categorical', target_metric_kwds=None, target_weight=0.5, transform_seed=42, force_approximation_algorithm=False, verbose=False, unique=False)`

UMAP variant for aligning multiple related datasets.

### Additional Parameters

#### alignment_regularisation (float, default: 1e-2)
Strength of alignment regularization between datasets.

#### alignment_window_size (int, default: 3)
Number of slices to consider on either side; consecutive mappings are chained across the window.

### Methods

#### fit(X, y=None, **fit_params)
Fit model to multiple datasets.

**Parameters:**
- `X`: list of arrays - List of datasets to align
- `relations`: required keyword in `fit_params`; list of `len(X)-1` dictionaries mapping **previous-slice row index -> next-slice row index**. Use stable scientific IDs to construct one-to-one matches; validate ranges and missing/duplicate matches. Each mapping must be nonempty. Partial mappings are allowed; unrelated rows need no match.
- `fit` returns `self`; `fit_transform` returns `embeddings_`. No ordinary new-row `transform` is implemented.

#### update(X, y=None, **fit_params)
Append a dataset using **one dictionary** passed as `relations={previous_slice_index: new_slice_index}`. This has the same forward direction as each dictionary used by `fit`, not a backward mapping from the new slice. The method mutates the model and returns **None** in 0.5.12. Do not assign its return to the mapper.

### Attributes

#### embeddings_
list of arrays - List of aligned embeddings, one per input dataset.

## Usage Examples

### Basic Usage with All Common Parameters

```python
import umap

# Standard 2D visualization embedding
reducer = umap.UMAP(
    n_neighbors=15,          # Balance local/global structure
    n_components=2,          # Output dimensions
    metric='euclidean',      # Distance metric
    min_dist=0.1,           # Effective packing parameter, not a hard bound
    spread=1.0,             # Scale of embedded points
    random_state=42,        # Reproducibility
    n_epochs=200,           # Training iterations (None = auto)
    learning_rate=1.0,      # SGD learning rate
    init='spectral',        # Initialization method
    low_memory=True,        # Memory-efficient mode
    verbose=True            # Print progress
)

embedding = reducer.fit_transform(data)
```

### Supervised Learning

```python
# Train with labels for class separation
reducer = umap.UMAP(
    n_neighbors=15,
    target_weight=0.5,           # Balance data structure vs labels
    target_metric='categorical',  # Metric for labels
    random_state=42
)

embedding = reducer.fit_transform(data, y=labels)
```

### Clustering Preprocessing

```python
# Candidate settings for clustering; compare to an unreduced baseline
reducer = umap.UMAP(
    n_neighbors=30,      # More global structure
    min_dist=0.0,        # Allow tight packing
    n_components=10,     # Higher-dimensional candidate; density is still distorted
    metric='euclidean',
    random_state=42
)

embedding = reducer.fit_transform(data)
```

### Custom Distance Metric

```python
from numba import njit

@njit()
def custom_distance(x, y):
    """Custom distance function (must be Numba-compatible)"""
    result = 0.0
    for i in range(x.shape[0]):
        result += abs(x[i] - y[i])
    return result

reducer = umap.UMAP(metric=custom_distance, random_state=42, n_jobs=1)
embedding = reducer.fit_transform(data)
```

### Parametric UMAP with Custom Architecture (illustrative, not executed)

```python
import keras
from umap.parametric_umap import ParametricUMAP

# Define custom encoder
encoder = keras.Sequential([
    keras.layers.InputLayer(shape=(input_dim,)),
    keras.layers.Dense(256, activation='relu'),
    keras.layers.Dropout(0.3),
    keras.layers.Dense(128, activation='relu'),
    keras.layers.Dropout(0.3),
    keras.layers.Dense(2)  # Output dimension
])

# Define decoder for reconstruction
decoder = keras.Sequential([
    keras.layers.InputLayer(shape=(2,)),
    keras.layers.Dense(128, activation='relu'),
    keras.layers.Dense(256, activation='relu'),
    keras.layers.Dense(input_dim)
])

# Linear decoder and MSE suit continuous features (e.g., training-standardized data).
# Train parametric UMAP with autoencoder
embedder = ParametricUMAP(
    encoder=encoder,
    decoder=decoder,
    dims=(input_dim,),
    parametric_reconstruction=True,
    parametric_reconstruction_loss_fcn=keras.losses.MeanSquaredError(),
    autoencoder_loss=True,
    batch_size=128,
    n_neighbors=15,
    min_dist=0.1,
    random_state=42
)
embedder.n_training_epochs = 10

embedding = embedder.fit_transform(data)
new_embedding = embedder.transform(new_data)
reconstructed = embedder.inverse_transform(embedding)
```

### DensMAP for Density Preservation

```python
# Preserve local density information
reducer = umap.UMAP(
    densmap=True,           # Enable DensMAP
    dens_lambda=2.0,       # Weight of density preservation
    dens_frac=0.3,         # Final fraction of optimization epochs
    output_dens=True,      # Output log local radii, not probabilities
    n_neighbors=15,
    min_dist=0.1,
    random_state=42
)

embedding, rad_orig, rad_emb = reducer.fit_transform(data)
assert rad_orig.shape == rad_emb.shape == (len(data),)
```

### Aligned UMAP for Time Series

```python
from umap import AlignedUMAP

# Multiple related datasets (e.g., different time points)
datasets = [day1_data, day2_data, day3_data, day4_data]
relations = [
    {day1_idx: day2_idx for day1_idx, day2_idx in matched_day1_to_day2},
    {day2_idx: day3_idx for day2_idx, day3_idx in matched_day2_to_day3},
    {day3_idx: day4_idx for day3_idx, day4_idx in matched_day3_to_day4},
]

# Align embeddings
mapper = AlignedUMAP(
    n_neighbors=15,
    alignment_regularisation=1e-2,  # Alignment strength
    alignment_window_size=2,        # Align with adjacent datasets
    n_components=2,
    random_state=42
)

mapper.fit(datasets, relations=relations)

# Access aligned embeddings
aligned_embeddings = mapper.embeddings_
# aligned_embeddings[0] is day1 embedding
# aligned_embeddings[1] is day2 embedding, etc.
```

### Precomputed distances and neighbors

Distance matrices must be nonnegative and finite with training shape `(n, n)`,
symmetric with zero diagonal. Do not pass a similarity matrix or a new-to-new
matrix to `transform`. Dense storage costs quadratic memory.

```python
from sklearn.metrics import pairwise_distances

D_train = pairwise_distances(X_train)
D_test_to_train = pairwise_distances(X_test, X_train)
mapper = umap.UMAP(metric="precomputed", n_neighbors=10,
                   random_state=42, n_jobs=1)
train_embedding = mapper.fit_transform(D_train)
test_embedding = mapper.transform(D_test_to_train)
assert test_embedding.shape == (len(X_test), 2)
```

For repeated fits on the same **features**, reuse a neighbor search instead:

```python
from sklearn.utils import check_random_state
from umap.umap_ import nearest_neighbors

knn = nearest_neighbors(data, n_neighbors=30, metric="euclidean",
                        metric_kwds={}, angular=False,
                        random_state=check_random_state(42), n_jobs=1)
mapper = umap.UMAP(n_neighbors=30, precomputed_knn=knn,
                   random_state=42, n_jobs=1).fit(data)
new_embedding = mapper.transform(new_data)
```

Do not reuse neighbors after changing row order, features, scaling, metric, or
training folds. Retain the compatible search index for transforms; just the two
neighbor arrays suffice for fitting but not for transforming new samples.

## Official sources reviewed

- [Release 0.5.12](https://github.com/lmcinnes/umap/releases/tag/release-0.5.12)
- [Core source](https://github.com/lmcinnes/umap/blob/release-0.5.12/umap/umap_.py), [aligned source](https://github.com/lmcinnes/umap/blob/release-0.5.12/umap/aligned_umap.py), [parametric source](https://github.com/lmcinnes/umap/blob/release-0.5.12/umap/parametric_umap.py)
- [Supervised UMAP](https://umap-learn.readthedocs.io/en/latest/supervised.html), [clustering](https://umap-learn.readthedocs.io/en/latest/clustering.html), [reproducibility](https://umap-learn.readthedocs.io/en/latest/reproducibility.html)
- [densMAP](https://umap-learn.readthedocs.io/en/latest/densmap_demo.html), [aligned mappings](https://umap-learn.readthedocs.io/en/latest/aligned_umap_politics_demo.html), [precomputed neighbors](https://umap-learn.readthedocs.io/en/latest/precomputed_k-nn.html)
- [HDBSCAN API](https://hdbscan.readthedocs.io/en/latest/api.html)
