# Applicability Domain and Out-of-Distribution Predictions

A model trained on one region of chemical space returns a number for any
structure it is given. Outside the region its training data covered, that number
is an extrapolation, and it is formatted identically to an interpolation. The
applicability domain (AD) is the label that distinguishes them.

The flag is not a prediction that a compound is inactive, toxic, or
unsafe. It says only that the training set does not cover this chemistry, so the
model's error on it is unknown and is usually much larger.

## Methods

| Method | How it works | Trade-off |
| --- | --- | --- |
| **Similarity to training** | Max Tanimoto to any training compound; below a threshold means outside | Robust, cheap, the sensible default; a single similar analogue can hide a novel scaffold |
| **Descriptor range** | Outside the training min/max on any descriptor | Catches gross property outliers; flags legitimate analogues just past one boundary |
| **Ensemble variance** | Spread across the ensemble's members | Needs a model that exposes it; measures disagreement, not distance |
| **Dedicated OOD model** | A learned one-class or density model | More machinery than most QSAR reports need |

`applicability_domain.py` implements the first two and a consensus of them.

## Choosing a threshold

A hardcoded 0.5 is a common default and a poor one: how similar is similar
enough depends entirely on how diverse the training chemistry is. A training set
of close analogues should require a high similarity; a deliberately broad set
should not.

The script therefore derives the default cut from the training set itself -- the
5th percentile of each training compound's similarity to its nearest *other*
training compound. The reading is: a test compound less similar to the training
set than the least-similar 5% of the training set are to each other is outside
the domain by the training set's own standard. Raise `--percentile` for a
stricter domain, or pass `--threshold` to fix it explicitly, and state which you
did.

## Reporting

The single number that matters is `outside_fraction`; the number that changes
decisions is the **performance gap between the two groups**.

When the test targets are known, pass `--prediction-col` and the script scores
the model separately inside and outside the domain. Quote both. A model with
RMSE 0.14 inside and 1.36 outside is not a model with RMSE 0.75 -- the average
describes neither group, and the second number is the one that applies to a
novel screening library.

Three cases worth recognising:

- **Most of the test set is outside the domain.** The headline metric is then
  mostly a statement about extrapolation. Retrain on chemistry that covers the
  intended screening library before quoting a number for it.
- **Nothing is outside the domain.** Suspicious: either the test set is drawn
  from the training chemistry, which makes the check vacuous, or the threshold is
  too loose.
- **The out-of-domain group is too small to score.** Then the size of the
  extrapolation penalty is unknown, and predictions on those compounds should not
  be acted on. Report that rather than the compound count.

## Operating guidance

- **Flag at the level of the decision, not the row.** AD flags are most useful
  when a screening pipeline routes out-of-domain hits to a different action --
  order a measurement, or run a physics-based calculation -- rather than
  silently ranking them with everything else.
- **Report the flag next to the prediction.** A prediction table without the AD
  column loses the information exactly when it is needed.
- **Do not use the flag as a filter to improve the metrics.** Dropping
  out-of-domain compounds and reporting only the in-domain score is the same
  evasion as choosing a favourable split; report both groups.
- **Recompute the domain when the training set changes.** The threshold is a
  property of the training data, so a retrained model has a new domain.
