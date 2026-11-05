# Circuits: Construction, Gates, Classical Logic, Boxes, Inspection

`Circuit` is a DAG of `Command`s over named `Qubit`/`Bit` units. Everything below was executed against
pytket 2.18.4. QASM/Quipper/SDK converters: `references/interop.md`. `Backend` API and result objects:
`references/backends.md`. Passes: `references/compilation.md`.

## Creating circuits

```python
from pytket import Bit, Circuit, OpType, Qubit
from pytket.unit_id import BitRegister, QubitRegister, UnitID   # UnitID is NOT in pytket

c = Circuit()                  # empty; grow with registers/wires
c = Circuit(4)                 # 4 qubits, default register "q"
c = Circuit(4, 2)              # + 2 classical bits, default register "c"
c = Circuit(2, 2, "my_circ")   # named; Circuit(n_qubits=2, n_bits=3, name="mine") also works

qreg = c.add_q_register("q", 3)   # -> QubitRegister;  creg = c.add_c_register("c", 3)
c.get_q_register("q") == qreg     # True; also get_c_register, .q_registers, .c_registers
ob = Bit("o")
c.add_bit(ob)                     # returns None -- keep your own handle
c.add_qubit(Qubit("ancilla"))     # returns None too
c.is_simple                       # PROPERTY: True only while default registers alone
c.flatten_registers()             # renames everything into "q"/"c"; is_simple -> True
c.rename_units({Qubit(0): Qubit("z", 0)})          # -> bool
c.add_blank_wires(2); c.remove_blank_wires()       # remove -> (n_removed, [UnitID, ...])
```

`Qubit(0) == Qubit("q", 0)` and `Bit(0) == Bit("c", 0)` — the default registers are literally `q`/`c`;
both subclass `UnitID`. Re-adding an existing wire name raises `RuntimeError`. Counts are a
**property/method split**:

```python
c.n_qubits, c.n_bits, c.n_gates, c.phase           # PROPERTIES (no parentheses)
c.n_1qb_gates(), c.n_2qb_gates(), c.n_nqb_gates(3) # METHODS
c.depth(), c.depth_2q(), c.depth_by_type(OpType.CX)  # METHODS; depth_by_type also takes a set
hasattr(c, "width")                                # False -- Circuit.width() does NOT exist
c.qubit_readout, c.bit_readout, c.qubit_to_bit_map  # {} until you measure
```

On `Circuit(3).H(0).CX(0,1).Rz(0.25,2).measure_all()`: `n_1qb_gates()==2`, `n_2qb_gates()==1`,
`n_gates==6` (measurements count), `n_bits==3`, `depth()==3`, `depth_2q()==1`,
`depth_by_type(OpType.CX)==1`, `depth_by_type({OpType.CX, OpType.CZ})==2`; the readout maps become
`{q[0]: 0, q[1]: 1}` / `{c[0]: 0, c[1]: 1}` / `{q[0]: c[0], q[1]: c[1]}`. `depth()` ignores
`OpType.Barrier`.

## Gate set and the angle convention

**All rotation angles are half-turns (multiples of π), never radians.** `tket/pytket/docs/optype.md:6`:
*"All parametrised OpTypes which take angles (e.g. Rz, CPhase, FSim) expect parameters in multiples of
pi (half-turns)."* Verified:

```python
import math
Circuit(1).Rx(0.5, 0).get_commands()[0].op.params   # [0.5]  == Rx(pi/2)
Circuit(1).Rx(0.5, 0).get_statevector()             # [0.7071+0j, -0.7071j]
half_turns = radians / math.pi                      # the only conversion you need
```

Passing radians **fails silently**: the circuit builds, compiles, runs, returns counts — and every
amplitude is wrong. This is the single most common pytket bug. Angles also canonicalise into `[0, r)`
at construction, so read-back params can differ: `Circuit(1).PhasedX(-0.1, 0.5, 0)` reads back
`params == [3.9, 0.5]`.

Signature shape is **parameters first, then qubits** (controls before target); `opgroup=` and
`condition*` kwargs last. Every method below was called successfully:

```python
c = Circuit(4)
# fixed single-qubit
c.H(0); c.X(0); c.Y(0); c.Z(0); c.S(0); c.Sdg(0); c.SX(0); c.SXdg(0); c.T(0); c.Tdg(0); c.V(0); c.Vdg(0)
# parametrised single-qubit: TK1 is the universal family; GPI/GPI2 are IonQ-native
c.Rx(0.25,0); c.Ry(0.25,0); c.Rz(0.25,0); c.U1(0.5,0); c.PhasedX(0.1,0.5,0); c.GPI(0.2,0); c.GPI2(0.2,0)
c.U3(0.1,0.2,0.3,0); c.TK1(0.1,0.2,0.3,0)
# two-qubit: standard, controlled, hardware-native, TK2 universal family
c.CX(0,1); c.CY(0,1); c.CZ(0,1); c.CH(0,1); c.CV(0,1); c.CSX(0,1); c.SWAP(0,1)
c.CRx(0.25,0,1); c.CRy(0.25,0,1); c.CRz(0.25,0,1); c.CU1(0.25,0,1); c.CU3(0.1,0.2,0.3,0,1)
c.ZZMax(0,1); c.ZZPhase(0.25,0,1); c.XXPhase(0.25,0,1); c.YYPhase(0.25,0,1); c.XXPhase3(0.25,0,1,2)
c.ECR(0,1); c.ISWAPMax(0,1); c.ISWAP(0.25,0,1); c.ESWAP(0.25,0,1); c.Sycamore(0,1)
c.PhasedISWAP(0.1,0.2,0,1); c.FSim(0.1,0.2,0,1); c.AAMS(0.1,0.2,0.3,0,1); c.TK2(0.1,0.2,0.3,0,1)
# three-qubit, multi-controlled (controls first, target last), directives
c.CCX(0,1,2); c.CSWAP(0,1,2)
c.add_gate(OpType.CnX, [0,1,2,3]); c.add_gate(OpType.CnRy, 0.5, [0,1,2,3])
c.add_gate(OpType.noop, [0]); c.add_barrier([0,1]); c.Measure(0,0); c.Reset(0)
```

`XXPhase3` takes **three qubits** despite the `XXPhase` name; `AAMS` takes **three angles**.
`CU1(λ) != CRz(λ)` — verified, their unitaries differ. `add_gate` returns the circuit, so it chains.
`Op.create(OpType.Rz, 0.3)` → `Rz(0.3)`, `Op.create(OpType.H)` → `H`, and it canonicalises too:
`Op.create(OpType.PhasedX, [-0.1, 0.5]).params` → `[3.9, 0.5]`.

Inspection returns **read-only copies**, in **topological order, not insertion order**:

```python
c = Circuit(3); c.CX(1, 2); c.H(0); c.CX(0, 1)
[str(cmd) for cmd in c.get_commands()]   # H q[0] moved FIRST -- a valid topological sort
cmd = c.get_commands()[0]
cmd.op, cmd.op.type, cmd.args, cmd.qubits, cmd.bits, cmd.opgroup
cmd.op.get_name()                        # 'Measure' for a Measure command
c.H(0, opgroup="mine")                   # tag commands for later substitution
cmd.op = None                            # AttributeError: property has no setter
```

## Measurements and classical logic

```python
c = Circuit(2)
c.H(0).CX(0, 1).measure_all()   # creates bits if absent
c.n_bits, c.qubit_readout       # 2, {q[0]: 0, q[1]: 1}
c.Measure(0, 0)                          # qubit 0 -> bit 0
qreg = c.add_q_register("q", 2)
c.measure_register(qreg, "c")            # creates register "c" if needed
c.Measure(0, 0); c.Reset(0)              # mid-circuit measurement + reset
```

Conditions are kwargs on **any** gate method, and `condition_value` is **little-endian** over
`condition_bits`. Registers also support `+ - * // << >>` inside `logic_exp` expressions:

```python
from pytket.circuit.logic_exp import (if_bit, if_not_bit, reg_eq, reg_neq,
                                      reg_lt, reg_gt, reg_leq, reg_geq)
c.X(q[0], condition_bits=[d[0], d[1]], condition_value=3)   # both bits set
c.H(q[0], condition=a[0])                                   # single bit == 1
c.X(q[0], condition=if_not_bit(a[2])); c.Y(q[3], condition=if_bit(a[1]))
c.Z(q[1], condition=(a[0] & a[1]) | a[2])                   # bit algebra
c.H(q[2], condition=reg_eq(a, 3)); c.CX(q[2], q[3], condition=reg_gt(a, 3))
```

Backend support varies sharply: `QuantinuumBackend` takes the full expression set, Qiskit/Aer accept
only whole-register equality. Check before relying on it.

```python
c.add_c_setreg(3, ra); c.add_c_setbits([True, False], [ra[0], ra[1]])
c.add_c_copyreg(ra, rb); c.add_c_copybits([ra[2]], [rb[1]])
c.add_c_and(ra[0], ra[1], ob)      # (arg0_in, arg1_in, arg_out); likewise add_c_or / add_c_xor
c.add_c_not(ra[0], ob); c.add_c_range_predicate(1, 5, ra.to_list(), ob)
c.add_c_setreg(3, rb, condition=reg_gt(ra, 1))    # classical ops are conditional too
```

### `ClExpr` — the pytket 2.0 replacement for `ClassicalExpBox`

`ClassicalExpBox` / `add_classicalexpression` were **removed in pytket 2.0** (migrate old dicts with
`pytket.utils.serialization.migration.circuit_dict_from_pytket1_dict`). There is **no `ClBit`/`ClReg`
class**, and `ClOp` is an **enum, not callable** — build `ClExpr(op=..., args=[...])` where args nest
`ClExpr`, `ClBitVar(i)`, `ClRegVar(i)`, or plain ints:

```python
from pytket.circuit import ClBitVar, ClExpr, ClOp, ClRegVar, WiredClExpr, add_clexpr_from_logicexp

expr = ClExpr(op=ClOp.RegSub, args=[ClExpr(op=ClOp.RegAdd, args=[ClRegVar(0), 3]), ClBitVar(0)])
wexpr = WiredClExpr(expr, bit_posn={0: 0}, reg_posn={0: [2, 0]}, output_posn=[2, 0])
c.add_clexpr(wexpr, c.bits)                 # positions index into this args list
type(c.get_commands()[0].op).__name__       # 'ClExprOp'
c.add_clexpr_from_logicexp(ra ^ rb, rc.to_list())   # convenience from a logic_exp expression
```

`WiredClExpr.to_dict()`/`.from_dict()` round-trip. `ClOp` members: `Bit{And,Eq,Neq,Not,One,Or,Xor,Zero}`
and `Reg{Add,And,Div,Eq,Geq,Gt,Leq,Lsh,Lt,Mul,Neg,Neq,Not,One,Or,Pow,Rsh,Sub,Xor,Zero}`. QASM export
needs `header="hqslib1"` (`references/interop.md`).

### WASM

```python
from pytket.wasm import WasmFileHandler, WasmModuleHandler
wf = WasmFileHandler("functions.wasm")     # (filepath, check_file=True, int_size=32)
wm = WasmModuleHandler(wasm_bytes)         # raw bytes, same defaults
c.add_wasm("my_func", wf, list_i=[3], list_o=[3], args=[ra.to_list(), rb.to_list()])
c.add_wasm_to_reg("my_func", wf, list_i=[ra], list_o=[rb])
```

Every entry in `list_i`/`list_o` must be `<= int_size` (default 32). QASM round-tripping WASM needs
`circuit_from_qasm_str_wasm` / `circuit_from_qasm_str_wasmmh`.

## Composing circuits and boxes

```python
a = Circuit(2, 2).CX(0, 1).measure_all(); b = Circuit(2).H(0)
a.append(b)            # IN PLACE, returns None; unit ids must match
c = a >> b             # sequential composition -> NEW Circuit
d = a * b              # parallel (tensor) composition -> NEW Circuit
main = Circuit(3)
main.add_circuit(Circuit(2).Z(0).CZ(1, 0), [1, 2])       # (circuit, qubits, bits=[])
sub = Circuit(2).X(0).X(1)
sub.rename_units({Qubit(0): Qubit("s", 0), Qubit(1): Qubit("s", 1)})
main.add_circuit_with_map(sub, {Qubit("s", 0): main.qubits[0], Qubit("s", 1): main.qubits[2]})
c2 = a.copy(); a.transpose(); inv = a.dagger()   # Circuit.dagger is a METHOD
```

`*` requires **disjoint** unit ids, else `RuntimeError: Cannot merge circuits as both contain unit:
q[0]`. `add_circuit_with_map` with a partial map on default-register ids raises `RuntimeError: Unit
already exists in circuit: q[1]` — rename the sub-circuit first, or map every unit. `Circuit.dagger()`
is a method; `CircBox.dagger` and `Op.dagger` are **properties**.

### Boxes

All boxes live in `pytket.circuit` and must be decomposed with `passes.DecomposeBoxes()` before
hardware — **`Circuit.decompose_boxes()` does not exist**.

```python
import numpy as np
from pytket.circuit import (CircBox, ConjugationBox, CustomGateDef, DiagonalBox, DummyBox, ExpBox,
    MultiplexedRotationBox, MultiplexedU2Box, MultiplexedTensoredU2Box, MultiplexorBox, PauliExpBox,
    PauliExpPairBox, PauliExpCommutingSetBox, PhasePolyBox, QControlBox, StatePreparationBox,
    TermSequenceBox, ToffoliBox, Unitary1qBox, Unitary2qBox, Unitary3qBox)   # all verified
from pytket.pauli import Pauli

c.add_circbox(CircBox(Circuit(2).CX(0, 1)), [0, 1])   # or c.add_gate(box, [0, 1])
c.add_unitary1qbox(Unitary1qBox(np.eye(2, dtype=complex)), 0)      # 2qBox / 3qBox likewise
c.add_unitary2qbox(Unitary2qBox(np.eye(4, dtype=complex)), 0, 1)   # 3 qubits is the hard cap
c.add_state_preparation_box(StatePreparationBox(np.array([1,0,0,0], dtype=complex)), [0, 1])
c.add_gate(DiagonalBox(np.array([1, 1, 1, 1j], dtype=complex)), [0, 1])
c.add_expbox(ExpBox(np.asfortranarray(A4), 0.25), 0, 1)   # e^{itA}; A4 is 4x4 complex128
c.add_gate(PauliExpBox([Pauli.X, Pauli.Y, Pauli.Y, Pauli.Z], -0.2), [0, 1, 2, 3])
c.add_gate(QControlBox(CircBox(Circuit(2).CX(0, 1)), 1), [2, 0, 1])   # controls FIRST
c.add_gate(QControlBox(Op.create(OpType.X), 2, [True, False]), [0, 1, 2])
c.add_gate(ConjugationBox(CircBox(Circuit(2).H(0)), CircBox(Circuit(2).CX(0, 1))), [0, 1])
c.add_gate(DummyBox(2, 0, Circuit(2).CX(0, 1).get_resources()), [0, 1])
```

Constructors that differ from the obvious guess (all verified): `ToffoliBox(n_qubits, permutation,
strat=..., rotation_axis=OpType.Ry)` with `permutation` a map `Sequence[bool] -> Sequence[bool]`
(`ToffoliBox(2, {(True,False): (False,True)})`); `MultiplexorBox({(False, False): CircBox(...),
(True, True): CircBox(...)})` — keys are `Sequence[bool]`, values must be `Op`;
`DummyBox(n_qubits, n_bits, resource_data)`; `PhasePolyBox(n_qubits, {Qubit(0): 0, Qubit(1): 1},
{(True, True): 0.5}, np.eye(2, dtype=bool, order="F"))` or `PhasePolyBox(circuit)`.
`ExpBox(A, t)` builds `e^{itA}` — verified against `scipy.linalg.expm(1j * t * A)`, so **`t` is radians
here, not half-turns**; the `.pyi` wants `order='F'`, so pass `np.asfortranarray(A)`. `PauliExpBox`
needs distinct qubits: repeating one raises `RuntimeError: Multiple operation arguments reference q[0]`.

```python
c.add_circbox_regwise(box, [qreg], [creg])
c.add_circbox_with_regmap(box, {"a": "q"}, {})     # BOTH maps required; pass {} when empty
ok = c.substitute_named(Circuit(1).Z(0), "grp1")   # -> bool; signature must match exactly

from sympy import symbols
a, b = symbols("a b")
gate_def = CustomGateDef.define("MyCRx", Circuit(2).Rx(a, 0).CX(0, 1), [a])   # only `a` bound
c.add_custom_gate(gate_def, [0.2], [0, 1])
c.free_symbols()                                   # {b} -- b stayed free
```

`substitute_opgroup` does **not** exist, and a mismatched replacement raises `RuntimeError: Mismatched
signature for operation group`. `substitute_named` accepts `Op`, `Circuit`, `CircBox`,
`Unitary1qBox/2qBox/3qBox`, `ExpBox`, `PauliExpBox`, `ToffoliBox`, `DummyBox`, `QControlBox`,
`CustomGate`.

**`CircBox.symbol_substitution({...})` MUTATES the box**, and the change propagates to every circuit it
was added to (verified: two separate hosts both read back the new params after one call on the shared
box). Copy the box for independent bindings. `CircBox.get_circuit()` returns the inner circuit.

## Implicit qubit permutations

`CliffordSimp` and friends absorb `SWAP`s into wire relabelling instead of emitting gates. The result
is invisible in `get_commands()`, silently dropped by QASM export, and changes how `get_statevector()`
must be read.

```python
from pytket.passes import CliffordSimp, RemoveImplicitQubitPermutation

ip = Circuit(3).CX(0, 1).SWAP(0, 1).CX(1, 2)
CliffordSimp().apply(ip)                       # 3 gates -> 2
ip.has_implicit_wireswaps                      # PROPERTY (bool), NOT a method -- now True
ip.implicit_qubit_permutation()                # METHOD -> {q[0]: q[1], q[1]: q[0], q[2]: q[2]}
[str(cmd) for cmd in ip.get_commands()]        # no SWAP anywhere
ip.replace_implicit_wire_swaps()               # -> explicit SWAPs, flag False
RemoveImplicitQubitPermutation().apply(ip)     # same effect, as a pass
Circuit(2).SWAP(0, 1).replace_SWAPs()          # the reverse: gates -> permutation
```

Before QASM export or statevector comparison, remove the permutation explicitly.

## Symbolic circuits

```python
import math, sympy
from pytket.circuit import fresh_symbol

alpha, beta = sympy.symbols("alpha beta")     # or: alpha = fresh_symbol("alpha")
sc = Circuit(2).Rx(alpha, 0).YYPhase(beta, 0, 1)
sc.free_symbols()          # {alpha, beta} -- a set of sympy Symbols
sc.is_symbolic()           # True
sc.symbol_substitution({alpha: 0.5, beta: 2 * alpha})   # returns None, in place
sc.is_symbolic()           # STILL True -- substitution is SIMULTANEOUS, not recursive
sc.get_commands()[1].op.params   # [2*alpha] -- beta's value was not re-resolved
```

Substitute to numerics in one pass, or loop until `is_symbolic()` is `False`. Convert radians first:
`half_turns = radians / math.pi`. Every backend enforces `NoSymbolsPredicate`, so symbolic circuits
must be substituted before submission. Simulating one raises `RuntimeError: Error trying to simulate
circuit Rx(z) q[0]; ...`, and `get_operator_expectation_value` raises `ValueError: QubitPauliOperator
contains unevaluated symbols.` See `references/algorithms.md` for the compile-once pattern.

## Serialization

```python
d = c.to_dict();  Circuit.from_dict(d) == c      # exact round trip
j = c.to_json();  Circuit.from_json(j) == c      # JSON added in pytket 2.13
```

Prefer these over `pickle`. For QASM2 (the only QASM pytket speaks), Quipper, QIR, and every extension
converter, see **`references/interop.md`** — including the `hqslib1` requirement for complex classical
ops and what QASM export silently drops.

## Analysis and verification

```python
import numpy as np
from pytket.utils import (compare_statevectors, compare_unitaries, counts_from_shot_table, Graph,
    permute_basis_indexing, permute_qubits_in_statevector, permute_rows_cols_in_unitary,
    probs_from_counts, probs_from_state, readout_counts)
from pytket.utils.stats import gate_counts        # NOT re-exported from pytket.utils

c.n_gates_of_type(OpType.CX)                          # conditional gates excluded by default
c.n_gates_of_type(OpType.CX, include_conditional=True)
c.get_resources()
# ResourceData(op_type_count={OpType.H: ResourceBounds(1, 1), OpType.CX: ResourceBounds(1, 1), ...},
#              gate_depth=ResourceBounds(3, 3), op_type_depth={...},
#              two_qubit_gate_depth=ResourceBounds(1, 1))
c.phase                        # PROPERTY; c.add_phase(0.5). There is NO get_phase()
gate_counts(c)                 # Counter[OpType]
c.commands_of_type(OpType.CX); c.ops_of_type(OpType.CX)

# Statevector / unitary simulation, both ILO-BE (qubit 0 is the MOST significant bit)
sv = c.get_statevector()      # shape (2**n,), C-contiguous
u  = c.get_unitary()          # shape (2**n, 2**n), F-contiguous
c.get_unitary_times_other(np.eye(2 ** c.n_qubits))
Circuit(2).X(0).get_statevector()   # [0, 0, 1+0j, 0] -- index 2, i.e. |10> with q0 leftmost
compare_unitaries(u1, u2)        # bool; IGNORES global phase
compare_statevectors(sv1, sv2)   # bool; IGNORES global phase
permute_qubits_in_statevector(sv, [1, 0, 2, 3]); permute_rows_cols_in_unitary(u, [1, 0, 2, 3])
permute_basis_indexing(u, [1, 0, 2, 3])     # ILO-BE <-> DLO-BE
probs_from_state(sv); probs_from_counts({(0, 0): 50, (1, 1): 50})
counts_from_shot_table(np.array([[0, 0], [1, 1]], dtype=np.uint8))
readout_counts(ctr)        # Counter[OutcomeArray] -> Counter[tuple[int, ...]]; ONE argument
```

**`get_unitary()` is O(4ⁿ) and `get_statevector()` is O(2ⁿ)** — small circuits only. Above ~14 qubits,
sample from a backend instead (`references/backends.md`). DAG/graph views are graphviz-backed
(`graphviz` and `networkx` are core deps); there is no `Circuit.create_dag()` — a `Circuit` already is
a DAG. Use `pytket.utils.Graph`:

```python
g = Graph(c)
g.get_DAG(); g.get_qubit_graph()   # graphviz Digraph / connectivity Graph
g.save_DAG("dag.pdf"); g.view_DAG()
g.as_nx()                          # networkx MultiDiGraph
```

## Display

```python
from pytket.circuit.display import (CircuitDisplayConfig, CircuitRenderer, RenderOptions,
    get_circuit_renderer, render_circuit_as_html, render_circuit_jupyter, view_browser)

render_circuit_jupyter(circ)        # inline in Jupyter; accepts a list of circuits
view_browser(circ)                  # script mode; render_circuit_as_html(circ) -> str
renderer = get_circuit_renderer()
renderer.set_render_options(zx_style=True, condense_c_bits=False, dark_theme=True)
renderer.config.min_height = "300px"; renderer.save_render_options()
```

The renderer is HTML/JS (Vue), **not** graphviz, and by default loads its JS from the internet.
Offline: `pip install pytket-offline-display`, then `from pytket.extensions.offline_display import
render_circuit_jupyter`. There is **no** `pytket[visualization]` extra and **no** plain `render_circuit`;
graphviz backs `pytket.utils.Graph` only. For LaTeX, `circ.to_latex_file("c.tex")` emits a quantikz
`standalone` document (filename must end `.tex`).

## `pytket.circuit_library` — not a random-circuit library

A repo-wide grep for `RandomCircuit` returns **0 hits**; none of `CliffordRandomCircuit`,
`QuantumVolumeRandomCircuit`, `WStateRandomCircuit`, `SycamoreRandomCircuit`, `TK1RandomCircuit` exist.
The module is **108 public gate-decomposition builders** — what `AutoRebase` draws on:

```python
from pytket.circuit_library import (BRIDGE, CCX, CCX_normal_decomp, C3X_normal_decomp, CX,
    CnX_vchain_decomp, CU1_using_CX, CRz_using_TK2, CX_using_AAMS, CX_using_ECR, CX_using_ISWAPMax,
    CX_using_XXPhase_0, CX_using_ZZMax, CX_using_ZZPhase, CX_using_flipped_CX, H_CZ_H, Rx_using_GPI,
    SWAP_using_CX_0, TK1_to_PhasedX, TK1_to_PhasedXRz, TK1_to_RzH, TK1_to_RzRx, TK1_to_RzSX,
    TK1_to_U3, TK2_using_3xCX, TK2_using_CX, X, approx_TK2_using_1xCX, approx_TK2_using_2xZZPhase,
    ladder_down, ladder_up)

CX_using_ZZMax().n_gates, TK2_using_CX(0.1, 0.2, 0.3).n_gates   # 7, 21
CnX_vchain_decomp(4).n_qubits, CX().n_gates                     # 6, 1
```

Random circuits: **no native generator**. The nearest thing is
`pytket.tailoring.PauliFrameRandomisation().sample_circuits(circ, 8)` — 8 Pauli-frame variants of a
circuit you already wrote (`references/noise.md`). Otherwise build them yourself. There is also **no
native QFT** — see `references/algorithms.md`.

## Gotchas / rules

- **Angles are half-turns.** Divide radians by `math.pi`. Radians fail silently. Sole exception:
  `ExpBox(A, t)` takes `t` in radians.
- `n_qubits`/`n_bits`/`n_gates`/`.phase`/`is_simple`/`has_implicit_wireswaps` are properties;
  `n_1qb_gates()`/`depth()`/`depth_2q()`/`depth_by_type()`/`implicit_qubit_permutation()` are methods.
  `Circuit.width()` and `Circuit.get_phase()` do not exist.
- `add_qubit`/`add_bit` return `None` — keep your own handle. `UnitID` comes from `pytket.unit_id`.
- `get_commands()` is a topological sort, not insertion order; `Command` objects are read-only copies.
- `CU1(λ) != CRz(λ)`. `XXPhase3` takes three qubits. `AAMS` takes three angles.
- `Circuit.dagger()` is a method; `CircBox.dagger` / `Op.dagger` are properties.
- `*` needs disjoint unit ids; `append` is in place and returns `None`; `>>` returns a new circuit.
- `add_circbox_with_regmap(box, qregmap, cregmap)` — both maps required; pass `{}` when empty.
- Boxes need `passes.DecomposeBoxes()` before hardware; `Circuit.decompose_boxes()` does not exist.
  Unitary boxes cap at 3 qubits.
- `CircBox.symbol_substitution` mutates the box and propagates to every host circuit.
- `symbol_substitution` is simultaneous, not recursive; loop until `is_symbolic()` is `False`. Every
  backend requires `NoSymbolsPredicate` — substitute before submitting.
- Implicit permutations are invisible in `get_commands()`, dropped by QASM export, and shift
  `get_statevector()` interpretation. Remove them explicitly.
- `substitute_opgroup` does not exist — use `substitute_named`, and match the signature exactly.
- `readout_counts` takes one argument. `gate_counts` lives in `pytket.utils.stats`.
- `get_unitary()` is O(4ⁿ), `get_statevector()` is O(2ⁿ). `compare_unitaries`/`compare_statevectors`
  ignore global phase; use `np.allclose` on a fixed column when relative phase matters.
- `pytket.circuit_library` is decompositions, not random circuits. `pytket.partition` is measurement
  reduction, not circuit cutting (`references/algorithms.md`).
- Display rendering needs internet unless `pytket-offline-display` is installed.

## Sources

- <https://quantinuum.github.io/tket/latest/manual/manual_circuits.html> ·
  <https://quantinuum.github.io/tket/latest/manual/manual_box.html> ·
  <https://quantinuum.github.io/tket/latest/manual/manual_conditional.html> ·
  <https://quantinuum.github.io/tket/latest/manual/manual_display.html> ·
  <https://quantinuum.github.io/tket/latest/api-docs/classCircuit.html> ·
  <https://quantinuum.github.io/tket/latest/api-docs/namespacepytket_1_1circuit__library.html>
- Repo (tket @ `d2bb207981244205cbf9ddc9ef0257112c366558`): `tket/pytket/docs/optype.md:6`,
  `docs/circuit.md`, `docs/classical.md`, `docs/display.md`;
  `tket/pytket/pytket/_tket/circuit.pyi` (`add_clexpr` `:845`, `add_circbox_with_regmap` `:875`,
  `add_expbox` `:919`, `add_custom_gate` `:1004`, `measure_all` `:1495`,
  `add_circuit`/`_with_map`/`append` `:1944`/`:1965`/`:1973`, `substitute_named` `:2217`–`:2327`);
  `tket/pytket/tests/clexpr_test.py:129-193`.
- Snippets executed against pytket 2.18.4 / pytket-qiskit 0.78.0 / numpy 2.5.3 / sympy 1.14.0.
  `pytket-qujax` and the `[zx]` extra were not installed in that environment.
