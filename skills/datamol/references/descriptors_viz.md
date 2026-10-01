# Datamol descriptors and visualization (0.13.0)

Sources: [descriptors API](https://docs.datamol.io/stable/api/datamol.descriptors.html),
[visualization API](https://docs.datamol.io/stable/api/datamol.viz.html), and released source.

## Default descriptors versus explicit screening properties

`compute_many_descriptors(mol)` returns a dict; the batch variant returns a fresh
RangeIndex DataFrame with one row per molecule. Preserve the input row mapping before
joining. Defaults include `mw` (exact molecular mass), `clogp`, `n_lipinski_hbd`,
`n_lipinski_hba`, `tpsa`, `qed`, `sas`, and ring/count descriptors. They do not include
`logp`, `hbd`, or `hba`. The 0.13 keys use `heterocycles`, fixing the old `heterocyles`
spelling. Do not silently change feature columns for an already trained model.

For explicit average molecular weight and H-bond descriptor definitions:

```python
import datamol as dm
import pandas as pd
mols = [dm.to_mol(s) for s in ["CCO", "c1ccccc1", "CC(=O)O"]]
properties = {"mw": "MolWt", "logp": "MolLogP", "hbd": "NumHDonors",
              "hba": "NumHAcceptors", "tpsa": "TPSA"}
descriptors = dm.descriptors.compute_many_descriptors(
    mols[0], properties_fn=properties, add_properties=False,
)
desc_df = dm.descriptors.batch_compute_many_descriptors(
    mols, properties_fn=properties, add_properties=False, n_jobs=1,
)
passes_screen = ((desc_df["mw"] <= 500) & (desc_df["logp"] <= 5)
                 & (desc_df["hbd"] <= 5) & (desc_df["hba"] <= 10))
assert len(passes_screen) == len(mols)
```

`properties_fn` is a mapping from output names to callables or RDKit descriptor names,
not a list. `add_properties=True` supplements that mapping with defaults (and mutates
the mapping); use False for a fixed feature schema. `any_rdkit_descriptor("TPSA")`
returns a callable found in RDKit Descriptors/rdMolDescriptors. Batch options include
`n_jobs`, `batch_size`, `progress`, and `progress_leave`. In the tested 0.13.0 stack,
parallel descriptor calls (`n_jobs=2` or `-1`) require an explicit positive `batch_size`,
for example `batch_size=128`: the default None is rejected by joblib. Serial examples
here use `n_jobs=1`; a two-worker call with `batch_size=2` was also executed.

These physicochemical cutoffs are screening heuristics, not evidence of activity,
safety, oral bioavailability or brain penetration. A TPSA cutoff alone cannot establish
blood-brain barrier permeability. H-bond-count definitions and molecular mass conventions
must accompany reported thresholds.

## Specialized properties

- `n_aromatic_atoms`: aromatic atom count.
- `n_aromatic_atoms_proportion`: aromatic atoms / heavy atoms; require at least one
  heavy atom to avoid a zero denominator.
- `n_charged_atoms`: atoms with nonzero formal charge.
- `n_rigid_bonds`: all bonds except acyclic single bonds, so ring bonds are included.
  This graph heuristic is not a forcefield flexibility calculation.
- `n_stereo_centers` / `n_stereo_centers_unspecified`: potential atom stereo centers /
  unspecified atom stereo centers, respectively.

## 2D grids

```python
# to_image defaults to SVG; request raster explicitly for a .png output.
image = dm.viz.to_image(mols, legends=[dm.to_smiles(m) for m in mols],
                        n_cols=3, use_svg=False, outfile="molecules.png")
svg = dm.viz.to_image(mols, use_svg=True, outfile="molecules.svg")
highlight = dm.viz.to_image(mols[0], highlight_atom=[0, 1, 2], highlight_bond=[0, 1])
```

Defaults are `use_svg=True`, `mol_size=(300, 300)`, `n_cols=4`, `max_mols=32`
(`max_mols_ipython=50` inside IPython), and `copy=True`. Grid truncation matters: set
`max_mols` explicitly for larger exports and verify visible molecule count. `indices=True`
and `bond_indices=True` display the respective indices. Highlights for a collection are
one list of indices per molecule; a flat index list is accepted for one molecule.
`align=True` uses a common substructure; supply an explicit template when needed.
The returned object depends on format and notebook context (PIL image, SVG text/widget).

## Conformers and circle grids

```python
# These require the mols/3D molecule from the core and conformer examples.
ring_svg = dm.viz.circle_grid(center_mol=mols[0], ring_mols=[mols[1:]],
                              margin=50, use_svg=True)
```

`circle_grid` takes `ring_mols`, not `circle_mols`, and `margin`, not `circle_margin`.
It supports `act_mapper`, `align`, `outfile`, and `layout_random_seed=19`.
`dm.viz.conformers(mol_3d, n_confs=None, align_conf=True, n_cols=3,
sync_views=True, remove_hs=True)` creates an NGLView widget; None uses all conformers,
a list selects IDs and an integer selects a bounded prefix. It needs a working notebook
widget frontend for interactive display. Widget construction was checked locally; browser
rendering and synchronization were not exercised.
