# Running quantum experiments

These examples target Cirq 1.7.0 and small local circuits. Keep circuit generation,
execution, and analysis separate. Record the question, observable, units, qubit
order, seed, shot count, package version, parameters, and calibration provenance
before interpreting an optimizer or benchmark result.

## Sweeps and reproducible data collection

```python
import cirq
import numpy as np
import sympy
import scipy.optimize
import networkx as nx

q0, q1 = qubits = list(cirq.LineQubit.range(2))
theta, phi = sympy.symbols("theta phi")
circuit = cirq.Circuit(
    cirq.ry(theta)(q0), cirq.rx(phi)(q1), cirq.CNOT(q0, q1),
    cirq.measure(*qubits, key="result"),
)
sweep = cirq.Product(cirq.Linspace("theta", 0, np.pi, 3),
                     cirq.Linspace("phi", 0, np.pi, 3))
sampler = cirq.Simulator(seed=42)
results = sampler.run_sweep(circuit, params=sweep, repetitions=100)
# Cirq JSON preserves result measurement arrays and ParamResolvers.
archive = cirq.to_json({"circuit": circuit, "results": results,
                        "qubit_order": qubits, "cirq_version": cirq.__version__})
restored = cirq.read_json(json_text=archive)
assert len(restored["results"]) == 9
```

Write the archive to a chosen output path after the experiment; retain raw data
alongside summaries. CSV cells containing a printed Counter are not a robust
lossless result format. For shot estimates include binomial/multinomial sampling
uncertainty and independent repeats when drift or optimizer noise matters.

## VQE with explicit observable ordering

A local state-vector expectation is exact up to numerical precision and does not
include finite-shot or hardware error. This is a **toy Pauli Hamiltonian**, not
an H2 electronic-structure calculation or a UCC chemistry ansatz.

```python
def toy_ansatz(params, qubits):
    return cirq.Circuit(cirq.ry(params[0])(qubits[0]),
                        cirq.ry(params[1])(qubits[1]),
                        cirq.CNOT(qubits[0], qubits[1]))

def vqe_experiment(hamiltonian, ansatz_func, initial_params, qubit_order):
    simulator = cirq.Simulator(dtype=np.complex128)
    history = []
    def objective(params):
        preparation = ansatz_func(params)
        if preparation.has_measurements():
            raise ValueError("VQE expectation requires a measurement-free ansatz")
        energy = simulator.simulate_expectation_values(
            preparation, observables=[hamiltonian], qubit_order=qubit_order
        )[0]
        energy = float(np.real(energy))
        history.append({"params": np.array(params, copy=True), "energy": energy})
        return energy
    optimum = scipy.optimize.minimize(
        objective, initial_params, method="COBYLA", options={"maxiter": 100}
    )
    return optimum, history

hamiltonian = cirq.Z(q0) + cirq.Z(q1) + cirq.Z(q0)*cirq.Z(q1)
optimum, history = vqe_experiment(
    hamiltonian, lambda params: toy_ansatz(params, qubits), [0.2, 0.3], qubits
)
exact_ground = np.linalg.eigvalsh(hamiltonian.matrix(qubits=qubits)).min()
assert optimum.fun >= exact_ground - 1e-8
print(optimum.fun, optimum.success, optimum.message)
```

Use the optimizer's `x` and `fun`, not the last history entry, as its returned
optimum. Inspect convergence and multiple starts. For a manually evaluated
`expectation_from_state_vector`, construct `qubit_map` from exactly the
`qubit_order` passed to simulation; `circuit.all_qubits()` is a set. The variational
bound only holds for a valid state and the intended Hamiltonian, not arbitrary
mitigated estimates or an incorrect qubit map.

## QAOA for unweighted MaxCut

Use `C = sum_edges (I-Z_i Z_j)/2` and the convention
`exp(-i gamma C)` followed by `exp(-i beta sum X)`, with angles in **radians**.
Cirq's `ZZPowGate` exponent is a half-turn parameter, so its exponent here is
`-gamma/pi` (up to global phase). Record this sign/unit convention with results.

```python
def qaoa_circuit(graph, params, p_layers, *, measure=True):
    if graph.is_directed() or graph.is_multigraph() or nx.number_of_selfloops(graph):
        raise ValueError("Expected a simple undirected graph without self-loops")
    if p_layers < 1 or len(params) != 2*p_layers:
        raise ValueError("Expected gamma then beta for each layer")
    nodes = list(graph.nodes())
    qubits = list(cirq.LineQubit.range(len(nodes)))
    node_qubit = dict(zip(nodes, qubits))
    circuit = cirq.Circuit(cirq.H.on_each(*qubits))
    for layer in range(p_layers):
        gamma, beta = params[layer], params[p_layers+layer]
        circuit.append(cirq.ZZPowGate(exponent=-gamma/np.pi)(node_qubit[u], node_qubit[v])
                       for u, v in graph.edges())
        circuit.append(cirq.rx(2*beta).on_each(*qubits))
    if measure:
        circuit.append(cirq.measure(*qubits, key="result"))
    return circuit, nodes, qubits

def mean_maxcut(result, graph, nodes):
    columns = {node: i for i, node in enumerate(nodes)}
    bits = result.measurements["result"]
    if bits.shape[1] != len(nodes) or len(bits) == 0:
        raise ValueError("Measurement dimensions do not match the graph")
    cut_per_shot = np.zeros(len(bits))
    for u, v in graph.edges():
        cut_per_shot += bits[:, columns[u]] != bits[:, columns[v]]
    return float(np.mean(cut_per_shot))

graph = nx.Graph([("left", "center"), ("center", "right")])
qaoa, nodes, order = qaoa_circuit(graph, [0.4, 0.2], p_layers=1)
qaoa_result = cirq.Simulator(seed=42).run(qaoa, repetitions=1000)
cut = mean_maxcut(qaoa_result, graph, nodes)
assert 0 <= cut <= graph.number_of_edges()
```

Raw measurement columns avoid accidentally reversing big-endian histogram bits.
Node labels need not be consecutive integers. The example treats every edge as
weight 1; implement both weighted cost evolution and weighted scoring if weights
are scientifically relevant. For optimization minimize `-mean_maxcut(...)` and
validate the chosen parameters on independent shots. A noisy optimizer result
alone does not establish superiority over a classical baseline.

## Quantum phase estimation

This example accepts a one-qubit unitary gate and a one-qubit eigenstate
preparation. Counting qubits are ordered most-significant first; the measured
integer k estimates the eigenphase as `k / 2**n` for eigenvalue `exp(2*pi*i*phase)`.

```python
def qpe_circuit(unitary, eigenstate_prep, n_counting_qubits):
    if n_counting_qubits < 1 or cirq.num_qubits(unitary) != 1 or not cirq.has_unitary(unitary):
        raise ValueError("Expected a one-qubit unitary and positive counting width")
    counting = list(cirq.LineQubit.range(n_counting_qubits))
    target = cirq.LineQubit(n_counting_qubits)
    circuit = cirq.Circuit(eigenstate_prep(target), cirq.H.on_each(*counting))
    for i, control in enumerate(counting):
        power = 2**(n_counting_qubits-1-i)
        circuit.append((unitary**power).on(target).controlled_by(control))
    circuit.append(cirq.qft(*counting, inverse=True))
    circuit.append(cirq.measure(*counting, key="phase"))
    return circuit

phase_circuit = qpe_circuit(cirq.ZPowGate(exponent=0.75), cirq.X, 3)
phase_result = cirq.Simulator(seed=42).run(phase_circuit, repetitions=100)
assert phase_result.histogram(key="phase") == {3: 100}  # phase = 3/8
```

If the input is a superposition of eigenstates, outcomes follow their weights;
nonrepresentable phases spread across nearby bins. Test these cases before using
phase estimation on a scientific Hamiltonian. The short example does not supply
Hamiltonian simulation or arbitrary multi-qubit controlled powers.

## Expectation values and fidelity

```python
def calculate_expectation_value(circuit, observable, simulator, qubit_order):
    if not circuit.are_all_measurements_terminal():
        raise ValueError("Cannot remove mid-circuit measurements for this observable")
    preparation = cirq.drop_terminal_measurements(circuit)
    return float(np.real(simulator.simulate_expectation_values(
        preparation, observables=[observable], qubit_order=qubit_order
    )[0]))

def classical_distribution_fidelity(counts1, counts2):
    total1, total2 = sum(counts1.values()), sum(counts2.values())
    if total1 <= 0 or total2 <= 0:
        raise ValueError("Expected nonempty histograms")
    states = set(counts1) | set(counts2)
    return float(sum(np.sqrt(counts1.get(s, 0)/total1 * counts2.get(s, 0)/total2)
                     for s in states)**2)

bell_plus = np.array([1, 0, 0, 1]) / np.sqrt(2)
bell_minus = np.array([1, 0, 0, -1]) / np.sqrt(2)
assert np.isclose(cirq.fidelity(bell_plus, bell_minus), 0)
assert classical_distribution_fidelity({0: 50, 3: 50}, {0: 50, 3: 50}) == 1
```

Identical measurement histograms in one basis do not establish state fidelity or
process fidelity. Quantum state/process estimation needs sufficient measurement
settings and assumptions. The example above has orthogonal states but identical
computational-basis histograms. Plot convergence with evaluation index, and
landscapes with axes matching the parameter-array shape and units.

## ReCirq and parallel execution

[ReCirq](https://github.com/quantumlib/ReCirq) is a collection of research
applications/experiments, not a universal base class with a mandated project
layout. Pick the relevant upstream experiment and inspect its own dependencies
and data schemas; no ReCirq package environment was executed in this review.

A useful project layout separates task descriptions (immutable parameters and
seeds), circuit generation, execution, persisted results, and analysis. On macOS
or other spawn-based multiprocessing environments, put worker functions at module
scope and call pools under `if __name__ == "__main__":`. Give each worker its own
simulator and distinct reproducible seed; do not copy a seeded sampler into every
worker and count duplicated random streams as independent experiments. Hardware
clients require provider-specific concurrency limits and durable job tracking.

Sources: [parameter sweeps](https://quantumai.google/cirq/simulate/params),
[expectation values](https://quantumai.google/reference/python/cirq/Simulator),
[QFT](https://quantumai.google/reference/python/cirq/qft),
[quantum fidelity](https://quantumai.google/reference/python/cirq/fidelity),
[ReCirq repository](https://github.com/quantumlib/ReCirq).
