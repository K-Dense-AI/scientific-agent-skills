# Overlap, counts, set algebra, and consensus

Locally tested with Python 0.10.0; Rust/CLI 0.10.0 source reviewed on **2026-10-01**.

## Interval meaning

Use 0-based, half-open intervals. Two valid intervals overlap when:

```text
a.start < b.end and b.start < a.end
```

Thus `[0,10)` overlaps `[9,20)` but not adjacent `[10,20)`. Validate assembly,
exact contig names, `start < end`, chromosome bounds, and Gtars' `u32` coordinate
limit before indexing.

Overlap and reduction answer different questions:

- overlap/query methods use ordinary half-open overlap;
- `reduce()` merges overlapping **and adjacent** intervals;
- `union()` reduces the concatenated sets;
- consensus first reduces the union, so adjacency can combine support domains.

## Python directional overlap queries

```python
from gtars.models import RegionSet

query = RegionSet("query.bed")
universe = RegionSet("universe.bed")

counts = query.count_overlaps(universe)
any_hit = query.any_overlaps(universe)
hit_indices = query.find_overlaps(universe)
query_with_hits = query.subset_by_overlaps(universe)
```

Interpretation is directional:

- `counts[i]` is the number of universe intervals overlapping query interval `i`;
- `any_hit[i]` is a boolean for query interval `i`;
- `hit_indices[i]` contains 0-based indices into the in-memory `universe`;
- `subset_by_overlaps` preserves only query intervals with one or more hits.

Both file-backed sets are sorted by the constructor. Do not join these arrays to
the original unsorted row number without carrying a separate stable identifier.

For actual intersection coordinates:

```python
pieces = query.intersect_all(universe)
```

`intersect_all` computes `[max(starts), min(ends))` for every overlapping pair.
It differs from `pintersect`, which pairs two sets by index position, truncates
to the shorter length, and emits zero-width placeholders for nonoverlaps.
Validate equal length and pairing before using it.

## Base-pair set metrics

```python
reduced = query.reduce()
difference = query.setdiff(universe)
combined = query.concat(universe)
union = query.union(universe)
pairwise = query.pintersect(universe)

jaccard = query.jaccard(universe)
covered_fraction = query.coverage(universe)
overlap_coefficient = query.overlap_coefficient(universe)
```

- Jaccard: `intersection_bp / union_bp`.
- Coverage: fraction of query base pairs covered by universe after overlap
  normalization.
- Overlap coefficient: `intersection_bp / min(query_bp, universe_bp)`.
- `concat` does not merge; `union` does.
- `setdiff` can split query intervals.

Empty-set edge cases and zero denominators should be tested with the exact pinned
version before relying on metric values.

## Rust index API

The exact wrapper dependency is:

```toml
[dependencies]
gtars = { version = "=0.10.0", default-features = false, features = [
  "core", "overlaprs"
] }
```

The following source-reviewed Rust template was not compiled in this audit:

```rust
use gtars::core::models::RegionSet;
use gtars::overlaprs::IndexedRegionSet;
use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {
    let universe = RegionSet::try_from("universe.bed")?;
    let query = RegionSet::try_from("query.bed")?;
    let index = IndexedRegionSet::new(universe);

    let counts = index.count_overlaps(&query, None);
    let flags = index.any_overlaps(&query, None);
    let hits = index.find_overlaps(&query, None);

    assert_eq!(counts.len(), query.len());
    assert_eq!(flags.len(), query.len());
    assert_eq!(hits.len(), query.len());
    Ok(())
}
```

The optional second argument is a region filter in the component API; `None`
queries all regions. Consult the exact
[`gtars-overlaprs 0.6.0` docs](https://docs.rs/gtars-overlaprs/0.6.0/gtars_overlaprs/)
compatible with the 0.10.0 wrapper (0.6.1 removes an unused error type).
Record the actual Cargo.lock resolution.

## CLI `overlaprs` is not a count command

The current CLI form is:

```bash
gtars overlaprs \
  --query query.bed \
  --universe universe.bed \
  --backend bits
```

Valid backends are `bits` and `ailist`; the handler defaults to `bits`. The
command writes every overlapping **universe interval** as BED3 to stdout. It does
not emit query coordinates, query IDs, universe IDs, or one count per query.
Repeated universe hits can therefore be indistinguishable in the output.
Unlike `RegionSet(path)`, this CLI reader does not skip comment, browser, track,
header, or blank rows: prepare a separate header-free BED file before invoking it.

Use Python `count_overlaps` when row-aligned counts are required. The CLI exposes
a `--streaming` flag in 0.10.0, but the tagged handler does not read it; do not
claim lower memory from that flag.

Build a non-executing local plan first:

```bash
python3 -B scripts/execution_plan.py \
  --operation overlap \
  --query query.bed \
  --universe universe.bed \
  --assembly GRCh38.p14 \
  --chrom-sizes GRCh38.p14.chrom.sizes
```

## Consensus semantics

Python:

```python
from gtars.genomic_distributions import consensus

rows = consensus([replicate_a, replicate_b, replicate_c])
```

CLI:

```bash
gtars consensus \
  --beds replicate_a.bed replicate_b.bed replicate_c.bed \
  --min-count 2 \
  --output consensus.bed
```

The algorithm:

1. concatenates every set;
2. reduces all ranges to a non-overlapping union, merging adjacency;
3. for each union range, counts how many input **sets** have at least one overlap;
4. returns BED4-like `chr, start, end, count`, sorted by chromosome/start.

It does not cut ranges at every support transition. For example, partially
overlapping `[0,10)` and `[5,15)` produce union `[0,15)` with count 2, even though
the edges are supported by one set. This is set-level support for a merged union
component, not per-base support.

`--min-count` filters after consensus computation and must be positive. Validate
that it does not exceed the number of input sets.

## Replicates and leakage

- Define biological replicate/donor/patient groups before consensus.
- Keep all samples from one patient in one train/validation/test split.
- Build a training consensus/universe from training replicates only.
- Do not use held-out overlap counts to tune `min-count`, merge gaps, blacklist
  handling, or backend parameters.
- Report per-replicate support and exclusions; a merged consensus is not evidence
  that every replicate supports every base.

## Scaling and bounds

- `RegionSet` loads full interval vectors and sorts them.
- Index memory scales with universe size; hit output can scale with the number of
  overlap pairs, much larger than either input.
- Cap input records/bytes, output rows/bytes, memory, and wall time.
- Pilot both backends on representative training data; identical semantics and
  deterministic result ordering must be verified before switching.
- Keep stdout redirected only to an approved nonexisting output path and verify
  it after completion.

## Removed stale APIs

There is no current Python `gtars.igd.build_index`, `igd.query`,
`filter_overlapping`, `filter_non_overlapping`, `overlap_fraction`, or
`overlap_coverage` surface matching the old skill. CLI `igd` has only `create`
and `search`; see `cli.md`.

## Official sources (accessed 2026-10-01)

- [Python RegionSet 0.10.0 binding](https://github.com/databio/gtars/blob/gtars-python-v0.10.0/gtars-python/src/models/region_set.rs)
- [Rust overlaprs source at v0.10.0](https://github.com/databio/gtars/tree/gtars-v0.10.0/gtars-overlaprs)
- [CLI overlap parser](https://github.com/databio/gtars/blob/gtars-v0.10.0/gtars-cli/src/overlaprs/cli.rs)
- [CLI overlap handler/output](https://github.com/databio/gtars/blob/gtars-v0.10.0/gtars-cli/src/overlaprs/handlers.rs)
- [Consensus implementation](https://github.com/databio/gtars/blob/gtars-v0.10.0/gtars-genomicdist/src/consensus.rs)
- [Gtars overlap module guide](https://docs.bedbase.org/gtars/overlaprs/)
