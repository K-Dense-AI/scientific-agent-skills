# Storage backends

Targets Zarr-Python 3.4.0. `zarr.storage` provides asynchronous store I/O behind the
synchronous array API. A store is not a plain v2 `MutableMapping`.

## Local and memory stores

```python
import numpy as np
import zarr
from zarr.storage import LocalStore, MemoryStore

for store in [LocalStore("local.zarr"), MemoryStore()]:
    z = zarr.create_array(store, data=np.arange(12), chunks=(4,))
    np.testing.assert_array_equal(zarr.open_array(store, mode="r")[:], np.arange(12))
```

A path creates a LocalStore automatically. MemoryStore data persists only as long as the
backing in-memory objects remain. Choose explicit read-only store/array modes for reads.

## ZIP archives

```python
import numpy as np
import zarr
from zarr.storage import ZipStore

with ZipStore("array.zip", mode="w") as store:
    z = zarr.create_array(store, data=np.arange(12), chunks=(4,))
with ZipStore("array.zip", mode="r") as store:
    np.testing.assert_array_equal(zarr.open_array(store, mode="r")[:], np.arange(12))
```

Close ZIP stores (the context manager does this). Write each chunk/metadata entry once;
ZIP lacks deletion and repeated updates create duplicate archive entries. Stage changing
data in a directory store, then archive the completed store. Do not share a writable ZIP
between independent processes.

## Fsspec and ObjectStore

`FsspecStore.from_url(url, storage_options=..., read_only=...)` resolves the protocol and
wraps supported synchronous filesystems when needed. Supplying an explicit filesystem
to `FsspecStore` requires its async-compatible form. This native memory-protocol example
checks the adapter without making a network request:

```python
import numpy as np
import zarr
from zarr.storage import FsspecStore

store = FsspecStore.from_url("memory://zarr-skill-example")
z = zarr.create_array(store, data=np.arange(12), chunks=(4,))
np.testing.assert_array_equal(zarr.open_array(store, mode="r")[:], np.arange(12))
```

ObjectStore is a separate obstore-backed adapter. Optional `obstore==0.11.1` was exercised
locally; its provider credential configuration differs from fsspec.

```python
import numpy as np
import zarr
from obstore.store import MemoryStore as ObMemoryStore
from zarr.storage import ObjectStore

store = ObjectStore(ObMemoryStore())
z = zarr.create_array(store, data=np.arange(6), chunks=(3,))
np.testing.assert_array_equal(zarr.open_array(store, mode="r")[:], np.arange(6))
```

## S3, GCS and HTTP

The following **illustrative remote examples** are source/API reviewed, not authenticated
cloud tests. Replace placeholders only with the intended authorized bucket and prefix.
Prefer read-only opens first; never put keys/tokens in notebooks, logs or attributes.

```python
# Illustrative remote: needs authorized existing stores and network access.
import zarr
from zarr.storage import FsspecStore

s3_store = FsspecStore.from_url(
    "s3://my-bucket/path/data.zarr", storage_options={"anon": False}, read_only=True,
)
s3_group = zarr.open_group(s3_store, mode="r", use_consolidated=False)
gcs_array = zarr.open_array(
    "gs://my-bucket/path/array.zarr", mode="r",
    storage_options={"project": "my-project", "token": "google_default"},
)
# Known array path: HTTP directory listing is not required for this bounded read.
http_array = zarr.open_array("https://example.org/array.zarr", mode="r")
subset = http_array[:10]
```

| Backend | URI/options and authentication | I/O contract |
|---|---|---|
| S3 / s3fs 2026.9.0 | `s3://bucket/key`; `anon=False` uses SDK credentials (roles/profiles preferred), `anon=True` for public buckets. Optional `endpoint_url` is an explicitly supplied S3-compatible endpoint, not a bucket path. | SDK GetObject byte/range reads, PutObject writes, HeadObject metadata, ListObjectsV2 pagination. Signed requests use the backend's region/credential configuration. |
| GCS / gcsfs 2026.8.1 | `gs://bucket/key` or `gcs://`; `token="google_default"` selects application-default credentials, `token="anon"` public access. `project` identifies the project, not authorization. | Backend object metadata/list/media requests; listing follows `nextPageToken`/`pageToken`. Writes may use multipart/resumable upload. |
| HTTP(S) / fsspec | Existing array or consolidated hierarchy URL; install remote dependencies. Server must support the required object and byte-range access. | Read-only HTTP GET/HEAD; no generic directory listing or write API is implied. Servers ignoring Range may force full-object reads or fail. |

Zarr has no universal hosted REST service, API key, pagination parameter or JSON query
endpoint. The backend handles object requests and pagination; metadata JSON and encoded
chunk bytes are distinct payloads. FsspecStore maps missing objects to missing chunks;
authentication/network failures must not be interpreted as scientific missing values.
Source review covers these backend contracts; no public example bucket, credentials,
remote write, permission policy, or object-version snapshot was validated here.

Use immutable/versioned prefixes for completed outputs when consistency matters. Listing,
metadata consolidation, append and multi-object writes do not form a transaction.
Consolidation requires a **group**, not an array root; see [integration](integration.md).

Sources: [Zarr stores](https://zarr.readthedocs.io/en/stable/user-guide/storage/),
[s3fs](https://s3fs.readthedocs.io/en/latest/), [gcsfs](https://gcsfs.readthedocs.io/en/latest/),
[fsspec HTTP](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.implementations.http.HTTPFileSystem).
