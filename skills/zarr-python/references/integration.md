# Integration, parallelism, and consolidated metadata

Tested with Zarr 3.4.0, NumPy 2.5.3, Dask 2026.8.0, and Xarray 2026.9.0.

## NumPy and Dask

NumPy conversion is eager. Dask can read and reduce by chunks, but `.compute()` still
materializes its **result**; a full 100000-by-100000 float64 result needs about 80 GB.
Write large results directly to a new store. Align Dask task boundaries to whole stored
chunks/shards and budget all concurrent task/codec buffers.

```python
import numpy as np
import zarr
import dask.array as da

expected = np.arange(96, dtype="f4").reshape(12, 8)
z = zarr.create_array("dask-input.zarr", data=expected, chunks=(4, 4))
lazy = da.from_zarr("dask-input.zarr")
np.testing.assert_allclose(lazy.mean(axis=0).compute(), expected.mean(axis=0))
da.to_zarr(lazy * 2, "dask-output.zarr", mode="w-", zarr_format=3)
np.testing.assert_array_equal(zarr.open_array("dask-output.zarr", mode="r")[:], expected * 2)
```

Dask `to_zarr` defaults to `mode="a"`; choose `"w-"` for new outputs. Known regular chunk
sizes are required for this path. Rechunking may involve large intermediate transfers;
benchmark it separately and don't assume a lazy graph is memory-free.

## Xarray: labeled data and missingness

`xr.open_zarr` opens a **group** with dimension metadata, not an arbitrary bare Zarr
array. Format 3 uses native `dimension_names`; format 2 conventionally uses the
`_ARRAY_DIMENSIONS` attribute. Prefer Xarray's writer to create a labeled dataset and
preserve coordinates, units, calendar and missing-value encodings together.

```python
import numpy as np
import xarray as xr

values = np.arange(24, dtype="f4").reshape(3, 2, 4)
values[1, 0, 1] = np.nan
expected = xr.Dataset(
    {"temperature": (("time", "lat", "lon"), values, {"units": "K"})},
    coords={
        "time": np.array(["2026-01-01", "2026-01-02", "2026-01-03"], dtype="datetime64[ns]"),
        "lat": [30.0, 60.0], "lon": [0.0, 90.0, 180.0, 270.0],
    },
    attrs={"source": "synthetic example"},
)
expected.to_zarr(
    "climate.zarr", mode="w-", zarr_format=3, consolidated=False,
    encoding={"temperature": {"chunks": (1, 2, 4), "_FillValue": np.nan}},
)
with xr.open_zarr("climate.zarr", consolidated=False) as actual:
    xr.testing.assert_identical(actual.compute(), expected)
    subset = actual.sel(time="2026-01-02", lat=slice(30, 60)).compute()
    assert subset.temperature.shape == (2, 4)
```

Storage `fill_value` and scientific `_FillValue` are different concepts in format 3.
With default Xarray behavior, a format-3 storage fill of zero is not automatically
missing; `_FillValue` controls masking. Format 2 normally interprets storage fill as
missing. Check `use_zarr_fill_value_as_mask`, decoding and dtype when opening; never
silently convert valid zeros to NaNs. A missing chunk can look like valid fill data,
so validate written coverage independently. Ascending versus descending coordinate
order changes which slice bounds select data; calendars and longitude conventions must
be explicit. Labels alone do not make a CF-compliant climate product.

For append/region writes, validate coordinates and existing schema first. Xarray's
`safe_chunks=True` checks a subset of chunk alignment constraints; it does not provide
locks or a multi-array transaction. Do not disable it merely to silence a warning.

## Parallel writes and concurrency

Concurrent reads of a stable store are supported; readers are not promised a snapshot
during writes. Assign disjoint stored objects to writers: chunks for unsharded arrays,
**shards** for sharded arrays. Independent inner chunks can share one shard. Serialize
append/resize/attribute changes and external publication. ZIP is not a concurrent store.
Zarr-Python 3 has no functioning `ThreadSynchronizer` or `ProcessSynchronizer`; an old
`synchronizer=` argument may warn and be ignored, not protect writes.

```python
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import zarr

z = zarr.create_array("parallel.zarr", shape=(16, 8), dtype="i4", chunks=(2, 4), shards=(8, 8))
def write_shard(start):
    target = zarr.open_array("parallel.zarr", mode="r+")
    target[start:start + 8, :] = start + 1

with zarr.config.set({"async.concurrency": 4, "threading.max_workers": 4}):
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(write_shard, [0, 8]))
read = zarr.open_array("parallel.zarr", mode="r")[:]
np.testing.assert_array_equal(read[:8], np.full((8, 8), 1))
np.testing.assert_array_equal(read[8:], np.full((8, 8), 9))
```

This is a local two-writer smoke test, not a distributed failure-recovery guarantee.
Dask worker threads multiply pressure on the store; tune internal concurrency alongside
worker count, memory and backend rate limits. The 3.4 default async concurrency is 10.

## Consolidation is group metadata caching

Format 2 writes `.zmetadata`; format 3 embeds consolidated metadata in the root group's
`zarr.json` and remains experimental. `tree()` shows logical nodes, not those files.
Do not consolidate a standalone array root or assume all later opens see fresh metadata.

```python
import numpy as np
import zarr

root = zarr.open_group("consolidated.zarr", mode="w-", zarr_format=2)
root.create_array("a", data=np.arange(8), chunks=(4,))
zarr.consolidate_metadata(root.store)
read = zarr.open_consolidated(root.store, mode="r")
np.testing.assert_array_equal(read["a"][:], np.arange(8))
# When freshness matters, explicitly bypass cached hierarchy metadata:
fresh = zarr.open_group(root.store, mode="r", use_consolidated=False)
assert fresh["a"].shape == (8,)
```

Consolidate only after metadata writers finish. Use `use_consolidated=False` for mutable
hierarchies and reconsolidate completed revisions. A cached hierarchy may omit newly
created children or stale array shapes/attributes; actual chunk data is not cached there.
Pass a configured FsspecStore for cloud consolidation: `consolidate_metadata` has no
`storage_options` argument. Reopen with the same backend authorization.

Sources: [Dask writer](https://docs.dask.org/en/stable/generated/dask.array.to_zarr.html),
[Xarray writer](https://docs.xarray.dev/en/stable/generated/xarray.Dataset.to_zarr.html),
[Xarray reader](https://docs.xarray.dev/en/stable/generated/xarray.open_zarr.html),
[consolidated metadata](https://zarr.readthedocs.io/en/stable/user-guide/consolidated_metadata/).
