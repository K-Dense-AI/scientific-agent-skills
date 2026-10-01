# Core concepts and lineage

Targets LaminDB 2.10.0. These examples assume an initialized instance and imports
`import lamindb as ln` and `import pandas as pd`. User file paths and pre-existing
keys below are illustrative; the equivalent local workflows have regression tests.

## Register and retrieve content

```python
artifact = ln.Artifact("sample.fasta", key="reference/sample.fasta").save()
frame = ln.Artifact.from_dataframe(
    pd.DataFrame({"count": [1, 2]}), key="experiments/counts.parquet"
).save()
# For a user-provided AnnData object:
# annotated = ln.Artifact.from_anndata(adata, key="scrna/batch.h5ad").save()
loaded = frame.load()
local_path = frame.cache()
```

`Artifact` records carry `uid`, `key`, `suffix`, `size`, `hash`, `created_by`,
`run`, and schema/provenance links. `describe()` displays metadata;
`view_lineage()` renders lineage and needs Graphviz's system executable in
addition to its Python package. Check whether a run exists before accessing it.

## Revisions

```python
changed = loaded.assign(count=[3, 4])
new = ln.Artifact.from_dataframe(
    changed,
    key="experiments/counts.parquet",
    revises=frame,
    version_tag="2",
).save()
latest = ln.Artifact.get(key="experiments/counts.parquet")
versions = new.versions.to_dataframe(limit=None)
exact_revision = ln.Artifact.get(frame.uid)
```

A key is a logical name, whereas a full UID identifies a revision. `get(key=...)`
preferentially selects a latest version; `.filter(key=...)` can include several
revisions. Identical content can be deduplicated; re-saving is not a guarantee
of a new revision. Use `version_tag`, not the retired `version` field, for labels.
Overwrite-enabled storage formats have additional old-content access restrictions;
review them before assuming all historical bytes remain accessible.

## Features and experimental entities

```python
from datetime import date

score = ln.Feature(name="gc_content", dtype=float).save()
observed = ln.Feature(name="experiment_date", dtype=date, coerce=True).save()
frame.features.set_values({score: 0.55, observed: "2026-09-30"})
ln.Artifact.filter(gc_content__gte=0.5).to_dataframe(include="features")

sample_type = ln.Record(name="Sample", is_type=True).save()
sample = ln.Record(name="control-1", type=sample_type).save()
replicate = ln.Record(name="control-1-replicate", type=sample_type).save()
replicate.parents.add(sample)
frame.records.add(sample)
label = ln.ULabel(name="reviewed").save()
frame.ulabels.add(label)
```

`set_values()` adds typed values, not merely a feature-name link. A string dtype
is free text; a categorical dtype backed by `Record`, `ULabel`, or Bionty enables
controlled terms. Date strings need deliberate coercion; preserve units and
original values when conversions matter scientifically.

## Script and notebook tracking

Run this pattern from a real script/notebook, with the input already registered:

```python
ln.Project(name="QC study").save()
ln.track(project="QC study", params={"minimum_count": 2})
inp = ln.Artifact.get(key="experiments/counts.parquet")
data = inp.load()
out = ln.Artifact.from_dataframe(
    data[data["count"] >= 2], key="experiments/filtered.parquet"
).save()
ln.finish()

run = out.run
assert inp in run.input_artifacts.all()
run.output_artifacts.to_dataframe()
run.transform.describe()
ln.Run.filter(params__minimum_count=2).to_dataframe()
ln.Run.filter(projects__name="QC study").to_dataframe()
ln.Artifact.filter(transform=run.transform).to_dataframe()
```

Tracking stores code, environment, parameters, and tracked input/output links.
Unregistered reads outside LaminDB need explicit registration/tracking. Do not
mark failed computation as successfully finished. The `params` JSON is distinct
from validated run `features`; arbitrary parameter dictionaries do not create
Feature records automatically.

## Function tracking

```python
@ln.step()
def filter_counts(input_key: str, output_key: str, threshold: int = 2):
    data = ln.Artifact.get(key=input_key).load()
    return ln.Artifact.from_dataframe(
        data[data["count"] >= threshold], key=output_key
    ).save()

@ln.flow()
def analysis():
    return filter_counts("experiments/counts.parquet", "experiments/step.parquet")
```

Invoke `analysis()` from a saved Python script. Decorator parameters are tracked;
function source discovery and code/environment capture depend on execution context.
Do not claim a decorator tracks every external tool or scheduler transition.

## Projects, branches, and spaces

Projects label data/runs; branch and space settings control which records are
created or visible in the current context. Inspect `lamin info` before writes.
The current CLI supports `lamin create project`, `lamin switch -c <branch>`, and
`lamin switch --space <space>`. Branch merging moves metadata records and should
be reviewed in the target instance; it is not a file-system merge or backup.

Sources: [tracking](https://docs.lamin.ai/track),
[change management](https://docs.lamin.ai/manage-changes),
[2.10.0 artifact implementation](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/models/artifact.py).
