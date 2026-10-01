# Distributed training contracts

Reviewed against the Lightning 2.6.6 release source. A two-process CPU DDP check validates synchronized means and demonstrates
evaluation sampler padding. It does not validate CUDA collectives, FSDP,
DeepSpeed, TPU or multi-node launching. All multi-device commands below are illustrative and require the
specified hardware, process launcher and compatible dependencies.

## Choose using measured memory

DDP keeps a full model, gradients and optimizer replica on each device. Use it
when each replica plus peak activations fits, and scale after a one-device smoke
run. FSDP shards training state and adds communication; DeepSpeed offers ZeRO
stages and offloading. There is no universal 500M/10B parameter cutoff or
universal fastest strategy: precision, optimizer, sequence length, activations,
batch size and interconnect determine memory and throughput.

```python
from datetime import timedelta
from lightning.pytorch.strategies import DDPStrategy
trainer = L.Trainer(
    accelerator="gpu", devices=4,
    strategy=DDPStrategy(find_unused_parameters=False,
                         gradient_as_bucket_view=True,
                         timeout=timedelta(minutes=30)),
    precision="16-mixed", accumulate_grad_batches=4,
)
```

Use `find_unused_parameters=False` only when all relevant parameters participate
in every backward pass; true adds graph traversal but supports unused parameters.
Set the process-group timeout with `DDPStrategy(timeout=...)`; `NCCL_TIMEOUT`
is not a supported replacement. NCCL is the usual CUDA backend, gloo for CPU.
`ddp_spawn` requires picklable objects and an import-safe main guard and is not a
generic fix for a distributed configuration bug. Prefer a script for scaling.

Effective batch size is local batch times world size times accumulation for
full accumulation windows. A partial final window, token masks and uneven ranks
need separate accounting. Treat linear learning-rate scaling as a hypothesis to
validate, not an automatic rule.

## Sampling, metrics and writes

Lightning replaces ordinary map-style loader samplers by DistributedSampler
when needed. To own sampling, use `use_distributed_sampler=False` and implement
correct rank/worker sharding and epoch reseeding. IterableDataset is not
sharded automatically. DistributedSampler can pad repeated indices when the
sample count is not divisible by world size, including validation/test. For
published metrics use a separate `Trainer(accelerator="cpu", devices=1)` or a
validated nonduplicating distributed evaluator.

`self.log(..., sync_dist=True, batch_size=...)` reduces tensor means across
ranks; all ranks must call it consistently. Use TorchMetrics objects for
nonlinear metrics. Rank-zero-only logging is unsuitable for monitored metrics
that all ranks need. Collect predictions using rank-specific outputs and stable
sample IDs; rank zero alone sees only its shard. `trainer.save_checkpoint` must
be called by every rank because sharded strategies use collectives. Use
rank-zero guards for ordinary shared-file writes that need no collectives.

## FSDP

```python
from lightning.pytorch.strategies import FSDPStrategy
import torch.nn as nn
trainer = L.Trainer(
    accelerator="gpu", devices=4, precision="bf16-mixed",
    strategy=FSDPStrategy(
        auto_wrap_policy={nn.TransformerEncoderLayer},
        activation_checkpointing_policy={nn.TransformerEncoderLayer},
        sharding_strategy="FULL_SHARD", cpu_offload=False,
        state_dict_type="sharded",
    ),
)
```

The policy classes must actually occur in the model. `mixed_precision` on
FSDPStrategy expects a PyTorch `MixedPrecision` object, not `True`; normally let
Trainer precision configure it. `FULL_SHARD` reshards parameters after forward
and backward; `SHARD_GRAD_OP` keeps parameters unsharded between forward and
backward but reshards after backward. It is not merely gradient/optimizer-only
sharding with permanently replicated parameters. `HYBRID_SHARD` shards within
node groups and replicates across them. CPU offloading trades memory for
transfer overhead and has gradient-accumulation constraints; validate the chosen
combination.

Use idempotent `configure_model()` for large model construction in the strategy
context. Do not allocate a giant model unconditionally in `__init__` or use the
deprecated `configure_sharded_model` hook. A sharded checkpoint is a directory;
keep its files together and resume via Trainer with the matching strategy.
`load_from_checkpoint` does not support sharded checkpoints. Full state dicts
are more portable but may require substantial rank-zero CPU memory.

## DeepSpeed

Lightning 2.6.6's DeepSpeedStrategy explicitly requires CUDA, even though
DeepSpeed upstream has other accelerator work. Install PyTorch first and use a
compatible DeepSpeed build; `ds_report` reports available ops. Pip installation
does not inherently compile every CUDA op: many compile just in time and need
their own compiler/toolkit dependencies.

```python
from lightning.pytorch.strategies import DeepSpeedStrategy
trainer = L.Trainer(
    accelerator="gpu", devices=4, precision="16-mixed",
    strategy=DeepSpeedStrategy(stage=3, offload_optimizer=True,
                              offload_parameters=True),
    accumulate_grad_batches=4,
)
```

Stage 1 shards optimizer state, stage 2 also gradients, stage 3 also parameters.
Aliases include `deepspeed_stage_1`, `_2`, `_3`, `_2_offload`, `_3_offload`, and
`deepspeed_stage_3_offload_nvme`. CPU and NVMe offload are distinct settings;
ensure memory/storage bandwidth and explicit writable paths.

Prefer the strategy's typed arguments for a small configuration. If supplying a
DeepSpeed JSON/dict, use actual numeric sizes: Hugging Face's `"auto"` bucket and
batch settings are not a general Lightning/DeepSpeed JSON contract. Verify
optimizer ownership, Trainer accumulation and precision against that config.
Keep the full sharded checkpoint directory for resume; a consolidated FP32
weights file is for model loading, not complete optimizer recovery.

## Multi-node launch

Setting `num_nodes` does not allocate hosts or open rendezvous ports. Every node
needs the same code/dependencies and accessible data/checkpoints. For a SLURM
setup that launches one process per GPU:

```bash
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=4
#SBATCH --gpus-per-node=4
#SBATCH --time=01:00:00
srun python train.py
```

The guarded script constructs `Trainer(accelerator="gpu", devices=4,
num_nodes=2, strategy="ddp")`. On a manually managed cluster, configure the
actual LightningEnvironment variables consistently (MASTER_ADDR, MASTER_PORT,
NODE_RANK) and launch the script on every node, or use a supported `torchrun`
launch with the correct node ranks. Merely parsing `--node_rank` without passing
it to the launcher/environment has no effect.

Sources: [DDP strategy](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/strategies/ddp.py),
[FSDP strategy](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/strategies/fsdp.py),
[FSDP guide](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/docs/source-pytorch/advanced/model_parallel/fsdp.rst),
[DeepSpeed strategy](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/strategies/deepspeed.py),
[DeepSpeed install](https://www.deepspeed.ai/tutorials/advanced-install/),
[cluster guide](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/docs/source-pytorch/clouds/cluster_advanced.rst).
