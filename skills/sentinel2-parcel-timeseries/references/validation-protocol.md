# Validating models trained on parcel labels

Field data usually give one label per parcel (infected or healthy, a yield class, a crop type),
while satellite data give hundreds of pixels per parcel. Training on pixels that inherit the
parcel label (weak labels) is legitimate, but it changes what counts as an independent sample.

## The unit of inference is the parcel

Pixels of one parcel share soil, variety, sowing date, irrigation, management and label.
They are not independent, so:

- **Split by parcel, never by pixel.** Use `LeaveOneGroupOut` (few parcels) or `GroupKFold`
  (many) with the parcel identifier as group. `parcel_group_cv.py` asserts that no parcel is in
  both train and test.
- **Score parcels, not pixels.** Average pixel probabilities per parcel, then compute the AUC
  over parcels. A pixel-level AUC counts each parcel hundreds of times and gives an effective
  sample size that does not exist.
- **Report the number of parcels** next to every metric. Each swap of one positive and one
  negative parcel in the ranking moves the AUC by 1/(n_pos x n_neg): 0.02 for 7 against 7.

## How much a pixel split inflates the score

`python scripts/parcel_group_cv.py --demo --permutations 30` builds 16 synthetic parcels whose
features identify the parcel but whose labels are random. Observed on scikit-learn 1.6.1:

| Protocol | Parcel AUC |
|---|---|
| random pixel split (leaky) | 1.00 |
| leave one parcel out | 0.09 |
| permutation test | p = 0.97 |

The leaky split scores perfectly on pure noise: the model recognises parcels it has already
seen. Always run `--compare-leaky` once on real data. A large gap means the model relies on
parcel identity.

An AUC well below 0.5 under leave-one-out on a null signal is a known artefact, not a result:
leaving a parcel out shifts the class balance of the training set against that parcel's class.
This is why the p-value comes from permuting labels **between parcels** and re-running the
whole protocol, not from comparing the AUC to 0.5.

## Negative control: can the model predict before the crop exists?

A model can separate labelled parcels for reasons unrelated to the condition studied: the
location or block, the previous crop, soil type, irrigation system, or the farmer's management.
When one of these is correlated with the label, the model learns it.

Test it directly. Retrain with features from a window where the condition cannot be visible,
typically before sowing or before emergence, using `--features` to select those columns:

```bash
python scripts/parcel_group_cv.py pixels.csv --group-col parcel_id --label-col label \
    --features "_m0[34]$" --model logistic --permutations 200
```

If pre-sowing features already give a high parcel AUC, the labels are predictable from the site,
and the in-season AUC cannot be attributed to the disease or crop state. Report both numbers.
Remedies: evaluate within a homogeneous subset (one irrigation type, one block), add parcels
that break the correlation, or model the site factor explicitly.

## Also check

- **Seed variance.** Models with random components (random forests, random convolution kernels
  such as MiniROCKET, neural networks) can change parcel AUC by 0.1 or more between seeds on a
  small set. Run several seeds and report the mean and the range, not the best seed.
- **Removing variables.** When a reviewer asks to drop location or management variables, retrain
  and compare parcel scores, and not only the AUC: identical AUC with reshuffled parcel scores is
  a different model.
- **Leakage through preprocessing.** Anything fitted on the data (scalers, feature selection,
  imputation by class, thresholds chosen on results) must be fitted inside each training fold.
  `parcel_group_cv.py` fills missing values with a column median over all rows, which uses no
  label and is fold-independent; anything supervised belongs in the model pipeline.
- **Labels mixed within a parcel.** `parcel_table()` raises when one parcel carries two labels,
  which usually reveals a join on the wrong key.

## Reporting checklist

1. Number of parcels per class, and pixels per parcel (median and range).
2. Split used (leave one parcel out or grouped k-fold) and the group variable.
3. Parcel-level AUC, its permutation p-value, and the leaky pixel-split AUC for contrast.
4. Negative-control AUC on a pre-sowing or pre-symptom window.
5. Spread over seeds for stochastic models.
6. What the label is (field score threshold, date of observation) and who observed it.
