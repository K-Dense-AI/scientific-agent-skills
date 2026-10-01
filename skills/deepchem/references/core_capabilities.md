# Core molecular workflow

Targets released DeepChem 2.8.0. Executed CPU contracts and backend limitations are
listed in [review.md](review.md). External data and pretrained-weight examples are
illustrative unless the review explicitly says they ran.

1. **Define the target.** Record assay, units, measurement conditions, structure
   standardization, compound identity and missing-label convention. For solubility,
   pH, temperature and salt form can change the outcome; a benchmark prediction
   does not establish those conditions for a new sample.
2. **Validate input.** Parse structures, audit failures and duplicate compounds,
   preserve `X/y/w/ids` alignment and observed counts. The shipped CSV guard rejects
   duplicate raw headers, bad labels, bad SMILES and featurization row loss.
3. **Choose representation.** Start with fingerprints plus a numeric baseline;
   compare graph or pretrained encoders only using compatible features. Dataset
   size alone does not establish that a neural architecture will perform better.
4. **Split before learning transformations.** A scaffold holdout asks about new
   scaffolds, a temporal holdout about future measurements, and a grouped holdout
   about new groups. Check that the chosen split matches the actual question.
5. **Fit on training data.** Learn target scaling from training data only.
   `dataset.w == 0` excludes missing labels only if the selected loss respects it.
6. **Select on validation data.** Tune architecture, epochs and thresholds here.
   The bundled fixed-epoch scripts report validation results but do not implement
   early stopping or select the best checkpoint automatically.
7. **Evaluate once on the holdout.** Report class support, per-task metrics, macro
   aggregation and variability across prespecified repeats, plus a baseline.
8. **Predict with the same representation.** Apply the saved training transforms
   and invert target transforms for original-unit predictions. Retain IDs and
   flag out-of-domain molecules; a point prediction is not a calibrated interval.

## Numeric baseline (self-contained CPU example)

These are synthetic labels for interface verification, not measured solubilities.
The split is explicitly by index only to exercise fit/predict in a tiny fixture;
use a scientifically appropriate grouped holdout for real research.

```python
import deepchem as dc
import numpy as np
from sklearn.ensemble import RandomForestRegressor

smiles = ['CCO', 'CCC', 'CCN', 'CCCl', 'c1ccccc1', 'c1ccncc1']
features = dc.feat.CircularFingerprint(size=2048).featurize(smiles)
data = dc.data.NumpyDataset(features, np.arange(6, dtype=float)[:, None], ids=smiles)
train = data.select([0, 1, 2, 3])
test = data.select([4, 5])
model = dc.models.SklearnModel(RandomForestRegressor(n_estimators=8, random_state=7))
model.fit(train)
prediction = model.predict(test)
assert prediction.shape == (2,)
assert np.isfinite(prediction).all()
```

## Graph and sequence branches

The graph mapping in [api_reference.md](api_reference.md) is mandatory: legacy
`ConvMol`, generic `GraphData`, DMPNN graphs and GROVER graphs are different inputs.
AttentiveFP and Torch MPNN require bond features. GROVER's featurizer is not a
pretrained model. Protein language models need their model-specific residue
alphabet/tokenization and labels, and homolog-aware evaluation; molecule scaffold
splits do not apply to proteins.

A pretrained encoder may help or hurt a small dataset. Check training-corpus
contamination and domain coverage, use a compatible prediction head, and compare
with a from-scratch baseline. A model's successful download does not demonstrate
successful transfer or scientific generalization.
