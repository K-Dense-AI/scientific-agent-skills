# deepTools 4.0.0 review and verification

Reviewed 2026-09-30 against official rolling documentation, the released 4.0.0
source and installed console entry points. The tested environment is Python 3.13
on macOS; deepTools requires Python >=3.12. No remote scientific service or user
data is required: these are local CLI and file-format contracts, not REST APIs.

## Contracts verified

| Surface | Verified behavior / correction |
| --- | --- |
| Installation | 4.0.0 supplies Rust-backed commands and macOS/Linux wheels; old 3.5.6 assumptions no longer apply |
| BAM coverage/comparison/summary | Shared read options removed --ignoreDuplicates; use already-marked duplicate flags with --samFlagExclude 1024; scaling is exact without --exactScaling |
| bamCompare | --scaleFactorsMethod accepts readCount/None, not SES; Rust RPGC ratio matches bamCoverage on a fixture despite docs claiming rejection; use --normalizeUsing separately from scaleFactorsMethod |
| Released arithmetic | BPM equals CPM; non-unity bamCoverage scaleFactor overrides normalization; bamCompare add/mean/first/second fall through to log2 and reciprocal_ratio has inverted magnitude |
| plotCorrelation | --whatToPlot heatmap/scatterplot, not --whatToShow (which belongs to plotHeatmap) |
| plotProfile | No --xAxisLabel; use supported reference/start/end labels |
| alignmentSieve | --ATACshift uses proper pairs; --ignoreDuplicates is flag based; shifting removes stored sequence; sort and index output |
| Shifted ATAC coverage | RPGC without extension yielded nonfinite signal on the shifted BAM; template uses CPM and validates output |
| RNA strands | dUTP transcript orientation; CPM on a strand with zero retained reads yielded nonfinite signal, so confirm strand counts first |
| computeMatrix | BED6 strands determine TSS orientation; reference-point and scale-regions numeric matrices checked |
| computeMatrixOperations | subset selects sample labels, not numeric indices; cbind matches BED6 identity against first matrix |
| multiBigwigSummary | --bwfiles, no BAM filtering flags; BED-region means verified; summary rows follow genomic order, not necessarily the input BED order |
| GC tools | computeGCBias needs --GCbiasFrequenciesFile, not --frequenciesFile; correction intentionally adds/removes reads |
| estimateReadFiltering | Samples bins via --binSize/--distanceBetweenBins, no --sampleSize or fragment-length filters; coordinate duplicates differ from marked duplicates |
| bigwigAverage / bigwigCompare | Released shared writer can omit final zero runs; fixedStep works for bigwigCompare; bigwigAverage lacks that switch |
| Genome sizes | Rolling table differs from tagged 4.0.0 values; record exact FASTA/contigs and method rather than treating assembly names as universal integers |

Remaining legacy read-processing code still differs from the Rust-backed commands.
In particular, help text about blacklist resolution can be inherited from a shared
parser without proving identical implementation behavior. Use a small interval
fixture to establish boundary behavior for the exact combination being used.
The skill does not recommend reproducing 3.5 analyses by silently changing to 4.0.

## Execution evidence

`tests/deeptools/test_runtime.py` creates tiny coordinate-sorted paired BAMs and
constant bigWigs. It checks retained-read CPM/RPKM/RPGC scaling, duplicate flags,
identical BAM log ratios, separate CPM normalization, plus/minus TSS order, region
scaling, sample-label subset, bigWig averaging/comparison, BED summaries, CSI index
validation and nonfinite/corrupt input rejection. The four generated workflows
execute to real BAM/bigWig/matrix/PNG outputs when external samtools is present.
RPGC output rounding required an absolute 0.005 numeric tolerance in this fixture.

The validator now decodes all BAM alignments and tests index access, checks every
BED interval (including gzip, metadata lines and late malformed rows), and opens
bigWig indexes. It checks the binary summary before native access: pyBigWig.header()
segfaulted on the nonfinite summary from the empty-strand coverage experiment.
It does not call that unsafe header path. It does not exhaustively inspect every
bigWig block, BED12 exon topology, index freshness, genome identity, or scientific
suitability. Compare reference dictionaries and provenance separately.

Not executed: real genome-scale sequencing analyses, GC correction with a reference
2bit genome, all visualization combinations, Linux/HPC/conda installs, or every
possible blacklist/missing-data boundary. GC examples remain illustrative. Generated
ChIP QC assumes paired-end samples for fragment-size analysis; expression and
differential binding require separate inferential workflows.

## Official sources

- [4.0.0 release notes](https://github.com/deeptools/deepTools/releases/tag/4.0.0)
- [PyPI release metadata](https://pypi.org/pypi/deeptools/4.0.0/json)
- [CLI overview](https://deeptools.readthedocs.io/en/latest/content/list_of_tools.html)
- [Released normalization source](https://github.com/deeptools/deepTools/blob/4.0.0/src/normalization.rs)
- [Released operation source](https://github.com/deeptools/deepTools/blob/4.0.0/src/calc.rs)
- [Released CLI source](https://github.com/deeptools/deepTools/tree/4.0.0/deeptools)
- [bamCoverage](https://deeptools.readthedocs.io/en/latest/content/tools/bamCoverage.html)
- [bamCompare](https://deeptools.readthedocs.io/en/latest/content/tools/bamCompare.html)
- [alignmentSieve](https://deeptools.readthedocs.io/en/latest/content/tools/alignmentSieve.html)
- [computeMatrix](https://deeptools.readthedocs.io/en/latest/content/tools/computeMatrix.html)
- [matrix operations](https://deeptools.readthedocs.io/en/latest/content/tools/computeMatrixOperations.html)
- [plotCorrelation](https://deeptools.readthedocs.io/en/latest/content/tools/plotCorrelation.html)
- [plotPCA](https://deeptools.readthedocs.io/en/latest/content/tools/plotPCA.html)
- [plotProfile](https://deeptools.readthedocs.io/en/latest/content/tools/plotProfile.html)
- [plotHeatmap](https://deeptools.readthedocs.io/en/latest/content/tools/plotHeatmap.html)
- [pyBigWig](https://github.com/deeptools/pyBigWig)
- [pysam](https://pysam.readthedocs.io/en/stable/api.html)

Rolling docs sometimes expose stale 3.5.6 content or fail to fetch (observed for the
GC pages); installed 4.0.0 help and released source were used to settle those flags.
