# Methylation, cytometry, system integration and trajectories

Targets scvi-tools 1.5.1. Specialized examples are illustrative and source-verified;
see SKILL.md for the narrower set of native synthetic checks performed.

## METHYLVI and METHYLANVI

Both models require **MuData**. Their `setup_anndata` methods raise
`NotImplementedError`. Each methylation context (for example `mCG`, `mCH`) is a
modality containing a cells-by-regions matrix with two layers: methylated cytosine
counts and total coverage counts. Require integer `0 <= mc <= cov`, shared cell
order and unique region IDs. Zero coverage means no observation, not an observed
unmethylated region; methylation ratios cannot replace the two count arrays.

```python
import scvi
from mudata import MuData

# mcg_adata.layers['mc'] and ['cov'] have already been validated.
mdata = MuData({"mCG": mcg_adata})
mdata.obs["batch"] = mcg_adata.obs["batch"].reindex(mdata.obs_names)
scvi.external.METHYLVI.setup_mudata(
    mdata, mc_layer="mc", cov_layer="cov",
    methylation_contexts=["mCG"], batch_key="batch",
)
methylvi = scvi.external.METHYLVI(mdata)
methylvi.train()
mdata.obsm["X_MethylVI"] = methylvi.get_latent_representation()
methylation_by_context = methylvi.get_normalized_methylation()
mcg_estimates = methylvi.get_normalized_methylation(context="mCG")
```

The first methylation result is a dictionary keyed by context; specifying `context`
returns that context's array/DataFrame. Region/coverage QC must use coverage,
not the number of methylated counts, or it preferentially removes hypomethylated
regions. Default likelihood is beta-binomial; binomial is also supported. The
relevant dispersion setting is `region`/`region-cell`, not `region_factors`.

```python
# Use a separate prepared MuData object for the semi-supervised example.
scvi.external.METHYLANVI.setup_mudata(
    labeled_mdata, mc_layer="mc", cov_layer="cov",
    methylation_contexts=["mCG"], labels_key="cell_type",
    unlabeled_category="Unknown", batch_key="batch",
)
methylanvi = scvi.external.METHYLANVI(labeled_mdata)
methylanvi.train()
labels = methylanvi.predict()
probabilities = methylanvi.predict(soft=True)
```

Put label/batch columns in global `mdata.obs`, or explicitly map those arguments
to the modality holding them through `modalities`. For a fitted methylation model,
`differential_methylation(groupby=..., group1=..., group2=..., mode='change')`
returns context-specific results and uses methylation differences, not RNA LFCs.
Annotation and region tests require independent validation and biological replicates.

## CYTOVI

CYTOVI registers transformed cytometry intensities from `.X` or `layer`, not a
TOTALVI-style `protein_expression_obsm_key`. Apply compensation/unmixing, instrument
QC and an assay-appropriate transform (for example arcsinh with a recorded cofactor)
before modeling. Default normal likelihood accepts transformed continuous values;
beta likelihood requires suitable bounded values and care at distribution boundaries.

```python
scvi.external.CYTOVI.setup_anndata(
    cyto_adata, layer="transformed", batch_key="batch", sample_key="sample",
)
cyto = scvi.external.CYTOVI(cyto_adata, protein_likelihood="normal")
cyto.train()
cyto_adata.obsm["X_CytoVI"] = cyto.get_latent_representation()
corrected_intensities = cyto.get_normalized_expression()
```

Partially overlapping panels need measurement masks, shared markers and appropriate
controls. Use the documented `scvi.external.cytovi` preprocessing utilities;
do not treat missing panel markers as measured zeros. Version 1.5.1 fixes a beta
likelihood NaN issue for merged masked panels. Assess retained biological signal
and agreement in control samples, not batch mixing alone.

## SysVI

SysVI is intended for substantial cross-system effects (for example protocol or
model-system differences). It models approximately normal inputs, commonly
library-normalized and log1p-transformed RNA, rather than raw RNA counts.

```python
import scanpy as sc

# sys_adata starts with measured counts; preserve before transforming.
sys_adata.layers["counts"] = sys_adata.X.copy()
sc.pp.normalize_total(sys_adata, target_sum=1e4)
sc.pp.log1p(sys_adata)
sys_adata.layers["log_normalized"] = sys_adata.X.copy()
scvi.external.SysVI.setup_anndata(
    sys_adata, layer="log_normalized", batch_key="system",
)
sysvi = scvi.external.SysVI(sys_adata)
sysvi.train()
sys_adata.obsm["X_SysVI"] = sysvi.get_latent_representation()
```

Tune cycle-consistency strength with biological-preservation checks and seeds;
more correction is not always better. A system covariate is treated differently
from auxiliary covariates. Gene orthology and shared feature definitions require
explicit decisions for cross-species data. SysVI is not a guarantee that confounded
or nonoverlapping biological states can be aligned safely.

## Decipher

```python
scvi.external.Decipher.setup_anndata(adata, layer="counts")
decipher = scvi.external.Decipher(adata)
decipher.train()
adata.obsm["X_decipher"] = decipher.get_latent_representation()
```

Decipher learns its own low-dimensional representation from counts. It does not
consume an SCVI embedding as the same input, and fitting alone does not return
validated pseudotime. Its trajectory utilities require a specified trajectory
and cluster annotation; evaluate alternative roots/branches and independent time
or lineage evidence. UMAP on its latent representation is a visualization, not a
trajectory inference validation.

SOLO, CellAssign and AmortizedLDA are covered in
[models-scrna-seq.md](models-scrna-seq.md); reference mapping is in
[workflows.md](workflows.md). Separate models' latent coordinates are not directly
comparable across assays without a justified correspondence or integration method.

Sources: [METHYLVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/methylvi/_methylvi_model.py),
[METHYLANVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/methylvi/_methylanvi_model.py),
[methylation outputs](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/methylvi/_base_components.py),
[CYTOVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/cytovi/_model.py),
[cytometry assumptions](https://github.com/scverse/scvi-tools/blob/1.5.1/docs/user_guide/models/cytovi.md),
[SysVI](https://github.com/scverse/scvi-tools/blob/1.5.1/docs/user_guide/models/sysvi.md),
[Decipher](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/decipher/_model.py).
