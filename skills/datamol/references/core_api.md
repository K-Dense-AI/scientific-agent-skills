# Datamol core API (0.13.0)

The [current API](https://docs.datamol.io/stable/api/datamol.mol.html) and installed
0.13.0 source were checked. These are call patterns, not exhaustive signatures.

## Conversion and identity

- `dm.to_mol(smiles)` accepts SMILES/CXSMILES, an existing Mol, or RDKit binary bytes.
  It does not auto-detect InChI or arbitrary formats. Parsing failures can return `None`;
  unsupported argument types can raise. Check the result before every downstream step.
- `dm.from_inchi(inchi)` and `dm.from_smarts(smarts)` return Mol or `None`.
- `dm.from_selfies(text)` returns a SMILES string by default; use `as_mol=True` for Mol.
- `dm.copy_mol(mol)` creates a copy. `dm.to_binary(mol)` handles one molecule; `dm.to_dict([mol])` and
  `dm.from_dict(payload)` serialize/restore a sequence of molecules through RDKit JSON. They support interchange; record RDKit version with persisted data.
- `dm.to_smiles(mol, canonical=True, isomeric=True)` retains specified stereochemistry.
  `dm.to_inchi`, `dm.to_inchikey`, `dm.to_smarts`, and `dm.to_selfies` are separate exports.
- `dm.hash_mol(mol, hash_scheme="all")` supports `all`, `no_stereo`, and `no_tautomers`.
  Choose the identity policy deliberately; collapsing stereoisomers or tautomers can
  merge biologically distinct records.
- `dm.reorder_atoms(mol)` changes atom indices. Store mappings before combining reordered
  structures with atom-indexed labels. `dm.add_hs`/`dm.remove_hs` also change atom topology.

## Sanitization and standardization

`dm.sanitize_mol(mol, charge_neutral=False)` attempts a sanitization round trip and can
return `None`. `dm.fix_mol`, `dm.fix_valence`, and `dm.fix_valence_charge` change structures
heuristically; a successful return does not establish that the original chemistry was recovered.

`dm.standardize_mol(mol, disconnect_metals=False, normalize=True, reionize=True,
uncharge=False, stereo=True)` returns a standardized molecule. It does not select the
largest fragment. Preserve source SMILES and identifiers; explicitly decide salt, charge,
metal, isotope and stereochemistry policy. `dm.standardize_smiles(smiles)` accepts no
policy keyword arguments in 0.13.0; use the molecule API for explicit choices.

## Fingerprints and distances

```python
import datamol as dm
import numpy as np
mols = [dm.to_mol(s) for s in ["CCO", "CCCO", "c1ccccc1"]]
fp = dm.to_fp(mols[0], fp_type="ecfp", radius=2, fpSize=2048)
assert fp.shape == (2048,)
distances = dm.pdist(mols, radius=2, fpSize=2048)  # square N x N by default
condensed = dm.pdist(mols, squareform=False, radius=2, fpSize=2048)
cross = dm.cdist(mols[:1], mols, radius=2, fpSize=2048)  # 1 x N
assert distances.shape == (3, 3) and condensed.shape == (3,)
assert np.allclose(np.diag(distances), 0)
```

ECFP defaults to radius 3 (ECFP6); FCFP defaults to radius 2. Generator fingerprints
use `fpSize`, not `n_bits`. Use `includeChirality=True` if stereochemistry should affect
similarity, and use identical options for every query/library operation. `as_array=False`
returns the RDKit fingerprint. `topological` means topological torsions; `rdkit` is the
RDKit path fingerprint. MACCS has its own fixed size (167); it does not accept `fpSize`.
Count variants include `ecfp-count`, `fcfp-count`, `atompair-count`, `topological-count`,
and `rdkit-count`. The similarity helpers compute binary Jaccard/Tanimoto distances;
do not use them to imply a count-vector Tanimoto metric. Lower distance means higher
similarity, with similarity = 1 - distance for the binary fingerprints used here.

## Clusters and selections

```python
cluster_indices, cluster_molecules = dm.cluster_mols(mols, cutoff=0.2)
picked_indices, picked_molecules = dm.pick_diverse(mols, npick=min(2, len(mols)), seed=42)
centroid_indices, centroid_molecules = dm.pick_centroids(mols, npick=2, method="sphere")
assert len(picked_indices) == len(picked_molecules) == 2
```

All three return two components. Cluster indices are groups of source positions; selection
indices address the original list. Retain these indices to preserve labels/IDs. `pick_centroids`
is a distance-based representative selector; the default sphere method may return fewer
than `npick` due to its threshold. It is not a geometric mean. Butina stores a quadratic
pairwise-distance list; no universal safe molecule count applies. Bound resources before
clustering. `pick_diverse` avoids storing the full pairwise matrix but is still work-dependent.

## Graphs and tables

`dm.to_graph(mol)` creates a NetworkX graph; `dm.get_all_path_between(mol, atom1, atom2)`
can grow combinatorially on ring-rich graphs. `dm.to_df(mols, mol_column="mol")` includes
molecules explicitly (the default is `None`). `dm.from_df(df, mol_column="mol")` returns
one molecule per row, attaching other columns as molecule properties; handle invalid rows.
