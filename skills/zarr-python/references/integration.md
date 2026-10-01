# Integration, Parallelism, and Consolidated Metadata

Using Zarr with NumPy, Dask, and Xarray; thread safety and concurrency settings; and
consolidating metadata for fast opens on cloud storage.

## Integration with NumPy, Dask, and Xarray

### NumPy Integration

Zarr arrays implement the NumPy array interface:

```python
import numpy as np
import zarr

z = zarr.zeros((1000, 1000), chunks=(100, 100))

# Use NumPy functions directly
result = np.sum(z, axis=0)  # NumPy operates on Zarr array
mean = np.mean(z[:100, :100])

# Convert to NumPy array
numpy_array = z[:]  # Loads entire array into memory
```

### Dask Integration

Dask provides lazy, parallel computation on Zarr arrays:

```python
import dask.array as da
import zarr

# Create large Zarr array
z = zarr.open('data.zarr', mode='w', shape=(100000, 100000),
              chunks=(1000, 1000), dtype='f4')

# Load as Dask array (lazy, no data loaded)
dask_array = da.from_zarr('data.zarr')

# Perform computations (parallel, out-of-core)
result = dask_array.mean(axis=0).compute()  # Parallel computation

# Write Dask array to Zarr
large_array = da.random.random((100000, 100000), chunks=(1000, 1000))
da.to_zarr(large_array, 'output.zarr')
```

**Benefits**:
- Process datasets larger than memory
- Automatic parallel computation across chunks
- Efficient I/O with chunked storage

### Xarray Integration

Xarray provides labeled, multidimensional arrays with Zarr backend:

```python
import xarray as xr
import zarr

# Open Zarr store as Xarray Dataset (lazy loading)
ds = xr.open_zarr('data.zarr')

# Dataset includes coordinates and metadata
print(ds)

# Access variables
temperature = ds['temperature']

# Perform labeled operations
subset = ds.sel(time='2024-01', lat=slice(30, 60))

# Write Xarray Dataset to Zarr
ds.to_zarr('output.zarr')

# Create from scratch with coordinates
ds = xr.Dataset(
    {
        'temperature': (['time', 'lat', 'lon'], data),
        'precipitation': (['time', 'lat', 'lon'], data2)
    },
    coords={
        'time': pd.date_range('2024-01-01', periods=365),
        'lat': np.arange(-90, 91, 1),
        'lon': np.arange(-180, 180, 1)
    }
)
ds.to_zarr('climate_data.zarr')
```

**Benefits**:
- Named dimensions and coordinates
- Label-based indexing and selection
- Integration with pandas for time series
- NetCDF-like interface familiar to climate/geospatial scientists

## Parallel Computing and Thread Safety

Zarr uses async I/O internally. Tune concurrency for remote storage or Dask-heavy workloads:

```python
import zarr

# Higher values can improve remote throughput; lower values reduce pressure
# when Dask already supplies many worker threads.
zarr.config.set({
    "async.concurrency": 8,
    "threading.max_workers": 8,
})
```

The old `synchronizer` argument (`ThreadSynchronizer`, `ProcessSynchronizer`) is **not available in Zarr-Python 3**. Use these patterns instead:

- **Reads:** concurrent reads of a stable store are supported; readers are not guaranteed a consistent snapshot during writes or metadata changes.
- **Writes:** assign workers disjoint chunks for unsharded arrays or disjoint **shards** for sharded arrays, subject to the store's write semantics. Different inner chunks may share a shard.
- **Shared stored objects and metadata:** coordinate externally; serialize resize/append and attribute updates.

For Dask-heavy workloads, estimate total concurrent I/O as roughly `dask_threads × async.concurrency` and lower Zarr's concurrency settings if the store or memory becomes saturated.

## Consolidated Metadata

For hierarchical stores with many arrays, consolidate metadata into a single file to reduce I/O operations:

```python
import zarr

# After creating arrays/groups
root = zarr.group('data.zarr')
# ... create multiple arrays/groups ...

# Consolidate metadata
zarr.consolidate_metadata('data.zarr')

# Open with consolidated metadata (faster, especially on cloud storage)
root = zarr.open_consolidated('data.zarr')
```

**Benefits**:
- Reduces metadata read operations from N (one per array) to 1
- Critical for cloud storage (reduces latency)
- Speeds up `tree()` operations and group traversal

**Cautions**:
- Metadata can become stale if arrays update without re-consolidation
- Not suitable for frequently-updated datasets
- Multi-writer scenarios may have inconsistent reads
