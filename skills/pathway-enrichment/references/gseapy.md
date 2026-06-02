# gseapy Reference

gseapy (v1.1.x, Python/Rust) wraps GSEA, preranked GSEA, ssGSEA, GSVA, and the
Enrichr API behind a pandas-friendly interface. License: BSD-3-Clause.

## Contents
- [Module map](#module-map)
- [ORA: enrichr (online) and enrich (offline)](#ora)
- [Preranked GSEA](#preranked-gsea)
- [Standard GSEA (matrix + classes)](#standard-gsea)
- [ssGSEA and GSVA](#ssgsea-and-gsva)
- [Gene sets: libraries, MSigDB, GMT](#gene-sets)
- [Gene-ID mapping with Biomart](#biomart)
- [Plotting](#plotting)
- [Result columns](#result-columns)
- [Troubleshooting](#troubleshooting)

## Module map

```python
import gseapy as gp
gp.enrichr      # online ORA via Enrichr API
gp.enrich       # offline ORA against a local GMT / dict
gp.prerank      # preranked GSEA (per-gene score)
gp.gsea         # standard GSEA (expression matrix + class labels)
gp.ssgsea       # single-sample GSEA (per-sample scores)
gp.gsva         # GSVA (per-sample scores)
gp.Msigdb       # download MSigDB collections
gp.Biomart      # gene/ID conversion
gp.get_library_name(organism="human")  # list Enrichr libraries
gp.get_library("KEGG_2021_Human")      # fetch a library as a dict
gp.read_gmt("sets.gmt")                 # load a local GMT as a dict
# plots: gp.dotplot, gp.barplot, gp.ringplot, gp.enrichment_map,
#        gp.gseaplot, gp.gseaplot2, gp.heatmap
```

## ORA

### enrichr (online)
```python
enr = gp.enrichr(
    gene_list=genes,                 # list, Series, DataFrame, or txt path (symbols)
    gene_sets=["MSigDB_Hallmark_2020", "KEGG_2021_Human"],  # names, GMT, or dict
    organism="human",                # human|mouse|fly|yeast|worm|fish
    background=None,                  # list or count; default is the library background
    outdir=None,                      # None = in-memory only
)
enr.results        # DataFrame: all terms across all libraries (Gene_set column)
```
Key result columns: `Gene_set`, `Term`, `Overlap` (k/K), `P-value`,
`Adjusted P-value` (BH within library), `Odds Ratio`, `Combined Score`, `Genes`.

`background` note: Enrichr's online API largely ignores arbitrary custom
backgrounds (it has fixed per-library backgrounds). For a true custom background
use `gp.enrich()` (below) or g:Profiler. See `interpretation.md`.

### enrich (offline, custom background)
```python
gene_sets = gp.read_gmt("c2.cp.reactome.v2024.1.Hs.symbols.gmt")  # dict
enr = gp.enrich(
    gene_list=genes,
    gene_sets=gene_sets,
    background=expressed_genes,       # REQUIRED here; the tested/expressed universe
    outdir=None,
)
```
Use this when reviewers will ask about the background, or when offline.

## Preranked GSEA

```python
pre = gp.prerank(
    rnk=rnk,                          # Series indexed by gene, or 2-col DataFrame/.rnk path
    gene_sets=["MSigDB_Hallmark_2020"],
    min_size=15, max_size=500,        # filter sets by size
    permutation_num=1000,             # >=1000 for publication
    weight=1.0,                       # weighted KS (classic = 0)
    seed=123, threads=4, outdir=None,
)
pre.res2d        # DataFrame of results (see Result columns)
pre.results      # dict keyed by term with ES curve, lead genes, etc.
```
`rnk` must be sorted high→low and have no duplicate gene IDs. Rank by the DESeq2
`stat`, or `sign(log2FoldChange) * -log10(pvalue)`; avoid log2FC alone.

## Standard GSEA

When you have the expression matrix and class labels (rather than a precomputed
rank), GSEA computes the ranking internally per the chosen metric.
```python
gsea = gp.gsea(
    data=expr_df,                     # genes x samples (DataFrame or GCT path)
    gene_sets="MSigDB_Hallmark_2020",
    cls=["A","A","B","B"],            # class vector or .cls path
    permutation_type="phenotype",     # or "gene_set" for few samples
    method="signal_to_noise",         # ranking metric
    permutation_num=1000, seed=123, threads=4, outdir=None,
)
gsea.res2d
```
With < ~7 samples per group, use `permutation_type="gene_set"`.

## ssGSEA and GSVA

Per-sample pathway scores (no class labels) — useful as features for ML or for
heatmaps of pathway activity across samples/cells.
```python
ss = gp.ssgsea(data=expr_df, gene_sets="MSigDB_Hallmark_2020",
               sample_norm_method="rank", outdir=None, threads=4)
ss.res2d                              # long-form NES per (Term, Name)
scores = ss.res2d.pivot(index="Term", columns="Name", values="NES")  # terms x samples

gsva = gp.gsva(data=expr_df, gene_sets="MSigDB_Hallmark_2020", outdir=None)
```

## Gene sets

### List / fetch Enrichr libraries
```python
gp.get_library_name(organism="human")     # names drift; check, don't hardcode
lib = gp.get_library("Reactome_2022")     # dict: {term: [genes]}
```
Common human libraries: `MSigDB_Hallmark_2020`, `GO_Biological_Process_2023`,
`GO_Molecular_Function_2023`, `GO_Cellular_Component_2023`, `KEGG_2021_Human`,
`Reactome_2022`, `WikiPathway_2023_Human`, `MSigDB_Oncogenic_Signatures`.

### MSigDB collections
```python
msig = gp.Msigdb()
print(msig.list_dbver())                   # available MSigDB versions
cats = msig.list_category(dbver="2024.1.Hs")
hallmark = msig.get_gmt(category="h.all", dbver="2024.1.Hs")  # dict for prerank/gsea
```
Useful categories: `h.all` (Hallmark), `c2.cp.kegg_medicus`, `c2.cp.reactome`,
`c2.cp.wikipathways`, `c5.go.bp`, `c7.immunesigdb`.

### Local GMT
```python
gene_sets = gp.read_gmt("my_sets.gmt")     # then pass to enrich/prerank/gsea
```

## Biomart

```python
bm = gp.Biomart()
# Ensembl gene IDs -> HGNC symbols
conv = bm.query(dataset="hsapiens_gene_ensembl",
                attributes=["ensembl_gene_id", "external_gene_name"],
                filters={"ensembl_gene_id": ensembl_ids})
```
For mouse→human ortholog mapping or many IDs, g:Profiler `g:Convert`/`g:Orth`
or the `mygene` package are often easier (see `databases-and-gene-sets.md`).

## Plotting

```python
gp.dotplot(enr.results, column="Adjusted P-value", size=5, top_term=15,
           title="ORA", cmap="viridis_r", ofname="dot.png")
gp.barplot(enr.results, column="Adjusted P-value", top_term=15, ofname="bar.png")
gp.dotplot(pre.res2d, column="FDR q-val", title="GSEA", ofname="gsea_dot.png")  # GSEA
gp.gseaplot(term=pre.res2d.Term.iloc[0], ofname="running.png",
            **pre.results[pre.res2d.Term.iloc[0]])                    # running-ES curve
gp.enrichment_map(pre.res2d)          # nodes=terms, edges=gene overlap (returns graph)
```
`dotplot`/`barplot` return a Matplotlib `Axes`; `get_figure().savefig(...)` to save.

## Result columns

Enrichr (ORA): `Gene_set`, `Term`, `Overlap`, `P-value`, `Adjusted P-value`,
`Old P-value`, `Old Adjusted P-value`, `Odds Ratio`, `Combined Score`, `Genes`.

GSEA/prerank (`res2d`): `Name`, `Term`, `ES` (enrichment score), `NES`
(normalized ES — compare across sets), `NOM p-val`, `FDR q-val`, `FWER p-val`,
`Tag %`, `Gene %`, `Lead_genes` (leading-edge genes driving the signal).

Rank by `NES` for direction/magnitude; filter by `FDR q-val`. Positive NES =
enriched at the top of the rank (e.g., up in your test condition).

## Troubleshooting

- **Empty / near-empty results** → almost always a gene-ID or organism mismatch.
  Check overlap: `set(genes) & set(gp.get_library(lib).keys()...)`; confirm symbols
  and `organism`.
- **HTTP errors / timeouts from Enrichr or MSigDB** → transient; retry, reduce the
  number of libraries, or switch to offline `gp.enrich()` with a local GMT.
- **`prerank` complains about duplicates / non-numeric** → dedupe the index and
  coerce scores to float; drop NaN before sorting.
- **Too few genes match a set** → raise `min_size` caution; tiny overlaps are noise.
- **Different results between runs (GSEA)** → set `seed` and report `permutation_num`.
