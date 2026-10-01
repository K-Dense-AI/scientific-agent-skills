# RNA models

Targets scvi-tools 1.5.1. Code is illustrative and source-verified; short synthetic
SCVI/SCANVI fitting, predictions, DE and persistence were exercised in CPU tests. Unless stated otherwise, examples require an
AnnData with measured RNA counts in `layers['counts']`, unique gene/cell IDs and
valid named metadata. Complete QC and feature selection before setup.

## SCVI and SCANVI

```python
import scvi

scvi.model.SCVI.setup_anndata(adata, layer="counts", batch_key="batch")
rna_model = scvi.model.SCVI(adata, n_latent=20, gene_likelihood="nb")
rna_model.train()
adata.obsm["X_scVI"] = rna_model.get_latent_representation()
normalized = rna_model.get_normalized_expression(library_size=1e4)

# cell_type contains known labels and a literal Unknown for unlabeled cells.
scanvi_model = scvi.model.SCANVI.from_scvi_model(
    rna_model, labels_key="cell_type", unlabeled_category="Unknown",
)
scanvi_model.train()
predictions = scanvi_model.predict()
probabilities = scanvi_model.predict(soft=True)
```

For training from scratch, use `SCANVI.setup_anndata` with `labels_key` and
`unlabeled_category`, then `SCANVI(adata)`. There is no `predict_proba()` method;
`predict(soft=True)` returns class probabilities. Provide `labels_key` explicitly
when the source SCVI model was not registered with labels. Do not reuse a SCANVI
registry to initialize a different class without that class's setup.

SCVI defaults include `n_latent=10`, `n_hidden=128`, `n_layers=1`,
`dropout_rate=0.1`, `gene_likelihood='zinb'`, and `dispersion='gene'`.
Dispersion options include gene, gene-batch, gene-label and gene-cell; a gene-batch
parameter is not a cell-specific parameter. Choice of likelihood requires checking
the assay and fit, not simply counting zeros.

Embeddings are candidates for integration, not guaranteed batch-free biology.
Normalized expression is decoded model output and does not replace measured counts.
Evaluate annotation on held-out donors, label ontology consistency and absent
reference types; large class probabilities alone do not establish calibration.

## AUTOZI

```python
scvi.model.AUTOZI.setup_anndata(adata, layer="counts")
model = scvi.model.AUTOZI(adata)
model.train()
posterior_beta_parameters = model.get_alphas_betas()
```

AUTOZI assesses evidence for extra zero inflation under its count-mixture model.
`get_alphas_betas()` returns beta-distribution parameters, not a vector labeling
technical zeros or direct per-gene dropout probabilities. It does not determine
whether a particular observed zero is biological or technical.

## VELOVI

VELOVI requires **preprocessed continuous** spliced and unspliced abundance layers,
commonly scVelo moments `Ms` and `Mu`. Preserve original spliced/unspliced counts
and record filtering, normalization, neighborhood and scaling choices.

```python
scvi.external.VELOVI.setup_anndata(
    velocity_adata, spliced_layer="Ms", unspliced_layer="Mu",
)
velocity_model = scvi.external.VELOVI(velocity_adata)
velocity_model.train()
latent_time = velocity_model.get_latent_time()
velocities = velocity_model.get_velocity()
rates = velocity_model.get_rates()
```

This setup has no batch-covariate argument. Do not advertise generic batch-corrected
velocity. Latent time can be gene/cell-specific and is not observed chronological
time. Validate kinetic assumptions, phase portraits, direction uncertainty and
preprocessing sensitivity before interpreting a trajectory or causal transition.
Follow the official velocity tutorial when exporting rescaled values to scVelo;
raw model outputs are not an interchangeable velocity graph.

## ContrastiveVI

```python
import numpy as np

scvi.external.ContrastiveVI.setup_anndata(adata, layer="counts", batch_key="batch")
model = scvi.external.ContrastiveVI(
    adata, n_background_latent=10, n_salient_latent=10,
)
background_idx = np.flatnonzero(adata.obs["condition"].eq("control"))
target_idx = np.flatnonzero(adata.obs["condition"].eq("treated"))
assert len(background_idx) and len(target_idx)
model.train(background_indices=background_idx, target_indices=target_idx)
background = model.get_latent_representation(representation_kind="background")
salient = model.get_latent_representation(representation_kind="salient")
```

The salient latent variable models target-specific variation. Confounding between
condition, donor or technology can also enter that space; it does not isolate a
causal perturbation effect automatically.

## CellAssign

Use a **genes-by-cell-types** binary marker DataFrame. Match marker rows exactly
to the modeled gene order, and compute size factors from the full count library
before restricting to marker genes.

```python
import numpy as np
import pandas as pd

markers = pd.DataFrame({
    "CD4 T": [1, 1, 0, 0], "CD8 T": [1, 0, 1, 0], "B": [0, 0, 0, 1],
}, index=["CD3D", "CD4", "CD8A", "CD19"])
assert markers.index.isin(adata.var_names).all()
lib = np.asarray(adata.layers["counts"].sum(axis=1)).ravel()
assert (lib > 0).all()
adata.obs["size_factor"] = lib / lib.mean()
marker_adata = adata[:, markers.index].copy()
scvi.external.CellAssign.setup_anndata(
    marker_adata, layer="counts", size_factor_key="size_factor",
)
model = scvi.external.CellAssign(marker_adata, markers)
model.train()
probabilities = model.predict()
```

This tiny marker matrix illustrates orientation, not a validated annotation panel.
Marker absence, non-specific expression and missing reference types affect results.
`predict` returns soft assignments; select labels only after checking uncertainty.

## SOLO

```python
# rna_model must have been trained using only counts and optional batch_key.
solo = scvi.external.SOLO.from_scvi_model(rna_model, restrict_to_batch="capture1")
solo.train()
scores = solo.predict(soft=True, return_logits=False)
```

SOLO does not support extra categorical/continuous covariates in the source model.
Analyze separate captures appropriately: simulated cross-capture doublets are not
physical droplet doublets. `restrict_to_batch` must match a registered batch value.
Returned rows correspond to source-cell barcodes (simulated doublets are omitted by
default); align the index before writing into `.obs`, especially after restriction.
Probability thresholds and expected doublet rates require assay-specific validation.

## LinearSCVI and AmortizedLDA

```python
scvi.model.LinearSCVI.setup_anndata(adata, layer="counts", batch_key="batch")
linear = scvi.model.LinearSCVI(adata, n_latent=10)
linear.train()
loadings = linear.get_loadings()

scvi.model.AmortizedLDA.setup_anndata(adata, layer="counts")
lda = scvi.model.AmortizedLDA(adata, n_topics=10)
lda.train()
cell_topics = lda.get_latent_representation()
gene_topics = lda.get_feature_by_topic()
```

Linear decoder loadings and LDA topics can aid interpretation; assess stability and
gene enrichment rather than treating components as uniquely identified pathways.
AmortizedLDA does not inherit every SCVI normalization or covariate API.

Sources: [SCVI](https://docs.scvi-tools.org/en/stable/api/reference/scvi.model.SCVI.html),
[SCANVI](https://docs.scvi-tools.org/en/stable/api/reference/scvi.model.SCANVI.html),
[RNA prediction mixin](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/base/_training_mixin.py),
[AUTOZI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/_autozi.py),
[VELOVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/velovi/_model.py),
[ContrastiveVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/contrastivevi/_model.py),
[CellAssign](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/cellassign/_model.py),
[SOLO](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/solo/_model.py),
[LinearSCVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/_linear_scvi.py),
[AmortizedLDA](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/_amortizedlda.py).
