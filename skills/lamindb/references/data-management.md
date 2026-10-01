# Queries, collections, and streaming

Targets LaminDB 2.10.0. Examples assume a configured instance and existing records.

## Retrieve and explore

```python
import lamindb as ln

ln.Artifact.to_dataframe(limit=20)
artifact = ln.Artifact.get(key="experiments/qc.parquet")
exact = ln.Artifact.get(artifact.uid)
maybe = ln.Artifact.filter(key="optional/file.parquet", is_latest=True).one_or_none()
```

`get()` and `one()` fail for ambiguity; `one_or_none()` tolerates no match, not
multiple matches. For versioned records, `get()` preferentially resolves latest
revisions; do not assume that `.filter(...).one()` applies the same rule.
`to_dataframe()` defaults to 20 rows in this release. Use an explicit limit or
`limit=None` for a deliberate full metadata export; do not mistake a preview for
all matching data.

```python
qs = ln.Artifact.filter(
    suffix=".parquet", key__startswith="experiments/", is_latest=True
).order_by("-created_at", "uid")
preview = qs.to_dataframe(limit=50)
for artifact in qs:
    print(artifact.uid, artifact.key)
```

Iterating a metadata DataFrame yields column names, not artifact objects.
Use the QuerySet to retrieve files; limit and paginate deliberately for large
registries. Slices (`qs[:50]`, `qs[50:100]`) are database offsets, not a REST cursor;
concurrent edits can change offset membership. Record a stable set of UIDs when
reproducing an analysis.

## Filters and feature queries

```python
ln.Artifact.filter(size__gt=1_000_000, suffix__in=[".h5ad", ".parquet"])
ln.Artifact.filter(description__icontains="rna")
ln.Artifact.filter(created_by__handle="researcher")
ln.Artifact.filter(ln.Q(suffix=".csv") | ln.Q(suffix=".parquet"))
ln.Artifact.filter(~ln.Q(key__startswith="scratch/"))

# Requires saved Feature definitions and corresponding artifact annotations:
ln.Artifact.filter(batch=1).to_dataframe(include="features")
batch = ln.Feature.get(name="batch")
ln.Artifact.filter(batch == 1).to_dataframe(include="features")
```

Use `__in`, `__gt`, `__gte`, `__lt`, `__lte`, `__isnull`, and related-field
traversal where supported by the underlying field type. Nested dictionaries
require a dictionary-typed feature; an arbitrary name is not automatically a
JSON field. Database backend collation affects text matching; do not assume
SQLite `contains` has universal case-sensitive behavior.

`search("...")` is text discovery with ranking/limits, not ontology synonym
standardization or a guarantee of complete fuzzy matching. Use exact IDs/filters
for final selection. `lookup()` is useful for modest registries but materializes
lookup data; there is no universal safe 100,000-record threshold.

## Collections and aggregates

```python
members = list(ln.Artifact.filter(key__startswith="experiments/", is_latest=True))
collection = ln.Collection(members, key="study/qc").save()
for member in collection.artifacts.all():
    path = member.cache()

from django.db.models import Sum
summary = ln.Artifact.filter(is_latest=True).aggregate(total_bytes=Sum("size"))
```

A collection groups artifact revisions; it does not align matrix features or
harmonize batch labels. Inspect member schemas before concatenating datasets.
For schema-linked data query `ln.Artifact.filter(schema=schema)`; there is no
`is_valid` field. A schema association does not prove current biological fitness.

## Format-aware access

`cache()` obtains a complete local file/folder (and can download it). `load()`
materializes a supported Python object. `open()` is format-specific:

```python
# Parquet/CSV: PyArrow Dataset, not a bytes file or context manager.
artifact = ln.Artifact.get(key="experiments/qc.parquet")
dataset = artifact.open()
for batch in dataset.to_batches(columns=["gene_count"], batch_size=1024):
    chunk = batch.to_pandas()

# AnnData: context-managed backed accessor.
artifact = ln.Artifact.get(key="scrna/validated.h5ad")
with artifact.open() as accessor:
    subset = accessor[:1000, :].to_memory()
```

For byte-oriented formats such as FASTA/FASTQ use `artifact.cache()` followed by
an appropriate local file reader (`gzip.open` for gzip), or consult the storage
API for the protocol in use. `Artifact.open()` is not a universal `read(n)` stream.
For Polars-backed tables, `with artifact.open(engine="polars") as lazy_frame:`
yields a LazyFrame and needs Polars installed. Optional backend execution was
not tested in this refresh.

`Artifact.backed()`, `delete_cache()`, and `is_cached()` do not exist in this
release. Configure cache through `lamin settings cache-dir get/set`; do not
recursively remove a shared cache as routine troubleshooting.

Sources: [query guide](https://docs.lamin.ai/query-search),
[array access](https://docs.lamin.ai/arrays),
[2.10.0 QuerySet source](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/models/query_set.py).
