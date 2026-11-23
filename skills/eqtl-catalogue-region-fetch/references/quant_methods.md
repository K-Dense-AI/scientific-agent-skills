# Quantification methods: what `quant_method` and `molecular_trait_id` mean

eQTL Catalogue v7+ harmonises six distinct quantification methods. Each measures a different molecular phenotype, uses a different `molecular_trait_id` namespace, and has different downstream interpretation. This reference documents what each is, what to filter on, and common pitfalls.

## The six methods

| `quant_method` | Phenotype | `molecular_trait_id` namespace | Most common use |
|---|---|---|---|
| `ge` | gene-level expression | Ensembl gene id (`ENSG########`) | the canonical "cis-eQTL"; pairs with GWAS in colocalisation, MR, fine-mapping |
| `tx` | per-transcript abundance | Ensembl transcript id (`ENST########`) | isoform-resolution analysis; abundance per transcript |
| `txrev` | transcript usage (proportional) | Ensembl transcript id (`ENST########`) | splicing / isoform-switch QTLs; RATIOS not abundance |
| `exon` | exon-level read count | exon id (study-specific format, often `<chr>_<start>_<end>`) | exon-usage QTLs; finer-grained than `tx` |
| `leafcutter` | intron excision ratio | intron cluster id (study-specific format) | splice-QTLs from junction-spanning reads |
| `microarray` | probe-level signal | probe id (platform-specific) | older studies on Affymetrix / Illumina arrays |

## Per-method semantics and pitfalls

### `ge` (gene expression)

- **Phenotype**: log-normalised gene-level expression (TPM-like).
- **`molecular_trait_id`**: Ensembl gene id, e.g. `ENSG00000115808` for STRN.
- **β interpretation**: per-ALT-allele change in log-normalised expression.
- **Downstream**: most cis-eQTL applications. Direct comparison to GWAS in coloc / MR is straightforward.
- **Pitfall**: requires `molecular_trait_id` filter when querying the harmonised `.all.tsv.gz` file (the file bundles all genes' rows; without the filter you fetch every gene's variants in the queried region).

### `tx` (transcript)

- **Phenotype**: per-transcript abundance (one record per Ensembl transcript).
- **`molecular_trait_id`**: Ensembl transcript id, e.g. `ENST00000263918` for STRN's canonical transcript.
- **β interpretation**: per-ALT-allele change in that transcript's abundance.
- **Downstream**: isoform-resolution coloc / MR. Useful when a gene has multiple transcripts and only one is implicated.
- **Pitfall**: a `tx` β at a transcript is NOT the same as the `ge` β at the parent gene. The agent must NOT report a `tx` row as if it were a gene-level eQTL.

### `txrev` (transcript usage)

- **Phenotype**: proportional usage of each transcript relative to gene total. Sums to 1 across a gene's transcripts.
- **`molecular_trait_id`**: Ensembl transcript id.
- **β interpretation**: per-ALT-allele change in the *fraction* of expression captured by that transcript. Not abundance.
- **Downstream**: splicing / isoform-switch QTLs. Useful for diagnosing alternative-splicing mechanisms.
- **Pitfall**: `txrev` β cannot be interpreted as expression change. If transcript A goes up in usage and transcript B goes down, total gene-level expression may be unchanged. The agent must NOT treat a `txrev` β as a `ge` β. Cross-method comparisons require explicit translation, not naive substitution.

### `exon` (exon expression)

- **Phenotype**: per-exon read count.
- **`molecular_trait_id`**: study-specific exon id (often `<chr>_<start>_<end>` or numeric within a gene).
- **β interpretation**: per-ALT-allele change in that exon's read count.
- **Downstream**: exon-usage QTLs; finer-grained than `tx`. Can localise splice-altering variants.
- **Pitfall**: exon ids are NOT stable across studies (different studies use different exon definitions). Match by genomic coordinates (chromosome + exon start + exon end), not by id.

### `leafcutter` (splice-QTL)

- **Phenotype**: intron excision ratio. Each "intron cluster" is a set of overlapping intron-spanning reads.
- **`molecular_trait_id`**: cluster id, format `<chr>:<intron_start>:<intron_end>:<cluster_id>`.
- **β interpretation**: per-ALT-allele change in the proportion of reads using that splice junction.
- **Downstream**: splicing-QTL analyses; coloc with disease GWAS specifically for splice mechanisms.
- **Pitfall**: `leafcutter` clusters are study-specific and recomputed per cohort. Do NOT match clusters across studies by id; match by genomic position.

### `microarray` (array-based)

- **Phenotype**: probe-level signal intensity.
- **`molecular_trait_id`**: platform-specific probe id (e.g., Affymetrix probe set, Illumina probe id).
- **β interpretation**: per-ALT-allele change in probe signal.
- **Downstream**: older studies (e.g. CEDAR, Fairfax 2014). Useful for historical comparisons but lower resolution than RNA-seq.
- **Pitfall**: probes can target multiple transcripts or non-coding regions. The probe-to-gene mapping is platform-specific; verify before treating a microarray hit as a gene-level eQTL. Many platforms have known cross-hybridisation issues at specific probes.

## What the skill emits

The skill returns rows from the harmonised `.all.tsv.gz` file with these columns (for any `quant_method`):

```
chromosome, position, ref, alt, variant, type,
molecular_trait_id, gene_id, beta, se, pvalue, nlog10p,
ac, an, maf, r2, median_tpm, rsid
```

`gene_id` is always the parent Ensembl gene id (even when `molecular_trait_id` is a transcript / exon / intron / probe), so the agent can group multi-row results by gene. `median_tpm` is the median expression of the molecular trait in the source tissue.

The skill's manifest carries the raw `quant_method` code AND a human-readable label (per the `CLAUDE.md` user-friendly enum-expansion rule):

```json
{
  "quant_method": "ge",
  "quant_method_label": "gene expression (ge)",
  ...
}
```

## When the user asks for "eQTLs"

Default: `quant_method=ge`. This is what most users mean.

If the request mentions splicing or alternative-isoform biology, ask whether they want `tx`, `txrev`, or `leafcutter` (each captures a different splicing aspect). If unclear, default to `ge` and surface the question explicitly: "I'll start with gene-level (ge); want me to also pull splice-QTL (leafcutter) for the same region?"

## See also

- `dataset_resolution.md`: how to resolve a (study, tissue, quant_method) tuple into a `dataset_id`.
- `cis_window_biology.md`: the strand-aware ±1 Mb cis-window applied during nominal-pass discovery (applies to all quantification methods).
- Kerimov N. et al. 2021. *A compendium of uniformly processed human gene expression and splicing quantitative trait loci.* Nat Genet 53:1290.
- eQTL Catalogue Methods page: `https://www.ebi.ac.uk/eqtl/Methods/`.
