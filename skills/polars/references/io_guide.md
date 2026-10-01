# Polars Data I/O Guide

Polars 1.44.2 I/O patterns. Local CSV, Parquet, JSON, IPC, Excel, SQLite, and
Arrow/pandas/NumPy conversions are covered by bounded native tests. Cloud providers,
BigQuery, ConnectorX/ADBC, and remote databases below are illustrative, documentation-
verified integrations, not authenticated end-to-end checks. See [review.md](review.md).
Fragments require the named files and schemas. All writes use user-chosen outputs.

## CSV Files

### Reading CSV

**Eager mode (loads into memory):**
```python
import polars as pl

# Basic read
df = pl.read_csv("data.csv")

# With options
df = pl.read_csv(
    "data.csv",
    separator=",",
    has_header=True,
    columns=["col1", "col2"],  # Select specific columns
    n_rows=1000,  # Parser limit; multithreading may exceed it; head(1000) caps output
    skip_rows=10,  # Skip records before parsing the header; respects CSV quoting
    schema_overrides={"col1": pl.Int64, "col2": pl.String},  # Specify types
    null_values=["NA", "null", ""],  # Define null values
    encoding="utf-8",
    ignore_errors=False
)
```

**Lazy mode (builds a plan; metadata/inference can read the source):**
```python
# Scan CSV (builds query plan)
lf = pl.scan_csv("data.csv")

# Apply operations
result = lf.filter(pl.col("age") > 25).select("name", "age")

# Execute and load
df = result.collect()
```

### Writing CSV

```python
# Basic write
df.write_csv("output.csv")

# With options
df.write_csv(
    "output.csv",
    separator=",",
    include_header=True,
    null_value="",  # How to represent nulls
    quote_char='"',
    line_terminator="\n"
)
```

### Multiple CSV Files

**Read multiple files:**
```python
# Read all CSVs in directory
lf = pl.scan_csv("data/*.csv")

# Read specific files
lf = pl.scan_csv(["file1.csv", "file2.csv", "file3.csv"])
```

## Parquet Files

Parquet is the recommended format for performance and compression.

### Reading Parquet

**Eager:**
```python
df = pl.read_parquet("data.parquet")

# With options
df = pl.read_parquet(
    "data.parquet",
    columns=["col1", "col2"],  # Select specific columns
    n_rows=1000,  # Read first N rows
    parallel="auto"  # Control parallelization
)
```

**Lazy (recommended):**
```python
lf = pl.scan_parquet("data.parquet")

# Automatic predicate and projection pushdown
result = lf.filter(pl.col("age") > 25).select("name", "age").collect()
```

### Writing Parquet

```python
# Basic write
df.write_parquet("output.parquet")

# With compression
df.write_parquet(
    "output.parquet",
    compression="snappy",  # Options: "snappy", "gzip", "brotli", "lz4", "zstd"
    statistics=True,  # Write statistics (enables predicate pushdown)
    use_pyarrow=False  # Use native writer; benchmark for the workload
)
```

### Partitioned Parquet (Hive-style)

**Write partitioned:**
```python
# Write with partitioning
df.write_parquet(
    "output_dir",
    partition_by=["year", "month"]  # Creates directory structure
)
# Creates year=.../month=... partitions; filenames and zero-padding are not fixed
```

**Read partitioned:**
```python
lf = pl.scan_parquet("output_dir/**/*.parquet", hive_partitioning=True)

# Explicitly parse Hive keys when scanning a glob; validate their inferred types
result = lf.filter(pl.col("year") == 2023).collect()
```

## JSON Files

### Reading JSON

**NDJSON (newline-delimited JSON) - recommended:**
```python
df = pl.read_ndjson("data.ndjson")

# Lazy
lf = pl.scan_ndjson("data.ndjson")
```

**Standard JSON:**
```python
df = pl.read_json("data.json")

# From JSON string
from io import StringIO
df = pl.read_json(StringIO('[{"col1": 1, "col2": "a"}, {"col1": 2, "col2": "b"}]'))
```

### Writing JSON

```python
# Write NDJSON
df.write_ndjson("output.ndjson")

# Write standard JSON
df.write_json("output.json")

# write_json emits row-oriented JSON; pretty/row_oriented are not current arguments.
# To serialize a column dictionary explicitly:
import json
from pathlib import Path
Path("columns.json").write_text(json.dumps(df.to_dict(as_series=False)), encoding="utf-8")
```

## Excel Files

### Reading Excel

```python
# Read first sheet
df = pl.read_excel("data.xlsx")

# Specific sheet
df = pl.read_excel("data.xlsx", sheet_name="Sheet1")
# Sheet IDs are 1-based; 0 returns a dictionary containing every sheet.
df = pl.read_excel("data.xlsx", sheet_id=1)
sheets = pl.read_excel("data.xlsx", sheet_id=0)

# With options
df = pl.read_excel(
    "data.xlsx",
    sheet_name="Sheet1",
    columns=["sample_id", "value"],  # Header names or zero-based positions
    engine="calamine",
    read_options={"n_rows": 100, "skip_rows": 5},  # fastexcel options, after header
    has_header=True
)
```

### Writing Excel

```python
# Write to Excel
df.write_excel("output.xlsx")

# Multiple sheets: reading uses fastexcel by default, writing uses xlsxwriter.
import xlsxwriter
with xlsxwriter.Workbook("output.xlsx") as writer:
    df1.write_excel(workbook=writer, worksheet="Sheet1")
    df2.write_excel(workbook=writer, worksheet="Sheet2")
```

## Database Connectivity

### Read from Database

```python
import polars as pl

# A connection/cursor, not a URI keyword. Bind values through the driver.
import sqlite3
with sqlite3.connect("study.sqlite") as connection:
    df = pl.read_database(
        "SELECT * FROM observations WHERE value > ?",
        connection=connection,
        execute_options={"parameters": [25]},
    )

# URI route: requires connectorx (default) or ADBC plus a suitable driver.
import os
df = pl.read_database_uri(
    "SELECT * FROM observations WHERE value > 25",
    uri=os.environ["STUDY_DATABASE_URI"],
    engine="connectorx",
)
```

### Write to Database

```python
# Using SQLAlchemy
from sqlalchemy import create_engine

engine = create_engine("sqlite:///study.sqlite")

# Choose the table-existence policy explicitly.
df.write_database(
    "table_name",
    connection=engine,
    if_table_exists="fail",  # Explicitly choose "append" or "replace" only if intended
)
```

### Common Database Connectors

**PostgreSQL:**
```python
uri = os.environ["STUDY_POSTGRES_URI"]  # postgresql:// URI supplied by deployment
df = pl.read_database_uri("SELECT * FROM table", uri=uri)
```

**MySQL:**
```python
uri = os.environ["STUDY_MYSQL_URI"]  # mysql:// URI supplied by deployment
df = pl.read_database_uri("SELECT * FROM table", uri=uri)
```

**SQLite:**
```python
uri = "sqlite:///path/to/database.db"
df = pl.read_database_uri("SELECT * FROM table", uri=uri)
```

For large database results, `read_database(..., iter_batches=True, batch_size=...)`
returns an iterator, but server-side cursors/batching depend on the driver; it is
not a guarantee against a buffered full query. SQLAlchemy writes currently route
through pandas and need pandas/PyArrow plus the database driver. Escape URI
credentials correctly and use parameterized queries instead of string interpolation.

## Cloud Storage

Native cloud Parquet/scan APIs use the provider URI scheme and credential chain;
`fsspec` is not a universal requirement for them. Install `boto3` for the AWS
provider, `azure-identity` for Azure, or `google-auth` for GCP when using those
credential helpers. Provider APIs are marked unstable. Read/write permissions,
account/region, object paths, and storage options are deployment-specific. Polars
handles object listing and transport internally; this skill defines no REST
endpoint, request body, or pagination protocol.

### AWS S3

```python
# Read from S3
df = pl.read_parquet("s3://bucket/path/to/file.parquet")
lf = pl.scan_parquet("s3://bucket/path/*.parquet")

# Write to S3
df.write_parquet("s3://bucket/path/output.parquet")

# Prefer cloud profiles, IAM roles, or Polars credential providers over
# hardcoding secrets in scripts.
lf = pl.scan_parquet(
    "s3://bucket/file.parquet",
    credential_provider=pl.CredentialProviderAWS(profile_name="analytics"),
)
df = lf.collect()
```

### Azure Blob Storage

```python
# Read from Azure
df = pl.read_parquet("az://container/path/file.parquet")

# Write to Azure
df.write_parquet("az://container/path/output.parquet")

# Prefer managed identity or an Azure SDK credential provider.
from azure.identity import DefaultAzureCredential

df = pl.read_parquet(
    "abfss://container@account.dfs.core.windows.net/path/file.parquet",
    credential_provider=pl.CredentialProviderAzure(
        credential=DefaultAzureCredential()
    ),
)
```

### Google Cloud Storage (GCS)

```python
# Read from GCS
df = pl.read_parquet("gs://bucket/path/file.parquet")

# Write to GCS
df.write_parquet("gs://bucket/path/output.parquet")

# Prefer Application Default Credentials or workload identity configured
# outside the script.
df = pl.read_parquet("gs://bucket/path/file.parquet")
```

## Google BigQuery

Illustrative; install `google-cloud-bigquery`, `pyarrow`, and the applicable
Google authentication dependencies. Queries can incur provider charges.

```python
# Use the BigQuery SDK and Arrow interoperability
from google.cloud import bigquery
client = bigquery.Client()

query = "SELECT * FROM `project.dataset.table` LIMIT 100"
df = pl.from_arrow(client.query(query).result().to_arrow())
```

## Apache Arrow

### IPC/Feather Format

**Read:**
```python
df = pl.read_ipc("data.arrow")
lf = pl.scan_ipc("data.arrow")
```

**Write:**
```python
df.write_ipc("output.arrow")

# Compressed
df.write_ipc("output.arrow", compression="zstd")
```

### Arrow Streaming

```python
# IPC stream format is distinct from the seekable IPC file format.
df.write_ipc_stream("output.arrows", compression="zstd")
df = pl.read_ipc_stream("output.arrows")
```

### From/To Arrow

```python
import pyarrow as pa

# From Arrow Table
arrow_table = pa.table({"col": [1, 2, 3]})
df = pl.from_arrow(arrow_table)

# To Arrow Table
arrow_table = df.to_arrow()
```

## In-Memory Formats

### Python Dictionaries

```python
# From dict
df = pl.DataFrame({
    "col1": [1, 2, 3],
    "col2": ["a", "b", "c"]
})

# To dict
data_dict = df.to_dict()  # Column-oriented
data_dict = df.to_dict(as_series=False)  # Lists instead of Series
```

### NumPy Arrays

```python
import numpy as np

# From NumPy
arr = np.array([[1, 2], [3, 4], [5, 6]])
df = pl.DataFrame(arr, schema=["col1", "col2"], orient="row")

# To NumPy
arr = df.to_numpy()
```

### Pandas DataFrames

```python
import pandas as pd

# From Pandas
pd_df = pd.DataFrame({"col": [1, 2, 3]})
pl_df = pl.from_pandas(pd_df)

# To Pandas
pd_df = pl_df.to_pandas()

# Arrow-backed pandas output preserves nullable integer types.
pd_df = pl_df.to_pandas(use_pyarrow_extension_array=True)
```

### Lists of Rows

```python
# From list of dicts
data = [
    {"name": "Alice", "age": 25},
    {"name": "Bob", "age": 30}
]
df = pl.DataFrame(data)

# To list of dicts
rows = df.to_dicts()

# From list of tuples
data = [("Alice", 25), ("Bob", 30)]
df = pl.DataFrame(data, schema=["name", "age"], orient="row")
```

## Streaming Large Files

Streaming reduces intermediate memory. `collect` still materializes its full
output in RAM; use a `sink_*` terminal directly on the LazyFrame for large output.
Some operators maintain large state or fall back to in-memory execution:

```python
# Streaming mode
lf = pl.scan_csv("very_large.csv")
result = lf.filter(pl.col("value") > 100).collect(engine="streaming")

# Streaming with multiple files
lf = pl.scan_parquet("data/*.parquet")
result = lf.group_by("category").agg(pl.col("value").sum()).collect(engine="streaming")
```

## Best Practices

### Format Selection

**Use Parquet when:**
- Need compression (ratio depends on data and codec)
- Want fast reads/writes
- Need to preserve data types
- Working with large datasets
- Need predicate pushdown

**Use CSV when:**
- Need human-readable format
- Interfacing with legacy systems
- Data is small
- Need universal compatibility

**Use JSON when:**
- Working with nested/hierarchical data
- Need web API compatibility
- Data has flexible schema

**Use Arrow IPC when:**
- Need zero-copy data sharing
- Fastest serialization required
- Working between Arrow-compatible systems

### Reading Large Files

```python
# 1. Always use lazy mode
lf = pl.scan_csv("large.csv")  # NOT read_csv

# 2. Filter and select early (pushdown optimization)
result = (
    lf
    .filter(pl.col("date") > pl.date(2023, 1, 1))  # Assumes a Date column
    .select("col1", "col2", "col3")  # Keep filter dependencies until used
    .collect()
)

# 3. Use streaming for very large data
result = lf.filter(...).select(...).collect(engine="streaming")

# 4. Read only needed rows during development
df = pl.read_csv("large.csv", n_rows=10000)  # Sample for testing
```

### Writing Large Files

```python
# 1. Use Parquet with compression
df.write_parquet("output.parquet", compression="zstd")

# 2. Use partitioning for very large datasets
df.write_parquet("output", partition_by=["year", "month"])

# 3. Write streaming
lf = pl.scan_csv("input.csv")
lf.sink_parquet("output.parquet")  # Streaming write
```

### Performance Tips

```python
# 1. Specify dtypes when reading CSV
df = pl.read_csv(
    "data.csv",
    schema_overrides={"id": pl.String, "name": pl.String}  # Other columns still infer
)

# 2. Use appropriate compression
df.write_parquet("output.parquet", compression="snappy")  # Fast
df.write_parquet("output.parquet", compression="zstd")    # Better compression

# 3. CSV uses its thread pool by default; n_threads is an optional upper limit.
df = pl.read_csv("data.csv", n_threads=2)

# 4. Read multiple files in parallel
lf = pl.scan_parquet("data/*.parquet")  # Automatic parallel read
```

## Error Handling

```python
try:
    df = pl.read_csv("data.csv")
except pl.exceptions.ComputeError as e:
    print(f"Error reading CSV: {e}")

# For diagnosis, retain raw strings and inspect failed casts before deciding a policy.
raw = pl.read_csv("messy.csv", infer_schema=False)
parsed = raw.with_columns(value=pl.col("value").cast(pl.Float64, strict=False))
failed = raw.filter(raw["value"].is_not_null() & parsed["value"].is_null())
# Do not silently ignore parser failures or truncate ragged scientific records.

# Handle missing files
from pathlib import Path
if Path("data.csv").exists():
    df = pl.read_csv("data.csv")
else:
    print("File not found")
```

## Schema Management

A sampled schema does not prove later rows conform. A full CSV `schema` must
match file column order; `schema_overrides` only overrides selected inferred types.
Keep IDs with leading zeros as String. Reject duplicate raw CSV headers before
parsing because readers can rename them. Count parse failures, nulls, NaNs, and
nonfinite floats; validate units, time zones, and sample-key uniqueness separately.
For lazy inputs, use `lf.collect_schema()` (may read source metadata).

```python
# Infer schema from sample
schema = pl.read_csv("data.csv", n_rows=1000).schema

# Use inferred schema for full read
df = pl.read_csv("data.csv", schema=schema)

# Define schema explicitly
schema = {
    "id": pl.Int64,
    "name": pl.String,
    "date": pl.Date,
    "value": pl.Float64
}
df = pl.read_csv("data.csv", schema=schema)
```

## Local SQL expressions

`SQLContext` queries registered frames using Polars' local SQL dialect. This does
not contact a database and is separate from `read_database`.

```python
observations = pl.DataFrame({"sample_id": ["A", "A", "B"], "value": [1., 3., 10.]})
with pl.SQLContext(observations=observations.lazy(), eager=False) as ctx:
    query = ctx.execute(
        "SELECT sample_id, AVG(value) AS mean_value "
        "FROM observations GROUP BY sample_id"
    )
result = query.collect().sort("sample_id")
```

The default result is a LazyFrame; `eager=True` collects it. Register inputs
explicitly rather than relying on discovery of globals. Polars SQL is not an exact
replacement for a provider's SQL dialect. Validate null, order, and aggregate
semantics against the expression equivalent when migrating a query.
