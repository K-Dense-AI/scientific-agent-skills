# CRAM, Remote I/O, Threads, and Performance

This reference targets pysam 0.24.0, which embeds HTSlib/samtools/bcftools
1.23.1.

## Pysam 0.24 CRAM Changes

Pysam 0.24 is the first pysam release to wrap HTSlib 1.22 or later. Two
inherited operational changes matter:

1. New CRAM output defaults to CRAM **3.1**, not 3.0.
2. HTSlib no longer contacts the EBI CRAM reference server by default.

For compatibility with a consumer that cannot read CRAM 3.1:

```python
with pysam.AlignmentFile(
    "output.cram",
    "wc",
    header=header,
    reference_filename="reference.fa",
    format_options=["version=3.0"],
) as output:
    ...
```

In pysam 0.24, `format_options` accepts a list of Python `str` values as
documented.

## Why the Reference Matters

CRAM commonly stores differences from a reference rather than complete read
sequences. A matching reference can therefore be required to decode or encode
records.

Reference identity is represented by `M5` MD5 values and often `UR` fields in
`@SQ` header lines. Contig names alone are not sufficient.

Treat the reference as part of the data provenance:

- preserve the exact FASTA used to create the CRAM
- preserve its `.fai`
- record assembly/version and checksum
- back up reference cache content when it is the only decoding source
- verify contig lengths and M5 tags

Some CRAM files embed all or part of their reference, but do not assume that
every CRAM is self-contained.

## Deterministic Local CRAM Access

Prefer an explicit local FASTA:

```python
import pysam

pysam.faidx("reference.fa")

with pysam.AlignmentFile(
    "sample.cram",
    "rc",
    reference_filename="reference.fa",
    require_index=True,
    threads=4,
) as cram:
    for read in cram.fetch("chr1", 1_000, 2_000):
        ...
```

Use the same reference when writing:

```python
with pysam.AlignmentFile("input.bam", "rb") as source, pysam.AlignmentFile(
    "output.cram",
    "wc",
    template=source,
    reference_filename="reference.fa",
    threads=4,
) as destination:
    for read in source.fetch(until_eof=True):
        destination.write(read)
```

Then create a CRAI and read the output back with the same FASTA.

## `REF_PATH` and `REF_CACHE`

Use these HTSlib environment variables only when reference-by-MD5 lookup is
intentional:

- `REF_PATH`: colon-separated local paths and optionally URLs used to find a
  sequence by its M5 checksum
- `REF_CACHE`: location where retrieved references are cached

A local cache layout commonly uses:

```text
/reference-cache/%2s/%2s/%s
```

Do not add a remote endpoint merely to make an error disappear. Network
reference lookup changes reproducibility, privacy, availability, and cache
behavior. Pysam 0.24 intentionally inherits HTSlib's removal of implicit EBI
fetching.

When remote lookup is required:

- configure a controlled institutional proxy/cache where possible
- place a local cache before remote sources
- ensure downloads are checksum-validated
- document network and retention behavior
- avoid credentials in URLs and logs

An explicit `reference_filename=` is usually clearer for a single known
assembly.

## Convert BAM to CRAM with Wrapped Samtools

For bulk conversion:

```python
import pysam.samtools

pysam.samtools.view(
    "-@",
    "4",
    "-C",
    "-T",
    "reference.fa",
    "-o",
    "output.cram",
    "input.bam",
    catch_stdout=False,
)
pysam.samtools.index(
    "-@",
    "4",
    "output.cram",
    catch_stdout=False,
)
```

Using `-o` plus `catch_stdout=False` avoids capturing binary CRAM output in
Python memory.

Validate:

```python
pysam.samtools.quickcheck("-v", "output.cram")

with pysam.AlignmentFile(
    "output.cram",
    "rc",
    reference_filename="reference.fa",
) as cram:
    first = next(cram.fetch(until_eof=True), None)
```

`quickcheck` is structural, not a full decode or biological validation.
Compare record counts and selected records to the source.

## CRAM Failure Diagnosis

When CRAM open/fetch fails, check in this order:

1. Confirm the FASTA assembly and contig names.
2. Confirm `.fai` exists and lengths match the alignment header.
3. Inspect `@SQ` `M5` and `UR` fields.
4. Pass `reference_filename=` explicitly.
5. Confirm CRAI matches the current CRAM.
6. Try a sequential read to separate index from reference problems.
7. Capture HTSlib/samtools error messages.

Do not disable validation or substitute a similarly named assembly.

## Remote HTSlib I/O

Depending on how the wheel/build was configured, HTSlib can read HTTP(S) and
other plugin-backed URLs. Random access also needs a reachable index and range
request support.

```python
with pysam.AlignmentFile(
    "https://example.org/data/sample.bam",
    "rb",
    index_filename="https://example.org/data/sample.bam.bai",
) as bam:
    for read in bam.fetch("chr1", 1_000, 2_000):
        ...
```

Remote support is build- and protocol-dependent. Before large analysis:

- issue one small known region query
- verify the exact index URL
- check content versioning/immutability
- confirm retries, timeout behavior, and credentials outside logs
- estimate request count from the access pattern

Many tiny random queries can be slower and more expensive than downloading or
staging a file once. Never put bearer tokens or secrets directly in committed
URLs.

## Threads

`threads=` on `AlignmentFile`, `VariantFile`, and `TabixFile` controls HTSlib
compression/decompression threads:

```python
with pysam.AlignmentFile("sample.bam", "rb", threads=4) as bam:
    ...
```

It does **not** parallelize Python filtering, pileup interpretation, or
statistical analysis. More threads can increase memory and I/O contention, and
returns diminish when storage or network is the bottleneck.

`threads > 1` cannot be combined with `ignore_truncation=True`.

## Python Thread Safety

Pysam releases the GIL for many I/O-intensive operations, but not every code
path has been comprehensively validated for thread safety.

Avoid sharing one active file handle across threads. Prefer:

- one independently opened handle per worker, or
- independent `fetch(..., multiple_iterators=True)` iterators when the
  overhead is acceptable

Variant iterators use `fetch(..., reopen=True)`; Tabix and alignment iterators
use `multiple_iterators=True`.

Reopening a remote file for every small iterator can be especially expensive.

## Multiprocessing

Partition work by independent contigs or nonoverlapping windows, but reopen
files inside each process:

```python
def process_region(bam_path: str, contig: str, start: int, stop: int):
    with pysam.AlignmentFile(bam_path, "rb", threads=1) as bam:
        return bam.count(contig, start, stop, read_callback="all")
```

Do not pass live pysam handles or proxy records between processes. Balance
process count and HTSlib `threads`; multiplying both can oversubscribe CPUs.

When partitioning pileup or coverage, include any necessary boundary context
and trim results back to the target windows. Reads overlap partition
boundaries.

## Access-Pattern Guidance

### Prefer sequential scans when

- every record is needed
- the file is unindexed
- remote request overhead dominates
- aggregate QC is being calculated

Use `fetch(until_eof=True)` for alignments and normal iteration for variants.

### Prefer indexed queries when

- only a small fraction of the genome is needed
- regions are grouped and ordered
- an index is available and current

Sort region requests by contig/start to improve locality. Merge heavily
overlapping windows when duplicate processing is not desired.

### Prefer native bulk commands when

- sorting, merging, indexing, or format conversion
- normalizing VCF
- producing standard command outputs

The wrapped samtools/bcftools implementations are usually faster and more
tested than equivalent Python loops.

## Pileup and Coverage Performance

- `count()` is appropriate for overlap-record counts.
- `count_coverage()` efficiently returns dense A/C/G/T arrays for an interval.
- `pileup()` is needed for base/read-level state but has more Python overhead.
- The default pileup depth cap is 8000; changing it can materially affect
  memory and results.
- Avoid one pileup call per nearby variant; group variants into windows or
  traverse columns once.
- Do not materialize all reads or pileup proxies into a list.

## File-Handle and Proxy Lifetimes

Pysam exposes proxy objects backed by HTSlib memory. Keep the owning file and
iterator alive while using:

- `PileupColumn`
- `PileupRead`
- `persist=False` FASTX records

Copy primitive values if data must outlive iteration.

## Reproducibility Checklist

- pin pysam (`pysam==0.24.0`)
- record `pysam.__version__` and `pysam.__samtools_version__`
- record reference FASTA checksum and assembly
- record CRAM output version
- record command arguments and filtering thresholds
- write outputs and indexes atomically or to new paths
- validate representative regions after writing
- avoid hidden network reference dependencies
