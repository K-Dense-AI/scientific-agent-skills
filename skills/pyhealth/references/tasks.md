# Tasks, schemas and label semantics

The following exports were checked in PyHealth 2.0.2. A name identifies a task
implementation, not proof that its cohort/outcome matches a proposed study. Inspect
`task.input_schema`, `task.output_schema` and raw `task(patient)` output before running
`base.set_task(task)`.

## Common clinical tasks

| Task | Data | Key implementation details |
|---|---|---|
| `MortalityPredictionMIMIC3`, `MortalityPredictionMIMIC4` | MIMIC-III/IV | Current-visit conditions/procedures/drugs -> `mortality: binary` in next visit; requires a future admission |
| `InHospitalMortalityMIMIC4` | MIMIC-IV labs | First 48 hours' selected labs; adults and stays longer than 48 hours; `labs: timeseries` -> `mortality: binary` |
| `MortalityPredictionEICU`, `MortalityPredictionEICU2`, `MortalityPredictionOMOP` | Matching source | Inspect source-specific mortality semantics and missing labels; they are not interchangeable with MIMIC |
| `ReadmissionPredictionMIMIC3`, `ReadmissionPredictionMIMIC4`, `ReadmissionPredictionOMOP` | Matching source | `readmission: binary`; default `window=timedelta(days=15)`, not a universal 30-day outcome |
| `ReadmissionPredictionEICU` | eICU | Different constructor/ICU-stay logic; no MIMIC-style `window` argument |
| `LengthOfStayPredictionMIMIC3`, `LengthOfStayPredictionMIMIC4`, `LengthOfStayPredictioneICU`, `LengthOfStayPredictionOMOP` | Matching source | `los: multiclass`; spelling of `eICU` differs from other class names |
| `DrugRecommendationMIMIC3`, `DrugRecommendationMIMIC4`, `DrugRecommendationEICU`, `DrugRecommendationOMOP` | Matching source | Historical inputs -> current medication set; inspect source-specific drug vocabularies |
| `MortalityPredictionStageNetMIMIC4` | MIMIC-IV | StageNet-oriented feature preparation |
| `DKAPredictionMIMIC4` | MIMIC-IV | DKA-specific cohort and label construction |
| `MIMIC3ICD9Coding` | MIMIC-III notes | Discharge-note ICD-9 coding, not early risk prediction |

For MIMIC mortality/readmission/LOS, load all three selectors:
`diagnoses_icd`, `procedures_icd`, `prescriptions`. Missing one may cause all visits
to be excluded. The LOS implementation uses whole-visit codes and prescriptions:
using it unchanged to claim admission-time prediction would leak future information.
Its ten categories are `<1` day, integer days `1` through `7`, days `8` through `14`,
and `>14`; MIMIC uses whole elapsed days.

MIMIC readmission excludes the last observed admission and normally minors. The
label compares next admission with current discharge using a strict `< window`.
This selected cohort is not all discharges with complete follow-up; address censoring,
transfers/overlaps, and patients without another recorded admission explicitly.
The next-visit MIMIC-III mortality task maps an invalid/missing future mortality flag
to zero: unknown status is not necessarily survival. Audit or override that behavior.

The MIMIC-IV in-hospital task also checks lab `storetime <= prediction_time`, beyond
measurement time. Keep that availability filter. The
[MEDS mortality task](https://pyhealth.readthedocs.io/en/latest/api/tasks/pyhealth.tasks.InHospitalMortalityMEDS.html)
has a separate contract; do not transfer its exact parameters to the MIMIC-IV task.

## Signals, images, text and other tasks

| Export | Dataset/task |
|---|---|
| `SleepStagingSleepEDF` | SleepEDF: `signal: tensor` -> `label: multiclass`; 30-second chunks by default |
| `EEGEventsTUEV`, `EEGAbnormalTUAB` | TUEV event / TUAB abnormality classification |
| `COVID19CXRClassification` | COVID19CXR multiclass |
| `ChestXray14BinaryClassification`, `ChestXray14MultilabelClassification` | One disease versus multi-disease ChestXray14 targets |
| `cardiology_isAR_fn`, `cardiology_isBBBFB_fn`, `cardiology_isAD_fn`, `cardiology_isCD_fn`, `cardiology_isWA_fn` | Legacy callable cardiology tasks; do not assume a BaseTask schema |
| `MedicalTranscriptionsClassification`, `DeIDNERTask` | Specialty classification / clinical de-identification |
| `VariantClassificationClinVar`, `MutationPathogenicityPrediction` | ClinVar/COSMIC labels |
| `CancerSurvivalPrediction`, `CancerMutationBurden` | TCGA-PRAD outcomes |
| `BenchmarkEHRShot` | EHRShot benchmark labels |

SleepStagingSleepEDF 2.0.2 retains six labels W/N1/N2/N3/N4/REM. It does not silently
merge N3 and N4 into the common five-class convention. Declare any remapping and
validate EDF channels, sample rate, annotation boundaries and patient/night grouping.
Other dataset recipes in this table are source-verified inventories, not executed
clinical or signal experiments.

## Metrics

| Output mode | Example `metrics` / `monitor` names |
|---|---|
| Binary | `pr_auc`, `roc_auc`, `f1` |
| Multiclass | `accuracy`, `f1_macro`, `cohen_kappa` |
| Multilabel | `pr_auc_samples`, `jaccard_samples`, `f1_samples` |

A metric's averaging policy matters; sample-wise multilabel metrics are not the only
valid choice. Inspect rare/absent classes, label coverage and decision thresholds.
PR-AUC of 0.5 has different meaning at 1% and 50% prevalence. Set the monitor to an
actual validation score key and specify `monitor_criterion`.

## Custom tasks use events in 2.x

Illustrative MIMIC-III adapter below keeps the built-in feature extraction but
excludes samples whose future mortality flag is unknown. This solves only that
missing-label issue; it retains the built-in next-admission cohort and feature timing.

```python
from pyhealth.tasks import MortalityPredictionMIMIC3

class KnownNextVisitMortality(MortalityPredictionMIMIC3):
    task_name = "KnownNextVisitMortality"

    def __call__(self, patient):
        admissions = patient.get_events(event_type="admissions")
        known = {
            current.hadm_id
            for current, future in zip(admissions, admissions[1:])
            if future.hospital_expire_flag in (0, 1, "0", "1")
        }
        return [s for s in super().__call__(patient) if s["hadm_id"] in known]
```

For a new outcome, subclass `BaseTask`, declare input/output schemas, and implement
`__call__(patient)` returning dictionaries with patient/record IDs plus all schema
fields. `[]` excludes a patient. Use `get_events(event_type=..., start=..., end=...,
filters=[(...)])`; the 2.x `Patient` has no `visits` or `next_visit` API. Define lab
thresholds, units, missingness, observation time and censoring in the task itself.
Give changed task implementations new cache identities or fresh cache roots.

Sources: [tasks](https://pyhealth.readthedocs.io/en/latest/api/tasks.html),
[released package](https://pypi.org/project/pyhealth/2.0.2/).
