# Coordinates and Indexing

Coordinate mistakes and stale indexes are the most common causes of plausible
but wrong genomic results. This reference targets pysam 0.24.0.

## The Pysam Rule

For Python API numeric arguments and properties, pysam uses **0-based,
half-open** intervals:

```text
[start, stop)
```

The first base is `0`; `start` is included and `stop` is excluded. Interval
length is `stop - start`.

The main exception is a textual samtools-style region string, which is
**1-based, inclusive**:

```text
chr1:100-199
```

These refer to the same 100 bases:

```python
file.fetch("chr1", 99, 199)
file.fetch(region="chr1:100-199")
```

This rule applies to:

- `AlignmentFile.fetch()`, `count()`, `count_coverage()`, and `pileup()`
- `VariantFile.fetch()`
- `FastaFile.fetch()`
- `TabixFile.fetch()`

Do not treat numeric `VariantFile.fetch()` arguments as VCF text coordinates.

## Format Conversion Table

| Source representation | Source convention | Convert to pysam numeric |
|---|---|---|
| BED `chromStart`, `chromEnd` | 0-based, half-open | use unchanged |
| VCF `POS` and REF | 1-based position | `start = POS - 1`; `stop = start + len(REF)` unless record semantics provide another end |
| `VariantRecord.start`, `.stop` | 0-based, half-open | use unchanged |
| GFF/GTF start/end columns | 1-based, inclusive | `start = start_text - 1`; `stop = end_text` |
| SAM `POS` | 1-based leftmost base | use `AlignedSegment.reference_start` |
| samtools region string | 1-based, inclusive | pass as `region=...`, or convert both endpoints |

For VCF structural variants, symbolic alleles, breakends, and records with
`INFO/END`, use `VariantRecord.start` and `VariantRecord.stop` rather than
reconstructing the interval from `len(REF)`.

## Single Positions

A 1-based position `p` becomes the one-base Python interval:

```python
start = p - 1
stop = p
```

For a VCF record:

```python
assert record.start == record.pos - 1
base = fasta.fetch(record.contig, record.start, record.start + 1)
```

## Overlap Versus Containment

Region fetches are overlap queries. An alignment or variant can begin before
the requested interval and still overlap it.

To require complete containment:

```python
def fully_contained(read, start: int, stop: int) -> bool:
    return (
        read.reference_start is not None
        and read.reference_end is not None
        and read.reference_start >= start
        and read.reference_end <= stop
    )
```

For point-based logic, define exactly what "overlap" means for deletions,
reference skips, symbolic alleles, and breakends.

`pileup()` has an additional trap: without `truncate=True`, it can emit columns
outside the requested interval because reads overlap the interval.

## Parser Coordinates

Pysam parser objects normalize coordinates:

- `asBed().start` / `.end`: 0-based, half-open
- `asGTF().start` / `.end`: exposed in Python coordinate convention
- `asVCF().pos`: parser-specific lightweight field; use `VariantFile` for full
  VCF record semantics

When creating a custom tabix index:

- `seq_col`, `start_col`, and `end_col` are 0-based **column indices**
- file coordinates default to 1-based unless `zerobased=True`
- later `TabixFile.fetch()` numeric query coordinates are still 0-based

These are three distinct concepts: Python column index, coordinate encoding in
the stored table, and coordinate encoding in the query.

## Contig Identity

Coordinate conversion does not solve contig mismatches. Check:

- `chr1` versus `1`
- mitochondrial names (`chrM`, `MT`, `M`)
- alternate loci and decoys
- assembly version (for example GRCh37 versus GRCh38)
- contig order and lengths

```python
alignment_contigs = dict(zip(bam.references, bam.lengths))
fasta_contigs = dict(zip(fasta.references, fasta.lengths))

shared = alignment_contigs.keys() & fasta_contigs.keys()
length_mismatches = {
    name: (alignment_contigs[name], fasta_contigs[name])
    for name in shared
    if alignment_contigs[name] != fasta_contigs[name]
}
```

Do not silently strip or add `chr` across arbitrary assemblies. Use an explicit
reviewed mapping.

## Index Matrix

| Data | Random-access index | Sort requirement |
|---|---|---|
| BAM | `.bai` or `.csi` | coordinate order |
| CRAM | `.crai` | coordinate order |
| BGZF VCF | `.tbi` or `.csi` | contig/position order |
| BCF | `.csi` | contig/position order |
| FASTA | `.fai`; BGZF FASTA also `.gzi` | FASTA layout, not coordinate sort |
| BED/GFF/GTF/custom BGZF table | `.tbi` or `.csi` | contig/start order |
| SAM / ordinary VCF / FASTQ | no random-access index through these APIs | sequential only |

An index is a view of a specific file. If the data file changes, rebuild the
index. A stale index may fail loudly or return wrong/incomplete regions.

## BAI/TBI Versus CSI

Legacy BAI and standard TBI indexes have a maximum coordinate near `2^29`
(512 Mi bases). This is insufficient for some plant, animal, and synthetic
references. CSI is parameterized and supports larger coordinates.

Create a BAM CSI:

```python
import pysam

pysam.index("-c", "large-reference.bam", catch_stdout=False)
```

Create a tabix CSI:

```python
pysam.tabix_index(
    "large-reference.bed.gz",
    preset="bed",
    csi=True,
    min_shift=14,
)
```

Create a VCF/BCF CSI:

```python
import pysam.bcftools

pysam.bcftools.index(
    "--csi",
    "variants.vcf.gz",
    catch_stdout=False,
)
```

Prefer CSI when reference sizes are unknown or potentially large. Confirm
downstream tools support it.

## Sort Before Indexing

Indexing does not sort records.

BAM:

```python
import pysam.samtools

pysam.samtools.sort(
    "-@", "4",
    "-o", "sorted.bam",
    "input.bam",
    catch_stdout=False,
)
pysam.samtools.index(
    "-@", "4",
    "sorted.bam",
    catch_stdout=False,
)
```

VCF:

```python
import pysam.bcftools

pysam.bcftools.sort(
    "-Oz",
    "-o", "sorted.vcf.gz",
    "input.vcf",
    catch_stdout=False,
)
pysam.bcftools.index(
    "--csi",
    "sorted.vcf.gz",
    catch_stdout=False,
)
```

Tabix tables must be sorted before `tabix_index()`. The Python function does
not verify sort order.

## Safe Tabix Creation

Prefer separate compression and indexing:

```python
pysam.tabix_compress("regions.bed", "regions.bed.gz")
pysam.tabix_index("regions.bed.gz", preset="bed")
```

Calling `tabix_index("regions.bed")` can automatically create
`regions.bed.gz` and remove the original. Use `keep_original=True` if relying
on that one-step path.

Do not pass `force=True` by default. Existing output should trigger review,
not silent replacement.

## Nonstandard and Remote Index Locations

Pass an explicit index:

```python
with pysam.AlignmentFile(
    "sample.bam",
    "rb",
    index_filename="indexes/sample.csi",
) as bam:
    ...

with pysam.VariantFile(
    "cohort.vcf.gz",
    index_filename="indexes/cohort.vcf.gz.csi",
) as variants:
    ...
```

Remote random access additionally depends on:

- an HTSlib build with the relevant network/plugin support
- a reachable index
- server range requests
- stable data and index URLs

Pass `index_filename` explicitly when automatic URL derivation is unreliable.
Read `cram_and_performance.md` before remote or CRAM access.

## Index Checks

Alignment:

```python
with pysam.AlignmentFile("sample.bam", "rb") as bam:
    if not bam.has_index():
        raise ValueError("random access requires a BAM/CRAM index")
    bam.check_index()
```

Variant and tabix constructors open a discovered index automatically; a region
fetch fails when none is available. Reopen output and test known regions rather
than checking only that an index filename exists.

## Boundary Tests

For important pipelines, test:

- first base of a contig
- exact interval start and stop
- a record spanning the query boundary
- a zero-length or invalid interval
- contig end
- a high coordinate beyond 512 Mi bases when CSI is expected
- missing and aliased contigs
- region string and numeric equivalents

One useful invariant:

```python
numeric = list(file.fetch(contig, start, stop))
region = f"{contig}:{start + 1}-{stop}"
textual = list(file.fetch(region=region))
```

For the same indexed file and valid nonempty interval, these queries should
select equivalent records.
