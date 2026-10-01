# QuTiP 5.3 Advanced Methods and Package Boundaries

Research and API verification date: **2026-10-01**. Examples target
`qutip==5.3.1`.

Specialized methods add assumptions and convergence parameters. Use them only
when the physical model requires them.

## Bloch-Redfield

`brmesolve` derives dissipative dynamics from system coupling operators and bath
noise-power spectra:

```python
import numpy as np
from qutip import basis, brmesolve, sigmax, sigmaz

def bath_spectrum(w):
    return 0.02 * w if w > 0.0 else 0.0

result = brmesolve(
    0.5 * sigmaz(),
    basis(2, 0),
    np.linspace(0.0, 30.0, 601),
    a_ops=[(sigmax(), bath_spectrum)],
    e_ops={"z": sigmaz()},
    sec_cutoff=0.1,
    options={"atol": 1e-10, "rtol": 1e-8, "progress_bar": ""},
)
```

Required assumptions:

- weak system-environment coupling (Born approximation);
- initially factorized system/bath state where the derivation requires it;
- bath correlations decay faster than system evolution (Markov approximation);
- stationary bath spectra with the correct angular-frequency and
  positive/negative-frequency convention;
- a justified secular or partial-secular cutoff.

`sec_cutoff=-1` disables secularization. QuTiP's documentation warns that the
non-secular equation may produce negativity. Inspect trace, Hermiticity, and
minimum density-matrix eigenvalue through the entire run.

Environment objects can express thermal and fitted spectra more clearly than
callbacks. When using a callback, test it over every transition frequency and
near zero.

## Diffusive stochastic evolution

Use `ssesolve` for conditioned pure states and `smesolve` for density matrices:

```python
result = smesolve(
    H,
    rho0,
    tlist,
    c_ops=unmonitored_channels,
    sc_ops=monitored_channels,
    heterodyne=False,
    e_ops={"signal": measured_quadrature},
    ntraj=300,
    seeds=20260723,
    options={
        "dt": 0.001,
        "store_measurement": "end",
        "progress_bar": "",
    },
)
```

`heterodyne=False` selects homodyne and `True` selects heterodyne. Legacy
integer noise selectors are stale.

Converge:

- stochastic integration `dt`;
- output grid;
- trajectory count;
- seed sensitivity;
- monitored efficiency/model choices;
- measurement timing (`"start"` versus default end-of-step semantics when
  relevant).

`SMESolver.run_from_experiment` can replay known numeric noise or measurement
records. Treat records as bounded numeric data; do not accept executable
callbacks from untrusted configuration.

## Non-Markovian Monte Carlo with time-local rates

`nm_mcsolve` is for time-local master equations whose decay rates can become
negative. Its current input is a collection of operator/rate pairs, not a
generic two-time bath-correlation callback:

```python
import numpy as np
from qutip import basis, nm_mcsolve, sigmam, sigmaz

def rate(t):
    return 0.1 * np.sin(t)

result = nm_mcsolve(
    0.5 * sigmaz(),
    basis(2, 0),
    np.linspace(0.0, 5.0, 101),
    [(sigmam(), rate)],
    e_ops=[basis(2, 0).proj()],
    ntraj=400,
    seeds=20260723,
    options={"progress_bar": ""},
)
```

Here the integrated rate is `0.1 * (1 - cos(t)) >= 0`, so the exact
excited population `exp(-0.1 * (1 - cos(t)))` stays in `[0, 1]` even
when the instantaneous rate becomes negative. A cosine rate instead would
produce population above one after pi for this initially excited state.

This method does not make an arbitrary non-Markovian model valid. Verify that
the time-local generator and influence-martingale construction apply, report
sampling uncertainty, and audit completeness/positivity behavior.

## Floquet theory

For \(H(t+T)=H(t)\), the current QuTiP 5 abstraction is `FloquetBasis`:

```python
import numpy as np
from qutip import FloquetBasis, QobjEvo, sigmax, sigmaz

drive_frequency = 2.0
period = 2.0 * np.pi / drive_frequency

def drive(t, amplitude, omega):
    return amplitude * np.cos(omega * t)

H = QobjEvo(
    [0.5 * sigmaz(), [sigmax(), drive]],
    args={"amplitude": 0.2, "omega": drive_frequency},
)
floquet = FloquetBasis(H, period)
quasienergies = floquet.e_quasi
modes_at_zero = floquet.mode(0.0)
```

Before using Floquet dynamics:

1. numerically check `H(t + period) - H(t)` over representative times;
2. state the quasi-energy branch convention;
3. sweep Hilbert truncation and any precomputation grid;
4. inspect near-degenerate quasi-energies;
5. compare one-period propagation with direct evolution.

`fsesolve` handles closed periodic dynamics. `fmmesolve` handles a
Floquet-Markov construction:

```python
result = fmmesolve(
    floquet,
    rho0,
    tlist,
    c_ops=coupling_operators,
    spectra_cb=spectrum_callbacks,
    e_ops={"z": sigmaz()},
    w_th=temperature,
)
```

The coupling operators and spectrum callbacks are paired by position. They are
not ordinary Lindblad channels. Spectrum callbacks must accept and return
NumPy arrays (use `np.where`, not scalar `if w > 0`). Use `FMESolver`
directly to sweep its `kmax` sideband cutoff and `nT` quadrature count.
Verify weak-coupling, bath, and thermal
assumptions. QuTiP 5 result states are in the lab basis by default; the
`store_floquet_states` option controls additional Floquet-basis storage.

Old free-function mode workflows may remain for compatibility, but new work
should use `FloquetBasis`.

## HEOM

Import from the current namespace:

```python
from qutip.solver.heom import DrudeLorentzBath, HEOMSolver
```

The legacy QuTiP 4 nonmarkov HEOM namespace is stale.

Example:

```python
import numpy as np
from qutip import basis, sigmax, sigmaz
from qutip.solver.heom import DrudeLorentzBath, HEOMSolver

H_system = 0.5 * sigmaz()
rho0 = basis(2, 0).proj()

bath = DrudeLorentzBath(
    sigmax(),
    lam=0.05,
    gamma=1.0,
    T=0.5,
    Nk=3,
)
solver = HEOMSolver(
    H_system,
    bath,
    max_depth=4,
    options={
        "atol": 1e-10,
        "rtol": 1e-8,
        "store_states": True,
        "store_ados": False,
        "progress_bar": "",
    },
)
result = solver.run(rho0, np.linspace(0.0, 10.0, 201))
reduced_states = result.states
```

For arbitrary exponential expansions, the full current constructor is:

```text
BosonicBath(Q, ck_real, vk_real, ck_imag, vk_imag,
             combine=True, tag=None)
```

Do not omit the imaginary coefficient/frequency lists; use empty lists only
when the modeled correlation genuinely has no imaginary expansion.

HEOM convergence requires independent sweeps of:

- hierarchy `max_depth`;
- bath expansion count (`Nk` or fitted exponent count);
- Matsubara versus Padé/environment approximation;
- ODE tolerances/integrator;
- system Hilbert truncation;
- time grid and duration.

Record \(\lambda\), cutoff, temperature, and all energies in one consistent
\(\hbar=k_B=1\) unit convention if that convention is used.

`result.states` are reduced system states. Set `store_ados=True` only when the
full auxiliary-density hierarchy is needed; then `result.ado_states` can be
large. A previous final ADO state may initialize a continuation only when its
hierarchy is compatible. QuTiP 5.3.1 fixes `final_ado_state` to return
the hierarchy object; it returns `None` when ADOs were not stored. Do not
replace the full hierarchy with `final_state` when continuing correlated dynamics.

HEOM can mix supported bosonic and fermionic baths. Fermionic odd parity is a
special solver construction and must match the initial operator parity.

## Permutational invariance (PIQS)

In QuTiP 5.3, use the `piqs` module exported by `qutip`:

```python
import numpy as np
from qutip import mesolve, piqs

N = 10
Jz = piqs.jspin(N, "z", basis="dicke")
rho0 = piqs.dicke(N, N / 2, N / 2)

ensemble = piqs.Dicke(
    N,
    emission=0.05,
    dephasing=0.01,
    collective_emission=0.02,
)
L = ensemble.liouvillian()
result = mesolve(
    L,
    rho0,
    np.linspace(0.0, 20.0, 201),
    e_ops={"Jz": Jz},
)
```

`piqs.Dicke.pisolve(initial_state, tlist)` is an optimized method only for
diagonal Hamiltonians and diagonal initial density matrices. It takes no
`e_ops`; use the general Liouvillian path for arbitrary observables and
non-diagonal cases.

PIQS exploits permutation symmetry in a Dicke basis. Before using it:

- verify identical two-level constituents and permutation-symmetric dynamics;
- distinguish local and collective rates;
- keep operators and states in the same `dicke` or `uncoupled` basis;
- do not interpret Dicke-basis matrix dimension as \(2^N\);
- compare with a small full-Hilbert-space model where feasible.

`piqs.collapse_uncoupled` returns ordinary collapse operators in a \(2^N\)
space and is only practical for modest `N`.

## Superoperators and channels

Current conversions:

```python
from qutip import (
    kraus_to_super,
    operator_to_vector,
    spre,
    spost,
    to_choi,
    to_kraus,
    to_super,
    vector_to_operator,
)
```

QuTiP column-stacks vectorized operators. Use the conversion functions rather
than manual reshape logic. Check complete positivity and trace preservation in
the intended representation, and preserve structured dimensions.

## QuTiP family packages

Official PyPI metadata snapshot:

| Distribution | Latest published | Release date | Maturity | `Requires-Python` | Required distributions |
|---|---:|---:|---|---|---|
| `qutip` | 5.3.1 | 2026-08-04 | production/stable | `>=3.11` | NumPy `>=1.23.2`; SciPy `>=1.9.2` except `1.16.0`/`1.17.0`; `packaging` |
| `qutip-qip` | 0.4.2 | 2026-06-23 | production/stable | not declared | NumPy `>=1.16.6`; SciPy `>=1.0`; QuTiP `>=4.6`; `packaging` |
| `qutip-qtrl` | 0.2.0 | 2026-06-23 | pre-alpha classifier | not declared | NumPy `>=1.19`; SciPy `>=1.0`; QuTiP `>=5.0.1`; `packaging` |
| `qutip-jax` | 0.1.1 | 2025-05-29 | pre-alpha classifier | not declared | QuTiP `>=5.1.0`; JAX; Diffrax; Equinox |
| `qutip-cupy` | no PyPI project | — | unreleased repository | — | no released metadata |

“Not declared” means the current PyPI `Requires-Python` field is empty, not
that every Python release is supported. Resolve and test each extension in the
same Python 3.11+ environment as QuTiP 5.3. Direct pins do not freeze transitive
JAX/CuPy stacks; use a lockfile for a deployable environment.

### qutip-qip 0.4.2

Status: production/stable on PyPI, released 2026-06-23.

Purpose:

- circuit and gate models;
- `QubitCircuit` unitary circuit simulation;
- `Processor` pulse/noise/open-system device simulation.

Migration boundary:

```python
from qutip_qip.circuit import QubitCircuit
```

Do not import `qutip.qip` in QuTiP 5 code. This package is a local simulator,
not a hardware provider or execution service.

### qutip-qtrl 0.2.0

Status: latest published release 2026-06-23; PyPI classifier is pre-alpha.

Purpose: quantum optimal control with GRAPE and CRAB, emphasizing integration
with QuTiP physics models.

Migration boundary:

```python
from qutip_qtrl import pulseoptim
```

It replaces the old `qutip.control` import. It is **not** a trajectory viewer.
For unitary control use `pulseoptim.optimize_pulse_unitary(H_d, H_c, U_0,
U_targ, num_tslots=..., evo_time=...)`. The Hamiltonian per slot is
`H_d + sum(amplitude[j] * H_c[j])`; no implicit `2*pi` conversion is added.
With `H_c=[sigmax()/2]`, a constant angular amplitude `omega` rotates by
`omega * evo_time`. Recompute the ordered product of slot propagators from
`result.final_amps` and `np.diff(result.time)`, and compare it with
`result.evo_full_final`. The equal-slot shortcut constructs float32 durations
in 0.2.0, so replaying a fresh `evo_time / num_tslots` can differ. Supply an
explicit float64 `tau` array when that precision matters. A PSU
objective ignores global phase. Specify `max_iter`, `max_wall_time`, amplitude
bounds and an intentional initial pulse; `seeds=` is not an optimizer argument.
Random pulse initialization uses NumPy RNG state in this release.

Optimization success does not establish robustness: report bounds, objective,
gradient/termination status, seeds, discretization, and validation under model
uncertainty.

### qutip-jax 0.1.1

Status: latest published release 2025-05-29; explicitly pre-alpha and described
as not ready for production use.

Purpose: a JAX linear-algebra data backend for GPU execution and automatic
differentiation. It depends on QuTiP 5.1 or newer plus JAX, Diffrax, and Equinox.

Importing `qutip_jax` registers `Qobj.to("jax")`, `"jaxdia"`, and the
`"diffrax"` integrator. Select those explicitly; installing it alone does not
move an ordinary solver to GPU. Avoid process-wide `set_as_default()` in
shared applications. Diffrax controls tolerances through a
`diffrax.PIDController(atol=..., rtol=...)` passed as
`options["stepsize_controller"]`, rather than ordinary solver `atol`/`rtol`.

CPU smoke tests used JAX/JAXlib 0.11.2, Diffrax 0.7.2 and Equinox 0.13.8.
That is a tested snapshot, not compatibility with every future release or
with another package's JAX pin. Check `jax_enable_x64`, actual device, JIT and
gradients for the required operations against the native backend. GPU,
MPI, and large-system scaling were not tested. Diffrax can emit its upstream
complex-dtype warning; a small CPU agreement test does not establish every
complex solve or derivative as correct.

### qutip-cupy

The repository belongs to the QuTiP GitHub organization and implements a CuPy
data backend, but:

- PyPI returns no `qutip-cupy` project;
- the repository README says it is not officially released;
- the repository's installation text targets development-era QuTiP and is not
  a reproducible 5.3 release recipe.

Do not recommend it as a stable extension. If a user explicitly accepts an
experimental source build, isolate and audit that separately rather than adding
it to this pinned skill snapshot.

## Parallel and performance boundaries

- `mcsolve`/stochastic solvers expose `map`, `num_cpus`, and related options.
  Parallelism changes scheduling and cost, not the required trajectory
  convergence.
- `parallel_map` executes Python callables. Use only trusted, statically defined
  local functions and bounded task lists.
- Sparse matrices help only when operations preserve sparsity.
- Large HEOM, Liouvillian, dense diagonalization, and PIQS/full-space conversions
  can grow rapidly. Estimate dimensions and memory before construction.
- QuTiP 5.3's `matrix_form` option for `mesolve` and new Krylov density-matrix
  support are performance choices that require output equivalence tests.

## Sources (verified 2026-10-01)

- [Bloch-Redfield guide](https://qutip.readthedocs.io/en/stable/guide/dynamics/dynamics-bloch-redfield.html)
- [Stochastic solver guide](https://qutip.readthedocs.io/en/stable/guide/dynamics/dynamics-stochastic.html)
- [Floquet API](https://qutip.readthedocs.io/en/stable/apidoc/solver.html#floquet-states-and-floquet-markov-master-equation)
- [HEOM API](https://qutip.readthedocs.io/en/stable/apidoc/heom.html)
- [PIQS API](https://qutip.readthedocs.io/en/stable/apidoc/piqs.html)
- [QuTiP 5.3.1 release](https://github.com/qutip/qutip/releases/tag/v5.3.1)
- [qutip-qip 0.4.2](https://pypi.org/project/qutip-qip/)
- [QIP circuit and device API](https://qutip-qip.readthedocs.io/en/stable/apidoc/qutip_qip.circuit.html)
- [QTRL 0.2.0 pulse API source](https://github.com/qutip/qutip-qtrl/blob/v0.2.0/src/qutip_qtrl/pulseoptim.py)
- [QTRL 0.2.0 slot construction](https://github.com/qutip/qutip-qtrl/blob/v0.2.0/src/qutip_qtrl/dynamics.py)
- [JAX solver guide](https://qutip-jax.readthedocs.io/en/latest/solver.html)
- [JAX 0.1.1 integrator source](https://github.com/qutip/qutip-jax/blob/v0.1.1/src/qutip_jax/ode.py)
- [qutip-qtrl 0.2.0](https://pypi.org/project/qutip-qtrl/)
- [qutip-jax 0.1.1](https://pypi.org/project/qutip-jax/)
- [official qutip-cupy repository](https://github.com/qutip/qutip-cupy)
