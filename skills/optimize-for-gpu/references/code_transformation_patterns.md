# Code Transformation Patterns

Before/after conversions: NumPy to CuPy, pandas to cuDF, a custom loop to a Numba CUDA
kernel, NetworkX to cuGraph, scikit-learn to cuML, a simulation loop to a Warp kernel,
file IO to KvikIO, maintained GPU-backed dashboards, scikit-image to cuCIM, legacy
GeoPandas-to-cuSpatial point-in-polygon, exact Faiss to exact cuVS search, and
`scipy.sparse.linalg` to RAFT.

These are illustrative patterns, not executed GPU benchmarks. Reuse the same inputs and
validate outputs before timing; independently generated CPU/GPU random arrays are not
a correctness comparison. Installation targets and hardware limits are in `installation.md`.

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

d_data = cuda.to_device(data)
d_out = cuda.device_array(d_data.shape, dtype=d_data.dtype)
threads = 256
blocks = (len(data) + threads - 1) // threads
process[blocks, threads](d_data, d_out)
out = d_out.copy_to_host()
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

# After (GPU) — match parameters and held-out quality; algorithms need not be identical
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
        velocities[i] += forces[i] * dt  # Unit mass, or forces stores accelerations
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

# After — device destination (local GDS only when configured and eligible)
import cupy as cp
import kvikio

gpu_data = cp.empty(1_000_000, dtype=cp.float32)
with kvikio.CuFile("data.bin", "r") as f:
    f.read(gpu_data)  # May use host staging in compatibility mode

# Reading from S3 directly to GPU
with kvikio.RemoteFile.open_s3_url("s3://bucket/data.bin") as f:
    buf = cp.empty(f.nbytes() // 4, dtype=cp.float32)
    f.read(buf)
```

### GPU-backed dashboard with maintained libraries

cuxfilter ended with RAPIDS 26.06. Do not start a new application with it. Keep large
transformations and aggregations in cuDF, then transfer only the compact display data at an
explicit visualization boundary:

```python
# Before — static matplotlib/seaborn plots, no interactivity
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_parquet("large_dataset.parquet")
fig, axes = plt.subplots(1, 2)
df.plot.scatter(x="feature1", y="feature2", ax=axes[0])
df["category"].value_counts().plot.bar(ax=axes[1])
plt.show()

# After — GPU data preparation plus a maintained dashboard stack
import cudf
import hvplot.pandas  # Registers .hvplot on pandas objects
import panel as pn

gpu_df = cudf.read_parquet("large_dataset.parquet")
gpu_summary = (
    gpu_df.groupby("category", as_index=False)
    .agg({"value_col": "mean"})
)
display_summary = gpu_summary.to_pandas()  # Transfer only the reduced result
dashboard = pn.Column(
    "# Interactive Explorer",
    display_summary.hvplot.bar(x="category", y="value_col"),
)
dashboard.servable()
```

For linked selections over detailed points, use HoloViews/hvPlot with Datashader and Panel.
Keep filter/aggregation callbacks on the GPU where practical, and document every conversion to
pandas. Read the cuxfilter reference only when maintaining an existing 26.06 application.

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

### GeoPandas point-in-polygon to cuSpatial (legacy 25.04 only)

cuSpatial is archived and incompatible with current RAPIDS packages. Use this only in an isolated
environment pinned to 25.04. `point_in_polygon` returns a boolean membership matrix; it is not a
drop-in replacement for `geopandas.sjoin`.

```python
# Before (CPU)
import geopandas as gpd
import numpy as np
from shapely.geometry import Point

points = gpd.GeoSeries([Point(x, y) for x, y in coords], crs="EPSG:4326")
polygons = gpd.read_file("regions.geojson").geometry.iloc[:31]
polygons = polygons.to_crs(points.crs)
if any(points.intersects(polygon.boundary).any() for polygon in polygons):
    raise ValueError("Validate a boundary predicate explicitly before this port")
membership_cpu = np.column_stack(
    [points.within(polygon).to_numpy() for polygon in polygons]
)

# After (GPU, legacy) — point-by-polygon membership on these non-boundary inputs
import cuspatial

points_gpu = cuspatial.from_geopandas(points)
polygons_gpu = cuspatial.from_geopandas(polygons)
membership_gpu = cuspatial.point_in_polygon(points_gpu, polygons_gpu)
```

### Exact Faiss search to exact cuVS search

Match algorithmic semantics before benchmarking. Use cuVS brute force for an exact Faiss
`IndexFlatL2` baseline; use CAGRA only when approximate results are acceptable and report recall@k
against this exact ground truth.

```python
# Before (CPU) — Faiss
import faiss
import numpy as np

rng = np.random.default_rng(42)
embeddings = rng.random((1_000_000, 128), dtype=np.float32)
queries = rng.random((1_000, 128), dtype=np.float32)
index = faiss.IndexFlatL2(128)
index.add(embeddings)
distances, neighbors = index.search(queries, k=10)

# After (GPU) — cuVS exact brute-force search
import cupy as cp
from cuvs.neighbors import brute_force

embeddings_gpu = cp.asarray(embeddings)
queries_gpu = cp.asarray(queries)
index_gpu = brute_force.build(embeddings_gpu, metric="sqeuclidean")
distances_gpu, neighbors_gpu = brute_force.search(index_gpu, queries_gpu, k=10)
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
