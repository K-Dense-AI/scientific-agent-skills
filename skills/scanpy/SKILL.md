---
name: scanpy
description: Standard single-cell RNA-seq analysis pipeline. Use for QC, normalization, dimensionality reduction (PCA/UMAP/t-SNE), clustering, differential expression, visualization, and converting R-friendly single-cell formats such as Seurat or SingleCellExperiment RDS files into h5ad for Scanpy. Best for exploratory scRNA-seq analysis with established workflows. For deep learning models use scvi-tools; for data format questions use anndata.
license: BSD-3-Clause
metadata: {"version": "1.3", "skill-author": "K-Dense Inc."}
---

# Scanpy: Single-Cell Analysis

## Overview

Scanpy is a scalable Python toolkit for analyzing single-cell RNA-seq data, built on AnnData. Apply this skill for complete single-cell workflows including quality control, normalization, dimensionality reduction, clustering, marker gene identification, visualization, and trajectory analysis. Current stable release: **scanpy 1.12.x** (January 2026).

## Installation

Requires Python **3.12+** (scanpy 1.12 dropped Python ≤3.11) and anndata **≥0.10**.

```bash
uv pip install "scanpy[leiden]"
```

The `[leiden]` extra installs `python-igraph` and `leidenalg`, required for Leiden clustering. For reproducible environments, pin a version: `uv pip install "scanpy[leiden]==1.12.1"`.

For large or out-of-core datasets, many functions support [Dask](https://docs.dask.org/) arrays (experimental):

```bash
uv pip install "scanpy[leiden]" dask
```

See the [Using dask with Scanpy](https://scanpy.scverse.org/en/stable/tutorials/experimental/dask.html) tutorial. For GPU-accelerated scanpy-like operations, use [rapids-singlecell](https://rapids-singlecell.readthedocs.io/) as a separate package.

If the input is an R-native single-cell object (`.rds`, `.RData`, Seurat, or SingleCellExperiment), first convert it to `.h5ad` with R tooling, then load it with Scanpy. Read `references/r_interop.md` for agent-run installation and conversion instructions across macOS, Linux, and Windows.

For AnnData structure and I/O details, use the **anndata** skill. For probabilistic models and batch correction, use **scvi-tools**.

## When to Use This Skill

This skill should be used when:
- Analyzing single-cell RNA-seq data (.h5ad, 10X, CSV formats)
- Working with R-friendly single-cell datasets (`.rds`, `.RData`, Seurat, SingleCellExperiment) that need conversion to `.h5ad`
- Performing quality control on scRNA-seq datasets
- Creating UMAP, t-SNE, or PCA visualizations
- Identifying cell clusters and finding marker genes
- Annotating cell types based on gene expression
- Conducting trajectory inference or pseudotime analysis
- Generating publication-quality single-cell plots

## Script Toolkit (prefer these over writing code from scratch)

This skill bundles ready-to-run CLI scripts in `scripts/` for every common step. **Run these instead of hand-writing scanpy code** — they handle file loading by extension, figure setup, sensible defaults, raw-count preservation, and progress logging. Each reads and writes `.h5ad`, so they chain together, and each has its own `--help`. Only drop down to writing scanpy code when a task isn't covered by a script or needs unusual customization.

All scripts use a shared `scripts/_common.py` helper (loading, saving, figure config) — keep it alongside the others. Run from the skill directory or pass full paths; figures default to `./figures/`.

| Script | Purpose | Typical call |
|--------|---------|--------------|
| `run_pipeline.py` | **Full workflow in one command**: load → QC → normalize → HVG → PCA → (batch) → UMAP → Leiden → markers | `python scripts/run_pipeline.py raw.h5ad -o processed.h5ad` |
| `inspect_data.py` | Summarize an unknown dataset (shape, obs/var, layers, what's already computed, raw vs normalized) | `python scripts/inspect_data.py data.h5ad` |
| `convert.py` | Load any format (10x dir/.h5, csv, loom, mtx) and write `.h5ad` | `python scripts/convert.py 10x_dir/ -o data.h5ad` |
| `qc_analysis.py` | QC metrics, before/after plots, filtering, optional Scrublet doublets | `python scripts/qc_analysis.py raw.h5ad -o qc.h5ad --scrublet` |
| `preprocess.py` | Normalize, log1p, HVG, optional scale/regress (keeps `counts` layer + `raw`) | `python scripts/preprocess.py qc.h5ad -o norm.h5ad` |
| `reduce_dimensions.py` | PCA + variance plot, neighbors, UMAP, optional t-SNE | `python scripts/reduce_dimensions.py norm.h5ad -o red.h5ad` |
| `batch_correct.py` | Integration: harmony / bbknn / combat | `python scripts/batch_correct.py red.h5ad -o int.h5ad --method harmony --batch-key sample` |
| `cluster.py` | Leiden (or louvain) at one or many resolutions | `python scripts/cluster.py red.h5ad -o clu.h5ad --resolution 0.3 0.6 1.0` |
| `find_markers.py` | `rank_genes_groups` + per-group CSVs + marker plots | `python scripts/find_markers.py clu.h5ad --groupby leiden -o clu.h5ad` |
| `annotate.py` | Map clusters → cell types from JSON/CSV; optional marker reference dotplot | `python scripts/annotate.py clu.h5ad -o ann.h5ad --mapping map.json` |
| `score_genes.py` | Score gene signatures (JSON) and/or cell-cycle phase | `python scripts/score_genes.py ann.h5ad -o scored.h5ad --gene-sets sigs.json` |
| `pseudobulk.py` | Aggregate counts by sample × cell type → matrix for pydeseq2 | `python scripts/pseudobulk.py ann.h5ad --by sample cell_type --out-prefix pb` |
| `subset.py` | Subset by obs values or gene list (optionally clear stale embeddings) | `python scripts/subset.py ann.h5ad -o tcells.h5ad --obs cell_type --keep "T cells"` |
| `plot.py` | Generate umap/tsne/pca/violin/dotplot/heatmap/etc. from a processed object | `python scripts/plot.py ann.h5ad --kind dotplot --genes CD3D CD14 --groupby cell_type` |

### One-shot end-to-end run

```bash
# Counts → clustered, marker-annotated object + figures + marker CSVs
python scripts/run_pipeline.py raw.h5ad -o processed.h5ad \
    --resolution 0.5 --n-top-genes 2000 --scrublet
# With multi-sample integration:
python scripts/run_pipeline.py raw.h5ad -o processed.h5ad --batch-key sample --batch-method harmony
# Reproducible parameters via JSON (keys mirror flag names with underscores):
python scripts/run_pipeline.py raw.h5ad -o processed.h5ad --config params.json
```

### Step-by-step chain (when you need to inspect/iterate between stages)

```bash
python scripts/qc_analysis.py        raw.h5ad  -o qc.h5ad   --scrublet
python scripts/preprocess.py         qc.h5ad   -o norm.h5ad --n-top-genes 2000
python scripts/reduce_dimensions.py  norm.h5ad -o red.h5ad  --n-pcs 40
python scripts/cluster.py            red.h5ad  -o clu.h5ad  --resolution 0.3 0.5 0.8
python scripts/find_markers.py       clu.h5ad  -o clu.h5ad  --groupby leiden --use-raw
# inspect results/markers/*.csv, decide labels, write a mapping JSON, then:
python scripts/annotate.py           clu.h5ad  -o ann.h5ad  --mapping celltypes.json
```

The sections below document the underlying scanpy calls each script performs — read them when customizing beyond the script flags.

## Quick Start

### Basic Import and Setup

```python
import scanpy as sc
import pandas as pd
import numpy as np

# Configure settings
sc.settings.verbosity = 3
sc.settings.set_figure_params(dpi=80, facecolor='white')
sc.settings.figdir = './figures/'
sc.settings.autosave = True  # Preferred over per-plot save= (deprecated in scanpy 1.12)
```

### Loading Data

```python
# From 10X Genomics
adata = sc.read_10x_mtx('path/to/data/')
adata = sc.read_10x_h5('path/to/data.h5')

# From h5ad (AnnData format)
adata = sc.read_h5ad('path/to/data.h5ad')

# From CSV
adata = sc.read_csv('path/to/data.csv')
```

For R-native files, do not try to parse Seurat `.rds` directly in Python. Convert first:

```bash
# See references/r_interop.md for installing R and conversion packages.
Rscript convert_rds_to_h5ad.R input.rds output.h5ad
```

```python
adata = sc.read_h5ad('output.h5ad')
```

### Understanding AnnData Structure

The AnnData object is the core data structure in scanpy:

```python
adata.X          # Expression matrix (cells × genes)
adata.obs        # Cell metadata (DataFrame)
adata.var        # Gene metadata (DataFrame)
adata.uns        # Unstructured annotations (dict)
adata.obsm       # Multi-dimensional cell data (PCA, UMAP)
adata.raw        # Raw data backup

# Access cell and gene names
adata.obs_names  # Cell barcodes
adata.var_names  # Gene names
```

## Standard Analysis Workflow

### 1. Quality Control

Identify and filter low-quality cells and genes:

```python
# Identify mitochondrial genes
adata.var['mt'] = adata.var_names.str.startswith('MT-')

# Calculate QC metrics
sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], inplace=True)

# Visualize QC metrics
sc.pl.violin(adata, ['n_genes_by_counts', 'total_counts', 'pct_counts_mt'],
             jitter=0.4, multi_panel=True)

# Filter cells and genes
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
adata = adata[adata.obs.pct_counts_mt < 5, :]  # Remove high MT% cells
```

**Doublet detection (optional, on raw counts before normalization):**

```python
sc.pp.scrublet(adata)  # Core API since scanpy 1.10 (was scanpy.external.pp)
adata = adata[~adata.obs['predicted_doublet'], :].copy()
```

**Use the QC script for automated analysis** (run from the skill directory or pass the full path):

```bash
python skills/scanpy/scripts/qc_analysis.py input_file.h5ad --output filtered.h5ad
```

### 2. Normalization and Preprocessing

```python
# Normalize to 10,000 counts per cell
sc.pp.normalize_total(adata, target_sum=1e4)

# Log-transform
sc.pp.log1p(adata)

# Save raw counts for later
adata.raw = adata

# Identify highly variable genes
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.pl.highly_variable_genes(adata)

# Subset to highly variable genes
adata = adata[:, adata.var.highly_variable]

# Regress out unwanted variation
sc.pp.regress_out(adata, ['total_counts', 'pct_counts_mt'])

# Scale data
sc.pp.scale(adata, max_value=10)
```

### 3. Dimensionality Reduction

```python
# PCA
sc.tl.pca(adata, svd_solver='arpack')
sc.pl.pca_variance_ratio(adata, log=True)  # Check elbow plot

# Compute neighborhood graph
sc.pp.neighbors(adata, n_neighbors=10, n_pcs=40)

# UMAP for visualization
sc.tl.umap(adata)
sc.pl.umap(adata, color='leiden')

# Alternative: t-SNE
sc.tl.tsne(adata)
```

### 4. Clustering

```python
# Leiden clustering (recommended)
sc.tl.leiden(adata, resolution=0.5)
sc.pl.umap(adata, color='leiden', legend_loc='on data')

# Try multiple resolutions to find optimal granularity
for res in [0.3, 0.5, 0.8, 1.0]:
    sc.tl.leiden(adata, resolution=res, key_added=f'leiden_{res}')
```

### 5. Marker Gene Identification

Use `rank_genes_groups` for **exploratory cluster markers** only. Per-cell statistical tests inflate p-values because cells are not independent observations. For rigorous differential expression between conditions or samples, pseudobulk first (see below) and use **pydeseq2** or similar tools.

```python
# Find marker genes for each cluster (exploratory)
sc.tl.rank_genes_groups(adata, 'leiden', method='wilcoxon')

# Visualize results
sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False)
sc.pl.rank_genes_groups_heatmap(adata, n_genes=10)
sc.pl.rank_genes_groups_dotplot(adata, n_genes=5)

# Get results as DataFrame
markers = sc.get.rank_genes_groups_df(adata, group='0')
```

### 6. Cell Type Annotation

```python
# Define marker genes for known cell types
marker_genes = ['CD3D', 'CD14', 'MS4A1', 'NKG7', 'FCGR3A']

# Visualize markers
sc.pl.umap(adata, color=marker_genes, use_raw=True)
sc.pl.dotplot(adata, var_names=marker_genes, groupby='leiden')

# Manual annotation
cluster_to_celltype = {
    '0': 'CD4 T cells',
    '1': 'CD14+ Monocytes',
    '2': 'B cells',
    '3': 'CD8 T cells',
}
adata.obs['cell_type'] = adata.obs['leiden'].map(cluster_to_celltype)

# Visualize annotated types
sc.pl.umap(adata, color='cell_type', legend_loc='on data')
```

### 7. Save Results

```python
# Save processed data
adata.write('results/processed_data.h5ad')

# Export metadata
adata.obs.to_csv('results/cell_metadata.csv')
adata.var.to_csv('results/gene_metadata.csv')
```

## Common Tasks

### Creating Publication-Quality Plots

Prefer `sc.settings.autosave` and `sc.settings.figdir` for saving figures. The per-plot `save=` parameter is deprecated in scanpy 1.12.

```python
# Set high-quality defaults
sc.settings.set_figure_params(dpi=300, frameon=False, figsize=(5, 5))
sc.settings.file_format_figs = 'pdf'
sc.settings.figdir = './figures/'
sc.settings.autosave = True

# UMAP with custom styling (saved as figures/umap.pdf via autosave)
sc.pl.umap(adata, color='cell_type',
           palette='Set2',
           legend_loc='on data',
           legend_fontsize=12,
           legend_fontoutline=2,
           frameon=False)

# Heatmap of marker genes
sc.pl.heatmap(adata, var_names=genes, groupby='cell_type',
              swap_axes=True, show_gene_labels=True)

# Dot plot
sc.pl.dotplot(adata, var_names=genes, groupby='cell_type')
```

Refer to `references/plotting_guide.md` for comprehensive visualization examples.

### Trajectory Inference

```python
# PAGA (Partition-based graph abstraction)
sc.tl.paga(adata, groups='leiden')
sc.pl.paga(adata, color='leiden')

# Diffusion pseudotime
adata.uns['iroot'] = np.flatnonzero(adata.obs['leiden'] == '0')[0]
sc.tl.dpt(adata)
sc.pl.umap(adata, color='dpt_pseudotime')
```

### Pseudobulk and Differential Expression Between Conditions

Pseudobulk by sample and cell type, then run proper DE (e.g., pydeseq2) rather than per-cell `rank_genes_groups`:

```python
# Aggregate counts by sample and cell type (dask-compatible in scanpy 1.12)
pb = sc.get.aggregate(
    adata,
    by=['sample', 'cell_type'],
    func='sum',
    layer='counts',  # Use raw counts layer if available
)
# Downstream: export pb and use pydeseq2 for condition comparisons
```

For quick exploratory comparisons within a cluster, `rank_genes_groups` is acceptable but interpret p-values cautiously:

```python
adata_subset = adata[adata.obs['cell_type'] == 'T cells']
sc.tl.rank_genes_groups(adata_subset, groupby='condition',
                         groups=['treated'], reference='control')
sc.pl.rank_genes_groups(adata_subset, groups=['treated'])
```

### Gene Set Scoring

```python
# Score cells for gene set expression
gene_set = ['CD3D', 'CD3E', 'CD3G']
sc.tl.score_genes(adata, gene_set, score_name='T_cell_score')
sc.pl.umap(adata, color='T_cell_score')
```

### Batch Correction

```python
# ComBat batch correction
sc.pp.combat(adata, key='batch')

# Alternative: use Harmony or scVI (separate packages)
```

## Key Parameters to Adjust

### Quality Control
- `min_genes`: Minimum genes per cell (typically 200-500)
- `min_cells`: Minimum cells per gene (typically 3-10)
- `pct_counts_mt`: Mitochondrial threshold (typically 5-20%)

### Normalization
- `target_sum`: Target counts per cell (default 1e4)

### Feature Selection
- `n_top_genes`: Number of HVGs (typically 2000-3000)
- `min_mean`, `max_mean`, `min_disp`: HVG selection parameters

### Dimensionality Reduction
- `n_pcs`: Number of principal components (check variance ratio plot)
- `n_neighbors`: Number of neighbors (typically 10-30)

### Clustering
- `resolution`: Clustering granularity (0.4-1.2, higher = more clusters)

## Common Pitfalls and Best Practices

1. **Always save raw counts**: `adata.raw = adata` before filtering genes
2. **Check QC plots carefully**: Adjust thresholds based on dataset quality
3. **Use Leiden clustering**: `sc.tl.louvain` is deprecated in scanpy 1.12
4. **Try multiple clustering resolutions**: Find optimal granularity
5. **Validate cell type annotations**: Use multiple marker genes
6. **Use `use_raw=True` for gene expression plots**: Shows normalized counts from `.raw`
7. **Check PCA variance ratio**: Determine optimal number of PCs
8. **Save intermediate results**: Long workflows can fail partway through
9. **Pseudobulk for DE**: Do not treat `rank_genes_groups` p-values as rigorous DE between conditions
10. **Save plots via settings**: Use `sc.settings.autosave` instead of deprecated `save=` on plot functions
11. **Convert R objects before Scanpy**: Use R packages to convert Seurat or SingleCellExperiment `.rds` files to `.h5ad`, preserving counts, metadata, and gene identifiers

## Bundled Resources

### scripts/ (CLI toolkit)
A composable set of `.h5ad`-in/`.h5ad`-out scripts covering the whole workflow plus a one-command end-to-end pipeline. See the **Script Toolkit** section above for the full table and chaining examples. Each script has `--help`. Files:

- `_common.py` — shared loading/saving/figure helpers imported by the others (not a CLI)
- `run_pipeline.py` — full pipeline in one command (flags or `--config` JSON)
- `inspect_data.py`, `convert.py` — explore and load/convert any input format
- `qc_analysis.py`, `preprocess.py`, `reduce_dimensions.py`, `batch_correct.py`, `cluster.py` — pipeline steps
- `find_markers.py`, `annotate.py`, `score_genes.py`, `pseudobulk.py` — markers, annotation, scoring, DE prep
- `subset.py`, `plot.py` — subset by metadata/genes; generate any standard plot

**Default to these scripts before writing scanpy code from scratch.**

### references/standard_workflow.md
Complete step-by-step workflow with detailed explanations and code examples for:
- Data loading and setup
- Quality control with visualization
- Normalization and scaling
- Feature selection
- Dimensionality reduction (PCA, UMAP, t-SNE)
- Clustering (Leiden)
- Doublet detection (scrublet) and pseudobulk aggregation
- Marker gene identification
- Cell type annotation
- Trajectory inference
- Differential expression

Read this reference when performing a complete analysis from scratch.

### references/api_reference.md
Quick reference guide for scanpy functions organized by module:
- Reading/writing data (`sc.read_*`, `adata.write_*`)
- Preprocessing (`sc.pp.*`)
- Tools (`sc.tl.*`)
- Plotting (`sc.pl.*`)
- AnnData structure and manipulation
- Settings and utilities

Use this for quick lookup of function signatures and common parameters.

### references/plotting_guide.md
Comprehensive visualization guide including:
- Quality control plots
- Dimensionality reduction visualizations
- Clustering visualizations
- Marker gene plots (heatmaps, dot plots, violin plots)
- Trajectory and pseudotime plots
- Publication-quality customization
- Multi-panel figures
- Color palettes and styling

Consult this when creating publication-ready figures.

### references/r_interop.md
Agent runbook for installing R on macOS, Linux, and Windows, installing CRAN/Bioconductor conversion packages, inspecting `.rds`/`.RData` inputs, converting Seurat or SingleCellExperiment objects to `.h5ad`, and validating the result in Scanpy.

### assets/analysis_template.py
Complete analysis template providing a full workflow from data loading through cell type annotation. Copy and customize this template for new analyses:

```bash
cp assets/analysis_template.py my_analysis.py
# Edit parameters and run
python my_analysis.py
```

The template includes all standard steps with configurable parameters and helpful comments.

### assets/ JSON templates
Edit-and-pass templates so you don't author config/mappings from scratch:
- `assets/pipeline_config.json` — parameter set for `run_pipeline.py --config`
- `assets/celltype_mapping.json` — cluster → cell-type map for `annotate.py --mapping`
- `assets/gene_signatures.json` — gene-set signatures for `score_genes.py --gene-sets`

## Additional Resources

- **Official scanpy documentation**: https://scanpy.scverse.org/en/stable/
- **Scanpy tutorials**: https://scanpy.scverse.org/en/stable/tutorials/index.html
- **Release notes**: https://scanpy.scverse.org/en/stable/release-notes/index.html
- **scverse ecosystem**: https://scverse.org/ (related tools: squidpy, scvi-tools, cellrank)
- **R interoperability**: https://www.bioconductor.org/packages/release/bioc/html/zellkonverter.html and https://mojaveazure.github.io/seurat-disk/
- **Best practices**: Luecken & Theis (2019) "Current best practices in single-cell RNA-seq"

## Tips for Effective Analysis

1. **Start with the template**: Use `assets/analysis_template.py` as a starting point
2. **Run QC script first**: Use `scripts/qc_analysis.py` for initial filtering
3. **Consult references as needed**: Load workflow and API references into context
4. **Iterate on clustering**: Try multiple resolutions and visualization methods
5. **Validate biologically**: Check marker genes match expected cell types
6. **Document parameters**: Record QC thresholds and analysis settings
7. **Save checkpoints**: Write intermediate results at key steps

