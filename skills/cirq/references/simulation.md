# Simulation in Cirq

These examples target Cirq 1.7.0. Run the blocks in order. Local simulations need
no provider credentials. Keep preparation circuits separate from measurement
circuits so a sampled collapse is not mistaken for an unmeasured final state.

## State vectors, density matrices, and samples

```python
import cirq
import numpy as np
import sympy

qubits = list(cirq.LineQubit.range(2))
q0, q1 = qubits
preparation = cirq.Circuit(cirq.H(q0), cirq.CNOT(q0, q1))
measured = preparation + cirq.Circuit(cirq.measure(*qubits, key="result"))
simulator = cirq.Simulator(seed=42, dtype=np.complex128)

state = simulator.simulate(preparation, qubit_order=qubits).final_state_vector
np.testing.assert_allclose(np.abs(state)**2, [0.5, 0, 0, 0.5])
result = simulator.run(measured, repetitions=1000)
print(result.histogram(key="result"))  # only 0 (00) and 3 (11)
assert result.measurements["result"].shape == (1000, 2)

density_sim = cirq.DensityMatrixSimulator(dtype=np.complex128, seed=42)
rho = density_sim.simulate(preparation, qubit_order=qubits).final_density_matrix
np.testing.assert_allclose(rho, np.outer(state, state.conj()))
```

`run` returns sampled measurement data. `simulate` returns the final quantum state;
if the circuit contains measurements, it simulates their collapse. To obtain an
ensemble state after unobserved measurements, use `cirq.dephase_measurements`
and a density matrix simulator (classical feedback requires separate handling).
Histogram integers are big-endian in the measurement's qubit argument order.

## Expectation values and reduced states

```python
observable = cirq.Z(q0) * cirq.Z(q1)
expectation = simulator.simulate_expectation_values(
    preparation, observables=[observable], qubit_order=qubits
)[0]
assert np.isclose(expectation, 1)

# Reduced state of q0 from a pure state, in the explicit order above.
reduced = cirq.density_matrix_from_state_vector(state, indices=[0], qid_shape=(2, 2))
np.testing.assert_allclose(reduced, np.eye(2) / 2)

# partial_trace expects a tensor with one ket and one bra axis per subsystem.
reduced_from_rho = cirq.partial_trace(rho.reshape(2, 2, 2, 2), keep_indices=[0])
np.testing.assert_allclose(reduced_from_rho, reduced)
```

Only drop **terminal** measurements when computing pre-measurement observables.
Removing mid-circuit measurements changes the computation. A `Simulator` result
has `final_state_vector`, whereas a `DensityMatrixSimulator` result has
`final_density_matrix`; do not mix these result interfaces.

## Parameter sweeps

```python
theta, phi = sympy.symbols("theta phi")
parameterized = cirq.Circuit(
    cirq.ry(theta)(q0), cirq.rx(phi)(q1),
    cirq.measure(q0, q1, key="result"),
)
product_sweep = cirq.Product(
    cirq.Linspace("theta", 0, np.pi, 3),
    cirq.Linspace("phi", 0, 2*np.pi, 4),
)
results = simulator.run_sweep(parameterized, params=product_sweep, repetitions=100)
assert len(results) == 12
paired_sweep = cirq.Zip(
    cirq.Linspace("theta", 0, np.pi, 3),
    cirq.Linspace("phi", 0, 2*np.pi, 3),
)
paired_results = simulator.run_sweep(parameterized, params=paired_sweep, repetitions=100)
assert len(paired_results) == 3
```

Sampling requires measurements. For measurement-free circuits use `simulate_sweep`
or `simulate_expectation_values_sweep`. Product sweeps evaluate every combination;
Zip sweeps pair values and stop at the shortest constituent sweep.

## Noisy simulation

```python
noisy = preparation.with_noise(cirq.depolarize(p=0.01))
noisy_rho = density_sim.simulate(noisy, qubit_order=qubits).final_density_matrix
assert np.isclose(np.trace(noisy_rho), 1)
assert np.linalg.eigvalsh(noisy_rho).min() >= -1e-10
noisy_samples = density_sim.run(
    noisy + cirq.Circuit(cirq.measure(*qubits, key="result")), repetitions=1000
)
```

`with_noise(channel)` inserts a constant noise layer on **all system qubits after
each moment**, including idle qubits and measurement moments. It is a toy model,
not automatically a calibrated gate-duration model. See [noise.md](noise.md) for
gate-specific, relaxation, and asymmetric readout examples.

`cirq.Simulator` can sample noisy trajectories for supported channels. Each
trajectory has a pure state; averaging many trajectories approximates the mixed
state. `DensityMatrixSimulator` propagates the ensemble density matrix directly.
The measurement sampling still has finite-shot uncertainty in both cases.

## Moment steps and initial states

```python
for index, step in enumerate(simulator.simulate_moment_steps(preparation, qubit_order=qubits)):
    print(index, step.state_vector())

bell_initial_state = np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)
initial_result = simulator.simulate(
    cirq.Circuit(cirq.I.on_each(*qubits)),
    initial_state=bell_initial_state, qubit_order=qubits,
)
np.testing.assert_allclose(initial_result.final_state_vector, bell_initial_state)
```

## Local Google Quantum Virtual Machine

The released package bundles historical/median calibration data. A QVM emulates
those data, not the currently assigned live processor. No Google Cloud project,
credentials, or hardware submission is needed here. Only simulate the two qubits
used by the circuit; do not initialize the entire device density matrix.

```python
import cirq_google as cg

available = cg.engine.list_virtual_processors()
processor_id = "willow_pink"  # present in Cirq 1.7.0; inspect available before changing
assert processor_id in available
virtual_engine = cg.engine.create_default_noisy_quantum_virtual_machine(
    processor_id, simulator_class=cirq.DensityMatrixSimulator, seed=42,
)
device = virtual_engine.get_processor(processor_id).get_device()
a, b = next(iter(device.metadata.nx_graph.edges))
virtual_circuit = cirq.Circuit(
    cirq.H(a), cirq.CNOT(a, b), cirq.measure(a, b, key="result")
)
compiled = cirq.optimize_for_target_gateset(
    virtual_circuit, gateset=device.metadata.compilation_target_gatesets[0]
)
device.validate_circuit(compiled)
virtual_result = virtual_engine.get_sampler(processor_id).run(compiled, repetitions=100)
```

For direct use of the bundled noise properties:
`cg.engine.load_device_noise_properties(processor_id)` returns the object needed
by `cg.NoiseModelFromGoogleNoiseProperties`. An Engine `DeviceSpecification`
protobuf is **not** a `GoogleNoiseProperties` object. For live calibration, the
conversion also needs valid gate durations; consult the processor-specific noise
documentation before substituting historical values.

## Resource choice and visualization

A dense n-qubit state vector stores `2**n` complex numbers; a density matrix stores
`4**n`. Multiply by `np.dtype(dtype).itemsize` for the array alone, then allow for
scratch memory. Do not promise a qubit limit without checking the machine and
simulator. For Clifford-only circuits use `cirq.CliffordSimulator`:

```python
clifford_result = cirq.CliffordSimulator(seed=42).run(measured, repetitions=100)
assert set(clifford_result.histogram(key="result")) <= {0, 3}
```

Plot state probabilities as `np.abs(state)**2`, or sampled histogram counts,
labeling which quantity is shown. Preserve the qubit order in axis labels and
record seeds, dtype, shot count, package version, and noise parameters.

Sources: [simulation](https://quantumai.google/cirq/simulate/simulation),
[QVM](https://quantumai.google/cirq/simulate/quantum_virtual_machine),
[partial trace](https://quantumai.google/reference/python/cirq/partial_trace),
[noise representation](https://quantumai.google/cirq/noise/representing_noise).
