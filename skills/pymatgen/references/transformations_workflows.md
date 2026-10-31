# Transformations and provenance-preserving workflows

Transformations create scientific hypotheses and derived structures. They are
not harmless cleanup. Always retain the original, make assumptions explicit,
bound candidate growth, and record parent/child checksums.

## Transformation contract

A pymatgen transformation exposes `apply_transformation(structure, ...)`.
One-to-one transformations return a structure; one-to-many transformations can
return ranked dictionaries when explicitly requested.

```python
from pymatgen.transformations.standard_transformations import (
    SubstitutionTransformation,
    SupercellTransformation,
)

parent = structure.copy()
supercell = SupercellTransformation([2, 2, 2]).apply_transformation(parent)
substituted = SubstitutionTransformation({"Na": "K"}).apply_transformation(
    parent
)
```

Even if a transformation currently returns a new object, keep `parent`
unchanged and assert it against a pre-operation checksum.

For every transformation, record:

- fully qualified class and package versions
- constructor arguments and defaults relied upon
- parent artifact/checksum
- occupancy, oxidation-state, charge, spin, and site-property assumptions
- candidate count/ranking method
- warnings and external executable use
- child artifact/checksum

## Supercells

```python
from pymatgen.transformations.standard_transformations import (
    SupercellTransformation,
)

transformation = SupercellTransformation(
    [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
)
child = transformation.apply_transformation(parent)
```

Check:

- scaling-matrix determinant is a positive integer
- expected site-count multiplier
- volume-per-site consistency
- atom/site-property mapping
- periodic boundary conditions
- memory and output growth

Reject a matrix or candidate whose determinant/site count exceeds the reviewed
bound. A non-diagonal matrix changes the cell basis and site ordering.

## Substitution and disorder

Complete substitution:

```python
from pymatgen.transformations.standard_transformations import (
    SubstitutionTransformation,
)

child = SubstitutionTransformation({"Fe": "Mn"}).apply_transformation(parent)
```

Partial substitution creates disorder:

```python
disordered = SubstitutionTransformation(
    {"Fe": {"Fe": 0.5, "Mn": 0.5}}
).apply_transformation(parent)
```

Verify composition, charge model, oxidation states, occupancy sums, and whether
all intended sites—not just a selected sublattice—were transformed. Partial
occupancy is an average/disordered representation, not one ordered atomic
configuration.

## Removing species and sites

```python
from pymatgen.transformations.standard_transformations import (
    RemoveSpeciesTransformation,
)

child = RemoveSpeciesTransformation(["H"]).apply_transformation(parent)
```

Removing species changes composition, charge, and possibly connectivity.
Never use it as silent parser cleanup. Record removed site indices/species and
validate charge/stoichiometry afterward.

## Primitive and conventional cells

```python
from pymatgen.transformations.standard_transformations import (
    ConventionalCellTransformation,
    PrimitiveCellTransformation,
)

primitive = PrimitiveCellTransformation(
    tolerance=0.5,
).apply_transformation(parent)
conventional = ConventionalCellTransformation(
    symprec=0.01,
    angle_tolerance=5,
).apply_transformation(parent)
```

These results depend on symmetry tolerances and can change site order or site
properties. Compare formula and volume per atom, preserve exact tolerances, and
do not treat standardized cells from different conventions as byte-identical.

## Strain and deformation

```python
from pymatgen.transformations.standard_transformations import (
    DeformStructureTransformation,
)

deformed = DeformStructureTransformation(
    [[1.01, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]
).apply_transformation(parent)
```

State whether a matrix is a deformation gradient, strain-like approximation,
or lattice transform. Bound determinant, condition number, minimum distances,
and strain magnitude. Generate positive and negative strains under one
manifest for tensor fitting.

## Oxidation-state decoration

Oxidation states are inputs to several transformations and electrostatic
rankings. Decoration can be explicit or guessed. Prefer explicit mappings
grounded in chemistry:

```python
decorated = parent.copy()
decorated.add_oxidation_state_by_element({"Li": 1, "O": -2})
```

If a guesser is explicitly approved, bound complexity and preserve all
candidate assignments and assumptions. Do not present the first guess as a
measured charge state.

## Ordering disordered structures

```python
from pymatgen.transformations.standard_transformations import (
    OrderDisorderedStructureTransformation,
)

transformation = OrderDisorderedStructureTransformation()
ranked = transformation.apply_transformation(
    disordered,
    return_ranked_list=20,
)
```

Ordering can grow combinatorially. Before running:

- verify rational occupancies and the required supercell
- require oxidation states if electrostatic ranking needs them
- cap maximum cell size, sites, candidates, runtime, RAM, and disk
- state the ranking model and ties
- preserve unreturned-candidate count when known

The top-ranked ordering is model-dependent, not a unique ground state.

## EnumerateStructureTransformation and enumlib

`EnumerateStructureTransformation` generates symmetrically distinct orderings
and requires the external enumlib executables (`enum.x` and `makestr.x`).
Several advanced transformations, including magnetic ordering, can rely on
enumeration.

Current installation docs recommend Enumlib.jl, which provides both executables
in recent releases, alongside the original Fortran implementation. The docs
record `makestr.x` tolerance failures on some inputs and a `makeStr.py` fallback;
verify the selected implementation on the actual structure. Current pymatgen
idealizes coordinates within the declared symmetry tolerance and raises when
fewer structures are produced than enumerated. Preserve those warnings and
the returned count. External enumlib execution was not tested in this refresh.

Treat enumlib as a separate native-code execution:

1. verify official source, version, build instructions, license, and hash
2. resolve the executable path explicitly
3. review exact argv and working directory
4. isolate untrusted inputs
5. enforce cell-size, candidate, CPU, RAM, disk, and wall-time limits
6. preserve stdout/stderr and exit status

Do not install or invoke enumlib automatically.

## Doping and charge balance

Advanced doping and charge-balance transformations encode chemical and
electrostatic assumptions. A requested dopant does not uniquely define:

- substituted host species/site
- oxidation state
- concentration/supercell
- compensating vacancies or co-dopants
- ordering

Require those choices before execution and report every generated candidate.
Validate composition and net formal charge after each transformation.

## Slabs and surfaces

`SlabTransformation` and `SlabGenerator` require explicit Miller index, slab
thickness, vacuum thickness, shift/termination, and cell-reduction choices.
Bound the number of terminations and generated structures. Record whether
sizes are in Å or unit planes.

Never overwrite the bulk parent. Surface energies additionally require
consistent bulk/slab methods, atom/reference accounting, surface area, and
whether one or two equivalent surfaces are present.

## Magnetic ordering

`MagOrderingTransformation` uses proposed magnetic moments and can enumerate
orderings. Record:

- magnetic species and moment magnitudes/units (typically μB)
- collinear/non-collinear assumptions
- supercell and ordering constraints
- enumlib version if used
- candidate count and ranking method

Generated magnetic arrangements are calculation inputs, not converged magnetic
ground states.

## Track history with TransformedStructure

```python
from pymatgen.alchemy.materials import TransformedStructure
from pymatgen.transformations.standard_transformations import (
    SubstitutionTransformation,
    SupercellTransformation,
)

tracked = TransformedStructure(parent.copy(), [])
tracked.append_transformation(SupercellTransformation([2, 2, 2]))
tracked.append_transformation(SubstitutionTransformation({"Na": "K"}))

child = tracked.final_structure
history = tracked.history
```

The history is useful but not sufficient provenance. Also store:

- input and output checksums
- warning stream
- exact versions and dependency lock
- user intent and acceptance criteria
- units and coordinate conventions
- external executable metadata

Use strict JSON after schema validation; do not use pickle.

## Workflow 1: validated local derivation

1. Hash and validate the original.
2. Capture parser warnings, units, PBC, coordinate mode, occupancy/disorder,
   oxidation states, minimum distances, and site properties.
3. Define transformation and bounds in a JSON plan.
4. Apply to a copy.
5. Validate the child and compare composition/site/lattice invariants expected
   for that transformation.
6. Write to a new path.
7. Create an artifact manifest linking parent, plan, and child.

Bundled helpers:

```bash
python scripts/composition_structure_validator.py structure input.cif
python scripts/artifact_manifest.py \
  --artifact input.cif --artifact transformed.json \
  --workflow "reviewed supercell derivation" --output manifest.json
```

## Workflow 2: disorder to bounded ordered candidates

1. Preserve the disordered parent as JSON/CIF.
2. Validate occupancy sums and intended site groups.
3. Define supercell/cell-size and candidate cap.
4. State oxidation states and ranking model.
5. Review enumlib native execution if required.
6. Generate no more than the approved number of candidates.
7. Validate each candidate and preserve mapping/rank.
8. Do not call rank 1 the ground state without an appropriate converged energy
   calculation.

## Workflow 3: compatible local phase diagram

1. Collect total energies and composition for one compatible method/correction
   scheme.
2. Preserve run and correction provenance per entry.
3. Include elemental endpoints and relevant competitors.
4. Write strict JSON with `energy_basis: total_per_entry`.
5. Run:

```bash
python scripts/phase_diagram_generator.py entries.json --analyze Li2O
```

6. Report eV/atom normalized outputs and dataset limitations.
7. Preserve the exact entries JSON and report checksum.

## Workflow 4: VASP input preparation

```python
from pymatgen.io.vasp.sets import MPRelaxSet

input_set = MPRelaxSet(
    child,
    user_incar_settings={"ENCUT": 600},
)
```

Before `write_input()`:

- review every generated file and user override
- verify VASP/input-set version compatibility
- confirm functional, DFT+U, magnetism, spin/SOC, k-points, smearing, and
  convergence
- handle POTCARs only under the user's VASP license
- write to a new calculation directory

Pymatgen does not run VASP or establish convergence.

## Workflow 5: band-structure chain

1. Relax under a documented method and verify convergence.
2. Parse the final structure to a new artifact.
3. Perform a compatible static calculation.
4. Generate a line-mode non-SCF calculation with a documented k-path and
   crystallographic setting.
5. Parse with projected eigenvalues disabled unless required.
6. Report method, structure, k-path, spin/SOC, Fermi convention, and numerical
   convergence with the gap.

Each stage must link to the exact previous output checksum. Do not reuse a
stale structure or charge density silently.

## Workflow 6: Materials Project to local analysis

1. Dry-run a bounded query with explicit fields and limit.
2. Review CC BY attribution, citation, and computed-data limitations.
3. Execute only with `--execute` and the named `MP_API_KEY`.
4. Preserve retrieval time, query, fields, origins, client versions, and
   database release when available.
5. Validate downloaded structures locally.
6. Perform transformations/analysis offline on new derived artifacts.

The database object is computed input with provenance, not experimental truth.

## Candidate and output bounds

Every automated workflow should cap:

- input bytes and sites
- supercell determinant
- generated candidates/slabs/orderings
- neighbors, k-points, bands, and projected arrays
- JSON records/bytes and plot points
- CPU, RAM, disk, and wall time

Stop on bound exhaustion and report partial progress; never silently truncate a
candidate set and present it as exhaustive.

## Sources (verified 2026-09-30)

- [pymatgen transformations API](https://pymatgen.org/pymatgen.transformations.html)
- [pymatgen alchemy API](https://pymatgen.org/pymatgen.alchemy.html)
- [pymatgen symmetry API](https://pymatgen.org/pymatgen.symmetry.html)
- [pymatgen surface API](https://pymatgen.org/pymatgen.core.html)
- [pymatgen VASP sets API](https://pymatgen.org/pymatgen.io.vasp.html)
- [pymatgen installation and enumlib requirements](https://pymatgen.org/installation.html)
- [pymatgen changelog](https://pymatgen.org/CHANGES.html)
- [Official pymatgen tutorial series](https://github.com/computron/pymatgen_tutorials)
