# Compass: the eight-task microbiome benchmark

`outpost-bio/Compass` on the Hugging Face Hub — gated, Apache 2.0, ~605 MB, ~62.8k rows across four
Hub configurations. Eight tasks are derived from those four configurations by filtering and by
choosing different target columns.

Hub card schemas/counts were checked on 2026-10-01 at revision
`370f857265cab6756bb06c72451c083b13e2418f`; gated data rows were not downloaded.
The benchmark definitions/scoring were reviewed in the 1.0.2 wheel and matching GitHub source.

Every configuration exposes `train` / `validation` / `test` splits and carries a `Split` column
recording the same assignment.

```python
from datasets import load_dataset
ds = load_dataset("outpost-bio/Compass", "mgnify-biomes",
                  revision="370f857265cab6756bb06c72451c083b13e2418f")   # requires access + HF_TOKEN
```

## The four source datasets

| Config | Source | Rows (train/val/test) | Extra columns |
| --- | --- | --- | --- |
| `mgnify-biomes` | MGnify metagenomic profiles across gut, skin, oral, marine, freshwater, soil, engineered systems | 33,121 / 4,139 / 4,139 | `Biome 1`–`Biome 5`, `Run Accession`, `Data Type`, `Sequencing Method`, `Pipeline Version`, `Study Accession` |
| `handuo` | Shi et al. — 16S amplicon study of drug–microbiome interactions in stool-derived communities | 3,168 / 396 / 396 | `SIC Name`, `Control`, `ATC Class`, `Sample ID` |
| `mastrorilli` | Mastrorilli et al. — drug degradation by gut communities | 9,282 / 3,084 / 3,053 | `Degradation Rate`, `Drug`, `Sample ID` |
| `roswall` | Roswall et al. — longitudinal infant gut cohort | 1,625 / 203 / 203 | `Timepoint`, `Delivery Mode`, `Sample ID` |

All configs carry `Taxa` and `Relative Abundances` as aligned list columns.

## The eight tasks

As defined in `waypoint_bio/benchmark.py`:

| # | Internal id | Config | Targets | Type | Pre-filter |
| --- | --- | --- | --- | --- | --- |
| 1 | `1_biome` | `mgnify-biomes` | `Biome 1`–`Biome 5` | classification (5 outputs) | none |
| 2 | `2_biome_gut` | `mgnify-biomes` | `Biome 4`, `Biome 5` | classification (2 outputs) | `Biome 3 == "Digestive system"` |
| 3 | `3_sic` | `handuo` | `SIC Name` | classification | `SIC Name` starts with `SIC`, excludes `control` and `seed` |
| 4 | `4_drug_non_drug` | `handuo` | `Control` | binary classification | none |
| 5 | `5_drug_class` | `handuo` | `ATC Class` | classification | `ATC Class` not null |
| 6 | `6_drug_degradation` | `mastrorilli` | `Degradation Rate` | regression | none; `Drug` used as covariate |
| 7 | `7_infant_age` | `roswall` | `Timepoint` | classification | none |
| 8 | `8_birth_mode` | `roswall` | `Delivery Mode` | binary classification | none |

What each asks, in plain terms:

1. **Biome classification** — predict all five levels of the MGnify biome ontology at once
   (e.g. `root → Host-associated → Human → Digestive system → Large intestine`).
2. **Gut biome classification** — same, restricted to digestive-system samples, predicting only the
   two finest levels. Harder: the easy environmental separations are gone.
3. **SIC classification** — identify which stool-derived in-vitro community a drug-perturbed sample
   came from.
4. **Drug vs. control** — did this community receive a drug?
5. **Drug class** — recover the ATC class of the applied drug from the resulting composition.
6. **Drug degradation** — regress the degradation rate from composition plus drug identity. The
   `Drug` covariate is one-hot encoded and concatenated to the pooled embedding.
7. **Infant age** — predict the sampling timepoint from an infant gut sample.
8. **Birth mode** — vaginal vs. caesarean delivery.

## Scoring

- **Classification:** macro-averaged F1 — F1 per class, averaged with equal weight. Chosen so the
  metric is not dominated by majority classes. Where a task has several target columns (1 and 2),
  the per-target macro-F1s are averaged.
- **Regression (task 6):** R², clamped to `[0, 1]` so it shares a scale with the F1 scores. A
  negative R² therefore reads as `0.0`, not as "worse than the mean".
- **Final score:** unweighted arithmetic mean of the eight task scores.

Supplementary metrics are computed and stored but do not enter the score: one-vs-one macro ROC-AUC,
macro PR-AUC (pairwise average precision over the same OVO pairs), balanced accuracy, plain
accuracy; and MSE, Pearson, Spearman for regression.

## `benchmark_results.json`

```
benchmark_results.json
├── model          string — the value passed to --model
├── final_score    number — mean of every results[].score
└── results        array, one object per task
    ├── task       string — "1_biome", "6_drug_degradation", ...
    ├── task_type  "classification" | "regression"
    ├── score      number — macro F1, or R² clamped to [0,1]
    └── metrics    object — keys depend on task_type
```

`metrics` keys are suffixed with the target column name:

| Task type | Keys |
| --- | --- |
| `classification` | `accuracy_<target>`, `balanced_accuracy_<target>`, `f1_macro_<target>`; with probabilities, binary `roc_auc_<target>` / `pr_auc_<target>` or multiclass `roc_auc_macro_ovo_<target>` / `pr_auc_macro_ovo_<target>`. Means: `f1_macro_mean`, optionally `roc_auc_mean`, `pr_auc_mean`. |
| `regression` | `mse_<target>`, `r2_<target>`, usually `pearson_<target>` and `spearman_<target>`. Mean: `r2_mean`. |

Example:

```json
{
  "model": "outpost-bio/Waypoint-6m",
  "final_score": 0.545,
  "results": [
    {"task": "1_biome", "task_type": "classification", "score": 0.65,
     "metrics": {"f1_macro_mean": 0.65, "roc_auc_mean": 0.81, "pr_auc_mean": 0.74}},
    {"task": "6_drug_degradation", "task_type": "regression", "score": 0.44,
     "metrics": {"mse_Degradation Rate": 0.019, "r2_Degradation Rate": 0.44, "r2_mean": 0.44}}
  ]
}
```

The numbers above are synthetic, not measured results. They illustrate a two-task subset,
whose mean is `(0.65 + 0.44) / 2 = 0.545`; this is not an eight-task Compass score.
The upstream README example has inconsistent numbers, so do not treat it as output validation.

## Interpreting a benchmark run

**Baselines matter more than the absolute score.** The paper compares Waypoint against classical
baselines (random forest and logistic regression on relative abundances) and against MGM, the prior
microbiome foundation model. Two findings shape how a Compass number should be read:

- In the paper, Waypoint beats the random-forest baseline from roughly **10,000 training examples upward**, and
  was weaker in some small-data settings. This is not a universal threshold. Report training-set
  size and held-out study/subject composition next to any score.
- Baselines can use every taxon; the transformer sees only its fixed vocabulary. The paper's fair
  comparison is the `(no unk)` baseline, with out-of-vocabulary taxa stripped from the baseline's
  input too. Report both vocabulary-matched baselines for representation comparisons and
  full-table baselines for practical method selection; clearly state each input restriction.

**Scale does not monotonically help.** Pretraining loss falls all the way to 170M, but the best
Compass score in the paper came from the **45M** model. Non-pretrained transformers get *worse* as
they grow — the gain from scale is a property of pretraining, not of capacity.

**Reproducibility.** The bundled config uses one epoch; the paper describes up to 300 epochs
with early stopping. Matching the YAML alone does not reproduce the paper. Record the protocol,
avoid `--max_samples` for a full benchmark, and report repeated independent seeds plus uncertainty.
However, the reviewed CLI seeds Torch/NumPy once but does not pass `--seed` into
`TrainingArguments`, which defaults to 42; YAML `seed` is unused.
A seed study requires an explicit local correction and disclosure. The CLI also loads unpinned
Compass revisions internally. Record actual revisions, task subset and software versions; a run
with changed hyperparameters or capped splits must be labelled as a different protocol.
