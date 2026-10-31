# Interpreting Enrichment Results

## Contents
- [ORA vs GSEA: the statistics](#ora-vs-gsea-the-statistics)
- [The background universe (ORA)](#the-background-universe-ora)
- [Multiple-testing correction](#multiple-testing-correction)
- [Reading GSEA output](#reading-gsea-output)
- [Reducing redundant terms](#reducing-redundant-terms)
- [Significance vs relevance](#significance-vs-relevance)
- [Reproducibility checklist](#reproducibility-checklist)
- [Publication table template](#publication-table-template)
- [Common misinterpretations](#common-misinterpretations)

## ORA vs GSEA: the statistics

**ORA** asks: among my *k* hits (out of a background of *N* genes), are more in
gene set *S* (size *K*) than expected by chance? This is a hypergeometric /
Fisher's exact test. It depends entirely on the threshold used to define hits and
on the background *N*. Good when there is a clear, strong hit list.

**GSEA** asks: walking down the *fully ranked* list of all tested genes, is gene
set *S* concentrated near the top (or bottom)? It uses a weighted Kolmogorov–
Smirnov-like running sum; significance comes from permutations. No arbitrary
threshold; sensitive to coordinated, modest shifts across many genes. Better when
effects are broad/subtle or when a hit list would be very short or very long.

Rule of thumb: a discrete hit list → ORA; a ranked table with per-gene scores →
GSEA. They answer different questions and can legitimately disagree.

## The background universe (ORA)

The background (the "domain" / universe) is the set of genes that *could* have
appeared as a hit. For RNA-seq that is the set of **expressed/tested genes**, not
all ~20,000 protein-coding genes. Using too large a background makes ordinary
housekeeping categories look significant — the most common way ORA results
mislead.

- GSEApy 1.3.1 routes explicit online background lists through Speedrichr;
  standard Enrichr uses its default background. **g:Profiler** accepts
  `domain_scope="custom"` and `background`; local **`gp.enrich()`** with a pinned
  GMT and explicit gene list makes the universe directly inspectable.
- The background must contain the query, use the same ID mapping as the query
  and library, and represent the actual selection opportunity (tested genes, not
  a separately chosen set that makes results smaller). Record N, k, K and overlap
  after mapping/intersection. Length, abundance and detection-dependent selection
  can bias ORA even with the right universe; consider a bias-aware null.

## Multiple-testing correction

- **Benjamini–Hochberg (FDR)** — used for Enrichr/gseapy ORA `Adjusted P-value`.
  Classic GSEA `FDR q-val` instead uses normalized enrichment-score permutation
  distributions. GSEApy 1.3.1 multilevel GSEA uses BH; state the backend.
- **g:SCS** — g:Profiler's default; accounts for the correlated structure of GO
  and overlapping terms. It is a different error-control procedure, not an FDR
  estimate; avoid a universal claim that it is superior to BH.
- **Bonferroni** controls family-wise error and does not require independent
  tests; it can be conservative with dependent/overlapping terms.

Define the testing family before looking at results. Classic GSEApy 1.3.1 scopes
FDR by library prefix (`library__term`), while multilevel BH covers all submitted
terms. Local GSEApy ORA applies BH to positive-overlap terms only. g:Profiler
returns adjusted `p_value` and source-specific domain metadata. None of these
automatically corrects across every cluster, contrast, library and threshold you
tried. Report those families and avoid selecting the most favorable run.

## Reading GSEA output

- **NES (normalized enrichment score)** — the headline metric; normalized for set
  size and the chosen null. Compare cautiously within the same method/run; it
  is not a fold-change or an interchangeable activity scale across cohorts. Sign = direction (positive = enriched at
  the top of your ranking, e.g., up in the test condition).
- **FDR q-val** — significance; filter on this. GSEA recommends `< 0.05` for
  gene-set permutations (including preranked analyses); the exploratory `< 0.25`
  convention applies to phenotype permutations. State the chosen threshold.
- **Leading-edge genes** (`Lead_genes`) — the subset of genes that drive the
  signal: hits at/before the positive peak or at/after the negative trough. Report these; they are the concrete
  biology and are useful for overlap/redundancy analysis.

## Reducing redundant terms

GO and large pathway sets return many overlapping terms describing the same
biology. Don't list 40 near-duplicates. Options:
- **Enrichment map** — graph with terms as nodes and edges weighted by gene
  overlap (Jaccard/overlap coefficient); cluster it and label clusters. gseapy:
  `gp.enrichment_map(...)`; render with `networkx` (see the networkx skill).
- **Leading-edge / gene overlap clustering** — group terms sharing most genes;
  keep one representative per group.
- **Parent terms / semantic similarity** — collapse child GO terms to a parent;
  REVIGO-style reduction by semantic similarity.
- Report a representative term per cluster plus the count of related terms.

## Significance vs relevance

- Check the **overlap count**, not just the p-value. "Term enriched, padj=0.01"
  with 2 genes out of a 1500-gene set is rarely meaningful.
- Watch **gene-set size**: tiny sets reach significance with few genes; huge,
  generic sets ("metabolic process") are uninformative — the `min_size`/`max_size`
  filters (15–500) exist for this reason.
- Assess power relative to the universe and term size; there is no universal
  minimum/maximum hit-list length. GSEA requires an appropriate complete ranking,
  which cannot be reconstructed from a hit list alone.

## Reproducibility checklist

- Record exact **library names and versions/date** (Enrichr/GO libraries drift).
- Record the **background** used (or state the default).
- For GSEA, record `permutation_num`, `seed`, `min_size`, `max_size`, weight, and
  the **ranking metric** (e.g., DESeq2 `stat`).
- State the **organism** and **gene-ID namespace**.
- Save the full results table, not just the filtered top hits.

## Publication table template

Report a compact, reviewer-friendly table:

| Term | Source | NES or odds ratio | Overlap / Set size | FDR | Key genes |
|------|--------|------------------------------|--------------------|-----|-----------|
| Interferon alpha response | Hallmark | NES +2.1 | 38/97 | 1e-4 | STAT1, IRF7, ISG15 |

For ORA use Odds Ratio + Overlap (k/K); for GSEA use NES + leading-edge size.
Note method, library version, background, and correction in the legend.

## Common misinterpretations

- "Enriched pathway X" does **not** mean pathway X is activated — ORA is
  direction-agnostic unless you split up/down lists; GSEA NES sign gives rank direction, not necessarily activation (sets can contain inhibitors).
- Overlapping significant GO terms are **not** independent findings.
- Absence of enrichment ≠ absence of biology (power, annotation gaps, wrong
  background, or ID mismatch can all hide real signal).
- Don't compare raw ES across gene sets as effect sizes; NES still depends on the
  null, gene-set collection and submitted ranking. Neither proves causality.
- Report Monte Carlo resolution and method; nominal p-values at the simulation
  floor do not establish arbitrarily tiny probabilities. More permutations do
  not fix confounding, selection bias, or an invalid null.
