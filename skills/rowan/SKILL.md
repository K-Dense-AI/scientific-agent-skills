---
name: rowan
description: Rowan is a cloud-native molecular modeling and medicinal-chemistry workflow platform with a Python API. Use for pKa and macropKa prediction, conformer and tautomer ensembles, docking and analogue docking, protein-ligand cofolding, MSA generation, molecular dynamics, permeability, descriptor workflows, and related small-molecule or protein modeling tasks. Ideal for programmatic batch screening, multi-step chemistry pipelines, and workflows that would otherwise require maintaining local HPC/GPU infrastructure.
license: Proprietary (API key required)
compatibility: Python 3.12+ with rowan-python and its RDKit/stjames dependencies. Requires network access and ROWAN_API_KEY for hosted workflows.
metadata:
  version: "1.7"
  last-reviewed: "2026-09-30"
  upstream-version: "rowan-python 3.2.0"
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

Use Rowan when you want to run medicinal-chemistry or molecular-design workflows programmatically without maintaining local HPC infrastructure, GPU provisioning, or a collection of separate modeling tools. The service manages hosted compute and results; available workflows depend on the account.

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
- Methods or element/charge regimes outside the selected engine's documented support

## Quick start

```bash
uv pip install "rowan-python==3.2.0"
```

```python
import rowan
# Reads ROWAN_API_KEY from the environment.

# Descriptors require a 3D Molecule, not a bare SMILES string.
mol = rowan.Molecule.from_smiles("CC(=O)Oc1ccccc1C(=O)O")
wf = rowan.submit_descriptors_workflow(mol, name="aspirin")
result = wf.result()

print(result.descriptors["MW"])       # exact/monoisotopic mass
print(result.descriptors["SLogP"])
print(result.descriptors["TopoPSA"])  # topological PSA
```

This submits a hosted calculation and consumes credits. Examples target
[`rowan-python` 3.2.0](https://pypi.org/project/rowan-python/3.2.0/), reviewed
2026-09-30 against the released SDK and [official reference](https://docs.rowansci.com/api/python/v3/).
Local schema/serialization smoke tests used `stjames` 0.0.279. Hosted examples
are illustrative: no authenticated workflows were run for this refresh. Lock
both package versions for a reproducible campaign.

## Installation

```bash
uv pip install "rowan-python==3.2.0"
# Lock dependencies in your own environment; do not install the unrelated "rowan" package.
```

## Authentication and account access

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
print(user.enabled_workflows)  # Account-specific backend workflow slugs
```

## Molecule input formats

Use SMILES for topology-based methods and real 3D structures for geometry-based
methods. SMARTS is a substructure-query language, not a general workflow molecule
input; convert InChI with a chemistry toolkit before passing a supported input.
Record stereochemistry, charge, protonation state, and the original identifier.
Canonicalization alone does not resolve these scientific choices.

### SMILES strings versus molecule objects

- pKa: `starling` and `chemprop_nevolianis2025` require a SMILES string;
  `gxtb_wagen2026` (default) and `aimnet2_wagen2024` require coordinates.
- Conformer search: SMILES works with OpenConf (default) or ETKDG; CREST/MCMM
  require a 3D molecule.
- Membrane permeability: `gnn-mtl` requires SMILES; `pypermm` requires a 3D molecule.
- ADMET, LogP, macropKa, and solubility are SMILES-based; pose-analysis MD needs
  ligand SMILES **and a protein complex containing its bound pose**.
- Descriptors, tautomers, docking, analogue docking, BDE, NMR, and Fukui need a
  `rowan.Molecule`, `stjames.Molecule`, or RDKit molecule with a conformer.
  `Chem.MolFromSmiles()` alone has no coordinates. Generate them explicitly with
  `rowan.Molecule.from_smiles()` or import an existing geometry. For analogue
  docking, preserve the reference pose in the receptor's coordinate frame.

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

# 1. Submit — named functions build and validate workflow-specific payloads
workflow = rowan.submit_descriptors_workflow(
    rowan.Molecule.from_smiles("CC(=O)Oc1ccccc1C(=O)O"),
    name="aspirin descriptors",
)

# 2. & 3. Wait and retrieve
result = workflow.result()  # Blocks until done (default: wait=True, poll_interval=5)
print(result.data)              # Raw dict
print(result.descriptors["MW"]) # exact mass; no result.molecular_weight property
```

For long-running workflows, use streaming:

```python
for partial in workflow.stream_result(poll_interval=5):
    print(f"Complete: {partial.complete}")  # bool, not a percentage
    print(partial.data)
```

### result() vs. stream_result()

| Pattern | Use when |
|---|---|
| `result()` | The process can block for completion |
| `stream_result()` | Polling snapshots are useful while the job runs |

`stream_result()` polls; it is not a server-pushed event stream. Partial typed
properties may be unavailable, so inspect `.data` until `.complete` is true.
`result(wait=False)` can return partial data or raise `WorkflowError` if no data
exists yet. `done()` includes failed and stopped runs, not only successes.

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

Rowan 3.2.0 has an unresolved `Folder.created_at` type annotation; initialize
the model once as below before folder operations (see troubleshooting).

```python
import rowan
from datetime import datetime
rowan.Folder.model_rebuild(_types_namespace={"datetime": datetime})

# Create a project
project = rowan.create_project(name="CDK2 lead optimization")
rowan.project_uuid = project.uuid
folder = rowan.create_folder(name="descriptors", parent_uuid=project.root_folder_uuid)

# Pass the destination folder explicitly on submissions
wf = rowan.submit_descriptors_workflow(
    rowan.Molecule.from_smiles("CCO"), name="test compound", folder=folder
)

# parent_uuid is a folder UUID, not a project UUID.
project = rowan.retrieve_project(project.uuid)
workflows = rowan.list_workflows(parent_uuid=project.root_folder_uuid, page=0, size=50)
# This lists only workflows directly in the root folder. List folder.uuid for the above job.
```

### Folders

Illustrative: `protein`, `pocket`, and the 3D `ligand` must be prepared first.
Run the `Folder.model_rebuild` initialization above first. `get_folder()` creates
missing path segments; `create_folder()` creates one folder.

```python
# Create a hierarchical folder structure
folder = rowan.get_folder("docking/batch_1/screening")

wf = rowan.submit_docking_workflow(
    protein=protein, pocket=pocket, initial_molecule=ligand,
    folder=folder,
    name="compound_001",
)

# List workflows in a folder
results = rowan.list_workflows(parent_uuid=folder.uuid, page=0, size=50)
```

List helpers return one page. Increment the zero-based `page` until an empty
page; `size` is page size, not a promise to return every match. Folder listing
is not recursive: walk child folders separately when inventorying a campaign.

## Workflow decision trees

### pKa vs. MacropKa

**Use microscopic pKa when:**

- You need the pKa of a single ionizable group
- You're interested in acid–base transitions and protonation thermodynamics
- The molecule has one or two ionizable sites
- A specific microscopic transition is the scientific question

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
- You need same-formula proton-shift isomers; enumerate charge/protonation states separately
- Downstream calculations (docking, pKa) depend on tautomeric form

**Combined workflow:**

```python
# Step 1: Find best tautomer
taut_wf = rowan.submit_tautomer_search_workflow(
    initial_molecule=rowan.Molecule.from_smiles("O=c1cccc[nH]1"),
    name="2-pyridone tautomers",
)
best_taut = taut_wf.result().best_tautomer  # Molecule or None, not SMILES
if best_taut is None:
    raise RuntimeError("No weighted tautomer structure was returned")

# Step 2: Generate conformers from best tautomer
conf_wf = rowan.submit_conformer_search_workflow(
    initial_molecule=best_taut,
    name="2-pyridone conformers",
)
```

### Docking vs. analogue docking vs. cofolding

| Workflow | Use When | Input | Output |
|----------|----------|-------|--------|
| Docking | Single ligand, known pocket | Protein + 3D ligand + pocket coords | Poses and scoring records |
| Analogue docking | Related compounds sharing a scaffold | Protein + SMILES list + bound reference pose | Poses and scores keyed by SMILES |
| Protein-ligand cofolding | Sequence + ligand, no crystal structure | Protein sequence + SMILES | ML-predicted bound complex |

## Protein utilities

### Upload proteins

Illustrative API calls below require an authenticated account and the named local file; they have not been re-run against the service for this documentation correction. Verify each PDB accession against its target before building a docking campaign: [1M17 is EGFR bound to erlotinib](https://www.rcsb.org/structure/1M17).

```python
# From local PDB file
protein = rowan.upload_protein(
    name="egfr_kinase_domain",
    file_path="egfr_kinase.pdb",
)

# From PDB database
protein_from_pdb = rowan.create_protein_from_pdb_id(
    name="EGFR (1M17)",
    code="1M17",
)

# Retrieve previously uploaded protein
protein = rowan.retrieve_protein("protein-uuid")

# List the first page of proteins
my_proteins = rowan.list_proteins(page=0, size=20)
```

### Protein preparation guidance

- **File format**: `upload_protein` selects mmCIF for `.cif`/`.mmcif`, PDB otherwise.
- **Preparation**: Upload/import stores a structure; it does not establish docking readiness.
  Inspect chain selection, alternate locations, missing atoms/residues, protonation,
  waters, metals, cofactors, and retained ligands for the chosen workflow.
- **Multi-chain structures**: Select the intended chains explicitly when appropriate.
- **Preparation workflow**: `submit_protein_preparation_workflow` exposes pH, missing-atom
  completion, and non-polymer retention; inspect those settings before using its defaults.
- **Pocket**: Derive coordinates from the prepared receptor or its bound ligand. Arbitrary
  example coordinates are not transferable between structures. Validate docking by
  redocking a known ligand and inspecting geometry; scores are not measured binding free energies.

## Workflow catalog

Nine common workflow categories — descriptors, microscopic pKa, MacropKa, conformer
search, tautomer search, docking, analogue docking, MSA generation, and protein-ligand
cofolding — each with submission code and result shapes, plus a directory of
workflow functions (core modeling, structure-based design, advanced computational
chemistry, reaction chemistry, advanced properties, binding free energy, and sequence and
structural biology) are in
[references/workflow_catalog.md](references/workflow_catalog.md).

## Batch submission, webhooks, and asynchronous work

Batch submit/poll/retrieve, the non-blocking fire-and-check pattern, webhook setup,
secret creation and rotation, signature verification (with a FastAPI
handler), and the limits of the published payload contract are in
[references/batch_and_webhooks.md](references/batch_and_webhooks.md).

## Access, pricing, and credits

Account access, dated published credit rates, and campaign budget guidance are in
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
