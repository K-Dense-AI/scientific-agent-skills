# RAFT (pylibraft) Reference

RAFT (Reusable Accelerated Functions and Tools) is a RAPIDS library of GPU-accelerated building blocks for machine learning and information retrieval. It provides low-level primitives — sparse eigensolvers, device memory management, random graph generation, and multi-GPU communication — that higher-level libraries like cuML and cuGraph are built on. Use `pylibraft` directly when you need these primitives without the overhead of a full ML framework.

> **Full documentation:** https://docs.rapids.ai/api/raft/stable/
> **Note:** Vector search and clustering algorithms have been migrated to [cuVS](https://github.com/rapidsai/cuvs). Use cuVS for nearest neighbor search, not RAFT.

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Core Concepts](#core-concepts)
3. [Device Memory Management](#device-memory-management)
4. [Sparse Eigenvalue Problems](#sparse-eigenvalue-problems)
5. [Random Graph Generation](#random-graph-generation)
6. [Multi-Node Multi-GPU with raft-dask](#multi-node-multi-gpu-with-raft-dask)
7. [Interoperability](#interoperability)
8. [Performance Tips](#performance-tips)
9. [Common Pitfalls](#common-pitfalls)

---

## Installation and Setup

Always use `uv add` (never `pip install` or `conda install`) in all install instructions, docstrings, comments, and error messages.

```bash
# pylibraft (core library)
uv add --extra-index-url=https://pypi.nvidia.com pylibraft-cu12   # For CUDA 12.x

# raft-dask (multi-node multi-GPU support, optional)
uv add --extra-index-url=https://pypi.nvidia.com raft-dask-cu12   # For CUDA 12.x
```

Verify:
```python
import pylibraft
from pylibraft.common import DeviceResources
handle = DeviceResources()
handle.sync()
print("pylibraft is working")
```

---

## Core Concepts

### DeviceResources (CUDA Resource Handle)

`DeviceResources` manages expensive CUDA resources (streams, stream pools, library handles for cuBLAS/cuSOLVER). Create one and reuse it across multiple RAFT calls to avoid repeated allocation overhead.

```python
from pylibraft.common import DeviceResources, Stream

# Default stream
handle = DeviceResources()

# Custom stream
stream = Stream()
handle = DeviceResources(stream)

# With a CuPy stream
import cupy
cupy_stream = cupy.cuda.Stream()
handle = DeviceResources(stream=cupy_stream.ptr)

# Always sync before reading results
handle.sync()
```

RAFT functions are asynchronous by default — they return immediately and work continues on the GPU. You must call `handle.sync()` before accessing output data on the CPU. If you don't pass a `handle`, RAFT allocates temporary resources internally and synchronizes before returning (convenient but slower for repeated calls).

### Stream

A thin wrapper around `cudaStream_t` for ordering GPU operations:

```python
from pylibraft.common import Stream

stream = Stream()
stream.sync()                  # Synchronize all work on this stream
ptr = stream.get_ptr()         # Get the raw cudaStream_t pointer (uintptr_t)
```

---

## Device Memory Management

### device_ndarray

`device_ndarray` is RAFT's lightweight GPU array type. It implements `__cuda_array_interface__`, making it interoperable with CuPy, Numba, PyTorch, and other GPU libraries.

```python
from pylibraft.common import device_ndarray
import numpy as np

# Allocate empty GPU array
gpu_arr = device_ndarray.empty((1000, 50), dtype=np.float32)

# From a NumPy array (copies data to GPU)
cpu_data = np.random.rand(1000, 50).astype(np.float32)
gpu_arr = device_ndarray(cpu_data)

# Back to NumPy (copies data to CPU)
result = gpu_arr.copy_to_host()

# Properties
print(gpu_arr.shape)          # (1000, 50)
print(gpu_arr.dtype)          # float32
print(gpu_arr.c_contiguous)   # True (row-major)
print(gpu_arr.f_contiguous)   # False
```

### Configuring Output Types

You can configure all RAFT compute APIs to return CuPy arrays or PyTorch tensors instead of `device_ndarray`:

```python
import pylibraft.config

pylibraft.config.set_output_as("cupy")    # All APIs return cupy arrays
pylibraft.config.set_output_as("torch")   # All APIs return torch tensors

# Custom conversion
pylibraft.config.set_output_as(lambda arr: arr.copy_to_host())  # Return numpy
```

---

## Sparse Eigenvalue Problems

### eigsh — Sparse Symmetric Eigenvalue Decomposition

GPU-accelerated Lanczos method for finding eigenvalues/eigenvectors of large sparse symmetric matrices. Drop-in replacement for `scipy.sparse.linalg.eigsh`.

```python
import cupy as cp
import cupyx.scipy.sparse as sp
from pylibraft.sparse.linalg import eigsh
from pylibraft.common import DeviceResources

# Create a sparse symmetric matrix (CSR format)
n = 10000
density = 0.01
A = sp.random(n, n, density=density, dtype=cp.float32, format='csr')
A = A + A.T  # Make symmetric

# Find 6 largest eigenvalues
handle = DeviceResources()
eigenvalues, eigenvectors = eigsh(A, k=6, which='LM', handle=handle)
handle.sync()

print(f"Eigenvalues shape: {eigenvalues.shape}")      # (6,)
print(f"Eigenvectors shape: {eigenvectors.shape}")     # (10000, 6)
```

**Parameters:**
- `A` — Sparse symmetric CSR matrix (`cupyx.scipy.sparse.csr_matrix`)
- `k` — Number of eigenvalues to compute (default: 6). Must be `1 <= k < n`
- `which` — Which eigenvalues:
  - `'LM'`: largest in magnitude (default)
  - `'LA'`: largest algebraic
  - `'SA'`: smallest algebraic
  - `'SM'`: smallest in magnitude
- `v0` — Starting vector (optional, random if None)
- `ncv` — Number of Lanczos vectors. Must be `k + 1 < ncv < n`
- `maxiter` — Maximum iterations
- `tol` — Convergence tolerance (0 = machine precision)
- `seed` — Random seed for reproducibility
- `handle` — Optional `DeviceResources` handle

**When to use:** Spectral methods (spectral clustering, graph partitioning, PageRank-like computations), dimensionality reduction on sparse data, physics simulations with large sparse Hamiltonians, structural analysis (vibration modes).

---

## Random Graph Generation

### rmat — R-MAT Graph Generation

Generates random graphs using the Recursive Matrix (R-MAT) model, commonly used for benchmarking graph algorithms with realistic structure (power-law degree distribution, community structure).

```python
import cupy as cp
from pylibraft.random import rmat
from pylibraft.common import DeviceResources

n_edges = 100000
r_scale = 16          # log2 of source node count (2^16 = 65536 nodes)
c_scale = 16          # log2 of destination node count
theta_len = max(r_scale, c_scale) * 4

# Output: edge list as (src, dst) pairs
out = cp.empty((n_edges, 2), dtype=cp.int32)
# Probability distribution at each R-MAT level
theta = cp.random.random_sample(theta_len, dtype=cp.float32)

handle = DeviceResources()
rmat(out, theta, r_scale, c_scale, seed=42, handle=handle)
handle.sync()

print(f"Generated {n_edges} edges")
print(f"Edge list shape: {out.shape}")       # (100000, 2)
print(f"Sample edges:\n{out[:5].get()}")     # First 5 edges on CPU
```

**When to use:** Benchmarking graph algorithms, generating synthetic social/web graphs, testing graph processing pipelines at scale.

---

## Multi-Node Multi-GPU with raft-dask

`raft-dask` provides a `Comms` class for managing NCCL and UCX communication across workers in a Dask cluster. This is the foundation for distributed GPU computing in RAPIDS.

```python
from dask_cuda import LocalCUDACluster
from dask.distributed import Client
from raft_dask.common import Comms, local_handle

# Set up a local multi-GPU Dask cluster
cluster = LocalCUDACluster()
client = Client(cluster)

def run_on_gpu(sessionId):
    handle = local_handle(sessionId)
    # Use handle with RAFT or cuML algorithms
    return "done"

# Initialize multi-GPU communication
comms = Comms(client=client)
comms.init()

# Submit work to each GPU worker
futures = [
    client.submit(run_on_gpu, comms.sessionId, workers=[w], pure=False)
    for w in comms.worker_addresses
]

# Wait for results
from dask.distributed import wait
wait(futures, timeout=60)

# Clean up
comms.destroy()
client.close()
cluster.close()
```

**Comms parameters:**
- `comms_p2p` (bool) — Enable UCX peer-to-peer communication (default: False). Enable for algorithms that need direct GPU-to-GPU transfers.
- `client` — Dask distributed client
- `verbose` (bool) — Enable verbose logging
- `streams_per_handle` (int) — Number of CUDA streams per handle

---

## Interoperability

RAFT's `device_ndarray` implements `__cuda_array_interface__`, enabling zero-copy sharing with other GPU libraries:

```python
import cupy as cp
import torch
from pylibraft.common import device_ndarray

# pylibraft -> CuPy (zero-copy)
raft_arr = device_ndarray(np.random.rand(100).astype(np.float32))
cupy_arr = cp.asarray(raft_arr)

# pylibraft -> PyTorch (zero-copy)
torch_tensor = torch.as_tensor(raft_arr, device='cuda')

# CuPy -> pylibraft (pass directly — RAFT APIs accept __cuda_array_interface__)
cupy_data = cp.random.rand(100, 50, dtype=cp.float32)
# Can pass cupy_data directly to pylibraft functions like eigsh()

# pylibraft -> NumPy (copy)
numpy_arr = raft_arr.copy_to_host()
```

RAFT functions accept any object implementing `__cuda_array_interface__` as input — you don't need to convert to `device_ndarray` first. This means CuPy arrays, Numba device arrays, PyTorch CUDA tensors, and cuDF columns all work directly.

---

## Performance Tips

1. **Reuse DeviceResources.** Creating a `DeviceResources` allocates CUDA library handles (cuBLAS, cuSOLVER). Create once, pass to all calls.

2. **Batch your syncs.** RAFT calls are asynchronous. Queue multiple operations before calling `handle.sync()` rather than syncing after each one.

3. **Use float32.** GPU throughput for float32 is 2x-32x higher than float64. Only use float64 when precision demands it.

4. **Pre-allocate outputs.** Many RAFT functions accept an `out` parameter. Pre-allocating avoids repeated GPU memory allocation.

5. **Keep data on GPU.** RAFT interoperates with CuPy, cuDF, and cuML via `__cuda_array_interface__`. Pass GPU arrays directly between libraries instead of round-tripping through CPU.

---

## Common Pitfalls

- **Forgetting to sync.** RAFT operations are asynchronous. Reading results without calling `handle.sync()` gives undefined/stale data. If you omit the `handle` parameter, RAFT syncs internally (safe but slower).

- **Using RAFT for vector search.** Vector search (k-NN, IVFPQ, CAGRA, etc.) has been migrated to [cuVS](https://github.com/rapidsai/cuvs). RAFT no longer maintains these algorithms.

- **Wrong sparse format.** `eigsh()` requires `cupyx.scipy.sparse.csr_matrix`. Other sparse formats (COO, CSC) must be converted first.

- **Non-symmetric matrix with eigsh.** `eigsh` is for real symmetric / Hermitian matrices only. For general eigenvalue problems, you'll need a different solver.

- **dtype mismatch.** RAFT functions are picky about dtypes. Use `float32` or `float64` explicitly — don't rely on implicit conversion.
