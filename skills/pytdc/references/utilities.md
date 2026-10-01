# Splits, evaluators, and benchmark groups

This reference describes behavior verified in the **PyTDC 1.1.15** source
distribution on 2026-10-01. The official website documents user-facing intent;
source inspection resolves exact method spellings and edge cases.

## Split API overview

Ordinary loaders return:

```python
{
    "train": train_frame,
    "valid": validation_frame,
    "test": test_frame,
}
```

The key is `valid`, not `val`. Generic defaults are:

```python
split = data.get_split(
    method="random",
    seed=42,
    frac=[0.7, 0.1, 0.2],
)
```

Fractions are train/validation/test and should be finite, non-negative, and sum to
one. Upstream does not consistently validate this before arithmetic; the bundled
CLI does.

### Loader-specific methods

| Loader family | Verified methods | Additional arguments |
|---|---|---|
| Single prediction | `random`, `scaffold`, internal `cold_<entity>` | none |
| Pair prediction (`DTI`, `DDI`, etc.) | `random`, `cold_split`, entity aliases such as `cold_drug`, `combination`, `time` | `column_name`, `time_column` |
| General multi-prediction frame | `random`, `cold_split`, `combination` | `column_name` |
| `MolGen`, `Reaction`, `RetroSyn` | `random` | none |
| Benchmark train/valid | group metadata chooses `scaffold`, `random`, `combination`, or `group` | `benchmark`, `split_type`, `seed` |

The generic official cold-start spelling is:

```python
split = data.get_split(
    method="cold_split",
    column_name=["Drug", "Target"],
    seed=42,
    frac=[0.7, 0.1, 0.2],
)
```

Inspect `data.get_data().columns` first. A DTI frame commonly uses `Drug` and
`Target`, but other tasks have different entity names. Prefer `cold_split` with
explicit columns over inferred aliases.

## Random split details

`create_fold`:

1. samples test rows with `random_state=seed`;
2. samples validation rows from the remainder with **fixed**
   `random_state=1`;
3. assigns remaining rows to train;
4. resets partition indices.

Consequences:

- the supplied seed changes test membership;
- it does not independently seed validation sampling;
- integer rounding and Pandas sampling can make exact counts differ from naïve
  multiplication;
- a different seed is not a guarantee that every partition changes.

Record content hashes or stable IDs when exact split reproducibility matters.

## Scaffold split details

The official generic documentation limits scaffold split to molecule-based
single-instance ADME, Tox, and HTS tasks. In 1.1.15 the implementation:

- requires RDKit;
- parses the configured molecular entity as SMILES;
- computes Bemis–Murcko scaffold strings with `includeChirality=False`;
- groups rows by exact scaffold string;
- shuffles large and small scaffold groups with `seed`;
- greedily assigns whole groups to partitions;
- omits SMILES that raise during scaffold generation.

The requested row fractions are targets, not guarantees, because whole scaffold
groups are assigned together. “Scaffold split” means exact computed scaffold groups
do not cross partitions in that implementation. It does **not** establish that:

- close analogs or similar scaffolds cannot cross;
- duplicates, labels, assay batches, sources, or dates are isolated;
- stereochemistry is isolated;
- invalid/missing structures are represented;
- preprocessing performed before splitting did not leak information.

Audit exact structures, scaffolds, identifiers, labels, provenance, and temporal
fields appropriate to the scientific question. Use cautious language such as
“partitioned by PyTDC's 1.1.15 Murcko-scaffold implementation,” not “leakage-free.”

## Cold split details

`cold_split` samples unique values independently for each requested column, then:

- keeps test rows satisfying all sampled test-entity memberships;
- removes any row containing a test entity from the train/validation pool;
- samples validation entity values from the remainder;
- keeps validation rows satisfying all validation memberships;
- removes validation entities from train.

For multiple columns this intersection/removal process can discard many
cross-combination rows, produce empty validation/test partitions, and yield row
fractions far from `frac`. PyTDC raises `ValueError` when test or validation is
empty.

Exact values in each requested column are designed to be disjoint across returned
partitions. That is a narrow entity-overlap property, not proof against:

- aliases or duplicated entities with different identifiers;
- homologous targets or structurally near-identical compounds;
- shared higher-level groups;
- preprocessing or label leakage.

The bundled loader CLI reports pairwise exact-value overlap counts for requested
columns without making a broader claim.

`cold_drug_target` is not a 1.1.15 method. Use:

```python
data.get_split(
    method="cold_split",
    column_name=["Drug", "Target"],
    seed=42,
)
```

## Combination and time splits

### Combination

The built-in `combination` implementation is designed for DrugSyn data with
`Drug1_ID`, `Drug2_ID`, and `Cell_Line_ID`. It separates drug-pair combinations
across partitions while representing cell lines.

In 1.1.15 it adds an internal `concat` column and does not remove it consistently
from every returned partition. Inspect schemas rather than assuming identical
columns. Do not apply it generically to DDI or DTI.

### Time

Pair loaders use:

```python
split = data.get_split(
    method="time",
    time_column="Year",
    frac=[0.7, 0.1, 0.2],
)
```

The verified built-in dataset case is `DTI(name="BindingDB_Patent")`, whose loader
adds `Year`. The implementation sorts by the time column and returns an additional
`split_time` summary. It does not use `seed`.

The spelling `temporal` is unsupported. Time boundaries can contain ties and the
implementation uses boundary comparisons, so inspect timestamps and counts.

`stratified=True` is not a supported `get_split` argument in these loaders.

## Evaluator registry

Discover exact names from the installed package:

```bash
python scripts/discover_metadata.py --kind evaluators --limit 100
```

Verified scalar registry names include:

```text
roc-auc, f1, pr-auc, precision, recall, accuracy,
mse, rmse, mae, r2, pcc, spearman,
micro-f1, macro-f1, kappa, avg-roc-auc,
rp@k, pr@k, range_logAUC
```

Generation/distribution names include:

```text
novelty, diversity, uniqueness, validity, fcd_distance, kl_divergence
```

Coordinate names include `rmsd` and `kabsch_rmsd`. Metadata also lists `smina`, but
the 1.1.15 `Evaluator.assign_evaluator` implementation does not bind an evaluator
function for it; treat `Evaluator("smina")` as an unresolved upstream inconsistency,
not supported usage.

Always pass exact registry names. Fuzzy matching exists, but aliases such as
`Pearson`, `Micro-AUPR`, and `Macro-AUPR` are not registered.

### Inputs and direction

| Metrics | Input | Better direction |
|---|---|---|
| `mse`, `rmse`, `mae` | continuous truth and predictions | lower |
| `r2`, `pcc`, `spearman` | continuous truth and predictions | higher |
| `roc-auc`, `pr-auc`, `range_logAUC` | binary truth and real-valued scores | higher |
| `accuracy`, `precision`, `recall`, `f1` | binary truth and scores plus optional threshold | higher |
| `micro-f1`, `macro-f1`, `kappa` | integer class labels | higher |
| `avg-roc-auc` | per-instance sequences of binary truth/scores | higher |
| `pr@k`, `rp@k` | binary truth/scores and target recall/precision | higher |
| `validity`, `uniqueness`, `novelty`, `diversity` | SMILES collections (some also need a reference set) | higher by their documented definitions |
| `kl_divergence` | generated and reference SMILES | higher; mean of `exp(-KL)` terms |
| `fcd_distance` | generated and reference SMILES | backend-dependent; see below |
| `rmsd`, `kabsch_rmsd` | paired coordinate arrays | lower |

This table describes evaluator semantics, not every benchmark's leaderboard
objective. Use `bm_metric_names` or the official benchmark page for the chosen
benchmark. Never infer a dataset's metric from “classification” or “regression”
alone.

### Call behavior

```python
from tdc import Evaluator

mae = Evaluator("MAE")(y_true, y_pred)
auroc = Evaluator("ROC-AUC")(y_true_binary, predicted_scores)
spearman = Evaluator("Spearman")(y_true, y_pred)
```

Thresholded `accuracy`, `precision`, `recall`, and `f1` default to 0.5 and convert
scores with `score > threshold`; a score exactly equal to the threshold becomes
class 0. `PR@K` and `RP@K` default to **0.5 through Evaluator**, overriding the
underlying functions' 0.9 default. Pass `threshold=0.9` explicitly when desired. Spearman returns
only the correlation coefficient from SciPy's result.

`pr-auc` calls scikit-learn `average_precision_score`, not trapezoidal PR-curve
integration. `avg-roc-auc` averages over axis 0 (one AUC per row/sequence), so
transpose task matrices only when that matches the intended unit of averaging.
`range_logAUC` defaults to FPR range `(0.001, 0.1)`; the public wrapper does not
forward `FPR_range`. Likewise `Evaluator("kabsch_rmsd")` performs rotation without
centroid translation and ignores a `translate` keyword; center paired coordinates
first or call `tdc.evaluator.kabsch_rmsd(P, Q, translate=True)` directly.

`kl_divergence` averages ten `exp(-KL)` terms over molecular descriptors and
internal similarity. Higher means closer distributions; it is not raw KL.
Unpatched 1.1.15 also imports removed `scipy.histogram`: KL fails on the tested
modern SciPy stack. A test-only alias to `numpy.histogram` reproduced the intended
transform, but is not an upstream fix or a supported unpatched workflow. Its KDE
can fail for tiny, constant, or singular samples.
`fcd_distance` tries TensorFlow/FCD first, returning `exp(-0.2 * raw_FCD)` (higher
is closer), then falls back to PyTorch/fcd_torch, returning raw FCD (lower is
closer). Record the selected backend and transformation; do not compare these
values directly or infer direction from the registry name. Optional FCD models
were source-verified only, not downloaded/executed in this refresh.

Validate lengths, shapes, label encoding, missing values, score calibration, and
class presence before calling. ROC-AUC is undefined when only one class is present.

## BenchmarkGroup API

Public specialized imports in 1.1.15 are:

```python
from tdc.benchmark_group import (
    admet_group,
    docking_group,
    drugcombo_group,
    dti_dg_group,
)
```

The generic top-level import is deprecated:

```python
# Compatibility only; emits a deprecation message.
from tdc import BenchmarkGroup
```

Use a specialized class. Construction can download and extract an entire group
archive:

```python
from tdc.benchmark_group import admet_group

group = admet_group(path=".pytdc-benchmarks")
```

Do this only after user approval.

### Retrieve fixed test and train/validation data

```python
benchmark = group.get("Caco2_Wang")
name = benchmark["name"]
train_val = benchmark["train_val"]
test = benchmark["test"]

train, valid = group.get_train_valid_split(
    seed=1,
    benchmark=name,
    split_type="default",
)
```

There is no general `get_test()` method in 1.1.15. `group.get()` returns
`train_val`, `test`, and normalized `name`. `get_train_valid_split` reads the
downloaded train/validation file and applies group metadata. The held-out test set
is fixed. The base splitter uses `[0.875, 0.125, 0.0]` of train_val for ordinary
train/valid splits; the `group` path instead holds out 0.2 within `Year`. With zero
test fraction, the random path's fixed validation seed makes its split identical
across the requested seeds. Vary model training seeds independently.

### One-run evaluation

Predictions must align exactly with the downloaded test-frame row order:

```python
predictions = {name: y_pred_test}
result = group.evaluate(predictions)
# {normalized_name: {metric_name: value}}
```

Do not include test labels as model features, generate predictions from test labels,
or tune against repeated test evaluations.

### Multi-run aggregation

```python
prediction_runs = [
    {name: y_pred_seed_1},
    {name: y_pred_seed_2},
    {name: y_pred_seed_3},
    {name: y_pred_seed_4},
    {name: y_pred_seed_5},
]
summary = group.evaluate_many(prediction_runs)
# {normalized_name: [mean, population_standard_deviation]}
```

Single-run scores are rounded to three decimals before `evaluate_many` computes
population standard deviation (`ddof=0`), then rounds the aggregate to three
decimals. Retain raw per-run metric values separately when more precision matters.
`evaluate(testing=False)` references an undefined `true` variable in 1.1.15; use
an explicit `Evaluator` on validation labels instead.

The input is a list of per-run dictionaries, not `{seed: predictions}` and not a
benchmark object indexed by seed. Non-docking groups require at least five runs.
The 1.1.15 implementation returns a `ValueError` object instead of raising when
fewer are supplied; the bundled CLI validates count first.

The official guidance calls for at least five independent runs. A seed should
control model initialization, stochastic training, and the train/validation split
where the upstream splitter actually uses it. Report every seed and protocol.

## Bundled benchmark JSON

Plan mode never constructs a group:

```bash
python scripts/benchmark_evaluation.py \
  --group admet_group --dataset Caco2_Wang
```

Single-run input:

```json
{
  "caco2_wang": [0.1, 0.2, 0.3]
}
```

Multi-run input:

```json
{
  "runs": [
    {"seed": 1, "predictions": {"caco2_wang": [0.1, 0.2]}},
    {"seed": 2, "predictions": {"caco2_wang": [0.1, 0.2]}},
    {"seed": 3, "predictions": {"caco2_wang": [0.1, 0.2]}},
    {"seed": 4, "predictions": {"caco2_wang": [0.1, 0.2]}},
    {"seed": 5, "predictions": {"caco2_wang": [0.1, 0.2]}}
  ]
}
```

The CLI bounds input size/run count/value count, rejects non-finite numbers,
duplicate normalized names, unequal benchmark sets or per-benchmark run lengths,
and verifies test-row counts before scoring. It requires `--execute` before group
construction. It intentionally excludes
`docking_group` because that path can invoke docking, receptor downloads, molecular
filters, and optional external services.
