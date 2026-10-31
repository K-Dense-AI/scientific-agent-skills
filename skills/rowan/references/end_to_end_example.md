# Example: Tautomer-Aware Analogue Triage

This illustrative campaign preserves molecule objects through geometry workflows,
uses SMILES only for a SMILES pKa method, and records workflow identifiers.
The toy aminopyridines below are not claimed to be active against a target.
Hosted results and docking accuracy were not tested in this refresh.

Requires `rowan-python==3.2.0`, pandas, a configured `ROWAN_API_KEY`, and a
prepared receptor plus validated pocket coordinates for the optional follow-up.

```python
from pathlib import Path
import json
import pandas as pd
import rowan

# Work around the Folder annotation defect in SDK 3.2.0.
from datetime import datetime
rowan.Folder.model_rebuild(_types_namespace={"datetime": datetime})

project = rowan.create_project(name="Analogue triage example")
rowan.project_uuid = project.uuid
folder = rowan.create_folder(name="round_1", parent_uuid=project.root_folder_uuid)
compounds = {"fluoro": "Nc1ncc(F)cc1", "chloro": "Nc1ncc(Cl)cc1", "methoxy": "Nc1ncc(OC)cc1"}

rows = []
selected_tautomers = {}
workflow_ids = {}

def remember(compound, step, workflow):
    workflow_ids.setdefault(compound, {})[step] = workflow.uuid
    Path("campaign_workflows.json").write_text(json.dumps(workflow_ids, indent=2))

for compound, smiles in compounds.items():
    try:
        taut_wf = rowan.submit_tautomer_search_workflow(
            rowan.Molecule.from_smiles(smiles), name=f"{compound} tautomers", folder=folder,
        )
        remember(compound, "tautomers", taut_wf)
        tautomer = taut_wf.result().best_tautomer  # Molecule or None
        if tautomer is None or not tautomer.smiles:
            rows.append({"compound": compound, "error": "No weighted tautomer with SMILES"})
            continue
        selected_tautomers[compound] = tautomer

        pka_wf = rowan.submit_pka_workflow(
            tautomer.smiles, method="starling", name=f"{compound} pKa", folder=folder,
        )
        remember(compound, "pka", pka_wf)
        desc_wf = rowan.submit_descriptors_workflow(
            tautomer, name=f"{compound} descriptors", folder=folder,
        )
        remember(compound, "descriptors", desc_wf)
        pka = pka_wf.result()
        desc = desc_wf.result().descriptors
        if desc is None:
            raise ValueError("Completed descriptor workflow returned no descriptors")
        rows.append({
            "compound": compound,
            "tautomer_smiles": tautomer.smiles,
            "strongest_acid": pka.strongest_acid,
            "strongest_base": pka.strongest_base,
            "exact_mass": desc.get("MW"),
            "topological_psa": desc.get("TopoPSA"),
            "logp": desc.get("SLogP"),
        })
    except rowan.WorkflowError as exc:
        rows.append({"compound": compound, "error": str(exc)})

summary = pd.DataFrame(rows)
summary.to_csv("triage.csv", index=False)
print(summary.to_string(index=False))
```

Do not automatically rank compounds by the smallest pKa: the relevant acid/base
site, desired charge at assay pH, permeability, solubility, and target interactions
all matter. A single highest-weight tautomer is a triage simplification. Carry
multiple populated tautomers/protomers into docking when warranted.

After reviewing the table and experimental objectives, supply `candidate.txt`
with the selected compound identifier, `prepared_receptor.pdb`, and `pocket.json`
containing `[[cx, cy, cz], [sx, sy, sz]]` in Å for that exact receptor:

```python
candidate = Path("candidate.txt").read_text().strip()
if candidate not in selected_tautomers:
    raise ValueError("Selected candidate has no usable tautomer structure")
pocket = json.loads(Path("pocket.json").read_text())
protein = rowan.upload_protein(
    name="prepared target", file_path="prepared_receptor.pdb", project_uuid=project.uuid,
)
docking_wf = rowan.submit_docking_workflow(
    protein=protein,
    pocket=pocket,
    initial_molecule=selected_tautomers[candidate],
    docking_settings=rowan.VinaSettings(scoring_function="vinardo"),
    do_pose_refinement=True,
    name=f"{candidate} docking",
    folder=folder,
)
remember(candidate, "docking", docking_wf)
dock = docking_wf.result()
if not dock.scores:
    raise RuntimeError("No successful docking poses")
print(f"Docking score: {dock.scores[0].score:.2f} kcal/mol")
Path("best_pose.xyz").write_text(dock.best_pose.to_xyz())
if dock.scores[0].complex_pdb:
    dock.get_complex(0).download_structure(name="docked_complex", file_format="mmcif")
```

Set per-workflow `max_credits` to the campaign's agreed limits before execution.
Inspect poses, stereochemistry, clashes, and retained waters/cofactors; validate
with a known ligand where possible. Neither a docking score nor a cofolding
confidence score establishes biological activity. For restartable batches and
submission ambiguity, see [batch_and_webhooks.md](batch_and_webhooks.md).
