# Datamol fragments and scaffolds (0.13.0)

Sources: [fragment API](https://docs.datamol.io/stable/api/datamol.fragment.html),
[scaffold API](https://docs.datamol.io/stable/api/datamol.scaffold.html), and released source.

## Murcko frameworks and split boundaries

```python
import datamol as dm
from collections import Counter
mol = dm.to_mol("c1ccc(cc1)CCN")  # phenethylamine
scaffold = dm.to_scaffold_murcko(mol)
assert dm.to_smiles(scaffold) == "c1ccccc1"  # terminal side chain is removed
mols = [dm.to_mol(s) for s in ["c1ccccc1CCN", "c1ccccc1O", "c1ccncc1"]]
scaffold_smiles = [dm.to_smiles(dm.to_scaffold_murcko(m)) for m in mols]
scaffold_counts = Counter(scaffold_smiles)
```

Murcko frameworks retain rings and linkers between rings. A chain attached to one ring
is a side chain, not a retained linker. Acyclic molecules have an empty scaffold; choose
and report their grouping policy explicitly. `make_generic=True` additionally abstracts
atom/bond chemistry. Standardize consistently before grouping and keep full molecule IDs.
Scaffold-disjoint splits do not by themselves prevent duplicates, analog leakage, target
leakage, or temporal leakage; check overlap and group sizes.

`dm.scaffold.fuzzy_scaffolding(mols, enforce_subs=None, n_atom_cuttoff=8, ...)`
accepts a **list** of molecules. It returns `(scaffold_smiles_set, scaffold_infos,
scaffold_to_group)`: the last two are pandas DataFrames in 0.13.0. `enforce_subs` contains substructure patterns;
`additional_templates` supplies Mol templates. MCS and R-group decomposition settings
matter; this is a template-generation tool, not a unique scaffold ontology. It removes
conformers from molecules during decomposition; pass `[dm.copy_mol(m) for m in mols]`
when the source coordinates must survive.

## BRICS, RECAP and MMPA contracts

`dm.fragment.brics(mol, singlepass=True, remove_parent=False, sanitize=True, fix=True)`
and `dm.fragment.recap(mol, remove_parent=False, sanitize=True, fix=True)` return
**lists of Mol**, not sets of SMILES. Parent inclusion and dummy-atom fixing change the
meaning of fragment counts. Request `remove_parent=True` to exclude the original molecule;
use `fix=False` when attachment labels must survive. Do not strip attachment points by
string replacement: that loses environment labels and can produce wrong chemistry.

```python
mol = dm.to_mol("CC(=O)Oc1ccccc1C(=O)O")
brics_molecules = dm.fragment.brics(mol, remove_parent=True, fix=False)
recap_molecules = dm.fragment.recap(mol, remove_parent=True, fix=False)
brics_smiles = {dm.to_smiles(fragment) for fragment in brics_molecules}
assert all(isinstance(fragment, dm.Mol) for fragment in brics_molecules)
```

BRICS uses compatibility rules between labelled environments; labels such as `[3*]` and
`[16*]` are not interchangeable generic atoms. RECAP follows its own retrosynthetic bond
rules. Neither is proof of a feasible synthesis or a reaction yield. Avoid claiming a fixed
universal count of bond types: RDKit implementations encode environment/rule combinations.
`dm.fragment.mmpa_frag(mol, max_cut=1, max_bond_cut=20)` returns a set of
`(core_smiles, sidechain_smiles)` pairs in the release, despite its Mol type annotation.
Its output alone is not a matched-pair dataset; matching requires comparing appropriate
common cores across molecules and validating attachment correspondence.

## Reproducible fragment counting and heuristic overlap

```python
def fragment_keys(molecule):
    return {dm.to_smiles(f) for f in dm.fragment.brics(
        molecule, remove_parent=True, fix=False,
    )}

# Each fragment contributes at most once per compound (prevalence, not site count).
fragment_counts = Counter()
for molecule in mols:
    fragment_counts.update(fragment_keys(molecule))
reference_fragments = fragment_keys(mol)

def fragment_score(molecule, reference):
    keys = fragment_keys(molecule)
    return len(keys & reference) / len(keys) if keys else 0.0

scores = [fragment_score(molecule, reference_fragments) for molecule in mols]
```

This overlap score measures the chosen fragmentation representation. It is not a validated
activity prediction. Specify fragmentation options, duplicate policy, attachment treatment,
and whether a parent molecule is included whenever comparing libraries.
