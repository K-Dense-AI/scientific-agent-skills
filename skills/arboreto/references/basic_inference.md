# Basic GRN inference

Use the exact environment and pre-import Dask configuration in `SKILL.md`.
All file/data examples below are illustrative adapters; the equivalent dense and
CSC API calls were executed on a synthetic fixture during the 2026-09-30 review.
Put inference calls inside a main guard when Dask creates worker processes.

## Data contract

Arboreto accepts a pandas DataFrame, dense two-dimensional NumPy array, or
`scipy.sparse.csc_matrix`. Rows are observations and columns are genes in all
three cases. For arrays/matrices, `gene_names` must match every column in order;
for DataFrames, Arboreto takes gene names from the columns.

- Use unique, nonempty gene identifiers in the same species and namespace as TFs.
- Remove sample labels, annotations, and other non-expression columns explicitly.
- Check finite numeric values, dimensions, TF overlap, and sufficient variation.
- Select and document the intended preprocessing upstream. Arboreto does not
  perform cell QC, normalize libraries, correct batches, or identify cell types.
- TF restriction limits predictors, not targets: every expression column is still
  modeled as a target, with self-prediction excluded.

```python
import numpy as np
import pandas as pd

# This example file has observation IDs in its first column.
expression_matrix = pd.read_csv("expression_data.tsv", sep="\t", index_col=0)
assert expression_matrix.columns.is_unique
assert expression_matrix.shape[0] >= 2 and expression_matrix.shape[1] >= 2
assert np.isfinite(expression_matrix.to_numpy(dtype=float)).all()
```

If there is no row-ID column, omit `index_col=0`; otherwise it would silently
remove the first gene. The bundled wrapper supports `--index-col 0` and checks
raw headers before pandas can suffix duplicate names.

## TF input

`arboreto.utils.load_tf_names(path)` reads one line per TF and strips whitespace;
it does not remove empty lines, deduplicate, or resolve identifiers. Normalize
those explicitly and report how many names overlap:

```python
from arboreto.utils import load_tf_names

requested = list(dict.fromkeys(tf for tf in load_tf_names("tfs.txt") if tf))
tf_names = [tf for tf in requested if tf in expression_matrix.columns]
if not tf_names:
    raise ValueError("No TFs match expression column names")
print(f"[OK] {len(tf_names)} of {len(requested)} TF names match")
```

Use a Python list, not a NumPy array, for `tf_names` (the upstream sentinel check
compares it to `'all'`). `None` or `'all'` uses every expression gene as a
candidate regulator. An empty list or a list with no overlap raises `ValueError`.
With only one matched TF, its own target fit has no remaining predictor and is
skipped with warnings; interpret target coverage accordingly.

## Dense and sparse adapters

These snippets assume an explicitly managed Dask `client`, loaded expression
matrix, and matching `tf_names`:

```python
from arboreto.algo import grnboost2
from scipy.sparse import csc_matrix

genes = expression_matrix.columns.tolist()
array = expression_matrix.to_numpy(dtype=float)
network = grnboost2(expression_data=array, gene_names=genes, tf_names=tf_names,
                    seed=777, client_or_address=client)

sparse_matrix = csc_matrix(array)
network_sparse = grnboost2(expression_data=sparse_matrix, gene_names=genes,
                           tf_names=tf_names, seed=777, client_or_address=client)
```

Converting an already-dense array to CSC is only an input-format example; it does
not avoid the initial dense allocation. Load large sparse data as sparse and
preserve it. Use `csc_matrix`, not `csc_array`; retain the SciPy compatibility pin
because Arboreto converts each sparse target using `.A`.

For AnnData, verify that `.X` or the selected layer contains the intended
normalized expression. This adapter avoids densifying the full matrix:

```python
from scipy import sparse

values = adata.layers["log_normalized"]  # choose an existing, documented layer
names = adata.var_names.tolist()
assert len(names) == len(set(names))
expression = sparse.csc_matrix(values) if sparse.issparse(values) else values
network = grnboost2(expression_data=expression, gene_names=names,
                    tf_names=tf_names, seed=777, client_or_address=client)
```

`adata.to_df()` produces a dense DataFrame even for sparse `.X`; use it only when
that allocation fits in memory. AnnData integration is illustrative, not a
separately executed dependency in this skill's tests.

## Output and selection

```python
# Upstream example convention: no header.
network.to_csv("network.tsv", sep="\t", index=False, header=False)
loaded = pd.read_csv("network.tsv", sep="\t", header=None,
                     names=["TF", "target", "importance"])

# For a downstream tool expecting named columns, write a separate headered file.
network.to_csv("adjacencies.tsv", sep="\t", index=False)

# Exploratory ranking: top 10 links per target, not a confidence threshold.
per_target = network.sort_values("importance", ascending=False).groupby("target").head(10)
```

`limit=5000` limits the global ranked output; it does not reduce the number of
models fitted. Neither a top-N rule nor an importance threshold is a significance
test. Scores do not encode activation/repression or direct causal effects.
