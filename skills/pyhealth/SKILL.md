---
name: pyhealth
description: Build clinical/healthcare deep-learning pipelines with PyHealth — loading EHR/signal/imaging datasets (MIMIC-III/IV, eICU, OMOP, SleepEDF, ChestXray14, EHRShot), defining tasks (mortality, readmission, length-of-stay, drug recommendation, sleep staging, ICD coding, EEG events), instantiating models (Transformer, RETAIN, GAMENet, SafeDrug, MICRON, StageNet, AdaCare, CNN/RNN/MLP), training with the PyHealth Trainer, computing clinical metrics, and using medical code utilities (ICD/ATC/NDC/RxNorm lookup and cross-mapping). Use this skill whenever the user mentions PyHealth, MIMIC, eICU, OMOP, EHR modeling, clinical prediction, drug recommendation, sleep staging, medical code mapping, ICD/ATC codes, or any healthcare ML pipeline that fits the dataset → task → model → trainer → metrics pattern, even if "PyHealth" isn't named explicitly.
metadata: {"version": "1.0", "skill-author": "K-Dense Inc."}
---

# PyHealth

PyHealth (https://pyhealth.dev/) is a Python toolkit for clinical deep learning. It provides a unified, modular pipeline across electronic health records (EHR), physiological signals, and medical imaging.

The library is built around a **5-stage pipeline** — `Dataset → Task → Model → Trainer → Metrics` — where each stage is replaceable and the interfaces between stages are stable. Code that follows this pipeline shape composes well; code that bypasses it usually fights the library.

## When to use this skill

Use this skill whenever the user is doing clinical/healthcare ML and any of the following are true:

- They mention PyHealth, MIMIC-III/IV, eICU, OMOP-CDM, EHRShot, SleepEDF, SHHS, ISRUC, COVID19-CXR, ChestX-ray14, TUEV/TUAB.
- They want to predict mortality, readmission, length of stay, drug recommendations, sleep stages, ICD codes, EEG events, or de-identification.
- They need to look up or cross-map medical codes (ICD-9-CM, ICD-10-CM, ATC, NDC, RxNorm, CCS).
- They have EHR-shaped data and want to train a clinical model without writing the plumbing themselves.

PyHealth is the right tool when the workflow fits its 5 stages. If the user just wants generic PyTorch on tabular data, this skill is not necessary.

## Installation (uv)

PyHealth 2.0 requires Python ≥ 3.12, < 3.14. Use `uv` for environment management — it's faster and reproducible.

```bash
# Create a project with the right Python
uv init my-pyhealth-project
cd my-pyhealth-project
uv python pin 3.12

# Add PyHealth (this also pulls in PyTorch and friends)
uv add pyhealth

# Run scripts inside the env
uv run python train.py
```

For a one-off script without a project, use `uv run --with pyhealth python script.py`. For the legacy 1.x line (Python 3.9+), `uv add pyhealth==1.16`. Detailed install notes, MIMIC access, and GPU/CPU device tips are in `references/installation.md`.

## The 5-stage pipeline

A complete pipeline is typically <20 lines. This is the canonical shape — start here and modify pieces:

```python
from pyhealth.datasets import MIMIC3Dataset, split_by_patient, get_dataloader
from pyhealth.tasks import MortalityPredictionMIMIC3
from pyhealth.models import Transformer
from pyhealth.trainer import Trainer
from pyhealth.metrics.binary import binary_metrics_fn

# 1. Dataset — raw patient registry
base = MIMIC3Dataset(
    root="https://storage.googleapis.com/pyhealth/Synthetic_MIMIC-III/",
    tables=["DIAGNOSES_ICD", "PROCEDURES_ICD", "PRESCRIPTIONS"],
)

# 2. Task — converts patients into supervised samples
samples = base.set_task(MortalityPredictionMIMIC3())

# 3. Split + DataLoaders (split by patient to avoid leakage)
train_ds, val_ds, test_ds = split_by_patient(samples, [0.8, 0.1, 0.1])
train_loader = get_dataloader(train_ds, batch_size=32, shuffle=True)
val_loader   = get_dataloader(val_ds,   batch_size=32, shuffle=False)
test_loader  = get_dataloader(test_ds,  batch_size=32, shuffle=False)

# 4. Model — must be passed the SampleDataset, not the BaseDataset
model = Transformer(dataset=samples)

# 5. Train + evaluate
trainer = Trainer(model=model)
trainer.train(
    train_dataloader=train_loader,
    val_dataloader=val_loader,
    epochs=50,
    monitor="pr_auc",
)

y_true, y_prob, _ = trainer.inference(test_loader)
print(binary_metrics_fn(y_true, y_prob, metrics=["pr_auc", "roc_auc"]))
```

A copy-pasteable starter is in `assets/starter_pipeline.py`.

## Critical things to get right

These are the mistakes that PyHealth code most commonly trips on. Internalize them before writing pipelines:

1. **Models take a `SampleDataset`, not a `BaseDataset`.** `MIMIC3Dataset(...)` returns a `BaseDataset` (a queryable patient registry). Only after `.set_task(task)` do you get a `SampleDataset`, which is what models, splitters, and DataLoaders expect. If you pass `base` to a model, it will fail or behave wrong.

2. **Always split by patient (or visit), not by sample.** Random sample-level splits leak information across train/test because the same patient can appear in both. Use `split_by_patient` for patient-level prediction, `split_by_visit` only when visits are independent.

3. **Match the task to the dataset.** Tasks are dataset-specific: `MortalityPredictionMIMIC3` won't work on MIMIC-IV — use `MortalityPredictionMIMIC4` or `InHospitalMortalityMIMIC4`. The full mapping is in `references/tasks.md`.

4. **Pick `monitor` to match the task type.** For binary classification use `"pr_auc"` or `"roc_auc"`. For multilabel (drug rec) use `"pr_auc_samples"` or `"jaccard_samples"`. For multiclass use `"accuracy"` or `"f1_macro"`. Wrong monitor → checkpoint selection saves the wrong epoch.

5. **MIMIC-IV uses `ehr_root=`, not `root=`.** This is the one inconsistency in the dataset constructors.

6. **For reproducible work, point `cache_dir=` somewhere persistent.** PyHealth caches the parsed dataset; without `cache_dir`, you re-parse every run.

## How to use this skill

PyHealth has a large API surface — there's no point loading it all at once. Read the reference file that matches the user's task:

| If the user is asking about… | Read |
|---|---|
| Installing, env setup, MIMIC access, GPU | `references/installation.md` |
| Which dataset class to use, loading patterns, splitting | `references/datasets.md` |
| What prediction task to choose (mortality, readmission, drug rec, sleep…) | `references/tasks.md` |
| Picking a model architecture, model-specific arguments | `references/models.md` |
| Looking up or cross-mapping ICD/ATC/NDC/RxNorm/CCS codes, tokenizers | `references/medcode.md` |
| End-to-end recipes for common scenarios | `references/examples.md` |

For multi-step tasks (e.g., "build a drug recommendation pipeline on MIMIC-IV"), read `tasks.md` + `models.md` + `examples.md` together — they cross-reference each other.

## A note on style

Write minimal, idiomatic PyHealth. The library is opinionated; lean into its abstractions instead of reimplementing them in raw PyTorch. If you find yourself writing a custom training loop, ask whether `Trainer` would do the job — it almost always will, and it handles checkpointing, logging, and best-model selection for free.

When the user has private MIMIC access, point them at the local CSV root; for demos and learning, the synthetic MIMIC-III bucket (`https://storage.googleapis.com/pyhealth/Synthetic_MIMIC-III/`) is fine and works without credentialing.
