---
name: pathway-enrichment
description: Run pathway and gene-set enrichment analysis on gene lists or ranked gene data, then interpret the results. Use whenever the user has a set of genes (differentially expressed genes from PyDESeq2/Scanpy, CRISPR-screen hits, cluster marker genes, proteomics hits) and wants to know which biological pathways, GO terms, or gene sets are over-represented or enriched. Covers over-representation analysis (ORA / Enrichr / Fisher / hypergeometric), ranked Gene Set Enrichment Analysis (GSEA / preranked), single-sample scoring (ssGSEA/GSVA), and functional profiling via gseapy, g:Profiler, Enrichr libraries, MSigDB, GO, KEGG, Reactome, and WikiPathways — plus gene-ID mapping, choosing the right background universe, multiple-testing correction, redundancy reduction, dotplots/enrichment maps, and publication-ready tables. Use this for "pathway analysis", "enrichment analysis", "GO enrichment", "KEGG/Reactome pathways", "GSEA", "over-representation", "functional annotation", or "what pathways are my genes in".
license: MIT
metadata: {"version": "1.0", "skill-author": "K-Dense Inc."}
---

# Pathway Enrichment

## Overview

Enrichment analysis answers "what biology is over-represented in my genes?" It is the standard last step after differential expression, a screen, or clustering. There are two core methods, and choosing correctly is the single most important decision:

- **ORA (over-representation analysis)** — take a *thresholded* gene list (e.g., padj < 0.05) and test which gene sets it overlaps more than chance, using Fisher's exact / hypergeometric tests. Tools: Enrichr, g:Profiler.
- **GSEA (gene set enrichment analysis)** — take the *whole ranked list* of genes (no threshold) and test whether each gene set is concentrated toward the top or bottom. Preranked GSEA uses a per-gene score (e.g., the DESeq2 `stat`). Better when effects are broad and subtle.

This skill orchestrates these analyses, the gene-set databases behind them, and the interpretation pitfalls that make results wrong or unpublishable.

## When to Use This Skill

Use this skill when the user wants to:
- Find enriched GO terms / KEGG / Reactome / WikiPathways / MSigDB Hallmark sets in a gene list.
- Run GSEA / preranked GSEA on DESeq2, edgeR, limma, or Scanpy `rank_genes_groups` output.
- Score pathway activity per sample/cell (ssGSEA, GSVA).
- Interpret, deduplicate, and visualize enrichment results, or build a publication table/figure.
- Decide between ORA and GSEA, pick gene-set libraries, choose a background, or fix gene-ID problems.

For quick one-off Enrichr lookups the `gget` skill (`gget enrichr`) is lighter weight; for raw pathway/interaction APIs (Reactome, KEGG, STRING) see the `database-lookup` skill. Use **this** skill for full, defensible enrichment workflows.

## Choosing the Right Method

| Situation | Method | Tool / entry point |
|-----------|--------|--------------------|
| You have a discrete hit list (DE genes, screen hits, cluster markers) | **ORA** | `gp.enrichr(...)` or g:Profiler |
| You have a full ranked list (every tested gene + a score) | **Preranked GSEA** | `gp.prerank(...)` |
| You have an expression matrix + class labels | **GSEA** | `gp.gsea(...)` |
| You want a pathway score per sample/cell | **ssGSEA / GSVA** | `gp.ssgsea(...)`, `gp.gsva(...)` |
| You need a custom background or 500+ organisms | **ORA with custom domain** | g:Profiler (`domain_scope='custom'`) |
| You want TF / signaling *activity* (PROGENy, DoRothEA) | activity inference | see `references/databases-and-gene-sets.md` (decoupler) |

When in doubt: a thresholded list → ORA; a ranked table with scores → GSEA. Never threshold a list and then feed it to GSEA — that discards the ranking GSEA depends on.

## Setup

```bash
uv pip install gseapy gprofiler-official
# gseapy pulls pandas, numpy, scipy, matplotlib. Network access is needed for
# Enrichr, g:Profiler, and MSigDB downloads. For fully offline ORA, use a local
# GMT file with gp.enrich() (see references/gseapy.md).
```

Verify and list available gene-set libraries (names change over time — never hardcode blindly):

```python
import gseapy as gp
names = gp.get_library_name(organism="human")   # 200+ Enrichr libraries
print([n for n in names if "Reactome" in n or "KEGG" in n or "Hallmark" in n])
```

## Quick Start

### ORA on a hit list (gseapy + Enrichr)

```python
import gseapy as gp

# Enrichr libraries expect HGNC gene SYMBOLS (human: UPPERCASE). Map IDs first if needed.
genes = [g.strip() for g in open("deg_symbols.txt") if g.strip()]

enr = gp.enrichr(
    gene_list=genes,
    gene_sets=["MSigDB_Hallmark_2020", "GO_Biological_Process_2023",
               "KEGG_2021_Human", "Reactome_2022"],
    organism="human",
    outdir=None,            # in-memory; set a path to also write tables/plots
)
res = enr.results
sig = res[res["Adjusted P-value"] < 0.05].sort_values("Adjusted P-value")
print(sig[["Gene_set", "Term", "Overlap", "Adjusted P-value", "Combined Score", "Genes"]].head(20))
```

### Preranked GSEA from DESeq2 results

```python
import gseapy as gp
import pandas as pd

res = pd.read_csv("deseq2_results.csv", index_col=0)   # index = gene symbols
# Rank by the test statistic (sign = direction, magnitude = evidence). This is
# more stable than ranking by log2FoldChange, which is noisy for low-count genes.
rnk = res["stat"].dropna().sort_values(ascending=False)
rnk.index = rnk.index.str.upper()
rnk = rnk[~rnk.index.duplicated(keep="first")]

pre = gp.prerank(
    rnk=rnk,
    gene_sets=["MSigDB_Hallmark_2020", "GO_Biological_Process_2023"],
    min_size=15, max_size=500,        # drop tiny/huge sets (noisy or generic)
    permutation_num=1000, seed=123,   # seed = reproducible p-values
    threads=4, outdir=None,
)
out = pre.res2d.sort_values("FDR q-val")
print(out[["Term", "ES", "NES", "NOM p-val", "FDR q-val", "Lead_genes"]].head(20))
```

If you have no `stat` column, build the rank from `sign(log2FoldChange) * -log10(pvalue)`.

## Core Workflow

For a defensible analysis, work through these steps. The middle steps (ID type, background) are where results most often silently go wrong.

### Step 1 — Pin down inputs and pick the method
Confirm: which genes, what organism, is there a per-gene score (→ GSEA) or just a list (→ ORA), and what comparison they represent (direction matters for interpretation).

### Step 2 — Get gene IDs into the right namespace
Enrichr/MSigDB libraries are keyed by **gene symbols** (human UPPERCASE, mouse Title-case). If you have Ensembl/Entrez IDs, convert first. See `references/databases-and-gene-sets.md` for `gp.Biomart`, g:Profiler `g:Convert`, and `mygene`. A silent ID mismatch is the #1 cause of "nothing is significant".

### Step 3 — Choose gene-set libraries to match the question
Hallmark (broad themes) → GO:BP (mechanism) → KEGG/Reactome/WikiPathways (curated pathways) → C7 (immune), etc. Don't run 50 libraries; pick 2–4 that fit the biology. Catalog and selection guidance: `references/databases-and-gene-sets.md`.

### Step 4 — Set the background universe (ORA only)
The background must be the genes that *could* have been detected in your assay (e.g., all expressed/tested genes), not the whole genome. The wrong background inflates significance. Enrichr uses a fixed background; when background matters, use g:Profiler with `domain_scope='custom'` + your `background`, or `gp.enrich()` with an explicit background. Rationale in `references/interpretation.md`.

### Step 5 — Run the analysis
Use the Quick Start patterns or the bundled `scripts/run_enrichment.py`. For GSEA always set a `seed` and report `permutation_num`.

### Step 6 — Filter on adjusted p-values
Use `Adjusted P-value` (ORA, Benjamini–Hochberg) or `FDR q-val` (GSEA), not raw p-values. Typical cutoff 0.05; also check the overlap/gene count so a "hit" isn't 1 gene out of a 2000-gene set.

### Step 7 — Visualize
Dotplots, bar plots, enrichment maps, and GSEA running-score plots are built into gseapy (`gp.dotplot`, `gp.barplot`, `gp.enrichment_map`, `gp.gseaplot`). See `references/gseapy.md`.

### Step 8 — Reduce redundancy and interpret
GO especially returns many near-duplicate terms. Collapse with an enrichment map (term–term similarity), leading-edge overlap, or parent terms, and report representative terms. Interpretation framework and a publication-table format are in `references/interpretation.md`.

## Helper Script

`scripts/run_enrichment.py` runs ORA or GSEA end-to-end and writes a results table plus a dotplot, handling the boilerplate (symbol cleanup, dedup, NA removal, rank construction from a DESeq2 table, per-library FDR filtering).

```bash
# ORA from a hit list (one gene symbol per line)
python scripts/run_enrichment.py ora \
  --genes deg_symbols.txt \
  --libraries MSigDB_Hallmark_2020 GO_Biological_Process_2023 KEGG_2021_Human \
  --organism human --outdir results/

# Preranked GSEA from a DESeq2 results CSV (auto-builds the rank from `stat`)
python scripts/run_enrichment.py gsea \
  --deseq2 deseq2_results.csv \
  --libraries MSigDB_Hallmark_2020 GO_Biological_Process_2023 \
  --organism human --outdir results/ --seed 123

# Preranked GSEA from an explicit 2-column rank file (gene,score)
python scripts/run_enrichment.py gsea --rnk ranked_genes.csv --outdir results/
```

Run `python scripts/run_enrichment.py --help` for all options (background file, FDR cutoff, min/max set size, permutations).

## Common Pitfalls

These cause most wrong or irreproducible results:

1. **Gene-ID / organism mismatch** — symbols vs Ensembl, human vs mouse casing. Map IDs and set `organism` correctly, or matches silently drop to ~zero.
2. **Wrong background (ORA)** — using the whole genome instead of the tested/expressed gene set inflates p-values. Set a custom background when it matters.
3. **Thresholding before GSEA** — GSEA needs the *full* ranked list; only ORA uses a cut list.
4. **Ranking GSEA by log2FoldChange alone** — unstable for low-count genes; prefer `stat` or `sign(LFC) * -log10(p)`.
5. **Multiple-testing across libraries** — FDR is computed *within* a library; running many libraries multiplies tests. Report per-library FDR and stay conservative.
6. **Redundant GO terms** — don't report 40 variants of the same term; collapse and show representatives.
7. **Significance ≠ relevance** — check the overlap count and gene-set size; tiny sets reach significance trivially.
8. **List too short/long for ORA** — <10 genes is underpowered; >2000 loses specificity (consider GSEA instead).
9. **No reproducibility metadata** — Enrichr/GO libraries are versioned and drift over time. Record library names+date and set a GSEA `seed`.

## Integration with Other Skills

- **Upstream (where genes come from):** `pydeseq2` (DE genes + `stat` for GSEA), `scanpy` (`rank_genes_groups` markers / scores), `depmap`/`pytdc` (screen hits), proteomics skills (`pyopenms`, `matchms`).
- **Databases / IDs:** `database-lookup` (Reactome, KEGG, STRING, Gene Ontology APIs), `gget` (`gget enrichr` quick path, `gget info` for ID mapping), `bioservices`.
- **Downstream:** `scientific-visualization` (custom figures), `networkx` (enrichment-map graphs), `scientific-writing` / `literature-review` (interpret and cite), `statistical-analysis` (multiple-testing details).

## Reference Files

Read the relevant file when you need depth:

- `references/gseapy.md` — full gseapy API: `enrichr`, offline `enrich`, `prerank`, `gsea`, `ssgsea`, `gsva`, `Msigdb`, `Biomart`, `get_library_name`/`read_gmt`, every plot, result-column meanings, GMT/offline usage, and troubleshooting (rate limits, empty results).
- `references/databases-and-gene-sets.md` — GO, KEGG, Reactome, WikiPathways, MSigDB collections, Enrichr library naming, g:Profiler sources, organism handling, gene-ID conversion, library selection by question, and pointers to Reactome/STRING APIs and decoupler activity inference.
- `references/interpretation.md` — ORA vs GSEA statistics, background-universe choice, multiple-testing methods (BH vs g:SCS vs Bonferroni), leading-edge genes, redundancy reduction, effect vs significance, a publication-table template, and reproducibility checklist.

## Resources

- gseapy docs: https://gseapy.readthedocs.io/ · repo: https://github.com/zqfang/GSEApy
- g:Profiler: https://biit.cs.ut.ee/gprofiler/ · Python client: https://pypi.org/project/gprofiler-official/
- Enrichr: https://maayanlab.cloud/Enrichr/ · MSigDB: https://www.gsea-msigdb.org/gsea/msigdb/
- GSEA method: Subramanian et al. (2005) PNAS, DOI: 10.1073/pnas.0506580102
