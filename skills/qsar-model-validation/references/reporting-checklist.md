# What a Defensible Model Report States

A reader who wants to reproduce or challenge a QSAR/ADMET result needs a fixed
set of facts. Their absence is what makes a number unusable, regardless of how
good the model is. Work through this list before a metric goes into a paper, a
report, an internal decision, or a regulatory submission.

## 1. The endpoint

- [ ] **What was modelled**, named precisely: IC50, EC50, Ki, Kd, percent
      inhibition, or a derived value. These are different targets and are not
      interchangeable; a model trained on a mixture predicts none of them.
- [ ] **Units and transformation.** If pIC50, say so, and give the conversion.
- [ ] **The activity cut-off**, for classification, and where it came from. A
      cut-off chosen to balance the classes is a modelling choice, not a
      property of the assay, and it must be stated.
- [ ] **Censored values** (`>`, `<`, ranges) and how they were handled.
- [ ] **Ties and conflicts**: how many compound–target pairs had disagreeing
      measurements, and the rule used. Averaging conflicting assay records
      without stating the rule fabricates precision.

## 2. The data

- [ ] **Source and version**, with a retrieval date. Databases are re-released;
      "from ChEMBL" is not reproducible.
- [ ] **Row counts through the pipeline**: rows read, rows dropped and why,
      duplicates collapsed, final count. A model trained on 92% of the table is
      not the model the report describes.
- [ ] **Structure standardization** decisions, and the fact that the submitted
      structure was retained alongside the standardized one.
- [ ] **Split sizes**, compounds and distinct scaffolds per side.

## 3. The evaluation

- [ ] **The split, named, next to every metric.** Random, scaffold, time, group.
- [ ] **The dummy baseline** for the same split, alongside the model's score.
- [ ] **Leakage checks**: exact overlap, near-duplicate count at a stated
      threshold, and shared scaffolds between the sides.
- [ ] **Seed or seeds**, with the range across seeds rather than a single value.
- [ ] **The metric definition** where it is ambiguous -- RAE against the
      training mean, enrichment at a stated cutoff, PR-AUC rather than ROC-AUC
      under imbalance.

## 4. Calibration and domain

- [ ] **Calibration**, whenever probabilities feed a decision: the reliability
      curve, and ECE with the bin count. State whether a correction was fitted
      and on which rows.
- [ ] **Applicability domain**: the method, the threshold and how it was
      derived, the out-of-domain fraction, and **performance scored separately
      inside and outside the domain**.

## 5. The claim

- [ ] **The limitation stated in the same place as the result**, not in a
      closing paragraph. "RMSE 1.28 on a scaffold split; the model does not beat
      the training mean on a time split" is a result. "RMSE 0.36" is a headline.
- [ ] **What the model was not tested on.** If no prospective data was used, say
      so; a retrospective result is not evidence of prospective utility.
- [ ] **Applicability of the conclusion**: which chemistry the result covers, and
      which it does not.

## Worked example

The table below is what `split_compare.py` produces on a table whose activity is
decided by scaffold family -- a synthetic illustration, but the shape of the
result is the ordinary case.

```
split     model  min    max    dummy  vs random  beats dummy
random    0.356  0.313  0.396  1.482  -          True
scaffold  1.283  1.096  1.445  1.416  0.927      True
time      1.467  1.466  1.467  1.330  1.110      False
```

Read it as three different claims about the same model:

- On a random split it beats a mean predictor by a wide margin. This is the
  number a report quotes when the split is not named, and it is the most
  flattering of the three.
- On a scaffold split its error is 0.93 higher -- 3.6 times the random-split
  error. New chemotypes are much harder, which is expected, and this is the
  number that applies to a novel series.
- On a time split it does not beat predicting the mean. Whatever it learned does
  not transfer forward.

None of these numbers is wrong. Quoting only the first is.

## Anti-patterns

| Statement | Why it fails |
| --- | --- |
| "RMSE 0.36" | No split, no baseline, no n |
| "AUC 0.95, 5-fold cross-validation" | Cross-validation over a random split is still a random split |
| "The model generalizes well to new compounds" | Only tested within known chemistry |
| "ADMET predictions for the library" | No domain flags, so extrapolations are indistinguishable |
| "Probability of toxicity: 0.8" | Uncalibrated, and the training prevalence is unstated |
| "We removed outliers to improve performance" | State the rule and report both numbers |
| "Test set: 30 compounds" | 30 compounds and 2 scaffolds is a different test set from 30 compounds and 30 scaffolds |
