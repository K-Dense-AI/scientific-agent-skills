# Datasets and event access

Contracts below were checked in the released PyHealth 2.0.2 wheel and
[dataset documentation](https://pyhealth.readthedocs.io/en/latest/api/datasets.html).
Constructors are not interchangeable across modalities.

## Two dataset layers

`BaseDataset` exposes a lazy, table-backed event registry. `get_patient(id)` and
`iter_patients()` return `Patient` objects; `set_task(task)` builds a processed,
indexable sample dataset. Use those samples with models, splitters and data loaders.
`create_sample_dataset(records, input_schema=..., output_schema=...)` is the public
helper for in-memory dictionaries; `SampleDataset(...)` itself takes a cache path,
not `samples=`.

```python
from pyhealth.datasets import MIMIC3Dataset
base = MIMIC3Dataset(
    root="https://storage.googleapis.com/pyhealth/Synthetic_MIMIC-III/",
    tables=["diagnoses_icd", "procedures_icd", "prescriptions"],
    cache_dir="./cache/mimic3", num_workers=1, dev=True,
)
```

The MIMIC-III constructor automatically adds `patients`, `admissions`, `icustays`.
All selectors above are lowercase; the bundled config translates them to uppercase
CSV filenames. `labevents` additionally needs `D_LABITEMS`; note events have their own
recording-time and availability caveats.

## MIMIC-IV: two supported constructors

```python
from pyhealth.datasets import MIMIC4Dataset, MIMIC4EHRDataset

# Combined EHR/note/CXR wrapper: modality-specific argument names
combined = MIMIC4Dataset(
    ehr_root="./data/mimic-iv",
    ehr_tables=["diagnoses_icd", "procedures_icd", "prescriptions"],
    cache_dir="./cache/mimic4",
)
# EHR-only reader: ordinary root/tables arguments
base = MIMIC4EHRDataset(
    root="./data/mimic-iv",
    tables=["diagnoses_icd", "procedures_icd", "prescriptions"],
    cache_dir="./cache/mimic4-ehr",
)
```

Both roots contain `hosp/` and `icu/`. `tables=` is not an argument to the combined
wrapper. Its other modalities use `note_root`/`note_tables`, `cxr_root`/`cxr_tables`.
These restricted-data examples are illustrative; constructor/config contracts were
verified, but no private MIMIC-IV records were loaded.

## Available dataset families

These names are exported by 2.0.2; this inventory does not certify every task/model
combination or dataset release. Read the selected class and bundled config first.

| Family | Classes |
|---|---|
| EHR | `MIMIC3Dataset`, `MIMIC4Dataset`, `MIMIC4EHRDataset`, `eICUDataset`, `OMOPDataset`, `MIMICExtractDataset`, `EHRShotDataset`, `Support2Dataset` |
| Sleep/signals | `SleepEDFDataset`, `SHHSDataset`, `ISRUCDataset`, `TUABDataset`, `TUEVDataset`, `CardiologyDataset`, `DREAMTDataset`, `BMDHSDataset` |
| Imaging | `COVID19CXRDataset`, `ChestXray14Dataset` |
| Text | `PhysioNetDeIDDataset`, `MedicalTranscriptionsDataset` |
| Genomics | `ClinVarDataset`, `COSMICDataset`, `TCGAPRADDataset` |

In 2.0.2, `SleepEDFDataset(root=..., subset="cassette")` accepts `root`,
`dataset_name`, `config_path`, `subset`; it does **not** accept `cache_dir` or `dev`.
The root contains `SC-subjects.xls` and the `sleep-cassette/` subdirectory
(or the corresponding telemetry files), unless metadata is already prepared.
Reading raw `.xls` metadata can require the optional pandas engine `xlrd`. Genomics and clinical text
are not imaging datasets even when they share the pipeline abstraction.

## Inspect actual events and samples

```python
patient = next(base.iter_patients())
admissions = patient.get_events(event_type="admissions")
if admissions:
    diagnoses = patient.get_events(
        event_type="diagnoses_icd",
        filters=[("hadm_id", "==", admissions[0].hadm_id)],
    )
    print([event.icd9_code for event in diagnoses])  # MIMIC-III only
```

MIMIC-IV diagnosis events use `icd_code` and `icd_version`. Keep the version when
harmonizing vocabularies; identically shaped code strings need not mean the same
thing. `get_events(start=..., end=...)` includes both time boundaries; `return_df=True`
returns prefixed Polars columns such as `diagnoses_icd/icd9_code`. Missing event
types can yield an empty frame without the expected columns: check before selecting.
Do not use the legacy `patient.visits`, `next_visit`, or `visit.get_code_list` APIs.

## Splitting and preprocessing

```python
from pyhealth.datasets import split_by_patient, get_dataloader
train, val, test = split_by_patient(samples, [0.6, 0.2, 0.2], seed=42)
train_loader = get_dataloader(train, batch_size=32, shuffle=True)
val_loader = get_dataloader(val, batch_size=32, shuffle=False)
test_loader = get_dataloader(test, batch_size=32, shuffle=False)
```

Check nonempty partitions and pairwise-disjoint patient IDs. Group all recordings
from the same person together for sleep/EEG as well. `split_by_visit` relies on record
identifiers and permits patient overlap; it is unsuitable for a new-patient claim.
`split_by_patient` does not implement time cutoffs or stratification. For a temporal
study build the date-based partition explicitly and state whether returning patients
are allowed. Fit feature transforms on training data only; the convenience
`set_task -> split` route fits processors before splitting. See
[train-only processing](examples.md).

For custom datasets, inspect `BaseDataset` and its config-driven `load_data`/
`load_table` interfaces. Do not start from obsolete patient/visit parsers.
