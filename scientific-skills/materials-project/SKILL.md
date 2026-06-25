---
name: materials-project
description: Query the Materials Project database (150,000+ computed inorganic materials) using mp-api and pymatgen. Use for crystal structure retrieval, band gap and electronic structure analysis, phase diagram construction, formation energy calculations, thermodynamic stability screening, and high-throughput materials discovery workflows. Triggers on keywords like "materials project", "crystal structure", "band gap", "phase diagram", "formation energy", "mp-id", "pymatgen", "computational materials", "DFT", "convex hull", or any request to screen, search, or analyze inorganic solid-state materials at scale.
allowed-tools: Read, Write, Edit, Bash
license: MIT license
metadata:
  skill-author: Community Contributor
---

# Materials Project

## What this is

The Materials Project is a DOE-funded database of quantum-mechanical properties
for over 150,000 inorganic materials, all computed with DFT. It has been running
since 2011 and at this point it's basically the first stop for anyone doing
computational materials work — battery research, solar cells, thermoelectrics,
hard coatings, you name it. The data is free and the Python client (`mp-api`)
is genuinely well-maintained.

This skill wraps two things: `mp-api`, which is the official client for talking
to the database, and `pymatgen` (Python Materials Genomics), which is the library
that actually lets you do something useful with the structures and data you get
back. The two are developed together and you really need both.

## When to reach for this skill

Any time the conversation involves:

- Looking up a crystal structure, pulling a band gap, or grabbing formation
  energies for a list of materials
- Building a phase diagram and checking whether something sits on the convex hull
- Screening thousands of materials by property ranges — band gap windows,
  stability cutoffs, magnetic ordering, etc.
- Starting a DFT calculation and needing a properly-relaxed input structure
- Converting between structure file formats (CIF, POSCAR, XYZ, JSON)
- Symmetry work — space groups, Wyckoff positions, primitive vs. conventional cells
- Anything described as "high-throughput" or "computational materials screening"

Keywords that should trigger this: "materials project", "crystal structure",
"band gap", "phase diagram", "formation energy", "energy above hull", "pymatgen",
"mp-api", "mp-id", "DFT", "convex hull", "inorganic material", "solid-state",
"thermoelectric", "battery cathode", "solar absorber", "synthesizability".

## Getting your API key

You need an API key. It's completely free, just requires registration.

Sign up at https://materialsproject.org, then go to your dashboard and hit
"Generate API Key". You'll get a long alphanumeric string — treat it like a
password, don't commit it to version control.

The cleanest way to handle it is an environment variable:

```bash
export MP_API_KEY="your_api_key_here"
```

Put that in your `.bashrc` or `.zshrc` and forget about it. Once it's set,
`MPRester()` picks it up automatically and you never have to pass it explicitly.

If you'd rather configure it through pymatgen (writes to `~/.config/pymatgen/config.yaml`):

```bash
python -c "from pymatgen.core import SETTINGS; SETTINGS['PMG_MAPI_KEY'] = 'your_key'"
```

One thing worth knowing: the free tier is rate-limited to around 5 requests/second
and 1,000 requests/hour. In practice this is fine for most workflows, but if
you're looping over individual material IDs for a large list, you'll hit the wall.
The fix is always to use a single `search()` call with `material_ids=[...]` rather
than individual lookups — the API handles batching internally.

## Installation

```bash
# the two things you actually need
uv pip install mp-api pymatgen

# visualization — add these if you're plotting phase diagrams or DOS
uv pip install matplotlib plotly crystal-toolkit

# if you're working in notebooks or doing ML feature generation
uv pip install jupyter matminer
```

pymatgen requires Python 3.10 or newer. If you're on something older, upgrade
before trying to debug mysterious import errors.

## Core patterns

### Searching by formula or chemical system

The `summary` endpoint is where you'll spend most of your time. It has the
broadest coverage and the fastest response times.

```python
from mp_api.client import MPRester

with MPRester() as mpr:
    results = mpr.materials.summary.search(
        formula="Fe2O3",
        fields=["material_id", "formula_pretty", "energy_above_hull",
                "band_gap", "is_stable"]
    )
    for r in results:
        print(r.material_id, r.formula_pretty, r.energy_above_hull, r.band_gap)
```

Always pass `fields`. Without it, the API returns everything it knows about each
material, which is slow and wastes bandwidth. Only request what you'll actually use.

### Fetching a structure by MP ID

```python
from mp_api.client import MPRester

with MPRester() as mpr:
    structure = mpr.get_structure_by_material_id("mp-1234")

print(structure)
print(f"Space group: {structure.get_space_group_info()}")
print(f"Lattice: {structure.lattice}")

# save it
structure.to(filename="mp-1234.cif")       # CIF
structure.to(filename="POSCAR")             # VASP input
```

The returned object is a pymatgen `Structure` — you get all pymatgen's analysis
methods on it for free.

### Screening by property range

Pass a `(min, max)` tuple for any numeric field. Use `None` for an open-ended
bound. This is how you do large-scale screening without looping:

```python
from mp_api.client import MPRester

with MPRester() as mpr:
    candidates = mpr.materials.summary.search(
        band_gap=(1.0, 2.0),
        is_stable=True,
        is_metal=False,
        fields=["material_id", "formula_pretty", "band_gap",
                "formation_energy_per_atom", "density"]
    )

print(f"Found {len(candidates)} candidates")
for c in candidates[:10]:
    print(f"{c.formula_pretty:15s}  Eg={c.band_gap:.2f} eV  "
          f"Ef={c.formation_energy_per_atom:.3f} eV/atom")
```

### Phase diagrams

This is one of the most powerful things the Materials Project enables. You pull
all the entries for a chemical system and let pymatgen compute the convex hull:

```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter

with MPRester() as mpr:
    entries = mpr.get_entries_in_chemsys(["Li", "Fe", "O"])

pd = PhaseDiagram(entries)
PDPlotter(pd).show()

# check how stable a specific compound is
with MPRester() as mpr:
    entry = mpr.get_entry_by_material_id("mp-757979")

ehull = pd.get_e_above_hull(entry)
print(f"Energy above hull: {ehull:.3f} eV/atom")
# < 0.025 eV/atom is generally considered synthesizable
```

### Electronic structure (DOS and band structure)

```python
from mp_api.client import MPRester
from pymatgen.electronic_structure.plotter import DosPlotter, BSPlotter

with MPRester() as mpr:
    dos = mpr.get_dos_by_material_id("mp-2715")   # GaAs
    bs  = mpr.get_bandstructure_by_material_id("mp-2715")

dp = DosPlotter()
dp.add_dos("Total DOS", dos)
dp.get_plot(xlim=(-6, 6)).show()

BSPlotter(bs).get_plot().show()

print(f"Band gap: {bs.get_band_gap()['energy']:.3f} eV")
print(f"Direct gap: {bs.get_band_gap()['direct']}")
```

### Symmetry analysis

```python
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from mp_api.client import MPRester

with MPRester() as mpr:
    structure = mpr.get_structure_by_material_id("mp-22862")  # TiO2 rutile

sga = SpacegroupAnalyzer(structure)
print(f"Space group: {sga.get_space_group_symbol()} ({sga.get_space_group_number()})")
print(f"Crystal system: {sga.get_crystal_system()}")
print(f"Point group: {sga.get_point_group_symbol()}")

primitive    = sga.get_primitive_standard_structure()
conventional = sga.get_conventional_standard_structure()
```

The default `symprec=0.1` Å works fine for MP structures. If you're analyzing
slightly distorted structures from a relaxation that didn't fully converge, try
bumping it to `0.3` before concluding the symmetry is broken.

### Bulk screening into a DataFrame

For anything involving more than ~20 materials, put it in a DataFrame:

```python
import pandas as pd
from mp_api.client import MPRester

with MPRester() as mpr:
    results = mpr.materials.summary.search(
        chemsys="Li-*-O",
        energy_above_hull=(0, 0.05),
        fields=["material_id", "formula_pretty", "band_gap",
                "formation_energy_per_atom", "energy_above_hull",
                "theoretical", "nsites"]
    )

df = pd.DataFrame([{
    "mp_id":     r.material_id,
    "formula":   r.formula_pretty,
    "Eg_eV":     r.band_gap,
    "Ef_eV_at":  r.formation_energy_per_atom,
    "Ehull":     r.energy_above_hull,
    "theory_only": r.theoretical,
    "n_sites":   r.nsites,
} for r in results])

df.sort_values("Ehull").to_csv("li_oxide_screen.csv", index=False)
```

### Elastic and mechanical properties

Not every material in the database has elasticity data — the calculations are
expensive. But for the ones that do:

```python
from mp_api.client import MPRester

with MPRester() as mpr:
    docs = mpr.materials.elasticity.search(
        material_ids=["mp-149"],   # Si
        fields=["material_id", "bulk_modulus", "shear_modulus",
                "universal_anisotropy", "elastic_tensor"]
    )

if docs:
    e = docs[0]
    print(f"Bulk modulus (Voigt): {e.bulk_modulus.voigt:.1f} GPa")
    print(f"Shear modulus (Voigt): {e.shear_modulus.voigt:.1f} GPa")
    print(f"Anisotropy: {e.universal_anisotropy:.4f}")
```

### Magnetic properties

```python
from mp_api.client import MPRester

with MPRester() as mpr:
    results = mpr.materials.summary.search(
        formula="Fe*O*",
        ordering="FiM",   # FM, AFM, FiM, or NM
        fields=["material_id", "formula_pretty", "total_magnetization",
                "ordering", "band_gap"]
    )

for r in results:
    print(f"{r.formula_pretty:15s}  μ={r.total_magnetization:.2f} μB  "
          f"{r.ordering}  Eg={r.band_gap:.2f} eV")
```

### Preparing VASP input files

```python
from mp_api.client import MPRester
from pymatgen.io.vasp.sets import MPRelaxSet
from monty.serialization import dumpfn

with MPRester() as mpr:
    structure = mpr.get_structure_by_material_id("mp-804")  # LiFePO4

# writes INCAR, KPOINTS, POSCAR (and POTCAR if your PSP library is configured)
MPRelaxSet(structure).write_input("./vasp_inputs/")

# also save a JSON copy for later
dumpfn(structure, "LiFePO4.json")
```

If you get an error about POTCAR, add `potcar_spec=True` to `write_input()` —
it writes a POTCAR.spec file listing the pseudopotentials without needing your
local POTCAR library. You'd still need to assemble the actual POTCAR before
submitting to a cluster.

## API endpoints at a glance

The `MPRester` organizes data into sub-clients. You access them as `mpr.<name>`:

| Sub-client | What you get |
|---|---|
| `mpr.materials.summary` | The main one — formula, stability, band gap, magnetic ordering |
| `mpr.materials.electronic_structure` | DOS and band structure objects |
| `mpr.materials.elasticity` | Elastic tensor, bulk/shear moduli, Poisson ratio |
| `mpr.materials.magnetism` | Magnetic ordering, site-resolved moments |
| `mpr.materials.dielectric` | Dielectric tensor, refractive index |
| `mpr.materials.piezoelectric` | Piezoelectric tensor and derived properties |
| `mpr.materials.phonon` | Phonon band structure and DOS |
| `mpr.materials.substrates` | Epitaxial substrate suggestions |
| `mpr.materials.surface_properties` | Surface energies, work functions |
| `mpr.materials.grain_boundaries` | Grain boundary energies |
| `mpr.materials.bonds` | Chemical bonding graphs |
| `mpr.materials.chemenv` | Chemical environment (coordination) analysis |
| `mpr.materials.alloys` | Suggested alloy pairs from phase stability |
| `mpr.materials.oxidation_states` | Predicted oxidation states |
| `mpr.materials.thermo` | Thermodynamic entries for phase diagram work |
| `mpr.materials.absorption` | Optical absorption spectra |
| `mpr.molecules.summary` | Molecular properties (separate dataset) |

To see every queryable field on an endpoint:

```python
with MPRester() as mpr:
    print(mpr.materials.summary.available_fields)
```

## Key pymatgen objects

| Class | Module | What it does |
|---|---|---|
| `Structure` | `pymatgen.core` | Periodic crystal structure — everything hangs off this |
| `Composition` | `pymatgen.core` | Chemical formula with proper element arithmetic |
| `Element`, `Species` | `pymatgen.core` | Element and oxidation-state representations |
| `Lattice` | `pymatgen.core` | Bravais lattice with all crystallographic methods |
| `SpacegroupAnalyzer` | `pymatgen.symmetry.analyzer` | Space group, point group, Wyckoff positions |
| `PhaseDiagram` | `pymatgen.analysis.phase_diagram` | Convex hull from a list of entries |
| `PDPlotter` | `pymatgen.analysis.phase_diagram` | 2D/3D phase diagram plots |
| `DosPlotter` | `pymatgen.electronic_structure.plotter` | DOS visualization |
| `BSPlotter` | `pymatgen.electronic_structure.plotter` | Band structure plots |
| `MPRelaxSet` | `pymatgen.io.vasp.sets` | Standard MP-compatible VASP inputs |
| `CifParser` | `pymatgen.io.cif` | Read/write CIF files |
| `StructureMatcher` | `pymatgen.analysis.structure_matcher` | Compare structures for equivalence |
| `BVAnalyzer` | `pymatgen.analysis.bond_valence` | Oxidation state assignment via bond valence |

## Things that will trip you up

**"API key not found" error** — You either forgot to set `MP_API_KEY` or the
environment variable isn't being picked up by the current shell. Run
`echo $MP_API_KEY` to confirm it's there. If empty, re-export it or pass
the key directly as `MPRester("your_key")`.

**Rate limit (HTTP 429)** — You're hitting the API in a tight loop. Switch to
a single `search()` call with `material_ids=[list_of_ids]` instead of looping.
If you genuinely need per-entry calls, add `time.sleep(0.25)` between them.

**Empty results from a chemsys query** — The chemical system format is hyphen-separated
elements, e.g. `"Li-Fe-O"`, not comma-separated. Also note that `chemsys` returns
*all* sub-systems — so `"Li-Fe-O"` includes Li oxides, Fe oxides, and binary
compounds in addition to ternaries. Use `nelements=3` to filter to strictly
ternary if that's what you want.

**Wrong MPRester import** — There are two. The old one is
`from pymatgen.ext.matproj import MPRester` and it points at the deprecated v1 API.
Always use `from mp_api.client import MPRester`. If your code was written before
2022, this is probably the issue.

**`MontyDecodeError`** — Usually a version mismatch between `mp-api` and `pymatgen`.
Run `uv pip install --upgrade mp-api pymatgen` to sync them.

**Missing POTCAR when writing VASP inputs** — `MPRelaxSet.write_input()` needs a
local POTCAR library configured via `PMG_VASP_PSP_DIR`. If you're just prototyping
or don't have the PAW files, pass `potcar_spec=True` and it'll write a spec file
instead of complaining.

**`theoretical=True` results mixed in** — The default search includes both
experimentally observed compounds (from the ICSD) and purely theoretical ones.
Set `theoretical=False` to restrict to compounds that have actually been made.
This matters a lot for synthesizability assessments.

## Works well alongside

- **matplotlib / plotly** — for phase diagram figures, DOS plots, property scatter plots
- **matminer** — for generating ML features from MP structures at scale
- **deepchem** — materials ML models trained on MP data
- **ase** (Atomic Simulation Environment) — `AseAtomsAdaptor` converts between
  pymatgen `Structure` and ASE `Atoms` objects for MD or NEB workflows
- **exploratory-data-analysis** skill — pandas + seaborn for screening large result sets
- **molecular-dynamics** skill — use MP structures as starting geometries for AIMD

## Further reading

- `references/api_endpoints.md` — detailed field listings for every endpoint
- `references/pymatgen_analysis.md` — deeper coverage of symmetry, phase diagrams,
  electronic structure, and structure manipulation in pymatgen
- `references/workflows.md` — complete worked examples for battery screening,
  solar absorbers, thermoelectrics, defect calculations, and combining MP data
  with local DFT results