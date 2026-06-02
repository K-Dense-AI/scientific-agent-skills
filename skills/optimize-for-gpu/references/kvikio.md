# KvikIO Reference — High-Performance GPU File IO

KvikIO is a Python and C++ library for high-performance file IO. It provides bindings to NVIDIA cuFile, enabling GPUDirect Storage (GDS) — reading and writing data directly between storage and GPU memory, bypassing CPU memory entirely. When GDS isn't available, KvikIO falls back gracefully to POSIX IO while still handling both host and device data seamlessly.

KvikIO is part of the RAPIDS ecosystem and interoperates with CuPy, cuDF, Numba, and other GPU libraries.

## Table of Contents

1. [Installation](#installation)
2. [When to Use KvikIO](#when-to-use-kvikio)
3. [CuFile — Local File IO](#cufile--local-file-io)
4. [RemoteFile — S3, HTTP, WebHDFS](#remotefile--s3-http-webhdfs)
5. [Zarr Integration](#zarr-integration)
6. [Memory-Mapped Files](#memory-mapped-files)
7. [Runtime Settings](#runtime-settings)
8. [Performance Optimization](#performance-optimization)
9. [Interoperability](#interoperability)
10. [Common Patterns](#common-patterns)
11. [Common Pitfalls](#common-pitfalls)

---

## Installation

```bash
# CUDA 12.x
uv add kvikio-cu12

# CUDA 13.x
uv add kvikio-cu13

# For Zarr support (optional)
uv add zarr
```

Verify installation:

```python
import kvikio
# Check if GDS is available
import kvikio.cufile_driver
print(kvikio.cufile_driver.get("is_gds_available"))  # True if GDS is set up
```

---

## When to Use KvikIO

Use KvikIO when:
- **Loading large binary data directly to GPU** — avoids the CPU-memory copy that standard `open()` or NumPy's `fromfile()` would require
- **Writing GPU arrays to disk** — saves directly from device memory without copying to host first
- **Reading from remote storage (S3, HTTP, WebHDFS) into GPU memory** — skips the host-memory staging step
- **Working with Zarr arrays on GPU** — the GDSStore backend reads chunks directly into CuPy arrays
- **IO is the bottleneck** — GDS can achieve close to raw NVMe bandwidth (6-7 GB/s per drive) vs standard IO that tops out at CPU-memory bandwidth
- **Overlapping IO and compute** — non-blocking reads/writes let you pipeline data loading with GPU computation

KvikIO is a poor fit when:
- Data is small (< 1 MB) — kernel launch and GDS overhead dominate
- You're reading structured formats (CSV, Parquet, JSON) — use cuDF instead, which has its own optimized readers
- You only need host memory — standard Python IO is simpler

---

## CuFile — Local File IO

`kvikio.CuFile` is the primary interface for local file IO. It replaces Python's `open()` for GPU workloads.

### Basic Usage

```python
import cupy as cp
import kvikio

# Write a GPU array to disk
a = cp.arange(1_000_000, dtype=cp.float32)
with kvikio.CuFile("data.bin", "w") as f:
    f.write(a)

# Read it back
b = cp.empty(1_000_000, dtype=cp.float32)
with kvikio.CuFile("data.bin", "r") as f:
    f.read(b)

assert cp.all(a == b)
```

### API Methods

| Method | Blocking | Description |
|--------|----------|-------------|
| `read(buf, size, file_offset)` | Yes | Read into device or host buffer |
| `write(buf, size, file_offset)` | Yes | Write from device or host buffer |
| `pread(buf, size, file_offset)` | No | Non-blocking parallel read, returns `IOFuture` |
| `pwrite(buf, size, file_offset)` | No | Non-blocking parallel write, returns `IOFuture` |
| `raw_read(buf, size, file_offset)` | Yes | Low-level single-thread read (device only) |
| `raw_write(buf, size, file_offset)` | Yes | Low-level single-thread write (device only) |
| `raw_read_async(buf, stream, size, file_offset)` | No | CUDA-stream async read (device only) |
| `raw_write_async(buf, stream, size, file_offset)` | No | CUDA-stream async write (device only) |

File modes: `"r"` (read), `"w"` (write/truncate), `"a"` (append), `"+"` (read+write).

### Non-Blocking IO with Futures

`pread` and `pwrite` split the operation into tasks executed in a thread pool and return an `IOFuture`:

```python
import cupy as cp
import kvikio

data = cp.empty(10_000_000, dtype=cp.float32)

with kvikio.CuFile("data.bin", "r") as f:
    # Launch two non-blocking reads for different sections
    future1 = f.pread(data[:5_000_000])
    future2 = f.pread(data[5_000_000:], file_offset=5_000_000 * 4)

    # Do other work while IO happens...

    # Wait for completion
    bytes_read1 = future1.get()
    bytes_read2 = future2.get()
```

### Partial Reads and Writes

```python
import cupy as cp
import kvikio

# Read only a portion of a file
buf = cp.empty(1000, dtype=cp.float32)
with kvikio.CuFile("data.bin", "r") as f:
    # Read 1000 floats starting at byte offset 4000
    f.read(buf, size=4000, file_offset=4000)
```

### Host Memory Support

KvikIO handles host memory transparently — no special API needed:

```python
import numpy as np
import kvikio

# Write from host memory
a = np.arange(1_000_000, dtype=np.float32)
with kvikio.CuFile("data.bin", "w") as f:
    f.write(a)

# Read into host memory
b = np.empty_like(a)
with kvikio.CuFile("data.bin", "r") as f:
    f.read(b)
```

### GDS Alignment

GDS works best with page-aligned IO. The GPU page size is 4 KiB (4096 bytes):
- **File offset**: should be a multiple of 4096
- **Transfer size**: should be a multiple of 4096

KvikIO handles unaligned IO correctly but splits it into aligned and unaligned parts, so aligned IO will be faster.

---

## RemoteFile — S3, HTTP, WebHDFS

`kvikio.RemoteFile` reads remote files directly into GPU or host memory.

### HTTP/HTTPS

```python
import cupy as cp
import kvikio

buf = cp.empty(1_000_000, dtype=cp.float32)
with kvikio.RemoteFile.open_http("https://example.com/data.bin") as f:
    print(f.nbytes())  # File size
    f.read(buf)
```

### AWS S3

```python
import cupy as cp
import kvikio

# Using bucket + object name (requires AWS env vars or explicit credentials)
with kvikio.RemoteFile.open_s3("my-bucket", "data/file.bin") as f:
    buf = cp.empty(f.nbytes(), dtype=cp.uint8)
    f.read(buf)

# Using S3 URL
with kvikio.RemoteFile.open_s3_url("s3://my-bucket/data/file.bin") as f:
    buf = cp.empty(f.nbytes(), dtype=cp.uint8)
    f.read(buf)

# Public S3 (no credentials needed)
with kvikio.RemoteFile.open_s3_public("s3://public-bucket/data.bin") as f:
    buf = cp.empty(f.nbytes(), dtype=cp.uint8)
    f.read(buf)

# Presigned URL
with kvikio.RemoteFile.open_s3_presigned_url(presigned_url) as f:
    buf = cp.empty(f.nbytes(), dtype=cp.uint8)
    f.read(buf)
```

AWS credentials come from environment variables (`AWS_DEFAULT_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) or can be passed as keyword arguments.

### Auto-Detect Endpoint Type

```python
import kvikio

# KvikIO figures out the protocol from the URL
with kvikio.RemoteFile.open("s3://bucket/object") as f:
    ...

with kvikio.RemoteFile.open("https://example.com/file.bin") as f:
    ...
```

### WebHDFS

```python
import kvikio

with kvikio.RemoteFile.open_webhdfs("http://namenode:9870/path/to/file") as f:
    buf = cp.empty(f.nbytes(), dtype=cp.uint8)
    f.read(buf)
```

### Host Memory with RemoteFile

RemoteFile reads into host memory just as easily:

```python
import numpy as np
import kvikio

with kvikio.RemoteFile.open_http("https://example.com/data.bin") as f:
    buf = np.empty(f.nbytes(), dtype=np.uint8)
    f.read(buf)
```

---

## Zarr Integration

KvikIO provides a GPU store backend for Zarr (version 3.x). This enables reading and writing chunked N-dimensional arrays directly in GPU memory via GDS.

```python
import zarr
from kvikio.zarr import GDSStore

# Enable GPU support in Zarr
zarr.config.enable_gpu()

# Create a GDS-backed store
store = GDSStore(root="data.zarr")

# Create and write a Zarr array (data stays on GPU)
z = zarr.create_array(
    store=store,
    shape=(1000, 1000),
    chunks=(100, 100),
    dtype="float32",
    overwrite=True,
)

# Reading returns CuPy arrays
chunk = z[:100, :100]  # Returns cupy.ndarray
```

Zarr + KvikIO is useful for:
- Climate/weather data (large multi-dimensional arrays)
- Bioinformatics (genomic arrays)
- Any workload using chunked arrays that need GPU processing

Requires: `uv add zarr` in addition to kvikio.

---

## Memory-Mapped Files

`kvikio.mmap.Mmap` provides memory-mapped file access with support for both host and device destinations:

```python
from kvikio.mmap import Mmap
import cupy as cp

# Map a file for reading
with Mmap("data.bin", flags="r") as m:
    print(m.file_size())

    # Sequential read into device memory
    buf = cp.empty(1000, dtype=cp.float32)
    m.read(buf, size=4000, offset=0)

    # Parallel read (returns IOFuture)
    future = m.pread(buf, size=4000, offset=0)
    future.get()
```

---

## Runtime Settings

KvikIO behavior is controlled via environment variables or the `kvikio.defaults` API.

### Key Settings

| Setting | Env Variable | Default | Description |
|---------|-------------|---------|-------------|
| Compatibility mode | `KVIKIO_COMPAT_MODE` | `AUTO` | `ON`: POSIX only, `OFF`: GDS only, `AUTO`: try GDS, fall back |
| Thread pool size | `KVIKIO_NTHREADS` | 1 | Number of IO threads for `pread`/`pwrite` |
| Task size | `KVIKIO_TASK_SIZE` | 4 MiB | Max size per parallel IO task |
| GDS threshold | `KVIKIO_GDS_THRESHOLD` | 16 KiB | Min size to use GDS (smaller uses POSIX) |
| Bounce buffer size | `KVIKIO_BOUNCE_BUFFER_SIZE` | 16 MiB | Size of intermediate host buffers per thread |
| Direct IO read | `KVIKIO_AUTO_DIRECT_IO_READ` | off | Opportunistic O_DIRECT for reads |
| Direct IO write | `KVIKIO_AUTO_DIRECT_IO_WRITE` | on | Opportunistic O_DIRECT for writes |

### Programmatic Configuration

```python
import kvikio.defaults

# Query settings
print(kvikio.defaults.get("compat_mode"))
print(kvikio.defaults.get("num_threads"))

# Modify settings at runtime
kvikio.defaults.set({"num_threads": 16, "task_size": 8 * 1024 * 1024})

# Enable direct IO for reads
kvikio.defaults.set({"auto_direct_io_read": True})
```

### Compatibility Mode

When GDS isn't available (missing `libcufile.so`, running in WSL, Docker without `/run/udev`), `AUTO` mode falls back to POSIX IO automatically. This means KvikIO code works everywhere — it just runs faster when GDS is available.

```python
import kvikio.cufile_driver

# Check if GDS is actually being used
print(kvikio.cufile_driver.get("is_gds_available"))
```

### cuFile Driver Configuration

```python
import kvikio.cufile_driver

# Query driver properties
print(kvikio.cufile_driver.get("is_gds_available"))
print(kvikio.cufile_driver.get("major_version"))

# Configure settable properties
kvikio.cufile_driver.set("max_device_cache_size", 1024)

# Use as context manager (auto-reverts on exit)
with kvikio.cufile_driver.set({"poll_mode": True}):
    # poll mode active here
    ...
# poll mode reverted
```

---

## Performance Optimization

### 1. Increase Thread Pool Size

The default of 1 thread is conservative. For large files, increase it:

```python
import kvikio.defaults
kvikio.defaults.set({"num_threads": 16})
```

### 2. Use Non-Blocking IO for Pipelining

Overlap IO with compute by using `pread`/`pwrite`:

```python
import cupy as cp
import kvikio

# Pipeline: read chunk N while processing chunk N-1
chunk_size = 10_000_000
buf_a = cp.empty(chunk_size, dtype=cp.float32)
buf_b = cp.empty(chunk_size, dtype=cp.float32)

with kvikio.CuFile("large_data.bin", "r") as f:
    # Start first read
    future = f.pread(buf_a)
    future.get()

    for offset in range(chunk_size * 4, file_size, chunk_size * 4):
        # Start next read while processing current
        next_future = f.pread(buf_b, file_offset=offset)

        # Process buf_a on GPU (overlaps with IO)
        result = cp.fft.fft(buf_a)

        next_future.get()
        buf_a, buf_b = buf_b, buf_a  # Swap buffers
```

### 3. Align IO to Page Boundaries

GDS performs best with 4 KiB-aligned offsets and sizes:

```python
# Good: aligned offset and size
f.read(buf, size=4096 * 1000, file_offset=4096 * 10)

# Slower: unaligned (KvikIO handles it, but splits into aligned + unaligned parts)
f.read(buf, size=5000, file_offset=100)
```

### 4. Enable Direct IO

For sequential writes and cold reads, Direct IO (bypassing OS page cache) can help:

```python
import kvikio.defaults
kvikio.defaults.set({
    "auto_direct_io_read": True,
    "auto_direct_io_write": True,
})
```

### 5. Tune Task and Bounce Buffer Sizes

For very large files, increase task and bounce buffer sizes:

```python
import kvikio.defaults
kvikio.defaults.set({
    "task_size": 16 * 1024 * 1024,       # 16 MiB per task
    "bounce_buffer_size": 64 * 1024 * 1024,  # 64 MiB bounce buffer
})
```

### 6. Page Cache Utilities

For benchmarking, clear the page cache to measure cold-read performance:

```python
import kvikio

# Check page cache residency
pages_cached, total_pages = kvikio.get_page_cache_info("data.bin")
print(f"{pages_cached}/{total_pages} pages in cache")

# Clear page cache (requires root or appropriate permissions)
kvikio.clear_page_cache()
```

---

## Interoperability

### With CuPy

KvikIO reads directly into CuPy arrays — this is the most common usage:

```python
import cupy as cp
import kvikio

data = cp.empty(1_000_000, dtype=cp.float64)
with kvikio.CuFile("data.bin", "r") as f:
    f.read(data)
# data is now a CuPy array, ready for GPU computation
```

### With Numba CUDA

KvikIO works with any buffer supporting the CUDA Array Interface:

```python
from numba import cuda
import kvikio

d_arr = cuda.device_array(1_000_000, dtype="float32")
with kvikio.CuFile("data.bin", "r") as f:
    f.read(d_arr)
```

### With cuDF

For raw binary data that isn't in a tabular format, use KvikIO to load, then convert:

```python
import cupy as cp
import cudf
import kvikio

# Load raw float array, wrap as cuDF Series
buf = cp.empty(1_000_000, dtype=cp.float32)
with kvikio.CuFile("signal.bin", "r") as f:
    f.read(buf)
signal = cudf.Series(buf)
```

For tabular formats (CSV, Parquet, JSON, ORC), use cuDF's own readers — they're optimized for those formats.

### With NumPy (Host Memory)

KvikIO seamlessly handles host memory:

```python
import numpy as np
import kvikio

arr = np.empty(1_000_000, dtype=np.float32)
with kvikio.CuFile("data.bin", "r") as f:
    f.read(arr)
```

---

## Common Patterns

### Save and Load GPU Model Checkpoints

```python
import cupy as cp
import kvikio

def save_checkpoint(arrays: dict[str, cp.ndarray], path: str):
    """Save multiple GPU arrays to a single file."""
    with kvikio.CuFile(path, "w") as f:
        offset = 0
        for arr in arrays.values():
            f.write(arr, file_offset=offset)
            offset += arr.nbytes

def load_checkpoint(shapes_dtypes: dict, path: str) -> dict[str, cp.ndarray]:
    """Load GPU arrays from a checkpoint file."""
    arrays = {}
    with kvikio.CuFile(path, "r") as f:
        offset = 0
        for name, (shape, dtype) in shapes_dtypes.items():
            arr = cp.empty(shape, dtype=dtype)
            f.read(arr, file_offset=offset)
            offset += arr.nbytes
            arrays[name] = arr
    return arrays
```

### Stream Data from S3 into GPU for Processing

```python
import cupy as cp
import kvikio

with kvikio.RemoteFile.open_s3("my-bucket", "large-dataset.bin") as f:
    total_bytes = f.nbytes()
    chunk_size = 100 * 1024 * 1024  # 100 MB chunks
    buf = cp.empty(chunk_size // 4, dtype=cp.float32)

    for offset in range(0, total_bytes, chunk_size):
        size = min(chunk_size, total_bytes - offset)
        f.read(buf[:size // 4], size=size, file_offset=offset)
        # Process chunk on GPU
        result = cp.mean(buf[:size // 4])
```

### Replace Python open() for GPU Workloads

```python
# Before: CPU-bound file IO
import numpy as np
data = np.fromfile("data.bin", dtype=np.float32)
import cupy as cp
gpu_data = cp.asarray(data)  # Extra copy: disk → CPU → GPU

# After: Direct to GPU
import cupy as cp
import kvikio
gpu_data = cp.empty(1_000_000, dtype=cp.float32)
with kvikio.CuFile("data.bin", "r") as f:
    f.read(gpu_data)  # disk → GPU directly (with GDS)
```

---

## Common Pitfalls

1. **Forgetting to set thread pool size** — The default is 1 thread. For large files, `kvikio.defaults.set({"num_threads": 16})` can dramatically improve throughput.

2. **Using KvikIO for structured formats** — Don't use KvikIO to read CSV/Parquet/JSON. Use `cudf.read_csv()`, `cudf.read_parquet()`, etc. KvikIO is for raw binary data.

3. **Not checking GDS availability** — Code works fine without GDS (falls back to POSIX), but won't get the full bandwidth benefit. Check with `kvikio.cufile_driver.get("is_gds_available")`.

4. **Misaligned IO in performance-critical paths** — Use 4 KiB-aligned offsets and sizes for best GDS performance.

5. **Not using context managers** — Always use `with kvikio.CuFile(...)` to ensure files are properly closed and deregistered.

6. **Expecting RemoteFile writes** — `RemoteFile` is read-only. To write to remote storage, write locally first, then upload via the appropriate SDK (boto3 for S3, etc.).

7. **Docker without GDS setup** — In Docker, mount `/run/udev` read-only (`--volume /run/udev:/run/udev:ro`) for GDS to work. Otherwise, KvikIO silently falls back to POSIX.
