# Input/Output Operations

Reviewed against AnnData 0.13.4. Native H5AD/Zarr and small text/Excel fixtures were exercised; remote stores and 10X biological inputs below are illustrative. Preserve identifiers, matrix units, transformations, and source checksums through conversion.

Since anndata 0.11, most `read_*` and `write_*` functions live in `anndata.io`. Top-level `read_h5ad` and `read_zarr` remain supported; use `anndata.io` for other readers rather than compatibility aliases.

```python
import anndata as ad
from anndata.io import read_csv, read_mtx, read_loom, read_elem, write_elem
```

Avoid deprecated I/O aliases such as `ad.read`; use `ad.read_h5ad` or `anndata.io.read_h5ad` explicitly.

## Native Formats

### H5AD (HDF5-based)
The recommended native format for AnnData objects, providing efficient storage and fast access.

#### Writing H5AD files
```python
import anndata as ad

# Write to file
adata.write_h5ad('data.h5ad')

# Write with compression
adata.write_h5ad('data.h5ad', compression='gzip')

# Write with specific compression level (0-9, higher = more compression)
adata.write_h5ad('data.h5ad', compression='gzip', compression_opts=9)
```

#### Reading H5AD files
```python
# Read entire file into memory
adata = ad.read_h5ad('data.h5ad')

# Read in backed mode (lazy loading for large files)
adata = ad.read_h5ad('data.h5ad', backed='r')  # Read-only
adata.file.close()
# Alternatively (do not leave a read-only handle open on this file):
adata = ad.read_h5ad('data.h5ad', backed='r+')  # In-place dense X updates only
adata.file.close()

# Backed mode keeps X on disk; obs/var and named layers can still load into RAM.
# 0.13 removed backed sparse item assignment, even with r+.
# Write a new file for obs/var/uns or sparse-X changes.
```

#### Backed mode operations
```python
# Open in backed mode
adata = ad.read_h5ad('large_dataset.h5ad', backed='r')

# Access metadata without loading X into memory
print(adata.obs.head())
print(adata.var.head())

# Subset operations create views
subset = adata[:100, :500]  # View, no data loaded

# Load specific data into memory
X_subset = subset.X[:]  # Now loads this subset

# Convert entire backed object to memory
adata_memory = adata.to_memory()
adata.file.close()
```

### Zarr

`read_zarr` is eager; use experimental `read_lazy` for lazy arrays and annotations.
AnnData 0.13 requires the Zarr >=3 Python package and writes sharded Zarr format 3
by default. Format 2 stores can still be read. Chunk shape and shard size have
different effects; benchmark representative row/column access instead of assuming
a universal setting.

#### Writing Zarr
```python
# Write to Zarr store
adata.write_zarr('data.zarr')

# Write with specific chunks (important for performance)
adata.write_zarr('data.zarr', chunks=(100, 100))
```

#### Reading Zarr
```python
# Read Zarr store
adata = ad.read_zarr('data.zarr')
```

#### Zarr v3 defaults (AnnData 0.13.4)
```python
adata.write_zarr('data.zarr', chunks=(1000, 1000), consolidate_metadata=True)
```

The deprecated `settings.zarr_write_format` is scheduled for removal in 0.14.
If a downstream reader requires format 2, verify that compatibility separately;
do not confuse the Zarr package version with the storage format.

#### Remote Zarr access
Use the requested dataset location, with its provider credentials and suitable fsspec adapter (`s3fs` for S3, `gcsfs` for GCS). The following placeholder stores are illustrative and were not contacted. These examples use Zarr 3 `FsspecStore`; credentials should come from provider configuration, not source code.

```python
from zarr.storage import FsspecStore
from anndata.experimental import read_lazy

store = FsspecStore.from_url('s3://bucket-name/data.zarr', read_only=True)
adata = read_lazy(store)  # Verify provider/store support on a small slice first
```

## Alternative Input Formats

### CSV/TSV
```python
from anndata.io import read_csv

# Read CSV (genes as columns, cells as rows)
adata = read_csv('data.csv')

# Read with custom delimiter
adata = read_csv('data.tsv', delimiter='\t')

# Specify that first column is row names
adata = read_csv('data.csv', first_column_names=True)
```

### Excel

Requires `openpyxl` for `.xlsx`; first column supplies row names and first row supplies feature names. Validate numeric matrix dtype after importing.
```python
from anndata.io import read_excel

# Read Excel file
adata = read_excel('data.xlsx', sheet=0)  # sheet is required

# Read specific sheet
adata = read_excel('data.xlsx', sheet='Sheet1')
```

### Matrix Market (MTX)
Common format for sparse matrices in genomics.

```python
from anndata.io import read_mtx

import pandas as pd

# read_mtx reads ONLY the matrix; it has no obs_names/var_names arguments.
# For this explicit feature-by-cell input, transpose to cells by features.
adata = read_mtx('matrix.mtx').T
features = pd.read_csv('features.tsv', sep='\t', header=None, dtype=str)
barcodes = pd.read_csv('barcodes.tsv', sep='\t', header=None, dtype=str)
assert adata.shape == (len(barcodes), len(features))
adata.obs_names = barcodes[0].to_numpy()
adata.var_names = features[0].to_numpy()  # Stable IDs; keep symbols separately
adata.var['gene_symbol'] = features[1].to_numpy()
assert adata.obs_names.is_unique and adata.var_names.is_unique
```

### 10X Genomics formats
10X readers are provided by **scanpy**, not anndata. After loading, the result is a standard `AnnData` object.

```python
import scanpy as sc

# Read 10X h5 format
adata = sc.read_10x_h5('filtered_feature_bc_matrix.h5')

# Read 10X MTX directory
adata = sc.read_10x_mtx('filtered_feature_bc_matrix/')

# Specify genome if multiple present
adata = sc.read_10x_h5('data.h5', genome='GRCh38')
```

### Loom input

Requires `loompy`; `read_loom` is deprecated in 0.13 (legacy import still passed
a synthetic test with loompy 3.0.8). Use the actual source layer and annotation names; defaults
`CellID`/`Gene` do not match every Loom file. The format is lossy relative to
AnnData (for example, it is not a full `uns`/`raw` archive).

```python
from anndata.io import read_loom

# Read Loom file
adata = read_loom('data.loom')

# Read with specific observation and variable annotations
adata = read_loom(
    'data.loom',
    obs_names='CellID',
    var_names='Gene'
)
```

### Text files
```python
from anndata.io import read_text

# Read generic text file
adata = read_text('data.txt', delimiter='\t')

# Read with custom parameters
adata = read_text(
    'data.txt',
    delimiter=',',
    first_column_names=True,
    dtype='float32'
)
```

### UMI tools
```python
from anndata.io import read_umi_tools

# Read UMI tools format
adata = read_umi_tools('counts.tsv.gz')  # Long table: gene, cell, count columns
```

### HDF5 (generic)
```python
from anndata.io import read_hdf

# Read from HDF5 file (not h5ad format)
adata = read_hdf('data.h5', key='dataset')
```

## Alternative Output Formats

### CSV
```python
# Explicitly include X; skip_data=True is the default. Sparse X is densified.
adata.write_csvs('output_dir/', skip_data=False)

# This creates:
# - output_dir/X.csv (expression matrix)
# - output_dir/obs.csv (observation annotations)
# - output_dir/var.csv (variable annotations)
# - output_dir/obsm.csv and varm.csv
# - output_dir/uns/<key>.csv (supported unstructured annotations only)
# This export cannot reconstruct the complete AnnData object.

# Skip certain components
adata.write_csvs('output_dir/', skip_data=True)  # Skip X matrix
```

### Loom output

`write_loom` is deprecated in AnnData 0.13. With AnnData 0.13.4 and loompy 3.0.8,
a synthetic export also failed because the writer passes the `layers[None]` key
to loompy (`AttributeError: 'NoneType' object has no attribute 'startswith'`).
Use `write_h5ad`/`write_zarr` for the complete object; legacy Loom conversion needs
an independently tested compatible environment and a field-by-field audit.
Do not delete `layers[None]` to bypass this error: it deletes X.

## Reading Specific Elements

For fine-grained control, read specific elements from an open store:

```python
import h5py
from anndata.io import read_elem

# Read just observation annotations from an h5ad file
with h5py.File('data.h5ad', 'r') as f:
    obs = read_elem(f['obs'])
    layer = read_elem(f['layers/normalized'])
    params = read_elem(f['uns/pca'])
```

## Writing Specific Elements

```python
from anndata.io import write_elem
import h5py

# Work on a copy of the native file. A layer belongs under /layers, not the root.
# Match both axes and use an unused string key without '/'.
with h5py.File('data.h5ad', 'r+') as f:
    layers = f['layers']
    assert 'new_layer' not in layers
    write_elem(layers, 'new_layer', adata.X.copy())
reopened = ad.read_h5ad('data.h5ad')
assert reopened.layers['new_layer'].shape == reopened.shape
```

## Lazy Operations

For very large datasets, use lazy reading to avoid loading entire datasets. `read_lazy` is experimental and is designed for on-disk or in-cloud AnnData stores, including lazy `obs` and `var` access.

```python
from anndata.experimental import read_lazy

adata = read_lazy('large_data.zarr')
print(adata.obs.iloc[:5].to_memory())  # Dataset2D is not a pandas DataFrame
```

For element-level control, use `read_elem_lazy` on an open store:

```python
import h5py
from anndata.experimental import read_elem_lazy

# Lazy read from an open store (returns dask-backed array)
with h5py.File('large_data.h5ad', 'r') as f:
    X_lazy = read_elem_lazy(f['X'])
    subset = X_lazy[:100, :100].compute()
```

## Common I/O Patterns

### Convert between formats
```python
from anndata.io import read_mtx, read_csv

# MTX to H5AD
adata = read_mtx('matrix.mtx').T
adata.write_h5ad('data.h5ad')

# CSV to H5AD
adata = read_csv('data.csv')
adata.write_h5ad('data.h5ad')

# H5AD to Zarr
adata = ad.read_h5ad('data.h5ad')
adata.write_zarr('data.zarr')
```

### Load metadata without data
```python
# Backed mode allows inspecting metadata without loading X
adata = ad.read_h5ad('large_file.h5ad', backed='r')
print(f"Dataset contains {adata.n_obs} observations and {adata.n_vars} variables")
print(adata.obs.columns)
print(adata.var.columns)
# X is not loaded into memory
```

### Update backed data or write a new file
```python
# Open in read-write mode for dense X updates
import h5py
adata = ad.read_h5ad('data.h5ad', backed='r+')

# Only dense HDF5 X supports this in 0.13; backed sparse assignment raises TypeError.
if isinstance(adata.X, h5py.Dataset):
    adata.X[0, 0] = 0

# Metadata changes are not persisted from backed mode; write a new file instead
adata_memory = adata.to_memory()
adata_memory.obs['new_column'] = values
adata.file.close()
adata_memory.write_h5ad('data_with_metadata.h5ad')
```

### Remote provenance

Download the dataset from its documented publisher location or object store;
record its accession/release, exact URI, checksum, and measurement conventions.
Validate the completed local file before opening it. A URL and valid HDF5 header
alone do not establish biological identity or count semantics. No particular
remote dataset, credentials, or provider was exercised for this refresh.

## Performance Tips

### Reading
- Use `backed='r'` for large files you only need to query
- Use `backed='r+'` only for dense `X` updates; write a new file for sparse/metadata changes
- Benchmark H5AD and Zarr for actual density, layout, compression, and access pattern
- Zarr is better for cloud storage and parallel access
- Consider compression for storage, but note it may slow down reading

### Writing
- Use compression for long-term storage: `compression='gzip'` or `compression='lzf'`
- LZF compression is faster but compresses less than GZIP
- For Zarr, tune chunk sizes based on access patterns:
  - Larger chunks for sequential reads
  - Smaller chunks for random access
- Convert string columns to categorical before writing (smaller files)

### Memory management
```python
# Convert strings to categoricals (reduces file size and memory)
adata.strings_to_categoricals()
adata.write_h5ad('data.h5ad')

# Use sparse matrices for sparse data
from scipy.sparse import csr_matrix
if isinstance(adata.X, np.ndarray):
    density = np.count_nonzero(adata.X) / adata.X.size
    if density < 0.5:  # If more than 50% zeros
        adata.X = csr_matrix(adata.X)
```

## Handling Large Datasets

### Strategy 1: Backed mode
```python
# Work with dataset larger than RAM
adata = ad.read_h5ad('100GB_file.h5ad', backed='r')

# Filter based on metadata (fast, no data loading)
filtered = adata[adata.obs['quality_score'] > 0.8]

# Load filtered subset into memory
adata_memory = filtered.to_memory()
```

### Strategy 2: Chunked processing
```python
# Process data in chunks
adata = ad.read_h5ad('large_file.h5ad', backed='r')

chunk_size = 1000
results = []

for i in range(0, adata.n_obs, chunk_size):
    chunk = adata[i:i+chunk_size, :].to_memory()
    # Process chunk
    result = process(chunk)
    results.append(result)
```

### Strategy 3: Use AnnCollection
```python
import anndata as ad
from anndata.experimental import AnnCollection

# Create backed objects, then lazily concatenate along observations
adatas = [
    ad.read_h5ad(f'dataset_{i}.h5ad', backed='r')
    for i in range(10)
]
collection = AnnCollection(
    adatas,
    join_obs='inner',
    join_vars='inner'
)

# Process collection lazily
# Data is loaded only when accessed
```

## Common Issues and Solutions

### Issue: Out of memory when reading
**Solution**: Use backed mode or read in chunks
```python
adata = ad.read_h5ad('file.h5ad', backed='r')
```

### Issue: Slow reading from cloud storage
**Solution**: Use Zarr format with appropriate chunking
```python
adata.write_zarr('data.zarr', chunks=(1000, 1000))
```

### Issue: Large file sizes
**Solution**: Use compression and convert to sparse/categorical
```python
adata.strings_to_categoricals()
from scipy.sparse import csr_matrix
adata.X = csr_matrix(adata.X)
adata.write_h5ad('compressed.h5ad', compression='gzip')
```

### Issue: Cannot modify backed metadata
**Solution**: Materialize a manageable subset and write a new file. Backed mode does not automatically save metadata; sparse X item updates are unsupported in 0.13.
```python
source = adata
try:
    adata = source.to_memory()
finally:
    source.file.close()
adata.obs['new_column'] = values
adata.write_h5ad('updated_file.h5ad')
```

## Store lifetime and verification

Keep a backed HDF5 object's file open until all views/chunks have been materialized;
close it in `finally`. `read_lazy` over HDF5 has the same lifetime requirement.
For every output, reopen it and compare shape, index order, selected values,
categoricals, named layers, raw feature names, and relevant `uns` provenance.
Native formats use versioned AnnData encodings; a root-level arbitrary dataset
is not a named layer.

Sources: [I/O API](https://anndata.readthedocs.io/en/stable/api.html),
[read_h5ad](https://anndata.readthedocs.io/en/stable/generated/anndata.io.read_h5ad.html),
[read_mtx](https://anndata.readthedocs.io/en/stable/generated/anndata.io.read_mtx.html),
[read_lazy](https://anndata.readthedocs.io/en/stable/generated/anndata.experimental.read_lazy.html),
[write_csvs](https://anndata.readthedocs.io/en/stable/generated/anndata.AnnData.write_csvs.html),
[on-disk specification](https://anndata.readthedocs.io/en/stable/fileformat-prose.html),
and installed AnnData 0.13.4 I/O source.
