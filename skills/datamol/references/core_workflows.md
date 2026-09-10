# Datamol Core Workflows

The ten workflow areas in full, with worked code: basic molecule handling, reading and
writing molecular files (including cloud and compressed formats), descriptors and
properties, fingerprints and similarity, clustering and diversity selection, scaffold
analysis, fragmentation, 3D conformer generation, visualization, and chemical reactions.

## Core Workflows

### 1. Basic Molecule Handling

**Creating molecules from SMILES**:
```python
import datamol as dm

# Single molecule
mol = dm.to_mol("CCO")  # Ethanol

# From list of SMILES
smiles_list = ["CCO", "c1ccccc1", "CC(=O)O"]
mols = [dm.to_mol(smi) for smi in smiles_list]

# Error handling
mol = dm.to_mol("invalid_smiles")  # Returns None
if mol is None:
    print("Failed to parse SMILES")
```

**Converting molecules to SMILES**:
```python
# Canonical SMILES
smiles = dm.to_smiles(mol)

# Isomeric SMILES (includes stereochemistry)
smiles = dm.to_smiles(mol, isomeric=True)

# Other formats
inchi = dm.to_inchi(mol)
inchikey = dm.to_inchikey(mol)
selfies = dm.to_selfies(mol)
```

**Standardization and sanitization** (always recommend for user-provided molecules):
```python
# Sanitize molecule
mol = dm.sanitize_mol(mol)

# Full standardization (recommended for datasets)
mol = dm.standardize_mol(
    mol,
    disconnect_metals=True,
    normalize=True,
    reionize=True
)

# For SMILES strings directly
clean_smiles = dm.standardize_smiles(smiles)
```

### 2. Reading and Writing Molecular Files

Refer to `references/io_module.md` for comprehensive I/O documentation.

**Reading files**:
```python
# SDF files (most common in chemistry)
df = dm.read_sdf("compounds.sdf", mol_column='mol')

# SMILES files
df = dm.read_smi("molecules.smi", smiles_column='smiles', mol_column='mol')

# CSV with SMILES column
df = dm.read_csv("data.csv", smiles_column="SMILES", mol_column="mol")

# Excel files
df = dm.read_excel("compounds.xlsx", sheet_name=0, mol_column="mol")

# Universal reader/writer (auto-detects format; supports compression)
df = dm.open_df("file.sdf")  # .sdf, .csv, .xlsx, .parquet, .json, .gz, etc.
dm.save_df(df, "output.parquet")
```

**Writing files**:
```python
# Save as SDF
dm.to_sdf(mols, "output.sdf")
# Or from DataFrame
dm.to_sdf(df, "output.sdf", mol_column="mol")

# Save as SMILES file
dm.to_smi(mols, "output.smi")

# Excel with rendered molecule images
dm.to_xlsx(df, "output.xlsx", mol_columns=["mol"])
```

**Remote file support** (S3, GCS, HTTP via fsspec):

Only use cloud paths when the user explicitly requests them. Confirm the destination before writing.

```python
# Read from cloud storage or HTTPS (user-provided URLs only)
df = dm.read_sdf("s3://bucket/compounds.sdf")
df = dm.read_csv("https://example.com/data.csv")

# Write to cloud storage — confirm path with user first
dm.to_sdf(mols, "s3://bucket/output.sdf")
```

Cloud backends read credentials from the standard provider environment (for example `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, or `GOOGLE_APPLICATION_CREDENTIALS`). Datamol passes these to fsspec locally; it does not collect or transmit environment variables to third-party endpoints. Scope credential access to the named provider variables only.

### 3. Molecular Descriptors and Properties

Refer to `references/descriptors_viz.md` for detailed descriptor documentation.

**Computing descriptors for a single molecule**:
```python
# Get standard descriptor set
descriptors = dm.descriptors.compute_many_descriptors(mol)
# Careful: the `mw` key is the MONOISOTOPIC (exact) mass, not average molecular
# weight, and it sits in the same dict as `n_lipinski_hba` / `n_lipinski_hbd`,
# which invites applying Lipinski's MW <= 500 to the wrong quantity. Measured
# 2026-09-09: aspirin dm mw 180.0423 vs RDKit MolWt 180.1590; atorvastatin
# 558.2530 vs 558.6500. The gap is about -0.07%, so it will not usually flip a
# 500 Da cutoff, but the two numbers are different quantities. For average
# molecular weight use rdkit.Chem.Descriptors.MolWt.
# Returns (ethanol, measured on datamol 0.13.0):
#   {'mw': 46.0419, 'clogp': -0.0014, 'n_lipinski_hbd': 1, 'n_lipinski_hba': 1,
#    'tpsa': 20.23, 'n_aromatic_rings': 0, 'qed': ..., 'sas': ..., 'fsp3': ...}
# Note the key names: it is `clogp`, not `logp`, and `n_lipinski_hba` /
# `n_lipinski_hbd`, not `hba` / `hbd`. There is no `n_aromatic_atoms` key in
# this dict; `dm.descriptors.n_aromatic_atoms(mol)` is a separate function.
```

**Batch descriptor computation** (recommended for datasets):
```python
# Compute for all molecules in parallel
desc_df = dm.descriptors.batch_compute_many_descriptors(
    mols,
    n_jobs=-1,      # Use all CPU cores
    progress=True   # Show progress bar
)
```

**Specific descriptors**:
```python
# Aromaticity
n_aromatic = dm.descriptors.n_aromatic_atoms(mol)
aromatic_ratio = dm.descriptors.n_aromatic_atoms_proportion(mol)

# Stereochemistry
n_stereo = dm.descriptors.n_stereo_centers(mol)
n_unspec = dm.descriptors.n_stereo_centers_unspecified(mol)

# Flexibility
n_rigid = dm.descriptors.n_rigid_bonds(mol)
```

**Drug-likeness filtering (Lipinski's Rule of Five)**:
```python
# Filter compounds
def is_druglike(mol):
    desc = dm.descriptors.compute_many_descriptors(mol)
    return (
        desc['mw'] <= 500 and
        desc['logp'] <= 5 and
        desc['hbd'] <= 5 and
        desc['hba'] <= 10
    )

druglike_mols = [mol for mol in mols if is_druglike(mol)]
```

### 4. Molecular Fingerprints and Similarity

**Generating fingerprints**:

Datamol defaults to ECFP6 (`radius=3`, `n_bits=2048`). Pass `radius=2` explicitly for ECFP4.

```python
# ECFP4 (common in similarity screening)
fp = dm.to_fp(mol, fp_type='ecfp', radius=2, n_bits=2048)

# Other fingerprint types
fp_maccs = dm.to_fp(mol, fp_type='maccs')
fp_topological = dm.to_fp(mol, fp_type='topological')
fp_atompair = dm.to_fp(mol, fp_type='atompair')
fp_rdkit = dm.to_fp(mol, fp_type='rdkit')
```

**Similarity calculations**:
```python
# Pairwise distances within a set
distance_matrix = dm.pdist(mols, n_jobs=-1)

# Distances between two sets
distances = dm.cdist(query_mols, library_mols, n_jobs=-1)

# Find most similar molecules (scipy is a PyPI package, not a file in this skill)
from scipy.spatial.distance import squareform  # third-party library
dist_matrix = squareform(dm.pdist(mols))
# Lower distance = higher similarity (Tanimoto distance = 1 - Tanimoto similarity)
```

### 5. Clustering and Diversity Selection

Refer to `references/core_api.md` for clustering details.

**Butina clustering**:
```python
# Cluster molecules by structural similarity
clusters = dm.cluster_mols(
    mols,
    cutoff=0.2,    # Tanimoto distance threshold (0=identical, 1=completely different)
    n_jobs=-1      # Parallel processing
)

# Each cluster is a list of molecule indices
for i, cluster in enumerate(clusters):
    print(f"Cluster {i}: {len(cluster)} molecules")
    cluster_mols = [mols[idx] for idx in cluster]
```

**Important**: Butina clustering builds a full distance matrix - suitable for ~1000 molecules, not for 10,000+.

**Diversity selection**:
```python
# Pick diverse subset
diverse_mols = dm.pick_diverse(
    mols,
    npick=100  # Select 100 diverse molecules
)

# Pick cluster centroids
centroids = dm.pick_centroids(
    mols,
    npick=50   # Select 50 representative molecules
)
```

### 6. Scaffold Analysis

Refer to `references/fragments_scaffolds.md` for complete scaffold documentation.

**Extracting Murcko scaffolds**:
```python
# Get Bemis-Murcko scaffold (core structure)
scaffold = dm.to_scaffold_murcko(mol)
scaffold_smiles = dm.to_smiles(scaffold)
```

**Scaffold-based analysis**:
```python
# Group compounds by scaffold
from collections import Counter

scaffolds = [dm.to_scaffold_murcko(mol) for mol in mols]
scaffold_smiles = [dm.to_smiles(s) for s in scaffolds]

# Count scaffold frequency
scaffold_counts = Counter(scaffold_smiles)
most_common = scaffold_counts.most_common(10)

# Create scaffold-to-molecules mapping
scaffold_groups = {}
for mol, scaf_smi in zip(mols, scaffold_smiles):
    if scaf_smi not in scaffold_groups:
        scaffold_groups[scaf_smi] = []
    scaffold_groups[scaf_smi].append(mol)
```

**Scaffold-based train/test splitting** (for ML):
```python
# Ensure train and test sets have different scaffolds
scaffold_to_mols = {}
for mol, scaf in zip(mols, scaffold_smiles):
    if scaf not in scaffold_to_mols:
        scaffold_to_mols[scaf] = []
    scaffold_to_mols[scaf].append(mol)

# Split scaffolds into train/test
import random
scaffolds = list(scaffold_to_mols.keys())
random.shuffle(scaffolds)
split_idx = int(0.8 * len(scaffolds))
train_scaffolds = scaffolds[:split_idx]
test_scaffolds = scaffolds[split_idx:]

# Get molecules for each split
train_mols = [mol for scaf in train_scaffolds for mol in scaffold_to_mols[scaf]]
test_mols = [mol for scaf in test_scaffolds for mol in scaffold_to_mols[scaf]]
```

### 7. Molecular Fragmentation

Refer to `references/fragments_scaffolds.md` for fragmentation details.

**BRICS fragmentation** (16 bond types):
```python
# Fragment molecule
fragments = dm.fragment.brics(mol)
# Returns: set of fragment SMILES with attachment points like '[1*]CCN'
```

**RECAP fragmentation** (11 bond types):
```python
fragments = dm.fragment.recap(mol)
```

**Fragment analysis**:
```python
# Find common fragments across compound library
from collections import Counter

all_fragments = []
for mol in mols:
    frags = dm.fragment.brics(mol)
    all_fragments.extend(frags)

fragment_counts = Counter(all_fragments)
common_frags = fragment_counts.most_common(20)

# Fragment-based scoring
def fragment_score(mol, reference_fragments):
    mol_frags = dm.fragment.brics(mol)
    overlap = mol_frags.intersection(reference_fragments)
    return len(overlap) / len(mol_frags) if mol_frags else 0
```

### 8. 3D Conformer Generation

Refer to `references/conformers_module.md` for detailed conformer documentation.

**Generating conformers**:
```python
# Generate 3D conformers
mol_3d = dm.conformers.generate(
    mol,
    n_confs=50,           # Number to generate (auto if None)
    rms_cutoff=0.5,       # Filter similar conformers (Ångströms)
    minimize_energy=True,  # Minimize with UFF force field
    method='ETKDGv3'      # Embedding method (recommended)
)

# Access conformers
n_conformers = mol_3d.GetNumConformers()
conf = mol_3d.GetConformer(0)  # Get first conformer
positions = conf.GetPositions()  # Nx3 array of atom coordinates
```

**Conformer clustering**:
```python
# Cluster conformers by RMSD
clusters = dm.conformers.cluster(
    mol_3d,
    rms_cutoff=1.0,
    centroids=False
)

# Get representative conformers
centroids = dm.conformers.return_centroids(mol_3d, clusters)
```

**SASA calculation**:
```python
# Calculate solvent accessible surface area
sasa_values = dm.conformers.sasa(mol_3d, n_jobs=-1)

# Access SASA from conformer properties
conf = mol_3d.GetConformer(0)
sasa = conf.GetDoubleProp('rdkit_free_sasa')
```

### 9. Visualization

Refer to `references/descriptors_viz.md` for visualization documentation.

**Basic molecule grid**:
```python
# Visualize molecules
dm.viz.to_image(
    mols[:20],
    legends=[dm.to_smiles(m) for m in mols[:20]],
    n_cols=5,
    mol_size=(300, 300)
)

# Save to file
dm.viz.to_image(mols, outfile="molecules.png")

# SVG for publications
dm.viz.to_image(mols, outfile="molecules.svg", use_svg=True)
```

**Aligned visualization** (for SAR analysis):
```python
# Align molecules by common substructure
dm.viz.to_image(
    similar_mols,
    align=True,  # Enable MCS alignment
    legends=activity_labels,
    n_cols=4
)
```

**Highlighting substructures**:
```python
# Highlight specific atoms and bonds
dm.viz.to_image(
    mol,
    highlight_atom=[0, 1, 2, 3],  # Atom indices
    highlight_bond=[0, 1, 2]      # Bond indices
)
```

**Conformer visualization**:
```python
# Display multiple conformers
dm.viz.conformers(
    mol_3d,
    n_confs=10,
    align_conf=True,
    n_cols=3
)
```

### 10. Chemical Reactions

Refer to `references/reactions_data.md` for reactions documentation.

**Applying reactions**:
```python
from rdkit.Chem import rdChemReactions

# Define reaction from SMARTS
rxn_smarts = '[C:1](=[O:2])[OH:3]>>[C:1](=[O:2])[Cl:3]'
rxn = rdChemReactions.ReactionFromSmarts(rxn_smarts)

# Apply to molecule
reactant = dm.to_mol("CC(=O)O")  # Acetic acid
product = dm.reactions.apply_reaction(
    rxn,
    (reactant,),
    sanitize=True
)

# Convert to SMILES
product_smiles = dm.to_smiles(product)
```

**Batch reaction application**:
```python
# Apply reaction to library
products = []
for mol in reactant_mols:
    try:
        prod = dm.reactions.apply_reaction(rxn, (mol,))
        if prod is not None:
            products.append(prod)
    except Exception as e:
        print(f"Reaction failed: {e}")
```
