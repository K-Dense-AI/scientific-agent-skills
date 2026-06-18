---
name: cellxgene-census
description: Query the CZ CELLxGENE Census programmatically for versioned public single-cell and spatial transcriptomics data. Use when you need population-scale cell metadata, gene expression slices, Census summary counts, source H5AD URIs/downloads, embeddings, spatial Census data, or reference atlas comparisons across organisms, tissues, diseases, assays, and cell types. For analyzing your own local single-cell data use scanpy, anndata, or scvi-tools.
allowed-tools: Read Write Edit Bash
license: MIT
compatibility: Requires Python >=3.10,<3.13. Examples target cellxgene-census 1.17.x and the 2025-11-08 stable LTS Census; spatial workflows need the spatial extra and TileDB-SOMA >=1.15.5. No authentication is required for public Census data.
metadata: {"version": "1.1", "skill-author": "K-Dense Inc."}
---

# CZ CELLxGENE Census

## Overview

The CZ CELLxGENE Census provides programmatic access to a comprehensive, versioned collection of standardized single-cell and spatial transcriptomics data from CZ CELLxGENE Discover. This skill enables efficient querying and analysis of public Census releases without downloading whole datasets first.

The Census includes:
- **217+ million total cells** and **125+ million unique cells** in the 2025-11-08 stable LTS release
- **1,845 datasets** in the 2025-11-08 stable LTS release
- **Human, mouse, marmoset, rhesus macaque, and chimpanzee** data in the current schema
- **Standardized metadata** (cell types, tissues, diseases, donors)
- **Raw gene expression** matrices and source H5AD lookup/download helpers
- **Pre-calculated summary counts, embeddings, and spatial data**
- **Integration with AnnData, Scanpy, TileDB-SOMA, TileDB-SOMA-ML, and other analysis tools**

## When to Use This Skill

This skill should be used when:
- Querying single-cell expression data by cell type, tissue, or disease
- Exploring available single-cell datasets and metadata
- Training machine learning models on single-cell data
- Performing large-scale cross-dataset analyses
- Integrating Census data with scanpy or other analysis frameworks
- Computing statistics across millions of cells
- Accessing pre-calculated embeddings or model predictions

## Installation and Setup

Install the Census API:
```bash
uv pip install "cellxgene-census==1.17.*"
```

For spatial workflows:
```bash
uv pip install "cellxgene-census[spatial]==1.17.*" "spatialdata[extra]>=0.2.5"
```

For PyTorch model training, use TileDB-SOMA-ML. The old `cellxgene_census.experimental.ml` loaders are deprecated:

```bash
uv pip install "cellxgene-census==1.17.*" tiledbsoma-ml
```

## Core Workflow Patterns

### 1. Opening the Census

Always use the context manager to ensure proper resource cleanup:

```python
import cellxgene_census

# Open latest stable version
with cellxgene_census.open_soma() as census:
    # Work with census data

# Open the current LTS version for reproducibility
with cellxgene_census.open_soma(census_version="2025-11-08") as census:
    # Work with census data
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

For queries returning < 100k cells that fit in memory, use `get_anndata()`:

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
```python
import tiledbsoma as soma

# Example: Calculate mean expression
n_observations = 0
sum_values = 0.0

with census["census_data"]["homo_sapiens"].axis_query(
    measurement_name="RNA",
    obs_query=soma.AxisQuery(value_filter="tissue_general == 'brain' and is_primary_data == True"),
    var_query=soma.AxisQuery(value_filter="feature_name in ['FOXP2', 'TBR1', 'SATB2']"),
) as query:
    iterator = query.X("raw").tables()
    for batch in iterator:
        values = batch["soma_data"].to_numpy()
        n_observations += len(values)
        sum_values += values.sum()

mean_expression = sum_values / n_observations
```

### 5. Machine Learning with PyTorch

For training models, use TileDB-SOMA-ML. The former `cellxgene_census.experimental.ml` PyTorch loaders are deprecated and scheduled for removal.

```python
import tiledbsoma as soma
from tiledbsoma_ml import ExperimentDataset, experiment_dataloader

with cellxgene_census.open_soma() as census:
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

        # Training loop
        for epoch in range(num_epochs):
            dataset.set_epoch(epoch)
            for X, obs in dataloader:
                labels = obs["cell_type"]

                # Forward pass
                outputs = model(X)
                loss = criterion(outputs, labels)

                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
```

**Train/test splitting:**
```python
train_dataset, test_dataset = dataset.random_split(0.8, 0.2, seed=42)
train_loader = experiment_dataloader(train_dataset, num_workers=2)
test_loader = experiment_dataloader(test_dataset, num_workers=2)
```

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
    obs_value_filter="cell_type == 'neuron' and tissue_general == 'cortex' and is_primary_data == True",
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
    adata.obs["tissue"] = tissue
    adatas.append(adata)

# Concatenate with AnnData's current API
import anndata as ad
combined = ad.concat(adatas, label="tissue", keys=tissues)

# Strategy 2: Query multiple datasets directly
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    obs_value_filter="tissue_general in ['lung', 'liver', 'kidney'] and is_primary_data == True",
)
```

## Key Concepts and Best Practices

### Always Filter for Primary Data
Unless analyzing duplicates, always include `is_primary_data == True` in queries to avoid counting cells multiple times:
```python
obs_value_filter="cell_type == 'B cell' and is_primary_data == True"
```

### Specify Census Version for Reproducibility
Always specify the Census version in production analyses:
```python
census = cellxgene_census.open_soma(census_version="2025-11-08")
```

### Estimate Query Size Before Loading
For large queries, first check the number of cells to avoid memory issues:
```python
# Get cell count
metadata = cellxgene_census.get_obs(
    census, "homo_sapiens",
    value_filter="tissue_general == 'brain' and is_primary_data == True",
    column_names=["soma_joinid"]
)
n_cells = len(metadata)
print(f"Query will return {n_cells:,} cells")

# If too large (>100k), use out-of-core processing
```

### Use tissue_general for Broader Groupings
The `tissue_general` field provides coarser categories than `tissue`, useful for cross-tissue analyses:
```python
# Broader grouping
obs_value_filter="tissue_general == 'immune system'"

# Specific tissue
obs_value_filter="tissue == 'peripheral blood mononuclear cell'"
```

### Select Only Needed Columns
Minimize data transfer by specifying only required metadata columns:
```python
obs_column_names=["cell_type", "tissue_general", "disease"]  # Not all columns
```

### Check Dataset Presence for Gene-Specific Queries
When analyzing specific genes, verify which datasets measured them:
```python
presence = cellxgene_census.get_presence_matrix(
    census,
    "homo_sapiens",
    var_value_filter="feature_name in ['CD4', 'CD8A']"
)
```

### Two-Step Workflow: Explore Then Query
First explore metadata to understand available data, then query expression:
```python
# Step 1: Explore what's available
metadata = cellxgene_census.get_obs(
    census, "homo_sapiens",
    value_filter="disease == 'COVID-19' and is_primary_data == True",
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

## Available Metadata Fields

### Cell Metadata (obs)
Key fields for filtering:
- `cell_type`, `cell_type_ontology_term_id`
- `tissue`, `tissue_general`, `tissue_ontology_term_id`
- `disease`, `disease_ontology_term_id`
- `assay`, `assay_ontology_term_id`
- `donor_id`, `sex`, `self_reported_ethnicity`
- `development_stage`, `development_stage_ontology_term_id`
- `dataset_id`
- `is_primary_data` (Boolean: True = unique cell)

The current schema includes organism collections beyond human and mouse. Confirm available organisms for the selected release with `list(census["census_data"].keys())`.

### Gene Metadata (var)
- `feature_id` (Ensembl gene ID, e.g., "ENSG00000161798")
- `feature_name` (Gene symbol, e.g., "FOXP2")
- `feature_type`
- `feature_length` (Gene length in base pairs)
- `nnz`, `n_measured_obs` (availability summaries useful for checking sparsity and coverage)

## Reference Documentation

This skill includes detailed reference documentation:

### references/census_schema.md
Comprehensive documentation of:
- Census data structure and organization
- All available metadata fields
- Value filter syntax and operators
- SOMA object types
- Data inclusion criteria

**When to read:** When you need detailed schema information, full list of metadata fields, or complex filter syntax.

### references/common_patterns.md
Examples and patterns for:
- Exploratory queries (metadata only)
- Small-to-medium queries (AnnData)
- Large queries (out-of-core processing)
- PyTorch integration
- Spatial Census access patterns
- Scanpy integration workflows
- Multi-dataset integration
- Best practices and common pitfalls

**When to read:** When implementing specific query patterns, looking for code examples, or troubleshooting common issues.

## Common Use Cases

### Use Case 1: Explore Cell Types in a Tissue
```python
with cellxgene_census.open_soma() as census:
    cells = cellxgene_census.get_obs(
        census, "homo_sapiens",
        value_filter="tissue_general == 'lung' and is_primary_data == True",
        column_names=["cell_type"]
    )
    print(cells["cell_type"].value_counts())
```

### Use Case 2: Query Marker Gene Expression
```python
with cellxgene_census.open_soma() as census:
    adata = cellxgene_census.get_anndata(
        census=census,
        organism="Homo sapiens",
        var_value_filter="feature_name in ['CD4', 'CD8A', 'CD19']",
        obs_value_filter="cell_type in ['T cell', 'B cell'] and is_primary_data == True",
    )
```

### Use Case 3: Train Cell Type Classifier
```python
import tiledbsoma as soma
from tiledbsoma_ml import ExperimentDataset, experiment_dataloader

with cellxgene_census.open_soma() as census:
    experiment = census["census_data"]["homo_sapiens"]
    with experiment.axis_query(
        measurement_name="RNA",
        obs_query=soma.AxisQuery(value_filter="is_primary_data == True"),
    ) as query:
        dataset = ExperimentDataset(
            query=query,
            layer_name="raw",
            obs_column_names=["cell_type"],
            batch_size=128,
            shuffle=True,
        )
        dataloader = experiment_dataloader(dataset)

        for X, obs in dataloader:
            labels = obs["cell_type"]
            # Training logic
            pass
```

### Use Case 4: Cross-Tissue Analysis
```python
with cellxgene_census.open_soma() as census:
    adata = cellxgene_census.get_anndata(
        census=census,
        organism="Homo sapiens",
        obs_value_filter="cell_type == 'macrophage' and tissue_general in ['lung', 'liver', 'brain'] and is_primary_data == True",
    )

    # Analyze macrophage differences across tissues
    sc.tl.rank_genes_groups(adata, groupby="tissue_general")
```

## Troubleshooting

### Query Returns Too Many Cells
- Add more specific filters to reduce scope
- Use `tissue` instead of `tissue_general` for finer granularity
- Filter by specific `dataset_id` if known
- Switch to out-of-core processing for large queries

### Memory Errors
- Reduce query scope with more restrictive filters
- Select fewer genes with `var_value_filter`
- Use out-of-core processing with `axis_query()`
- Process data in batches

### Duplicate Cells in Results
- Always include `is_primary_data == True` in filters
- Check if intentionally querying across multiple datasets

### Gene Not Found
- Verify gene name spelling (case-sensitive)
- Try Ensembl ID with `feature_id` instead of `feature_name`
- Check dataset presence matrix to see if gene was measured
- Some genes may have been filtered during Census construction

### Version Inconsistencies
- Always specify `census_version` explicitly
- Use same version across all analyses
- Check release notes for version-specific changes

