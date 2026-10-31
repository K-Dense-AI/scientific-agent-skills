# Workflow and storage integrations

The common contract is to load a registered input within a tracked execution,
run the scientific tool, and save the output with its schema and external run
identifiers. An available tutorial does not mean every external service call is
automatically tracked. Cloud/service examples below are source-verified patterns,
not authenticated end-to-end tests.

## Nextflow

Prefer the official `nf-lamin` plugin to hand-injected Python strings. Current
upstream compatibility guidance lists **nf-lamin 0.9.0**, LaminDB >=2.0, and
Nextflow >=25.10.0. Review the plugin configuration for input/output registration,
storage access, and your executor before deployment.

Illustrative `lamin.config`, using a preconfigured Nextflow secret:

```groovy
plugins {
    id 'nf-lamin@0.9.0'
}
lamin {
    instance = 'your-org/your-instance'
    api_key = secrets.LAMIN_API_KEY
}
```

Then run the user's pipeline with `nextflow run <pipeline> -c lamin.config`.
Configure the secret without exposing it in logs or command history. The plugin
can also read `LAMIN_CURRENT_INSTANCE` and `LAMIN_API_KEY` environment variables.
Do not interpolate arbitrary input keys into executable Python/Groovy source.
The placeholder `<pipeline>` is not a literal runnable pipeline name.

Sources: [nf-lamin](https://docs.lamin.ai/nf-lamin),
[Nextflow integration](https://docs.lamin.ai/nextflow).

## Snakemake, Redun, and Python workflows

Use a saved Python script with `ln.track()`/`ln.finish()` at process boundaries,
or a `@ln.flow()` entry point with `@ln.step()` functions as described in
[core concepts](core-concepts.md). The executor must inherit the intended instance
and credentials. Register an external input explicitly if the rule/task only
receives a filesystem path. Avoid assuming a nested step has an active parent
run or that a cached scheduler result means a new Lamin run executed.

Use the official [Snakemake](https://docs.lamin.ai/snakemake) and
[Redun](https://docs.lamin.ai/redun) examples to configure scheduler-specific
lifecycle behavior. These integrations were reviewed as documentation; no live
scheduler was launched in this refresh.

## W&B, MLflow, model training, and Lightning

Persist model/checkpoint files with `Artifact`, then attach the external run ID
as a **defined feature**. This local example is executed without calling either
service; replace the sample IDs only with actual successful run identifiers:

```python
import lamindb as ln

ln.Feature(name="wandb_run_id", dtype=str).save()
ln.Feature(name="mlflow_run_id", dtype=str).save()
# Existing model bytes from a completed, trusted training run:
model_artifact = ln.Artifact("model.bin", key="models/model.bin").save()
model_artifact.features.set_values({"wandb_run_id": "example-local-run"})
```

Upstream also provides `ln.examples.wandb.save_wandb_features()` and
`ln.examples.mlflow.save_mlflow_features()` to register broader feature sets.
Use each service's own lifecycle and upload API separately; a Lamin annotation
does not upload an artifact to that service. Preserve real metrics, split
provenance, hyperparameters, and model/code versions. Do not demonstrate invented
accuracy values as if they were measured.

Hugging Face/scVI training follows the same pattern: load the appropriate object,
train with that library's versioned API, save model files and derived AnnData,
then register those files. A pandas DataFrame is not automatically a compatible
Transformers training Dataset. Only load trusted pickle/joblib models. Lightning
has dedicated helpers under `lamindb.integrations.lightning`; consult its API and
the selected Lightning release instead of inventing callback names.

Sources: [Lamin integrations API](https://docs.lamin.ai/lamindb.integrations),
[W&B feature helper](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/examples/wandb/__init__.py),
[MLflow feature helper](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/examples/mlflow/__init__.py).

## DuckDB and large arrays

For an existing local or cached Parquet artifact, use a bound path, not string
interpolation into SQL. This query is illustrative; install/test DuckDB for the
project before using it on study data:

```python
import duckdb

path = str(artifact.cache())
with duckdb.connect() as connection:
    counts = connection.execute(
        "SELECT condition, count(*) AS n FROM read_parquet(?) GROUP BY condition",
        [path],
    ).df()
ln.Artifact.from_dataframe(counts, key="analysis/condition_counts.parquet").save()
```

Caching downloads the complete file. For true streaming use the format-specific
`Artifact.open()` accessors in [data management](data-management.md).
TileDB-SOMA needs a valid experiment layout, compatible AnnData/SOMA versions,
and a schema describing `obs`/measurements. Creating a generic `RNA` collection
does not build that layout. Optional SOMA/MuData/SpatialData backends were not
executed here; use current [array guidance](https://docs.lamin.ai/arrays).

## Visualization, storage, and external metadata

Vitessce configuration depends on its dataset wrappers, schema, file types, and
serving URLs. `VitessceConfig.from_object(adata)` is not a documented Lamin
integration. Use the official [Vitessce integration](https://docs.lamin.ai/vitessce)
for a supported configuration and ensure a receiving viewer can resolve every
URL; merely saving the JSON does not make private data accessible.

For S3/GCS/custom endpoints see [setup](setup-deployment.md). HTTP/Hugging Face
paths are source locations whose cache/access behavior depends on the supported
filesystem and credentials; registration does not guarantee zero-copy streaming.
For REST/database ingestion, use that service's verified request and pagination
contract, retrieve the complete intended dataset, validate with a Schema, and
save provenance with secrets removed. This skill defines no generic REST
endpoint or universal JSON response schema.

## Schema modules

`bionty` supplies biological registries. `pertdb` supplies perturbations and
related compounds/targets; the official full LaminDB install includes it, but
mount it deliberately (`--modules bionty,pertdb`) for a new relevant instance.
`Record` can represent lab samples/protocols without a fabricated `wetlab`
package API. Clinical/Benchling schemas depend on the actual configured module
or integration; no generic `clinical.Patient(patient_id=...)` contract or
enterprise plan entitlement is assumed.

Sources: [pertdb API](https://docs.lamin.ai/pertdb),
[DuckDB Python API](https://duckdb.org/docs/stable/clients/python/dbapi).
