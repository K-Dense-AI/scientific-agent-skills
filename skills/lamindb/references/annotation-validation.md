# Annotation and validation

Targets LaminDB 2.10.0. Curation checks schema constraints and adds queryable
annotations. It does not establish correct experimental interpretation.

## Choose schema semantics explicitly

```python
import lamindb as ln

count = ln.Feature(name="gene_count", dtype=int).save()
condition = ln.Feature(name="condition", dtype=str).save()

# Require these columns; other columns can remain unvalidated.
minimal = ln.Schema(name="qc_minimal", features=[count, condition]).save()

# Validate/annotate additional columns against the Feature registry too.
flexible = ln.Schema(
    name="qc_flexible", features=[count, condition], flexible=True
).save()

# Require precisely this feature set (order is independent unless requested).
strict = ln.Schema(
    name="qc_strict", features=[count, condition], maximal_set=True
).save()
```

`minimal_set=True` requires listed features by default. `maximal_set=True`
forbids extra features; `ordered_set=True` additionally requires their order.
`flexible` determines whether other encountered features are validated and
annotated. In particular, **`flexible=False` does not forbid extra columns**.
A feature-only registry schema `ln.Schema(itype=ln.Feature)` defaults to flexible;
unregistered column names can then require curation rather than being ignored.

Use `coerce=True` on `Feature` or `Schema` only after deciding a conversion is
scientifically acceptable. `coerce_dtype` is not a current Feature argument.
`nullable` and default values must reflect the assay's missing-data semantics.

## Validate, repair, then save

```python
import pandas as pd

frame = pd.DataFrame({"gene_count": [120, 130], "condition": ["control", "treated"]})
curator = ln.curators.DataFrameCurator(frame, strict)
curator.validate()  # None means normal return; invalid data raises ValidationError.
artifact = curator.save_artifact(key="experiments/qc.parquet")
assert artifact.schema == strict
pd.testing.assert_frame_equal(artifact.load(), frame)
```

For failures, catch `ln.errors.ValidationError` to inspect the message and stop
registration. `curator.cat.non_validated` describes unresolved categorical
values after their validation stage; it is not a replacement for dtype/shape
errors. Do not test `if curator.validate():` or blindly create new valid labels
to silence an error. After changing the underlying DataFrame, recreate the
curator and validate the complete corrected data again.

A shortcut for already clean data is:

```python
artifact = ln.Artifact.from_dataframe(
    frame, key="experiments/qc-direct.parquet", schema=strict
).save()
```

## Ontology-backed categorical columns

The registry association belongs in the **feature dtype**:

```python
import bionty as bt

cell_type = ln.Feature(name="cell_type", dtype=bt.CellType).save()
cell_schema = ln.Schema(name="cell_metadata", features=[cell_type], coerce=True).save()
# df must contain reviewed Cell Ontology names/IDs matching the chosen dtype.
# curator = ln.curators.DataFrameCurator(df, cell_schema)
# curator.validate()
# curator.cat.standardize("cell_type")
# curator.validate()
```

A plain `dtype=str` does not validate against Cell Ontology. Use
`dtype=bt.CellType.ontology_id` when input labels are ontology IDs. Review the
source and mappings using [ontology management](ontologies.md).
`curator.cat.lookup(public=True)` can aid discovery. `add_ontology()` and
`inspect_standardize()` are not methods in this release. Public source lookup
can perform downloads and is not an offline guarantee.

`cat.standardize("cell_type")` mutates the in-memory data by replacing known
synonyms. `cat.add_new_from("cell_type")` writes registry records; use it only
for explicitly accepted custom terms and preserve their provenance. A mismatch
should not silently become a new biological category.

## AnnData slots

Source-verified example for a user-supplied `adata`, after the selected gene and
cell-type records are available in the instance:

```python
obs_schema = ln.Schema(name="obs_metadata", features=[cell_type], coerce=True).save()
var_schema = ln.Schema(itype=bt.Gene.ensembl_gene_id, dtype=float).save()
anndata_schema = ln.Schema(
    name="scrna_schema",
    otype="AnnData",
    slots={"obs": obs_schema, "var.T": var_schema},
).save()
curator = ln.curators.AnnDataCurator(adata, anndata_schema)
curator.validate()
# If validation reported synonyms, review before standardizing:
# curator.slots["obs"].cat.standardize("cell_type")
# curator.validate()
artifact = curator.save_artifact(key="scrna/validated.h5ad")
```

`var.T` treats the gene index as feature identifiers. Defining a single
`Feature(name="ensembl_gene_id")` in a schema does not validate every gene ID.
Set the correct organism/source for Gene operations and check uniqueness;
gene symbols alone can be ambiguous. AnnData uses `curator.slots["obs"].cat`
or `curator.slots["var.T"].cat`, not `curator.cat.standardize("obs", ...)`.

The local regression suite exercises obs-slot curation, synonym replacement,
H5AD save/load, and backed slicing with synthetic local Bionty records. It does
not claim a downloaded Ensembl/Cell Ontology ingestion test.

## Other composite formats

These are source-verified slot contracts; optional backend execution is
illustrative and needs a separately compatible environment:

| Curator | Schema `otype` | Example slot names |
| --- | --- | --- |
| `MuDataCurator` | `MuData` | `obs`, `rna:obs`, `rna:var.T`, `uns:study_metadata` |
| `SpatialDataCurator` | `SpatialData` | `tables:cell_metadata:obs`, `attrs:bio` |
| `TiledbsomaExperimentCurator` | `tiledbsoma` | `obs`, `ms:RNA.T` |

Each slot maps to a real saved Schema for that component. Pass a valid existing
SOMA Experiment, not an empty collection masquerading as an expression dataset.
The reviewed LaminDB dependency cap is AnnData <=0.13.2; do not assume arbitrary
AnnData/TileDB-SOMA combinations can ingest each other.

## Provenance and scientific checks

Schemas are content-defined and can deduplicate equivalent definitions. They
have no `version`/`version_tag` constructor field in 2.10.0. Create and save a new
schema for a changed contract and retain the exact schema UID/hash with outputs.
Do not mutate schema membership to retroactively imply old data were validated
against new constraints. Query `Artifact.filter(schema=schema)`, not
`Artifact.filter(is_valid=True)`.

Before saving scientific results also check measurement units, matrix/layer
meaning, finite values, allowed missingness, identifier collisions, and whether
normalization or filtering changes biological interpretation. A universal
expression-value ceiling is not meaningful across counts and normalized assays.

Sources: [curation guide](https://docs.lamin.ai/curate),
[Schema source](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/models/schema.py),
[curator source](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/curators/core.py).
