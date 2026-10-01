# Rowan Workflow Catalog

Submission code, options, and result shapes for the common workflow categories, followed
by the SDK workflow directory. Hosted calls are illustrative, not authenticated service tests.
The source baseline is [rowan-python 3.2.0](https://pypi.org/project/rowan-python/3.2.0/);
see the [official workflow reference](https://docs.rowansci.com/api/python/v3/).

## Common workflow categories

### 1. Descriptors

A lightweight entry point for batch triage, SAR, or exploratory scripts.

```python
wf = rowan.submit_descriptors_workflow(
    rowan.Molecule.from_smiles("CC(=O)Oc1ccccc1C(=O)O"),
    name="aspirin descriptors",
)

result = wf.result()
print(result.descriptors["MW"])       # exact/monoisotopic mass
print(result.descriptors["SLogP"])    # model-dependent value
print(result.descriptors["TopoPSA"])  # topological PSA
print(result.descriptors["nHBAcc"])   # H-bond acceptor count
```

**Common descriptor keys:**

| Key | Description | Typical drug range |
|-----|-------------|-------------------|
| `MW` | Exact/monoisotopic mass (Da), not average MW | Do not substitute for average MW in strict filters |
| `SLogP` | Calculated LogP (lipophilicity) | -2 to +5 |
| `TopoPSA` | Topological polar surface area (Å²) | <140 for oral bioavailability |
| `TPSA` | 3D charged surface area, not topological PSA | — |
| `nHBDon` | H-bond donor count | ≤5 (Lipinski) |
| `nHBAcc` | H-bond acceptor count | ≤10 (Lipinski) |
| `nRot` | Rotatable bond count | <10 for oral drugs |
| `nRing` | Ring count | — |
| `nHeavyAtom` | Heavy atom count | — |
| `FilterItLogS` | Estimated aqueous solubility (LogS) | >-4 preferred |
| `Lipinski` | Lipinski Ro5 pass (1.0) or fail (0.0) | — |

The descriptor count and available keys depend on the service calculation; do not
hardcode a count. `result.descriptors` may be `None` before completion. For average
molecular weight, calculate it separately (for example, RDKit `MolWt`).

### 2. Microscopic pKa

For protonation-state energetics and acid/base behavior of a specific structure.

Four methods are available:

| Method | Input | Speed | Covers | Use when |
|--------|-------|-------|--------|----------|
| `chemprop_nevolianis2025` | SMILES string | Fast | Deprotonation only | Acidic groups only; quick screening |
| `starling` | SMILES string | Fast | Acid + base | SMILES-based acid/base site prediction |
| `aimnet2_wagen2024` | 3D molecule object | Slower | Acid + base | You already have a 3D structure |
| `gxtb_wagen2026` (**default**) | 3D molecule object | Slower | Acid + base | Current SDK default; set `method=` explicitly for reproducibility |

```python
# Fast path: SMILES input with full acid+base coverage (use starling method when available)
wf = rowan.submit_pka_workflow(
    initial_molecule="c1ccccc1O",       # phenol SMILES; param is initial_molecule, not initial_smiles
    method="starling",   # fast SMILES method, covers acid+base; chemprop_nevolianis2025 is deprotonation-only
    name="phenol pKa",
)

result = wf.result()
print(result.strongest_acid)    # float or None; do not treat a past prediction as a guarantee
print(result.strongest_base)    # None when no basic site is found
print(result.conjugate_bases)   # list of pKaMicrostate objects
# Each microstate has .pka and .atom_index. SMILES methods populate .smiles;
# 3D methods populate .delta_g (kcal/mol); Chemprop also populates .uncertainty.
```

### 3. MacropKa

For pH-dependent protonation behavior across a range.

```python
wf = rowan.submit_macropka_workflow(
    initial_smiles="c1ncc[nH]1",  # imidazole
    method="starling",  # 3.2.0 also accepts starling_ii; pin the intended model
    min_pH=0,
    max_pH=14,
    min_charge=-2,  # default
    max_charge=2,   # default
    compute_aqueous_solubility=True,  # default
    name="imidazole macropKa",
)

result = wf.result()
print([(v.initial_charge, v.final_charge, v.pka) for v in result.pka_values])
print(result.logd_by_ph)               # list of (pH, logD) pairs
print(result.aqueous_solubility_by_ph) # list of (pH, log-solubility) pairs
print(result.isoelectric_point)        # isoelectric point
print(result.data)
# Raw keys use pKa_values, logD_by_pH, aqueous_solubility_by_pH.
# Consult the method documentation before interpreting solubility units.
```

### 4. Conformer search

For 3D ensemble generation when ensemble quality matters.

```python
wf = rowan.submit_conformer_search_workflow(
    initial_molecule="CCOC(=O)N1CCC(CC1)Oc1ncnc2ccccc12",
    name="conformer search",
)

result = wf.result()
print(result.num_conformers)
print(result.get_energies())    # absolute energies in Hartree
print(result.get_energies(relative=True))  # relative kcal/mol, minimum is zero
print(result.get_conformers())  # list of 3D molecules
print(result.get_conformer(0).molecule)  # get_conformer returns a Calculation

# There is no num_conformers submit parameter. Configure the generator and
# ensemble through conf_gen_settings.
```

### 5. Tautomer search

For heterocycles and systems where tautomer state affects downstream modeling.

```python
wf = rowan.submit_tautomer_search_workflow(
    initial_molecule=rowan.Molecule.from_smiles("O=c1cccc[nH]1"),
    name="2-pyridone tautomers",
)

result = wf.result()
print(result.best_tautomer)  # highest-weight Molecule, or None
print(result.tautomers)      # Tautomer records: energy (Hartree), weight, structure_uuids
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

# Supply a validated pocket for this exact prepared receptor.
# pocket.json contains [[center_x, center_y, center_z], [size_x, size_y, size_z]] in Å.
import json
from pathlib import Path
pocket = json.loads(Path("pocket.json").read_text())

# Submit docking
wf = rowan.submit_docking_workflow(
    protein=protein,
    pocket=pocket,
    initial_molecule=rowan.Molecule.from_smiles(
        "Nc1ncc(F)cc1"
    ),
    docking_settings=rowan.VinaSettings(scoring_function="vinardo"),
    do_pose_refinement=True,
    do_csearch=True,
    name="lead docking",
)

result = wf.result()
print([s.score for s in result.scores])  # DockingScore records; .score is kcal/mol
print(result.best_pose)  # Mol object with 3D coordinates
print(result.data)  # Raw result dict
```

**Protein preparation tips:**

- Choose waters, metals, cofactors, protonation, and chains deliberately during preparation
- Compare scores within a consistent protocol; a docking score is not experimental affinity
- Use the same protein object across a docking series for consistency
- If you have a PDB ID, use `rowan.create_protein_from_pdb_id()` instead

### 7. Analogue docking

For placing a compound series into a shared binding context.

```python
# Toy analogue series; these are not validated binders.
analogues = ["Nc1ncc(F)cc1", "Nc1ncc(Cl)cc1", "Nc1ncc(OC)cc1"]
# From the preceding docking workflow or a crystallographic bound ligand:
reference_pose = result.best_pose  # Keep coordinates in the receptor frame.

wf = rowan.submit_analogue_docking_workflow(
    analogues=analogues,
    initial_molecule=reference_pose,  # aligned bound template, not newly embedded SMILES
    protein=protein,
    name="SAR series docking",
)
# Analogue docking does not accept a pocket parameter in SDK 3.2.0.

result = wf.result()
print(result.analogue_scores)  # dict[str, list[DockingScore]], keyed by SMILES
print(result.best_poses)       # dict[str, Molecule]; absent/failed analogues are omitted
```

### 8. MSA generation

For multiple-sequence alignment (useful for downstream cofolding). The short
sequence below demonstrates the schema; use the complete intended biological
construct for a scientific calculation.

```python
wf = rowan.submit_msa_workflow(
    initial_protein_sequences=[
        "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVP"
    ],
    output_formats={"colabfold", "chai", "boltz"},
    name="target MSA",
)

result = wf.result()
result.download_files(path=f"msa/{wf.uuid}")  # one tar.gz per requested format
```

### 9. Protein-ligand cofolding

For AI-based bound-complex prediction when no crystal structure is available.
The short example sequence is illustrative, not a validated folding target;
use the actual construct and inspect model-specific confidence and geometry.

```python
wf = rowan.submit_protein_cofolding_workflow(
    initial_protein_sequences=[
        "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVP"
    ],
    initial_smiles_list=[
        "Nc1ncc(F)cc1"
    ],
    model="boltz_2",
    name="protein-ligand cofolding",
)

result = wf.result()
print(result.predictions)  # CofoldingResult records with scores and structure UUIDs
print(result.messages)  # Model metadata/warnings

predicted_structure = result.get_predicted_structure()
if predicted_structure is None:
    raise RuntimeError("No predicted structure was returned")
predicted_structure.download_structure(name="predicted_complex", file_format="mmcif")
```

## Workflow directory

Named submit functions below use `POST /workflow`, build a workflow-specific
`workflow_data` payload, and expose `folder`/`folder_uuid`, `webhook_url`, and
`max_credits`. Availability is account-dependent. This directory covers the reviewed
SDK, not a guarantee that every account can run every workflow.

### Core molecular modeling workflows

| Workflow | Function | When to use |
|----------|----------|-------------|
| Descriptors | `submit_descriptors_workflow` | First-pass triage: exact mass, LogP, TopoPSA, HBA/HBD, Lipinski filter |
| pKa | `submit_pka_workflow` | Single ionizable group; need protonation thermodynamics |
| MacropKa | `submit_macropka_workflow` | Multi-ionizable drugs; pH-dependent charge/LogD/solubility |
| Conformer Search | `submit_conformer_search_workflow` | 3D ensemble for docking, MD, or SAR; known tautomer |
| Tautomer Search | `submit_tautomer_search_workflow` | Heterocycles, keto–enol; uncertain tautomeric form |
| LogP | `submit_logp_workflow` | Octanol/water partition coefficient |
| Solubility | `submit_solubility_workflow` | Aqueous or solvent-specific solubility prediction |
| Membrane Permeability | `submit_membrane_permeability_workflow` | Caco-2, PAMPA, BBB, plasma permeability |
| ADMET | `submit_admet_workflow` | Broad drug-likeness and ADMET property sweep |

### Structure-based design workflows

| Workflow | Function | When to use |
|----------|----------|-------------|
| Protein Preparation | `submit_protein_preparation_workflow` | Missing-atom completion and protonation |
| Pocket Detection | `submit_pocket_detection_workflow` | Candidate pocket detection for review |
| Binding Affinity | `submit_binding_affinity_workflow` | Model-specific complex scoring |
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
| Multistage Optimization | `submit_multistage_optimization_workflow` | Progressive optimization across levels of theory |

### Reaction chemistry

| Workflow | Function | When to use |
|----------|----------|-------------|
| Covalent Inhibitor Scan | `submit_covalent_inhibitor_scan_workflow` | Covalent reaction-coordinate scans |
| Double-Ended TS Search | `submit_double_ended_ts_search_workflow` | Transition state between two known structures |
| IRC | `submit_irc_workflow` | Confirm TS connectivity; intrinsic reaction coordinate |

### Advanced properties

| Workflow | Function | When to use |
|----------|----------|-------------|
| NMR | `submit_nmr_workflow` | Predicted 1H/13C chemical shifts for structure verification |
| Ion Mobility | `submit_ion_mobility_workflow` | Collision cross-section (CCS) for MS method development |
| Hydrogen Bond Strength | `submit_hydrogen_bond_donor_acceptor_strength_workflow` | H-bond donor/acceptor strength for formulation/solubility |
| Fukui | `submit_fukui_workflow` | Site reactivity indices for electrophilic/nucleophilic attack |
| Interaction Energy Decomposition | `submit_interaction_energy_decomposition_workflow` | Fragment-level interaction analysis |

### Binding free energy

| Workflow | Function | When to use |
|----------|----------|-------------|
| RBFE/FEP | `submit_relative_binding_free_energy_perturbation_workflow` | Relative ΔΔG for congeneric series |
| RBFE Graph | `submit_relative_binding_free_energy_graph_workflow` | Build and optimize an RBFE perturbation network |

### Sequence and structural biology

| Workflow | Function | When to use |
|----------|----------|-------------|
| MSA | `submit_msa_workflow` | Multiple sequence alignment for cofolding (ColabFold, Chai, Boltz) |
| Solvent-Dependent Conformers | `submit_solvent_dependent_conformers_workflow` | Solvation-aware conformer ensembles |

`submit_hydrogen_bond_basicity_workflow` remains a compatibility alias for the
donor/acceptor-strength function. For signatures of table-only workflows, consult
the matching page in the official reference; do not infer arguments from another workflow.
