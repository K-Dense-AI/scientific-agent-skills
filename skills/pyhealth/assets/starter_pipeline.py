"""
PyHealth starter pipeline. Replace the four marked lines for a different
dataset/task/model/monitor. Everything else stays the same.

Run:
    uv run python starter_pipeline.py
"""

from pyhealth.datasets import MIMIC3Dataset, split_by_patient, get_dataloader
from pyhealth.tasks import MortalityPredictionMIMIC3
from pyhealth.models import Transformer
from pyhealth.trainer import Trainer
from pyhealth.metrics.binary import binary_metrics_fn


# ---- 1. Dataset ----------------------------------------------------------
# Swap MIMIC3Dataset for MIMIC4Dataset / eICUDataset / OMOPDataset / etc.
# For MIMIC-IV use ehr_root= instead of root=.
base = MIMIC3Dataset(
    root="https://storage.googleapis.com/pyhealth/Synthetic_MIMIC-III/",
    tables=["DIAGNOSES_ICD", "PROCEDURES_ICD", "PRESCRIPTIONS"],
    cache_dir="./cache/mimic3",
)

# ---- 2. Task -------------------------------------------------------------
# Match the suffix to the dataset (MIMIC3 / MIMIC4 / EICU / OMOP).
task = MortalityPredictionMIMIC3()
samples = base.set_task(task)

# ---- 3. Split + DataLoaders ---------------------------------------------
# Always split_by_patient for clinical prediction to avoid patient leakage.
train, val, test = split_by_patient(samples, [0.8, 0.1, 0.1])
train_loader = get_dataloader(train, batch_size=32, shuffle=True)
val_loader = get_dataloader(val, batch_size=32, shuffle=False)
test_loader = get_dataloader(test, batch_size=32, shuffle=False)

# ---- 4. Model ------------------------------------------------------------
# Swap for RETAIN / RNN / GAMENet / SafeDrug / StageNet / etc.
# The model MUST receive the SampleDataset (`samples`), not the BaseDataset.
model = Transformer(dataset=samples)

# ---- 5. Trainer ----------------------------------------------------------
# monitor:
#   binary       -> "pr_auc" or "roc_auc"
#   multiclass   -> "accuracy" / "f1_macro" / "cohen_kappa"
#   multilabel   -> "pr_auc_samples" / "jaccard_samples"
trainer = Trainer(model=model)
trainer.train(
    train_dataloader=train_loader,
    val_dataloader=val_loader,
    epochs=50,
    monitor="pr_auc",
    patience=5,
)

# ---- 6. Evaluate ---------------------------------------------------------
y_true, y_prob, _ = trainer.inference(test_loader)
print(binary_metrics_fn(y_true, y_prob, metrics=["pr_auc", "roc_auc", "f1"]))
