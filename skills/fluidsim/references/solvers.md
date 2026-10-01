# Solver registry and selection

## Do not select by name alone

A solver key only identifies an implementation. Before use, verify in the
solver's 0.9.0 API/source:

1. Governing equations and prognostic variables.
2. Dimensional or nondimensional parameter definitions.
3. Geometry and boundary conditions.
4. Spatial discretization, truncation, and dealiasing.
5. Time integration and stability constraints.
6. Initial-condition and forcing classes registered for that solver.
7. Conserved/dissipated quantities and output definitions.
8. Known validation examples and limits of applicability.

Most primary FluidSim package CFD solvers use periodic domains and Fourier
pseudospectral methods. They are not general wall-bounded, free-surface,
industrial-geometry, multiphase, compressible, or shock-capturing solvers.

## FluidSim 0.9.0 registry

The following keys/modules come from the official 0.9.0 `pyproject.toml` entry
points and were cross-checked with the installed pinned package.

### Cartesian fluid and wave solvers

| Key | Direct import | Scope to verify |
|---|---|---|
| `ns2d` | `fluidsim.solvers.ns2d.solver.Simul` | 2D incompressible Navier–Stokes |
| `ns2d.bouss` | `fluidsim.solvers.ns2d.bouss.solver.Simul` | 2D Boussinesq variant |
| `ns2d.strat` | `fluidsim.solvers.ns2d.strat.solver.Simul` | 2D stratified Boussinesq, constant `N` |
| `ns3d` | `fluidsim.solvers.ns3d.solver.Simul` | 3D incompressible Navier–Stokes |
| `ns3d.bouss` | `fluidsim.solvers.ns3d.bouss.solver.Simul` | 3D Boussinesq variant |
| `ns3d.strat` | `fluidsim.solvers.ns3d.strat.solver.Simul` | 3D stratified Boussinesq, constant `N` |
| `sw1l` | `fluidsim.solvers.sw1l.solver.Simul` | One-layer shallow-water equations |
| `sw1l.exactlin` | `fluidsim.solvers.sw1l.exactlin.solver.Simul` | SW1L exact-linear variant |
| `sw1l.modified` | `fluidsim.solvers.sw1l.modified.solver.Simul` | Modified SW1L equations |
| `sw1l.onlywaves` | `fluidsim.solvers.sw1l.onlywaves.solver.Simul` | SW1L wave-only variant |
| `plate2d` | `fluidsim.solvers.plate2d.solver.Simul` | 2D Föppl–von Kármán elastic plate |
| `waves2d` | `fluidsim.solvers.waves2d.solver.Simul` | 2D wave model |

`fvk` is **not** the current entry-point key. Use `plate2d` after verifying its
equations and parameters.

### Lower-dimensional models

| Key | Module |
|---|---|
| `ad1d` | `fluidsim.solvers.ad1d.solver` |
| `ad1d.pseudo_spect` | `fluidsim.solvers.ad1d.pseudo_spect.solver` |
| `burgers1d` | `fluidsim.solvers.burgers1d.solver` |
| `burgers1d.skew_sym` | `fluidsim.solvers.burgers1d.skew_sym.solver` |
| `nl1d` | `fluidsim.solvers.nl1d.solver` |
| `models0d.lorenz` | `fluidsim.solvers.models0d.lorenz.solver` |
| `models0d.predaprey` | `fluidsim.solvers.models0d.predaprey.solver` |

These are useful for model studies, testing, and teaching. Do not apply the
Cartesian CFD configuration schema mechanically to 0D/1D solvers.

### Spherical solvers

| Key | Module |
|---|---|
| `sphere.ns2d` | `fluidsim.solvers.sphere.ns2d.solver` |
| `sphere.sw1l` | `fluidsim.solvers.sphere.sw1l.solver` |

FluidSim 0.9.0 source contains these entry points, but the `sphere` optional
dependency is commented out in package metadata. Confirm and pin compatible
`fluidsht`/spherical-harmonic dependencies before import. Spherical resolution,
operators, geometry, and diagnostics differ from Cartesian `nx`/`ny` plans.

### Framework/base adapters

The registry also declares:

- `Base` → `fluidsim.base.solvers.base`
- `BasePS` → `fluidsim.base.solvers.pseudo_spect`
- `BaseSH` → `fluidsim.base.sphericalharmo.solver`
- `basil` → `fluidsim.base.basilisk.solver`
- `dedalus` → `fluidsim.base.dedalus.solver`

These are framework/base or external-interface entry points, not evidence that
all external runtimes are installed. Check the external project's current API,
license, and environment separately.

## Imports

Prefer direct imports in reproducible scripts:

```python
from fluidsim.solvers.ns3d.strat.solver import Simul

params = Simul.create_default_params()
```

FluidSim also supports registry lookup:

```python
from fluidsim import import_simul_class_from_key

Simul = import_simul_class_from_key("ns2d.strat")
```

Only pass a reviewed literal or a value checked against a fixed allowlist. Do not
derive module names or solver keys from untrusted text. The bundled generator
uses a static key-to-module map and never performs a dynamic import.

## Selection questions

### NS2D versus NS3D

- Dimensionality changes the equations and invariant/cascade structure; a 2D
  run is not a cheaper approximation to arbitrary 3D physics.
- NS3D memory and FFT communication grow rapidly. Estimate before
  instantiation.
- State keys, forcing normalization, spectra, and budget outputs differ.

### Boussinesq versus stratified

Do not use `.bouss` and `.strat` interchangeably. Inspect the solver equation
documentation, variable definitions, background state, buoyancy sign, `N`,
rotation, and energy definitions. Record dimensional mapping for buoyancy and
density variables.

### Shallow water

Verify the exact SW1L variant, layer-depth/height variable, wave speed
parameterization, Coriolis convention, potential-vorticity definition, and
whether the planned regime satisfies the model assumptions. A SW1L run does not
by itself validate tsunami or geophysical predictions.

### Elastic plate

Use `plate2d`, not the old `fvk` label. Verify plate parameters, forcing,
dissipation, dimensional scaling, and whether the output represents displacement,
velocity, or derived quantities.

## Default-parameter discovery

Every selected solver should be interrogated in the exact locked environment:

```python
from fluidsim.solvers.ns2d.solver import Simul

params = Simul.create_default_params()
print(params)
```

Use IPython completion or the generated parameter documentation. `ParamContainer`
prevents silently adding unknown attributes, but it does not establish that a
valid attribute is physically meaningful.

For NS2D 0.9.0, the pinned smoke test found:

- `oper`: `nx`, `ny`, `Lx`, `Ly`, `coef_dealiasing`,
  `truncation_shape`, `type_fft`, `NO_KY0`, `NO_SHEAR_MODES`.
- Time stepping: `USE_CFL`, `USE_T_END`, `cfl_coef`, `deltat0`,
  `deltat_max`, `it_end`, `max_elapsed`, `t_end`, `type_time_scheme`.
- Initial types advertised by the solver:
  `from_file`, `from_simul`, `in_script`, `constant`, `noise`, `jet`, `dipole`.
- Forcing types advertised:
  `in_script`, `in_script_coarse`, `pseudo_spectral`, `proportional`,
  `tcrandom`, `tcrandom_anisotropic`.

Do not generalize that list to other solvers. The bundled validator now uses
per-solver initialization, forcing, physics-parameter, and output profiles
checked against all twelve Cartesian solver defaults. For example, NS3D does
not register `jet`, `increments`, or `spectra_multidim`; SW1L and `waves2d`
have different forcing/output surfaces. These checks establish API availability,
not physical validation of every solver.

## Evidence required before interpretation

For any solver:

- Map each code variable and coefficient to the stated model.
- Verify sign conventions, normalization, and Fourier conventions.
- Confirm periodicity and domain lengths.
- Check initial-condition constraints (for example divergence-free velocity).
- Check forcing injection in measured output, not only requested parameters.
- Check all relevant invariant/budget residuals.
- Inspect spectral support and dealiased tails.
- Repeat at refined grid and time step.
- Compare with a suitable independent benchmark.

## Sources (verified 2026-10-01)

- [FluidSim 0.9.0 package entry points](https://github.com/fluiddyn/fluidsim/blob/0.9.0/pyproject.toml).
- [FluidSim solver API index](https://fluidsim.readthedocs.io/en/latest/generated/fluidsim.solvers.html).
- [NS2D solver API](https://fluidsim.readthedocs.io/en/latest/generated/fluidsim.solvers.ns2d.solver.html).
- [NS3D solver API](https://fluidsim.readthedocs.io/en/latest/generated/fluidsim.solvers.ns3d.solver.html).
- [FluidSim documentation overview](https://fluidsim.readthedocs.io/en/latest/).
- Mohanan et al., [FluidSim primary paper](https://doi.org/10.5334/jors.239),
  published 2019-04-26. Method and performance statements in this reference are
  limited to the implementations and benchmarks described there.
