# QuTiP 5.3 Core Concepts

Research and API verification date: **2026-10-01**. Examples target
`qutip==5.3.1`.

## Units and the equation being solved

QuTiP does not attach physical units. The standard solver equations use
\(\hbar=1\), so a Hamiltonian has angular-frequency units and time has reciprocal
units:

\[
\dot{\rho}=-i[H,\rho]+\sum_k\left(C_k\rho C_k^\dagger
-\tfrac12\{C_k^\dagger C_k,\rho\}\right).
\]

Choose one unit system and state it in reports:

- if time is ns, Hamiltonian coefficients and rates are in ns\(^{-1}\);
- a frequency quoted in cycles/time becomes angular frequency \(2\pi f\);
- temperature in HEOM or thermal spectra must be converted consistently with
  \(k_B=1\) only if that convention was explicitly selected.

Dimensional consistency is a model property, not something QuTiP can infer.

## Qobj structure

`Qobj` stores numerical data plus quantum dimension metadata:

```python
from qutip import Qobj, basis, sigmaz

ket = basis(2, 0)
rho = ket.proj()
H = 0.5 * sigmaz()

assert ket.isket and ket.dims == [[2], [1]]
assert rho.isoper and rho.dims == [[2], [2]]
assert H.isherm
```

Important properties and methods:

| API | Meaning |
|---|---|
| `.dims` | Structured input/output Hilbert spaces |
| `.shape` | Flattened matrix shape |
| `.type` | `ket`, `bra`, `oper`, `super`, `operator-ket`, or `operator-bra` |
| `.isket`, `.isoper`, `.issuper` | Semantic type checks |
| `.isherm`, `.isunitary` | Cached/computed structural properties |
| `.dag()` | Adjoint |
| `.tr()` | Trace |
| `.norm()` | L2 norm for kets by default; trace norm for operators by default |
| `.proj()` | Ket/bra projector |
| `.ptrace(sel)` | Keep selected subsystems and trace out the rest |
| `.full()` | Dense matrix with flattened shape |
| `.full_tensor()` | QuTiP 5.3 dense array reshaped by tensor dimensions |

Construct raw `Qobj` values only when built-in constructors are unsuitable:

```python
from qutip import Qobj

rho = Qobj(
    [[0.75, 0.1], [0.1, 0.25]],
    dims=[[2], [2]],
)
```

Supplying correct matrix shape with incorrect `dims` can invalidate later
tensor, partial-trace, and superoperator operations.

## States and physicality

### Kets

```python
from qutip import basis, coherent

qubit = (basis(2, 0) + basis(2, 1)).unit()
oscillator = coherent(30, 1.5)

assert abs(qubit.norm() - 1.0) < 1e-12
```

### Density matrices

A physical finite-dimensional density matrix is Hermitian, trace one, and
positive semidefinite:

```python
import numpy as np
from qutip import thermal_dm

rho = thermal_dm(20, 0.7)
tol = 1e-10
eigenvalues = np.asarray(rho.eigenenergies(), dtype=float)

assert rho.isherm
assert abs(complex(rho.tr()) - 1.0) < tol
assert eigenvalues.min() >= -tol
```

Use a tolerance tied to solver error and matrix scale. Report the minimum
eigenvalue instead of silently clipping it. If a method such as non-secular
Bloch-Redfield produces material negativity, revisit its physical assumptions.

Common constructors:

```python
from qutip import (
    basis,
    coherent,
    coherent_dm,
    fock,
    fock_dm,
    maximally_mixed_dm,
    thermal_dm,
)

psi_n = fock(16, 3)
rho_n = fock_dm(16, 3)
psi_alpha = coherent(24, 1.2)
rho_alpha = coherent_dm(24, 1.2)
rho_th = thermal_dm(24, 0.5)
rho_mix = maximally_mixed_dm([2, 2])
```

Oscillator constructors use a finite truncation. Sweep the cutoff and monitor
edge population, observables, and state trace. A normalized truncated state is
not by itself evidence that the cutoff is adequate.

## Tensor products and subsystem order

Arguments to `tensor` define subsystem order from left to right:

```python
from qutip import basis, destroy, qeye, sigmaz, tensor

N = 12
psi = tensor(basis(N, 2), basis(2, 0))  # cavity index 0, qubit index 1
a = tensor(destroy(N), qeye(2))
sz = tensor(qeye(N), sigmaz())

assert psi.dims == [[N, 2], [1]]
assert a.dims == [[N, 2], [N, 2]]
assert sz.dims == a.dims
```

`Qobj.ptrace(sel)` keeps `sel`:

```python
rho = psi.proj()
rho_cavity = rho.ptrace(0)
rho_qubit = rho.ptrace(1)
```

The selected subsystems remain in their original order even if `sel` is passed
in another order. Use `permute` when an explicit subsystem reordering is
intended.

For a composite operator with `dims == [[2, 3], [2, 3]]`,
`full_tensor().shape` is `(2, 3, 2, 3)`. Treat this as a useful dimensional
audit, not a replacement for documenting subsystem labels.

## Operators and observables

```python
from qutip import create, destroy, jmat, num, sigmam, sigmap, sigmax, sigmay, sigmaz

N = 20
a = destroy(N)
adag = create(N)
n = num(N)
sx, sy, sz = sigmax(), sigmay(), sigmaz()
sm, sp = sigmam(), sigmap()
Jx = jmat(1, "x")
```

Hamiltonians and ideal observables should be Hermitian within tolerance.
Collapse operators generally need not be Hermitian.

Expectation and variance:

```python
from qutip import expect, variance

mean_n = expect(n, rho)
var_n = variance(n, rho)
```

Do not interpret a visibly non-real expectation of a Hermitian observable as a
physical value; first audit Hermiticity, state validity, dimensions, and solver
accuracy.

## Collapse operators and rate conventions

If a dissipator is written as \(\gamma\,\mathcal{D}[A]\rho\), pass
\(C=\sqrt{\gamma}A\):

```python
import numpy as np
from qutip import sigmam, sigmaz

gamma_down = 0.2
gamma_phi = 0.05  # desired off-diagonal coherence decay
c_ops = [
    np.sqrt(gamma_down) * sigmam(),
    np.sqrt(gamma_phi / 2.0) * sigmaz(),
]
```

The factor for dephasing depends on how a publication defines its dephasing
rate. Derive the matrix-element decay for the chosen dissipator and test it on
a two-level state instead of copying a symbol by name.

For a thermal oscillator with occupation \(n_\mathrm{th}\):

```python
c_ops = [
    np.sqrt(kappa * (n_th + 1.0)) * a,
    np.sqrt(kappa * n_th) * a.dag(),
]
```

Rates must be finite and nonnegative in standard Lindblad form. Time-dependent
rates require extra care: a coefficient multiplies the collapse **amplitude**,
so a target rate \(\gamma(t)\) needs an amplitude proportional to
\(\sqrt{\gamma(t)}\).

## Liouvillians and vectorization

```python
from qutip import liouvillian, operator_to_vector, vector_to_operator

L = liouvillian(H, c_ops)
rho_vec = operator_to_vector(rho)
derivative = L * rho_vec
rho_roundtrip = vector_to_operator(rho_vec)

assert L.issuper
assert (rho_roundtrip - rho).norm() < 1e-12
```

QuTiP uses column-stacked operator vectorization. Use
`operator_to_vector`/`vector_to_operator`; do not reproduce reshape order by
guesswork.

Useful superoperator constructors and conversions include:

```python
from qutip import (
    kraus_to_super,
    spost,
    spre,
    sprepost,
    to_choi,
    to_kraus,
    to_super,
)
```

For a quantum channel, check the intended representation and the map properties
such as complete positivity and trace preservation. QuTiP exposes properties
including `iscp`, `istp`, and `iscptp` on suitable map objects.

## Truncation and basis audits

For every truncated bosonic or spin model:

1. increase each cutoff independently;
2. compare the actual reported observables, not only energies;
3. inspect occupation near the cutoff;
4. recheck all tensor dimensions after changing a cutoff;
5. state whether the model is in a bare, dressed, rotating, Floquet, Dicke, or
   other basis;
6. document every rotating-wave or excitation-number restriction.

An excitation-number-restricted space does not have the same factorization as
the corresponding full tensor space. Do not apply subsystem operations unless
their meaning in the restricted representation is established.

## Local model validation

`../scripts/qobj_model_validator.py` accepts a bounded strict-JSON model made
only of numeric arrays. It rejects URLs, symlinks, duplicate keys, non-finite
numbers, unknown roles, executable coefficients, dimensions whose product
exceeds 64, and incompatible subsystem structures. It checks Hamiltonian and
observable Hermiticity, initial-state norm/trace/positivity, and nonnegative
collapse rates.

It is a preflight audit, not a proof that the physical model is appropriate.

## Sources (verified 2026-10-01)

- [QuTiP 5.3 quantum-object API](https://qutip.readthedocs.io/en/stable/apidoc/quantumobject.html)
- [Tensor-product guide](https://qutip.readthedocs.io/en/stable/guide/guide-tensor.html)
- [QuTiP 5.3.1 release notes](https://github.com/qutip/qutip/releases/tag/v5.3.1)
- [QuTiP 5.3 changelog](https://qutip.readthedocs.io/en/stable/changelog.html)
