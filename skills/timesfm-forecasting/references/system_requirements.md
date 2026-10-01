# Resource and backend checks

Run `python scripts/check_system.py --model v2.5` before initial model loading.
Use `--json` for machine-readable output; exit 1 indicates a failed threshold.
`--model v3.0` provides a separate resource estimate; it does not grant permission
to use restricted weights or validate the 3.0 API.

The checker measures total/available RAM, CUDA or MPS availability, free space
on the configured Hub cache volume, Python and package importability. On macOS
`vm_stat` uses the page size reported by the OS (often 16,384 bytes), not a fixed
4,096-byte multiplier. Unknown measurements warn instead of fabricating RAM.

Thresholds are local heuristics, not published hardware minima or peak-RSS
predictions. For 2.5 they block below 2 GiB available RAM or 2 GiB free cache
space and warn below 4 GiB available RAM. Batch size recommendation is always 1
until the user measures the actual workload. Temporary copies, compiler caches,
activations, other processes and model/backend changes may require much more.
No preflight can guarantee the process will avoid OOM.

## Devices

The 2.5 torch loader automatically uses CUDA:0 when CUDA is available, otherwise
CPU. It does not auto-select Apple MPS even if PyTorch detects it. MPS detection
is reported as informational/warning, and the effective 2.5 mode stays CPU.
A tiny CUDA device may still OOM; its reported VRAM is total, not necessarily
free. Multi-device count affects the upstream batch calculation; do not infer
that this wrapper distributes weights across GPUs.

3.0 supports an explicit torch device and a separate MLX backend. See
`timesfm3.md`. Neither GPU nor MLX performance was tested in this refresh.

## Install and cache

Package 3.0.2 declares Python >=3.10, NumPy >=1.26.4,
huggingface_hub >=0.28.0 and safetensors >=0.5.3. Its torch extra declares
PyTorch >=2.0.0. The tested CPU stack uses Python 3.13, PyTorch 2.14.1,
NumPy 2.5.3 and pandas 3.0.6. Platform wheel/interpreter support depends on
those selected releases; do not equate the package's minimum with every backend's.

XReg needs JAX and scikit-learn, not Flax. Current JAX 0.11.2 requires Python
>=3.12. On macOS install CPU `jax`, not `jax[cuda]`. The upstream Flax extra
also requests CUDA JAX; a CPU Flax setup needs individually compatible packages
and was not runtime-tested here. Matplotlib/Pillow are for optional plots/GIFs.

Cache precedence is `HF_HUB_CACHE`, otherwise `HF_HOME/hub`, otherwise
`XDG_CACHE_HOME/huggingface/hub` (default `~/.cache/huggingface/hub`). The checker
uses the nearest existing ancestor to check the correct filesystem before a
new directory exists. The 2.5 float32 checkpoint is roughly 0.8 GB; this excludes
framework packages, temporary files and compiler artifacts.

```bash
# Public model; network/download needed only when it is not already cached.
hf download google/timesfm-2.5-200m-pytorch \
  --revision 1d952420fba87f3c6dee4f240de0f1a0fbc790e3
```

Use `local_files_only=True` for offline loading of a populated cache. Do not
force-download a checkpoint routinely. The [Hub CLI](https://huggingface.co/docs/huggingface_hub/en/guides/cli)
is `hf`, replacing the old `huggingface-cli` spelling.
