# Variant Files: VCF and BCF

This reference targets pysam 0.24.0. Numeric pysam coordinates are 0-based,
half-open even though VCF text uses a 1-based `POS`.

## Open and Iterate

`VariantFile` auto-detects VCF, BGZF-compressed VCF, and BCF input:

```python
import pysam

with pysam.VariantFile("cohort.vcf.gz", threads=4) as variants:
    for record in variants:
        print(record.contig, record.pos, record.ref, record.alts)
```

Common modes:

- `r`: VCF input
- `rb`: BCF input; input auto-detection usually makes an explicit mode
  unnecessary
- `w`: VCF output; a `.vcf.gz` suffix selects BGZF-compressed VCF
- `wb`: compressed BCF output
- `wbu` / `wb0`: uncompressed BCF output

Writing requires a `VariantHeader`.

Useful constructor options:

- `index_filename=` for a nonstandard or remote index
- `drop_samples=True` to skip sample data
- `threads=` for compression/decompression
- `ignore_truncation=True` for missing BGZF EOF markers; not compatible with
  `threads > 1`

## Coordinates and Region Queries

```python
with pysam.VariantFile("cohort.vcf.gz") as variants:
    # Numeric coordinates: [999_999, 2_000_000)
    numeric = variants.fetch("chr1", 999_999, 2_000_000)

    # Region string: 1-based inclusive
    text = variants.fetch(region="chr1:1000000-2000000")
```

`VariantFile.fetch()` explicitly defines numeric `start`/`stop` as 0-based,
half-open. Region strings follow samtools notation.

For each `VariantRecord`:

- `contig` / `chrom`: contig name
- `pos`: 1-based VCF position
- `start`: 0-based inclusive position
- `stop`: 0-based exclusive record end
- `rlen`: reference span

Do not subtract one from a numeric `start` passed to `fetch()`. Use
`record.start` when integrating with BAM, BED, or FASTA APIs.

Random access requires:

- BGZF VCF: `.tbi` or `.csi`
- BCF: `.csi`

An unindexed VCF.gz or BCF can still be read sequentially with normal
iteration. `fetch()` with no region is index-driven; use `for record in
variants` for a true sequential pass.

For simultaneous iterators, `VariantFile.fetch()` uses `reopen=True`:

```python
first = variants.fetch("chr1", reopen=True)
second = variants.fetch("chr2", reopen=True)
```

## Header Model

```python
with pysam.VariantFile("cohort.vcf.gz") as variants:
    header = variants.header
    print(list(header.samples))

    for name, contig in header.contigs.items():
        print(name, contig.length)

    for name, field in header.info.items():
        print(name, field.number, field.type, field.description)
```

Important collections:

- `header.contigs`
- `header.samples`
- `header.filters`
- `header.info`
- `header.formats`
- `header.records`

INFO and FORMAT values can only be interpreted safely when their definitions
exist in the header. Do not infer missing Number/Type metadata.

## Record Fields

```python
for record in variants:
    alleles = record.alleles       # (REF, ALT1, ALT2, ...)
    alt_alleles = record.alts      # tuple or None
    identifier = record.id         # string or None
    quality = record.qual          # float or None
    filters = tuple(record.filter.keys())
```

`record.alleles_variant_types` classifies alleles with values such as `REF`,
`SNP`, `MNP`, `INDEL`, `BND`, `OVERLAP`, and `OTHER`.

Handle non-simple alleles:

- multiallelic records can have several ALT alleles
- symbolic alleles include `<DEL>`, `<DUP>`, `<INS>`, and others
- breakends use bracket notation
- spanning deletion uses `*`
- gVCF records often use `<NON_REF>` or `<*>`

Do not apply single-nucleotide logic to every record.

## INFO Fields

```python
for record in variants:
    depth = record.info.get("DP")
    frequencies = record.info.get("AF")
    if frequencies is not None:
        for allele_index, frequency in enumerate(frequencies, start=1):
            alt = record.alleles[allele_index]
            print(alt, frequency)
```

Number semantics matter:

- `1`: one value
- `A`: one value per ALT allele
- `R`: one value per REF+ALT allele
- `G`: one value per genotype
- `.`: variable number

Flag fields are represented as booleans. Missing values may be `None`, a tuple
containing `None`, or absent from the mapping depending on the field.

## FILTER Semantics

```python
filters = tuple(record.filter.keys())

if "PASS" in filters:
    status = "pass"
elif not filters:
    status = "unfiltered"  # VCF '.'
else:
    status = "failed"
```

`PASS`, an empty filter set (`.`), and a failed filter are distinct states. Do
not treat `.` as equivalent to `PASS` without an explicit policy.

## Sample and Genotype Data

```python
for sample_name, call in record.samples.items():
    genotype = call.get("GT")
    depth = call.get("DP")
    genotype_quality = call.get("GQ")
    phased = call.phased
    allele_strings = call.alleles
```

Genotype allele integers index `record.alleles`:

- `0`: REF
- `1`: first ALT
- `2`: second ALT
- `None`: missing allele

Do not assume diploidy:

```python
def called_alleles(genotype):
    if genotype is None:
        return ()
    return tuple(allele for allele in genotype if allele is not None)


called = called_alleles(record.samples["sample_A"].get("GT"))
alternate_count = sum(allele > 0 for allele in called)
```

`call.phased` records separator semantics but the Python GT remains a tuple.

## Efficient Sample Subsetting

Call `subset_samples()` before retrieving any record:

```python
samples = ["sample_A", "sample_B"]

with pysam.VariantFile("cohort.bcf") as source:
    source.subset_samples(samples)
    output_header = source.header.copy()

    with pysam.VariantFile(
        "subset.bcf", "wb", header=output_header, threads=4
    ) as destination:
        for record in source:
            destination.write(record)
```

This reduces decoding and memory. Do not copy a header, clear its sample
collection, and manually reconstruct records; that approach is error-prone.
Validate that every requested sample is present before subsetting.

## Writing Unchanged Records

When the destination uses the input header:

```python
with pysam.VariantFile("input.vcf.gz") as source, pysam.VariantFile(
    "passing.vcf.gz",
    "w",
    header=source.header,
    threads=4,
) as destination:
    for record in source:
        if "PASS" in record.filter:
            destination.write(record)
```

Write to a new file. Reopen and validate it before replacing any source.

## Safely Add Header Fields

Records are tied to their originating header. When the destination header is
changed, copy and translate records:

```python
with pysam.VariantFile("input.vcf.gz") as source:
    output_header = source.header.copy()
    output_header.info.add(
        "BAM_DP",
        number=1,
        type="Integer",
        description="Aligned base depth from the selected BAM and filters",
    )

    with pysam.VariantFile(
        "annotated.vcf.gz", "w", header=output_header
    ) as destination:
        for input_record in source:
            record = input_record.copy()
            record.translate(output_header)
            record.info["BAM_DP"] = 27
            destination.write(record)
```

Declare INFO, FORMAT, FILTER, and contig metadata before assigning values. Use
distinct field names when the new value has semantics different from an
existing field.

## Construct New Records

```python
header = pysam.VariantHeader()
header.add_meta("fileformat", value="VCFv4.5")
header.contigs.add("chr1", length=248_956_422)
header.info.add(
    "DP",
    number=1,
    type="Integer",
    description="Total depth",
)
header.formats.add(
    "GT",
    number=1,
    type="String",
    description="Genotype",
)
header.add_sample("sample_A")

with pysam.VariantFile("new.vcf.gz", "w", header=header) as output:
    record = output.header.new_record(
        contig="chr1",
        start=99_999,
        stop=100_000,
        alleles=("A", "G"),
        id="example",
        qual=60,
    )
    record.filter.add("PASS")
    record.info["DP"] = 40
    record.samples["sample_A"]["GT"] = (0, 1)
    output.write(record)
```

`start`/`stop` here are numeric Python coordinates. `start=99_999` writes VCF
`POS=100000`.

## Filtering Patterns

Make missing-value policy explicit:

```python
def passes(record, *, min_qual=30.0, min_dp=10) -> bool:
    if record.qual is None or record.qual < min_qual:
        return False
    depth = record.info.get("DP")
    if depth is None or depth < min_dp:
        return False
    return "PASS" in record.filter
```

For ALT-frequency filtering:

```python
frequencies = record.info.get("AF")
keep = (
    frequencies is not None
    and any(value is not None and value >= 0.01 for value in frequencies)
)
```

For genotype predicates, ignore missing alleles and preserve ploidy:

```python
gt = record.samples["sample_A"].get("GT")
has_alt = gt is not None and any(
    allele is not None and allele > 0 for allele in gt
)
```

## Compression and Indexing

Plain VCF must be coordinate sorted before compression/indexing:

```python
import pysam

pysam.tabix_compress("sorted.vcf", "sorted.vcf.gz")
pysam.tabix_index("sorted.vcf.gz", preset="vcf")
```

The last call creates TBI. To choose CSI instead, compress first and then use
bcftools indexing:

```python
import pysam.bcftools

pysam.bcftools.index("--csi", "sorted.vcf.gz", catch_stdout=False)
```

Do not use ordinary gzip for a random-access VCF. BGZF permits blocked random
access.

`tabix_index()` can automatically compress an uncompressed input and delete
the original unless `keep_original=True`; the explicit two-step pattern above
is safer. Do not use `force=True` unless overwrite is intended.

For BCF:

```python
pysam.bcftools.index("--csi", "cohort.bcf", catch_stdout=False)
```

Use CSI when contigs may exceed the legacy TBI coordinate limit. Read
`coordinates_and_indexing.md` for index selection.

## Header Translation Across Inputs

Do not merge VCFs by grouping Python records and appending sample calls. Inputs
can differ in contig order, INFO/FORMAT definitions, normalization, and allele
representation. Prefer `bcftools merge`, `bcftools concat`, or a dedicated
variant-merging tool after normalization and header reconciliation.

`record.translate(destination_header)` remaps header dictionaries but does not
normalize alleles, split multiallelic records, or resolve conflicting metadata.

## Validation Checklist

- Reopen the written file with `VariantFile`.
- Confirm contig order and sample order.
- Confirm each assigned INFO/FORMAT/FILTER field is declared with correct
  Number and Type.
- Check missing, haploid, polyploid, multiallelic, symbolic, and filtered
  records.
- Index the final coordinate-sorted output and fetch known edge intervals.
- Use bcftools validation/normalization commands when format-level guarantees
  are required.
