# Testing, Reproducibility, and Troubleshooting

Quantum workflows combine deterministic program transformations, stochastic sampling, changing hardware, and classical post-processing. Test each layer separately.

## Testing Pyramid

1. **Pure classical tests**: bit ordering, objective functions, post-processing.
2. **Circuit semantic tests**: small statevectors, operators, and measurement bases.
3. **Primitive contract tests**: PUB shapes, result registers, metadata handling.
4. **Transpilation tests**: target compatibility, layout propagation, structural budgets.
5. **Noisy simulation tests**: robustness under a recorded model.
6. **Bounded hardware smoke tests**: smallest useful QPU job.

Do not use QPU jobs as unit tests.

## Run the Bundled Smoke Test

```bash
python scripts/check_environment.py
python scripts/run_local_primitives.py --shots 256 --seed 43
```

Machine-readable output:

```bash
python scripts/check_environment.py --json
python scripts/run_local_primitives.py --json
```

## Deterministic Seeds

Use separate explicit seeds:

```python
seed_transpiler = 43
seed_simulator = 44

pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1,
    seed_transpiler=seed_transpiler,
)

sampler = StatevectorSampler(seed=seed_simulator)
```

Record both. A simulator seed does not make real hardware deterministic. A transpiler seed does not freeze calibration changes or behavior across package versions.

## Test Circuit Semantics

For small unitary circuits:

```python
from qiskit.quantum_info import Operator, Statevector

reference_state = Statevector.from_instruction(reference_circuit)
candidate_state = Statevector.from_instruction(candidate_circuit)
assert reference_state.equiv(candidate_state)

reference_operator = Operator(reference_circuit)
candidate_operator = Operator(candidate_circuit)
assert reference_operator.equiv(candidate_operator)
```

`equiv()` accounts for global phase. Only construct dense operators for small circuits; memory grows as \(4^n\).

Remove final measurements before statevector comparison:

```python
unitary_part = measured_circuit.remove_final_measurements(
    inplace=False
)
```

Circuits with resets, measurements, or classical control need behavior-specific tests rather than unitary equivalence.

## Test Bit Ordering Explicitly

```python
def qiskit_bitstring_to_values(bitstring):
    return [
        int(bit)
        for bit in reversed(bitstring.replace(" ", ""))
    ]

assert qiskit_bitstring_to_values("10") == [0, 1]
```

Also test Pauli-label mapping:

```python
from qiskit.quantum_info import SparsePauliOp

operator = SparsePauliOp.from_list([("ZI", 1.0)])
assert operator.num_qubits == 2
# "ZI" means Z on qubit 1 and I on qubit 0.
```

This is especially important for optimization variables and graph vertices.

## Test Parameter Order and Shapes

```python
parameter_order = list(circuit.parameters)
assert parameter_values.shape[-1] == len(parameter_order)

stored_names = [parameter.name for parameter in parameter_order]
assert stored_names == expected_parameter_names
```

For every nontrivial PUB broadcast, assert the result shape:

```python
pub_result = estimator.run(
    [(circuit, observables, parameter_values)]
).result()[0]

assert pub_result.data.evs.shape == expected_shape
```

Do not rely on a visual reading of nested lists.

## Test Sampled Results Statistically

Never assert an exact count split from finite shots:

```python
counts = pub_result.data.meas.get_counts()
shots = sum(counts.values())

p_zero = counts.get("0", 0) / shots
assert abs(p_zero - 0.5) < 0.1
```

Choose tolerance from the expected binomial uncertainty and desired failure probability, not an arbitrary constant copied into every test.

For exact probability assertions, use `Statevector.probabilities_dict()` on a small unitary circuit:

```python
from qiskit.quantum_info import Statevector

probabilities = Statevector.from_instruction(
    unitary_circuit
).probabilities_dict()
```

## Test Estimator Values

```python
import numpy as np

actual = np.asarray(pub_result.data.evs)
np.testing.assert_allclose(
    actual,
    expected,
    rtol=1e-10,
    atol=1e-12,
)
```

Use tight tolerances only for exact local simulation. For noisy or hardware estimates, use a statistical test and report uncertainty.

## Test Transpilation

Check invariants, not a full textual snapshot:

```python
isa_circuit = pass_manager.run(circuit)

assert isa_circuit.num_qubits <= backend.num_qubits
assert isa_circuit.layout is not None
target_operations = set(backend.operation_names)
circuit_operations = set(isa_circuit.count_ops()) - {
    "barrier",
}
assert circuit_operations.issubset(
    target_operations
)
```

Control-flow and directive names may require target-aware handling; use target APIs for rigorous compatibility checks.

Track bounded structural regressions:

```python
def two_qubit_instruction_count(circuit):
    return sum(
        len(item.qubits) == 2
        for item in circuit.data
    )

assert isa_circuit.depth() <= depth_budget
assert (
    two_qubit_instruction_count(isa_circuit)
    <= two_qubit_budget
)
```

Compiler improvements can legitimately change exact circuit text and layout. Snapshot stable application metrics and broad budgets instead.

## Test Observable Layout

```python
isa_observable = observable.apply_layout(
    isa_circuit.layout
)
assert isa_observable.num_qubits == isa_circuit.num_qubits
```

For a small target, compare the logical expectation value and the compiled/mapped expectation value using a local Estimator.

Never submit a logical observable with a physically laid-out circuit.

## QPY Round-Trip Test

```python
from io import BytesIO
from qiskit import qpy

buffer = BytesIO()
qpy.dump(circuit, buffer)
buffer.seek(0)
loaded = qpy.load(buffer)[0]

assert loaded == circuit
```

Also test required metadata and parameter names. Newer Qiskit normally loads QPY written by older versions; older Qiskit is not expected to load newer QPY.

Do not use pickle as a fallback for untrusted data.

## Runtime Code Without QPU Jobs

Use:

- fake backends for `Target` and compilation tests,
- Aer for ideal/noisy execution,
- Runtime primitives in local-testing mode,
- `scripts/inspect_runtime.py` for read-only account/backend checks.

```python
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

backend = FakeSherbrooke()
```

Fake backend names can change. Choose one present in the pinned Runtime version.

## Show Deprecation Warnings

Run examples with warnings enabled:

```bash
python -W default scripts/run_local_primitives.py
```

For migration tests:

```bash
python -W error::DeprecationWarning your_test.py
```

Do not globally suppress deprecation warnings. Qiskit 2.x warnings identify code likely to break in Qiskit 3.0.

## Resource Guards

Before dense simulation:

```python
def statevector_bytes(num_qubits, bytes_per_complex=16):
    return (2 ** num_qubits) * bytes_per_complex

def density_matrix_bytes(num_qubits, bytes_per_complex=16):
    return (4 ** num_qubits) * bytes_per_complex
```

Set project-specific memory and qubit limits. Include parameter-sweep dimensions and number of observables when estimating total work.

Before Runtime:

- bound PUB count,
- bound shots or precision,
- account for twirling and mitigation expansion,
- bound optimizer iterations,
- set session or batch `max_time`,
- confirm plan allocation.

## Provenance Record

Store:

```python
from importlib.metadata import version
import platform
import sys

provenance = {
    "python": sys.version,
    "platform": platform.platform(),
    "qiskit": version("qiskit"),
    "qiskit_ibm_runtime": version(
        "qiskit-ibm-runtime"
    ),
    "backend": backend.name,
    "seed_transpiler": seed_transpiler,
    "seed_simulator": seed_simulator,
    "optimization_level": optimization_level,
    "primitive_options": primitive_options,
    "job_ids": job_ids,
}
```

Do not include API keys, saved-account dictionaries, full environments, headers, or tokens.

## Troubleshooting Matrix

### Invalid mixed Qiskit environment

Symptoms:

- import error mentioning an invalid environment,
- both `qiskit-terra` and modern `qiskit`,
- modules missing after an in-place upgrade.

Fix: create a fresh virtual environment and install `qiskit`, not `qiskit-terra`.

### `ImportError` for `Sampler` or `Estimator`

Use an explicit current implementation:

```python
from qiskit.primitives import (
    StatevectorEstimator,
    StatevectorSampler,
)
from qiskit_ibm_runtime import (
    EstimatorV2,
    SamplerV2,
)
```

### Result has no `.quasi_dists` or `.values`

The code expects V1 output. Use:

```python
counts = result[0].data.meas.get_counts()
expectation_values = result[0].data.evs
```

### Result has no `.data.meas`

Inspect register names:

```python
print([register.name for register in circuit.cregs])
print(pub_result.data)
```

Use `.data.<actual_register_name>`.

### Parameter/broadcast error

Print:

```python
print([parameter.name for parameter in circuit.parameters])
print(parameter_values.shape)
print(observables.shape if hasattr(observables, "shape") else type(observables))
```

Reduce to one circuit, one observable, and one parameter row, then rebuild the broadcast.

### Runtime rejects a non-ISA circuit

Compile with a pass manager generated from the exact backend object and submit its output.

### Wrong Estimator value after transpilation

Apply:

```python
isa_observable = observable.apply_layout(
    isa_circuit.layout
)
```

### `backend.configuration()` fails

Use BackendV2 direct attributes and `backend.target`.

### `qiskit.pulse` import fails

Pulse was removed in Qiskit 2.0. Use fractional gates for supported IBM rotations or Qiskit Dynamics for control-model research.

### Session is rejected

Open Plan users must use job or batch mode.

### Hardware and simulation disagree

Check:

1. bit order,
2. observable layout,
3. measurement basis,
4. simulator target and noise snapshot,
5. QPU calibration time,
6. primitive options and mitigation,
7. statistical uncertainty,
8. total shot allocation after twirling.

Do not tune a noise model solely to make one experiment match.

## Release Upgrade Test

When changing a Qiskit pin:

1. create a new environment,
2. run the environment checker,
3. run local primitive smoke tests,
4. run all deprecation warnings as errors,
5. round-trip representative QPY artifacts,
6. compare circuit semantics,
7. compare compiled structural budgets on pinned fake targets,
8. validate Runtime option models without submitting,
9. run one bounded noisy simulation,
10. only then schedule a minimal hardware smoke test.
