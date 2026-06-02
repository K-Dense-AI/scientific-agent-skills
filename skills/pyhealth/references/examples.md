# End-to-end recipes

These are complete pipelines for the most common scenarios. Copy, then modify the dataset/task/model/monitor lines for the user's situation. All examples assume `uv add pyhealth` has been run.

## 1. Mortality prediction on MIMIC-III (binary)

```python
from pyhealth.datasets import MIMIC3Dataset, split_by_patient, get_dataloader
from pyhealth.tasks import MortalityPredictionMIMIC3
from pyhealth.models import Transformer
from pyhealth.trainer import Trainer
from pyhealth.metrics.binary import binary_metrics_fn

base = MIMIC3Dataset(
    root="https://storage.googleapis.com/pyhealth/Synthetic_MIMIC-III/",
    tables=["DIAGNOSES_ICD", "PROCEDURES_ICD", "PRESCRIPTIONS"],
    cache_dir="./cache/mimic3",
)
samples = base.set_task(MortalityPredictionMIMIC3())

train, val, test = split_by_patient(samples, [0.8, 0.1, 0.1])
train_loader = get_dataloader(train, batch_size=32, shuffle=True)
val_loader   = get_dataloader(val,   batch_size=32, shuffle=False)
test_loader  = get_dataloader(test,  batch_size=32, shuffle=False)

model = Transformer(dataset=samples)
trainer = Trainer(model=model)
trainer.train(
    train_dataloader=train_loader,
    val_dataloader=val_loader,
    epochs=50,
    monitor="pr_auc",
    patience=5,
)

y_true, y_prob, _ = trainer.inference(test_loader)
print(binary_metrics_fn(y_true, y_prob, metrics=["pr_auc", "roc_auc", "f1"]))
```

## 2. Readmission prediction on MIMIC-IV with RETAIN (interpretable)

Use RETAIN when the user wants to *explain* predictions, not just make them.

```python
from pyhealth.datasets import MIMIC4Dataset, split_by_patient, get_dataloader
from pyhealth.tasks import ReadmissionPredictionMIMIC4
from pyhealth.models import RETAIN
from pyhealth.trainer import Trainer

base = MIMIC4Dataset(
    ehr_root="/path/to/mimic-iv/hosp",   # ehr_root, not root
    tables=["diagnoses_icd", "procedures_icd", "prescriptions"],
    cache_dir="./cache/mimic4",
)
samples = base.set_task(ReadmissionPredictionMIMIC4())

train, val, test = split_by_patient(samples, [0.8, 0.1, 0.1])
train_loader = get_dataloader(train, batch_size=32, shuffle=True)
val_loader   = get_dataloader(val,   batch_size=32, shuffle=False)
test_loader  = get_dataloader(test,  batch_size=32, shuffle=False)

model = RETAIN(dataset=samples)
trainer = Trainer(model=model, metrics=["roc_auc", "pr_auc", "f1"])
trainer.train(
    train_dataloader=train_loader,
    val_dataloader=val_loader,
    epochs=30,
    monitor="roc_auc",
)
print(trainer.evaluate(test_loader))
```

## 3. Drug recommendation on MIMIC-III with SafeDrug (multilabel)

Drug rec is **multilabel** — every visit has a *set* of drugs. Use a `_samples` monitor.

```python
from pyhealth.datasets import MIMIC3Dataset, split_by_patient, get_dataloader
from pyhealth.tasks import DrugRecommendationMIMIC3
from pyhealth.models import SafeDrug
from pyhealth.trainer import Trainer

base = MIMIC3Dataset(
    root="https://storage.googleapis.com/pyhealth/Synthetic_MIMIC-III/",
    tables=["DIAGNOSES_ICD", "PROCEDURES_ICD", "PRESCRIPTIONS"],
)
samples = base.set_task(DrugRecommendationMIMIC3())

train, val, test = split_by_patient(samples, [0.8, 0.1, 0.1])
train_loader = get_dataloader(train, batch_size=64, shuffle=True)
val_loader   = get_dataloader(val,   batch_size=64, shuffle=False)
test_loader  = get_dataloader(test,  batch_size=64, shuffle=False)

model = SafeDrug(dataset=samples)
trainer = Trainer(model=model)
trainer.train(
    train_dataloader=train_loader,
    val_dataloader=val_loader,
    epochs=30,
    monitor="pr_auc_samples",     # multilabel — note _samples suffix
)
print(trainer.evaluate(test_loader))
```

## 4. Length-of-stay (multiclass) baseline

```python
from pyhealth.datasets import MIMIC3Dataset, split_by_patient, get_dataloader
from pyhealth.tasks import LengthOfStayPredictionMIMIC3
from pyhealth.models import RNN
from pyhealth.trainer import Trainer

base = MIMIC3Dataset(
    root="https://storage.googleapis.com/pyhealth/Synthetic_MIMIC-III/",
    tables=["DIAGNOSES_ICD", "PROCEDURES_ICD"],
)
samples = base.set_task(LengthOfStayPredictionMIMIC3())

train, val, test = split_by_patient(samples, [0.8, 0.1, 0.1])
loaders = [get_dataloader(d, batch_size=32, shuffle=s)
           for d, s in [(train, True), (val, False), (test, False)]]

model = RNN(dataset=samples, rnn_type="GRU", hidden_dim=128)
trainer = Trainer(model=model)
trainer.train(
    train_dataloader=loaders[0],
    val_dataloader=loaders[1],
    epochs=30,
    monitor="cohen_kappa",
)
print(trainer.evaluate(loaders[2]))
```

## 5. Sleep staging on Sleep-EDF (multiclass on signals)

```python
from pyhealth.datasets import SleepEDFDataset, split_by_patient, get_dataloader
from pyhealth.tasks import SleepStagingSleepEDF
from pyhealth.models import SparcNet
from pyhealth.trainer import Trainer

base = SleepEDFDataset(root="/path/to/sleepedf", cache_dir="./cache/sleepedf")
samples = base.set_task(SleepStagingSleepEDF())

train, val, test = split_by_patient(samples, [0.8, 0.1, 0.1])
train_loader = get_dataloader(train, batch_size=128, shuffle=True)
val_loader   = get_dataloader(val,   batch_size=128, shuffle=False)
test_loader  = get_dataloader(test,  batch_size=128, shuffle=False)

model = SparcNet(dataset=samples)
trainer = Trainer(model=model)
trainer.train(
    train_dataloader=train_loader,
    val_dataloader=val_loader,
    epochs=20,
    monitor="cohen_kappa",
)
print(trainer.evaluate(test_loader))
```

## 6. Code lookup + cross-mapping (no model)

When the user wants help interpreting codes or reducing label cardinality, no training is needed:

```python
from pyhealth.medcode import InnerMap, CrossMap

icd9 = InnerMap.load("ICD9CM")
print(icd9.lookup("428.0"))   # 'Congestive heart failure, unspecified'

# Roll up MIMIC-III ICD-9 diagnoses to CCS for a smaller label space
icd9_to_ccs = CrossMap.load("ICD9CM", "CCSCM")
ccs_codes = icd9_to_ccs.map("428.0")   # ['108']
```

## 7. Logistic regression baseline (always run this first)

Before reaching for a Transformer, run a logistic-regression baseline. It's fast, hard to misuse, and tells you whether the task signal exists at all.

```python
from pyhealth.models import LogisticRegression
from pyhealth.trainer import Trainer

model = LogisticRegression(dataset=samples)
trainer = Trainer(model=model)
trainer.train(train_dataloader=train_loader, val_dataloader=val_loader, epochs=10, monitor="pr_auc")
```

If LR gets PR-AUC of 0.5, deeper models likely won't help — investigate the task or features. If LR is already strong, the headroom for fancy models is small.

## 8. Loading a checkpoint and predicting

```python
from pyhealth.trainer import Trainer
from pyhealth.models import Transformer

model = Transformer(dataset=samples)
trainer = Trainer(model=model)
trainer.load_ckpt("./output/best.ckpt")

y_true, y_prob, loss = trainer.inference(test_loader)
```

## 9. Custom task on MIMIC-III

When no built-in task fits — e.g., the user wants to predict a specific lab value 24h ahead:

```python
from pyhealth.tasks import BaseTask
from pyhealth.datasets import MIMIC3Dataset

class HighCreatininePrediction(BaseTask):
    task_name = "HighCreatininePrediction"
    input_schema = {"diagnoses": "sequence", "procedures": "sequence"}
    output_schema = {"label": "binary"}

    def __call__(self, patient):
        samples = []
        for visit in patient.visits[:-1]:
            next_visit = patient.next_visit(visit)
            label = self._has_high_creatinine(next_visit)
            samples.append({
                "patient_id": patient.patient_id,
                "visit_id": visit.visit_id,
                "diagnoses": visit.get_code_list("DIAGNOSES_ICD"),
                "procedures": visit.get_code_list("PROCEDURES_ICD"),
                "label": int(label),
            })
        return samples

    def _has_high_creatinine(self, visit): ...

base = MIMIC3Dataset(root=..., tables=["DIAGNOSES_ICD", "PROCEDURES_ICD", "LABEVENTS"])
samples = base.set_task(HighCreatininePrediction())
```

The exact `Patient`/`Visit` API varies — read `help(patient)` interactively if the user is on a custom dataset.
