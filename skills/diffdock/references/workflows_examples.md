# DiffDock workflow recipes

These target v1.1.3 user-complex inference. Input generation and local helper tests
were executed with synthetic fixtures; pretrained docking and external GNINA/GUI
commands were source-checked, not executed. Replace illustrative filenames with
prepared inputs. Run upstream commands from its repository root.

## Generate a traceable screening batch

This Python recipe expects a CSV with `compound_id,smiles`, unique IDs, and a prepared
`target_protein.pdb`. It preserves source identifiers instead of relabeling filtered
rows. Generated names must pass the helper's safe-name rule. Screening here produces
poses for later assessment, not a validated affinity ranking.

```python
import csv
from pathlib import Path
import pandas as pd

library = Path("ligand_library.csv")
with library.open(newline="") as handle:
    header = next(csv.reader(handle))
if len(header) != len(set(header)):
    raise ValueError("Duplicate library columns")
ligands = pd.read_csv(library, dtype=str, keep_default_na=False)
if ligands.empty or ligands["compound_id"].eq("").any() or ligands["compound_id"].duplicated().any():
    raise ValueError("Require nonempty library and unique nonempty compound IDs")
rows = pd.DataFrame({
    "complex_name": "compound_" + ligands["compound_id"],
    "protein_path": str(Path("target_protein.pdb").resolve()),
    "ligand_description": ligands["smiles"],
    "protein_sequence": "",
})
rows.to_csv("screening.csv", index=False)
```

```bash
python /path/to/diffdock-skill/scripts/prepare_batch_csv.py screening.csv --validate
python -m inference --config default_inference_args.yaml \
  --protein_ligand_csv screening.csv --out_dir results/screening_001/ --loglevel INFO
python /path/to/diffdock-skill/scripts/analyze_results.py results/screening_001/ --export all_poses.csv
```

Reconcile every `complex_name` with output directories and expected ranks. A missing
output is a failed/skipped result, not a nonbinder. Preserve input CSV, configuration,
checkpoint identity, source revision, logs, and raw outputs together.

## Receptor ensemble

Use one row per known conformation, retaining the same ligand state. This illustrative
input generator does not perform protein preparation:

```python
from pathlib import Path
import pandas as pd

conformations = ["conf1.pdb", "conf2.pdb", "conf3.pdb"]
pd.DataFrame({
    "complex_name": [f"ensemble_{i}" for i in range(len(conformations))],
    "protein_path": [str(Path(name).resolve()) for name in conformations],
    "ligand_description": ["CC(=O)Oc1ccccc1C(=O)O"] * len(conformations),
    "protein_sequence": [""] * len(conformations),
}).to_csv("ensemble.csv", index=False)
```

Copy the bundled config and edit `samples_per_complex` to 20 if increased sampling is
justified. The YAML value wins over CLI values. Run with the copied config, ensemble
CSV and a fresh output directory. Inspect all conformations; score differences are
not relative binding free energies.

## GNINA as a separate step

The [official GNINA CLI](https://github.com/gnina/gnina) supports receptor/ligand input
and `--score_only`. This illustrative loop scores existing poses without relaxation:

```bash
for pose in results/screening_001/compound_001/rank*_confidence*.sdf; do
    test -f "$pose" || continue
    gnina --receptor target_protein.pdb --ligand "$pose" --score_only > "${pose%.sdf}_gnina.txt"
done
```

Keep different score fields, units, versions and model identities separate. An affinity
model's output is an estimate requiring appropriate validation; confidence is not its
substitute. `score_only` does not relax a pose. For subsequent minimization, preserve
raw coordinates and ligand stereochemistry, specify a compatible protein/ligand force
field and protonation model, and recheck the result.

A generic OpenMM `ForceField('amber14-all.xml', ...)` does not parameterize an arbitrary
ligand. A valid minimization workflow must add the ligand topology/coordinates, obtain
its parameters, build the combined system, set positions in the Context, and validate
atom mapping/units before minimization. No incomplete OpenMM snippet is supplied here.

## Local GUI

```bash
python app/main.py
```

Upstream documents `http://localhost:7860`. The released interface takes a PDB ID or
uploaded receptor and ligand SMILES/file; sequence input is supported by inference CLI,
not this GUI. The application may download a structure given a PDB ID, so record the
retrieved structure and its biological interpretation. Hosted demo operations and
network transfer of private inputs require the user's intended destination.

## Sources

- [Inference and configuration](https://github.com/gcorso/DiffDock/blob/v1.1.3/inference.py)
- [Released web interface](https://github.com/gcorso/DiffDock/blob/v1.1.3/app/main.py)
- [GNINA CLI reference](https://github.com/gnina/gnina)
- [OpenMM application guide](https://docs.openmm.org/latest/userguide/application/02_running_sims.html)
