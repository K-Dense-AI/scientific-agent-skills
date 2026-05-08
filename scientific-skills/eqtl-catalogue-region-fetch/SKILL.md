---
name: eqtl-catalogue-region-fetch
description: Fetch a region of cis-QTL summary statistics from EBI eQTL Catalogue v7+ via tabix-on-FTP. Returns harmonised per-variant rows (variant_id, chromosome, position, ref, alt, beta, SE, p-value, MAF, molecular_trait_id, study_id) for downstream colocalization, fine-mapping, regional plotting, or Mendelian randomisation. Covers all expression-related QTL flavors the catalogue hosts (gene-level, exon, transcript, transcript-event/txrevise, splicing/leafcutter, microarray, allelic fold-change). Use when an agent needs cis-QTL beta / SE / p-value for every variant in a window around a gene's TSS for one specific dataset (study × tissue × quantification method).
license: MIT
compatibility: Requires network access (queries EBI eQTL Catalogue FTP and REST API)
metadata:
    skill-author: Aviv Madar
    website: https://www.ebi.ac.uk/eqtl/
    docs: https://www.ebi.ac.uk/eqtl/Methods/
---

# eQTL Catalogue Region Fetch

## Overview

Pulls a region of cis-QTL summary statistics from EBI's [eQTL Catalogue v7+](https://www.ebi.ac.uk/eqtl/) and returns harmonised per-variant rows ready for downstream colocalization, fine-mapping, regional plotting, or Mendelian randomisation. The skill targets the catalogue's tabix-indexed FTP files (NOT the REST API — see "Caveats" below) and exposes coverage of every expression-related QTL flavor the catalogue hosts.

The eQTL Catalogue is the canonical mirror of curated eQTL studies (GTEx, BLUEPRINT, Quach 2016, GENCORD, Schmiedel 2018, Lepik 2017, BrainSeq, ROSMAP, and more), reprocessed through a uniform Snakemake pipeline (Kerimov 2021, *Nat Genet* 53:1290) so per-dataset summary statistics can be joined and compared without per-source preprocessing.

## Trigger

**Fire when** the user (or upstream agent step) wants:

- A regional slice of cis-eQTL summary statistics (β, SE, p-value) for variants around a gene's TSS, from one (study × tissue × quant_method) in eQTL Catalogue.
- Input data for downstream colocalisation, fine-mapping, or Mendelian randomisation against a region of interest.
- Provenance-rich, harmonised eQTL summary stats with allele orientation preserved (ALT-effect β).

Trigger phrases that route here include "eqtl region fetch", "eqtl catalogue tabix", "eqtl sumstats slice", "cis-eqtl region pull", "GTEx eqtl region", and similar.

**Do NOT fire when** the user wants:

- A **point lookup of one variant in one tissue**: `database-lookup` (GTEx via REST) is the right skill for single-variant queries.
- **All eQTLs for a gene across all tissues**: this skill returns one (study × tissue × quant_method) at a time. Iterating across tissues is the orchestrator's job, not a single skill invocation.
- **pQTL data**: eQTL Catalogue does not host pQTL summary statistics. Use UKB-PPP or deCODE for protein QTLs.
- **trans-eQTL data**: eQTL Catalogue's cis-window is ±1 Mb of TSS; trans-eQTL signals are at distant variants and require a different upstream (e.g., eQTLGen for blood trans).
- **Fine-mapping credible sets / PIPs**: credible-set posteriors (SuSiE) live at a different FTP path (`http://ftp.ebi.ac.uk/pub/databases/spot/eQTL/susie/`) and require a separate skill. The nominal-pass `.all.tsv.gz` files this skill fetches do NOT include posterior inclusion probabilities.

## Quick Start Workflow

The bundled script accepts a JSON or YAML config and writes a harmonised TSV plus a provenance manifest:

```bash
python scripts/eqtl_catalogue_region_fetch.py \
    --input scripts/examples/sort1_gtex_minor_salivary_gland.json \
    --output ./out/sort1_run
```

Output:

```
./out/sort1_run/
├── variants.tsv     # one row per variant (effect-allele convention, GRCh38)
├── manifest.yaml    # provenance: dataset, region, source URL, fetched-at timestamp
└── report.md        # human-readable summary
```

Three biology demos are bundled (`scripts/examples/`):

| Demo file | Locus | Tissue | Story |
|---|---|---|---|
| `sort1_gtex_minor_salivary_gland.json` | SORT1 (1p13.3) | minor salivary gland | Canonical LDL/CHD locus (Musunuru 2010) |
| `il6r_gtex_small_intestine.json` | IL6R (1q21.3) | small intestine | MR-classic IL6R × CRP (Swerdlow 2012) |
| `irf5_gtex_adipose_visceral.json` | IRF5 (7q32.1) | adipose (visceral) | SLE-associated cis-eQTL (Wang 2021) |

Use `--list-demos` to see the full list.

## Config Schema

Minimum config (JSON or YAML):

```json
{
  "dataset_id": "QTD000266",
  "molecular_trait_id": "ENSG00000134243",
  "chromosome": "1",
  "start_bp": 108774968,
  "end_bp": 109774968
}
```

| Field | Type | Description | Required |
|---|---|---|---|
| `dataset_id` | string | eQTL Catalogue dataset id (`QTD######` form). Maps 1:1 to one (study × tissue × quantification) combination. | Yes |
| `molecular_trait_id` | string | Optional ENSG (versioned or bare) to filter to one gene. Required for ge-eQTL datasets where the FTP file bundles many genes. | Recommended |
| `chromosome` | string | Chromosome name without `chr` prefix (1, 2, ..., X, Y, MT) | Yes |
| `start_bp` | integer | Region start, 1-based GRCh38 inclusive | Yes |
| `end_bp` | integer | Region end, 1-based GRCh38 inclusive | Yes |
| `study_id` | string | Optional `QTS######` parent study id; if omitted the skill resolves it from `dataset_id` via the metadata REST endpoint | No |

## Output Files

`variants.tsv` columns (TSV; effect-allele = `alt`; per-copy-`alt` beta):

```
variant_id  chromosome  position_bp  allele_a  allele_b  beta  se  p  maf  molecular_trait_id  study_id
```

`manifest.yaml` records the dataset_id, region, study/tissue labels, quant_method (with human-readable label), n_variants, source URL, and fetched-at UTC timestamp — sufficient to re-fetch the exact slice reproducibly.

## Resolving a dataset_id from an Open Targets studyId

OT studyIds for QTL studies follow the pattern `<study_label>_<quant_method>_<sample_group>_<molecular_trait_id>` — e.g. `gtex_ge_adipose_visceral_ensg00000128604` is the IRF5 ge-eQTL in GTEx visceral adipose. The eQTL Catalogue's metadata REST endpoint maps the first three pieces to a `dataset_id` (`QTD######`):

```python
import requests

# Slug parsing:
# study_label    = "gtex"
# quant_method   = "ge"
# sample_group   = "adipose_visceral"
# molecular_trait_id (per-row filter, not used in dataset resolution)
#                 = "ENSG00000128604"

resp = requests.get(
    "https://www.ebi.ac.uk/eqtl/api/v2/datasets/",
    params={"study_label": "GTEx", "quant_method": "ge", "size": 200},
    timeout=30,
)
records = resp.json()
match = next(d for d in records if d["sample_group"] == "adipose_visceral")
print(match["dataset_id"])   # "QTD000121"
```

Pass that `dataset_id` (plus the ENSG and the region) into this skill's config.

## Quant Methods Supported

`quant_method` values exposed by the catalogue and surfaced by this skill:

| Code | Meaning |
|---|---|
| `ge` | Gene expression (canonical eQTL) |
| `exon` | Exon-level expression |
| `tx` | Transcript-level expression |
| `txrev` | Transcript-event usage (txrevise tool — promoter / 3' end / internal-event ratios) |
| `leafcutter` | Intron-excision splicing (sQTL via Leafcutter) |
| `microarray` | Microarray-based expression |
| `aFC` | Allelic fold-change |

Note: pQTL data is **not** in the eQTL Catalogue (UKB-PPP and deCODE are the canonical pQTL sources).

## Gotchas

1. **Use FTP tabix, not the REST API, for regional fetches.** The eQTL Catalogue v2 REST API at `/api/v2/datasets/{id}/associations` silently truncates regional fetches to one side of TSS and ignores `pos_min` / `pos_max` query parameters. This skill fetches via tabix on the canonical FTP `.all.tsv.gz`, which serves the full strand-aware cis-window correctly. Do NOT swap the fetcher to REST.

2. **Cis-window is ±1 Mb of strand-aware TSS in genomic coordinates.** The upstream pipeline computes cis-eQTLs only for variants within ±1 Mb of the gene's transcription start site. For `+` strand genes TSS = `gene.start` (lower coord). For `−` strand genes TSS = `gene.end` (higher coord). When querying a window in genomic coords that extends beyond ±1 Mb of TSS, expect zero rows on the far side. This is correct biology, not a bug.

3. **`molecular_trait_id` filter is required for `ge` eQTL files.** The harmonised `ge` `.all.tsv.gz` bundles every gene's variant rows together. Querying a chromosomal region without a gene filter returns variants for all genes in that region (potentially thousands of rows per variant). Always pass the target Ensembl gene ID. Other quant methods (`tx`, `txrev`, `exon`, `leafcutter`) have similar bundling behavior on `molecular_trait_id` (transcript / intron / exon ID).

4. **β is reported on the ALT allele.** Do NOT compare effect sizes across datasets without explicit allele harmonisation. The skill preserves `ref` / `alt` columns; downstream tools (e.g., TwoSampleMR `harmonise_data`) flip signs when alleles are swapped. Cross-dataset comparisons (eQTL β vs GWAS β at the same variant) without harmonisation can silently invert direction.

5. **Quantification methods are not interchangeable.**
   - `ge` (gene expression): gene-level, the most common eQTL definition
   - `tx` (transcript): per-isoform abundance
   - `txrev` (transcript usage): proportional, not abundance
   - `exon` (exon expression): per-exon read count
   - `leafcutter` (splice junction): splice-QTL on intron excision ratio

   These represent distinct biology. A `txrev` row is NOT a `ge` eQTL. The skill's manifest carries the raw `quant_method` code AND a human-readable label so consumers cannot conflate them.

## Operational Notes

- **Coordinate convention is 1-based inclusive throughout** (matches Ensembl, GTEx, GWAS Catalog harmonised, eQTL Catalogue, OT, 1000G VCF). The only place 0-based half-open shows up in this stack is BED files; this skill never produces BED.
- **Per-study attribution required.** Sources are CC-BY-4.0 (catalogue level); per-study attribution is the original publication of each constituent dataset (see `manifest.yaml.release.study_label` and the catalogue's [studies page](https://www.ebi.ac.uk/eqtl/Studies/) for citation strings).
- **Network required on first call** for any (dataset, region). Subsequent calls hit a local JSON cache at `~/.cache/eqtl_catalogue_region_fetch/` (overridable via `EQTL_CATALOGUE_CACHE_DIR`). Pass `--no-cache` to bypass.

## Safety

**Not for clinical decisions.** This skill returns research-grade summary statistics from public databases. Do not use the output for direct clinical decision-making, diagnosis, or treatment selection without independent validation by a qualified clinician.

**Effect estimates may not generalise across populations.** The ancestry of the source study is recorded in the dataset metadata (`sample_group`, `population` fields where present). Effect sizes from a single-ancestry study should not be assumed to apply to other ancestries without appropriate harmonisation and trans-ancestry validation.

## Agent Boundary

The skill returns harmonised summary statistics (β, SE, p-value) for variants in a chromosomal window from one (study × tissue × quant_method) dataset. The agent should:

- **Use the output as input to colocalisation, fine-mapping, or Mendelian randomisation tooling.** These are the appropriate downstream methods for inferring causal effects.
- **NOT make causal-effect claims directly from a single eQTL p-value.** A low p-value at a variant means statistical association, not causation. Causal interpretation requires colocalisation or MR analysis with proper instrumental-variable assumptions.
- **NOT cherry-pick variants by p-value alone.** Statistical inference requires the full credible set / window context.
- **NOT compare effect sizes across datasets without harmonising effect alleles.** The skill normalises within one dataset; cross-dataset comparison requires a harmonisation step (e.g., TwoSampleMR `harmonise_data`).
- **Surface tissue, quant_method, and sample size in the user-facing reply** alongside any β / p-value the agent quotes. The same variant in IAV-stimulated monocytes (Quach 2016, N=198) and in resting monocytes (BLUEPRINT, N=191) is a different biological measurement, even though the genomic position is identical. When reporting, expand all three fields: `quantification = gene expression (ge); tissue = monocyte; n_samples = 198`.
- **NOT silently swap tissues or quantification methods.** If the user asked for `monocyte / ge` and the dataset is `monocyte / txrev`, the agent must say so explicitly and ask whether to proceed.

## Sources & Licensing

- eQTL Catalogue v7+ (Kerimov 2021 *Nat Genet* 53:1290): **CC-BY-4.0**
- Per-study attribution: original publication of each constituent dataset
- Skill code: **MIT**
