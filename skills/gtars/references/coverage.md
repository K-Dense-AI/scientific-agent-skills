# Coverage, uniwig, and bigWig

Source-reviewed against `gtars-cli==0.10.0` / `gtars-uniwig==0.9.0` on
**2026-10-01**; CLI/Rust templates were not executed in this audit. Published
crate source takes precedence when older guide examples differ.

## Distinguish two meanings of coverage

- Python `RegionSet.coverage(other)` returns a single fraction of base pairs in
  the first set covered by the second.
- `gtars uniwig` creates positional signal tracks (WIG, NPY, bedGraph, bigWig,
  and limited BAM-derived outputs).

Python 0.10.0 does not export `gtars.uniwig`. Old examples using
`gtars.uniwig.coverage_from_bed`, `coverage.normalize()`, `smooth()`,
`call_peaks()`, or `to_bigwig()` are not current APIs.

## Input contract

For BED and narrowPeak:

1. use 0-based half-open intervals;
2. supply the exact assembly's local `chrom.sizes`;
3. require every contig to exist and every end to be within bounds;
4. sort by chromosome dictionary order, then numeric start/end;
5. use one local file (BED, narrowPeak, or BAM);
6. preserve strand separately—uniwig's BED path produces start/end/core counts,
   not a generic BED6 strand-aware split.

The official module guide states that uniwig expects a single chromosome-sorted
input. Never concatenate samples, patients, or assemblies without a reviewed
aggregation policy.

Run the deterministic preflight:

```bash
python3 -B scripts/coverage_preflight.py \
  --input fragments.sorted.bed.gz \
  --input-type bed \
  --chrom-sizes GRCh38.p14.chrom.sizes \
  --assembly GRCh38.p14 \
  --output-prefix derived/sample01 \
  --output-type bw \
  --count-type core \
  --threads 4
```

It validates local paths, bounds, sorting, Gtars `u32` coordinates, output
prefix collisions (including derived output files), and a dense-value budget
rounded separately for each contig. It writes and executes
nothing.

## Current batch CLI

BigWig generation uses the root `uniwig` command directly—there is no `generate`
subcommand:

```bash
gtars uniwig \
  --file fragments.sorted.bed.gz \
  --filetype bed \
  --chromref GRCh38.p14.chrom.sizes \
  --smoothsize 5 \
  --stepsize 1 \
  --fileheader derived/sample01_ \
  --outputtype bw \
  --counttype core \
  --threads 4 \
  --zoom 1
```

Equivalent short options are `-f`, `-t`, `-c`, `-m`, `-s`, `-l`, `-y`, `-u`,
`-p`, and `-z`. Valid batch count types are:

- `start`: accumulations at interval starts;
- `end`: accumulations at interval ends;
- `core`: interval-body accumulations;
- `all`: produce start, end, and core;
- `shift`: BAM-specific shifted workflow.

The implementation accepts `wig`, `npy`, `bedgraph`, `bw`, and `bigwig` strings
along relevant paths, but use the documented compact `bw` for BigWig. BED and
narrowPeak can produce WIG, NPY, bedGraph, or BigWig. BAM paths produce BigWig or
BED in the documented workflow.

Other batch flags:

- `--score` uses narrowPeak score;
- `--bamscale FLOAT` scales BAM values (default `1.0`);
- `--no-bamshift` disables direction-aware BAM shifting;
- `--wigstep fixed|variable` selects WIG step style;
- `--debug` increases output.

Validate scientific meaning before using start/end/shift signals. ATAC cut-site
shifts and ChIP fragment-body counts are not interchangeable.

## Streaming mode

For large **BED** input, CLI 0.10.0 exposes a streaming processor. Memory still
depends on the operation and interval distribution; pilot representative data:

```bash
gtars uniwig \
  --file fragments.sorted.bed.gz \
  --filetype bed \
  --chromref GRCh38.p14.chrom.sizes \
  --smoothsize 5 \
  --stepsize 1 \
  --fileheader derived/sample01_ \
  --outputtype bedgraph \
  --counttype core \
  --streaming \
  --dense 0
```

Streaming constraints in tagged source:

- only BED input;
- only `wig` or `bedgraph` output, not BigWig or NPY;
- count type `start`, `end`, `core`, or `all` (not BAM `shift`);
- `--dense 0` is sparse, `--dense -1` is fully dense, and positive `N` fills
  gaps no wider than `N`;
- `--stdout` is available; multiple count types receive separator comments.

If stdin is used with `--counttype all`, the handler buffers stdin into memory so
it can replay it. Do not claim constant memory for that combination.

## BAM QC and BAM coverage

Library-complexity metrics are a subcommand:

```bash
gtars uniwig bamqc \
  --input aligned.bam \
  --output bamqc.tsv \
  --threads 1
```

Parallel BAM QC (`--threads >1`) requires a `.bai` index. Bound BAM size, index
size, decompression work, threads, and output. Metrics NRF/PBC1/PBC2 are technical
QC summaries, not evidence of biological quality or suitability.

For BAM-to-bigWig, the batch path requires the same `--smoothsize`,
`--stepsize`, `--fileheader`, `--chromref`, and output controls. Keep alignment
assembly, filtering, duplicate policy, paired-end handling, and shift/scaling in
the provenance record.

## BigWig preflight and postflight

Before generation:

- verify the exact chromosome dictionary and checksum;
- reject unknown/out-of-bounds contigs;
- ensure sorted input and numeric signal values;
- reserve disk for intermediate bedGraph plus final BigWig;
- set threads explicitly (upstream batch default is 6);
- use a new output prefix;
- avoid patient identifiers in filenames and track labels.

After generation:

- verify nonzero file size and BigWig readability with a trusted, pinned reader;
- compare its chromosome dictionary and lengths with the input checksum;
- query fixed synthetic positions with known expected coverage;
- check min/max/NaN behavior and start/end/core suffixes;
- record SHA-256, tool versions, parameters, and input hashes.

UCSC documents bedGraph coordinates as 0-based half-open and numerically ordered.
Its BigWig tools require matching chromosome sizes. A successful binary write
does not prove the assembly or signal semantics are correct.

## Rust APIs

Enable only uniwig:

```toml
[dependencies]
gtars = { version = "=0.10.0", default-features = false, features = ["uniwig"] }
```

The wrapper re-exports `gtars_uniwig` as `gtars::uniwig`. The primary batch
function is:

```text
uniwig_main(
  vec_count_type, smoothsize, filepath, chromsizerefpath, bwfileheader,
  output_type, filetype, num_threads, score, stepsize, zoom, debug,
  bam_shift, bam_scale, wigstep
) -> Result<(), Box<dyn Error>>
```

It is deliberately string-heavy and has many arguments; prefer the pinned CLI
unless embedding is necessary. The typed streaming API is:

```text
uniwig::stream::uniwig_streaming(
  input, output, chrom_sizes, smooth_size, step_size,
  CountType::{Start|End|Core},
  OutputFormat::{Wig|BedGraph},
  max_gap
)
```

`read_chrom_sizes(BufRead)` parses the dictionary. BigWig is a batch API, not a
streaming `OutputFormat`.

## Threading and resources

- Batch uniwig builds a Rayon pool of exactly `--threads`; the CLI default is 6.
- Streaming mode is not controlled by the batch `--threads` path.
- Output work can scale with total assembly span divided by step size, not only
  with BED row count.
- Smoothing, dense gap filling, three count types, BigWig intermediates, and high
  thread counts can multiply memory/disk.
- Start with one thread and one small synthetic contig. Increase only after
  measuring peak RSS, temporary disk, throughput, and deterministic equivalence.

## Official sources (accessed 2026-10-01)

- [Gtars uniwig module guide](https://docs.bedbase.org/gtars/uniwig/)
- [CLI uniwig parser at gtars-v0.10.0](https://github.com/databio/gtars/blob/gtars-v0.10.0/gtars-cli/src/uniwig/cli.rs)
- [CLI uniwig handler at gtars-v0.10.0](https://github.com/databio/gtars/blob/gtars-v0.10.0/gtars-cli/src/uniwig/handlers.rs)
- [Rust uniwig 0.9.0 source](https://github.com/databio/gtars/tree/gtars-v0.10.0/gtars-uniwig)
- [UCSC bedGraph format](https://genome.ucsc.edu/goldenPath/help/bedgraph.html)
- [UCSC BigWig format](https://genome.ucsc.edu/goldenPath/help/bigWig.html)
