# LaminDB Integrations

This document covers LaminDB integrations with workflow managers, MLOps platforms, visualization tools, and other third-party systems.

## Overview

LaminDB supports extensive integrations across data storage, computational workflows, machine learning platforms, and visualization tools, enabling seamless incorporation into existing data science and bioinformatics pipelines.

## Data Storage Integrations

### Local Filesystem

```bash
lamin init --storage ./mydata
```

```python
import lamindb as ln

# Save artifacts to local storage
artifact = ln.Artifact("data.csv", key="local/data.csv").save()

# Load from local storage
data = artifact.load()
```

### AWS S3

```bash
# Initialize with S3 storage
export LAMIN_DB_URL='<set-in-secret-manager>'
lamin init --storage s3://my-bucket/path \
  --db "$LAMIN_DB_URL"
```

```python
# Artifacts automatically sync to S3
artifact = ln.Artifact("data.csv", key="experiments/data.csv").save()

# Transparent S3 access
data = artifact.load()  # Downloads from S3 if not cached
```

### S3-Compatible Services

Support for MinIO, Cloudflare R2, and other S3-compatible endpoints:

```bash
# Initialize with custom S3 endpoint
lamin init --storage 's3://bucket?endpoint_url=http://minio.example.com:9000'

# Configure credentials outside shared scripts and do not echo values
export AWS_ACCESS_KEY_ID='<redacted>'
export AWS_SECRET_ACCESS_KEY='<redacted>'
```

### Google Cloud Storage

```bash
# Install GCP extras
uv pip install 'lamindb[gcp]==2.5.1'

# Initialize with GCS
export LAMIN_DB_URL='<set-in-secret-manager>'
lamin init --storage gs://my-bucket/path \
  --db "$LAMIN_DB_URL"
```

```python
# Artifacts sync to GCS
artifact = ln.Artifact("data.csv", key="experiments/data.csv").save()
```

### HTTP/HTTPS (Read-Only)

```python
# Access remote files without copying
artifact = ln.Artifact(
    "https://example.com/data.csv",
    key="remote/data.csv"
).save()

# Stream remote content
with artifact.open() as f:
    data = f.read()
```

### HuggingFace Datasets

```python
# Access HuggingFace datasets
from datasets import load_dataset

dataset = load_dataset("squad", split="train")

# Register as LaminDB artifact
artifact = ln.Artifact.from_dataframe(
    dataset.to_pandas(),
    key="hf/squad_train.parquet",
    description="SQuAD training data from HuggingFace"
).save()
```

## Workflow Manager Integrations

### Nextflow

Track Nextflow pipeline execution and outputs. For current native Nextflow projects, prefer the `nf-lamin` plugin and its `nextflow.config` integration. Inline Python tracking is still useful for custom process scripts.

```python
# In your Nextflow process script
import lamindb as ln

# Initialize tracking
ln.track()

# Your Nextflow process logic
input_artifact = ln.Artifact.get(key="${input_key}")
data = input_artifact.load()

# Process data
result = process_data(data)

# Save output
output_artifact = ln.Artifact.from_dataframe(
    result,
    key="${output_key}"
).save()

ln.finish()
```

**Nextflow config example:**
```nextflow
process ANALYZE {
    input:
    val input_key

    output:
    path "result.csv"

    script:
    """
    #!/usr/bin/env python
    import lamindb as ln
    ln.track()
    artifact = ln.Artifact.get(key="${input_key}")
    # Process and save
    ln.finish()
    """
}
```

### Snakemake

Integrate LaminDB into Snakemake workflows:

```python
# In Snakemake rule
rule process_data:
    input:
        "data/input.csv"
    output:
        "data/output.csv"
    run:
        import lamindb as ln

        ln.track()

        # Load input artifact
        artifact = ln.Artifact.get(key="inputs/data.csv")
        data = artifact.load()

        # Process
        result = analyze(data)

        # Save output
        result.to_csv(output[0])
        ln.Artifact(output[0], key="outputs/result.csv").save()

        ln.finish()
```

### Redun

Track Redun task execution:

```python
from redun import task
import lamindb as ln

@task()
@ln.step()
def process_dataset(input_key: str, output_key: str):
    """Redun task with LaminDB tracking."""
    # Load input
    artifact = ln.Artifact.get(key=input_key)
    data = artifact.load()

    # Process
    result = transform(data)

    # Save output
    ln.Artifact.from_dataframe(result, key=output_key).save()

    return output_key

# Redun automatically tracks lineage alongside LaminDB
```

## MLOps Platform Integrations

### Weights & Biases (W&B)

Combine W&B experiment tracking with LaminDB data management:

```python
import wandb
import lamindb as ln

# Initialize both
wandb.init(project="my-project", name="experiment-1")
ln.track(params={"learning_rate": 0.01, "batch_size": 32})

# Load training data
train_artifact = ln.Artifact.get(key="datasets/train.parquet")
train_data = train_artifact.load()

# Train model
model = train_model(train_data)

# Log to W&B
wandb.log({"accuracy": 0.95, "loss": 0.05})

# Save model in LaminDB
import joblib
joblib.dump(model, "model.pkl")
model_artifact = ln.Artifact(
    "model.pkl",
    key="models/experiment-1.pkl",
    description=f"Model from W&B run {wandb.run.id}"
).save()

# Link W&B run ID
model_artifact.features.set_values({"wandb_run_id": wandb.run.id})

ln.finish()
wandb.finish()
```

### MLflow

Integrate MLflow model tracking with LaminDB:

```python
import mlflow
import lamindb as ln

# Start runs and record parameters in LaminDB
mlflow.start_run()
params = {"max_depth": 5, "n_estimators": 100}
ln.track(params=params)

# Log parameters to MLflow too
mlflow.log_params(params)

# Load data from LaminDB
data_artifact = ln.Artifact.get(key="datasets/features.parquet")
X = data_artifact.load()

# Train and log model
model = train_model(X)
mlflow.sklearn.log_model(model, "model")

# Save to LaminDB
import joblib
joblib.dump(model, "model.pkl")
model_artifact = ln.Artifact(
    "model.pkl",
    key=f"models/{mlflow.active_run().info.run_id}.pkl"
).save()

mlflow.end_run()
ln.finish()
```

### HuggingFace Transformers

Track model fine-tuning with LaminDB:

```python
from transformers import Trainer, TrainingArguments
import lamindb as ln

ln.track(params={"model": "bert-base", "epochs": 3})

# Load training data
train_artifact = ln.Artifact.get(key="datasets/train_tokenized.parquet")
train_dataset = train_artifact.load()

# Configure trainer
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
)

# Train
trainer.train()

# Save model to LaminDB
trainer.save_model("./model")
model_artifact = ln.Artifact(
    "./model",
    key="models/bert_finetuned",
    description="BERT fine-tuned on custom dataset"
).save()

ln.finish()
```

### scVI-tools

Single-cell analysis with scVI and LaminDB:

```python
import scvi
import lamindb as ln

ln.track()

# Load data
adata_artifact = ln.Artifact.get(key="scrna/raw_counts.h5ad")
adata = adata_artifact.load()

# Setup scVI
scvi.model.SCVI.setup_anndata(adata, layer="counts")

# Train model
model = scvi.model.SCVI(adata)
model.train()

# Save latent representation
adata.obsm["X_scvi"] = model.get_latent_representation()

# Save results
result_artifact = ln.Artifact.from_anndata(
    adata,
    key="scrna/scvi_latent.h5ad",
    description="scVI latent representation"
).save()

ln.finish()
```

## Array Store Integrations

### TileDB-SOMA

Scalable array storage with cellxgene support:

```python
import tiledbsoma as soma
import lamindb as ln

# Create SOMA experiment
uri = "tiledb://my-namespace/experiment"

with soma.Experiment.create(uri) as exp:
    # Add measurements
    exp.add_new_collection("RNA")

    # Register in LaminDB
    artifact = ln.Artifact(
        uri,
        key="cellxgene/experiment.soma",
        description="TileDB-SOMA experiment"
    ).save()

# Query with SOMA
with soma.Experiment.open(uri) as exp:
    obs = exp.obs.read().to_pandas()
```

### DuckDB

Query artifacts with DuckDB:

```python
import duckdb
import lamindb as ln

# Get artifact
artifact = ln.Artifact.get(key="datasets/large_data.parquet")

# Query with DuckDB (without loading full file)
path = artifact.cache()
result = duckdb.query(f"""
    SELECT cell_type, COUNT(*) as count
    FROM read_parquet('{path}')
    GROUP BY cell_type
    ORDER BY count DESC
""").to_df()

# Save query result
result_artifact = ln.Artifact.from_dataframe(
    result,
    key="analysis/cell_type_counts.parquet"
).save()
```

## Visualization Integrations

### Vitessce

Create interactive visualizations:

```python
from vitessce import VitessceConfig
import lamindb as ln

# Load spatial data
artifact = ln.Artifact.get(key="spatial/visium_slide.h5ad")
adata = artifact.load()

# Create Vitessce configuration
vc = VitessceConfig.from_object(adata)

# Save configuration
import json
config_file = "vitessce_config.json"
with open(config_file, "w") as f:
    json.dump(vc.to_dict(), f)

# Register configuration
config_artifact = ln.Artifact(
    config_file,
    key="visualizations/spatial_config.json",
    description="Vitessce visualization config"
).save()
```

## Schema Module Integrations

### Bionty (Biological Ontologies)

```python
import bionty as bt

# Import biological ontologies
bt.CellType.import_source()
bt.Gene.import_source(organism="human")

# Use in data curation
cell_types = bt.CellType.from_values(adata.obs.cell_type)
```

### WetLab

Track wet lab experiments:

```bash
# Install wetlab module
uv pip install 'lamindb-wetlab==<reviewed-version>'
```

```python
# Use wetlab registries
import lamindb_wetlab as wetlab

# Track experiments, samples, protocols
experiment = wetlab.Experiment(name="RNA-seq batch 1").save()
```

### Clinical Data

```bash
# Install the relevant clinical schema module after confirming its current release
uv pip install '<clinical-module>==<reviewed-version>'
```

```python
# Use the selected clinical schema module, such as clinicore or an OMOP module
import clinicore as clinical

# Track clinical data
patient = clinical.Patient(patient_id="P001").save()
```

## Git Integration

### Sync with Git Repositories

```bash
export LAMINDB_SYNC_GIT_REPO=https://github.com/user/repo.git
lamin settings set dev-dir .
```

```python
# Or programmatically
import lamindb as ln

ln.settings.sync_git_repo = "https://github.com/user/repo.git"

# Scripts tracked with git commits
ln.track()  # Automatically captures git commit hash
# ... your code ...
ln.finish()

# View git information
transform = ln.Transform.get(name="analysis.py")
transform.source_code  # Shows code at git commit
transform.hash        # Git commit hash
```

## Enterprise Integrations

### Benchling

Sync with Benchling registries (requires team/enterprise plan):

```python
# Configure Benchling connection (contact LaminDB team)
# Syncs schemas and data from Benchling registries

# Access synced Benchling data
# Details available through enterprise support
```

## Custom Integration Patterns

### REST API Integration

Validate and sanitize external content before registering it as a LaminDB artifact. Treat REST responses as untrusted until schema validation passes.

```python
import requests
import lamindb as ln

ln.track()

# Fetch from API
response = requests.get("https://api.example.com/data")
data = response.json()

# Convert to DataFrame
import pandas as pd
df = pd.DataFrame(data)

# Validate before saving to LaminDB
schema = ln.Schema.get(name="external_api_schema")
curator = ln.curators.DataFrameCurator(df, schema)
curator.validate()

artifact = curator.save_artifact(
    key="api/fetched_data.parquet",
    description="Data fetched from external API"
)

artifact.features.set_values({"api_url": response.url})

ln.finish()
```

### Database Integration

```python
import os
import pandas as pd
import sqlalchemy as sa
import lamindb as ln

ln.track()

# Connect using a named secret; never paste or print the URL value
engine = sa.create_engine(os.environ["SOURCE_DB_URL"])

# Query data
query = "SELECT * FROM experiments WHERE date > '2025-01-01'"
df = pd.read_sql(query, engine)

# Validate external rows before registration
schema = ln.Schema.get(name="external_experiments_schema")
curator = ln.curators.DataFrameCurator(df, schema)
curator.validate()

artifact = curator.save_artifact(
    key="external_db/experiments_2025.parquet",
    description="Experiments from external database"
)

ln.finish()
```

## Croissant Metadata

Export datasets with Croissant metadata format:

```python
# Create artifact with rich metadata
artifact = ln.Artifact.from_dataframe(
    df,
    key="datasets/published_data.parquet",
    description="Published dataset with Croissant metadata"
).save()

# Export Croissant metadata (requires additional configuration)
# Enables dataset discovery and interoperability
```

## Best Practices for Integrations

1. **Track consistently**: Use `ln.track()` in all integrated workflows
2. **Link IDs**: Store external system IDs (W&B run ID, MLflow experiment ID) as non-secret features
3. **Centralize data**: Use LaminDB as single source of truth for data artifacts
4. **Sync parameters**: Log parameters to both LaminDB and ML platforms
5. **Version together**: Keep code (git), data (LaminDB), and experiments (ML platform) in sync
6. **Cache strategically**: Configure appropriate cache locations for cloud storage
7. **Use ontology-backed annotations**: Link validated Bionty records through module-specific managers such as `artifact.cell_types.add(...)`, schemas, or typed features
8. **Document integrations**: Add descriptions explaining integration context
9. **Test incrementally**: Verify integration with small datasets first
10. **Monitor lineage**: Use `view_lineage()` to ensure integration tracking works

## Troubleshooting Common Issues

**Issue: S3 credentials not found**
```bash
test -n "$AWS_ACCESS_KEY_ID" && echo "AWS_ACCESS_KEY_ID is set"
test -n "$AWS_SECRET_ACCESS_KEY" && echo "AWS_SECRET_ACCESS_KEY is set"
export AWS_DEFAULT_REGION=us-east-1
```

**Issue: GCS authentication failure**
```bash
gcloud auth application-default login
test -n "$GOOGLE_APPLICATION_CREDENTIALS" && echo "GOOGLE_APPLICATION_CREDENTIALS is set"
```

**Issue: Git sync not working**
```bash
# Ensure git repo is set
lamin settings get sync-git-repo

# Ensure you're in git repo
git status

# Commit changes before tracking
git add .
git commit -m "Update analysis"
ln.track()
```

**Issue: MLflow artifacts not syncing**
```python
# Save explicitly to both systems
mlflow.log_artifact("model.pkl")
ln.Artifact("model.pkl", key="models/model.pkl").save()
```
