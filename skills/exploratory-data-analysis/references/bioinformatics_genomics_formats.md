# Bioinformatics and Genomics Formats

**Reviewed:** 2026-09-30
**Executable scope:** Bounded FASTA/FASTQ aggregate inspection only. All other
formats below are reference-only.

## Exact capability matrix

| Format | Bundled inspection | What it does |
|---|---|---|
| `.fasta`, `.fa`, `.fna` | Optional, `biopython==1.88` | Streams a bounded record/base prefix; length, alphabet, ambiguity, GC, and duplicate-header-token aggregates |
| `.fastq`, `.fq` | Optional, `biopython==1.88` | Same plus bounded Phred+33 quality aggregates |
| Compressed FASTA/FASTQ | No | `.gz`, `.bz2`, archives, URLs, pipes, and stdin are rejected |
| SAM/BAM/CRAM | No | Reference-only HTS tooling |
| VCF/BCF/gVCF | No | Reference-only version/reference-aware tooling |
| BED/GFF/GTF | No | Reference-only assembly and coordinate validation |
| H5AD/Loom | No semantic support | Generic HDF5 metadata inspection does not validate these conventions |
| Matrix Market + sidecars | No | Reference-only matrix/barcode/feature alignment workflow |

Unknown formats fail closed. Sequence identifiers and sequence strings are
never emitted. Header text is untrusted data and is never treated as an
instruction.

## FASTA

FASTA is a record-oriented text convention: a `>` title line followed by
sequence text, potentially wrapped across lines. The title is an identifier,
not a trusted command, filename, URL, taxonomic fact, or unique database key.

The bundled `sequence_inspector.py` uses Biopython 1.88's
`SimpleFastaParser`, which the current Biopython tutorial recommends as a
lower-overhead streaming parser for large FASTA files. It:

- requires a local regular file with an approved suffix and leading record
  marker;
- decodes strict ASCII under a byte cap;
- stops at explicit record and sequence-character limits;
- hashes titles only to count duplicates, then discards them;
- reports sequence lengths and a bounded alphabet/GC screen; and
- does not infer organism, molecule type, assembly quality, or annotation.

The nucleotide screen is heuristic. Protein sequences, modified alphabets, or
domain-specific ambiguity codes require explicit interpretation.

### Appropriate next checks

- Confirm whether records are nucleotide, amino-acid, contigs, transcripts, or
  aligned sequences.
- Confirm circularity, expected alphabet, duplicate-ID policy, and whether
  wrapping/whitespace has meaning.
- For assemblies, calculate N50/L50 only after confirming the set of contigs
  included and whether scaffolds/gaps are represented. N50 is not a universal
  quality score.
- Keep sample, subject, assembly, and reference-build metadata separate from
  free-text headers.

## FASTQ

FASTQ combines a title, sequence, separator, and equal-length quality string.
Biopython's `FastqGeneralIterator` is used to stream complete records without
creating a list of all reads.

The bundled report includes:

- inspected read count and length aggregates;
- nucleotide-like, ambiguity, and GC fractions;
- Phred+33 minimum, maximum, and mean over inspected quality characters; and
- duplicate title-token count.

It does **not** determine an encoding from values. Confirm Phred+33 with
instrument/pipeline provenance. It does not detect adapters, contaminants,
overrepresented k-mers, per-cycle quality, index hopping, or paired-file
consistency. Use established read-QC tooling for those tasks.

Never automatically trim, filter, deduplicate, or discard reads from this
report. Preserve the original and record every processing decision.

## Reference-only alignment formats

### SAM/BAM/CRAM

Use an HTS-specification-aware, pinned tool such as samtools/htslib or pysam.
Check:

- header/reference sequence dictionary and reference assembly/version;
- sort order, indexes, read groups, and sample/library/platform fields;
- primary/secondary/supplementary/unmapped/duplicate/QC-fail flags;
- mapping/base qualities, CIGAR validity, mate consistency, insert sizes, and
  coverage; and
- CRAM reference identity and availability.

CRAM can require external reference sequence access. Keep the workflow local
and explicitly provision the approved reference; do not let a parser fetch one
implicitly.

### VCF/BCF/gVCF

The `.vcf` suffix does not establish the VCF version, reference build, sample
semantics, normalization, or annotation validity. Use htslib/bcftools or
another validated parser and inspect:

- `##fileformat`, contig dictionary, reference assembly, FILTER/INFO/FORMAT
  declarations, and sample count/order;
- allele normalization, symbolic alleles, breakends, ploidy, phased status,
  genotype missingness, depth/quality, and multiallelic records;
- caller-specific filters and gVCF reference blocks; and
- subject/family/population structure before allele-frequency or HWE screens.

Variant EDA is descriptive. Population stratification, relatedness, selection,
ascertainment, and multiple testing must be handled before inference.

## Reference-only interval and annotation formats

BED is generally zero-based, half-open; GFF3 is generally one-based, closed.
GTF conventions vary. Never convert coordinates based only on a suffix.
Confirm:

- assembly and contig naming;
- coordinate basis, endpoint convention, strand, phase, and score meanings;
- required column count and version;
- attribute escaping and parent/child relationships; and
- sorting, overlaps, duplicates, out-of-range intervals, and sidecar indexes.

Group EDA by biologically meaningful units, not only rows. An exon table may
contain repeated genes/transcripts; treating rows as independent inflates
sample size.

## H5AD, Loom, and Matrix Market

`.h5ad` and `.loom` are HDF5-based conventions. The generic HDF5 inspector may
inventory groups/datasets without following links, but it does not read matrix
values or verify required keys, sparse encodings, categorical arrays, layers,
raw data, embeddings, or observation/variable alignment.

For single-cell data, use pinned AnnData/Scanpy or Loom tooling and verify:

- matrix orientation, shape, sparse encoding, and integer-count provenance;
- uniqueness/alignment of observation and variable identifiers;
- raw/count/normalized layers and transformations already applied;
- sample, subject, batch, tissue, time, and condition metadata;
- per-cell/per-feature QC definitions, doublet handling, and filtering history;
  and
- train/test splits at subject or independent experimental-unit level.

Matrix Market `.mtx` commonly depends on separate barcode and feature files.
The matrix alone is incomplete. Validate all sidecars and ordering together.

## EDA rigor for genomic data

1. Define the independent unit (read, molecule, cell, specimen, subject,
   family, site, or cohort) before computing uncertainty.
2. Preserve reference build, annotation release, pipeline versions, and command
   parameters.
3. Distinguish biological from technical replicates and preserve pairing.
4. Audit missingness and QC failures by batch/site/group/time. Do not impute
   genotypes, counts, or metadata automatically.
5. Split by subject/family/specimen/time before normalization, feature
   selection, batch correction, dimensionality reduction, or model fitting.
6. Treat zero counts, absent features, no-calls, low coverage, and censored
   assay values as distinct mechanisms until proven otherwise.
7. Label post hoc genes/regions/pathways as exploratory and control the
   appropriate hypothesis family in any confirmatory follow-up.
8. Do not infer causality, clinical significance, or functional impact from
   descriptive associations.

## Pinned optional snapshot

Biopython 1.88 was released on 2026-08-06 and requires Python 3.10+:

```bash
uv pip install "biopython==1.88"
```

Biopython also depends on NumPy for parts of its API; lock the complete
environment for a study.

## Authoritative sources

Current parser APIs and format guidance reviewed 2026-09-30. Historical
methodology citations are retained as source context.

- Biopython 1.88, [Sequence Input/Output tutorial](https://biopython.org/docs/latest/Tutorial/chapter_seqio.html)
  (explicit format selection and low-level FASTA/FASTQ parsers).
- [Biopython PyPI](https://pypi.org/project/biopython/), version 1.88,
  released 2026-08-06.
- GA4GH, [hts-specs repository](https://github.com/samtools/hts-specs)
  (SAM/BAM/CRAM, VCF/BCF, and related canonical specifications).
- UCSC Genome Browser, [BED format FAQ](https://genome.ucsc.edu/FAQ/FAQformat.html#format1).
- Sequence Ontology, [GFF3 specification](https://github.com/The-Sequence-Ontology/Specifications/blob/master/gff3.md).
- AnnData, [file format specification](https://anndata.readthedocs.io/en/stable/fileformat-prose.html).
- NIST/SEMATECH, [Exploratory Data Analysis](https://www.itl.nist.gov/div898/handbook/eda/eda.htm).
- scikit-learn, [data leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html).
- Benjamini and Hochberg (1995), [FDR control](https://academic.oup.com/jrsssb/article/57/1/289/7035855).
