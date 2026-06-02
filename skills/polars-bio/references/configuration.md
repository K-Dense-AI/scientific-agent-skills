# Configuration

## Overview

polars-bio uses a global configuration system based on `set_option` and `get_option` to control execution behavior, coordinate systems, parallelism, and streaming modes.

## set_option / get_option

```python
import polars_bio as pb

# Set a configuration option
pb.set_option("datafusion.execution.target_partitions", 8)

# Get current value
value = pb.get_option("datafusion.execution.target_partitions")
```

## Parallelism

### DataFusion Target Partitions

Controls the number of parallel execution partitions. Defaults to 1 (single-threaded).

```python
import os
import polars_bio as pb

# Use all available CPU cores
pb.set_option("datafusion.execution.target_partitions", os.cpu_count())

# Set specific number of partitions
pb.set_option("datafusion.execution.target_partitions", 8)
```

**When to increase parallelism:**
- Processing large files (>1GB)
- Running interval operations on millions of intervals
- Batch processing multiple chromosomes

**When to keep default (1):**
- Small datasets
- Memory-constrained environments
- Debugging (deterministic execution)

## Coordinate Systems

polars-bio defaults to **1-based** coordinates (genomic convention). Configure globally with the DataFusion bio option (boolean, not a string):

### Global Coordinate System

```python
import polars_bio as pb

# Switch to 0-based half-open coordinates
pb.set_option("datafusion.bio.coordinate_system_zero_based", True)

# Switch back to 1-based (default)
pb.set_option("datafusion.bio.coordinate_system_zero_based", False)

# Check current setting ("true" or "false")
print(pb.get_option("datafusion.bio.coordinate_system_zero_based"))
```

### Strict Coordinate Metadata Checking

By default, missing coordinate metadata on manually constructed DataFrames triggers a warning and falls back to the global setting. Enable strict checking to raise `MissingCoordinateSystemError`:

```python
pb.set_option("datafusion.bio.coordinate_system_check", True)
```

When both inputs have metadata but different coordinate systems, interval operations raise `CoordinateSystemMismatchError`.

### Per-File Override via I/O Functions

I/O functions accept `use_zero_based` to set coordinate metadata on the resulting DataFrame:

```python
# Read with explicit 0-based metadata
df = pb.read_bed("regions.bed", use_zero_based=True)
```

**Note:** Interval operations (overlap, nearest, etc.) do **not** accept `use_zero_based`. They read coordinate metadata from the DataFrames, which is set by I/O functions or the global option. For manually constructed Polars DataFrames, attach metadata before calling interval ops:

```python
import polars as pl

df = pl.DataFrame({"chrom": ["chr1"], "start": [1], "end": [100]})
df.config_meta.set(coordinate_system_zero_based=False)  # 1-based
```

Alternatively, use `pb.set_source_metadata(df, format="bed", path="")` or I/O functions that set metadata automatically.

### File Format Conventions

| Format | Native Coordinate System | polars-bio Conversion |
|--------|-------------------------|----------------------|
| BED | 0-based half-open | Converted to configured system on read |
| VCF | 1-based | Converted to configured system on read |
| GFF/GTF | 1-based | Converted to configured system on read |
| BAM/SAM | 0-based | Converted to configured system on read |

## Streaming Execution Modes

polars-bio supports two streaming modes for out-of-core processing:

### DataFusion Streaming

Enabled by default for interval operations. Processes data in batches through the DataFusion execution engine.

```python
# DataFusion streaming is automatic for interval operations
result = pb.overlap(lf1, lf2)  # Streams if inputs are LazyFrames
```

### Polars Streaming

Use Polars' native streaming for post-processing operations:

```python
# Collect with Polars streaming engine
result = lf.collect(engine="streaming")
```

### Combining Both

```python
import polars_bio as pb

# Scan files lazily (DataFusion streaming for I/O)
lf1 = pb.scan_bed("large1.bed")
lf2 = pb.scan_bed("large2.bed")

# Interval operation (DataFusion streaming)
result_lf = pb.overlap(lf1, lf2)

# Collect with Polars streaming for final materialization
result = result_lf.collect(engine="streaming")
```

## Logging

Control log verbosity for debugging:

```python
import polars_bio as pb

# Set log level
pb.set_loglevel("debug")   # Detailed execution info
pb.set_loglevel("info")    # Standard messages
pb.set_loglevel("warn")    # Warnings only (default)
```

**Note:** Only `"debug"`, `"info"`, and `"warn"` are valid log levels.

## Metadata Management

polars-bio attaches coordinate system and source metadata to DataFrames produced by I/O functions. This metadata is used by interval operations to determine the coordinate system.

```python
import polars_bio as pb

# Inspect metadata on a DataFrame
metadata = pb.get_metadata(df)

# Print metadata summary
pb.print_metadata_summary(df)

# Print metadata as JSON
pb.print_metadata_json(df)

# Set metadata on a manually created DataFrame
pb.set_source_metadata(df, format="bed", path="regions.bed")

# Register a DataFrame as a SQL table
pb.from_polars("my_table", df)
```

## Complete Configuration Reference

| Option | Default | Description |
|--------|---------|-------------|
| `datafusion.execution.target_partitions` | `1` | Number of parallel execution partitions |
| `datafusion.bio.coordinate_system_zero_based` | `false` | Global coordinate system (`true` = 0-based half-open, `false` = 1-based) |
| `datafusion.bio.coordinate_system_check` | `false` | When `true`, raise `MissingCoordinateSystemError` if inputs lack coordinate metadata |
| `bio.interval_join_algorithm` | `"coitrees"` | Interval join algorithm (`Coitrees`, `IntervalTree`, `ArrayIntervalTree`, `Lapper`, `SuperIntervals`) |
