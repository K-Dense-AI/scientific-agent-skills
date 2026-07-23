# FASTA, FASTQ, and Tabix-Indexed Files

This reference targets pysam 0.24.0.

## Indexed FASTA

`FastaFile` provides random access through a faidx index.

```python
import pysam

pysam.faidx("reference.fa")

with pysam.FastaFile("reference.fa") as fasta:
    print(fasta.references)
    print(fasta.lengths)
    print(fasta.get_reference_length("chr1"))
```

An uncompressed FASTA needs `<name>.fai`. A BGZF-compressed FASTA also needs a
`.gzi` compressed-offset index. Ordinary gzip is not suitable for indexed
random access.

The constructor can use nonstandard index paths:

```python
fasta = pysam.FastaFile(
    "reference.fa.gz",
    filepath_index="indexes/reference.fa.gz.fai",
    filepath_index_compressed="indexes/reference.fa.gz.gzi",
)
```

### Numeric and string coordinates

```python
with pysam.FastaFile("reference.fa") as fasta:
    # Numeric: 0-based, half-open
    sequence = fasta.fetch("chr1", 999, 1_099)

    # Region string: 1-based, inclusive
    same_sequence = fasta.fetch(region="chr1:1000-1099")
```

If start or end is omitted, pysam uses the sequence boundary. Invalid regions
raise `ValueError` or `IndexError`; do not silently clip unless that is the
documented workflow.

### Fetch variant context

```python
def variant_context(
    fasta: pysam.FastaFile,
    contig: str,
    pos_1based: int,
    ref: str,
    flank: int = 20,
) -> tuple[str, bool]:
    start = pos_1based - 1
    context_start = max(0, start - flank)
    context_stop = min(
        fasta.get_reference_length(contig),
        start + len(ref) + flank,
    )
    context = fasta.fetch(contig, context_start, context_stop)
    observed_ref = fasta.fetch(contig, start, start + len(ref))
    return context, observed_ref.upper() == ref.upper()
```

Validate the entire REF allele, not only its first base. A mismatch often
means the VCF and FASTA use different assemblies, contig aliases, or
normalization.

### Strand-aware extraction

Coordinates do not encode strand. Reverse-complement after fetching:

```python
IUPAC_COMPLEMENT = str.maketrans(
    "ACGTRYMKBDHVNacgtrymkbdhvn",
    "TGCAYRKMVHDBNtgcayrkmvhdbn",
)


def reverse_complement(sequence: str) -> str:
    return sequence.translate(IUPAC_COMPLEMENT)[::-1]


sequence = fasta.fetch("chr1", start, stop)
if strand == "-":
    sequence = reverse_complement(sequence)
```

Confirm annotation coordinates before conversion: BED is normally 0-based
half-open; GFF/GTF text is normally 1-based inclusive.

## Sequential FASTA and FASTQ

`FastxFile` streams FASTA, FASTQ, or mixed FASTX records. It does not implement
random access.

```python
with pysam.FastxFile("reads.fastq.gz") as reads:
    for record in reads:
        print(record.name)
        print(record.sequence)
        print(record.comment)
        print(record.quality)
```

The current class is `FastxFile`; `FastqFile` is an old compatibility name.

### Record persistence

`persist=True` is the default and copies each record so it remains valid.
For high-throughput scans, `persist=False` avoids the copy:

```python
with pysam.FastxFile("reads.fastq.gz", persist=False) as reads:
    for record in reads:
        process(record.name, record.sequence)
        # Do not save `record` for use after the iterator advances.
```

With `persist=False`, records are read-only proxies and cease to be valid after
iteration advances. Copy needed strings or use the default when retaining
records.

### Quality scores

```python
with pysam.FastxFile("reads.fastq") as reads:
    for record in reads:
        if record.quality is None:  # FASTA record
            continue
        qualities = record.get_quality_array()
        mean_quality = (
            sum(qualities) / len(qualities) if qualities else None
        )
```

Pysam converts the FASTQ quality string to numeric Phred scores. Confirm the
source encoding for legacy FASTQ; modern data is normally Phred+33.

### Safe writing

`str(record)` preserves whether the record is FASTA or FASTQ and includes the
comment and quality line correctly:

```python
with pysam.FastxFile("reads.fastq.gz") as source, open(
    "filtered.fastq", "x", encoding="utf-8"
) as destination:
    for record in source:
        qualities = record.get_quality_array()
        if qualities and sum(qualities) / len(qualities) >= 20:
            destination.write(str(record) + "\n")
```

Use exclusive creation (`"x"`) when replacement was not requested. Manual
four-line FASTQ formatting can lose comments or create sequence/quality length
mismatches.

### Streaming statistics

```python
def fastx_stats(path: str) -> dict[str, float | int | None]:
    record_count = 0
    base_count = 0
    quality_sum = 0
    quality_count = 0

    with pysam.FastxFile(path, persist=False) as records:
        for record in records:
            record_count += 1
            base_count += len(record.sequence)
            if record.quality is not None:
                qualities = record.get_quality_array()
                quality_sum += sum(qualities)
                quality_count += len(qualities)

    return {
        "records": record_count,
        "bases": base_count,
        "mean_length": (
            base_count / record_count if record_count else None
        ),
        "mean_quality": (
            quality_sum / quality_count if quality_count else None
        ),
    }
```

This is a full scan but has constant memory.

## BGZF and Tabix

`TabixFile` provides random access to coordinate-sorted, BGZF-compressed
tabular files.

### Non-destructive compression and indexing

```python
import pysam

pysam.tabix_compress("regions.bed", "regions.bed.gz")
pysam.tabix_index("regions.bed.gz", preset="bed")
```

This leaves `regions.bed` intact. By contrast, calling `tabix_index()` directly
on an uncompressed file may automatically compress it and remove the original
unless `keep_original=True`.

Do not use `force=True` unless replacing existing compressed data or indexes is
explicitly intended.

### Input requirements

- Sort by contig and coordinate first. `tabix_index()` does not verify sort
  order.
- Use BGZF, not ordinary gzip.
- Select the correct preset: commonly `bed`, `gff`, `sam`, or `vcf`.
- Presets define columns and coordinate conventions.

For a custom table:

```python
pysam.tabix_index(
    "custom.tsv.gz",
    seq_col=0,
    start_col=1,
    end_col=2,
    zerobased=True,
)
```

Python column indices are 0-based. File coordinates are assumed 1-based unless
`zerobased=True`. This is separate from query coordinates, which are always
numeric 0-based in the Python API.

Use CSI for references beyond legacy TBI limits:

```python
pysam.tabix_index(
    "regions.bed.gz",
    preset="bed",
    csi=True,
    min_shift=14,
)
```

### Querying

```python
with pysam.TabixFile(
    "regions.bed.gz",
    parser=pysam.asBed(),
    threads=4,
) as regions:
    for row in regions.fetch("chr1", 1_000, 2_000):
        print(row.contig, row.start, row.end, row.name)
```

Numeric query coordinates are 0-based, half-open. Region strings are
samtools-style 1-based inclusive.

Useful parsers:

- `pysam.asTuple()`: tuple-like fields
- `pysam.asBed()`: BED fields with 0-based start/end
- `pysam.asGTF()`: GTF/GFF-like fields and attributes
- `pysam.asVCF()`: lightweight tabix VCF parser

For complete VCF semantics, use `VariantFile`, not `TabixFile(asVCF())`.

Without a parser, each result is the raw tab-delimited string:

```python
with pysam.TabixFile("annotations.tsv.gz") as table:
    for line in table.fetch("chr1", 1_000, 2_000):
        fields = line.split("\t")
```

### Headers and multiple iterators

```python
with pysam.TabixFile("annotations.gff.gz") as table:
    header_lines = list(table.header)
    first = table.fetch("chr1", multiple_iterators=True)
    second = table.fetch("chr2", multiple_iterators=True)
```

Header lines are yielded without trailing newlines. Each
`multiple_iterators=True` iterator reopens the file and adds overhead.

## Choosing the Right Interface

| Data | Interface | Access |
|---|---|---|
| Reference FASTA | `FastaFile` | indexed random access |
| FASTA/FASTQ reads | `FastxFile` | sequential |
| BED/GFF/GTF/custom table | `TabixFile` | BGZF + tabix/CSI random access |
| VCF/BCF | `VariantFile` | structured records, sequential or indexed |

## Common Pitfalls

- Mixing numeric 0-based coordinates with 1-based region strings
- Expecting `FastaFile` to open without `.fai`
- Using ordinary gzip for indexed FASTA or tabix data
- Retaining a `persist=False` FASTX proxy
- Assuming every FASTX record has qualities
- Manually formatting FASTQ and losing comments or quality alignment
- Letting `tabix_index()` remove the uncompressed source unexpectedly
- Indexing an unsorted file
- Forgetting `zerobased=True` for custom 0-based table coordinates
- Using a TBI index for coordinates beyond its legacy range
