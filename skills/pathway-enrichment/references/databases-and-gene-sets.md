# Databases, Gene Sets, and Gene-ID Mapping

## Contents
- [Picking libraries by question](#picking-libraries-by-question)
- [The main gene-set databases](#the-main-gene-set-databases)
- [MSigDB collections](#msigdb-collections)
- [g:Profiler (alternative ORA, custom background, 500+ organisms)](#gprofiler)
- [Gene-ID types and conversion](#gene-id-types-and-conversion)
- [Organism handling](#organism-handling)
- [Pathway/interaction APIs (Reactome, KEGG, STRING)](#pathwayinteraction-apis)
- [Activity inference (decoupler: PROGENy, DoRothEA/CollecTRI)](#activity-inference)

## Picking libraries by question

Match the database to the biological question instead of running everything:

| Question | Best gene sets |
|----------|----------------|
| "What are the broad themes?" | MSigDB **Hallmark** (50 curated, low redundancy) |
| "What mechanism/process?" | **GO Biological Process** |
| "Which curated pathways?" | **Reactome**, **KEGG**, **WikiPathways** |
| "Molecular function / localization?" | GO MF / GO CC |
| "Immune signatures?" | MSigDB **C7** (ImmuneSigDB) |
| "Oncogenic / perturbation?" | MSigDB **C6** (oncogenic), **C2:CGP** |
| "TF targets / regulons?" | MSigDB **C3**, ChEA, or decoupler (below) |
| "Disease/phenotype association?" | g:Profiler HP, DisGeNET, GWAS Catalog |

Start narrow (Hallmark + one of GO:BP / Reactome). Add libraries only if the
question needs them — each extra library multiplies the testing burden.

## The main gene-set databases

- **GO (Gene Ontology)** — three namespaces: Biological Process (BP), Molecular
  Function (MF), Cellular Component (CC). Hierarchical → highly redundant; collapse
  terms after testing (see `interpretation.md`).
- **KEGG** — manually curated metabolic & signaling pathways. Compact, well known.
- **Reactome** — large, expert-curated, hierarchical human pathway set; good
  granularity. APIs in `database-lookup`.
- **WikiPathways** — community-curated pathways; complements KEGG/Reactome.
- **MSigDB** — collections of collections (Hallmark, curated, GO, immune, etc.);
  the standard source of GMT files for GSEA.

## MSigDB collections

| Collection | Contents |
|-----------|----------|
| **H** (`h.all`) | Hallmark — 50 refined, non-redundant signatures (best default for GSEA) |
| **C2:CP** | Canonical Pathways: `c2.cp.kegg_medicus`, `c2.cp.reactome`, `c2.cp.wikipathways`, `c2.cp.biocarta` |
| **C2:CGP** | Chemical & genetic perturbations |
| **C3** | Regulatory targets (TFT, miRNA) |
| **C5** | Ontology: `c5.go.bp`, `c5.go.mf`, `c5.go.cc`, `c5.hpo` |
| **C6** | Oncogenic signatures |
| **C7** | ImmuneSigDB |
| **C8** | Cell-type signatures |

Fetch via gseapy: `gp.Msigdb().get_gmt(category="h.all", dbver="2024.1.Hs")`
(use `dbver="…Mm"` for mouse symbols). See `gseapy.md`.

## g:Profiler

The official client (`gprofiler-official`) is the best path when you need a
**custom background**, **many organisms** (~500), or g:Profiler's `g:SCS`
multiple-testing correction. It performs ORA over GO, KEGG, Reactome,
WikiPathways, miRTarBase, CORUM, HP, and more in one call.

```python
from gprofiler import GProfiler

gp = GProfiler(return_dataframe=True)
res = gp.profile(
    organism="hsapiens",                      # mmusculus, dmelanogaster, ...
    query=gene_list,                          # symbols, Ensembl, Entrez — auto-detected
    sources=["GO:BP", "KEGG", "REAC", "WP"],  # restrict sources
    user_threshold=0.05,
    significance_threshold_method="g_SCS",    # default; or "fdr" / "bonferroni"
    domain_scope="custom",                    # use a custom statistical background
    background=expressed_genes,               # the tested/expressed universe
    no_iea=False,                             # True = drop electronic GO annotations
)
# columns: source, native, name, p_value, term_size, query_size,
#          intersection_size, effective_domain_size, intersections
```

`gp.convert(organism="hsapiens", query=ids, target_namespace="ENTREZGENE")` maps
IDs; `gp.orth(...)` maps orthologs across organisms.

## Gene-ID types and conversion

Enrichr and MSigDB libraries are keyed by **gene symbols**. Convert other ID
types before ORA/GSEA, or matches silently drop.

| You have | Convert with |
|----------|--------------|
| Ensembl gene IDs (`ENSG…`) | `gp.Biomart`, g:Profiler `g:Convert`, or `mygene` |
| Entrez IDs | `mygene`, g:Profiler |
| Mouse symbols → human | g:Profiler `g:Orth`, `mygene` (then run human libraries) |

`mygene` example:
```python
import mygene
mg = mygene.MyGeneInfo()
hits = mg.querymany(ensembl_ids, scopes="ensembl.gene",
                    fields="symbol", species="human", as_dataframe=True)
symbols = hits["symbol"].dropna().tolist()
```
Strip Ensembl version suffixes first (`ENSG00000141510.16` → `ENSG00000141510`).
The `gget` skill (`gget info`) is another quick ID-mapping path.

## Organism handling

- Human symbols are UPPERCASE (`TP53`); mouse symbols are Title-case (`Trp53`).
- Set `organism=` for `gp.enrichr` (Enrichr) and use the matching MSigDB `dbver`
  (`…Hs` vs `…Mm`) or g:Profiler `organism=` code.
- Don't run human libraries on mouse symbols — convert or map orthologs first.

## Pathway/interaction APIs

For raw pathway content or network context (not enrichment statistics), use the
`database-lookup` skill, which wraps:
- **Reactome** content + Analysis Service (submit a gene list, get pathway
  over-representation).
- **KEGG** pathways/compounds.
- **STRING** — protein–protein interactions plus its own functional-enrichment
  endpoint for a submitted gene set; pairs well with `networkx` for network views.
- **Gene Ontology / QuickGO** term metadata.

## Activity inference

When the goal is **pathway or TF activity** (a continuous score per sample/cell)
rather than over-representation of a list, use `decoupler`. It runs multiple
enrichment/activity methods (ORA, GSEA, univariate linear models, etc.) against
curated priors:
- **PROGENy** — 14 signaling pathway responsive signatures.
- **DoRothEA / CollecTRI** — TF→target regulons for TF-activity inference.
- **MSigDB** priors via its OmniPath integration.

decoupler integrates natively with AnnData/Scanpy (per-cell activities) and with
per-sample pseudobulk matrices. APIs evolve between major versions — check the
current decoupler docs (https://decoupler-py.readthedocs.io/) for exact function
names before writing code.
