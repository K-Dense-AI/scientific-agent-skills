# Circuit transformations

Target: Cirq 1.7.0. The examples below use small unitary circuits so equivalence
can be checked exactly. For measurement/feed-forward circuits, validate outcome
semantics separately; a unitary comparison does not apply.

## Compile and simplify

```python
import cirq
import numpy as np
import networkx as nx

qubits = list(cirq.LineQubit.range(3))
q0, q1, q2 = qubits
circuit = cirq.Circuit(cirq.H(q0), cirq.CNOT(q0, q2), cirq.T(q1))
compiled = cirq.optimize_for_target_gateset(circuit, gateset=cirq.CZTargetGateset())
cirq.testing.assert_allclose_up_to_global_phase(
    cirq.unitary(circuit), cirq.unitary(compiled), atol=1e-7
)

@cirq.transformer
def optimization_pipeline(circuit, *, context=None):
    circuit = cirq.merge_single_qubit_gates_to_phxz(circuit, context=context)
    circuit = cirq.drop_negligible_operations(circuit, context=context, atol=1e-8)
    circuit = cirq.eject_z(circuit, context=context)
    return cirq.drop_empty_moments(circuit, context=context)

optimized = optimization_pipeline(circuit)
cirq.testing.assert_allclose_up_to_global_phase(
    cirq.unitary(circuit), cirq.unitary(optimized), atol=1e-7
)
print("Moments:", len(circuit), "->", len(optimized))
```

Compilation to a gateset does not ensure device connectivity. A validation
`Gateset` is not necessarily a `CompilationTargetGateset`; choose a compiler
explicitly, or use the device's advertised `compilation_target_gatesets`. Preserve
routing maps, then compile and call `device.validate_circuit`.

Dropping tiny rotations is approximate and its error accumulates; set a tolerance
appropriate to the full circuit, not just an individual gate. Gate count and
moment count are useful diagnostics, not a substitute for calibrated duration.

## Custom transformers that preserve the circuit

Do not delete arbitrary Z gates or replace H with Ry(pi/2) alone. The latter needs
a Z first: matrix multiplication gives Ry(pi/2) Z = H.

```python
@cirq.transformer(add_deep_support=True)
class HToZRy:
    def __call__(self, circuit, *, context=None):
        def map_op(op, _):
            # Only untagged exact H; fractional H powers and controls are unchanged.
            if op.gate == cirq.H and not op.tags:
                q = op.qubits[0]
                return [cirq.Z(q), cirq.ry(np.pi / 2)(q)]
            return op

        ignored = () if context is None else context.tags_to_ignore
        return cirq.map_operations_and_unroll(circuit, map_op, tags_to_ignore=ignored)

transformed = HToZRy()(circuit)
cirq.testing.assert_allclose_up_to_global_phase(
    cirq.unitary(circuit), cirq.unitary(transformed), atol=1e-7
)
```

## Analytical two-qubit compilation

Use the public matrix compiler rather than manually reconstructing KAK
interaction angles. The input is a 4x4 two-qubit unitary, not a 2x2 matrix.

```python
def compile_two_qubit_unitary(unitary, qubits):
    if len(qubits) != 2 or np.shape(unitary) != (4, 4):
        raise ValueError("Expected two qubits and a 4x4 unitary")
    return cirq.Circuit(cirq.two_qubit_matrix_to_cz_operations(
        qubits[0], qubits[1], unitary, allow_partial_czs=False
    ))

matrix = cirq.unitary(cirq.FSimGate(theta=0.31, phi=0.17))
decomposed = compile_two_qubit_unitary(matrix, [q0, q1])
cirq.testing.assert_allclose_up_to_global_phase(matrix, cirq.unitary(decomposed), atol=1e-7)
```

For custom decomposable gates implement `_decompose_`; confirm the resulting
unitary against an independent target matrix (for example `cirq.CCNOT`).
`cirq.decompose` returns operations; wrap them in `cirq.Circuit` when needed.

## Routing and final qubit permutations

```python
graph = nx.path_graph(qubits)
router = cirq.RouteCQC(graph)
routed, initial_map, final_swap_map = router.route_circuit(circuit)
cirq.testing.assert_circuits_have_same_unitary_given_final_permutation(
    routed, circuit.transform_qubits(initial_map), final_swap_map
)
assert all(len(op.qubits) < 2 or graph.has_edge(*op.qubits)
           for op in routed.all_operations())
```

`initial_map` maps logical inputs to physical qubits; `final_swap_map` records the
final physical permutation. The final position of logical `q` is
`final_swap_map[initial_map[q]]`. Preserve this when adding readout after routing
or comparing states. If readout was already part of the routed circuit, its
measurement keys/order travel with it; do not blindly permute results again.

RouteCQC requires multi-qubit operations to have been decomposed to at most two
qubits (including nested circuit operations as documented). For directed graphs,
also check the final native gate directions. Manually inserting SWAPs without
updating subsequent operations changes the algorithm.

## Measurement transformations

- `cirq.drop_terminal_measurements(circuit)` removes eligible terminal
  measurements, to inspect the pre-measurement state.
- `cirq.dephase_measurements(circuit)` replaces measurements with dephasing
  channels for ensemble density-matrix calculations. It does not align or move
  measurements and does not produce readout samples.
- Classical controls need `cirq.defer_measurements` before dephasing; deferral
  introduces ancillas, which changes memory requirements and output support.

Never remove operations merely because they are after a measurement. Reset,
feed-forward, and repeated measurements can be essential parts of the algorithm.

## Google device example, entirely local

```python
import cirq_google as cg

device = cg.Sycamore
routed, initial_map, final_swap_map = cirq.RouteCQC(
    device.metadata.nx_graph
).route_circuit(circuit)
compiled_for_device = cirq.optimize_for_target_gateset(
    routed, gateset=cg.SycamoreTargetGateset()
)
device.validate_circuit(compiled_for_device)
```

The bundled Sycamore model is useful for local topology checks; it does not
establish access or describe every currently assigned Google processor.

Sources: [transformers](https://quantumai.google/cirq/transform/transformers),
[RouteCQC](https://quantumai.google/reference/python/cirq/RouteCQC),
[two-qubit compilation](https://quantumai.google/reference/python/cirq/two_qubit_matrix_to_cz_operations),
[dephasing measurements](https://quantumai.google/reference/python/cirq/dephase_measurements).
