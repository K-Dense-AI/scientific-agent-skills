# pymatgen Analysis

pymatgen is a large library and most people only use a fraction of it. This
covers the parts that come up most often when working with Materials Project data —
structure handling, symmetry, phase diagrams, electronic structure, and getting
data into formats other tools understand.

All examples assume you already have a `Structure` object, either from `mp-api`
or loaded from a file.

---

## Reading and writing structures

pymatgen can figure out the file format from the extension in most cases:

```python
from pymatgen.core import Structure

# from file — works for CIF, POSCAR/CONTCAR, XYZ, JSON, and others
structure = Structure.from_file("structure.cif")
structure = Structure.from_file("POSCAR")

# from a JSON saved with monty
from monty.serialization import loadfn
structure = loadfn("structure.json")

# from an ASE Atoms object (useful if you're coming from ASE or GPAW)
from pymatgen.io.ase import AseAtomsAdaptor
structure = AseAtomsAdaptor.get_structure(ase_atoms)
```

Writing is similarly straightforward:

```python
structure.to(filename="output.cif")
structure.to(filename="POSCAR")
structure.to(filename="output.xyz")   # non-periodic, mostly for visualization

# monty JSON — fully roundtrip serializable
from monty.serialization import dumpfn
dumpfn(structure, "structure.json")

# convert to ASE for downstream MD or NEB calculations
from pymatgen.io.ase import AseAtomsAdaptor
atoms = AseAtomsAdaptor.get_atoms(structure)
```

---

## SpacegroupAnalyzer — symmetry work

The workhorse for anything symmetry-related. It wraps spglib under the hood.

```python
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

sga = SpacegroupAnalyzer(structure, symprec=0.1)

sga.get_space_group_number()      # e.g. 225
sga.get_space_group_symbol()      # e.g. "Fm-3m"
sga.get_point_group_symbol()      # e.g. "m-3m"
sga.get_crystal_system()          # "cubic", "tetragonal", etc.
sga.get_lattice_type()            # similar, but returns the Bravais lattice type
sga.get_hall()                    # Hall symbol

primitive    = sga.get_primitive_standard_structure()
conventional = sga.get_conventional_standard_structure()
refined      = sga.get_refined_structure()

sym_ops     = sga.get_symmetry_operations()      # list of SymmOp objects
sym_dataset = sga.get_symmetry_dataset()         # raw spglib output dict
sym_struct  = sga.get_symmetrized_structure()    # SymmetrizedStructure with Wyckoff labels
```

A note on `symprec`: the default of `0.1` Å is calibrated for well-converged
DFT structures from the Materials Project. If you're working with a structure
from a less tightly converged relaxation, or something with thermal expansion
baked in, you might need `0.3` or even `0.5` to get sensible results. Going too
high will spuriously merge distinct sites.

---

## PhaseDiagram — thermodynamic stability

This is one of the more powerful things you can do with MP data. You pull all
the computed entries for a chemical system and pymatgen does the convex hull
construction.

```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter

with MPRester() as mpr:
    entries = mpr.get_entries_in_chemsys(["Li", "Fe", "O"])

pd_obj = PhaseDiagram(entries)

# key methods
pd_obj.stable_entries                          # set of entries on the hull
pd_obj.unstable_entries                        # everything else
pd_obj.get_e_above_hull(entry)                 # float, eV/atom
pd_obj.get_decomposition(composition)          # {entry: fraction} dict
pd_obj.get_equilibrium_reaction_energy(entry)  # float
pd_obj.get_hull_energy(composition)            # hull energy at that composition
pd_obj.get_form_energy(entry)                  # formation energy relative to references
```

As a rough guide: entries within ~25 meV/atom of the hull are generally
considered synthesizable. Between 25 and 100 meV/atom is a gray zone where
metastable phases are sometimes accessible. Above 100 meV/atom is usually
unstable in practice, though there are exceptions (some kinetically trapped phases
persist because the decomposition barrier is high).

Plotting:

```python
plotter = PDPlotter(pd_obj, backend="matplotlib")
plotter.show()
plotter.get_plot(show_unstable=0.05).savefig("phase_diagram.png", dpi=300)
# show_unstable=0.05 includes entries within 50 meV/atom of the hull
```

For open-system thermodynamics (e.g. oxygen partial pressure effects in
oxide systems), use `GrandPotentialPhaseDiagram`:

```python
from pymatgen.analysis.phase_diagram import GrandPotentialPhaseDiagram
from pymatgen.core import Element

# fix the oxygen chemical potential (units: eV per O atom)
# -5.0 eV is roughly reducing; -1.0 eV is strongly oxidizing
gppd = GrandPotentialPhaseDiagram(entries, {Element("O"): -5.0})
```

---

## StructureMatcher — comparing structures

Useful for deduplication, finding equivalent polymorphs, and checking
whether your DFT-relaxed structure drifted into a different phase.

```python
from pymatgen.analysis.structure_matcher import StructureMatcher

sm = StructureMatcher(
    ltol=0.2,             # fractional tolerance on lattice lengths
    stol=0.3,             # site tolerance as fraction of average nearest-neighbor distance
    angle_tol=5,          # tolerance on lattice angles (degrees)
    primitive_cell=True,  # reduce to primitive cell before comparing
    scale=True,           # allow volume scaling
    attempt_supercell=False
)

sm.fit(s1, s2)                          # True if structures are equivalent
sm.group_structures(list_of_structures)  # returns list of equivalent groups
sm.get_mapping(s1, s2)                  # atom-to-atom mapping, or None
sm.find_indexes(s1, [s2, s3, s4])       # index of the best match in the list
```

The defaults are reasonable for comparing MP structures to each other. If you're
comparing against something from experiment (where the cell may not be optimally
converged), loosen `ltol` and `angle_tol` somewhat.

---

## BVAnalyzer — oxidation state assignment via bond valence

Quick and reasonably reliable for most ionic materials:

```python
from pymatgen.analysis.bond_valence import BVAnalyzer

bva = BVAnalyzer()

# returns a copy of the structure decorated with oxidation states
structure_with_oxi = bva.get_oxi_state_decorated_structure(structure)

# or just the list of valences
valences = bva.get_valences(structure)   # list of floats, one per site
```

This can fail on unusual compounds or materials with mixed valency. In those
cases `get_valences()` raises a `ValueError` — worth catching if you're running
this in bulk.

---

## DosPlotter and BSPlotter — electronic structure visualization

```python
from mp_api.client import MPRester
from pymatgen.electronic_structure.plotter import DosPlotter, BSPlotter

with MPRester() as mpr:
    dos = mpr.get_dos_by_material_id("mp-2715")
    bs  = mpr.get_bandstructure_by_material_id("mp-2715")

# DOS — add total and element-projected contributions
dp = DosPlotter()
dp.add_dos("Total", dos)
dp.add_dos_dict(dos.get_element_dos())    # element-projected
dp.add_dos_dict(dos.get_spd_dos())        # s/p/d orbital projected
plt = dp.get_plot(xlim=(-6, 6), ylim=(-5, 20))
plt.savefig("dos.png", dpi=300)

# band structure
bp = BSPlotter(bs)
bp.get_plot(zero_to_efermi=True, vbm_cbm_marker=True).show()
bp.save_plot("bandstructure.png")

# extracting numbers you actually need
bg = bs.get_band_gap()
print(f"Gap: {bg['energy']:.3f} eV")
print(f"Direct: {bg['direct']}")
print(f"Transition: {bg['transition']}")   # e.g. "Γ→X" for indirect gap

vbm = bs.get_vbm()   # dict with 'energy', 'kpoint', 'band_index'
cbm = bs.get_cbm()
print(f"VBM at {vbm['kpoint'].label}, {vbm['energy']:.3f} eV")
print(f"CBM at {cbm['kpoint'].label}, {cbm['energy']:.3f} eV")
```

---

## VASP input generation

pymatgen has input sets that encode the standard MP calculation parameters —
same ones used to build the database. This is helpful for making calculations
that are directly comparable to MP data.

```python
from pymatgen.io.vasp.sets import (
    MPRelaxSet,        # standard structure relaxation
    MPStaticSet,       # single-point energy / charge density
    MPNonSCFSet,       # non-self-consistent (DOS and band structure)
    MPMetalRelaxSet,   # uses denser k-mesh and smearing for metals
    MPScanRelaxSet     # SCAN meta-GGA functional
)

relax = MPRelaxSet(structure, user_incar_settings={"EDIFF": 1e-6})
relax.write_input("./vasp_relax/")

static = MPStaticSet(structure)
static.write_input("./vasp_static/")

# non-SCF for band structure, using the charge density from a prior static run
nscf = MPNonSCFSet.from_prev_calc(prev_calc_dir="./vasp_static/", mode="line")
nscf.write_input("./vasp_nscf/")
```

The `write_input()` method tries to write a POTCAR and will raise an error if
`PMG_VASP_PSP_DIR` isn't configured. Workaround:

```python
relax.write_input("./vasp_relax/", potcar_spec=True)
# writes POTCAR.spec instead — you assemble the real POTCAR separately
```

---

## Composition — formula arithmetic

`Composition` lets you work with chemical formulas as objects rather than strings,
which is useful when building phase diagrams or comparing compositions:

```python
from pymatgen.core import Composition

c = Composition("Li3PO4")

c.reduced_formula                # "Li3PO4"
c.hill_formula                   # "Li3O4P" (carbon-first, then alphabetical)
c.formula                        # "Li3 P1 O4"
c.num_atoms                      # 8.0
c.weight                         # molecular weight in g/mol
c.get_atomic_fraction("O")       # 0.5
c.elements                       # [Element Li, Element P, Element O]
c.chemical_system                # "Li-O-P"

# element fractions
for el, frac in c.items():
    print(el, frac)
```

---

## AseAtomsAdaptor — bridge to ASE

If you need to use an ASE calculator (EMT, GPAW, MACE, etc.) with a structure
from pymatgen:

```python
from pymatgen.io.ase import AseAtomsAdaptor

# pymatgen → ASE
atoms = AseAtomsAdaptor.get_atoms(structure)

# ASE → pymatgen
structure = AseAtomsAdaptor.get_structure(atoms)
```

This is a lossless roundtrip for the basic structural data (positions, cell,
species). Some information like site properties and oxidation states may not
survive depending on the ASE calculator's output format.

---

## matminer — ML feature generation from MP structures

`matminer` is a separate package (not part of pymatgen) but is commonly used
alongside it for building ML models on materials data:

```bash
uv pip install matminer
```

```python
from matminer.featurizers.structure import SiteStatsFingerprint
from matminer.featurizers.site import CrystalNNFingerprint
import pandas as pd

# Build a structural fingerprint featurizer
ssf = SiteStatsFingerprint(CrystalNNFingerprint.from_preset("ops"))
ssf.fit([structure])
features = ssf.featurize(structure)   # numpy array of descriptors

# Featurize a whole DataFrame of MP results efficiently
df = pd.DataFrame([{
    "structure": mpr.get_structure_by_material_id(r.material_id),
    "band_gap":  r.band_gap,
    "mp_id":     r.material_id,
} for r in results])

df = ssf.featurize_dataframe(df, "structure", ignore_errors=True)
# ignore_errors=True skips structures that fail featurization
# rather than crashing your whole batch
```

matminer has dozens of featurizers beyond `SiteStatsFingerprint`. The
[matminer documentation](https://hackingmaterials.lbl.gov/matminer/) has a
full catalog sorted by whether they operate on structures, compositions, or sites.