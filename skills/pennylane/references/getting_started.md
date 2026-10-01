# Getting started with PennyLane 0.45.1

## QNodes and measurements

A quantum function queues operations and returns measurement objects. A QNode
attaches execution and differentiation. This block is self-contained and tested:

```python
import pennylane as qml
from pennylane import numpy as np

dev = qml.device("default.qubit", wires=["a", "b"], seed=42)

def bell_function():
    qml.Hadamard("a")
    qml.CNOT(wires=["a", "b"])
    return qml.probs(wires=["a", "b"])

bell = qml.QNode(bell_function, dev)
assert np.allclose(bell(), [0.5, 0.0, 0.0, 0.5])

@qml.set_shots(100)
@qml.qnode(dev, diff_method=None)
def sample_bell():
    qml.Hadamard("a")
    qml.CNOT(wires=["a", "b"])
    return qml.sample(wires=["a", "b"])

samples = sample_bell()
assert samples.shape == (100, 2)
assert np.all(samples[:, 0] == samples[:, 1])
```

`qml.expval`, `qml.var` and `qml.probs` can use analytic simulation or finite
shots on compatible devices. `qml.sample` and `qml.counts` need finite shots.
`qml.state`/`qml.density_matrix` are simulator diagnostics, not full-state
measurements available directly from hardware. Basis-state/probability order is
lexicographic in the **requested wire order**; preserve it when interpreting bits.

## Differentiable and batched input

Use `pennylane.numpy`, not ordinary NumPy, for Autograd trainability. Parameters
must influence a measured quantity; extra unused parameters have zero gradients.

```python
import pennylane as qml
from pennylane import numpy as np

dev = qml.device("default.qubit", wires=1)

@qml.qnode(dev, interface="autograd", diff_method="backprop")
def rotate(x):
    qml.RY(x, wires=0)
    return qml.expval(qml.Z(0))

x = np.array(0.4, requires_grad=True)
assert np.allclose(qml.grad(rotate)(x), -np.sin(x))
values = rotate(np.array([0.1, 0.2, 0.3], requires_grad=False))
assert np.allclose(values, np.cos([0.1, 0.2, 0.3]))
```

The array above is operator parameter broadcasting. A Python list comprehension
is repeated execution, not vectorization. With vector features, index the final
feature dimension (`inputs[..., i]`) or use an embedding template that handles
batching. JAX `vmap` can express a dataset batch explicitly.

## Random streams and shot uncertainty

A seed reproduces an execution **sequence**, not the same sample every time.
Use independent streams when estimating variability:

```python
import pennylane as qml
import numpy as np

def make_sampler(seed):
    dev = qml.device("default.qubit", wires=1, seed=seed)
    @qml.set_shots(128)
    @qml.qnode(dev, diff_method=None)
    def sample():
        qml.Hadamard(0)
        return qml.sample(qml.Z(0))
    return sample

a, b = make_sampler(12), make_sampler(12)
a1, a2 = a(), a()
b1, b2 = b(), b()
assert np.array_equal(a1, b1)
assert np.array_equal(a2, b2)
```

For independent Pauli outcomes, estimate the expectation's standard error from
sample standard deviation divided by the square root of shots. Correlated device
drift and error mitigation can invalidate this simple model. Report shots and
repetitions, and keep analytic, sampled and noisy estimates distinct.

## Dependencies and device choices

`default.qubit` handles pure states, `default.mixed` density matrices and explicit
noise channels, `lightning.qubit` compiled state-vector simulation. Their useful
sizes depend on RAM, circuit, precision and gradients, not a fixed qubit limit.
A complex128 state alone takes `16 * 2**n` bytes; a density matrix takes
`16 * 4**n`, before work buffers. Measure speed instead of assuming a backend is
always faster. `default.clifford` needs the optional Stim package and is limited
to its documented supported operations/measurements.

## Sources

- [QNode](https://docs.pennylane.ai/en/stable/code/api/pennylane.QNode.html)
- [Measurements](https://docs.pennylane.ai/en/stable/introduction/measurements.html)
- [set_shots](https://docs.pennylane.ai/en/stable/code/api/pennylane.set_shots.html)
- [DefaultQubit](https://docs.pennylane.ai/en/stable/code/api/pennylane.devices.default_qubit.DefaultQubit.html)
