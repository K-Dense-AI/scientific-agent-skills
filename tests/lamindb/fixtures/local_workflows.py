"""Synthetic, local-only workflows; invoked from a temporary working directory."""
from datetime import date
from pathlib import Path

import lamindb_setup as setup

setup.init(storage="./storage", name="local-contracts", modules="bionty")

import anndata as ad
import bionty as bt
import lamindb as ln
import numpy as np
import pandas as pd

count = ln.Feature(name="gene_count", dtype=int).save()
condition = ln.Feature(name="condition", dtype=str).save()
schema = ln.Schema(
    name="strict", features=[count, condition], maximal_set=True
).save()
frame = pd.DataFrame({"gene_count": [120, 130], "condition": ["control", "treated"]})
curator = ln.curators.DataFrameCurator(frame, schema)
assert curator.validate() is None
artifact = curator.save_artifact(key="experiments/qc.parquet")
assert artifact.schema == schema
pd.testing.assert_frame_equal(artifact.load(), frame)
assert artifact.open().count_rows() == 2
assert sum(batch.num_rows for batch in artifact.open().to_batches(batch_size=1)) == 2

# Missing required columns, unexpected columns and wrong dtypes must reject data.
for invalid in [
    frame.drop(columns="condition"), frame.assign(extra=[1, 2]),
    frame.assign(gene_count=["not-an-int", "bad"]),
]:
    try:
        ln.curators.DataFrameCurator(invalid, schema).validate()
    except ln.errors.ValidationError:
        pass
    else:
        raise AssertionError("invalid table was accepted")

# flexible=False does not mean a closed schema.
minimal = ln.Schema(name="minimal", features=[count, condition]).save()
assert ln.curators.DataFrameCurator(frame.assign(extra=[1, 2]), minimal).validate() is None

batch = ln.Feature(name="batch", dtype=int).save()
observed = ln.Feature(name="experiment_date", dtype=date, coerce=True).save()
artifact.features.set_values({batch: 1, observed: "2026-09-30"})
assert ln.Artifact.filter(batch=1).one() == artifact
assert ln.Artifact.filter(batch == 1).one() == artifact
assert not ln.Artifact.filter(key="missing").one_or_none()
assert len(ln.Artifact.filter(batch=1).to_dataframe(include="features", limit=None)) == 1

changed = frame.assign(gene_count=[121, 131])
new = ln.Artifact.from_dataframe(
    changed, key="experiments/qc.parquet", revises=artifact, version_tag="2"
).save()
assert ln.Artifact.get(key="experiments/qc.parquet") == new
assert ln.Artifact.get(artifact.uid) == artifact
assert new.versions.count() == 2
assert new.versions.get(version_tag="2") == new
collection = ln.Collection([artifact, new], key="study/qc").save()
assert set(collection.artifacts.all()) == {artifact, new}

# Local synthetic vocabulary: no ontology downloads or real biology assertions.
parent = bt.CellType(name="Example parent cell").save()
child = bt.CellType(name="Example child cell").save()
child.parents.add(parent)
child.add_synonym("Example alias")
assert list(bt.CellType.standardize(["Example alias"])) == ["Example child cell"]
assert bt.CellType.validate(["Example child cell"], field=bt.CellType.name).all()
assert child in parent.query_children()
assert parent in child.query_parents()
records = bt.CellType.from_values(["Example child cell"], field=bt.CellType.name)
records.save()
new.cell_types.add(*records)
assert ln.Artifact.filter(cell_types=child).one() == new

cell_type = ln.Feature(name="cell_type", dtype=bt.CellType).save()
obs_schema = ln.Schema(name="obs", features=[cell_type], coerce=True).save()
adata = ad.AnnData(
    np.array([[1., 2.], [3., 4.]]),
    obs=pd.DataFrame({"cell_type": ["Example alias", "Example child cell"]}, index=["c1", "c2"]),
)
anndata_schema = ln.Schema(name="ann", otype="AnnData", slots={"obs": obs_schema}).save()
ann_curator = ln.curators.AnnDataCurator(adata, anndata_schema)
try:
    ann_curator.validate()
except ln.errors.ValidationError:
    pass
ann_curator.slots["obs"].cat.standardize("cell_type")
assert ann_curator.validate() is None
assert list(adata.obs.cell_type) == ["Example child cell", "Example child cell"]
ann = ann_curator.save_artifact(key="scrna/validated.h5ad")
assert ann.schema == anndata_schema
assert ann.load().shape == adata.shape
with ann.open() as accessor:
    assert accessor[:1, :].to_memory().n_obs == 1

sample_type = ln.Record(name="Sample", is_type=True).save()
sample = ln.Record(name="control-1", type=sample_type).save()
artifact.records.add(sample)
label = ln.ULabel(name="reviewed").save()
artifact.ulabels.add(label)
assert ln.Artifact.filter(records=sample, ulabels=label).one() == artifact

# Track a real saved script against real local input/output artifacts.
project = ln.Project(name="QC study").save()
ln.track(project="QC study", params={"minimum_count": 125}, pypackages=False)
data = new.load()
out = ln.Artifact.from_dataframe(
    data[data.gene_count >= 125], key="experiments/filtered.parquet"
).save()
ln.finish()
assert out.run.finished_at is not None
assert new in out.run.input_artifacts.all()
assert out in out.run.output_artifacts.all()
assert out.run in ln.Run.filter(projects=project, params__minimum_count=125)
assert out in ln.Artifact.filter(transform=out.run.transform)

@ln.step()
def filter_counts(input_key: str, output_key: str, threshold: int = 2):
    data = ln.Artifact.get(key=input_key).load()
    return ln.Artifact.from_dataframe(
        data[data.gene_count >= threshold], key=output_key
    ).save()

@ln.flow()
def analysis():
    return filter_counts("experiments/qc.parquet", "experiments/step.parquet", 0)

step_output = analysis()
assert step_output.run is not None

# External-system IDs are annotations, with no calls to external services.
Path("model.bin").write_bytes(b"synthetic model fixture")
ln.Feature(name="wandb_run_id", dtype=str).save()
ln.Feature(name="mlflow_run_id", dtype=str).save()
model = ln.Artifact("model.bin", key="models/model.bin").save()
model.features.set_values({"wandb_run_id": "example-local-run"})
assert ln.Artifact.filter(wandb_run_id="example-local-run").one() == model
print("[OK] local Lamin contracts")
