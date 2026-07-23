---
name: qiskit
description: Build, simulate, transpile, and execute quantum circuits with Qiskit and IBM Quantum Runtime. Use for Qiskit 2.x circuits and operators, V2 Sampler or Estimator primitives, target-aware transpilation, local or noisy simulation, IBM QPU execution, Runtime sessions or batches, error mitigation, and Qiskit ecosystem packages.
license: Apache-2.0
compatibility: Python 3.10+ on a supported 64-bit platform. Local SDK workflows need qiskit; noisy simulation needs qiskit-aer; IBM QPU access needs qiskit-ibm-runtime, network access, an IBM Quantum Platform account, and an API key.
metadata:
  version: "2.0"
  skill-author: K-Dense Inc.
---

# Qiskit

Use current Qiskit 2.x APIs to build circuits, prepare hardware-compatible instruction set architecture (ISA) circuits, and execute them through V2 primitives.

This skill was verified on **2026-07-23** against the PyPI releases `qiskit==2.5.0`, `qiskit-ibm-runtime==0.48.0`, and `qiskit-aer==0.17.2`. Check [references/sources.md](references/sources.md) before changing pins or documenting newly released behavior.

## Choose the Right Path

| Goal | Recommended interface |
|---|---|
| Exact local sampling | `qiskit.primitives.StatevectorSampler` |
| Exact local expectation values | `qiskit.primitives.StatevectorEstimator` |
| High-performance or noisy simulation | Qiskit Aer |
| IBM QPU sampling | `qiskit_ibm_runtime.SamplerV2` |
| IBM QPU expectation values and mitigation | `qiskit_ibm_runtime.EstimatorV2` |
| Backend without native primitives | `BackendSamplerV2` or `BackendEstimatorV2` |
| Open-system or master-equation dynamics | Prefer QuTiP |
| Differentiable quantum machine learning | Prefer PennyLane unless Qiskit integration is required |

## Installation

Create an isolated environment and install only the components needed:

```bash
uv venv --python 3.13
source .venv/bin/activate

# Core SDK plus plotting support
uv pip install "qiskit[visualization]==2.5.0"

# Add only when needed
uv pip install "qiskit-ibm-runtime==0.48.0"
uv pip install "qiskit-aer==0.17.2"
```

Do not install `qiskit-terra`; it was superseded by the `qiskit` distribution. Qiskit Runtime, Aer, Nature, Machine Learning, Optimization, and Algorithms are separate distributions.

For IBM account setup, CI-safe credential handling, optional packages, and environment repair, read [references/setup.md](references/setup.md).

## Core Workflow

Follow this sequence for every hardware-oriented workload:

1. **Map** the problem to a circuit and, for Estimator, one or more observables.
2. **Optimize** the parameterized circuit once for the selected backend.
3. **Apply the layout** to every observable.
4. **Execute** ISA circuits through a V2 primitive using Primitive Unified Blocs (PUBs).
5. **Analyze** register-aware results, metadata, uncertainty, and resource usage.

Do not bind and retranspile a parameterized circuit inside every optimizer iteration. Transpile the parameterized circuit once, then pass parameter arrays in PUBs.

## Quick Local Sampling

```python
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure_all()  # creates the classical register named "meas"

sampler = StatevectorSampler(seed=7)
pub_result = sampler.run([circuit], shots=1024).result()[0]
counts = pub_result.data.meas.get_counts()
print(counts)
```

Sampler V2 preserves shots and classical-register structure. Access the register by its actual name; `measure_all()` uses `meas`.

## Quick Local Estimation

```python
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp

theta = Parameter("theta")
circuit = QuantumCircuit(2)
circuit.ry(theta, 0)
circuit.cx(0, 1)

observable = SparsePauliOp.from_list([("ZZ", 1.0), ("XX", 0.5)])
parameter_values = [[0.0], [np.pi / 4], [np.pi / 2]]

estimator = StatevectorEstimator(seed=7)
pub = (circuit, observable, parameter_values)
pub_result = estimator.run([pub]).result()[0]
print(pub_result.data.evs)
```

Estimator circuits should not contain final measurements. PUB arrays broadcast; verify circuit parameter order before constructing large sweeps.

## IBM QPU Sampling

This example assumes credentials were saved securely as described in [references/setup.md](references/setup.md). It never embeds or prints an API key.

```python
from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

service = QiskitRuntimeService()
backend = service.least_busy(
    operational=True,
    simulator=False,
    min_num_qubits=2,
)

circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure_all()

pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1,
    seed_transpiler=7,
)
isa_circuit = pass_manager.run(circuit)

sampler = Sampler(mode=backend)
job = sampler.run([isa_circuit], shots=1024)
print("job_id:", job.job_id())
counts = job.result()[0].data.meas.get_counts()
```

Save the job ID before waiting for results so the job can be retrieved later.

## IBM QPU Estimation

Runtime Estimator requires both an ISA circuit and observables mapped through the transpiler layout:

```python
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2 as Estimator

circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
observable = SparsePauliOp.from_list([("ZZ", 1.0)])

pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1,
    seed_transpiler=7,
)
isa_circuit = pass_manager.run(circuit)
isa_observable = observable.apply_layout(isa_circuit.layout)

estimator = Estimator(
    mode=backend,
    options={"resilience_level": 1},
)
pub_result = estimator.run(
    [(isa_circuit, isa_observable)],
    precision=0.02,
).result()[0]
print(pub_result.data.evs, pub_result.data.stds)
```

Error mitigation is not guaranteed to improve every workload and increases cost. Record the complete options and result metadata.

## Non-Negotiable Qiskit 2.x Rules

- Use V2 primitive interfaces and PUB inputs. Do not write new V1 `Sampler`, `Estimator`, or `QuantumInstance` code.
- Runtime primitives accept ISA circuits; they do not perform layout, routing, and basis translation for you.
- Apply the transpiler layout to Estimator observables with `observable.apply_layout(isa_circuit.layout)`.
- Use `mode=backend`, `mode=session`, or `mode=batch` for Runtime primitives.
- Use `EstimatorV2` for resilience levels and expectation-value mitigation. Sampler has different noise-management options and no Estimator-style resilience levels.
- Treat `BackendV2.target`, `backend.operation_names`, `backend.coupling_map`, and direct backend attributes as the source of hardware constraints. Do not use `backend.configuration()` or `BackendProperties`.
- Read Sampler output by classical register name. Bitstrings are displayed most-significant bit first; Qiskit qubit 0 is conventionally the least-significant bit.
- Use a fixed `seed_transpiler` when comparing compilation settings. A simulator seed does not make QPU results deterministic.
- `qiskit.pulse` was removed in Qiskit 2.0. Use supported fractional gates for IBM hardware or Qiskit Dynamics for pulse-model research.
- QPY is the Qiskit-native circuit serialization format. Do not use Python pickle for untrusted circuit artifacts.

See [references/migration.md](references/migration.md) for a detailed old-to-current API map.

## Execution Modes

Choose based on workload shape and account plan:

- **Job mode**: one-off work; instantiate a primitive with `mode=backend`.
- **Batch mode**: independent jobs submitted together; available on the Open Plan.
- **Session mode**: iterative jobs that benefit from prioritized follow-on execution; unavailable on the Open Plan.

```python
from qiskit_ibm_runtime import Batch, SamplerV2 as Sampler

with Batch(backend=backend, max_time="10m") as batch:
    sampler = Sampler(mode=batch)
    jobs = [sampler.run([circuit], shots=1024) for circuit in isa_circuits]

results = [job.result() for job in jobs]
```

Close sessions and batches after submission. Exiting their context stops new submissions but allows accepted jobs to finish, subject to service limits.

## Reference Map

Read only the files needed for the current task:

| Topic | Reference |
|---|---|
| Versions, installation, authentication, CI | [references/setup.md](references/setup.md) |
| Circuits, parameters, control flow, QPY | [references/circuits.md](references/circuits.md) |
| V2 PUBs, broadcasting, local and Runtime results | [references/primitives.md](references/primitives.md) |
| Targets, ISA circuits, layouts, pass managers | [references/transpilation.md](references/transpilation.md) |
| IBM backends, modes, jobs, Aer, mitigation | [references/backends.md](references/backends.md) |
| End-to-end map/optimize/execute/analyze patterns | [references/patterns.md](references/patterns.md) |
| Algorithms, addons, Nature, ML, Optimization | [references/algorithms.md](references/algorithms.md) |
| Circuit, result, state, and backend plots | [references/visualization.md](references/visualization.md) |
| Qiskit 0.x/1.x and Runtime migration | [references/migration.md](references/migration.md) |
| Testing, reproducibility, and troubleshooting | [references/testing.md](references/testing.md) |
| Upstream docs, release notes, and version baseline | [references/sources.md](references/sources.md) |

## Bundled Scripts

Run from the skill directory:

```bash
# Installed-package and legacy-environment checks; no network or credential reads
python scripts/check_environment.py

# Runnable V2 local Sampler and Estimator example
python scripts/run_local_primitives.py --shots 1024 --seed 7

# Read-only IBM backend capability inspection; uses saved credentials
python scripts/inspect_runtime.py --min-qubits 5
```

The Runtime inspection script selects or inspects a backend but never submits a quantum job.

## Final Checklist

Before returning Qiskit code:

1. Confirm package versions and Python compatibility.
2. Run locally with statevector primitives or Aer.
3. Verify parameter order, observable qubit count, and classical-register names.
4. Transpile against the exact `BackendV2` target and inspect depth and two-qubit operations.
5. Apply the final layout to every observable.
6. Estimate QPU cost and choose job, batch, or session mode.
7. Save job IDs, package versions, seeds, backend name, primitive options, and result metadata.
8. Never expose API keys in source, logs, notebooks, or version control.
