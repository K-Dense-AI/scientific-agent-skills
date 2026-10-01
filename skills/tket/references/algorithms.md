# Algorithms: Pauli Algebra, Expectation Values, ZX, Tableau, QFT/QPE

Circuits and boxes: `references/circuits.md`. Backends and results: `references/backends.md`.
Mitigation: `references/noise.md`. Executed against pytket 2.18.4 unless marked **illustrative**.

## Pauli algebra (`pytket.pauli`)

```python
import numpy as np
from pytket import Circuit, OpType, Qubit
from pytket.pauli import Pauli, QubitPauliString, QubitPauliTensor, PauliStabiliser, pauli_string_mult
from pytket.utils import QubitPauliOperator

q0, q1 = Qubit(0), Qubit(1)
Pauli.I.value, Pauli.X.value, Pauli.Y.value, Pauli.Z.value  # 0,1,2,3 -- int(Pauli.Z) raises
# `from pytket.pauli import I, X, Y, Z` are the SAME members (`I is Pauli.I` -> True).
s = QubitPauliString()                               # four constructor forms:
s = QubitPauliString(q0, Pauli.Z)                    # str(s) -> '(Zq[0])'
s = QubitPauliString([q0, q1], [Pauli.Z, Pauli.X])   # '(Zq[0], Xq[1])'; also ({q0: Z, q1: X})
s.map                       # PROPERTY -> dict[Qubit, Pauli];   s[q1] = Pauli.I works
s.compress()                # in place, returns None;   s.commutes_with(other) -> bool
s.to_sparse_matrix(2)       # scipy csc_matrix (4,4); also ([q1, q0])
s.dot_state(sv); s.state_expectation(sv)   # no .get_expectation_value(), no from_str
pauli_string_mult(QubitPauliString(q0, Pauli.X), QubitPauliString(q0, Pauli.Y))  # ('(Zq[0])', 1j)
t = QubitPauliTensor([q0, q1], [Pauli.X, Pauli.X], 0.25)   # 5 ctors: (coeff=1.0), (q,p,coeff),
t.coeff, t.string, t * t, 2.0 * t       # (0.25+0j)  # ([q],[p],coeff), (map,coeff), (string,coeff)
PauliStabiliser([Pauli.X, Pauli.X], 1)  # .string (list[Pauli]), .coeff; no __repr__
H = QubitPauliOperator({QubitPauliString([q0], [Pauli.Z]): 0.6,
                        QubitPauliString([q0, q1], [Pauli.X, Pauli.X]): 0.4})
H.get_dict(); H.all_qubits  # dict[QubitPauliString, Expr]; PROPERTY -> set[Qubit]
H[qps]; H + H; H - H; H * 2.0; H.to_sparse_matrix(2); H.state_expectation(sv)
H.subs({a: 0.5}); H.compress(abs_tol=1e-10)  # both return None -- IN PLACE
QubitPauliOperator.from_list(H.to_list()) == H   # True
```

`.to_dict()` was **removed in 1.0** — use `.map`. `QubitPauliString` has **no `__mul__`** — use
`pauli_string_mult(a, b) -> (QubitPauliString, complex)`. `from_OpenFermion`/`to_OpenFermion` were
also removed in 1.0:

```python
pauli_sym = {"I": Pauli.I, "X": Pauli.X, "Y": Pauli.Y, "Z": Pauli.Z}
def qpo_from_openfermion(openf_op):   # openf_op.terms -> {(qubit, pauli), ...: coeff}
    return QubitPauliOperator({QubitPauliString([Qubit(q) for q, _ in term],
        [pauli_sym[p] for _, p in term]): coeff for term, coeff in openf_op.terms.items()})
```

## Expectation values — three routes

```python
from pytket.utils import (get_operator_expectation_value, get_pauli_expectation_value,
                          expectation_from_counts, expectation_from_shots, append_pauli_measurement)
from pytket.partition import PauliPartitionStrat, GraphColourMethod
from pytket.extensions.qiskit import AerBackend

ansatz = Circuit(3).H(0).CX(0, 1).CX(1, 2).Rz(0.3, 2).CX(1, 2).CX(0, 1).H(0)
ham = QubitPauliOperator({
    QubitPauliString([Qubit(0)], [Pauli.Z]): 0.1,
    QubitPauliString([Qubit(0), Qubit(1), Qubit(2)], [Pauli.Y, Pauli.Z, Pauli.X]): 0.4,
    QubitPauliString([Qubit(0), Qubit(1)], [Pauli.X, Pauli.X]): 0.2})
b = AerBackend(); ca = b.get_compiled_circuit(ansatz)
ham.state_expectation(ansatz.get_statevector())   # Route 1 exact, no backend (O(2**n))
#                                                 -> (0.05877852522924734+0j)
# Route 2 module-level, shot-based: get_operator_expectation_value(state_circuit, operator,
#   backend, n_shots=None, partition_strat=None, colour_method=LargestFirst, **kwargs)
get_operator_expectation_value(ca, ham, b, n_shots=20000, seed=11)        # (0.05768+0j)
get_operator_expectation_value(ca, ham, b, n_shots=20000, seed=11,
    partition_strat=PauliPartitionStrat.CommutingSets,
    colour_method=GraphColourMethod.LargestFirst)                         # (0.05826+0j)
zz = QubitPauliString([Qubit(0), Qubit(1)], [Pauli.Z, Pauli.Z])  # Route 3 backend method:
bell = b.get_compiled_circuit(Circuit(2).H(0).CX(0, 1))          # state-exact, NO n_shots kwarg
b.get_operator_expectation_value(bell, QubitPauliOperator({zz: 1.0}))     # 1.0000000000000002
b.get_pauli_expectation_value(bell, zz)
b.supports_expectation, b.expectation_allows_nonhermitian                 # True, False
expectation_from_counts({(0, 0): 50, (1, 1): 50})                 # 1.0; uniform -> 0.0
expectation_from_shots(np.array([[0, 0], [1, 1]] * 10, dtype=np.uint8))   # 1.0
# -> 1 - 2*(odd-parity rate), in [-1,1], using EVERY classical bit.
circ = Circuit(2).H(0).CX(0, 1)
append_pauli_measurement(QubitPauliString([Qubit(0), Qubit(1)], [Pauli.X, Pauli.X]), circ)
circ.n_bits   # 2 -- mutates circ, creates Bit(0..k-1), H for X and Rx(0.5) for Y
# out-of-circuit qubit -> RuntimeError: Circuit does not contain unit with id: q[2]
```

All three routes agree. **`Backend.get_operator_expectation_value(state_circuit, operator,
valid_check=True)` takes NO `n_shots`** — passing one raises `TypeError`; use the module-level
function for shot-based values. A symbolic operator makes the module function raise `ValueError:
QubitPauliOperator contains unevaluated symbols.` — substitute first.

## Measurement reduction (`pytket.partition`)

Full treatment in `references/noise.md`. Minimal verified path:

```python
from pytket.partition import measurement_reduction, MeasurementBitMap

strings = [QubitPauliString([Qubit(0)], [Pauli.Z]),
           QubitPauliString([Qubit(0), Qubit(1)], [Pauli.X, Pauli.X]),
           QubitPauliString([Qubit(1)], [Pauli.Z])]
setup = measurement_reduction(strings, PauliPartitionStrat.CommutingSets,
                              GraphColourMethod.LargestFirst)
setup.verify()                    # True
len(setup.measurement_circs)      # 2 circuits from 3 strings (NonConflictingSets -> 3)
setup.results[strings[0]][0]      # MeasurementBitMap: .circ_index, .bits, .invert
full = []                         # measurement_circs are MEASUREMENT-ONLY: append to a
for mcirc in setup.measurement_circs:      # copy of the state circuit before running
    c = state_circuit.copy(); c.append(mcirc); full.append(c)
results = b.get_results(b.process_circuits(full, n_shots=20000, seed=11))

def term_expectation(result, bm):          # odd-parity formula, per MeasurementBitMap
    counts = result.get_counts(); n = sum(counts.values())
    odd = sum(cnt for bits, cnt in counts.items() if sum(bits[i] for i in bm.bits) % 2)
    return ((-1) ** bm.invert) * (-2 * odd / n + 1)
# Summing coeff * term_expectation over setup.results[s] reproduces get_operator_expectation_value
# exactly: 0.3247 (manual) == 0.3247 (module-level), exact 0.3236, for H = {Z(q0):0.6, X(q0)X(q1):0.4}
# on Circuit(2).H(0).CX(0,1).Rz(0.2,1), 20000 shots, seed=11.
```

`PauliPartitionStrat` = `NonConflictingSets | CommutingSets` **only**; `GraphColourMethod` =
`Lazy | LargestFirst | Exhaustive`. `get_operator_expectation_value` defaults to **LargestFirst**,
`measurement_reduction` to **Lazy**.

## Hand-built QFT and QPE (no native QFT)

`[n for n in dir(pytket.circuit_library) if "qft" in n.lower()]` is empty — build it (half-turns):

```python
from pytket.circuit import CircBox, DiagonalBox, QControlBox
from pytket.passes import DecomposeBoxes
from pytket.utils import compare_unitaries

def build_qft_circuit(n):
    qft = Circuit(n)
    for i in range(n):
        qft.H(i)
        for j in range(i + 1, n):
            qft.CU1(1 / 2 ** (j - i), j, i)
    for k in range(n // 2):
        qft.SWAP(k, n - k - 1)
    return qft

build_qft_circuit(3).n_gates                      # 7
outer = Circuit(3)                                # CircBox.dagger is a PROPERTY, not a method
outer.add_gate(CircBox(build_qft_circuit(3)).dagger, [0, 1, 2])
compare_unitaries(build_qft_circuit(3).get_unitary(), outer.get_unitary().conj().T)   # True

def build_qpe(n_meas, unitary_box, state_prep_box, n_target):
    qpe = Circuit()
    m = qpe.add_q_register("m", n_meas); p = qpe.add_q_register("p", n_target)
    qpe.add_gate(state_prep_box, list(p))
    ctrl_u = QControlBox(unitary_box, 1)
    for i in range(n_meas):
        qpe.H(m[i])
    for k in range(n_meas):                  # m[n_meas-k-1] controls U**(2**k); the naive
        for _ in range(2 ** k):              # power loop costs O(2**k) gates, so depth
            qpe.add_gate(ctrl_u, [m[n_meas - k - 1]] + list(p))   # explodes -- keep n_meas small
    qpe.add_gate(CircBox(build_qft_circuit(n_meas)).dagger, list(m))
    qpe.measure_register(m, "c")
    return qpe

u = DiagonalBox(np.array([1, 1, 1, np.exp(1j * np.pi / 8)], dtype=complex))
qpe = build_qpe(4, u, CircBox(Circuit(2).X(0).X(1)), 2)   # |11>, eigenvalue e^{i pi/8}
DecomposeBoxes().apply(qpe)                                # 6 qubits, 4 bits
# AerBackend, 200 shots, seed=4 -> Counter({(0, 0, 0, 1): 200}); theta = 1/16, deterministic.
```

## ZX calculus (`pytket.zx`)

**The pyzx names do not exist in pytket**: `full_reduce`, `spider_simp`, `clifford_simp`,
`gadget_simp`, `pivot_simp`, `zx_to_circuit`, `ZXDiagram.to_tensor`, `gflow`, `is_gflow`,
`has_gflow`, `get_vertices`, `get_wires`, `vertex_degree`, `set_phase`. Real API:

```python
from pytket.zx import (ZXDiagram, ZXType, ZXWireType, QuantumType, Rewrite, PhasedGen, Flow,
                       circuit_to_zx)

d = ZXDiagram(1, 1, 0, 0)                  # (n_in, n_out, n_open_in, n_open_out)
inp = d.get_boundary(ZXType.Input)[0]; out = d.get_boundary(ZXType.Output)[0]
v = d.add_vertex(ZXType.ZSpider, 0.25)
d.add_wire(inp, v); d.add_wire(v, out, ZXWireType.H)
d.check_validity()                         # every Input/Output vertex must have degree 1
d.vertices, d.wires                        # PROPERTIES -> list
d.n_vertices, d.n_wires, d.scalar          # ints, float
d.degree(v); d.neighbours(v); d.adj_wires(v); d.get_zxtype(v)     # methods
d.get_vertex_ZXGen(v).param                # PhasedGen; ZXGen is immutable, so:
d.set_vertex_ZXGen(v, PhasedGen(ZXType.ZSpider, 0.5, QuantumType.Quantum))
# ZXType: Input, Output, Open, ZSpider, XSpider, Hbox (lowercase b), XY, XZ, YZ, PX, PY, PZ,
#         Triangle, ZXBox.   ZXWireType: Basic, H.   QuantumType: Quantum, Classical.
```

`Rewrite` exposes exactly **20 static constructors** plus `apply`/`sequence`/`repeat` (`apply(diag)`
mutates in place, returns `bool`):

| Category | Rewrites |
|---|---|
| Decomposition into generating sets | `decompose_boxes`, `basic_wires`, `rebase_to_zx`, `rebase_to_mbqc` |
| Into graphlike form | `red_to_green`, `spider_fusion`, `self_loop_removal`, `parallel_h_removal`, `separate_boundaries`, `io_extension` |
| Reduction within graphlike form | `remove_interior_cliffords`, `remove_interior_paulis`, `gadgetise_interior_paulis`, `merge_gadgets`, `extend_at_boundary_paulis` |
| MBQC | `extend_for_PX_outputs`, `internalise_gadgets` |
| Composite sequences | `to_graphlike_form`, `reduce_graphlike_form`, `to_MBQC_diag` |

Two upstream caveats, verbatim: rewrites "expect the inputs to be of a particular form", so applying
them to diagrams not in that form (especially classical or mixed) "may cause some issues"; and passes
"may not track the global scalar", so "semantics of diagrams is only preserved up to scalar".
`tket/pytket/tests/zx_diagram_test.py` needs `final = final * 0.5 * 1j` to match the original —
**never compare ZX tensors to circuit unitaries without renormalising**.

```python
from pytket.passes import AutoRebase, ZXGraphlikeOptimisation, RemoveRedundancies, FullPeepholeOptimise

c = Circuit(2).H(0).CX(0, 1).Rz(0.25, 1).CX(0, 1)
AutoRebase({OpType.Rz, OpType.Rx, OpType.X, OpType.Z, OpType.H, OpType.CX, OpType.CZ}).apply(c)
diag, boundary_map = circuit_to_zx(c)    # (ZXDiagram, dict[UnitID, tuple[ZXVert, ZXVert]])
for rw in (Rewrite.to_graphlike_form(), Rewrite.reduce_graphlike_form(), Rewrite.to_MBQC_diag()):
    rw.apply(diag)                       # extraction is #P-hard in general, needs MBQC form
out, vert_to_unit = diag.to_circuit()    # (Circuit, dict[ZXVert, UnitID]); 12 gates here
compare_unitaries(c.get_unitary(), out.get_unitary())   # ALWAYS verify -- extraction can inflate
fl = Flow.identify_pauli_flow(diag)      # works on an MBQC diagram -> Flow
fl.d(v); fl.c(v); fl.odd(v, diag)        # int / list / list; also .dmap, .cmap, .focus
Flow.identify_focussed_sets(diag)        # -> list
# Flow.identify_causal_flow(diag) needs ALL measured vertices to be XY, else
#   RuntimeError: Causal flow is only defined when all measured vertices are XY
#   (or RuntimeError: ZXDiagram must be in MBQC form to identify causal flow, if not MBQC).
```

`circuit_to_zx` accepts only a gate subset — **rebase first**. The **only** ZX pass is
`ZXGraphlikeOptimisation(allow_swaps=True)` (no `passes.ZXPass`); it needs the circuit to already
satisfy `GateSetPredicate {H, noop, SWAP, Rz, Rx, X, Z, CX, CZ}`, else `RuntimeError: Predicate
requirements are not satisfied: GateSetPredicate:{ ... }`. Verified on
`Circuit(5).CCX(0,1,4).CCX(2,4,3).CCX(0,1,4)`: raw `(3 gates, depth 3)` → `AutoRebase` `(45, 31)` →
`ZXGraphlikeOptimisation` `(85, 56)` → `RemoveRedundancies()` + `FullPeepholeOptimise()` `(51, 36)`,
`compare_unitaries` True throughout — ZX **inflated** and peephole recovered, so run peephole
**after** extraction and judge ZX inside the whole sequence. ZX wins on Clifford-dense / phase-gadget
structure and T-count reduction; it loses on already-good circuits. `pytket.zx.tensor_eval`
(`tensor_from_quantum_diagram`, `unitary_from_quantum_diagram`, `tensor_from_mixed_diagram`,
`density_matrix_from_cptp_diagram`, `unitary_from_classical_diagram`,
`fix_inputs_to_binary_state`, `fix_outputs_to_binary_state`, `fix_boundaries_to_binary_states`) needs
the `[zx]` extra (quimb / numba / autoray); without it the import warns *"Missing package for tensor
evaluation of ZX diagrams. Run pip install 'pytket[ZX]'."*

## Tableau / stabiliser (`pytket.tableau`)

Real names: `UnitaryTableau`, `UnitaryRevTableau`, `UnitaryTableauBox` — **not**
`Tableau`/`TableauBox`/`tableau_to_circuit`/`circuit_to_tableau`.

```python
from pytket.tableau import UnitaryTableau, UnitaryRevTableau, UnitaryTableauBox

tab = UnitaryTableau(2)                    # ctors: (nqb) / (xx,xz,xph,zx,zz,zph) / (circuit)
tab.apply_gate_at_end(OpType.CX, [Qubit(0), Qubit(1)])
tab.apply_gate_at_front(OpType.H, [Qubit(0)])
tab.get_xrow(Qubit(0)); tab.get_zrow(Qubit(0)); tab.get_row_product(qpt)  # -> QubitPauliTensor
tab.to_circuit()                           # NOT gate-count optimised
UnitaryTableau(Circuit(3).H(0).CX(0, 1).V(1)).to_circuit().n_gates  # 16 from a 3-gate Clifford
box = UnitaryTableauBox(tab); Circuit(2).add_gate(box, [0, 1]).n_gates   # 1; box.get_tableau()
n = 2                        # six-array ctor: xx, xz, zx, zz are bool (*,*) order='F';
I = np.eye(n, dtype=bool, order="F"); Zr = np.zeros((n, n), dtype=bool, order="F")
ph = np.zeros(n, dtype=bool, order="C")            # xph, zph are bool (*,) order='C'
compare_unitaries(UnitaryTableau(I, Zr, ph, Zr, I, ph).to_circuit().get_unitary(), np.eye(4))  # True
# wrong row assignment -> ValueError: Rows of tableau do not (anti-)commute as expected
```

Row semantics: `UnitaryTableau` satisfies `P U = U X_qb`; `UnitaryRevTableau` satisfies `U P = X_qb U`.
Only **unparameterised Clifford** OpTypes apply — otherwise `RuntimeError: Cannot be applied to a
SymplecticTableau: not a Clifford gate: Rx`. For Clifford optimisation prefer `passes.CliffordSimp` /
`Transform.OptimiseCliffords` over `to_circuit()`.

## Assertions

`ProjectorAssertionBox` (OpType 110) and `StabiliserAssertionBox` (OpType 111), applied via
**`Circuit.add_assertion(...)`** — there is no `pytket.circuit.Assertion`.

```python
from pytket.circuit import BasisOrder, ProjectorAssertionBox, StabiliserAssertionBox

bell = Circuit(2).H(0).CX(0, 1)
proj = np.zeros((4, 4), dtype=complex, order="F")        # F-order ndarray
proj[1, 1] = proj[2, 2] = proj[1, 2] = proj[2, 1] = 0.5  # |Bell><Bell|
bell.add_assertion(ProjectorAssertionBox(proj, basis=BasisOrder.ilo), [Qubit(0), Qubit(1)], name="bell")
anc = Circuit(3).H(0).CX(0, 1)      # stabiliser form: ancilla is a REQUIRED positional (3rd arg);
anc.add_assertion(StabiliserAssertionBox(["XX", "ZZ"]), [0, 1], 2, name="bell_stab")   # signed str ok
DecomposeBoxes().apply(bell)             # assertions are boxes -- synthesise before running
res = b.run_circuit(b.get_compiled_circuit(bell), n_shots=100, seed=3)
res.get_debug_info()                     # {'bell': 1.0}  -- assertion name -> success rate
```

Overloads (`circuit.pyi:1015`/`:1027`): `(ProjectorAssertionBox, qubits, ancilla=None, name=None)`
and `(StabiliserAssertionBox, qubits, ancilla, name=None)`; the stabiliser box takes
`Sequence[PauliStabiliser]` **or** `Sequence[str]`. Projectors are limited to 2×2 / 4×4 / 8×8; rank
> 2\*\*(n-1) needs an ancilla, else `RuntimeError: This assertion requires an ancilla`. Omitting the
stabiliser ancilla raises `TypeError: add_assertion(): incompatible function arguments.` The backend
must support mid-circuit measurement **and** reset (AerBackend does).

## Variational / differentiable work

**pytket-qujax** — *documented, not executed* (qujax/JAX absent from the build venv): **illustrative**.
`pip install pytket-qujax` (needs JAX); module `pytket.extensions.qujax`:

```python
from pytket.extensions.qujax import (tk_to_qujax, tk_to_qujax_args, tk_to_param,
                                     qujax_args_to_tk, print_circuit)
sim = tk_to_qujax(circuit, symbol_map=None, simulator="statetensor")  # |densitytensor|unitarytensor
gates, qubit_inds, param_inds = tk_to_qujax_args(circuit, symbol_map=None)
params = tk_to_param(circuit)     # NO qujax_to_tk / get_function / get_circuit
# symbol_map fixes parameter order; every gate must exist in qujax.gates; angles stay HALF-TURNS;
# measurements raise TypeError("Measurements not supported in qujax. ..."); Barrier is skipped.
# Gradients: jax.jit(jax.value_and_grad(lambda p: expect(sim(p)))) -- standard JAX.
```

`pytket-pennylane` is **archived**; the maintained packaged-VQE route is `pytket-qiskit` + Qiskit
primitives (`EstimatorV2`/`SamplerV2`) + `qiskit-algorithms` (`references/interop.md`). Compact HEA +
VQE loop (**illustrative** — compile once, substitute per iteration):

```python
from scipy.optimize import minimize
from sympy import Symbol

def hea(n, depth, params):
    c = Circuit(n); idx = 0
    for _ in range(depth):
        for q in range(n):                      # one rotation layer
            c.Ry(params[idx], q); c.Rz(params[idx + 1], q); idx += 2
        for q in range(n - 1):                  # one entangling layer
            c.CX(q, q + 1)
        c.add_barrier()                         # stops tket rearranging across layers
    return c

theta = [Symbol(f"t{i}") for i in range(2 * n_qubits * depth)]
compiled = backend.get_compiled_circuit(hea(n_qubits, depth, theta))   # compile ONCE
def objective(values):   # do NOT re-run FullPeepholeOptimise/PauliSimp inside the objective
    bound = compiled.copy()
    bound.symbol_substitution(dict(zip(theta, values / np.pi)))        # radians -> half-turns
    return backend.get_operator_expectation_value(bound, ham).real
result = minimize(objective, x0, method="COBYLA")
```

## Ansatz sequencing and entanglement swapping

`gen_term_sequence_circuit` builds a **single Trotter step**; the docs recommend `CommutingSets` +
`Lazy` for sequencing (`NonConflictingSets` is for measurement reduction):

```python
from pytket.utils import gen_term_sequence_circuit
trot = gen_term_sequence_circuit(ham, Circuit(3), partition_strat=PauliPartitionStrat.CommutingSets,
                                 colour_method=GraphColourMethod.Lazy)
# reference_state.copy() + one CircBox per commuting set. The identity term becomes
# add_phase(-coeff / 2) INSIDE its CircBox; the outer circuit's .phase stays 0.0.
```

`TermSequenceBox` takes a **list of `(paulis, coeff)` tuples, NOT a `QubitPauliOperator`** (an
operator raises `TypeError`): `TermSequenceBox([([Pauli.X, Pauli.X], 0.25), ([Pauli.Z, Pauli.I],
0.5)])`, defaults `synthesis_strategy=PauliSynthStrat.Sets`, `cx_config_type=CXConfigType.Tree`. For
UCC use `Transform.UCCSynthesis(PauliSynthStrat.Sets, CXConfigType.Tree)`. **`TermSequenceBox` +
`PauliSynthStrat.Greedy` does not preserve global phase.** Entanglement swapping / teleportation uses
mid-circuit measurement + feed-forward via `condition=` (verified to build):

```python
qtel = Circuit()
a = qtel.add_q_register("a", 2); bq = qtel.add_q_register("b", 1); d = qtel.add_c_register("d", 2)
qtel.H(a[1]); qtel.CX(a[1], bq[0]); qtel.CX(a[0], a[1]); qtel.H(a[0])
qtel.Measure(a[0], d[0]); qtel.Measure(a[1], d[1])
for cv, gate in [(2, "X"), (3, "X"), (1, "Z"), (3, "Z")]:   # little-endian feed-forward
    getattr(qtel, gate)(bq[0], condition_bits=[d[0], d[1]], condition_value=cv)
# (n_qubits=3, n_bits=2, n_gates=10). Reuse on other registers: tel = qtel.copy();
# tel.rename_units({...}); es.append(tel); es.add_gate(OpType.Reset, [...]) to recycle a qubit.
```

## Verify your compiled circuit

```python
from pytket.passes import FullPeepholeOptimise
from pytket.utils.stats import gate_counts

c = Circuit(4).CCX(0, 1, 3).CX(1, 2).Rz(0.37, 2).CCX(0, 1, 3).H(0).CX(2, 3)
o = c.copy(); FullPeepholeOptimise().apply(o)
compare_unitaries(c.get_unitary(), o.get_unitary())            # True
np.allclose(c.get_statevector(), o.get_statevector())          # True
gate_counts(c)[OpType.CX], gate_counts(o)[OpType.CX]           # 2, 14 -- FPO EXPANDED the CCXs
c.depth(), o.depth(), c.n_gates, o.n_gates                     # 4, 24, 6, 30
a1 = Circuit(1).Rx(0.5, 0); a2 = a1.copy(); a2.add_phase(0.5)  # compare_* IGNORE global phase:
compare_unitaries(a1.get_unitary(), a2.get_unitary())          # True
np.allclose(a1.get_unitary()[:, 0], a2.get_unitary()[:, 0])    # False -- a fixed column catches it
```

"Optimisation" can **inflate** a circuit — report gate/depth counts alongside the equivalence check.

## Circuit "partitioning" clarification

`pytket.partition` is **Pauli measurement reduction, NOT circuit cutting**. `Partition`, `SubCircuit`,
`partition_circuit`, `subcircuits_to_circboxes` return **0 matches** repo-wide (pytket-1.x API used by
the external CutQC project). The native equivalent is a manual `CircBox` split → per-chunk optimise →
reassemble → verify (`get_commands()` is topological, not source order):

```python
original = Circuit(4).CX(0,1).Rz(0.3,1).CX(1,2).H(3).CX(2,3).Rx(0.7,0).CX(3,0)
cmds = original.get_commands(); cuts = [3, 5]; bounds = [0, *cuts, len(cmds)]
chunks, orderings = [], []
for lo, hi in zip(bounds, bounds[1:]):
    used = sorted({u for cmd in cmds[lo:hi] for u in cmd.args}, key=str)
    orderings.append(used)
    to_local = {orig: Qubit(i) for i, orig in enumerate(used)}
    sub = Circuit(len(used))               # rebuild the slice on local indices
    for cmd in cmds[lo:hi]:
        sub.add_gate(cmd.op, [to_local[u] for u in cmd.args])
    chunks.append(sub)                     # optimise each chunk here
rebuilt = Circuit(4)
for sub, used in zip(chunks, orderings):
    rebuilt.add_circbox(CircBox(sub), list(used))
DecomposeBoxes().apply(rebuilt)
compare_unitaries(original.get_unitary(), rebuilt.get_unitary())   # True; 7 gates
```

For genuinely large circuits use **`pytket-cutensornet`** (Linux + NVIDIA): `GeneralState`
(`.get_amplitude`, `.sample`, `.expectation_value`), `CuTensorNetStateBackend` /
`CuTensorNetShotsBackend`, `MPSxGate`/`MPSxMPO`/`TTNxGate`, `simulate()`.

## Gotchas / rules

- `QubitPauliString`: **no `__mul__`** (use `pauli_string_mult`), **no `.to_dict()`** (use `.map`;
  removed in 1.0); read `Pauli` via `.value`. `QubitPauliTensor` **does** support `*`.
  `QubitPauliOperator.subs()`/`.compress()` mutate in place and return `None`.
- `Backend.get_operator_expectation_value` takes **no `n_shots`** (state-exact, `TypeError`
  otherwise); the module-level `get_operator_expectation_value(..., n_shots=...)` is the shot route.
- `measurement_reduction` circuits are measurement-only — **append** them to a copy of the state
  circuit. Its default colour method is `Lazy`; the expectation helper's is `LargestFirst`.
- `gen_term_sequence_circuit` is **one** Trotter step; the identity term's phase lands inside its
  CircBox, not on the outer `.phase`. `TermSequenceBox` takes `(paulis, coeff)` tuples, and `Greedy`
  synthesis drops global phase.
- No native QFT and no random-circuit generator (`references/circuits.md`). `CircBox(...).dagger` is
  a **property**; naive controlled-power QPE costs O(2**k) gates.
- The pyzx API is **not** the pytket API. ZX rewrites may not track the global scalar (renormalise
  before comparing), extraction needs `to_MBQC_diag()` first and can inflate gate counts, and peephole
  passes go **after** extraction. `ZXGraphlikeOptimisation` needs a pre-rebased circuit.
- `pytket.tableau` classes are `UnitaryTableau`/`UnitaryRevTableau`/`UnitaryTableauBox`;
  `to_circuit()` is not gate-count optimised; only unparameterised Clifford gates apply.
- Assertions go through `Circuit.add_assertion`; the stabiliser form needs `ancilla` as a required
  positional; read results with `BackendResult.get_debug_info()`; the backend must support mid-circuit
  measurement **and** reset.
- `get_unitary()` is O(4ⁿ), `get_statevector()` is O(2ⁿ). `compare_unitaries`/`compare_statevectors`
  ignore global phase — use `np.allclose` on a fixed column when relative phase matters, and report
  gate/depth counts because "optimising" passes can inflate a circuit.
- `pytket.partition` is measurement reduction, **not** circuit cutting; use `pytket-cutensornet` for
  large-circuit simulation. pytket-qujax keeps half-turns and cannot represent measurements;
  `pytket-pennylane` is archived — route maintained VQE through `pytket-qiskit`.

## Sources

- <https://quantinuum.github.io/tket/latest/manual/manual_pauli.html> ·
  <https://quantinuum.github.io/tket/latest/manual/manual_expectation.html> ·
  <https://quantinuum.github.io/tket/latest/manual/manual_zx.html> ·
  <https://quantinuum.github.io/tket/latest/manual/manual_stabiliser.html>
- Repo (tket @ `d2bb207981244205cbf9ddc9ef0257112c366558`): `tket/pytket/docs/pauli.md`, `zx.md`,
  `tableau.md`; `tket/pytket/pytket/utils/expectations.py`, `term_sequence.py:30-76`;
  `tket/pytket/pytket/_tket/circuit.pyi` (`add_assertion` `:1015`/`:1027`);
  `tket/pytket/tests/zx_diagram_test.py` (the `final * 0.5 * 1j` scalar caveat).
- Executed against pytket 2.18.4 / pytket-qiskit 0.78.0 / numpy 2.5.3 / sympy 1.14.0. The `[zx]`
  extra and pytket-qujax were **not** installed — ZX tensor-eval and qujax snippets are documented,
  not executed.
