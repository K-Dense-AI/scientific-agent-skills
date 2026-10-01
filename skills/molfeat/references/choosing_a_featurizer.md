# Choosing representations and evaluating molecular models

Start with ECFP and a simple estimator. Choose descriptors for interpretability,
pharmacophores for a stated interaction hypothesis, and 3D features only when the
conformer protocol is justified. Pretrained embeddings are candidates to evaluate;
model size or pretraining volume does not establish task performance.

Use identical splits, assay endpoints, and molecule policies across representations.
Keep close analogues, duplicate structures, and repeated measurements together when
they would otherwise leak information. A scaffold split is useful for testing novel
cores; temporal splitting may better approximate future screening. Record which
scientific generalization question the split addresses.

## Toy grouped QSAR pipeline

Executed on synthetic data to check API behavior only; its score has no scientific
meaning. Replace inputs, labels, and group assignments with curated assay records.
All preprocessing that learns from data stays inside the cross-validation pipeline.

```python
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, cross_val_score
from molfeat.calc import RDKitDescriptors2D
from molfeat.trans import MoleculeTransformer

smiles = ["CCO", "CCCO", "CCCCO", "CCCCCO",
          "CCN", "CCCN", "CCCCN", "CCCCCN"]
y = np.arange(8, dtype=float)  # artificial labels
groups = np.array([0, 0, 1, 1, 2, 2, 3, 3])  # artificial groups
pipeline = Pipeline([
    ("features", MoleculeTransformer(RDKitDescriptors2D(), dtype=np.float64)),
    ("impute", SimpleImputer(strategy="median")),
    ("scale", StandardScaler()),
    ("regress", Ridge(alpha=1.0)),
])
scores = cross_val_score(
    pipeline, smiles, y, groups=groups, cv=GroupKFold(4),
    scoring="neg_mean_absolute_error", error_score="raise",
)
assert np.isfinite(scores).all()
```

Validate molecular inputs before splitting while preserving labels/IDs. Do not drop
rows inside a scikit-learn transformer without also handling the target vector.
`MoleculeTransformer.fit` can remove training columns containing NaN; keep feature
names after fitting. Imputers do not automatically handle Inf, and missing validation
descriptors still need a declared policy. Tune representations/hyperparameters in an
inner split and reserve an untouched evaluation set.

Classification requires class-aware metrics and sufficient positive/negative examples
in each fold. ROC AUC alone can obscure poor precision in sparse screening libraries;
report PR metrics and enrichment at a prespecified screening budget when applicable.
Confirm activity units, assay comparability, censoring, and target transforms before
regression; raw IC50 values are not interchangeable with pIC50.

## Bounded-memory virtual screening

Illustrative: `classifier` is fitted and its training featurizer is supplied. Invalid
inputs must be reported, and output rows carry their original positions. This example
retains only a chunk's feature matrix and immediately emits scores.

```python
import numpy as np

def scored_chunks(smiles, transformer, classifier, active_label=1, chunk_size=1000):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    matches = np.flatnonzero(np.asarray(classifier.classes_) == active_label)
    if len(matches) != 1:
        raise ValueError("active_label must identify one fitted classifier class")
    column = int(matches[0])
    for start in range(0, len(smiles), chunk_size):
        chunk = smiles[start:start + chunk_size]
        X, valid_ids = transformer(chunk, ignore_errors=True)
        rejected = sorted(set(range(len(chunk))) - set(valid_ids))
        original_positions = np.asarray(valid_ids, dtype=int) + start
        if len(valid_ids):
            if not np.isfinite(X).all():
                raise ValueError("nonfinite screening features require an explicit policy")
            probabilities = classifier.predict_proba(X)[:, column]
        else:
            probabilities = np.empty(0)
        yield original_positions, probabilities, [start + i for i in rejected]
```

Write results per chunk, or maintain a bounded top-k heap. Avoid featurizing a million
molecules at once or accumulating every chunk before `vstack`. A probability from an
uncalibrated classifier is a ranking score, not established biological confidence.
Check chemical applicability and validate prioritized compounds experimentally.

## Compare featurizers without mixing interfaces

Use `MoleculeTransformer(FPCalculator(...))` for a calculator, `FeatConcat` directly
for an `FPVecTransformer` container, and `PretrainedHFTransformer` directly for
embeddings. Wrapping either of the latter as a single-molecule calculator changes the
expected batch interface. Fix seeds and use paired evaluation on the same folds.
See [API contracts](api_reference.md) and [examples](examples.md) for executable patterns.
