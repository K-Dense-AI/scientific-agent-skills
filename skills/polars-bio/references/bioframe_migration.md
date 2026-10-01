# Migrate from bioframe to polars-bio 0.36.0

Treat migration as a semantic port. Similar function names do not make the two
libraries drop-in replacements. Compare the [polars-bio range API](https://biodatageeks.org/polars-bio/api/operations/)
with the [bioframe interval API](https://bioframe.readthedocs.io/en/latest/api-intervalops.html).

| bioframe operation | polars-bio counterpart | Check during migration |
|---|---|---|
| `overlap` | `overlap` | bioframe defaults to left join; polars-bio outputs inner pairs |
| `closest` | `nearest` | k, ties, self-matches, no-target nulls, zero-gap distance |
| `count_overlaps` | `count_overlaps` | Count target records per original query, including duplicates |
| `coverage` | `coverage` | Union-covered bases, not hit counts or read depth |
| `merge` | `merge` | Different bookend/min_dist boundary behavior |
| `cluster` | `cluster` | Labels/bounds and preservation of input rows |
| `complement` | `complement(view_df=...)` | Explicit finite view DataFrame, matched coordinates |
| `subtract` | `subtract` | Fragment output lacks source annotations |

## Coordinates and schemas first

Bioframe typically uses BED-style 0-based half-open coordinates. polars-bio's
native readers default to **1-based closed**, including BED conversion. Specify
`use_zero_based=True` on readers when porting BED workflows. For manually built
Polars frames, attach `coordinate_system_zero_based=True` after verifying the
actual values. Metadata labels do not convert coordinates.

```python
# Template: both files use the same reference assembly.
import polars as pl
import polars_bio as pb

pb.set_option("datafusion.bio.coordinate_system_zero_based", True)
pb.set_option("datafusion.bio.coordinate_system_check", True)
peaks = pb.scan_table("peaks.bed6", schema="bed6")
peaks.config_meta.set(coordinate_system_zero_based=True)
genes = pb.scan_table("genes.bed6", schema="bed6")
genes.config_meta.set(coordinate_system_zero_based=True)

hits = pb.overlap(peaks, genes, suffixes=("_peak", "_gene")).collect()
```

Use `scan_table(..., schema="bed6")` if score/strand matter: `scan_bed` exposes
only BED4 fields even when the input has six or twelve columns. Generic table
readers do not automatically attach genomic coordinate metadata. Read schemas
by actual type, including unsigned positions and nested VCF/GFF attributes.

## Boundaries and grouping are not interchangeable

For half-open `[0,10)` and `[10,20)`, 0.36.0 `merge(min_dist=0)` returns two
intervals; `min_dist=1` joins them. Bioframe's default `min_dist=0` joins bookends.
Do not blanket-replace thresholds for every coordinate convention: test exact
gap boundaries and closed-coordinate inputs separately.

polars-bio signatures expose `on_cols` but currently reject non-None values.
Port stranded/sample-specific work by splitting matching input groups, applying
the operation and restoring group labels. A post-filter on joined strand
columns cannot correct an already computed count or nearest choice.

Default overlap returns only matched pairs. To reproduce a bioframe left join,
preserve stable query IDs and explicitly join unmatched query IDs back with null
target fields; `overlap_output="left"` means left **hits**, not a SQL left join.
Duplicate rows and multiple target hits require cardinality checks.

## pandas interoperability

```bash
uv pip install "polars-bio[pandas]==0.36.0" "polars==1.44.2"
```

The pandas extra requires pandas >=3.0. Optional conversion template:

```python
# pandas_df already contains half-open coordinates.
polars_df = pl.from_pandas(pandas_df)
polars_df.config_meta.set(coordinate_system_zero_based=True)
result = pb.merge(polars_df, min_dist=1).collect()
pandas_result = result.to_pandas()
pandas_result.attrs["coordinate_system_zero_based"] = True
```

Range APIs also support `output_type="pandas.DataFrame"`. A pandas index is not
an automatic stable row-ID column in Polars; materialize it deliberately when
needed. `LazyFrame.pb` supplies interval chaining; `DataFrame.pb` is for writes.

## Acceptance fixture before a large migration

Include intervals that are disjoint, overlapping, nested, duplicated and exactly
bookended; at least one absent contig; multiple nearest ties; and strand groups.
Check pair cardinality, zero-hit preservation, union length, complement bounds,
subtracted fragment provenance and coordinate metadata. Validate native Int32
indexing limits and Int16 depth limits before any custom-coordinate/deep-read job.

A lazy output is not a guarantee of bounded working memory: index builds, merge,
sort, aggregation and final collection can materialize substantial data. Measure
runtime and peak memory on representative data rather than repeating a fixed
speedup claim. The upstream paper reports operation- and dataset-specific
benchmarks; it does not establish a universal bioframe replacement performance.
