# Rowan Workflow Catalog

Submission code, options, and result shapes for the common workflow categories, followed
by the complete list of supported workflow types.

## Common workflow categories

### 1. Descriptors

A lightweight entry point for batch triage, SAR, or exploratory scripts.

```python
wf = rowan.submit_descriptors_workflow(
    rowan.Molecule.from_smiles("CC(=O)Oc1ccccc1C(=O)O"),
    name="aspirin descriptors",
)

result = wf.result()
print(result.descriptors["MW"])       # 180.042 — exact mass
print(result.descriptors["SLogP"])    # 1.31
print(result.descriptors["TopoPSA"])  # 63.6 — topological PSA
print(result.descriptors["nHBAcc"])   # 3.0
```

**Common descriptor keys:**

| Key | Description | Typical drug range |
|-----|-------------|-------------------|
| `MW` | Exact/monoisotopic mass (Da), not average MW | <500 (Lipinski) |
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

The result contains about 1,679 molecular descriptors in SDK 3.1.13 (BCUT,
GETAWAY, WHIM, etc.); access any via `result.descriptors["key"]`. For average
molecular weight, calculate it separately (for example, RDKit `MolWt`).

### 2. Microscopic pKa

For protonation-state energetics and acid/base behavior of a specific structure.

Four methods are available:

| Method | Input | Speed | Covers | Use when |
|--------|-------|-------|--------|----------|
| `chemprop_nevolianis2025` | SMILES string | Fast | Deprotonation only | Acidic groups only; quick screening |
| `starling` | SMILES string | Fast | Acid + base | Most drug-like molecules; preferred SMILES method |
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
print(result.strongest_acid)    # 9.995 for phenol (verified; literature ~9.95)
print(result.strongest_base)    # None when no basic site is found
print(result.conjugate_bases)   # list of pKaMicrostate objects
# Access each microstate with .pka, .smiles, .atom_index, .delta_g, .uncertainty
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
    name="conformer search",
)

result = wf.result()
print(result.num_conformers)
print(result.get_energies())    # [0.0, 1.2, 2.5, ...]
print(result.get_conformers())  # list of 3D molecules
print(result.get_conformer(0))  # lowest-energy conformer

# There is no num_conformers submit parameter. Configure the generator and
# ensemble through conf_gen_settings.
```

### 5. Tautomer search

For heterocycles and systems where tautomer state affects downstream modeling.

```python
wf = rowan.submit_tautomer_search_workflow(
    initial_molecule=rowan.Molecule.from_smiles("O=c1[nH]ccnc1"),
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

# Binding pocket: [[center_x, center_y, center_z], [size_x, size_y, size_z]] in Å
pocket = [[10.5, 24.2, 31.8], [18.0, 18.0, 18.0]]

# Submit docking
wf = rowan.submit_docking_workflow(
    protein=protein,
    pocket=pocket,
    initial_molecule=rowan.Molecule.from_smiles(
        "CCNc1ncc(c(Nc2ccc(F)cc2)n1)-c1cccnc1"
    ),
    do_pose_refinement=True,
    do_csearch=True,
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
    initial_molecule=rowan.Molecule.from_smiles(analogues[0]),  # reference ligand
    protein=protein,
    name="SAR series docking",
)
# Analogue docking does not accept a pocket parameter in SDK 3.1.13.

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
| Multistage Optimization | `submit_multistage_optimization_workflow` | Progressive optimization across levels of theory |

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
| RBFE Graph | `submit_relative_binding_free_energy_graph_workflow` | Build and optimize an RBFE perturbation network |

### Sequence and structural biology

| Workflow | Function | When to use |
|----------|----------|-------------|
| MSA | `submit_msa_workflow` | Multiple sequence alignment for cofolding (ColabFold, Chai, Boltz) |
| Solvent-Dependent Conformers | `submit_solvent_dependent_conformers_workflow` | Solvation-aware conformer ensembles |
