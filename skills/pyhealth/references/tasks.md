# Tasks

A **task** turns a `BaseDataset` (raw patients) into a `SampleDataset` (supervised samples). Tasks define `input_schema` (which fields go to the model) and `output_schema` (the label).

```python
samples = base.set_task(MortalityPredictionMIMIC3())
```

Tasks are **dataset-specific**. Picking the wrong combo (e.g., `MortalityPredictionMIMIC3` on a MIMIC-IV dataset) will fail. Match the suffix.

## Task → Dataset compatibility matrix

### Mortality prediction (binary)

| Task class | Dataset |
|---|---|
| `MortalityPredictionMIMIC3` | MIMIC-III |
| `MortalityPredictionMIMIC4` | MIMIC-IV |
| `InHospitalMortalityMIMIC4` | MIMIC-IV (in-hospital, narrower than next-visit) |
| `MortalityPredictionEICU`, `MortalityPredictionEICU2` | eICU |
| `MortalityPredictionOMOP` | OMOP |
| `MortalityPredictionStageNetMIMIC4` | MIMIC-IV (paired with StageNet model) |

### Readmission prediction (binary)

| Task class | Dataset |
|---|---|
| `ReadmissionPredictionMIMIC3` | MIMIC-III |
| `ReadmissionPredictionMIMIC4` | MIMIC-IV |
| `ReadmissionPredictionEICU` | eICU |
| `ReadmissionPredictionOMOP` | OMOP |

### Length-of-stay prediction (multiclass)

| Task class | Dataset |
|---|---|
| `LengthOfStayPredictionMIMIC3` | MIMIC-III |
| `LengthOfStayPredictionMIMIC4` | MIMIC-IV |
| `LengthOfStayPredictioneICU` | eICU |
| `LengthOfStayPredictionOMOP` | OMOP |

LOS is bucketed into discrete classes (e.g., <1 day, 1-2 days, …, >14 days). Treat as multiclass classification.

### Drug recommendation (multilabel)

| Task class | Dataset |
|---|---|
| `DrugRecommendationMIMIC3` | MIMIC-III |
| `DrugRecommendationMIMIC4` | MIMIC-IV |
| `DrugRecommendationEICU` | eICU |

Multilabel = each visit has a set of drugs prescribed; predict the set. Use models with drug-aware structure (`GAMENet`, `SafeDrug`, `MICRON`, `MoleRec`) or fall back to `Transformer` / `RNN`.

### Specialized clinical

| Task class | What it predicts |
|---|---|
| `DKAPredictionMIMIC4` | Diabetic ketoacidosis risk |
| `MIMIC3ICD9Coding` | ICD-9 codes for a discharge note (multilabel) |

### Sleep & EEG

| Task class | Dataset | Predicts |
|---|---|---|
| `SleepStagingSleepEDF` | SleepEDF | Sleep stage (multiclass) |
| `EEGEventsTUEV` | TUEV | EEG events |
| `EEGAbnormalTUAB` | TUAB | EEG abnormality (binary) |

### Imaging

| Task class | Dataset | Predicts |
|---|---|---|
| `COVID19CXRClassification` | COVID19-CXR | COVID-19 (multiclass) |
| `ChestXray14BinaryClassification` | ChestX-ray14 | Single-disease binary |
| `ChestXray14MultilabelClassification` | ChestX-ray14 | Multi-disease multilabel |
| `cardiology_isAR_fn`, `_isBBBFB_fn`, `_isAD_fn`, `_isCD_fn`, `_isWA_fn` | Cardiology | Various ECG abnormalities |

### Text / NLP

| Task class | Dataset | Predicts |
|---|---|---|
| `MedicalTranscriptionsClassification` | Medical Transcriptions | Specialty/category |
| `DeIDNERTask` | PhysioNet DeID | De-identification NER |

### Genomics

| Task class | Dataset | Predicts |
|---|---|---|
| `VariantClassificationClinVar` | ClinVar | Variant pathogenicity |
| `MutationPathogenicityPrediction` | COSMIC | Mutation pathogenicity |
| `CancerSurvivalPrediction` | TCGA-PRAD | Cancer survival |
| `CancerMutationBurden` | TCGA-PRAD | Tumor mutation burden |

### Benchmarks

| Task class | Use |
|---|---|
| `BenchmarkEHRShot` | Multi-task EHR few-shot benchmark on EHRShot |

## Picking the right `monitor` metric

The `Trainer.train(monitor=...)` argument decides which checkpoint gets saved. Match it to the task type:

| Task type | Good `monitor` choices |
|---|---|
| Binary (mortality, readmission, EEG abnormal) | `"pr_auc"`, `"roc_auc"`, `"f1"` |
| Multiclass (LOS, sleep staging, COVID CXR) | `"accuracy"`, `"f1_macro"`, `"cohen_kappa"` |
| Multilabel (drug rec, ICD coding, ChestXray14) | `"pr_auc_samples"`, `"jaccard_samples"`, `"f1_samples"` |

Mismatched `monitor` (e.g., `"pr_auc"` on a multiclass task) silently saves the wrong epoch.

## Custom tasks

When no built-in task fits, subclass `BaseTask`:

```python
from pyhealth.tasks import BaseTask

class MyTask(BaseTask):
    task_name = "MyTask"
    input_schema = {"diagnoses": "sequence", "procedures": "sequence"}
    output_schema = {"label": "binary"}

    def __call__(self, patient):
        # Iterate the patient's visits, decide which become samples,
        # extract features, compute the label, and return a list of dicts.
        samples = []
        for i, visit in enumerate(patient.visits):
            if i == len(patient.visits) - 1:
                continue  # need at least one future visit for the label
            samples.append({
                "patient_id": patient.patient_id,
                "visit_id": visit.visit_id,
                "diagnoses": visit.get_code_list("DIAGNOSES_ICD"),
                "procedures": visit.get_code_list("PROCEDURES_ICD"),
                "label": int(self._compute_label(patient, visit)),
            })
        return samples

    def _compute_label(self, patient, visit): ...
```

The `__call__` is invoked once per patient. Returning `[]` for a patient excludes them from the SampleDataset. The schema strings (`"sequence"`, `"binary"`, `"multilabel"`, `"multiclass"`, `"regression"`) tell PyHealth's processors how to handle each field.
