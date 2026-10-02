# Metrics, Baselines, and Calibration

## Always report a baseline

A metric without a baseline is uninterpretable. `split_compare.py` fits a dummy
predictor on the same training fold and reports its score beside the model's, so
that "the model reaches AUC 0.72" can be read against "the majority class
reaches AUC 0.50".

The baseline belongs to the split, not to the dataset: the dummy's score changes
when the class balance changes, which is precisely why the comparison has to be
made within the same split. A model that beats the baseline on a random split
and does not beat it on a scaffold split has learned the training chemistry and
nothing that transfers.

## Regression metrics

| Metric | Use it for | Watch out for |
| --- | --- | --- |
| **RMSE** | The headline when large errors matter | Dominated by a few outliers; always pair with MAE |
| **MAE** | The typical error, robust to outliers | Hides a heavy tail |
| **R²** | Comparing against a variance-only baseline | Goes negative on a bad split, which is informative |
| **RAE** | Cross-dataset comparison | The denominator must be the *training* mean |

**RAE is the one most often computed wrongly.** It is
`Σ|y − ŷ| / Σ|y − ȳ_train|`: the naive predictor is the training-set mean, not
the test-set mean. Dividing by the test mean makes the model look better exactly
when the test set is unrepresentative -- which is the situation the metric exists
to expose. `regression_metrics()` takes `train_mean` explicitly for this reason.

**Report the sample size with every metric.** An RMSE on 30 compounds carries an
interval wide enough to swallow most claimed improvements.

## Classification metrics

| Metric | Use it for | Watch out for |
| --- | --- | --- |
| **ROC-AUC** | Ranking, when the classes are balanced | Optimistic under class imbalance |
| **PR-AUC** | Ranking actives when they are rare | Depends on prevalence, so it is not comparable across datasets |
| **Enrichment factor** | Screening: how many actives in the top *n*% | Meaningless without the cutoff stated |
| **Accuracy** | Almost nothing here | A 2%-active dataset gives 98% accuracy by predicting "inactive" |

For screening claims the enrichment factor at a stated cutoff is the number a
medicinal chemist actually wants, and it is the one least often reported. State
the cutoff: "3.4-fold enrichment in the top 1%" is a claim; "good enrichment" is
not.

**A single-class test split makes AUC undefined.** `classification_metrics()`
returns `None` rather than a number. Do not substitute 0.5 or drop the row: a
test split with no actives cannot support any statement about ranking actives,
and saying so is the correct result.

## Calibration

Discrimination and calibration are different properties, and only the first is
measured by AUC.

- **Discrimination**: does the model rank actives above inactives?
- **Calibration**: when the model says 0.8, is it right about 80% of the time?

A model can have AUC 1.00 and be badly calibrated. That combination is common
with small or shallow forests, whose probabilities are pulled toward the middle,
and it is the dangerous case: the ranking looks perfect in the validation table,
while every threshold-based decision downstream is made on a number that does
not mean what it says.

### Reading the reliability curve

Bin the predictions, and for each bin compare the mean predicted probability to
the observed frequency. Report the curve, not only a summary number -- the shape
tells you *where* the model is wrong (overconfident at the top, underconfident in
the middle), which is what determines whether a correction will help.

### Expected calibration error, and its floor

ECE is the bin-weighted mean of |observed − predicted|. With equal-width bins it
**cannot fall below roughly 1/(2 × bins)** for extreme probabilities: a perfectly
calibrated forecast of 0.9 lands in the bin centred at 0.9, leaving a 0.1 gap.
So with `bins=10`, an ECE of 0.05 is not a defect and an ECE of 0.0 is
unreachable. Compare ECE values computed with the same bin count, and treat the
curve as the primary artefact.

### Brier score

Brier is the mean squared error of the probabilities. It mixes discrimination
and calibration, so it is a good summary and a poor diagnostic: a model can
improve its Brier score by sharpening its ranking without becoming any better
calibrated.

### Fitting a correction

- **Platt scaling** fits a one-parameter logistic on the score's log-odds. It
  needs few rows and preserves the ranking exactly.
- **Isotonic regression** fits a monotone step function. It is more flexible and
  needs more data; on a small calibration slice it will overfit and can make ECE
  worse.

Both must be fitted on rows that are **not** the rows being reported on.
`calibration_report.py` holds out a calibration slice and scores only the
evaluation slice, because a calibrator fitted and graded on the same rows
reports a near-perfect ECE that means nothing.

A monotone calibrator must leave ROC-AUC unchanged. If it moves, the correction
is not monotone -- usually because the scores contain ties that the fitting
procedure broke. The script checks this and says so.

## Uncertainty on the metric

Report an interval, or the spread across seeds. `--bootstrap` gives a percentile
interval over resampled test rows; resamples on which the metric is undefined
(an AUC draw containing one class) are counted and reported rather than silently
dropped, because hiding them would narrow the interval for the wrong reason.

The bootstrap covers sampling variation of the *test set*. It does not cover the
variation from the split itself, which is usually larger. Running several seeds
is the better check when the table allows it.
