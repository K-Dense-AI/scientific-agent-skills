# Datamol I/O (0.13.0)

Verified against the [I/O API](https://docs.datamol.io/stable/api/datamol.io.html) and
released source. File examples below are templates: supply actual paths and schemas.

## Read contracts

| Function | Return/default and parameters |
|---|---|
| `dm.read_sdf(path)` | List of Mol by default (`as_df=False`); invalid records discarded by default. |
| `dm.read_sdf(path, as_df=True, mol_column="mol", discard_invalid=False)` | DataFrame including molecules; preserve invalid records for a rejection log. `smiles_column="smiles"`, `sanitize=True`, `remove_hs=True`, `strict_parsing=True`, `n_jobs=1`. |
| `dm.read_smi(path)` | List of valid molecules; no `as_df`, `smiles_column` or `mol_column` arguments. For a named/tabular SMILES file prefer explicit CSV parsing. |
| `dm.read_csv(path, smiles_column="SMILES", mol_column="mol")` | DataFrame with molecules; without `smiles_column` it does not create molecules. Other kwargs go to pandas. |
| `dm.read_excel(path, sheet_name=0, smiles_column="smiles", mol_column="mol")` | DataFrame for a single sheet; use one selected sheet when creating molecules. |
| `dm.read_molblock(text, sanitize=True, remove_hs=True, strict_parsing=True)` | Mol or `None`; `fail_if_invalid=True` raises for invalid molecules. |
| `dm.read_mol2file(path, cleanup_substructures=True, remove_hs=True)` | List of Mol, not one molecule; inspect each parsed record. |
| `dm.read_pdbfile(path, proximity_bonding=True)` / `dm.read_pdbblock(text, proximity_bonding=True)` | Mol; coordinate proximity can infer bonds and is not a validated chemical topology. |

For SMILES plus IDs, define the delimiter/header rather than silently dropping records:

```python
import datamol as dm
# Illustrative: two-column, headerless whitespace-delimited file.
df = dm.read_csv("molecules.smi", sep=r"\s+", header=None,
                 names=["smiles", "id"], smiles_column="smiles", mol_column="mol")
rejected = df.loc[df["mol"].isna()].copy()
accepted = df.loc[df["mol"].notna()].copy()
```

## Write contracts

- `dm.to_sdf(mols, path)` or `dm.to_sdf(df, path, mol_column="mol")` writes SDF.
  Invalid molecules are skipped: check counts before/after export. Retain original record IDs.
- `dm.to_smi(mols, path, error_if_empty=True)` writes a molecule sequence; no `mol_column`
  parameter. Use a tabular file when IDs and rejection provenance must survive.
- `dm.to_xlsx(df, path, mol_column="mol")` renders one molecule column (singular), with
  `mol_size=(300, 300)` by default.
- `dm.to_molblock(mol, conf_id=-1)` and `dm.to_pdbblock(mol, conf_id=-1)` return strings.
  An SDF write exports one conformer per molecule; explicitly enumerate conformers if all are needed.

## Universal tables and serialization

`dm.open_df(path, **kwargs)` dispatches by extension among CSV, Excel, Parquet, JSON and
SDF; SDF defaults to a DataFrame here, but include `mol_column="mol"` to retain molecules.
`dm.save_df(df, path, **kwargs)` supports the same formats, including SDF. Compression
support depends on format/extension and the delegated reader, not every suffix combination.
CSV/Excel/JSON/Parquet are not portable storage for Python Mol objects: export canonical
SMILES and scalar columns, then reconstruct molecules when reading.

```python
# Continue with accepted rows from the parsing example, retaining source IDs.
portable = accepted.drop(columns=["mol"]).copy()
portable["smiles"] = [dm.to_smiles(m) for m in accepted["mol"]]
dm.save_df(portable, "compounds.parquet")
restored = dm.open_df("compounds.parquet")
restored["mol"] = [dm.to_mol(s) for s in restored["smiles"]]
```

## Remote I/O

Path-based readers/writers commonly delegate to fsspec or pandas. Mol/PDB block functions
consume/return text, not remote URLs. Current Datamol bundles S3/GCS backends; additional
protocols such as Azure require their own compatible backend. Authentication follows the
chosen provider/backend (environment, config, or workload identity); it is not restricted
to environment variables. Use only the requested destinations and avoid logging credentials.
HTTPS is a useful read source, not a promise of writable HTTP storage.

```python
# Illustrative provider-dependent paths; not exercised in this review.
df = dm.read_sdf("s3://bucket/compounds.sdf", as_df=True, mol_column="mol")
dm.to_sdf(df, "gs://bucket/results.sdf", mol_column="mol")
```

For `n_jobs`, use `1` for serial and `-1` for all available cores; do not assume `None`
means all cores. Review remote access, sizes and output counts independently of local tests.
