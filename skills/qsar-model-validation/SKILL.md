---
name: qsar-model-validation
description: Validate QSAR, activity-prediction, and ADMET models before their numbers are trusted, reported, or used in a decision. Use when reporting model performance, choosing between random and scaffold splits, checking a molecule table for data leakage, computing an applicability domain or out-of-distribution flags, calibrating predicted probabilities, or reviewing a virtual-screening or ADMET model for a paper, a report, or a go/no-go call. Triggers include "scaffold split", "random split", "cross-validation", "data leakage", "applicability domain", "out of distribution", "OOD", "probability calibration", "reliability curve", "ECE", "Brier score", "enrichment factor", "dummy baseline", "the model looks too good", "metrics do not reproduce", "ADMET prediction confidence", and any request to judge whether a QSAR, ADMET, or property-prediction number is trustworthy. For the modelling APIs themselves, see the rdkit, deepchem, pytdc, molfeat, and scikit-learn skills.
license: MIT
compatibility: Requires Python 3.10+ with rdkit, scikit-learn, pandas, numpy, and scipy installed. No network access is needed; every script reads local CSV or TSV files.
metadata:
  version: "1.0"
  skill-author: caliperworks
---

# QSAR Model Validation

## Overview

Decide whether a molecular property model's reported numbers can be trusted, and
document the evidence so a reviewer cannot take them apart by asking one
question.

Most published QSAR and ADMET metrics are inflated, and they are inflated in a
specific, mechanical way: a random split puts analogues of the test compounds in
the training set, so the model is scored on chemistry it has already seen. The
error is not in the arithmetic. It is that the number answers a different
question from the one the report claims to answer.

This skill produces the comparison that makes the gap visible -- the same model,
the same table, several splits, with the leakage counts that explain the
difference -- and states what each number does and does not support.

## When to Use This Skill

Use this skill when:

- Reporting QSAR, ADMET, or activity-prediction performance in a paper, a
  report, or a slide.
- Deciding how to split a molecule table, or reviewing someone else's split.
- A model's cross-validation score looks too good, or does not reproduce.
- Computing an applicability domain, or marking which predictions are
  extrapolations.
- Checking whether predicted probabilities can be read as probabilities.
- Reviewing a virtual-screening result before it drives which compounds get
  made or ordered.
- Comparing two models whose scores came from different splits.

## Installation

Use **uv** to install the libraries these scripts import. They are the ordinary
scientific Python stack; no chemistry-specific extras are needed beyond RDKit.

```bash
uv pip install "rdkit>=2024.3" "scikit-learn>=1.4" "pandas>=2.2" "numpy>=1.26" "scipy>=1.11"
```

**Compatibility notes (verified against RDKit 2026.3.6, scikit-learn 1.4+,
pandas 2.2+, Python 3.12):**

- **RDKit 2024.09 deprecated `AllChem.GetMorganFingerprintAsBitVect`** in favour
  of `rdFingerprintGenerator`. The scripts use the newer generator and fall back
  to the older entry point when it is absent, so both sides of that change work.
  If you write your own fingerprint loop against an older release, expect the
  deprecation warning.
- **`scipy` is optional.** Without it, rank correlation is reported as `null`
  rather than failing; every other metric is computed from scikit-learn and
  NumPy.
- **A constant input array does not reliably have `std() == 0`.** The dummy
  baseline's repeated prediction has a standard deviation around `1e-16` from
  floating-point cancellation. Check for constancy by counting distinct values,
  as `_common._is_constant` does, not by comparing a standard deviation to zero.

## Validation Workflow

Work through these in order. Each step exists because skipping it produces a
number that is wrong in a way the report will not reveal.

1. **Fix the endpoint before touching a model.** IC50, EC50, Ki, Kd, and percent
   inhibition are different targets and cannot share a label column. Pick a
   scale, state the units, keep censored values censored, and decide -- now, in
   writing -- how conflicting measurements of the same compound will be
   combined. See `references/reporting-checklist.md` for the full endpoint list.

2. **Split by the question being asked.** A random split answers "can it rank new
   compounds from known chemistry"; a scaffold split answers "can it rank new
   chemotypes"; a time split answers "would it have worked forward". Almost every
   report claims the second and measures the first. `references/splits.md` has
   the decision table and the two ways a scaffold split silently degenerates.

3. **Score every split you can afford, and keep the random one as a reference.**
   The gap between the random and scaffold numbers is the most informative value
   in the comparison, because it quantifies how much of the performance came
   from recognizable chemistry.

4. **Check leakage explicitly.** Count exact duplicate structures across the
   fold, near-duplicates above a stated Tanimoto, and scaffolds present on both
   sides. A scaffold split that shares scaffolds is not a scaffold split.

5. **Fit a dummy baseline on the same training fold.** A metric without a
   baseline cannot be interpreted, and the baseline's own score moves with the
   class balance, so it has to come from the same split.

6. **Report metrics with the split named, the sample size, and a seed range.**
   Three seeds is usually enough to see whether a difference between two models
   is larger than the split-to-split noise. `references/metrics-and-calibration.md`
   covers metric choice, the RAE denominator, and enrichment factors.

7. **Calibrate anything that will be read as a probability.** ROC-AUC measures
   ranking only. Fit the correction on rows held out from the rows you report
   on, and verify that ROC-AUC did not move -- a monotone calibrator must not
   change it.

8. **Mark the applicability domain and report performance separately inside and
   outside it.** A model that is accurate in-domain and useless out-of-domain is
   the normal case, and a single averaged metric describes neither group. See
   `references/applicability-domain.md`.

## Common Failure Modes

| Failure | What it produces |
| --- | --- |
| Reporting only a random split | A metric inflated by analogues in the training set; the model fails on new chemistry |
| No dummy baseline | No way to tell a weak model from a strong one |
| Averaging conflicting assay records without a stated rule | Fabricated precision; the label noise is hidden rather than handled |
| Mixing IC50, EC50, and Ki into one label column | Label noise that no model can overcome |
| Fitting scaling, imputation, or feature selection before splitting | Leakage from the test set into training |
| Cross-validation over a random split | Still a random split; the folds do not fix the split type |
| Selecting features or hyperparameters on the test set | The test set becomes a validation set and stops being a test |
| Quoting probabilities that were never calibrated | Systematic overconfidence in every threshold decision |
| A single split with a single seed | A point estimate whose spread is unknown and often larger than the claimed difference |
| Reporting an out-of-domain fraction with no per-group performance | Hides that the headline number describes extrapolation |
| R² or AUC with no sample size or scaffold count | Conceals a test set of four independent scaffolds |

## Scripts

### Compare splits

The central tool. Fits one fixed model on random, scaffold, time, and group
splits of the same table, scores each against a dummy baseline, and reports the
leakage counts that explain any gap. The human-readable comparison goes to
stderr; the JSON document goes to stdout, so it can be piped.

```bash
python scripts/split_compare.py --input actives.csv --target-col pIC50 \
    --task regression --seeds 0,1,2

python scripts/split_compare.py --input actives.csv --smiles-col SMILES --target-col pIC50 \
    --task classification --active-threshold 6.5 --group-col series --time-col year \
    --bootstrap 1000 --output report.json
```

Results are written to `report.json` with `--output`, which refuses to overwrite
without `--force`. Duplicate structures are collapsed to their mean before
splitting, and the count is reported under `cleaning`.

### Mark the applicability domain

```bash
python scripts/applicability_domain.py --train train.csv --test test.csv \
    --target-col pIC50 --prediction-col predicted --task regression
```

Pass `--prediction-col` as well as `--target-col` to have the model scored
separately inside and outside the domain, which is the comparison worth
reporting. The similarity threshold defaults to the 5th percentile of the
training set's own nearest-neighbour similarity distribution; `--threshold`
overrides it and the report states which was used. `--method descriptor-range`
switches to the training min/max box, and `consensus` flags on either.

### Report and fix calibration

```bash
python scripts/calibration_report.py --input predictions.csv \
    --probability-col prob --label-col active --bins 10

python scripts/calibration_report.py --input predictions.csv \
    --probability-col prob --label-col active --method isotonic \
    --calibration-col is_calibration_row
```

Without `--calibration-col` the input is split into a calibration slice and an
evaluation slice, and only the evaluation slice is scored -- a calibrator fitted
and graded on the same rows is always excellent and always meaningless. The
script reports ECE, Brier, the reliability curve, and whether the correction
actually helped; if it did not, it says so instead of presenting it as an
improvement.

## Reporting

Every number in a report needs four things attached: the endpoint, the split
name, the sample size, and the baseline it should be compared against. Anything
less cannot be reproduced or challenged.

`references/reporting-checklist.md` is the full field list, with a worked
example of reading a three-split comparison and a table of statements that read
as results but are not.

## Related Skills

- **rdkit** -- structure parsing, descriptors, and the fingerprint generators
  these scripts call.
- **deepchem**, **pytdc**, **molfeat** -- model and dataset APIs; use them to
  train, and this skill to decide whether the resulting number means anything.
- **scikit-learn** -- the estimators and metrics underneath the comparison.
- **statistical-analysis** -- effect sizes, intervals, and multiple-comparison
  corrections when several models are being compared at once.
- **scientific-critical-thinking** -- reviewing the claim rather than the code.
