# LightningModule contracts

Reviewed against Lightning 2.6.6. The executable example is
[`template_lightning_module.py`](../scripts/template_lightning_module.py).
Fragments with project-defined names below are illustrative.

## Model and hooks

Implement `__init__`, `forward`, `training_step`, and `configure_optimizers`.
Validation, test, and prediction are separate hooks; `fit()` does not run `test()`.
Automatic optimization expects a differentiable scalar loss or a dictionary with
`loss`. Returning `None` intentionally skips that training batch; it is not a
substitute for returning the loss when training is intended.

`validation_step` and `test_step` run in evaluation mode with gradients disabled;
`predict_step` also runs through the evaluation machinery. For derivative-based
scientific inference, use `Trainer(inference_mode=False)` and explicitly enable
gradients in the appropriate step. After evaluation, Lightning restores the
previous training mode. Do not keep stochastic training augmentation in an
evaluation DataLoader merely because dropout is disabled.

Use `on_train_epoch_end` / `on_validation_epoch_end` for epoch work. The old
`training_epoch_end(outputs)` / `validation_epoch_end(outputs)` hooks are removed.
If you keep outputs yourself, detach them and clear them after reduction. A
TorchMetrics state usually uses less memory than retaining every prediction.
`setup(stage)` runs for fit/validate/test/predict; `configure_model()` can create
large layers in a strategy-aware context and must be idempotent. The old
`configure_sharded_model()` hook is deprecated.

## Optimizers

Automatic optimization supports one optimizer. For a monitored scheduler:

```python
def configure_optimizers(self):
    optimizer = torch.optim.Adam(self.parameters(), lr=self.hparams.learning_rate)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min")
    return {
        "optimizer": optimizer,
        "lr_scheduler": {
            "scheduler": scheduler,
            "monitor": "val/loss",
            "interval": "epoch",
            "frequency": 1,
            "strict": True,
        },
    }
```

Log that exact key on every scheduled validation pass. Align scheduler frequency
with `check_val_every_n_epoch`; the bundled template assumes validation every
epoch. `ReduceLROnPlateau` no longer accepts `verbose`. For a per-step scheduler,
set `interval="step"`; `trainer.estimated_stepping_batches` includes accumulation
and is useful for `OneCycleLR(total_steps=...)`.

Multiple optimizers require `self.automatic_optimization = False`. An illustrative
manual step for one of them is:

```python
opt_g, opt_d = self.optimizers()
self.toggle_optimizer(opt_g)
opt_g.zero_grad()
g_loss = self.generator_loss(batch)
self.manual_backward(g_loss)
self.clip_gradients(opt_g, gradient_clip_val=1.0, gradient_clip_algorithm="norm")
opt_g.step()
self.untoggle_optimizer(opt_g)
# Compute a fresh discriminator loss and repeat with opt_d.
```

Manual optimization owns zeroing, backward, stepping, accumulation, clipping,
and scheduler steps. Trainer automatic-optimization settings do not implement
those operations for you. Use Lightning's optimizer wrappers and
`manual_backward` to preserve precision/strategy integration.

## Metrics and gradients

For a per-example mean, specify its batch size:

```python
self.log("val/loss", loss, on_step=False, on_epoch=True,
         batch_size=y.size(0), sync_dist=True)
```

Lightning weights batch means by sample count. `sync_dist` defaults to false;
all ranks must call a synchronized log in the same order. A global AUROC/F1 is
not the average of batch or rank AUROC/F1 values: use independent train/val/test
TorchMetrics instances and log the metric object. See [logging](logging.md).

`on_after_backward` sees scaled FP16 gradients before unscaling. Inspect unscaled
gradients in `on_before_optimizer_step(self, optimizer)`, after accumulation.
For logging, compute norms without mutating gradients; use Trainer clipping in
automatic optimization. Calling `clip_grad_norm_` just to inspect norms can
silently change training, especially before unscaling.

## Checkpoint and inference

Call `save_hyperparameters()` in `__init__`; exclude modules, data, credentials,
and other unsuitable constructor arguments with `ignore=[...]`. Supply excluded
arguments explicitly when loading. `current_epoch` is zero based;
`global_step` counts optimizer steps, not batches.

```python
model = TemplateLightningModule.load_from_checkpoint(
    "checkpoints/last.ckpt", map_location="cpu", weights_only=True,
)
model.eval()
with torch.inference_mode():
    predictions = model(data)
```

This restores the module's parameters and constructor hyperparameters. To resume
optimizer/scheduler/loop/callback state, use a new Trainer with
`fit(model, datamodule=dm, ckpt_path=path, weights_only=True)` instead. Do not
confuse `weights_only=True` (restricted deserialization) with
`ModelCheckpoint(save_weights_only=True)` (omits training state).

Lightning 2.6.6 patches checkpoint class/instantiator validation vulnerabilities.
Still load only provenance-checked checkpoints. Never switch to
`weights_only=False` merely to bypass an error from an unknown checkpoint.
Custom checkpoint values should be tensors and simple serializable values when
using restricted loading.

Sources: [2.6.6 module API/source](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/core/module.py),
[optimization guide](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/docs/source-pytorch/common/optimization.rst),
[checkpoint fixes](https://github.com/Lightning-AI/pytorch-lightning/releases/tag/2.6.6).
