# Read depth (polars-bio 0.36.0)

`pb.depth()` computes CIGAR-aware read depth for BAM, SAM and self-contained
CRAM input. This differs from `pb.coverage(query, targets)`, which measures
union-covered interval length. See the [depth API](https://biodatageeks.org/polars-bio/api/operations/)
and [pinned native coverage implementation](https://github.com/biodatageeks/datafusion-bio-functions/blob/v0.22.2/datafusion/bio-function-pileup/src/coverage.rs).

## Arguments and output

```python
# Template: supply a validated alignment file.
import polars_bio as pb
blocks = pb.depth("sample.bam", use_zero_based=True,
                   filter_flag=1796, min_mapping_quality=20).collect()
```

| Argument | Default | Meaning |
|---|---|---|
| `filter_flag` | `1796` | Exclude reads carrying any bit in mask |
| `min_mapping_quality` | `0` | Minimum MAPQ; no base-quality filtering |
| `binary_cigar` | `True` | Binary CIGAR path |
| `dense_mode` | `"auto"` | Dense when contig lengths are available; also `"force"` / `"disable"` |
| `use_zero_based` | `None` | Session convention; True requests half-open/zero-based |
| `per_base` | `False` | True requires dense accumulation with contig lengths |
| `output_type` | `"polars.LazyFrame"` | Also `"polars.DataFrame"` or optional `"pandas.DataFrame"` |

Block columns: `contig` String, `pos_start`/`pos_end` Int32, `coverage` Int16.
Per-base columns: `contig` String, `pos` Int32, `coverage` Int16. The default
block output omits zero-depth blocks in the exercised fixtures. Per-base dense
output includes zeroes across represented contig lengths. Check which contigs
were emitted, especially contigs with no reads, rather than assuming a whole
reference denominator. Dense accumulation needs memory proportional to contig
length even when the returned run-length encoding is small.

Index files are auto-discovered but a sequential SAM/BAM scan works without
one. The Python depth API has no `reference_path`; external-reference CRAM needs
a suitable conversion to BAM, whereas `read_cram` can accept a local reference.
Do not pass CRAM-reader or cloud-I/O keyword arguments that depth does not expose.

## Filters and CIGAR semantics

Default 1796 = 4 + 256 + 512 + 1024: excludes unmapped, secondary, QC-failed and
duplicate reads. Supplementary (2048) is **not** excluded. If the protocol calls
for excluding it, use `filter_flag=1796 | 2048`. MAPQ 255 often means unavailable
mapping quality; a lower-bound threshold does not automatically exclude it.

Native CIGAR behavior, verified with a synthetic spliced/deletion-bearing read:

| Operation | Coverage effect |
|---|---|
| `M`, `=`, `X` | Count aligned reference positions |
| `D`, `N` | Advance reference position without coverage |
| `I`, `S`, `H`, `P` | Do not add covered reference positions |

For a read starting at SAM POS 2 with `3M2D2M3N2M`, half-open covered blocks are
`[1,4)`, `[6,8)`, `[11,13)`. Deletions are not counted as aligned bases.
The API does not expose minimum base quality or paired-mate overlap correction;
report this as read coverage, not fragment coverage or a nucleotide pileup.
Align filter semantics before comparing with samtools/mosdepth defaults.

## Native numerical limitation

In 0.36.0, depth accumulation is emitted via a narrowing Int16 cast. A tiny
fixture of **32,768 reads at one base returned -32,768**. This is silent overflow,
not negative biological coverage. High positive counts may also wrap to plausible
small values, so merely checking for negatives is insufficient. Choose an
independent wider-depth implementation when such depths are possible; widening
the already emitted result does not repair it. Cast to Int64 before subsequent
multiplication/summation only when source depth is known to be within range.

## Correct summary denominators

Do not average block rows: long and short blocks represent different numbers of
bases. This executed synthetic example includes known zero-depth target space:

```python
import polars as pl

# Half-open blocks entirely within a known 20-base assay target.
blocks = pl.DataFrame({"pos_start": [0, 10], "pos_end": [10, 15],
                        "coverage": [2, 4]})
target_bases = 20
summary = blocks.select(
    ((pl.col("pos_end").cast(pl.Int64) - pl.col("pos_start").cast(pl.Int64))
      * pl.col("coverage").cast(pl.Int64)).sum().alias("aligned_base_total")
)
mean_depth_over_target = summary["aligned_base_total"][0] / target_bases
assert mean_depth_over_target == 2.0  # 10*2 + 5*4 over 20 bases
```

For a real panel, merge/normalize target intervals to a nonoverlapping union,
intersect blocks with those targets, calculate **clipped intersection lengths**,
then divide the weighted total by the entire union length, including uncovered
bases. A left overlap join alone does not clip bounds; repeated overlapping
targets can double count. For closed intervals the length formula adds one.
A block-row median is not a base-weighted median; build a depth histogram weighted
by represented bases and add the zero-depth remainder instead.

## Adequately covered regions and gaps

```python
# Template: this call explicitly requests half-open coordinates.
depth = pb.depth("sample.bam", use_zero_based=True).collect()
intervals = depth.rename({"contig": "chrom", "pos_start": "start", "pos_end": "end"})
intervals.config_meta.set(coordinate_system_zero_based=True)
adequate = intervals.filter(pl.col("coverage") >= 30)
# min_dist=1 merges adjacent integer half-open blocks in 0.36.0.
merged = pb.merge(adequate, min_dist=1).collect()

# Bounds must match the assembly or assay being assessed.
genome = pl.DataFrame({"chrom": ["chr1"], "start": [0], "end": [1000]})
genome.config_meta.set(coordinate_system_zero_based=True)
gaps = pb.complement(adequate, view_df=genome).collect()
```

For panel QC use the panel bounds, not arbitrary whole-chromosome sizes. Report
assembly, mask/quality filters, read versus fragment semantics, coordinate
convention, low-coverage threshold and denominator together.
