# Datamol core workflows (0.13.0)

These local snippets were executed with Python 3.13 / RDKit 2026.03.6. Run the setup
first. Each step preserves the relationship between input structures and outputs.
Use [the pipeline patterns](workflow_patterns.md) for rejected-row and selection provenance.

## 1. Molecules and explicit structure policy

```python
import datamol as dm
import numpy as np
import pandas as pd
from pathlib import Path
from tempfile import TemporaryDirectory

smiles_list = ["CCO", "CCCO", "c1ccccc1O", "c1ccccc1CCN", "c1ccncc1", "CC(=O)O"]
mols = [dm.to_mol(s) for s in smiles_list]
assert all(m is not None for m in mols)
with dm.without_rdkit_log():
    invalid = dm.to_mol("invalid_smiles")
assert invalid is None
mol = mols[0]  # keep a valid molecule for subsequent examples
smiles = dm.to_smiles(mol, canonical=True, isomeric=True)
inchi, inchikey, selfies = dm.to_inchi(mol), dm.to_inchikey(mol), dm.to_selfies(mol)
assert dm.from_selfies(selfies, as_mol=True) is not None
# Illustrative, deliberately specified policy for these ordinary organic molecules.
standardized = dm.standardize_mol(mol, disconnect_metals=False, normalize=True,
                                  reionize=True, uncharge=False, stereo=True)
assert standardized is not None
```

Choose the policy from the assayed entity before standardizing. Preserve source structures;
metal disconnection, salt/fragment selection and neutralization are not universally appropriate.
Sanitization/fixing is not evidence that an invalid source structure has been recovered.

## 2. Local I/O and portable tables

```python
with TemporaryDirectory() as directory:
    base = Path(directory)
    dm.to_sdf(mols, base / "compounds.sdf")
    df = dm.read_sdf(base / "compounds.sdf", as_df=True, mol_column="mol",
                     discard_invalid=False)
    assert len(df) == len(mols)
    dm.to_smi(mols, base / "molecules.smi", error_if_empty=True)
    assert len(dm.read_smi(base / "molecules.smi")) == len(mols)
    dm.to_xlsx(df, base / "compounds.xlsx", mol_column="mol")
    portable = df.drop(columns="mol")
    dm.save_df(portable, str(base / "compounds.parquet"))
    assert len(dm.open_df(str(base / "compounds.parquet"))) == len(mols)
```

`read_sdf` returns a list unless `as_df=True`; `open_df` selects DataFrame mode for SDF.
Do not serialize Python Mol objects into Parquet/CSV. Use SMILES plus scalar properties
and reconstruct on read. See [I/O contracts](io_module.md) for rejection handling,
file-format parameters, and illustrative cloud paths. Remote credentials/writes were not tested.

## 3. Descriptors with an explicit feature schema

```python
properties = {"mw": "MolWt", "logp": "MolLogP", "hbd": "NumHDonors",
              "hba": "NumHAcceptors", "tpsa": "TPSA"}
desc_df = dm.descriptors.batch_compute_many_descriptors(
    mols, properties_fn=properties, add_properties=False, n_jobs=1,
)
passes_screen = ((desc_df["mw"] <= 500) & (desc_df["logp"] <= 5)
                 & (desc_df["hbd"] <= 5) & (desc_df["hba"] <= 10))
selected = [m for m, keep in zip(mols, passes_screen) if keep]
assert len(desc_df) == len(mols)
n_aromatic = dm.descriptors.n_aromatic_atoms(mol)
n_stereo = dm.descriptors.n_stereo_centers(mol)
n_unspecified = dm.descriptors.n_stereo_centers_unspecified(mol)
n_rigid = dm.descriptors.n_rigid_bonds(mol)
```

This defines average MolWt and RDKit donor/acceptor counts. Datamol defaults instead use
exact mass (`mw`), `clogp`, `n_lipinski_hbd`, and `n_lipinski_hba`. See
[descriptor semantics](descriptors_viz.md). Screen passage is not validated drug-likeness.

## 4. Fingerprints and similarities

```python
fp_options = dict(fp_type="ecfp", radius=2, fpSize=2048, includeChirality=True)
fps = np.stack([dm.to_fp(m, **fp_options) for m in mols])
distance_matrix = dm.pdist(mols, n_jobs=1, **fp_options)  # square by default
query_distances = dm.cdist(mols[:1], mols, n_jobs=1, **fp_options)
nearest = np.argsort(query_distances[0])
assert nearest[0] == 0 and np.isclose(query_distances[0, 0], 0)
for fp_type in ["maccs", "topological", "atompair", "rdkit"]:
    assert dm.to_fp(mol, fp_type=fp_type).ndim == 1
```

ECFP radius 2 is ECFP4; Datamol defaults to radius 3. Use `fpSize`, not `n_bits`.
`pdist(..., squareform=False)` returns condensed distances; calling SciPy `squareform`
on the default square output would convert it into a vector. Binary Tanimoto similarity
is 1 - distance. Compare libraries only with the same fingerprint configuration.

## 5. Clustering and diversity

```python
from functools import partial
feature_fn = partial(dm.to_fp, as_array=False, **fp_options)
cluster_indices, cluster_molecules = dm.cluster_mols(mols, cutoff=0.2, feature_fn=feature_fn)
for indices, molecules in zip(cluster_indices, cluster_molecules):
    assert len(indices) == len(molecules)
picked_indices, diverse_mols = dm.pick_diverse(mols, npick=min(3, len(mols)),
                                              feature_fn=feature_fn, seed=42)
centroid_indices, centroid_mols = dm.pick_centroids(mols, npick=3, feature_fn=feature_fn)
```

Both selectors return `(indices, molecules)`; preserve indices for labels/IDs. Butina needs
quadratic distance storage. Select a resource budget, not a universal molecule-count cutoff.
The sphere centroid selector may return fewer than requested due to its distance threshold.

## 6. Scaffolds and a toy scaffold-disjoint split

```python
from collections import defaultdict
import random
scaffold_groups = defaultdict(list)
for index, molecule in enumerate(mols):
    key = dm.to_smiles(dm.to_scaffold_murcko(molecule))
    scaffold_groups[key].append(index)
keys = sorted(scaffold_groups)
random.Random(42).shuffle(keys)
split_index = int(0.8 * len(keys))
train_keys, test_keys = keys[:split_index], keys[split_index:]
train_indices = [i for key in train_keys for i in scaffold_groups[key]]
test_indices = [i for key in test_keys for i in scaffold_groups[key]]
assert set(train_keys).isdisjoint(test_keys)
assert set(train_indices).isdisjoint(test_indices)
```

This divides scaffold groups, not exactly 80% of molecules. All acyclic molecules share an
empty Murcko scaffold here; report that policy and inspect resulting class/size balance.
Validate chemical duplicate/analog and task-specific leakage separately.

## 7. Fragmentation

```python
from collections import Counter
fragment_counts = Counter()
for molecule in mols:
    fragments = dm.fragment.brics(molecule, remove_parent=True, fix=False)
    fragment_counts.update({dm.to_smiles(f) for f in fragments})
recap_fragments = dm.fragment.recap(mol, remove_parent=True, fix=False)
```

These functions return lists of Mol. Canonicalize to strings before set overlap/counting;
otherwise Python object identity can silently corrupt counts. This counts compound prevalence,
not repeated fragment sites. See [fragment contracts](fragments_scaffolds.md).

## 8. Conformers

```python
mol_3d = dm.conformers.generate(dm.to_mol("CC(C)CCO"), n_confs=10, rms_cutoff=0.5,
                                minimize_energy=True, forcefield="UFF", random_seed=19)
assert mol_3d.GetNumConformers() > 0
coords = dm.conformers.get_coords(mol_3d)
cluster_molecules_3d = dm.conformers.cluster(mol_3d, rms_cutoff=1.0, centroids=False)
centroid_molecule_3d = dm.conformers.cluster(mol_3d, rms_cutoff=1.0, centroids=True)
# SASA is supported on this tested macOS stack; Datamol disables it on Windows.
sasa_values = dm.conformers.sasa(mol_3d, n_jobs=1)
```

Generation defaults to no minimization; this example enables it explicitly. Conformer
clustering returns Mol objects, not index tuples. See [conformer contracts](conformers_module.md)
for symmetry-aware RMS, finite-energy versus convergence checks, units and property storage.

## 9. Visualize

```python
with TemporaryDirectory() as directory:
    dm.viz.to_image(diverse_mols, legends=[str(i) for i in picked_indices],
                     n_cols=3, use_svg=False, outfile=str(Path(directory) / "diverse.png"))
    dm.viz.to_image(mols, use_svg=True, outfile=str(Path(directory) / "molecules.svg"))
    dm.viz.to_image(mols[0], highlight_atom=[0, 1, 2], highlight_bond=[0, 1])
```

The default is SVG, so set `use_svg=False` for PNG. Use `align=True` for related series
or an explicit common template. Interactive `dm.viz.conformers(mol_3d, n_confs=None)`
needs a notebook frontend; only widget construction was checked locally.

## 10. Reaction enumeration

```python
from rdkit.Chem import rdChemReactions
rxn = rdChemReactions.ReactionFromSmarts("[C:1](=[O:2])[OH:3]>>[C:1](=[O:2])[Cl:3]")
groups = dm.reactions.apply_reaction(rxn, (dm.to_mol("CC(=O)O"),))
products = [p for group in groups for p in group if p is not None]
assert {dm.to_smiles(p) for p in products} == {"CC(=O)Cl"}
```

Default output is nested product groups. Empty matches and invalid products are separate
outcomes. SMARTS application/sanitization does not demonstrate a feasible synthesis;
see [reaction and dataset patterns](reactions_data.md).
