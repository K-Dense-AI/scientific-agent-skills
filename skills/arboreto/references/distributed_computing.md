# Dask execution and compatibility

## Released package versus repository source

As reviewed 2026-09-30, PyPI Arboreto 0.1.6 constructs a metadata dataframe from
an empty list even when metadata were not requested. Dask's newer dataframe
backend rejects this with `TypeError: Must supply at least one delayed object`.
Current Arboreto GitHub source moves that construction under `include_meta`,
but the wheel remains 0.1.6. Installing the wheel does not include that source fix.

Use the exact Python 3.11 dependency recipe in `SKILL.md`, and execute this
before importing Arboreto or `dask.dataframe`:

```python
import dask
dask.config.set({"dataframe.query-planning": False})
```

That switch selects the legacy backend retained by the tested Dask 2024.7.1.
It is not a workaround for every current Dask release; newer versions no longer
provide the legacy backend. Restart kernels that imported the backend too early.
Dask and distributed must be the same pinned release on client, scheduler, and
workers. Preserve SciPy 1.13.1 for sparse `.A` handling in the released package.

An older Python 3.10.20 environment with Dask/distributed 2023.12.1, NumPy 1.26.4,
pandas 1.5.3, scikit-learn 1.3.2, and SciPy 1.11.4 also passed the synthetic
profiles. The same old Dask stack failed to import on Python 3.11.11. This is
why the main recipe specifies an entire tested stack instead of loose bounds.

## Bounded local workers

Illustrative real-data adapter; one-worker dense/sparse synthetic inference and
the wrapper were executed with this context-manager pattern:

```python
import dask
dask.config.set({"dataframe.query-planning": False})
from distributed import LocalCluster, Client
from arboreto.algo import grnboost2
import pandas as pd

if __name__ == "__main__":
    expression = pd.read_csv("expression.tsv", sep="\t", index_col=0)
    with LocalCluster(n_workers=2, threads_per_worker=1,
                      memory_limit="2GB", dashboard_address=None) as cluster:
        with Client(cluster) as client:
            network = grnboost2(expression_data=expression, tf_names=["TF1", "TF2"],
                                client_or_address=client, seed=777)
    network.to_csv("network.tsv", sep="\t", index=False, header=False)
```

The memory limit is per worker, not for the whole job. Measure a pilot before
choosing worker count: Arboreto scatters the TF matrix to every worker and the
full expression matrix still resides on the client. A dense DataFrame is
converted to NumPy internally; it has no inherent distributed-storage advantage.
CSC can preserve sparse inputs, but regressions and target conversions still
allocate memory. A shared filesystem is not inherently required when the client
loads and scatters all inputs.

The default Arboreto `"local"` path uses Dask's automatic worker configuration,
not a promise to use every physical core. Explicit workers make the resource
budget clear. Context managers close resources on exceptions; a supplied client
is not closed by Arboreto. Reusing a client is supported upstream, but a repeated
in-process-client probe here cancelled a future after its first run. Use a fresh
client/cluster per run if this occurs; separate process clients passed all probes.

## Remote scheduler (illustrative; not executed)

Use the same environment/backend configuration on all nodes. These are the
current Dask CLI command forms; replace `scheduler.example` with your own trusted
scheduler hostname:

```bash
# Head node
DASK_DATAFRAME__QUERY_PLANNING=False dask scheduler

# Worker node: four worker processes, one thread each, 4 GB each
DASK_DATAFRAME__QUERY_PLANNING=False dask worker tcp://scheduler.example:8786 \
  --nworkers 4 --nthreads 1 --memory-limit 4GB
```

`--nprocs` is stale; current workers use `--nworkers`. Avoid shell comments after
continuation backslashes. `Client("tcp://scheduler.example:8786")` can be passed
as `client_or_address` inside a context manager, after the pre-import backend
configuration. TCP scheduler/worker connections are executable-code trust
boundaries: use a trusted network and the deployment's configured TLS/auth setup.

For a dashboard, enable it deliberately and inspect `client.dashboard_link`;
`Client()` does not guarantee that a URL will be printed. Restrict dashboard
exposure according to the deployment. Monitor worker restarts, spill, client
memory, and target-level retry warnings before interpreting missing links.

## Verified sources

- [Arboreto user guide](https://arboreto.readthedocs.io/en/latest/userguide.html)
- [Current Arboreto graph construction](https://github.com/aertslab/arboreto/blob/master/arboreto/core.py)
- [Dask 2024.7.1 backend selection](https://github.com/dask/dask/blob/2024.7.1/dask/dataframe/__init__.py)
- [Current Dask from_delayed](https://github.com/dask/dask/blob/main/dask/dataframe/dask_expr/io/_delayed.py)
- [Dask command line](https://docs.dask.org/en/stable/deploying-cli.html)
- [SciPy 1.14 removals](https://docs.scipy.org/doc/scipy/release/1.14.0-notes.html)
