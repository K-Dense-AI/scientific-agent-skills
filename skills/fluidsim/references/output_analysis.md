# Output inventory, plotting, and budget analysis

## Analyze without overclaiming

Output analysis can detect errors and quantify diagnostics. It cannot by itself
establish:

- Correct equations, units, or boundary/initial/forcing conditions.
- Adequate resolution or dealiasing.
- Stable/accurate time integration.
- Conservation or budget closure.
- Statistical stationarity.
- Grid/time convergence.
- Physical validity.

Keep plotting descriptive until those checks pass.

## FluidSim 0.9 physical-state format

Official 0.9 source selects:

- `.nc` with `h5netcdf` when h5py lacks MPI support (normal default).
- `.h5` with h5py when h5py is MPI-enabled.

Filename:

```text
state_phys_t<TIME>[_it<ITERATION>].nc
```

or `.h5`, depending on the backend. The file is HDF5-backed in either current
path. It contains:

- `/state_phys`: solver state datasets, plus netCDF dimension-scale datasets
  such as `x` and `y`; coordinates alone are not a valid physical state.
- `/state_phys` attributes including `time`, `it`, variable type, and purpose.
- `/info_simul`: solver and parameter provenance.
- Saved state parameters when available, including restart-relevant forcing
  state in 0.9.
- Root attributes such as run/solver identity, axes, and save date.

Do not infer the latest valid checkpoint solely from a filename. Verify HDF5
readability, `/state_phys`, time/iteration attributes, expected datasets,
parameters, state parameters, size, and checksum.

## Other common outputs

Exact outputs depend on the solver and enabled classes.

### Spatial means

- Legacy/solver-specific: `spatial_means.txt`, generally repeated
  `key = value` records.
- Some output classes use `spatial_means.json`, JSON-lines records.
- Typical content can include time, energy/enstrophy, forcing power,
  dissipation, and solver-specific quantities.

Use the solver's `load()` implementation. It can return a dictionary, pandas
object, or another solver-specific structure; do not assume one universal
DataFrame schema.

### Spectra

Current 2D base spectra initialize:

```text
spectra1D.h5
spectra2D.h5
```

Common datasets include:

- `times`
- `kxE`, `kyE`, or `khE`
- solver-specific `spectrum1D*` or `spectrum2D*` arrays

NS2D/NS3D and stratified variants define different keys and dimensions.
`load1d_mean()`/`load2d_mean()` return dictionaries in the base implementation;
inspect keys before use.

### Spectral energy budget

The current base filename is:

```text
spect_energy_budg.h5
```

For NS2D, current source computes `transfer2D_E` and `transfer2D_Z` and derives
fluxes with a reverse cumulative sum multiplied by wave-number spacing. Other
solvers define different transfer/budget terms.

Do not interpret a transfer sign, flux plateau, or cascade without verifying:

- Fourier/spectrum normalization.
- Wave-number coordinate and shell/bin measure.
- Sign convention.
- Time averaging interval and stationarity.
- Forcing/dissipation ranges.
- Finite-domain and dealiased cutoff effects.
- Closure against the corresponding global budget.

### Logs and parameter files

A normal run may include:

- `params_simul.xml`
- `info_solver.xml`
- `stdout.txt`
- a run lock while advancing
- solver/output-specific HDF5, netCDF4, text, or JSON files

Inventory actual contents instead of assuming all files exist.

## Bounded metadata inventory

```bash
python3 scripts/output_inventory.py \
  --path run-directory \
  --max-files 256 \
  --max-hdf5-files 32 \
  --max-datasets 2000 \
  --max-attributes 5000
```

The helper:

- Accepts only local paths inside `--root`.
- Rejects URLs, parent traversal, symlinks, hard links, special files, and
  unbounded counts.
- Lazily imports h5py only for HDF5/netCDF4 candidates.
- Reports dataset shape, dtype, chunks, compression, and allocated storage.
- Reads only a short allowlist of scalar provenance attributes.
- Does not index datasets.
- Does not follow soft or external HDF5 links.
- Emits strict JSON and no raw field values.

The byte/count limits and hyperslabs bound requested data, not native HDF5
metadata allocation or decompression buffers; they are not an OS memory quota.

If a `.nc` file is classic netCDF rather than HDF5, it reports it unreadable
rather than trying another unbounded parser.

## Read-only FluidSim object

```python
from fluidsim import load_sim_for_plot

sim = load_sim_for_plot(
    "run-directory",
    merge_missing_params=False,
    hide_stdout=True,
)
```

Official 0.9 source uses a coarse operator and disables saving/online plots.
This is appropriate for output-class analysis, not full-resolution arbitrary
field operations.

Examples:

```python
sim.output.phys_fields.plot(time=1.0)
sim.output.spatial_means.plot()
sim.output.spectra.plot1d(tmin=0.5, tmax=1.0, coef_compensate=0)
sim.output.spect_energy_budg.plot(tmin=0.5, tmax=1.0)
```

For NS2D, `plot1d` and `plot2d` default to `coef_compensate=3`, multiplying
the plotted spectrum by a power of wave number. Use `coef_compensate=0` for
an uncompensated spectrum and record the choice before interpreting slopes.

Methods and accepted arguments vary by solver/output class. Check the selected
class API. A successful plot says nothing about correctness.

## Full state loading

```python
from fluidsim import load_state_phys_file

sim = load_state_phys_file(
    "run-directory",
    t_approx="last",
    modif_save_params=True,
    merge_missing_params=False,
    init_with_initialized_state=True,
    hide_stdout=True,
)
```

This can allocate full-resolution state/operators. Run the memory estimator
first and do not use it merely to inspect metadata.

`modif_save_params=True` disables saving/online plotting. To continue a run,
use the reviewed restart workflow rather than toggling saving casually.

## Scalar and spectral summary helper

```bash
python3 scripts/budget_summary.py \
  --path run-directory \
  --max-files 128 \
  --max-records 200000 \
  --max-datasets 256 \
  --max-values-per-dataset 4096
```

It:

- Aggregates finite spatial-mean values in constant memory.
- Supports every semicolon-separated term in FluidSim key/value text and
  strict JSON-lines, including enstrophy and total injection/dissipation.
- Counts nonfinite values rather than silently reporting a finite-only success;
  its mean remains an unweighted mean of finite saved samples.
- Summarizes only bounded spectral/budget hyperslabs.
- Uses the latest first-axis record for multidimensional datasets.
- Emits a sum only when the entire latest record fits the value bound.
- Does not follow soft/external links, and rejects virtual/external dataset
  storage before reading values; it does not load full large arrays.
- Explicitly reports that convergence/physical validity are not established.

This is a triage summary, not a solver-aware closure calculation or a
time-weighted average. Check `nonfinite_count` alongside the finite statistics.

## Budget checks

Construct a table or plot for each governing budget:

1. Stored quantity change over the same interval.
2. Measured forcing/input.
3. Physical and numerical dissipation.
4. Transfer terms with consistent sign/normalization.
5. Boundary terms (zero only if justified by periodicity/model).
6. Residual after all terms.

Report absolute and normalized residuals, time interval, differencing method,
save cadence, and uncertainty. A small instantaneous residual can be accidental;
inspect trends and refinement.

For forced turbulence, compare requested `forcing_rate` to measured forcing
power. They are not interchangeable without checking the implementation's
normalization and time discretization.

## Resolution and dealiasing diagnostics

At minimum:

- Plot/inspect spectra up to the dealiased cutoff.
- Quantify energy/variance in a documented high-wave-number tail band.
- Check pile-up, aliasing signatures, anisotropy, and directional spectra where
  relevant.
- Check physical-space extrema/gradients and solver constraints.
- Repeat at finer resolution with the same physical/nondimensional problem.
- Avoid choosing an “inertial range” after seeing the desired slope without
  reporting selection criteria and sensitivity.

Power-law fitting alone does not verify a cascade or resolved simulation.

## Time-step diagnostics

Use stdout/output time-step history to inspect:

- Initial and maximum `deltat`.
- CFL-driven changes.
- Fast-wave or buoyancy/rotation scales.
- Diffusive/hyperdiffusive limits.
- Discontinuities around restart.
- Sensitivity to lower `deltat_max`/`cfl_coef`.

Do not infer stability from the absence of NaNs.

## Stationarity and averaging

Before time averaging:

- Define stationarity metrics and burn-in independently of the desired result.
- Plot energy, dissipation, forcing, and key observables.
- Check drift and autocorrelation/integral times.
- Report effective sample duration/count.
- Repeat across seeds or independent intervals where stochastic uncertainty
  matters.

Do not label “statistically steady” from a short visual plateau.

## Custom HDF5 reading

If built-in loaders are insufficient, keep access bounded:

```python
import h5py

with h5py.File("spectra2D.h5", "r") as handle:
    dataset = handle["spectrum2D_E"]
    latest = dataset[-1, :4096]
```

Before indexing, inspect shape, dtype, chunks, and expected bytes. Never use
`dataset[...]` or `[:]` on an unknown large field. Check HDF5 links before
traversal; an external link can open another file.

## Plot/report provenance

Every exported result should carry:

- Parent run/config/script/lock hashes.
- Solver and package/backend versions.
- Grid/domain/dealiasing/time scheme/CFL.
- Initial/forcing/dissipation definitions.
- State/output file hashes or immutable manifest.
- Exact dataset keys and time window.
- Averaging/binning/normalization and plotting code revision.
- Refinement and budget-check results.

Avoid manual GUI-only transformations that cannot be reconstructed.

## Sources (verified 2026-10-01)

- [Physical-field save source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/util/phys_fields.py)
  — `.nc`/`.h5` selection, groups, attributes, state parameters, filename.
- [Physical-fields output source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/base/output/phys_fields.py).
- [NS2D spatial-means source](https://fluidsim.readthedocs.io/en/latest/_modules/fluidsim/solvers/ns2d/output/spatial_means.html)
  — semicolon-separated energy, enstrophy, and total budget terms.
- [h5py link access](https://docs.h5py.org/en/stable/high/group.html) and
  [dataset storage](https://docs.h5py.org/en/stable/high/dataset.html).
- [Spatial-means source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/base/output/spatial_means.py).
- [Spectra source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/base/output/spectra.py).
- [Spectral-budget base source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/base/output/spect_energy_budget.py).
- [NS2D spectral-budget source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/solvers/ns2d/output/spect_energy_budget.py).
- [Load utilities](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/util/util.py).
- Mohanan et al., [FluidSim primary paper](https://doi.org/10.5334/jors.239),
  published 2019-04-26 — architecture and output-class method claims.
