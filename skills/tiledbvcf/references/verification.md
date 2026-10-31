# TileDB-VCF verification notes

Reviewed 2026-10-01 against TileDB-VCF 0.40.3 and tiledb-cloud 0.14.4.

## Distribution and local environment

The [official TileDB channel metadata](https://api.anaconda.org/package/tiledb/tiledbvcf-py)
listed 0.40.3 builds for Python 3.9-3.12 on osx-arm64, osx-64, and linux-64.
[PyPI tiledbvcf metadata](https://pypi.org/pypi/tiledbvcf/json) and the
conda-forge tiledbvcf-py package endpoint returned 404. This is a distribution
constraint, not absence of a macOS build. The native library is also available
through the project's documented source-build and container routes.

An unpinned native osx-arm64 Conda solve succeeded but importing the resulting
package failed: its bundled libtiledb needed exact versioned Azure dylibs absent
from the newer dependencies selected by Conda. Pinning azure-core-cpp 1.16.2,
azure-storage-blobs-cpp 12.16.0, azure-storage-files-datalake-cpp 12.14.0,
capnproto 1.4.0, and c-blosc2 2.23.1 resolved the import failure without binary
patches. The resolved environment used Python 3.12.14, pandas 2.3.3, NumPy 2.5.3,
and PyArrow 24.0.0. The CLI reported TileDB-VCF 0.40.3, embedded TileDB 2.30.0,
and htslib 1.23; the Conda TileDB package version alone was not an accurate
indicator of the bundled library's runtime version.

Tests in `tests/tiledbvcf/` (repository-level, outside this shipped skill) use
tiny synthetic, indexed VCFs, not real human data. Native checks cover incremental
ingestion, multiallelic and missing GT values, deletion overlap boundaries, BED
coordinates, sample partitions, total record limits, cohort statistics, QC,
semantic per-sample export, and CLI create/store/list/stat/TSV. Native checks
require the separate Conda build and bcftools; an ordinary uv environment cannot
install TileDB-VCF from PyPI.

## Source and runtime findings

- [Released Python Dataset source](https://github.com/TileDB-Inc/TileDB-VCF/blob/0.40.3/apis/python/src/tiledbvcf/dataset.py)
  defines `memory_budget_mb`, explicit `create_dataset`, the batch-continuation
  protocol, 1-based explicit region strings, and `(index, count)` partitions.
  `read_iter` does not accept `set_af_filter`; use `read` with continuation when
  applying that filter.
- [Native in-memory exporter](https://github.com/TileDB-Inc/TileDB-VCF/blob/0.40.3/libtiledbvcf/src/read/in_memory_exporter.cc)
  converts `pos_start` and `pos_end` to 1-based output while keeping BED endpoints
  in BED conventions. Statistics `pos` remained 0-based in the native fixture.
- A BED read followed by a string-region read on the same Dataset retained the
  old BED interval, adding a record outside the new requested window. The skill
  requires reopening the reader when switching selectors. This is an observed
  0.40.3 behavior, not a universal claim about future releases.
- The CLI's variadic `--tiledb-config` consumed following positional paths until
  `--` was added. The invalid command printed a missing-input error with exit
  code zero. Validate sample counts and artifacts after ingestion.
- Cohort AF was 3/4 for a site where S1 was 0/1 and S2 was 1/1. Selecting S1 with
  AF >0.6 still returned S1, establishing that this query does not recompute AF
  on the selected sample subset. Both variant-statistics and allele-count tables
  reported the VCF POS=1 site as `pos=0`.

## Cloud SDK and endpoint contracts

The [published 0.14.4 wheel](https://pypi.org/pypi/tiledb-cloud/0.14.4/json),
including `tiledb/cloud/vcf/query.py`, `vcf/ingestion.py`, `utilities/_common.py`,
`client.py`, `config.py`, and generated REST client modules, is the contract
source. Some older website examples still name obsolete partition arguments;
follow the released `num_region_partitions` signature.

The default service base is `https://api.tiledb.com`; a configured deployment host
may override it. The SDK reads `TILEDB_REST_TOKEN` and sends it using the
`X-TILEDB-REST-API-KEY` header. `tiledb.cloud.Config()` propagates the authenticated
client configuration to the native library as `rest.server_address` and
`rest.token`. Importing only the Cloud client does not supply that configuration
to an independently opened native Dataset. `login()` can persist configuration;
environment-based credentials avoid putting a literal token in the example.

| Released generated route | Request / response contract |
| --- | --- |
| `POST /v1/udfs/generic/{namespace}` | JSON GenericUDF payload; binary result (`application/octet-stream`, SDK response type `file`) |
| `POST /v1/taskgraphs/{namespace}/graphs` | JSON graph payload; `TaskGraph` response |
| `POST /v1/taskgraphs/{namespace}/graphs/{id}/submit` | No request body; `TaskGraphLog` response |

These submission calls use API-key or basic authentication and have no pagination
query parameters. The SDK handles serialization, graph state, and result
retrieval; the skill does not invent a `/vcf` REST endpoint. Route/method/body/auth
and result-type dispatch were tested against the installed client with transport
mocked. This is not proof that a hosted deployment accepts the calls today.

The distributed `read` wrapper waits for its DAG and returns `pyarrow.Table`.
The public `vcf.ingest` wrapper starts a batch graph and returns a status/graph-ID
mapping before completion. Underlying `ingest_vcf` validates exactly one source
selector. The PyPI `life-sciences` extra installs TileDB-SOMA, not TileDB-VCF.
Cloud account authorization, storage roles, quotas, distributed native image
versions, paid execution, and remote object storage were not exercised.

## Further official sources

- [Data model](https://tiledb-inc.github.io/TileDB-VCF/documentation/data-model.html)
- [Released CLI option definitions](https://github.com/TileDB-Inc/TileDB-VCF/blob/0.40.3/libtiledbvcf/src/cli/tiledbvcf.cc)
- [Released QC wrapper](https://github.com/TileDB-Inc/TileDB-VCF/blob/0.40.3/apis/python/src/tiledbvcf/sample_qc.py)
- [Released allele-frequency wrapper](https://github.com/TileDB-Inc/TileDB-VCF/blob/0.40.3/apis/python/src/tiledbvcf/allele_frequency.py)
- [bcftools manual](https://samtools.github.io/bcftools/bcftools.html)
