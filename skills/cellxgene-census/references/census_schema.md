# CZ CELLxGENE Census Data Schema Reference

## Overview

The CZ CELLxGENE Census is a versioned collection of single-cell and spatial transcriptomics data built on the TileDB-SOMA framework. This reference documents the data structure, available metadata fields, and query syntax.

Current reference point:
- Package examples target `cellxgene-census==1.17.*`
- Current stable LTS Census: `2025-11-08`
- Census schema version: `2.4.0`
- CELLxGENE dataset schema version: `7.0.0`
- Stable LTS package compatibility: `cellxgene-census` 1.17.x

## High-Level Structure

The Census is organized as a `SOMACollection` with these main components:

### 1. census_info
Summary information including:
- **summary**: Build date, cell counts, dataset statistics
- **datasets**: All datasets from CELLxGENE Discover with metadata
- **summary_cell_counts**: Cell counts stratified by metadata categories

### 2. census_data
Organism-specific `SOMAExperiment` objects:
- **"homo_sapiens"**: Human single-cell data
- **"mus_musculus"**: Mouse single-cell data
- **"callithrix_jacchus"**: Common marmoset single-cell data
- **"macaca_mulatta"**: Rhesus macaque single-cell data
- **"pan_troglodytes"**: Chimpanzee single-cell data

### 3. census_spatial_sequencing
Spatial organism-specific `SOMAExperiment` objects for supported releases. Spatial and non-spatial data share core metadata requirements, while spatial observations also include spatial columns such as `array_col`, `array_row`, and `in_tissue`.

## Single-Cell Data Structure Per Organism

Each organism experiment contains:

### obs (Cell Metadata)
Cell-level annotations stored as a `SOMADataFrame`. Access via:
```python
census["census_data"]["homo_sapiens"].obs
```

### ms["RNA"] (Measurement)
RNA measurement data including:
- **X**: Data matrices with layers:
  - `raw`: Raw count data
- **var**: Gene metadata
- **feature_dataset_presence_matrix**: Sparse boolean array showing which genes were measured in each dataset

## Spatial Data Structure Per Organism

Spatial data is stored separately from the single-cell Census data:
```python
census["census_spatial_sequencing"]["homo_sapiens"]
```

Each spatial organism experiment contains:
- `obs`: Spatial observation metadata, including core Census metadata and spatial fields such as `array_col`, `array_row`, and `in_tissue`
- `ms["RNA"]`: RNA measurement matrices and feature metadata
- `spatial[scene_id].obsl["loc"]`: point-cloud positions for each scene, with `x`, `y`, and `soma_joinid`

Use `axis_query(...).to_spatialdata(X_name="raw")` when exporting a spatial slice to `spatialdata`.

## Cell Metadata Fields (obs)

### Required/Core Fields

**Identity & Dataset:**
- `soma_joinid`: Unique integer identifier for joins
- `dataset_id`: Source dataset identifier
- `is_primary_data`: Boolean flag (True = unique cell, False = duplicate across datasets)

**Cell Type:**
- `cell_type`: Human-readable cell type name
- `cell_type_ontology_term_id`: Standardized ontology term (e.g., "CL:0000236")

**Tissue:**
- `tissue`: Specific tissue name
- `tissue_general`: Broader tissue category (useful for grouping)
- `tissue_ontology_term_id`: Standardized ontology term
- `tissue_general_ontology_term_id`: Standardized ontology term for the broader tissue category

**Assay:**
- `assay`: Sequencing technology used
- `assay_ontology_term_id`: Standardized ontology term

**Disease:**
- `disease`: Disease status or condition
- `disease_ontology_term_id`: Standardized ontology term

**Donor:**
- `donor_id`: Unique donor identifier
- `sex`: Biological sex (male, female, unknown)
- `self_reported_ethnicity`: Ethnicity information
- `development_stage`: Life stage (adult, child, embryonic, etc.)
- `development_stage_ontology_term_id`: Standardized ontology term

**Organism:**
- `organism`: Scientific name (for example, Homo sapiens or Mus musculus)
- `organism_ontology_term_id`: Standardized ontology term

**Technical:**
- `suspension_type`: Sample preparation type (cell, nucleus, na)

## Gene Metadata Fields (var)

Access via:
```python
census["census_data"]["homo_sapiens"].ms["RNA"].var
```

**Available Fields:**
- `soma_joinid`: Unique integer identifier for joins
- `feature_id`: Ensembl gene ID (e.g., "ENSG00000161798")
- `feature_name`: Gene symbol (e.g., "FOXP2")
- `feature_type`: Feature type from the source schema
- `feature_length`: Gene length in base pairs
- `nnz`: Non-zero count summary
- `n_measured_obs`: Number of measured observations for the feature

## Value Filter Syntax

Queries use Python-like expressions for filtering. The syntax is processed by TileDB-SOMA.

### Comparison Operators
- `==`: Equal to
- `!=`: Not equal to
- `<`, `>`, `<=`, `>=`: Numeric comparisons
- `in`: Membership test (e.g., `feature_id in ['ENSG00000161798', 'ENSG00000188229']`)

### Logical Operators
- `and`, `&`: Logical AND
- `or`, `|`: Logical OR

### Examples

**Single condition:**
```python
value_filter="cell_type == 'B cell'"
```

**Multiple conditions with AND:**
```python
value_filter="cell_type == 'B cell' and tissue_general == 'lung' and is_primary_data == True"
```

**Using IN for multiple values:**
```python
value_filter="tissue in ['lung', 'liver', 'kidney']"
```

**Complex condition:**
```python
value_filter="(cell_type == 'neuron' or cell_type == 'astrocyte') and disease != 'normal'"
```

**Filtering genes:**
```python
var_value_filter="feature_name in ['CD4', 'CD8A', 'CD19']"
```

### Multi-Value Disease Fields

In current LTS releases, `disease` and `disease_ontology_term_id` may contain multiple values delimited by ` || `. Exact equality filters such as `disease == 'COVID-19'` can miss cells whose disease field contains multiple labels. For comprehensive disease queries, first inspect available values with `get_obs()` or `summary_cell_counts`, then choose filters that match the selected release's encoding.

## Data Inclusion Criteria

The Census includes all data from CZ CELLxGENE Discover meeting:

1. **Species**: Human (*Homo sapiens*) or mouse (*Mus musculus*)
2. **Technology**: Approved sequencing technologies for RNA
3. **Count Type**: Raw counts only (no processed/normalized-only data)
4. **Metadata**: Standardized following CELLxGENE schema
5. **Both spatial and non-spatial data**: Includes traditional and spatial transcriptomics

## Important Data Characteristics

### Duplicate Cells
Cells may appear across multiple datasets. Use `is_primary_data == True` to filter for unique cells in most analyses.

### Count Types
The Census includes:
- **Molecule counts**: From UMI-based methods
- **Full-gene sequencing read counts**: From non-UMI methods
These may need different normalization approaches.

### Versioning
Census releases are versioned (e.g., "2025-11-08", "stable", "latest"). Always specify an LTS build date for reproducible analysis:
```python
census = cellxgene_census.open_soma(census_version="2025-11-08")
```

`stable` resolves to the current LTS release. `latest` resolves to the newest weekly release, which provides fast access to newly ingested datasets but is retained for a shorter period than LTS releases.

## Feature Dataset Presence Matrix

Access which genes were measured in each dataset:
```python
presence_matrix = census["census_data"]["homo_sapiens"].ms["RNA"]["feature_dataset_presence_matrix"]
```

This sparse boolean matrix helps understand:
- Gene coverage across datasets
- Which datasets to include for specific gene analyses
- Technical batch effects related to gene coverage

## SOMA Object Types

Core TileDB-SOMA objects used:
- **DataFrame**: Tabular data (obs, var)
- **SparseNDArray**: Sparse matrices (X layers, presence matrix)
- **DenseNDArray**: Dense arrays (less common)
- **Collection**: Container for related objects
- **Experiment**: Top-level container for measurements
- **SOMAScene**: Spatial transcriptomics scenes
- **obs_spatial_presence**: Spatial data availability
