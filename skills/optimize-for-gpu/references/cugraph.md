# cuGraph Reference

> Review: 2026-10-01. Code below is illustrative unless explicitly described as CPU-tested.
> GPU execution, performance, GDS, and multi-GPU behavior require validation on target hardware.

cuGraph is NVIDIA's GPU-accelerated graph analytics library within the RAPIDS ecosystem. It
supports both a direct Python API and an **nx-cugraph** NetworkX backend. Performance depends on
algorithm, graph topology and size, graph-construction cost, fallback behavior, and GPU hardware,
so benchmark the complete workload instead of promising a fixed speedup.

> **Full documentation:** https://docs.nvidia.com/cugraph/26.08/
> **Version target:** 26.08
> **Repository:** https://github.com/rapidsai/cugraph

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Two Usage Modes](#two-usage-modes)
3. [nx-cugraph: Zero-Code-Change NetworkX Backend](#nx-cugraph-zero-code-change-networkx-backend)
4. [Direct cuGraph API](#direct-cugraph-api)
5. [Graph Creation and Data Loading](#graph-creation-and-data-loading)
6. [Supported Graph Types](#supported-graph-types)
7. [Algorithm Catalog](#algorithm-catalog)
8. [Multi-GPU Support with Dask](#multi-gpu-support-with-dask)
9. [GNN Support (cugraph-pyg and WholeGraph)](#gnn-support)
10. [Performance Characteristics and Benchmarks](#performance-characteristics-and-benchmarks)
11. [Memory Management](#memory-management)
12. [Interoperability](#interoperability)
13. [Known Limitations vs NetworkX](#known-limitations-vs-networkx)
14. [Common Migration Patterns](#common-migration-patterns)

---

## Installation and Setup

Use `uv add` in standalone examples; follow the user's existing project package manager when one
is already configured.

```bash
uv add --extra-index-url=https://pypi.nvidia.com "cugraph-cu12==26.8.*"    # Core cuGraph for CUDA 12.x
uv add --extra-index-url=https://pypi.nvidia.com "nx-cugraph-cu12==26.8.*" # NetworkX backend
# For CUDA 13.x, use the -cu13 packages: cugraph-cu13, nx-cugraph-cu13
```

26.08 cuGraph and nx-cugraph wheels are published on PyPI. The NVIDIA index is optional for these current packages; historical releases may still use stub distributions.

**Platform:** Linux and WSL2 only (no native macOS or Windows).
**Requires:** Python >= 3.11, NVIDIA GPU with CUDA 12.x or 13.x support, NetworkX >= 3.2 (>= 3.5 recommended for optimal nx-cugraph).

Verify:
```python
import cugraph
print(cugraph.__version__)

# Quick test with built-in dataset
from cugraph.datasets import karate
G = karate.get_graph()
result = cugraph.degree_centrality(G)
print(result.head())
```

---

## Two Usage Modes

### Mode 1: nx-cugraph Backend (Zero Code Change)
Accelerate existing NetworkX code by setting one environment variable. No code changes required.

```bash
NX_CUGRAPH_AUTOCONFIG=True python my_networkx_script.py
```

### Mode 2: Direct cuGraph API
Use cuGraph's native API for maximum control, working directly with cuDF DataFrames and cuGraph graph objects.

```python
import cugraph
import cudf

edges = cudf.DataFrame({
    "src": [0, 1, 2, 0],
    "dst": [1, 2, 3, 3],
    "weight": [1.0, 2.0, 1.5, 3.0]
})
G = cugraph.Graph()
G.from_cudf_edgelist(edges, source="src", destination="dst", edge_attr="weight")
result = cugraph.pagerank(G)
```

**When to use which:**
- **nx-cugraph**: Existing NetworkX codebases, rapid prototyping, when you want zero migration effort
- **Direct API**: Maximum performance, multi-GPU workflows, integration with cuDF/cuML pipelines, GNN training

---

## nx-cugraph: Zero-Code-Change NetworkX Backend

nx-cugraph is a NetworkX backend that transparently redirects supported algorithm calls to GPU-accelerated cuGraph implementations.

### How It Works

NetworkX >= 3.2 has a backend dispatch system. When nx-cugraph is installed and enabled, NetworkX automatically redirects supported function calls to GPU implementations. Unsupported calls fall back to default NetworkX.

### Three Ways to Enable

**1. Environment Variable (recommended for zero code change):**
```bash
export NX_CUGRAPH_AUTOCONFIG=True
python my_script.py
# OR inline:
NX_CUGRAPH_AUTOCONFIG=True python my_script.py
```

**2. Keyword Argument (explicit per-call):**
```python
import networkx as nx
result = nx.betweenness_centrality(G, k=10, backend="cugraph")
```

**3. Type-Based Dispatch (explicit graph conversion):**
```python
import networkx as nx
import nx_cugraph as nxcg

G_nx = nx.karate_club_graph()
G_gpu = nxcg.from_networkx(G_nx)  # Convert once, reuse for multiple algorithms
result = nx.pagerank(G_gpu)       # Automatically dispatched to GPU
```

Since 26.04, GPU-backed graphs can also be constructed directly, e.g. `nx.Graph(backend="cugraph")`.

### Supported Algorithms in nx-cugraph

**Centrality:**
- `betweenness_centrality`, `edge_betweenness_centrality`
- `degree_centrality`, `in_degree_centrality`, `out_degree_centrality`
- `eigenvector_centrality`, `katz_centrality`

**Community:**
- `louvain_communities`, `leiden_communities`

**Components:**
- `connected_components`, `is_connected`, `number_connected_components`
- `node_connected_component`
- `weakly_connected_components`, `is_weakly_connected`, `number_weakly_connected_components`

**Clustering:**
- `average_clustering`, `clustering`, `transitivity`, `triangles`

**Core:**
- `core_number`, `k_truss`

**Link Analysis:**
- `pagerank`, `hits`

**Link Prediction:**
- `jaccard_coefficient`

**Shortest Paths (23+ functions):**
- `shortest_path`, `shortest_path_length`
- `has_path`, `all_pairs_shortest_path`, `all_pairs_shortest_path_length`
- `dijkstra_path`, `dijkstra_path_length`, `all_pairs_dijkstra`, `all_pairs_dijkstra_path_length`
- `bellman_ford_path`, `bellman_ford_path_length`, `all_pairs_bellman_ford_path_length`
- `single_source_shortest_path`, `single_source_shortest_path_length`
- `single_source_dijkstra`, `single_source_dijkstra_path`, `single_source_dijkstra_path_length`
- `single_source_bellman_ford`, `single_source_bellman_ford_path`, `single_source_bellman_ford_path_length`
- `single_target_shortest_path_length`

**Traversal:**
- `bfs_edges`, `bfs_layers`, `bfs_predecessors`, `bfs_successors`, `bfs_tree`
- `generic_bfs_edges`, `descendants_at_distance`

**DAG:**
- `ancestors`, `descendants`

**Bipartite:**
- `betweenness_centrality` (bipartite), `biadjacency_matrix`
- `complete_bipartite_graph`, `from_biadjacency_matrix`

**Tree:**
- `is_arborescence`, `is_branching`, `is_forest`, `is_tree`

**Operators:**
- `complement`, `reverse`

**Reciprocity:**
- `overall_reciprocity`, `reciprocity`

**Isolate:**
- `is_isolate`, `isolates`, `number_of_isolates`

**Lowest Common Ancestors:**
- `lowest_common_ancestor`

**Layout:**
- `forceatlas2_layout`

**Graph Generators:** Various generators are also supported for creating graphs directly on GPU.

---

## Direct cuGraph API

### Quick Example

```python
import cugraph
import cudf

# Load edges from cuDF DataFrame
edges = cudf.DataFrame({
    "source": [0, 1, 2, 3, 0, 2],
    "destination": [1, 2, 3, 4, 4, 1],
    "weight": [1.0, 2.0, 1.0, 3.0, 0.5, 1.5]
})

G = cugraph.Graph(directed=True)
G.from_cudf_edgelist(edges, source="source", destination="destination", edge_attr="weight")

# Run algorithms
pr = cugraph.pagerank(G)
bc = cugraph.betweenness_centrality(G)
components = cugraph.weakly_connected_components(G)
```

---

## Graph Creation and Data Loading

### From cuDF DataFrame (Primary Method)
```python
import cudf, cugraph

df = cudf.DataFrame({"src": [0, 1, 2], "dst": [1, 2, 3], "wt": [1.0, 2.0, 3.0]})

# Unweighted
G = cugraph.Graph()
G.from_cudf_edgelist(df, source="src", destination="dst")

# Weighted
G = cugraph.Graph()
G.from_cudf_edgelist(df, source="src", destination="dst", edge_attr="wt")

# Directed
G = cugraph.Graph(directed=True)
G.from_cudf_edgelist(df, source="src", destination="dst")
```

### From Pandas DataFrame
```python
import pandas as pd, cugraph

df = pd.DataFrame({"src": [0, 1, 2], "dst": [1, 2, 3]})
G = cugraph.Graph()
G.from_pandas_edgelist(df, source="src", destination="dst")
```

### From cuDF Adjacency List
```python
G = cugraph.Graph()
G.from_cudf_adjlist(offsets, indices, values)  # CSR format
```

### From NumPy Array
```python
import numpy as np
adj_matrix = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]])
G = cugraph.Graph()
G.from_numpy_array(adj_matrix)
```

### From Pandas Adjacency Matrix
```python
G = cugraph.Graph()
G.from_pandas_adjacency(adj_df)
```

### From Dask-cuDF (Multi-GPU)
```python
G = cugraph.Graph()
G.from_dask_cudf_edgelist(dask_cudf_df, source="src", destination="dst")
```

### From Built-in Datasets
```python
from cugraph.datasets import karate, dolphins, polbooks, netscience
G = karate.get_graph()
```

### Symmetrization (Undirected Graphs)
```python
# Ensure all edges are bidirectional
sym_df = cugraph.symmetrize_df(df, "src", "dst")

# Or symmetrize a graph directly
sym_df = cugraph.symmetrize(source_col, dest_col, weight_col)
```

### Vertex Renumbering
cuGraph internally renumbers vertices to contiguous integers starting from 0. Native high-level algorithms such as PageRank already restore external IDs. Do not unrenumber those results twice:
```python
result = cugraph.pagerank(G)
# Use G.unrenumber only for an explicitly internal-ID table from a lower-level API.
```

---

## Supported Graph Types

| Graph Type | cuGraph Class | Notes |
|---|---|---|
| **Undirected** | `cugraph.Graph()` | Default; edges are bidirectional |
| **Directed** | `cugraph.Graph(directed=True)` | Directed edges; some algorithms require directed/undirected |
| **Weighted** | Set `edge_attr` in `from_cudf_edgelist` | Edge weights used by SSSP, PageRank, Louvain, etc. |
| **MultiGraph** | `cugraph.MultiGraph()` | Multiple edges between same vertex pairs |
| **Bipartite** | Represent bipartite structure in a standard Graph | Check nx-cugraph for supported NetworkX bipartite operations |

**Important:** cuGraph uses a CSR (Compressed Sparse Row) internal representation. Graphs are immutable after creation -- you cannot dynamically add/remove individual edges after calling `from_cudf_edgelist()`. To modify a graph, reconstruct it from a new DataFrame.

---

## Algorithm Catalog

The multi-GPU column uses callable aliases exported by `import cugraph.dask`.
Namespace subpackages may instead expose modules or single-GPU imports; do not
construct an API path by inserting `centrality`, `community`, or `components`.
Column entries identify APIs, not interchangeable return schemas or weight support.

### Centrality

| Algorithm | Single-GPU | Multi-GPU | NetworkX Equivalent |
|---|---|---|---|
| Betweenness Centrality | `cugraph.betweenness_centrality(G)` | `cugraph.dask.betweenness_centrality()` | `nx.betweenness_centrality()` |
| Edge Betweenness | `cugraph.edge_betweenness_centrality(G)` | `cugraph.dask.edge_betweenness_centrality()` | `nx.edge_betweenness_centrality()` |
| Degree Centrality | `cugraph.degree_centrality(G)` | -- | `nx.degree_centrality()` |
| Eigenvector Centrality | `cugraph.eigenvector_centrality(G)` | `cugraph.dask.eigenvector_centrality()` | `nx.eigenvector_centrality()` |
| Katz Centrality | `cugraph.katz_centrality(G)` | `cugraph.dask.katz_centrality()` | `nx.katz_centrality()` |

### Community Detection

| Algorithm | Single-GPU | Multi-GPU | NetworkX Equivalent |
|---|---|---|---|
| Louvain | `cugraph.louvain(G, max_level=, max_iter=, resolution=)` | `cugraph.dask.louvain()` | `nx.community.louvain_communities()` |
| Leiden | `cugraph.leiden(G, max_iter=, resolution=)` | `cugraph.dask.leiden()` | `nx.community.leiden_communities()` |
| ECG | `cugraph.ecg(G, min_weight=)` | `cugraph.dask.ecg()` | -- |
| Spectral Balanced Cut | `cugraph.spectralBalancedCutClustering(G, num_clusters)` | -- | -- |
| Spectral Modularity | `cugraph.spectralModularityMaximizationClustering(G, num_clusters)` | -- | -- |
| Triangle Counting | `cugraph.triangle_count(G)` | `cugraph.dask.triangle_count()` | `nx.triangles()` |
| K-Truss | `cugraph.k_truss(G, k)` or `cugraph.ktruss_subgraph(G, k)` | `cugraph.dask.ktruss_subgraph()` | `nx.k_truss()` |
| EgoNet | `cugraph.ego_graph(G, n, radius=)` | `cugraph.dask.ego_graph()` | `nx.ego_graph()` |
| Induced Subgraph | `cugraph.induced_subgraph(G, vertices)` | `cugraph.dask.induced_subgraph()` | `G.subgraph(vertices)` |

**Clustering Analysis:**
- `cugraph.analyzeClustering_edge_cut(G, n_clusters, clustering)`
- `cugraph.analyzeClustering_modularity(G, n_clusters, clustering)`
- `cugraph.analyzeClustering_ratio_cut(G, n_clusters, clustering)`

### Traversal

| Algorithm | Single-GPU | Multi-GPU | NetworkX Equivalent |
|---|---|---|---|
| BFS | `cugraph.bfs(G, start=, depth_limit=)` | `cugraph.dask.bfs()` | `nx.bfs_edges()` |
| BFS Edges | `cugraph.bfs_edges(G, source)` | -- | `nx.bfs_edges()` |
| SSSP | `cugraph.sssp(G, source=)` | `cugraph.dask.sssp()` | `nx.single_source_dijkstra()` |
| Shortest Path | `cugraph.shortest_path(G, source=)` | -- | `nx.shortest_path()` |
| Shortest Path Length | `cugraph.shortest_path_length(G, source, target=)` | -- | `nx.shortest_path_length()` |
| Filter Unreachable | `cugraph.filter_unreachable(df)` | -- | -- |

### Link Analysis

| Algorithm | Single-GPU | Multi-GPU | NetworkX Equivalent |
|---|---|---|---|
| PageRank | `cugraph.pagerank(G, alpha=)` | `cugraph.dask.pagerank()` | `nx.pagerank()` |
| HITS | `cugraph.hits(G, max_iter=, tol=)` | `cugraph.dask.hits()` | `nx.hits()` |

### Link Prediction / Similarity

| Algorithm | Single-GPU | Multi-GPU | NetworkX Equivalent |
|---|---|---|---|
| Jaccard | `cugraph.jaccard(G, vertex_pair=)` | `cugraph.dask.jaccard()` | `nx.jaccard_coefficient()` |
| Cosine Similarity | `cugraph.cosine(G, vertex_pair=)` | `cugraph.dask.cosine()` | -- |
| Overlap | `cugraph.overlap(G, vertex_pair=)` | `cugraph.dask.overlap()` | -- |
| Sorensen | `cugraph.sorensen(G, vertex_pair=)` | `cugraph.dask.sorensen()` | -- |

**NetworkX-compatible wrappers:** `cugraph.jaccard_coefficient(G, ebunch)`, `cugraph.overlap_coefficient(G, ebunch)`, `cugraph.sorensen_coefficient(G, ebunch)`

### Components

| Algorithm | Single-GPU | Multi-GPU | NetworkX Equivalent |
|---|---|---|---|
| Connected Components | `cugraph.connected_components(G)` | -- | `nx.connected_components()` |
| Weakly Connected | `cugraph.weakly_connected_components(G)` | `cugraph.dask.weakly_connected_components()` | `nx.weakly_connected_components()` |
| Strongly Connected | `cugraph.strongly_connected_components(G)` | -- | `nx.strongly_connected_components()` |

### Cores

| Algorithm | Single-GPU | Multi-GPU | NetworkX Equivalent |
|---|---|---|---|
| Core Number | `cugraph.core_number(G, degree_type=)` | `cugraph.dask.core_number()` | `nx.core_number()` |
| K-Core | `cugraph.k_core(G, k=, core_number=)` | `cugraph.dask.k_core()` | `nx.k_core()` |

### Sampling

| Algorithm | Single-GPU | Multi-GPU | Notes |
|---|---|---|---|
| Biased Random Walks | `cugraph.biased_random_walks(G, start_vertices)` | `cugraph.dask.biased_random_walks()` | Weighted/biased traversal |
| Uniform Random Walks | -- | `cugraph.dask.uniform_random_walks()` | Padded result with max path length |
| Random Walks | -- | `cugraph.dask.random_walks()` | General random walk |
| Node2Vec | -- | `cugraph.dask.sampling.node2vec_random_walks()` | Node2Vec sampling framework |
| Homogeneous Neighbor Sample | `cugraph.homogeneous_neighbor_sample(G, start_vertices, fanout)` | -- | Configurable fan-out per hop |
| Heterogeneous Neighbor Sample | `cugraph.heterogeneous_neighbor_sample(G, ...)` | -- | Multi-type node/edge graphs |

### Layout

| Algorithm | Single-GPU | Multi-GPU | NetworkX Equivalent |
|---|---|---|---|
| Force Atlas 2 | `cugraph.force_atlas2(G)` | -- | `nx.forceatlas2_layout()` (via nx-cugraph) |

### Tree

| Algorithm | Single-GPU | Multi-GPU | NetworkX Equivalent |
|---|---|---|---|
| Minimum Spanning Tree | `cugraph.minimum_spanning_tree(G)` | -- | `nx.minimum_spanning_tree()` |
| Maximum Spanning Tree | `cugraph.maximum_spanning_tree(G)` | -- | `nx.maximum_spanning_tree()` |

### Linear Assignment

| Algorithm | Single-GPU | Multi-GPU |
|---|---|---|
| Hungarian | `cugraph.hungarian(G, workers, cost)` | -- |

### Utilities

| Function | Purpose |
|---|---|
| `cugraph.symmetrize(src, dst, val)` | Make edges bidirectional (for undirected graphs) |
| `cugraph.symmetrize_df(df, src, dst)` | Symmetrize a DataFrame |
| `cugraph.symmetrize_ddf(ddf, src, dst)` | Symmetrize a Dask DataFrame |
| `cugraph.NumberMap` | Map external vertex IDs to contiguous internal IDs |
| `G.unrenumber(df, col)` | Map internal vertex IDs back to original |

---

## Multi-GPU Support with Dask

cuGraph supports multi-GPU computation through Dask for graphs that exceed single-GPU memory or need faster processing.

### Setup
```python
from dask.distributed import Client
from dask_cuda import LocalCUDACluster
import cugraph
import cugraph.dask as dask_cugraph
import dask_cudf

# Initialize multi-GPU cluster
cluster = LocalCUDACluster()
client = Client(cluster)
import cugraph.dask.comms.comms as Comms
Comms.initialize(p2p=True)

# Load distributed edge list
ddf = dask_cudf.read_csv("large_graph.csv", names=["src", "dst", "weight"])

# Create distributed graph
G = cugraph.Graph(directed=True)
G.from_dask_cudf_edgelist(ddf, source="src", destination="dst", edge_attr="weight")

# Run multi-GPU algorithms
pr = dask_cugraph.pagerank(G)
components = dask_cugraph.weakly_connected_components(G)
# Materialize or write distributed outputs before teardown.
pr_local = pr.compute()
Comms.destroy()
client.close()
cluster.close()
```

### Algorithms with Multi-GPU Support

The following algorithms have Dask-based multi-GPU implementations:
- **Centrality:** Betweenness, Edge Betweenness, Eigenvector, Katz
- **Community:** Louvain, Leiden, ECG, K-Truss, Triangle Counting, EgoNet, Induced Subgraph
- **Components:** Weakly Connected Components
- **Cores:** Core Number, K-Core
- **Link Analysis:** PageRank, HITS
- **Link Prediction:** Overlap, Sorensen
- **Sampling:** Random Walks, Biased Random Walks, Uniform Random Walks, Node2Vec, Neighborhood Sampling
- **Traversal:** BFS, SSSP
- **Utilities:** Renumbering, Symmetrize, Path Extraction, Two-Hop Neighbors, RMAT Generator

---

## GNN Support

### cugraph-pyg (PyTorch Geometric Integration)

As of release 25.06, **cugraph-pyg is the recommended GNN framework integration** (cuGraph-DGL has been removed).

cugraph-pyg provides native GPU-accelerated implementations of PyG's core interfaces:

- **GraphStore**: GPU-accelerated graph storage using cuGraph's CSR representation
- **FeatureStore**: GPU-resident feature storage for node/edge features
- **Sampler/Loader**: GPU-accelerated neighborhood sampling with configurable fan-out

```bash
uv add --extra-index-url=https://pypi.nvidia.com "cugraph-pyg-cu12==26.8.*"
```

**Key capabilities:**
- Heterogeneous graph sampling (multiple node/edge types)
- Multi-GPU distributed sampling
- Direct integration with PyG's `NeighborLoader` and training loops
- GPU-accelerated centrality, community detection, and other analytics within PyG workflows

**Repository:** https://github.com/rapidsai/cugraph-gnn

### WholeGraph (Distributed GPU Memory for GNNs)

WholeGraph provides distributed GPU memory management for large-scale GNN training through its **WholeMemory** abstraction.

```bash
uv add --extra-index-url=https://pypi.nvidia.com "pylibwholegraph-cu12==26.8.*"
```

**Core concepts:**

- **WholeMemory**: A unified view of GPU memory distributed across multiple GPUs. Each GPU sees the entire memory space through a single abstraction, even though data is physically distributed.
- **WholeMemory Communicator**: Defines the set of GPUs that collaborate, with one process per GPU.
- **WholeMemory Tensor**: Like PyTorch tensors but distributed; supports 1D and 2D data with first dimension partitioned across GPUs.
- **WholeMemory Embedding**: 2D tensor variant with built-in cache policies and sparse optimizers (SGD, Adam, RMSProp, AdaGrad).

**Memory modes:**
| Mode | Description | Use Case |
|---|---|---|
| **Continuous** | Single continuous address space via hardware peer-to-peer | NVLink systems (DGX) |
| **Chunked** | Per-GPU chunks with direct multi-pointer access | Multi-GPU with some NVLink |
| **Distributed** | Explicit communication required for remote access | Multi-node clusters |

**Storage locations:** Host memory (pinned) or device/GPU memory.

**Graph storage:** CSR format with ROW_INDEX and COL_INDEX as WholeMemory Tensors for efficient distributed graph management.

**Cache policies:** Device-cached host memory, local-cached global memory -- critical for handling graphs larger than GPU memory.

**Target hardware:** NVLink systems like DGX A100/H100 servers for optimal performance.

### cuGraph-DGL (DEPRECATED)

**cuGraph-DGL has been removed as of release 25.06.** Users should migrate to cugraph-pyg. The cuGraph team is not planning further work in the DGL ecosystem.

---

## Performance Characteristics and Benchmarks

Benchmark with the user's actual topology and algorithm:

1. Check that the requested NetworkX algorithm dispatches to nx-cugraph rather than falling back
   to CPU.
2. Measure graph construction and conversion separately from repeated algorithm calls, then report
   both warm algorithm time and end-to-end time.
3. Warm the CUDA context before collecting timed repetitions.
4. Verify output semantics, convergence tolerance, sampled-algorithm parameters, and floating-point
   tolerance against the CPU implementation.
5. Record vertices, edges, directedness, weight dtype, GPU model, CPU baseline, software versions,
   and whether the graph was already device-resident.
6. Use multi-GPU only after estimating graph and temporary-memory requirements and measuring the
   communication cost.

Small or one-shot graphs can lose to NetworkX after setup and transfer. Large device-resident
graphs with supported algorithms are better candidates, but graph size alone does not establish a
speedup.

---

## Memory Management

### GPU Memory Considerations

- cuGraph stores graphs in CSR format on GPU memory
- Estimate CSR storage from offset/index/weight dtypes, edge symmetrization, renumber maps and retained edge lists. Peak construction/algorithm memory can be much larger than final CSR storage.
- Algorithm working memory varies; some algorithms (like betweenness centrality) need additional O(V) or O(E) temporary space

### Strategies for Large Graphs

1. **Use multi-GPU** via Dask for graphs exceeding single GPU memory
2. **Use WholeGraph** for GNN workloads that need distributed feature/graph storage
3. **Use `rmm`** (RAPIDS Memory Manager) for fine-grained GPU memory control:
   ```python
   import rmm
   rmm.reinitialize(pool_allocator=True, initial_pool_size=2**30)  # 1 GB pool
   ```
4. **Monitor memory** with `nvidia-smi` or `cupy.cuda.runtime.memGetInfo()` (device free/total, not per-process peak)
5. **Delete intermediate results** explicitly: `del result; import gc; gc.collect()`

---

## Interoperability

### With cuDF
cuGraph natively consumes and produces cuDF DataFrames. Algorithm results are returned as cuDF DataFrames with vertex/edge columns.

```python
import cudf, cugraph
# Create graph from cuDF
edges = cudf.read_csv("edges.csv")
G = cugraph.Graph()
G.from_cudf_edgelist(edges, source="src", destination="dst")

# Results come back as cuDF DataFrames
pr = cugraph.pagerank(G)  # cuDF DataFrame with 'vertex' and 'pagerank' columns
```

### With cuML
Pipe graph analytics results into cuML for downstream ML:
```python
import cuml
# Use graph embeddings (e.g., from Node2Vec) as features for cuML
# Or use community labels as features for classification
louvain_result = cugraph.louvain(G)
# Feed partition labels into cuML models
```

### With CuPy / SciPy
```python
# cuGraph can work with CuPy and SciPy sparse matrices as input data
import cupy, scipy
```

### With NetworkX
```python
import networkx as nx
import nx_cugraph as nxcg

# Convert once when repeated algorithms justify keeping the graph on GPU.
G_nx = nx.karate_club_graph()
G_gpu = nxcg.from_networkx(G_nx)
result = nx.pagerank(G_gpu)
```

### With PyTorch Geometric
```python
# Via cugraph-pyg (see GNN Support section)
from cugraph_pyg.data import GraphStore, FeatureStore
from cugraph_pyg.loader import NeighborLoader
```

### With Pandas
```python
import pandas as pd
df = pd.DataFrame({"src": [0, 1, 2], "dst": [1, 2, 3]})
G = cugraph.Graph()
G.from_pandas_edgelist(df, source="src", destination="dst")
```

---

## Known Limitations vs NetworkX

1. **Immutable graphs:** Cannot add/remove individual edges after graph creation. Must reconstruct from DataFrame.
2. **No node/edge attributes on Graph object:** cuGraph stores structure only. Node/edge properties must be maintained separately (e.g., in cuDF DataFrames). The nx-cugraph backend handles attribute mapping transparently.
3. **Vertex types:** Vertices must be integers (or will be renumbered to integers internally). String vertex IDs are renumbered automatically.
4. **Not all NetworkX algorithms supported:** Check the nx-cugraph supported algorithms list. Unsupported calls fall back to CPU NetworkX.
5. **Numerical precision:** GPU floating-point results may differ slightly from CPU results due to parallel reduction ordering.
6. **No dynamic graphs:** cuGraph is designed for static graph analytics, not streaming/dynamic graph updates.
7. **Strongly Connected Components:** Single-GPU only (no multi-GPU Dask variant).
8. **Spectral Clustering:** Single-GPU only.
9. **Minimum/Maximum Spanning Tree:** Single-GPU only.
10. **Force Atlas 2 layout:** Single-GPU only.
11. **Compatibility doc:** The official list of NetworkX APIs accelerated by nx-cugraph is maintained at https://docs.nvidia.com/cugraph/26.08/nx_cugraph/supported-algorithms/ (~80 algorithms plus generators and utilities).

---

## Common Migration Patterns

### NetworkX to nx-cugraph (Zero Effort)
```python
# Before (CPU):
import networkx as nx
G = nx.from_pandas_edgelist(df, "src", "dst")
pr = nx.pagerank(G)

# After (GPU, no code changes):
# Just set: NX_CUGRAPH_AUTOCONFIG=True
# Same code runs on GPU automatically
```

### NetworkX to Direct cuGraph API
```python
# Before (NetworkX):
import networkx as nx
G = nx.from_pandas_edgelist(df, "src", "dst")
pr = nx.pagerank(G, alpha=0.85)
bc = nx.betweenness_centrality(G)  # Exact baseline; use matched sampling for large graphs
communities = nx.community.louvain_communities(G, resolution=1.0)

# After (cuGraph):
import cudf, cugraph
edges = cudf.from_pandas(df)
G = cugraph.Graph()
G.from_cudf_edgelist(edges, source="src", destination="dst")
pr = cugraph.pagerank(G, alpha=0.85)
bc = cugraph.betweenness_centrality(G)
parts, modularity = cugraph.louvain(G, resolution=1.0)
```

### Pandas to cuDF + cuGraph Pipeline
```python
# Before:
import pandas as pd
import networkx as nx
df = pd.read_csv("edges.csv")
G = nx.from_pandas_edgelist(df, "source", "target", "weight")
result = nx.pagerank(G)

# After:
import cudf
import cugraph
df = cudf.read_csv("edges.csv")
G = cugraph.Graph()
G.from_cudf_edgelist(df, source="source", destination="target", edge_attr="weight")
result = cugraph.pagerank(G)
```

### Adding Multi-GPU to Existing cuGraph Code
```python
# Before (single-GPU):
import cugraph
G = cugraph.Graph()
G.from_cudf_edgelist(edges, source="src", destination="dst")
result = cugraph.pagerank(G)

# After (multi-GPU):
from dask.distributed import Client
from dask_cuda import LocalCUDACluster
import cugraph, cugraph.dask as dcg
import dask_cudf

cluster = LocalCUDACluster()
client = Client(cluster)
import cugraph.dask.comms.comms as Comms
Comms.initialize(p2p=True)

ddf = dask_cudf.from_cudf(edges, npartitions=len(cluster.workers))
G = cugraph.Graph()
G.from_dask_cudf_edgelist(ddf, source="src", destination="dst")
result = dcg.pagerank(G)
result_local = result.compute()  # Only if the result fits one GPU
Comms.destroy()
client.close()
cluster.close()
```
