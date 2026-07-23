# Circuits, Parameters, Control Flow, and Serialization

## Circuit Data Model

`QuantumCircuit` stores ordered quantum bits, classical bits, instructions, parameters, global phase, metadata, and optional real-time classical control flow.

```python
from qiskit import QuantumCircuit

circuit = QuantumCircuit(3, 3, name="ghz")
circuit.h(0)
circuit.cx(0, 1)
circuit.cx(1, 2)
circuit.measure([0, 1, 2], [0, 1, 2])

print(circuit.num_qubits)
print(circuit.num_clbits)
print(circuit.depth())
print(circuit.count_ops())
```

Use explicit registers when result names or control-flow operands matter:

```python
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

qubits = QuantumRegister(2, "q")
syndrome = ClassicalRegister(1, "syndrome")
readout = ClassicalRegister(2, "readout")
circuit = QuantumCircuit(qubits, syndrome, readout)
```

Sampler V2 returns one data field per classical register, so meaningful register names improve result handling.

## Bit and Pauli Ordering

Qiskit uses little-endian conventions:

- Qubit 0 is conventionally the least-significant qubit.
- Count strings are printed most-significant classical bit first.
- The rightmost character of a Pauli label acts on qubit 0.
- Circuit diagrams normally draw qubit 0 at the top.

For a two-qubit operator, `"ZI"` applies `Z` to qubit 1 and identity to qubit 0. Never reverse strings based only on visual circuit order.

When translating a bitstring into graph vertices or variables, write and test an explicit conversion:

```python
def qiskit_bitstring_to_qubit_values(bitstring: str) -> list[int]:
    """Return values ordered as qubit/classical-bit 0, 1, ..."""
    return [int(bit) for bit in reversed(bitstring.replace(" ", ""))]
```

Spaces can appear between multiple classical registers in formatted count keys.

## Gates and Instructions

```python
from math import pi
from qiskit import QuantumCircuit

circuit = QuantumCircuit(3)

# One-qubit gates
circuit.x(0)
circuit.h(1)
circuit.s(1)
circuit.t(2)
circuit.rx(pi / 3, 0)
circuit.ry(pi / 4, 1)
circuit.rz(pi / 5, 2)

# Two- and three-qubit gates
circuit.cx(0, 1)
circuit.cz(1, 2)
circuit.swap(0, 2)
circuit.ccx(0, 1, 2)
```

Prefer high-level gates while constructing the algorithm. Let a target-aware transpiler translate them to the selected backend's instruction set.

Barriers are directives that constrain some transpiler reordering and optimization. Use them only when the experimental boundary matters, not as visual decoration:

```python
circuit.barrier(label="logical-boundary")
```

## Measurements and Resets

```python
from qiskit import QuantumCircuit

circuit = QuantumCircuit(2, 2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure([0, 1], [0, 1])
```

`measure_all()` adds measurements and, unless suitable classical bits already exist, creates a register named `meas`:

```python
circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure_all()
print([register.name for register in circuit.cregs])
```

Sampler requires measurement instructions for sampled classical output. Estimator generally uses circuits without final measurements.

Use `reset()` only when the execution target supports it:

```python
circuit.reset(0)
```

## Parameterized Circuits

Primitive PUBs are the preferred way to evaluate one parameterized circuit at many values.

```python
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector

theta = ParameterVector("theta", 3)
circuit = QuantumCircuit(3)
for qubit, parameter in enumerate(theta):
    circuit.ry(parameter, qubit)
circuit.cx(0, 1)
circuit.cx(1, 2)

parameter_order = list(circuit.parameters)
parameter_values = np.array(
    [
        [0.0, 0.0, 0.0],
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]
)

assert parameter_values.shape[-1] == len(parameter_order)
```

Do not assume that creation order and `circuit.parameters` order are interchangeable for arbitrary named parameters. Print or persist the order:

```python
print([parameter.name for parameter in circuit.parameters])
```

For debugging or APIs that require a bound circuit:

```python
bound = circuit.assign_parameters(
    dict(zip(parameter_order, parameter_values[0], strict=True))
)
```

For iterative primitive workloads, keep the circuit parameterized and pass values in the PUB instead of producing and transpiling a bound circuit on every iteration.

## Composition and Reuse

```python
from qiskit import QuantumCircuit

prepare = QuantumCircuit(2, name="prepare")
prepare.h(0)

entangle = QuantumCircuit(2, name="entangle")
entangle.cx(0, 1)

combined = prepare.compose(entangle)
```

Map qubits explicitly when composing circuits with different widths:

```python
larger = QuantumCircuit(4)
larger.compose(combined, qubits=[1, 3], inplace=True)
```

Convert a reusable unitary subcircuit to a gate or instruction:

```python
bell_prep = combined.to_gate(label="Bell prep")
outer = QuantumCircuit(2)
outer.append(bell_prep, [0, 1])
```

Circuits containing measurements or other non-unitary instructions cannot be converted to a `Gate`.

## Current Circuit-Library Constructors

Qiskit 2.x is moving from mutable blueprint classes to functions and gates that build concrete objects immediately.

```python
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate, efficient_su2, real_amplitudes

ansatz = efficient_su2(
    num_qubits=4,
    reps=2,
    entanglement="linear",
)

real_ansatz = real_amplitudes(
    num_qubits=4,
    reps=2,
    entanglement="reverse_linear",
)

qft = QuantumCircuit(4)
qft.append(QFTGate(4), range(4))
```

The old `QFT` blueprint class is deprecated as of Qiskit 2.1 and is scheduled for removal in Qiskit 3.0. Use `QFTGate` or `qiskit.synthesis.qft.synth_qft_full`.

Other current constructors include:

```python
from qiskit.circuit.library import (
    grover_operator,
    n_local,
    pauli_feature_map,
    zz_feature_map,
)
```

Check the current API before using a class copied from an older tutorial; several blueprint classes have function replacements.

## Dynamic Circuits and Classical Control

Qiskit expresses structured real-time control flow with context managers:

```python
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

qubit = QuantumRegister(1, "q")
flag = ClassicalRegister(1, "flag")
circuit = QuantumCircuit(qubit, flag)

circuit.h(qubit[0])
circuit.measure(qubit[0], flag[0])
with circuit.if_test((flag[0], True)):
    circuit.x(qubit[0])
```

Other structured builders include `if_test`, `while_loop`, `for_loop`, and `switch`.

Before executing dynamic circuits:

1. Confirm the selected backend target includes the required control-flow operations.
2. Transpile against that exact backend.
3. Check current compatibility among dynamic circuits, fractional gates, and mitigation options.
4. Test classical-register interpretation locally or on a fake backend.

Legacy `instruction.c_if(...)` patterns were removed in Qiskit 2.0.

## Circuit Inspection

```python
print("qubits:", circuit.num_qubits)
print("classical bits:", circuit.num_clbits)
print("parameters:", [parameter.name for parameter in circuit.parameters])
print("depth:", circuit.depth())
print("size:", circuit.size())
print("operations:", circuit.count_ops())
print("nonlocal gates:", circuit.num_nonlocal_gates())
```

These metrics are structural, not direct fidelity or cost estimates. Recompute them after target-aware transpilation.

## QPY Serialization

QPY preserves Qiskit circuits more faithfully than interchange formats intended for other tools:

```python
from pathlib import Path
from qiskit import qpy

path = Path("experiment.qpy")
with path.open("wb") as output_file:
    qpy.dump(circuit, output_file)

with path.open("rb") as input_file:
    loaded_circuits = qpy.load(input_file)

loaded = loaded_circuits[0]
```

QPY is forward-compatible: newer Qiskit releases can normally load older QPY files. Older releases are not expected to load QPY produced by newer versions.

Record the writing Qiskit version and retain source code for long-lived artifacts. Treat all external binary inputs as untrusted and enforce source, size, and version policies. Never substitute Python pickle for untrusted circuit data.

## OpenQASM Interchange

Use OpenQASM when interoperability is more important than preserving every Qiskit-specific object:

```python
from qiskit import qasm2, qasm3

qasm2_text = qasm2.dumps(circuit)
round_tripped = qasm2.loads(qasm2_text)

qasm3_text = qasm3.dumps(circuit)
```

OpenQASM 2 cannot represent all modern control-flow and classical-expression features. OpenQASM 3 import requires optional tooling and may not round-trip Qiskit metadata or custom instructions. Validate semantics after interchange.

## Common Circuit Mistakes

- **Wrong output register**: inspect `circuit.cregs` and use the corresponding Sampler result field.
- **Reversed interpretation**: account for count-string and Pauli-label ordering explicitly.
- **Parameter shape mismatch**: make the final value-array dimension equal `len(circuit.parameters)`.
- **Duplicate measurements**: use `remove_final_measurements()` before adding a new measurement scheme.
- **Estimator failure**: remove final measurements and non-unitary instructions.
- **Unsupported control flow**: inspect `backend.operation_names` and `backend.target`.
- **Circuit wider than target**: compare `circuit.num_qubits` with `backend.num_qubits` before transpiling.
- **Unexpected optimization across boundaries**: add a barrier only when that behavior is intentional.
