# Migration to Qiskit 2.5 and Runtime 0.48

Use this guide when adapting code written for Qiskit 0.x, Qiskit 1.x, or early Qiskit Runtime releases.

## Start with a Clean Environment

Do not upgrade an environment containing both old `qiskit-terra` and modern `qiskit`.

```bash
uv venv --python 3.13 .venv-qiskit-2
source .venv-qiskit-2/bin/activate
uv pip install \
  "qiskit==2.5.0" \
  "qiskit-ibm-runtime==0.48.0" \
  "qiskit-aer==0.17.2"
```

Run:

```bash
python scripts/check_environment.py --require-runtime --require-aer
```

## High-Level API Map

| Legacy pattern | Qiskit 2.5 pattern |
|---|---|
| Install `qiskit-terra` | Install `qiskit` |
| `from qiskit import Aer` | `from qiskit_aer import AerSimulator` |
| `execute(circuit, backend)` | V2 primitive, or provider-specific backend only when necessary |
| `QuantumInstance` | Primitive implementation plus explicit transpilation |
| `qiskit.opflow` | `qiskit.quantum_info.SparsePauliOp` and primitive PUBs |
| `circuit.bind_parameters(...)` | `circuit.assign_parameters(...)`, or pass values in PUBs |
| V1 `Sampler` / `Estimator` | `StatevectorSampler` / `StatevectorEstimator`, Runtime `SamplerV2` / `EstimatorV2` |
| Parallel V1 input lists | One or more PUB tuples |
| `result.quasi_dists` | `result[i].data.<register>.get_counts()` |
| `result.values` | `result[i].data.evs` |
| Runtime shared `Options()` | `SamplerOptions`, `EstimatorOptions`, dict, or `.options.update()` |
| Primitive `backend=` / `session=` | Primitive `mode=` |
| Runtime auto-transpilation | Explicit backend-specific ISA circuit |
| Logical observable submitted unchanged | `observable.apply_layout(isa_circuit.layout)` |
| `backend.configuration()` / `.properties()` | BackendV2 direct attributes and `backend.target` |
| `channel="ibm_quantum"` | `channel="ibm_quantum_platform"` |
| `qiskit.pulse` | IBM fractional gates or Qiskit Dynamics, depending on the goal |
| `QFT(...)` blueprint class | `QFTGate(...)` or `synth_qft_full(...)` |
| Blueprint ansatz classes | Function constructors such as `efficient_su2(...)` |
| `instruction.c_if(...)` | Structured circuit control flow such as `if_test(...)` |

## Migrate V1 Sampler

Legacy shape:

```python
# Legacy; do not use
# sampler = Sampler()
# result = sampler.run(circuits, parameter_values).result()
# quasi_distribution = result.quasi_dists[0]
```

Current local V2:

```python
from qiskit.primitives import StatevectorSampler

sampler = StatevectorSampler(seed=41)
pub_result = sampler.run(
    [(measured_circuit, parameter_values)],
    shots=1024,
).result()[0]

counts = pub_result.data.meas.get_counts(0)
```

Key changes:

- measured shot data replace V1 quasi-distributions,
- output is organized by classical register,
- parameter sweeps retain array shape,
- a PUB contains one circuit and its parameter values.

## Migrate V1 Estimator

Legacy shape:

```python
# Legacy; do not use
# estimator = Estimator()
# result = estimator.run(circuits, observables, values).result()
# expectation_value = result.values[0]
```

Current local V2:

```python
from qiskit.primitives import StatevectorEstimator

estimator = StatevectorEstimator()
pub_result = estimator.run(
    [(circuit, observable, parameter_values)]
).result()[0]

expectation_values = pub_result.data.evs
standard_deviations = pub_result.data.stds
```

## Migrate Runtime Execution

Legacy Runtime:

```python
# Legacy; do not use
# options = Options()
# options.resilience_level = 2
# estimator = Estimator(session=session, options=options)
```

Current Runtime:

```python
from qiskit_ibm_runtime import EstimatorV2 as Estimator

estimator = Estimator(
    mode=session,
    options={"resilience_level": 2},
)
```

Use current mode syntax:

```python
sampler = Sampler(mode=backend)
sampler = Sampler(mode=batch)
sampler = Sampler(mode=session)
```

Do not pass `backend=backend` to a primitive inside a batch or session; that selects job mode.

## Migrate to ISA Circuits

Legacy Runtime examples often submitted logical circuits and relied on service-side transpilation. V2 Runtime requires ISA circuits:

```python
from qiskit.transpiler import generate_preset_pass_manager

pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1,
    seed_transpiler=41,
)
isa_circuit = pass_manager.run(logical_circuit)
```

Estimator observables must follow the layout:

```python
isa_observable = logical_observable.apply_layout(
    isa_circuit.layout
)
```

Failing to map observables can silently change the physical qubits being measured or produce a width error.

## Migrate BackendV1 Access

Legacy:

```python
# Legacy; do not use
# basis_gates = backend.configuration().basis_gates
# coupling_map = backend.configuration().coupling_map
# properties = backend.properties()
```

Current:

```python
basis_operations = backend.operation_names
coupling_map = backend.coupling_map
target = backend.target
num_qubits = backend.num_qubits
```

Query gate errors, durations, and qubit support through the `Target` entries. Do not combine a backend with manually copied basis and coupling data unless constructing a deliberately synthetic target.

## Migrate IBM Account Configuration

The IBM Quantum Platform Classic channel is retired.

Current trusted-machine setup:

```python
import os
from qiskit_ibm_runtime import QiskitRuntimeService

QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform",
    token=os.environ["IBM_QUANTUM_API_KEY"],
    instance=os.environ.get("IBM_QUANTUM_INSTANCE"),
    set_as_default=True,
    overwrite=True,
)
```

Do not paste a key into source or a notebook. See [setup.md](setup.md).

## Migrate Pulse Code

`qiskit.pulse` was removed in Qiskit 2.0 without a drop-in replacement.

Choose based on intent:

- To execute supported continuous-angle one- and two-qubit rotations on IBM hardware, request a backend target with fractional gates.
- To model driven quantum systems and pulse-level dynamics, use the independently released Qiskit Dynamics project.
- To keep a historical pulse workflow unchanged, isolate it in a legacy Qiskit 1.x environment only for archival reproducibility; do not mix it with Qiskit 2.x.

Do not copy `pulse.build`, `ScheduleBlock`, or pulse-drawer examples into Qiskit 2.x code.

QPY files containing `ScheduleBlock` objects cannot be loaded by Qiskit 2.x.

## Migrate Circuit-Library Blueprints

Several mutable blueprint classes are deprecated in favor of eagerly built functions or gates:

```python
from qiskit.circuit.library import (
    QFTGate,
    efficient_su2,
    real_amplitudes,
    zz_feature_map,
)

qft_gate = QFTGate(4)
ansatz = efficient_su2(4, reps=2)
real_ansatz = real_amplitudes(4, reps=2)
feature_map = zz_feature_map(4, reps=2)
```

The old `QFT` class is deprecated as of 2.1 and scheduled for removal in 3.0.

Function constructors can differ in mutability and construction timing from blueprint classes. Test parameter order and circuit metadata after migration.

## Migrate Classical Conditions

Legacy per-instruction conditions were removed:

```python
# Legacy; do not use
# circuit.x(0).c_if(classical_register, 1)
```

Use structured control flow:

```python
with circuit.if_test((classical_bit, True)):
    circuit.x(0)
```

Then verify that the selected backend target supports the corresponding control-flow instruction.

## Migrate Qiskit Algorithms

Old `quantum_instance=` constructors are not current.

```python
from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import PhaseEstimation

phase_estimation = PhaseEstimation(
    num_evaluation_qubits=4,
    sampler=StatevectorSampler(seed=41),
)
```

Current `VQE` takes a V2 Estimator; current `QAOA` takes a V2 Sampler.

Use optimizer objects:

```python
from qiskit_algorithms.optimizers import COBYLA

optimizer = COBYLA(maxiter=100)
```

Do not use strings such as `optimizer="COBYLA"` unless a specific current package API documents that form.

## Migrate Qiskit Machine Learning

Since Qiskit Machine Learning 0.8, several features moved out of `qiskit_algorithms`:

```python
# Current package locations
from qiskit_machine_learning.optimizers import COBYLA
from qiskit_machine_learning.state_fidelities import ComputeUncompute
from qiskit_machine_learning.utils import algorithm_globals
```

Check the package's 0.8 migration guide for gradients, optimizers, fidelities, and utilities. Do not assume an import path from a Qiskit Machine Learning 0.7 tutorial still works.

## Migrate Qiskit Nature

Use mapper classes directly:

```python
from qiskit_nature.second_q.mappers import JordanWignerMapper

mapper = JordanWignerMapper()
qubit_operator = mapper.map(fermionic_operator)
```

`QubitConverter` is obsolete. Current application code lives primarily under `qiskit_nature.second_q`.

## Serialization Migration

Prefer:

- QPY for Qiskit-native circuit persistence,
- OpenQASM for supported interchange,
- explicit JSON-compatible experiment metadata.

Avoid Python pickle for untrusted artifacts. QPY is forward-compatible but not backward-compatible: newer Qiskit normally reads older QPY, not vice versa.

Record the Qiskit version that wrote each QPY file.

## Migration Validation

After each migration:

1. Run imports with deprecation warnings visible.
2. Compare a small logical circuit's ideal state or operator.
3. Verify parameter order and PUB output shape.
4. Verify count-string and Pauli-label ordering.
5. Compile against a fake `BackendV2`.
6. Confirm all Estimator observables use the compiled layout.
7. Compare application-level outputs, not circuit text alone.
8. Run one bounded noisy simulation before a QPU.
9. Record new package pins and update the experiment manifest.

Do not silence deprecation warnings globally. Treat them as scheduled migration work before Qiskit 3.0.
