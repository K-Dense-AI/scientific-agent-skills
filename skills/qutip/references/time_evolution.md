# QuTiP 5.3 Time Evolution

Research and API verification date: **2026-10-01**. All signatures and examples
target `qutip==5.3.1`.

## Solver selection

| Solver | State/model | Main uncertainty |
|---|---|---|
| `sesolve` | Schrödinger equation, pure state, no collapse channels | ODE and model approximation |
| `mesolve` | Lindblad master equation, mixed state, or Liouvillian | channel validity and ODE error |
| `mcsolve` | quantum-jump trajectories | ODE error plus sampling error |
| `brmesolve` | microscopic weak-coupling bath spectra | Born-Markov/secular approximation and positivity |
| `ssesolve` | stochastic Schrödinger equation | diffusive record sampling |
| `smesolve` | stochastic master equation with monitored/unmonitored channels | diffusive record sampling |
| `fsesolve`/`fmmesolve` | periodic Floquet dynamics | period, basis, harmonic and bath approximations |

Do not use `mcsolve` merely to make a deterministic calculation parallel. Do
not use `brmesolve` as a generic replacement for a Lindblad model.

## Current function signatures

The important QuTiP 5.3 call boundaries are:

```text
sesolve(H, psi0, tlist, *, e_ops=None, args=None, options=None)
mesolve(H, rho0, tlist, c_ops=None, *, e_ops=None, args=None, options=None)
mcsolve(H, state, tlist, c_ops=(), *, e_ops=None, ntraj=500,
        args=None, options=None, seeds=None, target_tol=None, timeout=None)
brmesolve(H, psi0, tlist, a_ops=None, sec_cutoff=0.1, *,
          c_ops=None, e_ops=None, args=None, options=None)
ssesolve(H, psi0, tlist, sc_ops=(), heterodyne=False, *,
         e_ops=None, args=None, ntraj=500, options=None, seeds=None,
         target_tol=None, timeout=None)
smesolve(H, rho0, tlist, c_ops=(), sc_ops=(), heterodyne=False, *,
         e_ops=None, args=None, ntraj=500, options=None, seeds=None,
         target_tol=None, timeout=None)
```

In 5.3, `e_ops`, `args`, and `options` are keyword-only. Passing solver options
as arbitrary solver keyword arguments was removed. The old `qutip.Options`
export is no longer present; pass an ordinary dictionary.

## `sesolve`: closed unitary evolution

```python
import numpy as np
from qutip import basis, sesolve, sigmax, sigmaz

H = 0.5 * sigmax()
psi0 = basis(2, 0)
tlist = np.linspace(0.0, 10.0, 201)

result = sesolve(
    H,
    psi0,
    tlist,
    e_ops={"z": sigmaz()},
    options={"atol": 1e-10, "rtol": 1e-8, "progress_bar": ""},
)
z = np.asarray(result.e_data["z"])
```

For an ODE norm/trace audit, set `options["normalize_output"] = False`:
`sesolve`/`mesolve` normally normalize an initially normalized state on output,
which can conceal integrator drift. Quantum-jump trajectory normalization is
part of the unravelling and is a different operation.

Audit Hamiltonian Hermiticity and state norm. If norm drift is material, tighten
tolerances or investigate the model; do not normalize away unexplained error.

## `mesolve`: Lindblad or explicit Liouvillian evolution

```python
import numpy as np
from qutip import basis, mesolve, sigmam, sigmaz

gamma = 0.2
excited = basis(2, 0)
tlist = np.linspace(0.0, 12.0, 241)

result = mesolve(
    0.5 * sigmaz(),
    excited,
    tlist,
    c_ops=[np.sqrt(gamma) * sigmam()],
    e_ops={"p_excited": excited.proj()},
    options={
        "method": "adams",
        "atol": 1e-10,
        "rtol": 1e-8,
        "store_final_state": True,
        "progress_bar": "",
    },
)
```

When no collapse operators are supplied and `H` is not a superoperator,
`mesolve` may defer to `sesolve`. If `H` is an explicit Liouvillian, document
whether it is in valid Lindblad form or represents a deliberate approximation.

## `mcsolve`: quantum jumps

```python
result = mcsolve(
    0.5 * sigmaz(),
    excited,
    tlist,
    [np.sqrt(gamma) * sigmam()],
    e_ops=[excited.proj()],
    ntraj=500,
    seeds=20260723,
    options={
        "keep_runs_results": False,
        "progress_bar": "",
    },
)

mean_population = result.average_expect[0]
trajectory_spread = result.std_expect[0]
seed_manifest = result.seeds
```

`seeds` may be one integer/`SeedSequence` used to spawn trajectory seeds, or a
list with one seed per trajectory. QuTiP stores the realized seeds in the
result. Reusing them enables a paired comparison, but paired runs are not
independent replicates.

Trajectory rigor:

- increase `ntraj` and report stabilization or a target uncertainty;
- distinguish trajectory standard deviation from standard error of the mean;
- set `options={"keep_runs_results": True}` only when individual trajectories
  are actually required, because memory scales with trajectories and time
  points;
- collapse records are available per trajectory through result attributes such
  as `collapse`; do not print unbounded records by default;
- `target_tol` may stop before `ntraj`, so report the number actually run;
- report timeout termination and solver stats.

For mixed initial conditions, current QuTiP can sample the initial mixture; the
result then includes initial-state accounting. State this extra source of
sampling explicitly.

## `brmesolve`: Bloch-Redfield evolution

```python
import numpy as np
from qutip import basis, brmesolve, sigmax, sigmaz

def one_sided_spectrum(w):
    return 0.03 * w if w > 0.0 else 0.0

tlist = np.linspace(0.0, 30.0, 601)
result = brmesolve(
    0.5 * sigmaz(),
    basis(2, 0),
    tlist,
    a_ops=[(sigmax(), one_sided_spectrum)],
    e_ops={"z": sigmaz()},
    sec_cutoff=0.1,
    options={"atol": 1e-10, "rtol": 1e-8, "progress_bar": ""},
)
```

The coupling operator in each `a_ops` pair is normally Hermitian, and the
spectrum is a function of **angular frequency**. Prefer a current QuTiP
Environment object when it represents the bath more clearly.

Required checks:

- weak system-bath coupling (Born approximation);
- short bath memory compared with system dynamics (Markov approximation);
- stationary bath and correct positive/negative-frequency convention;
- secular choice: `sec_cutoff=-1` disables secularization and can worsen
  positivity;
- density-matrix trace, Hermiticity, and minimum eigenvalue over time.

See `advanced.md` for the physical boundaries.

## Stochastic Schrödinger and master equations

Use these for diffusive continuous-measurement unravellings, not jump
trajectories:

```python
result = smesolve(
    H,
    rho0,
    tlist,
    c_ops=unmonitored_channels,
    sc_ops=monitored_channels,
    heterodyne=False,  # homodyne
    e_ops={"signal": measured_quadrature},
    ntraj=200,
    seeds=20260723,
    options={"dt": 0.001, "store_measurement": "end", "progress_bar": ""},
)
```

- `c_ops` are unmonitored deterministic dissipation channels. Even from a ket,
  use `smesolve` if any such channel is present; `ssesolve` has no `c_ops`.
- Stochastic methods include `platen`, `rouchon`, and `euler`, each with its
  own options. Do not pass deterministic `adams`/`bdf` or their `atol`/`rtol`
  to a fixed-step stochastic integrator; converge `dt` instead.
- `sc_ops` are monitored stochastic channels.
- `heterodyne=False` is homodyne; `True` is heterodyne.
- Legacy integer `noise` selectors are not current API.
- Measurement records can be much larger than expectation summaries; store
  them only when needed.
- Converge the stochastic integration step `dt` separately from `ntraj`.
- `result.measurement` has shape `(ntraj, n_sc_ops, len(tlist)-1)` for homodyne
  and `(ntraj, n_sc_ops, 2, len(tlist)-1)` for heterodyne. Use
  `store_measurement="start"` for replay with `run_from_experiment(...,
  measurement=True)`; the default/end record uses different state timing.

## Time-dependent systems and QobjEvo

### Pythonic callable coefficients

```python
import numpy as np
from qutip import QobjEvo, sigmax, sigmaz

def pulse(t, amplitude, center, width):
    return amplitude * np.exp(-0.5 * ((t - center) / width) ** 2)

H = QobjEvo(
    [0.5 * sigmaz(), [sigmax(), pulse]],
    args={"amplitude": 0.2, "center": 5.0, "width": 1.0},
)
H_at_t = H(5.0)
H.arguments(amplitude=0.15)
```

The Pythonic form `f(t, parameter, ...)` is current. The legacy
`f(t, args_dictionary)` form is deprecated in 5.3 and scheduled for removal in
5.5.

### Sampled coefficients

```python
coefficient_times = np.linspace(0.0, 10.0, 501)
samples = np.cos(coefficient_times)
H = QobjEvo(
    [0.5 * sigmaz(), [sigmax(), samples]],
    tlist=coefficient_times,
    order=3,
)
```

Sample times must be sorted and match coefficient length. `order=0` gives a
left/previous-value step function; the default cubic spline can overshoot.
Converge the coefficient sampling independently of solver output times.

QuTiP also accepts expression strings and may compile them, but this skill does
not construct such expressions from configuration or user text. Use trusted
callables or numeric arrays in generated workflows.

## Option dictionaries and integrators

Common solver options:

```python
options = {
    "method": "adams",
    "atol": 1e-10,
    "rtol": 1e-8,
    "nsteps": 10000,
    "store_states": False,
    "store_final_state": True,
    "progress_bar": "",
}
```

Options are solver- and integrator-specific. Consult the selected solver's
`.options` documentation before using a key.

Common integration choices:

- `adams`: non-stiff default for many deterministic solvers;
- `bdf`: stiff systems;
- `lsoda`: switches between non-stiff and stiff methods;
- explicit high-order methods such as `dop853`, `vern7`, or `vern9`;
- `diag`: diagonalization-based constant-system evolution;
- `krylov`: suitable cases where Krylov evolution is beneficial.

An integrator label is not an accuracy certificate. Compare at least two
tolerance levels, inspect warnings/stats, and compare a second method for a
representative stiff or difficult case.

QuTiP 5.3 adds `matrix_form` for `mesolve`/`MESolver`:

```python
options = {"matrix_form": True, "atol": 1e-10, "rtol": 1e-8}
```

It uses matrix-matrix products and may reduce memory in suitable models.
Benchmark both time and verified observables before adopting it.

## Time grids

`tlist` is the requested output grid, not necessarily the integrator's internal
step sequence.

Checks:

1. finite, strictly increasing values;
2. includes the physically intended initial time;
3. resolves the fastest Hamiltonian, decay, drive-envelope, and measurement
   scales in the returned output;
4. long enough to capture transients or steady behavior;
5. converged under a denser output grid where downstream interpolation, FFT, or
   peak detection depends on sampling.

For FFT spectra, a uniform `taulist` is required and its spacing/window set
Nyquist range and frequency resolution.

## Result semantics

Current solver results can contain:

| Attribute | Meaning |
|---|---|
| `times` | returned times |
| `states` | stored states; may be empty depending on options and `e_ops` |
| `final_state` | final state when requested |
| `expect` | list aligned with list-form `e_ops` |
| `e_data` | dictionary keyed like dict-form `e_ops` |
| `options` | effective result/solver options |
| `solver` | solver name |
| `stats` | timing and diagnostic statistics |

Multi-trajectory results add trajectory counts, seeds, standard deviations,
average states, measurements, and optionally individual run results. Never
assume `.states` means individual trajectories; inspect
`keep_runs_results` and the concrete result type. For multi-trajectory results,
`.expect`/`.e_data` and `.states` switch to per-run arrays when runs are retained.
Use `.average_expect`/`.average_e_data` and `.average_states` explicitly for
ensemble means, and `.runs_expect`/`.runs_states` for individual trajectories.
Trajectory count is an unravelling sample count, not hardware measurement shots.

QuTiP 5.3 adds `Result.plot_expect()` and `MultiTrajResult.plot_expect()`.
Prefer explicit axes in reusable code.

## Repeated systems

Solver classes (`SESolver`, `MESolver`, `MCSolver`, `BRSolver`, `SMESolver`,
and others) can reuse a constructed right-hand side across runs:

```python
from qutip import MESolver

solver = MESolver(H, c_ops, options={"atol": 1e-10, "rtol": 1e-8})
first = solver.run(rho_a, tlist, e_ops=e_ops)
second = solver.run(rho_b, tlist, e_ops=e_ops)
```

Use the class interface when repeated setup is material, and verify that
updated arguments and initial states are the intended ones.

## Portable output

Do not load untrusted serialized Python or QuTiP objects. For exchange and
audit, save:

- scalar configuration and assumptions;
- real/imaginary numeric arrays;
- dimensions, versions, tolerances, seeds, and solver stats;
- checksums and schema versions where long-term provenance matters.

The bundled CLIs use bounded strict JSON and never pickle results.

## Local tools

- `../scripts/two_level_simulation.py`: bounded `mesolve`/`mcsolve` example.
- `../scripts/solver_config_planner.py`: solver and option checklist.
- `../scripts/convergence_sweep.py`: deterministic or trajectory convergence.
- `../scripts/result_audit.py`: portable JSON audit.

## Sources (verified 2026-10-01)

- [Dynamics API](https://qutip.readthedocs.io/en/stable/apidoc/solver.html)
- [QobjEvo and coefficients API](https://qutip.readthedocs.io/en/stable/apidoc/time_dep.html)
- [Dynamics user guide](https://qutip.readthedocs.io/en/stable/guide/guide-dynamics.html)
- [Monte Carlo guide](https://qutip.readthedocs.io/en/stable/guide/dynamics/dynamics-monte.html)
- [Stochastic solver guide](https://qutip.readthedocs.io/en/stable/guide/dynamics/dynamics-stochastic.html)
- [Bloch-Redfield guide](https://qutip.readthedocs.io/en/stable/guide/dynamics/dynamics-bloch-redfield.html)
- [QuTiP 5.3.1 release](https://github.com/qutip/qutip/releases/tag/v5.3.1)
- [QuTiP 5 migration changelog](https://qutip.readthedocs.io/en/stable/changelog.html#qutip-5-0-0-2024-03-28)
