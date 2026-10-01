# Analysis: tolerances, computed entries, bands, DOS, and model limits

This reference targets `pymatgen==2026.9.24` with
`pymatgen-core==2026.9.23`. An analysis object returning a value does not
establish convergence, uncertainty, experimental agreement, or suitability of
the underlying model.

## Symmetry

```python
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

analyzer = SpacegroupAnalyzer(
    structure,
    symprec=0.01,          # Å
    angle_tolerance=5.0,   # degrees
)

result = {
    "symbol": analyzer.get_space_group_symbol(),
    "number": analyzer.get_space_group_number(),
    "crystal_system": str(analyzer.get_crystal_system()),
    "point_group": analyzer.get_point_group_symbol(),
    "operation_count": len(analyzer.get_symmetry_operations()),
}
symmetrized = analyzer.get_symmetrized_structure()
equivalent_indices = symmetrized.equivalent_indices
wyckoff_symbols = symmetrized.wyckoff_symbols
```

The documented pymatgen default is `symprec=0.01 Å`; a looser value such as
`0.1 Å` is often used for relaxed structures and by the Materials Project
pipeline. Results can change with:

- coordinate precision and relaxation noise
- occupancy/disorder model
- oxidation/spin/site properties used or ignored
- primitive/conventional representation
- `symprec`, `angle_tolerance`, and spglib version

Always sweep justified tolerances and report the entire sensitivity grid. Do
not choose a tolerance solely because it gives a desired group.

Standardized or primitive structures are new representations:

```python
conventional = analyzer.get_conventional_standard_structure(
    keep_site_properties=False
)
primitive = analyzer.get_primitive_standard_structure(
    keep_site_properties=False
)
```

Site properties can be lost or propagated without symmetry-aware adjustment.
Preserve the parent and compare composition, volume per atom, magnetic order,
and property semantics.

## Structure matching

```python
from pymatgen.analysis.structure_matcher import StructureMatcher

matcher = StructureMatcher(
    ltol=0.2,
    stol=0.3,
    angle_tol=5,
    primitive_cell=True,
    scale=True,
)
matches = matcher.fit(first, second)
```

Record every tolerance and option. A match is equivalence under the chosen
algorithm, reductions, scaling, and species comparator—not identity of files,
provenance, defects, magnetic states, or experimental phases.

`fit()` is directional. For order-independent grouping use
`matcher.group_structures(structures, symmetric=True)` in this snapshot;
the new option is ignored for anonymous matching. Current mixed-functional
entry processing also sorts inputs and uses symmetric grouping, fixing earlier
hash-seed-dependent hulls. Recompute old mixed hulls when comparing versions.

## Local environments

```python
from pymatgen.analysis.local_env import CrystalNN, VoronoiNN

crystal_nn = CrystalNN()
neighbors = crystal_nn.get_nn_info(structure, 0)

voronoi_nn = VoronoiNN()
voronoi_neighbors = voronoi_nn.get_nn_info(structure, 0)
```

Coordination depends on the method, radii/oxidation information, weights,
cutoffs, disorder, and geometry. Preserve:

- algorithm and pymatgen version
- all constructor settings
- oxidation-state decoration
- site index/label mapping
- warnings and failures
- whether weighted or integer coordination was reported

Bound the number of sites and neighbors emitted. Cross-check model-sensitive
conclusions with more than one justified definition.

## Phase diagrams

An `Entry` contains a composition and a total energy:

```python
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.entries.computed_entries import ComputedEntry

entries = [
    ComputedEntry("Li", -1.0, entry_id="local-Li"),
    ComputedEntry("O2", -2.0, entry_id="local-O2"),
    ComputedEntry("Li2O", -4.0, entry_id="local-Li2O"),
]
diagram = PhaseDiagram(entries)

for entry in entries:
    print(
        entry.entry_id,
        diagram.get_form_energy_per_atom(entry),
        diagram.get_e_above_hull(entry),
    )
```

`ComputedEntry.energy` is total eV for the represented composition, not
eV/atom. `energy_per_atom`, formation energy, and hull distance are normalized
values.

### Comparability gate

Before constructing a hull, verify that entries share a compatible:

- functional and correction/mixing scheme
- pseudopotential family and valence configuration
- magnetic, spin, and SOC treatment
- reference-state convention
- numerical convergence level
- temperature/pressure model

Include elemental endpoints and all relevant competing phases. Missing phases
can make unstable entries appear stable. Duplicate compositions are allowed as
polymorphs only when their energies are comparable and provenance is distinct.

`diagram.stable_entries` means on the computed zero-temperature convex hull for
that exact entry set. It is not experimental stability or synthesizability.

### Decomposition

```python
from pymatgen.core import Composition

target = Composition("Li2O", strict=True)
decomposition = diagram.get_decomposition(target)
```

For an existing entry, use `get_e_above_hull(entry)`. A bare composition has no
candidate energy, so it has a hull decomposition but no intrinsic energy above
hull.

### Plotting

```python
from pymatgen.analysis.phase_diagram import PDPlotter

plotter = PDPlotter(diagram, show_unstable=0.2, backend="matplotlib")
plotter.write_image("phase.new.svg", image_format="svg")
```

Plot to a new path, bound unstable points and output size, and preserve the
machine-readable entry table. Plotting backends and image export can introduce
optional dependencies. The default Plotly backend needs its image-export stack;
the bundled CLI selects Matplotlib so PNG/PDF/SVG export works with the tested
package set.

## Chemical-potential and Pourbaix analyses

`ChemicalPotentialDiagram` and `PourbaixDiagram` add assumptions beyond a
composition hull. Record reference states, open species, aqueous ion data,
concentrations, pH, electrochemical potential, temperature, corrections, and
solvent convention. Do not reuse a solid-state entry set as a valid aqueous
thermodynamic model without the required transformations and references.

## Electronic band structures

The following VASP snippets are illustrative because they require the user's
calculation files; the current method signatures were verified.

```python
from pymatgen.io.vasp import Vasprun

run = Vasprun(
    "vasprun.xml",
    parse_dos=False,
    parse_eigen=True,
    parse_projected_eigen=False,
    parse_potcar_file=False,
)
bands = run.get_band_structure(line_mode=True)

gap = bands.get_band_gap()
vbm = bands.get_vbm()
cbm = bands.get_cbm()
metal = bands.is_metal()
```

Report:

- source calculation and convergence status
- structure checksum
- functional, pseudopotentials, DFT+U, spin, SOC
- k-point mesh/path and line-mode reconstruction
- Fermi-energy convention and any override
- occupation/smearing settings
- direct/indirect criterion and numerical tolerance

A DFT band gap is method-dependent. Materials Project documents that its PBE
band gaps are systematically underestimated.

`BSPlotter` can plot a `BandStructureSymmLine`; plotting does not validate the
k-path. High-symmetry paths depend on crystallographic setting and magnetic
primitive-cell assumptions.

## Density of states

```python
from pymatgen.io.vasp import Vasprun

run = Vasprun(
    "vasprun.xml",
    parse_dos=True,
    parse_eigen=False,
    parse_projected_eigen=False,
    parse_potcar_file=False,
)
dos = run.complete_dos
element_dos = dos.get_element_dos()
site_dos = dos.get_site_dos(run.final_structure[0])
orbital_dos = dos.get_spd_dos()
```

Check:

- energy grid and reference/Fermi level
- density units and normalization
- spin channels and SOC
- smearing and integration method
- projection basis and completeness
- consistency between DOS sites and final structure

Do not compare integrated/projected DOS across calculations until these
conventions match.

For individual d orbitals, use `Orbital.dx2_y2`. `Orbital.dx2` remains a
deprecated alias until 2027-08-17; this snapshot still serializes the legacy
`dx2` key while accepting both spellings on read.

## VASP parse cost

`Vasprun(parse_projected_eigen=True)` can require extreme time and memory.
`BSVasprun` is optimized for eigenvalue-focused band-structure parsing. Large
XML/HDF5/volumetric files need file-size, array-size, site/k-point/band, memory,
and wall-time bounds.

## Diffraction

```python
from pymatgen.analysis.diffraction.xrd import XRDCalculator

calculator = XRDCalculator(wavelength="CuKa")
pattern = calculator.get_pattern(
    structure,
    scaled=True,
    two_theta_range=(5, 90),
)

for two_theta, intensity, hkls in zip(
    pattern.x,
    pattern.y,
    pattern.hkls,
    strict=True,
):
    print(two_theta, intensity, hkls)
```

Peak positions/intensities depend on radiation, occupancies, structure,
instrumental broadening, preferred orientation, temperature/displacement, and
the ideal-powder model. A simulated pattern is not a phase-identification
result by itself.

## Surfaces, slabs, and Wulff shapes

```python
from pymatgen.core.surface import SlabGenerator

generator = SlabGenerator(
    structure,
    miller_index=(1, 1, 1),
    min_slab_size=12.0,
    min_vacuum_size=15.0,
    center_slab=True,
    in_unit_planes=False,
)
slabs = generator.get_slabs()
```

Record bulk parent, Miller-index convention, slab/vacuum units, termination,
symmetrization, dipole correction, in-plane cell, fixed layers, and candidate
limit. Slab thickness and vacuum are convergence parameters, not universal
constants.

Current `WulffShape` takes parallel Miller-index and surface-energy sequences:

```python
from pymatgen.analysis.wulff import WulffShape

wulff = WulffShape(
    structure.lattice,
    [(1, 0, 0), (1, 1, 0), (1, 1, 1)],
    [1.0, 1.1, 0.9],  # one consistent energy unit per area
)
```

Surface energies must share composition/chemical-potential, slab, functional,
and area conventions. Report their unit explicitly.

## Adsorption

`AdsorbateSiteFinder` produces geometric candidates, not adsorption energies or
preferred sites. Bound generated structures and preserve slab termination,
adsorbate geometry/charge/spin, coverage, orientation, and parent mapping.

## Elasticity and other tensors

`pymatgen.analysis.elasticity` represents strain, stress, and elastic tensors.
Verify Voigt index convention, stress sign, units (typically GPa for reported
moduli), reference frame, crystal symmetry, finite-strain magnitude, and fit
quality. Mechanical-stability criteria depend on crystal class and conditions.

## Analysis report checklist

- source checksum and parser warnings
- exact package versions
- units and normalization
- all tolerances/model parameters
- bounded input/output sizes
- disorder and oxidation-state handling
- convergence and uncertainty evidence
- method-specific caveats
- no claim of experimental truth from computed output alone

## Sources (verified 2026-09-30)

- [pymatgen analysis API](https://pymatgen.org/pymatgen.analysis.html)
- [pymatgen symmetry API](https://pymatgen.org/pymatgen.symmetry.html)
- [pymatgen electronic-structure API](https://pymatgen.org/pymatgen.electronic_structure.html)
- [pymatgen VASP API](https://pymatgen.org/pymatgen.io.vasp.html)
- [pymatgen usage guide](https://pymatgen.org/usage.html)
- [pymatgen changelog](https://pymatgen.org/CHANGES.html)
- [Materials Project electronic-structure methodology](https://docs.materialsproject.org/methodology/materials-methodology/electronic-structure)
- [Materials Project computed-data FAQ](https://docs.materialsproject.org/frequently-asked-questions)
