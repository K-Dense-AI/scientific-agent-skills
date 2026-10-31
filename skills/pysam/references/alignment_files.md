# Alignment Files: SAM, BAM, and CRAM

This reference targets pysam 0.24.1. All numeric coordinates shown here are
0-based, half-open.

## Open Modes and Handles

| Format | Read | Write |
|---|---:|---:|
| SAM text | `r` | `w` |
| BAM | `rb` | `wb` |
| CRAM | `rc` | `wc` |

```python
import pysam

with pysam.AlignmentFile("input.bam", "rb", threads=4) as alignments:
    print(alignments.references)
```

For CRAM, supply the exact reference where possible:

```python
with pysam.AlignmentFile(
    "input.cram",
    "rc",
    reference_filename="GRCh38.fa",
    threads=4,
) as alignments:
    ...
```

`AlignmentFile` can use a path or a real file object that exposes `fileno()`.
In-memory objects such as `io.BytesIO` are not supported by HTSlib. Use `"-"`
for stdin/stdout. When an existing file object is accepted,
`duplicate_filehandle=True` (the default) prevents pysam from closing the
caller's descriptor.

Useful constructor options:

- `index_filename=`: nonstandard, remote, or separately named index
- `require_index=True`: fail early if random access is required
- `reference_filename=`: CRAM reference FASTA
- `threads=`: compression/decompression threads
- `format_options=["key=value"]`: HTSlib format options
- `ignore_truncation=True`: downgrade a missing BGZF EOF marker to a warning;
  do not combine with `threads > 1`

## Headers and Index State

`AlignmentFile.header` is an `AlignmentHeader`, not a plain dictionary.

```python
with pysam.AlignmentFile("input.bam", "rb") as bam:
    header_dict = bam.header.to_dict()
    header_text = str(bam.header)
    contigs = dict(zip(bam.references, bam.lengths))
    has_index = bam.has_index()
```

Use `check_index()` when a missing index should be an error. It raises for SAM,
closed files, or unusable indexes. `get_index_statistics()` exposes per-contig
mapped/unmapped counts recorded in an available index; these are index
statistics, not a fresh scan of every record. CRAI does not store these counts:
CRAM `mapped`, `unmapped`, `nocoordinate`, and index-statistic values return zero
and must not be interpreted as an empty CRAM. Use a sequential scan for counts.

## Iteration Choices

### Indexed region query

```python
with pysam.AlignmentFile("input.bam", "rb") as bam:
    for read in bam.fetch("chr1", 1_000, 2_000):
        ...
```

- Requires BAI/CSI for BAM or CRAI for CRAM.
- Returns reads overlapping the interval, including reads that start before it
  or end after it.
- Records are returned in coordinate/index order.
- BAM/CRAM `fetch()` with no region requires an index and visits placed records
  by reference. Placed unmapped records can appear in both this and region
  queries; test `read.is_unmapped`. Unplaced reads need sequential scanning.
- SAM `fetch()` without a region is sequential; SAM region access is unsupported
  by `AlignmentFile` even though standalone samtools can index BGZF SAM.

### Sequential scan

```python
with pysam.AlignmentFile("input.bam", "rb") as bam:
    for read in bam.fetch(until_eof=True):
        ...
```

- Does not require an index.
- Starts at the current file position.
- Preserves file order.
- Includes unplaced unmapped records.

`fetch("*")` requests only unplaced unmapped records at the end of a
coordinate-sorted alignment file.

### Multiple active iterators

`multiple_iterators` belongs to `fetch()`, not the `AlignmentFile`
constructor:

```python
with pysam.AlignmentFile("input.bam", "rb") as bam:
    chr1_reads = bam.fetch("chr1", multiple_iterators=True)
    chr2_reads = bam.fetch("chr2", multiple_iterators=True)
```

Each such iterator reopens the file and has overhead. Prefer one ordered pass
when possible.

## `AlignedSegment` Essentials

### Identity and sequence

- `query_name`
- `query_sequence`
- `query_qualities`: numeric Phred scores, or `None`
- `query_length`
- `query_alignment_sequence`: query bases participating in the alignment
- `query_alignment_qualities`
- `get_forward_sequence()` / `get_forward_qualities()`: original sequencer
  orientation of the retained sequence (hard-clipped bases cannot be recovered)

Assigning `query_sequence` invalidates `query_qualities`. Save and reassign
qualities after changing sequence.

### Reference placement

- `reference_name`
- `reference_id`
- `reference_start`: 0-based inclusive
- `reference_end`: 0-based exclusive; derived from CIGAR
- `mapping_quality`
- `next_reference_name`, `next_reference_start`
- `template_length`

Many placement-derived properties are `None` or sentinel values for unmapped
or CIGAR-less records. Check `is_unmapped` before using them.

### Flags

Common boolean properties:

- pairing: `is_paired`, `is_proper_pair`, `is_read1`, `is_read2`
- orientation: `is_reverse`, `mate_is_reverse`
- mapping: `is_unmapped`, `mate_is_unmapped`
- status: `is_secondary`, `is_supplementary`, `is_qcfail`, `is_duplicate`

For a typical primary mapped-read filter:

```python
def keep_primary(read: pysam.AlignedSegment) -> bool:
    return (
        not read.is_unmapped
        and not read.is_secondary
        and not read.is_supplementary
        and not read.is_qcfail
        and not read.is_duplicate
        and read.mapping_quality >= 20
    )
```

State whether supplementary alignments and duplicates are intentionally
excluded; there is no universal filter for every analysis. MAPQ 255 denotes
unavailable quality, and the numeric threshold above keeps it. Exclude it
explicitly when the assay requires measured MAPQ. Proper-pair flags describe
the aligner's criteria, not independent proof of a valid biological fragment.

## CIGAR Operations and Alignment Geometry

`cigartuples` stores `(operation, length)`, the reverse of textual SAM CIGAR
notation.

| Enum | Code | SAM op | Consumes query | Consumes reference |
|---|---:|---:|---:|---:|
| `CIGAR_OPS.CMATCH` | 0 | `M` | yes | yes |
| `CIGAR_OPS.CINS` | 1 | `I` | yes | no |
| `CIGAR_OPS.CDEL` | 2 | `D` | no | yes |
| `CIGAR_OPS.CREF_SKIP` | 3 | `N` | no | yes |
| `CIGAR_OPS.CSOFT_CLIP` | 4 | `S` | yes | no |
| `CIGAR_OPS.CHARD_CLIP` | 5 | `H` | no | no |
| `CIGAR_OPS.CPAD` | 6 | `P` | no | no |
| `CIGAR_OPS.CEQUAL` | 7 | `=` | yes | yes |
| `CIGAR_OPS.CDIFF` | 8 | `X` | yes | yes |
| `CIGAR_OPS.CBACK` | 9 | `B` | legacy | legacy |

Prefer enum members in new code. Top-level aliases such as `pysam.CMATCH`
remain in 0.24 for compatibility but are expected to be removed in a future
release.

Useful geometry methods:

```python
blocks = read.get_blocks()  # M/=/X blocks; D/N gaps, I can split adjacent blocks
pairs = read.get_aligned_pairs(matches_only=False, with_cigar=True)
reference_positions = read.get_reference_positions(full_length=True)
```

`get_aligned_pairs(with_seq=True)` needs an MD tag and returns reference bases
derived from that tag. It does not consult a separately opened FASTA.

## Optional Tags and Modified Bases

```python
if read.has_tag("NM"):
    edit_distance = read.get_tag("NM")

read.set_tag("XX", 7, value_type="i")
all_tags = read.get_tags(with_value_type=True)
```

Use standard tags according to the SAM tags specification. Avoid changing
alignment-derived tags such as NM/MD without recomputing them.

For base modifications encoded by MM/ML:

```python
for (canonical_base, strand, modification), calls in (
    read.modified_bases or {}
).items():
    for query_position, quality in calls:
        probability_lower_bound = None if quality < 0 else quality / 256.0
```

The key is `(canonical base, strand, modification)`, where strand is `0`
forward or `1` reverse. pysam 0.24 removed the earlier five-modification-type
limit and fixed crashes on degenerate empty MM calls. ML values are quantized:
`quality / 256` is a lower bound, not an exact posterior. These query positions
refer to stored SEQ; use `modified_bases_forward` with `get_forward_sequence()`
when the original orientation is required.

## Counting and Coverage

### Record count

```python
with pysam.AlignmentFile("input.bam", "rb") as bam:
    raw_overlap_count = bam.count("chr1", 1_000, 2_000)
    filtered_count = bam.count(
        "chr1",
        1_000,
        2_000,
        read_callback="all",
    )
```

`count()` defaults to `read_callback="nofilter"`. `"all"` excludes reads with
unmapped, secondary, QC-fail, or duplicate flags. It does not accept a
`quality=` argument. Use a callback for custom record filtering:

```python
count = bam.count(
    "chr1",
    1_000,
    2_000,
    read_callback=lambda read: keep_primary(read),
)
```

### A/C/G/T base coverage

```python
a, c, g, t = bam.count_coverage(
    "chr1",
    1_000,
    2_000,
    quality_threshold=20,
    read_callback="all",
)
depth = [sum(values) for values in zip(a, c, g, t)]
```

For `0 <= start < stop <= contig_length`, the result has `stop - start`
positions, including zero coverage. Validate these bounds: an end past the
contig is clipped. In 0.24.1, the array allocation does not derive its span
from `region=` or the `end=` alias; use numeric `contig`, `start`, and `stop`
for this method. Only A/C/G/T bases count. Deletions, reference skips, and
ambiguous query bases do not contribute. Overlapping mates count separately;
this method does not apply pileup BAQ or pair-overlap adjustments.

## Pileup Semantics

```python
with pysam.FastaFile("reference.fa") as fasta, pysam.AlignmentFile(
    "input.bam", "rb"
) as bam:
    iterator = bam.pileup(
        "chr1",
        1_000,
        2_000,
        truncate=True,
        stepper="samtools",
        fastafile=fasta,
        min_mapping_quality=20,
        min_base_quality=20,
        max_depth=100_000,
        ignore_overlaps=True,
        ignore_orphans=True,
    )
    for column in iterator:
        for pileup_read in column.pileups:
            if pileup_read.is_del or pileup_read.is_refskip:
                continue
            query_position = pileup_read.query_position
            base = pileup_read.alignment.query_sequence[query_position]
```

Key defaults and behaviors:

- Without `truncate=True`, columns outside the requested interval can appear
  when overlapping reads extend beyond the interval.
- `stepper="all"` filters unmapped, secondary, QC-fail, and duplicate reads.
- `stepper="nofilter"` disables the read callback's flag/MAPQ filtering;
  base-quality thresholds, the depth cap, and overlap handling still apply.
- `stepper="samtools"` applies samtools-style processing; provide `fastafile`
  for full BAQ/reference behavior.
- Default `min_base_quality` is 13.
- Default `max_depth` is 8000.
- Paired overlap detection and orphan filtering are enabled by default.
- `nsegments` precedes the base-quality filter. Despite its name,
  `get_num_aligned()` also counts deletion/reference-skip entries that pass the
  quality check in 0.24.1. For observed base depth, count `column.pileups` entries
  with `not is_del`, `not is_refskip`, and a non-`None` `query_position`.
- Overlap handling adjusts base qualities; with `min_base_quality=0`, a
  zero-quality mate can reappear. It does not universally remove one record.

Consume each `PileupColumn` before advancing the iterator: its backing buffer
changes on advance, not only on iterator destruction. Copy primitive values
needed later. For concurrent CRAM pileups open separate file handles;
`multiple_iterators=True` is not implemented for CRAM pileup.

For SNP support, inspect base and quality. For insertions/deletions, use
`PileupRead.indel`, deletion/refskip state, CIGAR, and normalized alleles.
Single-base counting is not an indel caller.

## Writing Alignments

### Preserve an input header

```python
with pysam.AlignmentFile("input.bam", "rb") as source, pysam.AlignmentFile(
    "filtered.bam", "wb", template=source, threads=4
) as destination:
    for read in source.fetch(until_eof=True):
        if keep_primary(read):
            destination.write(read)
```

The output retains input order and `@SQ`, `@RG`, `@PG`, and optional tags.
Keep the reference order intact: record reference IDs are numeric. Check each
`RG` tag against a defined `@RG ID` and its intended sample before combining
files. Per-record filters can drop one mate; they do not repair flags, mate
coordinates, TLEN, or fetch a mate outside a requested region. Only index
coordinate-sorted output with unmapped records in valid positions.

### Construct a new record

```python
header = pysam.AlignmentHeader.from_dict(
    {
        "HD": {"VN": "1.6", "SO": "coordinate"},
        "SQ": [{"SN": "chr1", "LN": 248_956_422}],
    }
)

with pysam.AlignmentFile("new.bam", "wb", header=header) as output:
    read = pysam.AlignedSegment(output.header)
    read.query_name = "read001"
    read.query_sequence = "ACGTACGTAA"
    read.flag = 0
    read.reference_id = output.get_tid("chr1")
    read.reference_start = 100
    read.mapping_quality = 60
    read.cigartuples = [(pysam.CIGAR_OPS.CMATCH, 10)]
    read.query_qualities = pysam.qualitystring_to_array("IIIIIIIIII")
    output.write(read)
```

Construct records against the destination header so numeric reference IDs map
correctly. Sequence length, qualities, and query-consuming CIGAR operations
must agree.

## Validation

For BAM/CRAM:

```python
pysam.samtools.quickcheck("-v", "filtered.bam")
pysam.samtools.index("filtered.bam", catch_stdout=False)
```

`quickcheck` checks basic headers and EOF markers, not biological correctness.
Reopen the file, verify header/reference compatibility, and inspect expected
regions. Read `cram_and_performance.md` for CRAM-specific validation.
