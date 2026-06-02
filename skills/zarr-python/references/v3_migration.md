# Zarr-Python 3 Migration Quick Reference

Targets **zarr 3.2.x** (PyPI stable, May 2026). Official guide: [3.0 Migration Guide](https://zarr.readthedocs.io/en/stable/user-guide/v3_migration/).

## Version and format defaults

| Topic | Zarr-Python 2 | Zarr-Python 3 |
|-------|---------------|---------------|
| Pin while migrating downstream | `zarr>=2,<3` | `zarr>=3,<4` |
| Default on-disk format | Zarr v2 | Zarr v3 (`zarr_format=3`) |
| Write v2-compatible data | default | `zarr_format=2` on create/open |
| Python requirement | 3.9–3.11 (late 2.x) | **3.12+** (3.2.1 on PyPI) |

```python
# Keep writing Zarr format 2 arrays (interop with older tools)
z = zarr.create_array(store="data.zarr", shape=(1000, 1000), chunks=(100, 100),
                      dtype="f4", zarr_format=2)
```

## Store imports and backends

```python
# v3 — stores live under zarr.storage
from zarr.storage import LocalStore, MemoryStore, ZipStore, FsspecStore
```

| v2 | v3 |
|----|-----|
| `DirectoryStore` | `LocalStore` |
| `FSStore` | `FsspecStore` |
| `TempStore` | `tempfile.TemporaryDirectory` + `LocalStore` |
| `S3Map` / `GCSMap` (s3fs/gcsfs) | Prefer `FsspecStore` or URI strings (see below) |
| `DBMStore`, `LMDBStore`, `SQLiteStore`, `RedisStore`, `MongoDBStore` | Removed — use `FsspecStore` or custom store |

### Cloud storage (recommended v3 pattern)

```python
import zarr

# URI + storage_options (requires s3fs for S3)
root = zarr.open_group(
    store="s3://my-bucket/path/data.zarr",
    mode="r",
    storage_options={"anon": False},  # uses AWS_* env vars via fsspec
)

# Explicit FsspecStore
from zarr.storage import FsspecStore
store = FsspecStore.from_url("s3://my-bucket/path/data.zarr", storage_options={"anon": False})
root = zarr.open_group(store=store, mode="r")
```

Install remote I/O extras: `uv pip install "zarr[remote]"` (pulls fsspec). Add `s3fs` or `gcsfs` for the target protocol.

## Codecs and compression

- Zarr v3 arrays: use `zarr.codecs.*` (e.g. `BloscCodec`, `GzipCodec`, `BytesCodec`) via `compressors=` on `create_array`.
- Zarr v2 arrays: `numcodecs` codecs still work; import from `numcodecs`, not `zarr.*`.
- `compressor=` kwarg on creation functions → use `compressors=` in v3.

```python
from zarr.codecs import BloscCodec

z = zarr.create_array(
    store="data.zarr", shape=(1000, 1000), chunks=(100, 100), dtype="f4",
    compressors=BloscCodec(cname="zstd", clevel=5, shuffle="shuffle"),
)
```

## Groups and h5py-style API

| v2 (removed in v3) | v3 replacement |
|--------------------|----------------|
| `group.create_dataset(...)` | `group.create_array(...)` |
| `group.require_dataset(...)` | `group.require_array(...)` |
| `group.foo` attribute access | `group["foo"]` only |

## Array operations

```python
# resize — pass a shape tuple, not separate dimension args
z.resize((15000, 15000))  # not z.resize(15000, 15000)
```

Advanced indexing: `vindex`, `oindex`, and `blocks` remain as convenience properties; equivalent methods are `get_coordinate_selection`, `get_orthogonal_selection`, etc.

## Not yet ported to v3 (avoid or expect errors)

From the [migration guide WIP list](https://zarr.readthedocs.io/en/stable/user-guide/v3_migration/#work-in-progress):

- `synchronizer` argument (`ThreadSynchronizer`, `ProcessSynchronizer`) — use separate chunks per writer or external coordination; see [performance guide — thread safety](https://zarr.readthedocs.io/en/stable/user-guide/performance/).
- `zarr.copy`, `zarr.copy_all`, `zarr.copy_store`, `Group.move`
- Object dtypes, ragged arrays, `cache_attrs`, `cache_metadata`, `chunk_store`

## Zarr-Python 2 support

Install last 2.x: `uv pip install "zarr==2.*"`. Maintenance lives on the `support/v2` branch (security fixes for ~6 months after 3.0).
