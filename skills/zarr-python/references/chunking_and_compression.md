# Chunking and compression

Targets Zarr-Python 3.4.0. These examples are local synthetic roundtrips, not benchmarks.

## Match layout to queries and memory

A chunk is the unit decoded for a read; a shard packs multiple chunks into one stored
object. Count the chunks touched by representative slices and benchmark latency,
throughput, object requests, and peak memory. Approximately 1 MiB uncompressed per chunk
is a useful starting experiment for Blosc, not a universal minimum or optimum. For
float32, `(512, 512)` is 1 MiB. Larger cloud objects can amortize requests; sharding lets
small read chunks coexist with larger stored objects. There is no universal 5–100 MB
cloud optimum or fixed codec ranking.

For row reads, `(small_rows, all_columns)` often reduces touched chunks; for column
reads, reverse that geometry. For a full `[:, y, x]` trace, long time-axis chunks can
help; for `[t, :, :]` images, short time-axis chunks can help. State the selection before
claiming a layout is faster. Budget concurrent decoded chunks, output buffers, codec
scratch memory, and compressed shard buffers; do not assume only one chunk is resident.

## Sharding

```python
import numpy as np
import zarr

expected = np.arange(256, dtype="i4").reshape(16, 16)
z = zarr.create_array("sharded.zarr", data=expected, chunks=(2, 2), shards=(8, 8))
assert z.chunks == (2, 2) and z.shards == (8, 8)
z.oindex[[1, 3], [2, 4]] = [[1000, 1001], [1002, 1003]]
expected[np.ix_([1, 3], [2, 4])] = [[1000, 1001], [1002, 1003]]
np.testing.assert_array_equal(zarr.open_array("sharded.zarr", mode="r")[:], expected)
```

Shard dimensions must be multiples of chunk dimensions. Assign a single writer to each
shard even when workers update different inner chunks. Partial writes may rewrite a
shard; backend byte-range reads and coalescing affect performance. Measure with the
actual backend rather than promising fewer requests for every selection.

## Rectilinear chunks are experimental

Nested per-axis lengths require an explicit opt-in. They are not ordinary Dask regular
chunks; use `dask_array.chunksize` for a regular grid, not its nested `.chunks` tuple.
An unsharded rectilinear array has no single uniform `Array.chunks` shape.

```python
import numpy as np
import zarr

with zarr.config.set({"array.rectilinear_chunks": True}):
    rect = zarr.create_array(
        "rectilinear.zarr", shape=(6, 10), dtype="f4",
        chunks=([1, 2, 3], [5, 5]),
    )
    rect[:] = np.arange(60, dtype="f4").reshape(6, 10)
    np.testing.assert_array_equal(rect[1:4], np.arange(60).reshape(6, 10)[1:4])
```

Validate consumer compatibility before choosing this extension. Resize uses the grid's
own rules: explicit lengths preserve rectilinear identity even if initially uniform.

## Codec selection

Format-3 numeric defaults use `BytesCodec` plus `ZstdCodec(level=0)` in this release.
`compressors="auto"` selects defaults. `compressors=None` removes compression while
retaining serialization. A format-3 codec must implement the relevant Zarr codec
interface; plain format-2 `numcodecs.Blosc` is not accepted as a format-3 compressor.

```python
import numpy as np
import zarr
from zarr.codecs import BloscCodec, GzipCodec, ZstdCodec

values = np.linspace(-1, 1, 64, dtype="f4").reshape(8, 8)
codecs = [
    BloscCodec(cname="zstd", clevel=5, shuffle="bitshuffle"),
    BloscCodec(cname="lz4", clevel=1),
    GzipCodec(level=6), ZstdCodec(level=3), None,
]
for codec in codecs:
    arr = zarr.create_array(None, data=values, chunks=(4, 4), compressors=codec)
    np.testing.assert_array_equal(arr[:], values)
    print(arr.compressors)
```

These codecs are lossless for the tested numeric data. Benchmark speed and stored bytes;
Gzip is not inherently the best compression ratio. Available Blosc backends depend on
the build; inspect `numcodecs.blosc.list_compressors()` instead of assuming Snappy exists.
Lossy quantization/casting needs a declared error budget and downstream scientific
validation; byte checksums alone cannot validate the resulting measurements.

For format 2, use NumCodecs:

```python
import numpy as np
import zarr
from numcodecs import Blosc

legacy = zarr.create_array(
    "format2.zarr", data=np.arange(12, dtype="i4"), chunks=(4,), zarr_format=2,
    compressors=Blosc(cname="zstd", clevel=5, shuffle=Blosc.BITSHUFFLE),
)
np.testing.assert_array_equal(zarr.open_array("format2.zarr", mode="r")[:], np.arange(12))
```

Sources: [performance](https://zarr.readthedocs.io/en/stable/user-guide/performance/),
[rectilinear example](https://zarr.readthedocs.io/en/stable/user-guide/examples/rectilinear_chunks/),
[released array implementation](https://github.com/zarr-developers/zarr-python/blob/v3.4.0/src/zarr/core/array.py).
