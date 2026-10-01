# Performance and memory

Targets core 4.19.0. See [caching](https://vaex.io/docs/guides/caching.html),
[configuration](https://vaex.io/docs/conf.html), and released executor/cache source.

## Batch independent reductions

```python
import asyncio
import numpy as np
import vaex

df = vaex.from_arrays(x=np.arange(10.), y=np.arange(10.) ** 2)
df['derived'] = df.x ** 2 + df.y
pending = [df.derived.mean(delay=True), df.x.std(delay=True), df.y.sum(delay=True)]
df.execute()
values = [task.get().item() for task in pending]
assert np.allclose(values, [57., np.std(np.arange(10.)), 285.])

async def compute(frame):
    mean = frame.x.mean(delay=True)
    count = frame.count(delay=True)
    await frame.execute_async()
    return mean.get().item(), count.get().item()

assert asyncio.run(compute(df)) == (4.5, 10)
```

In a notebook with a running event loop, use `await compute(df)` instead of
`asyncio.run`. Defining an expression or virtual column defers per-row evaluation;
ordinary reductions execute now. Promises must be executed before `.get()`.
There is no public `vaex.execute([tasks])` collection API. Batching compatible tasks
can share scans, but "one pass" is not universal: limits, means, variance or dependant
tasks can need preliminary work. Measure actual data passes and timing on the target workload.

## Memory boundaries

| Operation | Allocation to plan for |
| --- | --- |
| HDF5/Arrow open | Metadata, handles, mapped/address space and accessed pages |
| Virtual columns | Expression metadata and per-chunk temporary arrays |
| Filters/selections | Boolean masks and selection/cache metadata |
| Reductions/grids | Chunk buffers and grid accumulators; grid size grows with dimensions |
| Groupby/unique/join/sort | Cardinality dictionaries, output tables and/or row index arrays |
| `.values`, `.to_numpy()`, unchunked pandas conversion | Requested full arrays |
| `.materialize()` | Full selected virtual columns in memory |
| sklearn `Predictor.fit` | Full feature matrix and target, plus estimator allocations |

`df.byte_size()` describes data bytes, not resident memory or a process limit.
`df.is_local()` tells whether the frame is local rather than a remote server frame;
it accepts no column argument and does not indicate virtual columns or memory mapping.
Use `df.virtual_columns` to inspect derived definitions. `df.copy()` is shallow.

```python
assert 'derived' in df.virtual_columns
assert df.is_local()
materialized = df.materialize('derived')  # small fixture only
assert 'derived' not in materialized.virtual_columns
assert np.allclose(materialized.derived.to_numpy(), 2 * np.arange(10.) ** 2)
rows = 0
for start, stop, chunk in df[['x', 'derived']].to_pandas_df(chunk_size=3):
    assert len(chunk) == stop - start
    rows += len(chunk)
assert rows == 10
```

Export already evaluates virtual columns in chunks. Materializing first is not a fix
for an out-of-memory export. Reduce selected columns/chunk size, bound group cardinality,
check disk capacity and profile the actual operation instead. Avoid collecting all
pandas chunks into a list, which reconstructs the full allocation.

## Explicit caching and timing

`vaex.cache` starts disabled unless configured. A repeated mean is not guaranteed to
be cached. Optional `cachetools` supplies the bounded in-memory cache below:

```python
import time
import vaex.cache

with vaex.cache.memory(maxsize='8MiB', clear=True):
    first = df.x.mean()
    second = df.x.mean()
    assert first == second
with vaex.cache.off():
    start = time.perf_counter()
    result = df.y.sum()
    elapsed = time.perf_counter() - start
assert result == 285
print({'elapsed_seconds': elapsed, 'column_bytes': df.byte_size()})
```

Cache budget is not a total-RSS cap. Cached results, operating-system file cache and
warm compiled kernels can change timing; report warm/cold conditions, package versions,
row/column counts, dtype, hardware, storage and workload. No universal billion-rows-per-second
claim applies to arbitrary expressions or files. Use Python profiling tools or timing;
`with vaex.profiler():` is not a supported context manager.

Set `VAEX_NUM_THREADS` in the process environment before starting Python for repeatable
thread limits. Avoid oversubscription with BLAS/Numba/estimator threads. More threads
can increase per-worker buffers and do not guarantee faster I/O.

## Other execution engines

Core 4.19.0 does not have `to_dask_dataframe()`. Its documented Dask integration is
`to_dask_array()` for numerical arrays; that alone does not provision a distributed
cluster. Core pins Dask `<2024.9`, so current standalone Dask recommendations cannot
be transplanted into this environment without compatibility work. [Dask guide](https://vaex.io/docs/guides/dask.html).

For custom functions, prefer built-in expression operations. `df.apply(function,
arguments=[...], vectorize=True)` calls the function on array chunks and can allocate
chunk outputs; `vectorize=False` has different, row-function behavior. Verify types,
nulls and independent numerical results. JIT compilation does not create a nonexistent
`Expression.custom_agg` API, and compilation time is separate from steady-state timing.
