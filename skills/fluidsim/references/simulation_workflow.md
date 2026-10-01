# Bounded simulation, pilot, and restart workflow

## 1. Define the scientific contract

Before code, record:

- Equations, dependent variables, approximations, and solver key.
- Units for every dimensional quantity, or reference scales and a complete
  nondimensionalization map.
- Domain lengths, geometry, periodic boundary conditions, and symmetries.
- Initial-condition construction, constraints, amplitude/spectrum, and seed.
- Forcing field, band, normalization, correlation, and expected/measured input.
- Dissipation and any hypo-/hyper-viscosity.
- Observables and acceptance thresholds.
- Conservation/budget identities and expected numerical residual behavior.
- Grid, dealiasing, timestep/CFL, and refinement plan.
- Independent benchmark or verification target.

Do not proceed from a prompt that only says “simulate turbulence” or supplies a
Reynolds number without its definition and scaling.

## 2. Declare operational bounds

Every plan must explicitly bound:

- CPU cores.
- MPI ranks and threads/rank.
- Total and per-rank RAM envelope.
- Disk bytes and file/inode count.
- Wall time and FluidSim `max_elapsed`.
- Grid dimensions and total points.
- State snapshot and diagnostic save periods.
- Safe output root and subdirectory.

The bundled JSON schema requires these fields. Start from:

```bash
python3 scripts/solver_config_validator.py --example
```

Save the reviewed JSON locally, then:

```bash
python3 scripts/solver_config_validator.py --config config.json
python3 scripts/grid_resource_estimator.py --config config.json
python3 scripts/simulation_dry_run.py --config config.json --output run.py
```

The resource estimator reports an approximate allocation/storage model, not
measured peaks or enforced quotas. Save records are counted independently of
the declared file limit; exceeding a limit is a failure, never a truncated
estimate. Enabled diagnostics outside physical fields, spectra, spectral budget,
and spatial means require a separate estimate. Iteration-only termination does
not provide the time horizon this storage model needs.

The generator does not import FluidSim or run anything. The generated script
prints a JSON dry run by default. Execution requires both `--execute` and the
exact reviewed config ID. An MPI plan is only a command preview; the tool never
invokes a launcher or scheduler.

## 3. Verify the locked environment

In an isolated exact environment:

```python
from importlib.metadata import version
from fluidfft import get_methods

assert version("fluidsim") == "0.9.0"
assert version("fluidfft") == "0.4.5"
print(sorted(get_methods()))
```

Record registered FFT methods, then load and exercise the chosen method.
`get_methods()` lists entry points even when an optional dependency is absent
(for example Dask). Importing a package is not enough: construct the selected
solver's defaults and run its tiny transform/solver smoke.

## 4. Tiny no-output serial smoke

After approval, use a trivial, bounded state:

```python
from fluidsim.solvers.ns2d.solver import Simul

params = Simul.create_default_params()
params.oper.nx = params.oper.ny = 8
params.oper.Lx = params.oper.Ly = 2.0
params.oper.coef_dealiasing = 2 / 3
params.time_stepping.USE_CFL = False
params.time_stepping.deltat0 = 0.001
params.time_stepping.deltat_max = 0.001
params.time_stepping.t_end = 0.001
params.time_stepping.max_elapsed = "00:01:00"
params.init_fields.type = "constant"
params.init_fields.constant.value = 0.0
params.output.HAS_TO_SAVE = False
params.output.ONLINE_PLOT_OK = False

sim = Simul(params)
sim.time_stepping.start()
```

This checks import, FFT construction, initialization, and one bounded step. It
does not test the intended physics, forcing, conservation, convergence,
performance, output, or restart.

## 5. Tiny output/restart smoke

Use a dedicated empty output root under a quota. Keep:

- `params.output.sub_directory` a safe one-component study identifier.
- `ONLINE_PLOT_OK = False` for unattended runs.
- Short `t_end`, short `max_elapsed`, and low resolution.
- One or two physical-state saves and a bounded scalar diagnostic.
- Spectra/budget outputs disabled unless they are the feature being tested.

Inspect before analysis:

```bash
python3 scripts/output_inventory.py --path fluidsim-runs
python3 scripts/budget_summary.py --path fluidsim-runs
```

Confirm exact filenames and growth. FluidSim 0.9 defaults to
`state_phys_t*.nc` for physical states; spectra remain HDF5.

## 6. Representative scientific pilot

Increase only enough to exercise the intended:

- Initial-condition path.
- Forcing type and injection normalization.
- Solver-specific state and outputs.
- FFT backend.
- Checkpoint and restart.
- Analysis code.

During and after the pilot, check:

- CFL and `deltat` history against all relevant wave/advection/diffusion limits.
- Divergence or other constraints.
- Energy/enstrophy/scalar/potential-energy budgets as appropriate.
- Measured forcing input and dissipation.
- Spectral tails and dealiasing contamination.
- Runtime, peak RSS, per-rank imbalance, file count, and disk growth.
- NaN/Inf, stalled advancement, unexpected truncation, and incomplete files.

A passing pilot permits planning a refinement study; it does not validate a
production run.

## 7. Running a reviewed serial plan

The generated script is deliberately gated:

```bash
python3 run.py
python3 run.py --execute --acknowledge-config-id REVIEWED_CONFIG_ID
```

At execution, it verifies the installed FluidSim/FluidFFT versions, assigns
reviewed thread limits before NumPy import, and checks the actual MPI size.
Restart paths are anchored to the script directory and rehashed before loading;
use a matching `provenance.restart.path` and `init_fields.from_file.path`.
These are preflight checks, not RAM/disk/CPU quota enforcement.

The first command is dry-run only. The second is a real simulation and must be
issued by the user or approved operator after reviewing limits and output
destination.

Never silently increase resolution, duration, save frequency, rank count, or
wall time after approval.

## 8. Read-only loading

Use the lightweight loader:

```python
from fluidsim import load_sim_for_plot

sim = load_sim_for_plot(
    "run-directory",
    merge_missing_params=False,
    hide_stdout=True,
)
```

Use native loaders only on trusted run metadata: they import the recorded
solver/extension modules. For untrusted files, start with the bounded metadata
helpers instead.

Official 0.9 source shows that it:

- Loads solver and parameters from the result directory.
- Sets a constant initialization and coarse operator.
- Sets `NEW_DIR_RESULTS = False`.
- Sets `output.HAS_TO_SAVE = False` and `ONLINE_PLOT_OK = False`.
- Selects default/sequential FFT for plotting.
- Can merge missing defaults for older runs when explicitly requested.

`merge_missing_params=True` helps load old metadata but does not prove that an
old result is scientifically or numerically equivalent under the new version.

## 9. State-bearing loading

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

This constructs a full-resolution operator and loads state; it can be expensive.
With the default `modif_save_params=True`, saving and online plotting are
disabled. Loading a state object is not the same as approving a restart.

## 10. Reviewed Python restart

First compare metadata:

```bash
python3 scripts/restart_compatibility.py \
  --source state_phys_t001.000.nc \
  --target-config restart-config.json
```

The checker uses required state keys and dataset shapes/dtypes, not just a
nonempty `/state_phys` group. It requires grid/domain metadata and finite state
time. For a directory it examines at most 256 entries in that run, selecting by
stored time/iteration rather than filename ordering; ambiguous latest states
require an explicit file. Soft/external links are rejected. For time-correlated
forcing, `/state_params/forcing` must contain `seed0`, `seed1`, and
`t_last_change`. A JSON manifest must provide `state.dataset_metadata` entries
with `shape` and `numeric: true` for each required field; its digest is a
declaration, unlike a digest computed from the checkpoint.

Then, after approval:

```python
from fluidsim import load_for_restart

params, Simul = load_for_restart(
    "run-directory",
    t_approx="last",
    merge_missing_params=False,
)
params.time_stepping.t_end = 2.0
params.time_stepping.max_elapsed = "00:10:00"
params.NEW_DIR_RESULTS = True

sim = Simul(params)
sim.time_stepping.start()
```

`load_for_restart` reads parameters from `/info_simul/params`, sets
`init_fields.type = "from_file"`, points it to the selected state file, and by
default sets `NEW_DIR_RESULTS = False`. Explicitly choose append versus new
directory. Never append to an irreplaceable run without a backup and checksum.

Record:

- Parent run ID/path and state SHA-256.
- Selected state time/iteration.
- Parent and child package/backend/platform versions.
- Every changed parameter and justification.
- Append/new-directory decision.
- Forcing state continuity.
- Child output inventory and lock/script/config hashes.

FluidSim 0.9.0 stores “state parameters” in restarting files. FluidSim 0.8.6
fixed incorrect restart of time-correlated forcing; old checkpoints need extra
review.

## 11. Upstream restart CLI

Safe first action:

```bash
fluidsim-restart --only-check run-directory --t_end 2.0
```

Current options include `--only-check`, `--only-init`, `--new-dir-results`,
`--t_approx`, target/additive time or iteration bounds,
`--merge-missing-params`, and `--max-elapsed`.

Avoid `--modify-params` with any untrusted or generated text. Official source
passes that string to Python code execution. The bundled generator never emits
this option.

The CLI does not supply scheduler resource limits. Running it under MPI or a
scheduler remains a separate, explicit operational action.

## 12. Resolution changes

Do not change `oper.nx/ny/nz` and treat an old state file as directly compatible.
FluidSim provides:

```bash
fluidsim-modif-resolution run-directory 5/4
```

This creates a new state at modified resolution. Before use:

- Inventory free memory and disk; interpolation/FFT can be expensive.
- Preserve the original state.
- Record coefficient, source/output hashes, and implementation version.
- Check domain, state keys, normalization, and constraints.
- Treat the child as a new numerical experiment.
- Re-run transient, budget, spectral, and refinement checks.

Do not run this automatically or on a large state by default.

## 13. MPI/HPC handoff

After a serial pilot:

1. Ask the site scheduler for the intended allocation; never submit from this
   skill.
2. Verify the pinned MPI/FluidFFT environment inside that allocation.
3. Run a manually launched tiny two-rank smoke.
4. Benchmark candidate FFT methods on representative small shapes.
5. Confirm decomposition compatibility and local array sizes.
6. Set explicit process/thread affinity.
7. Set memory/rank, wall time, scratch, output quota, and signal/checkpoint
   behavior.
8. Use a short restartable pilot before scale-up.

The 2019 FluidSim/FluidFFT performance results are hardware- and shape-specific.
Do not extrapolate their wall times or fastest backend to another cluster.

## Failure and interruption handling

- Preserve logs and last complete checkpoint.
- Treat a signal-terminated or wall-time-limited run as incomplete until the
  checkpoint is inventoried and validated.
- Do not pick the lexically latest file without checking its time, iteration,
  HDF5 readability, and checksum.
- Never overwrite the parent state during recovery.
- Re-run the compatibility checker before every continuation.
- Explain any budget discontinuity at the restart boundary.

## Sources (verified 2026-10-01)

- [FluidSim user tutorial](https://fluidsim.readthedocs.io/en/latest/ipynb/tuto_user.html).
- [Restart and resolution change](https://fluidsim.readthedocs.io/en/latest/ipynb/restart_modif_resol.html).
- [FluidSim load/restart source](https://github.com/fluiddyn/fluidsim/blob/0.9.0/fluidsim/util/util.py).
- [Restart CLI source](https://fluidsim.readthedocs.io/en/latest/_modules/fluidsim_core/scripts/restart.html).
- [FluidSim 0.9 release notes](https://fluidsim.readthedocs.io/en/latest/changes.html).
- Mohanan et al., [FluidSim primary paper](https://doi.org/10.5334/jors.239),
  published 2019-04-26; performance claims are limited to its documented
  benchmark setup.
