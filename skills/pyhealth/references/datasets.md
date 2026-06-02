# Datasets

PyHealth datasets are **queryable patient registries**, not PyTorch `Dataset`s. The PyTorch-compatible object is the `SampleDataset` returned by `base.set_task(task)`. Don't try to index `BaseDataset` like a list — it won't work.

## Two-tier object model

```
BaseDataset                         SampleDataset
├── parses raw CSVs                 ├── one row per supervised sample
├── one row per patient             ├── indexable, length-ed
├── .set_task(task) → SampleDataset ├── feeds into get_dataloader(...)
├── .get_patient(id) → Patient      └── feeds into Model(dataset=...)
└── .iter_patients() → iterator
```

Always go `BaseDataset → set_task → SampleDataset` before doing anything else.

## EHR / clinical datasets

| Class | Import | Constructor signature highlights |
|---|---|---|
| `MIMIC3Dataset` | `from pyhealth.datasets import MIMIC3Dataset` | `root, tables, cache_dir=None, dev=False, num_workers=...` |
| `MIMIC4Dataset` | `from pyhealth.datasets import MIMIC4Dataset` | `ehr_root, tables, ...` *(note: `ehr_root`, not `root`)* |
| `eICUDataset` | `from pyhealth.datasets import eICUDataset` | `root, tables, ...` |
| `OMOPDataset` | `from pyhealth.datasets import OMOPDataset` | `root, tables, ...` |
| `EHRShotDataset` | `from pyhealth.datasets import EHRShotDataset` | few-shot benchmark |
| `Support2Dataset` | `from pyhealth.datasets import Support2Dataset` | palliative care outcomes |
| `MIMICExtractDataset` | `from pyhealth.datasets import MIMICExtractDataset` | pre-processed MIMIC |

### Common MIMIC tables

- **MIMIC-III** (uppercase): `DIAGNOSES_ICD`, `PROCEDURES_ICD`, `PRESCRIPTIONS`, `LABEVENTS`, `NOTEEVENTS`
- **MIMIC-IV** (lowercase): `diagnoses_icd`, `procedures_icd`, `prescriptions`, `labevents`

### MIMIC-III example

```python
from pyhealth.datasets import MIMIC3Dataset

base = MIMIC3Dataset(
    root="https://storage.googleapis.com/pyhealth/Synthetic_MIMIC-III/",
    tables=["DIAGNOSES_ICD", "PROCEDURES_ICD", "PRESCRIPTIONS"],
    cache_dir="./cache/mimic3",
    dev=False,
)
```

### MIMIC-IV example

```python
from pyhealth.datasets import MIMIC4Dataset

base = MIMIC4Dataset(
    ehr_root="/path/to/mimic-iv-2.2/hosp",      # NOT root=
    tables=["diagnoses_icd", "procedures_icd", "prescriptions"],
    cache_dir="./cache/mimic4",
)
```

## Signal / sleep datasets

| Class | Use |
|---|---|
| `SleepEDFDataset` | Sleep-EDF polysomnography → sleep stage classification |
| `SHHSDataset` | Sleep Heart Health Study EEG |
| `ISRUCDataset` | ISRUC sleep dataset |
| `TUABDataset` | Temple University abnormal EEG |
| `TUEVDataset` | Temple University EEG events |
| `CardiologyDataset` | ECG / cardiology recordings |
| `DREAMTDataset`, `BMDHSDataset` | Sleep / respiratory recordings |

## Imaging datasets

| Class | Use |
|---|---|
| `COVID19CXRDataset` | COVID-19 chest X-ray classification |
| `ChestXray14Dataset` | NIH ChestX-ray14, multi-label |
| `PhysioNetDeIDDataset` | De-identified clinical notes |

## Genomics datasets

| Class | Use |
|---|---|
| `ClinVarDataset` | Variant pathogenicity classification |
| `COSMICDataset` | Mutation pathogenicity |
| `TCGAPRADDataset` | Cancer survival, mutation burden |

## Text dataset

| Class | Use |
|---|---|
| `MedicalTranscriptionsDataset` | Clinical transcription category classification |

## Splitting and DataLoaders

After `set_task`, split and wrap in DataLoaders. **Always split by patient** (not by sample) for clinical prediction — random sample splits leak the same patient into train and test.

```python
from pyhealth.datasets import split_by_patient, split_by_visit, get_dataloader

train, val, test = split_by_patient(samples, [0.8, 0.1, 0.1])

train_loader = get_dataloader(train, batch_size=32, shuffle=True)
val_loader   = get_dataloader(val,   batch_size=32, shuffle=False)
test_loader  = get_dataloader(test,  batch_size=32, shuffle=False)
```

Use `split_by_visit` only when visits are independent (rare — most clinical tasks need patient-level splits). For time-aware evaluation, use `split_by_patient` with chronological cutoffs from a custom task.

## Inspecting a dataset

```python
base.stats()                          # summary printout
patient = base.get_patient("p001")    # Patient object
events = patient.get_events()         # all events for that patient

for p in base.iter_patients():        # iterate without loading all into memory
    ...

len(samples)                          # only valid AFTER set_task
samples[0]                            # dict of features + label for one sample
```

## Custom datasets

Subclass `BaseDataset` if the user has a non-standard EHR source. They must implement parsing of patients/events; `set_task` then works as usual. This is more involved than picking a built-in dataset — only suggest it when nothing else fits.
