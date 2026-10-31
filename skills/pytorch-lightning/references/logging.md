# Metrics and logger integrations

Reviewed for Lightning 2.6.6. CSV logging is exercised locally; external logger
integrations below are documentation/source-verified illustrations, not tested
hosted-service sessions. No tracking server is required for the bundled scripts.

## Local first

```python
from lightning.pytorch.loggers import CSVLogger
logger = CSVLogger("logs", name="experiment", version="run-001")
trainer = L.Trainer(logger=logger, log_every_n_steps=1)
```

CSVLogger writes `metrics.csv` and, when hyperparameters are logged,
`hparams.yaml`. `logger=True` selects TensorBoard only when `tensorboard` or
`tensorboardX` is installed; otherwise it selects CSV. `logger=False` disables
backend logging, while metrics can still be available for callbacks.

TensorBoard needs the optional `tensorboard` package:

```python
from lightning.pytorch.loggers import TensorBoardLogger
logger = TensorBoardLogger("logs", name="experiment", default_hp_metric=False)
# View with: tensorboard --logdir logs
```

Its `.experiment` is a SummaryWriter with methods such as `add_image`,
`add_histogram`, `add_graph`, `add_figure`, `add_text`, and `add_audio`. These are
TensorBoard-specific, not common methods on every logger. Run direct experiment
calls only on global rank zero, check the logger type, detach tensors and close
figures. Gate expensive media logging and avoid exposing private samples.

## Metric semantics

For a batch mean loss/accuracy, use an explicit sample count:

```python
self.log("val/loss", loss, on_step=False, on_epoch=True,
         batch_size=y.size(0), sync_dist=True, prog_bar=True)
```

Epoch tensor means are weighted by `batch_size`. With masks/tokens, decide
whether the target is a mean per example or per valid token; use its actual
normalizing count rather than blindly taking the tensor's first dimension.
`sync_dist=False` is the default. All ranks must participate in synchronized
calls; rank-dependent conditionals can hang. `rank_zero_only=True` tells
Lightning that the caller logs only on rank zero; it is not a decorator that
prevents other ranks executing code, and such a metric must not drive a
synchronized callback monitor.

`on_step`/`on_epoch` defaults depend on the hook: training_step defaults to
step-only, validation/test steps to epoch-only. Not every hook permits logging.
Set flags explicitly when the reduction matters. Both true creates `_step` and
`_epoch` names; monitor the correct one. `reduce_fx` supports mean/sum/min/max;
it does not make a nonlinear batch metric globally correct.

For AUROC, F1, precision/recall and other nonlinear metrics, maintain a
TorchMetrics instance per stage/loader and log the **object**:

```python
# in __init__
from torchmetrics.classification import MulticlassAccuracy
self.val_accuracy = MulticlassAccuracy(num_classes=10, average="micro")

# in validation_step
self.val_accuracy.update(logits, y)
self.log("val/accuracy", self.val_accuracy, on_step=False, on_epoch=True)
```

TorchMetrics manages distributed state synchronization and Lightning resets
logged metric objects between epochs. Logging a scalar returned from a metric
call instead loses that lifecycle contract. Do not share one instance between
train and validation. For scientific test metrics, DDP sampler padding still
biases sample coverage even if the metric reduction is correct.

## Optional tracking services

Install only the selected backend. Use provider credentials through its existing
configuration/environment, not embedded in code or saved hyperparameters.
SDKs choose network endpoints/authentication and handle their request bodies;
Lightning logger wrappers do not define independent REST endpoints or pagination.
Confirm the actual target account/project/server before enabling online logging.

| Logger | Current contract and data destination |
| --- | --- |
| `WandbLogger` | Requires `wandb`; `offline=False`, `log_model=False` by default. Online runs send metrics/hyperparameters to the configured W&B backend. `log_model=True` logs checkpoints at finalization (and during training when saving all); `"all"` logs each saved checkpoint. |
| `MLFlowLogger` | Requires `mlflow` (the slim client can suffice for remote tracking). Explicit `tracking_uri` overrides `MLFLOW_TRACKING_URI`; without a URI the wrapper falls back to `file:./mlruns`. `log_model=False` is default. The current MLflow SDK's default backend alone does not change that wrapper fallback. |
| `CometLogger` | Requires `comet-ml`; current Lightning arguments are `project`, `online`, and `name` via kwargs. Old `project_name`, `offline`, `experiment_name`, and `save_dir` are deprecated by the wrapper. The constructor can create an experiment immediately. |

Offline W&B illustration (no model artifacts):

```python
from lightning.pytorch.loggers import WandbLogger
logger = WandbLogger(project="my-project", save_dir="logs",
                     offline=True, log_model=False)
```

Do not reuse an already active online W&B run when expecting offline isolation.
Lightning rejects `offline=True` combined with model uploading. Offline files
may later be uploaded only when that is intended. Avoid automatic `.watch` or
media/artifact uploads without a concrete experiment need.

MLflow server illustration (requires a configured server and authorization):

```python
from lightning.pytorch.loggers import MLFlowLogger
logger = MLFlowLogger(experiment_name="my-experiment", run_name="run-001",
                      tracking_uri="http://127.0.0.1:5000", log_model=False)
logger.log_metrics({"val_loss": 0.5}, step=1)
```

The example URI is a local server the user must run, not a public service.
`logger.experiment` is an `MlflowClient`; direct `log_metric` needs
`run_id=logger.run_id, key=..., value=...`. Prefer the wrapper's `log_metrics`
for rank handling and consistent step semantics.

For Comet, verify the installed wrapper/SDK pair before relying on offline
persistence: Lightning 2.6.6 sets `ExperimentConfig(disabled=True)` when
`online=False`, although the Comet SDK's `start(online=False)` normally creates
an offline experiment. The SDK now favors `project_name`, while Lightning's
wrapper still favors `project` and forwards it. Use CSV for a guaranteed local
smoke run; do not treat an untested Comet constructor as a no-side-effect probe.
Online Comet needs configured authentication (e.g. `COMET_API_KEY`) and explicit
user intent to send the logged data.

Neptune's service permanently shut down March 5, 2026, and Lightning removed
NeptuneLogger in 2.6.4. Do not suggest restoring it by pinning an old client.

For multiple backends, pass `logger=[...]`; direct media calls must iterate
`self.loggers` and dispatch by type. A custom Logger must implement `name`,
`version`, `log_metrics`, and `log_hyperparams`; if overriding `save_dir`, use a
property backed by `_save_dir` (the base property has no setter). Decorate backend
writes with `rank_zero_only`. Implement `save`/`finalize` when flushing is needed.

Sources: [tensor aggregation](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/trainer/connectors/logger_connector/result.py),
[W&B wrapper](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/loggers/wandb.py),
[W&B 0.30 initialization](https://github.com/wandb/wandb/blob/v0.30.0/wandb/sdk/wandb_init.py),
[MLflow wrapper](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/loggers/mlflow.py),
[MLflow 3.16.1 client](https://github.com/mlflow/mlflow/blob/v3.16.1/mlflow/tracking/client.py),
[Comet wrapper](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/loggers/comet.py),
[Comet start API](https://www.comet.com/docs/v2/api-and-sdk/python-sdk/reference/start/),
[TorchMetrics integration](https://lightning.ai/docs/torchmetrics/stable/pages/lightning.html),
[Neptune shutdown](https://docs.neptune.ai/).
