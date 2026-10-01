# Performance, patterns, and validation

## Storage sizing

```python
import numpy as np
import zarr

z = zarr.create_array(None, data=np.ones((8, 8), dtype="f4"), chunks=(4, 4))
print(z.info)             # Cheap metadata summary.
print(z.info_complete())  # May list/read storage to compute complete information.
stored = z.nbytes_stored()  # Method, not a numeric property.
assert stored > 0
print({"logical_bytes": z.nbytes, "stored_bytes": stored, "logical_to_stored": z.nbytes / stored})
```

Stored bytes include metadata and initialized objects; uninitialized fill chunks may
consume no chunk bytes. The logical/stored ratio is not a pure codec compression ratio,
especially for tiny or sparse arrays. Record dtype, chunk/shard shape, codec settings,
backend, actual read selections, cold/warm cache state and concurrent workers when
benchmarking. Remove unsupported claims of universal codec or layout superiority.

## Appendable time series

```python
import numpy as np
import zarr

root = zarr.open_group("timeseries.zarr", mode="w-", zarr_format=3)
data = root.create_array("value", shape=(0, 4), chunks=(2, 4), dtype="f4")
time = root.create_array("time", shape=(0,), chunks=(2,), dtype="i8")
time.attrs["units"] = "seconds since 2026-01-01T00:00:00Z"
# A single coordinator owns both appends; they are not an atomic pair.
new_time = np.array([0, 60], dtype="i8")
new_values = np.arange(8, dtype="f4").reshape(2, 4)
assert len(new_time) == len(new_values) and np.all(np.diff(new_time) > 0)
data.append(new_values, axis=0)
time.append(new_time, axis=0)
assert data.shape[0] == time.shape[0]
np.testing.assert_array_equal(root["value"][:], new_values)
```

For real streams, check the previous last timestamp too, stage batches and retain a
completion manifest. Recover interrupted batches before readers treat them as complete.
Do not compress missing time intervals by dropping observations and relabeling positions.

## Bounded numeric HDF5 conversion

This worked example copies one homogeneous numeric dataset and selected metadata. It
is not a general HDF5 hierarchy, reference, compound/vlen type, dimension-scale, link,
or compression-filter converter. Validate such cases explicitly before conversion.

```python
import h5py
import numpy as np
import zarr

expected = np.arange(96, dtype="f4").reshape(12, 8)
with h5py.File("input.h5", "w") as h5:
    source = h5.create_dataset("measurements", data=expected, chunks=(4, 4))
    source.attrs["units"] = "K"
with h5py.File("input.h5", "r") as h5:
    source = h5["measurements"]
    dest = zarr.create_array(
        "converted.zarr", shape=source.shape, dtype=source.dtype, chunks=(4, 4),
        attributes={"units": str(source.attrs["units"])},
        dimension_names=("sample", "feature"),
    )
    for row in range(0, source.shape[0], 4):
        for col in range(0, source.shape[1], 4):
            selection = (slice(row, row + 4), slice(col, col + 4))
            dest[selection] = source[selection]
reopened = zarr.open_array("converted.zarr", mode="r")
np.testing.assert_array_equal(reopened[:], expected)
assert reopened.dtype == expected.dtype and reopened.attrs["units"] == "K"
```

Do not use `dataset[:]` for a large input. HDF5 handles must stay open while being read;
process workers cannot share a serialized h5py dataset safely. Attribute conversion must
preserve meaning: don't blindly stringify arrays, units or identifiers.

## NumPy and NetCDF

```python
import numpy as np
import zarr

np.save("input.npy", np.arange(96, dtype="f4").reshape(12, 8))
source = np.load("input.npy", mmap_mode="r", allow_pickle=False)
dest = zarr.create_array("from-numpy.zarr", shape=source.shape, dtype=source.dtype, chunks=(4, 4))
for row in range(0, source.shape[0], 4):
    for col in range(0, source.shape[1], 4):
        selection = (slice(row, row + 4), slice(col, col + 4))
        dest[selection] = source[selection]
np.testing.assert_array_equal(dest[:], source)
```

For NetCDF, start with a labeled Xarray group and a separately selected NetCDF engine.
`xr.open_zarr` cannot recover missing dimensions/coordinates from a bare numeric array.
`Dataset.to_netcdf` is illustrative here: engine-specific dtypes, calendars, fill encodings
and roundtrip equality must be checked before claiming a faithful conversion.

## Missing chunks and scientific validity

Default fill reads are valid for deliberately sparse/unwritten arrays, but can hide an
incomplete transfer. Keep expected object counts/checksums or a write-coverage manifest.
For an array required to have every chunk physically stored, create with
`config={"write_empty_chunks": True}` and open under a runtime configuration context:

```python
import numpy as np
import zarr

zarr.create_array("complete.zarr", data=np.zeros(8, dtype="i4"), chunks=(4,),
                  config={"write_empty_chunks": True})
with zarr.config.set({"array.read_missing_chunks": False}):
    strict = zarr.open_array("complete.zarr", mode="r")
    np.testing.assert_array_equal(strict[:], np.zeros(8))
```

In 3.4.0, `open_array(..., config={"read_missing_chunks": False})` silently ignores
that keyword on an existing array; the context above is the tested alternative. This
policy intentionally rejects absent fill chunks and is inappropriate for ordinary
sparse stores. It is not a transaction or proof that all expected samples exist.

Verify representative edge chunks, shapes/dtypes, NaNs, signedness, valid zeros, IDs,
axis order, units, coordinates, and provenance. Exact lossless value equality verifies
storage mechanics, not calibration or biological correctness. Lossy codecs need
application-specific numerical and scientific checks.

## Troubleshooting

- **High memory:** count task outputs and concurrent chunk/shard buffers; reduce both
  worker count and async concurrency before increasing object sizes.
- **Slow queries:** measure chunk overlap and request count for the actual slices;
  changing compressors cannot repair a poor axis layout.
- **Stale hierarchy:** reopen with `use_consolidated=False`, then reconsolidate after
  writers finish.
- **Conflicting writes:** partition by whole stored chunks/shards and serialize metadata;
  distinct element slices are not enough.
- **Unknown codec:** inspect metadata and install the known codec package in the target
  environment; do not reinterpret encoded bytes or silently substitute another codec.

Source: [released Array API](https://github.com/zarr-developers/zarr-python/blob/v3.4.0/src/zarr/core/array.py),
[h5py datasets](https://docs.h5py.org/en/stable/high/dataset.html).
