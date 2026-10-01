# Parameter surface and validation

## Source of truth

Create parameters from the exact selected class:

```python
from fluidsim.solvers.ns2d.solver import Simul

params = Simul.create_default_params()
print(params)
```

FluidSim composes parameters from registered operator, state, time-stepping,
initialization, forcing, and output classes. The tree is solver- and
extension-specific. There is no universal flat FluidSim parameter schema.

`ParamContainer` rejects assignment to undeclared attributes, which catches many
typos. It does not check units, physical interpretation, numerical convergence,
or whether a valid option is appropriate.

The following snapshot was introspected from a pinned
`fluidsim[fft]==0.9.0`/`fluidfft==0.4.5` NS2D environment on 2026-09-30 and reviewed on 2026-10-01.

## Top-level controls

Common pseudospectral fields:

```python
params.NEW_DIR_RESULTS = True
params.ONLY_COARSE_OPER = False
params.short_name_type_run = ""

params.nu_2 = 1e-3
params.nu_4 = 0.0
params.nu_8 = 0.0
params.nu_m4 = 0.0
```

- `NEW_DIR_RESULTS` primarily controls loading/restart output behavior. Official
  docs say a loaded simulation creates a new directory when true and appends to
  the old directory when false. Choose explicitly and preserve the parent.
- `ONLY_COARSE_OPER` is for fast loading/plotting and cannot process full fields.
- `nu_2`, `nu_4`, `nu_8`, and `nu_m4` are solver dissipation coefficients. Their
  dimensions depend on derivative order and nondimensionalization.

Do not use higher-order dissipation merely to hide insufficient resolution.
State its definition and verify budgets/tails/refinement.

Solver-specific top-level examples include:

- `N` for constant stratification in `.strat` solvers.
- `f` for rotation where implemented.
- `beta`, `c2`, projections, and other fields in specific solvers.

Inspect the selected solver documentation rather than copying these blindly.

## Operators

NS2D defaults:

```python
params.oper.nx = 48
params.oper.ny = 48
params.oper.Lx = 8
params.oper.Ly = 8
params.oper.coef_dealiasing = 2 / 3
params.oper.truncation_shape = "cubic"
params.oper.type_fft = "default"
params.oper.NO_KY0 = False
params.oper.NO_SHEAR_MODES = False
```

NS3D adds `nz`/`Lz` and solver-specific options. Never infer physical spacing
without the domain convention. Record:

- `nx`, `ny`, `nz` and `Lx`, `Ly`, `Lz`.
- Grid spacing and maximum represented/dealiased wave numbers.
- `coef_dealiasing`, truncation shape, and phase-shift scheme if used.
- Actual selected FluidFFT method and decomposition.
- Removed modes/symmetries.

Powers of two are not a universal requirement or guarantee of fastest FFT.
Benchmark representative allowed shapes on the target backend.

`type_fft="default"` delegates selection. For provenance-critical runs, inspect
and record the actual method; set an explicit tested method if the environment
supports it.

## Time stepping

NS2D 0.9.0 defaults:

```python
params.time_stepping.USE_CFL = True
params.time_stepping.USE_T_END = True
params.time_stepping.cfl_coef = None
params.time_stepping.deltat0 = 0.2
params.time_stepping.deltat_max = 0.2
params.time_stepping.it_end = 10
params.time_stepping.max_elapsed = None
params.time_stepping.t_end = 10.0
params.time_stepping.type_time_scheme = "RK4"
```

The current field is `cfl_coef`, **not** `CFL`.

For reproducible bounded plans, set explicitly:

```python
params.time_stepping.USE_CFL = True
params.time_stepping.cfl_coef = 0.5
params.time_stepping.deltat0 = 1e-3
params.time_stepping.deltat_max = 1e-2
params.time_stepping.USE_T_END = True
params.time_stepping.t_end = 0.1
params.time_stepping.max_elapsed = "00:05:00"
```

`cfl_coef=0.5` here is an explicit pilot choice, not a universal recommendation.
The acceptable value depends on equations, scheme, waves, dissipation, and
resolution. Check recorded `deltat` and refine.

Current pseudospectral scheme names documented in 0.9:

- `Euler`
- `Euler_phaseshift`
- `Euler_phaseshift_random`
- `RK2`
- `RK2_trapezoid`
- `RK2_phaseshift`
- `RK2_phaseshift_random`
- `RK2_phaseshift_random_split`
- `RK2_phaseshift_exact`
- `RK4`

Random phase-shift schemes also expose:

```python
params.time_stepping.phaseshift_random.nb_pairs = 1
params.time_stepping.phaseshift_random.nb_steps_compute_new_pair = None
```

Do not infer exact dealiasing or convergence from a scheme name. Verify its
implementation and test a smaller time step.

## Initial fields

NS2D advertises:

```python
params.init_fields.type = "constant"
params.init_fields.modif_after_init = False
```

Available types in the pinned NS2D profile:

- `constant`
- `noise`
- `jet`
- `dipole`
- `from_file`
- `from_simul`
- `in_script`

Nested fields include:

```python
params.init_fields.constant.value = 0.0
params.init_fields.noise.velo_max = 1.0
params.init_fields.noise.length = 0.0
params.init_fields.from_file.path = "state_phys_t001.000.nc"
```

Other solvers advertise different types/variables. For random initial fields,
record seed, process count, backend, generated spectrum/amplitude, and resulting
constraints. A seed alone may not guarantee bitwise identity across MPI
decompositions or versions.

For in-script initialization:

1. Inspect `sim.state.keys_state_phys`/solver state documentation.
2. Fill the solver's canonical variables.
3. Use the solver's documented physical-to-spectral conversion method.
4. Enforce divergence/constraints and dealias if required.
5. Save and inspect the initialized state before advancement.

Do not reuse old examples with guessed keys such as `vx` versus `ux`, or call a
spectral-to-physical method after modifying physical fields.

## Forcing

Base fields:

```python
params.forcing.enable = False
params.forcing.type = ""
params.forcing.forcing_rate = 1.0
params.forcing.key_forced = None
params.forcing.nkmin_forcing = 4
params.forcing.nkmax_forcing = 5
```

NS2D advertises `in_script`, `in_script_coarse`, `pseudo_spectral`,
`proportional`, `tcrandom`, and `tcrandom_anisotropic`.

Nested current fields:

```python
params.forcing.normalized.constant_rate_of = None
params.forcing.normalized.type = "2nd_degree_eq"
params.forcing.normalized.which_root = "minabs"
params.forcing.random.only_positive = False
params.forcing.tcrandom.time_correlation = "based_on_forcing_rate"
```

The old flat field `tcrandom_time_correlation` is not current.

For a time-correlated random plan:

```python
params.forcing.enable = True
params.forcing.type = "tcrandom"
params.forcing.forcing_rate = 1.0
params.forcing.nkmin_forcing = 4
params.forcing.nkmax_forcing = 5
params.forcing.tcrandom.time_correlation = "based_on_forcing_rate"
```

The integers multiply an operator wave-number spacing; they are not necessarily
physical wave numbers. Verify the resulting forced region. Measure actual input
in spatial means/budgets.

FluidSim 0.9.0 restart files store state parameters, including time-correlated
forcing seeds/state. Do not drop these groups when copying or converting
checkpoints.

## Output

Common controls:

```python
params.output.HAS_TO_SAVE = True
params.output.ONLINE_PLOT_OK = False
params.output.period_refresh_plots = 1
params.output.sub_directory = "bounded-pilot"

params.output.periods_print.print_stdout = 0.1
params.output.periods_plot.phys_fields = 0.0
params.output.periods_save.phys_fields = 0.5
params.output.periods_save.spatial_means = 0.05
params.output.periods_save.spectra = 0.5
params.output.periods_save.spect_energy_budg = 0.0
```

NS2D's 0.9 output tree also includes `increments`, `spectra_multidim`,
`temporal_spectra`, and `spatiotemporal_spectra`. A period of zero disables that
specific output.

`sub_directory` is created under `FLUIDSIM_PATH`. Use a safe one-component
identifier. Preflight quota, collision, and symlink behavior. `HAS_TO_SAVE=False`
is the correct smoke-test setting, but produces no restart checkpoint.

Physical-field settings include:

```python
params.output.phys_fields.field_to_plot = "rot"
params.output.phys_fields.file_with_it = False
```

Field names are solver-specific. Disable online plotting for unattended jobs.

## Strict JSON validator

The bundled validator covers reviewed Cartesian CFD profiles and requires
scientific and resource metadata in addition to FluidSim parameters:

```bash
python3 scripts/solver_config_validator.py --example
python3 scripts/solver_config_validator.py --config config.json
```

It rejects:

- Options absent from the selected released solver: for example NS3D has no
  `periods_save.increments`, and `waves2d` has no `periods_save.spectra`.
  Do not reuse the whole NS2D JSON example after changing only the solver key.

- Unknown keys and old `CFL`.
- Non-finite numbers and duplicate JSON keys.
- Unbounded grid/resources/output.
- Unsafe output or restart paths.
- Missing units/nondimensionalization, boundaries, initialization, forcing,
  resolution/dealiasing, CFL/timestep, budget, refinement, or acceptance
  statements.
- CPU oversubscription and inconsistent serial/MPI preview modes.

The bundled profile covers a subset of each solver's parameters. Unsupported
extensions need their own reviewed script. The generator refuses `in_script`
and `from_simul` initializers, and forcing types requiring callbacks, because
a JSON plan does not provide their implementations.

It validates a plan mechanically. It explicitly reports that physical validity
and numerical convergence are not established.

## Parameter provenance

Preserve:

- Exact parameter file from the run.
- Canonical strict JSON plan and SHA-256.
- Generated launch script and SHA-256.
- `uv.lock` and SHA-256.
- Solver module/key and package versions.
- FFT method, MPI size, threads, hardware, compiler/native libraries.
- Environment variables affecting FluidSim, FluidFFT, Transonic, OpenMP, MPI,
  and HDF5.
- Every restart parent/child and changed parameter.

Do not rely only on directory names; they are summaries, not canonical
configuration.

## Sources (verified 2026-10-01)

- [FluidSim user tutorial](https://fluidsim.readthedocs.io/en/latest/ipynb/tuto_user.html)
  — defaults, mutation behavior, output and loaders.
- [NS2D generated parameter documentation](https://fluidsim.readthedocs.io/en/latest/generated/fluidsim.solvers.ns2d.solver.html).
- [Pseudospectral time-stepping API](https://fluidsim.readthedocs.io/en/latest/generated/fluidsim.base.time_stepping.pseudo_spect.html).
- [Forcing base source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/base/forcing/base.py).
- [Specific forcing source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/base/forcing/specific.py).
- [FluidSim 0.9 package source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/pyproject.toml).
