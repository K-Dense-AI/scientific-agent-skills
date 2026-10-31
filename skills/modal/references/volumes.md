# Modal Volumes

Reviewed against SDK 1.6.0 and the official [Volumes guide](https://modal.com/docs/guide/volumes).
Examples with training/model helpers are illustrative; no cloud persistence test was run.

## Table of Contents

- [Overview](#overview)
- [Creating Volumes](#creating-volumes)
- [Mounting Volumes](#mounting-volumes)
- [Reading and Writing Files](#reading-and-writing-files)
- [CLI Access](#cli-access)
- [Commits and Reloads](#commits-and-reloads)
- [Concurrent Access](#concurrent-access)
- [Volumes v2](#volumes-v2)
- [Common Patterns](#common-patterns)

## Overview

Volumes are Modal's distributed file system, optimized for write-once, read-many workloads like storing model weights and distributing them across containers.

Key characteristics:
- Persistent across function invocations and deployments
- Mountable by multiple functions simultaneously
- Background auto-commits every few seconds
- Final commit on container shutdown

## Creating Volumes

### In Code (Lazy Creation)

```python
vol = modal.Volume.from_name("my-volume", create_if_missing=True)
```

### Via CLI

```bash
modal volume create my-volume

# v2 volume (beta)
modal volume create my-volume --version=2
```

### Programmatic v2

```python
vol = modal.Volume.from_name("my-volume", create_if_missing=True, version=2)
```

## Mounting Volumes

Mount volumes to functions via the `volumes` parameter:

```python
vol = modal.Volume.from_name("model-store", create_if_missing=True)

@app.function(volumes={"/models": vol})
def use_model():
    import json
    # Access files at /models/
    with open("/models/config.json") as f:
        config = json.load(f)
```

Mount multiple volumes:

```python
weights_vol = modal.Volume.from_name("weights")
data_vol = modal.Volume.from_name("datasets")

@app.function(volumes={"/weights": weights_vol, "/data": data_vol})
def train():
    ...
```

## Reading and Writing Files

### Writing

```python
@app.function(volumes={"/data": vol})
def save_results(results):
    import json
    import os

    os.makedirs("/data/outputs", exist_ok=True)
    with open("/data/outputs/results.json", "w") as f:
        json.dump(results, f)
    vol.commit()
```

### Reading

```python
@app.function(volumes={"/data": vol})
def load_results():
    import json
    vol.reload()
    with open("/data/outputs/results.json") as f:
        return json.load(f)
```

### Large Files (Model Weights)

```python
@app.function(volumes={"/models": vol}, gpu="L40S")
def save_model():
    import torch
    model = train_model()
    torch.save(model.state_dict(), "/models/checkpoint.pt")
    vol.commit()

@app.function(volumes={"/models": vol}, gpu="L40S")
def load_model():
    import torch
    vol.reload()
    model = MyModel()
    model.load_state_dict(torch.load("/models/checkpoint.pt", weights_only=True))
    return model
```

## CLI Access

```bash
# List files
modal volume ls my-volume
modal volume ls my-volume /subdir/

# Upload files
modal volume put my-volume local_file.txt
modal volume put my-volume local_file.txt /remote/path/file.txt

# Download files
modal volume get my-volume /remote/file.txt local_file.txt

# Delete a volume
modal volume delete my-volume
```

## Commits and Reloads

Modal auto-commits volume changes in the background every few seconds and on container shutdown.

### Explicit Commit

Persist the writer's changes before signaling downstream work. A commit does not
refresh an already mounted reader; that reader must reload after closing its open
volume file handles:

```python
@app.function(volumes={"/data": vol})
def writer():
    with open("/data/file.txt", "w") as f:
        f.write("hello")
    vol.commit()  # Persist; already mounted readers still need reload()
```

### Reload

See changes from other containers:

```python
@app.function(volumes={"/data": vol})
def reader():
    vol.reload()  # Refresh to see latest writes
    with open("/data/file.txt") as f:
        return f.read()
```

Close all file handles first, and do not read/write the mount while `reload()` runs:
it temporarily appears empty to the reloading container. Reload from the mounted
Function; a local SDK call does not refresh a remote container's mount.

## Concurrent Access

### v1 Volumes

- Recommended max 5 concurrent commits
- Last write wins for concurrent modifications of the same file
- Avoid concurrent modification of identical files
- Max 500,000 files (inodes)

### v2 Volumes

- Hundreds of concurrent writers (distinct files)
- No file count limit
- Improved random access performance
- Files strictly smaller than 1 TiB; at most 262,144 files per directory

## Volumes v2

v2 Volumes (beta) offer significant improvements:
The official guide does not yet guarantee against data loss. Retain another copy
of irreplaceable research data; do not treat v2 as the sole durable archive.

| Feature | v1 | v2 |
|---------|----|----|
| Max files | 500,000 | Unlimited |
| Concurrent writes | ~5 | Hundreds |
| Max file size | No documented limit | Less than 1 TiB |
| Random access | Limited | Full support |
| Hard links | No | Yes |

Enable v2:

```python
vol = modal.Volume.from_name("my-vol-v2", create_if_missing=True, version=2)
```

## Common Patterns

### Model Weight Storage

```python
vol = modal.Volume.from_name("model-weights", create_if_missing=True)

# Download once during image build
def download_weights():
    from huggingface_hub import snapshot_download
    snapshot_download("openai-community/gpt2", local_dir="/models/gpt2")
    vol.commit()

image = (
    modal.Image.debian_slim()
    .uv_pip_install("huggingface_hub")
    .run_function(download_weights, volumes={"/models": vol})
)
```

Mount the same Volume in consuming Functions. A cached `run_function` build step
does not rerun if Volume files are later removed; use a dedicated download Function
when population must be checked independently of the Image cache.

### Training Checkpoints

```python
@app.function(volumes={"/checkpoints": vol}, gpu="H100", timeout=86400)
def train():
    for epoch in range(100):
        train_one_epoch()
        torch.save(model.state_dict(), f"/checkpoints/epoch_{epoch}.pt")
        vol.commit()  # Save checkpoint immediately
```

### Shared Data Between Functions

```python
data_vol = modal.Volume.from_name("shared-data", create_if_missing=True)

@app.function(volumes={"/data": data_vol})
def preprocess():
    # Write processed data
    df.to_parquet("/data/processed.parquet")
    data_vol.commit()

@app.function(volumes={"/data": data_vol})
def analyze():
    data_vol.reload()  # Ensure we see latest data
    df = pd.read_parquet("/data/processed.parquet")
    return df.describe()
```

### Performance Tips

- Volumes are optimized for large files, not many small files
- Keep under 50,000 files and directories for best v1 performance
- Use Parquet or other columnar formats instead of many small CSVs
- For truly temporary data, use `ephemeral_disk` instead of Volumes
