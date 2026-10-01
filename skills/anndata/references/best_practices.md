# Best Practices

Guidelines reviewed for AnnData 0.13.4. User-file paths and application-specific `process`/`analyze` functions are illustrative. Small synthetic tests verify the data-structure and native-I/O contracts; they do not validate biological analysis.

## Memory Management

### Use sparse matrices for sparse data
```python
import numpy as np
from scipy.sparse import csr_matrix, csc_matrix
import anndata as ad

# Check data sparsity
data = np.random.rand(1000, 2000)
sparsity = 1 - np.count_nonzero(data) / data.size
print(f"Sparsity: {sparsity:.2%}")

# Convert to sparse if >50% zeros (anndata 0.12+ requires csr or csc)
if sparsity > 0.5:
    adata = ad.AnnData(X=csr_matrix(data))
else:
    adata = ad.AnnData(X=data)

# Measure actual memory: data.nbytes versus CSR data/indices/indptr.nbytes.
# Density, dtype, index width, and temporary arrays determine savings.
```

### Convert strings to categoricals
```python
# Inefficient: string columns use lots of memory
adata.obs['cell_type'] = ['Type_A', 'Type_B', 'Type_C'] * 333 + ['Type_A']

# Efficient: convert to categorical
adata.obs['cell_type'] = adata.obs['cell_type'].astype('category')

# Convert all string columns
adata.strings_to_categoricals()

# Check obs.memory_usage(deep=True); savings depend on category cardinality.
```

### Use backed mode for large datasets
```python
# Don't load entire dataset into memory
adata = ad.read_h5ad('large_dataset.h5ad', backed='r')

# Work with metadata
filtered = adata[adata.obs['quality'] > 0.8]

# Load only filtered subset
adata_subset = filtered.to_memory()

# Benefits: Work with datasets larger than RAM
```

## Views vs Copies

### Understanding views
```python
# Subsetting creates a view by default
subset = adata[0:100, :]
print(subset.is_view)  # True

# Views defer subset copies. In 0.13, .X also uses copy-on-write.
# Modification can allocate a full subset copy; make ownership explicit.

# Check if object is a view
if adata.is_view:
    adata = adata.copy()  # Make independent
```

### When to use views
```python
# Good: Read-only operations on subsets
mean_expr = adata[adata.obs['cell_type'] == 'T cell'].X.mean()

# Good: Temporary analysis
temp_subset = adata[:100, :]
result = analyze(temp_subset.X)
```

### When to use copies
```python
# Create independent copy for modifications
adata_filtered = adata[keep_cells, :].copy()

# Safe to modify without affecting original
adata_filtered.obs['new_column'] = values

# Always copy when:
# - Storing subset for later use
# - Modifying subset data
# - Passing to function that modifies data
```

## Data Storage Best Practices

### Choose the right format

**H5AD (HDF5) - Default choice**
```python
adata.write_h5ad('data.h5ad', compression='gzip')
```
- Fast random access
- Supports backed mode
- Good compression
- Best for: Most use cases

**Zarr - Cloud and parallel access**
```python
import anndata

# AnnData 0.13.4 defaults to Zarr v3 with automatic sharding.
adata.write_zarr('data.zarr', chunks=(100, 100))
```
- Excellent for cloud storage (S3, GCS)
- Supports parallel I/O and default Zarr v3 sharding in 0.13.4
- Good compression
- Best for: Large datasets, cloud workflows, parallel processing

**CSV - Interoperability**
```python
adata.write_csvs('output_dir/', skip_data=False)
```
- Human readable
- Interoperable tabular export; loses parts of AnnData and may densify X
- Large file sizes, slow
- Best for: Sharing with non-Python tools, small datasets

### Optimize file size
```python
# Before saving, optimize:

# 1. Convert to sparse if appropriate
from scipy.sparse import csr_matrix, issparse
if not issparse(adata.X):
    density = np.count_nonzero(adata.X) / adata.X.size
    if density < 0.5:
        adata.X = csr_matrix(adata.X)

# 2. Convert strings to categoricals
adata.strings_to_categoricals()

# 3. Use compression
adata.write_h5ad('data.h5ad', compression='gzip', compression_opts=9)

# Compare actual sizes and read/write times; there is no universal reduction factor.
```

## Backed Mode Strategies

### Read-only analysis
```python
# Open in read-only backed mode
adata = ad.read_h5ad('data.h5ad', backed='r')

# Perform filtering without loading data
high_quality = adata[adata.obs['quality_score'] > 0.8]

# Load only filtered data
adata_filtered = high_quality.to_memory()
```

### Read-write modifications
```python
# Open in read-write backed mode
adata = ad.read_h5ad('data.h5ad', backed='r+')

# Dense HDF5 X supports in-place writes; backed sparse X does not in 0.13.
import h5py
if isinstance(adata.X, h5py.Dataset):
    adata.X[0, 0] = 0

# Metadata changes are not persisted from backed mode; load and write a new file
adata_memory = adata.to_memory()
adata_memory.obs['new_annotation'] = values
adata.file.close()
adata_memory.write_h5ad('data_with_annotations.h5ad')
```

### Chunked processing
```python
# Process large dataset in chunks
adata = ad.read_h5ad('huge_dataset.h5ad', backed='r')

results = []
chunk_size = 1000

for i in range(0, adata.n_obs, chunk_size):
    chunk = adata[i:i+chunk_size, :].to_memory()
    result = process(chunk)
    results.append(result)

final_result = combine(results)
```

## Performance Optimization

### Subsetting performance
```python
# Boolean mask: clear and aligned to obs
mask = np.array(adata.obs['quality'] > 0.5)
subset = adata[mask, :]

# A boolean Series is also supported; it does not inherently create a view chain
subset = adata[adata.obs['quality'] > 0.5, :]

# Integer positions: useful when already available; benchmark actual workloads
indices = np.where(adata.obs['quality'] > 0.5)[0]
subset = adata[indices, :]
```

### Avoid repeated subsetting
```python
# Inefficient: Multiple subset operations
for cell_type in ['A', 'B', 'C']:
    subset = adata[adata.obs['cell_type'] == cell_type]
    process(subset)

# Alternative: reuse groups when several operations need the same grouping
groups = adata.obs.groupby('cell_type', observed=True).groups
for cell_type, indices in groups.items():
    subset = adata[indices, :]
    process(subset)
```

### Use chunked operations for large matrices
```python
# Process X in chunks
for chunk, start, stop in adata.chunked_X(chunk_size=1000):
    result = compute(chunk)

# More memory efficient than loading full X
```

## Working with Raw Data

### Store raw before filtering
```python
# Original data with all genes
adata = ad.AnnData(X=counts)

# Store raw before filtering
adata.raw = adata.copy()

# Filter to highly variable genes
adata = adata[:, adata.var['highly_variable']]

# Later: access original data
original_expression = adata.raw.X
all_genes = adata.raw.var_names
```

### When to use raw
```python
# Use raw for:
# - Differential expression on filtered genes
# - Visualization of specific genes not in filtered set
# - Accessing the snapshot values, which may be counts OR normalized data
# Check raw_semantics; .raw is not automatically counts or a full object backup.

# Access raw data
if adata.raw is not None:
    gene_expr = adata.raw[:, 'GENE_NAME'].X
else:
    gene_expr = adata[:, 'GENE_NAME'].X
```

## Metadata Management

### Naming conventions
```python
# Consistent naming improves usability

# Observation metadata (obs):
# - cell_id, sample_id
# - cell_type, tissue, condition
# - n_genes, n_counts, percent_mito
# - cluster, leiden, louvain

# Variable metadata (var):
# - gene_id, gene_name
# - highly_variable, n_cells
# - mean_expression, dispersion

# Embeddings (obsm):
# - X_pca, X_umap, X_tsne
# - X_diffmap, X_draw_graph_fr

# Follow conventions from scanpy/scverse ecosystem
```

### Document metadata
```python
# Store metadata descriptions in uns
adata.uns['metadata_descriptions'] = {
    'cell_type': 'Cell type annotation from automated clustering',
    'doublet_score': 'Scrublet predicted doublet score; higher suggests a doublet',
    'batch': 'Experimental batch identifier'
}

# Store processing history
adata.uns['processing_steps'] = [
    'Raw counts loaded from 10X',
    'Filtered: n_genes > 200, n_counts < 50000',
    'Normalized to 10000 counts per cell',
    'Log transformed'
]
```

## Reproducibility

### Set random seeds
```python
import numpy as np

# Set seed for reproducible results
np.random.seed(42)

# Document in uns
adata.uns['random_seed'] = 42
```

### Store parameters
```python
# Store analysis parameters in uns
adata.uns['pca'] = {
    'n_comps': 50,
    'svd_solver': 'arpack',
    'random_state': 42
}

adata.uns['neighbors'] = {
    'n_neighbors': 15,
    'n_pcs': 50,
    'metric': 'euclidean',
    'method': 'umap'
}
```

### Version tracking
```python
import sys
from importlib.metadata import version

# Store package versions (anndata.__version__ deprecated in 0.12.3)
adata.uns['versions'] = {
    'anndata': version('anndata'),
    'scanpy': version('scanpy'),
    'numpy': version('numpy'),
    'python': sys.version,
}
```

## Error Handling

### Check data validity
```python
# Verify dimensions
assert adata.n_obs == len(adata.obs)
assert adata.n_vars == len(adata.var)
assert adata.X.shape == (adata.n_obs, adata.n_vars)

# Check for NaN values
has_nan = np.isnan(adata.X.data).any() if issparse(adata.X) else np.isnan(adata.X).any()
if has_nan:
    print("Warning: Data contains NaN values")

# Check for negative values (if counts expected)
has_negative = (adata.X.data < 0).any() if issparse(adata.X) else (adata.X < 0).any()
if has_negative:
    print("Warning: Data contains negative values")
```

### Validate metadata
```python
# Check for missing values
missing_obs = adata.obs.isnull().sum()
if missing_obs.any():
    print("Missing values in obs:")
    print(missing_obs[missing_obs > 0])

# Verify indices are unique
assert adata.obs_names.is_unique, "Observation names not unique"
assert adata.var_names.is_unique, "Variable names not unique"

# Check metadata alignment
assert len(adata.obs) == adata.n_obs
assert len(adata.var) == adata.n_vars
```

## Integration with Other Tools

### Scanpy integration
```python
import scanpy as sc

# AnnData is native format for scanpy
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata)
sc.pp.pca(adata)
sc.pp.neighbors(adata)
sc.tl.umap(adata)
```

### Pandas integration
```python
import pandas as pd

# Convert only a manageable subset: to_df densifies sparse data
df = adata[:100, :100].to_df()

# Create from DataFrame
adata = ad.AnnData(df)

# Work with metadata as DataFrames
assert external_metadata.index.is_unique
adata.obs = adata.obs.join(external_metadata, how='left', validate='one_to_one')
```

### PyTorch integration

`AnnLoader` is deprecated; use the official [annbatch.Loader migration tutorial](https://anndata.readthedocs.io/en/stable/tutorials/notebooks/annbatch.html).
No training, accelerator, or third-party version combination was executed here.

## Common Pitfalls

### Pitfall 1: Modifying views
```python
# In 0.13, assigning .X to a view materializes that view (copy-on-write).
subset = adata[:100, :]
subset.X = new_data  # Can allocate unexpectedly; older releases behaved differently

# Correct: Copy before modifying
subset = adata[:100, :].copy()
subset.X = new_data  # Independent copy
```

### Pitfall 2: Index misalignment
```python
# Wrong: Assuming order matches
external_data = pd.read_csv('data.csv')
adata.obs['new_col'] = external_data['values']  # May misalign!

# Correct: Align on index
adata.obs['new_col'] = external_data.set_index('cell_id').loc[adata.obs_names, 'values']
```

### Pitfall 3: Mixing sparse and dense
```python
# SciPy sparse + nonzero scalar raises NotImplementedError.
# Adding 1 to .data alone changes only stored entries, NOT every matrix element.
# A zero-preserving operation such as log1p can safely preserve sparsity:
from scipy.sparse import issparse
if issparse(adata.X):
    result = adata.X.copy()
    result.data = np.log1p(result.data)
else:
    result = np.log1p(adata.X)
```

### Pitfall 4: Not handling views
```python
# An in-memory view keeps its parent alive even if the local name is deleted.
subset = adata[mask, :]
del adata
# Copy when independent ownership is required:
subset = subset.copy()
# For backed data, keep the HDF5 file open until .to_memory() completes.
```

### Pitfall 5: Ignoring memory constraints
```python
# Wrong: Loading huge dataset into memory
adata = ad.read_h5ad('100GB_file.h5ad')  # OOM error!

# Correct: Use backed mode
adata = ad.read_h5ad('100GB_file.h5ad', backed='r')
subset = adata[adata.obs['keep']].to_memory()
```

## Workflow Example

Complete best-practices workflow:

```python
import anndata as ad
import numpy as np
from scipy.sparse import csr_matrix, issparse

# 1. Load with backed mode if large
source = ad.read_h5ad('data.h5ad', backed='r')
adata = source

# 2. Quick metadata check without loading data
print(f"Dataset: {adata.n_obs} cells × {adata.n_vars} genes")

# 3. Filter based on metadata
high_quality = adata[adata.obs['quality_score'] > 0.8]

# 4. Load filtered subset to memory
adata = high_quality.to_memory()
source.file.close()

# 5. Convert to optimal storage types (csr/csc sparse only since 0.12)
adata.strings_to_categoricals()
if not issparse(adata.X):
    density = np.count_nonzero(adata.X) / adata.X.size
    if density < 0.5:
        adata.X = csr_matrix(adata.X)

# 6. Store raw before filtering genes
adata.raw = adata.copy()

# 7. Filter to highly variable genes
adata = adata[:, adata.var['highly_variable']].copy()

# 8. Document processing
adata.uns['processing'] = {
    'filtered': 'quality_score > 0.8',
    'n_hvg': adata.n_vars,
    'matrix_semantics': 'retain and document input transformations'
}

# 9. Save optimized
adata.write_h5ad('processed.h5ad', compression='gzip')
```

## Provenance and compatibility

- `raw` retains its feature axis on gene filtering, but follows cell filtering. Named
  layers follow both axes. Store counts separately if later analyses need all genes.
- AnnData 0.13 includes X as `layers[None]`; use `key is not None` for named-layer
  iteration and `layers.clear(keep_x=True)` to retain X. Check third-party exporters
  before upgrading: this change breaks some older string-key assumptions.
- Keep stable feature IDs separate from symbols; making duplicate names unique is
  a syntactic repair, not biological deduplication. Record species and genome build.
- H5AD backed reads can still load metadata and layers; Zarr `read_zarr` is eager.
  Budget memory before `to_memory`, `to_df`, transposition, scaling, or dense export.
- Reopen native output and compare identifiers in order, dtypes, categories, selected
  matrix values, named layers, raw gene IDs, and source/transformation provenance.

Sources: [AnnData 0.13 release notes](https://anndata.readthedocs.io/en/stable/release-notes/),
[raw](https://anndata.readthedocs.io/en/stable/generated/anndata.AnnData.raw.html),
[write_csvs](https://anndata.readthedocs.io/en/stable/generated/anndata.AnnData.write_csvs.html),
[read_h5ad](https://anndata.readthedocs.io/en/stable/generated/anndata.io.read_h5ad.html),
and installed AnnData 0.13.4 source.
