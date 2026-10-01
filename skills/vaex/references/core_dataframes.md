# Core DataFrames and loading

Targets core 4.19.0. [API](https://vaex.io/docs/api.html),
[I/O guide](https://vaex.io/docs/guides/io.html), and the released package source
were checked on 2026-10-01. Examples in each reference run sequentially unless marked illustrative.

## Construct and inspect a small fixture

```python
import numpy as np
import pandas as pd
import pyarrow as pa
import vaex

df = vaex.from_arrays(x=np.arange(6.), y=np.arange(6.) ** 2,
                      category=np.array(['A', 'B'] * 3))
from_dict = vaex.from_dict({'x': [1, 2], 'label': ['a', 'b']})
from_arrow = vaex.from_arrow_table(pa.table({'x': [1, 2], 'y': [3, 4]}))
from_pandas = vaex.from_pandas(pd.DataFrame({'x': [1, 2]}), copy_index=False)
assert from_dict.shape == (2, 2)
assert from_arrow.x.tolist() == [1, 2]
assert from_pandas.get_column_names() == ['x']
print(df.shape, len(df), df.get_column_names(), df.dtypes)
print(df.head(2))                  # Vaex DataFrame, not pandas
print(df.tail(2))
row = dict(zip(df.get_column_names(), df[0]))  # integer indexing returns a list
assert row['x'] == 0
```

These constructors start from in-memory objects. Wrapping a pandas frame or Arrow
table does not retroactively make its existing allocation out of core. Object columns
must have consistent types; verify null and timestamp representations after conversion.
`df.describe()` executes summary work and may be expensive across many columns.
`df.byte_size()` estimates column bytes; it is not process RSS, peak memory, or OS page-cache usage.

## Open existing data

Illustrative file paths (create or obtain compatible files first):

```python
hdf = vaex.open('measurements.hdf5')
arrow = vaex.open('measurements.arrow')
parquet = vaex.open('measurements.parquet')
csv = vaex.open('measurements.csv')
parts = vaex.open('part-*.hdf5')
explicit_parts = vaex.open_many(['part-001.hdf5', 'part-002.hdf5'])
```

Local compatible HDF5 and uncompressed Arrow buffers can be memory mapped; metadata
and accessed pages still use memory. Parquet decoding/compression and compressed
Feather require buffers. Lazy CSV indexes the file and infers a schema, then reparses
needed chunks. It is not a no-read open; compressed CSV is unsupported by that lazy reader.
Use explicit types for identifiers and mixed/missing columns. See [I/O](io_operations.md).

`vaex.example()` is an N-body satellite-accretion simulation, not NYC taxi data.
`vaex.datasets.iris()` and `.titanic()` may download/cache data. Use synthetic fixtures
when network access or a dataset download is unnecessary; record dataset provenance
when using an example scientifically.

## Expressions versus arrays

```python
expr = df.x ** 2 + df.y
assert 'energy' not in df.get_column_names()
df['energy'] = expr
assert 'energy' in df.virtual_columns
assert 'energy' not in df.get_column_names(virtual=False)
assert np.isclose(df.energy.mean(), 55 / 3)  # computes now
preview = df[:3].energy.to_numpy()          # bounds rows before evaluation
assert preview.tolist() == [0., 2., 8.]
```

Expressions defer the per-row calculation, but reductions without `delay=True`
execute. `.values` may return NumPy, masked NumPy, or Arrow depending on dtype;
`.to_numpy()`, `.tolist()` and `.to_pandas_df()` materialize their requested data.
For larger-than-RAM data, select a bounded subset or iterate chunks before conversion.
A filter is a view with its own selection/mask state, not a guarantee of zero allocation.

## Copies, columns and rows

```python
copy = df.copy()                     # shares underlying data
subset = df[['x', 'energy']][:3]      # column selection and row slice
assert subset.shape == (3, 2)
renamed = df.copy()
new_name = renamed.rename('x', 'distance')  # mutates names; returns the new name
assert new_name == 'distance'
assert 'distance' in renamed.get_column_names()
assert 'x' in df.get_column_names()
reduced = df.drop('category')
assert 'category' not in reduced.get_column_names()
combined = vaex.concat([df[:2], df[2:]])
assert len(combined) == len(df)
sample = df.sample(n=3, random_state=7).to_pandas_df()
assert len(sample) == 3
```

Use bracket access for columns that collide with frame methods, such as `df['label']`.
`copy(deep=True)` and `df.row()` are not core 4.19.0 methods. Export and reopen a
snapshot for independent persisted data; explicit array copies are only suitable for
bounded datasets. For horizontal combination, validate row IDs/order or perform an
explicit key join. Assigning another frame's expression is not an identity alignment.
`vaex.concat` resolves schemas; inspect types and counts rather than assuming exact
schema equality. Record units outside a plain numeric column when the source carries them.
