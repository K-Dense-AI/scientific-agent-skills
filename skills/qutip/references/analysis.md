# QuTiP 5.3 Analysis, Steady States, and Spectra

Research and API verification date: **2026-10-01**. Examples target
`qutip==5.3.1`.

## Analysis starts with invariants

For every reported state, record quantitative checks before interpreting an
observable:

```python
import numpy as np

def density_audit(rho, tolerance=1e-9):
    if not rho.isoper:
        raise ValueError("density_audit requires an operator")
    hermitian = bool(rho.isherm)
    eigenvalues = np.linalg.eigvalsh(rho.full()) if hermitian else None
    trace = complex(rho.tr())
    return {
        "is_hermitian": hermitian,
        "trace_error": float(abs(trace - 1.0)),
        "minimum_eigenvalue": float(eigenvalues.min()) if hermitian else None,
        "positive_within_tolerance": hermitian and bool(eigenvalues.min() >= -tolerance),
    }
```

Also check:

- `state.dims` matches every observable and the declared subsystem order;
- ket norm or density-matrix trace stays stable over time;
- Hermitian observables have negligible imaginary expectation;
- populations remain within tolerance of `[0, 1]`;
- symmetry, conserved quantity, or analytic-limit checks hold where applicable;
- numerical tolerance is smaller than the effect being claimed.

Do not repair a state by clipping eigenvalues or renormalizing unless that
post-processing is part of a documented method and its impact is reported.

## Expectations and uncertainty

```python
from qutip import expect, num, variance

n_op = num(N)
mean_n = expect(n_op, rho)
variance_n = variance(n_op, rho)
```

For solver output, dict-form `e_ops` gives named `result.e_data`:

```python
result = mesolve(
    H,
    rho0,
    tlist,
    c_ops=c_ops,
    e_ops={"number": n_op, "energy": H},
)
number_vs_time = result.e_data["number"]
```

For Monte Carlo/stochastic results, report both ensemble means and sampling
uncertainty. `std_expect` is trajectory spread, not automatically the standard
error; a simple independent-trajectory standard error scales as
`std / sqrt(ntraj)`, subject to the solver's sampling design.

## Entropy, purity, and distances

```python
from qutip import entropy_linear, entropy_vn, fidelity, tracedist

von_neumann_nats = entropy_vn(rho)          # default natural-log base
von_neumann_bits = entropy_vn(rho, base=2)
linear_entropy = entropy_linear(rho)
purity = float((rho * rho).tr().real)
state_fidelity = fidelity(rho, sigma)
trace_distance = tracedist(rho, sigma)
```

Always state the logarithm base. QuTiP `fidelity` returns root fidelity
`Tr(sqrt(sqrt(rho) * sigma * sqrt(rho)))`; for two kets this is absolute
overlap. Square it only when the comparison uses the squared convention.

For bipartite entropy:

```python
rho_A = rho_AB.ptrace(0)  # keep subsystem 0
entanglement_entropy = entropy_vn(rho_A, base=2)
```

This is an entanglement entropy only when the global bipartite state and the
chosen measure meet the necessary assumptions. For mixed states, reduced-state
entropy also contains classical mixture.

Common specialized functions include `concurrence`, `negativity`,
`entropy_mutual`, and `partial_transpose`. Verify their supported dimensions and
argument definitions in the current API before applying them.

## Steady-state calculation

Current signature:

```text
steadystate(A, c_ops=[], *, method="direct", solver=None, **kwargs)
```

`A` may be a Hamiltonian or a Liouvillian. Available high-level methods include
`direct`, `eigen`, `svd`, `power`, and `propagator`; linear-system solver choices
are separate.

```python
from qutip import liouvillian, operator_to_vector, steadystate

rho_ss = steadystate(H, c_ops, method="direct")
L = liouvillian(H, c_ops)
residual = (L * operator_to_vector(rho_ss)).norm()
```

Report:

- residual norm and normalization error;
- Hermiticity and minimum eigenvalue;
- method and linear solver;
- matrix/data representation and relevant tolerances;
- whether the zero eigenvalue is unique;
- comparison with long-time evolution from more than one initial state when
  uniqueness matters.

A small residual does not prove uniqueness or physicality. Degenerate steady
spaces require analysis of the Liouvillian nullspace and initial-state
dependence.

The `svd` method is dense and intended for small systems. Sparse/direct methods
can still be memory intensive; monitor fill-in and compare methods on a reduced
model.

For periodically driven systems, a static `steadystate` call is generally not
the desired asymptotic object. Use an appropriate periodic/Floquet approach.
In QuTiP 5.3, `steadystate_fourier` is the current name for the specialized
cosine-driven Fourier solver; `steadystate_floquet` is deprecated.

## Two-time correlations

Current stationary/transient two-operator API:

```python
from qutip import correlation_2op_1t, correlation_2op_2t

corr_1t = correlation_2op_1t(
    H,
    rho0,
    taulist,
    c_ops,
    a_op,
    b_op,
    solver="me",
    options={"atol": 1e-10, "rtol": 1e-8},
)

corr_2t = correlation_2op_2t(
    H,
    rho0,
    tlist,
    taulist,
    c_ops,
    a_op,
    b_op,
)
```

For `correlation_2op_1t`, the quantity is ordered according to the function's
documented \(A(\tau)B(0)\)-style convention. Do not infer operator order from a
variable name.

Passing `state0=None` requests a steady-state initial condition only for
supported constant systems with collapse operators. Compute and audit the
steady state explicitly when provenance matters.

Current three-operator entry points include:

```python
from qutip import correlation_3op, correlation_3op_1t, correlation_3op_2t
```

QuTiP 5.3 added `max_t_plus_tau` and mapping controls to selected two-time and
three-operator routines. The old `correlation_4op_1t` recipe is not a current
public API; express a four-operator quantity through the documented
three-operator interfaces when mathematically appropriate, or derive a tested
regression workflow.

Correlation checks:

- operator ordering and adjoints;
- transient versus stationary definition;
- normalized versus unnormalized coherence;
- regression-theorem assumptions;
- convergence of both `tlist` and `taulist`;
- tail decay before finite-window transforms.

## Direct stationary spectrum

Current signature:

```text
spectrum(H, wlist, c_ops, a_op, b_op, solver="es")
```

```python
import numpy as np
from qutip import spectrum

wlist = np.linspace(-5.0, 5.0, 1001)
S = spectrum(H, wlist, c_ops, a_op, b_op, solver="es")
```

The function computes the Fourier transform of a **steady-state** correlation.
Supported solver strategies include exponential-series (`"es"`),
pseudo-inverse (`"pi"`), and generic linear solve (`"solve"`).

QuTiP 5 removed public `spectrum_ss` and `spectrum_pi`. Select the strategy with
the `solver` argument to `spectrum`; do not call the removed functions.

Audit:

- stationarity and steady-state uniqueness;
- angular-frequency units;
- operator order;
- whether the spectrum is symmetrized, one-sided, or normally ordered;
- negative-frequency interpretation and thermal detailed balance;
- frequency window/resolution;
- convergence across solver strategies near singular points.

## FFT of a sampled correlation

Current signature:

```text
spectrum_correlation_fft(tlist, y, inverse=False)
```

```python
from qutip import spectrum_correlation_fft

frequencies, spectrum_values = spectrum_correlation_fft(taulist, corr)
```

Before trusting peaks:

1. require a uniform, strictly increasing `taulist`;
2. verify the correlation has decayed at the end of the window;
3. double the time window to test frequency resolution;
4. halve the timestep to test aliasing and high-frequency content;
5. compare window functions and disclose any window applied outside QuTiP;
6. check forward/inverse sign and normalization conventions against an analytic
   signal;
7. avoid interpreting zero-padding as additional physical resolution.

Use a direct `spectrum` calculation as a cross-check when its steady-state
assumptions apply.

## Liouvillian and eigenvalue diagnostics

```python
eigenvalues = L.eigenenergies()
gap_candidates = sorted(
    (-value.real for value in eigenvalues if value.real < -1e-12)
)
```

Liouvillian spectra are non-Hermitian in general. Eigenvalue conditioning,
degeneracy, and sparse solver targeting can make naive sorting misleading.
Verify left/right eigenvector conventions and residuals before interpreting a
spectral gap.

For Hamiltonians:

```python
energies, states = H.eigenstates()
ground_energy, ground_state = H.groundstate()
```

Track basis and units, handle degeneracy explicitly, and sweep truncation before
claiming spectral convergence.

## Convergence matrix

Vary one numerical control at a time, then perform selected joint checks:

| Control | Typical comparison |
|---|---|
| Hilbert cutoff | observables and boundary occupation |
| output grid | interpolated trace/peak/FFT quantities |
| `atol`, `rtol` | endpoint and maximum trajectory differences |
| integrator | representative observable and invariant differences |
| simulation duration | steady-state distance and correlation tail |
| frequency range/spacing | peak location, area, and edge sensitivity |
| trajectories | mean, uncertainty, and seed sensitivity |
| `sec_cutoff` | positivity and observable stability |
| HEOM depth/exponents | reduced state and target observable |

Define acceptance thresholds before looking at the final comparison. Report
absolute and relative differences and handle near-zero denominators explicitly.

## Portable result audit

`../scripts/result_audit.py` reads only bounded strict JSON. It checks schema,
version, finite values, monotonic time grids, population bounds, analytic
reference error when available, convergence deltas, and whether assumptions,
seeds, and solver stats were recorded. It does not load QuTiP result files or
other Python-object serialization. Its pass status means report consistency,
not numerical convergence or scientific validity; separately inspect analytic
error, invariant checks, and the sweep acceptance status.

`../scripts/steady_state_spectrum_planner.py` produces a bounded plan for
steady-state and direct/FFT spectrum checks without running a model.

## Sources (verified 2026-10-01)

- [Solver, correlation, spectrum, and steady-state API](https://qutip.readthedocs.io/en/stable/apidoc/solver.html)
- [Steady-state guide](https://qutip.readthedocs.io/en/stable/guide/guide-steady.html)
- [Correlation guide](https://qutip.readthedocs.io/en/stable/guide/guide-correlation.html)
- [Quantum-object API](https://qutip.readthedocs.io/en/stable/apidoc/quantumobject.html)
- [QuTiP 5.3.1 release notes](https://github.com/qutip/qutip/releases/tag/v5.3.1)
- [QuTiP 5 changelog](https://qutip.readthedocs.io/en/stable/changelog.html)
