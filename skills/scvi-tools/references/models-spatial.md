# Spatial models: scvi-tools 1.5.1 compatibility workflows

Upstream moved ongoing maintenance of DestVI, Stereoscope, Tangram, GIMVI, SCVIVA,
RESOLVI and DIAGVI to [scVIVA-tools](https://scviva-tools.readthedocs.io/en/latest/)
starting with scvi-tools 1.5. The classes below remain in 1.5.1; these source-verified
examples support existing pinned workflows and were not biologically validated.
For new spatial analyses, check the companion package's current API rather than
assuming these namespaces will persist. No spatial model fitting was executed in
this refresh.

## Shared preparation

Keep measured counts for count-based spatial models, unique gene IDs, cell/spot
IDs, spatial coordinates and slide/library metadata. Align reference and spatial
genes **before** training a reference that will be transferred. Merely having some
gene overlap is insufficient when a method expects identical columns.

```python
# sc_adata and spatial_adata already contain measured layers['counts'].
assert sc_adata.var_names.is_unique and spatial_adata.var_names.is_unique
shared = sc_adata.var_names[sc_adata.var_names.isin(spatial_adata.var_names)]
assert len(shared) > 0
sc_adata = sc_adata[:, shared].copy()
spatial_adata = spatial_adata[:, shared].copy()
assert sc_adata.var_names.equals(spatial_adata.var_names)
```

Choose informative shared genes and check reference cell types/assays and spatial
QC, not just a nonzero overlap count. Load spatial data with the current reader for
the assay; preserve coordinates and image scale metadata. Do not assume a Visium
reader creates a `counts` layer. Independent slides need separate spatial neighborhoods.

## CondSCVI to DestVI

```python
from scvi.model import CondSCVI, DestVI

CondSCVI.setup_anndata(sc_adata, layer="counts", labels_key="cell_type")
reference = CondSCVI(sc_adata, weight_obs=False)
reference.train(max_epochs=300)
DestVI.setup_anndata(spatial_adata, layer="counts")
destvi = DestVI.from_rna_model(spatial_adata, reference)
destvi.train(max_epochs=2500)
proportions = destvi.get_proportions()  # spots-by-cell-types DataFrame
spatial_adata.obsm["proportions"] = proportions
for cell_type in proportions.columns:
    spatial_adata.obs[f"prop_{cell_type}"] = proportions[cell_type]
cell_type_expression = destvi.get_scale_for_ct("T cells")
```

DestVI requires a labeled **CondSCVI**, not SCVI, reference. The example's epoch
counts are starting configurations, not convergence guarantees. Inspect reference
fit and abundance support, sensitivity to cell-type granularity, and tissue markers.
`get_gamma()` exposes within-type latent variables; it is not a matrix of gene
scaling factors. DataFrame outputs use label/`.iloc` indexing, not `[:, i]`.

The base model does not automatically use a spatial-neighbor prior simply because
coordinates are present. Cell proportions are model estimates, not direct cell counts
or proof that every reference type is present in every spot. Infer within-type
expression only where that type is supported.

## Stereoscope

```python
from scvi.external import RNAStereoscope, SpatialStereoscope

RNAStereoscope.setup_anndata(sc_adata, labels_key="cell_type", layer="counts")
rna = RNAStereoscope(sc_adata)
rna.train(max_epochs=100)
SpatialStereoscope.setup_anndata(spatial_adata, layer="counts")
spatial = SpatialStereoscope.from_rna_model(spatial_adata, rna)
spatial.train(max_epochs=2000)
proportions = spatial.get_proportions()
```

Both datasets need aligned shared genes. Compare reference adequacy and held-out
markers; there is no universal guarantee that this workflow is faster or more
accurate than DestVI on a new assay.

## Tangram

The 1.5.1 wrapper is PyTorch, uses **MuData**, and optimizes a cell-to-location
mapping. It is not a generic optimal-transport API. Its projection methods differ
from the standalone `tangram-sc` package, so do not mix their signatures.

```python
from mudata import MuData
from scvi.external import Tangram

# sc_mapping and sp_mapping have identical selected genes/order and
# appropriately processed expression for Tangram (not a count likelihood).
assert sc_mapping.var_names.equals(sp_mapping.var_names)
map_data = MuData({"sc": sc_mapping, "sp": sp_mapping})
Tangram.setup_mudata(
    map_data, density_prior_key=None,
    modalities={"sc_layer": "sc", "sp_layer": "sp", "density_prior_key": "sp"},
)
tangram = Tangram(map_data)
tangram.train()
mapper = tangram.get_mapper_matrix()
projected_types = Tangram.project_cell_annotations(
    sc_mapping, sp_mapping, mapper, sc_mapping.obs["cell_type"],
)
projected_genes = Tangram.project_genes(sc_mapping, sp_mapping, mapper)
```

This explicit example omits a density prior. To use one, create a correctly normalized
spatial `.obs` column and pass its key; the default string alone is not a computed
prior. The 1.5.1 implementation's feature-equality guard is ineffective (it tests a
one-element tuple), so the explicit assertion is necessary. Tangram densifies its
registered matrices and is not minibatched; estimate memory before fitting.
Projection results are predictions, not observed expression or exact cell locations.
Validate with held-out genes and spatial controls, and preserve the mapping's cell
and spot order when projecting full-feature objects.

## GIMVI

```python
import scvi

scvi.external.GIMVI.setup_anndata(sc_adata, layer="counts")
scvi.external.GIMVI.setup_anndata(spatial_panel_adata, layer="counts")
gimvi = scvi.external.GIMVI(sc_adata, spatial_panel_adata)
gimvi.train()
sc_latent, spatial_latent = gimvi.get_latent_representation()
_, imputed_spatial = gimvi.get_imputed_values(normalized=True)
```

Unlike DestVI, GIMVI can use a spatial feature subset to predict unmeasured genes;
each spatial gene must be identifiable in the sequencing feature space. Preserve
full RNA features and gene mapping rather than reducing both matrices blindly to
the measured spatial panel. Evaluate imputation on held-out measured genes and do
not use imputed values as independent experimental validation.

## SCVIVA

The preprocessing method is named `preprocessing_anndata`, not
`preprocess_anndata`. It needs labels, coordinates, sample membership and an
expression embedding before neighborhood construction.

```python
# spatial_adata.obsm['X_scVI'] already contains an expression embedding.
# Each sample has enough cells for the selected neighbor count.
scvi.external.SCVIVA.preprocessing_anndata(
    spatial_adata, sample_key="sample", labels_key="cell_type",
    cell_coordinates_key="spatial", expression_embedding_key="X_scVI",
    k_nn=20,
)
scvi.external.SCVIVA.setup_anndata(
    spatial_adata, layer="counts", sample_key="sample", labels_key="cell_type",
    cell_coordinates_key="spatial", expression_embedding_key="X_scVI",
)
scviva = scvi.external.SCVIVA(spatial_adata)
scviva.train()
spatial_adata.obsm["X_scVIVA"] = scviva.get_latent_representation()
```

Keep sample boundaries and coordinate units explicit; do not connect separate slides
in a common numerical coordinate plane. Neighborhood effects are associations,
not evidence of cell-cell causal signaling. Test robustness to neighborhood size,
label uncertainty and tissue coverage.

## RESOLVI

RESOLVI models expression contamination/background and misassignment in
single-cell-resolution spatial assays. It is not a general multiscale resolution
converter or a generic substitute for spot deconvolution.

```python
scvi.external.RESOLVI.setup_anndata(
    spatial_adata, layer="counts", batch_key="slide",
    prepare_data_kwargs={"spatial_rep": "spatial", "n_neighbors": 10},
)
resolvi = scvi.external.RESOLVI(spatial_adata)
resolvi.train()
corrected_expression = resolvi.get_normalized_expression()
```

Setup prepares spatial neighbors by default. Supply the actual coordinate key:
its internal default is `X_spatial`, whereas many readers use `spatial`. There must
be enough cells within each slide for the requested neighborhood. Its validation
split support differs from SCVI; 1.5 raises errors for unsupported validation settings.
Assess contamination assumptions and rare-cell preservation using external controls.

For plotting proportions, put named columns in `.obs` and use the appropriate
spatial plotting API with correct image/coordinate scaling. Do not pass a Series
as a `color` key or treat spatial autocorrelation of inferred proportions as
independent confirmation of the same model.

Sources: [spatial maintenance](https://github.com/scverse/scvi-tools/blob/1.5.1/docs/user_guide/models/destvi.md),
[DestVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/_destvi.py),
[Stereoscope](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/stereoscope/_model.py),
[Tangram](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/tangram/_model.py),
[GIMVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/gimvi/_model.py),
[SCVIVA](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/scviva/_model.py),
[RESOLVI](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/external/resolvi/_model.py).
