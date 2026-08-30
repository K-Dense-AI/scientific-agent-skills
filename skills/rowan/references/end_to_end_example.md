# End-to-End Example: Lead Optimization Campaign

A complete campaign: project and folder setup, tautomer selection, pKa and property
prediction across an analogue series, result collection and summary, and a docking
follow-up on the selected compound.

## End-to-end example: Lead optimization campaign

This example demonstrates a realistic workflow for optimizing a hit compound:

```python
import rowan
import pandas as pd

# 1. Create a project and folder for organization
project = rowan.create_project(name="CDK2 Hit Optimization")
rowan.set_project("CDK2 Hit Optimization")
folder = rowan.create_folder(name="round_1_tautomers_and_pka")

# 2. Load hit compound and analogues
hit = "CCNc1ncc(c(Nc2ccc(F)cc2)n1)-c1cccnc1"  # Known hit
analogues = [
    "CCNc1ncc(c(Nc2ccccc2)n1)-c1cccnc1",      # Remove F
    "CCNc1ncc(c(Nc2ccc(Cl)cc2)n1)-c1cccnc1",  # Cl instead of F
    "CCC(C)Nc1ncc(c(Nc2ccc(F)cc2)n1)-c1cccnc1",  # Propyl instead of ethyl
]

# 3. Determine best tautomers (just in case)
print("Searching tautomeric forms...")
taut_workflows = [
    rowan.submit_tautomer_search_workflow(
        rowan.Molecule.from_smiles(smi), name=f"analog_{i}", folder=folder,
    )
    for i, smi in enumerate(analogues)
]

best_tautomers = []
for wf in taut_workflows:
    result = wf.result()
    best_tautomers.append(result.best_tautomer)

# 4. Predict pKa and basic properties for all analogues
print("Predicting pKa and properties...")
pka_workflows = [
    rowan.submit_pka_workflow(
        smi, method="chemprop_nevolianis2025", name=f"compound_{i}", folder=folder,
    )
    for i, smi in enumerate(best_tautomers)
]

descriptor_workflows = [
    rowan.submit_descriptors_workflow(
        rowan.Molecule.from_smiles(smi), name=f"compound_{i}", folder=folder
    )
    for i, smi in enumerate(best_tautomers)
]

# 5. Collect results
pka_results = []
for wf in pka_workflows:
    try:
        result = wf.result()
        pka_results.append({
            "compound": wf.name,
            "pka": result.strongest_acid,  # pKa of the strongest acid site
            "uuid": wf.uuid,
        })
    except rowan.WorkflowError as e:
        print(f"pKa prediction failed for {wf.name}: {e}")

descriptor_results = []
for wf in descriptor_workflows:
    try:
        result = wf.result()
        desc = result.descriptors
        descriptor_results.append({
            "compound": wf.name,
            "exact_mass": desc.get("MW"),
            "topological_psa": desc.get("TopoPSA"),
            "logp": desc.get("SLogP"),
            "hba": desc.get("nHBAcc"),
            "hbd": desc.get("nHBDon"),
            "uuid": wf.uuid,
        })
    except rowan.WorkflowError as e:
        print(f"Descriptor calculation failed for {wf.name}: {e}")

# 6. Merge and summarize
df_pka = pd.DataFrame(pka_results)
df_desc = pd.DataFrame(descriptor_results)
df = df_pka.merge(df_desc, on="compound", how="outer")

print("\n=== Preliminary SAR ===")
print(df.to_string())

# 7. Select promising compound for docking
# compound names are "compound_0", "compound_1", etc. — extract the index
top_idx = int(df.loc[df["pka"].idxmin(), "compound"].split("_")[1])
top_smiles = best_tautomers[top_idx]

print(f"\nProceeding with docking: {top_smiles}")

# 8. Docking campaign
protein = rowan.create_protein_from_pdb_id(code="1CKP", name="CDK2_1CKP")
pocket = [[10.5, 24.2, 31.8], [18.0, 18.0, 18.0]]

docking_wf = rowan.submit_docking_workflow(
    protein=protein,
    pocket=pocket,
    initial_molecule=rowan.Molecule.from_smiles(top_smiles),
    do_pose_refinement=True,
    name=f"docking_{top_idx}",
)

dock_result = docking_wf.result()
print(f"\nDocking score: {dock_result.scores[0]:.2f} kcal/mol")
print(f"Best pose saved to: best_pose.pdb")
dock_result.best_pose.write("best_pose.pdb")
```
