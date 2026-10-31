# cuVS Reference

> Review: 2026-10-01. Code below is illustrative unless explicitly described as CPU-tested.
> GPU execution, performance, GDS, and multi-GPU behavior require validation on target hardware.

cuVS is NVIDIA's GPU-accelerated library for exact and approximate nearest-neighbor search, part
of the RAPIDS ecosystem. It provides CAGRA, IVF-Flat, IVF-PQ, brute-force, and CPU-serving
interoperability. Compare equal metrics and exactness requirements, validate ANN recall, and
benchmark build, search, transfer, and serialization costs separately.

> **Full documentation:** https://docs.nvidia.com/cuvs/home
> **Reviewed release source:** https://github.com/rapidsai/cuvs/tree/v26.08.00/python/cuvs/cuvs

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [When to Use cuVS](#when-to-use-cuvs)
3. [Index Selection Guide](#index-selection-guide)
4. [CAGRA — Graph-Based Index](#cagra)
5. [IVF-Flat — Inverted File Index](#ivf-flat)
6. [IVF-PQ — Compressed Inverted File Index](#ivf-pq)
7. [Brute Force — Exact Search](#brute-force)
8. [HNSW — CPU Search from GPU Index](#hnsw)
9. [Distance Metrics](#distance-metrics)
10. [Filtering](#filtering)
11. [Multi-GPU](#multi-gpu)
12. [Memory and Performance](#memory-and-performance)
13. [Interoperability](#interoperability)
14. [Common Patterns](#common-patterns)

---

## Installation and Setup

Use `uv add` in standalone examples; follow the user's existing project package manager when one
is already configured.

```bash
uv add --extra-index-url=https://pypi.nvidia.com "cuvs-cu12==26.8.*"   # For CUDA 12.x
uv add --extra-index-url=https://pypi.nvidia.com "cuvs-cu13==26.8.*"   # For CUDA 13.x
```

cuVS wheels (including the companion `libcuvs` wheel) are also published directly to PyPI, so the extra index is optional — but the official cuVS docs still show it and it does no harm.

**Platform:** Linux and WSL2 only (no native macOS or Windows).
**Requires:** NVIDIA GPU with CUDA 12.x or 13.x support, Python 3.11+, CuPy recommended for GPU arrays.

Verify:
```python
from cuvs.neighbors import cagra
import cupy as cp

dataset = cp.random.rand(1000, 128, dtype=cp.float32)
index = cagra.build(cagra.IndexParams(), dataset)
print("cuVS working — built CAGRA index")
```

---

## When to Use cuVS

cuVS is the right tool when the user needs:
- **Nearest neighbor search** on high-dimensional vectors (embeddings)
- **Similarity search** for RAG, recommender systems, image/text/audio retrieval
- **k-NN graph construction** for clustering or visualization pipelines
- **Vector database backends** — cuVS powers search in Milvus, Lucene, Kinetica, and Faiss GPU
- **Replacing Faiss, Annoy, ScaNN, or sklearn NearestNeighbors** with GPU acceleration

cuVS is NOT the right tool for:
- General machine learning (use cuML instead)
- Small or low-dimensional datasets where build, transfer, or launch overhead dominates in a
  representative benchmark
- CPU-only environments with no GPU available

---

## Index Selection Guide

| Index | Best For | Build Speed | Search Speed | Memory | Accuracy |
|-------|----------|-------------|--------------|--------|----------|
| **CAGRA** | Strong first ANN candidate | Fast | Fast | Medium | Tunable |
| **IVF-Flat** | High-recall ANN without vector compression | Medium | Fast | High (stores full vectors) | Tunable |
| **IVF-PQ** | Large datasets that don't fit in GPU memory | Medium | Fast | Low (compressed) | Good |
| **Brute Force** | Small datasets or ground truth | N/A | Slow at scale | High | Exact |
| **HNSW** | CPU-side serving from GPU-built index | Slow | Fast (CPU) | Medium | High |

Benchmark CAGRA as the first ANN candidate, then compare IVF-PQ when memory is tight and IVF-Flat
when avoiding vector compression matters. Use brute force for exact search and recall ground truth.
Choose build and search parameters from measured latency, throughput, memory, and recall targets.

---

## CAGRA

CAGRA (CUDA Accelerated Graph-based) is a graph-based ANN index optimized for GPU. Treat it as a strong ANN candidate and compare recall, memory, and end-to-end latency.

### Build

```python
import cupy as cp
from cuvs.neighbors import cagra

n_samples = 1_000_000
n_features = 128
dataset = cp.random.rand(n_samples, n_features, dtype=cp.float32)

# Default parameters work well for most cases
index_params = cagra.IndexParams(
    metric="sqeuclidean",             # "sqeuclidean", "inner_product", "cosine"
    intermediate_graph_degree=128,     # Higher = better quality, slower build
    graph_degree=64,                   # Final graph degree (lower = less memory)
    build_algo="ivf_pq",              # "ivf_pq", "nn_descent", "iterative_cagra_search", or "ace"
)

index = cagra.build(index_params, dataset)
```

### Search

```python
from cuvs.common import Resources

queries = cp.random.rand(1000, n_features, dtype=cp.float32)

search_params = cagra.SearchParams(
    itopk_size=64,       # Intermediate top-k (higher = more accurate, slower)
    search_width=1,      # Starting nodes per iteration
    max_iterations=0,    # 0 = auto
    algo="auto",         # "auto", "single_cta", "multi_cta", "multi_kernel"
)

resources = Resources()
distances, neighbors = cagra.search(
    search_params, index, queries, k=10, resources=resources
)
resources.sync()

# distances: shape (1000, 10) — squared Euclidean distances
# neighbors: shape (1000, 10) — indices into original dataset
```

### Save / Load

Persist the exact cuVS release, dtype, metric and dataset identity alongside the index.
Serialized formats are experimental and not guaranteed portable across releases.

```python
cagra.save("my_index.cagra", index)
loaded_index = cagra.load("my_index.cagra")
```

### Extend

```python
new_data = cp.random.rand(10_000, n_features, dtype=cp.float32)
extended_index = cagra.extend(cagra.ExtendParams(), index, new_data)
```

### With Compression (for large datasets)

```python
from cuvs.neighbors.cagra import CompressionParams

index_params = cagra.IndexParams(
    compression=CompressionParams(
        pq_bits=8,
        pq_dim=64,
    )
)
index = cagra.build(index_params, dataset)
```

---

## IVF-Flat

IVF-Flat partitions the dataset into clusters (inverted file) and stores full vectors. Higher accuracy than IVF-PQ but uses more memory.

### Build

```python
from cuvs.neighbors import ivf_flat

build_params = ivf_flat.IndexParams(
    n_lists=1024,                    # Number of clusters (sqrt(n_samples) is a good start)
    metric="sqeuclidean",            # "sqeuclidean", "euclidean", "inner_product", "cosine"
    kmeans_trainset_fraction=0.5,    # Fraction of data used for k-means training
    kmeans_n_iters=20,               # K-means iterations
    add_data_on_build=True,          # Add vectors during build (vs. extend later)
)

index = ivf_flat.build(build_params, dataset)
```

### Search

```python
search_params = ivf_flat.SearchParams(
    n_probes=50,    # Clusters to search (higher = more accurate, slower)
)

distances, neighbors = ivf_flat.search(
    search_params, index, queries, k=10
)
```

### Save / Load / Extend

```python
ivf_flat.save("my_index.ivf_flat", index)
loaded_index = ivf_flat.load("my_index.ivf_flat")

# Extend with new data
import numpy as np
new_vectors = cp.random.rand(5000, n_features, dtype=cp.float32)
new_indices = cp.arange(n_samples, n_samples + 5000, dtype=cp.int64)
ivf_flat.extend(index, new_vectors, new_indices)
```

---

## IVF-PQ

IVF-PQ compresses vectors using product quantization, dramatically reducing memory usage. Best for large datasets that don't fit in GPU memory with full vectors.

### Build

```python
from cuvs.neighbors import ivf_pq

build_params = ivf_pq.IndexParams(
    n_lists=1024,                # Number of clusters
    metric="sqeuclidean",        # "sqeuclidean", "inner_product"
    pq_bits=8,                   # Bits per subquantizer (4 or 8)
    pq_dim=0,                    # PQ dimensions (0 = auto, typically dim/4)
    codebook_kind="subspace",    # "subspace" or "cluster"
    kmeans_n_iters=20,
    add_data_on_build=True,
)

index = ivf_pq.build(build_params, dataset)
```

### Search

```python
search_params = ivf_pq.SearchParams(
    n_probes=50,                     # Clusters to search
    lut_dtype="float32",             # Look-up table precision
    internal_distance_dtype="float32",
)

distances, neighbors = ivf_pq.search(
    search_params, index, queries, k=10
)
```

### Save / Load / Extend

```python
ivf_pq.save("my_index.ivf_pq", index)
loaded_index = ivf_pq.load("my_index.ivf_pq")

# Extend
new_vectors = cp.random.rand(5000, n_features, dtype=cp.float32)
new_indices = cp.arange(n_samples, n_samples + 5000, dtype=cp.int64)
ivf_pq.extend(index, new_vectors, new_indices)
```

---

## Brute Force

Exact k-NN search — computes all distances. Use for small datasets (< 50K vectors) or generating ground truth to evaluate approximate indexes.

```python
from cuvs.neighbors import brute_force

# Build (just stores the dataset)
index = brute_force.build(dataset, metric="sqeuclidean")

# Search
distances, neighbors = brute_force.search(index, queries, k=10)

# Save / Load
brute_force.save("bf_index.bin", index)
loaded = brute_force.load("bf_index.bin")
```

---

## HNSW

cuVS provides an HNSW implementation for CPU-side search. The typical workflow is: build a CAGRA index on GPU, convert it to HNSW for CPU serving. This lets you leverage GPU speed for building while serving from CPU (useful when GPU isn't available at query time).

```python
from cuvs.neighbors import cagra, hnsw
import numpy as np

# Build CAGRA on GPU
dataset_gpu = cp.random.rand(100_000, 128, dtype=cp.float32)
cagra_index = cagra.build(cagra.IndexParams(), dataset_gpu)

# Convert to HNSW for CPU search
hnsw_index = hnsw.from_cagra(hnsw.IndexParams(), cagra_index)

# Search on CPU with numpy queries
queries_cpu = np.random.rand(100, 128).astype(np.float32)
search_params = hnsw.SearchParams(
    ef=200,           # Search depth (higher = more accurate, slower)
    num_threads=0,    # 0 = auto (uses all available threads)
)
distances, neighbors = hnsw.search(search_params, hnsw_index, queries_cpu, k=10)

# Save / Load
hnsw.save("my_index.hnsw", hnsw_index)
loaded = hnsw.load(hnsw.IndexParams(), "my_index.hnsw", dim=128,
                    dtype=np.float32, metric="sqeuclidean")
```

### Extendable HNSW

To add vectors after building, use `hierarchy="cpu"`:

```python
hnsw_index = hnsw.from_cagra(hnsw.IndexParams(hierarchy="cpu"), cagra_index)

new_data = np.random.rand(5000, 128).astype(np.float32)
hnsw.extend(hnsw.ExtendParams(), hnsw_index, new_data)
```

---

## Distance Metrics

| Metric | String | Notes |
|--------|--------|-------|
| Squared Euclidean | `"sqeuclidean"` | Default. Fastest — avoids sqrt. |
| Euclidean | `"euclidean"` | L2 distance |
| Inner Product | `"inner_product"` | For normalized embeddings (cosine similarity via dot product) |
| Cosine | `"cosine"` | Supported by CAGRA and IVF-Flat |

For cosine similarity with IVF-PQ, normalize vectors to unit length and use `"inner_product"`.

---

## Filtering

cuVS supports pre-filtering search results using bitmaps or bitsets to exclude specific vectors.

```python
import numpy as np
import cupy as cp
from cuvs.neighbors import brute_force, filters

def pack_allowed_mask(allowed):
    """Pack sample inclusion flags into little-endian uint32 words."""
    allowed = np.asarray(allowed, dtype=np.bool_)
    if allowed.ndim != 1:
        raise ValueError("Expected one inclusion flag per indexed vector")
    padded = np.pad(allowed, (0, (-allowed.size) % 32), constant_values=False)
    return np.packbits(padded, bitorder="little").view("<u4").astype(np.uint32)

# 1 = allowed, 0 = excluded. One packed bit per indexed vector, NOT one byte.
allowed = np.ones(dataset.shape[0], dtype=np.bool_)
allowed[:1000] = False
bitset = cp.asarray(pack_allowed_mask(allowed))
prefilter = filters.from_bitset(bitset)
distances, neighbors = brute_force.search(index, queries, k=10, prefilter=prefilter)
```

CAGRA uses `filter=prefilter` rather than `prefilter=`. Keep the bitset/filter alive until
search completes; validate sentinel results if fewer than k candidates survive.
`pack_allowed_mask` is CPU-tested; the filtered GPU search remains illustrative.

---

## Multi-GPU

For datasets too large for a single GPU, use the multi-GPU API:

```python
from cuvs.neighbors.mg import cagra as mg_cagra

# Build across all available GPUs
build_params = mg_cagra.IndexParams(
    intermediate_graph_degree=64,
    graph_degree=32,
)
dataset_host = cp.asnumpy(dataset)  # MG CAGRA requires host input
queries_host = cp.asnumpy(queries)
index = mg_cagra.build(build_params, dataset_host)

# Search across GPUs
search_params = mg_cagra.SearchParams()
distances, neighbors = mg_cagra.search(search_params, index, queries_host, k=10)
```

Multi-GPU is also available for IVF-Flat and IVF-PQ via `cuvs.neighbors.mg`.

---

## Memory and Performance

### Supported Data Types

Dtypes are index-specific. Brute force accepts float32/float16; do not assume the int8/uint8 support of CAGRA or IVF-Flat applies to every index or metric.

Using `float16` halves memory and can speed up both build and search when full float32 precision isn't needed (common for embeddings).

### Performance Tips

1. **Use CuPy arrays as input.** NumPy arrays work but trigger a CPU-to-GPU transfer. If your vectors are already on GPU (from a model or pipeline), pass them directly.

2. **Tune search parameters, not just build parameters.** The biggest accuracy/speed tradeoff is at search time:
   - CAGRA: increase `itopk_size` (default 64)
   - IVF-Flat/IVF-PQ: increase `n_probes` (default 20)
   - HNSW: increase `ef` (default 200)

3. **Evaluate reduced precision, do not assume it is free.** If the chosen index supports float16,
compare recall/ranking metrics and end-to-end performance with float32 before changing storage.

4. **n_lists tuning for IVF indexes.** A good starting point is `sqrt(n_samples)`. Too few lists = slow search, too many = poor recall.

5. **Batch queries.** GPU throughput scales with batch size. Searching 1000 queries at once is far more efficient than 1000 individual searches.

6. **Reuse the Resources handle.** Create one `Resources()` object and pass it to all build/search calls — it manages CUDA streams and memory.

### Memory Estimates

- **Brute force:** `n_samples * dim * dtype_size` (full dataset)
- **IVF-Flat:** Similar to brute force + cluster overhead
- **IVF-PQ:** `n_samples * pq_dim * pq_bits / 8` (heavily compressed)
- **CAGRA:** `n_samples * (dim * dtype_size + graph_degree * 4)` (dataset + graph)

---

## Interoperability

- **CuPy:** Native input — zero-copy via `__cuda_array_interface__`
- **NumPy:** Accepted as input (auto-transferred to GPU for GPU indexes, used directly for HNSW)
- **PyTorch / TensorFlow:** Use a supported array-interface or DLPack conversion (e.g. to CuPy), preserving device, layout, ownership and stream ordering.
- **cuDF:** Convert columns to CuPy with `.values` before passing to cuVS
- **Faiss:** cuVS powers Faiss GPU under the hood; for direct use, cuVS gives more control
- **Vector databases:** cuVS is integrated into Milvus, Lucene, and Kinetica

### End-to-End RAG Pipeline Example

```python
import cupy as cp
from cuvs.neighbors import cagra

# Assume embeddings come from a model (e.g., sentence-transformers on GPU)
document_embeddings = cp.array(embeddings, dtype=cp.float32)  # (n_docs, 768)

# Build index
index_params = cagra.IndexParams(metric="inner_product")
index = cagra.build(index_params, document_embeddings)
cagra.save("doc_index.cagra", index)

# At query time
query_embedding = cp.array(encode("user question"), dtype=cp.float32).reshape(1, -1)
search_params = cagra.SearchParams(itopk_size=128)
distances, neighbors = cagra.search(search_params, index, query_embedding, k=20)

# neighbors[0] contains the indices of the top-20 most similar documents
top_doc_ids = cp.asnumpy(cp.asarray(neighbors)[0])  # Transfer to CPU
```

---

## Common Patterns

### Pattern 1: Quick ANN Search (CAGRA)

```python
import cupy as cp
from cuvs.neighbors import cagra

dataset = cp.random.rand(500_000, 128, dtype=cp.float32)
queries = cp.random.rand(1000, 128, dtype=cp.float32)

index = cagra.build(cagra.IndexParams(), dataset)
distances, neighbors = cagra.search(cagra.SearchParams(), index, queries, k=10)
```

### Pattern 2: Memory-Efficient Search (IVF-PQ)

```python
import cupy as cp
from cuvs.neighbors import ivf_pq

dataset = cp.random.rand(10_000_000, 256, dtype=cp.float32)

# PQ compresses vectors — uses ~32x less memory than brute force
params = ivf_pq.IndexParams(n_lists=4096, pq_bits=8, pq_dim=64)
index = ivf_pq.build(params, dataset)

search_params = ivf_pq.SearchParams(n_probes=100)
distances, neighbors = ivf_pq.search(search_params, index, queries, k=10)
```

### Pattern 3: GPU Build, CPU Serve (CAGRA → HNSW)

```python
import cupy as cp
import numpy as np
from cuvs.neighbors import cagra, hnsw

# Build on GPU (fast)
dataset = cp.random.rand(1_000_000, 128, dtype=cp.float32)
gpu_index = cagra.build(cagra.IndexParams(), dataset)

# Convert to HNSW for CPU serving
cpu_index = hnsw.from_cagra(hnsw.IndexParams(), gpu_index)
hnsw.save("serving_index.hnsw", cpu_index)

# At serving time (no GPU needed)
loaded = hnsw.load(hnsw.IndexParams(), "serving_index.hnsw",
                    dim=128, dtype=np.float32)
queries = np.random.rand(100, 128).astype(np.float32)
distances, neighbors = hnsw.search(
    hnsw.SearchParams(ef=200), loaded, queries, k=10
)
```

### Pattern 4: Validate with Brute Force

```python
from cuvs.neighbors import brute_force, cagra

# Ground truth
bf_index = brute_force.build(dataset)
gt_distances, gt_neighbors = brute_force.search(bf_index, queries, k=10)

# Approximate
cagra_index = cagra.build(cagra.IndexParams(), dataset)
approx_distances, approx_neighbors = cagra.search(
    cagra.SearchParams(), cagra_index, queries, k=10
)

# Materialize once; default cuVS output containers need not be CuPy arrays.
gt_neighbors_cpu = cp.asnumpy(cp.asarray(gt_neighbors))
approx_neighbors_cpu = cp.asnumpy(cp.asarray(approx_neighbors))
# Ties can admit multiple exact top-k sets; decide a tie policy for duplicate vectors.
recall = sum(
    len(set(gt_neighbors_cpu[i]) & set(approx_neighbors_cpu[i])) / 10
    for i in range(len(queries))
) / len(queries)
print(f"Recall@10: {recall:.4f}")
```

### Pattern 5: Cosine Similarity Search

```python
import cupy as cp
from cuvs.neighbors import cagra

# Normalize embeddings to unit length
embeddings = cp.random.rand(100_000, 768, dtype=cp.float32)
norms = cp.linalg.norm(embeddings, axis=1, keepdims=True)
if bool(cp.any(norms == 0)):
    raise ValueError("Cosine similarity is undefined for zero-norm embeddings")
embeddings_normalized = embeddings / norms

# Use inner_product on normalized vectors = cosine similarity
index = cagra.build(
    cagra.IndexParams(metric="inner_product"),
    embeddings_normalized,
)

query = cp.random.rand(1, 768, dtype=cp.float32)
query_norm = cp.linalg.norm(query)
if float(query_norm) == 0:
    raise ValueError("Cosine similarity is undefined for a zero-norm query")
query_normalized = query / query_norm

distances, neighbors = cagra.search(
    cagra.SearchParams(), index, query_normalized, k=10
)
```

---

## Beyond Neighbors: Clustering, Distance, and Preprocessing

cuVS also provides GPU-accelerated clustering, pairwise distance, and quantization — useful building blocks in vector search pipelines.

### K-Means Clustering

```python
import cupy as cp
from cuvs.cluster.kmeans import fit, predict, KMeansParams

X = cp.random.rand(100_000, 128, dtype=cp.float32)

params = KMeansParams(
    n_clusters=256,
    init_method="KMeansPlusPlus",   # or "Random", "Array"
    max_iter=300,
    tol=1e-4,
)
centroids, inertia, n_iter = fit(params, X)
labels, inertia = predict(params, X, centroids)
```

For host-resident datasets, `device_buffer_samples` bounds the device staging batch in 26.08.
This still requires enough host RAM for the NumPy input:

```python
import numpy as np
from cuvs.cluster.kmeans import fit, KMeansParams

X_host = np.random.rand(10_000_000, 128).astype(np.float32)
params = KMeansParams(n_clusters=1000, device_buffer_samples=1_000_000)
centroids, inertia, n_iter = fit(params, X_host)
```

### Pairwise Distance

```python
from cuvs.distance import pairwise_distance

# Supports: euclidean, l2, l1, inner_product, cosine, chebyshev,
# canberra, hellinger, jensenshannon, kl_divergence, correlation, minkowski
output = pairwise_distance(X, Y, metric="euclidean")
```

### Quantization (Preprocessing)

Quantization compresses vectors before indexing, reducing memory and often improving search throughput.

**Scalar quantization** (float32 → int8):
```python
from cuvs.preprocessing.quantize import scalar

params = scalar.QuantizerParams(quantile=0.99)
quantizer = scalar.train(params, dataset)
transformed = scalar.transform(quantizer, dataset)       # int8
reconstructed = scalar.inverse_transform(quantizer, transformed)
```

**Binary quantization** (float32 → uint8 bitpacked):
```python
from cuvs.preprocessing.quantize import binary

transformed = binary.transform(dataset)  # uint8
# Use with metric="bitwise_hamming"
```

**Product quantization**:
```python
from cuvs.preprocessing.quantize import pq

params = pq.QuantizerParams(pq_bits=8, pq_dim=16)
quantizer = pq.build(params, dataset)
transformed, _ = pq.transform(quantizer, dataset)        # uint8
reconstructed = pq.inverse_transform(quantizer, transformed)
```

### PCA (Preprocessing)

GPU-accelerated PCA for dimensionality reduction before indexing (added in 26.06):

```python
import cupy as cp
from cuvs.preprocessing import pca

X = cp.random.random_sample((500, 32), dtype=cp.float32)
params = pca.Params(n_components=8, copy=True)
result = pca.fit(params, X)
transformed = pca.transform(params, X, result.components,
                            result.singular_vals, result.mu)
reconstructed = pca.inverse_transform(
    params, transformed, result.components,
    result.singular_vals, result.mu)
```

### NN-Descent (k-NN Graph Construction)

Builds an all-neighbors k-NN graph — useful as input to UMAP, t-SNE, or graph-based clustering.

```python
import cupy as cp
from cuvs.neighbors import nn_descent

dataset = cp.random.rand(100_000, 128, dtype=cp.float32)

build_params = nn_descent.IndexParams(
    metric="sqeuclidean",
    graph_degree=64,
    intermediate_graph_degree=96,   # >= 1.5 * graph_degree
    max_iterations=20,
)
index = nn_descent.build(build_params, dataset)
graph = index.graph  # (n_samples, graph_degree) — the k-NN graph
```
