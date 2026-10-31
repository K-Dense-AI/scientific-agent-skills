# Tamarind Bio illustrative settings and output interpretation

Reviewed **2026-09-30** using the [live public catalog](https://app.tamarind.bio/tools.json),
[REST contract](https://app.tamarind.bio/api/openapi.json), and tool documentation.
These examples are **not authenticated `validate-job` results**. Replace file
placeholders, read `GET /tools/{name}/schema`, then validate each settings object
before a compute submission. Historical exact error messages are not a contract.

## Authentication and discovery check

This read-only check does not submit jobs. Supply the user's deployment and key:

```python
import os
import requests

base = os.environ.get("TAMARIND_BASE_URL", "https://app.tamarind.bio/api").rstrip("/")
headers = {"x-api-key": os.environ["TAMARIND_API_KEY"]}
response = requests.get(f"{base}/tools", headers=headers, timeout=(10, 60))
response.raise_for_status()
tools = response.json()
assert isinstance(tools, list)
print("[OK] Account tool catalog returned", len(tools), "entries")
```

To check a payload next, use `/validate-job` as shown in [workflows](workflows.md).
That call requires authentication even though it does not spend a compute job.

## AlphaFold monomer and multimer

`sequence` is the public catalog's required setting for `alphafold`:

```json
{"sequence": "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"}
```

For a homodimer, this illustrative short sequence pair shows colon separation:

```json
{"sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIE:MKTAYIAKQRQISFVKSHFSRQLEERLGLIE"}
```

It does not establish that these chains interact. Read optional model-count,
recycle, MSA, and template fields from the account schema instead of assuming
string versus numeric representations or defaults.

## Boltz and Chai sequence modes

```json
{"inputFormat": "sequence", "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALP"}
```

The current public catalog makes `inputFormat` **optional with default
`"sequence"`** for both tools. Boltz advertises `sequence`, `list`, `molecules`,
and `yaml`; Chai advertises `sequence`, `molecules`, and `list` (no YAML mode in
this catalog). Set a mode explicitly when useful, then supply its conditional
fields. Do not claim that omitting `inputFormat` universally fails validation.

## DiffDock with a SMILES ligand

```json
{"proteinFile": "target.pdb", "ligandFormat": "SMILES",
 "ligandSmiles": "CC(=O)Oc1ccccc1C(=O)O"}
```

Upload an actual target first. The current `proteinFile` declaration accepts PDB
and CIF extensions. `ligandFormat` defaults to `"sdf/mol2 file"`; set `"SMILES"`
to activate `ligandSmiles`. The file branch uses `ligandFile` with SDF/MOL2.

## AutoDock Vina with a SMILES ligand

```json
{"receptorFile": "receptor.pdb", "ligandFormat": "smiles",
 "ligandSmiles": "CC(=O)Oc1ccccc1C(=O)O"}
```

This is the **catalog-backed minimum branch**, not a complete scientific docking
protocol. Vina uses `receptorFile`, accepts PDB/CIF, and its `ligandFormat` values
are lowercase `"sdf"`/`"smiles"` with default `"sdf"`. Determine a meaningful
search box from the receptor/pocket and read its current fields, units, and
sampling settings from the full account schema. The public required-settings
catalog does not verify optional box parameter names or their defaults; do not
reuse coordinates from an unrelated target or claim arbitrary example coordinates
are required API settings.

## ProteinMPNN inverse folding

```json
{"pdbFile": "backbone.pdb", "designedResidues": {"A": "1 2 3 4 5"}}
```

The selected residues must exist on chain A of the uploaded structure. The
catalog currently declares PDB/CIF input and a space-separated residue-list
representation. Its empty-map default does not justify assuming which chains or
residues will be redesigned. Inspect the full schema to choose a model variant,
sample count, and explicit design region, then validate. Fold generated sequences
through the folding tool's `sequence` field, not a template parameter.

## Outputs and failure interpretation

- `Score` is optional and can be JSON text, a number, or null; parse by actual
  type. Metrics and output filenames depend on the tool/task/version.
- `/tools` can expose `outputs.mainCSV`, task-specific `outputs.byTask`, column
  metadata, and `filterMetrics`. Use these and the actual archive to find data;
  do not assume every folder emits `rank_*.pdb` or every tool has pLDDT.
- pLDDT, pTM, and interface confidence are model confidence estimates, not proof
  of affinity, specificity, or experimental validation. Assess geometries and
  chemical validity and compare only compatible metrics/scales.
- `Complete` permits result retrieval but does not prove usable scientific
  output. `Stopped`/`Failed` require log inspection (`fileName: "output.log"`).
- `/result` 202 means archive preparation: wait and repeat retrieval. It is not
  an instruction to run the scientific job again.
- `/validate-job` success returns the normalized settings to submit. An unknown
  key warning still needs correction; a typo in an optional field can otherwise
  run with the wrong default.
- Relative uploaded paths and `JobName/path/to/file.ext` references are distinct
  from inline content. Avoid inventing storage keys or treating arbitrary text
  as an existing file. Current documentation says redundant email prefixes are
  stripped; older double-prefix errors are no longer universal.
