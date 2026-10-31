# Worked ESM workflows

These recipes target `esm==3.4.1.post1`. Pretrained generation and folding remain
illustrative; tiny random-model embedding behavior and synthetic downstream
analysis were executed. Scientific quality requires task-specific evaluation.

## Variant library with preserved constraints

Start from an identified parent and an explicit set of mutable positions. This
example takes a loaded ESM3 `model` and a real `parent_sequence`; positions are
**0-based Python indices**. A sampled position need not change amino acid, so
record realized changes as well as masks. The local seed below controls mask
selection only; it does not seed the hosted model.

```python
import random
from esm.sdk.api import ESMProtein, ESMProteinError, GenerationConfig

rng = random.Random(17)
mutable_positions = list(range(len(parent_sequence)))  # Exclude fixed sites first.
variants = {}
for attempt in range(20):
    positions = rng.sample(mutable_positions, k=min(3, len(mutable_positions)))
    if not positions:
        raise ValueError("No mutable positions")
    prompt = list(parent_sequence)
    for position in positions:
        prompt[position] = "_"
    prompt = "".join(prompt)
    result = model.generate(ESMProtein(sequence=prompt), GenerationConfig(
        track="sequence", num_steps=min(20, len(positions)), temperature=0.7,
    ))
    if isinstance(result, ESMProteinError):
        raise result
    sequence = result.sequence
    if sequence is None or len(sequence) != len(parent_sequence) or "_" in sequence:
        raise ValueError("Incomplete or wrong-length generation")
    if any(a != "_" and a != b for a, b in zip(prompt, sequence)):
        raise ValueError("Generation changed a fixed residue")
    changes = [i for i, (a, b) in enumerate(zip(parent_sequence, sequence)) if a != b]
    if changes and sequence not in variants:
        variants[sequence] = {"attempt": attempt, "masks": positions, "changes": changes}
```

Deduplicate, retain candidate IDs and rejected attempts, and avoid claiming 20
attempts yield 20 distinct variants. For a GFP project, use an experimentally
annotated parent and mapped essential residues: a word such as
`green_fluorescent_protein` or a chosen range does not enforce chromophore
chemistry. Function prompts require the model's actual vocabulary.

## Structure-conditioned design and screening

Use the inverse-folding recipe in `esm3-api.md` with an explicit PDB chain and
cloned coordinates. For each candidate:

1. Confirm length, fixed residues, alphabet, chain mapping and absence of masks.
2. Predict again from a **sequence-only** input. Retaining target coordinates
   conditions the result and prevents a meaningful round-trip check.
3. Compare matching finite atoms after superposition. Report residue coverage,
   missing regions, structural deviations and model confidence together.
4. Prioritize designs using a specified, validated assay model or experimental
   protocol. Increasing total hydrophobic fraction is not a valid generic
   stability objective; it can promote aggregation or harm solubility.
5. Save candidate sequences as valid FASTA (headers and sequence lines only);
   put properties, parent IDs, mutations, seeds and model settings in JSON/TSV.

Coordinate existence is a software-success check, not biological validation.
Neither confidence nor same-model structure agreement establishes improved
stability, preserved catalytic function or experimental success. Keep candidate
selection criteria explicit and plan the relevant wet-lab assay.

## Embedding clustering and representative selection

Compute residue-only features using `embed_sequences` from
`scripts/esm_embeddings.py`, in memory-bounded batches. Keep a parallel list of
unique input IDs; do not use an embedding-only cache across model revisions.
The following consumes a real `(N,D)` finite feature matrix. Synthetic vectors
were used to validate its small-dataset behavior, not biological clusters.

```python
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

X = np.asarray(embeddings, dtype=float)
if X.ndim != 2 or len(X) < 2 or X.shape[1] == 0 or not np.isfinite(X).all():
    raise ValueError("Need at least two finite, nonempty embedding vectors")
if np.any(np.linalg.norm(X, axis=1) == 0):
    raise ValueError("Zero embeddings cannot be used for cosine-style comparison")
X = normalize(X)
unique_count = len(np.unique(X, axis=0))
n_clusters = min(5, len(X), unique_count)
clusterer = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit(X)
labels = clusterer.labels_
representative_indices = []
for label in np.unique(labels):
    indices = np.flatnonzero(labels == label)
    distances = np.linalg.norm(X[indices] - clusterer.cluster_centers_[label], axis=1)
    representative_indices.append(int(indices[np.argmin(distances)]))

# Exploratory coordinates; cluster in the defined feature space, not in t-SNE.
components = min(2, len(X) - 1, X.shape[1])
projection = PCA(n_components=components).fit_transform(X)
```

The representative indices refer to the original input order. Choose clustering
settings using task-specific stability checks and biological controls; automatic
`min(5,...)` is a runnable illustration, not a scientifically chosen cluster
count. A one-component projection needs a one-dimensional plot. If using t-SNE,
require `perplexity < N`, record settings and seed, and avoid interpreting visual
separation as evidence of separate functions.

## Function prediction with embeddings

For a supervised task, curate labels and split homologous sequence groups into
train/validation/test before fitting a classifier. Fit scalers, PCA, feature
selection and hyperparameters on training/validation data only; retain an
independent test set. Report class balance and suitable metrics/calibration,
not accuracy alone on an arbitrary random split. A pretrained-model benchmark
also needs an explicit policy for training-set homology and historical leakage.

ESM3 function annotations are model hypotheses; compare them with experimentally
supported annotations and assess false positives. Low sampling temperature does
not turn them into calibrated probabilities. Do not assign names such as
"kinase" to arbitrary toy sequences and use those as evaluation truth.

## Reproducibility record

Save input identifiers, exact sequences and hashes, selected chain/residue maps,
model/checkpoint revision or hosted ID, SDK version, mask positions, generated
candidates, confidence outputs, settings and all applicable seeds. Define whether
a reported result is synthetic code verification, pretrained inference, or
experimental validation. Retain errors without presenting failed records as
completed predictions.

Sources: [ESM3 generation example](https://github.com/Biohub/esm/blob/main/_assets/ESM3_README.md),
[ESMC interface](https://github.com/Biohub/esm/blob/main/esm/models/esmc/model.py),
[scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html),
[PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html),
[KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html).
