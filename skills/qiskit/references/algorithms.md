# Algorithms, Addons, and Application Packages

The core `qiskit` distribution provides circuits, operators, primitives, synthesis, transpilation, and quantum-information tools. High-level algorithms and domain applications live in separate packages.

## Verified Package Matrix

Checked on **2026-07-23**:

| Package | Version | Primary role |
|---|---:|---|
| `qiskit-algorithms` | 0.4.0 | VQE, QAOA, Grover, phase estimation, eigensolvers, optimizers |
| `qiskit-nature` | 0.8.0 | Electronic structure, second quantization, mappers |
| `qiskit-nature-pyscf` | 0.4.0 | PySCF electronic-structure driver integration |
| `qiskit-machine-learning` | 0.9.0 | Kernels, QNNs, classifiers/regressors, Torch connector |
| `qiskit-optimization` | 0.7.0 | Quadratic programs, converters, quantum optimization wrappers |
| `qiskit-addon-cutting` | 0.10.0 | Circuit and operator cutting |
| `qiskit-addon-sqd` | 0.12.1 | Sample-based quantum diagonalization |
| `qiskit-addon-obp` | 0.3.0 | Operator backpropagation |
| `qiskit-addon-mpf` | 0.3.0 | Multi-product formulas |
| `qiskit-addon-aqc-tensor` | 0.3.1 | Approximate quantum compilation with tensor networks |

Install exact pins together in a fresh environment:

```bash
uv pip install \
  "qiskit==2.5.0" \
  "qiskit-algorithms==0.4.0" \
  "qiskit-optimization==0.7.0"
```

For chemistry:

```bash
uv pip install \
  "qiskit==2.5.0" \
  "qiskit-algorithms==0.4.0" \
  "qiskit-nature==0.8.0" \
  "qiskit-nature-pyscf==0.4.0"
```

Resolve application packages together; their Qiskit compatibility windows can differ.

## Decide Between Manual and Library Implementations

Use a manual circuit when:

- teaching or inspecting a small algorithm,
- testing a new circuit construction,
- controlling every primitive PUB and compilation step,
- avoiding an application package dependency.

Use an application package when:

- it provides tested problem transformations,
- the result object and domain post-processing are valuable,
- the implementation accepts current V2 primitives,
- its release supports the installed Qiskit version.

Do not copy a pre-1.0 algorithm tutorial without checking constructors and primitive requirements.

## VQE with Qiskit Algorithms 0.4

This verified local example uses the V2 `StatevectorEstimator`:

```python
from qiskit.circuit.library import efficient_su2
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp
from qiskit_algorithms import VQE
from qiskit_algorithms.optimizers import SLSQP

hamiltonian = SparsePauliOp.from_list(
    [
        ("ZI", 1.0),
        ("IZ", 1.0),
        ("XX", 0.2),
    ]
)
ansatz = efficient_su2(
    num_qubits=2,
    reps=1,
    entanglement="linear",
)

vqe = VQE(
    estimator=StatevectorEstimator(),
    ansatz=ansatz,
    optimizer=SLSQP(maxiter=100),
    initial_point=[0.0] * ansatz.num_parameters,
)
result = vqe.compute_minimum_eigenvalue(hamiltonian)
print(float(result.eigenvalue.real))
```

For hardware:

1. Use a Runtime `EstimatorV2`.
2. Provide a transpiler adapter or manage the parameterized ISA circuit explicitly.
3. Bound optimizer iterations and requested precision.
4. Store each job ID and convergence record.

Do not transpile a newly bound circuit from scratch in every cost-function call.

## QAOA and Qiskit Optimization

Model a binary problem with `QuadraticProgram`:

```python
from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

problem = QuadraticProgram("binary_demo")
problem.binary_var("x")
problem.binary_var("y")
problem.maximize(
    linear={"x": 1, "y": 1},
    quadratic={("x", "y"): -2},
)

qaoa = QAOA(
    sampler=StatevectorSampler(seed=5),
    optimizer=COBYLA(maxiter=100),
    reps=1,
)
solver = MinimumEigenOptimizer(qaoa)
result = solver.solve(problem)

print(result.x, result.fval, result.status)
```

Use optimizer objects such as `COBYLA(...)`, not old string-valued optimizer arguments.

Before claiming a quantum result:

- compare with a classical solver for small instances,
- verify variable-to-bitstring ordering,
- report feasibility and objective value,
- separate optimizer stochasticity from quantum sampling,
- quantify total circuit evaluations and shot cost.

## Grover and Phase Estimation

Qiskit Algorithms 0.4 constructors accept V2 Sampler implementations:

```python
from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import Grover, PhaseEstimation

sampler = StatevectorSampler(seed=5)
grover = Grover(sampler=sampler)
phase_estimation = PhaseEstimation(
    num_evaluation_qubits=4,
    sampler=sampler,
)
```

The old `quantum_instance=` argument is not current.

Use `QFTGate` in custom phase-estimation circuits:

```python
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate

inverse_qft = QFTGate(4).inverse()
circuit = QuantumCircuit(4)
circuit.append(inverse_qft, range(4))
```

The `QFT` blueprint class is deprecated and scheduled for removal in Qiskit 3.0.

## Qiskit Nature

Qiskit Nature converts domain problems into second-quantized operators and qubit operators.

```python
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import JordanWignerMapper

driver = PySCFDriver(
    atom="H 0 0 0; H 0 0 0.735",
    basis="sto3g",
    charge=0,
    spin=0,
)
problem = driver.run()

fermionic_hamiltonian = problem.hamiltonian.second_q_op()
mapper = JordanWignerMapper()
qubit_hamiltonian = mapper.map(fermionic_hamiltonian)

print(problem.num_spatial_orbitals)
print(problem.num_particles)
print(qubit_hamiltonian.num_qubits)
```

The PySCF calculation is classical preprocessing. Record:

- geometry and units,
- basis set,
- charge and spin,
- active-space or freeze-core choices,
- mapper and symmetry reductions,
- nuclear repulsion energy,
- package versions.

Do not add the nuclear repulsion term twice. Prefer Qiskit Nature's result interpreters for complete energy reporting.

`QubitConverter` is obsolete; use mapper classes directly.

## Qiskit Machine Learning 0.9

Qiskit Machine Learning includes quantum kernels, quantum neural networks, trainable models, and PyTorch integration.

This verified kernel example uses APIs moved into the Machine Learning package:

```python
import numpy as np
from qiskit.circuit.library import zz_feature_map
from qiskit.primitives import StatevectorSampler
from qiskit_machine_learning.kernels import FidelityQuantumKernel
from qiskit_machine_learning.state_fidelities import ComputeUncompute

feature_map = zz_feature_map(
    feature_dimension=2,
    reps=1,
    entanglement="full",
)
sampler = StatevectorSampler(seed=5)
fidelity = ComputeUncompute(sampler=sampler)
kernel = FidelityQuantumKernel(
    fidelity=fidelity,
    feature_map=feature_map,
)

x = np.array([[0.1, 0.2], [0.3, 0.4]])
kernel_matrix = kernel.evaluate(x)
```

Since Qiskit Machine Learning 0.8, relevant gradients, optimizers, state fidelities, and utilities moved from `qiskit_algorithms` into `qiskit_machine_learning`. Check its migration guide before adapting old imports.

For evaluation:

- use a held-out test set,
- compare against matched classical kernels/models,
- avoid generating labels randomly in demonstration code presented as evidence,
- account for kernel-matrix \(O(n^2)\) evaluations,
- separate simulation results from hardware results.

## Qiskit Addons

Addons are modular algorithm-building components aligned with stages of the Qiskit workflow.

| Addon | Typical stage | Use |
|---|---|---|
| Circuit cutting | Optimize / execute / reconstruct | Split large circuits or observables and reconstruct estimates |
| Operator backpropagation (OBP) | Optimize | Move selected circuit operations into observables |
| Multi-product formulas (MPF) | Map / optimize | Approximate time evolution using formula combinations |
| AQC-Tensor | Map / optimize | Approximate target circuits with tensor-network-assisted compilation |
| Sample-based quantum diagonalization (SQD) | Analyze | Combine QPU samples with classical subspace diagonalization |

Example installation:

```bash
uv pip install "qiskit-addon-cutting==0.10.0"
uv pip install "qiskit-addon-sqd==0.12.1"
uv pip install "qiskit-addon-obp==0.3.0"
uv pip install "qiskit-addon-mpf==0.3.0"
uv pip install "qiskit-addon-aqc-tensor==0.3.1"
```

Each addon has independent release notes and assumptions. Read its tutorial and validate against a classically tractable instance.

## Direct Quantum-Information Tools

Many tasks do not need a high-level algorithm package:

```python
from qiskit.quantum_info import DensityMatrix, Operator, Statevector

state = Statevector.from_instruction(circuit)
operator = Operator(circuit)
density_matrix = DensityMatrix(state)
```

Use `qiskit.quantum_info` for:

- ideal state/operator analysis,
- fidelity and distance metrics,
- partial traces and entropies,
- Pauli and Clifford algebra,
- channel representations,
- small-system validation.

Dense state and operator memory grows exponentially; check dimensions before constructing them.

## Algorithm Review Checklist

1. Is the cited speedup asymptotic, heuristic, or empirically demonstrated?
2. Does state preparation or readout dominate the claimed advantage?
3. Is the instance classically verifiable at the tested size?
4. Are package and primitive versions compatible?
5. Does the implementation use V2 primitives?
6. Is the parameterized circuit compiled once for the selected target?
7. Are observable layouts and bit order handled correctly?
8. Are optimizer evaluations, precision, shots, mitigation, and total QPU usage reported?
9. Is every result labeled as ideal simulation, noisy simulation, or hardware?
10. Are classical baselines and uncertainty included?
