# I/O: parsers, writers, VASP, Q-Chem, and trust boundaries

This reference targets `pymatgen-core==2026.9.23`, which now owns core and
electronic-structure-code I/O under the unchanged `pymatgen.io` namespace.

## I/O is a semantic conversion

Parsing and writing are not neutral byte operations. Before any conversion,
record:

- object kind: periodic `Structure` or non-periodic `Molecule`
- input and output formats, including format variants
- lattice/PBC and coordinate mode
- units
- species order, labels, occupancies/disorder, and oxidation states
- charge/spin for molecules
- site properties such as selective dynamics, velocities, forces, and magmoms
- parser warnings and any automatic corrections

Never overwrite the input or an existing output. Write a new artifact,
round-trip it, and compare the properties the workflow depends on.

## Convenience interface

```python
from pymatgen.core import Molecule, Structure

structure = Structure.from_file("input.cif", primitive=False, sort=False)
cif_text = structure.to(fmt="cif")
poscar_text = structure.to(fmt="poscar")

molecule = Molecule.from_file("molecule.xyz")
xyz_text = molecule.to(fmt="xyz")
```

Use explicit `fmt` when a filename or extension is ambiguous. Never assume
automatic detection means the detected interpretation was scientifically
correct.

## CIF

Use the current parser method and retain all warnings:

```python
import warnings
from pymatgen.io.cif import CifParser

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    parser = CifParser(
        "input.cif",
        occupancy_tolerance=1.0,
        site_tolerance=1e-4,
        frac_tolerance=1e-4,
        check_cif=True,
        comp_tol=0.01,
    )
    structures = parser.parse_structures(
        primitive=False,
        symmetrized=False,
        check_occu=True,
        on_error="raise",
    )

parser_warnings = list(parser.warnings)
python_warnings = [str(item.message) for item in caught]
```

Important behavior:

- A CIF can contain multiple data blocks/structures. Select an index explicitly.
- The parser attempts to repair some out-of-spec content and reports changes.
- Sites close within `site_tolerance` can be merged.
- Occupancy slightly above 1 can be rescaled when it falls within
  `occupancy_tolerance`; increasing that tolerance is a scientific decision,
  not a generic repair.
- `frac_tolerance` can round coordinates near common fractions.
- `check_cif` compares parsed structure composition against CIF composition and
  may warn about omissions such as difficult-to-locate hydrogens.
- `parse_structures(primitive=False)` is the current explicit behavior. Do not
  rely on historical defaults.

Writing:

```python
from pymatgen.io.cif import CifWriter

writer = CifWriter(
    structure,
    symprec=None,
    significant_figures=8,
    write_site_properties=False,
)
cif_text = str(writer)
```

Setting `symprec` asks the writer to find symmetry and can refine to a
conventional representation depending on `refine_struct`; that changes the
representation. Report `symprec`, `angle_tolerance`, and `refine_struct`.

### Untrusted CIFs

A critical arbitrary-code-execution vulnerability in magnetic CIF
transformation parsing affected pymatgen through 2024.2.8 and was fixed in
2024.2.20. Use a current pinned release, but still parse attacker-controlled
files only in a low-privilege isolated process with byte, CPU, memory, disk,
site-count, and wall-time limits.

## POSCAR/CONTCAR

```python
from pymatgen.io.vasp import Poscar

poscar = Poscar.from_file(
    "POSCAR",
    check_for_potcar=False,
    read_velocities=True,
)
structure = poscar.structure

direct_text = poscar.get_str(direct=True, significant_figures=16)
cartesian_text = poscar.get_str(direct=False, significant_figures=16)
```

Record:

- direct/fractional versus Cartesian coordinates
- scale factor interpretation and units
- element-name source, especially VASP 4 files
- species order
- selective-dynamics flags
- velocities, predictor-corrector data, and lattice velocities if present

POSCAR cannot faithfully represent partial occupancies. Oxidation states and
arbitrary site properties generally do not round-trip. Never "fix" a POSCAR by
searching nearby directories for POTCAR files without explicit approval.

## XYZ and other low-context formats

XYZ is a Cartesian, non-periodic coordinate format. Converting a periodic
structure to XYZ drops lattice and periodicity. Basic XYZ also does not define
oxidation states, partial occupancies, bonds, charge, spin multiplicity, or
arbitrary site properties.

`Structure.to(fmt="xyz")` is unsupported in the tested registry. The bundled
converter uses `pymatgen.io.xyz.XYZ(structure)` explicitly, after acknowledging
the loss of lattice/PBC. Read the result as a `Molecule`.

CSSR and XSF have their own representational limits. Treat support in
`Structure.to()` as syntactic capability, not proof of losslessness.

## JSON and MSON

Pymatgen core objects implement `as_dict()`/`from_dict()`:

```python
import json
from pymatgen.core import Structure

text = json.dumps(structure.as_dict(), allow_nan=False, sort_keys=True)
payload = json.loads(text)
restored = Structure.from_dict(payload)
```

For untrusted input, use a bounded strict JSON parser, reject duplicate keys and
non-finite values, validate the expected schema, and call a specific
constructor. Do not use pickle. Do not pass attacker-controlled `@module` or
`@class` metadata to a general dynamic object decoder.

`Structure.from_dict()` itself decodes site-property MSON values. The bundled
loader therefore rejects nested MSON metadata, duplicate keys and non-finite
numbers before constructing a structure. It accepts plain `.json`/`.mson`
files only; decompress and inspect compressed JSON separately.

YAML is not used by the bundled CLIs. If a workflow truly needs YAML, use a
safe loader plus schema validation; YAML safety does not solve object-schema or
resource-exhaustion risks.

## VASP input objects

```python
from pymatgen.io.vasp import Incar, Kpoints, Poscar

incar = Incar({"ENCUT": 520, "ISMEAR": 0, "SIGMA": 0.05})
kpoints = Kpoints.automatic_density(structure, 1000)
poscar = Poscar(structure)
```

Input sets encode versioned methodological choices:

```python
from pymatgen.io.vasp.sets import MPNonSCFSet, MPRelaxSet, MPStaticSet

relax = MPRelaxSet(structure)
static = MPStaticSet(structure)
bands = MPNonSCFSet(structure, mode="line")
```

Before writing:

1. inspect the generated INCAR, KPOINTS, POSCAR, and POTCAR specification
2. record input-set class, pymatgen/core versions, all user overrides, and the
   source structure checksum
3. check magnetic moments, DFT+U, functional, pseudopotential family, ENCUT,
   k-point density/path, smearing, spin/SOC, symmetry, and convergence criteria
4. write to a new calculation directory

POTCAR datasets are VASP-licensed and not distributed by pymatgen. A
`POTCAR.spec` is not a POTCAR. Do not redistribute pseudopotential contents or
silently use files from an unrelated installation.

## VASP output parsing

This file-dependent example is illustrative; signatures were checked against
the pinned core release, but a licensed calculation was not run.

```python
from pymatgen.io.vasp import Vasprun

run = Vasprun(
    "vasprun.xml",
    ionic_step_skip=None,
    parse_dos=True,
    parse_eigen=True,
    parse_projected_eigen=False,
    parse_potcar_file=False,
    exception_on_bad_xml=True,
)

final_structure = run.final_structure
final_energy_eV = float(run.final_energy)
band_structure = run.get_band_structure(line_mode=True)
complete_dos = run.complete_dos
```

Use `BSVasprun` when only eigenvalue/band-structure information is needed.
Projected eigenvalues can take extreme time and memory; leave
`parse_projected_eigen=False` unless they are required and resources are
bounded.

Parser success does not establish:

- electronic or ionic convergence
- a correct k-path or line-mode reconstruction
- comparable energies
- valid pseudopotential hashes
- correct Fermi level, occupations, spin/SOC, or projection interpretation

Preserve source-file checksums and parsing options. Large XML, HDF5, CHGCAR,
LOCPOT, WAVECAR, and trajectory files need explicit byte and memory limits.

For collinear spin-polarized LOCPOT/ELFCAR, the current primary channels are
`spin_up` and `spin_down`; CHGCAR retains `total` and `diff`. Old LOCPOT/ELFCAR
aliases warn. Volumetric interpolation now uses periodic `i/n` grid positions;
`interpolator` is a method, without the old `.grid`/`.values` attributes or
SciPy `method`/`fill_value` call options.

## Band structures and DOS

`Vasprun.get_band_structure()` returns a `BandStructure` or
`BandStructureSymmLine` depending on inputs. Relevant methods include
`is_metal()`, `get_band_gap()`, `get_vbm()`, and `get_cbm()`.

`run.complete_dos` is a `CompleteDos`; current analyses include total,
element-, site-, and orbital-projected DOS. Verify energy reference, Fermi
level, normalization, smearing, spin channels, projection completeness, and
whether the DOS and band run correspond to the same structure/method.

## Q-Chem

Current imports:

```python
from pymatgen.io.qchem.inputs import QCInput
from pymatgen.io.qchem.outputs import QCOutput

job = QCInput(
    molecule,
    rem={
        "job_type": "sp",
        "method": "wb97x-v",
        "basis": "def2-svpd",
    },
)
text = str(job)

parsed = QCOutput("qchem.out")
data = parsed.data
```

The input construction is exercised with a synthetic water molecule. Output
parsing is illustrative and needs an actual Q-Chem output file.

`QCInput` accepts explicit sections such as `rem`, `opt`, `pcm`, `solvent`,
`smx`, `scan`, `plots`, `nbo`, `geom_opt`, and others. Validate each setting
against the licensed Q-Chem version and manual. Preserve molecule atom order,
charge, spin multiplicity, method/basis, solvent model, job type, and input
text.

`QCOutput` parses a file into structured data; inspect parser errors,
completion, SCF/geometry convergence, imaginary frequencies, and units before
using a result.

## External and native programs

Pymatgen interfaces can call or depend on optional external tools, including:

- enumlib (`enum.x`, `makestr.x`) for derivative-structure enumeration
- Bader analysis executable
- packmol
- ffmpeg
- Zeo++/Voro++
- graph and visualization libraries

Do not invoke them automatically. Verify official source, version, hash,
license, native build scripts, executable path, exact argv, working directory,
input/output paths, and CPU/RAM/disk/time bounds. Never interpolate untrusted
text into a shell command.

## Safe conversion sequence

1. Inventory source bytes, checksum, format, and parser warnings.
2. Validate lattice/PBC, coordinates, species order, occupancy/disorder,
   oxidation states, labels, and site properties.
3. Generate a dry-run representation-loss plan.
4. Refuse an incompatible target (for example, disordered structure to POSCAR).
5. Require explicit acknowledgement for remaining losses.
6. Render in memory, enforce an output-byte bound, and create a new file
   exclusively.
7. Parse the output under the same safety bounds.
8. Compare formula, site count, lattice, PBC, coordinates, occupancy, labels,
   and required properties with explicit numerical tolerances.
9. Record both checksums and every warning in the artifact manifest.

## Sources (verified 2026-09-30)

- [pymatgen I/O API](https://pymatgen.org/pymatgen.io.html)
- [CIF parser and writer API](https://pymatgen.org/pymatgen.io.html)
- [VASP I/O API](https://pymatgen.org/pymatgen.io.vasp.html)
- [Q-Chem I/O API](https://pymatgen.org/pymatgen.io.qchem.html)
- [pymatgen installation and external programs](https://pymatgen.org/installation.html)
- [pymatgen-core source](https://github.com/materialsproject/pymatgen-core)
- [CVE-2024-23346 official advisory](https://github.com/materialsproject/pymatgen/security/advisories/GHSA-vgv8-5cpj-qj2f)
- [pymatgen changelog](https://pymatgen.org/CHANGES.html)
