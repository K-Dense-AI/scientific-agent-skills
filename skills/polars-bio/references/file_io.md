# File I/O (polars-bio 0.36.0)

Use the [reader API](https://biodatageeks.org/polars-bio/api/reading/),
[format guide](https://biodatageeks.org/polars-bio/features/reading/), and
[writer API](https://biodatageeks.org/polars-bio/api/writing/).
The examples with filenames are templates. Small synthetic local reads and
round trips were exercised on 0.36.0/Polars 1.44.2; inspect real input schemas.

## Select a format-specific entry point

| Format | Eager / lazy | SQL registration | Native output |
|---|---|---|---|
| BED | `read_bed` / `scan_bed` | `register_bed` | No BED writer |
| VCF text | `read_vcf` / `scan_vcf` | `register_vcf` | `write_vcf` / `sink_vcf` |
| BCF binary | `read_bcf` / `scan_bcf` | `register_bcf` | No BCF writer |
| VCF Zarr | `read_vcf_zarr` / `scan_vcf_zarr` | `register_vcf_zarr` | None |
| BAM | `read_bam` / `scan_bam` | `register_bam` | `write_bam` / `sink_bam` |
| SAM | `read_sam` / `scan_sam` | `register_sam` | `write_sam` / `sink_sam` |
| CRAM | `read_cram` / `scan_cram` | `register_cram` (reference caveat below) | `write_cram` / `sink_cram` |
| GFF / GTF | `read_gff` / `scan_gff`; `read_gtf` / `scan_gtf` | `register_gff` / `register_gtf` | None |
| FASTA / FASTQ | `read_fasta` / `scan_fasta`; `read_fastq` / `scan_fastq` | `register_fasta` / `register_fastq` | Corresponding `write_*` / `sink_*` |
| Hi-C pairs | `read_pairs` / `scan_pairs` | `register_pairs` | None |
| Tabular text | `read_table` / `scan_table` | Use `from_polars` | Use Polars |

0.36.0 also has BGEN/PGEN, BigWig/BigBed, Cooler, MSA and structure readers.
Consult their specific signatures and companion-file requirements when needed;
this reference's examples concern genomic intervals and the formats above.

## BED and custom tables

`read_bed`/`scan_bed` expose `chrom` (String), `start`/`end` (UInt32) and
`name` (String). BED3 yields a null name. Extra BED6/BED12 fields are discarded,
not auto-detected into extra columns. Do not lose strand or exon block structure
by assuming a BED12 input is twelve output columns.

```python
import polars as pl
import polars_bio as pb

# Preserve native half-open coordinates.
regions = pb.scan_bed("regions.bed", use_zero_based=True)

# Preserve BED6 annotations; generic table readers do not convert coordinates.
bed6 = pb.scan_table("regions.bed6", schema="bed6")
bed6.config_meta.set(coordinate_system_zero_based=True)

# Nonstandard, headerless TSV: explicit Polars schema.
custom = pl.scan_csv("regions.tsv", separator="\t", has_header=False,
                     schema={"chrom": pl.String, "start": pl.Int64,
                             "end": pl.Int64, "label": pl.String})
custom.config_meta.set(coordinate_system_zero_based=True)
```

Despite its `Dict` annotation, `read_table`/`scan_table` expect a named schema
such as `"bed3"`/`"bed6"`/`"bed12"`, not a dictionary of Python types. They wrap
Polars TSV scanning; pass Polars CSV options as appropriate. Handle `track`,
`browser` and comment lines explicitly and validate field counts. BED12 block
columns need parsing/explosion if analysis is at exon level, not outer span.

There is no `pb.write_bed`: select the intended ordered BED columns and use
Polars tab-separated output with no header after confirming 0-based coordinates.

## VCF, BCF and VCF Zarr

```python
variants = pb.scan_vcf("cohort.vcf.gz", use_zero_based=True,
                       info_fields=["AF"], format_fields=["GT", "DP"])
binary = pb.scan_bcf("cohort.bcf", use_zero_based=True,
                     info_fields=[], format_fields=["GT"])
local_zarr = pb.scan_vcf_zarr("cohort.vcz", use_zero_based=True,
                             info_fields=[], format_fields=[])
```

VCF and BCF entry points are distinct; passing `.bcf` to `read_vcf` is rejected.
Base VCF columns include `chrom`, `start`, `end`, `id`, `ref`, `alt`, `qual` and
`filter`. Executed VCF output had UInt32 bounds and Float64 `qual`. There is no
universal raw `info` string: `info_fields=None` expands header declarations;
`[]` excludes them. FORMAT behaves analogously. Inspect list versus scalar
fields from their VCF Number declarations before filtering.

Single-sample FORMAT appears at the top level, with collision handling such as
`fmt_DP` when INFO already owns `DP`. Multisample `genotypes` is a struct of
per-field lists; sample order is in `pb.get_metadata(df)["header"]["sample_names"]`.
`samples=[...]` is case sensitive and follows requested order; missing names
warn and are skipped. Validate the selected names/count instead of treating a
warning as proof that every requested sample was loaded.

BCF additionally supports `genotype_output="dosage"` with
`format_fields=["GT"]`: nullable Int8 ALT counts, biallelic only, missing/partial
calls null. It is not an imputed dosage-probability reader. This option is absent
from text VCF. VCF Zarr uses local directory paths and has its own
`genotype_encoding_raw` option; do not pass that option to VCF/BCF.

VCF interval span is a representation of the record, not a complete model of
structural-variant breakends or all allele effects. Confirm END, REF length,
symbolic alleles and multiallelic normalization against the biological question.
Variant-record counts are not allele counts or independent sample counts.

### VCF writes and fidelity

```python
# Retains per-record INFO/FORMAT key layout as well as source metadata.
lf = pb.scan_vcf("cohort.vcf", use_zero_based=True,
                  preserve_record_layout=True)
pb.sink_vcf(lf.filter(pl.col("qual") > 30), "filtered.vcf.bgz")
```

Keep `_vcf_info_keys`, `_vcf_format_keys` and their metadata to retain source
key layout. Numeric values can still be canonicalized, so this is not a byte
identity guarantee. Local input header text is preserved; remote headers are
rebuilt from typed metadata and can lose free-form provenance lines. Added
annotation fields require correct header declarations. A declared `INFO_<id>`
column can supply source INFO values when an annotation column shadows `<id>`.
Write a small file and re-read with a VCF parser before relying on a transformed
header/schema. BCF is input-only; `write_vcf` emits text even if given a misleading
extension, so use `.vcf`, `.vcf.gz` or `.vcf.bgz`.

## BAM, SAM and CRAM

Executed SAM/BAM schemas contain `name`, `chrom`, `start`, `end`, `flags`,
`cigar`, `mapping_quality`, `mate_chrom`, `mate_start`, `sequence`,
`quality_scores`, `template_length`. Bounds and flags are UInt32;
`template_length` is Int32. Unmapped positions can be null. Read optional tags
with `tag_fields=["NM", "MD"]`; `infer_tag_types=True` samples 100 records by
default. For unsampled/custom tags supply SAM hints such as `"pt:i"` or
`"ML:B:C"`, not a guessed string cast.

```python
alignments = pb.scan_bam("reads.bam", use_zero_based=True,
                         tag_fields=["NM", "MD"])
cram = pb.scan_cram("reads.cram", reference_path="reference.fa",
                    use_zero_based=True)
pb.sink_bam(alignments, "filtered.bam", sort_on_write=True)
```

An index is optional for a full sequential scan. Neighboring BAI/CSI (BAM),
CRAI (CRAM), TBI/CSI (compressed VCF/GFF/GTF/pairs), or CSI (BCF) enables supported
indexed paths. Validate a region query against a full-scan fixture before
assuming a complex filter is pushed down. Keep index and data versions matched.

External-reference CRAM reads require a local FASTA and `.fai`; embedded-reference
files may omit it. `register_cram` and `depth` lack `reference_path`; use a reader
plus `from_polars` for SQL, or convert external-reference CRAM to BAM for depth.
CRAM MD/NM tags have an upstream reader limitation; use BAM when those tags are
required. Verify contig names, lengths and reference identity, not just a filename.

`write_*` returns the row count; `sink_*` returns None. BAM/SAM/CRAM offer
`sort_on_write`; sorting may buffer data. CRAM writers **require** `reference_path`.
Preserve sequence headers and coordinate metadata, verify reference ordering for
index creation, and create/check an index separately; writing is not evidence of
an index. Alignment-span overlap includes CIGAR-skipped regions unless the reads
are split into aligned blocks; choose depth for CIGAR-aware coverage instead.

## Annotation, sequence and pairs schemas

- GFF/GTF use UInt32 `start`/`end`, `type`, `source`, Float32 `score`, `strand`,
  UInt32 `phase`. Default `attributes` is `List(Struct(tag, value))`. Use
  `attr_fields=["ID", "Name"]` for those GFF3 keys or actual GTF keys such as
  `["gene_id", "gene_name"]`; projected fields replace the attributes column.
  Missing keys are not evidence that a gene lacks the biological annotation.
- FASTA uses String `name`, `description`, `sequence`. FASTQ adds String
  `quality_scores`. Validate sequence/quality lengths and quality encoding for
  the producing technology. Both formats have writers and lazy sinks.
- Pairs uses `readID`, `chrom1`, `pos1`, `chrom2`, `pos2`, `strand1`, `strand2`;
  positions are UInt32 in the exercised fixture and obey `use_zero_based`.
  These are two contact points, not automatically one contiguous interval.

`describe_vcf`/`describe_bcf` inspect variant field definitions;
`describe_bam`/`describe_sam`/`describe_cram` sample tags. Discovery from a sample
cannot prove a rare tag never occurs. Check exact signatures: describe helpers
do not all expose the same cloud or concurrency arguments.

## Remote data and compression

These are object/file reads, not a paginated REST service. For supported remote
readers pass URI strings (`s3://`, `gs://`, `az://`, HTTP(S)) and individual
options. SAM and VCF Zarr do not expose the common cloud options; do not assume
cloud support for every `read_*`. A small public HTTPS BED read was executed;
authenticated provider access remains untested.

[Official cloud options](https://biodatageeks.org/polars-bio/features/cloud/):

| Option | 0.36.0 behavior |
|---|---|
| `chunk_size` | MiB per ranged request, usually 8 for readers/scans; 64 for most registration helpers; `register_fasta` uses 8 |
| `concurrent_fetches` | Default 8 on functions exposing it, not 1; supported backend/path dependent |
| `allow_anonymous` | Default True for supported public S3/GCS reads; set False for authentication |
| `max_retries`, `timeout` | Common defaults 5 and 300 seconds |
| `enable_request_payer` | S3-only requester-pays option; enabling can incur charges |

S3 supports `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_REGION`/`AWS_DEFAULT_REGION`, and custom `AWS_ENDPOINT_URL`. GCS supports
`GOOGLE_APPLICATION_CREDENTIALS`. Azure uses `AZURE_STORAGE_ACCOUNT`,
`AZURE_STORAGE_KEY`, and `AZURE_ENDPOINT_URL`; anonymous/concurrent capabilities
are not equivalent to S3/GCS. Verify the provider's supported credential path
instead of assuming every cloud SDK default credential chain is implemented.
Never embed credentials in a published URL or source file.

Object reads can require HEAD and ranged GET support. At eight 8-MiB fetches,
up to 64 MiB can be in flight per stream, before parser and join allocations.
`concurrent_fetches=1` reduces concurrency but does not guarantee GET-only signed
URL compatibility for every HTTP/indexed path. Keep request limits small when
probing, and do not interpret `limit()` as a guarantee of tiny network transfer.

GZIP and BGZF differ: a `.gz` suffix does not prove BGZF or indexability. A plain
GZIP BED fixture succeeded in 0.36.0 despite an outdated reader docstring.
For VCF/FASTA/FASTQ writes, `.gz` selects GZIP and `.bgz` selects BGZF; native BAM
is BGZF. Use BGZF plus the appropriate matching index for supported selective
reads. Parallel decompression, fetching, and indexed parsing are separate
features; none is guaranteed across every format merely by compressing a file.
