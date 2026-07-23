# Target-Aware Transpilation

Transpilation rewrites an abstract circuit into an **instruction set architecture (ISA) circuit** that satisfies a specific backend `Target`:

- only supported instructions,
- valid qubit operands and connectivity,
- backend timing and control-flow constraints,
- an explicit virtual-to-physical qubit layout.

IBM Runtime V2 primitives require ISA circuits. They do not perform layout, routing, and basis translation automatically.

## Recommended Entry Point

Use a preset staged pass manager:

```python
from qiskit.transpiler import generate_preset_pass_manager

pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1,
    seed_transpiler=17,
)
isa_circuit = pass_manager.run(circuit)
```

The pass manager can be reused for circuits targeting the same backend snapshot:

```python
isa_circuits = pass_manager.run(circuits)
```

`qiskit.transpile()` remains a convenient wrapper, but a pass manager is easier to reuse, inspect, and customize.

## The BackendV2 Target

`backend.target` is the source of supported operations and constraints:

```python
print("backend:", backend.name)
print("qubits:", backend.num_qubits)
print("operations:", sorted(backend.operation_names))
print("coupling map:", backend.coupling_map)
print("target:", backend.target)
```

Do not use these removed or legacy BackendV1 access patterns:

```python
# Do not use in Qiskit 2.x code:
# backend.configuration().basis_gates
# backend.properties()
# BackendProperties
```

For a synthetic target:

```python
from qiskit.transpiler import CouplingMap, Target

target = Target.from_configuration(
    basis_gates=["cz", "sx", "rz"],
    coupling_map=CouplingMap.from_line(5),
)
pass_manager = generate_preset_pass_manager(
    target=target,
    optimization_level=1,
    seed_transpiler=17,
)
isa_circuit = pass_manager.run(circuit)
```

Prefer one coherent `backend` or `target`. Combining a backend with separate `basis_gates` or `coupling_map` inputs creates competing sources of truth and is discouraged.

## Preset Optimization Levels

| Level | Typical intent |
|---:|---|
| 0 | Minimal transformation needed to satisfy the target |
| 1 | Light optimization with relatively low compilation cost |
| 2 | More optimization and search |
| 3 | Heavier optimization and search; highest classical cost |

Higher does not guarantee a better experimental result. Compare levels using the same circuit, target snapshot, and seed:

```python
compiled = {}
for level in (0, 1, 2, 3):
    manager = generate_preset_pass_manager(
        backend=backend,
        optimization_level=level,
        seed_transpiler=17,
    )
    compiled[level] = manager.run(circuit)
```

Start with levels 1 and 3 for a bounded comparison. Evaluate target-native two-qubit operations, depth, estimated duration when available, and downstream result quality.

## Transpiler Stages

A preset `StagedPassManager` has six conceptual stages:

1. **init**: validate and synthesize high-level operations.
2. **layout**: map virtual qubits to physical qubits.
3. **routing**: add routing operations to satisfy connectivity.
4. **translation**: convert to target-supported instructions.
5. **optimization**: simplify and resynthesize the target circuit.
6. **scheduling**: apply hardware-aware timing passes when configured.

Qiskit 2.x scheduling does not restore `qiskit.pulse`; that module was removed.

Inspect the generated manager:

```python
print(pass_manager)
print(pass_manager.property_set)
```

The property set is primarily a pass-development and debugging interface; do not build long-term application logic around undocumented keys.

## Layouts and Observables

Transpilation can permute logical qubits. Estimator observables must be mapped to the final physical layout:

```python
from qiskit.quantum_info import SparsePauliOp

observable = SparsePauliOp.from_list([("ZZ", 1.0)])
isa_circuit = pass_manager.run(circuit)
isa_observable = observable.apply_layout(isa_circuit.layout)
```

Submit the mapped observable:

```python
pub = (isa_circuit, isa_observable, parameter_values)
```

Do not manually guess the permutation from a circuit drawing. Use `isa_circuit.layout`.

For a list of observables:

```python
isa_observables = [
    observable.apply_layout(isa_circuit.layout)
    for observable in observables
]
```

## Parameterized Workloads

Transpile the parameterized circuit once:

```python
parameterized_isa = pass_manager.run(parameterized_circuit)
isa_observable = observable.apply_layout(parameterized_isa.layout)

for values in optimizer_values:
    pub = (parameterized_isa, isa_observable, [values])
    result = estimator.run([pub], precision=0.03).result()[0]
```

This avoids repeated layout and routing. Retranspile only when the circuit structure, target, selected backend feature set, or compilation strategy changes.

## Initial Layouts

Use an explicit layout only when calibration analysis or a reproducibility requirement justifies it:

```python
pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=2,
    initial_layout=[3, 5, 8],
    seed_transpiler=17,
)
```

An explicit layout bypasses the preset layout-selection logic. Confirm every physical qubit and interaction is supported by the target.

## Approximate Synthesis

`approximation_degree` trades unitary fidelity for potentially cheaper circuits:

```python
pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=3,
    approximation_degree=0.99,
    seed_transpiler=17,
)
```

Treat approximation as an experimental parameter. Compare ideal-unitary error, native two-qubit count, and hardware outcome. Do not describe `0.99` as a universal one-percent error bound for the whole algorithm.

## Reproducibility

Set the transpiler seed explicitly:

```python
pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=3,
    seed_transpiler=17,
)
```

Qiskit 2.5 also supports `QISKIT_TRANSPILER_SEED`, but an explicit argument is clearer in reproducible code.

Record:

- Qiskit version,
- backend name and target/calibration timestamp if available,
- optimization level,
- seed,
- all non-default pass-manager arguments,
- input and output QPY artifacts,
- output layout and structural metrics.

A fixed seed stabilizes stochastic compiler choices; it does not freeze changing backend calibration data or package behavior across releases.

## Analyze Compiled Circuits

```python
def two_qubit_instruction_count(circuit):
    return sum(
        len(item.qubits) == 2
        for item in circuit.data
    )

print("logical depth:", circuit.depth())
print("ISA depth:", isa_circuit.depth())
print("ISA size:", isa_circuit.size())
print("ISA operations:", isa_circuit.count_ops())
print("two-qubit instructions:", two_qubit_instruction_count(isa_circuit))
print("layout:", isa_circuit.layout)
```

Count all two-qubit instructions rather than only `cx`; current targets may use `cz`, `ecr`, `rzz`, or other operations.

Circuit metrics are proxies. Calibration-aware quality depends on which physical qubits and operations were selected.

## Verify ISA Compatibility

Runtime rejects circuits that do not satisfy the target. A practical preflight is:

1. Compile using the exact backend.
2. Confirm the compiled width fits `backend.num_qubits`.
3. Inspect every instruction name and qubit tuple against `backend.target`.
4. Submit only the pass-manager output.

For advanced validation, use target APIs rather than a hardcoded basis list.

## Fake Backends and Aer

Test target-aware compilation without consuming QPU time:

```python
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

fake_backend = FakeSherbrooke()
pass_manager = generate_preset_pass_manager(
    backend=fake_backend,
    optimization_level=1,
    seed_transpiler=17,
)
isa_circuit = pass_manager.run(circuit)
```

Fake-backend availability can change between Runtime releases. List the installed fake-provider exports rather than assuming an old tutorial backend exists.

For an Aer noise model derived from a real backend:

```python
from qiskit_aer import AerSimulator

noisy_simulator = AerSimulator.from_backend(backend)
simulator_pass_manager = generate_preset_pass_manager(
    backend=noisy_simulator,
    optimization_level=1,
    seed_transpiler=17,
)
simulator_circuit = simulator_pass_manager.run(circuit)
```

An Aer model is an approximation of the calibration data used to create it; it is not a faithful predictor of every QPU effect.

## Dynamic Circuits and Fractional Gates

Backend capabilities can depend on how the backend is requested:

```python
backend = service.backend(
    backend_name,
    use_fractional_gates=True,
)
```

Fractional-gate support and dynamic-control support have evolved across Runtime versions. Inspect the returned target and current feature-compatibility documentation instead of assuming both are available for every backend and option combination.

If a circuit uses `if_else`, `while_loop`, `switch_case`, `for_loop`, or classical expressions:

- confirm the operations are present in `backend.operation_names`,
- compile against that returned backend object,
- check mitigation and fractional-gate compatibility,
- test the full branch behavior.

## Custom Pass Managers

Customize only after measuring a limitation in preset output:

```python
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import RemoveBarriers

cleanup = PassManager([RemoveBarriers()])
cleaned = cleanup.run(circuit)
```

For target-aware custom pipelines, use `StagedPassManager` or modify a generated preset stage. Every custom transformation must preserve circuit semantics, parameters, control flow, and global phase as appropriate.

Write regression tests based on operator/state equivalence for small circuits and application-level outputs for larger circuits.

## Common Failures

- **Circuit not ISA-compatible**: submit the pass-manager output, not the abstract input.
- **Wrong expectation value**: map the observable through `isa_circuit.layout`.
- **Too many routing operations**: compare layout methods, seeds, initial layouts, and circuit connectivity.
- **Compilation is slow**: lower the optimization level or reduce repeated transpilation.
- **BackendV1 attribute error**: replace `configuration()` and `properties()` access with BackendV2 target and direct attributes.
- **Unknown instruction**: inspect the exact backend target; do not use a generic basis copied from another device.
- **Dynamic-circuit rejection**: verify target control-flow operations and incompatible backend feature flags.
- **Non-reproducible comparison**: fix the seed and backend snapshot, and store all compiler settings.
