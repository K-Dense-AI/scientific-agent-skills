# Advanced features

Targets PennyLane 0.45.1. Core/ML blocks are tested; the Catalyst block is explicitly
illustrative because its native compiler was not executed in this review.

## Templates with valid shapes and reference states

```python
import pennylane as qml
from pennylane import numpy as np

dev = qml.device("default.qubit", wires=4)
initial_shape, layer_shape = qml.SimplifiedTwoDesign.shape(n_layers=2, n_wires=4)
initial = np.zeros(initial_shape, requires_grad=True)
weights = np.ones(layer_shape, requires_grad=True) * 0.1
@qml.qnode(dev)
def two_design(initial, weights):
    qml.SimplifiedTwoDesign(initial, weights, wires=range(4))
    return qml.expval(qml.Z(0))
assert np.isfinite(two_design(initial, weights))

shape = qml.ParticleConservingU1.shape(n_layers=2, n_wires=4)
particle_weights = np.ones(shape, requires_grad=True) * 0.1
@qml.qnode(dev)
def particle_circuit(weights):
    qml.ParticleConservingU1(weights, wires=range(4), init_state=np.array([1, 1, 0, 0]))
    return qml.expval(qml.qchem.particle_number(4))
assert np.allclose(particle_circuit(particle_weights), 2.0)
```

`SimplifiedTwoDesign` takes two differently shaped arrays; slicing a single
homogeneous tensor is not a valid general construction. `StronglyEntanglingLayers`,
`BasicEntanglerLayers` and `RandomLayers` each expose their own `shape` convention.
Random templates have separate structure and parameter seeds. A particle-conserving
ansatz starting in the vacuum remains there; prepare the required occupation.

## Explicit noise and a physical density matrix

```python
import pennylane as qml
import numpy as np

dev = qml.device("default.mixed", wires=1)
def noise_kraus(p):
    if not 0 <= p <= 1:
        raise ValueError("p must lie in [0, 1]")
    return [np.sqrt(1-p)*np.eye(2), np.sqrt(p/3)*qml.matrix(qml.X(0)),
            np.sqrt(p/3)*qml.matrix(qml.Y(0)), np.sqrt(p/3)*qml.matrix(qml.Z(0))]

kraus = noise_kraus(0.15)
assert np.allclose(sum(k.conj().T @ k for k in kraus), np.eye(2))
@qml.qnode(dev)
def noisy():
    qml.Hadamard(0)
    qml.QubitChannel(kraus, wires=0)
    qml.AmplitudeDamping(0.1, wires=0)
    return qml.density_matrix(wires=[0])
rho = noisy()
assert np.allclose(rho, rho.conj().T)
assert np.allclose(np.trace(rho), 1)
assert np.linalg.eigvalsh(rho).min() >= -1e-10
```

`DepolarizingChannel`, `AmplitudeDamping`, `PhaseDamping`, `BitFlip` and `PhaseFlip`
have specific physical meanings and probability conventions. Match them to the
experiment. Adding noise once at the circuit end is not noise after every gate.
Reusable ansatz functions should queue gates, not call nested QNodes. Current noise
insertion/mitigation transforms live in `qml.noise`, not `qml.transforms`. A noise
model or mitigation method needs independent calibration and uncertainty checks.

## Pulse evolution: a Hamiltonian must be evolved

This JAX 0.7.1 example is a **simulated** driven qubit with `hbar=1`, amplitude in
cycles per time unit and duration in matching time units. The implementation
converts amplitude to angular frequency with a factor of `2*pi`. It does not
submit a calibrated hardware pulse.

```python
import pennylane as qml
import jax
import jax.numpy as jnp

jax.config.update("jax_enable_x64", True)
def amplitude(params, time):
    return params[0]  # constant envelope; required callback order is (params, time)
H_drive = qml.pulse.drive(amplitude, phase=0.0, wires=[0])
dev = qml.device("default.qubit", wires=1)
@qml.qnode(dev, interface="jax")
def pulse_state(params):
    qml.evolve(H_drive)([params], t=[0.0, 1.0], atol=1e-9, rtol=1e-9)
    return qml.state()
psi = pulse_state(jnp.array([0.4]))
assert jnp.allclose(jnp.abs(psi)**2, jnp.array([jnp.cos(jnp.pi * 0.4)**2, jnp.sin(jnp.pi * 0.4)**2]), atol=1e-7)
target = jnp.array([0.0, 1.0], dtype=complex)
def infidelity(params):
    return 1 - jnp.abs(jnp.vdot(target, pulse_state(params)))**2
grad = jax.grad(infidelity)(jnp.array([0.4]))
assert jnp.isfinite(grad).all()
```

`qml.pulse.drive(amplitude, phase, wires)` returns a `ParametrizedHamiltonian`.
Its phase-zero one-wire matrix is `pi * amplitude * X`; verify this convention
before comparing a pulse area with a rotation angle. It has neither `freq` nor
`duration` arguments and does not by itself apply a gate.
Carrier-aware `qml.pulse.transmon_drive` is a different Hamiltonian constructor.
Use `qml.evolve` for duration/time integration, preserve callback parameter ordering,
and verify solver tolerance convergence. State fidelity needs a returned state
vector; taking an inner product of a scalar expectation is not fidelity.

## Catalyst compilation (illustrative, not executed)

Catalyst 0.15.0 requires PennyLane/Lightning >=0.45 and exactly JAX/JAXlib 0.7.1.
Install it in a supported platform environment and validate against eager results.
Use compiler-native differentiation/control flow:

```python
# Illustrative: requires the optional native Catalyst compiler.
import pennylane as qml
from catalyst import qjit, grad, for_loop

dev = qml.device("lightning.qubit", wires=1)
@qjit(capture=False)
@qml.qnode(dev)
def compiled(x):
    @for_loop(0, 3, 1)
    def layer(i):
        qml.RY(x, wires=0)
    layer()
    return qml.expval(qml.Z(0))

compiled_gradient = qjit(grad(compiled), capture=False)
# After installation, compare compiled(0.2) to cos(0.6), and its gradient to -3*sin(0.6).
```

Separate first-call compilation from warmed execution when timing. The example uses `capture=False`; with program capture enabled, use the
PennyLane control-flow forms supported by that mode instead. Explicit loop
constructs or supported AutoGraph are needed for dynamic classical control. Do not
wrap Autograd `qml.grad` around an already compiled function and assume portability.

## Three-qubit bit-flip code with two syndrome wires

```python
import pennylane as qml
import numpy as np

dev = qml.device("default.qubit", wires=5)
@qml.qnode(dev)
def recover(error_wire):
    qml.RY(0.7, wires=0)
    qml.CNOT([0, 1])
    qml.CNOT([0, 2])
    if error_wire is not None:  # classical circuit-construction choice
        qml.X(error_wire)
    qml.CNOT([0, 3]); qml.CNOT([1, 3])
    s1 = qml.measure(3)
    qml.CNOT([1, 4]); qml.CNOT([2, 4])
    s2 = qml.measure(4)
    qml.cond(s1 & ~s2, qml.X)(wires=0)
    qml.cond(s1 & s2, qml.X)(wires=1)
    qml.cond(~s1 & s2, qml.X)(wires=2)
    qml.CNOT([0, 2]); qml.CNOT([0, 1])
    return qml.density_matrix(wires=[0])
reference = recover(None)
for wire in range(3):
    assert np.allclose(recover(wire), reference)
```

This corrects a single bit flip under ideal gates/measurements, not phase errors,
multiple errors or a fault-tolerant hardware implementation. Allocate all five
wires. Validate the recovered density matrix, not only one expectation value.

## Resource and performance accounting

Use current `qml.specs(...).resources` at a declared transform level. Simulation
memory formulas count the state only; gradients and intermediate buffers add cost.
Do not turn a guessed per-gate constant into a hardware runtime prediction.
Measure representative inputs, compilation overhead, shot count and device queue
latency separately. Record circuit splitting, gradient evaluations and shot budgets.

## Sources

- [Templates](https://docs.pennylane.ai/en/stable/code/qml_templates.html)
- [pulse.drive and frequency conversion source](https://github.com/PennyLaneAI/pennylane/blob/v0.45.1/pennylane/pulse/hardware_hamiltonian.py)
- [ParametrizedEvolution](https://docs.pennylane.ai/en/stable/code/api/pennylane.pulse.ParametrizedEvolution.html)
- [Noise module](https://docs.pennylane.ai/en/stable/code/qml_noise.html)
- [Catalyst gradients](https://docs.pennylane.ai/projects/catalyst/en/stable/code/api/catalyst.grad.html)
- [Catalyst control-flow source](https://github.com/PennyLaneAI/catalyst/blob/v0.15.0/frontend/catalyst/api_extensions/control_flow.py)
