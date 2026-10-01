# Datamol pipeline patterns (0.13.0)

These functions were tested on small synthetic inputs. Supply project inputs/paths when
applying them. Use explicit structure policies and preserve source-row provenance.

## Load, screen and select diverse compounds

```python
import datamol as dm
import numpy as np
import pandas as pd


def prepare_library(raw):
    """Illustrative policy for ordinary organic compounds; returns accepted and rejected rows."""
    if "mol" not in raw or "source_id" not in raw:
        raise ValueError("Expected mol and source_id columns")
    df = raw.copy()
    df["source_smiles"] = [dm.to_smiles(m) if m is not None else None for m in df["mol"]]
    transformed, reasons = [], []
    for molecule in df["mol"]:
        try:
            clean = None if molecule is None else dm.standardize_mol(
                molecule, disconnect_metals=False, normalize=True,
                reionize=True, uncharge=False, stereo=True,
            )
            transformed.append(clean)
            reasons.append(None if clean is not None else "invalid molecule")
        except Exception as error:
            transformed.append(None)
            reasons.append(type(error).__name__)
    df["mol"], df["rejection_reason"] = transformed, reasons
    rejected = df.loc[df["mol"].isna()].copy()
    accepted = df.loc[df["mol"].notna()].copy().reset_index(drop=True)
    if accepted.empty:
        return accepted, rejected
    properties = {"mw": "MolWt", "logp": "MolLogP", "hbd": "NumHDonors", "hba": "NumHAcceptors"}
    desc = dm.descriptors.batch_compute_many_descriptors(
        accepted["mol"].tolist(), properties_fn=properties, add_properties=False, n_jobs=1,
    )
    # Both frames now have the same RangeIndex; no accidental label re-alignment.
    accepted = pd.concat([accepted, desc.add_prefix("screen_")], axis=1)
    accepted["passes_screen"] = ((desc["mw"] <= 500) & (desc["logp"] <= 5)
                                 & (desc["hbd"] <= 5) & (desc["hba"] <= 10))
    return accepted, rejected


def select_diverse(accepted, limit=100):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")
    if accepted.empty:
        return accepted.copy()
    eligible = accepted.loc[accepted["passes_screen"]].copy().reset_index(drop=True)
    if eligible.empty:
        return eligible
    indices, _ = dm.pick_diverse(eligible["mol"].tolist(), npick=min(limit, len(eligible)), seed=42)
    return eligible.iloc[indices].copy()
```

Read SDF using `dm.read_sdf(path, as_df=True, mol_column="mol", discard_invalid=False)`;
assign or validate a durable `source_id` before passing it to `prepare_library`. Its
`source_smiles` is the parsed representation; archive raw files separately to retain records
that cannot be parsed. Report all parsed-invalid and screening-excluded rows. Do not treat
the screening criteria as validated activity, safety or bioavailability predictions.

```python
# Executed synthetic example with a failed record and non-contiguous row labels.
raw = pd.DataFrame({"source_id": ["a", "bad", "b"],
                    "mol": [dm.to_mol("CCO"), None, dm.to_mol("c1ccccc1")]}, index=[8, 2, 20])
accepted, rejected = prepare_library(raw)
selection = select_diverse(accepted, limit=100)
assert set(selection["source_id"]) == {"a", "b"}
assert rejected["source_id"].tolist() == ["bad"]
```

Export the selected table and an ID-labelled PNG grid explicitly with `use_svg=False`.
Keep rejected rows separately. Use a project-approved destination before writing artifacts.

## SAR by scaffold series

Illustrative template: `mols`, `activities` and activity units must come from the same rows.
Do not mix assays, censoring conventions or pActivity versus concentration scales.

```python
def sar_table(mols, activities):
    if len(mols) != len(activities):
        raise ValueError("Molecules and activities must be row-aligned")
    return pd.DataFrame({"mol": mols,
                         "scaffold": [dm.to_smiles(dm.to_scaffold_murcko(m)) for m in mols],
                         "activity": activities})
```

Group this table by scaffold to summarize measured values and visualize related compounds
with labelled units and `align=True`. An empty Murcko scaffold groups acyclic molecules
without asserting they form a meaningful SAR series.

## Similarity ranking

```python
def similarity_ranking(query_actives, library_mols, limit=100):
    if not query_actives or not library_mols:
        raise ValueError("Need nonempty query and library molecules")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")
    distances = dm.cdist(query_actives, library_mols, n_jobs=1,
                         fp_type="ecfp", radius=2, fpSize=2048, includeChirality=True)
    similarities = 1 - distances.min(axis=0)
    indices = np.argsort(-similarities, kind="stable")[:limit]
    return indices, similarities[indices]
```

This ranks by maximum binary Tanimoto similarity to any query; a hit is a structural
candidate, not an experimentally confirmed active. Keep the source index alongside score.
The returned cross-distance matrix uses O(query count × library count) memory. Chunk the
library and retain top results for large screens, with the same fingerprint settings in every chunk.
