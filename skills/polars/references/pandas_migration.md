# Pandas to Polars Migration Guide

Migration patterns reviewed with Polars 1.44.2 and pandas 3.0.6. Fragments require
matching input columns; see [review.md](review.md) for tested behavior and limits.

## Core Conceptual Differences

### 1. No Index System

**Pandas:** Uses row-based indexing system
```python
df.loc[0, "column"]
df.iloc[0:5]
df.set_index("id")
```

**Polars:** Uses integer positions only
```python
df[0, "column"]  # Row position, column name
df[0:5]  # Row slice
# Preserve former index labels as explicit columns; group_by is an aggregation
```

### 2. Memory Format

Both systems store data by column. pandas supports NumPy-backed and extension
arrays, including Arrow; Polars uses columnar typed buffers with Arrow interchange.
Performance, memory, and zero-copy behavior depend on types, chunking, and workload;
benchmark the actual conversion and query.

### 3. Parallelization

**Pandas:** Parallel behavior depends on the operation and backend
**Polars:** Parallel by default using Rust's concurrency

### 4. Lazy Evaluation

**Pandas:** Only eager evaluation
**Polars:** Both eager (DataFrame) and lazy (LazyFrame) with query optimization

### 5. Type Strictness

**Pandas:** Allows silent type conversions
**Polars:** Typed columns with inference and common-supertype coercion; validate dtypes

**Example:**
```python
# pandas may infer float here; nullable Int64/Arrow dtypes can preserve integers
pd_df["int_col"] = [1, 2, None, 4]  # dtype: float64

# Polars: Keeps as integer with null
pl_df = pl.DataFrame({"int_col": [1, 2, None, 4]})  # dtype: Int64
```

## Operation Mappings

### Data Selection

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Select column | `df["col"]` or `df.col` | `df.select("col")` or `df["col"]` |
| Select multiple | `df[["a", "b"]]` | `df.select("a", "b")` |
| Select by position | `df.iloc[:, 0:3]` | `df.select(pl.col(df.columns[0:3]))` |
| Select by condition | `df[df["age"] > 25]` | `df.filter(pl.col("age") > 25)` |

### Data Filtering

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Single condition | `df[df["age"] > 25]` | `df.filter(pl.col("age") > 25)` |
| Multiple conditions | `df[(df["age"] > 25) & (df["city"] == "NY")]` | `df.filter(pl.col("age") > 25, pl.col("city") == "NY")` |
| Query method | `df.query("age > 25")` | `df.filter(pl.col("age") > 25)` |
| isin | `df[df["city"].isin(["NY", "LA"])]` | `df.filter(pl.col("city").is_in(["NY", "LA"]))` |
| isna (float) | `df[df["value"].isna()]` | `df.filter(pl.col("value").is_null() | pl.col("value").is_nan())` |
| notna (float) | `df[df["value"].notna()]` | `df.filter(pl.col("value").is_not_null() & pl.col("value").is_not_nan())` |

### Adding/Modifying Columns

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Add column | `df["new"] = df["old"] * 2` | `df.with_columns(new=pl.col("old") * 2)` |
| Multiple columns | `df.assign(a=..., b=...)` | `df.with_columns(a=..., b=...)` |
| Conditional column | `np.where(condition, a, b)` | `pl.when(condition).then(a).otherwise(b)` |

**Important difference - Parallel execution:**

```python
# Pandas: Sequential (lambda sees previous results)
df.assign(
    a=lambda df_: df_.value * 10,
    b=lambda df_: df_.value * 100
)

# Polars: Parallel (all computed together)
df.with_columns(
    a=pl.col("value") * 10,
    b=pl.col("value") * 100
)
```

### Grouping and Aggregation

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Group by | `df.groupby("col")` | `df.group_by("col")` |
| Agg single | `df.groupby("col")["val"].mean()` | `df.group_by("col").agg(pl.col("val").mean())` |
| Agg multiple | `df.groupby("col").agg({"val": ["mean", "sum"]})` | `df.group_by("col").agg(pl.col("val").mean().alias("mean"), pl.col("val").sum().alias("sum"))` |
| Size | `df.groupby("col").size()` | `df.group_by("col").agg(pl.len())` |
| Count | `df.groupby("col").count()` | `df.group_by("col").agg(pl.exclude("col").count())` |

### Window Functions

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Transform | `df.groupby("col").transform("mean")` | `df.with_columns(pl.col("val").mean().over("col"))` |
| Rank | `df.groupby("col")["val"].rank()` | `df.with_columns(pl.col("val").rank().over("col"))` |
| Shift | `df.groupby("col")["val"].shift(1)` | `df.with_columns(pl.col("val").shift(1).over("col"))` |
| Cumsum | `df.groupby("col")["val"].cumsum()` | `df.with_columns(pl.col("val").cum_sum().over("col"))` |

### Joins

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Inner join | `df1.merge(df2, on="id")` | `df1.join(df2, on="id", how="inner")` |
| Left join | `df1.merge(df2, on="id", how="left")` | `df1.join(df2, on="id", how="left")` |
| Different keys | `df1.merge(df2, left_on="a", right_on="b")` | `df1.join(df2, left_on="a", right_on="b")` |

### Concatenation

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Vertical | `pd.concat([df1, df2], axis=0)` | `pl.concat([df1, df2], how="vertical")` |
| Horizontal | `pd.concat([df1, df2], axis=1)` | `pl.concat([df1, df2], how="horizontal_extend")` |

### Sorting

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Sort by column | `df.sort_values("col")` | `df.sort("col")` |
| Descending | `df.sort_values("col", ascending=False)` | `df.sort("col", descending=True)` |
| Multiple columns | `df.sort_values(["a", "b"])` | `df.sort("a", "b")` |

### Reshaping

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Pivot | `df.pivot(index="a", columns="b", values="c")` | `df.pivot(on="b", values="c", index="a")` |
| Melt | `df.melt(id_vars="id")` | `df.unpivot(index="id")` |

### I/O Operations

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Read CSV | `pd.read_csv("file.csv")` | `pl.read_csv("file.csv")` or `pl.scan_csv("file.csv")` |
| Write CSV | `df.to_csv("file.csv")` | `df.write_csv("file.csv")` |
| Read Parquet | `pd.read_parquet("file.parquet")` | `pl.read_parquet("file.parquet")` |
| Write Parquet | `df.to_parquet("file.parquet")` | `df.write_parquet("file.parquet")` |
| Read Excel | `pd.read_excel("file.xlsx")` | `pl.read_excel("file.xlsx")` |

### String Operations

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Upper | `df["col"].str.upper()` | `df.select(pl.col("col").str.to_uppercase())` |
| Lower | `df["col"].str.lower()` | `df.select(pl.col("col").str.to_lowercase())` |
| Contains | `df["col"].str.contains("pattern")` | `df.filter(pl.col("col").str.contains("pattern"))` |
| Replace | `df["col"].str.replace("old", "new")` | `df.select(pl.col("col").str.replace("old", "new"))` |
| Split | `df["col"].str.split(" ")` | `df.select(pl.col("col").str.split(" "))` |

### Datetime Operations

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Parse dates | `pd.to_datetime(df["col"])` | `df.select(pl.col("col").str.strptime(pl.Date, "%Y-%m-%d"))` |
| Year | `df["date"].dt.year` | `df.select(pl.col("date").dt.year())` |
| Month | `df["date"].dt.month` | `df.select(pl.col("date").dt.month())` |
| Day | `df["date"].dt.day` | `df.select(pl.col("date").dt.day())` |

### Missing Data

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Drop nulls | `df.dropna()` | `df.drop_nulls()` |
| Fill nulls | `df.fillna(0)` | `df.fill_null(0)` |
| Check null | `df["col"].isna()` | `df.select(pl.col("col").is_null())` |
| Forward fill | `df.ffill()` | `df.select(pl.col("col").fill_null(strategy="forward"))` |

These missing-data mappings only match pandas after deciding how floating NaNs
should be treated: Polars `drop_nulls`, `fill_null`, and `is_null` do not include
NaNs. For float measurements, `fill_nan(None)` can normalize NaN to null before
those operations; retain counts and a declared exclusion/imputation rule.

### Other Operations

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Unique values | `df["col"].unique()` | `df["col"].unique()` |
| Value counts | `df["col"].value_counts()` | `df["col"].value_counts()` |
| Describe | `df.describe()` | `df.describe()` |
| Sample | `df.sample(n=100)` | `df.sample(n=100)` |
| Head | `df.head()` | `df.head()` |
| Tail | `df.tail()` | `df.tail()` |

## Common Migration Patterns

### Pattern 1: Chained Operations

**Pandas:**
```python
result = (df
    .assign(new_col=lambda x: x["old_col"] * 2)
    .query("new_col > 10")
    .groupby("category")
    .agg({"value": "sum"})
    .reset_index()
)
```

**Polars:**
```python
result = (df
    .with_columns(new_col=pl.col("old_col") * 2)
    .filter(pl.col("new_col") > 10)
    .group_by("category")
    .agg(pl.col("value").sum())
)
# No reset_index needed - Polars doesn't have index
```

### Pattern 2: Apply Functions

**Pandas:**
```python
# Avoid in Polars - breaks parallelization
df["result"] = df["value"].apply(lambda x: x * 2)
```

**Polars:**
```python
# Use expressions instead
df = df.with_columns(result=pl.col("value") * 2)

# If custom function needed
df = df.with_columns(
    result=pl.col("value").map_elements(lambda x: float(x) * 2, return_dtype=pl.Float64)
)
```

### Pattern 3: Conditional Column Creation

**Pandas:**
```python
df["category"] = np.where(
    df["value"] > 100,
    "high",
    np.where(df["value"] > 50, "medium", "low")
)
```

**Polars:**
```python
df = df.with_columns(
    category=pl.when(pl.col("value") > 100)
        .then(pl.lit("high"))
        .when(pl.col("value") > 50)
        .then(pl.lit("medium"))
        .otherwise(pl.lit("low"))
)
```

### Pattern 4: Group Transform

**Pandas:**
```python
df["group_mean"] = df.groupby("category")["value"].transform("mean")
```

**Polars:**
```python
df = df.with_columns(
    group_mean=pl.col("value").mean().over("category")
)
```

### Pattern 5: Multiple Aggregations

**Pandas:**
```python
result = df.groupby("category").agg({
    "value": ["mean", "sum", "count"],
    "price": ["min", "max"]
})
```

**Polars:**
```python
result = df.group_by("category").agg(
    pl.col("value").mean().alias("value_mean"),
    pl.col("value").sum().alias("value_sum"),
    pl.col("value").count().alias("value_count"),
    pl.col("price").min().alias("price_min"),
    pl.col("price").max().alias("price_max")
)
```

## Performance Anti-Patterns to Avoid

### Pattern 1: Lazy Pipeline Helpers

`pipe` does not disable parallelism. A helper returning a native LazyFrame keeps
its plan optimizable; collecting inside the helper creates a materialization boundary.

```python
def add_double(lf: pl.LazyFrame) -> pl.LazyFrame:
    return lf.with_columns(doubled=pl.col("value") * 2)

result = df.lazy().pipe(add_double).filter(pl.col("doubled") > 10).collect()
```

### Anti-Pattern 2: Python Functions in Hot Paths

**Bad:**
```python
df = df.with_columns(
    result=pl.col("value").map_elements(lambda x: x * 2)
)
```

**Good:**
```python
df = df.with_columns(result=pl.col("value") * 2)
```

### Anti-Pattern 3: Using Eager Reading for Large Files

**Bad:**
```python
df = pl.read_csv("large_file.csv")
result = df.filter(pl.col("age") > 25).select("name", "age")
```

**Good:**
```python
lf = pl.scan_csv("large_file.csv")
result = lf.filter(pl.col("age") > 25).select("name", "age").collect()
```

### Anti-Pattern 4: Row Iteration

**Bad:**
```python
for row in df.iter_rows():
    # Process row
    pass
```

**Good:**
```python
# Use vectorized operations
df = df.with_columns(
    # Vectorized computation
)
```

## Migration Checklist

When migrating from pandas to Polars:

1. **Preserve index labels** - Move them into named columns before conversion
2. **Replace apply/map with expressions** - Use Polars native operations
3. **Update column assignment** - Use `with_columns()` instead of direct assignment
4. **Change groupby.transform to .over()** - Window functions work differently
5. **Update string operations** - Use `.str.to_uppercase()` instead of `.str.upper()`
6. **Validate inferred/coerced types** - Cast deliberately, checking overflow and null counts
7. **Consider lazy evaluation** - Use `scan_*` instead of `read_*` for large data
8. **Update aggregation syntax** - More explicit in Polars
9. **Remove reset_index calls** - Not needed in Polars
10. **Update conditional logic** - Use `when().then().otherwise()` pattern

## Compatibility Layer

For gradual migration, you can use both libraries:

```python
import pandas as pd
import polars as pl

# Convert pandas to Polars
pl_df = pl.from_pandas(pd_df)

# Convert Polars to pandas
pd_df = pl_df.to_pandas()

# Arrow interchange; conversion may copy depending on dtype/chunk layout.
import pyarrow as pa
pl_df = pl.from_arrow(pa.Table.from_pandas(pd_df, preserve_index=False))
pd_df = pl_df.to_pandas(use_pyarrow_extension_array=True)
```

`pl.from_pandas` defaults to `nan_to_null=True` and excludes ordinary pandas
index labels unless requested; use `reset_index` deliberately for meaningful labels.
Horizontal concatenation aligns by position in Polars, not by pandas index.
Polars joins do not match null keys by default, while pandas merge does.
Polars group-by retains null groups; pandas default group-by drops NA keys.
`n_unique` includes null in Polars; pandas `nunique` excludes NA by default.

## When to Stick with Pandas

Consider staying with pandas when:
- Working with time series requiring complex index operations
- Need extensive ecosystem support (some libraries only support pandas)
- Existing code depends on pandas semantics and has not been validated after migration
- Data is small and performance isn't critical
- Using advanced pandas features without Polars equivalents

## When to Switch to Polars

Switch to Polars when:
- Performance is critical
- Working with large datasets (>1GB)
- Need lazy evaluation and query optimization
- Want better type safety
- Need parallel execution by default
- Starting a new project
