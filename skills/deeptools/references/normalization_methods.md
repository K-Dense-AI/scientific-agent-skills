# deepTools 4.0.0 normalization

Choose the denominator, counting unit and region universe before generating tracks.
A BAM contains alignments: paired mates are counted independently by default. For
one mate per pair use a consistent SAM-flag policy, for example
`--samFlagInclude 64` for first mates; this alone does not require proper pairing.
Record extension, mapping quality, duplicate marking/filtering and blacklist policy.
Normalization cannot repair confounding, batch effects or differing biological composition.

## bamCoverage methods

Let C be the count in an output bin, N the retained mapped-read count, L the bin
length in bases, F the read/fragment length used by the coverage model, and G the
effective genome size. Conceptually:

| Method | Scale | Interpretation |
| --- | --- | --- |
| None | C | Unscaled binned signal; valid when raw coverage is the intended quantity |
| CPM | C / (N / 1e6) | Library-size-scaled bin signal |
| RPKM | C / ((N / 1e6) * (L / 1000)) | RPKM of the output **bin**, not of a gene/transcript |
| BPM | C / (N / 1e6) in released 4.0.0 Rust code | Numerically CPM in this release; rolling docs describe a different denominator |
| RPGC | C / (N * F / G) | Signal relative to the model's 1x genome-wide depth |

RPGC values are normalized coverage, not observed absolute molecular abundance.
The 4.0.0 BPM formula algebraically cancels bin width and equals CPM, which was
verified numerically. RPGC derives its scale from read/extension statistics. A
`--region` run uses a restricted read universe; do not splice independently
normalized chromosome tracks into a genome-wide track without reconciling scales. Use
identical bin widths, contig/filter policies and counting units across samples.
In 4.0.0 the rewritten coverage backend computes scaling from all reads;
`--exactScaling` is removed.

```bash
# Illustrative hg38 reference value; verify the actual reference/contig set first.
bamCoverage -b chip.bam -o chip.bw --normalizeUsing RPGC \
    --effectiveGenomeSize 2913022398 --extendReads 200 \
    --samFlagExclude 1024 --binSize 10

# Spliced, reverse-stranded dUTP library: no extension.
bamCoverage -b rnaseq.bam -o forward.bw --normalizeUsing CPM \
    --filterRNAstrand forward --binSize 1
```

The first command assumes duplicates were marked upstream and 200 bp is an
appropriate single-end fallback (paired ends can supply fragment lengths).
The second's `forward` means transcript strand under the dUTP convention; libraries
with opposite orientation invert the labels. Unstranded libraries cannot be separated
into transcript strands by applying this option. Annotation-aware quantification is
required for gene/transcript expression; coverage tracks do not replace it.

## bamCompare contracts

`--scaleFactorsMethod` accepts **readCount** (default) or **None** in 4.0.0.
SES was removed. `--normalizeUsing` is separate: set `--scaleFactorsMethod None`
for RPKM, CPM or BPM normalization. The **released Rust bamCompare accepts RPGC**
with `--effectiveGenomeSize`; a tiny ratio fixture matched bamCoverage scaling.
This contradicts the rolling documentation note that it exits. For an easily
inspected RPGC comparison, generate two tracks using bamCoverage with consistent
settings, then compare them with bigwigCompare.

```bash
# Default read-count scaling followed by log2 ratio.
bamCompare -b1 chip.bam -b2 input.bam -o ratio.bw \
    --operation log2 --scaleFactorsMethod readCount \
    --pseudocount 1 --samFlagExclude 1024

# Per-file CPM scaling, then a difference (not a statistical test).
bamCompare -b1 chip.bam -b2 input.bam -o difference.bw \
    --scaleFactorsMethod None --normalizeUsing CPM --operation subtract

# Compare already-normalized tracks; do not normalize them a second time.
bigwigCompare -b1 chip.bw -b2 input.bw -o ratio_from_tracks.bw \
    --operation log2 --pseudocount 1 --fixedStep
```

`readCount` rescales the deeper library down to the shallower one: 100M versus 50M
reads receives factors 0.5 and 1, not 1 and 2. The common scale matters when adding
pseudocounts. Log2/ratio operations apply pseudocounts after scaling; choose their
units deliberately and save the value. In the released Rust implementation,
subtract also includes the pseudocounts: use equal values (they cancel) or zero.
Do not use its advertised add/mean/first/second operations: all fell through to
log2 in the tested release. reciprocal_ratio returned the inverse magnitude of
the documented result. Use separately generated tracks plus bigwigCompare for
those operations and inspect zero/missingness (below). `--skipZeroOverZero` omits bins where both
original signals are zero. Positive log2 values mean higher scaled treatment signal;
they do not establish differential binding, significance or absolute enrichment.

## Custom spike-in factors

A spike-in design requires its own reference, recovery assumptions, read assignment
and scaling derivation. RPGC does not implement spike-in normalization automatically.
Apply a justified factor with `--scaleFactor` and `--normalizeUsing None`.
**4.0.0 discrepancy:** the Rust source returns a non-unity manual factor before
computing normalization. A CPM+scaleFactor=2 probe produced 2, not twice CPM.
It therefore overrides, rather than multiplies, the requested normalization in
this release. Compute the desired combined factor explicitly instead.

```bash
# Illustrative factor only; derive from the experiment before using.
bamCoverage -b chip.bam -o chip_spike.bw --normalizeUsing None \
    --scaleFactor 0.8 --extendReads 200
```

For bamCompare, manual factors are `--scaleFactors 0.5:1`; specify
`--scaleFactorsMethod None` and leave `--normalizeUsing None` for a pure custom scale.

## Correlation and PCA

`multiBamSummary` produces counts, not CPM. Pearson/Spearman correlation is invariant
to positive sample-wise multiplication, so library-size scaling alone does not
change either correlation. Region selection, zeros, outliers, nonlinear transforms
and sample composition do. Constant columns make correlation undefined.
PCA is sensitive to scaling and transforms: record `--transpose`, `--log2`,
`--rowCenter` and `--ntop`. There is no universal replicate correlation cutoff.

## Effective genome size and exclusions

Use the exact contig set, non-N/mappability method, read length and filtering policy
recorded for the experiment; see `effective_genome_sizes.md`. `--ignoreForNormalization`
excludes named chromosomes from the denominator, not automatically from output.
Blacklist semantics changed in the rewritten 4.0 tools; do not assume all legacy
QC commands apply the same region handling. Compare retained-read and interval counts.
GC correction intentionally adds/removes reads; do not subsequently deduplicate the
corrected BAM and erase the correction.

Sources: [bamCoverage](https://deeptools.readthedocs.io/en/latest/content/tools/bamCoverage.html),
[bamCompare](https://deeptools.readthedocs.io/en/latest/content/tools/bamCompare.html),
[released normalization source](https://github.com/deeptools/deepTools/blob/4.0.0/src/normalization.rs),
[released operation source](https://github.com/deeptools/deepTools/blob/4.0.0/src/calc.rs),
[4.0.0 release](https://github.com/deeptools/deepTools/releases/tag/4.0.0).

**Verified 4.0.0 limitation:** the legacy bigwigCompare writer can drop a final
zero-valued run (an identical-track log2 comparison produced an empty bigWig).
Use `--fixedStep` to retain zero bins and inspect output coverage/missingness.

For shifted ATAC alignments, this skill uses CPM. The tested 4.0.0 alignmentSieve
output lacked stored sequences; RPGC without extension then produced nonfinite
coverage. Also check for zero retained reads in each RNA strand before normalizing:
an unrepresented strand produced NaN CPM output instead of a useful track.
