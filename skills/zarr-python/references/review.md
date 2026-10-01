# Review evidence and scope

Reviewed 2026-10-01 against Zarr-Python 3.4.0 (2026-09-15). Official PyPI release
metadata and version-tagged source were checked; 15 Zarr runtime source files matched
the installed wheel byte for byte. Six additional backend/integration files
(s3fs, gcsfs including credentials, fsspec HTTP, Xarray and Dask) also matched their
released source. Rolling documentation is interpreted through that
release's source and native behavior.

The repository tests execute every local Python example and the migration CLI example,
plus independent checks of codecs, local/ZIP/memory/obstore/fsspec adapters, indexing,
rectilinear gating, shard writes, dtype/NaN/zero preservation, Xarray/Dask/HDF5 conversion,
metadata-only migration, stale consolidation, missing chunks and read-only failures.
Small synthetic fixtures test mechanics, not throughput, calibration or scientific validity.

Remote S3/GCS/HTTP examples are illustrative. Provider constructor options and backend
request/pagination code were reviewed; memory-protocol and loopback HTTP tests exercise
adapters without external credentials. No authenticated cloud requests, remote writes,
public bucket datasets, distributed scheduler, GPU, lossy codec, general HDF5 hierarchy
conversion or NetCDF engine roundtrip is claimed.

## Primary sources

- [Zarr 3.4.0 PyPI metadata](https://pypi.org/pypi/zarr/3.4.0/json)
- [Zarr release notes](https://zarr.readthedocs.io/en/stable/release-notes/)
- [Zarr v3.4.0 source](https://github.com/zarr-developers/zarr-python/tree/v3.4.0/src/zarr)
- [Storage guide](https://zarr.readthedocs.io/en/stable/user-guide/storage/)
- [Performance guide](https://zarr.readthedocs.io/en/stable/user-guide/performance/)
- [CLI guide](https://zarr.readthedocs.io/en/stable/user-guide/cli/)
- [Migration guide](https://zarr.readthedocs.io/en/stable/user-guide/v3_migration/)
- [Consolidation guide](https://zarr.readthedocs.io/en/stable/user-guide/consolidated_metadata/)
- [s3fs 2026.9.0 source](https://github.com/fsspec/s3fs/blob/2026.9.0/s3fs/core.py)
- [gcsfs 2026.8.1 source](https://github.com/fsspec/gcsfs/blob/2026.8.1/gcsfs/core.py)
- [fsspec HTTP source](https://github.com/fsspec/filesystem_spec/blob/2026.9.0/fsspec/implementations/http.py)
- [Xarray 2026.9.0 Zarr backend](https://github.com/pydata/xarray/blob/v2026.09.0/xarray/backends/zarr.py)
- [Dask 2026.8.0 array I/O](https://github.com/dask/dask/blob/2026.8.0/dask/array/core.py)
- [h5py datasets](https://docs.h5py.org/en/stable/high/dataset.html)
