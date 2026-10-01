# System preparation and force-field provenance

Reviewed 2026-10-01. OpenMM 8.6.1 is the executed simulation release. PDBFixer
1.12.0 was exercised on a water/ion fixture. OpenFF Toolkit 0.18.0 APIs below
were reviewed in official documentation; OpenFF parameterization is illustrative
and was not executed in this audit.

## PDBFixer: preserve scientific decisions

PDBFixer can propose missing residues from SEQRES and replace modified residues,
but neither operation establishes the correct experimental construct. Its
`removeHeterogens(True)` keeps water and removes ligands, ions and cofactors; do
not use it as general protein-ligand preparation. This conservative example adds
missing atoms/hydrogens without silently rebuilding entire loops or deleting
heterogens. Inspect retained nonstandard residues and parameterize them separately.
Use `conda install -c conda-forge pdbfixer` in a separate environment if needed.

```python
from pdbfixer import PDBFixer
from openmm.app import PDBFile

def fix_pdb(input_pdb, output_pdb, ph=7.0):
    fixer = PDBFixer(filename=input_pdb)
    fixer.findMissingResidues()
    print("Missing residue proposals:", fixer.missingResidues)
    fixer.missingResidues = {}  # Explicit policy: do not invent absent loops/termini.
    fixer.findNonstandardResidues()
    print("Nonstandard residues retained:", fixer.nonstandardResidues)
    # Review before opting into replaceNonstandardResidues or heterogen deletion.
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()
    fixer.addMissingHydrogens(ph)
    with open(output_pdb, "w") as handle:
        PDBFile.writeFile(fixer.topology, fixer.positions, handle, keepIds=True)
    return output_pdb
```

Hydrogens assigned at a pH are a model choice, not a pKa calculation. Inspect
histidines, catalytic groups, metal binding, disulfides and termini manually.
Run `Modeller.addHydrogens(..., pH=...)` using the intended force field and consistent
pH afterward; retained unknown ligands still need explicit chemical preparation.

## OpenFF ligand parameters

The official Toolkit installation route uses conda-forge/Mamba and chemistry
backends. Although Toolkit 0.18.0 and Interchange 0.5.1 are on PyPI, their metadata does
not declare the complete dependency stack; a bare pip install is insufficient.
For example, `mamba create -n md-openff -c conda-forge openff-toolkit openff-interchange`
is an illustrative environment command; check the solved force-field/charge
backend dependencies before running it.

Sage 2.3.0 (`openff-2.3.0.offxml`) is the stable small-molecule release reviewed
here; OpenFF 3.0 alpha force fields are research prereleases. Sage 2.3 uses AshGC
charges and needs the corresponding OpenFF NAGL implementation and model. Record
and validate those versions; do not silently substitute older AM1-BCC charges.
Installing/resolving these optional models was outside this small smoke audit.

```python
from openff.toolkit import Molecule, ForceField as OFFForceField

def parameterize_ligand(smiles, ff_name="openff-2.3.0.offxml"):
    """Illustrative ligand-only parameterization; requires the charge backend/model."""
    mol = Molecule.from_smiles(smiles)  # Undefined stereochemistry raises by default.
    mol.generate_conformers(n_conformers=1)
    off_ff = OFFForceField(ff_name)
    return off_ff.create_interchange(mol.to_topology())
```

The SMILES must encode the intended stereoisomer, tautomer and formal charge.
A generated conformer is not the bound pose. Map every ligand atom back to the
complex before merging through a supported template/system construction route.
Preserve nonbonded conventions, water/ion parameters, exceptions and charge totals;
do not concatenate independent OpenMM Systems or confuse OpenFF with GAFF2.

## Official sources

- [OpenMM running simulations and force-field inventory](https://docs.openmm.org/latest/userguide/application/02_running_sims.html)
- [Modeller and solvent semantics](https://docs.openmm.org/latest/api-python/generated/openmm.app.modeller.Modeller.html)
- [Simulation and restart APIs](https://docs.openmm.org/latest/api-python/generated/openmm.app.simulation.Simulation.html)
- [Barostat Context parameters](https://docs.openmm.org/latest/api-python/generated/openmm.openmm.MonteCarloBarostat.html)
- [PDBFixer 1.12 release](https://github.com/openmm/pdbfixer/releases/tag/v1.12)
- [PDBFixer manual](https://github.com/openmm/pdbfixer/blob/v1.12/Manual.html)
- [OpenFF installation](https://docs.openforcefield.org/projects/toolkit/en/stable/installation.html)
- [OpenFF ForceField API](https://docs.openforcefield.org/projects/toolkit/en/stable/api/generated/openff.toolkit.typing.engines.smirnoff.ForceField.html)
- [OpenFF force-field releases](https://github.com/openforcefield/openff-forcefields/releases)
- [NAGL installation](https://docs.openforcefield.org/projects/nagl/en/stable/installation.html)
