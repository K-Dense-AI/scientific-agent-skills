# Callback contracts

Targets Lightning 2.6.6. Examples below with project model/data names are
illustrative; CPU tests exercise checkpoint, early-stopping, learning-rate,
prediction and state-restoration hooks.

## Built-in callbacks

```python
from lightning.pytorch.callbacks import ModelCheckpoint, EarlyStopping, LearningRateMonitor
from lightning.pytorch.loggers import CSVLogger

checkpoint = ModelCheckpoint(
    dirpath="checkpoints",
    filename="epoch-{epoch:02d}-step-{step:06d}",
    auto_insert_metric_name=False,
    monitor="val/loss", mode="min", save_top_k=3, save_last=True,
)
callbacks = [checkpoint, EarlyStopping(monitor="val/loss", patience=10),
             LearningRateMonitor(logging_interval="step")]
trainer = L.Trainer(callbacks=callbacks, logger=CSVLogger("logs"))
```

`save_top_k > 1` requires a monitor. `save_top_k=-1` retains all snapshots.
`save_last=True` updates at the callback's save events; it is not a guarantee
against sudden process termination. Use the returned `best_model_path`,
`last_model_path`, and `best_k_models` instead of guessing a directory. A slash
in a metric name can create nested paths when automatically inserted into a
filename; the example uses epoch/step and disables metric-name insertion.
Align saving with fresh validation metrics. `every_n_train_steps`,
`train_time_interval`, and `every_n_epochs` are mutually exclusive triggers;
step-based monitoring may defer saving until validation makes the metric
available. `save_on_exception=True` is available in 2.6.6, but cannot catch an
uninterruptible host kill.

EarlyStopping `patience` counts **checks with no improvement**, not epochs.
Changing validation frequency changes how long it waits. It defaults to
`strict=True` and checks finite values. Validation losses logged only during
sanity checking cannot drive regular checkpoint/early-stop decisions.

LearningRateMonitor needs an enabled logger. DeviceStatsMonitor reports
backend-dependent metrics; CPU monitoring needs `psutil`. RichProgressBar and
RichModelSummary need `rich`. Do not promise identical GPU/CPU/TPU metric names.
Timer accepts a duration string, `timedelta` or dict and `interval="step"` or
`"epoch"`; `"batch"` is not valid.

For scheduled accumulation:

```python
from lightning.pytorch.callbacks import GradientAccumulationScheduler
trainer = L.Trainer(callbacks=[
    GradientAccumulationScheduler(scheduling={0: 4, 5: 2}),
])
```

This is for automatic optimization and is not supported by every strategy.
BatchSizeFinder or `Tuner.scale_batch_size` probes a batch-size attribute on the
model/DataModule; it does not discover a scientifically optimal batch size. It
needs representative data and spare memory, and tuning support depends on the
strategy. Prefer the built-in `Tuner.lr_find` to a homemade callback that leaves
changed weights/LR behind. StochasticWeightAveraging changes model averaging
and the learning-rate schedule: validate its effect and batch-normalization
statistics for the actual model.

## Custom state and hooks

```python
from lightning.pytorch.callbacks import Callback

class BatchCounter(Callback):
    def __init__(self):
        self.count = 0

    @property
    def state_key(self):
        return "batch-counter"

    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        self.count += 1

    def state_dict(self):
        return {"count": self.count}

    def load_state_dict(self, state_dict):
        self.count = state_dict["count"]
```

Give differently configured instances unique `state_key` values. Pass callbacks
to the resumed Trainer to restore their state. `on_save_checkpoint` and
`on_load_checkpoint` are notification hooks; persistent callback state belongs
in `state_dict`/`load_state_dict`.

- Setup/teardown: `setup(trainer, pl_module, stage)` and `teardown(...)`, including
  standalone validation.
- Train batches: `on_train_batch_end(trainer, pl_module, outputs, batch, batch_idx)`.
- Evaluation/prediction batches additionally accept `dataloader_idx=0`, e.g.
  `on_predict_batch_end(trainer, pl_module, outputs, batch, batch_idx, dataloader_idx=0)`.
- Inspect unscaled accumulated gradients at
  `on_before_optimizer_step(trainer, pl_module, optimizer)`.
- Exceptions: `on_exception(trainer, pl_module, exception)`.

Do not include sanity-validation metrics in an experiment report: check
`trainer.sanity_checking`. Detach/copy values when retaining metric snapshots.
Callbacks generally follow registration order, with documented exceptions such
as ModelCheckpoint running last; design independent callbacks instead of
relying on incidental ordering.

For distributed checkpointing call `trainer.save_checkpoint` on every rank:
strategies may need collectives. For prediction, write bounded CPU batches to
rank-specific files using BasePredictionWriter; concatenate by stable sample ID
and verify duplicates/missing samples. Do not let every rank overwrite the same
file, or assume rank zero's local predictions include all other ranks.

Sources: [callback hook signatures](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/callbacks/callback.py),
[ModelCheckpoint](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/callbacks/model_checkpoint.py),
[EarlyStopping](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/callbacks/early_stopping.py),
[Timer](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/callbacks/timer.py).
