# Modal GPU Compute

Reviewed against SDK 1.6.0, the [GPU guide](https://modal.com/docs/guide/gpu),
[multi-node guide](https://modal.com/docs/guide/multi-node-clusters) and
[RTX PRO release](https://modal.com/blog/product-updates-rtx-pro-6000-command-k-sandbox-fs-api-and-more).
GPU allocation and model workloads were not executed. A payment method is required.

## Table of Contents

- [Available GPUs](#available-gpus)
- [Requesting GPUs](#requesting-gpus)
- [GPU Selection Guide](#gpu-selection-guide)
- [Multi-GPU](#multi-gpu)
- [GPU Fallback Chains](#gpu-fallback-chains)
- [Auto-Upgrades](#auto-upgrades)
- [Multi-GPU Training](#multi-gpu-training)

## Available GPUs

| GPU | VRAM | Max per Container | Best For |
|-----|------|-------------------|----------|
| T4 | 16 GB | 8 | Budget inference, small models |
| L4 | 24 GB | 8 | Inference, video processing |
| A10 | 24 GB | 4 | Inference, fine-tuning small models |
| L40S | 48 GB | 8 | Inference (best cost/perf), medium models |
| A100-40GB | 40 GB | 8 | Training, large model inference |
| A100-80GB | 80 GB | 8 | Training, large models |
| RTX-PRO-6000 | 96 GB | Confirm workspace capacity | Rendering, inference |
| H100 | 80 GB | 8 | Large-scale training, fast inference |
| H200 | 141 GB | 8 | Very large models, training |
| B200 | 192 GB | 8 | Largest models, maximum throughput |
| B200+ | 192 or 288 GB | 8 | B200 or B300, B200 pricing |
| B300 | 288 GB | 8 | Large models, CUDA 13.1+ |

## Requesting GPUs

### Basic Request

```python
@app.function(gpu="H100")
def train():
    import torch
    assert torch.cuda.is_available()
    print(f"Using: {torch.cuda.get_device_name(0)}")
```

### String Shorthand

```python
gpu="T4"           # Single T4
gpu="A100-80GB"    # Single A100 80GB
gpu="H100:4"       # Four H100s
```

### Case-Insensitive Strings

GPU strings are case-insensitive, so `gpu="h100"` and `gpu="H100"` are equivalent.

> **Deprecation:** The legacy `modal.gpu.*` objects (e.g. `modal.gpu.H100(count=2)`) are deprecated as of v0.73.31. Always configure GPUs with strings — use `gpu="H100:2"` for multiple GPUs and `gpu="A100-80GB"` for the 80 GB A100.

## GPU Selection Guide

### For Inference

These are starting points, not fit guarantees: account for precision/quantization,
weights, activations, KV cache and batch/context length. A 70B BF16 model needs
about 140 GB for weights alone and does not fit on one 80 GB H100.

| Model Size | Recommended GPU | Why |
|-----------|----------------|-----|
| < 7B params | T4, L4 | Cost-effective, sufficient VRAM |
| 7B-13B params | L40S | Best cost/performance, 48 GB VRAM |
| 13B-70B params | A100-80GB, H100 | Large VRAM, fast memory bandwidth |
| 70B+ params | H100:2+, H200, B200 | Multi-GPU or very large VRAM |

### For Training

| Task | Recommended GPU |
|------|----------------|
| Fine-tuning (LoRA) | L40S, A100-40GB |
| Full fine-tuning small models | A100-80GB |
| Full fine-tuning large models | H100:4+, H200 |
| Pre-training | H100:8, B200:8 |

### General Recommendation

L40S is the best default for inference workloads — it offers an excellent trade-off of cost and performance with 48 GB of GPU RAM.

## Multi-GPU

Request multiple GPUs by appending `:count`:

```python
@app.function(gpu="H100:4")
def distributed():
    import torch
    print(f"GPUs available: {torch.cuda.device_count()}")
    # All 4 GPUs are on the same physical machine
```

- Up to 8 GPUs for most types (up to 4 for A10)
- All GPUs attach to the same physical machine
- Requesting more than 2 GPUs may result in longer wait times
- Maximum listed single-node VRAM: 8 x B300 = 2,304 GB

## GPU Fallback Chains

Specify a prioritized list of GPU types:

```python
@app.function(gpu=["H100", "A100-80GB", "L40S"])
def flexible():
    # Modal tries H100 first, then A100-80GB, then L40S
    ...
```

Useful for reducing queue times when a specific GPU isn't available.

## Auto-Upgrades

### H100 → H200

Modal may automatically upgrade H100 requests to H200 at no extra cost. To prevent this:

```python
@app.function(gpu="H100!")  # Exclamation mark prevents auto-upgrade
def must_use_h100():
    ...
```

### A100 → A100-80GB

`gpu="A100"` requests may be upgraded to 80GB at no extra cost.
Use `gpu="A100-40GB"` when you specifically require the 40GB variant.

### B200+

`gpu="B200+"` allows Modal to run on B200 or B300 GPUs at B200 pricing.
Both `B200+` and direct `B300` requests require a stack compatible with CUDA 13.1+.

## Multi-GPU Training

Modal 1.6 adds `@modal.clustered(size=N)` and `modal.Cluster.from_context()` for
multi-node Functions and Servers. The dedicated current guide supersedes the older
GPU page's private-beta wording. Clustered jobs require full GPU nodes (e.g. H100:8),
not CPU-only jobs or partial H100:4 nodes; verify workspace availability before use.
The snippets below are single-node launcher templates, not tested training jobs.

### PyTorch DDP Example

```python
# train.py must implement distributed training and read torchrun's rank variables.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install("torch")
    .add_local_file("train.py", "/root/train.py")
)

@app.function(gpu="H100:4", image=image, timeout=86400)
def train_distributed():
    import subprocess
    subprocess.run([
        "torchrun", "--standalone", "--nnodes=1", "--nproc-per-node=4",
        "/root/train.py",
    ], check=True)
```

Requesting four GPUs does not start four Python workers. The launcher establishes
`RANK`, `WORLD_SIZE` and `LOCAL_RANK`; initialize the process group inside `train.py`.

### PyTorch Lightning

When using frameworks that re-execute Python entrypoints (like PyTorch Lightning), either:

1. Use a strategy supported by the installed Lightning release (the Modal guide lists `ddp_spawn` / `ddp_notebook`)
2. Or run training as a subprocess

```python
@app.function(gpu="H100:4", image=image)
def train():
    import subprocess
    subprocess.run(["python", "train_script.py"], check=True)
```

### Hugging Face Accelerate

Install `accelerate` in the Image and include `train.py` with `add_local_file`.

```python
@app.function(gpu="A100-80GB:4", image=image)
def finetune():
    import subprocess
    subprocess.run([
        "accelerate", "launch",
        "--num_processes", "4",
        "train.py"
    ], check=True)
```

> **Security:** These launchers use fixed, hardcoded argument lists. Never build the
> `subprocess` argument list from unsanitized user input. If a workload needs
> user-supplied values (e.g. hyperparameters), validate them against an allowlist or
> pass them as files / environment variables rather than as command arguments.
