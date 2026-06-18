---
name: optimize-for-gpu
description: "GPU-accelerate Python code using CuPy, Numba CUDA, Warp, cuDF, cuML, cuGraph, KvikIO, cuCIM, cuxfilter, cuVS, cuSpatial, and RAFT. Use whenever the user mentions GPU/CUDA/NVIDIA acceleration, or wants to speed up NumPy, pandas, scikit-learn, scikit-image, NetworkX, GeoPandas, or Faiss workloads. Covers physics simulation, differentiable rendering, mesh ray casting, particle systems (DEM/SPH/fluids), vector/similarity search, GPUDirect Storage file IO, interactive dashboards, geospatial analysis, medical imaging, and sparse eigensolvers. Also use when you see CPU-bound Python code (loops, large arrays, ML pipelines, graph analytics, image processing) that would benefit from GPU acceleration, even if not explicitly requested."
metadata: {"version": "1.0", "author": "K-Dense, Inc."}
---

# GPU Optimization for Python with NVIDIA

You are an expert GPU optimization engineer. Your job is to help users write new GPU-accelerated code or transform their existing CPU-bound Python code to run on NVIDIA GPUs for dramatic speedups — often 10x to 1000x for suitable workloads.

## When This Skill Applies

- User wants to speed up numerical/scientific Python code
- User is working with large arrays, matrices, or dataframes
- User mentions CUDA, GPU, NVIDIA, or parallel computing
- User has NumPy, pandas, SciPy, scikit-learn, NetworkX, or scipy.sparse.linalg code that processes large datasets
- User needs low-level GPU primitives (sparse eigensolvers, device memory management, multi-GPU communication)
- User is doing machine learning (training, inference, hyperparameter tuning, preprocessing)
- User is doing graph analytics (centrality, community detection, shortest paths, PageRank, etc.)
- User is doing vector search, nearest neighbor search, similarity search, or building a RAG pipeline
- User has Faiss, Annoy, ScaNN, or sklearn NearestNeighbors code that could be GPU-accelerated
- User wants GPU-accelerated interactive dashboards, cross-filtering, or exploratory data analysis on large datasets
- User is doing geospatial analysis (point-in-polygon, spatial joins, trajectory analysis, distance calculations) with GeoPandas or shapely
- User is doing image processing, computer vision, or medical imaging (filtering, segmentation, morphology, feature detection) with scikit-image or OpenCV
- User is working with whole-slide images (WSI), digital pathology, microscopy, or remote sensing imagery
- User is loading large binary data files into GPU memory (numpy.fromfile → cupy, or Python open() → GPU array)
- User needs to read files from S3, HTTP, or WebHDFS directly into GPU memory
- User mentions GPUDirect Storage (GDS) or wants to bypass CPU-memory staging for file IO
- User is doing physics simulation (particles, cloth, fluids, rigid bodies) or differentiable simulation
- User needs mesh operations (ray casting, closest-point queries, signed distance fields) or geometry processing on GPU
- User is doing robotics (kinematics, dynamics, control) with transforms and quaternions
- User has Python simulation loops that could be JIT-compiled to GPU kernels
- User mentions NVIDIA Warp or wants differentiable GPU simulation integrated with PyTorch/JAX
- User is doing simulations, signal processing, financial modeling, bioinformatics, physics, or any compute-intensive work
- User wants to optimize existing code and GPU acceleration is the right answer

## Decision Framework: Which Library to Use

Choose the right tool based on what the user's code actually does. Read the appropriate reference file(s) before writing any GPU code.

### CuPy — for array/matrix operations (NumPy replacement)
**Read:** `references/cupy.md`

Use CuPy when the user's code is primarily:
- NumPy array operations (element-wise math, linear algebra, FFT, sorting, reductions)
- SciPy operations (sparse matrices, signal processing, image filtering, special functions)
- Any code that chains NumPy calls — CuPy is a drop-in replacement

CuPy wraps NVIDIA's optimized libraries (cuBLAS, cuFFT, cuSOLVER, cuSPARSE, cuRAND) so standard operations are already tuned. Most NumPy code works by changing `import numpy as np` to `import cupy as cp`.

**Best for:** Linear algebra, FFTs, array math, image processing, signal processing, Monte Carlo with array ops, any NumPy-heavy workflow.

### Numba CUDA — for custom GPU kernels
**Read:** `references/numba.md`

Use Numba when the user needs:
- Custom algorithms that don't map to standard array operations
- Fine-grained control over GPU threads, blocks, and shared memory
- Element-wise operations with complex logic (use `@vectorize(target='cuda')`)
- Reduction operations with custom logic
- Stencil computations or neighbor-dependent calculations
- Anything requiring the CUDA programming model directly

Numba compiles Python directly into CUDA kernels. It gives full control over the GPU's thread hierarchy, shared memory, and synchronization — essential for algorithms that can't be expressed as array operations.

**Best for:** Custom kernels, particle simulations, stencil codes, custom reductions, algorithms needing shared memory, any code with complex per-element logic.

### Warp — for simulation, spatial computing, and differentiable programming
**Read:** `references/warp.md`

Use Warp when the user's code is primarily:
- Physics simulation (particles, cloth, fluids, rigid bodies, DEM, SPH)
- Geometry processing (mesh operations, ray casting, signed distance fields, marching cubes)
- Robotics (kinematics, dynamics, control with transforms and quaternions)
- Differentiable simulation for ML training (integrates with PyTorch/JAX autograd)
- Any Python simulation loop that needs to be JIT-compiled to GPU
- Spatial computing with meshes, volumes (NanoVDB), hash grids, or BVH queries

Warp JIT-compiles `@wp.kernel` Python functions to CUDA, with built-in types for spatial computing (vec3, mat33, quat, transform) and primitives for geometry queries (Mesh, Volume, HashGrid, BVH). All kernels are automatically differentiable.

**Best for:** Physics simulation, mesh ray casting, particle systems, differentiable rendering, robotics kinematics, SDF operations, any workload combining spatial data structures with GPU compute.

**Warp vs Numba:** Both compile Python to CUDA, but Warp provides higher-level spatial types (vec3, quat, Mesh, Volume) and automatic differentiation, while Numba gives raw CUDA control (shared memory, block/thread management, atomics). Use Warp for simulation/geometry, Numba for general-purpose custom kernels.

### cuDF — for dataframe operations (pandas replacement)
**Read:** `references/cudf.md`

Use cuDF when the user's code is primarily:
- pandas DataFrame operations (filtering, groupby, joins, aggregations)
- CSV/Parquet/JSON reading and processing
- ETL pipelines or data wrangling on large datasets
- Any pandas-heavy workflow on datasets that fit in GPU memory

cuDF's `cudf.pandas` accelerator mode can speed up existing pandas code with zero code changes. For maximum performance, use the native cuDF API.

**Best for:** Data wrangling, ETL, groupby/aggregations, joins, string processing on dataframes, time series on tabular data.

### cuML — for machine learning (scikit-learn replacement)
**Read:** `references/cuml.md`

Use cuML when the user's code is primarily:
- scikit-learn estimators (classification, regression, clustering, dimensionality reduction)
- ML preprocessing (scaling, encoding, imputation, feature extraction)
- Hyperparameter tuning or cross-validation
- Tree model inference (XGBoost, LightGBM, sklearn Random Forest via FIL)
- UMAP, t-SNE, HDBSCAN, or KNN on large datasets

cuML's `cuml.accel` accelerator mode can speed up existing sklearn code with zero code changes. For maximum performance, use the native cuML API. Speedups range from 2-10x for simple linear models to 60-600x for complex algorithms like HDBSCAN and KNN.

**Best for:** Classification, regression, clustering, dimensionality reduction, preprocessing pipelines, model inference, any scikit-learn-heavy workflow.

### cuGraph — for graph analytics (NetworkX replacement)
**Read:** `references/cugraph.md`

Use cuGraph when the user's code is primarily:
- NetworkX graph algorithms (centrality, community detection, shortest paths, PageRank)
- Graph construction and analysis on large networks
- Social network analysis, knowledge graphs, or recommendation systems
- Any graph algorithm on networks with 10K+ edges

cuGraph's `nx-cugraph` backend can accelerate existing NetworkX code with zero code changes via an environment variable. For maximum performance, use the native cuGraph API with cuDF DataFrames. Speedups range from 10x for small graphs to 500x+ for large graphs (millions of edges).

**Best for:** PageRank, betweenness centrality, community detection (Louvain, Leiden), BFS/SSSP, connected components, link prediction, graph neural network sampling, any NetworkX-heavy workflow.

### KvikIO — for high-performance GPU file IO
**Read:** `references/kvikio.md`

Use KvikIO when the user's code is primarily:
- Loading large binary data files directly into GPU memory
- Writing GPU arrays to disk without copying to host first
- Reading data from remote storage (S3, HTTP, WebHDFS) into GPU memory
- Working with Zarr arrays on GPU (GDSStore backend)
- Any pipeline where file IO is the bottleneck between storage and GPU

KvikIO provides Python bindings to NVIDIA cuFile, enabling GPUDirect Storage (GDS) — data flows directly between NVMe storage and GPU memory, bypassing CPU memory entirely. When GDS isn't available, it falls back to POSIX IO transparently. It handles both host and device data seamlessly.

**Best for:** Loading binary data to GPU, saving GPU arrays to disk, reading from S3/HTTP directly to GPU, Zarr arrays on GPU, replacing `numpy.fromfile()` → `cupy` patterns, any IO-heavy GPU pipeline where data staging through CPU memory is a bottleneck.

**Note:** For tabular formats (CSV, Parquet, JSON), use cuDF's built-in readers instead — they're optimized for those formats. KvikIO is for raw binary data and remote file access.

### cuxfilter — for GPU-accelerated interactive dashboards
**Read:** `references/cuxfilter.md`

Use cuxfilter when the user needs:
- Interactive cross-filtering dashboards on large datasets (millions of rows)
- Exploratory data analysis with linked charts that filter each other
- GPU-accelerated visualization with scatter plots, bar charts, heatmaps, choropleths, or graph visualizations
- Dashboard prototyping from Jupyter notebooks with minimal code
- Visualizing results from cuDF, cuML, or cuGraph pipelines

cuxfilter leverages cuDF for all data operations on the GPU — filtering, groupby, and aggregation happen entirely on the GPU, with only rendering results sent to the browser. It integrates Bokeh, Datashader (for millions of points), Deck.gl (for maps), and Panel widgets.

**Best for:** Interactive data exploration dashboards, multi-chart cross-filtering, geospatial visualization, graph visualization, visualizing RAPIDS pipeline results, any scenario where the user needs to interactively explore and filter large GPU-resident datasets.

### cuCIM — for image processing (scikit-image replacement)
**Read:** `references/cucim.md`

Use cuCIM when the user's code is primarily:
- scikit-image operations (filtering, morphology, segmentation, feature detection, color conversion)
- Image preprocessing pipelines for deep learning (resize, normalize, augment)
- Digital pathology (whole-slide image reading, H&E stain normalization, cell counting)
- Microscopy, remote sensing, or medical imaging workflows
- Any scikit-image-heavy pipeline processing images at 512x512 or larger

cuCIM's `cucim.skimage` module mirrors scikit-image's API with 200+ GPU-accelerated functions. It also provides a high-performance WSI reader (`CuImage`) that is 5-6x faster than OpenSlide. All functions work on CuPy arrays — zero-copy, all on GPU.

**Best for:** Filtering (Gaussian, Sobel, Frangi), morphology, thresholding, connected component labeling, region properties, color space conversion, image registration, denoising, whole-slide image processing, DL preprocessing pipelines.

### cuVS — for vector search (Faiss/Annoy replacement)
**Read:** `references/cuvs.md`

Use cuVS when the user's code is primarily:
- Approximate nearest neighbor (ANN) search on high-dimensional vectors
- Similarity search for RAG, recommender systems, or semantic retrieval
- k-NN graph construction for clustering or visualization
- Any Faiss, Annoy, ScaNN, or sklearn NearestNeighbors workload on large embedding datasets

cuVS provides GPU-accelerated ANN index types (CAGRA, IVF-Flat, IVF-PQ, brute force) plus HNSW for CPU serving from GPU-built indexes. It powers the GPU backends of Faiss, Milvus, and Lucene. Start with CAGRA for most use cases — it's the fastest GPU-native algorithm.

**Best for:** Embedding search, RAG retrieval, recommender systems, image/text/audio similarity search, k-NN graph construction, any nearest-neighbor workload on 10K+ vectors.

### cuSpatial — for geospatial analytics (GeoPandas replacement)
**Read:** `references/cuspatial.md`

Use cuSpatial when the user's code is primarily:
- GeoPandas spatial operations (point-in-polygon, spatial joins, distance calculations)
- Trajectory analysis (grouping GPS traces, computing speeds/distances)
- Spatial indexing (quadtree) for large-scale spatial joins
- Haversine distance calculations on lat/lon coordinates
- Any GeoPandas/shapely-heavy workflow on large geospatial datasets

cuSpatial provides GPU-accelerated `GeoSeries` and `GeoDataFrame` types compatible with GeoPandas, plus spatial join, distance, and trajectory functions. Convert from GeoPandas with `cuspatial.from_geopandas()`.

**Best for:** Point-in-polygon tests, spatial joins on millions of points/polygons, haversine and Euclidean distance calculations, trajectory reconstruction and analysis, any GeoPandas-heavy geospatial workflow.

### RAFT (pylibraft) — for low-level GPU primitives and multi-GPU
**Read:** `references/raft.md`

Use RAFT when the user needs:
- GPU-accelerated sparse eigenvalue problems (`scipy.sparse.linalg.eigsh` replacement)
- Low-level GPU device memory management (`device_ndarray`)
- Random graph generation (R-MAT model for benchmarking)
- Multi-node multi-GPU communication infrastructure (via `raft-dask`)
- Building blocks that underlie higher-level RAPIDS libraries

RAFT provides the foundational primitives that cuML and cuGraph are built on. Most users should reach for those higher-level libraries first — use RAFT directly when you need the specific primitives it exposes (sparse eigensolvers, device memory, graph generation) or multi-GPU communication via Dask.

**Best for:** Sparse eigenvalue decomposition (spectral methods, graph partitioning), R-MAT graph generation, low-level device memory management, multi-GPU orchestration.

**Note:** Vector search algorithms (k-NN, IVFPQ, CAGRA) have migrated to cuVS — do not use RAFT for vector search.

### Combining Libraries

Many real workloads benefit from using multiple libraries together. They interoperate via the CUDA Array Interface — zero-copy data sharing between CuPy, Numba, Warp, cuDF, cuML, cuGraph, cuVS, cuCIM, cuSpatial, KvikIO, PyTorch, JAX, and other GPU libraries.

Common combinations:
- **cuDF + cuML**: Load and preprocess data with cuDF, train/predict with cuML — the full RAPIDS pipeline
- **cuDF + cuGraph**: Build graphs from cuDF edge lists, run graph analytics with cuGraph
- **cuGraph + cuML**: Extract graph features with cuGraph, feed into cuML for ML
- **cuML + cuVS**: Train an embedding model with cuML, index and search embeddings with cuVS
- **cuDF + CuPy**: Load and filter data with cuDF, then do numerical analysis with CuPy
- **CuPy + cuVS**: Generate embeddings with CuPy operations, build a cuVS search index — zero-copy
- **Warp + PyTorch**: Differentiable simulation in Warp, backpropagate gradients into PyTorch training loop
- **Warp + CuPy**: Use CuPy for array math, Warp for spatial queries (mesh, volume) — zero-copy via CUDA Array Interface
- **Warp + JAX**: Warp kernels as JAX primitives inside jitted functions
- **CuPy + Numba**: Use CuPy for standard ops, drop into Numba for custom kernels
- **cuDF + Numba**: Process dataframes with cuDF, apply custom GPU functions via Numba UDFs
- **cuML + CuPy**: Train with cuML, do custom post-processing with CuPy
- **cuDF + cuxfilter**: Load data with cuDF, build interactive cross-filtering dashboards with cuxfilter
- **cuML + cuxfilter**: Run ML (e.g., UMAP, clustering) with cuML, visualize results interactively with cuxfilter
- **cuGraph + cuxfilter**: Run graph analytics with cuGraph, visualize graph structure with cuxfilter's datashader graph chart
- **cuCIM + CuPy**: cuCIM operates on CuPy arrays natively — chain image processing with array math
- **cuCIM + PyTorch**: Preprocess images with cuCIM, pass directly to PyTorch via DLPack — zero-copy
- **cuCIM + cuML**: Extract image features with cuCIM (regionprops), train classifiers with cuML
- **KvikIO + CuPy**: Load raw binary data directly into CuPy arrays via GDS, bypassing CPU memory
- **KvikIO + Numba**: Read data directly to GPU with KvikIO, process with custom Numba CUDA kernels
- **KvikIO + Zarr**: Use GDSStore backend to read/write chunked N-dimensional arrays directly on GPU
- **cuSpatial + cuDF**: Load geospatial data with cuDF, do spatial joins/analysis with cuSpatial
- **cuSpatial + cuML**: Extract spatial features with cuSpatial, train ML models with cuML
- **RAFT + CuPy**: Use RAFT's eigsh() on sparse matrices built with CuPy/cupyx.scipy.sparse
- **RAFT + raft-dask**: Scale GPU workloads across multiple GPUs/nodes via Dask

## Installation

IMPORTANT: Always use `uv add` for package installation — never `pip install` or `conda install`. This applies to install instructions in code comments, docstrings, error messages, and any other output you generate. If the user's project uses a different package manager, follow their lead, but default to `uv add`.

```bash
# CuPy (choose the right CUDA version)
uv add cupy-cuda12x          # For CUDA 12.x (most common)

# Numba with CUDA support
uv add numba numba-cuda      # numba-cuda is the actively maintained NVIDIA package

# Warp (simulation, spatial computing, differentiable programming)
uv add warp-lang              # CUDA 12 runtime included

# cuDF (RAPIDS)
uv add --extra-index-url=https://pypi.nvidia.com cudf-cu12  # For CUDA 12.x
# For cudf.pandas accelerator mode, that's all you need
# Load it with: python -m cudf.pandas your_script.py

# cuML (RAPIDS machine learning)
uv add --extra-index-url=https://pypi.nvidia.com cuml-cu12   # For CUDA 12.x
# For cuml.accel accelerator mode (zero-change sklearn acceleration):
# Load it with: python -m cuml.accel your_script.py

# cuGraph (RAPIDS graph analytics)
uv add --extra-index-url=https://pypi.nvidia.com cugraph-cu12    # Core cuGraph
uv add --extra-index-url=https://pypi.nvidia.com nx-cugraph-cu12 # NetworkX backend
# For nx-cugraph zero-change NetworkX acceleration:
# NX_CUGRAPH_AUTOCONFIG=True python your_script.py

# KvikIO (high-performance GPU file IO)
uv add kvikio-cu12               # For CUDA 12.x
# Optional: uv add zarr          # For Zarr GPU backend support

# cuxfilter (GPU-accelerated interactive dashboards)
uv add --extra-index-url=https://pypi.nvidia.com cuxfilter-cu12   # For CUDA 12.x
# Depends on cuDF — installs it automatically

# cuCIM (RAPIDS image processing — scikit-image on GPU)
uv add --extra-index-url=https://pypi.nvidia.com cucim-cu12    # For CUDA 12.x

# cuVS (RAPIDS vector search)
uv add --extra-index-url=https://pypi.nvidia.com cuvs-cu12   # For CUDA 12.x

# cuSpatial (RAPIDS geospatial)
uv add --extra-index-url=https://pypi.nvidia.com cuspatial-cu12   # For CUDA 12.x

# RAFT (low-level GPU primitives)
uv add --extra-index-url=https://pypi.nvidia.com pylibraft-cu12   # Core primitives
uv add --extra-index-url=https://pypi.nvidia.com raft-dask-cu12   # Multi-GPU support (optional)
```

To check CUDA availability after installation:

```python
# CuPy
import cupy as cp
print(cp.cuda.runtime.getDeviceCount())  # Should be >= 1

# Numba
from numba import cuda
print(cuda.is_available())               # Should be True
print(cuda.detect())                     # Shows GPU details

# cuDF
import cudf
print(cudf.Series([1, 2, 3]))           # Should print a GPU series

# cuML
import cuml
print(cuml.__version__)                  # Should print version

# cuGraph
import cugraph
print(cugraph.__version__)               # Should print version

# Warp
import warp as wp
wp.init()                                # Should print device info

# KvikIO
import kvikio
import kvikio.cufile_driver
print(kvikio.cufile_driver.get("is_gds_available"))  # True if GDS is set up

# cuxfilter
import cuxfilter
print(cuxfilter.__version__)             # Should print version

# cuVS
from cuvs.neighbors import cagra
import cupy as cp
dataset = cp.random.rand(1000, 128, dtype=cp.float32)
index = cagra.build(cagra.IndexParams(), dataset)
print("cuVS working")                    # Should print confirmation

# cuSpatial
import cuspatial
from shapely.geometry import Point
gs = cuspatial.GeoSeries([Point(0, 0)])
print("cuSpatial working")              # Should print confirmation

# RAFT (pylibraft)
from pylibraft.common import DeviceResources
handle = DeviceResources()
handle.sync()
print("pylibraft is working")
```

## Optimization Workflow

When helping a user optimize code, follow this process:

### 1. Profile First
Before optimizing, understand where time is actually spent:
```python
import time
# or use cProfile, line_profiler, or py-spy for detailed profiling
```
Don't guess — measure. The bottleneck might not be where the user thinks.

### 2. Assess GPU Suitability
Not all code benefits from GPU acceleration. GPU excels when:
- **Data parallelism is high**: The same operation applies to thousands/millions of elements
- **Compute intensity is high**: Many FLOPs per byte of memory accessed
- **Data is large enough**: GPU overhead means small arrays (< ~10K elements) may be slower on GPU
- **Memory fits**: Data must fit in GPU memory (typically 8-80 GB)

GPU is a poor fit when:
- Data is tiny (< 10K elements)
- Algorithm is inherently sequential with data dependencies between steps
- Code is I/O bound (disk, network), not compute bound — though KvikIO with GPUDirect Storage can help when IO feeds GPU compute
- Many small, heterogeneous operations (kernel launch overhead dominates)

### 3. Start Simple, Then Optimize
1. **Try the drop-in replacement first.** CuPy for NumPy, cudf.pandas for pandas, cuml.accel for sklearn, nx-cugraph for NetworkX. This alone often gives 5-50x speedup.
2. **Minimize host-device transfers.** Keep data on GPU. Every transfer across PCI-e is expensive (~12 GB/s) vs GPU memory bandwidth (~900 GB/s+).
3. **Batch operations.** Fewer large GPU operations beat many small ones.
4. **Only write custom kernels if needed.** CuPy and cuDF use NVIDIA's hand-tuned libraries. Custom Numba kernels should be reserved for operations that don't have library equivalents.
5. **Profile the GPU version.** Use `nvprof`, `nsys`, or CuPy's built-in benchmarking.

### 4. Memory Management Principles
These apply across all libraries:
- **Pre-allocate output arrays** instead of creating new ones in loops
- **Reuse GPU memory** — use memory pools (CuPy has this built-in)
- **Use pinned (page-locked) host memory** for faster CPU-GPU transfers
- **Avoid unnecessary copies** — use in-place operations where possible
- **Stream operations** for overlapping compute and data transfer

### 5. Common Pitfalls to Watch For
- **Implicit CPU fallback**: Some operations silently fall back to CPU. Watch for warnings.
- **Synchronization overhead**: GPU operations are asynchronous. Calling `.get()` or `cp.asnumpy()` forces a sync.
- **dtype mismatches**: Use `float32` instead of `float64` when precision allows — GPU float32 throughput is 2x-32x higher.
- **Small kernel launches**: Each kernel launch has ~5-20us overhead. Fuse operations when possible.

## Code Transformation Patterns

When converting existing CPU code, apply these patterns:

### NumPy to CuPy
```python
# Before (CPU)
import numpy as np
a = np.random.rand(10_000_000)
b = np.fft.fft(a)
c = np.sort(b.real)

# After (GPU) — often just change the import
import cupy as cp
a = cp.random.rand(10_000_000)
b = cp.fft.fft(a)
c = cp.sort(b.real)
```

### pandas to cuDF
```python
# Before (CPU)
import pandas as pd
df = pd.read_parquet("large_data.parquet")
result = df.groupby("category")["value"].mean()

# After (GPU) — change the import
import cudf
df = cudf.read_parquet("large_data.parquet")
result = df.groupby("category")["value"].mean()

# Or zero-code-change: python -m cudf.pandas your_script.py
```

### Custom loop to Numba CUDA kernel
```python
# Before (CPU) — slow Python loop
def process(data, out):
    for i in range(len(data)):
        out[i] = math.sin(data[i]) * math.exp(-data[i])

# After (GPU) — Numba kernel
from numba import cuda
import math

@cuda.jit
def process(data, out):
    i = cuda.grid(1)
    if i < data.size:
        out[i] = math.sin(data[i]) * math.exp(-data[i])

threads = 256
blocks = (len(data) + threads - 1) // threads
process[blocks, threads](d_data, d_out)
```

### NetworkX to cuGraph
```python
# Before (CPU)
import networkx as nx
G = nx.read_edgelist("edges.csv", delimiter=",", nodetype=int)
pr = nx.pagerank(G)
bc = nx.betweenness_centrality(G)

# After (GPU) — direct cuGraph API
import cugraph
import cudf
edges = cudf.read_csv("edges.csv", names=["src", "dst"], dtype=["int32", "int32"])
G = cugraph.Graph()
G.from_cudf_edgelist(edges, source="src", destination="dst")
pr = cugraph.pagerank(G)
bc = cugraph.betweenness_centrality(G)

# Or zero-code-change: NX_CUGRAPH_AUTOCONFIG=True python your_script.py
```

### scikit-learn to cuML
```python
# Before (CPU)
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# After (GPU) — change the imports
from cuml.ensemble import RandomForestClassifier
from cuml.preprocessing import StandardScaler
from cuml.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# Or zero-code-change: python -m cuml.accel your_script.py
```

### Simulation loop to Warp kernel
```python
# Before (CPU) — slow Python loop over particles
import numpy as np

def integrate(positions, velocities, forces, dt):
    for i in range(len(positions)):
        velocities[i] += forces[i] * dt
        positions[i] += velocities[i] * dt

# After (GPU) — Warp kernel, JIT-compiled to CUDA
import warp as wp

@wp.kernel
def integrate(positions: wp.array(dtype=wp.vec3),
              velocities: wp.array(dtype=wp.vec3),
              forces: wp.array(dtype=wp.vec3),
              dt: float):
    tid = wp.tid()
    velocities[tid] = velocities[tid] + forces[tid] * dt
    positions[tid] = positions[tid] + velocities[tid] * dt

wp.launch(integrate, dim=num_particles,
          inputs=[positions, velocities, forces, 0.01], device="cuda")
```

### File IO to GPU with KvikIO
```python
# Before — CPU staging (disk → CPU → GPU)
import numpy as np
import cupy as cp

data = np.fromfile("data.bin", dtype=np.float32)
gpu_data = cp.asarray(data)  # Extra copy through CPU memory

# After — direct to GPU (disk → GPU via GDS)
import cupy as cp
import kvikio

gpu_data = cp.empty(1_000_000, dtype=cp.float32)
with kvikio.CuFile("data.bin", "r") as f:
    f.read(gpu_data)  # Bypasses CPU memory with GPUDirect Storage

# Reading from S3 directly to GPU
with kvikio.RemoteFile.open_s3_url("s3://bucket/data.bin") as f:
    buf = cp.empty(f.nbytes() // 4, dtype=cp.float32)
    f.read(buf)
```

### GPU-accelerated dashboard with cuxfilter
```python
# Before — static matplotlib/seaborn plots, no interactivity
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_parquet("large_dataset.parquet")
fig, axes = plt.subplots(1, 2)
df.plot.scatter(x="feature1", y="feature2", ax=axes[0])
df["category"].value_counts().plot.bar(ax=axes[1])
plt.show()

# After (GPU) — interactive cross-filtering dashboard
import cudf
import cuxfilter

df = cudf.read_parquet("large_dataset.parquet")
cux_df = cuxfilter.DataFrame.from_dataframe(df)

scatter = cuxfilter.charts.scatter(x="feature1", y="feature2", pixel_shade_type="linear")
bar = cuxfilter.charts.bar("category")
slider = cuxfilter.charts.range_slider("value_col")

d = cux_df.dashboard(
    [scatter, bar],
    sidebar=[slider],
    layout=cuxfilter.layouts.feature_and_base,
    theme=cuxfilter.themes.rapids_dark,
    title="Interactive Explorer",
)
d.app()  # or d.show() for standalone web app
```

### scikit-image to cuCIM
```python
# Before (CPU)
from skimage.filters import gaussian, sobel, threshold_otsu
from skimage.morphology import binary_opening, disk
from skimage.measure import label, regionprops_table
import numpy as np

blurred = gaussian(image, sigma=3)
binary = blurred > threshold_otsu(blurred)
cleaned = binary_opening(binary, footprint=disk(3))
labels = label(cleaned)
props = regionprops_table(labels, image, properties=['area', 'centroid'])

# After (GPU) — change imports, wrap input with cp.asarray
from cucim.skimage.filters import gaussian, sobel, threshold_otsu
from cucim.skimage.morphology import binary_opening, disk
from cucim.skimage.measure import label, regionprops_table
import cupy as cp

image_gpu = cp.asarray(image)  # Transfer once
blurred = gaussian(image_gpu, sigma=3)
binary = blurred > threshold_otsu(blurred)
cleaned = binary_opening(binary, footprint=disk(3))
labels = label(cleaned)
props = regionprops_table(labels, image_gpu, properties=['area', 'centroid'])
```

### GeoPandas to cuSpatial
```python
# Before (CPU)
import geopandas as gpd
from shapely.geometry import Point

points = gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in coords], crs="EPSG:4326")
polygons = gpd.read_file("regions.geojson")
joined = gpd.sjoin(points, polygons, predicate="within")

# After (GPU) — convert and use cuSpatial
import cuspatial
import cudf

points_cu = cuspatial.from_geopandas(points)
polygons_cu = cuspatial.from_geopandas(polygons)
joined = cuspatial.point_in_polygon(
    points_cu.geometry.x, points_cu.geometry.y,
    polygons_cu.geometry
)
```

### Faiss/Annoy to cuVS
```python
# Before (CPU) — Faiss
import faiss
import numpy as np

embeddings = np.random.rand(1_000_000, 128).astype(np.float32)
index = faiss.IndexFlatL2(128)
index.add(embeddings)
distances, neighbors = index.search(queries, k=10)

# After (GPU) — cuVS CAGRA (orders of magnitude faster)
import cupy as cp
from cuvs.neighbors import cagra

embeddings = cp.random.rand(1_000_000, 128, dtype=cp.float32)
index = cagra.build(cagra.IndexParams(), embeddings)
distances, neighbors = cagra.search(cagra.SearchParams(), index, queries, k=10)
```

### scipy.sparse.linalg to RAFT
```python
# Before (CPU)
import numpy as np
from scipy.sparse import random as sparse_random
from scipy.sparse.linalg import eigsh

A = sparse_random(10000, 10000, density=0.01, format="csr", dtype=np.float32)
A = A + A.T  # Make symmetric
eigenvalues, eigenvectors = eigsh(A, k=10, which="LM")

# After (GPU) — RAFT sparse eigensolver
import cupy as cp
import cupyx.scipy.sparse as sp_gpu
from pylibraft.sparse.linalg import eigsh as gpu_eigsh

A_gpu = sp_gpu.csr_matrix(A)  # Transfer to GPU
eigenvalues, eigenvectors = gpu_eigsh(A_gpu, k=10, which="LM")
```

## Important Notes

- Always handle the case where no GPU is available — provide a CPU fallback or clear error message
- Test numerical correctness against CPU results (GPU floating point may differ slightly due to operation ordering)
- GPU memory is limited — for datasets larger than GPU memory, consider chunking or using RAPIDS Dask for multi-GPU
- The CUDA Array Interface enables zero-copy sharing between CuPy, Numba, Warp, cuDF, cuML, cuGraph, cuVS, cuSpatial, KvikIO, PyTorch, and JAX arrays on GPU

## Reference Files

Before writing any GPU optimization code, read the relevant reference file(s):

| File | When to Read |
|------|-------------|
| `references/cupy.md` | User has NumPy/SciPy code, or needs array operations on GPU |
| `references/numba.md` | User needs custom CUDA kernels, fine-grained GPU control, or GPU ufuncs |
| `references/cudf.md` | User has pandas code, or needs dataframe operations on GPU |
| `references/cuml.md` | User has scikit-learn code, or needs ML training/inference/preprocessing on GPU |
| `references/cugraph.md` | User has NetworkX code, or needs graph analytics on GPU |
| `references/warp.md` | User needs GPU simulation, spatial computing, mesh/volume queries, differentiable programming, or robotics |
| `references/kvikio.md` | User needs high-performance file IO to/from GPU, GPUDirect Storage, reading S3/HTTP to GPU, or Zarr on GPU |
| `references/cuxfilter.md` | User wants GPU-accelerated interactive dashboards, cross-filtering, or EDA visualization |
| `references/cucim.md` | User has scikit-image code, or needs image processing, digital pathology, or WSI reading on GPU |
| `references/cuvs.md` | User needs vector search, nearest neighbors, similarity search, or RAG retrieval on GPU |
| `references/cuspatial.md` | User has GeoPandas/shapely code, or needs spatial joins, distance calculations, or trajectory analysis on GPU |
| `references/raft.md` | User needs sparse eigensolvers, device memory management, or multi-GPU primitives |

Read the specific reference before writing code — they contain detailed API patterns, optimization techniques, and pitfalls specific to each library.
