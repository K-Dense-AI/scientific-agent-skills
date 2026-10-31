# MDAnalysis Analysis Reference

Reviewed against MDAnalysis 2.10.0 on 2026-10-01. Examples use local topology
and trajectory files and are illustrative outside the synthetic regression checks.
Atom order, molecule integrity, box vectors and time units must be checked first.

## MDAnalysis Universe and AtomGroup

```python
import MDAnalysis as mda

# Load Universe
u = mda.Universe("topology.pdb", "trajectory.dcd")
# or for single structure:
u = mda.Universe("structure.pdb")

# Key attributes
print(u.atoms.n_atoms)          # Total atoms
print(u.residues.n_residues)    # Total residues
print(u.trajectory.n_frames)   # Number of frames
print(u.trajectory.dt)         # Time step in ps
print(u.trajectory.totaltime)  # Stored span, (n_frames - 1) * dt, in ps
```

## Atom Selection Language

MDAnalysis uses a rich selection language:

```python
# Basic selections
protein = u.select_atoms("protein")
backbone = u.select_atoms("backbone")  # CA, N, C, O
calpha = u.select_atoms("protein and name CA")
water = u.select_atoms("resname WAT or resname HOH or resname TIP3")
ligand = u.select_atoms("resname LIG")

# By residue number
region = u.select_atoms("resid 10:50")
specific = u.select_atoms("resid 45 and name CA")

# By proximity
near_ligand = u.select_atoms("protein and around 5.0 resname LIG", updating=True)

# By property
charged = u.select_atoms("resname ARG LYS ASP GLU")
hydrophobic = u.select_atoms("resname ALA VAL LEU ILE PRO PHE TRP MET")

# Boolean combinations
active_site = u.select_atoms("(resid 100 102 145 200) and protein")

# Inverse
not_water = u.select_atoms("not (resname WAT HOH)")
```

Geometric selections use periodic dimensions by default; `updating=True`
re-evaluates the selection each frame. Verify residue naming (`protein` uses
recognized residue names) and use `resindex` plus a saved identity map when IDs
repeat across chains.

## Common Analysis Modules

### RMSD and RMSF

```python
from MDAnalysis.analysis import rms, align

# Make molecules whole using trusted bonds before this structural analysis.
# Keep original coordinates/boxes for separate periodic contact calculations.
aligned = u.copy()
aligned.trajectory[0]
align.AlignTraj(aligned, aligned, select='backbone', in_memory=True).run()

# RMSD
R = rms.RMSD(aligned, select='backbone', groupselections=['protein and name CA'], ref_frame=0)
R.run()
# Shape (n_frames, 4): frame, time (ps), backbone RMSD, CA RMSD (Å).
# CA RMSD uses the backbone fit; groupselections are not fitted independently.

# RMSF (per-atom fluctuations)
from MDAnalysis.analysis.rms import RMSF
rmsf = RMSF(aligned.select_atoms('backbone')).run()
# rmsf.results.rmsf: per-atom RMSF values in Angstroms
```

### Radius of Gyration

```python
protein = aligned.select_atoms("protein")  # Must be whole; valid atomic masses required.
rg = []
for ts in aligned.trajectory:
    rg.append(protein.radius_of_gyration())
import numpy as np
print(f"Mean Rg: {np.mean(rg):.2f} Å")
```

### Secondary Structure Analysis

```python
from MDAnalysis.analysis.dssp import DSSP

# DSSP secondary structure assignment per frame
dssp = DSSP(u).run()
# dssp.results.dssp: per-residue per-frame secondary structure codes
# H = helix (including 3_10 and pi), E = strand, - = loop/unordered.
# Requires complete, correctly ordered backbone atoms; not eight-state DSSP.
```

### Hydrogen Bonds

```python
from MDAnalysis.analysis.hydrogenbonds import HydrogenBondAnalysis

# Illustrative BACKBONE-only selection; adapt names to the actual topology.
# Explicit H selection avoids charge-based guessing on PDB files without charges.
# With reliable bonds, prefer donors_sel=None to pair bonded donor and H atoms.
hbonds = HydrogenBondAnalysis(
    u,
    donors_sel="protein and name N",
    hydrogens_sel="protein and name H HN",
    acceptors_sel="protein and name O",
    d_h_cutoff=1.2,          # donor-H distance (Å)
    d_a_cutoff=3.0,          # donor-acceptor distance (Å)
    d_h_a_angle_cutoff=150   # D-H-A angle (degrees)
)
hbonds.run()

counts = hbonds.count_by_time()  # One count per analyzed frame (including zeros).
# The result table has one row per bond occurrence, not one row per frame.
import pandas as pd
df = pd.DataFrame(hbonds.results.hbonds,
                  columns=['frame', 'donor_ix', 'hydrogen_ix', 'acceptor_ix',
                           'DA_dist', 'DHA_angle'])
```

### Principal Component Analysis (PCA)

```python
from MDAnalysis.analysis import pca

# Requires atom types (normally inferred when reading PDB) and matched atom order.
# Fit AND project the same already aligned coordinates. transform() does not align.
pca_analysis = pca.PCA(aligned, select='backbone', align=False).run()

# PC variances
print(pca_analysis.results.variance[:5])  # Raw coordinate variance in Å².
print(100 * pca_analysis.results.cumulated_variance[:5])  # Cumulative percent.

# Project trajectory onto PCs
projected = pca_analysis.transform(aligned.select_atoms('backbone'), n_components=3)
# Shape: (n_frames, n_components)
```

### Free Energy Surface (FES)

This is a relative, coordinate-dependent `-RT log p` surface for equilibrated,
unbiased sampling at one temperature. Biased/enhanced sampling requires the
appropriate reweighting first. Empty bins are unsampled, not measured barriers.
Bin size, coordinate Jacobians and autocorrelation affect interpretation; report
replicate/block uncertainty. A projected histogram is not a binding free energy.

```python
import numpy as np
import matplotlib.pyplot as plt

def plot_free_energy_surface(x, y, bins=50, T=300, xlabel="PC1", ylabel="PC2",
                              output="fes.png"):
    """
    Compute 2D free energy surface from two order parameters.
    FES = -kT * ln(P(x,y))
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.ndim != 1 or y.shape != x.shape or len(x) < 2:
        raise ValueError("x and y must be equal-length 1D arrays with at least two samples")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or not np.isfinite(T) or T <= 0:
        raise ValueError("Coordinates must be finite and T must be finite and positive")
    R_gas = 0.00831446261815324  # kJ/mol/K (molar gas constant)
    kT = R_gas * T

    # 2D histogram
    H, xedges, yedges = np.histogram2d(x, y, bins=bins, density=True)
    H = H.T

    # Free energy
    H_safe = np.where(H > 0, H, np.nan)
    fes = -kT * np.log(H_safe)
    fes -= np.nanmin(fes)  # Shift minimum to 0

    # Plot
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.pcolormesh(xedges, yedges, np.ma.masked_invalid(fes),
                       shading='flat', cmap='RdYlBu_r')
    plt.colorbar(im, ax=ax, label='Free Energy (kJ/mol)')
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.savefig(output, dpi=150, bbox_inches='tight')
    return fig
```

## Trajectory Formats Supported

| Format | Extension | Notes |
|--------|-----------|-------|
| DCD | `.dcd` | CHARMM/NAMD binary; widely used |
| XTC | `.xtc` | GROMACS compressed |
| TRR | `.trr` | GROMACS full precision |
| NetCDF | `.nc` | AMBER format |
| LAMMPS | `.lammpstrj` | LAMMPS dump |
| HDF5 | `.h5md` | H5MD standard |
| PDB | `.pdb` | Multi-model PDB |

## MDAnalysis Interoperability

```python
# Convert to numpy
positions = u.atoms.positions.copy()  # Snapshot in Å: shape (N, 3)

# Write to PDB
with mda.Writer("frame_10.pdb", u.atoms.n_atoms) as W:
    u.trajectory[10]  # Move to frame 10
    W.write(u.atoms)

# Write a topology with exactly the subset atom order before its trajectory.
protein = u.select_atoms("protein")
protein.write("protein_topology.pdb")
# Write a uniformly sampled trajectory subset, preserving the frame interval.
# DCD cannot represent arbitrary timestamps; separately record the time origin.
with mda.Writer("protein_traj.dcd", protein.n_atoms, dt=u.trajectory.dt) as W:
    for ts in u.trajectory:
        W.write(u.select_atoms("protein"))

# Convert to MDTraj (for compatibility)
# import mdtraj as md
# traj = md.load("trajectory.dcd", top="topology.pdb")
```

## Performance Tips

- **Use `in_memory=True`** for AlignTraj when RAM allows (much faster iteration)
- **Select minimal atoms** before analysis to reduce memory/compute
- **Parallel execution:** inspect `get_supported_backends()` for that class; do not
  assume every analysis or coordinate transformation supports multiprocessing
- **Choose a frame slice** with `start`/`stop`/`step`; slicing is not a general streaming
  guarantee (PCA still builds a coordinate covariance matrix):

```python
# Analyze every 10th frame from frame 100 to 1000
R.run(start=100, stop=1000, step=10)
```


## Official API references

- [RMSD/RMSF](https://docs.mdanalysis.org/2.10.0/documentation_pages/analysis/rms.html)
- [Alignment](https://docs.mdanalysis.org/2.10.0/documentation_pages/analysis/align.html)
- [PCA](https://docs.mdanalysis.org/2.10.0/documentation_pages/analysis/pca.html)
- [DSSP](https://docs.mdanalysis.org/2.10.0/documentation_pages/analysis/dssp.html)
- [Hydrogen bonds](https://docs.mdanalysis.org/2.10.0/documentation_pages/analysis/hydrogenbonds.html)
- [Groups and selections](https://docs.mdanalysis.org/2.10.0/documentation_pages/core/groups.html)
- [Distances and periodic boxes](https://docs.mdanalysis.org/2.10.0/documentation_pages/lib/distances.html)
- [Units](https://docs.mdanalysis.org/2.10.0/documentation_pages/units.html)
