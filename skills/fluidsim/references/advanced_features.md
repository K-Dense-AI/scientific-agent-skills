# Forcing, operators, MPI, extensions, and migrations

## Forcing architecture

FluidSim assembles forcing classes through the selected solver's registry.
NS2D 0.9 advertises:

- `in_script`
- `in_script_coarse`
- `pseudo_spectral`
- `proportional`
- `tcrandom`
- `tcrandom_anisotropic`

Availability and default forced variable are solver-specific.

Base fields:

```python
params.forcing.enable = True
params.forcing.type = "tcrandom"
params.forcing.forcing_rate = 1.0
params.forcing.key_forced = None
params.forcing.nkmin_forcing = 4
params.forcing.nkmax_forcing = 5
params.forcing.tcrandom.time_correlation = "based_on_forcing_rate"
```

Current source converts `nkmin_forcing`/`nkmax_forcing` to dimensional
wave-number bounds using the operator's wave-number spacing. Inspect the
resulting forced region; the integers are not necessarily physical wave
numbers.

### Normalization

Current normalized-forcing fields include:

```python
params.forcing.normalized.constant_rate_of = None
params.forcing.normalized.type = "2nd_degree_eq"
params.forcing.normalized.which_root = "minabs"
```

The implementation can solve a quadratic normalization so the time-step-mean
injection of a quadratic quantity matches `forcing_rate`. The exact quadratic
quantity and key depend on the solver/forced field. Therefore:

- State the intended injected invariant and units.
- Confirm `key_forced`.
- Measure forcing power in output.
- Check the global/spectral budget using the same convention.
- Test time-step sensitivity of the measured injection.

Do not call `forcing_rate` “energy input” without verifying the selected class.

### Time-correlated random forcing

The 0.9 field is:

```python
params.forcing.tcrandom.time_correlation = "based_on_forcing_rate"
```

or a positive finite time value. The rate-derived setting requires positive
`forcing_rate`. Current source derives the default period as a power of
the forcing rate and stores two random seeds plus the last-change time in state
parameters under `/state_params/forcing` (`seed0`, `seed1`, `t_last_change`).
FluidSim 0.9.0 writes these state parameters into restart files;
0.8.6 fixed a time-correlated forcing restart bug.

For reproducibility, preserve:

- Initial random seed strategy.
- Saved forcing state parameters.
- MPI rank count/decomposition and package versions.
- Correlation-time setting and measured autocorrelation.
- Restart boundary diagnostics.

### In-script forcing

Use the solver's registered `InScriptForcing*` interface and documented
`compute_forcing_fft_each_time` or coarse equivalent. Do not monkey-patch a
method with a lambda copied from an old example:

- State keys have changed in some solvers.
- Local spectral layout depends on FFT/MPI backend.
- Hermitian/reality constraints and normalization must be preserved.
- A literal global Fourier index is not portable across decompositions.

Implement a reviewed subclass/extension with unit tests on tiny sequential and
MPI layouts. Validate zero-net/target injection, symmetry, and budget effects.

## Operators and array ownership

`sim.oper` provides solver-selected grids, FFT/IFFT, differentiation, vector
calculus, projections, spectra, dealiasing, and distributed-array helpers.
Method names and array layouts depend on operator class.

Never assume:

- Axis order from `nx`, `ny`, `nz`.
- Full global arrays on every rank.
- A Fourier mode has the same local index under another backend/rank count.
- All FFT backends use the same spectral shape.
- A gathered array fits rank-0 memory.
- Direct NumPy sums have the same normalization as
  `oper.sum_wavenumbers`.

Use documented operator methods and inspect:

```python
print(type(sim.oper))
print(sim.oper.axes)
print(sim.params.oper)
```

For custom diagnostics, test sequential and distributed shapes and compare
against analytical transforms at tiny resolution.

## Dealiasing

The common Cartesian field is:

```python
params.oper.coef_dealiasing = 2 / 3
params.oper.truncation_shape = "cubic"
```

FluidSim also implements phase-shift time schemes. A coefficient or scheme name
does not prove alias removal for a custom nonlinearity. Verify:

- Polynomial/nonlinear form and expected alias interactions.
- Where dealiasing is applied.
- Truncation geometry.
- Spectral tails and invariant transfer.
- Results under stricter truncation or exact phase-shift method.

Do not combine an aggressive cutoff and high-order dissipation merely to obtain
a visually smooth spectrum.

## Time schemes

Documented pseudospectral names:

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

The implementation treats linear terms with exact coefficients in its
pseudospectral stepper and evaluates nonlinear tendencies according to the
named scheme. Verify source and solver coupling before making an order/stability
claim.

Always check:

- Advective CFL.
- Wave frequency limits (stratification, rotation, shallow-water waves).
- Diffusive/hyperdiffusive limits.
- Forcing correlation and output cadence relative to `deltat`.
- Smaller `cfl_coef`/`deltat_max` comparison.

`USE_CFL=True` only activates the solver's CFL logic; it does not guarantee all
accuracy/stability constraints are resolved.

## Custom initial conditions

`in_script` gives direct control, but use current state keys:

1. Construct `Simul` with `init_fields.type = "in_script"`.
2. Inspect the solver's state documentation/keys.
3. Fill canonical physical or spectral variables.
4. Call the documented conversion in the correct direction.
5. Apply projection/dealiasing/constraints as required.
6. Save an initialization checkpoint and verify budgets before stepping.

Old examples that fill `vx`/`vy` and then call a
spectral-to-physical conversion can overwrite the intended state. NS2D 0.9
documentation shows physical keys including `ux`, `uy`, and `rot`; use the
selected solver's actual keys.

## Extending a solver

FluidSim's `InfoSolver`/class registry supports extensions. For a research
extension:

- Pin FluidSim/FluidSim Core source and version.
- Subclass the closest solver and extend default parameters through the current
  class mechanism.
- Register state variables, operators, initialization, forcing, outputs, and
  restart state explicitly.
- Define nonlinear tendencies with documented sign and normalization.
- Add unit/manufactured-solution tests and budget identities.
- Test serialization/restart and old/new parameter merging.
- Benchmark only after correctness tests.

Avoid private-method snippets from old versions without source review.

## FluidFFT backend selection

Registered methods are entry points, not proof their dependencies load.
Discover them:

```python
from fluidfft import get_methods

print(sorted(get_methods(ndim=2)))
print(sorted(get_methods(ndim=3)))
```

Set per run:

```python
params.oper.type_fft = "fft2d.with_pyfftw"
```

or use `FLUIDSIM_TYPE_FFT2D`/`FLUIDSIM_TYPE_FFT3D` before process start.
Record actual method and plugin distribution.

FluidFFT's 2019 primary paper demonstrates:

- Unified C++/Python APIs for multiple FFT libraries.
- One-dimensional and pencil/two-dimensional MPI decompositions.
- Hardware/shape/process-count-dependent fastest methods.
- Scaling beyond the limits of slab decomposition in the tested cases.

Do not transfer its fastest-method or wall-time numbers to current hardware.
Benchmark a bounded representative shape in the target environment.

## MPI planning and safety

Never call `mpirun`, `mpiexec`, `srun`, `qsub`, `sbatch`, OAR tools, or a
FluidDyn cluster submitter automatically.

Required preflight:

- Written resource estimate and output estimate.
- Approved allocation and partition/account.
- Exact MPI implementation/ABI and launcher.
- FFT plugin/native library compatibility.
- Rank/thread placement and oversubscription check.
- Per-rank local shapes and no zero-sized unsupported decomposition.
- Memory/rank and rank-0 gather/output risk.
- Wall-time signal/checkpoint behavior.
- Filesystem quota, inode count, stripe policy, and cleanup.
- Tiny serial then two-rank smoke.
- Restart plan with immutable parent state.

Output behavior can differ with MPI-enabled h5py. Standard h5py usually causes
rank 0 to write assembled state; MPI h5py can use an `mpio` driver. Verify the
locked h5py build and output path with a tiny test.

## Parametric studies

Do not loop over simulations and start them directly in one script by default.
Instead:

1. Materialize one strict config per case.
2. Assign a stable case ID and seed.
3. Validate/estimate each case.
4. Sum aggregate CPU, memory concurrency, disk, files, and wall time.
5. Generate scripts only.
6. Review sampling design and avoid changing multiple factors ambiguously.
7. Submit through an approved external workflow.
8. Track failures/missing cases without silently resampling.

Analyze observables with refinement and stochastic uncertainty, not only final
values.

## Checkpoint and restart

Physical-state saving is checkpoint creation:

```python
params.output.periods_save.phys_fields = 1.0
```

But checkpoint usability requires:

- Complete `/state_phys` datasets.
- `/info_simul/params` and solver metadata.
- 0.9 state parameters where needed.
- Matching solver/grid/domain/state.
- SHA-256 and parent lineage.
- Enough disk for parent and child.

Use the bundled compatibility checker before every continuation. A mechanically
compatible state can still be scientifically invalid after changed viscosity,
forcing, timestep, backend, or resolution.

## Migration notes to 0.9.0

### 0.9.0 (release notes dated 2025-12-03)

- Restart files store state parameters.
- Added basic physical-field utilities.
- Fixed restart filenames.
- Improved post-initialization information and profile analysis.

### 0.8.6 (2025-11-23)

- h5netcdf 1.7 compatibility.
- Fixed incorrect restart for time-correlated forcing.

### 0.8.5 (2025-10-23)

- Python 3.14 support.

### 0.8.2 (2024-08-17)

- Python 3.12, NumPy 2.0, and mpi4py 4.0 compatibility.

### 0.8.0 (2024-01-31)

- Meson/meson-python build system.

Practical migrations from the previous skill:

- Python baseline: `>=3.11`, not `>=3.9` for 0.9.0.
- Use exact `fluidsim==0.9.0` and lock dependencies.
- Pseudospectral defaults need the `fft` extra.
- Use `time_stepping.cfl_coef`, not `CFL`.
- Use `forcing.tcrandom.time_correlation`, not a flat field.
- Use `plate2d`, not `fvk`.
- Physical states default to `.nc`, not `.h5`; spectra remain `.h5`.
- Use `spect_energy_budg.h5`, not a timestamped budget glob.
- Prefer `load_for_restart`/`fluidsim-restart --only-check`; preserve state
  parameters and hashes.
- Do not advertise ParaView direct compatibility without an explicit tested
  conversion/plugin.

## Sources (verified 2026-10-01)

- [FluidSim forcing base source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/base/forcing/base.py).
- [Specific forcing source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/base/forcing/specific.py).
- [Pseudospectral time-step API](https://fluidsim.readthedocs.io/en/latest/generated/fluidsim.base.time_stepping.pseudo_spect.html).
- [FluidSim development tutorial](https://fluidsim.readthedocs.io/en/latest/ipynb/tuto_dev.html).
- [FluidSim release notes](https://fluidsim.readthedocs.io/en/latest/changes.html).
- [FluidFFT plugins](https://fluidfft.readthedocs.io/en/latest/plugins.html).
- [FluidFFT supported libraries](https://fluidfft.readthedocs.io/en/latest/install/fft_libs.html).
- Mohanan et al., [FluidFFT primary paper](https://doi.org/10.5334/jors.238),
  published 2019-04-01.
- Mohanan et al., [FluidSim primary paper](https://doi.org/10.5334/jors.239),
  published 2019-04-26.
