# Scientific training validation

Applies to the Lightning 2.6.6 templates. These checks complement the exact
contracts in [LightningModule](lightning_module.md), [DataModule](data_module.md),
[Trainer](trainer.md), [callbacks](callbacks.md), [logging](logging.md), and
[distributed training](distributed_training.md).

## Before a real fit

1. Identify the unit of independence (patient, animal, experimental batch, time,
   site). Split those units before preprocessing or augmentation; record sample
   IDs and data versions. Use the validation set for model selection and preserve
   the test set for the prespecified final comparison.
2. Assert shape, dtype, label range, class support, finite values and sample
   counts. Check that the module and DataModule agree: the bundled pair uses
   784-feature vectors, ten classes, and random synthetic labels.
3. Call `L.seed_everything(seed, workers=True)` before constructing the model and
   data. Seed separate NumPy Generator instances explicitly if used; the global
   seed does not retroactively seed existing generators. Save the software and
   hardware configuration, split provenance and all model-selection decisions.
4. Run a CPU `fast_dev_run` to check basic plumbing, then a short normal fit with
   checkpointing and a local logger. Fast dev runs suppress important callbacks
   and cannot establish recoverability.
5. Check that loss is finite and parameters change. Overfit a small subset to
   test capacity, but do not use its validation metrics to claim generalization.
   Test an uneven final batch so reductions cannot hide a mean-of-means bug.

## Reproducibility and resume

Use deterministic algorithms where feasible, with `benchmark=False`, while
recording unsupported operations. PyTorch does not guarantee identical results
across versions/platforms or CPU/GPU even with the same seed. Full precision
alone does not establish determinism. Test repeatability with the same stack
and quantify variability across seeds for scientific comparisons.

A full Lightning checkpoint restores weights, optimizer/scheduler, loop,
callback and DataModule state. It does not by itself establish bitwise resume
for stochastic workers, arbitrary iterable streams, changed datasets or device
counts. An RNG snapshot needs all relevant generators/devices and must be
restored at the right lifecycle point; a naive NumPy tuple added to a checkpoint
may also be incompatible with restricted deserialization. Prefer simple tensor
and primitive checkpoint state and explicit data/split provenance.

The bundled DataModule deliberately rebuilds existing splits after state
restoration because Lightning calls `setup` before `load_state_dict`. For real
streaming data, implement and validate cursor/sampler state separately. Compare
an interrupted run with an uninterrupted control if exact continuation matters.
A resume smoke that increments global_step is narrower evidence.

Use the best **validation-selected** checkpoint explicitly for final testing.
Passing the final in-memory model to `test(model)` evaluates those final weights,
not necessarily the best checkpoint. Inspect early-stopping check counts, final
sample count and the actual checkpoint path in the output record.

## Numeric and performance checks

- Let Lightning move the model and ordinary batches to the selected device.
  Create new tensors on `self.device` or with `x.new_*`; register persistent
  non-parameter tensors as buffers. Explicit `.cpu()` is appropriate when
  exporting detached results, not as a blanket forbidden operation.
- Let Trainer precision manage mixed precision; do not manually cast the entire
  model to BF16 while claiming FP32 master-weight mixed precision. Compare loss,
  gradients and final scientific metrics to a full-precision baseline.
- Inspect unscaled gradients in `on_before_optimizer_step`. Configure clipping
  through Trainer in automatic optimization; manually clip only when managing
  manual optimization. `clip_grad_norm_` mutates gradients.
- Detach retained outputs and clear them at epoch end. `torch.cuda.empty_cache()`
  releases unused cached blocks, not live tensors, and is not a routine cure for
  retained computation graphs. Profile before adding cache clearing or workers.
- Gradient accumulation changes optimizer-step counts; use
  `trainer.estimated_stepping_batches` for step schedules, and account for partial
  windows. BatchSizeFinder tests memory capacity, not convergence or a suitable
  statistical batch size.
- Disable augmentation for evaluation, keep dropout/batch normalization in eval
  mode, and use inference/no-grad contexts. For derivatives in evaluation, use
  `inference_mode=False` and explicitly enable gradients.

## Report the evidence

Record split IDs, preprocessing fit scope, seed(s), package/hardware versions,
checkpoint path, monitor, stopping rule, effective batch, metric definition,
sample count and uncertainty. Separate CPU hook/checkpoint tests from actual
GPU or distributed execution. A successful fit on random labels only establishes
that the templates compose; it is not a performance benchmark.

Source: [PyTorch reproducibility](https://docs.pytorch.org/docs/2.14/notes/randomness.html)
and the release-specific Lightning sources linked in the component references.
