# Chromatin accessibility models

Targets scvi-tools 1.5.1. These source-verified examples are illustrative;
short PEAKVI/POISSONVI CPU fits and accessibility output shapes were tested.
Genome downloads, SCBASSET training and motif inference were not executed.

## PEAKVI and POISSONVI

Use a consistent genome assembly, genomic regions and feature order across samples.
Apply assay-specific cell QC (library size, TSS enrichment, fragment length, blacklist
regions) and remove poorly supported peaks before setup. Do not indiscriminately
remove sex-chromosome peaks when sex-linked biology is relevant.

```python
import scvi

# atac_adata: cells by peaks; layer counts contains measured accessibility counts.
scvi.model.PEAKVI.setup_anndata(atac_adata, layer="counts", batch_key="batch")
peakvi = scvi.model.PEAKVI(atac_adata, n_latent=20)
peakvi.train()
atac_adata.obsm["X_PeakVI"] = peakvi.get_latent_representation()
accessibility = peakvi.get_normalized_accessibility()
da = peakvi.differential_accessibility(
    groupby="cell_type", group1="TypeA", group2="TypeB",
    mode="change", delta=0.05,
)
```

PEAKVI models binarized accessibility, so input counts do not make it a quantitative
fragment model. `get_normalized_accessibility()` returns accessibility probabilities,
optionally with cell/region normalization choices. It is not named
`get_accessibility_estimates`. `n_hidden` and `n_latent` default to `None` and are
inferred from feature count; encoder and decoder each default to two layers
(`n_layers_encoder`, `n_layers_decoder`), not a single `n_layers` option.
`get_region_factors()` exposes the learned region factors when enabled.

```python
# fragment_adata contains region-level fragment counts, not raw fragments.tsv rows.
scvi.external.POISSONVI.setup_anndata(
    fragment_adata, layer="counts", batch_key="batch",
)
poissonvi = scvi.external.POISSONVI(fragment_adata)
poissonvi.train()
fragment_latent = poissonvi.get_latent_representation()
fragment_estimates = poissonvi.get_normalized_accessibility()
```

POISSONVI retains quantitative count information. Do not confuse read counts,
Tn5 insertions and fragments; document the counting convention and use the
upstream `reads_to_fragments` helper only when its read-pair assumptions match the
assay. The 1.5.1 fragment validator requires at least 100 observations; it raises on
smaller inputs before model construction. Its count-frequency heuristic can warn
on legitimate count distributions, so verify provenance rather than modifying counts
to satisfy the heuristic. No universal speed or accuracy ordering between PEAKVI and POISSONVI follows
from the API. Compare held-out fit and biological preservation.

Accessibility DE is not RNA log fold-change: PEAKVI reports an absolute probability
effect `scale2 - scale1`. Its `delta=0.05` denotes accessibility difference. Apply
replicate-aware interpretation and the caveats in
[differential-expression.md](differential-expression.md).

## SCBASSET: sequence-aware accessibility

SCBASSET has a different orientation: **regions by cells**. The DNA sequence codes
belong to observations in `.obsm`, and batch annotations for cells belong to `.var`.
The sequence helper first operates on ordinary cells-by-regions AnnData and writes
to `.varm`; transposition then moves those arrays to `.obsm`.

```python
# Before this block: atac_adata.var has chr, start, end in the correct assembly;
# the hg38 genome is already installed locally with genomepy.
scvi.data.add_dna_sequence(
    atac_adata, genome_name="hg38", install_genome=False,
)
bdata = atac_adata.T.copy()  # regions x cells; varm -> obsm
scvi.external.SCBASSET.setup_anndata(
    bdata, dna_code_key="dna_code", layer="counts", batch_key="batch",
)
scbasset = scvi.external.SCBASSET(bdata, n_bottleneck_layer=32)
scbasset.train()
cell_embeddings = scbasset.get_latent_representation()
# Rows correspond to bdata.var_names, which are the original cell IDs.
```

Install the `regseq` extra (`genomepy`, Biopython) for sequence extraction. Explicitly
check chromosome naming, peak coordinate convention, sequence length (default
1344), bounds and genome build. The helper's default `install_genome=True` downloads
a genome; choose it only when the download is intended.

The constructor's cell embedding size is `n_bottleneck_layer`, not `n_latent`.
Do not supply invented `conv_layers`/`n_filters`/`filter_size` arguments as if they
were documented high-level constructor parameters.

`get_tf_activity(tf, genome='human', motif_dir=...)` scores motif injection against
background sequences and may download its motif library. A TF activity score is
sequence-model evidence, not direct binding or causal regulatory activity. Validate
with held-out regions/cells, motif controls and independent experiments.

## Downstream and multimodal analysis

Store latent embeddings on the **cell-indexed** object, construct Scanpy neighbors
using `use_rep`, then visualize/cluster. UMAP layout does not establish integration
quality. For paired or partially paired RNA/ATAC use MULTIVI's MuData workflow in
[models-multimodal.md](models-multimodal.md), preserving measurement missingness and
feature identities. Avoid dense whole-genome probability arrays when only a region
subset is needed; use `region_list`, `indices` or a justified output threshold.

Sources: [PEAKVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/_peakvi.py),
[POISSONVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/poissonvi/_model.py),
[SCBASSET](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/scbasset/_model.py),
[sequence/count preprocessing](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/data/_preprocessing.py).
