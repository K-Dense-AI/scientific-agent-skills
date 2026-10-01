# Core classes: explicit chemistry, coordinates, and periodicity

This reference targets the verified `pymatgen==2026.9.24` wrapper with
`pymatgen-core==2026.9.23`. Core objects now ship from `pymatgen-core` but keep
the public `pymatgen.core` namespace.

## Units and representation

Pymatgen does not make every quantity "atomic units." Common contracts include:

- lattice vectors and Cartesian coordinates: Å
- lattice angles: degrees
- structure volume: Å³
- density: g/cm³
- composition weight: amu for the represented composition
- electronic and entry energies: usually eV; phase-diagram normalized values:
  eV/atom

Read the specific method contract before combining quantities. Record units in
every artifact.

`Structure` is periodic and owns a `Lattice`; `Molecule` is non-periodic.
Structure coordinates are fractional by default. Molecule coordinates are
Cartesian. Never infer which object or coordinate mode the user intended.

## Element and Species

```python
from pymatgen.core import DummySpecies, Element, Species

iron = Element("Fe")
silicon = Element.from_Z(14)
oxygen = Element.from_name("oxygen")
fe2 = Species("Fe", oxidation_state=2)
vacancy_label = DummySpecies("X")
```

Important distinctions:

- `Element.symbol` is the chemical symbol.
- `Element.Z` is atomic number.
- `Element.X` is Pauling electronegativity, not the symbol.
- Elemental properties can be missing or uncertain; do not replace missing
  values with zero.
- `Species` adds oxidation state and optional properties. Oxidation state is
  formal chemical annotation, not an automatically validated charge model.
- A dummy species is a modeling label, not a physical atom.

Current API documentation also exposes predicates and data such as
`is_metal`, `is_noble_gas`, `atomic_mass`, oxidation-state sets, and electronic
configuration. Check for `None`/missing values and retain property provenance.

## Composition

Use strict parsing at external boundaries:

```python
from pymatgen.core import Composition

composition = Composition("LiFePO4", strict=True)
formula = composition.formula
reduced = composition.reduced_formula
chemical_system = composition.chemical_system
mass_amu = float(composition.weight)
```

Construction from a mapping is explicit:

```python
composition = Composition({"Fe": 2, "O": 3}, strict=True)
```

Safety rules:

1. Bound formula length before parsing.
2. Reject duplicate JSON keys, non-finite values, and non-positive amounts in
   external mappings.
3. Keep full and reduced formulas distinct. Reduction loses the integer scale.
4. A composition is not a structure, phase, oxidation-state assignment, or
   proof that a compound exists.
5. `oxi_state_guesses()` is heuristic and can be combinatorial. Call it only
   after explicit user approval and bound elements, formula size, runtime, and
   returned guesses.
6. Do not mix `Element` and oxidized `Species` keys without intentionally
   defining how charge decoration should behave.

The bundled validator does not guess by default:

```bash
python scripts/composition_structure_validator.py composition "Fe2O3"
python scripts/composition_structure_validator.py composition "Fe2O3" \
  --guess-oxidation-states
```

## Lattice

```python
from pymatgen.core import Lattice

cubic = Lattice.cubic(5.64)
triclinic = Lattice.from_parameters(
    a=4.0,
    b=5.0,
    c=6.0,
    alpha=80,
    beta=90,
    gamma=100,
)
matrix_lattice = Lattice(
    [
        [4.0, 0.0, 0.0],
        [0.5, 5.0, 0.0],
        [0.2, 0.3, 6.0],
    ],
    pbc=(True, True, True),
)
```

The matrix rows are lattice vectors. Preserve:

- matrix and `(a, b, c)`
- `(alpha, beta, gamma)`
- determinant/volume and handedness
- periodic-boundary-condition tuple
- whether the cell was reduced, standardized, strained, or transformed

Niggli/LLL reduction and crystallographic standardization can change the cell
basis and site coordinates without changing intended periodic geometry. They
still produce new representations and require provenance.

## Structure and IStructure

The verified constructor includes explicit safety-relevant switches:

```python
from pymatgen.core import Lattice, Structure

structure = Structure(
    lattice=Lattice.cubic(5.64),
    species=["Na", "Cl"],
    coords=[[0, 0, 0], [0.5, 0.5, 0.5]],
    coords_are_cartesian=False,
    validate_proximity=True,
    to_unit_cell=False,
)
```

`Structure` is mutable. `IStructure` is immutable/hashable. Prefer:

```python
original = Structure.from_file("input.cif", primitive=False, sort=False)
derived = original.copy()
derived.make_supercell([2, 2, 2])
```

Do not mutate `original` in a provenance-sensitive workflow.

### Disorder and occupancy

Each periodic site's `species` is a composition-like mapping. An ordered site
has one species with occupancy 1. A disordered site can contain multiple
species and fractional occupancies.

```python
for index, site in enumerate(structure):
    occupancy_sum = sum(float(value) for value in site.species.values())
    print(index, site.species, occupancy_sum)
```

Before downstream analysis:

- report `structure.is_ordered`
- reject non-positive or overfull occupancy unless an explicitly documented
  parser tolerance explains a tiny rounding deviation
- preserve vacancy conventions and oxidation-state decoration
- check whether the target method supports disorder

Ordering a disordered structure changes the model and may create many
candidates. It is never a format cleanup.

### Coordinate safety

`site.frac_coords` and `site.coords` are fractional and Cartesian,
respectively. Fractional coordinates outside `[0, 1)` can be valid periodic
images; wrapping them is a transformation, not an automatic fix.

Record whether `to_unit_cell`, sorting, merging, primitive reduction, or
standardization occurred. Check minimum periodic distances under a site-count
bound; an all-pairs matrix is quadratic.
The bundled distance checks exclude periodic images of the same site, so a
one-site structure has a null pair distance. Check lattice self-image contacts
separately when small cells are possible.

### Oxidation states

Oxidation states can be attached to species:

```python
decorated = structure.copy()
decorated.add_oxidation_state_by_element({"Na": 1, "Cl": -1})
```

This mutates the copied structure. Preserve the undecorated parent, mapping,
method, and any charge-balance assumptions. `add_oxidation_state_by_guess()` is
heuristic; do not invoke it implicitly.

### Common methods

Current public operations include:

- `Structure.from_file(path, primitive=False, sort=False, merge_tol=0.0)`
- `Structure.from_str(text, fmt=...)`
- `structure.to(filename=..., fmt=...)`
- `get_distance(i, j)` and bounded neighbor methods
- `get_primitive_structure()`
- `copy()`, `make_supercell()`, `apply_strain()`, and site editing
- `interpolate()` for compatible endpoints

Every operation has assumptions. Interpolation does not establish a physical
path; primitive/standard cells can alter site order and properties.

## Molecule and IMolecule

```python
from pymatgen.core import Molecule

water = Molecule(
    ["O", "H", "H"],
    [[0.0, 0.0, 0.0], [0.758, 0.0, 0.504], [-0.758, 0.0, 0.504]],
    charge=0,
    spin_multiplicity=1,
)
```

Molecule coordinates are Cartesian Å. Record:

- charge and spin multiplicity
- atom order, labels, and site properties
- coordinate origin/orientation
- whether hydrogens, bond perception, centering, or geometry generation changed
  the object

File formats often omit charge, multiplicity, bonding, isotope, or atom-label
semantics. `Molecule.from_file()` parsing success does not prove those fields
were present or preserved.

## Explicit JSON serialization

Core objects expose `as_dict()` and `from_dict()`:

```python
import json
from pymatgen.core import Structure

payload = structure.as_dict()
text = json.dumps(payload, allow_nan=False, sort_keys=True)

decoded = json.loads(text)
restored = Structure.from_dict(decoded)
```

For untrusted JSON:

1. enforce byte, nesting, collection, and string limits
2. reject duplicate keys and non-finite numbers
3. validate the expected `Structure` schema
4. call the specific class constructor

Do not use pickle. Do not feed attacker-controlled MSON metadata to a general
decoder that dynamically imports classes. JSON is only a syntax; schema
validation is the trust boundary.

In this release, even `Structure.from_dict()` decodes MSON-valued site
properties through `PeriodicSite.from_dict()`. The example above is a trusted
round trip. The bundled intake rejects nested `@...` metadata and duplicate
keys before this constructor; supply ordinary JSON lists/numbers for properties
such as magmoms rather than serialized arbitrary Python objects.

## Validation checklist

- object kind (composition/molecule/periodic structure) is explicit
- units and coordinate mode are explicit
- lattice/PBC and charge/spin are recorded where applicable
- all parser warnings are preserved
- occupancy/disorder and oxidation states are reported
- coordinates and lattice values are finite
- minimum distances are checked under a bound
- original is immutable or retained unchanged
- output schema and maximum size are explicit
- provenance links every derived object to its parent checksum

## Sources (verified 2026-09-30)

- [pymatgen core API](https://pymatgen.org/pymatgen.core.html)
- [pymatgen usage guide](https://pymatgen.org/usage.html)
- [pymatgen-core 2026.9.23 package metadata](https://pypi.org/project/pymatgen-core/)
- [pymatgen 2026.9.24 package metadata](https://pypi.org/project/pymatgen/)
- [pymatgen-core source](https://github.com/materialsproject/pymatgen-core)
- [pymatgen changelog](https://pymatgen.org/CHANGES.html)
