# Recipes for PyHealth 2.0.2

The starter's invented-data CPU path and the public synthetic MIMIC-III
`set_task -> split -> Transformer -> Trainer` path were executed. Restricted MIMIC-IV,
full SleepEDF and specialized molecular-model experiments below are illustrative,
with constructor/schema contracts checked against released source.

## 1. A runnable plumbing check

From the skill root:

```bash
uv run --no-project --isolated --python 3.12 --with pyhealth==2.0.2 python assets/starter_pipeline.py --demo --epochs 1
```

The asset requires an explicit `--demo` or `--root` choice. Demo records are invented.
For real MIMIC-III, use an authorized local root, e.g. `--root ./data/mimic-iii`;
optional `--dev` limits patient processing. It checks for both binary classes in
train/validation/test before AUC evaluation. The public synthetic bucket with `dev=True` (up to 1000 patients) yielded
20 eligible next-visit samples (18 negative, 2 positive), too few to support three
partitions with both classes. Use the accuracy-only smoke example in `SKILL.md` to
check that download; do not interpret its scores clinically.

## 2. Fit processors only on training patients

For a modest dataset, gather raw task dictionaries, partition patient IDs, then
create processed datasets. This example assumes an already configured `base` and
`task` and was exercised with small synthetic Patient fixtures. For large cohorts,
implement the same policy with streaming/cache-backed preparation.

```python
import random
from pyhealth.datasets import create_sample_dataset

raw = [sample for patient in base.iter_patients() for sample in task(patient)]
ids = sorted({sample["patient_id"] for sample in raw})
random.Random(42).shuffle(ids)
n_train, n_val = int(0.6 * len(ids)), int(0.2 * len(ids))
groups = [set(ids[:n_train]), set(ids[n_train:n_train + n_val]),
          set(ids[n_train + n_val:])]
raw_parts = [[s for s in raw if s["patient_id"] in group] for group in groups]
if any(not part for part in raw_parts):
    raise ValueError("Need a nonempty cohort in each partition")
train = create_sample_dataset(raw_parts[0], input_schema=task.input_schema,
                              output_schema=task.output_schema)
val, test = [create_sample_dataset(
    part, input_schema=task.input_schema, output_schema=task.output_schema,
    input_processors=train.input_processors, output_processors=train.output_processors,
) for part in raw_parts[1:]]
```

Check class counts and unknown-code rates; random patient splitting does not
stratify outcomes or enforce calendar time. Define the target label vocabulary in
advance, especially for multilabel tasks: silently dropping unseen test labels
would overstate performance. Keep fitted processors with the checkpoint.

## 3. MIMIC-IV readmission adaptation

```python
from datetime import timedelta
from pyhealth.datasets import MIMIC4EHRDataset
from pyhealth.tasks import ReadmissionPredictionMIMIC4
from pyhealth.models import RETAIN

base = MIMIC4EHRDataset(
    root="./data/mimic-iv",  # parent of hosp/ and icu/
    tables=["diagnoses_icd", "procedures_icd", "prescriptions"],
    cache_dir="./cache/mimic4",
)
task = ReadmissionPredictionMIMIC4(window=timedelta(days=30))
# Apply the patient/processor partition recipe above, then:
model = RETAIN(dataset=train, embedding_dim=32)
```

Use binary metrics with `Trainer(metrics=["pr_auc", "roc_auc"])`. The upstream task
uses the next recorded admission, excludes the final admission and checks a strict
less-than threshold. Resolve follow-up completeness and transfers before calling
this a 30-day post-discharge readmission study. Attention is an inspection aid.

## 4. Medication recommendation

```python
from pyhealth.tasks import DrugRecommendationMIMIC3
from pyhealth.models import SafeDrug

task = DrugRecommendationMIMIC3()
# Use a MIMIC3 base containing diagnoses_icd/procedures_icd/prescriptions;
# apply the raw-patient partition and training-processor recipe above.
model = SafeDrug(dataset=train, embedding_dim=32, hidden_dim=32)
```

Built-in MIMIC drug tasks map NDC to ATC level 3 and create nested history features;
current-visit medications are excluded from `drugs_hist`. Verify this on actual
samples, check mapped label coverage and resource availability. Use explicit
multilabel metrics such as `pr_auc_samples` and `jaccard_samples`, and report DDI
behavior separately from predictive accuracy. A safe-sounding model name is not a
prescribing guarantee. See [models](models.md) for specialized-model caveats.

## 5. Length of stay

```python
from pyhealth.tasks import LengthOfStayPredictionMIMIC3
from pyhealth.models import RNN

task = LengthOfStayPredictionMIMIC3()
# The base needs prescriptions as well as diagnoses_icd/procedures_icd.
# Apply the partition/processor recipe, then:
model = RNN(dataset=train, rnn_type="GRU", embedding_dim=32, hidden_dim=64)
```

Use `Trainer(metrics=["accuracy", "f1_macro", "cohen_kappa"])` and a matching
monitor. The built-in task is whole-visit code-based, ten-class LOS classification;
filtering features to a declared prediction time is necessary for prospective claims.

## 6. Sleep staging

```python
from pyhealth.datasets import SleepEDFDataset
from pyhealth.tasks import SleepStagingSleepEDF
from pyhealth.models import SparcNet

base = SleepEDFDataset(root="./data/sleep-edf", subset="cassette")
task = SleepStagingSleepEDF(chunk_duration=30.0)
# Group recordings from one subject together before creating train/val/test.
# After preparing compatible signal tensors and processors:
model = SparcNet(dataset=train)
```

The root contains `SC-subjects.xls` and `sleep-cassette/` (or `ST-subjects.xls`
and `sleep-telemetry/`). Initial metadata preparation uses pandas Excel loading
and can require `xlrd` for the `.xls` workbook. Alternatively provide the correctly
prepared `sleepedf-cassette-pyhealth.csv`/`sleepedf-telemetry-pyhealth.csv`.
No `cache_dir=` argument on this dataset wrapper in 2.0.2. Verify person IDs across
nights; an epoch/recording split is not necessarily a subject split. The built-in
task retains W/N1/N2/N3/N4/REM as six classes; decide explicitly whether to merge N3/N4.
Check MNE annotation availability and channel layout before training. Suitable
multiclass metric names include `accuracy`, `f1_macro`, `cohen_kappa`.

## 7. Baselines and checkpoints

`LogisticRegression(dataset=train)` is a PyHealth embedding-plus-linear-head model.
Also consider a separately specified fixed-feature baseline when that is the intended
comparison. Low logistic-model PR-AUC does not prove deeper models cannot help;
compare with prevalence and inspect data quality/label definitions.

After training, reuse the same architecture and processor vocabularies:

```python
trainer.load_ckpt("./output/experiment/best.ckpt")
y_true, y_prob, mean_loss = trainer.inference(test_loader)
```

The checkpoint path is `output_path/exp_name/best.ckpt` when logging is enabled.
It contains weights, not a complete preprocessing pipeline. Medical-code-only
workflows and tested tokenizer examples are in [medical codes](medcode.md).
