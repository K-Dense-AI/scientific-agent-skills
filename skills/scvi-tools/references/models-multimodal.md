# Multimodal and Multi-omics Integration Models

This document covers models for joint analysis of multiple data modalities in scvi-tools.

## totalVI (Total Variational Inference)

**Purpose**: Joint analysis of CITE-seq data (simultaneous RNA and protein measurements from same cells).

**Key Features**:
- Jointly models gene expression and protein abundance
- Learns shared low-dimensional representations
- Enables protein imputation from RNA data
- Performs differential expression for both modalities
- Handles batch effects in both RNA and protein layers

**When to Use**:
- Analyzing CITE-seq or REAP-seq data
- Joint RNA + surface protein measurements
- Imputing missing proteins
- Integrating protein and RNA information
- Multi-batch CITE-seq integration

**Data Requirements**:
- AnnData with gene expression in `.X` or a layer
- Protein measurements in `.obsm["protein_expression"]`
- Same cells measured for both modalities

**Basic Usage**:
```python
import scvi

# Setup data - specify both RNA and protein layers
scvi.model.TOTALVI.setup_anndata(
    adata,
    layer="counts",  # RNA counts
    protein_expression_obsm_key="protein_expression",  # Protein counts
    batch_key="batch"
)

# Train model
model = scvi.model.TOTALVI(adata)
model.train()

# Get joint latent representation
latent = model.get_latent_representation()

# Get normalized values for both modalities
rna_normalized = model.get_normalized_expression()
protein_normalized = model.get_normalized_expression(
    transform_batch="batch1",
    protein_expression=True
)

# Differential expression (works for both RNA and protein)
rna_de = model.differential_expression(groupby="cell_type")
protein_de = model.differential_expression(
    groupby="cell_type",
    protein_expression=True
)
```

**Key Parameters**:
- `n_latent`: Latent space dimensionality (default: 20)
- `n_layers_encoder`: Number of encoder layers (default: 1)
- `n_layers_decoder`: Number of decoder layers (default: 1)
- `protein_dispersion`: Protein dispersion handling ("protein" or "protein-batch")
- `empirical_protein_background_prior`: Use empirical background for proteins

**Advanced Features**:

**Protein Imputation**:
```python
# Impute missing proteins for RNA-only cells
# (useful for mapping RNA-seq to CITE-seq reference)
protein_foreground = model.get_protein_foreground_probability()
imputed_proteins = model.get_normalized_expression(
    protein_expression=True,
    n_samples=25
)
```

**Denoising**:
```python
# Get denoised counts for both modalities
denoised_rna = model.get_normalized_expression(n_samples=25)
denoised_protein = model.get_normalized_expression(
    protein_expression=True,
    n_samples=25
)
```

**Best Practices**:
1. Use empirical protein background prior for datasets with ambient protein
2. Consider protein-specific dispersion for heterogeneous protein data
3. Use joint latent space for clustering (better than RNA alone)
4. Validate protein imputation with known markers
5. Check protein QC metrics before training

## totalANVI (Semi-supervised CITE-seq)

**Purpose**: The semi-supervised counterpart to totalVI -- joint RNA + protein
modeling that also propagates cell-type labels (totalVI is to scVI as totalANVI
is to scANVI). Lives in `scvi.external`.

**When to Use**:
- CITE-seq integration where some cells are labeled and you want annotation transfer
- Query-to-reference mapping on CITE-seq data

**Basic Usage**:
```python
scvi.external.TOTALANVI.setup_anndata(
    adata,
    protein_expression_obsm_key="protein_expression",
    batch_key="batch",
    labels_key="cell_type",
    unlabeled_category="Unknown",
)
model = scvi.external.TOTALANVI(adata)
model.train()
predictions = model.predict()  # cell-type predictions
```

## DIAGVI (Diagonal Integration of Unpaired Data)

**Purpose**: Integrate unpaired single-cell datasets (diagonal integration --
datasets that do not share the same feature space or paired cells). Added in
scvi-tools 1.4.3; lives in `scvi.external`. Consult the
[scvi-tools API](https://docs.scvi-tools.org/en/stable/api/index.html) for the
current setup signature, then follow the standard
`setup -> train -> get_latent_representation` workflow.

## MultiVI (Multi-modal Variational Inference)

**Purpose**: Integration of paired and unpaired multi-omic data (e.g., RNA + ATAC, paired and unpaired cells).

**Key Features**:
- Handles paired data (same cells) and unpaired data (different cells)
- Integrates multiple modalities: RNA, ATAC, proteins, etc.
- Missing modality imputation
- Learns shared representations across modalities
- Flexible integration strategy

**When to Use**:
- 10x Multiome data (paired RNA + ATAC)
- Integrating separate RNA-seq and ATAC-seq experiments
- Some cells with both modalities, some with only one
- Cross-modality imputation tasks

**Data Requirements**:
- A `MuData` object with one modality per `.mod` (e.g. `"rna"`, `"atac"`, optional `"protein"`)
- Can handle:
  - All cells with both modalities (fully paired)
  - Mix of paired and unpaired cells
  - Completely unpaired datasets

> **Breaking change (v1.3):** `MULTIVI.setup_anndata` was removed. Configure the
> model from a `MuData` object via `setup_mudata`. For a single concatenated
> multiome matrix, split it into per-modality AnnData with
> `scvi.data.organize_multiome_anndatas` first.

**Basic Usage**:
```python
import scvi
from mudata import MuData

# rna_adata: gene-expression counts; atac_adata: peak/region counts.
# For a concatenated multiome matrix, split it first:
#   rna_adata, atac_adata = scvi.data.organize_multiome_anndatas(
#       multiome_adata, rna_indices_end=n_genes
#   )
mdata = MuData({"rna": rna_adata, "atac": atac_adata})

# Configure from the MuData object (modalities maps model args -> mod keys)
scvi.model.MULTIVI.setup_mudata(
    mdata,
    batch_key="batch",
    modalities={"rna_layer": "rna", "atac_layer": "atac"},
)

model = scvi.model.MULTIVI(
    mdata,
    n_genes=rna_adata.n_vars,
    n_regions=atac_adata.n_vars,
)
model.train()

# Get joint latent representation
mdata.obsm["X_multiVI"] = model.get_latent_representation()

# Get normalized expression / accessibility
rna_normalized = model.get_normalized_expression()
atac_normalized = model.get_accessibility_estimates()
```

**Key Parameters**:
- `n_genes`: Number of gene features (required)
- `n_regions`: Number of accessibility regions (required)
- `n_latent`: Latent dimensionality (default: 20)

**Integration Scenarios** (handled by how you build the MuData / organize inputs):

**Scenario 1: Fully Paired (10x Multiome)**:
```python
# Every cell measured in both modalities -- the two .mod objects share obs_names
mdata = MuData({"rna": rna_adata, "atac": atac_adata})
```

**Scenario 2 & 3: Partially or Completely Unpaired**:
```python
# Combine a paired multiome matrix with RNA-only and/or ATAC-only experiments.
# organize_multiome_anndatas pads missing features and tracks per-cell modality.
joint = scvi.data.organize_multiome_anndatas(
    multi_anndata=paired_multiome_adata,  # cells with both modalities (or None)
    rna_anndata=rna_only_adata,           # expression-only cells (optional)
    atac_anndata=atac_only_adata,         # accessibility-only cells (optional)
)
```

**Advanced Use Cases**:

**Cross-Modality Prediction**:
```python
# Predict peaks from gene expression
accessibility_from_rna = model.get_accessibility_estimates(
    indices=rna_only_cells
)

# Predict genes from accessibility
expression_from_atac = model.get_normalized_expression(
    indices=atac_only_cells
)
```

**Modality-Specific Analysis**:
```python
# Each modality is accessible as its own AnnData on the MuData object
rna_subset = mdata.mod["rna"]
atac_subset = mdata.mod["atac"]
```

## MrVI (Multi-resolution Variational Inference)

**Purpose**: Multi-sample analysis accounting for sample-specific and shared variation.

**Key Features**:
- Simultaneously analyzes multiple samples/conditions
- Decomposes variation into:
  - Shared variation (common across samples)
  - Sample-specific variation
- Enables sample-level comparisons
- Identifies sample-specific cell states

**When to Use**:
- Comparing multiple biological samples or conditions
- Identifying sample-specific vs. shared cell states
- Disease vs. healthy sample comparisons
- Understanding inter-sample heterogeneity
- Multi-donor studies

**Basic Usage** (MrVI lives in `scvi.external`; the default backend is now PyTorch):
```python
scvi.external.MRVI.setup_anndata(
    adata,
    batch_key="batch",
    sample_key="sample",  # Critical: defines biological samples
)

model = scvi.external.MRVI(adata)
model.train()

# Cell-state (u) representation, shared across samples
shared_latent = model.get_latent_representation()

# Per-cell, sample-resolved representation and sample-sample distances
local_sample_repr = model.get_local_sample_representation()
sample_distances = model.get_local_sample_distances()
```

**Key Parameters**:
- `sample_key`: Column in `adata.obs` defining biological samples (required)
- `batch_key`: Technical batch covariate
- `n_latent` / `n_latent_u`: Dimensionalities of the cell-state and sample-aware latent spaces

**Analysis Workflow**:
```python
# 1. Identify shared cell states across samples
adata.obsm["X_MrVI"] = model.get_latent_representation()
sc.pp.neighbors(adata, use_rep="X_MrVI")
sc.tl.umap(adata)
sc.tl.leiden(adata, key_added="shared_clusters")

# 2. Sample-resolved representation and pairwise sample distances
local_sample_repr = model.get_local_sample_representation()
distances = model.get_local_sample_distances()

# 3. Test how a sample covariate shifts abundance / expression
de_results = model.differential_abundance(sample_cov_keys=["condition"])
```

**Use Cases**:
- **Multi-donor studies**: Separate donor effects from cell type variation
- **Disease studies**: Identify disease-specific vs. shared biology
- **Time series**: Separate temporal from stable variation
- **Batch + biology**: Disentangle technical and biological variation

## totalVI vs. MultiVI vs. MrVI: When to Use Which?

### totalVI
**Use for**: CITE-seq (RNA + protein, same cells)
- Paired measurements
- Single modality type per feature
- Focus: protein imputation, joint analysis

### MultiVI
**Use for**: Multiple modalities (RNA + ATAC, etc.)
- Paired, unpaired, or mixed
- Different feature types
- Focus: cross-modality integration and imputation

### MrVI
**Use for**: Multi-sample RNA-seq
- Single modality (RNA)
- Multiple biological samples
- Focus: sample-level variation decomposition

## Integration Best Practices

### For CITE-seq (totalVI)
1. **Quality control proteins**: Remove low-quality antibodies
2. **Background subtraction**: Use empirical background prior
3. **Joint clustering**: Use joint latent space, not RNA alone
4. **Validation**: Check known markers in both modalities

### For Multiome/Multi-modal (MultiVI)
1. **Feature filtering**: Filter genes and peaks independently
2. **Balance modalities**: Ensure reasonable representation of each
3. **Modality weights**: Consider if one modality dominates
4. **Imputation validation**: Validate imputed values carefully

### For Multi-sample (MrVI)
1. **Sample definition**: Carefully define biological samples
2. **Sample size**: Need sufficient cells per sample
3. **Covariate handling**: Properly account for batch vs. sample
4. **Interpretation**: Distinguish technical from biological variation

## Complete Example: CITE-seq Analysis with totalVI

```python
import scvi
import scanpy as sc

# 1. Load CITE-seq data
adata = sc.read_h5ad("cite_seq.h5ad")

# 2. QC and filtering
sc.pp.filter_genes(adata, min_cells=3)
sc.pp.highly_variable_genes(adata, n_top_genes=4000)

# Protein QC
protein_counts = adata.obsm["protein_expression"]
# Remove low-quality proteins

# 3. Setup totalVI
scvi.model.TOTALVI.setup_anndata(
    adata,
    layer="counts",
    protein_expression_obsm_key="protein_expression",
    batch_key="batch"
)

# 4. Train
model = scvi.model.TOTALVI(adata, n_latent=20)
model.train(max_epochs=400)

# 5. Extract joint representation
latent = model.get_latent_representation()
adata.obsm["X_totalVI"] = latent

# 6. Clustering on joint space
sc.pp.neighbors(adata, use_rep="X_totalVI")
sc.tl.umap(adata)
sc.tl.leiden(adata, resolution=0.5)

# 7. Differential expression for both modalities
rna_de = model.differential_expression(
    groupby="leiden",
    group1="0",
    group2="1"
)

protein_de = model.differential_expression(
    groupby="leiden",
    group1="0",
    group2="1",
    protein_expression=True
)

# 8. Save model
model.save("totalvi_model")
```
