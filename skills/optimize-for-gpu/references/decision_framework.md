# Decision Framework: Which Library to Use

Each RAPIDS/GPU library, the CPU library it replaces, what it is good at, and when it is
the wrong choice — CuPy, Numba CUDA, Warp, cuDF, cuML, cuGraph, KvikIO, cuxfilter, cuCIM,
cuVS, cuSpatial, and RAFT — plus guidance on combining them.

Choose the right tool based on what the user's code actually does. Read the appropriate reference file(s) before writing any GPU code.

First decide whether a port is justified: establish an end-to-end baseline, estimate peak device
memory including temporaries, and identify transfer and fallback boundaries. Prefer an accelerator
or backend mode before a native rewrite, and prefer a maintained library operation before a custom
kernel. Validate output semantics and use synchronized GPU timing on representative data.

### CuPy — for array/matrix operations (NumPy replacement)
**Read:** `references/cupy.md`

Use CuPy when the user's code is primarily:
- NumPy array operations (element-wise math, linear algebra, FFT, sorting, reductions)
- SciPy operations (sparse matrices, signal processing, image filtering, special functions)
- Compatible chains of numeric NumPy calls — check CuPy coverage and semantics before porting

CuPy wraps NVIDIA's optimized libraries (cuBLAS, cuFFT, cuSOLVER, cuSPARSE, cuRAND) so standard operations are already tuned. Many numeric operations have matching names; unsupported dtypes, argument differences, and transfer boundaries still need review.

**Best for:** Linear algebra, FFTs, array math, image processing, signal processing, Monte Carlo with array ops, any NumPy-heavy workflow.

### Numba-CUDA-MLIR / Numba-CUDA — for custom GPU kernels
**Read:** `references/numba.md`

Use this path when the user needs:
- Custom algorithms that don't map to standard array operations
- Fine-grained control over GPU threads, blocks, and shared memory
- Reduction operations with custom logic
- Stencil computations or neighbor-dependent calculations
- Anything requiring the CUDA programming model directly

For new projects, evaluate **Numba-CUDA-MLIR**, where NVIDIA is doing new feature development.
Use the established `numba-cuda` package for existing `numba.cuda` code, compatibility, or features
not yet available in the MLIR implementation; it is in maintenance mode through the CUDA 13
lifetime. Do not invest in custom kernels until profiling rules out CuPy or another tuned library.

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

Warp JIT-compiles `@wp.kernel` Python functions to CUDA, with built-in types for spatial computing
(vec3, mat33, quat, transform) and primitives for geometry queries (Mesh, Volume, HashGrid, BVH).
Warp can generate adjoint kernels for differentiable programs. The higher-level `warp.sim` module
was removed in Warp 1.10; use the separate **Newton** engine for maintained high-level rigid-body,
robotics, and simulation-environment APIs, and use Warp for custom kernels and domain primitives.

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

Start with cuML's `cuml.accel` accelerator mode when compatibility permits. Move to the native
cuML API for unsupported estimators, explicit output control, or a measured performance reason.
Benchmark the user's estimator, dimensions, and end-to-end pipeline rather than relying on headline
speedup ranges.

**Best for:** Classification, regression, clustering, dimensionality reduction, preprocessing pipelines, model inference, any scikit-learn-heavy workflow.

### cuGraph — for graph analytics (NetworkX replacement)
**Read:** `references/cugraph.md`

Use cuGraph when the user's code is primarily:
- NetworkX graph algorithms (centrality, community detection, shortest paths, PageRank)
- Graph construction and analysis on large networks
- Social network analysis, knowledge graphs, or recommendation systems
- Supported graph algorithms with enough repeated work to amortize conversion

Start with the `nx-cugraph` backend and inspect fallback behavior. Move to the native cuGraph API
with cuDF edge lists for unsupported operations or a measured performance reason. Include graph
construction and host-device conversion in end-to-end benchmarks.

**Best for:** PageRank, betweenness centrality, community detection (Louvain, Leiden), BFS/SSSP, connected components, link prediction, graph neural network sampling, any NetworkX-heavy workflow.

### KvikIO — for high-performance GPU file IO
**Read:** `references/kvikio.md`

Use KvikIO when the user's code is primarily:
- Loading large binary data files directly into GPU memory
- Writing GPU arrays to disk without copying to host first
- Reading data from remote storage (S3, HTTP, WebHDFS) into GPU memory
- Working with Zarr arrays on GPU (GDSStore backend)
- Any pipeline where file IO is the bottleneck between storage and GPU

KvikIO can use cuFile/GDS for eligible local I/O. Compatibility mode and unsupported configurations stage through host memory. RemoteFile uses HTTP/libcurl and host bounce buffers; accepting a GPU destination does not mean network-to-GPU GDS.

**Best for:** Loading binary data to GPU, saving GPU arrays to disk, reading S3/HTTP objects into device buffers, Zarr arrays on GPU, replacing `numpy.fromfile()` → `cupy` patterns, any IO-heavy GPU pipeline where data staging through CPU memory is a bottleneck.

**Note:** For tabular formats (CSV, Parquet, JSON), use cuDF's built-in readers instead — they're optimized for those formats. KvikIO is for raw binary data and remote file access.

### cuxfilter — legacy dashboards only
**Read:** `references/cuxfilter.md`

**Project status: sunset.** RAPIDS 26.06 was cuxfilter's final release (RSN 60). Reach
for cuxfilter only when the user already uses it or explicitly requests it. For new dashboards,
prefer cuDF for GPU data prep combined with HoloViews/hvPlot/Datashader linked selections, served
with Panel, Plotly Dash, Streamlit, or Bokeh.

Maintain cuxfilter when an existing application needs:
- Interactive cross-filtering dashboards on large datasets (millions of rows)
- Exploratory data analysis with linked charts that filter each other
- GPU-accelerated visualization with scatter plots, bar charts, heatmaps, choropleths, or graph visualizations
- Dashboard prototyping from Jupyter notebooks with minimal code
- Visualizing results from cuDF, cuML, or cuGraph pipelines

cuxfilter leverages cuDF for all data operations on the GPU — filtering, groupby, and aggregation happen entirely on the GPU, with only rendering results sent to the browser. It integrates Bokeh, Datashader (for millions of points), Deck.gl (for maps), and Panel widgets.

**Best for:** Existing 26.06 applications that cannot yet migrate. Do not start a new dependency on
an unmaintained dashboard framework.

### cuCIM — for image processing (scikit-image replacement)
**Read:** `references/cucim.md`

Use cuCIM when the user's code is primarily:
- scikit-image operations (filtering, morphology, segmentation, feature detection, color conversion)
- Image preprocessing pipelines for deep learning (resize, normalize, augment)
- Digital pathology (whole-slide image reading, H&E stain normalization, cell counting)
- Microscopy, remote sensing, or medical imaging workflows
- scikit-image-heavy pipelines whose measured hot path has cuCIM coverage

cuCIM provides a substantial subset of scikit-image and a WSI reader (`CuImage`). Some operations return Python scalars, tuples, dictionaries, or region objects and may synchronize; array outputs and zero-copy behavior are operation-specific.

**Best for:** Filtering (Gaussian, Sobel, Frangi), morphology, thresholding, connected component labeling, region properties, color space conversion, image registration, denoising, whole-slide image processing, DL preprocessing pipelines.

### cuVS — for vector search (Faiss/Annoy replacement)
**Read:** `references/cuvs.md`

Use cuVS when the user's code is primarily:
- Approximate nearest neighbor (ANN) search on high-dimensional vectors
- Similarity search for RAG, recommender systems, or semantic retrieval
- k-NN graph construction for clustering or visualization
- Any Faiss, Annoy, ScaNN, or sklearn NearestNeighbors workload on large embedding datasets

cuVS provides GPU-accelerated ANN index types (CAGRA, IVF-Flat, IVF-PQ, brute force) plus HNSW for CPU serving from GPU-built indexes. It powers the GPU backends of Faiss, Milvus, and Lucene. Evaluate CAGRA as one ANN candidate and select by measured recall, memory, and latency.

**Best for:** Embedding search, RAG retrieval, recommender systems, image/text/audio similarity search, k-NN graph construction, nearest-neighbor workloads that justify index build and transfer costs.

### cuSpatial — archived geospatial pipelines only
**Read:** `references/cuspatial.md`

**Project status: archived.** The cuSpatial repository has been read-only since July 2025; the final release is 25.04, which pins `cudf-cu12==25.4.*` and therefore conflicts with current RAPIDS releases in the same environment. No official successor exists. Recommend it only in a dedicated legacy environment; otherwise keep geometry operations on GeoPandas/Shapely (CPU) and accelerate the tabular parts of the workflow with cuDF.

Maintain cuSpatial when an isolated 25.04 environment already uses:
- GeoPandas spatial operations (point-in-polygon, spatial joins, distance calculations)
- Trajectory analysis (grouping GPS traces, computing speeds/distances)
- Spatial indexing (quadtree) for large-scale spatial joins
- Haversine distance calculations on lat/lon coordinates
- Any GeoPandas/shapely-heavy workflow on large geospatial datasets

cuSpatial provides GPU-accelerated `GeoSeries` and `GeoDataFrame` types compatible with GeoPandas, plus spatial join, distance, and trajectory functions. Convert from GeoPandas with `cuspatial.from_geopandas()`.

**Best for:** Existing pipelines pinned to the 25.04 stack. Do not present it as a current
GeoPandas replacement or combine it with current RAPIDS packages.

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

Many real workloads benefit from using multiple libraries together. Many support the CUDA Array Interface or DLPack. Check the exact producer/consumer: dataframe conversion, dtype/layout changes, and cross-device movement may allocate or copy; JAX/TensorFlow generally need DLPack rather than assuming a CUDA Array Interface.

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
- **cuDF + cuxfilter (legacy 26.06 only)**: Maintain an existing cross-filtering dashboard
- **cuML + cuxfilter (legacy 26.06 only)**: Maintain an existing ML visualization workflow
- **cuGraph + cuxfilter (legacy 26.06 only)**: Maintain an existing graph visualization
- **cuCIM + CuPy**: cuCIM operates on CuPy arrays natively — chain image processing with array math
- **cuCIM + PyTorch**: Preprocess images with cuCIM, pass directly to PyTorch via DLPack — zero-copy
- **cuCIM + cuML**: Extract image features with cuCIM (regionprops), train classifiers with cuML
- **KvikIO + CuPy**: Load raw binary data directly into CuPy arrays via GDS, bypassing CPU memory
- **KvikIO + Numba**: Read data directly to GPU with KvikIO, process with custom Numba CUDA kernels
- **KvikIO + Zarr**: Use GDSStore backend to read/write chunked N-dimensional arrays directly on GPU
- **cuSpatial + cuDF (legacy 25.04 only)**: Keep both packages on the compatible frozen stack
- **cuSpatial + cuML (legacy 25.04 only)**: Keep the full environment pinned and isolated
- **RAFT + CuPy**: Use RAFT's eigsh() on sparse matrices built with CuPy/cupyx.scipy.sparse
- **RAFT + raft-dask**: Scale GPU workloads across multiple GPUs/nodes via Dask
