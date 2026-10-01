# Polars Data Transformations

Polars 1.44.2 patterns. Fragments require the named input columns; see
[review.md](review.md) for the bounded native checks and untested integrations.

## Joins

Joins combine data from multiple DataFrames based on common columns.

### Basic Join Types

**Inner Join (intersection):**
```python
# Keep only matching rows from both DataFrames
result = df1.join(df2, on="id", how="inner")
```

**Left Join (all left + matches from right):**
```python
# Keep all rows from left, add matching rows from right
result = df1.join(df2, on="id", how="left")
```

**Full Join (union):**
```python
# Keep all rows from both DataFrames
result = df1.join(df2, on="id", how="full")
```

**Cross Join (Cartesian product):**
```python
# Every row from left with every row from right
result = df1.join(df2, how="cross")
```

**Semi Join (filtered left):**
```python
# Keep only left rows that have a match in right
result = df1.join(df2, on="id", how="semi")
```

**Anti Join (non-matching left):**
```python
# Keep only left rows that DON'T have a match in right
result = df1.join(df2, on="id", how="anti")
```

### Join correctness

Default `validate="m:m"` does not check uniqueness. Use `validate="m:1"` for
a sample-to-metadata join or `"1:1"` for paired samples; duplicate keys otherwise
multiply observations. Audit unmatched keys with anti joins. The current docs
exclude validation from streaming support: validate keys independently before a
large streaming join, and test the selected engine.

Null keys do not match unless `nulls_equal=True` (formerly `join_nulls`). Full joins
retain both key columns by default; choose `coalesce=True` if merged keys are wanted.
Request `maintain_order="left"` or sort by explicit keys when order matters.

### Join Syntax Variations

**Single column join:**
```python
df1.join(df2, on="id")
```

**Multiple columns join:**
```python
df1.join(df2, on=["id", "date"])
```

**Different column names:**
```python
df1.join(df2, left_on="user_id", right_on="id")
```

**Multiple different columns:**
```python
df1.join(
    df2,
    left_on=["user_id", "date"],
    right_on=["id", "timestamp"]
)
```

### Suffix Handling

When both DataFrames have columns with the same name (other than join keys):

```python
# Add suffixes to distinguish columns
result = df1.join(df2, on="id", suffix="_right")

# Results in: value, value_right (if both had "value" column)
```

### Join Examples

**Example 1: Customer Orders**
```python
customers = pl.DataFrame({
    "customer_id": [1, 2, 3, 4],
    "name": ["Alice", "Bob", "Charlie", "David"]
})

orders = pl.DataFrame({
    "order_id": [101, 102, 103],
    "customer_id": [1, 2, 1],
    "amount": [100, 200, 150]
})

# Inner join - only customers with orders
result = customers.join(orders, on="customer_id", how="inner")

# Left join - all customers, even without orders
result = customers.join(orders, on="customer_id", how="left")
```

**Example 2: Time-series data**
```python
prices = pl.DataFrame({
    "date": ["2023-01-01", "2023-01-02", "2023-01-03"],
    "stock": ["AAPL", "AAPL", "AAPL"],
    "price": [150, 152, 151]
})

volumes = pl.DataFrame({
    "date": ["2023-01-01", "2023-01-02"],
    "stock": ["AAPL", "AAPL"],
    "volume": [1000000, 1100000]
})

result = prices.join(
    volumes,
    on=["date", "stock"],
    how="left"
)
```

### Asof Joins (Nearest Match)

For time-series data, join to nearest timestamp:

```python
# Join to nearest earlier timestamp
quotes = pl.DataFrame({
    "timestamp": [1.0, 2.0, 3.0, 4.0, 5.0],
    "stock": ["A", "A", "A", "A", "A"],
    "quote": [100, 101, 102, 103, 104]
})

trades = pl.DataFrame({
    "timestamp": [1.5, 3.5, 4.2],
    "stock": ["A", "A", "A"],
    "trade": [50, 75, 100]
})

result = trades.sort("stock", "timestamp").join_asof(
    quotes.sort("stock", "timestamp"),
    on="timestamp",
    by="stock",
    strategy="backward",  # or "forward", "nearest"
    tolerance=0.6,  # timestamp units; unmatched rows retain null quote
)
```

As-of keys must have matching dtypes and be sorted within each `by` group. Polars
cannot verify grouped sortedness automatically in every case. `nearest` may match
a future observation; choose direction and tolerance according to the study.

## Concatenation

Concatenation stacks DataFrames together.

### Vertical Concatenation (Stack Rows)

```python
df1 = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
df2 = pl.DataFrame({"a": [5, 6], "b": [7, 8]})

# Stack rows
result = pl.concat([df1, df2], how="vertical")
# Result: 4 rows, same columns
```

**Handling mismatched schemas:**
```python
df1 = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
df2 = pl.DataFrame({"a": [5, 6], "c": [7, 8]})

# Diagonal concat - fills missing columns with nulls
result = pl.concat([df1, df2], how="diagonal")
# Result: columns a, b, c (with nulls where not present)
```

### Horizontal Concatenation (Stack Columns)

```python
df1 = pl.DataFrame({"a": [1, 2, 3]})
df2 = pl.DataFrame({"b": [4, 5, 6]})

# Stack columns
result = pl.concat([df1, df2], how="horizontal_extend")
# Result: 3 rows, columns a and b
```

**Note:** Horizontal concat aligns by row position and pads shorter frames with nulls
with `how="horizontal_extend"`. In 1.44.2, `how="horizontal"` also pads but is
deprecated toward an equal-height contract; `strict` is transitional/deprecated.
Validate heights explicitly when needed; a keyed join is safer for sample alignment. `vertical` requires matching schemas; the `*_relaxed`
variants coerce to a common supertype, so inspect the result dtype.

#As-of keys must have matching dtypes and be sorted within each `by` group. Polars
cannot verify grouped sortedness automatically in every case. `nearest` may match
a future observation; choose direction and tolerance according to the study.

## Concatenation Options

```python
# Rechunk after concatenation (better performance for subsequent operations)
result = pl.concat([df1, df2], rechunk=True)

# Parallel subplans (applies to LazyFrames)
result = pl.concat([lf1, lf2], parallel=True)
```

### Use Cases

**Combining data from multiple sources:**
```python
# Read multiple files and concatenate
files = ["data_2023.csv", "data_2024.csv", "data_2025.csv"]
dfs = [pl.read_csv(f) for f in files]
combined = pl.concat(dfs, how="vertical")
```

**Adding computed columns:**
```python
base = pl.DataFrame({"value": [1, 2, 3]})
computed = pl.DataFrame({"doubled": [2, 4, 6]})
result = pl.concat([base, computed], how="horizontal_extend")
```

## Pivoting (Wide Format)

Convert unique values from one column into multiple columns.

### Basic Pivot

```python
df = pl.DataFrame({
    "date": ["2023-01", "2023-01", "2023-02", "2023-02"],
    "product": ["A", "B", "A", "B"],
    "sales": [100, 150, 120, 160]
})

# Pivot: products become columns
pivoted = df.pivot(
    on="product",
    values="sales",
    index="date"
)
# Result:
# date     | A   | B
# 2023-01  | 100 | 150
# 2023-02  | 120 | 160
```

In 1.44.2, `LazyFrame.pivot` is available with required `on_columns`, which declares
the output categories before execution (the API is unstable):

```python
pivoted_lazy = df.lazy().pivot(
    on="product", on_columns=["A", "B"], values="sales", index="date"
).collect()
```
Validate that observed categories belong to `on_columns`; undeclared levels can be
excluded. Duplicate cells raise unless an aggregation is supplied. Choose a
scientifically meaningful aggregation, not `first` merely to silence duplicate data.

### Pivot with Aggregation

When there are duplicate combinations, aggregate:

```python
df = pl.DataFrame({
    "date": ["2023-01", "2023-01", "2023-01"],
    "product": ["A", "A", "B"],
    "sales": [100, 110, 150]
})

# Aggregate duplicates
pivoted = df.pivot(
    on="product",
    values="sales",
    index="date",
    aggregate_function="sum"  # or "mean", "max", "min", etc.
)
```

### Multiple Index Columns

```python
df = pl.DataFrame({
    "region": ["North", "North", "South", "South"],
    "date": ["2023-01", "2023-01", "2023-01", "2023-01"],
    "product": ["A", "B", "A", "B"],
    "sales": [100, 150, 120, 160]
})

pivoted = df.pivot(
    on="product",
    values="sales",
    index=["region", "date"]
)
```

## Unpivoting/Melting (Long Format)

Use column names or selectors (`import polars.selectors as cs`) for `on`, not a
general expression. Sort the result explicitly if a particular row order is needed.

Convert multiple columns into rows (opposite of pivot).

### Basic Unpivot

```python
df = pl.DataFrame({
    "date": ["2023-01", "2023-02"],
    "product_A": [100, 120],
    "product_B": [150, 160]
})

# Unpivot: convert columns to rows
unpivoted = df.unpivot(
    index="date",
    on=["product_A", "product_B"]
)
# Result:
# date     | variable   | value
# 2023-01  | product_A  | 100
# 2023-02  | product_A  | 120
# 2023-01  | product_B  | 150
# 2023-02  | product_B  | 160
```

### Custom Column Names

```python
unpivoted = df.unpivot(
    index="date",
    on=["product_A", "product_B"],
    variable_name="product",
    value_name="sales"
)
```

### Unpivot by Pattern

```python
# Unpivot all columns matching pattern
df = pl.DataFrame({
    "id": [1, 2],
    "sales_Q1": [100, 200],
    "sales_Q2": [150, 250],
    "sales_Q3": [120, 220],
    "revenue_Q1": [1000, 2000]
})

# Unpivot all sales columns
unpivoted = df.unpivot(
    index="id",
    on=cs.matches("^sales_.*$")
)
```

## Exploding (Unnesting Lists)

Convert list columns into multiple rows. Choose `empty_as_null` explicitly: `True`
retains an empty-list record as one null, `False` drops it. The default changes in
Polars 2.0. `keep_nulls=True` separately preserves null lists. Check both policies
against the experimental-unit counts.

### Basic Explode

```python
df = pl.DataFrame({
    "id": [1, 2],
    "values": [[1, 2, 3], [4, 5]]
})

# Explode list into rows
exploded = df.explode("values", empty_as_null=True)
# Result:
# id | values
# 1  | 1
# 1  | 2
# 1  | 3
# 2  | 4
# 2  | 5
```

### Multiple Column Explode

```python
df = pl.DataFrame({
    "id": [1, 2],
    "letters": [["a", "b"], ["c", "d"]],
    "numbers": [[1, 2], [3, 4]]
})

# Explode multiple columns (must be same length)
exploded = df.explode("letters", "numbers", empty_as_null=True)
```

## Transposing

Swap rows and columns:

```python
df = pl.DataFrame({
    "metric": ["sales", "costs", "profit"],
    "Q1": [100, 60, 40],
    "Q2": [150, 80, 70]
})

# Transpose
transposed = df.transpose(
    include_header=True,
    header_name="quarter",
    column_names="metric"
)
# Result: quarters as rows, metrics as columns
```

## Reshaping Patterns

### Pattern 1: Wide to Long to Wide

```python
# Start wide
wide = pl.DataFrame({
    "id": [1, 2],
    "A": [10, 20],
    "B": [30, 40]
})

# To long
long = wide.unpivot(index="id", on=["A", "B"])

# Back to wide (maybe with transformations)
wide_again = long.pivot(on="variable", values="value", index="id")
```

### Pattern 2: Nested to Flat

```python
# Nested data
df = pl.DataFrame({
    "user": [1, 2],
    "purchases": [
        [{"item": "A", "qty": 2}, {"item": "B", "qty": 1}],
        [{"item": "C", "qty": 3}]
    ]
})

# Explode and unnest
flat = (
    df.explode("purchases", empty_as_null=True)
    .unnest("purchases")
)
```

### Pattern 3: Aggregation to Pivot

```python
# Raw data
sales = pl.DataFrame({
    "date": ["2023-01", "2023-01", "2023-02"],
    "product": ["A", "B", "A"],
    "sales": [100, 150, 120]
})

# Aggregate then pivot
result = (
    sales
    .group_by("date", "product")
    .agg(pl.col("sales").sum())
    .pivot(on="product", values="sales", index="date")
)
```

## Advanced Transformations

### Conditional Reshaping

```python
# Pivot only certain values
df.filter(pl.col("year") >= 2020).pivot(...)

# Unpivot with filtering
df.unpivot(index="id", on=cs.matches("^sales.*$"))
```

### Multi-level Transformations

```python
# Complex reshaping pipeline
result = (
    df
    .unpivot(index="id", on=cs.matches("^Q[0-9]_.*$"))
    .with_columns(
        quarter=pl.col("variable").str.extract(r"Q([0-9])", 1),
        metric=pl.col("variable").str.extract(r"Q[0-9]_(.*)", 1)
    )
    .drop("variable")
    .pivot(on="metric", values="value", index=["id", "quarter"])
)
```

## Performance Considerations

### Join Performance

```python
# 1. Polars has no row index; pre-sorting equi-joins is not universally faster.
# Benchmark the optimized lazy plan on representative data.
result = df1.join(df2, on="id", validate="m:1")

# 2. Use appropriate join type
# semi/anti avoid materializing right-side columns and duplicate matches
matches = df1.join(df2, on="id", how="semi")  # Better than filtering after inner join

# 3. Filter before joining
df1_filtered = df1.filter(pl.col("active"))
result = df1_filtered.join(df2, on="id")  # Smaller join
```

#As-of keys must have matching dtypes and be sorted within each `by` group. Polars
cannot verify grouped sortedness automatically in every case. `nearest` may match
a future observation; choose direction and tolerance according to the study.

## Concatenation Performance

```python
# 1. Rechunk after concatenation
result = pl.concat(dfs, rechunk=True)

# 2. Use lazy mode for large concatenations
lf1 = pl.scan_parquet("file1.parquet")
lf2 = pl.scan_parquet("file2.parquet")
result = pl.concat([lf1, lf2]).collect()
```

### Pivot Performance

```python
# 1. Filter before pivoting
pivoted = df.filter(pl.col("year") == 2023).pivot(...)

# 2. Define the scientific aggregation; no aggregation detects duplicate cells.
pivoted = df.pivot(on="product", values="sales", index="date")
```

## Common Use Cases

### Time Series Alignment

```python
# Align two time series with different timestamps
ts1.sort("timestamp").join_asof(
    ts2.sort("timestamp"), on="timestamp", strategy="backward", tolerance="1s"
)  # Assumes matching Datetime keys; choose the tolerance for the experiment
```

### Feature Engineering

```python
# Create lag features in timestamp order within each user
df.sort("user_id", "timestamp").with_columns(
    pl.col("value").shift(1).over("user_id").alias("prev_value"),
    pl.col("value").shift(2).over("user_id").alias("prev_prev_value")
)
```

### Data Denormalization

```python
# Combine normalized tables
orders.join(customers, on="customer_id").join(products, on="product_id")
```

### Report Generation

```python
# Pivot for reporting
sales.pivot(on="product", values="amount", index="month")
```
