# Core Workflow Patterns

Reviewed against Census 1.18.0, TileDB-SOMA 2.3.0, and the 2025-11-08 LTS.
Snippets share an open `census` context unless shown otherwise. Large cohort,
model-training, and downstream analysis blocks are illustrative: first inspect
metadata and size, restrict datasets/genes, and supply the named callbacks/model.
API and sparse-statistics contracts were exercised on a small local SOMA fixture;
a 10-cell/3-gene slice and metadata were also read from the public LTS.


The eight patterns in full, with code: opening the Census, exploring Census information,
querying expression data at small to medium scale, large-scale out-of-core queries,
machine learning with PyTorch, spatial Census data, Scanpy integration, and
multi-dataset integration.

## Core Workflow Patterns

### 1. Opening the Census

Always use the context manager to ensure proper resource cleanup:

```python
import cellxgene_census

# Resolve a moving alias once, then record the concrete build
build = cellxgene_census.get_census_version_description("stable")["release_build"]
with cellxgene_census.open_soma(census_version=build) as census:
    print(build, list(census["census_data"]))

# Open the reviewed LTS version for reproducibility
with cellxgene_census.open_soma(census_version="2025-11-08") as census:
    print(list(census["census_data"]))
```

**Key points:**
- Use context manager (`with` statement) for automatic cleanup
- Specify `census_version` for reproducible analyses
- `stable` opens the current LTS Census release; `latest` opens the newest weekly release retained for a shorter period

### 2. Exploring Census Information

Before querying expression data, explore available datasets and metadata.

**Access summary information:**
```python
# Get summary statistics as label/value rows
summary = census["census_info"]["summary"].read().concat().to_pandas()
summary_values = summary.set_index("label")["value"]
print(f"Total cells: {int(summary_values['total_cell_count']):,}")
print(f"Unique cells: {int(summary_values['unique_cell_count']):,}")

# Get all datasets
datasets = census["census_info"]["datasets"].read().concat().to_pandas()

# Get precomputed counts by organism, cell type, tissue, disease, and assay
summary_counts = census["census_info"]["summary_cell_counts"].read().concat().to_pandas()
tissue_counts = summary_counts[summary_counts["category"].eq("tissue_general")]
```

**Query cell metadata to understand available data:**
```python
# Get unique cell types in a tissue
cell_metadata = cellxgene_census.get_obs(
    census,
    "homo_sapiens",
    value_filter="tissue_general == 'brain' and is_primary_data == True",
    column_names=["cell_type"]
)
unique_cell_types = cell_metadata["cell_type"].unique()
print(f"Found {len(unique_cell_types)} cell types in brain")

# Count cells by tissue
tissue_metadata = cellxgene_census.get_obs(
    census,
    "homo_sapiens",
    value_filter="is_primary_data == True",
    column_names=["tissue_general"],
)
tissue_counts = tissue_metadata["tissue_general"].value_counts()
```

**Important:** Always filter for `is_primary_data == True` to avoid counting duplicate cells unless specifically analyzing duplicates.

### 3. Querying Expression Data (Small to Medium Scale)

For slices whose expression, metadata, and downstream copies fit in memory, use `get_anndata()`:

```python
# Basic query with cell type and tissue filters
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",  # or "Mus musculus"
    obs_value_filter="cell_type == 'B cell' and tissue_general == 'lung' and is_primary_data == True",
    obs_column_names=["assay", "disease", "sex", "donor_id"],
)

# Query specific genes with multiple filters
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    var_value_filter="feature_name in ['CD4', 'CD8A', 'CD19', 'FOXP3']",
    obs_value_filter="cell_type == 'T cell' and disease == 'COVID-19' and is_primary_data == True",
    obs_column_names=["cell_type", "tissue_general", "donor_id"],
)
```

**Filter syntax:**
- Use `obs_value_filter` for cell filtering
- Use `var_value_filter` for gene filtering
- Combine conditions with `and`, `or`
- Use `in` for multiple values: `tissue in ['lung', 'liver']`
- Select only needed columns with `obs_column_names`
- In current LTS releases, `disease` and `disease_ontology_term_id` may contain ` || `-delimited multiple values; inspect available values before relying on exact equality filters for disease cohorts

**Getting metadata separately:**
```python
# Query cell metadata
cell_metadata = cellxgene_census.get_obs(
    census, "homo_sapiens",
    value_filter="disease == 'COVID-19' and is_primary_data == True",
    column_names=["cell_type", "tissue_general", "donor_id"]
)

# Query gene metadata
gene_metadata = cellxgene_census.get_var(
    census, "homo_sapiens",
    value_filter="feature_name in ['CD4', 'CD8A']",
    column_names=["feature_id", "feature_name", "feature_length"]
)
```

### 4. Large-Scale Queries (Out-of-Core Processing)

For queries exceeding available RAM, use `axis_query()` with iterative processing:

```python
import tiledbsoma as soma

# Create axis query
with census["census_data"]["homo_sapiens"].axis_query(
    measurement_name="RNA",
    obs_query=soma.AxisQuery(
        value_filter="tissue_general == 'brain' and is_primary_data == True"
    ),
    var_query=soma.AxisQuery(
        value_filter="feature_name in ['FOXP2', 'TBR1', 'SATB2']"
    ),
) as query:
    # Iterate through expression matrix in chunks
    iterator = query.X("raw").tables()
    for batch in iterator:
        # batch is a pyarrow.Table with columns:
        # - soma_data: expression value
        # - soma_dim_0: cell (obs) coordinate
        # - soma_dim_1: gene (var) coordinate
        process_batch(batch)
```

**Computing incremental statistics:**

Use the tested per-gene `mean_variance(..., nnz_only=False)` workflow in
[common_patterns.md](common_patterns.md). Sparse tables contain stored entries,
so averaging their values silently excludes zeros. Also exclude datasets that did
not measure a gene; missing measurements are not biological zero expression.

### 5. Machine Learning with PyTorch

For training models, use TileDB-SOMA-ML. The former `cellxgene_census.experimental.ml` PyTorch loaders are absent from 1.18.0.

```python
import tiledbsoma as soma
import torch
from tiledbsoma_ml import ExperimentDataset, experiment_dataloader

with cellxgene_census.open_soma(census_version="2025-11-08") as census:
    experiment = census["census_data"]["homo_sapiens"]
    with experiment.axis_query(
        measurement_name="RNA",
        obs_query=soma.AxisQuery(
            value_filter="tissue_general == 'liver' and is_primary_data == True"
        ),
    ) as query:
        dataset = ExperimentDataset(
            query=query,
            layer_name="raw",
            obs_column_names=["cell_type"],
            batch_size=128,
            shuffle=True,
        )
        dataloader = experiment_dataloader(dataset)

        # Illustrative: fit label_to_id on training metadata; supply model,
        # criterion, optimizer, and num_epochs for the intended task.
        # Training loop
        for epoch in range(num_epochs):
            dataset.set_epoch(epoch)
            for X, obs in dataloader:
                encoded = obs["cell_type"].astype(str).map(label_to_id)
                if encoded.isna().any():
                    raise ValueError("Unseen cell type in training batch")
                labels = torch.as_tensor(encoded.to_numpy(), dtype=torch.long)

                # Forward pass (default loader emits NumPy X)
                outputs = model(torch.as_tensor(X, dtype=torch.float32))
                loss = criterion(outputs, labels)

                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
```

**Train/test splitting:**
```python
train_dataset, test_dataset = dataset.random_split(0.8, 0.2, seed=42)
train_loader = experiment_dataloader(train_dataset, num_workers=0)
test_loader = experiment_dataloader(test_dataset, num_workers=0)
```

The split block belongs inside the open query context. Cell-level random splits
do not test generalization to unseen donors/studies. Keep a fixed training label
vocabulary; use donor/study holdouts for that evaluation.

Use `batch_size` and `shuffle` on `ExperimentDataset`, not on `torch.utils.data.DataLoader`; `experiment_dataloader()` rejects DataLoader-level `batch_size`, `shuffle`, `sampler`, and `batch_sampler` arguments.

### 6. Spatial Census Data

Spatial data is available for supported Census releases in a separate `census_spatial_sequencing` collection. Use the spatial extra and a current TileDB-SOMA version when querying Visium or Slide-seq V2 data:

```python
import cellxgene_census
import tiledbsoma as soma

with cellxgene_census.open_soma(census_version="2025-11-08") as census:
    spatial_experiment = census["census_spatial_sequencing"]["homo_sapiens"]
    with spatial_experiment.axis_query(
        measurement_name="RNA",
        obs_query=soma.AxisQuery(
            value_filter="dataset_id == '4cceac62-9513-42a4-90e5-2878dbb0192c'"
        ),
    ) as query:
        sdata = query.to_spatialdata(X_name="raw")
```

### 7. Integration with Scanpy

Seamlessly integrate Census data with scanpy workflows:

```python
import scanpy as sc

# Load data from Census
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    obs_value_filter="cell_type == 'neuron' and tissue_general == 'brain' and is_primary_data == True",
)

# Standard scanpy workflow
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)

# Dimensionality reduction
sc.pp.pca(adata, n_comps=50)
sc.pp.neighbors(adata)
sc.tl.umap(adata)

# Visualization
sc.pl.umap(adata, color=["cell_type", "tissue", "disease"])
```

### 8. Multi-Dataset Integration

Query and integrate multiple datasets:

```python
# Strategy 1: Query multiple tissues separately
tissues = ["lung", "liver", "kidney"]
adatas = []

for tissue in tissues:
    adata = cellxgene_census.get_anndata(
        census=census,
        organism="Homo sapiens",
        obs_value_filter=f"tissue_general == '{tissue}' and is_primary_data == True",
    )
    adata.obs["query_tissue"] = tissue
    adatas.append(adata)

# Concatenate with AnnData's current API
import anndata as ad
for adata in adatas:
    adata.var_names = adata.var["feature_id"].astype(str)
combined = ad.concat(adatas, label="query_tissue", keys=tissues, join="inner")
# Concatenation preserves batches; it does not correct batch effects.

# Strategy 2: Query multiple datasets directly
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    obs_value_filter="tissue_general in ['lung', 'liver', 'kidney'] and is_primary_data == True",
)
```
