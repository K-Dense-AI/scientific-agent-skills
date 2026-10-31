# Trainer configuration and resume

Targets Lightning 2.6.6. See
[`quick_trainer_setup.py`](../scripts/quick_trainer_setup.py) for helpers. These
helpers log locally and monitor `val/loss`, matching the model template. GPU,
FSDP and DeepSpeed configurations remain illustrative on the CPU audit host.

## Loop entry points

`fit(model, train_dataloaders=None, val_dataloaders=None, datamodule=None,
ckpt_path=None, weights_only=None)` trains and optionally validates. Supply
loaders or a DataModule, not both. The `validate`, `test`, and `predict` methods
also accept `model`, `dataloaders`, `datamodule`, `ckpt_path`, and `weights_only`;
`predict` additionally accepts `return_predictions`.

```python
trainer.fit(model, datamodule=dm)
trainer.validate(model, datamodule=dm, ckpt_path="best", weights_only=True)
trainer.test(model, datamodule=dm, ckpt_path="best", weights_only=True)
predictions = trainer.predict(model, datamodule=dm, ckpt_path="best", weights_only=True)
```

These checkpoint aliases require a corresponding checkpoint on this Trainer.
An explicit path is clearer across sessions. Passing a model with no `ckpt_path`
evaluates the supplied weights; it does not select the best checkpoint for you.
Keep the test set independent of model selection and hyperparameter tuning.
`fit` never implicitly calls `test`.

## Parameters that commonly cause mistakes

| Parameter | Contract |
| --- | --- |
| `max_epochs` | Constructor default is `None`; resolves to 1000 only if neither an epoch, step nor time limit is set. Prefer an explicit limit. |
| `max_steps` | Optimizer-step limit, default -1. Stops at the first reached limit together with `max_epochs`. |
| `max_time` | `DD:HH:MM:SS`, `timedelta`, or a timedelta-compatible dict. It requests a stop; it cannot protect against immediate scheduler kill. |
| `accelerator`, `devices` | Use `"cpu", 1` for a smoke test. CPU `devices=4` means four processes, not a four-thread limit. `"gpu"` selects an available GPU backend; CUDA-specific strategies need CUDA. |
| `precision` | `"32-true"` is default. `"16-mixed"` and `"bf16-mixed"` require appropriate hardware/strategy support. |
| `accumulate_grad_batches` | Integer. For changing accumulation use `GradientAccumulationScheduler(scheduling={0: 4, 5: 2})`; do not pass a dict here. |
| `check_val_every_n_epoch` | Defaults to 1; affects checkpoint/early-stop and plateau-scheduler cadence. |
| `val_check_interval` | Float fraction of epoch, integer training-batch count, or a time string/timedelta/dict in 2.6.6. Integer across-epoch checks use `check_val_every_n_epoch=None`. |
| `limit_*_batches` | Integer means a count; float means a fraction, applied per loader. `1` and `1.0` differ. |
| `num_sanity_val_steps` | Default 2; runs validation before training. Exclude sanity checks from custom evaluation artifacts. |
| `logger` | Default enabled: TensorBoard if installed, CSV otherwise. Explicit `logger=False` disables backend logging. |
| `log_every_n_steps` | Default 50. A short run needs a smaller value for step logs. |
| `enable_checkpointing` | Default true. `False` conflicts with a supplied ModelCheckpoint callback. |
| `gradient_clip_val` | Applies to automatic optimization, after precision unscaling. Manual optimization must clip explicitly. |
| `inference_mode` | Default true for validate/test/predict. Use false plus `torch.enable_grad()` for derivative calculations. |
| `benchmark` | Default None preserves current cuDNN state unless deterministic mode makes it false. |

IPU/HPU and other plugin accelerators require their supported external integration;
do not assume an accelerator name in an old example is installed by core
Lightning. Check `Trainer` against the selected release and hardware.

## Meaningful smoke and resume

`fast_dev_run=True` runs one batch in the invoked loops and suppresses logging,
checkpointing and early stopping. It tests basic hook plumbing, not real
checkpoint behavior. Use a short normal CPU fit to test those features:

```python
trainer = L.Trainer(
    accelerator="cpu", devices=1, max_epochs=1,
    limit_train_batches=2, limit_val_batches=2,
    logger=False, enable_progress_bar=False,
    callbacks=[L.pytorch.callbacks.ModelCheckpoint(
        dirpath="checkpoints", monitor="val/loss", save_last=True,
    )],
)
trainer.fit(model, datamodule=dm)
path = trainer.checkpoint_callback.last_model_path
resumed = L.Trainer(accelerator="cpu", devices=1, max_epochs=2, logger=False)
resumed.fit(new_model, datamodule=new_dm, ckpt_path=path, weights_only=True)
```

`max_epochs=2` is the total target, not two additional epochs. A full checkpoint
restores model, optimizer, scheduler, loop, callback and DataModule state.
Recreate the same callback configuration; changing checkpoint directories may
prevent restoration of ranked-file bookkeeping. A weights-only saved checkpoint
cannot resume the optimizer/loop. `load_from_checkpoint` alone is model loading,
not a training resume. Exact continuation additionally depends on RNG, workers,
sampler/stream state, data order, hardware and software versions.

Call `L.seed_everything(seed, workers=True)` **before** constructing model/data.
Use `deterministic=True, benchmark=False` where supported, and record versions,
seeds, split IDs and device count. This does not promise identical results across
PyTorch releases, devices or distributed layouts.

Sources: [Trainer signature and semantics](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/trainer/trainer.py),
[default logger selection](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/trainer/connectors/logger_connector/logger_connector.py),
[PyTorch reproducibility](https://docs.pytorch.org/docs/2.14/notes/randomness.html).
