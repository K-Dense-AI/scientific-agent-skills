# Input/Output Operations

AnnData provides comprehensive I/O functionality for reading and writing data in various formats.

Since anndata 0.11, most `read_*` and `write_*` functions live in `anndata.io`. Top-level `read_h5ad` and `read_zarr` remain at `anndata` without deprecation warnings; other top-level imports still work but emit `FutureWarning`.

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
adata = ad.read_h5ad('data.h5ad', backed='r+')  # Read-write for X

# Backed mode enables working with datasets larger than RAM
# Only accessed data is loaded into memory
# In backed mode, only X updates are persisted; write a new file for obs/var/uns changes.
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
```

### Zarr
Hierarchical array storage format, optimized for cloud storage and parallel I/O.

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

#### Zarr v3 (anndata 0.12+)
```python
import anndata

# Default writes Zarr v2; opt into v3 and optional auto-sharding
anndata.settings.zarr_write_format = 3
anndata.settings.auto_shard_zarr_v3 = True  # experimental; independent of zarr_write_format

adata.write_zarr('data.zarr', chunks=(1000, 1000))
```

Zarr v3 writing is available in anndata 0.12, with structured-array exceptions and evolving performance guidance. Consolidated metadata is recommended for remote Zarr stores.

#### Remote Zarr access
Only open remote stores from trusted, expected locations. Prefer allowlisted HTTPS/S3/GCS paths or signed URLs, and avoid asking an agent to fetch arbitrary user-supplied URLs.

```python
import fsspec

# Access Zarr from an expected S3 location
store = fsspec.get_mapper('s3://bucket-name/data.zarr')
adata = ad.read_zarr(store)

# Access Zarr from a trusted HTTPS location
store = fsspec.get_mapper('https://example.com/data.zarr')
adata = ad.read_zarr(store)
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
```python
from anndata.io import read_excel

# Read Excel file
adata = read_excel('data.xlsx')

# Read specific sheet
adata = read_excel('data.xlsx', sheet='Sheet1')
```

### Matrix Market (MTX)
Common format for sparse matrices in genomics.

```python
from anndata.io import read_mtx

# Read MTX with associated files
# Requires: matrix.mtx, genes.tsv, barcodes.tsv
adata = read_mtx('matrix.mtx')

# Read with custom gene and barcode files
adata = read_mtx(
    'matrix.mtx',
    var_names='genes.tsv',
    obs_names='barcodes.tsv'
)

# Transpose if needed (MTX often has genes as rows)
adata = adata.T
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

### Loom
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
adata = read_umi_tools('counts.tsv')
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
# Write to CSV files (creates multiple files)
adata.write_csvs('output_dir/')

# This creates:
# - output_dir/X.csv (expression matrix)
# - output_dir/obs.csv (observation annotations)
# - output_dir/var.csv (variable annotations)
# - output_dir/uns.csv (unstructured annotations, if possible)

# Skip certain components
adata.write_csvs('output_dir/', skip_data=True)  # Skip X matrix
```

### Loom
```python
# Write to Loom format
adata.write_loom('output.loom')
```

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

# Write element to existing file
with h5py.File('data.h5ad', 'a') as f:
    write_elem(f, 'new_layer', adata.X.copy())
```

## Lazy Operations

For very large datasets, use lazy reading to avoid loading entire datasets. `read_lazy` is experimental and is designed for on-disk or in-cloud AnnData stores, including lazy `obs` and `var` access.

```python
from anndata.experimental import read_lazy

adata = read_lazy('large_data.zarr')
print(adata.obs.head())  # Does not require loading X
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
# Open in read-write mode for X updates
adata = ad.read_h5ad('data.h5ad', backed='r+')

# X updates can be persisted in backed mode
adata.X[0, 0] = 0

# Metadata changes are not persisted from backed mode; write a new file instead
adata_memory = adata.to_memory()
adata_memory.obs['new_column'] = values
adata_memory.write_h5ad('data_with_metadata.h5ad')
```

### Download from a trusted URL
Validate remote sources before downloading. Prefer local files or vetted object-store paths over arbitrary URLs.

```python
import anndata as ad
import urllib.request
from urllib.parse import urlparse

url = 'https://example.org/datasets/reference.h5ad'
parsed = urlparse(url)
trusted_hosts = {'example.org'}

if parsed.scheme != 'https' or parsed.netloc not in trusted_hosts:
    raise ValueError('Refusing to download from an untrusted host')

urllib.request.urlretrieve(url, 'reference.h5ad')
adata = ad.read_h5ad('reference.h5ad')
```

## Performance Tips

### Reading
- Use `backed='r'` for large files you only need to query
- Use `backed='r+'` only for `X` updates; write a new file for metadata changes
- H5AD format is generally fastest for random access
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
**Solution**: Load to memory and write a new file. Backed mode only persists updates to `X`.
```python
adata = adata.to_memory()
adata.obs['new_column'] = values
adata.write_h5ad('updated_file.h5ad')
```
