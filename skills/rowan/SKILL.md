---
name: rowan
description: Rowan is a cloud-native molecular modeling and medicinal-chemistry workflow platform with a Python API. Use for pKa and macropKa prediction, conformer and tautomer ensembles, docking and analogue docking, protein-ligand cofolding, MSA generation, molecular dynamics, permeability, descriptor workflows, and related small-molecule or protein modeling tasks. Ideal for programmatic batch screening, multi-step chemistry pipelines, and workflows that would otherwise require maintaining local HPC/GPU infrastructure.
license: Proprietary (API key required)
compatibility: Python 3.12+, API key required
required_environment_variables: [{"name": "ROWAN_API_KEY", "prompt": "Rowan computational chemistry API key.", "required_for": "full functionality"}]
metadata: {"version": "1.2", "skill-author": "Rowan Science", "trigger-keywords": "pKa prediction, molecular docking, conformer search, chemistry workflow, drug discovery, SMILES, protein structure, batch molecular modeling, cloud chemistry", "openclaw": {"primaryEnv": "ROWAN_API_KEY", "envVars": [{"name": "ROWAN_API_KEY", "required": true, "description": "Rowan computational chemistry API key."}]}}
---

# Rowan: Cloud-Native Molecular-Modeling and Drug-Design Workflows

## Overview

Rowan is a cloud-native workflow platform for molecular simulation, medicinal chemistry, and structure-based design. Its Python API exposes a unified interface for small-molecule modeling, property prediction, docking, molecular dynamics, and AI structure workflows.

Use Rowan when you want to run medicinal-chemistry or molecular-design workflows programmatically without maintaining local HPC infrastructure, GPU provisioning, or a collection of separate modeling tools. Rowan handles all infrastructure, result management, and computation scaling.

## When to use Rowan

**Rowan is a good fit for:**

- Quantum chemistry, semiempirical methods, or neural network potentials
- Batch property prediction (pKa, descriptors, permeability, solubility)
- Conformer and tautomer ensemble generation
- Docking workflows (single-ligand, analogue series, pose refinement)
- Protein-ligand cofolding and MSA generation
- Multi-step chemistry pipelines (e.g., tautomer search → docking → pose analysis)
- Batch medicinal-chemistry campaigns where you need consistent, scalable infrastructure

**Rowan is not the right fit for:**
- Simple molecular I/O (use RDKit directly)
- Post-HF *ab initio* quantum chemistry or relativistic calculations

## Access and pricing model

Rowan uses a credit-based usage model. All users, including free-tier users, can create API keys and use the Python API.

### Free-tier access

- Access to all Rowan core workflows
- 20 credits per week
- 500 signup credits

### Pricing and credit consumption

Credits are consumed according to compute type:

- **CPU**: 1 credit per minute
- **GPU**: 3 credits per minute
- **H100/H200 GPU**: 7 credits per minute

Purchased credits are priced per credit and remain valid for up to one year from purchase.

### Typical cost estimates

| Workflow | Typical Runtime | Estimated Credits | Notes |
|----------|----------------|-------------------|-------|
| Descriptors | <1 min | 0.5–2 | Lightweight, good for triage |
| pKa (single transition) | 2–5 min | 2–5 | Depends on molecule size |
| MacropKa (pH 0–14) | 5–15 min | 5–15 | Broader sampling, higher cost |
| Conformer search | 3–10 min | 3–10 | Ensemble quality matters |
| Tautomer search | 2–5 min | 2–5 | Heterocyclic systems |
| Docking (single ligand) | 5–20 min | 5–20 | Depends on pocket size, refinement |
| Analogue docking series (10–50 ligands) | 30–120 min | 30–100+ | Shared reference frame |
| MSA generation | 5–30 min | 5–30 | Sequence length dependent |
| Protein-ligand cofolding | 15–60 min | 20–50+ | AI structure prediction, GPU-heavy |

## Quick start

```bash
uv pip install rowan-python
```

```python
import rowan
rowan.api_key = "your_api_key_here"  # or set ROWAN_API_KEY env var

# Submit a descriptors workflow — completes in under a minute
wf = rowan.submit_descriptors_workflow("CC(=O)Oc1ccccc1C(=O)O", name="aspirin")
result = wf.result()

print(result.descriptors['MW'])    # 180.16
print(result.descriptors['SLogP']) # 1.19
print(result.descriptors['TPSA'])  # 59.44
```

If that prints without error, you're set up correctly.

## Installation

```bash
uv pip install rowan-python
# or: pip install rowan-python
```

## User and webhook management

### Authentication

Set an API key via environment variable (recommended):

```bash
export ROWAN_API_KEY="your_api_key_here"
```

Or set directly in Python:

```python
import rowan
rowan.api_key = "your_api_key_here"
```

Verify authentication:

```python
import rowan
user = rowan.whoami()  # Returns user info if authenticated
print(f"User: {user.email}")
print(f"Credits available: {user.credits_available_string}")
```

### Webhook secret management

For webhook signature verification, manage secrets through your user account:

```python
import rowan

# Get your current webhook secret (returns None if none exists)
secret = rowan.get_webhook_secret()
if secret is None:
    secret = rowan.create_webhook_secret()
print(f"Secret key: {secret.secret}")

# Rotate your secret (invalidates old, creates new)
# Use this periodically for security
new_secret = rowan.rotate_webhook_secret()
print(f"New secret created (old secret disabled): {new_secret.secret}")

# Verify incoming webhook signatures
is_valid = rowan.verify_webhook_secret(
    request_body=b"...",           # Raw request body (bytes)
    signature="X-Rowan-Signature", # From request header
    secret=secret.secret
)
```

## Molecule input formats

Rowan accepts molecules in the following formats:

- **SMILES** (preferred): `"CCO"`, `"c1ccccc1O"`
- **SMARTS patterns** (for some workflows): subset of SMARTS for substructure matching
- **InChI** (if supported in your API version): `"InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"`

The API will validate input and raise a `rowan.ValidationError` if a molecule cannot be parsed. Always use canonicalized SMILES for reproducibility.

**Tip:** Use RDKit to validate SMILES before submission:

```python
from rdkit import Chem
smiles = "CCO"
mol = Chem.MolFromSmiles(smiles)
if mol is None:
    raise ValueError(f"Invalid SMILES: {smiles}")
```

## Core usage pattern

Most Rowan tasks follow the same three-step pattern:

1. **Submit** a workflow
2. **Wait** for completion (with optional streaming)
3. **Retrieve** typed results with convenience properties

```python
import rowan

# 1. Submit — use the specific workflow function (not the generic submit_workflow)
workflow = rowan.submit_descriptors_workflow(
    "CC(=O)Oc1ccccc1C(=O)O",
    name="aspirin descriptors",
)

# 2. & 3. Wait and retrieve
result = workflow.result()  # Blocks until done (default: wait=True, poll_interval=5)
print(result.data)              # Raw dict
print(result.descriptors['MW']) # 180.16 — use result.descriptors dict, not result.molecular_weight
```

For long-running workflows, use streaming:

```python
for partial in workflow.stream_result(poll_interval=5):
    print(f"Progress: {partial.complete}%")
    print(partial.data)
```

### result() vs. stream_result()

| Pattern | Use When | Duration |
|---------|----------|----------|
| `result()` | You can wait for the full result | <5 min typical |
| `stream_result()` | You want progress feedback or need early partial results | >5 min, or interactive use |

**Guideline:** Use `result()` for descriptors, pKa. Use `stream_result()` for conformer search, docking, cofolding.

## Working with results

Rowan's API includes **typed workflow result objects** with convenience properties.

### Using typed properties and .data

Results have two access patterns:

1. **Convenience properties** (recommended first): `result.descriptors`, `result.best_pose`, `result.conformer_energies`
2. **Raw fallback**: `result.data` — raw dictionary from the API

Example:

```python
result = rowan.submit_descriptors_workflow(
    "CCO",
    name="ethanol",
).result()

# Convenience property (returns dict of all descriptors):
print(result.descriptors['MW'])   # 46.042
print(result.descriptors['SLogP'])  # -0.001
print(result.descriptors['TPSA'])   # 57.96

# Raw data fallback (descriptors are nested under 'descriptors' key):
print(result.data['descriptors'])
# {'MW': 46.042, 'SLogP': -0.001, 'TPSA': 57.96, 'nHBDon': 1.0, 'nHBAcc': 1.0, ...}
```

**Note:** `DescriptorsResult` does **not** have a `molecular_weight` property. Descriptor keys use short names (`MW`, `SLogP`, `nHBDon`) not verbose names.

### Cache invalidation

Some result properties are lazily loaded (e.g., conformer geometries, protein structures). To refresh:

```python
result.clear_cache()
new_structures = result.conformer_molecules  # Refetched
```

## Projects, folders, and organization

For nontrivial campaigns, use projects and folders to keep work organized.

### Projects

```python
import rowan

# Create a project
project = rowan.create_project(name="CDK2 lead optimization")
rowan.set_project("CDK2 lead optimization")

# All subsequent workflows go into this project
wf = rowan.submit_descriptors_workflow("CCO", name="test compound")

# Retrieve later
project = rowan.retrieve_project("CDK2 lead optimization")
workflows = rowan.list_workflows(project=project, size=50)
```

### Folders

```python
# Create a hierarchical folder structure
folder = rowan.create_folder(name="docking/batch_1/screening")

wf = rowan.submit_docking_workflow(
    # ... docking params ...
    folder=folder,
    name="compound_001",
)

# List workflows in a folder
results = rowan.list_workflows(folder=folder)
```

## Workflow decision trees

### pKa vs. MacropKa

**Use microscopic pKa when:**

- You need the pKa of a single ionizable group
- You're interested in acid–base transitions and protonation thermodynamics
- The molecule has one or two ionizable sites
- Speed is critical (faster, fewer credits)

**Use macropKa when:**

- You need pH-dependent behavior across a physiologically relevant range (e.g., 0–14)
- You want aggregated charge and protonation-state populations across pH
- The molecule has multiple ionizable groups with coupled protonation
- You need downstream properties like aqueous solubility at different pH

**Example decision:**

```text
Phenol (pKa ~10): Use microscopic pKa
Amine (pKa ~9–10): Use microscopic pKa
Multi-ionizable drug (N, O, acidic group): Use macropKa
ADME assessment across GI pH: Use macropKa
```

### Conformer search vs. tautomer search

**Use conformer search when:**

- A single tautomeric form is known
- You need a diverse 3D ensemble for docking, MD, or SAR analysis
- Rotatable bonds dominate the chemical space

**Use tautomer search when:**

- Tautomeric equilibrium is uncertain (e.g., heterocycles, keto–enol systems)
- You need to model all relevant protonation isomers
- Downstream calculations (docking, pKa) depend on tautomeric form

**Combined workflow:**

```python
# Step 1: Find best tautomer
taut_wf = rowan.submit_tautomer_search_workflow(
    initial_molecule="O=c1[nH]ccnc1",
    name="imidazole tautomers",
)
best_taut = taut_wf.result().best_tautomer

# Step 2: Generate conformers from best tautomer
conf_wf = rowan.submit_conformer_search_workflow(
    initial_molecule=best_taut,
    name="imidazole conformers",
)
```

### Docking vs. analogue docking vs. cofolding

| Workflow | Use When | Input | Output |
|----------|----------|-------|--------|
| Docking | Single ligand, known pocket | Protein + SMILES + pocket coords | Pose, score, dG |
| Analogue docking | 5–100+ related compounds | Protein + SMILES list + reference ligand | All poses, reference-aligned |
| Protein-ligand cofolding | Sequence + ligand, no crystal structure | Protein sequence + SMILES | ML-predicted bound complex |

## Common workflow categories

### 1. Descriptors

A lightweight entry point for batch triage, SAR, or exploratory scripts.

```python
wf = rowan.submit_descriptors_workflow(
    "CC(=O)Oc1ccccc1C(=O)O",  # positional arg, accepts SMILES string
    name="aspirin descriptors",
)

result = wf.result()
print(result.descriptors['MW'])    # 180.16
print(result.descriptors['SLogP']) # 1.19
print(result.descriptors['TPSA'])  # 59.44
print(result.data['descriptors'])
# {'MW': 180.16, 'SLogP': 1.19, 'TPSA': 59.44, 'nHBDon': 1.0, 'nHBAcc': 4.0, ...}
```

**Common descriptor keys:**

| Key | Description | Typical drug range |
|-----|-------------|-------------------|
| `MW` | Molecular weight (Da) | <500 (Lipinski) |
| `SLogP` | Calculated LogP (lipophilicity) | -2 to +5 |
| `TPSA` | Topological polar surface area (Å²) | <140 for oral bioavailability |
| `nHBDon` | H-bond donor count | ≤5 (Lipinski) |
| `nHBAcc` | H-bond acceptor count | ≤10 (Lipinski) |
| `nRot` | Rotatable bond count | <10 for oral drugs |
| `nRing` | Ring count | — |
| `nHeavyAtom` | Heavy atom count | — |
| `FilterItLogS` | Estimated aqueous solubility (LogS) | >-4 preferred |
| `Lipinski` | Lipinski Ro5 pass (1.0) or fail (0.0) | — |

The result contains hundreds of additional molecular descriptors (BCUT, GETAWAY, WHIM, etc.); access any via `result.descriptors['key']`.

### 2. Microscopic pKa

For protonation-state energetics and acid/base behavior of a specific structure.

Two methods are available:

| Method | Input | Speed | Covers | Use when |
|--------|-------|-------|--------|----------|
| `chemprop_nevolianis2025` | SMILES string | Fast | Deprotonation only (anionic conjugate bases) | Acidic groups only; quick screening |
| `starling` | SMILES string | Fast | Acid + base (full protonation/deprotonation) | Most drug-like molecules; preferred SMILES method |
| `aimnet2_wagen2024` (default) | 3D molecule object | Slower, higher accuracy | Acid + base | You already have a 3D structure (e.g. from conformer search) |

```python
# Fast path: SMILES input with full acid+base coverage (use starling method when available)
wf = rowan.submit_pka_workflow(
    initial_molecule="c1ccccc1O",       # phenol SMILES; param is initial_molecule, not initial_smiles
    method="starling",   # fast SMILES method, covers acid+base; chemprop_nevolianis2025 is deprotonation-only
    name="phenol pKa",
)

result = wf.result()
print(result.strongest_acid)    # 9.81 (pKa of the most acidic site)
print(result.conjugate_bases)   # list of {pka, smiles, atom_index, ...} per deprotonatable site
```

### 3. MacropKa

For pH-dependent protonation behavior across a range.

```python
wf = rowan.submit_macropka_workflow(
    initial_smiles="CN1CCN(CC1)C2=NC=NC3=CC=CC=C32",  # imidazole
    min_pH=0,
    max_pH=14,
    min_charge=-2,  # default
    max_charge=2,   # default
    compute_aqueous_solubility=True,  # default
    name="imidazole macropKa",
)

result = wf.result()
print(result.pka_values)               # list of pKa values
print(result.logd_by_ph)               # dict of {pH: logD}
print(result.aqueous_solubility_by_ph) # dict of {pH: solubility}
print(result.isoelectric_point)        # isoelectric point
print(result.data)
# {'pKa_values': [...], 'logD_by_pH': {...}, 'aqueous_solubility_by_pH': {...}, ...}
```

### 4. Conformer search

For 3D ensemble generation when ensemble quality matters.

```python
wf = rowan.submit_conformer_search_workflow(
    initial_molecule="CCOC(=O)N1CCC(CC1)Oc1ncnc2ccccc12",
    num_conformers=50,  # Optional: override default
    name="conformer search",
)

result = wf.result()
print(result.conformer_energies)  # [0.0, 1.2, 2.5, ...]
print(result.conformer_molecules)  # List of 3D molecules
print(result.best_conformer)  # Lowest-energy conformer
```

### 5. Tautomer search

For heterocycles and systems where tautomer state affects downstream modeling.

```python
wf = rowan.submit_tautomer_search_workflow(
    initial_molecule="O=c1[nH]ccnc1",  # or keto tautomer
    name="imidazolone tautomers",
)

result = wf.result()
print(result.best_tautomer)  # Most stable SMILES string
print(result.tautomers)      # List of tautomeric SMILES
print(result.molecules)      # List of molecule objects
```

### 6. Docking

For protein-ligand docking with optional pose refinement and conformer generation.

```python
# Upload protein once, reuse in multiple workflows
protein = rowan.upload_protein(
    name="CDK2",
    file_path="cdk2.pdb",
)

# Define binding pocket
pocket = {
    "center": [10.5, 24.2, 31.8],
    "size": [18.0, 18.0, 18.0],
}

# Submit docking
wf = rowan.submit_docking_workflow(
    protein=protein,
    pocket=pocket,
    initial_molecule="CCNc1ncc(c(Nc2ccc(F)cc2)n1)-c1cccnc1",
    do_pose_refinement=True,
    do_conformer_search=True,
    name="lead docking",
)

result = wf.result()
print(result.scores)  # Docking scores (kcal/mol)
print(result.best_pose)  # Mol object with 3D coordinates
print(result.data)  # Raw result dict
```

**Protein preparation tips:**

- PDB files should be reasonably clean (remove water/heteroatoms unless intended)
- Use the same protein object across a docking series for consistency
- If you have a PDB ID, use `rowan.create_protein_from_pdb_id()` instead

### 7. Analogue docking

For placing a compound series into a shared binding context.

```python
# Analogue series (e.g., SAR campaign)
analogues = [
    "CCNc1ncc(c(Nc2ccc(F)cc2)n1)-c1cccnc1",    # reference
    "CCNc1ncc(c(Nc2ccc(Cl)cc2)n1)-c1cccnc1",   # chloro
    "CCNc1ncc(c(Nc2ccc(OC)cc2)n1)-c1cccnc1",   # methoxy
    "CCNc1ncc(c(Nc2cc(C)c(F)cc2)n1)-c1cccnc1", # methyl, fluoro
]

wf = rowan.submit_analogue_docking_workflow(
    analogues=analogues,
    initial_molecule=analogues[0],  # Reference ligand
    protein=protein,
    pocket=pocket,
    name="SAR series docking",
)

result = wf.result()
print(result.analogue_scores)  # List of scores for each analogue
print(result.best_poses)  # List of poses
```

### 8. MSA generation

For multiple-sequence alignment (useful for downstream cofolding).

```python
wf = rowan.submit_msa_workflow(
    initial_protein_sequences=[
        "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVP"
    ],
    output_formats=["colabfold", "chai", "boltz"],
    name="target MSA",
)

result = wf.result()
result.download_files()  # Downloads alignments to disk
```

### 9. Protein-ligand cofolding

For AI-based bound-complex prediction when no crystal structure is available.

```python
wf = rowan.submit_protein_cofolding_workflow(
    initial_protein_sequences=[
        "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVP"
    ],
    initial_smiles_list=[
        "CCNc1ncc(c(Nc2ccc(F)cc2)n1)-c1cccnc1"
    ],
    name="protein-ligand cofolding",
)

result = wf.result()
print(result.predictions)  # List of predicted structures
print(result.messages)  # Model metadata/warnings

predicted_structure = result.get_predicted_structure()
predicted_structure.write("predicted_complex.pdb")
```

## All supported workflow types

All workflows follow the same submit → wait → retrieve pattern and support webhooks and project/folder organization.

### Core molecular modeling workflows

| Workflow | Function | When to use |
|----------|----------|-------------|
| Descriptors | `submit_descriptors_workflow` | First-pass triage: MW, LogP, TPSA, HBA/HBD, Lipinski filter |
| pKa | `submit_pka_workflow` | Single ionizable group; need protonation thermodynamics |
| MacropKa | `submit_macropka_workflow` | Multi-ionizable drugs; pH-dependent charge/LogD/solubility |
| Conformer Search | `submit_conformer_search_workflow` | 3D ensemble for docking, MD, or SAR; known tautomer |
| Tautomer Search | `submit_tautomer_search_workflow` | Heterocycles, keto–enol; uncertain tautomeric form |
| Solubility | `submit_solubility_workflow` | Aqueous or solvent-specific solubility prediction |
| Membrane Permeability | `submit_membrane_permeability_workflow` | Caco-2, PAMPA, BBB, plasma permeability |
| ADMET | `submit_admet_workflow` | Broad drug-likeness and ADMET property sweep |

### Structure-based design workflows

| Workflow | Function | When to use |
|----------|----------|-------------|
| Docking | `submit_docking_workflow` | Single ligand, known binding pocket |
| Analogue Docking | `submit_analogue_docking_workflow` | SAR series (5–100+ compounds) in a shared pocket |
| Batch Docking | `submit_batch_docking_workflow` | Fast library screening; large compound sets |
| Protein MD | `submit_protein_md_workflow` | Long-timescale dynamics; conformational sampling |
| Pose Analysis MD | `submit_pose_analysis_md_workflow` | MD refinement of a docking pose |
| Protein Cofolding | `submit_protein_cofolding_workflow` | No crystal structure; AI-predicted bound complex |
| Protein Binder Design | `submit_protein_binder_design_workflow` | De novo binder generation against a protein target |

### Advanced computational chemistry

| Workflow | Function | When to use |
|----------|----------|-------------|
| Basic Calculation | `submit_basic_calculation_workflow` | QM/ML geometry optimization or single-point energy |
| Electronic Properties | `submit_electronic_properties_workflow` | Dipole, partial charges, HOMO-LUMO, ESP |
| BDE | `submit_bde_workflow` | Bond dissociation energies; metabolic soft-spot prediction |
| Redox Potential | `submit_redox_potential_workflow` | Oxidation/reduction potentials |
| Spin States | `submit_spin_states_workflow` | Spin-state energy ordering for organometallics/radicals |
| Strain | `submit_strain_workflow` | Conformational strain relative to global minimum |
| Scan | `submit_scan_workflow` | PES scans; torsion profiles |
| Multistage Optimization | `submit_multistage_opt_workflow` | Progressive optimization across levels of theory |

### Reaction chemistry

| Workflow | Function | When to use |
|----------|----------|-------------|
| Double-Ended TS Search | `submit_double_ended_ts_search_workflow` | Transition state between two known structures |
| IRC | `submit_irc_workflow` | Confirm TS connectivity; intrinsic reaction coordinate |

### Advanced properties

| Workflow | Function | When to use |
|----------|----------|-------------|
| NMR | `submit_nmr_workflow` | Predicted 1H/13C chemical shifts for structure verification |
| Ion Mobility | `submit_ion_mobility_workflow` | Collision cross-section (CCS) for MS method development |
| Hydrogen Bond Strength | `submit_hydrogen_bond_basicity_workflow` | H-bond donor/acceptor strength for formulation/solubility |
| Fukui | `submit_fukui_workflow` | Site reactivity indices for electrophilic/nucleophilic attack |
| Interaction Energy Decomposition | `submit_interaction_energy_decomposition_workflow` | Fragment-level interaction analysis |

### Binding free energy

| Workflow | Function | When to use |
|----------|----------|-------------|
| RBFE/FEP | `submit_relative_binding_free_energy_perturbation_workflow` | Relative ΔΔG for congeneric series |
| RBFE Graph | `submit_rbfe_graph_workflow` | Build and optimize an RBFE perturbation network |

### Sequence and structural biology

| Workflow | Function | When to use |
|----------|----------|-------------|
| MSA | `submit_msa_workflow` | Multiple sequence alignment for cofolding (ColabFold, Chai, Boltz) |
| Solvent-Dependent Conformers | `submit_solvent_dependent_conformers_workflow` | Solvation-aware conformer ensembles |

## Batch submission and retrieval

For libraries or analogue series, submit in a loop using the specific workflow function. The generic `rowan.batch_submit_workflow()` and `rowan.submit_workflow()` functions currently return 422 errors from the API — use the named functions (`submit_descriptors_workflow`, `submit_pka_workflow`, etc.) instead.

### Submit a batch

```python
smileses = ["CCO", "CC(=O)O", "c1ccccc1O"]
names = ["ethanol", "acetic acid", "phenol"]

workflows = [
    rowan.submit_descriptors_workflow(smi, name=name)
    for smi, name in zip(smileses, names)
]

print(f"Submitted {len(workflows)} workflows")
```

### Poll batch status

```python
statuses = rowan.batch_poll_status([wf.uuid for wf in workflows])
# Returns aggregate counts — not per-UUID:
# {'queued': 0, 'running': 1, 'complete': 2, 'failed': 0, 'total': 3, ...}

if statuses["complete"] == statuses["total"]:
    print("All workflows done")
elif statuses["failed"] > 0:
    print(f"{statuses['failed']} workflows failed")
```

### Retrieve and collect results

```python
results = []
for wf in workflows:
    try:
        result = wf.result()
        results.append(result.data)
    except rowan.WorkflowError as e:
        print(f"Workflow {wf.uuid} failed: {e}")

# Optionally aggregate into DataFrame
import pandas as pd
df = pd.DataFrame(results)
```

### Non-blocking / fire-and-check pattern

For long-running workflows where you don't want to hold a process open, submit workflows, save their UUIDs, and check back later in a separate process.

**Session 1 — submit and save UUIDs:**

```python
import rowan, json

rowan.api_key = "..."
smileses = ["CCO", "CC(=O)O", "c1ccccc1O"]

workflows = [
    rowan.submit_descriptors_workflow(smi, name=f"compound_{i}")
    for i, smi in enumerate(smileses)
]

# Save UUIDs to disk (or a database)
uuids = [wf.uuid for wf in workflows]
with open("workflow_uuids.json", "w") as f:
    json.dump(uuids, f)

print("Submitted. Check back later.")
```

**Session 2 — check status and collect results when ready:**

```python
import rowan, json

rowan.api_key = "..."

with open("workflow_uuids.json") as f:
    uuids = json.load(f)

results = []
for uuid in uuids:
    wf = rowan.retrieve_workflow(uuid)
    if wf.done():
        result = wf.result(wait=False)
        results.append({"uuid": uuid, "data": result.data})
    else:
        print(f"{uuid}: still running ({wf.status})")

print(f"Collected {len(results)} completed results")
```

## Webhooks and asynchronous workflows

For long-running campaigns or when you don't want to keep a process alive, use webhooks to notify your backend when workflows complete.

### Setting up webhooks

Every workflow submission function accepts a `webhook_url` parameter:

```python
wf = rowan.submit_docking_workflow(
    protein=protein,
    pocket=pocket,
    initial_molecule="CCO",
    webhook_url="https://myserver.com/rowan_callback",
    name="docking with webhook",
)

print(f"Workflow submitted. Result will be POSTed to webhook when complete.")
```

Webhook URLs can be passed to any specific workflow function (`submit_docking_workflow()`, `submit_pka_workflow()`, `submit_descriptors_workflow()`, etc.).

### Webhook authentication with secrets

Rowan supports webhook signature verification to ensure requests are authentic. You'll need to:

1. **Create or retrieve a webhook secret:**

```python
import rowan

# Create a new webhook secret
secret = rowan.create_webhook_secret()
print(f"Your webhook secret: {secret.secret}")

# Or retrieve an existing secret
secret = rowan.get_webhook_secret()

# Rotate your secret (invalidates old one, creates new)
new_secret = rowan.rotate_webhook_secret()
```

2. **Verify incoming webhook requests:**

```python
import rowan
import hmac
import json

def verify_webhook(request_body: bytes, signature: str, secret: str) -> bool:
    """Verify the HMAC-SHA256 signature of a webhook request."""
    return rowan.verify_webhook_secret(request_body, signature, secret)
```

### Webhook payload and signature

When a workflow completes, Rowan POSTs a JSON payload to your webhook URL with the header:

```text
X-Rowan-Signature: <HMAC-SHA256 signature>
```

The request body contains the complete workflow result:

```json
{
  "workflow_uuid": "wf_12345abc",
  "workflow_type": "docking",
  "workflow_name": "lead docking",
  "status": "COMPLETED_OK",
  "created_at": "2025-04-01T12:00:00Z",
  "completed_at": "2025-04-01T12:15:30Z",
  "data": {
    "scores": [-8.2, -8.0, -7.9],
    "best_pose": {...},
    "metadata": {...}
  }
}
```

### Example webhook handler with signature verification (FastAPI)

```python
from fastapi import FastAPI, Request, HTTPException
import rowan
import json

app = FastAPI()
_ws = rowan.get_webhook_secret() or rowan.create_webhook_secret()
webhook_secret = _ws.secret

@app.post("/rowan_callback")
async def handle_rowan_webhook(request: Request):
    # Get request body and signature
    body = await request.body()
    signature = request.headers.get("X-Rowan-Signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing X-Rowan-Signature header")

    # Verify signature
    if not rowan.verify_webhook_secret(body, signature, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse and process
    payload = json.loads(body)
    wf_uuid = payload["workflow_uuid"]
    status = payload["status"]

    if status == "COMPLETED_OK":
        print(f"Workflow {wf_uuid} succeeded!")
        result_data = payload["data"]
        # Process result, update database, trigger next workflow, etc.
    elif status == "FAILED":
        print(f"Workflow {wf_uuid} failed!")
        # Handle failure

    # Respond quickly to prevent retries
    return {"status": "received"}
```

### Webhook best practices

- **Always verify signatures** using `rowan.verify_webhook_secret()` to ensure requests are from Rowan
- **Respond quickly** (< 5 seconds); offload heavy processing to async tasks or background jobs
- **Implement idempotency**: workflows may retry; handle duplicate payloads gracefully using `workflow_uuid`
- **Log all events** for debugging and audit trails
- **Use for long campaigns**: webhooks shine with 50+ workflows; for small jobs, polling with `result()` is simpler
- **Rotate secrets regularly** using `rowan.rotate_webhook_secret()` for security
- **Return 2xx status** to confirm receipt; Rowan may retry on 5xx errors

## Protein utilities

### Upload proteins

```python
# From local PDB file
protein = rowan.upload_protein(
    name="egfr_kinase_domain",
    file_path="egfr_kinase.pdb",
)

# From PDB database
protein_from_pdb = rowan.create_protein_from_pdb_id(
    name="CDK2 (1M17)",
    code="1M17",
)

# Retrieve previously uploaded protein
protein = rowan.retrieve_protein("protein-uuid")

# List all proteins
my_proteins = rowan.list_proteins()
```

### Protein preparation guidance

- **File format**: PDB, mmCIF (Rowan auto-detects)
- **Water molecules**: Rowan usually keeps relevant water; remove bulk water beforehand if desired
- **Heteroatoms**: Cofactors, ions, and bound ligands are usually preserved; remove unwanted heteroatoms before upload
- **Multi-chain proteins**: Fully supported
- **Resolution**: Works with NMR structures, homology models, and cryo-EM; quality matters for downstream predictions
- **Validation**: Rowan validates PDB syntax; severely malformed files may be rejected

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
        smi, name=f"analog_{i}", folder=folder,
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
        smi, method="chemprop_nevolianis2025", name=f"pka_{i}", folder=folder,
    )
    for i, smi in enumerate(best_tautomers)
]

descriptor_workflows = [
    rowan.submit_descriptors_workflow(smi, name=f"desc_{i}", folder=folder)
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
            "mw": desc.get("MW"),
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
# compound names are "pka_0", "pka_1", etc. — extract index to look up SMILES
top_idx = int(df.loc[df["pka"].idxmin(), "compound"].split("_")[1])
top_smiles = best_tautomers[top_idx]

print(f"\nProceeding with docking: {top_smiles}")

# 8. Docking campaign
protein = rowan.create_protein_from_pdb_id(name="CDK2_1CKP", code="1CKP")
pocket = {"center": [10.5, 24.2, 31.8], "size": [18.0, 18.0, 18.0]}

docking_wf = rowan.submit_docking_workflow(
    protein=protein,
    pocket=pocket,
    initial_molecule=top_smiles,
    do_pose_refinement=True,
    name=f"docking_{top_compound}",
)

dock_result = docking_wf.result()
print(f"\nDocking score: {dock_result.scores[0]:.2f} kcal/mol")
print(f"Best pose saved to: best_pose.pdb")
dock_result.best_pose.write("best_pose.pdb")
```

## Error handling and troubleshooting

### Common errors and solutions

```python
import rowan

# Error 1: Invalid SMILES
try:
    wf = rowan.submit_descriptors_workflow("CCCC(CC", name="bad smiles")  # Invalid
except rowan.ValidationError as e:
    print(f"Invalid SMILES: {e}")
    # Solution: Use RDKit to validate before submission
    from rdkit import Chem
    smi = Chem.MolToSmiles(Chem.MolFromSmiles(smi))

# Error 2: API key not set
try:
    wf = rowan.submit_descriptors_workflow("CCO")
except rowan.AuthenticationError:
    print("API key not found. Set ROWAN_API_KEY env var or call rowan.api_key = '...'")

# Error 3: Insufficient credits
try:
    wf = rowan.submit_protein_cofolding_workflow(...)
except rowan.InsufficientCreditsError as e:
    print(f"Not enough credits: {e}. Purchase more or reduce job size.")

# Error 4: Workflow failed (bad molecule, etc.)
try:
    wf = rowan.submit_docking_workflow(...)
    result = wf.result()
except rowan.WorkflowError as e:
    print(f"Workflow failed: {e}")
    # Check wf.status for details
    print(f"Status: {wf.status}")

# Error 5: Workflow not yet done — poll manually
result = wf.result(wait=True, poll_interval=5)  # waits and polls every 5s
# Or check status without blocking:
if not wf.done():
    print("Workflow still running. Call wf.result() again later.")
```

### Debugging tips

- **Check workflow status**: `wf.status`, check `wf.done()`, or call `wf.get_status()`
- **Inspect raw result**: `result.data` instead of convenience properties
- **Re-run failed workflow**: Save UUIDs and retry with `rowan.retrieve_workflow(uuid)`
- **Validate molecules beforehand**: Use RDKit or Chemaxon before batch submission

## Recommended usage patterns

- **Prefer Rowan-native workflows** over low-level assembly when they exist
- **Use projects and folders** for any nontrivial campaign (>5 workflows)
- **Use `result()` to block until complete** (default: `wait=True, poll_interval=5`)
- **Use typed result properties first**, fall back to `.data` for unmapped fields
- **Use batch submission** for compound libraries or analogue series
- **Chain workflows** for multi-step chemistry campaigns:
  - `pKa → macropKa → permeability` (ADME assessment)
  - `tautomer search → docking → pose-analysis MD` (pose refinement)
  - `MSA generation → protein-ligand cofolding` (AI structure prediction)
- **Use webhooks** for long-running campaigns (>50 workflows) or asynchronous pipelines
- **Use streaming** for interactive feedback on large conformer/docking searches

## Summary

Use Rowan when your workflow requires cloud execution for molecular-design tasks, especially when you want one unified API and consistent result handling across small-molecule modeling, proteins, docking, ADME prediction, and ML structure generation.

Rowan is a molecular-design workflow platform, not just a remote chemistry engine. It handles infrastructure scaling, result persistence, and multi-step pipeline orchestration so you can focus on science.
