# Standard Analysis Workflow and Common Tasks

Reviewed for Scanpy 1.12.4 / AnnData 0.13.4 on 2026-10-01. These snippets are
illustrative and require the named genes, groups and prior results to exist.
Use the tested CLI workflow for a runnable starting point. Counts, normalized
expression and `.raw` have distinct roles; see [upstream-review.md](upstream-review.md).


The seven workflow steps in full — quality control, normalization and preprocessing,
dimensionality reduction, clustering, marker gene identification, cell type annotation,
and saving results — followed by common tasks: publication-quality plots, trajectory
inference, pseudobulk differential expression between conditions, gene set scoring, and
batch correction.

## Standard Analysis Workflow

### 1. Quality Control

Identify and filter low-quality cells and genes:

```python
# Identify mitochondrial genes
adata.var['mt'] = adata.var_names.str.startswith('MT-')

# Calculate QC metrics
sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], percent_top=None, inplace=True)

# Visualize QC metrics
sc.pl.violin(adata, ['n_genes_by_counts', 'total_counts', 'pct_counts_mt'],
             jitter=0.4, multi_panel=True)

# Filter cells and genes
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
adata = adata[adata.obs.pct_counts_mt < 5, :].copy()  # Remove high MT% cells
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
# Preserve identified raw counts BEFORE normalization
adata.layers["counts"] = adata.X.copy()
# Normalize to 10,000 counts per cell
sc.pp.normalize_total(adata, target_sum=1e4)

# Log-transform
sc.pp.log1p(adata)

# Save the full log-normalized matrix for markers/plots, not raw counts
adata.raw = adata.copy()

# Identify highly variable genes
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.pl.highly_variable_genes(adata)

# Gene subsetting also subsets counts: retain full-gene data for pseudobulk
adata.write_h5ad("full_gene_lognorm.h5ad")
# Subset to highly variable genes
adata = adata[:, adata.var.highly_variable].copy()

# Optional only with biological justification; can remove true signal
# sc.pp.regress_out(adata, ['total_counts', 'pct_counts_mt'])

# Scale data
sc.pp.scale(adata, max_value=10)
```

### 3. Dimensionality Reduction

```python
# PCA
n_pcs = min(40, adata.n_obs - 1, adata.n_vars - 1)
sc.pp.pca(adata, n_comps=n_pcs, svd_solver='arpack')
sc.pl.pca_variance_ratio(adata, log=True)  # Check elbow plot

# Compute neighborhood graph
sc.pp.neighbors(adata, n_neighbors=10, n_pcs=n_pcs, use_rep='X_pca')

# UMAP for visualization
sc.tl.umap(adata)
sc.pl.umap(adata, color='total_counts')

# Alternative: t-SNE
sc.tl.tsne(adata)
```

### 4. Clustering

```python
# Leiden clustering (recommended)
sc.tl.leiden(adata, resolution=0.5, flavor='igraph', directed=False, n_iterations=2)
sc.pl.umap(adata, color='leiden', legend_loc='on data')

# Try multiple resolutions to find optimal granularity
for res in [0.3, 0.5, 0.8, 1.0]:
    sc.tl.leiden(adata, resolution=res, key_added=f'leiden_{res}')
```

### 5. Marker Gene Identification

Use `rank_genes_groups` for **exploratory cluster markers** only. Per-cell statistical tests inflate significance (often making p-values too small) because cells are not independent observations. For rigorous differential expression between conditions or samples, pseudobulk first (see below) and use **pydeseq2** or similar tools.

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
sc.set_figure_params(dpi=300, frameon=False, figsize=(5, 5))
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
sc.tl.diffmap(adata, n_comps=10)  # choose fewer for small datasets
sc.tl.dpt(adata, n_dcs=10)
sc.pl.umap(adata, color='dpt_pseudotime')
```

### Pseudobulk and Differential Expression Between Conditions

Pseudobulk by sample and cell type, then run proper DE (e.g., pydeseq2) rather than per-cell `rank_genes_groups`:

```python
# Load the FULL-GENE object, then transfer reviewed cell-type/sample metadata
# Group values must be unambiguous: the CLI handles underscore collisions.
# Aggregate counts by sample and cell type
pb = sc.get.aggregate(
    adata,
    by=['sample', 'cell_type'],
    func='sum',
    layer='counts',  # Required original counts, no normalized fallback
)
# pb.layers["sum"] is samples x genes; pb.X is None.
# Join condition/donor metadata, select one cell type and verify replication/design.
```

For quick exploratory comparisons within a cluster, `rank_genes_groups` is acceptable but interpret p-values cautiously:

```python
adata_subset = adata[adata.obs['cell_type'] == 'T cells'].copy()
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
