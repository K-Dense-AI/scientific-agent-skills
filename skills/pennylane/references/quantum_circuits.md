# Quantum circuits

Examples target PennyLane 0.45.1. Each Python block is self-contained and tested.

## Gates, controls and wire labels

`RX`, `RY`, `RZ` take angles in radians. `Rot(phi, theta, omega, wires=...)`
and `U3(theta, phi, delta, wires=...)` have different conventions; inspect their
matrices before substituting. `CNOT`, `CZ`, `SWAP`, `CRX`, `CRY`, `CRZ`,
`IsingXX`, `IsingYY`, `IsingZZ`, `Toffoli` and `MultiRZ` use ordered wire lists.
For a multi-controlled X, `wires` contains all controls followed by the target;
`control_wires=` is not the current constructor.

```python
import pennylane as qml
import numpy as np

dev = qml.device("default.qubit", wires=["a", "b", "target"])
@qml.qnode(dev)
def controlled():
    qml.BasisState(np.array([1, 1, 0]), wires=["a", "b", "target"])
    qml.MultiControlledX(wires=["a", "b", "target"])
    return qml.probs(wires=["a", "b", "target"])
assert np.argmax(controlled()) == 7

def layer(weights, wires):
    for angle, wire in zip(weights, wires, strict=True):
        qml.RY(angle, wires=wire)
    for a, b in zip(wires[:-1], wires[1:]):
        qml.CNOT(wires=[a, b])

@qml.qnode(dev)
def negative_control():
    qml.ctrl(qml.X, control="a", control_values=[0])(wires="target")
    return qml.expval(qml.Z("target"))
assert np.allclose(negative_control(), -1)
```

Do not construct neighbors using `wire + 1`: labels need not be consecutive
integers. Basis encodings require binary entries; amplitude preparation requires
`2**n` amplitudes with nonzero finite norm. `qml.AmplitudeEmbedding(...,
normalize=True)` normalizes amplitudes, but does not make arbitrary feature
preprocessing differentiable.

## Measurement feedback

```python
import pennylane as qml
import numpy as np

dev = qml.device("default.qubit", wires=3)  # one auxiliary wire for deferred measurement
@qml.qnode(dev)
def adaptive():
    qml.Hadamard(0)
    bit = qml.measure(0)
    qml.cond(bit, qml.X)(wires=1)
    return qml.expval(qml.Z(0) @ qml.Z(1))
assert np.allclose(adaptive(), 1.0)
```

A measurement value is symbolic during circuit construction. Use `qml.cond`
(and bitwise `&`, `|`, `~` for combinations), not ordinary `if bit` or `while bit`.
Native one-shot execution, deferred measurements and tree traversal have different
resource costs/support. Check device, shot and differentiation compatibility.
Ordinary Python loops unroll during construction; compiled dynamic loops require
Catalyst's supported control flow. Reset/postselection changes the state and the
effective accepted shot count; report the acceptance rate.

## QFT and inverse

Use the library transform rather than a partial hand-written controlled-RZ
circuit: controlled phase and final wire reversal matter.

```python
import pennylane as qml
import numpy as np

wires = [0, 1, 2]
U = qml.matrix(qml.QFT(wires=wires), wire_order=wires)
indices = np.arange(8)
expected = np.exp(2j * np.pi * np.outer(indices, indices) / 8) / np.sqrt(8)
assert np.allclose(U, expected)
Uinv = qml.matrix(qml.adjoint(qml.QFT)(wires=wires), wire_order=wires)
assert np.allclose(Uinv @ U, np.eye(8))
```

## Inspect and transform

```python
import pennylane as qml
import numpy as np

dev = qml.device("default.qubit", wires=2)
@qml.qnode(dev)
def circuit(x):
    qml.Hadamard(0)
    qml.Hadamard(0)
    qml.RY(x, 0)
    qml.CNOT([0, 1])
    return qml.expval(qml.Z(1))

optimized = qml.transforms.cancel_inverses(circuit)
assert np.allclose(optimized(0.2), circuit(0.2))
print(qml.draw(optimized)(0.2))
spec = qml.specs(optimized, level="device")(0.2)
resources = spec.resources
assert resources.num_gates == 2
assert resources.depth == 2
print(resources.gate_types)

with qml.tape.QuantumTape() as tape:
    qml.Rot(0.1, 0.2, 0.3, wires=0)
    qml.expval(qml.Z(0))
tapes, postprocess = qml.transforms.decompose(tape, gate_set={qml.RZ, qml.RY})
results = qml.execute(tapes, dev)
assert np.allclose(postprocess(results), np.cos(0.2))
```

A tape transform returns `(tapes, postprocessing_fn)`, not a single tape.
`commute_controlled` moves compatible gates through controlled operations; it does
not move measurements to the end. `merge_rotations` combines compatible rotations.
Compare outputs before/after transforms, and record the `qml.specs` level. In
0.45.1 the result is `CircuitSpecs`, with a `SpecsResources` object under
`.resources`; splitting transforms can make `.resources` a list. Dictionary
lookups such as `specs['depth']` and legacy `num_trainable_params` do not apply.
`qml.draw_mpl` additionally needs Matplotlib and returns `(figure, axes)`.

## Sources

- [Operations](https://docs.pennylane.ai/en/stable/code/qml.html)
- [MultiControlledX](https://docs.pennylane.ai/en/stable/code/api/pennylane.MultiControlledX.html)
- [Dynamic circuits](https://docs.pennylane.ai/en/stable/introduction/dynamic_quantum_circuits.html)
- [QFT](https://docs.pennylane.ai/en/stable/code/api/pennylane.QFT.html)
- [Transforms](https://docs.pennylane.ai/en/stable/code/qml_transforms.html)
- [specs](https://docs.pennylane.ai/en/stable/code/api/pennylane.specs.html)
