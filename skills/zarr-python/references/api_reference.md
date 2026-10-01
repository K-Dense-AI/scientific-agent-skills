# Zarr-Python 3.4.0 API reference

These are selected callable forms, not exhaustive copied signatures. Explicitly select
format/mode when behavior matters; defaults can also be affected by runtime configuration.

| Operation | Current form / behavior |
|---|---|
| New array | `zarr.create_array(store, shape=..., dtype=..., chunks="auto", shards=None, compressors="auto", overwrite=False)`; `store=None` gives memory. |
| From NumPy | `zarr.create_array(store, data=values, chunks=...)`; omit both shape and dtype. |
| Copy array | `zarr.from_array(store, data=source, chunks="keep", shards="keep")`; preserve tested source semantics, validate destination after copying. |
| Convenience | `zarr.zeros(shape, **kwargs)`, `ones`, `empty`, `full(shape, fill_value, **kwargs)`, `array(data, **kwargs)`, `zeros_like(source, **kwargs)`. `empty` does not establish scientifically meaningful values. |
| Open array | `zarr.open_array(store, mode="r", path="", zarr_format=None, storage_options=None)`; mode is forwarded through kwargs. |
| Open unknown node | `zarr.open(store, mode="r")` detects array/group; default signature mode is `None`, resolved from store writability (normally `"a"`). |
| Open group | `zarr.open_group(store, mode="r", path=None, use_consolidated=None)`; `None` uses consolidation if available, `False` bypasses, `True` requires it. |
| Create/require child | `group.create_array(name, ...)`, `require_array(name, shape=..., dtype=...)`, `create_group(name)`, `require_group(name)`. |
| Resize/append | `array.resize(new_shape_tuple)` returns None; `array.append(data, axis=0)` returns the new shape. |
| Metadata | `array.attrs`, `group.attrs` hold JSON-compatible values; native v3 `dimension_names` are not coordinate arrays. |
| Sizing | `array.nbytes` is logical bytes; **`array.nbytes_stored()`** computes stored bytes. `array.info` is metadata; `array.info_complete()` obtains storage-dependent details. |
| Consolidate | `zarr.consolidate_metadata(store, path=None, zarr_format=None)` returns Group; supply a configured store for credentials. |
| Require consolidation | `zarr.open_consolidated(store, mode="r", ...)` returns Group, not Array. |

Modes: `r` existing read-only; `r+` existing read/write; `a` open or create; `w` replace;
`w-` create only. Creation flags are not distributed exclusive-writer locks.

On an existing array, `open_array(..., config=...)` does not forward that configuration
in 3.4.0. Use a `zarr.config.set` context before opening when enforcing missing-chunk
policy; see the tested example in [performance](performance_and_patterns.md).

## Selection semantics

For a 2-D array, `z.vindex[[0, 5], [2, 7]]` pairs coordinates and returns two values;
`z.oindex[[0, 5], [2, 7]]` returns a 2-by-2 Cartesian product. Explicit coordinate
selection takes a tuple of per-axis coordinate arrays:
`z.get_coordinate_selection(([0, 5], [2, 7]))`. `z.blocks[i, j]` selects chunks.
Negative-step slices are unsupported. Rectilinear grids require an experimental flag;
`Array.chunks` cannot describe every rectilinear layout with one tuple.

## Stores and codecs

`LocalStore`, `MemoryStore`, `ZipStore`, `FsspecStore`, and `ObjectStore` live in
`zarr.storage`. ObjectStore requires obstore; FsspecStore requires fsspec plus the
selected protocol backend. `FsspecStore.from_url(url, storage_options=None,
read_only=False)` resolves the URI. Old DirectoryStore/FSStore names are replaced;
legacy database/N5 stores are removed. S3Map/GCSMap are backend mappings, not newly
supported Zarr store classes.

For format 3, use `zarr.codecs.BloscCodec`, `GzipCodec`, `ZstdCodec`;
pass `shuffle="bitshuffle"` to BloscCodec (the BloscShuffle enum is deprecated).
`compressors=None` disables compression, not serialization. Format-2 arrays use
NumCodecs (e.g. `numcodecs.Blosc`) through `compressors=` in `create_array`. Numeric
format-3 defaults are Zstd; use `"auto"`, not the invalid `"default"` string.

## Exceptions and coordination

Missing nodes use `NodeNotFoundError` / `ArrayNotFoundError` / `GroupNotFoundError`;
`PathNotFoundError` and `ReadOnlyError` are not exported by this release. Read-only
mutation raises ValueError. `UnknownCodecError` subclasses ValueError; malformed
metadata may raise `MetadataValidationError`. Preserve the original error context;
authentication errors must not be treated as missing chunks.

Use one writer per stored object (per **shard** if sharded), including boundaries.
No working v2 synchronizers are provided. Neither consolidation nor `require_array`
is a transaction or a lock. Current concurrency configuration keys include
`async.concurrency` and `threading.max_workers`.

Sources: [API](https://zarr.readthedocs.io/en/stable/api/zarr/),
[released sync API](https://github.com/zarr-developers/zarr-python/blob/v3.4.0/src/zarr/api/synchronous.py),
[released errors](https://github.com/zarr-developers/zarr-python/blob/v3.4.0/src/zarr/errors.py).
