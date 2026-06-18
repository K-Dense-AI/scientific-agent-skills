---
name: cirq
description: Google quantum computing framework. Use when targeting Google Quantum AI hardware, designing noise-aware circuits, or running quantum characterization experiments. Best for Google hardware, noise modeling, and low-level circuit design. For IBM hardware use qiskit; for quantum ML with autodiff use pennylane; for physics simulations use qutip.
license: Apache-2.0 license
allowed-tools: Read Write Edit Bash
metadata: {"version": "1.0", "skill-author": "K-Dense Inc."}
---

# Cirq - Quantum Computing with Python

Cirq is Google Quantum AI's open-source framework for designing, simulating, and running quantum circuits on quantum computers and simulators.

## When to Use This Skill

Use this skill when:
- Building, simulating, or optimizing NISQ circuits in Python
- Running jobs on Google Quantum AI processors (via `cirq-google`) or partner backends (IonQ, Azure Quantum, AQT, Pasqal)
- Modeling noise, compiling to hardware gatesets, or designing characterization experiments
- Using parameter sweeps, transformers, or the ReCirq experiment patterns

For IBM hardware use **qiskit**; for quantum ML with autodiff use **pennylane**; for physics simulations use **qutip**.

## Installation

Requires Python 3.11+. Current stable release: **1.6.1** (August 2025). Vendor packages share the same version number.

```bash
uv pip install "cirq==1.6.1"
```

For hardware integration (pin matching versions for reproducibility):
```bash
# Google Quantum Engine (requires approved GCP project access)
uv pip install "cirq-google==1.6.1"

# IonQ
uv pip install "cirq-ionq==1.6.1"

# AQT (Alpine Quantum Technologies)
uv pip install "cirq-aqt==1.6.1"

# Pasqal
uv pip install "cirq-pasqal==1.6.1"

# Azure Quantum (IonQ, Honeywell/Quantinuum backends)
uv pip install "azure-quantum[cirq]"
```

For latest features during development, omit version pins; for production or hardware runs, pin all packages to the same Cirq release.

## Quick Start

### Basic Circuit

```python
import cirq
import numpy as np

# Create qubits
q0, q1 = cirq.LineQubit.range(2)

# Build circuit
circuit = cirq.Circuit(
    cirq.H(q0),              # Hadamard on q0
    cirq.CNOT(q0, q1),       # CNOT with q0 control, q1 target
    cirq.measure(q0, q1, key='result')
)

print(circuit)

# Simulate
simulator = cirq.Simulator()
result = simulator.run(circuit, repetitions=1000)

# Display results
print(result.histogram(key='result'))
```

### Parameterized Circuit

```python
import sympy

# Define symbolic parameter
theta = sympy.Symbol('theta')

# Create parameterized circuit
circuit = cirq.Circuit(
    cirq.ry(theta)(q0),
    cirq.measure(q0, key='m')
)

# Sweep over parameter values
sweep = cirq.Linspace('theta', start=0, stop=2*np.pi, length=20)
results = simulator.run_sweep(circuit, params=sweep, repetitions=1000)

# Process results
for params, result in zip(sweep, results):
    theta_val = params['theta']
    counts = result.histogram(key='m')
    print(f"θ={theta_val:.2f}: {counts}")
```

## Core Capabilities

### Circuit Building
For comprehensive information about building quantum circuits, including qubits, gates, operations, custom gates, and circuit patterns, see:
- **[references/building.md](references/building.md)** - Complete guide to circuit construction

Common topics:
- Qubit types (GridQubit, LineQubit, NamedQubit)
- Single and two-qubit gates
- Parameterized gates and operations
- Custom gate decomposition
- Circuit organization with moments
- Standard circuit patterns (Bell states, GHZ, QFT)
- Import/export (OpenQASM, JSON)
- Working with qudits and observables

### Simulation
For detailed information about simulating quantum circuits, including exact simulation, noisy simulation, parameter sweeps, and the Quantum Virtual Machine, see:
- **[references/simulation.md](references/simulation.md)** - Complete guide to quantum simulation

Common topics:
- Exact simulation (state vector, density matrix)
- Sampling and measurements
- Parameter sweeps (single and multiple parameters)
- Noisy simulation
- State histograms and visualization
- Quantum Virtual Machine (QVM)
- Expectation values and observables
- Performance optimization

### Circuit Transformation
For information about optimizing, compiling, and manipulating quantum circuits, see:
- **[references/transformation.md](references/transformation.md)** - Complete guide to circuit transformations

Common topics:
- Transformer framework
- Gate decomposition
- Circuit optimization (merge gates, eject Z gates, drop negligible operations)
- Circuit compilation for hardware
- Qubit routing and SWAP insertion
- Custom transformers
- Transformation pipelines

### Hardware Integration
For information about running circuits on real quantum hardware from various providers, see:
- **[references/hardware.md](references/hardware.md)** - Complete guide to hardware integration

Supported providers:
- **Google Quantum AI** (`cirq-google`) — Sycamore, Weber, Willow processors via Quantum Engine (restricted access; requires approved GCP project)
- **IonQ** (`cirq-ionq`) — trapped-ion QPUs and simulators
- **Azure Quantum** (`azure-quantum[cirq]`) — IonQ and Honeywell/Quantinuum backends
- **AQT** (`cirq-aqt`) — Alpine Quantum Technologies
- **Pasqal** (`cirq-pasqal`) — neutral-atom devices

Topics include device representation, qubit selection, authentication, job management, and circuit optimization for hardware. See [Access and authentication](https://quantumai.google/cirq/google/access) for Google Cloud setup.

### Noise Modeling
For information about modeling noise, noisy simulation, characterization, and error mitigation, see:
- **[references/noise.md](references/noise.md)** - Complete guide to noise modeling

Common topics:
- Noise channels (depolarizing, amplitude damping, phase damping)
- Noise models (constant, gate-specific, qubit-specific, thermal)
- Adding noise to circuits
- Readout noise
- Noise characterization (randomized benchmarking, XEB)
- Noise visualization (heatmaps)
- Error mitigation techniques

### Quantum Experiments
For information about designing experiments, parameter sweeps, data collection, and using the ReCirq framework, see:
- **[references/experiments.md](references/experiments.md)** - Complete guide to quantum experiments

Common topics:
- Experiment design patterns
- Parameter sweeps and data collection
- ReCirq framework structure
- Common algorithms (VQE, QAOA, QPE)
- Data analysis and visualization
- Statistical analysis and fidelity estimation
- Parallel data collection

## Common Patterns

### Variational Algorithm Template

```python
import scipy.optimize

def variational_algorithm(ansatz, cost_function, initial_params):
    """Template for variational quantum algorithms."""

    def objective(params):
        circuit = ansatz(params)
        simulator = cirq.Simulator()
        result = simulator.simulate(circuit)
        return cost_function(result)

    # Optimize
    result = scipy.optimize.minimize(
        objective,
        initial_params,
        method='COBYLA'
    )

    return result

# Define ansatz
def my_ansatz(params):
    q = cirq.LineQubit(0)
    return cirq.Circuit(
        cirq.ry(params[0])(q),
        cirq.rz(params[1])(q)
    )

# Define cost function
def my_cost(result):
    state = result.final_state_vector
    # Calculate cost based on state
    return np.real(state[0])

# Run optimization
result = variational_algorithm(my_ansatz, my_cost, [0.0, 0.0])
```

### Hardware Execution Template

```python
import os

def run_on_hardware(circuit, provider='google', processor_id=None, repetitions=1000):
    """Template for running on quantum hardware."""

    if provider == 'google':
        import cirq_google as cg

        project_id = os.environ['GOOGLE_CLOUD_PROJECT']
        engine = cg.Engine(project_id=project_id)

        # List available processors: engine.list_processors()
        processor_id = processor_id or 'weber'  # use your assigned processor_id
        sampler = engine.get_sampler(processor_id=processor_id)
        return sampler.run(circuit, repetitions=repetitions)

    elif provider == 'ionq':
        import cirq_ionq as ionq

        # Requires IONQ_API_KEY in environment
        service = ionq.Service()
        return service.run(circuit, repetitions=repetitions, target='qpu')

    elif provider == 'azure':
        from azure.quantum.cirq import AzureQuantumService

        service = AzureQuantumService(
            resource_id=os.environ['AZURE_QUANTUM_RESOURCE_ID'],
            location=os.environ['AZURE_QUANTUM_LOCATION'],
        )
        return service.run(circuit, repetitions=repetitions, target='ionq.qpu')

    else:
        raise ValueError(f"Unknown provider: {provider}")
```

### Noise Study Template

```python
def noise_comparison_study(circuit, noise_levels):
    """Compare circuit performance at different noise levels."""

    results = {}

    for noise_level in noise_levels:
        # Create noisy circuit
        noisy_circuit = circuit.with_noise(cirq.depolarize(p=noise_level))

        # Simulate
        simulator = cirq.DensityMatrixSimulator()
        result = simulator.run(noisy_circuit, repetitions=1000)

        # Analyze
        results[noise_level] = {
            'histogram': result.histogram(key='result'),
            'dominant_state': max(
                result.histogram(key='result').items(),
                key=lambda x: x[1]
            )
        }

    return results

# Run study
noise_levels = [0.0, 0.001, 0.01, 0.05, 0.1]
results = noise_comparison_study(circuit, noise_levels)
```

## Best Practices

1. **Circuit Design**
   - Use appropriate qubit types for your topology
   - Keep circuits modular and reusable
   - Label measurements with descriptive keys
   - Validate circuits against device constraints before execution

2. **Simulation**
   - Use state vector simulation for pure states (more efficient)
   - Use density matrix simulation only when needed (mixed states, noise)
   - Leverage parameter sweeps instead of individual runs
   - Monitor memory usage for large systems (2^n grows quickly)

3. **Hardware Execution**
   - Always test on simulators first
   - Select best qubits using calibration data
   - Optimize circuits for target hardware gateset
   - Implement error mitigation for production runs
   - Store expensive hardware results immediately

4. **Circuit Optimization**
   - Start with high-level built-in transformers
   - Chain multiple optimizations in sequence
   - Track depth and gate count reduction
   - Validate correctness after transformation

5. **Noise Modeling**
   - Use realistic noise models from calibration data
   - Include all error sources (gate, decoherence, readout)
   - Characterize before mitigating
   - Keep circuits shallow to minimize noise accumulation

6. **Experiments**
   - Structure experiments with clear separation (data generation, collection, analysis)
   - Use ReCirq patterns for reproducibility
   - Save intermediate results frequently
   - Parallelize independent tasks
   - Document thoroughly with metadata

## Additional Resources

- **Official Documentation**: https://quantumai.google/cirq
- **API Reference**: https://quantumai.google/reference/python/cirq
- **Tutorials**: https://quantumai.google/cirq/tutorials
- **Examples**: https://github.com/quantumlib/Cirq/tree/main/examples
- **Version policy**: https://quantumai.google/cirq/dev/versions
- **ReCirq**: https://github.com/quantumlib/ReCirq

## Common Issues

**Circuit too deep for hardware:**
- Use circuit optimization transformers to reduce depth
- See `transformation.md` for optimization techniques

**Memory issues with simulation:**
- Switch from density matrix to state vector simulator
- Reduce number of qubits or use stabilizer simulator for Clifford circuits

**Device validation errors:**
- Check qubit connectivity with device.metadata.nx_graph
- Decompose gates to device-native gateset
- See `hardware.md` for device-specific compilation

**Noisy simulation too slow:**
- Density matrix simulation is O(2^2n) - consider reducing qubits
- Use noise models selectively on critical operations only
- See `simulation.md` for performance optimization

