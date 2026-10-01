# Processing, statistics and joins

Targets core 4.19.0. Sources: [API](https://vaex.io/docs/api.html),
[missing-data guide](https://vaex.io/docs/guides/missing_or_invalid_data.html), and released
`expression.py`, `functions.py`, `agg.py`, `groupby.py`, and `join.py`.

## Filters, selections and missing values

```python
import numpy as np
import pyarrow as pa
import vaex

df = vaex.from_arrays(
    x=np.array([1., 2., 3., 4., 5., 6.]),
    y=np.array([1., 4., 9., 16., 25., 36.]),
    group=np.array(['A', 'B', 'A', 'B', 'A', 'B']),
    value=pa.array([1., None, float('nan'), 4., 5., 6.]),
    text=np.array([' Alice ', 'Bob', 'Cara', 'Dan', 'Eve', 'Frank']),
    timestamp=np.array(['2024-01-01', '2024-01-02', '2024-02-01',
                        '2024-02-02', '2024-03-01', '2024-03-02'], dtype='datetime64[ns]'),
)
filtered = df[(df.x >= 2) & (df.x < 5)]
assert filtered.x.tolist() == [2., 3., 4.]
df.select(df.x >= 4, name='high')
assert df.count(selection='high') == 3
assert df.mean('x', selection='high') == 5
assert df[df.group.isin(['A'])].count() == 3
assert df.value.isna().sum() == 2       # null/masked or NaN
assert df.value.ismissing().sum() == 1  # null/masked
assert df.value.isnan().sum() == 1      # IEEE NaN
df['filled'] = df.value.fillna(0)
assert df.filled.tolist() == [1., 0., 0., 4., 5., 6.]
```

Named selections affect operations using `selection=...`; creating one does not
remove rows from the frame. Boolean expressions need `&`, `|`, `~` and parentheses.
Use explicit inequalities for intervals; there is no `Expression.between` method.
`fillna(value)` does not accept pandas `method='ffill'`. Forward/backward filling
requires explicit ordering, group boundaries and time-gap policy outside that API.
Never silently impute scientific measurements to zero; the value above is a mechanics example.

## Virtual numeric, text and date transformations

```python
df['squared'] = df.x ** 2
df['log_x'] = df.x.log()  # x is strictly positive in this fixture
df['radius'] = (df.x ** 2 + df.y ** 2).sqrt()
df['band'] = (df.x >= 4).where('high', 'low')
df['clean_name'] = df.text.str.strip().str.lower()
df['starts_a'] = df.clean_name.str.startswith('a')
df['padded'] = df.group.str.pad(width=4, side='left', fillchar='0')
df['year'] = df.timestamp.dt.year
df['month'] = df.timestamp.dt.month
df['weekday'] = df.timestamp.dt.dayofweek
df['next_day'] = df.timestamp + np.timedelta64(1, 'D')
df['bin'] = df.x.digitize([2., 4., 6.])
assert df.bin.tolist() == [0, 1, 1, 2, 2, 3]
assert df.band.tolist() == ['low'] * 3 + ['high'] * 3
assert df.clean_name.tolist()[0] == 'alice'
assert df.month.tolist() == [1, 1, 2, 2, 3, 3]
```

`str.replace(pat, repl, regex=False)` defaults to literal replacement. `str.split`
returns list-valued rows; indexing the resulting expression with `[0]` selects a row,
not the first token in every row. Do not treat it as pandas `.str` list indexing.
For token extraction prefer a verified regex/extraction path or a bounded Arrow operation.
Datetime casting is not a general free-form parser: normalize format/time zone first,
preserve the original field, and verify timezone/DST and invalid-date handling.
`digitize` returns bin indices including underflow/overflow; define labels and edges
explicitly instead of discarding these rows. `vaex.vrange` generates virtual numeric
values; it is not a groupby binning instruction.

## Reductions and approximate percentiles

```python
assert df.x.sum() == 21
assert np.isclose(df.x.var(), np.var(np.arange(1., 7.), ddof=0))
assert np.isclose(df.x.std(), np.std(np.arange(1., 7.), ddof=0))
assert df.count() == 6
assert df.value.count() == 4
assert df.x.minmax().tolist() == [1., 6.]
assert df.group.nunique() == 2
correlation = df.correlation('x', 'y')
assert 0.9 < correlation <= 1
# Histogram-based approximation, not NumPy's exact linear-interpolation quantile:
quartiles = df.percentile_approx('x', percentage=[25, 50, 75], percentile_shape=4096)
assert np.all(np.diff(quartiles) >= 0)
assert 1 <= quartiles[0] <= quartiles[-1] <= 6
pending = [df.x.mean(delay=True), df.y.sum(delay=True)]
df.execute()
assert [p.get().item() for p in pending] == [3.5, 91.0]
```

`std`/`var` use the population denominator here (ddof=0), despite an imprecise
"sample variance" docstring. For an unbiased sample variance, compute the valid
count and multiply population variance by `n/(n-1)` only when `n>1`; this does not
address weights, clustering or dependence. NaNs/nulls are skipped by many reductions;
report the valid count for the exact expression and selection. Infinity is a separate
case. `unique()` and high-cardinality groups allocate outputs proportional to cardinality.
There is no `.quantile()` or `.prod()` expression method in this release.

## Grouped and binned statistics

```python
summary = df.groupby('group', agg={
    'rows': vaex.agg.count(),
    'valid': vaex.agg.count('value'),
    'sum_x': vaex.agg.sum('x'),
    'mean_x': vaex.agg.mean('x'),
    'range_x': vaex.agg.max('x') - vaex.agg.min('x'),
}).sort('group')
assert summary.rows.tolist() == [3, 3]
assert summary.sum_x.tolist() == [9., 12.]
assert summary.range_x.tolist() == [4., 4.]
monthly = df.groupby(['year', 'month'], agg={'sum_x': vaex.agg.sum('x')})
assert monthly.sum_x.sum() == 21
counts = df.count(binby=['x', 'y'], limits=[[0., 7.], [0., 37.]], shape=(7, 4))
means = df.mean('x', binby=['x', 'y'], limits=[[0., 7.], [0., 37.]], shape=(7, 4))
assert counts.shape == (7, 4)
assert counts.sum() == 6
assert np.all(np.isnan(means[counts == 0]))
```

Keys in the aggregation dictionary name output columns; explicit aggregator objects
bind each expression. Do not pass pandas-style `lambda group:` functions. Group
order is not observation order. Sort a small summary by the real time coordinate,
and represent missing time bins explicitly before drawing connecting lines.
For grids, limits are intervals, not bin centers, and the last upper edge is excluded.
Validate retained counts, including missing and out-of-range rows.

## Joins, duplicates and filters

```python
lookup = vaex.from_arrays(group=np.array(['A', 'B']), offset=np.array([10., 20.]))
assert lookup.group.nunique() == len(lookup)
# extract fixes the row membership of the filtered view before joining.
left = df[df.x >= 4].extract()
joined = left.join(lookup, on='group', how='left')
assert len(joined) == 3
assert joined.offset.tolist() == [20., 10., 20.]
inner = left.join(lookup[lookup.group == 'A'].extract(), on='group', how='inner')
assert inner.x.tolist() == [5.]
```

Vaex `join` defaults to `how='left'`, supports left/right/inner, and uses one key
expression per side (`on`, or `left_on`/`right_on`). Lists of key names are not a
composite-key API. Use a documented upstream database/Arrow join for real composite
keys, or a collision-free encoding with an explicit validation contract; concatenating
strings with a separator can collide. Filter semantics are subtle: released docs warn
that underlying rows may participate, so extract the intended populations first.
Right-side duplicates can raise unless `allow_duplication=True`; enabling it can expand
rows. Check row counts, unmatched/null keys, duplicates and scientific identity afterwards.
Sorting and join indices consume RAM, even with memory-mapped source columns.
