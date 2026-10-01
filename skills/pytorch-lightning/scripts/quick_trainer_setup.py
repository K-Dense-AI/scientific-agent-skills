"""
Quick Trainer Setup Examples for PyTorch Lightning.

Targets Lightning 2.6.6. Helpers use local loggers and monitor val/loss, matching
template_lightning_module.py. GPU/FSDP/DeepSpeed configurations are illustrative;
CPU tests exercise the single-device helper with explicit CPU/full-precision overrides.
This script provides Trainer configurations for common use cases.
Copy and modify these configurations for your specific needs.
"""

import lightning as L
from lightning.pytorch.callbacks import (
    ModelCheckpoint,
    EarlyStopping,
    LearningRateMonitor,
)
from lightning.pytorch import loggers as pl_loggers
from lightning.pytorch.strategies import DDPStrategy, FSDPStrategy


# =============================================================================
# 1. BASIC TRAINING (Single GPU/CPU)
# =============================================================================

def basic_trainer():
    """
    Simple trainer for quick prototyping.
    Use for: Small models, debugging, single GPU training
    """
    trainer = L.Trainer(
        max_epochs=10,
        accelerator="auto",  # Automatically select GPU/CPU
        devices=1,           # Keep the basic smoke run on one device
        enable_progress_bar=True,
        logger=pl_loggers.CSVLogger("logs", name="basic"),
    )
    return trainer


# =============================================================================
# 2. DEBUGGING CONFIGURATION
# =============================================================================

def debug_trainer():
    """
    Trainer for debugging with fast dev run and anomaly detection.
    Use for: Finding bugs, testing code quickly
    """
    trainer = L.Trainer(
        fast_dev_run=True,           # Run 1 batch through train/val/test
        accelerator="cpu",            # Use CPU for easier debugging
        detect_anomaly=True,          # Detect NaN/Inf in gradients
        log_every_n_steps=1,         # Log every step
        enable_progress_bar=True,
    )
    return trainer


# =============================================================================
# 3. PRODUCTION TRAINING (Single GPU)
# =============================================================================

def production_single_gpu_trainer(
    max_epochs=100,
    log_dir="logs",
    checkpoint_dir="checkpoints",
    accelerator="gpu",
    precision="16-mixed",
):
    """
    Production-ready trainer for single GPU with checkpointing and logging.
    Use for: Final training runs on single GPU
    """
    # Callbacks
    checkpoint_callback = ModelCheckpoint(
        dirpath=checkpoint_dir,
        filename="epoch-{epoch:02d}-step-{step:06d}",
        auto_insert_metric_name=False,
        monitor="val/loss",
        mode="min",
        save_top_k=3,
        save_last=True,
        verbose=True,
    )

    early_stop_callback = EarlyStopping(
        monitor="val/loss",
        patience=10,
        mode="min",
        verbose=True,
    )

    lr_monitor = LearningRateMonitor(logging_interval="step")

    # Logger
    csv_logger = pl_loggers.CSVLogger(
        save_dir=log_dir,
        name="my_model",
    )

    # Trainer
    trainer = L.Trainer(
        max_epochs=max_epochs,
        accelerator=accelerator,
        devices=1,
        precision=precision,        # Mixed precision for speed
        callbacks=[
            checkpoint_callback,
            early_stop_callback,
            lr_monitor,
        ],
        logger=csv_logger,
        log_every_n_steps=50,
        gradient_clip_val=1.0,       # Clip gradients
        enable_progress_bar=True,
    )

    return trainer


# =============================================================================
# 4. MULTI-GPU TRAINING (DDP)
# =============================================================================

def multi_gpu_ddp_trainer(
    max_epochs=100,
    num_gpus=4,
    log_dir="logs",
    checkpoint_dir="checkpoints"
):
    """
    Multi-GPU training with Distributed Data Parallel.
    Use when a full replica plus optimizer state and activations fits per GPU
    """
    # Callbacks
    checkpoint_callback = ModelCheckpoint(
        dirpath=checkpoint_dir,
        filename="epoch-{epoch:02d}-step-{step:06d}",
        auto_insert_metric_name=False,
        monitor="val/loss",
        mode="min",
        save_top_k=3,
        save_last=True,
    )

    early_stop_callback = EarlyStopping(
        monitor="val/loss",
        patience=10,
        mode="min",
    )

    lr_monitor = LearningRateMonitor(logging_interval="step")

    # Logger
    csv_logger = pl_loggers.CSVLogger(
        name="my-project",
        save_dir=log_dir,
    )

    # Trainer
    trainer = L.Trainer(
        max_epochs=max_epochs,
        accelerator="gpu",
        devices=num_gpus,
        strategy=DDPStrategy(
            find_unused_parameters=False,
            gradient_as_bucket_view=True,
        ),
        precision="16-mixed",
        callbacks=[
            checkpoint_callback,
            early_stop_callback,
            lr_monitor,
        ],
        logger=csv_logger,
        log_every_n_steps=50,
        gradient_clip_val=1.0,
        sync_batchnorm=True,         # Sync batch norm across GPUs
    )

    return trainer


# =============================================================================
# 5. LARGE MODEL TRAINING (FSDP)
# =============================================================================

def large_model_fsdp_trainer(
    max_epochs=100,
    num_gpus=8,
    log_dir="logs",
    checkpoint_dir="checkpoints"
):
    """
    Training for memory-constrained models with FSDP.
    Use for: Large transformers, models that don't fit in single GPU
    """
    import torch.nn as nn

    # Callbacks
    checkpoint_callback = ModelCheckpoint(
        dirpath=checkpoint_dir,
        filename="epoch-{epoch:02d}-step-{step:06d}",
        auto_insert_metric_name=False,
        monitor="val/loss",
        mode="min",
        save_top_k=3,
        save_last=True,
    )

    lr_monitor = LearningRateMonitor(logging_interval="step")

    # Logger
    csv_logger = pl_loggers.CSVLogger(
        name="large-model",
        save_dir=log_dir,
    )

    # Trainer with FSDP
    trainer = L.Trainer(
        max_epochs=max_epochs,
        accelerator="gpu",
        devices=num_gpus,
        strategy=FSDPStrategy(
            sharding_strategy="FULL_SHARD",
            activation_checkpointing_policy={
                nn.TransformerEncoderLayer,
                nn.TransformerDecoderLayer,
            },
            cpu_offload=False,       # Set True if GPU memory insufficient
        ),
        precision="bf16-mixed",      # BFloat16 for A100/H100
        callbacks=[
            checkpoint_callback,
            lr_monitor,
        ],
        logger=csv_logger,
        log_every_n_steps=10,
        gradient_clip_val=1.0,
        accumulate_grad_batches=4,   # Gradient accumulation
    )

    return trainer


# =============================================================================
# 6. VERY LARGE MODEL TRAINING (DeepSpeed)
# =============================================================================

def deepspeed_trainer(
    max_epochs=100,
    num_gpus=8,
    stage=3,
    log_dir="logs",
    checkpoint_dir="checkpoints"
):
    """
    Training for very large models with DeepSpeed.
    Use when ZeRO sharding is needed; measure memory and throughput
    """
    if stage not in (1, 2, 3):
        raise ValueError("DeepSpeed stage must be 1, 2, or 3")

    # Callbacks
    checkpoint_callback = ModelCheckpoint(
        dirpath=checkpoint_dir,
        filename="{epoch:02d}-{step:06d}",
        monitor="val/loss",          # Required: save_top_k > 1 needs a quantity
        mode="min",
        save_top_k=3,
        save_last=True,
        every_n_epochs=1,           # Rank using fresh validation metrics
    )

    lr_monitor = LearningRateMonitor(logging_interval="step")

    # Logger
    csv_logger = pl_loggers.CSVLogger(
        name="very-large-model",
        save_dir=log_dir,
    )

    # Select DeepSpeed stage
    strategy = f"deepspeed_stage_{stage}"

    # Trainer
    trainer = L.Trainer(
        max_epochs=max_epochs,
        accelerator="gpu",
        devices=num_gpus,
        strategy=strategy,
        precision="16-mixed",
        callbacks=[
            checkpoint_callback,
            lr_monitor,
        ],
        logger=csv_logger,
        log_every_n_steps=10,
        gradient_clip_val=1.0,
        accumulate_grad_batches=4,
    )

    return trainer


# =============================================================================
# 7. HYPERPARAMETER TUNING
# =============================================================================

def hyperparameter_tuning_trainer(max_epochs=50):
    """
    Lightweight trainer for hyperparameter search.
    Use for: Quick experiments, hyperparameter tuning
    """
    trainer = L.Trainer(
        max_epochs=max_epochs,
        accelerator="auto",
        devices=1,
        enable_checkpointing=False,  # Don't save checkpoints
        logger=False,                 # Disable logging
        enable_progress_bar=False,
        limit_train_batches=0.5,     # Use 50% of training data
        limit_val_batches=0.5,       # Use 50% of validation data
    )
    return trainer


# =============================================================================
# 8. OVERFITTING TEST
# =============================================================================

def overfit_test_trainer(num_batches=10):
    """
    Trainer for overfitting on small subset to verify model capacity.
    Use for: Testing if model can learn, debugging
    """
    trainer = L.Trainer(
        max_epochs=100,
        accelerator="auto",
        devices=1,
        overfit_batches=num_batches,  # Overfit on N batches
        log_every_n_steps=1,
        enable_progress_bar=True,
    )
    return trainer


# =============================================================================
# 9. TIME-LIMITED TRAINING (SLURM)
# =============================================================================

def time_limited_trainer(
    max_time_hours=23.5,
    max_epochs=1000,
    checkpoint_dir="checkpoints"
):
    """
    Training with time limit for SLURM clusters.
    Use for: Cluster jobs with time limits
    """
    from datetime import timedelta

    checkpoint_callback = ModelCheckpoint(
        dirpath=checkpoint_dir,
        monitor="val/loss",          # Required: save_top_k > 1 needs a quantity
        mode="min",
        save_top_k=3,
        save_last=True,              # Important for resuming
        every_n_epochs=1,
    )

    trainer = L.Trainer(
        max_epochs=max_epochs,
        max_time=timedelta(hours=max_time_hours),
        accelerator="gpu",
        devices="auto",
        callbacks=[checkpoint_callback],
        log_every_n_steps=50,
    )

    return trainer


# =============================================================================
# 10. REPRODUCIBLE RESEARCH
# =============================================================================

def reproducible_trainer(seed=42, max_epochs=100):
    """
    Seeded trainer for repeatable runs on the same software/hardware stack.
    Use for: Publications, reproducible results
    """
    # Call this before creating the model and DataModule.
    L.seed_everything(seed, workers=True)

    # Callbacks
    checkpoint_callback = ModelCheckpoint(
        dirpath="checkpoints",
        filename="epoch-{epoch:02d}-step-{step:06d}",
        auto_insert_metric_name=False,
        monitor="val/loss",
        mode="min",
        save_top_k=3,
        save_last=True,
    )

    # Trainer
    trainer = L.Trainer(
        max_epochs=max_epochs,
        accelerator="gpu",
        devices=1,
        precision="32-true",         # Full precision for reproducibility
        deterministic=True,          # Use deterministic algorithms
        benchmark=False,             # Disable cudnn benchmarking
        callbacks=[checkpoint_callback],
        log_every_n_steps=50,
    )

    return trainer


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    from lightning.pytorch.accelerators import CUDAAccelerator

    # Trainer construction validates the requested hardware, so the GPU-only
    # configurations below can only be built where that hardware exists.
    cuda_devices = CUDAAccelerator.auto_device_count() if CUDAAccelerator.is_available() else 0

    print("PyTorch Lightning Trainer Configurations\n")

    # Example 1: Basic training
    print("1. Basic Trainer:")
    trainer = basic_trainer()
    print(f"   - Max epochs: {trainer.max_epochs}")
    print(f"   - Accelerator: {trainer.accelerator}")
    print()

    # Example 2: Debug training
    print("2. Debug Trainer:")
    trainer = debug_trainer()
    print(f"   - Fast dev run: {trainer.fast_dev_run}")
    print(f"   - Accelerator: {trainer.accelerator}")
    print()

    # Example 3: Production single GPU
    print("3. Production Single GPU Trainer:")
    if cuda_devices >= 1:
        trainer = production_single_gpu_trainer(max_epochs=100)
        print(f"   - Max epochs: {trainer.max_epochs}")
        print(f"   - Precision: {trainer.precision}")
        print(f"   - Callbacks: {len(trainer.callbacks)}")
    else:
        print("   - skipped: no CUDA GPU on this machine")
    print()

    # Example 4: Multi-GPU DDP
    print("4. Multi-GPU DDP Trainer:")
    if cuda_devices >= 4:
        trainer = multi_gpu_ddp_trainer(num_gpus=4)
        print(f"   - Strategy: {trainer.strategy}")
        print(f"   - Devices: {trainer.num_devices}")
    else:
        print(f"   - skipped: needs 4 CUDA GPUs, found {cuda_devices}")
    print()

    # Example 5: FSDP for large models
    print("5. FSDP Trainer for Large Models:")
    if cuda_devices >= 8:
        trainer = large_model_fsdp_trainer(num_gpus=8)
        print(f"   - Strategy: {trainer.strategy}")
        print(f"   - Precision: {trainer.precision}")
    else:
        print(f"   - skipped: needs 8 CUDA GPUs, found {cuda_devices}")
    print()

    print("\nTo use these configurations:")
    print("1. Import the desired function")
    print("2. Create trainer: trainer = production_single_gpu_trainer()")
    print("3. Train model: trainer.fit(model, datamodule=dm)")
