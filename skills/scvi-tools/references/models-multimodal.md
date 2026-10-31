# Multimodal integration and sample-aware RNA models

Targets scvi-tools 1.5.1. Examples are illustrative unless covered by the limited
synthetic checks recorded in SKILL.md. Verify cell/feature alignment and modality
measurement provenance before setup; missing measurements are not observed zeros.

## TOTALVI: CITE-seq RNA and antibody counts

Use raw RNA counts in a layer and raw protein counts in an `.obsm` DataFrame whose
index exactly matches `adata.obs_names`. Protein columns preserve antibody names.

```python
import scvi

scvi.model.TOTALVI.setup_anndata(
    adata, layer="counts", protein_expression_obsm_key="protein_expression",
    batch_key="batch",
)
model = scvi.model.TOTALVI(adata)
model.train()
adata.obsm["X_totalVI"] = model.get_latent_representation()
rna_normalized, protein_normalized = model.get_normalized_expression(
    n_samples=25, return_mean=True,
)
foreground_probability = model.get_protein_foreground_probability()
rna_de = model.differential_expression(
    groupby="cell_type", group1="T cells", group2="B cells",
    mode="change", use_field=["rna"],
)
protein_de = model.differential_expression(
    groupby="cell_type", group1="T cells", group2="B cells",
    mode="change", use_field=["protein"],
)
```

`get_normalized_expression()` returns a **tuple** `(RNA, protein)` and has no
`protein_expression` argument. `transform_batch` changes decoder conditioning;
it does not select the protein return. RNA library scaling and protein scaling
have distinct semantics (`library_size` versus `scale_protein`). Protein foreground
probability is a mixture probability, not protein abundance.

DE defaults to both modalities. In 1.5.1, `use_field=['rna']` or `['protein']`
selects one; protein feature names in the DE index receive a `_protein` suffix.
Do not compare antibody and gene effects without preserving those identities.

TOTALVI can integrate RNA-only cells or partially overlapping antibody panels using
its documented batch/panel missing-protein handling. Do not fabricate a zero-count
protein panel and interpret imputed values as measurements. Background is modeled
rather than simply subtracted. Validate imputation using held-out measured proteins
and batches with adequate reference overlap; no automatic benefit over RNA-only
clustering is guaranteed.

## TOTALANVI: partially labeled CITE-seq

```python
scanvi_total = scvi.external.TOTALANVI.from_totalvi_model(
    model, labels_key="cell_type", unlabeled_category="Unknown",
)
scanvi_total.train()
labels = scanvi_total.predict()
class_probabilities = scanvi_total.predict(soft=True)
```

Alternatively register with `TOTALANVI.setup_anndata` including the same count and
protein keys plus `labels_key`/`unlabeled_category`, then initialize it. The current
class also supports MuData. Missing cell types and label quality limit transfer;
validate on independent samples and allow unassigned query cells.

## MULTIVI: RNA, ATAC and optional protein modalities

Use `MULTIVI.setup_mudata`. The old `setup_anndata` is a deprecated no-op in
1.5.1, not a functioning alternative. The input must encode cells and modalities
as required by the model, not merely contain two arbitrary AnnData objects.

### Fully paired example

```python
from mudata import MuData

assert rna_adata.obs_names.equals(atac_adata.obs_names)
assert rna_adata.obs_names.is_unique
mdata = MuData({"rna": rna_adata, "atac": atac_adata})
# Explicit global batch metadata; do not rely on automatic obs-column pulling.
mdata.obs["batch"] = rna_adata.obs["batch"].reindex(mdata.obs_names)
scvi.model.MULTIVI.setup_mudata(
    mdata, rna_layer="counts", atac_layer="counts", batch_key="batch",
    modalities={"rna_layer": "rna", "atac_layer": "atac"},
)
model_multi = scvi.model.MULTIVI(mdata, n_latent=20, fully_paired=True)
model_multi.train()
mdata.obsm["X_multiVI"] = model_multi.get_latent_representation()
rna_estimates = model_multi.get_normalized_expression()
atac_estimates = model_multi.get_normalized_accessibility()
```

With MuData, `n_genes` and `n_regions` are inferred; they are not required constructor
arguments. `get_accessibility_estimates` is not the current method. Latent defaults
are data-dependent (`n_latent=None`), so specify a value when reproducibility matters.

### Partially paired inputs

Represent all cells in a common order in each registered modality, with absent
modality blocks zero-filled according to the upstream MultiVI workflow. Keep a
separate provenance column for measured RNA/ATAC; exclude true empty libraries
before zero-padding so that a failed assay is not mistaken for an unmeasured modality.
Maintain a common peak coordinate system/genome assembly and gene naming scheme.
Independent modalities with disjoint `obs_names` in MuData alone are not a complete
working setup for the required registration.

`scvi.data.organize_multiome_anndatas(multi_anndata, rna_anndata, atac_anndata)`
returns **one concatenated AnnData**, not a tuple of RNA and ATAC objects. It needs
a real multiome object (the source calls `.copy()` on it); `multi_anndata=None`
does not create a completely unpaired workflow. It has no `rna_indices_end`
argument. Features not in the multiome object are discarded. If using the helper,
do not use its unpaired-concatenation branch with AnnData 0.13.4: it calls
the removed `AnnData.concatenate` method and raises `AttributeError` (reproduced).
Construct the aligned zero-filled object explicitly with `anndata.concat` instead,
audit feature types and modality provenance, then split by reliable feature metadata
and register the aligned MuData. The fully paired example above was exercised
natively and does not call this helper.

Fully unpaired integration needs a carefully specified common feature/missingness
representation and adequate biological overlap. Evaluate held-out cross-modality
prediction rather than assuming the alignment is identifiable without anchors.

## MRVI: biological-sample variation

MRVI is a **single-modality RNA** model for multiple samples, not an RNA/ATAC
joint model. Its 1.5.1 implementation is PyTorch; JAX support was removed in 1.5.

```python
scvi.external.MRVI.setup_anndata(
    adata, layer="counts", sample_key="sample", batch_key="batch",
)
mrvi = scvi.external.MRVI(adata)
mrvi.train()
shared_latent = mrvi.get_latent_representation()
local_sample_repr = mrvi.get_local_sample_representation()
sample_distances = mrvi.get_local_sample_distances()
da_results = mrvi.differential_abundance(sample_cov_keys=["condition"])
```

Sample covariates must be constant within sample and the design must distinguish
technical batches from the biological contrast. Local sample representations and
distances can be large; subset cells or aggregate when warranted. DA returns an
xarray Dataset containing sample/covariate log probabilities. MRVI's separate
`differential_expression(sample_cov_keys=[...])` performs multivariate analysis
across sample-conditioned cell-state shifts; do not pass SCVI's `group1/group2`
arguments or interpret DA as gene DE.

## DIAGVI: two unpaired modalities

DIAGVI remains at `scvi.external.DIAGVI` in 1.5.1 but ongoing development moved to
scVIVA-tools. Its `setup_mudata(mdata, modalities=['rna', 'protein'], ...)` takes a
**list of two modality names**, unlike MULTIVI's argument-to-modality mapping.
Alternatively register each AnnData with `setup_anndata` and initialize with a
modality dictionary. The constructor accepts `guidance_graph` and/or `mapping_df`
for prior feature relationships. Install `scvi-tools[diagvi]` for `geomloss` and
`torch-geometric`. Choose modality-appropriate likelihoods and documented feature
relationships; arbitrary unpaired datasets cannot be assumed identifiable.
Follow the official workflow for graph construction and evaluation before training.

Sources: [TOTALVI source](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/_totalvi.py),
[TOTALANVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/totalanvi/_model.py),
[MULTIVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/_multivi.py),
[multiome helper](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/data/_preprocessing.py),
[MRVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/mrvi/_model.py),
[DIAGVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/diagvi/_model.py),
[DIAGVI maintenance](https://docs.scvi-tools.org/en/stable/user_guide/models/diagvi.html).
