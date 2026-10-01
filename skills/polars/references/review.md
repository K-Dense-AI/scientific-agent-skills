# Polars review and execution scope

Reviewed 2026-10-01. Targets Polars 1.44.2 (Python >=3.10), using its published
Python wheel, public release notes, and official stable API/user documentation.
The native recipe suite ran on macOS ARM64, Python 3.13.3, with PyArrow 25.0.1,
pandas 3.0.6, NumPy 2.5.3, SQLAlchemy 2.1.1, fastexcel 0.21.0, XlsxWriter 3.2.9.
These are a tested combination, not minimum versions for every integration.

## Sources and corrected contracts

- [1.44 release notes](https://pola.rs/posts/polars-1-44/) and
  [1.44.2 release](https://github.com/pola-rs/polars/releases/tag/py-1.44.2):
  current version, conditional masking, SQL changes, and deprecations. The 1.44
  implementation masks unused elementwise branch inputs. The older `when`
  docstring saying all branches always execute is not an accurate description
  of every 1.44 query; native tests cover masked casts and failing gathers.
- [Collect](https://docs.pola.rs/api/python/stable/reference/lazyframe/api/polars.LazyFrame.collect.html),
  [streaming](https://docs.pola.rs/user-guide/concepts/streaming/), and
  [lazy API](https://docs.pola.rs/api/python/stable/reference/lazyframe/index.html):
  `engine="streaming"`, materialized output versus direct sinks, lazy schema I/O,
  optimizer boundaries and memory limitations. `collect` defaults to `auto`, which
  honors engine affinity and otherwise uses in-memory execution in 1.44.2. GPU
  needs compatible NVIDIA/CUDA hardware and `cudf-polars`; it is not tested here.
- [Join](https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.join.html),
  [as-of join](https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.join_asof.html),
  [window mapping](https://docs.pola.rs/api/python/stable/reference/expressions/api/polars.Expr.over.html),
  [lazy pivot](https://docs.pola.rs/api/python/stable/reference/lazyframe/api/polars.LazyFrame.pivot.html):
  cardinality, null policy, sorting/tolerance, row alignment, declared pivot levels.
- [Concat](https://docs.pola.rs/api/python/stable/reference/api/polars.concat.html):
  use `horizontal_extend` to intentionally pad shorter inputs. In 1.44.2 the
  compatibility wrapper still pads `horizontal` with a deprecation warning, even
  though the API description already describes the forthcoming equal-height
  contract. `strict=True` works in this release but is transitional. Validate
  heights and sample IDs explicitly instead of relying on a changing default.
- [I/O index](https://docs.pola.rs/api/python/stable/reference/io.html),
  [Excel](https://docs.pola.rs/api/python/stable/reference/api/polars.read_excel.html),
  [fastexcel](https://fastexcel.toucantoco.dev/fastexcel.html),
  [database read](https://docs.pola.rs/api/python/stable/reference/api/polars.read_database.html),
  [URI read](https://docs.pola.rs/api/python/stable/reference/api/polars.read_database_uri.html),
  [database write](https://docs.pola.rs/api/python/stable/reference/api/polars.DataFrame.write_database.html):
  source/file distinctions, sheet IDs/options, connection versus URI, driver-bound
  parameters, result batching, write mode, and distinct IPC file/stream methods.
- [Cloud storage](https://docs.pola.rs/user-guide/io/cloud-storage/),
  [Azure credentials](https://docs.pola.rs/api/python/stable/reference/api/polars.CredentialProviderAzure.html),
  [BigQuery RowIterator](https://docs.cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.table.RowIterator):
  provider credentials and native cloud transport, SDK-to-Arrow conversion. Polars
  and provider SDKs own transport/pagination; there are no custom REST endpoints
  in this skill. BigQuery `to_arrow()` loads all result pages into one Arrow table.
- [SQL](https://docs.pola.rs/user-guide/sql/intro/),
  [pandas migration](https://docs.pola.rs/user-guide/migration/pandas/),
  [missing data](https://docs.pola.rs/user-guide/expressions/missing-data/):
  local SQL versus database execution, no index alignment, null versus NaN, and
  conversion defaults. Scientific units and time-zone interpretation remain the
  caller's responsibility.

## Native validation and limits

Run `python tests/run_all.py --isolated polars` from the repository. The suite
checks leading-zero IDs, CSV record skipping and invalid casts; duplicate raw
headers; null/NaN/infinity and statistical conventions; optimizer-preserving
filters; expression contexts/pipe; join cardinality and as-of alignment;
concatenation and eager/lazy pivots; window layout/time order; local
CSV/Parquet/JSON/NDJSON/IPC/Excel round trips; SQLite parameters/batches/write
policy; local SQL; and Arrow/pandas/NumPy conversion semantics.

This is small synthetic correctness testing, not a throughput, peak-memory,
out-of-core, or GPU benchmark. Remote S3/Azure/GCS, PostgreSQL/MySQL,
ConnectorX/ADBC, and BigQuery examples were checked against documentation and
signatures, not authenticated services. Their credentials, driver installation,
network access, permissions, and provider costs require deployment-specific
validation. Example fragments with undefined inputs or `...` are illustrative;
they are not complete stand-alone programs. No real research dataset was used.
