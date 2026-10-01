# Datamol reactions and bundled data (0.13.0)

Sources: [reaction API](https://docs.datamol.io/stable/api/datamol.reactions.html),
[data API](https://docs.datamol.io/stable/api/datamol.data.html), and released source.

## Reaction outputs and validation

`dm.reactions.apply_reaction(rxn, reactants, product_index=None,
single_product_group=False, as_smiles=False, rm_attach=False, sanitize=True)`
returns all product groups by default. With `product_index=None`, each group is a list
of product molecules. `product_index=0` instead selects the first product slot from
each group, producing a flat list. No matches return `[]`; failed sanitization can leave
`None` entries. `single_product_group=True` randomly chooses a group; it is not a
chemically ranked or deterministically first product. Retain all groups for enumeration.

```python
import datamol as dm
from rdkit.Chem import rdChemReactions
# Computational substitution pattern; no reaction conditions or yield are implied.
rxn = rdChemReactions.ReactionFromSmarts("[C:1](=[O:2])[OH:3]>>[C:1](=[O:2])[Cl:3]")
reactant = dm.to_mol("CC(=O)O")
groups = dm.reactions.apply_reaction(rxn, (reactant,), single_product_group=False)
products = [p for group in groups for p in group if p is not None]
product_smiles = sorted({dm.to_smiles(p) for p in products})
assert product_smiles == ["CC(=O)Cl"]
assert dm.reactions.apply_reaction(rxn, (dm.to_mol("CC"),)) == []
```

`rxn_from_smarts`, `rxn_from_block`, and `rxn_from_block_file` initialize reaction
objects; `rxn_to_smarts`, `rxn_to_block`, and `rxn_to_block_file` export them.
`can_react(rxn, mol)` checks reactant-pattern matching. `is_reaction_ok(rxn)` invokes
RDKit preprocessing/sanitization; it does not validate synthetic feasibility, conditions,
selectivity, safety or yield. Atom mapping tracks atoms in a computational template;
it does not imply atom-balanced laboratory chemistry. Deduplicate products by an explicit
stereochemistry/tautomer policy and keep input/product-group provenance.

These simple templates were executed on matching toy reactants; they are illustrative
chemical transformations, not validated synthesis instructions:

```python
amide_rxn = rdChemReactions.ReactionFromSmarts(
    "[N;H1,H2:1].[C:2](=[O:3])[OH]>>[N:1][C:2](=[O:3])"
)
suzuki_rxn = rdChemReactions.ReactionFromSmarts(
    "[c:1][Br].[c:2][B]([OH])[OH]>>[c:1][c:2]"
)
esterification = rdChemReactions.ReactionFromSmarts(
    "[C:1][OH:2].[C:3](=[O:4])[Cl]>>[C:1][O:2][C:3](=[O:4])"
)
```

For a library, preserve `(source_id, product_group, product_slot)` and log both empty
matches and invalid products; do not silently append nested groups as though they were Mol.

## Bundled datasets

| Call | Verified 0.13.0 snapshot |
|---|---|
| `dm.data.cdk2(as_df=True, mol_column="mol")` | 47 rows, including structures, ID, Cluster and modelling metadata. No measured activity column is supplied. |
| `dm.data.freesolv(as_df=True)` | 642 rows: `iupac`, `smiles`, `expt`, `calc`; hydration free energies in kcal/mol. No Mol column by default. |
| `dm.data.solubility(as_df=True, mol_column="mol")` | 1,282 rows: `mol`, `ID`, `NAME`, `SOL`, `SOL_classification`, `smiles`, `split`. Target is `SOL`, not `solubility`. |

All three accept `as_df=False` for molecules. These are bundled toy snapshots, not a
fresh download of the originating datasets. Inspect target definitions, units, duplicates,
license and source provenance before drawing research conclusions. A bundled split is
an example boundary, not evidence that it is scaffold-disjoint or suitable for your task.

```python
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
sol = dm.data.solubility()
train = sol.loc[sol["split"] == "train"]
test = sol.loc[sol["split"] == "test"]
# One molecule per call: dm.to_fp does not featurize a pandas Series.
X_train = np.stack([dm.to_fp(m, radius=2) for m in train["mol"]])
X_test = np.stack([dm.to_fp(m, radius=2) for m in test["mol"]])
model = RandomForestRegressor(n_estimators=20, random_state=42, n_jobs=1)
model.fit(X_train, train["SOL"].astype(float))
predictions = model.predict(X_test)
mae = mean_absolute_error(test["SOL"].astype(float), predictions)
print(f"Toy held-out MAE: {mae:.3f}")
```

This small executed baseline checks the API and feature/label alignment. It is not a
benchmark claim or evidence of prospective predictive performance.
