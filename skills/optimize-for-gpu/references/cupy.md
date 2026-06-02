# CuPy Reference

CuPy is a NumPy/SciPy-compatible array library for GPU-accelerated computing. It wraps NVIDIA's optimized libraries (cuBLAS, cuFFT, cuSOLVER, cuSPARSE, cuRAND) so standard array operations are already highly tuned. Most NumPy code works by simply changing the import.

> **Full documentation:** https://docs.cupy.dev/en/stable/

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [The Drop-In Replacement Pattern](#the-drop-in-replacement-pattern)
3. [Core API: cupy.ndarray](#core-api)
4. [Supported Operations](#supported-operations)
5. [Custom Kernels](#custom-kernels)
6. [Kernel Fusion](#kernel-fusion)
7. [Memory Management](#memory-management)
8. [Streams and Async Operations](#streams-and-async-operations)
9. [Multi-GPU](#multi-gpu)
10. [Performance Optimization](#performance-optimization)
11. [Interoperability](#interoperability)
12. [Key Differences from NumPy](#key-differences-from-numpy)
13. [Common Pitfalls](#common-pitfalls)
14. [Environment Variables](#environment-variables)

---

## Installation and Setup

Always use `uv add` (never `pip install` or `conda install`) in all install instructions, docstrings, comments, and error messages.

```bash
uv add cupy-cuda12x    # For CUDA 12.x (most common)
```

Verify:
```python
import cupy as cp
print(cp.cuda.runtime.getDeviceCount())  # >= 1 means GPU is available
print(cp.show_config())                  # Full environment info
```

---

## The Drop-In Replacement Pattern

The fastest way to GPU-accelerate NumPy code: change the import.

```python
# Before (CPU)
import numpy as np
a = np.random.rand(10_000_000)
b = np.fft.fft(a)
c = np.sort(b.real)

# After (GPU)
import cupy as cp
a = cp.random.rand(10_000_000)
b = cp.fft.fft(a)
c = cp.sort(b.real)
```

### Data Transfer Between CPU and GPU

```python
# NumPy → CuPy (CPU → GPU)
gpu_array = cp.asarray(numpy_array)     # Zero-copy if already on current device
gpu_array = cp.array(numpy_array)       # Always copies

# CuPy → NumPy (GPU → CPU)
cpu_array = cp.asnumpy(gpu_array)       # Copy to CPU
cpu_array = gpu_array.get()             # Same thing
```

### Writing CPU/GPU Agnostic Code

```python
def normalize(x):
    xp = cp.get_array_module(x)  # Returns cupy or numpy depending on input
    return x / xp.linalg.norm(x)

# Works with both NumPy and CuPy arrays
normalize(numpy_array)   # Runs on CPU
normalize(cupy_array)    # Runs on GPU
```

CuPy arrays implement `__array_ufunc__` and `__array_function__`, so NumPy functions can dispatch to CuPy automatically when given CuPy arrays (NumPy >= 1.17).

---

## Core API

`cupy.ndarray` mirrors `numpy.ndarray` — same attributes (`shape`, `dtype`, `ndim`, `size`, `strides`, `T`), plus `device` (which GPU the array lives on).

**Important:** `cupy.ndarray` and `numpy.ndarray` are NOT implicitly convertible. Every conversion incurs a host-device data transfer.

### Array Creation

```python
cp.empty((1000, 1000), dtype=cp.float32)
cp.zeros((1000,), dtype=cp.float64)
cp.ones((512, 512), dtype=cp.float32)
cp.full((100,), fill_value=3.14, dtype=cp.float32)
cp.arange(0, 100, 0.1)
cp.linspace(0, 1, 1000)
cp.eye(100)
cp.random.rand(1000, 1000)                    # Uniform [0, 1)
cp.random.randn(1000, 1000)                   # Standard normal
cp.random.default_rng(42).normal(0, 1, 1000)  # Generator API
```

CuPy's random supports a `dtype` argument (float32/float64) — unlike NumPy which always returns float64. Use `dtype=cp.float32` when you don't need double precision.

---

## Supported Operations

CuPy implements most of NumPy and large parts of SciPy. All are GPU-accelerated.

### Array Math and Element-wise Operations
`sin`, `cos`, `tan`, `exp`, `log`, `log2`, `log10`, `sqrt`, `square`, `abs`, `power`, `add`, `subtract`, `multiply`, `divide`, `mod`, `clip`, `sign`, `ceil`, `floor`, `round`, `maximum`, `minimum`

### Reductions
`sum`, `prod`, `mean`, `std`, `var`, `min`, `max`, `argmin`, `argmax`, `cumsum`, `cumprod`, `any`, `all`, `nansum`, `nanmean`, `nanstd`, `nanvar`

### Linear Algebra (`cupy.linalg` — powered by cuBLAS/cuSOLVER)
`dot`, `matmul`, `@` operator, `tensordot`, `einsum`, `inner`, `outer`, `cholesky`, `qr`, `svd`, `eig`, `eigh`, `eigvalsh`, `norm`, `solve`, `inv`, `pinv`, `lstsq`, `det`, `slogdet`, `matrix_rank`, `matrix_power`

### FFT (`cupy.fft` — powered by cuFFT)
`fft`, `ifft`, `fft2`, `ifft2`, `fftn`, `ifftn`, `rfft`, `irfft`, `rfft2`, `irfft2`, `rfftn`, `irfftn`, `fftfreq`, `rfftfreq`, `fftshift`, `ifftshift`

### Sorting and Searching
`sort`, `argsort`, `partition`, `argpartition`, `argmin`, `argmax`, `where`, `nonzero`, `unique`, `searchsorted`

### Array Manipulation
`reshape`, `ravel`, `flatten`, `transpose`, `swapaxes`, `concatenate`, `stack`, `vstack`, `hstack`, `dstack`, `split`, `hsplit`, `vsplit`, `tile`, `repeat`, `pad`, `flip`, `fliplr`, `flipud`, `roll`, `rot90`, `broadcast_to`, `expand_dims`, `squeeze`

### Sparse Matrices (`cupyx.scipy.sparse`)
CSR, CSC, COO formats. Matrix-vector multiply, matrix-matrix multiply, conversions between formats. Powered by cuSPARSE.

### Signal Processing (`cupyx.scipy.signal`)
Convolution, correlation, filtering, window functions.

### Special Functions (`cupyx.scipy.special`)
Bessel functions, error functions, gamma functions, and more.

### Statistics
`mean`, `median`, `std`, `var`, `percentile`, `quantile`, `corrcoef`, `cov`, `histogram`, `bincount`, `digitize`

---

## Custom Kernels

When built-in operations aren't enough, CuPy offers several ways to write custom GPU code, ordered from simplest to most powerful.

### ElementwiseKernel — Custom Element-wise Operations

CuPy handles indexing and broadcasting automatically. You just write the per-element logic in C++.

```python
squared_diff = cp.ElementwiseKernel(
    'float32 x, float32 y',   # Input params
    'float32 z',               # Output params
    'z = (x - y) * (x - y)',  # Per-element operation (C++ code)
    'squared_diff'             # Kernel name
)

result = squared_diff(a, b)  # Broadcasting works automatically
```

**Type-generic kernels:** Use single-letter type placeholders. Same letter = same type, resolved from arguments at call time.

```python
generic_squared_diff = cp.ElementwiseKernel(
    'T x, T y', 'T z',
    'z = (x - y) * (x - y)',
    'generic_squared_diff'
)
# Works with float32, float64, etc. — type inferred from inputs
```

**Raw indexing:** Prefix with `raw` to disable automatic indexing. Use `i` for loop index.

```python
# Access neighbors — raw disables auto-indexing so you can index manually
stencil = cp.ElementwiseKernel(
    'raw T x', 'T y',
    'y = (x[i > 0 ? i-1 : 0] + x[i] + x[i < _ind.size()-1 ? i+1 : _ind.size()-1]) / 3',
    'stencil_1d'
)
```

### ReductionKernel — Custom Reductions

Four-part reduction: map each element, reduce pairs, post-process the result.

```python
l2norm = cp.ReductionKernel(
    'T x',           # Input
    'T y',           # Output
    'x * x',         # Map: square each element
    'a + b',         # Reduce: sum pairs (a, b are the binary operands)
    'y = sqrt(a)',   # Post-map: sqrt of final sum
    '0',             # Identity element
    'l2norm'         # Kernel name
)

norm = l2norm(array)        # Full reduction → scalar
norms = l2norm(matrix, axis=1)  # Reduce along axis → vector
```

### RawKernel — Full CUDA C/C++

For complete control over grid, blocks, shared memory — write raw CUDA.

```python
kernel_code = r'''
extern "C" __global__
void vector_add(const float* a, const float* b, float* c, int n) {
    int tid = blockDim.x * blockIdx.x + threadIdx.x;
    if (tid < n) {
        c[tid] = a[tid] + b[tid];
    }
}
'''
vector_add = cp.RawKernel(kernel_code, 'vector_add')

n = 1_000_000
a = cp.random.rand(n, dtype=cp.float32)
b = cp.random.rand(n, dtype=cp.float32)
c = cp.zeros(n, dtype=cp.float32)

threads = 256
blocks = (n + threads - 1) // threads
vector_add((blocks,), (threads,), (a, b, c, n))  # (grid, block, args)
```

**Important RawKernel caveats:**
- Ignores array views/strides — `matrix.T` is treated as `matrix`. Handle strides yourself.
- Use `extern "C"` to prevent C++ name mangling.
- For complex numbers, include `<cupy/complex.cuh>`.
- Compiled binaries cached in `~/.cupy/kernel_cache`.

**CuPy dtype to CUDA type mapping:**

| CuPy dtype | CUDA type |
|-----------|-----------|
| `float16` | `half` |
| `float32` | `float` |
| `float64` | `double` |
| `int32` | `int` |
| `int64` | `long long` |
| `complex64` | `complex<float>` |
| `complex128` | `complex<double>` |

### RawModule — Large CUDA Codebases

For multi-kernel CUDA files or precompiled binaries:

```python
module = cp.RawModule(code=cuda_source)       # From source string
module = cp.RawModule(path='kernels.cu')      # From file
module = cp.RawModule(path='kernels.cubin')   # From precompiled

kernel = module.get_function('my_kernel')
kernel((blocks,), (threads,), (args...))
```

### JIT Kernel (cupyx.jit.rawkernel) — CUDA Kernels in Python Syntax

Write CUDA-style kernels using Python syntax instead of C++.

```python
@cupyx.jit.rawkernel()
def my_kernel(x, y, size):
    tid = cupyx.jit.grid(1)
    if tid < size:
        y[tid] = x[tid] * 2.0

my_kernel[blocks, threads](x, y, n)
```

Available JIT primitives:
- `cupyx.jit.threadIdx`, `blockIdx`, `blockDim`, `gridDim`
- `cupyx.jit.grid(ndim)`, `gridsize(ndim)`
- `cupyx.jit.syncthreads()`, `syncwarp()`
- `cupyx.jit.shared_memory(dtype, size)`
- `cupyx.jit.atomic_add/min/max/and/or/xor(array, index, value)`
- Warp shuffles: `shfl_sync`, `shfl_up_sync`, `shfl_down_sync`, `shfl_xor_sync`

**Limitation:** Does not work in Python REPL (needs source code access). Use from .py files.

---

## Kernel Fusion

Combine multiple element-wise operations into a single kernel launch — eliminates intermediate arrays and reduces kernel launch overhead.

```python
@cp.fuse()
def fused_op(x, y):
    return cp.sqrt((x - y) ** 2 + 1.0)

# This compiles into ONE kernel instead of multiple
result = fused_op(a, b)
```

**Limitation:** Only fuses elementwise and simple reduction operations. Does not support `matmul`, `reshape`, indexing, etc.

---

## Memory Management

### Memory Pools (Default Behavior)

CuPy uses memory pools by default — this is critical for performance. The pool caches freed GPU memory for reuse, avoiding expensive `cudaMalloc`/`cudaFree` calls and implicit synchronization.

**Key insight:** Memory is NOT freed to the OS when arrays go out of scope — it's returned to the pool. This is expected behavior (shows up in `nvidia-smi` as still-allocated).

```python
mempool = cp.get_default_memory_pool()
mempool.used_bytes()        # Currently allocated by CuPy arrays
mempool.total_bytes()       # Total held by pool (including free blocks)
mempool.free_all_blocks()   # Release all unused memory back to OS

pinned_mempool = cp.get_default_pinned_memory_pool()
pinned_mempool.free_all_blocks()
```

### Limiting GPU Memory

```python
mempool = cp.get_default_memory_pool()
with cp.cuda.Device(0):
    mempool.set_limit(size=4 * 1024**3)  # 4 GiB limit for GPU 0
```

Or via environment variable (set before `import cupy`):
```bash
export CUPY_GPU_MEMORY_LIMIT="50%"     # Percentage of total GPU memory
export CUPY_GPU_MEMORY_LIMIT="4294967296"  # Bytes
```

### Managed (Unified) Memory

Data auto-migrates between CPU and GPU. Useful when data doesn't fit in GPU memory.

```python
cp.cuda.set_allocator(cp.cuda.MemoryPool(cp.cuda.malloc_managed).malloc)
```

### Pinned Memory for Fast Transfers

```python
# High-level API
pinned_array = cupyx.empty_pinned((1000,), dtype=np.float32)
pinned_array = cupyx.zeros_pinned((1000,), dtype=np.float32)

# These are NumPy arrays backed by page-locked memory — transfers to GPU are faster
```

### Disabling Pools

```python
cp.cuda.set_allocator(None)                    # Disable device pool
cp.cuda.set_pinned_memory_allocator(None)      # Disable pinned pool
```

Must be done before any CuPy operations.

### Using RMM (RAPIDS Memory Manager)

When using CuPy alongside cuDF/RAPIDS, align on a single allocator:

```python
import rmm
rmm.reinitialize(pool_allocator=True)
cp.cuda.set_allocator(rmm.rmm_cupy_allocator)
```

---

## Streams and Async Operations

Streams enable overlapping computation with data transfer and running multiple operations concurrently.

```python
stream = cp.cuda.Stream()

# Context manager style
with stream:
    d_data = cp.asarray(host_data)     # H→D transfer on this stream
    result = cp.sum(d_data)            # Kernel on this stream
# Operations enqueued but may not be complete here

stream.synchronize()  # Wait for all operations on this stream
```

### Multiple Streams for Overlap

```python
s1 = cp.cuda.Stream()
s2 = cp.cuda.Stream()

with s1:
    d_a = cp.asarray(data_a)
    result_a = cp.fft.fft(d_a)

with s2:
    d_b = cp.asarray(data_b)  # Overlaps with s1's FFT
    result_b = cp.fft.fft(d_b)

cp.cuda.Device().synchronize()  # Wait for all streams
```

### Events for Timing

```python
start = cp.cuda.Event()
end = cp.cuda.Event()

start.record()
# ... GPU operations ...
end.record()
end.synchronize()

elapsed_ms = cp.cuda.get_elapsed_time(start, end)
```

### Per-Thread Default Stream

```bash
export CUPY_CUDA_PER_THREAD_DEFAULT_STREAM=1
```

Enables per-thread default streams for better concurrency in multi-threaded applications.

---

## Multi-GPU

```python
# Set current device
cp.cuda.Device(0).use()

# Context manager
with cp.cuda.Device(1):
    x = cp.array([1, 2, 3])  # Allocated on GPU 1

# Check which device an array is on
print(x.device)  # Device 1
```

Cross-device operations may work via P2P (peer-to-peer) memory access if the GPU topology supports it. Use `cp.asarray()` to explicitly transfer arrays between devices.

### Per-Device Memory Limits

```python
mempool = cp.get_default_memory_pool()
with cp.cuda.Device(0):
    mempool.set_limit(size=4 * 1024**3)
with cp.cuda.Device(1):
    mempool.set_limit(size=4 * 1024**3)
```

---

## Performance Optimization

### Benchmarking (Critical First Step)

**Never use `time.perf_counter()` or `%timeit` for GPU code** — they measure only CPU time, not GPU execution time. CuPy operations are asynchronous.

```python
from cupyx.profiler import benchmark

result = benchmark(my_function, (arg1, arg2), n_repeat=100, n_warmup=10)
print(result)  # Shows CPU and GPU elapsed times with statistics
```

In IPython/Jupyter:
```python
%load_ext cupy
%gpu_timeit my_function(args)
```

### One-Time Overheads

- **Context initialization:** First CuPy call may take 1-5 seconds (CUDA context creation). This is one-time.
- **Kernel JIT compilation:** First call to any operation triggers on-the-fly kernel compilation. Cached in `~/.cupy/kernel_cache`. Persist this directory across CI/CD runs.

### CUB and cuTENSOR Acceleration

```bash
# CuPy v11+ uses CUB by default
export CUPY_ACCELERATORS=cub          # CUB only (default)
export CUPY_ACCELERATORS=cub,cutensor # Both (requires cuTENSOR installed)
```

CUB accelerates: reductions (`sum`, `prod`, `amin`, `amax`, `argmin`, `argmax`), inclusive scans (`cumsum`), histograms, sparse matrix-vector multiply, and `ReductionKernel`. Can provide ~100x speedup for reductions.

cuTENSOR accelerates: binary elementwise ufuncs, reduction, tensor contraction.

### Key Optimization Strategies

1. **Prefer float32 over float64.** Consumer GPUs have 2x-32x higher float32 throughput. Use `dtype=cp.float32` when precision allows.

2. **Minimize CPU-GPU transfers.** Every `cp.asnumpy()` / `.get()` triggers synchronization and PCI-e transfer. Keep data on GPU as long as possible.

3. **Use kernel fusion.** `@cp.fuse()` combines multiple elementwise operations into one kernel, eliminating intermediate arrays.

4. **Batch operations.** Fewer large operations beat many small ones (kernel launch overhead ~5-20us each).

5. **Pre-allocate output arrays.** Use `out=` parameter in ufuncs to avoid repeated allocation:
   ```python
   cp.add(a, b, out=result)  # Writes into existing array
   ```

6. **Use in-place operations.** `a += b` avoids allocating a new array.

7. **Use streams** to overlap computation and data transfer.

8. **Profile with NVTX markers** for Nsight Systems analysis:
   ```python
   with cupyx.profiler.time_range('my_operation', color_id=0):
       result = heavy_computation()
   ```

### Decision Tree: Which Kernel Approach?

1. **Can be expressed as NumPy ops?** → Use built-in CuPy functions (fastest development, often best performance)
2. **Multiple chained elementwise ops?** → Use `@cp.fuse()`
3. **Custom elementwise with broadcasting?** → Use `ElementwiseKernel`
4. **Custom reduction?** → Use `ReductionKernel`
5. **Need full grid/block/shared memory control?** → Use `RawKernel` or `cupyx.jit.rawkernel`
6. **Large CUDA codebase?** → Use `RawModule`

---

## Interoperability

CuPy interoperates with other GPU libraries via the CUDA Array Interface and DLPack protocol — both enable zero-copy data sharing.

### NumPy

```python
# NumPy functions auto-dispatch to CuPy (NumPy >= 1.17)
import numpy as np
result = np.sum(cupy_array)  # Dispatches to CuPy, returns CuPy array
```

### Numba

```python
from numba import cuda

@cuda.jit
def numba_kernel(x, y):
    i = cuda.grid(1)
    if i < x.shape[0]:
        y[i] = x[i] * 2

# CuPy arrays pass directly to Numba kernels — zero copy
a = cp.arange(1000, dtype=cp.float32)
b = cp.zeros_like(a)
numba_kernel[4, 256](a, b)
```

### PyTorch

```python
import torch

# CuPy → PyTorch (zero copy via CUDA Array Interface)
cupy_array = cp.array([1.0, 2.0, 3.0], dtype=cp.float32)
torch_tensor = torch.as_tensor(cupy_array, device='cuda')

# PyTorch → CuPy (zero copy)
cupy_array = cp.asarray(torch_tensor)

# Via DLPack (also zero copy)
cupy_array = cp.from_dlpack(torch_tensor)
torch_tensor = torch.from_dlpack(cupy_array)
```

### cuDF

```python
import cudf

# cuDF → CuPy
arr = df.to_cupy()
arr = cp.asarray(df['column'])

# CuPy → cuDF
df = cudf.DataFrame(cupy_array)
s = cudf.Series(cupy_array)
```

### Raw Pointer Interop

```python
# Export pointer
ptr = cupy_array.data.ptr  # Raw device pointer as int

# Import foreign pointer
mem = cp.cuda.UnownedMemory(ptr, size_bytes, owner=owner_obj)
memptr = cp.cuda.MemoryPointer(mem, offset=0)
arr = cp.ndarray(shape, dtype, memptr=memptr)
```

---

## Key Differences from NumPy

These are the behavioral differences that can cause bugs if you're not aware of them.

1. **Reductions return 0-d arrays, not scalars.** `cp.sum(a)` returns a 0-d `cupy.ndarray`, not a Python float. This avoids implicit GPU-CPU synchronization. Use `.item()` if you need a scalar.

2. **Out-of-bounds indexing wraps silently.** NumPy raises `IndexError`; CuPy wraps around without error.

3. **Duplicate indices in assignment are undefined.** `a[[0, 0]] = [1, 2]` — NumPy stores the last value; CuPy stores an undefined value (GPU race condition).

4. **Float-to-integer casts differ at edges.** Casting negative float to unsigned int or infinity to int gives different results than NumPy.

5. **No string/object dtypes.** CuPy only supports numeric types. No structured arrays with string fields.

6. **CuPy ufuncs require CuPy arrays.** Unlike NumPy ufuncs, CuPy ufuncs don't accept lists or NumPy arrays — convert first.

7. **Random seed arrays are hashed.** Array seeds produce less entropy than NumPy's approach.

---

## Common Pitfalls

1. **Measuring with CPU timers.** GPU operations are async. `time.perf_counter()` measures only the time to *enqueue* operations, not execute them. Always use `cupyx.profiler.benchmark()`.

2. **Unnecessary round-trips.** Every `cp.asnumpy()` / `.get()` syncs the GPU and copies data across PCI-e. Restructure code to keep data on GPU.

3. **"Memory leak" from pools.** The memory pool caches freed blocks. `nvidia-smi` shows them as allocated. Use `mempool.free_all_blocks()` to release.

4. **First-call latency.** CUDA context init + kernel JIT compilation. Warm up before benchmarking.

5. **Mixing devices.** Using an array from GPU 0 on GPU 1 without explicit transfer can fail or be slow.

6. **RawKernel ignoring views.** Transposed or sliced arrays passed to RawKernel are treated as the original contiguous layout. You must handle strides manually.

7. **Forgetting `synchronize()` before reading results.** If you pass data back to CPU or use it in non-CuPy code, ensure the GPU is done first.

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `CUPY_ACCELERATORS` | Backend list: `cub`, `cutensor` (default: `cub` for v11+) |
| `CUPY_CACHE_DIR` | Kernel cache directory (default: `~/.cupy/kernel_cache`) |
| `CUPY_GPU_MEMORY_LIMIT` | GPU memory limit (bytes or `"50%"`) |
| `CUPY_CACHE_SAVE_CUDA_SOURCE` | Set `1` to dump kernel source for profiling |
| `CUPY_CUDA_PER_THREAD_DEFAULT_STREAM` | Set `1` for per-thread default streams |
