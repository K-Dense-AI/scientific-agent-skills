# LightningDataModule and evaluation data

Reviewed against Lightning 2.6.6. Use the executable
[`template_datamodule.py`](../scripts/template_datamodule.py) as the complete
example; project-specific fragments below are illustrative.

## Lifecycle

- `prepare_data()` downloads/processes durable data without assigning state that
  other processes need. By default `prepare_data_per_node=True` calls it on local
  rank zero **on each node**, not once globally. With shared storage and
  `prepare_data_per_node=False`, only global rank zero prepares it. Make it
  idempotent: different Trainer calls/jobs may prepare again.
- Lightning places a barrier before `setup(stage)`. `setup` runs in every
  process; assign datasets, splits and transforms here.
- Handle `"fit"`, `"validate"`, `"test"`, and `"predict"` explicitly. A
  DataModule that creates validation only for `"fit"` breaks standalone
  `trainer.validate(model, datamodule=dm)`.
- `train_dataloader`, `val_dataloader`, `test_dataloader`, and
  `predict_dataloader` return loaders for the corresponding initialized dataset.
  `teardown(stage)` releases resources when that stage ends.

The bundled example generates small deterministic `(784,)` float32 vectors and
int64 labels in `[0, 10)`, matching the model template. Its train/validation
indices are disjoint, and its synthetic test/predict data use separate seeds.
It is a mechanics test with random labels, not a scientifically meaningful
benchmark or a replacement for real held-out subject IDs.

## Prevent leakage

A `random_split` returns Subsets sharing one underlying dataset. Assigning
`val_subset.dataset.transform = evaluation_transform` also changes training;
leaving it unchanged applies training augmentation to validation. Use independent
dataset views over identical sample IDs with separate transforms, as in the
bundled example. Seed the split explicitly so all ranks use the same indices.
Fit normalization, feature selection, token vocabularies, and imputation on the
training partition only. Split patients/subjects/sites/time periods before
windowing or augmentation when observations are correlated.

For cross-validation, create a **fresh model, optimizer, callbacks, and Trainer
for every fold**. Never reuse the fitted model across folds. Preserve every
sample in exactly one validation fold, including the remainder when the count is
not divisible by the fold count. Record indices and seed; use grouped,
stratified, or temporal folds appropriate to the scientific question.

## Loaders and distributed sampling

```python
return DataLoader(
    self.train_dataset,
    batch_size=self.hparams.batch_size,
    shuffle=True,
    num_workers=self.hparams.num_workers,
    persistent_workers=self.hparams.num_workers > 0,
    pin_memory=self.hparams.pin_memory,
    drop_last=False,
)
```

Start with zero workers for a portable smoke test. Tune workers on the actual
host. `persistent_workers=True` requires positive `num_workers`; CUDA pinned
memory is an optimization to measure, not a requirement on CPU/MPS. Evaluation
loaders normally use `shuffle=False, drop_last=False`. Dropping a training tail
is a deliberate tradeoff (e.g. batch normalization), not a universal default.

Lightning injects `DistributedSampler` for map-style datasets when the strategy
needs it and `use_distributed_sampler=True` (default). It preserves an existing
distributed sampler. If using a custom sharder, set that flag false and handle
rank/worker partitioning and epoch reseeding yourself. Iterable datasets are not
automatically sharded. DDP evaluation samplers can pad with duplicate samples;
final exact evaluation should use a separate one-device Trainer or a verified
nonduplicating distributed evaluation design.

For multiple validation loaders, return a list, implement
`validation_step(self, batch, batch_idx, dataloader_idx=0)`, and keep metric states
separate. Lightning normally appends `/dataloader_idx_0`, etc.; callback monitor
keys must match the resulting names. A dict does not create custom metric names.

## Transfer and checkpoint state

`transfer_batch_to_device(batch, device, dataloader_idx)` supports custom batch
objects; delegate to `super()` for standard structures. Use
`on_before_batch_transfer` for processing before the device move and
`on_after_batch_transfer` afterward (the selected device can be CPU). Guard
training-only augmentation with `self.trainer.training` so it cannot alter
validation/test/prediction.

Lightning restores `DataModule.load_state_dict` **after** `setup` during a normal
fit resume. Changing a saved fold/seed/ratio in `load_state_dict` must rebuild any
already-created datasets; simply updating an attribute leaves stale splits.
The template restores seed, count and ratio and rebuilds active views. With real
data, persist stable split IDs plus dataset/preprocessing version and reject
incompatible input data. DataModule state does not automatically recover a
stream's cursor or arbitrary worker RNG state.

Sources: [DataModule lifecycle guide](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/docs/source-pytorch/data/datamodule.rst),
[Trainer setup and restoration order](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/trainer/trainer.py),
[checkpoint connector](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.6/src/lightning/pytorch/trainer/connectors/checkpoint_connector.py).
