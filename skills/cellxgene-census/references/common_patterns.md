# Common Query Patterns and Best Practices

Reviewed against Census 1.18.0, TileDB-SOMA 2.3.0, and the 2025-11-08 LTS.
Snippets share an open `census` context unless shown otherwise. Large cohort,
model-training, and downstream analysis blocks are illustrative: first inspect
metadata and size, restrict datasets/genes, and supply the named callbacks/model.
API and sparse-statistics contracts were exercised on a small local SOMA fixture;
a 10-cell/3-gene slice and metadata were also read from the public LTS.


## Query Pattern Categories

### 1. Exploratory Queries (Metadata Only)

Use when exploring available data without loading expression matrices.

**Pattern: Get unique cell types in a tissue**
```python
import cellxgene_census

with cellxgene_census.open_soma(census_version="2025-11-08") as census:
    cell_metadata = cellxgene_census.get_obs(
        census,
        "homo_sapiens",
        value_filter="tissue_general == 'brain' and is_primary_data == True",
        column_names=["cell_type"]
    )
    unique_cell_types = cell_metadata["cell_type"].unique()
    print(f"Found {len(unique_cell_types)} unique cell types")
```

**Pattern: Count cells by condition**
```python
cell_metadata = cellxgene_census.get_obs(
    census,
    "homo_sapiens",
    value_filter="disease != 'normal' and is_primary_data == True",
    column_names=["disease", "tissue_general"]
)
counts = cell_metadata.groupby(["disease", "tissue_general"]).size()
```

**Pattern: Explore dataset information**
```python
# Access datasets table
datasets = census["census_info"]["datasets"].read().concat().to_pandas()

# Title search is discovery only; disease labels are on obs, not datasets.
candidates = datasets[datasets["dataset_title"].str.contains("COVID", case=False, na=False)]
```

### 2. Small-to-Medium Queries (AnnData)

Use `get_anndata()` when results fit in memory. There is no safe universal cell-count threshold; include gene count, sparsity, embeddings, and downstream copies in the estimate.

**Pattern: Tissue-specific cell type query**
```python
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    obs_value_filter="cell_type == 'B cell' and tissue_general == 'lung' and is_primary_data == True",
    obs_column_names=["assay", "disease", "sex", "donor_id"],
)
```

**Pattern: Gene-specific query with multiple genes**
```python
marker_genes = ["CD4", "CD8A", "CD19", "FOXP3"]

# First get gene IDs
gene_metadata = cellxgene_census.get_var(
    census, "homo_sapiens",
    value_filter=f"feature_name in {marker_genes}",
    column_names=["feature_id", "feature_name"]
)
gene_ids = gene_metadata["feature_id"].tolist()
if not gene_ids:
    raise ValueError("No requested marker genes found")
# Inspect duplicate symbols; retain feature_id rather than collapsing matches.

# Query with gene filter
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    var_value_filter=f"feature_id in {gene_ids}",
    obs_value_filter="cell_type == 'T cell' and is_primary_data == True",
)
```

**Pattern: Multi-tissue query**
```python
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    obs_value_filter="tissue_general in ['lung', 'liver', 'kidney'] and is_primary_data == True",
    obs_column_names=["cell_type", "tissue_general", "dataset_id"],
)
```

**Pattern: Disease-specific query**
```python
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    obs_value_filter="disease == 'COVID-19' and tissue_general == 'lung' and is_primary_data == True",
)
```

**Pattern: Include compound disease labels**

Schema 2.4.0 stores multiple disease labels/IDs in one string separated by ` || `.
Use summary rows to discover the actual strings and token membership to choose
whole values; substring matching can confuse distinct disease names. This
includes co-diagnoses rather than only the exact single-label cohort.

```python
summary = census["census_info"]["summary_cell_counts"].read().concat().to_pandas()
disease_values = summary.loc[
    summary["organism"].eq("homo_sapiens") & summary["category"].eq("disease"),
    "label",
].unique()
matching = [value for value in disease_values if "COVID-19" in value.split(" || ")]
if not matching:
    raise ValueError("Requested disease not present in this release")
disease_filter = f"disease in {matching!r} and is_primary_data == True"
# Add dataset/tissue restrictions after inspecting cohort size.
```

For precise ontology-based cohorts, inspect `disease_ontology_term_id` as well;
matching one ontology term does not automatically include all descendants.

### 3. Large Queries (Out-of-Core Processing)

Use `axis_query()` for queries that exceed available RAM.

**Pattern: Iterative processing**
```python
import tiledbsoma as soma

# Create query
with census["census_data"]["homo_sapiens"].axis_query(
    measurement_name="RNA",
    obs_query=soma.AxisQuery(
        value_filter="tissue_general == 'brain' and is_primary_data == True"
    ),
    var_query=soma.AxisQuery(
        value_filter="feature_name in ['FOXP2', 'TBR1', 'SATB2']"
    ),
) as query:
    # Iterate through X matrix in chunks
    iterator = query.X("raw").tables()
    for batch in iterator:
        # Process batch (a pyarrow.Table); soma_dim_0 = cells, soma_dim_1 = genes
        # batch has columns: soma_data, soma_dim_0, soma_dim_1
        process_batch(batch)
```

**Pattern: Per-gene mean and variance including measured zeros**

Restrict to datasets that measured every requested feature before computing the
statistics. This example selects CD4 by its unique Ensembl ID. It includes sparse
zeros, returns one row per gene, and rejects empty or one-cell selections rather
than returning an undefined sample variance.

```python
from cellxgene_census.experimental.pp import mean_variance

# Assumes census and soma are imported/open as above.
genes = cellxgene_census.get_var(
    census, "homo_sapiens", value_filter="feature_id == 'ENSG00000010610'",
    column_names=["soma_joinid", "feature_id"],
)
if len(genes) != 1:
    raise ValueError("Expected one CD4 feature")
datasets = census["census_info"]["datasets"].read().concat().to_pandas()
presence = cellxgene_census.get_presence_matrix(census, "homo_sapiens")
covered = presence[datasets["soma_joinid"].to_numpy(), :][:, genes["soma_joinid"].to_numpy()]
eligible_ids = datasets.loc[covered.toarray().all(axis=1), "dataset_id"].tolist()
if not eligible_ids:
    raise ValueError("No datasets measured CD4")

with census["census_data"]["homo_sapiens"].axis_query(
    measurement_name="RNA",
    obs_query=soma.AxisQuery(value_filter=(
        f"dataset_id in {eligible_ids!r} and tissue_general == 'brain' "
        "and is_primary_data == True"
    )),
    var_query=soma.AxisQuery(coords=(genes["soma_joinid"].to_numpy(),)),
) as query:
    if query.n_obs < 2:
        raise ValueError("At least two selected cells are required")
    stats = mean_variance(
        query, layer="raw", axis=0, calculate_mean=True,
        calculate_variance=True, ddof=1, nnz_only=False,
    )
```

These describe raw count distributions, not normalized differential expression.
For genes with different measurement coverage, either use a common measured
subset or compute each gene with its own valid denominator. `nnz_only=True` is a
different estimand: the distribution of explicitly stored entries.

### 4. PyTorch Integration (Machine Learning)

Use TileDB-SOMA-ML for training models. The former `cellxgene_census.experimental.ml` loaders are absent from 1.18.0.

**Pattern: Create training dataloader**
```python
import tiledbsoma as soma
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

        for epoch in range(num_epochs):
            dataset.set_epoch(epoch)
            for X, obs in dataloader:
                labels = obs["cell_type"]
                # Train model...
```

**Pattern: Train/test split**
```python
# Split data
train_dataset, test_dataset = dataset.random_split(0.8, 0.2, seed=42)

# Create loaders
train_loader = experiment_dataloader(train_dataset, num_workers=0)
test_loader = experiment_dataloader(test_dataset, num_workers=0)
```

Set `batch_size` and `shuffle` on `ExperimentDataset`, not on the PyTorch `DataLoader`. On macOS, enable multiple workers only from an importable script under `if __name__ == "__main__":`. Keep iteration within the open Census/query context.

A random cell split measures within-cohort interpolation; hold out donors or studies to test generalization. Keep one vocabulary fitted on the training data and define how unseen labels are handled. `X` is NumPy (or SciPy sparse), and `obs` is pandas, so convert inputs to tensors and string labels to stable integer IDs before computing a PyTorch loss.

### 5. Spatial Census Data

Use the `cellxgene-census[spatial]` extra and query the `census_spatial_sequencing` collection for Visium or Slide-seq V2 data.

```python
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

### 6. Integration Workflows

**Pattern: Scanpy integration**
```python
import scanpy as sc

# Load data
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    obs_value_filter="cell_type == 'neuron' and is_primary_data == True",
)

# Standard scanpy workflow
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata)
sc.pp.pca(adata)
sc.pp.neighbors(adata)
sc.tl.umap(adata)
sc.pl.umap(adata, color=["cell_type", "tissue_general"])
```

**Pattern: Multi-dataset integration**
```python
# Query multiple datasets separately
datasets_to_integrate = ["dataset_id_1", "dataset_id_2", "dataset_id_3"]

adatas = []
for dataset_id in datasets_to_integrate:
    adata = cellxgene_census.get_anndata(
        census=census,
        organism="Homo sapiens",
        obs_value_filter=f"dataset_id == '{dataset_id}' and is_primary_data == True",
    )
    adatas.append(adata)

# Scanpy's wrapper expects ONE AnnData with contiguous batches and X_pca.
# Install scanorama separately for this illustrative integration workflow.
import anndata as ad
import scanpy as sc
import scanpy.external as sce
for item in adatas:
    item.var_names = item.var["feature_id"].astype(str)
combined = ad.concat(adatas, label="batch", keys=datasets_to_integrate, join="inner")
combined.layers["counts"] = combined.X.copy()
sc.pp.normalize_total(combined, target_sum=1e4)
sc.pp.log1p(combined)
sc.pp.highly_variable_genes(combined, n_top_genes=2000, batch_key="batch")
sc.pp.pca(combined)
sce.pp.scanorama_integrate(combined, key="batch")
sc.pp.neighbors(combined, use_rep="X_scanorama")
```

## Best Practices

### 1. Always Filter for Primary Data
Unless specifically analyzing duplicates, always include `is_primary_data == True`:
```python
obs_value_filter="cell_type == 'B cell' and is_primary_data == True"
```

### 2. Specify Census Version
For reproducible analysis, always specify the Census version:
```python
census = cellxgene_census.open_soma(census_version="2025-11-08")
```

### 3. Use Context Manager
Always use the context manager to ensure proper cleanup:
```python
with cellxgene_census.open_soma(census_version="2025-11-08") as census:
    print(list(census["census_data"]))
```

### 4. Select Only Needed Columns
Minimize data transfer by selecting only required metadata columns:
```python
obs_column_names=["cell_type", "tissue_general", "disease"]  # Not all columns
```

### 5. Check Dataset Presence for Gene Queries
When analyzing specific genes, check which datasets measured them:
```python
genes = cellxgene_census.get_var(
    census, "homo_sapiens",
    value_filter="feature_name in ['CD4', 'CD8A']",
    column_names=["soma_joinid", "feature_id", "feature_name"],
)
presence = cellxgene_census.get_presence_matrix(census, "homo_sapiens")
# Columns use Census join IDs, not positions in the filtered gene table.
gene_presence = presence[:, genes["soma_joinid"].to_numpy()]
```

### 6. Use tissue_general for Broader Queries
`tissue_general` provides coarser groupings than `tissue`, useful for cross-tissue analyses:
```python
# Better for broad queries
obs_value_filter="tissue_general == 'immune system'"

# Use specific tissue when needed
obs_value_filter="tissue == 'venous blood'"
```

### 7. Combine Metadata Exploration with Expression Queries
First explore metadata to understand available data, then query expression:
```python
# Step 1: Explore
metadata = cellxgene_census.get_obs(
    census, "homo_sapiens",
    value_filter="disease == 'COVID-19'",
    column_names=["cell_type", "tissue_general"]
)
print(metadata.value_counts())

# Step 2: Query based on findings
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    obs_value_filter="disease == 'COVID-19' and cell_type == 'T cell' and is_primary_data == True",
)
```

### 8. Memory Management for Large Queries
For large queries, check estimated size before loading:
```python
# Get cell count first
metadata = cellxgene_census.get_obs(
    census, "homo_sapiens",
    value_filter="tissue_general == 'brain' and is_primary_data == True",
    column_names=["soma_joinid"]
)
n_cells = len(metadata)
print(f"Query will return {n_cells} cells")

# If too large, use out-of-core processing or further filtering
```

### 9. Leverage Ontology Terms for Consistency
When possible, use ontology term IDs instead of free text:
```python
# More reliable than cell_type == 'B cell' across datasets
obs_value_filter="cell_type_ontology_term_id == 'CL:0000236'"
```

### 10. Batch Processing Pattern
For systematic analyses across multiple conditions:
```python
tissues = ["lung", "liver", "kidney", "heart"]
results = {}

for tissue in tissues:
    adata = cellxgene_census.get_anndata(
        census=census,
        organism="Homo sapiens",
        obs_value_filter=f"tissue_general == '{tissue}' and is_primary_data == True",
    )
    # Perform analysis
    results[tissue] = analyze(adata)
```

## Common Pitfalls to Avoid

1. **Not filtering for is_primary_data**: Leads to counting duplicate cells
2. **Loading too much data**: Use metadata queries to estimate size first
3. **Not using context manager**: Can cause resource leaks
4. **Inconsistent versioning**: Results not reproducible without specifying version
5. **Overly broad queries**: Start with focused queries, expand as needed
6. **Ignoring dataset presence**: Some genes not measured in all datasets
7. **Wrong count normalization**: Be aware of UMI vs read count differences
