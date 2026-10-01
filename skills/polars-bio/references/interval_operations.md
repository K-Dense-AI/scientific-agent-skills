# Genomic interval operations (polars-bio 0.36.0)

Use the [current API](https://biodatageeks.org/polars-bio/api/operations/) alongside
[release source](https://github.com/biodatageeks/polars-bio/blob/0.36.0/polars_bio/range_op.py).
Signatures alone are insufficient: `on_cols` is present but rejected. The examples
below use small synthetic half-open intervals and were executed on Polars 1.44.2.

## Prepare inputs

All eight operations accept Polars DataFrames/LazyFrames; supported registered
tables or file paths can also be supplied. Prefer explicit reader results when
format options or coordinate conventions matter. Default column names are
`chrom`, `start`, `end`; use `cols1`/`cols2` for two inputs, `cols` for one input,
and `view_cols` for complement bounds.

```python
import polars as pl
import polars_bio as pb

pb.set_option("datafusion.bio.coordinate_system_zero_based", True)
pb.set_option("datafusion.bio.coordinate_system_check", True)
a = pl.DataFrame({"chrom": ["chr1", "chr1", "chr2"],
                  "start": [0, 10, 0], "end": [10, 20, 10]})
b = pl.DataFrame({"chrom": ["chr1", "chr1"],
                  "start": [5, 8], "end": [12, 15]})
for frame in (a, b):
    frame.config_meta.set(coordinate_system_zero_based=True)
```

Validate assembly and contig aliases independently of coordinate metadata.
Require integer, non-null bounds, positive-length intervals, and finite genome
limits. Keep a row ID before a join if duplicate records are meaningful. The
COITrees backend uses signed Int32 interval positions even when the output
retains Int64 columns; check upper bounds before indexing.

## Overlap, hits, counts and covered bases

```python
pairs = pb.overlap(a, b, suffixes=("_query", "_target")).collect()
assert pairs.height == 4

hits = pb.overlap(a, b, overlap_output="left", distinct_output=True).collect()
assert hits.height == 2

counts = pb.count_overlaps(a, b).collect().sort("chrom", "start")
assert counts["count"].to_list() == [2, 2, 0]

covered = pb.coverage(a, b).collect().sort("chrom", "start")
assert covered["coverage"].to_list() == [5, 5, 0]
```

`overlap` defaults to an inner pair join, not a left join. Default suffixes are
`("_1", "_2")`. `overlap_output="left"` retains original left names; without
`distinct_output=True` the left row repeats per match. Distinct output operates
on source row identity, not unique coordinate values.

`count_overlaps` returns original query fields plus Int64 `count` (default
suffixes `("", "_")`). Default `naive_query=True` uses the native path and
internally exchanges operands, so a general build/probe memory rule does not
apply unchanged. Keep this tested default unless separately checking the
alternative strategy's schema, metadata and boundary behavior.

`coverage` returns original query fields plus Int64 `coverage`: union length of
intersections with targets. Overlapping targets do not double count a base.
For the example, two targets hit each chr1 query but only five bases per query
are covered. Divide by `end-start` for a half-open coverage fraction, or by
`end-start+1` for closed intervals. Read depth is a different measurement.

## Nearest

```python
nearest = pb.nearest(a, b, k=3).collect()
nonoverlapping = pb.nearest(a, b, overlap=False).collect()
without_distance = pb.nearest(a, b, distance=False).collect()
```

The defaults are `k=1`, `overlap=True`, `distance=True`, suffixes `("_1", "_2")`.
`k=3` is implemented in 0.36.0. A query with no target on its contig retains a
row whose target fields and distance are null. Requesting k larger than the
candidate set does not fabricate k real neighbors.

Distance counts intervening bases: `[0,10)` to `[10,20)` has distance 0;
`[0,10)` to `[12,20)` has distance 2. Closed `[1,10]` to `[11,20]` also has
zero intervening bases. Thus `distance == 0` is not an overlap test. Recompute
intersection using the proper inequality if that distinction matters.
Tie order is not a biological ranking: for reproducible annotation define an
explicit tie policy and test it. A self-nearest query can select the same row;
there is no documented `exclude_self` or strand-direction parameter here.

## Merge and cluster

```python
separate = pb.merge(a).collect()                # 3 rows: bookends stay separate
joined = pb.merge(a, min_dist=1).collect()       # chr1 becomes [0,20)
clusters = pb.cluster(a, min_dist=1).collect()
assert separate.height == 3
assert joined.height == 2
assert "n_intervals" in joined.columns
assert {"cluster", "cluster_start", "cluster_end"} <= set(clusters.columns)
```

In 0.36.0, `min_dist=0` merges overlapping intervals; it does not join adjacent
half-open bookends. For integer half-open bounds, `min_dist=1` joins bookends.
The effective gap threshold is strict in half-open mode: verify a gap equal to
and just below the chosen threshold. Closed-coordinate boundary comparisons
also depend on the coordinate metadata; do not transplant bioframe thresholds.

`merge` discards additional annotations and returns bounds plus `n_intervals`.
`cluster` retains rows and adds cluster labels and bounds; labels are execution
identifiers, not stable biological IDs. It has no `on_cols` parameter.

## Complement and subtract

```python
genome = pl.DataFrame({"chrom": ["chr1", "chr2"],
                       "start": [0, 0], "end": [20, 10]})
genome.config_meta.set(coordinate_system_zero_based=True)
gaps = pb.complement(b, view_df=genome).collect().sort("chrom", "start")
fragments = pb.subtract(a, b).collect().sort("chrom", "start")
assert fragments.select("chrom", "start", "end").rows() == [
    ("chr1", 0, 5), ("chr1", 15, 20), ("chr2", 0, 10)]
assert gaps.rows() == fragments.rows()
```

Give complement finite, valid, nonoverlapping assembly view bounds; check the
view's coordinates yourself rather than relying on two-input metadata validation.
Without a view the implementation extends contigs toward Int64 maximum, which
is not a genome definition. Subtraction can split one source interval into
several coordinate fragments and does not carry source annotations: rejoin to
explicit IDs if provenance matters, accounting for duplicate/overlapping sources.

## Grouping, output and execution

Non-None `on_cols` currently raises `AssertionError` for overlap, nearest,
coverage, count_overlaps and merge. For same-strand or within-sample operations,
partition both inputs by the grouping values, operate only on corresponding
partitions, and restore those keys in the output. Filtering an unstranded count
or nearest result after computation does not fix its semantics.

Most calls return LazyFrames; eager Polars, pandas (optional extra), and
`datafusion.DataFrame` output are supported by range operations. Avoid assuming
this `output_type` set applies to `depth` or `sql`. Interval method chaining is
`a.lazy().pb.overlap(b)`, not `a.pb.overlap(b)`. Projection after pair joins must
use suffixed names before feeding a new single-interval operation.

Output batch streaming does not mean constant memory: many operations retain
an index, sort or aggregate input, and `.collect()` materializes the final
result. Do not swap arguments solely to optimize memory when query semantics
must stay fixed. Benchmark a representative subset and use sinks for large
outputs. Parallel partitioning can alter output order; sort explicitly for
comparisons and reproducible exports.
