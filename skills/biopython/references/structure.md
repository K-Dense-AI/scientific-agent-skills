# Structural Bioinformatics with Bio.PDB

## Overview

Bio.PDB provides tools for working with macromolecular 3D structures from PDB and mmCIF files. The module uses the SMCRA (Structure/Model/Chain/Residue/Atom) architecture to represent protein structures hierarchically.

## SMCRA Architecture

The Bio.PDB module organizes structures hierarchically:

```
Structure
  └── Model       (multiple models for NMR structures)
      └── Chain   (e.g., chain A, B, C)
          └── Residue  (amino acids, nucleotides, heteroatoms)
              └── Atom (individual atoms)
```

## Parsing Structure Files

### PDB Format

```python
from Bio.PDB import PDBParser

# Create parser
parser = PDBParser(QUIET=True)  # QUIET=True suppresses warnings

# Parse structure
structure = parser.get_structure("1crn", "1crn.pdb")

# Access basic information
print(f"Structure ID: {structure.id}")
print(f"Number of models: {len(structure)}")
```

### mmCIF Format

mmCIF format is more modern and handles large structures better:

```python
from Bio.PDB import MMCIFParser

# Create parser
parser = MMCIFParser(QUIET=True)

# Parse structure
structure = parser.get_structure("1crn", "1crn.cif")
```

### Download from PDB

```python
from Bio.PDB import PDBList

# Create PDB list object
pdbl = PDBList()

# Download PDB file
pdbl.retrieve_pdb_file("1CRN", file_format="pdb", pdir="structures/")

# Download mmCIF file
pdbl.retrieve_pdb_file("1CRN", file_format="mmCif", pdir="structures/")

# For an accession confirmed obsolete in the PDB archive only:
# pdbl.retrieve_pdb_file(obsolete_id, obsolete=True, file_format="mmCif", pdir="structures/")
```

## Navigating Structure Hierarchy

### Access Models

```python
# Get first model
model = structure[0]

# Iterate through all models
for model in structure:
    print(f"Model {model.id}")
```

### Access Chains

```python
# Get specific chain
chain = model["A"]

# Iterate through all chains
for chain in model:
    print(f"Chain {chain.id}")
```

### Access Residues

```python
# Iterate through residues in a chain
for residue in chain:
    print(f"Residue: {residue.resname} {residue.id[1]}")

# Get specific residue by ID
# Residue ID is tuple: (hetfield, sequence_id, insertion_code)
residue = chain[(" ", 10, " ")]  # Standard amino acid at position 10
```

### Access Atoms

```python
# Iterate through atoms in a residue
for atom in residue:
    print(f"Atom: {atom.name}, Coordinates: {atom.coord}")

# Get specific atom
ca_atom = residue["CA"]  # Alpha carbon
print(f"CA coordinates: {ca_atom.coord}")
```

### Alternative Access Patterns

```python
# Direct access through hierarchy
atom = structure[0]["A"][10]["CA"]

# Get all atoms
atoms = list(structure.get_atoms())
print(f"Total atoms: {len(atoms)}")

# Get all residues
residues = list(structure.get_residues())

# Get all chains
chains = list(structure.get_chains())
```

## Working with Atom Coordinates

### Accessing Coordinates

```python
# Get atom coordinates
coord = atom.coord
print(f"X: {coord[0]}, Y: {coord[1]}, Z: {coord[2]}")

# Get B-factor (temperature factor)
b_factor = atom.bfactor

# Get occupancy
occupancy = atom.occupancy

# Get element
element = atom.element
```

### Calculate Distances

```python
from Bio.PDB import Vector

# Calculate distance between two atoms
atom1 = residue1["CA"]
atom2 = residue2["CA"]

distance = atom1 - atom2  # Returns distance in Angstroms
print(f"Distance: {distance:.2f} Å")
```

### Calculate Angles

```python
from Bio.PDB.vectors import calc_angle

# Calculate angle between three atoms
angle = calc_angle(
    atom1.get_vector(),
    atom2.get_vector(),
    atom3.get_vector()
)
print(f"Angle: {angle:.2f} radians")
```

### Calculate Dihedrals

```python
from Bio.PDB.vectors import calc_dihedral

# Calculate dihedral angle between four atoms
dihedral = calc_dihedral(
    atom1.get_vector(),
    atom2.get_vector(),
    atom3.get_vector(),
    atom4.get_vector()
)
print(f"Dihedral: {dihedral:.2f} radians")
```

## Structure Analysis

### Secondary Structure (DSSP)

DSSP assigns secondary structure to protein structures:

```python
from Bio.PDB import DSSP, PDBParser

# Parse structure
parser = PDBParser()
structure = parser.get_structure("1crn", "1crn.pdb")

# Run DSSP (requires DSSP executable installed)
model = structure[0]
dssp = DSSP(model, "1crn.pdb")

# Access results
for residue_key in dssp.keys():
    dssp_data = dssp[residue_key]
    residue_id = residue_key[1]
    ss = dssp_data[2]  # Secondary structure code
    phi = dssp_data[4]  # Phi angle
    psi = dssp_data[5]  # Psi angle
    print(f"Residue {residue_id}: {ss}, φ={phi:.1f}°, ψ={psi:.1f}°")
```

Secondary structure codes:
- `H` - Alpha helix
- `B` - Beta bridge
- `E` - Strand
- `G` - 3-10 helix
- `I` - Pi helix
- `T` - Turn
- `S` - Bend
- `-` - Coil/loop

### Solvent Accessibility (DSSP)

```python
# Get relative solvent accessibility
for residue_key in dssp.keys():
    acc = dssp[residue_key][3]  # Relative accessibility
    print(f"Residue {residue_key[1]}: {acc:.2f} relative accessibility")
```

### Neighbor Search

Find nearby atoms efficiently:

```python
from Bio.PDB import NeighborSearch

# Get all atoms
atoms = list(structure.get_atoms())

# Create neighbor search object
ns = NeighborSearch(atoms)

# Find atoms within radius
center_atom = structure[0]["A"][10]["CA"]
nearby_atoms = ns.search(center_atom.coord, 5.0)  # 5 Å radius
print(f"Found {len(nearby_atoms)} atoms within 5 Å")

# Find residues within radius
nearby_residues = ns.search(center_atom.coord, 5.0, level="R")

# Find chains within radius
nearby_chains = ns.search(center_atom.coord, 10.0, level="C")
```

### Contact Map

```python
def calculate_contact_map(chain, distance_threshold=8.0):
    """Calculate residue-residue contact map."""
    residues = list(chain.get_residues())
    n = len(residues)
    contact_map = [[0] * n for _ in range(n)]

    for i, res1 in enumerate(residues):
        for j, res2 in enumerate(residues):
            if i < j:
                # Get CA atoms
                if res1.has_id("CA") and res2.has_id("CA"):
                    dist = res1["CA"] - res2["CA"]
                    if dist < distance_threshold:
                        contact_map[i][j] = 1
                        contact_map[j][i] = 1

    return contact_map
```

## Structure Quality Assessment

### Ramachandran Plot Data

```python
from Bio.PDB import Polypeptide

def get_phi_psi(structure):
    """Extract phi and psi angles for Ramachandran plot."""
    phi_psi = []

    for model in structure:
        for chain in model:
            polypeptides = Polypeptide.PPBuilder().build_peptides(chain)
            for poly in polypeptides:
                angles = poly.get_phi_psi_list()
                for residue, (phi, psi) in zip(poly, angles):
                    if phi is not None and psi is not None:  # Keep valid zero angles
                        phi_psi.append((residue.resname, phi, psi))

    return phi_psi
```

### Check for Missing Atoms

```python
def check_missing_atoms(structure):
    """Identify residues with missing atoms."""
    missing = []

    for residue in structure.get_residues():
        if residue.id[0] == " ":  # Standard amino acid
            resname = residue.resname

            # Expected backbone atoms
            expected = ["N", "CA", "C", "O"]

            for atom_name in expected:
                if not residue.has_id(atom_name):
                    missing.append((residue.full_id, atom_name))

    return missing
```

## Structure Manipulation

### Select Specific Atoms

```python
from Bio.PDB import Select

class CASelect(Select):
    """Select only CA atoms."""
    def accept_atom(self, atom):
        return atom.name == "CA"

class ChainASelect(Select):
    """Select only chain A."""
    def accept_chain(self, chain):
        return chain.id == "A"

# Use with PDBIO
from Bio.PDB import PDBIO

io = PDBIO()
io.set_structure(structure)
io.save("ca_only.pdb", CASelect())
io.save("chain_a.pdb", ChainASelect())
```

### Transform Structures

```python
import numpy as np

# Rotate structure
from Bio.PDB.vectors import Vector, rotaxis

# Define rotation axis and angle
axis = Vector(1, 0, 0)  # X-axis
angle = np.pi / 4  # 45 degrees

# Create rotation matrix
rotation = rotaxis(angle, axis).T  # Atom.transform uses row-vector multiplication

# Apply rotation to all atoms
for atom in structure.get_atoms():
    atom.transform(rotation, np.zeros(3))
```

### Superimpose Structures

```python
from Bio.PDB import Superimposer, PDBParser

# Parse two structures
parser = PDBParser()
structure1 = parser.get_structure("ref", "reference.pdb")
structure2 = parser.get_structure("mov", "mobile.pdb")

# Establish homologous residue pairs first (e.g. from a sequence alignment).
# The order is explicit: reference residue 10 corresponds to mobile residue 12.
# These IDs are illustrative; replace with the verified map for these inputs.
residue_pairs = [(10, 12), (11, 13), (12, 14)]
ref_atoms = [structure1[0]["A"][i]["CA"] for i, j in residue_pairs]
mov_atoms = [structure2[0]["A"][j]["CA"] for i, j in residue_pairs]

# Superimpose
super_imposer = Superimposer()
super_imposer.set_atoms(ref_atoms, mov_atoms)

# Apply transformation
super_imposer.apply(structure2.get_atoms())

# Get RMSD
rmsd = super_imposer.rms
print(f"RMSD: {rmsd:.2f} Å")

# Save superimposed structure
from Bio.PDB import PDBIO
io = PDBIO()
io.set_structure(structure2)
io.save("superimposed.pdb")
```

## Writing Structure Files

### Save PDB Files

```python
from Bio.PDB import PDBIO

io = PDBIO()
io.set_structure(structure)
io.save("output.pdb")
```

### Save mmCIF Files

```python
from Bio.PDB import MMCIFIO

io = MMCIFIO()
io.set_structure(structure)
io.save("output.cif")
```

## Sequence from Structure

### Extract Sequence

```python
from Bio.PDB import Polypeptide

# Get polypeptides from structure
ppb = Polypeptide.PPBuilder()

for model in structure:
    for chain in model:
        for pp in ppb.build_peptides(chain):
            sequence = pp.get_sequence()
            print(f"Chain {chain.id}: {sequence}")
```

### Map to FASTA

```python
from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

# Extract sequences and create FASTA
records = []
ppb = Polypeptide.PPBuilder()

for model in structure:
    for chain in model:
        for pp in ppb.build_peptides(chain):
            seq_record = SeqRecord(
                pp.get_sequence(),
                id=f"{structure.id}_{model.id}_{chain.id}_{pp[0].id[1]}_{pp[-1].id[1]}",
                description=f"Chain {chain.id}"
            )
            records.append(seq_record)

SeqIO.write(records, "structure_sequences.fasta", "fasta")
```

## Best Practices

1. **Use mmCIF** for large structures and modern data
2. **Inspect parser warnings** before using `QUIET=True`; suppression does not repair data
3. **Check for missing atoms** before analysis
4. **Use NeighborSearch** for efficient spatial queries
5. **Validate structure quality** with DSSP or Ramachandran analysis
6. **Handle multiple models** appropriately (NMR structures)
7. **Be aware of heteroatoms** - they have different residue IDs
8. **Use Select classes** for targeted structure output
9. **Cache downloaded structures** locally
10. **Consider alternative conformations** - some residues have multiple positions

## Common Use Cases

### Calculate RMSD Between Structures

```python
from Bio.PDB import PDBParser, Superimposer

parser = PDBParser()
structure1 = parser.get_structure("s1", "structure1.pdb")
structure2 = parser.get_structure("s2", "structure2.pdb")

# Use a verified residue correspondence; never truncate unmatched atom lists.
residue_pairs = [(10, 12), (11, 13), (12, 14)]  # illustrative map
atoms1 = [structure1[0]["A"][i]["CA"] for i, j in residue_pairs]
atoms2 = [structure2[0]["A"][j]["CA"] for i, j in residue_pairs]

# Calculate RMSD
sup = Superimposer()
sup.set_atoms(atoms1, atoms2)
print(f"RMSD: {sup.rms:.3f} Å")
```

### Find Binding Site Residues

```python
def find_binding_site(structure, ligand_chain, ligand_res_id, distance=5.0):
    """Find residues near a ligand."""
    from Bio.PDB import NeighborSearch

    # Get ligand atoms
    ligand = structure[0][ligand_chain][ligand_res_id]
    ligand_atoms = list(ligand.get_atoms())

    # Get all protein atoms
    protein_atoms = []
    from Bio.PDB.Polypeptide import is_aa
    for residue in structure[0].get_residues():
        if residue is not ligand and is_aa(residue):
            protein_atoms.extend(residue.get_atoms())

    # Find nearby atoms
    ns = NeighborSearch(protein_atoms)
    binding_site = set()

    for ligand_atom in ligand_atoms:
        nearby = ns.search(ligand_atom.coord, distance, level="R")
        binding_site.update(nearby)

    return list(binding_site)
```

### Calculate Center of Mass

```python
import numpy as np

def center_of_mass(entity):
    """Calculate center of mass for structure entity."""
    atoms = list(entity.get_atoms())
    if not atoms:
        raise ValueError("Cannot calculate center of mass of an empty entity")
    masses = np.array([atom.mass for atom in atoms])
    if not np.all(np.isfinite(masses)) or np.any(masses <= 0):
        raise ValueError("Check element assignments before calculating masses")
    coords = np.array([atom.coord for atom in atoms])
    return np.average(coords, axis=0, weights=masses)
```
