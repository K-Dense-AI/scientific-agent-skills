# Correct Pysam Workflow Patterns

These patterns target pysam 0.24.0 and make filtering and coordinate semantics
explicit. Adapt thresholds to the assay rather than treating them as universal
defaults.

## Preflight an Analysis

Before combining files, verify:

1. Reference assembly and contig naming agree (`chr1` versus `1`).
2. Numeric coordinates use 0-based, half-open intervals.
3. Alignment and variant inputs are sorted as expected.
4. Random-access inputs have valid indexes.
5. CRAM has the exact reference FASTA available.
6. Read-group/sample metadata identifies the intended samples.
7. Duplicate, secondary, supplementary, QC-fail, and quality policies are
   stated.

Use the bundled inspectors:

```bash
python scripts/inspect_hts.py sample.bam
python scripts/inspect_hts.py cohort.vcf.gz
python scripts/inspect_hts.py reference.fa
```

## Streaming Alignment QC

The bundled script scans in file order and does not require an index:

```bash
python scripts/alignment_qc.py sample.bam --output sample.qc.json
python scripts/alignment_qc.py sample.cram \
  --reference reference.fa \
  --max-records 100000
```

The report counts alignment records, not unique templates or fragments.
Secondary and supplementary records are reported separately. Use
`--max-records` for a sampling pass; omit it for a complete scan.

For index-level counts without reading every record:

```python
import pysam

with pysam.AlignmentFile("sample.bam", "rb", require_index=True) as bam:
    for stats in bam.get_index_statistics():
        print(stats.contig, stats.mapped, stats.unmapped, stats.total)
```

Index statistics are fast but cannot replace custom record-level QC.

## Zero-Aware Coverage

`pileup()` omits positions with no columns. Use `count_coverage()` when zeros
must be represented:

```python
import pysam


def base_depth(
    bam: pysam.AlignmentFile,
    contig: str,
    start: int,
    stop: int,
    *,
    min_base_quality: int = 20,
) -> list[int]:
    a, c, g, t = bam.count_coverage(
        contig,
        start,
        stop,
        quality_threshold=min_base_quality,
        read_callback="all",
    )
    return [sum(counts) for counts in zip(a, c, g, t)]


with pysam.AlignmentFile("sample.bam", "rb") as bam:
    depth = base_depth(bam, "chr1", 1_000, 2_000)
```

`read_callback="all"` excludes unmapped, secondary, QC-fail, and duplicate
records, but not supplementary records. Use a custom callback when
supplementary or low-MAPQ reads must also be excluded:

```python
def usable_read(read: pysam.AlignedSegment) -> bool:
    return (
        not read.is_unmapped
        and not read.is_secondary
        and not read.is_supplementary
        and not read.is_qcfail
        and not read.is_duplicate
        and read.mapping_quality >= 20
    )


a, c, g, t = bam.count_coverage(
    "chr1",
    1_000,
    2_000,
    quality_threshold=20,
    read_callback=usable_read,
)
```

Only A/C/G/T query bases contribute.

### Convert low-depth bases into intervals

```python
def below_threshold_intervals(
    depths: list[int],
    start: int,
    threshold: int,
):
    interval_start = None

    for offset, value in enumerate(depths):
        position = start + offset
        if value < threshold and interval_start is None:
            interval_start = position
        elif value >= threshold and interval_start is not None:
            yield interval_start, position
            interval_start = None

    if interval_start is not None:
        yield interval_start, start + len(depths)
```

The yielded intervals remain 0-based, half-open and correctly include regions
with no aligned columns.

## Exact Pileup at a Position

Use explicit pileup options and retain the iterator:

```python
def aligned_depth_at(
    bam: pysam.AlignmentFile,
    fasta: pysam.FastaFile,
    contig: str,
    position: int,
) -> int:
    iterator = bam.pileup(
        contig,
        position,
        position + 1,
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
        if column.reference_pos == position:
            return column.get_num_aligned()
    return 0
```

This definition is not identical to VCF `INFO/DP` from a caller. Name custom
annotations so their provenance and filters remain clear.

## SNP Base Support

This helper is deliberately limited to single-nucleotide REF/ALT alleles:

```python
from collections import Counter


def snp_base_counts(
    bam: pysam.AlignmentFile,
    fasta: pysam.FastaFile,
    record: pysam.VariantRecord,
) -> Counter[str]:
    if (
        len(record.ref) != 1
        or not record.alts
        or any(len(alt) != 1 for alt in record.alts)
    ):
        raise ValueError("snp_base_counts only supports simple SNP records")

    counts: Counter[str] = Counter()
    iterator = bam.pileup(
        record.contig,
        record.start,
        record.start + 1,
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
            if query_position is None:
                continue
            base = pileup_read.alignment.query_sequence[query_position]
            counts[base.upper()] += 1
    return counts
```

For indels, inspect `PileupRead.indel`, CIGAR, and normalized alleles or use a
dedicated variant caller. This SNP method must not be generalized to symbolic
or breakend alleles.

## Annotate a VCF with BAM-Derived Depth

Copy the header, declare a new field, translate copied records, and use
`record.start` directly:

```python
import pysam


def annotate_depth(
    input_vcf: str,
    input_bam: str,
    reference_fasta: str,
    output_vcf: str,
) -> None:
    with pysam.FastaFile(reference_fasta) as fasta, pysam.AlignmentFile(
        input_bam,
        "rb",
        reference_filename=reference_fasta,
    ) as bam, pysam.VariantFile(input_vcf) as source:
        header = source.header.copy()
        if "BAM_BASE_DP" in header.info:
            raise ValueError("BAM_BASE_DP already exists in input header")
        header.info.add(
            "BAM_BASE_DP",
            number=1,
            type="Integer",
            description=(
                "Aligned base depth at POS; MAPQ>=20, baseQ>=20, "
                "samtools pileup filters, paired overlaps collapsed"
            ),
        )

        with pysam.VariantFile(output_vcf, "w", header=header) as output:
            for source_record in source:
                record = source_record.copy()
                record.translate(header)
                record.info["BAM_BASE_DP"] = aligned_depth_at(
                    bam,
                    fasta,
                    record.contig,
                    record.start,
                )
                output.write(record)
```

For CRAM input, `reference_filename` is essential. For a large unindexed VCF,
this pattern can issue many BAM seeks; process by contig or sorted windows to
improve locality.

## Validate VCF REF Alleles Against FASTA

```python
def reference_matches(
    record: pysam.VariantRecord,
    fasta: pysam.FastaFile,
) -> bool:
    observed = fasta.fetch(
        record.contig,
        record.start,
        record.start + len(record.ref),
    )
    return observed.upper() == record.ref.upper()


with pysam.FastaFile("reference.fa") as fasta, pysam.VariantFile(
    "variants.vcf.gz"
) as variants:
    mismatches = [
        (record.contig, record.pos, record.ref)
        for record in variants
        if not reference_matches(record, fasta)
    ]
```

Do not "fix" mismatches automatically. Investigate assembly version, contig
aliases, left normalization, and strand/representation errors.

## Filter an Alignment File

Use the bundled script for common primary-read filtering:

```bash
python scripts/alignment_qc.py input.bam --max-records 10000
python scripts/filter_alignments.py input.bam filtered.bam \
  --min-mapq 20 --exclude-duplicates --exclude-supplementary --index
```

If implementing custom filtering, preserve the source header and stream
records:

```python
with pysam.AlignmentFile("input.bam", "rb") as source, pysam.AlignmentFile(
    "filtered.bam", "wb", template=source
) as output:
    for read in source.fetch(until_eof=True):
        if usable_read(read):
            output.write(read)
```

Filtering preserves input order; it does not sort. Index only coordinate-sorted
output. If the header's sort-order declaration is wrong, fix the workflow
rather than trusting it.

## Extract Strand-Aware BED Sequences

```python
IUPAC_COMPLEMENT = str.maketrans(
    "ACGTRYMKBDHVNacgtrymkbdhvn",
    "TGCAYRKMVHDBNtgcayrkmvhdbn",
)


with pysam.TabixFile(
    "genes.bed.gz", parser=pysam.asBed()
) as genes, pysam.FastaFile("reference.fa") as fasta, open(
    "genes.fa", "x", encoding="utf-8"
) as output:
    for gene in genes.fetch():
        sequence = fasta.fetch(gene.contig, gene.start, gene.end)
        if gene.strand == "-":
            sequence = sequence.translate(IUPAC_COMPLEMENT)[::-1]
        output.write(f">{gene.name}\n{sequence}\n")
```

BED parser coordinates are already 0-based. Sanitize or encode record names if
they will be consumed by strict downstream FASTA parsers.

## Count RNA Splice Junctions

`find_introns()` counts `N` CIGAR operations:

```python
with pysam.AlignmentFile("rna.bam", "rb") as bam:
    primary_reads = (
        read
        for read in bam.fetch("chr1")
        if not read.is_secondary
        and not read.is_supplementary
        and not read.is_duplicate
        and read.mapping_quality >= 20
    )
    junction_counts = bam.find_introns(primary_reads)
```

Keys are `(start, stop)` 0-based splice intervals. Filter strand and library
orientation according to the assay.

## Bulk Operations via Wrapped Tools

For sort/index and normalization, mature command implementations are usually
preferable to Python record loops:

```python
import pysam.samtools
import pysam.bcftools

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

pysam.bcftools.norm(
    "-f", "reference.fa",
    "-m", "-any",
    "-Oz",
    "-o", "normalized.vcf.gz",
    "input.vcf.gz",
    catch_stdout=False,
)
pysam.bcftools.index(
    "--csi",
    "normalized.vcf.gz",
    catch_stdout=False,
)
```

Pass each argument as its own string. Do not split or evaluate an untrusted
shell command. Use `catch_stdout=False` when `-o` writes large or binary data.

## Do Not Hand-Roll Complex VCF Merges

Combining records by `(contig, pos, ref, alts)` is insufficient because inputs
can differ in:

- allele normalization and multiallelic decomposition
- contig order and metadata
- INFO/FORMAT Number and Type definitions
- FILTER definitions
- sample names and ploidy
- duplicate positions and phasing

Normalize and validate inputs, then use `bcftools merge` for samples or
`bcftools concat` for disjoint genomic partitions as appropriate.

## Output Validation

Alignment output:

```python
pysam.samtools.quickcheck("-v", "filtered.bam")
```

Variant output:

```python
with pysam.VariantFile("annotated.vcf.gz") as variants:
    assert "BAM_BASE_DP" in variants.header.info
```

Then index final sorted output and fetch known intervals at contig starts,
interval boundaries, and high-coordinate regions. Format validity does not
prove biological validity; compare counts and selected records to an
independent tool when results matter.
