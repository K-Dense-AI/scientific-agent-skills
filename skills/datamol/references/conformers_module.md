# Datamol conformers (0.13.0)

Checked against [the conformer API](https://docs.datamol.io/stable/api/datamol.conformers.html)
and released source. Coordinates are in angstrom; SASA is in square angstrom.

## Generate and validate

`dm.conformers.generate` defaults to `minimize_energy=False`, `forcefield="UFF"`,
`method=None` (selects ETKDGv3), `random_seed=19`, `num_threads=1`, and `add_hs=True`.
Hydrogens are added for embedding and removed from the returned molecule. Do not assume
explicit hydrogens survive. With `n_confs=None`, the requested count depends on rotatable
bonds. Requested counts are upper targets, not guaranteed surviving counts.

```python
import datamol as dm
import numpy as np
mol = dm.to_mol("CC(C)CCO")  # 3-methylbutan-1-ol
mol.SetProp("source_id", "compound-001")
mol_3d = dm.conformers.generate(
    mol, n_confs=10, rms_cutoff=0.5, minimize_energy=True,
    method="ETKDGv3", forcefield="UFF", random_seed=19, num_threads=1,
)
assert mol_3d is not None and mol_3d.GetNumConformers() > 0
coords = dm.conformers.get_coords(mol_3d)
assert coords.shape == (mol_3d.GetNumAtoms(), 3) and np.isfinite(coords).all()
energies = [c.GetDoubleProp("rdkit_UFF_energy") for c in mol_3d.GetConformers()]
assert np.isfinite(energies).all()
```

Other embedding methods are ETDG, ETKDG and ETKDGv2. Available forcefield choices are
UFF, MMFF94s and MMFF94s_noEstat. Check parameter coverage and convergence; finite energies
are not proof of converged minima, equilibrium populations, or bioactive conformations.
Set `verbose=True, warning_not_converged=1` when minimization diagnostics matter.
Embedding failure raises unless `ignore_failure=True`, which can return `None`.

0.13 uses optimal symmetry-aware alignment for RMS pruning. `rms_cutoff` is applied after
minimization when enabled; larger thresholds generally keep fewer representatives. A seed
supports reproducibility within a pinned environment, not identical output across RDKit releases.

## Cluster output is molecular

```python
for conformer in mol_3d.GetConformers():
    conformer.SetIntProp("source_conformer_id", conformer.GetId())
cluster_molecules = dm.conformers.cluster(mol_3d, rms_cutoff=1.0, centroids=False)
centroid_molecule = dm.conformers.cluster(mol_3d, rms_cutoff=1.0, centroids=True)
assert sum(m.GetNumConformers() for m in cluster_molecules) == mol_3d.GetNumConformers()
assert centroid_molecule.GetNumConformers() == len(cluster_molecules)
assert centroid_molecule.GetProp("source_id") == "compound-001"
selected_source_ids = [c.GetIntProp("source_conformer_id") for c in centroid_molecule.GetConformers()]
```

Clustering assigns new conformer IDs. Keep a per-conformer source-ID property as above
when linking selected conformers to energies or upstream metadata.

`centroids=True` is the default: one Mol containing representative conformers. False
returns a list of Mol, one per cluster, containing every cluster member. It does **not**
return index tuples. `dm.conformers.return_centroids(mol, conf_clusters)` is a lower-level
helper for precomputed integer index groups, not the output of `cluster`; its default path
mutates the supplied molecule. Prefer `cluster`, which copies the input.
`already_aligned=True` uses distances in the existing common frame instead of optimal
pairwise alignment. `dm.conformers.rmsd(mol, num_threads=1)` returns a square RMSD array.

## SASA and coordinates

```python
# Serial execution also stores properties on the original conformers.
sasa_values = dm.conformers.sasa(mol_3d, n_jobs=1)
assert len(sasa_values) == mol_3d.GetNumConformers()
assert np.isfinite(sasa_values).all()
assert mol_3d.GetConformer(0).HasProp("rdkit_free_sasa")
center = dm.conformers.center_of_mass(mol_3d, use_atoms=True, digits=4)
moved = dm.copy_mol(mol_3d)
dm.conformers.translate(moved, new_centroid=np.zeros(3), conf_id=0)
```

SASA uses RDKit FreeSASA with van der Waals radii. Datamol disables it on Windows.
Supply existing conformer IDs when using `conf_id`; generated conformers have contiguous
IDs, but arbitrary imported IDs need explicit handling. Parallel workers can return values
without propagating per-conformer property mutation back to the parent; use returned values.
`get_coords(mol, conf_id=-1)` returns an atom-by-3 array; `-1` selects the default conformer.
`center_of_mass(..., use_atoms=False)` computes the geometric center of represented atoms;
`digits` controls rounding. `translate(mol, new_centroid, conf_id=-1)` moves the conformer
in place to the new RDKit centroid; it does not accept a transformation matrix.
