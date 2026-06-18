# Zarr Python Quick Reference

Concise reference for **zarr 3.2.x**. See `references/v3_migration.md` for Zarr-Python 2→3 changes.

## Array Creation

### `zarr.zeros()` / `zarr.ones()` / `zarr.empty()` / `zarr.full()`
```python
zarr.zeros(shape, *, chunks=None, dtype='f8', store=None, compressors='default',
           fill_value=0, zarr_format=3)
```

### `zarr.create_array()`
```python
zarr.create_array(store, *, shape, chunks, dtype='f8', compressors='default',
                  filters=None, fill_value=0, zarr_format=3, storage_options=None,
                  overwrite=False)
```

`chunks` may be a regular tuple (for example `(100, 100)`) or, in Zarr 3.2+, a rectilinear nested sequence (for example `([10, 20, 30], [50, 50])`).

### `zarr.array()`
```python
zarr.array(data, *, chunks=None, dtype=None, store=None, compressors='default')
```

### `zarr.open_array()` / `zarr.open()`
```python
zarr.open_array(store, mode='a', *, shape=None, chunks=None, dtype=None)
zarr.open(store, mode='r')  # auto-detects Array or Group
```

**Mode:** `'r'`, `'r+'`, `'a'` (default create-if-missing), `'w'` (overwrite), `'w-'` (create only).

## Storage (zarr.storage)

Built-in stores in v3: `LocalStore`, `MemoryStore`, `ZipStore`, `FsspecStore`, `ObjectStore`.

```python
from zarr.storage import LocalStore, MemoryStore, ZipStore, FsspecStore

# Local directory (default when passing a path string)
store = LocalStore('path/to/data.zarr')

# In-memory
store = MemoryStore()

# ZIP archive
store = ZipStore('data.zip', mode='w')  # close when done writing

# Cloud via fsspec URI (install pinned zarr[remote] + pinned backend)
store = FsspecStore.from_url('s3://bucket/path.zarr', storage_options={'anon': False})
group = zarr.open_group(store=store, mode='r')

# Shorthand — pass URI directly to open/create
zarr.open_group('s3://bucket/data.zarr', mode='r', storage_options={'anon': True})
```

**Removed in v3:** `DirectoryStore`, `FSStore`, `S3Map`, `GCSMap`, `DBMStore`, `LMDBStore`, `SQLiteStore`, `RedisStore`, `MongoDBStore`, `N5Store`.

## Compression (zarr.codecs)

```python
from zarr.codecs import BloscCodec, BloscShuffle, GzipCodec, ZstdCodec

# Default Blosc (zstd) is applied when compressors='default'
codec = BloscCodec(cname='zstd', clevel=5, shuffle=BloscShuffle.bitshuffle)
z = zarr.create_array('data.zarr', shape=(1000, 1000), chunks=(100, 100),
                      dtype='f4', compressors=codec)

# No compression
z = zarr.create_array('data.zarr', shape=(1000, 1000), chunks=(100, 100),
                      dtype='f4', compressors=None)
```

For **Zarr format 2** arrays, import codecs from `numcodecs` instead of `zarr.codecs`.

## Indexing

### Basic (NumPy-style)
```python
z[0:100, 0:100]
z[10:20, 50:60] = np.random.random((10, 10))
```

### Advanced (v3)
```python
z.vindex[[0, 5, 10], [2, 8, 15]]           # coordinate (convenience)
z.get_coordinate_selection([0, 5, 10])     # explicit API

z.oindex[0:10, [5, 10, 15]]                # orthogonal
z.get_orthogonal_selection((slice(0, 10), [5, 10, 15]))

z.blocks[0, 0]                             # chunk/block access
```

## Groups

```python
root = zarr.group('data.zarr')
grp = root.create_group('temperature')
arr = grp.create_array('t2m', shape=(365, 720, 1440), chunks=(1, 720, 1440), dtype='f4')
sub = root['temperature/t2m']

# v3 only — no create_dataset / require_dataset
arr2 = root.require_array('precip', shape=(100, 100), chunks=(10, 10), dtype='f4')
```

## Array properties and methods

```python
z.shape, z.chunks, z.dtype, z.size
z.nbytes          # uncompressed logical size
z.nbytes_stored   # stored (compressed) size
z.info            # summary string
z.resize((1500, 1500))   # tuple shape, not separate args
z.append(new_data, axis=0)
```

## Metadata consolidation

```python
zarr.consolidate_metadata('data.zarr')
root = zarr.open_consolidated('data.zarr')  # pass storage_options for cloud URIs
```

## Integration

```python
import dask.array as da
dask_arr = da.from_zarr('data.zarr')
da.to_zarr(dask_arr, 'output.zarr')

import xarray as xr
ds = xr.open_zarr('data.zarr')
ds.to_zarr('output.zarr')
```

## Thread / process safety (v3)

- Reads: safe without coordination.
- Writes: safe across workers when chunks do not overlap.
- `synchronizer=` / `ThreadSynchronizer` / `ProcessSynchronizer`: **not available in v3** (see migration reference).
- Tune Zarr's internal concurrency with `zarr.config.set({"async.concurrency": 8, "threading.max_workers": 8})`, especially when combining Zarr with Dask.

## Format versions

```python
z = zarr.create_array(..., zarr_format=3)  # default
z = zarr.create_array(..., zarr_format=2)  # legacy interop
```

## Common dtypes

`'f4'`, `'f8'`, `'i4'`, `'i8'`, `'u4'`, `'u8'`, `'bool'`, `'c8'`, `'c16'`

## Errors

```python
import zarr.errors
# PathNotFoundError, ReadOnlyError, GroupNotFoundError — see zarr.errors module
```
