---
name: pennylane
description: Hardware-agnostic quantum ML framework with automatic differentiation. Use when training quantum circuits via gradients, building hybrid quantum-classical models, or needing device portability across IBM/Google/Rigetti/IonQ. Best for variational algorithms (VQE, QAOA), quantum neural networks, and integration with PyTorch or JAX. For hardware-specific optimizations use qiskit (IBM) or cirq (Google); for open quantum systems use qutip.
license: Apache-2.0 license
allowed-tools:
  - Read
  - Bash
  - Python
metadata: {"version": "1.1", "skill-author": "K-Dense Inc."}
---

# PennyLane

## Overview

PennyLane is a quantum computing library that enables training quantum computers like neural networks. It provides automatic differentiation of quantum circuits, device-independent programming, and seamless integration with classical machine learning frameworks.

## Installation

PennyLane 0.45.0 requires Python 3.11 or newer. Install using uv with pinned versions for reproducible environments:

```bash
uv pip install "pennylane==0.45.0"
```

For quantum hardware access, install the plugin matching the target provider. Start from a clean environment when adding or upgrading Qiskit because its dependency graph is strict.

```bash
# IBM Quantum
uv pip install "pennylane-qiskit==0.45.0"

# Amazon Braket
uv pip install "amazon-braket-pennylane-plugin==1.34.1"

# Google Cirq
uv pip install "pennylane-cirq==0.44.0"

# Rigetti Forest
uv pip install "pennylane-rigetti==0.40.0"

# IonQ
uv pip install "pennylane-ionq==0.45.0"

# High-performance local simulators
uv pip install "pennylane-lightning==0.45.0"

# Catalyst JIT compilation
uv pip install "pennylane-catalyst==0.15.0"
```

## Quick Start

Build a quantum circuit and optimize its parameters:

```python
import pennylane as qml
from pennylane import numpy as np

# Create device
dev = qml.device('default.qubit', wires=2)

# Define quantum circuit
@qml.qnode(dev)
def circuit(params):
    qml.RX(params[0], wires=0)
    qml.RY(params[1], wires=1)
    qml.CNOT(wires=[0, 1])
    return qml.expval(qml.PauliZ(0))

# Optimize parameters
opt = qml.GradientDescentOptimizer(stepsize=0.1)
params = np.array([0.1, 0.2], requires_grad=True)

for i in range(100):
    params = opt.step(circuit, params)
```

## Core Capabilities

### 1. Quantum Circuit Construction

Build circuits with gates, measurements, and state preparation. See `references/quantum_circuits.md` for:
- Single and multi-qubit gates
- Controlled operations and conditional logic
- Mid-circuit measurements and adaptive circuits
- Various measurement types (expectation, probability, samples)
- Circuit inspection and debugging

### 2. Quantum Machine Learning

Create hybrid quantum-classical models. See `references/quantum_ml.md` for:
- Integration with PyTorch and JAX
- Quantum neural networks and variational classifiers
- Data encoding strategies (angle, amplitude, basis, IQP)
- Training hybrid models with backpropagation
- Transfer learning with quantum circuits

### 3. Quantum Chemistry

Simulate molecules and compute ground state energies. See `references/quantum_chemistry.md` for:
- Molecular Hamiltonian generation
- Variational Quantum Eigensolver (VQE)
- UCCSD ansatz for chemistry
- Geometry optimization and dissociation curves
- Molecular property calculations

### 4. Device Management

Execute on simulators or quantum hardware. See `references/devices_backends.md` for:
- Built-in simulators (default.qubit, lightning.qubit, default.mixed)
- Hardware plugins (IBM, Amazon Braket, Google, Rigetti, IonQ)
- Device selection and configuration
- Performance optimization and caching
- GPU acceleration and JIT compilation

### 5. Optimization

Train quantum circuits with various optimizers. See `references/optimization.md` for:
- Built-in optimizers (Adam, gradient descent, momentum, RMSProp)
- Gradient computation methods (backprop, parameter-shift, adjoint)
- Variational algorithms (VQE, QAOA)
- Training strategies (learning rate schedules, mini-batches)
- Handling barren plateaus and local minima

### 6. Advanced Features

Leverage templates, transforms, and compilation. See `references/advanced_features.md` for:
- Circuit templates and layers
- Transforms and circuit optimization
- Pulse-level programming
- Catalyst JIT compilation
- Noise models and error mitigation
- Resource estimation

## Common Workflows

### Train a Variational Classifier

```python
# 1. Define ansatz
@qml.qnode(dev)
def classifier(x, weights):
    # Encode data
    qml.AngleEmbedding(x, wires=range(4))

    # Variational layers
    qml.StronglyEntanglingLayers(weights, wires=range(4))

    return qml.expval(qml.PauliZ(0))

# 2. Train
opt = qml.AdamOptimizer(stepsize=0.01)
weights = np.random.random((3, 4, 3))  # 3 layers, 4 wires

for epoch in range(100):
    for x, y in zip(X_train, y_train):
        weights = opt.step(lambda w: (classifier(x, w) - y)**2, weights)
```

### Run VQE for Molecular Ground State

```python
from pennylane import qchem

# 1. Build Hamiltonian
symbols = ['H', 'H']
geometry = np.array([[0.0, 0.0, -0.66140414], [0.0, 0.0, 0.66140414]])
molecule = qchem.Molecule(symbols, geometry)
H, n_qubits = qchem.molecular_hamiltonian(molecule)
hf_state = qchem.hf_state(electrons=2, orbitals=n_qubits)
singles, doubles = qchem.excitations(electrons=2, orbitals=n_qubits)
s_wires, d_wires = qchem.excitations_to_wires(singles, doubles)

# 2. Define ansatz
@qml.qnode(dev)
def vqe_circuit(params):
    qml.BasisState(hf_state, wires=range(n_qubits))
    qml.UCCSD(params, wires=range(n_qubits), s_wires=s_wires, d_wires=d_wires)
    return qml.expval(H)

# 3. Optimize
opt = qml.AdamOptimizer(stepsize=0.1)
params = np.zeros(len(singles) + len(doubles), requires_grad=True)

for i in range(100):
    params, energy = opt.step_and_cost(vqe_circuit, params)
    print(f"Step {i}: Energy = {energy:.6f} Ha")
```

### Switch Between Devices

```python
# Same circuit, different backends
circuit_def = lambda dev: qml.qnode(dev)(circuit_function)

# Test on simulator
dev_sim = qml.device('default.qubit', wires=4)
result_sim = circuit_def(dev_sim)(params)

# Run on quantum hardware
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService()
backend = service.least_busy(operational=True, simulator=False, min_num_qubits=4)
dev_hw = qml.device('qiskit.remote', wires=backend.num_qubits, backend=backend)
result_hw = circuit_def(dev_hw)(params)
```

## Detailed Documentation

For comprehensive coverage of specific topics, consult the reference files:

- **Getting started**: `references/getting_started.md` - Installation, basic concepts, first steps
- **Quantum circuits**: `references/quantum_circuits.md` - Gates, measurements, circuit patterns
- **Quantum ML**: `references/quantum_ml.md` - Hybrid models, framework integration, QNNs
- **Quantum chemistry**: `references/quantum_chemistry.md` - VQE, molecular Hamiltonians, chemistry workflows
- **Devices**: `references/devices_backends.md` - Simulators, hardware plugins, device configuration
- **Optimization**: `references/optimization.md` - Optimizers, gradients, variational algorithms
- **Advanced**: `references/advanced_features.md` - Templates, transforms, JIT compilation, noise

## Best Practices

1. **Start with simulators** - Test on `default.qubit` before deploying to hardware
2. **Use parameter-shift for hardware** - Backpropagation only works on simulators
3. **Choose appropriate encodings** - Match data encoding to problem structure
4. **Initialize carefully** - Use small random values to avoid barren plateaus
5. **Monitor gradients** - Check for vanishing gradients in deep circuits
6. **Cache devices** - Reuse device objects to reduce initialization overhead
7. **Profile circuits** - Use `qml.specs()` to analyze circuit complexity
8. **Test locally** - Validate on simulators before submitting to hardware
9. **Use templates** - Leverage built-in templates for common circuit patterns
10. **Compile when possible** - Use Catalyst JIT for performance-critical code

## Resources

- Official documentation: https://docs.pennylane.ai
- Codebook (tutorials): https://pennylane.ai/codebook
- QML demonstrations: https://pennylane.ai/qml/demonstrations
- Community forum: https://discuss.pennylane.ai
- GitHub: https://github.com/PennyLaneAI/pennylane

