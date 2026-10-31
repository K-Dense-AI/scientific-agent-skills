# Chemistry and Molecular Formats

**Reviewed:** 2026-09-30
**Executable scope:** No chemistry-native format has a bundled parser. This file
is a reference-only routing guide, not a support claim.

## Capability boundary

| Format family | Bundled chemistry inspection | Required approach |
|---|---|---|
| PDB, PDBx/mmCIF/CIF | No | Dictionary/version-aware structural tooling |
| Molfile/SDF, SMILES, XYZ | No | Chemistry-aware parser with explicit sanitization policy |
| DCD/XTC/TRR and topology files | No | Topology-aware trajectory tooling |
| Gaussian/QM outputs, cube grids | No | Program/version-aware parser |
| Pickle/joblib/dill molecule/model files | **Never** | Obtain a non-executable interchange export |
| Genuine CSV/TSV/JSON/NPY/NPZ/HDF5 exports | General inspector only | Apply the exact general-format capability; no chemical semantics are inferred |

The `.cif`, `.log`, `.out`, `.raw`, and `.dat` suffixes are ambiguous. The
capability manifest registers `.cif` and `.raw` as reference-only; unregistered
`.log`, `.out`, and `.dat` fail closed. It does not sniff content or guess a producer.

## PDB and PDBx/mmCIF

wwPDB states that PDBx/mmCIF is its official working and archive format.
Legacy PDB format 3.30 remains distributed where representable but has field
and size limitations.

Use a pinned parser such as Gemmi, Biopython's `Bio.PDB`, or official wwPDB
validation services/tools in a separately reviewed environment. Confirm:

- file/dictionary version and experimental method;
- model count, chain/entity mapping, assemblies, alternate locations,
  insertion codes, occupancy, B factors, and missing residues/atoms;
- unit cell, symmetry, resolution, R factors, validation metrics, and
  biological versus crystallographic assembly;
- ligand/component definitions, covalent links, protonation/charge assumptions,
  and coordinate units; and
- whether multiple models are alternatives, an ensemble, or time/order data.

Do not interpret a low B factor, occupancy, model score, or missing atom as a
quality verdict without experimental context. Do not claim binding, stability,
function, or causality from a coordinate inventory.

## Molfile, SDF, and line notations

Molfile/SDF records can represent atoms, bonds, coordinates, charges,
stereochemistry, query features, and arbitrary property blocks. SMILES is a
line notation whose interpretation depends on aromaticity, valence,
stereochemistry, isotope, charge, and sanitization rules.

Before EDA:

1. Identify CTfile/version and producer.
2. Parse with errors preserved; count invalid records rather than silently
   dropping them.
3. Keep the original string/record and a separate standardized representation.
4. Record sanitization, aromaticity, tautomer, protonation, salt/fragment,
   stereochemistry, isotope, and charge policies.
5. Distinguish 2-D drawing coordinates from experimentally or computationally
   meaningful 3-D conformers.
6. Treat property names/values as untrusted metadata and redact identifiers.

Descriptor distributions are conditional on these choices. Do not automatically
neutralize, desalinate, canonicalize, deduplicate, generate conformers, or
discard parser failures.

## XYZ and coordinate text

XYZ commonly starts each frame with atom count and a comment line, followed by
element and Cartesian coordinates. Variants can contain trajectories,
additional columns, or nonstandard units. Confirm:

- atom-count/frame boundaries;
- element/isotope labels and units (often Å, but not guaranteed);
- periodic cell/charge/spin information stored elsewhere;
- whether frames are independent molecules, optimization steps, or dynamics;
  and
- topology/bond inference policy.

The generic tabular scanner is not an XYZ parser.

## Molecular dynamics trajectories

DCD, XTC, TRR, NetCDF trajectories, and related files usually need a matching
topology and sometimes unit-cell/time metadata. A suffix does not supply these.
With MDAnalysis/MDTraj or another pinned reader, inspect:

- topology/trajectory atom count and ordering;
- frame count, time step, units, coordinates, velocities/forces, and box;
- periodic-boundary and imaging/unwrapping choices;
- equilibration, sampling interval, restraints, thermostat/barostat, and
  replica identity; and
- corrupted/truncated frames before calculating RMSD/RMSF or contacts.

Frames are temporally dependent. Do not treat frames as independent replicates
or split adjacent frames randomly across train/test.

## Quantum chemistry outputs and grids

`.log`/`.out` files are program- and version-specific; use cclib or a
producer-specific parser only after confirming the producer. Check:

- method, basis set, charge, multiplicity, units, software/version, and job
  termination;
- optimization/frequency convergence and imaginary modes;
- geometry/energy step count and whether the final structure is intended;
- SCF convergence, warnings, symmetry, solvation, and corrections; and
- whether values are raw, relative, thermal-corrected, or post-processed.

Cube and similar volumetric grids require origin, axis vectors, shape, units,
orbital/density identity, and integration conventions. Bound grid reads and do
not eagerly load an unverified declared shape.

## HDF5, NumPy, and tabular chemistry exports

If the file is genuinely `.npy`, `.npz`, `.h5`, `.hdf5`, `.csv`, `.tsv`, or
strict `.json`, the general inspector can report container structure and
aggregate numeric properties. It cannot infer:

- atom/molecule/conformer axes;
- coordinate or energy units;
- descriptor definitions;
- train/test compound grouping;
- assay censoring or detection limits; or
- chemical identity from field names.

HDF5 object names/attributes are redacted, external/soft links are not followed,
and dataset values are not read. NumPy object arrays are rejected. Pickled
models or RDKit objects are never deserialized.

## Chemistry EDA rigor

1. Define the independent unit: compound, batch, conformer, frame, calculation,
   assay plate, specimen, or replicate.
2. Preserve raw structures and measured values; record standardization as a
   derived transformation.
3. Create a data dictionary with units, assay endpoints, bounds, censoring,
   LOD/LOQ, qualifiers, and provenance.
4. Distinguish missing, failed, inactive, below detection, above quantitation,
   and structurally invalid records.
5. Split related analogues, scaffolds, batches, time, sites, or subjects before
   learned preprocessing to prevent leakage. Random row splits can be
   misleading.
6. Compare robust/classical summaries and investigate outliers against
   measurement and structure; do not delete automatically.
7. Treat transformations (for example log concentration) as scientifically
   defined and retain units/inverse interpretation.
8. Label descriptor/property screening as exploratory and define multiplicity
   control for inferential follow-up.
9. Do not infer binding, efficacy, toxicity, mechanism, or causal effects from
   EDA alone.

## Recommended reference-only tooling

Pin and validate tooling per project rather than treating this list as bundled
support:

- Gemmi or Biopython for PDBx/mmCIF/PDB;
- RDKit or Open Babel for Molfile/SDF/SMILES;
- ASE for XYZ and computational structures;
- MDAnalysis or MDTraj for topology/trajectory pairs; and
- cclib for supported quantum-chemistry outputs.

Check each parser's current format table and release notes. Never pass untrusted
property text to shell commands or dynamic evaluation.

## Authoritative sources

Current parser APIs and format guidance reviewed 2026-09-30. Historical
methodology citations are retained as source context.

- wwPDB, [File Formats and the PDB](https://www.wwpdb.org/documentation/file-formats-and-the-pdb)
  (PDBx/mmCIF is the official archive/working format; legacy PDB format 3.30
  where representable).
- wwPDB, [PDBx/mmCIF Dictionary Resources](https://mmcif.wwpdb.org/) and
  [current user guide](https://mmcif.wwpdb.org/docs/user-guide/guide.html).
- wwPDB, [legacy PDB format 3.30](https://www.wwpdb.org/documentation/file-format-content/format33/v3.3.html).
- IUCr, [CIF format specifications](https://www.iucr.org/resources/cif/spec)
  (links to CIF 1.1 and 2.0 syntax).
- RDKit, [current file parsing API](https://www.rdkit.org/docs/GettingStartedInPython.html#reading-and-writing-molecules).
- MDAnalysis, [supported topology and trajectory formats](https://userguide.mdanalysis.org/stable/formats/index.html).
- cclib, [supported programs and data](https://cclib.github.io/data.html).
- NIST/SEMATECH, [Exploratory Data Analysis](https://www.itl.nist.gov/div898/handbook/eda/eda.htm).
- scikit-learn, [data leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html).
