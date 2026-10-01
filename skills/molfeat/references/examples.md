# Worked Molfeat 1.0 examples

These small CPU examples use Molfeat 1.0.0 with datamol 0.13.0. They are covered by
local smoke tests. Dataset-scale workflows are illustrative and need project data.

## Preprocess explicitly and retain IDs

`preprocess()` is not an automatically invoked transformation hook. Apply a chosen
standardization policy explicitly; the example below normalizes molecules without
asserting that all salts, tautomers, or protonation states should be collapsed.

```python
import datamol as dm
import numpy as np
from molfeat.calc import FPCalculator
from molfeat.trans import MoleculeTransformer

rows = [("a", "CCO"), ("bad", "invalid"), ("b", "CC(=O)O")]
accepted, rejected = [], []
for record_id, smiles in rows:
    mol = dm.to_mol(smiles)
    if mol is None or mol.GetNumAtoms() == 0:
        rejected.append(record_id)
        continue
    mol = dm.standardize_mol(mol)
    accepted.append((record_id, mol))

transformer = MoleculeTransformer(
    FPCalculator("ecfp", radius=2, fpSize=2048), dtype=np.float32,
)
X = transformer([mol for _, mol in accepted])  # strict: catch unexpected failures
assert X.shape == (2, 2048)
assert [record_id for record_id, _ in accepted] == ["a", "b"]
assert rejected == ["bad"]
```

For real data retain original SMILES and the standardized form with each ID. Confirm
whether mixtures and protonation variants are distinct assay records before removing
fragments. Enforce the same policy in validation and deployment.

## Concatenate and persist

```python
import numpy as np
from molfeat.trans import FeatConcat, MoleculeTransformer
from molfeat.trans.fp import FPVecTransformer

parts = [FPVecTransformer("maccs"), FPVecTransformer("ecfp:4", length=2048)]
combined = FeatConcat(parts, dtype=np.float32)
smiles = ["CCO", "c1ccccc1"]
X = combined(smiles, enforce_dtype=True)
assert X.shape == (2, 2215)

# Save each component state; FeatConcat is a container, not a calculator.
for i, part in enumerate(parts):
    part.to_state_json_file(f"component_{i}.json")
restored = FeatConcat([
    MoleculeTransformer.from_state_json_file(f"component_{i}.json")
    for i in range(len(parts))
])
np.testing.assert_array_equal(restored(smiles), X)
```

Use strict calls after common validation. See the API reference for the 1.0
`FeatConcat(ignore_errors=True)` row-alignment limitation.

## Named and pharmacophore descriptors

```python
import numpy as np
from molfeat.calc import CATS, RDKitDescriptors2D, Pharmacophore2D

rdkit_2d = RDKitDescriptors2D()
values = rdkit_2d("CCO")
assert len(values) == len(rdkit_2d.columns)
nonfinite_names = np.asarray(rdkit_2d.columns)[~np.isfinite(values)]

cats = CATS(use_3d_distances=False, scale="raw")
assert cats("CCO").shape == (189,)
gobbi = Pharmacophore2D(factory="gobbi", length=2048)
assert gobbi("c1ccccc1O").shape == (2048,)
```

Do not replace all undefined descriptors with zero without documenting why that is
scientifically meaningful. Fit imputation/column selection on the training fold and
record the final ordered column list. Optional `MordredDescriptors` defaults to 2D;
install `molfeat[mordred]` to use it, and inspect missing values separately.

## Generate and check one 3D conformer

```python
import datamol as dm
import numpy as np
from molfeat.calc import RDKitDescriptors3D, USRDescriptors, CATS

mol = dm.conformers.generate(
    dm.to_mol("CCCO"), n_confs=1, random_seed=42,
    minimize_energy=True, num_threads=1,
)
assert mol is not None and mol.GetNumConformers() == 1
shape = USRDescriptors("USR")(mol)
assert shape.shape == (12,) and np.isfinite(shape).all()
rdkit_3d = RDKitDescriptors3D()(mol)
cats_3d = CATS(use_3d_distances=True)(mol)
assert cats_3d.shape == (126,)
```

The current datamol API is `dm.conformers.generate`, not
`dm.conform.generate_conformers`. One conformer is a smoke test, not a representative
conformational ensemble. For a scientific study record sampling, protonation,
force field, minimization/convergence, coordinates, conformer IDs, and the rule for
aggregating conformer descriptors. Plain SMILES contain no 3D coordinates.

## Binary Tanimoto similarity

```python
import numpy as np
from rdkit import DataStructs
from molfeat.calc import FPCalculator

calc = FPCalculator("ecfp", radius=2, fpSize=2048, includeChirality=True)
query = calc("CCO", raw=True)
library = ["CCO", "CCCO", "c1ccccc1"]
fingerprints = [calc(s, raw=True) for s in library]
scores = np.array(DataStructs.BulkTanimotoSimilarity(query, fingerprints))
assert scores[0] == 1.0
ranked_positions = np.argsort(-scores, kind="stable")
```

Use the same fingerprint configuration for query and reference compounds. Binary
Tanimoto, count-vector similarity, cosine on embeddings, and distances on scaled
continuous descriptors encode different assumptions; do not interchange their
thresholds. Shape descriptors need their own appropriate metric.

## Cache identity and large batches

A single `embeddings_cache.npz` filename is insufficient provenance. Save numeric
features with input IDs and a manifest containing standardized input identity,
configuration/state, model revision/tokenizer/pooling/max length, package versions,
and row order. Validate the manifest before reuse. Load numeric arrays with
`allow_pickle=False`. For large datasets, write each chunk or score it immediately;
retaining all chunks before stacking does not bound total memory.
