---
name: rowan
description: Rowan is a cloud-native molecular modeling and medicinal-chemistry workflow platform with a Python API. Use for pKa and macropKa prediction, conformer and tautomer ensembles, docking and analogue docking, protein-ligand cofolding, MSA generation, molecular dynamics, permeability, descriptor workflows, and related small-molecule or protein modeling tasks. Ideal for programmatic batch screening, multi-step chemistry pipelines, and workflows that would otherwise require maintaining local HPC/GPU infrastructure.
license: Proprietary (API key required)
compatibility: Python 3.12+, API key required
metadata:
  version: "1.5"
  skill-author: Rowan Science
  trigger-keywords: pKa prediction, molecular docking, conformer search, chemistry workflow, drug discovery, SMILES, protein structure, batch molecular modeling, cloud chemistry
  openclaw:
    primaryEnv: ROWAN_API_KEY
    envVars:
    - name: ROWAN_API_KEY
      required: true
      description: Rowan computational chemistry API key.
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

## Quick start

```bash
uv pip install rowan-python
```

```python
import rowan
rowan.api_key = "your_api_key_here"  # or set ROWAN_API_KEY env var

# Descriptors require a 3D Molecule, not a bare SMILES string.
mol = rowan.Molecule.from_smiles("CC(=O)Oc1ccccc1C(=O)O")
wf = rowan.submit_descriptors_workflow(mol, name="aspirin")
result = wf.result()

print(result.descriptors["MW"])       # 180.042 — exact mass
print(result.descriptors["SLogP"])    # 1.31
print(result.descriptors["TopoPSA"])  # 63.6 — topological PSA
```

If that prints without error, you're set up correctly. These values and examples
were verified against `rowan-python` 3.1.13.

## Installation

```bash
uv pip install rowan-python
# or: uv pip install rowan-python
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
print(f"Credits available: {user.credits_available_string()}")
```

## Molecule input formats

Rowan accepts molecules in the following formats:

- **SMILES** (preferred): `"CCO"`, `"c1ccccc1O"`
- **SMARTS patterns** (for some workflows): subset of SMARTS for substructure matching
- **InChI** (if supported in your API version): `"InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"`

The API validates molecule inputs and raises `ValueError` for an unparseable
SMILES or a workflow-incompatible input type. Always use canonicalized SMILES
for reproducibility.

### SMILES strings versus molecule objects

Accepted input types vary by workflow in `rowan-python` 3.1.13. Only these
common workflows accept a bare string: pKa, conformer search, membrane
permeability, ADMET, LogP, macropKa, solubility, and pose-analysis MD. Most
others — including descriptors, tautomer search, docking, analogue docking,
BDE, NMR, and Fukui — require `rowan.Molecule.from_smiles(smiles)` or an RDKit
`Mol`/`RWMol`. A wrong type raises `ValueError` before submission.

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
    rowan.Molecule.from_smiles("CC(=O)Oc1ccccc1C(=O)O"),
    name="aspirin descriptors",
)

# 2. & 3. Wait and retrieve
result = workflow.result()  # Blocks until done (default: wait=True, poll_interval=5)
print(result.data)              # Raw dict
print(result.descriptors["MW"]) # 180.042 exact mass; no result.molecular_weight property
```

For long-running workflows, use streaming:

```python
for partial in workflow.stream_result(poll_interval=5):
    print(f"Complete: {partial.complete}")  # bool, not a percentage
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

1. **Convenience properties** (recommended first): `result.descriptors`, `result.best_pose`, `result.scores`. Result classes differ: conformer search uses `get_energies()` and `get_conformers()` methods.
2. **Raw fallback**: `result.data` — raw dictionary from the API

Example:

```python
result = rowan.submit_descriptors_workflow(
    rowan.Molecule.from_smiles("CCO"),
    name="ethanol",
).result()

# Convenience property (returns all descriptors):
print(result.descriptors["MW"])       # exact/monoisotopic mass
print(result.descriptors["SLogP"])
print(result.descriptors["TopoPSA"])  # usual topological PSA

# Raw data fallback:
print(result.data["descriptors"])
```

**Note:** `DescriptorsResult` does **not** have a `molecular_weight` property.
`MW` is exact/monoisotopic mass, not average molecular weight. `TPSA` is a 3D
charged-surface descriptor; use `TopoPSA` for the usual topological polar
surface area used in drug-likeness rules.

### Cache invalidation

Some result properties are lazily loaded (e.g., conformer geometries, protein structures). To refresh:

```python
result.clear_cache()
new_structures = result.get_conformers()  # Refetched for ConformerSearchResult
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
wf = rowan.submit_descriptors_workflow(
    rowan.Molecule.from_smiles("CCO"), name="test compound"
)

# retrieve_project takes a UUID; list_workflows scopes with parent_uuid.
project = rowan.retrieve_project(project.uuid)
workflows = rowan.list_workflows(parent_uuid=project.uuid, size=50)
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
results = rowan.list_workflows(parent_uuid=folder.uuid)
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
    initial_molecule=rowan.Molecule.from_smiles("O=c1[nH]ccnc1"),
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

## Workflow catalog

Nine common workflow categories — descriptors, microscopic pKa, MacropKa, conformer
search, tautomer search, docking, analogue docking, MSA generation, and protein-ligand
cofolding — each with submission code and result shapes, plus the complete list of every
supported workflow type (core modeling, structure-based design, advanced computational
chemistry, reaction chemistry, advanced properties, binding free energy, and sequence and
structural biology) are in
[references/workflow_catalog.md](references/workflow_catalog.md).

## Batch submission, webhooks, and asynchronous work

Batch submit/poll/retrieve, the non-blocking fire-and-check pattern, webhook setup,
secret creation and rotation, payload and signature verification (with a FastAPI
handler), and webhook best practices are in
[references/batch_and_webhooks.md](references/batch_and_webhooks.md).

## Access, pricing, and credits

Free-tier limits, credit consumption per workflow, and typical cost estimates are in
[references/access_and_pricing.md](references/access_and_pricing.md).

## Worked example and troubleshooting

A full lead-optimization campaign — project setup, tautomers, pKa across an analogue
series, result collection, and a docking follow-up — is in
[references/end_to_end_example.md](references/end_to_end_example.md).

Common errors with their fixes, and debugging tips, are in
[references/troubleshooting.md](references/troubleshooting.md).

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
