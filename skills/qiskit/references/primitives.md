# V2 Primitives and PUBs

Qiskit primitives standardize two core tasks:

- **Sampler** executes measured circuits and returns shot-resolved classical data.
- **Estimator** computes expectation values of observables for states prepared by circuits.

Use V2 interfaces. Their unit of work is a **Primitive Unified Bloc (PUB)**.

## Implementations

| Implementation | Use |
|---|---|
| `StatevectorSampler` | Exact statevector evolution plus finite-shot sampling on the local CPU |
| `StatevectorEstimator` | Local statevector expectation values |
| Aer `SamplerV2` / `EstimatorV2` | High-performance and noisy local simulation |
| Runtime `SamplerV2` / `EstimatorV2` | IBM QPUs and IBM Runtime services |
| `BackendSamplerV2` / `BackendEstimatorV2` | Adapt a `BackendV2` that lacks native primitives |

The V2 `run()` structure is shared, but options are implementation-specific. Do not pass Runtime resilience options to statevector or Aer primitives.

## Sampler PUBs

A Sampler PUB contains:

1. One circuit with measurements.
2. Optional parameter values.

Pass shots at the `run()` level unless a specific current API requires otherwise.

### One Circuit

```python
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure_all()

sampler = StatevectorSampler(seed=11)
primitive_result = sampler.run([circuit], shots=1024).result()
pub_result = primitive_result[0]

counts = pub_result.data.meas.get_counts()
bitstrings = pub_result.data.meas.get_bitstrings()
metadata = pub_result.metadata
```

`meas` is the name of the classical register created by `measure_all()`.

### Multiple Circuits

```python
circuit_x = QuantumCircuit(1)
circuit_x.x(0)
circuit_x.measure_all()

circuit_h = QuantumCircuit(1)
circuit_h.h(0)
circuit_h.measure_all()

result = sampler.run([circuit_x, circuit_h], shots=512).result()
counts_x = result[0].data.meas.get_counts()
counts_h = result[1].data.meas.get_counts()
```

Each input PUB produces one `PubResult`.

### Parameter Sweep

```python
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives import StatevectorSampler

theta = Parameter("theta")
circuit = QuantumCircuit(1)
circuit.ry(theta, 0)
circuit.measure_all()

values = [[0.0], [np.pi / 2], [np.pi]]
sampler = StatevectorSampler(seed=11)
pub_result = sampler.run(
    [(circuit, values)],
    shots=256,
).result()[0]

for index, value in enumerate(values):
    counts = pub_result.data.meas.get_counts(index)
    print(value[0], counts)
```

For a shaped `BitArray`, pass an index to `get_counts()` when results must remain separated by parameter point. Calling it without an index can aggregate over axes.

## Multiple Classical Registers

Sampler data fields use register names:

```python
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.primitives import StatevectorSampler

qubits = QuantumRegister(2, "q")
left = ClassicalRegister(1, "left")
right = ClassicalRegister(1, "right")
circuit = QuantumCircuit(qubits, left, right)
circuit.h(qubits[0])
circuit.cx(qubits[0], qubits[1])
circuit.measure(qubits[0], left[0])
circuit.measure(qubits[1], right[0])

pub_result = StatevectorSampler(seed=11).run(
    [circuit],
    shots=256,
).result()[0]

left_counts = pub_result.data.left.get_counts()
right_counts = pub_result.data.right.get_counts()
```

Do not assume every result has `.data.meas`. Inspect `circuit.cregs` or `pub_result.data`.

## Estimator PUBs

An Estimator PUB contains:

1. One circuit, normally without final measurements.
2. One observable or an array of observables.
3. Optional parameter values.

### One Circuit and Observable

```python
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp

circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)

observable = SparsePauliOp.from_list(
    [
        ("ZZ", 1.0),
        ("XX", 0.5),
    ]
)

estimator = StatevectorEstimator()
pub_result = estimator.run(
    [(circuit, observable)]
).result()[0]

expectation_values = pub_result.data.evs
standard_deviations = pub_result.data.stds
```

`SparsePauliOp` labels are little-endian with respect to qubit indices: the rightmost label character acts on qubit 0.

### Parameter Sweep

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

observable = SparsePauliOp.from_list([("ZI", 1.0), ("XX", 0.5)])
values = [[0.0], [np.pi / 4], [np.pi / 2]]

pub_result = StatevectorEstimator().run(
    [(circuit, observable, values)]
).result()[0]

print(pub_result.data.evs)
```

The final axis of `values` corresponds to `list(circuit.parameters)`.

### Multiple Observables

```python
observables = [
    [SparsePauliOp.from_list([("ZZ", 1.0)])],
    [SparsePauliOp.from_list([("XX", 1.0)])],
]

pub_result = StatevectorEstimator().run(
    [(circuit, observables, values)]
).result()[0]
assert pub_result.data.evs.shape == (2, len(values))
```

Estimator V2 broadcasts observable and parameter arrays. For nontrivial shapes, build a small test first and assert the output shape rather than relying on intuition.

## Precision and Shots

- Sampler controls finite sampling with `shots`.
- Estimator controls target accuracy with `precision`.
- `StatevectorEstimator` is exact at its default precision of zero for supported circuits and Pauli observables.
- Runtime may translate requested precision into a shot and randomization budget.
- Runtime twirling settings can affect how shots are allocated.

```python
pub_result = runtime_estimator.run(
    [(isa_circuit, isa_observable)],
    precision=0.02,
).result()[0]
```

Record requested precision, realized metadata, primitive options, and usage. Do not compare two experiments solely by nominal shot count when mitigation or twirling differs.

## Runtime Sampler V2

Runtime circuits must already satisfy the selected backend's ISA:

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
    seed_transpiler=11,
)
isa_circuit = pass_manager.run(circuit)

sampler = Sampler(
    mode=backend,
    options={"default_shots": 1024},
)
job = sampler.run([isa_circuit])
print(job.job_id())
counts = job.result()[0].data.meas.get_counts()
```

Sampler noise-management options include dynamical decoupling, twirling, execution, environment, and simulator settings. Sampler does not expose Estimator resilience levels.

## Runtime Estimator V2

Map observables through the final circuit layout:

```python
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime import EstimatorV2 as Estimator

observable = SparsePauliOp.from_list([("ZZ", 1.0)])
isa_observable = observable.apply_layout(isa_circuit.layout)

estimator = Estimator(
    mode=backend,
    options={"resilience_level": 1},
)
job = estimator.run(
    [(isa_circuit, isa_observable)],
    precision=0.02,
)
print(job.job_id())
pub_result = job.result()[0]
print(pub_result.data.evs, pub_result.data.stds)
```

For a parameterized circuit, transpile once and include values in the PUB:

```python
pub = (isa_circuit, isa_observable, parameter_values)
pub_result = estimator.run([pub], precision=0.02).result()[0]
```

## Runtime Options

Set options with a dictionary, an options dataclass, direct attributes, or `.update()`:

```python
from qiskit_ibm_runtime import EstimatorOptions, EstimatorV2 as Estimator

options = EstimatorOptions(
    resilience_level=2,
    resilience={
        "zne_mitigation": True,
        "zne": {"noise_factors": [1, 3, 5]},
    },
)
estimator = Estimator(mode=backend, options=options)

estimator.options.default_precision = 0.02
estimator.options.update(
    dynamical_decoupling={
        "enable": True,
        "sequence_type": "XpXm",
    }
)
```

Current Estimator resilience levels are `0`, `1`, and `2`; there is no level 3. Advanced features can be incompatible with each other, especially fractional gates, gate twirling, PEA, PEC, and gate-folding ZNE. Consult the current options guide before combining them.

Do not use the old shared `Options()` object or `.set_options()`.

## Job, Batch, and Session Modes

```python
from qiskit_ibm_runtime import (
    Batch,
    EstimatorV2 as Estimator,
    SamplerV2 as Sampler,
    Session,
)

# Job mode
sampler = Sampler(mode=backend)
job = sampler.run([isa_circuit], shots=1024)

# Batch mode: independent jobs
with Batch(backend=backend, max_time="10m") as batch:
    sampler = Sampler(mode=batch)
    batch_jobs = [
        sampler.run([circuit], shots=1024)
        for circuit in isa_circuits
    ]

# Session mode: iterative jobs; unavailable on the Open Plan
with Session(backend=backend, max_time="20m") as session:
    estimator = Estimator(mode=session)
    session_jobs = [
        estimator.run([pub], precision=0.03)
        for pub in iterative_pubs
    ]
```

Create the primitive with `mode=batch` or `mode=session`. Passing the backend instead runs in job mode even inside a context.

## Adapting a Backend

Use backend primitives when a provider exposes `BackendV2` but no native V2 primitive:

```python
from qiskit.primitives import BackendEstimatorV2, BackendSamplerV2

sampler = BackendSamplerV2(backend=backend)
estimator = BackendEstimatorV2(backend=backend)
```

Provider behavior, result quality, and options differ. Transpile for the backend target and read the provider documentation.

## Result Handling Checklist

For every result:

1. Match each `PubResult` to its input PUB.
2. Use the actual classical-register field for Sampler output.
3. Preserve array dimensions for parameter and observable sweeps.
4. Store metadata alongside values or counts.
5. Store the job ID before blocking on `result()`.
6. Record package versions, backend name, seeds, precision or shots, and all non-default options.
7. Treat mitigated expectation values as estimates with method-dependent bias and overhead.

## Migration Traps

| Old pattern | Current pattern |
|---|---|
| `Sampler()` or `Estimator()` V1 | Explicit V2 implementation |
| `.quasi_dists` | Shot-resolved `BitArray`, such as `.data.meas.get_counts()` |
| `.values` | `.result()[i].data.evs` |
| Parallel circuit/observable/value lists | One or more PUB tuples |
| Shared `Options()` | `SamplerOptions`, `EstimatorOptions`, dictionaries, or `.options.update()` |
| `backend=` / `session=` primitive arguments | `mode=` |
| Runtime auto-transpilation | Explicit ISA circuit preparation |
| Unmapped observables | `observable.apply_layout(isa_circuit.layout)` |

## Common Errors

- **No `meas` field**: the circuit has a differently named register or no measurements.
- **Shape/broadcast error**: check `circuit.parameters`, the last parameter-value axis, and observable-array shape.
- **Circuit not ISA-compatible**: transpile against the exact backend target before Runtime execution.
- **Observable qubit mismatch**: apply the circuit layout and confirm the resulting width.
- **Unsupported option**: options are implementation- and version-specific.
- **Session rejected**: Open Plan workloads must use job or batch mode.
- **Unexpected cost**: mitigation, twirling, and precision settings can multiply circuit and shot counts.
