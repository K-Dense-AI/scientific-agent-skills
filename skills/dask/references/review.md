# Current contract and validation record

Reviewed September 30, 2026 against official documentation and released packages.
The recipes target Dask/distributed **2026.8.0**, Python **3.13.3**, pandas **3.0.6**,
NumPy **2.5.1**, PyArrow **25.0.1**, SciPy **1.18.1**, Zarr **3.4.0**, h5py **3.16.0**,
Xarray **2026.9.0**, and Dask-ML **2025.1.0**. Core Dask requires Python 3.10+;
these current optional packages have stricter requirements (Zarr 3.4: Python 3.12+).
Use an isolated environment instead of changing another scientific package's stack.

## Contract corrections that affect results

- `da.from_delayed` wraps one delayed array. Assemble a grid with `da.block` after
  wrapping each block separately. Declare its actual shape and dtype.
- Exact `svd` requires chunking along one dimension only; the QR recipe uses one
  column of chunks. A randomized compressed SVD is a different, approximate method.
- `map_blocks` processes blocks independently. Use `map_overlap` for Gaussian filters,
  with halo depth matching the filter radius, floating output, and explicit spatial
  axes. A per-block FFT differs from a global FFT, which requires a single chunk along
  each transform axis. Chunk-local means require sample-count weighting for global means.
- `drop_axis` combines all chunks on that axis before mapping; it can defeat memory
  bounds. The block-mean example preserves rank instead.
- `set_index(sorted=True)` asserts existing ordering. Use ordinary `set_index` to sort
  arbitrary input before time resampling; parse timestamps and check timezone policy.
- Name aggregated output columns before Parquet writing; MultiIndex/non-string column
  names are rejected by the Dask writer. The ETL example uses named aggregations.
- CSV blocksize is source bytes, not pandas memory. Inferred dtypes can fail on later
  files; specify null-capable dtypes where needed and validate complete partitions.
- `map_partitions(meta=...)` supplies a structural contract, not automatic dtype
  conversion. Clear divisions when changing index order. Row-wise apply loops over
  pandas rows within each partition; it does not create one task per row.
- Bag `from_sequence` consumes its input locally: pass filenames and map a loader.
  `read_text(...).map(json.loads)` assumes JSON Lines. `foldby` needs a binary combine
  function such as addition, not Python's iterable `sum`.
- `to_zarr` has `mode='a'` by default. Use `mode='w-'` for new outputs and explicitly
  choose `mode='w'` only when replacing output is intended. Its `**zarr_array_kwargs`
  are direct keywords (e.g. `zarr_format=3`), not a nested `zarr_array_kwargs=` mapping.
- HDF5 handles must stay open through computation and are not serializable to process
  workers. Local HDF5 examples explicitly use threads; remote workers must open their
  own files and return concrete chunks.

## Distributed execution

`submit` schedules work immediately but execution waits for resources and dependencies.
List/dict scatter returns corresponding collections of futures; wrap the object in a
one-element list and unpack it to obtain one future for the whole object. Scattered
objects still move between workers and are lost if their only replicas disappear.
Load substantial data on workers where possible. `compute()` and `gather()` collect
results into the client; partitioned writes execute without first collecting a pandas
DataFrame or NumPy array. `persist()` retains partitions, requires a memory budget, and
can prevent later DataFrame I/O projection/filter pushdown.

Nested blocking worker tasks use `worker_client()` so child tasks can run even with
one initial worker slot. Blocking queue/event patterns need spare runnable threads and
finite timeouts in production. Stateful/side-effect submissions need `pure=False` and
idempotent external effects; `fire_and_forget` provides no exactly-once guarantee.
Actors are not automatically reconstructed after worker loss. Distributed lock leases
are not a replacement for durable storage transactions.

Use `Client.register_plugin`, and import Kubernetes `KubeCluster` from
`dask_kubernetes.operator`. The reviewed optional releases are Dask Kubernetes
**2026.3.0** and Dask-jobqueue **0.9.0**. Kubernetes requires its operator/CRDs,
authorized kubeconfig, and a worker image matching the client environment. SLURM
requires site-specific queue/account/resource policy. Close separately created clusters
as well as clients. Adaptive scaling is a cluster method; a client connected only to an
address need not own a cluster object.

## Executed verification and limits

`tests/dask/test_recipes.py` passed **19 tests** in the isolated skill environment. It executes selected Markdown recipes against small synthetic
fixtures: delayed blocks; unequal block means; Gaussian image seams and boundaries;
SVD/QR reconstruction; local Zarr/HDF5 roundtrips; constant-input normalization;
unsorted time-series resampling; CSV/Parquet ETL; Bag loading and foldby; nested worker
tasks; scatter; actors; queues/events/variables; plugin registration; diagnostic HTML;
Dask-ML scaling and Xarray; guarded process scheduling and a process worker.

The numerical checks compare against NumPy, pandas, or SciPy. Use tolerance-based
comparisons for floating reductions because partition order can change rounding. Check
units, missing-data policy, random seeds, coordinate order, and output dtypes before
scaling scientific data. Small fixtures establish recipe correctness, not large-data
throughput, peak memory, fault tolerance, or cluster capacity.

Local clients used one or two threads with dashboards disabled; one guarded subprocess
used the processes scheduler and a separate worker process. A local performance-report
HTML file was generated; no browser/dashboard interaction or externally exposed service
was tested. Bind personal dashboards to loopback (e.g. `dashboard_address='127.0.0.1:8787'`)
and use the deployment's authenticated access/TLS policy for remote schedulers. A
scheduler address is not an authenticated public web API.

Cloud S3/GCS paths, SLURM, Kubernetes creation/scaling, production adaptive scaling,
external database writes, and hardware-scale workloads are illustrative and were not
executed. The skill implements no REST API client, authentication flow, or pagination.
Graphviz rendering is optional and needs both its Python package and system executable.

## Official sources

- [Release metadata](https://pypi.org/pypi/dask/json) and [installation requirements](https://docs.dask.org/en/stable/install.html)
- [Array API](https://docs.dask.org/en/stable/array-api.html), [array creation](https://docs.dask.org/en/stable/array-creation.html), [map_blocks](https://docs.dask.org/en/stable/generated/dask.array.map_blocks.html)
- [Overlap](https://docs.dask.org/en/stable/array-overlap.html), [SVD restrictions](https://docs.dask.org/en/stable/generated/dask.array.linalg.svd.html), [FFT axes](https://docs.dask.org/en/stable/generated/dask.array.fft.fft2.html)
- [Gaussian radius and dtype behavior](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter.html), [chunking](https://docs.dask.org/en/stable/array-chunks.html)
- [Zarr writer](https://docs.dask.org/en/stable/generated/dask.array.to_zarr.html)
- [DataFrame API](https://docs.dask.org/en/stable/dataframe-api.html), [set_index](https://docs.dask.org/en/stable/generated/dask.dataframe.DataFrame.set_index.html), [map_partitions](https://docs.dask.org/en/stable/generated/dask.dataframe.DataFrame.map_partitions.html)
- [CSV reader](https://docs.dask.org/en/stable/generated/dask.dataframe.read_csv.html), [Parquet writer](https://docs.dask.org/en/stable/generated/dask.dataframe.to_parquet.html), [DataFrame best practices](https://docs.dask.org/en/stable/dataframe-best-practices.html)
- [Bag API](https://docs.dask.org/en/stable/bag-api.html), [Bag creation](https://docs.dask.org/en/stable/bag-creation.html), [foldby](https://docs.dask.org/en/stable/generated/dask.bag.Bag.foldby.html)
- [Distributed API](https://distributed.dask.org/en/stable/api.html), [nested tasks](https://distributed.dask.org/en/stable/task-launch.html), [scheduling](https://docs.dask.org/en/stable/scheduling.html), [TLS](https://distributed.dask.org/en/stable/tls.html)
- [Kubernetes operator client](https://kubernetes.dask.org/en/stable/operator_kubecluster.html), [SLURMCluster](https://jobqueue.dask.org/en/latest/generated/dask_jobqueue.SLURMCluster.html)
- [StandardScaler](https://ml.dask.org/modules/generated/dask_ml.preprocessing.StandardScaler.html), [Xarray DataArray](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.html)
