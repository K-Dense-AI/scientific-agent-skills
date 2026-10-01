# Optimization and objective conventions

Targets PennyLane 0.45.1. Each block is self-contained and exercised numerically.

## Gradients before optimization

```python
import pennylane as qml
from pennylane import numpy as np

dev = qml.device("default.qubit", wires=1)
def quantum_function(x):
    qml.RY(x, 0)
    return qml.expval(qml.Z(0))
x = np.array(0.4, requires_grad=True)
for method in ["backprop", "parameter-shift", "adjoint", "finite-diff"]:
    circuit = qml.QNode(quantum_function, dev, diff_method=method)
    assert np.allclose(qml.grad(circuit)(x), -np.sin(x), atol=1e-6)
second_order = qml.QNode(quantum_function, dev, diff_method="parameter-shift", max_diff=2)
assert np.allclose(qml.jacobian(qml.grad(second_order))(x), -np.cos(x))
```

Backprop/adjoint require supporting simulators and compatible measurements;
finite-shot gradients typically use parameter-shift or stochastic estimates.
A parameter-shift gradient's circuit count depends on generators, decomposition,
measurements and batching; do not assume exactly two circuits for every parameter.
`max_diff=2` enables the higher-order derivative path above.

Use the optimizer from the chosen interface. PennyLane's
`GradientDescentOptimizer`, `AdamOptimizer`, `MomentumOptimizer`,
`NesterovMomentumOptimizer`, `AdagradOptimizer` and `RMSPropOptimizer` work with
Autograd arrays. Torch uses `torch.optim`; JAX uses its own updates or Optax.
`step_and_cost` gives the **old** cost and **new** parameters. Recompute final cost.

## SPSA and quantum natural gradient

```python
import pennylane as qml
from pennylane import numpy as np

np.random.seed(19)
dev = qml.device("default.qubit", wires=1)
@qml.qnode(dev)
def cost(x):
    qml.RY(x[0], 0)
    return qml.expval(qml.Z(0))
x = np.array([0.5], requires_grad=True)
spsa = qml.SPSAOptimizer(maxiter=80, a=0.3, c=0.1)
for _ in range(80):
    x = spsa.step(cost, x)
assert cost(x) < cost(np.array([0.5], requires_grad=True))

qng = qml.QNGOptimizer(stepsize=0.1, approx="block-diag", lam=0.01)
y = np.array([0.5], requires_grad=True)
y = qng.step(cost, y)
assert cost(y) < cost(np.array([0.5], requires_grad=True))
```

SPSA has `step`/`step_and_cost`, not `minimize`. Its optimizer estimates gradients
itself; setting the QNode to `diff_method='spsa'` as well is unnecessary here.
QNG needs a compatible QNode/metric; regularization handles near-singularity but
changes the update. Full `qml.metric_tensor` can need an auxiliary wire;
block-diagonal approximations have different cost/geometry.
`QNSPSAOptimizer` is a stochastic natural-gradient approximation, not quantum
analytic descent. `RotosolveOptimizer` needs per-argument frequency information
(`nums_frequency` or `spectra`) and is not a universal drop-in optimizer.

## MaxCut: minimize negative cut size

```python
import pennylane as qml
from pennylane import numpy as np
import networkx as nx

graph = nx.cycle_graph(3)
cost_h, mixer_h = qml.qaoa.maxcut(graph)
dev = qml.device("default.qubit", wires=list(graph.nodes))
@qml.qnode(dev)
def qaoa_energy(params):
    for wire in graph.nodes:
        qml.Hadamard(wire)
    for gamma, beta in params:
        qml.qaoa.cost_layer(gamma, cost_h)
        qml.qaoa.mixer_layer(beta, mixer_h)
    return qml.expval(cost_h)

params = np.array([[0.3, 0.2]], requires_grad=True)
initial_energy = float(qaoa_energy(params))
opt = qml.AdamOptimizer(stepsize=0.1)
for _ in range(80):
    params = opt.step(qaoa_energy, params)
final_energy = float(qaoa_energy(params))
assert final_energy < initial_energy
assert final_energy >= -2.0 - 1e-8
assert -final_energy > 1.99
```

`maxcut(graph)` has no `constrained` keyword. Its Hamiltonian is
`sum((Zi Zj - I)/2)`, so each cut edge contributes **-1**. Negating this objective
before minimizing favors the wrong answer. The measured mean cut score is not
the best sampled bit string; evaluate each bit string with the classical graph
objective, record sample frequencies, and compare with exact small instances.
Node labels determine wires. Weighted or constrained problems require a matching
cost construction; do not assume unweighted MaxCut reads edge weights.

## QUBO: include linear terms, offset and both matrix triangles

For the declared convention `f(x) = x.T @ Q @ x`, with binary `x`, substitute
`x_i=(I-Z_i)/2`. A symmetric matrix includes off-diagonal contributions twice.
Keep the constant to reproduce absolute objectives.

```python
import itertools
import pennylane as qml
import numpy as np

def qubo_hamiltonian(Q):
    Q = np.asarray(Q, dtype=float)
    if Q.ndim != 2 or Q.shape[0] != Q.shape[1] or not len(Q) or not np.isfinite(Q).all():
        raise ValueError("Q must be a nonempty finite square real matrix")
    n = len(Q)
    offset = np.trace(Q) / 2
    linear = -np.diag(Q).copy() / 2
    coeffs, observables = [], []
    for i in range(n):
        for j in range(i + 1, n):
            pair = Q[i, j] + Q[j, i]
            offset += pair / 4
            linear[i] -= pair / 4
            linear[j] -= pair / 4
            coeffs.append(pair / 4)
            observables.append(qml.Z(i) @ qml.Z(j))
    coeffs.extend(linear)
    observables.extend(qml.Z(i) for i in range(n))
    coeffs.append(offset)
    observables.append(qml.I(0))
    return qml.Hamiltonian(coeffs, observables)

Q = np.array([[1.0, -2.0], [-2.0, 1.0]])
H = qubo_hamiltonian(Q)
expected = [np.asarray(x) @ Q @ np.asarray(x) for x in itertools.product([0, 1], repeat=2)]
assert np.allclose(np.diag(qml.matrix(H, wire_order=[0, 1])), expected)
```

Use this diagonal `H` with `qml.qaoa.cost_layer`, an X mixer and the same minimization
convention. For a polynomial written with each `i<j` term only once, convert it
to the stated matrix convention first. Enumerate small problems before training.

## Training and scientific diagnostics

Keep optimizer state between batches/epochs; recreating Adam resets its moments.
Compute validation loss on held-out data and retain the best parameters. Monitor
finite loss, gradient norm, objective improvement and several seeded restarts.
For barren-plateau studies, estimate each parameter's gradient distribution across
independent initializations and system sizes; variance across different parameters
at one initialization plus a universal threshold is not evidence of exponential
concentration. Compare analytic and finite-shot gradients to separate shot noise.

## Sources

- [Gradient interfaces](https://docs.pennylane.ai/en/stable/introduction/interfaces.html)
- [SPSAOptimizer](https://docs.pennylane.ai/en/stable/code/api/pennylane.SPSAOptimizer.html)
- [QNGOptimizer](https://docs.pennylane.ai/en/stable/code/api/pennylane.QNGOptimizer.html)
- [RotosolveOptimizer](https://docs.pennylane.ai/en/stable/code/api/pennylane.RotosolveOptimizer.html)
- [MaxCut](https://docs.pennylane.ai/en/stable/code/api/pennylane.qaoa.cost.maxcut.html)
