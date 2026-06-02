# Numba CUDA Reference

Numba compiles Python directly into CUDA kernels, giving you full control over GPU threads, blocks, shared memory, and synchronization. Use Numba when your algorithm needs custom GPU logic that can't be expressed as standard array operations.

> **Full documentation:** https://numba.readthedocs.io/en/stable/cuda/index.html

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Core Concepts: Kernels, Threads, Blocks, Grids](#core-concepts)
3. [Writing CUDA Kernels](#writing-cuda-kernels)
4. [Thread Positioning](#thread-positioning)
5. [Memory Management](#memory-management)
6. [Shared Memory](#shared-memory)
7. [Device Functions](#device-functions)
8. [Atomic Operations](#atomic-operations)
9. [GPU Ufuncs: @vectorize and @guvectorize](#gpu-ufuncs)
10. [GPU Reductions](#gpu-reductions)
11. [Streams and Async Operations](#streams)
12. [Random Number Generation](#random-number-generation)
13. [Cooperative Groups](#cooperative-groups)
14. [Common Patterns for Scientific Computing](#common-patterns)
15. [Performance Optimization](#performance-optimization)
16. [Debugging](#debugging)
17. [Interoperability](#interoperability)
18. [Common Pitfalls](#common-pitfalls)

---

## Installation and Setup

Always use `uv add` (never `pip install` or `conda install`) in all install instructions, docstrings, comments, and error messages.

```bash
uv add numba numba-cuda
```

The `numba-cuda` package is the actively maintained NVIDIA implementation. It implements functionality under the `numba.cuda` namespace — no code changes needed vs the old built-in target.

**Requirements:** CUDA Toolkit >= 11.2, GPU with Compute Capability >= 5.0 (Maxwell or newer).

```python
from numba import cuda

# Verify GPU is available
print(cuda.is_available())   # True if CUDA works
cuda.detect()                # Prints GPU details
```

---

## Core Concepts

CUDA organizes parallel execution in a hierarchy:

```
Grid (of blocks) → Blocks (of threads) → Threads
```

- **Thread**: The smallest unit of execution. Each runs your kernel function.
- **Block**: A group of threads that can share fast on-chip memory and synchronize with each other. Max 1024 threads per block.
- **Grid**: The collection of all blocks for a kernel launch.

A **kernel** is a function that runs on the GPU, launched from the CPU. A **device function** runs on the GPU but is called from other GPU code (not from CPU).

---

## Writing CUDA Kernels

### The @cuda.jit Decorator

```python
from numba import cuda

@cuda.jit
def my_kernel(input_array, output_array):
    i = cuda.grid(1)                    # Get this thread's global index
    if i < input_array.size:            # Bounds check — ALWAYS do this
        output_array[i] = input_array[i] * 2.0
```

**Key parameters for @cuda.jit:**

| Parameter | Purpose |
|-----------|---------|
| `device=True` | Makes this a device function (callable from GPU only, can return values) |
| `fastmath=True` | Enables fast math (fast sqrt, division, FMA, trig/exp/log approximations on float32). Use when IEEE-754 strictness isn't required |
| `max_registers=N` | Limits registers per thread to increase occupancy |
| `cache=True` | Caches compiled kernel to disk |
| `debug=True` | Enables exception checking (slow — for debugging only, pair with `opt=False`) |
| `lineinfo=True` | Source line info for profiling without full debug overhead |

### Launching Kernels

```python
import numpy as np
from numba import cuda

data = np.random.rand(1_000_000).astype(np.float32)
out = np.zeros_like(data)

# Transfer to GPU
d_data = cuda.to_device(data)
d_out = cuda.device_array_like(out)

# Calculate launch configuration
threads_per_block = 256
blocks_per_grid = (data.size + threads_per_block - 1) // threads_per_block

# Launch
my_kernel[blocks_per_grid, threads_per_block](d_data, d_out)

# Get results back
result = d_out.copy_to_host()
```

**Launch syntax:** `kernel[grid_dim, block_dim, stream, dynamic_shared_mem_bytes](...args)`

The 3rd and 4th parameters are optional (stream and dynamic shared memory size in bytes).

### 2D Launch Configuration

```python
@cuda.jit
def kernel_2d(matrix, output):
    x, y = cuda.grid(2)
    if x < matrix.shape[0] and y < matrix.shape[1]:
        output[x, y] = matrix[x, y] * 2.0

threads = (16, 16)
blocks = (
    (matrix.shape[0] + threads[0] - 1) // threads[0],
    (matrix.shape[1] + threads[1] - 1) // threads[1],
)
kernel_2d[blocks, threads](d_matrix, d_output)
```

### Convenience: .forall() for 1D

```python
# Automatically computes grid dimensions for 1D
my_kernel.forall(len(data))(d_data, d_out)
```

### Critical Rules for Kernels

1. **Kernels CANNOT return values.** All output must be written to arrays passed as arguments.
2. **Always check array bounds.** If grid_size > array_size, out-of-bounds threads corrupt memory silently.
3. **Kernel launches are asynchronous.** Use `cuda.synchronize()` before reading results on the CPU.

---

## Thread Positioning

### Intrinsics

| Intrinsic | Description |
|-----------|-------------|
| `cuda.threadIdx.x/y/z` | Thread index within its block |
| `cuda.blockIdx.x/y/z` | Block index within the grid |
| `cuda.blockDim.x/y/z` | Threads per block |
| `cuda.gridDim.x/y/z` | Blocks in the grid |
| `cuda.grid(ndim)` | Absolute position in entire grid (1D → int, 2D/3D → tuple) |
| `cuda.gridsize(ndim)` | Total number of threads in entire grid |

### Grid-Stride Loop Pattern

For processing data larger than the grid, use a grid-stride loop. This decouples grid size from problem size and is essential for reusing RNG states.

```python
@cuda.jit
def process_large(data, out):
    start = cuda.grid(1)
    stride = cuda.gridsize(1)
    for i in range(start, data.shape[0], stride):
        out[i] = data[i] * 2.0
```

---

## Memory Management

### Data Transfer

```python
# Host → Device
d_array = cuda.to_device(numpy_array)                    # Synchronous copy
d_array = cuda.to_device(numpy_array, stream=stream)     # Async copy

# Allocate on device (no copy)
d_array = cuda.device_array(shape=(1000,), dtype=np.float32)
d_array = cuda.device_array_like(numpy_array)

# Device → Host
host_array = d_array.copy_to_host()                      # New array
d_array.copy_to_host(existing_array)                     # Into pre-allocated
d_array.copy_to_host(stream=stream)                      # Async
```

### Memory Types

| Type | API | Use Case |
|------|-----|----------|
| **Device** | `cuda.device_array()`, `cuda.to_device()` | Standard GPU memory |
| **Pinned** | `cuda.pinned_array()`, `cuda.pinned()` context manager | Page-locked host memory — faster transfers |
| **Mapped** | `cuda.mapped_array()` | Accessible from both host and device |
| **Managed** | `cuda.managed_array()` | Unified memory — auto-migrates between host/device (Linux/x86 recommended) |
| **Constant** | `cuda.const.array_like(arr)` | Read-only, cached, set from host |

### Pinned Memory for Fast Transfers

```python
# Allocate pinned host memory (page-locked — faster PCI-e transfers)
with cuda.pinned(host_array):
    d_array = cuda.to_device(host_array, stream=stream)
    # Transfer is faster because the OS can't page this memory out

# Or allocate directly
pinned = cuda.pinned_array(shape=(1000,), dtype=np.float32)
```

### Deallocation Control

```python
with cuda.defer_cleanup():
    # All GPU deallocation deferred here — avoids implicit synchronization
    # Use this in performance-critical sections
    run_many_kernels()
# Cleanup happens here
```

---

## Shared Memory

Shared memory is fast on-chip memory (tens of TB/s bandwidth) shared within a block. It's the key to high-performance kernels — use it to cache data that multiple threads in a block will access.

### Static Shared Memory (size known at compile time)

```python
from numba import cuda, float32

@cuda.jit
def kernel_with_shared(data, output):
    # Allocate shared memory — visible to all threads in this block
    shared = cuda.shared.array(256, dtype=float32)

    tid = cuda.threadIdx.x
    i = cuda.grid(1)

    # Each thread loads one element into shared memory
    if i < data.size:
        shared[tid] = data[i]

    # BARRIER: wait for ALL threads in block to finish loading
    cuda.syncthreads()

    # Now safe to read any element in shared[]
    if i < data.size and tid > 0:
        output[i] = shared[tid] + shared[tid - 1]
```

### Dynamic Shared Memory (size set at launch)

```python
@cuda.jit
def kernel_dynamic_shared(data):
    # size=0 means "use dynamic shared memory"
    dyn = cuda.shared.array(0, dtype=float32)
    tid = cuda.threadIdx.x
    dyn[tid] = data[cuda.grid(1)]
    cuda.syncthreads()
    # ...

# Specify size at launch (4th parameter = bytes)
kernel_dynamic_shared[blocks, threads, stream, 1024](data)  # 1024 bytes of shared mem
```

**Important:** All `cuda.shared.array(0, ...)` calls in the same kernel alias the same memory region. To use multiple dynamic shared arrays, take disjoint slices manually.

### Local Memory (per-thread scratchpad)

```python
@cuda.jit
def kernel_with_local(data):
    # Each thread gets its own private array
    local_buf = cuda.local.array(10, dtype=float32)
    i = cuda.grid(1)
    for j in range(10):
        local_buf[j] = data[i * 10 + j]
    # Process local_buf...
```

---

## Device Functions

Device functions run on the GPU and are called from kernels or other device functions. Unlike kernels, they **can return values**.

```python
@cuda.jit(device=True)
def compute_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

@cuda.jit
def kernel(points, distances):
    i = cuda.grid(1)
    if i < points.shape[0] - 1:
        distances[i] = compute_distance(
            points[i, 0], points[i, 1],
            points[i+1, 0], points[i+1, 1]
        )
```

**Cross-compilation note:** A function decorated with `@numba.jit` (CPU JIT) can also be called from CUDA kernels — useful for sharing logic between CPU and GPU code paths.

---

## Atomic Operations

Atomics ensure thread-safe updates to shared data. All return the **old** value.

```python
cuda.atomic.add(array, index, value)       # +=   (int32, float32, float64)
cuda.atomic.sub(array, index, value)       # -=   (int32, float32, float64)
cuda.atomic.max(array, index, value)       # max  (int/uint 32/64, float 32/64)
cuda.atomic.min(array, index, value)       # min  (same types)
cuda.atomic.nanmax(array, index, value)    # max ignoring NaN
cuda.atomic.nanmin(array, index, value)    # min ignoring NaN
cuda.atomic.and_(array, index, value)      # &=   (int/uint 32/64)
cuda.atomic.or_(array, index, value)       # |=   (int/uint 32/64)
cuda.atomic.xor(array, index, value)       # ^=   (int/uint 32/64)
cuda.atomic.exch(array, index, value)      # exchange
cuda.atomic.cas(array, index, old, value)  # compare-and-swap
```

Multi-dimensional indexing works via tuples: `cuda.atomic.add(result, (row, col), value)`

### Example: Histogram

```python
@cuda.jit
def histogram(data, bins):
    i = cuda.grid(1)
    if i < data.size:
        bin_idx = int(data[i] * len(bins))
        if 0 <= bin_idx < len(bins):
            cuda.atomic.add(bins, bin_idx, 1)
```

---

## GPU Ufuncs

### @vectorize — Element-wise Operations on GPU

The simplest way to run element-wise operations on GPU. Write a scalar function, Numba broadcasts it over arrays automatically.

```python
from numba import vectorize, float32, float64
import math

@vectorize([float32(float32, float32),
            float64(float64, float64)],
           target='cuda')
def gpu_hypot(x, y):
    return math.sqrt(x**2 + y**2)

# Usage — just call it like a NumPy ufunc
result = gpu_hypot(array_x, array_y)

# Pass device arrays to avoid transfers
d_x = cuda.to_device(x)
d_y = cuda.to_device(y)
d_result = gpu_hypot(d_x, d_y)
```

### @guvectorize — Generalized Ufuncs

For operations on sub-arrays (not just scalars). Uses NumPy's generalized ufunc signature.

```python
from numba import guvectorize, float32

@guvectorize([float32[:,:], float32[:,:], float32[:,:]],
             '(m,n),(n,p)->(m,p)', target='cuda')
def gpu_matmul(A, B, C):
    for i in range(A.shape[0]):
        for j in range(B.shape[1]):
            total = 0.0
            for k in range(A.shape[1]):
                total += A[i, k] * B[k, j]
            C[i, j] = total
```

---

## GPU Reductions

```python
from numba import cuda

# Define reduction operation
sum_reduce = cuda.reduce(lambda a, b: a + b)

# Use it
result = sum_reduce(array)                    # Full reduction
result = sum_reduce(array, init=0)            # With initial value
sum_reduce(array, res=device_result)          # Write to device array (no D→H copy)
sum_reduce(array, stream=stream)              # Async
```

Custom reduction:

```python
@cuda.reduce
def max_reduce(a, b):
    return a if a > b else b

maximum = max_reduce(data_array)
```

---

## Streams

Streams enable overlapping computation with data transfer and running multiple kernels concurrently.

```python
stream = cuda.stream()

# Async transfer → kernel → transfer back
d_data = cuda.to_device(host_data, stream=stream)
my_kernel[blocks, threads, stream](d_data, d_out)
result = d_out.copy_to_host(stream=stream)
stream.synchronize()  # Wait for everything on this stream

# Context manager that auto-synchronizes
with stream.auto_synchronize():
    d_data = cuda.to_device(host_data, stream=stream)
    my_kernel[blocks, threads, stream](d_data, d_out)
    result = d_out.copy_to_host(stream=stream)
# Synchronizes here automatically
```

### Pipeline Pattern (overlap transfer and compute)

```python
stream1 = cuda.stream()
stream2 = cuda.stream()

# Chunk 1: transfer on stream1
d_chunk1 = cuda.to_device(data[:half], stream=stream1)
# Chunk 2: transfer on stream2 (overlaps with stream1 transfer)
d_chunk2 = cuda.to_device(data[half:], stream=stream2)

# Process chunk1 on stream1
kernel[blocks, threads, stream1](d_chunk1, d_out1)
# Process chunk2 on stream2 (overlaps with stream1 compute)
kernel[blocks, threads, stream2](d_chunk2, d_out2)

cuda.synchronize()  # Wait for all streams
```

---

## Random Number Generation

Numba provides GPU-native random number generation using the xoroshiro128+ algorithm.

```python
from numba import cuda
from numba.cuda.random import (
    create_xoroshiro128p_states,
    xoroshiro128p_uniform_float32,
    xoroshiro128p_uniform_float64,
    xoroshiro128p_normal_float32,
    xoroshiro128p_normal_float64,
)

# Create RNG states — one per thread
n_threads = 256 * 128
rng_states = create_xoroshiro128p_states(n_threads, seed=42)

@cuda.jit
def monte_carlo_pi(rng_states, iterations, out):
    gid = cuda.grid(1)
    if gid < out.size:
        inside = 0
        for _ in range(iterations):
            x = xoroshiro128p_uniform_float32(rng_states, gid)
            y = xoroshiro128p_uniform_float32(rng_states, gid)
            if x**2 + y**2 <= 1.0:
                inside += 1
        out[gid] = inside / iterations * 4.0

monte_carlo_pi[128, 256](rng_states, 10000, d_out)
```

**Tip:** RNG states consume memory proportional to thread count. Use grid-stride loops to limit the number of states needed for large problems.

---

## Cooperative Groups

For algorithms requiring synchronization across ALL blocks in a grid (not just within a single block).

```python
@cuda.jit
def iterative_kernel(M):
    col = cuda.grid(1)
    g = cuda.cg.this_grid()  # Get grid group

    for row in range(1, M.shape[0]):
        M[row, col] = M[row - 1, col] + 1
        g.sync()  # Global barrier — all blocks wait here

# Query max grid size for cooperative launch
overload = iterative_kernel.overloads[signature]
max_blocks = overload.max_cooperative_grid_blocks(block_dim)
```

Cooperative launches are triggered automatically when `g.sync()` is detected. The grid must not exceed `max_cooperative_grid_blocks()`.

---

## Common Patterns

### Tiled Matrix Multiplication with Shared Memory

This is the canonical example of shared memory optimization — tiles of A and B are loaded into fast shared memory to reduce slow global memory accesses.

```python
from numba import cuda, float32
import numpy as np

TPB = 16  # Tile/block size

@cuda.jit
def matmul_shared(A, B, C):
    sA = cuda.shared.array((TPB, TPB), dtype=float32)
    sB = cuda.shared.array((TPB, TPB), dtype=float32)

    x, y = cuda.grid(2)
    tx, ty = cuda.threadIdx.x, cuda.threadIdx.y

    tmp = float32(0.0)
    for tile in range(cuda.gridDim.x):
        # Load tile into shared memory (with bounds check)
        col = tx + tile * TPB
        row = ty + tile * TPB
        sA[ty, tx] = A[y, col] if (y < A.shape[0] and col < A.shape[1]) else 0
        sB[ty, tx] = B[row, x] if (x < B.shape[1] and row < B.shape[0]) else 0
        cuda.syncthreads()

        # Compute partial dot product from this tile
        for k in range(TPB):
            tmp += sA[ty, k] * sB[k, tx]
        cuda.syncthreads()

    if y < C.shape[0] and x < C.shape[1]:
        C[y, x] = tmp
```

### Parallel Prefix Sum (Scan)

```python
@cuda.jit
def inclusive_scan(data, output):
    shared = cuda.shared.array(256, dtype=float32)
    tid = cuda.threadIdx.x
    i = cuda.grid(1)

    shared[tid] = data[i] if i < data.size else 0
    cuda.syncthreads()

    # Up-sweep
    offset = 1
    while offset < cuda.blockDim.x:
        if tid >= offset:
            shared[tid] += shared[tid - offset]
        offset *= 2
        cuda.syncthreads()

    if i < data.size:
        output[i] = shared[tid]
```

### Shared Memory Reduction

```python
@cuda.jit
def block_reduce_sum(data, partial_sums):
    shared = cuda.shared.array(256, dtype=float32)
    tid = cuda.threadIdx.x
    i = cuda.grid(1)

    shared[tid] = data[i] if i < data.size else 0.0
    cuda.syncthreads()

    # Tree reduction in shared memory
    s = cuda.blockDim.x // 2
    while s > 0:
        if tid < s:
            shared[tid] += shared[tid + s]
        s //= 2
        cuda.syncthreads()

    # Thread 0 of each block writes the block's sum
    if tid == 0:
        partial_sums[cuda.blockIdx.x] = shared[0]
```

### Stencil / Neighbor Access Pattern

```python
@cuda.jit
def stencil_1d(data, output, radius):
    shared = cuda.shared.array(288, dtype=float32)  # blockDim + 2*radius
    tid = cuda.threadIdx.x
    i = cuda.grid(1)

    # Load center + halo into shared memory
    shared[tid + radius] = data[i] if i < data.size else 0
    if tid < radius:
        shared[tid] = data[i - radius] if i >= radius else 0
        shared[tid + cuda.blockDim.x + radius] = (
            data[i + cuda.blockDim.x] if i + cuda.blockDim.x < data.size else 0
        )
    cuda.syncthreads()

    if i < data.size:
        total = float32(0.0)
        for j in range(-radius, radius + 1):
            total += shared[tid + radius + j]
        output[i] = total / (2 * radius + 1)
```

---

## Performance Optimization

### GPU-Specific Tips

1. **Minimize host-device transfers.** Use `cuda.to_device()` and keep data on GPU across multiple kernel calls. Every PCI-e transfer is expensive (~12 GB/s) vs GPU memory bandwidth (~900+ GB/s).

2. **Use shared memory** for data reused across threads in a block. Shared memory bandwidth is ~10-100x higher than global memory.

3. **Coalesce memory accesses.** Adjacent threads (consecutive `threadIdx.x`) should access adjacent memory locations. This lets the hardware combine accesses into fewer wide transactions.

4. **Choose block size for occupancy.** 128-256 threads/block for 1D, (16,16) or (32,32) for 2D. Too few threads underutilizes the GPU; too many may limit registers/shared memory per thread.

5. **Use `fastmath=True`** when IEEE-754 strictness isn't required. Enables FMA, fast sqrt/division, and faster trig/exp/log for float32.

6. **Prefer float32 over float64** when precision allows. GPU float32 throughput is 2x-32x higher depending on the GPU (consumer GPUs heavily penalize float64).

7. **Use streams** to overlap data transfer with computation.

8. **Use `cuda.defer_cleanup()`** in performance-critical sections to prevent implicit synchronization from memory deallocation.

9. **Limit register usage** with `max_registers` parameter when occupancy is the bottleneck.

10. **Use grid-stride loops** to decouple grid size from problem size and improve flexibility.

### What Not To Do

- Don't use Python objects, strings, or dynamic memory allocation inside kernels — Numba CUDA supports a restricted Python subset.
- Don't put `syncthreads()` inside divergent branches — if threads in a block take different paths through a barrier, behavior is undefined (deadlock or corruption).
- Don't forget `cuda.synchronize()` before reading results on CPU — kernel launches are async.
- Don't launch kernels with tiny data sizes — kernel launch overhead (~5-20us) dominates for small arrays.

---

## Debugging

### CUDA Simulator

Run CUDA code on CPU for debugging — supports `print()` and `pdb` inside kernels.

```bash
export NUMBA_ENABLE_CUDASIM=1
python your_script.py
```

The simulator runs kernels one block at a time, spawning one thread per CUDA thread. Supports shared/local/constant memory, atomics, and `syncthreads()`.

### Debug a Specific Thread

```python
@cuda.jit
def debug_kernel(data, out):
    i = cuda.grid(1)
    if cuda.threadIdx.x == 0 and cuda.blockIdx.x == 0:
        # Only thread (0,0) hits the debugger
        from pdb import set_trace; set_trace()
    if i < data.size:
        out[i] = data[i] * 2
```

### On-Device Debug Mode

```python
@cuda.jit(debug=True, opt=False)
def kernel_debug(data):
    # Enables CUDA exception checking — much slower but catches errors
    ...
```

---

## Interoperability

Numba supports the **CUDA Array Interface** (version 3) — any object exposing `__cuda_array_interface__` can be passed directly to Numba kernels with zero copy.

### With CuPy

```python
import cupy as cp
from numba import cuda

@cuda.jit
def add_kernel(x, y, out):
    i = cuda.grid(1)
    if i < x.shape[0]:
        out[i] = x[i] + y[i]

# CuPy arrays work directly — zero copy
a = cp.arange(1000, dtype=cp.float32)
b = cp.ones(1000, dtype=cp.float32)
out = cp.zeros(1000, dtype=cp.float32)
add_kernel[4, 256](a, b, out)
```

### With PyTorch

```python
import torch
from numba import cuda

t = torch.cuda.FloatTensor([1, 2, 3])
d_array = cuda.as_cuda_array(t)  # Zero-copy Numba view of PyTorch tensor
```

### Checking GPU Arrays

```python
cuda.is_cuda_array(obj)       # True if obj has __cuda_array_interface__
cuda.as_cuda_array(obj)       # Wrap as Numba device array (zero copy)
```

**Compatible libraries:** CuPy, PyTorch, JAX, PyCUDA, RAPIDS (cuDF, cuML), PyArrow, mpi4py, NVIDIA DALI.

---

## Common Pitfalls

1. **Forgetting bounds checks.** If `blocks * threads > array_size`, out-of-bounds threads corrupt memory silently. Always: `if i < array.size`.

2. **Trying to return values from kernels.** Kernels cannot return — write to output arrays instead. Return values are silently discarded.

3. **Implicit synchronous transfers.** Passing host (NumPy) arrays directly to kernels triggers synchronous copy-back. Use explicit `cuda.to_device()` / `copy_to_host()`.

4. **Shared memory size must be a compile-time constant** for static allocation. Use dynamic shared memory (size=0) for runtime-determined sizes.

5. **Dynamic shared memory aliasing.** All `cuda.shared.array(0, ...)` in the same kernel share the same memory. Slice manually for multiple arrays.

6. **`syncthreads()` in divergent branches.** All threads in a block must reach the same `syncthreads()` call. Divergent paths → undefined behavior.

7. **Atomic operation type restrictions.** `atomic.add` supports int32, float32, float64. Bitwise atomics only work on integer types.

8. **Forgetting `cuda.synchronize()`.** Kernel launches are async. Reading host-side results before sync gives stale/incomplete data.

9. **Unsupported Python features in kernels.** No dynamic allocation, no Python objects, no string operations, no exceptions (unless debug mode). Stick to numeric types and math.

10. **Using float64 on consumer GPUs.** Consumer NVIDIA GPUs (GeForce) have heavily throttled float64 throughput (often 1/32 of float32). Use float32 unless you need the precision.
