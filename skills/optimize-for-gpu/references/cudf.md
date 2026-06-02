# cuDF Reference

cuDF is a GPU DataFrame library that provides a pandas-like API for loading, joining, aggregating, filtering, and manipulating tabular data entirely on the GPU. It's part of the NVIDIA RAPIDS ecosystem and is built on the Apache Arrow columnar memory format.

> **Full documentation:** https://docs.rapids.ai/api/cudf/stable/

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Two Usage Modes](#two-usage-modes)
3. [cudf.pandas Accelerator Mode](#cudfpandas-accelerator-mode)
4. [Core API: DataFrame and Series](#core-api)
5. [IO Operations](#io-operations)
6. [GroupBy Operations](#groupby-operations)
7. [String Operations](#string-operations)
8. [User Defined Functions (UDFs)](#user-defined-functions)
9. [Missing Data Handling](#missing-data-handling)
10. [Data Types](#data-types)
11. [Memory Management](#memory-management)
12. [Interoperability](#interoperability)
13. [Multi-GPU with Dask-cuDF](#multi-gpu-with-dask-cudf)
14. [Performance Optimization](#performance-optimization)
15. [Key Differences from pandas](#key-differences-from-pandas)
16. [Common Migration Patterns](#common-migration-patterns)

---

## Installation and Setup

Always use `uv add` (never `pip install` or `conda install`) in all install instructions, docstrings, comments, and error messages.

```bash
uv add --extra-index-url=https://pypi.nvidia.com cudf-cu12    # For CUDA 12.x
```

Verify:
```python
import cudf
print(cudf.Series([1, 2, 3]))  # Should print a GPU series
```

---

## Two Usage Modes

cuDF offers two ways to accelerate pandas code:

### 1. cudf.pandas (Zero-Code-Change)
Drop-in replacement that automatically accelerates pandas. Falls back to CPU for unsupported operations. Best for: quick acceleration of existing code, mixed codebases, prototyping.

### 2. Direct cuDF API
Replace `import pandas` with `import cudf`. Maximum performance, no proxy overhead, but requires adapting code to cuDF's API (which has some behavioral differences from pandas). Best for: production pipelines, maximum performance, new GPU-first code.

---

## cudf.pandas Accelerator Mode

The fastest path from pandas to GPU — no code changes required.

### Activation

```python
# Jupyter/IPython (MUST be before any pandas import)
%load_ext cudf.pandas
import pandas as pd  # Now GPU-accelerated

# Command line
# python -m cudf.pandas your_script.py
# python -m cudf.pandas --profile your_script.py  # With profiling

# Programmatic
import cudf.pandas
cudf.pandas.install()
import pandas as pd  # Now GPU-accelerated
```

**Critical:** If pandas was already imported in the session, you must restart the kernel/process.

### How It Works

- `import pandas` returns a proxy module that wraps cuDF and pandas.
- Every operation is first attempted on GPU (cuDF). If it fails, it automatically falls back to CPU (pandas).
- Data transfers between GPU and CPU happen only when necessary.
- Uses managed memory by default — can process datasets larger than GPU memory.
- Currently passes **93% of pandas' 187,000+ unit tests**.

### Profiling GPU vs CPU Execution

```python
%%cudf.pandas.profile        # Shows GPU vs CPU operation breakdown per cell
%%cudf.pandas.line_profile   # Per-line GPU/CPU timing
```

### Accessing Underlying Objects

```python
proxy_df.as_gpu_object()  # Get the cuDF DataFrame directly
proxy_df.as_cpu_object()  # Get the pandas DataFrame directly
```

Note: automatic fallback stops working after you extract the underlying object.

### Compatible Third-Party Libraries
cuGraph, cuML, Hvplot, Holoview, Ibis, NumPy, Matplotlib, Plotly, PyTorch, Seaborn, Scikit-Learn, SciPy, TensorFlow, XGBoost.

**Not compatible:** Joblib. For distributed work, use Dask-cuDF instead.

### Limitations

- Join operations don't guarantee pandas' row ordering (for performance).
- Cannot use `import cudf` alongside cudf.pandas in the same session.
- Pickled objects are not interchangeable between regular pandas and cudf.pandas.
- Proxy arrays subclass `numpy.ndarray`, which can cause eager device-to-host transfers.
- To force CPU-only: set `CUDF_PANDAS_FALLBACK_MODE=1`.

---

## Core API

### Creating DataFrames and Series

```python
import cudf

# From dict
df = cudf.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0], "c": ["x", "y", "z"]})

# From pandas
import pandas as pd
gdf = cudf.DataFrame.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
# or
gdf = cudf.DataFrame(pandas_df)

# Series
s = cudf.Series([1, 2, 3, None, 5])

# Back to pandas
pdf = gdf.to_pandas()
```

### Common Operations (Same as pandas)

```python
df.head(10)
df.tail(5)
df.describe()
df.info()
df.dtypes
df.columns
df.shape

# Selection
df["a"]                     # Column → Series
df[["a", "b"]]             # Multiple columns → DataFrame
df.loc[2:5, ["a", "b"]]   # Label-based indexing
df.iloc[0:3]               # Integer-based indexing

# Filtering
df[df["a"] > 2]
df.query("a > 2 and b < 6")  # Supports @var for local variables

# Sorting
df.sort_values("a", ascending=False)
df.sort_index()

# Missing data
df.fillna(0)
df.dropna()
df.isna()

# Aggregations
df["a"].sum()
df["a"].mean()
df["a"].std()
df["a"].value_counts()

# Transforms
df["a"].clip(lower=1, upper=5)
df["a"].apply(lambda x: x * 2)  # JIT-compiled

# Combining
cudf.concat([df1, df2])
df1.merge(df2, on="key")
df1.merge(df2, on="key", how="left")  # left, right, inner, outer

# Arrow interop (zero-copy)
arrow_table = df.to_arrow()
df = cudf.DataFrame.from_arrow(arrow_table)
```

---

## IO Operations

GPU-accelerated file reading and writing — often dramatically faster than pandas for large files.

### Parquet (Recommended for Performance)

```python
# Read
df = cudf.read_parquet("data.parquet")
df = cudf.read_parquet("data.parquet", columns=["a", "b"])  # Read only specific columns

# Write
df.to_parquet("output.parquet")

# Metadata inspection (without loading data)
cudf.io.parquet.read_parquet_metadata("data.parquet")

# Incremental writing
writer = cudf.io.parquet.ParquetDatasetWriter("output_dir/", partition_cols=["year"])
writer.write_table(df)
writer.close()
```

### CSV

```python
df = cudf.read_csv("data.csv")
df = cudf.read_csv("data.csv", usecols=["a", "b"], dtype={"a": "int32"})
df.to_csv("output.csv", index=False)
```

### JSON

```python
df = cudf.read_json("data.json")
df = cudf.read_json("data.json", lines=True)  # JSON Lines format
df.to_json("output.json")
```

### ORC

```python
df = cudf.read_orc("data.orc")
df.to_orc("output.orc")
```

### Other Formats

| Format | Read | Write | GPU-Accelerated |
|--------|------|-------|-----------------|
| Avro | `cudf.read_avro()` | N/A | Yes (read only) |
| Text | `cudf.read_text()` | N/A | Yes (read only) |
| HDF5 | `cudf.read_hdf()` | `df.to_hdf()` | No (uses pandas) |
| Feather | `cudf.read_feather()` | `df.to_feather()` | No (uses pandas) |

**Prefer Parquet over CSV** — columnar format reads faster on GPU, supports predicate pushdown, and compresses well.

---

## GroupBy Operations

### Basic GroupBy

```python
df.groupby("category").sum()
df.groupby(["category", "subcategory"]).mean()
df.groupby("category").agg({"value": "sum", "count": "max"})
df.groupby("category").agg({"value": ["sum", "min", "max"], "count": "mean"})
```

### Supported Aggregations

**Universal:** `count`, `size`, `nunique`, `nth`, `collect`, `unique`
**Numeric:** `sum`, `mean`, `var`, `std`, `median`, `idxmin`, `idxmax`, `min`, `max`, `quantile`
**Specialized:** `corr`, `cov`

### GroupBy Transform

```python
df.groupby("category").transform("max")  # Broadcasts result to match group size
```

### GroupBy Apply

```python
df.groupby("category").apply(lambda x: x.max() - x.min())
```

**Warning:** Apply runs the function sequentially per group — can be slow with many small groups. Use vectorized aggregations whenever possible.

### JIT-Compiled GroupBy (User-Defined Aggregation)

```python
def custom_agg(df):
    return df["value"].max() - df["value"].min() / 2

result = df.groupby("category").apply(custom_agg, engine="jit")
```

JIT restrictions: no nulls, only int32/64 and float32/64, cannot return new columns.

### Important: Sort Behavior

cuDF uses `sort=False` by default (unlike pandas which sorts by default). To match pandas:
```python
df.groupby("category", sort=True).sum()
# Or globally:
cudf.set_option("mode.pandas_compatible", True)
```

---

## String Operations

cuDF provides GPU-accelerated string operations via the `.str` accessor — identical API to pandas.

```python
s = cudf.Series(["Hello World", "foo bar", "RAPIDS GPU", None])

# Case
s.str.lower()
s.str.upper()
s.str.title()
s.str.capitalize()

# Pattern matching
s.str.contains("World")
s.str.startswith("Hello")
s.str.endswith("GPU")
s.str.match(r"^[A-Z]")

# Extraction and replacement
s.str.extract(r"(\w+)\s(\w+)")
s.str.replace("World", "GPU")
s.str.slice(0, 5)

# Splitting and joining
s.str.split(" ")
s.str.cat(sep=", ")

# Info
s.str.len()
s.str.isalpha()
s.str.isdigit()

# cuDF-exclusive operations (not in pandas)
s.str.normalize_spaces()   # Collapse whitespace
s.str.tokenize()           # Tokenize strings
s.str.ngrams(2)            # Generate n-grams
s.str.edit_distance(other) # Levenshtein distance
s.str.url_encode()
s.str.url_decode()
```

---

## User Defined Functions

### Series.apply() — JIT-Compiled

```python
s = cudf.Series([1, 2, 3, 4, 5])

def square_plus_one(x):
    return x ** 2 + 1

s.apply(square_plus_one)  # Compiled to GPU kernel via Numba
```

With arguments:
```python
def add_constant(x, c):
    return x + c

s.apply(add_constant, args=(42,))
```

### DataFrame.apply() — Row-wise (axis=1)

```python
def row_func(row):
    return row["a"] + row["b"] * 2

df.apply(row_func, axis=1)  # Access columns by name via dict-like syntax
```

### Null Handling in UDFs

Nulls propagate automatically:
```python
s = cudf.Series([1, cudf.NA, 3])
def f(x):
    return x + 1
s.apply(f)  # Returns [2, <NA>, 4]
```

Explicit null checks:
```python
def f(x):
    if x is cudf.NA:
        return 0
    return x + 1
```

### String UDFs

String operations inside UDFs support: `==`, `!=`, `>=`, `<=`, `startswith()`, `endswith()`, `find()`, `rfind()`, `count()`, `in`, `strip/lstrip/rstrip()`, `upper/lower()`, `replace()`, `+` (concatenation), `len()`, boolean checks.

For string UDFs creating intermediate strings, allocate heap:
```python
from cudf.core.udf.utils import set_malloc_heap_size
set_malloc_heap_size(int(2e9))  # 2 GB
```

### Rolling Window UDFs

```python
import math

s = cudf.Series([16, 25, 36, 49, 64, 81], dtype="float64")

def max_sqrt(window):
    result = 0
    for val in window:
        result = max(result, math.sqrt(val))
    return result

s.rolling(window=3, min_periods=3).apply(max_sqrt)
```

**Limitation:** Rolling UDFs do NOT support null values.

### Custom Numba CUDA Kernels on cuDF Columns

For maximum control, write CUDA kernels that operate directly on cuDF columns:

```python
from numba import cuda

@cuda.jit
def gpu_multiply(in_col, out_col, multiplier):
    i = cuda.grid(1)
    if i < in_col.size:
        out_col[i] = in_col[i] * multiplier

df["result"] = 0.0
gpu_multiply.forall(len(df))(df["a"], df["result"], 10.0)
```

### UDF Limitations

- Only numeric non-decimal types have full support; strings have partial support.
- `**kwargs` not supported.
- Bitwise operations not implemented in UDFs.
- GroupBy JIT: no nulls, only int32/64 and float32/64, cannot return new columns.
- Rolling UDFs: no null support.

---

## Missing Data Handling

- Missing values are `<NA>` (not NaN) — cuDF uses a separate null mask, not NaN sentinels.
- All dtypes are nullable (including integers — no float coercion for missing ints).
- `np.nan` inserted into integer columns becomes `<NA>` without casting to float.

```python
s = cudf.Series([1, None, 3, None, 5])

s.isna()                # Boolean mask
s.notna()
s.fillna(0)             # Fill with scalar
s.fillna({"a": 0, "b": 1})  # Fill with dict (per-column)
s.dropna()

# Aggregations skip NA by default
s.sum()                 # skipna=True (default)
s.sum(skipna=False)     # Propagates NA

# GroupBy excludes NA groups by default
df.groupby("a", dropna=False).sum()  # Include NA groups
```

---

## Data Types

| Category | Types |
|----------|-------|
| Integer | `int8`, `int16`, `int32`, `int64`, `uint32`, `uint64` |
| Float | `float32`, `float64` |
| Datetime | `datetime64[s/ms/us/ns]` |
| Timedelta | `timedelta[s/ms/us/ns]` |
| Categorical | `CategoricalDtype` |
| String | `object` / `string` |
| Decimal | `Decimal32Dtype`, `Decimal64Dtype`, `Decimal128Dtype` |
| List | `ListDtype` (nested lists) |
| Struct | `StructDtype` (dict-like) |

All types are nullable. List columns have a `.list` accessor (`get()`, `len()`, `contains()`, `sort_values()`, `unique()`, `concat()`). Struct columns have a `.struct` accessor (`field()`, `explode()`).

**No `object` dtype for arbitrary Python objects** — `object` dtype only stores strings.

---

## Memory Management

### RMM (RAPIDS Memory Manager)

cuDF uses RMM for GPU memory allocation. Configure it for your workload:

```python
import rmm

# Pool allocator (recommended for production — avoids per-allocation cudaMalloc overhead)
pool = rmm.mr.PoolMemoryResource(
    rmm.mr.CudaMemoryResource(),
    initial_pool_size="1GiB",
    maximum_pool_size="4GiB"
)
rmm.mr.set_current_device_resource(pool)

# Managed memory (allows datasets larger than GPU memory)
rmm.mr.set_current_device_resource(rmm.mr.ManagedMemoryResource())

# Managed + pool (best of both)
pool = rmm.mr.PoolMemoryResource(
    rmm.mr.ManagedMemoryResource(),
    initial_pool_size="1GiB"
)
rmm.mr.set_current_device_resource(pool)
```

### Aligning CuPy and Numba with RMM

When using cuDF with CuPy or Numba, align all libraries on the same allocator to avoid memory fragmentation:

```python
# CuPy
from rmm.allocators.cupy import rmm_cupy_allocator
import cupy
cupy.cuda.set_allocator(rmm_cupy_allocator)

# Numba
from rmm.allocators.numba import RMMNumbaManager
from numba import cuda
cuda.set_memory_manager(RMMNumbaManager)
```

### Copy-on-Write

```python
cudf.set_option("copy_on_write", True)
# or: export CUDF_COPY_ON_WRITE=1
```

Slices, `.head()`, shallow copies, and view-generating methods share memory until one is modified. Reduces memory usage significantly for workflows with many derived DataFrames.

### Memory Profiling

```python
rmm.statistics.enable_statistics()
stats = rmm.statistics.get_statistics()
# Returns: current_bytes, current_count, peak_bytes, peak_count, total_bytes, total_count
```

---

## Interoperability

### CuPy (Zero-Copy)

```python
import cupy as cp

# cuDF → CuPy
arr = df.to_cupy()             # DataFrame → 2D CuPy array
arr = cp.asarray(df["col"])    # Series → 1D CuPy array
arr = df["col"].values         # Series → 1D CuPy array

# CuPy → cuDF
df = cudf.DataFrame(cupy_2d_array)
s = cudf.Series(cupy_1d_array)

# Via DLPack
df = cudf.from_dlpack(cupy_array.__dlpack__())
```

### Arrow (Zero-Copy)

```python
arrow_table = df.to_arrow()
df = cudf.DataFrame.from_arrow(arrow_table)
```

### RAPIDS Ecosystem

- **cuML:** Accepts cuDF DataFrames directly for ML pipelines.
- **cuGraph:** Accepts cuDF DataFrames for graph analytics.
- **Dask-cuDF:** Distributed GPU DataFrames (see below).

### CUDA Array Interface

cuDF Series exposes `__cuda_array_interface__` for zero-copy sharing with any compatible library (CuPy, Numba, PyTorch, etc.).

---

## Multi-GPU with Dask-cuDF

For datasets larger than a single GPU's memory, or for multi-GPU parallelism:

```python
import dask_cudf
from dask.distributed import Client
from dask_cuda import LocalCUDACluster

# One worker per GPU
cluster = LocalCUDACluster()
client = Client(cluster)

# From files
ddf = dask_cudf.read_csv("path/*.csv")
ddf = dask_cudf.read_parquet("path/")

# From cuDF DataFrame
ddf = dask_cudf.from_cudf(df, npartitions=16)

# Operations (lazy — call .compute() to execute)
result = ddf.groupby("a").sum().compute()

# Persist in GPU memory for repeated access
ddf = ddf.persist()
```

Key differences from cuDF: `.iloc` not supported, must call `.compute()` to materialize, transpose not implemented.

---

## Performance Optimization

1. **Start with cudf.pandas** for easiest adoption — zero code changes, automatic GPU/CPU fallback.

2. **Switch to direct cuDF API for max performance** — avoids proxy overhead and fallback copying costs.

3. **Prefer Parquet over CSV** — columnar format, faster GPU reads, predicate pushdown, better compression.

4. **Use pool allocators** via RMM — avoids per-allocation `cudaMalloc` overhead.

5. **Enable copy-on-write** — `cudf.set_option("copy_on_write", True)` reduces memory from slices and views.

6. **Reshape data to be long** (more rows, fewer columns) — GPUs parallelize over rows.

7. **Never iterate** — use vectorized operations exclusively. `for row in df.iterrows()` defeats the purpose of GPU acceleration.

8. **Minimum dataset size:** GPUs shine with **10,000-100,000+ rows**. Smaller datasets may be faster on CPU.

9. **Use vectorized string ops** (`.str.` accessor) instead of row-wise string UDFs.

10. **Use CuPy for row-wise math** that cuDF doesn't support natively.

11. **Use Numba CUDA kernels** for complex element-wise operations.

12. **Align all RAPIDS libraries on the same RMM allocator** to avoid memory fragmentation.

13. **For distributed workloads**, use Dask-cuDF with `persist()` to keep data on GPU memory.

---

## Key Differences from pandas

1. **Result ordering is non-deterministic** by default (groupby, joins, etc.). Use `sort=True` or `cudf.set_option("mode.pandas_compatible", True)`.

2. **All types are nullable.** Missing values are `<NA>`, not NaN. Integer columns with missing values stay integer (no float coercion).

3. **No iteration.** `for val in series` is not supported. Convert to pandas first if you must iterate.

4. **Unique column names required.** No duplicate column names.

5. **No arbitrary Python objects.** The `object` dtype only stores strings.

6. **`.apply()` uses Numba JIT.** Only a subset of Python is supported inside UDFs — no arbitrary Python objects, no external library calls.

7. **Floating-point results may differ slightly** due to GPU parallel operation ordering. Use tolerance-based comparisons.

8. **GroupBy defaults to `sort=False`** (pandas defaults to `sort=True`).

9. **No ExtensionDtype support** from pandas.

---

## Common Migration Patterns

### Pattern 1: Zero-Effort (cudf.pandas)
```python
%load_ext cudf.pandas
import pandas as pd
# Everything else stays exactly the same
```

### Pattern 2: Direct Import Swap
```python
# Before
import pandas as pd
df = pd.read_csv("data.csv")
result = df.groupby("col").mean()

# After
import cudf
df = cudf.read_csv("data.csv")
result = df.groupby("col").mean()
```

### Pattern 3: Replace Iteration with Vectorized Ops
```python
# Before (pandas — slow even on CPU)
for idx, row in df.iterrows():
    df.at[idx, "c"] = row["a"] + row["b"]

# After (cuDF)
df["c"] = df["a"] + df["b"]
```

### Pattern 4: Replace apply() with Vectorized
```python
# Before
df["result"] = df.apply(lambda row: row["a"] ** 2 + row["b"], axis=1)

# After (vectorized — much faster)
df["result"] = df["a"] ** 2 + df["b"]
```

### Pattern 5: GPU Processing, CPU at Boundaries
```python
# Load and process on GPU
gdf = cudf.read_parquet("data.parquet")
result = gdf.groupby("key").agg({"val": "sum"})

# Convert to pandas only when needed (plotting, export, etc.)
pdf = result.to_pandas()
pdf.plot()
```

### Pattern 6: CuPy for Unsupported Math
```python
import cupy as cp

# Convert to CuPy for operations cuDF doesn't support
arr = df[["x", "y", "z"]].to_cupy()
norms = cp.linalg.norm(arr, axis=1)
df["norm"] = cudf.Series(norms)
```

---

## Configuration

```python
cudf.set_option("copy_on_write", True)            # Enable copy-on-write
cudf.set_option("mode.pandas_compatible", True)    # Match pandas behavior
cudf.describe_option()                             # List all options
```

| Environment Variable | Purpose |
|---------------------|---------|
| `CUDF_COPY_ON_WRITE=1` | Enable copy-on-write |
| `CUDF_PANDAS_RMM_MODE` | Control memory allocator for cudf.pandas |
| `CUDF_PANDAS_FALLBACK_MODE=1` | Force CPU-only execution in cudf.pandas |
