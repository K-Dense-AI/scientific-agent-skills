# GSEApy reference (tested 1.3.1)

Python/Rust implementation, BSD-3-Clause. These patterns require your own validated
inputs; offline numerical/plotting APIs were exercised with synthetic data. See
[verified-api.md](verified-api.md) for online verification and service limitations.

## ORA: online and local

```python
import gseapy as gp
# genes and tested_genes must already use the library's namespace/species.
enr = gp.enrichr(
    gene_list=genes, gene_sets=["MSigDB_Hallmark_2020"], organism="human",
    background=tested_genes, outdir=None,
)
results = enr.results                  # all submitted libraries
```

In 1.3.1, named libraries with a nonempty iterable background use **Speedrichr**.
Without that background, the standard Enrichr service supplies its default.
The public wrapper docstring still says online backgrounds are ignored; released
`enrich_online()` code contradicts that and was tested with mocked transport.
A numeric background count does not select the custom-background route.
Speedrichr's base URL is not organism-specific; use local GMT for custom
backgrounds with fly/fish/worm/yeast rather than assuming the routing is correct.

For offline analysis, pass a GMT/dict **and explicit gene universe**:

```python
sets = gp.read_gmt("pathways.symbols.gmt")
assert set(genes) <= set(tested_genes)
enr = gp.enrich(gene_list=genes, gene_sets=sets,
                background=tested_genes, outdir=None)
```

The local one-sided hypergeometric test intersects each set and query with the
background. `Overlap` is hits / set size after intersection. It returns only
terms with at least one hit and applies BH over those returned terms, not every
zero-hit term in the GMT. If the planned testing family includes all eligible
terms, retain zero-hit tests with p=1 and recompute BH over that full family.
Its `Odds Ratio` includes a 0.5 continuity correction in all four cells; this
need not equal the online service's odds ratio. `Combined Score` is a ranking
heuristic, not an adjusted p-value or biological effect size.

`enr.results` can remain a list when no terms match. Check that it is a DataFrame
before filtering. Standard export, Speedrichr and local results have different
columns: Speedrichr JSON does not include `Overlap`; do not require it universally.
`outdir=None` suppresses result files, but online library downloads may still cache.

## Preranked GSEA

```python
pre = gp.prerank(
    rnk=rnk,                          # unique IDs, finite signed scores, all tested genes
    gene_sets="pathways.symbols.gmt",
    organism="human",                # only routes named Enrichr libraries
    min_size=15, max_size=500,        # matched size after intersection with rank
    method="permutation", permutation_num=1000,
    weight=1.0, seed=123, threads=4, ascending=None, outdir=None,
)
results = pre.res2d
```

Sort `rnk` descending first; `ascending=None` preserves that order, including ties.
The helper uses a stable sort and reports ties. GSEApy itself can uppercase
inputs when sampled gene sets are uppercase; this heuristic is not orthology.
Verify matching IDs beforehand and inspect matched/leading genes afterward. A seed cannot make ambiguous
identifier mapping or arbitrary tied ranks scientifically valid. Check sensitivity
when many ranks tie. Never let upstream duplicate renaming (`GENE_1`) stand in for
resolving multiple probes/transcripts. Do not feed an unsigned DESeq2 LRT statistic
when interpreting positive/negative enrichment; use the signed contrast statistic.

Classic permutation results include `ES`, `NES`, `NOM p-val`, `FDR q-val`,
`FWER p-val`, `Tag %`, `Gene %`, `Lead_genes`. FDR is based on NES nulls and is
scoped by the prefix before `__` in 1.3.1. GSEApy prefixes combined libraries;
avoid `__` inside custom term names unless that grouping is intentional. A single
dict without such prefixes defines one family. The hosted API prose describing
pooled FDR across all named libraries is stale relative to the 1.2.1+ source.

`method="multilevel"` is a separate, optional backend in 1.3.x: supports one
ranked list, `sample_size=101`, `eps=1e-50`, plus `permutation_num` for simple-null
normalization. It estimates smaller tail p-values, uses fgsea-style NES, applies
**BH across all tested terms**, reports `log2err`, and omits `FWER p-val`.
Do not mix its q-values/NES with the classic method without identifying the
backend. The bundled helper deliberately uses `method="permutation"`. In a 1.3.1 native
smoke, extreme sets still returned nominal p=0 despite release notes describing
a p-value floor. Interpret zero as no observed exceedances at the chosen
permutation resolution, never as a mathematically zero probability.

## Standard GSEA (matrix and independent class labels)

```python
result = gp.gsea(
    data=expr_df, gene_sets="pathways.symbols.gmt",  # genes x samples
    cls=["A"] * 7 + ["B"] * 7,                   # aligned with columns
    permutation_type="phenotype", method="signal_to_noise",
    min_size=15, max_size=500, permutation_num=1000,
    seed=123, threads=4, outdir=None,
)
```

Phenotype permutation requires exchangeable independent biological samples;
paired/block/confounded designs need a design-aware analysis upstream, not
unrestricted label shuffling. Signal-to-noise and t-test metrics need at least
three samples per phenotype; the GSEA guide recommends at least seven for
phenotype permutation. For smaller groups, gene-set permutations change the
null and fail to preserve gene correlation; disclose that limitation. Do not
pretend thousands of cells are independent biological replicates.

## ssGSEA and GSVA

```python
ss = gp.ssgsea(data=expr_df, gene_sets="pathways.symbols.gmt",
               sample_norm_method="rank", min_size=15, max_size=500,
               permutation_num=0, outdir=None, threads=4)
scores = ss.res2d.pivot(index="Term", columns="Name", values="NES")
gsva = gp.gsva(data=expr_df, gene_sets="pathways.symbols.gmt",
               kcdf="Gaussian", min_size=15, max_size=500, outdir=None)
```

These are sample-level scores, not differential-enrichment p-values. ssGSEA NES
normalization depends on the submitted score range, so separately processed
cohorts need not be comparable. Choose GSVA `kcdf` for the supplied scale:
Gaussian for continuous/log expression, Poisson for nonnegative counts, or None
for direct ECDF. Do not call pathway-membership scores evidence of activation;
use signed responsive signatures and a study design when that is the question.

## Library discovery and GMTs

```python
names = gp.get_library_name(organism="human")
lib = gp.get_library("MSigDB_Hallmark_2020", organism="human")
sets = gp.read_gmt("pathways.symbols.gmt")
```

`get_library` defaults to `min_size=0, max_size=2000`, so it can omit large terms;
choose and record these limits deliberately. The 2026-10-01 human catalog included
`GO_Biological_Process_2026`, `KEGG_2026`, `Reactome_Pathways_2024`,
`WikiPathways_2024_Human`, plus older versioned names. Names with a year do not
replace storing a downloaded GMT and its hash. Discovery verifies availability,
not species compatibility or curation quality.

```python
# lxml is needed by pandas.read_html used for the MSigDB directory listings.
versions = gp.Msigdb.list_dbver()           # DataFrame, not a plain list
categories = gp.Msigdb.list_category(dbver="2026.1.Hs")
hallmark = gp.Msigdb.get_gmt(category="h.all", dbver="2026.1.Hs")
assert hallmark and len(hallmark) == 50
# Mouse collection codes differ: use mh.all / m* categories from its own catalog.
```

`entrez=True` fetches Entrez rather than symbols. Directory listings can contain
non-release entries (currently `msigdb_releases.json`); inspect `Name` values,
not just the last row. MSigDB's website requests registration and license
compliance; public SDK-accessible GMTs do not waive those terms.

## BioMart identifiers

```python
bm = gp.Biomart()
attrs = ["ensembl_gene_id", "external_gene_name"]
conv = bm.query(dataset="hsapiens_gene_ensembl", attributes=attrs,
                filters={"ensembl_gene_id": ensembl_ids})
if conv is None or list(conv.columns) != attrs:
    raise RuntimeError("BioMart did not return the requested mapping schema")
# Inspect empty symbols, duplicate source IDs, and one-to-many mappings here.
```

The default host returned service-unavailable HTML parsed as a one-column table
during review. HTTP success/nonempty output alone is insufficient. Pin an archive
host and release when available; do not accept a different species/assembly just
to obtain a response. g:Profiler/MyGene are alternatives with different mapping
semantics, described in [databases-and-gene-sets.md](databases-and-gene-sets.md).

## Plotting and outputs

```python
ax = gp.dotplot(enr.results, column="Adjusted P-value", top_term=15, cutoff=0.05)
ax.get_figure().savefig("ora.png", dpi=200, bbox_inches="tight")
gp.barplot(enr.results, column="Adjusted P-value", ofname="bar.png")
gp.dotplot(pre.res2d, column="FDR q-val", ofname="gsea.png")
term = pre.res2d.Term.iloc[0]
gp.gseaplot(term=term, rank_metric=pre.ranking, ofname="running.png",
            **pre.results[term])
nodes, edges = gp.enrichment_map(pre.res2d, column="FDR q-val", cutoff=0.05)
```

`enrichment_map` returns **two DataFrames**, not a NetworkX graph. Use
`networkx.from_pandas_edgelist(edges, source="src_idx", target="targ_idx", edge_attr=True)`
and attach term labels from `nodes`. Without `ofname`, dotplot/barplot return
Axes; with `ofname` they save and may return None. Use `dotplot(show_ring=True)`;
there is no top-level `gp.ringplot` in 1.3.1. `gseaplot2` takes lists of terms,
hit-index lists and running-score vectors; `heatmap` takes a numeric DataFrame.
A cutoff with no matching terms can raise; report no significant result instead
of silently plotting nonsignificant terms as discoveries.
