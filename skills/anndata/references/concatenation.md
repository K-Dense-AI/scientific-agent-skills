# Concatenating AnnData Objects

Combine multiple AnnData objects along either axis. Reviewed for AnnData 0.13.4. Match stable identifiers, species/genome build, units, and preprocessing before concatenating. Feature unions with sparse zero fill conflate unmeasured features with observed zeros; preserve a per-batch feature-presence record when that distinction matters.

## Basic Concatenation

### Concatenate along observations (stack cells/samples)
```python
import anndata as ad
import numpy as np

# Create multiple AnnData objects
adata1 = ad.AnnData(X=np.random.rand(100, 50))
adata2 = ad.AnnData(X=np.random.rand(150, 50))
adata3 = ad.AnnData(X=np.random.rand(200, 50))

# Concatenate along observations (axis=0, default)
adata_combined = ad.concat([adata1, adata2, adata3], axis=0, index_unique='-')

print(adata_combined.shape)  # (450, 50)
```

### Concatenate along variables (stack genes/features)
```python
# Create objects with same observations, different variables
adata1 = ad.AnnData(X=np.random.rand(100, 50))
adata2 = ad.AnnData(X=np.random.rand(100, 30))
adata3 = ad.AnnData(X=np.random.rand(100, 70))

# Concatenate along variables (axis=1)
adata_combined = ad.concat([adata1, adata2, adata3], axis=1)

print(adata_combined.shape)  # (100, 150)
```

## Join Types

### Inner join (intersection)
Keep only variables/observations present in all objects.

```python
import pandas as pd

# Create objects with different variables
adata1 = ad.AnnData(
    X=np.random.rand(100, 50),
    var=pd.DataFrame(index=[f'Gene_{i}' for i in range(50)])
)
adata2 = ad.AnnData(
    X=np.random.rand(150, 60),
    var=pd.DataFrame(index=[f'Gene_{i}' for i in range(10, 70)])
)

# Inner join: only genes 10-49 are kept (overlap)
adata_inner = ad.concat([adata1, adata2], join='inner')
print(adata_inner.n_vars)  # 40 genes (overlap)
```

### Outer join (union)
Keep all variables/observations, filling missing values.

```python
# Outer join: all genes are kept
adata_outer = ad.concat([adata1, adata2], join='outer')
print(adata_outer.n_vars)  # 70 genes (union)

# Missing values are filled with appropriate defaults:
# - 0 for sparse matrices
# - NaN for dense matrices
```

### Fill values for outer joins
```python
# Specify fill value for missing data
adata_filled = ad.concat([adata1, adata2], join='outer', fill_value=0)
```

## Tracking Data Sources

### Add batch labels
```python
# Label which object each observation came from
adata_combined = ad.concat(
    [adata1, adata2, adata3],
    label='batch',  # Column name for labels
    keys=['batch1', 'batch2', 'batch3']  # Labels for each object
)

print(adata_combined.obs['batch'].value_counts())
# batch1    100
# batch2    150
# batch3    200
```

### Automatic batch labels
```python
# If keys not provided, uses integer indices
adata_combined = ad.concat(
    [adata1, adata2, adata3],
    label='dataset'
)
# dataset column contains: 0, 1, 2
```

## Merge Strategies

Control how metadata from different objects is combined using the `merge` parameter.

### merge=None (default for either axis)
Exclude metadata on non-concatenation axis.

```python
# When concatenating observations, merge controls var-side annotations
adata1.var['gene_type'] = 'protein_coding'
adata2.var['gene_type'] = 'protein_coding'

# Variable index is kept; var annotation columns are dropped even if identical
adata_combined = ad.concat([adata1, adata2], merge=None)
```

### merge='same'
Keep metadata that is identical across all objects.

```python
adata1.var['chromosome'] = 'chr1'
adata2.var['chromosome'] = 'chr1'
adata1.var['type'] = 'protein_coding'
adata2.var['type'] = 'lncRNA'  # Different

# 'chromosome' is kept (same), 'type' is excluded (different)
adata_combined = ad.concat([adata1, adata2], merge='same')
```

### merge='unique'
Keep elements with one possible value across inputs after index alignment; this does not mean all entries within a column must be identical.

```python
adata1.var['gene_id'] = adata1.var_names
adata2.var['gene_id'] = adata2.var_names

# gene_id is kept (unique values for each key)
adata_combined = ad.concat([adata1, adata2], merge='unique')
```

### merge='first'
Take values from the first object containing each key.

```python
adata1.var['description'] = 'Desc1'
adata2.var['description'] = 'Desc2'

# Uses descriptions from adata1
adata_combined = ad.concat([adata1, adata2], merge='first')
```

### merge='only'
Keep metadata that appears in only one object.

```python
adata1.var['adata1_specific'] = 1
adata2.var['adata2_specific'] = 2

# Both metadata columns are kept
adata_combined = ad.concat([adata1, adata2], merge='only')
```

## Handling Index Conflicts

### Make indices unique
```python
import pandas as pd

# Create objects with overlapping observation names
adata1 = ad.AnnData(
    X=np.random.rand(3, 10),
    obs=pd.DataFrame(index=['cell_1', 'cell_2', 'cell_3'])
)
adata2 = ad.AnnData(
    X=np.random.rand(3, 10),
    obs=pd.DataFrame(index=['cell_1', 'cell_2', 'cell_3'])
)

# Make indices unique by appending batch keys
adata_combined = ad.concat(
    [adata1, adata2],
    label='batch',
    keys=['batch1', 'batch2'],
    index_unique='_'  # Separator for making indices unique
)

print(adata_combined.obs_names)
# ['cell_1_batch1', 'cell_2_batch1', 'cell_3_batch1',
#  'cell_1_batch2', 'cell_2_batch2', 'cell_3_batch2']
```

## Concatenating Layers

```python
# Objects with layers
adata1 = ad.AnnData(X=np.random.rand(100, 50))
adata1.layers['normalized'] = np.random.rand(100, 50)
adata1.layers['scaled'] = np.random.rand(100, 50)

adata2 = ad.AnnData(X=np.random.rand(150, 50))
adata2.layers['normalized'] = np.random.rand(150, 50)
adata2.layers['scaled'] = np.random.rand(150, 50)

# With join="inner", common layers are concatenated (outer joins union keys)
adata_combined = ad.concat([adata1, adata2])

print(adata_combined.layers.keys())
# Contains None (X), 'normalized', and 'scaled' in AnnData 0.13.4
```

## Concatenating Multi-dimensional Annotations

### obsm/varm
```python
# Objects with embeddings
adata1.obsm['X_pca'] = np.random.rand(100, 50)
adata2.obsm['X_pca'] = np.random.rand(150, 50)

# obsm is concatenated along observation axis
adata_combined = ad.concat([adata1, adata2])
print(adata_combined.obsm['X_pca'].shape)  # (250, 50)
```

### obsp/varp (pairwise annotations)
```python
from scipy.sparse import csr_matrix

# Pairwise matrices
adata1.obsp['connectivities'] = csr_matrix((100, 100))
adata2.obsp['connectivities'] = csr_matrix((150, 150))

# By default, obsp is NOT concatenated (set pairwise=True to include)
adata_combined = ad.concat([adata1, adata2])
# adata_combined.obsp is empty

# Include pairwise data (creates block diagonal matrix)
adata_combined = ad.concat([adata1, adata2], pairwise=True)
print(adata_combined.obsp['connectivities'].shape)  # (250, 250)
```

## Concatenating uns (unstructured)

Unstructured metadata is merged recursively:

```python
adata1.uns['experiment'] = {'date': '2025-01-01', 'batch': 'A'}
adata2.uns['experiment'] = {'date': '2025-01-01', 'batch': 'B'}

# Using merge='unique' for uns
adata_combined = ad.concat([adata1, adata2], uns_merge='unique')
# 'date' is kept; conflicting 'batch' is excluded
```

## Lazy Concatenation (AnnCollection)

For very large datasets, use `AnnCollection` to lazily concatenate AnnData objects along the observation axis. This API is experimental; use backed AnnData objects when the inputs are stored in `.h5ad` files.

```python
import anndata as ad
from anndata.experimental import AnnCollection

files = ['data1.h5ad', 'data2.h5ad', 'data3.h5ad']
backed_adatas = [ad.read_h5ad(path, backed='r') for path in files]

collection = AnnCollection(
    backed_adatas,
    join_obs='outer',
    join_vars='inner',
    label='dataset',
    keys=['dataset1', 'dataset2', 'dataset3']
)

# Access data lazily
print(collection.n_obs)  # Total observations
print(collection.obs.head())  # Metadata loaded, not X

# Collection conversion contains annotations only; X is None.
metadata_only = collection.to_adata()

# A selected view can gather X, but 0.13.4 default conversion may fail because
# X also appears in layers[None]. This workaround EXPLICITLY omits all named layers.
selected = collection[:100, :].to_adata(ignore_layers=True)
# This is not a full-fidelity conversion (var metadata/raw/uns are not restored).
```

### Working with AnnCollection
```python
# Subset without loading data
subset = collection[collection.obs['cell_type'] == 'T cell']

# Indexing is by observations/variables, not source dataset.
first_observation = collection[0, :]
# Keep the original input list to iterate through source datasets.
for source in backed_adatas:
    print(source.shape)
# After materializing needed subsets:
for source in backed_adatas:
    source.file.close()
```

## Concatenation on Disk

For datasets too large for memory, use experimental `concat_on_disk`.
`max_loaded_elems` limits sparse processing; dense input uses Dask. Pairwise
concatenation is not implemented here. Reopen the result and compare it with
`ad.concat` on a representative subset before committing a large workflow:

```python
import anndata as ad
from anndata.experimental import concat_on_disk

# Concatenate without loading into memory
concat_on_disk(
    ['data1.h5ad', 'data2.h5ad', 'data3.h5ad'],
    'combined.h5ad',
    join='outer',
    label='source',
    keys=['one', 'two', 'three'],
    index_unique='-',
    max_loaded_elems=1_000_000
)

# Load result in backed mode
adata = ad.read_h5ad('combined.h5ad', backed='r')
```

## Common Concatenation Patterns

### Combine technical replicates
```python
# Multiple runs of the same samples
replicates = [adata_run1, adata_run2, adata_run3]
adata_combined = ad.concat(
    replicates,
    label='technical_replicate',
    keys=['rep1', 'rep2', 'rep3'],
    join='inner'  # Keep only genes measured in all runs
)
```

### Combine batches from experiment
```python
# Different experimental batches
batches = [adata_batch1, adata_batch2, adata_batch3]
adata_combined = ad.concat(
    batches,
    label='batch',
    keys=['batch1', 'batch2', 'batch3'],
    join='outer'  # Keep all genes
)

# Later: apply batch correction
```

### Merge multi-modal data
```python
# Different measurement modalities (e.g., RNA + protein)
adata_rna = ad.AnnData(X=np.random.rand(100, 2000))
adata_protein = ad.AnnData(X=np.random.rand(100, 50))

# Concatenate along variables to combine modalities
adata_multimodal = ad.concat([adata_rna, adata_protein], axis=1)

# Add labels to distinguish modalities
adata_multimodal.var['modality'] = ['RNA'] * 2000 + ['protein'] * 50
```

## Best Practices

1. **Check compatibility before concatenating**
```python
# Verify shapes are compatible
print([adata.n_vars for adata in [adata1, adata2, adata3]])

# Check variable names match
print([set(adata.var_names) for adata in [adata1, adata2, adata3]])
```

2. **Use appropriate join type**
- `inner`: When you need the same features across all samples (most stringent)
- `outer`: When you want to preserve all features (most inclusive)

3. **Track data sources**
Always use `label` and `keys` to track which observations came from which dataset.

4. **Consider memory usage**
- For large datasets, use `AnnCollection` or `concat_on_disk`
- Consider backed mode for the result

5. **Handle batch effects**
Concatenation does not estimate batch effects. Choose an analysis method based on
experimental design and matrix semantics; automatic correction can erase biology
when batch and condition are confounded. See the scanpy skill for analysis.

6. **Validate results**
```python
# Check dimensions
print(adata_combined.shape)

# Check batch distribution
print(adata_combined.obs['batch'].value_counts())

# Verify metadata integrity
print(adata_combined.var.head())
print(adata_combined.obs.head())
```

`pairwise=True` creates block-diagonal graphs with no cross-batch neighbors; recompute
a graph after integration when cross-batch relationships are needed. `axis=1` aligns
observations by name but does not make RNA counts and protein values statistically
comparable; preserve modality and use a MuData container for separate matrices.

Sources: [concat](https://anndata.readthedocs.io/en/stable/generated/anndata.concat.html),
[AnnCollection](https://anndata.readthedocs.io/en/stable/generated/anndata.experimental.AnnCollection.html),
[to_adata](https://anndata.readthedocs.io/en/stable/generated/anndata.experimental.AnnCollection.to_adata.html),
[concat_on_disk](https://anndata.readthedocs.io/en/stable/generated/anndata.experimental.concat_on_disk.html),
and installed 0.13.4 source. Biological and user-file examples are illustrative.
