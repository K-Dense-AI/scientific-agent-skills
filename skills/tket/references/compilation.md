# Compilation

Compilation in TKET is a `SequencePass` of `BasePass` objects applied to a `Circuit`. Everything below is `pytket.passes` unless stated. Verified by execution against pytket 2.18.4 + pytket-qiskit 0.78.0. Backend helpers (`default_compilation_pass`, `get_compiled_circuit`, `valid_circuit`, `required_predicates`) → [references/backends.md](backends.md).

```python
from pytket import Circuit, OpType
from pytket.circuit import Node, Qubit, fresh_symbol
from pytket.architecture import Architecture, SquareGrid, RingArch, FullyConnected
from pytket.placement import GraphPlacement, LinePlacement, Placement
from pytket.mapping import LexiLabellingMethod, LexiRouteRoutingMethod
from pytket.transform import PauliSynthStrat, CXConfigType
from pytket.utils import gate_counts, compare_unitaries, prepare_circuit
```

## Mental model

Not Qiskit's `PassManager`: no DAG, no property set, no analysis/run split.

```python
changed = FullPeepholeOptimise().apply(circ)   # -> bool, MUTATES circ
```

- **Passes mutate in place.** `apply()` returns `True` when the pass *claims* it modified the circuit — not a guarantee (`PauliSimp().apply()` returned `True` twice on the same circuit) — and `False` when it is definitely unmodified.
- Nothing returns a new circuit except `backend.get_compiled_circuit()` (verified `compiled is not circ` → `True`). Copy first when the original matters: `compiled = circ.copy(); FullPeepholeOptimise().apply(compiled)`.
- Introspect with `p.get_preconditions()`, `p.get_postconditions()`, `p.get_gate_set() -> set[OpType] | None`. For `SynthesiseTket()` these are `[]`, `[GateSetPredicate:{TK1 Collapse CX Phase Measure Reset}, MaxTwoQubitGatesPredicate]`, `None`.
- `apply()` also takes `(circuit, before_apply, after_apply)` callbacks, each receiving `(CompilationUnit, config_dict)` where `config_dict` is the pass's own `to_dict()`.
- Serialise with `p.to_dict()` / `BasePass.from_dict(d, custom_deserialisation={...})`. `str(pass)` prints only `<tket::SequencePass>` — **use `.to_dict()` to inspect a pipeline**.
- `pytket.transform.Transform` is the lower level: same in-place semantics and `bool` return, no predicate checking. Compose with `>>`, `Transform.sequence([...])`, `Transform.repeat(t)`, `Transform.while_repeat(cond, body)`.

## The one-liner

```python
from pytket.extensions.qiskit import AerBackend

backend = AerBackend()
pipeline = backend.default_compilation_pass(optimisation_level=2)   # -> SequencePass
compiled = backend.get_compiled_circuit(circ, optimisation_level=2)
compiled_list = backend.get_compiled_circuits(circ_list, optimisation_level=1)
```

| Level | Semantics | AerBackend contents (verified via `to_dict()`) |
|---:|---|---|
| 0 | rebase to the backend gateset only | `DecomposeBoxes`, `AutoRebase` |
| 1 | + resynthesis | `DecomposeBoxes`, `SynthesiseTket` |
| 2 | **default**; + peephole optimisation | `DecomposeBoxes`, `FullPeepholeOptimise` |

**`default_compilation_pass` is abstract on `Backend`** — contents are per-extension, so never assume them. pytket-quantinuum also takes level 3 (`RemoveBarriers()` + `GreedyPauliSimp()`); Aer stops at 2. Level 2 can be very slow on large circuits. Level 0 can **inflate** gate counts, because satisfying connectivity costs gates: the user-guide example goes 13 → 22 at level 0 → 6 at level 2, and a 7-gate 4-qubit circuit reproduced that locally (level 0 → 8 gates / 5 CX vs level 1 → 7 / 5).

## Predicates

```python
from pytket.predicates import (
    GateSetPredicate, ConnectivityPredicate, MaxNQubitsPredicate, NoClassicalControlPredicate,
    NoFastFeedforwardPredicate, NoMidMeasurePredicate, NoSymbolsPredicate, DirectednessPredicate,
    PlacementPredicate, DefaultRegisterPredicate, MaxTwoQubitGatesPredicate, NoBarriersPredicate,
    NoClassicalBitsPredicate, NoWireSwapsPredicate, CliffordCircuitPredicate,
    CommutableMeasuresPredicate, NormalisedTK2Predicate, UserDefinedPredicate, MaxNClRegPredicate)

pred = GateSetPredicate({OpType.CX, OpType.Rz, OpType.SX, OpType.X, OpType.Measure})
pred.verify(circ)      # -> bool
pred.gate_set          # -> set[OpType]
pred.to_dict()         # -> {'allowed_types': ['CX'], 'type': 'GateSetPredicate'}
pred.implies(other)    # subset -> True, superset -> False (verified)
UserDefinedPredicate(lambda c: c.n_qubits <= 2).verify(circ)

for pred in backend.required_predicates:   # the manual diagnosis idiom
    if not pred.verify(circ):
        print(type(pred).__name__, "failed")
```

`DirectednessPredicate` **requires** an `Architecture` — bare `DirectednessPredicate()` raises `TypeError`. Verified `.verify()` on `Circuit(2).H(0).CX(0,1).measure_all()`: `NoBarriersPredicate`, `NoWireSwapsPredicate`, `CliffordCircuitPredicate`, `CommutableMeasuresPredicate`, `NoClassicalControlPredicate`, `NoFastFeedforwardPredicate`, `DefaultRegisterPredicate`, `NoMidMeasurePredicate`, `MaxTwoQubitGatesPredicate()` all `True`; `NoClassicalBitsPredicate` **False** (True only when nothing is measured); `PlacementPredicate(arc)` **False** until placed. Backend requirements are `backend.required_predicates` — a **list**, never `required_properties`. On `AerBackend()`: `['NoSymbolsPredicate', 'GateSetPredicate', 'MaxNQubitsPredicate']`; check all at once with `backend.valid_circuit(circ)`. **There is no `predicate.get_failure_reason()`** (`hasattr` → `False`), hence the loop above. Verified: a symbolic `Rx(a, 0).CX(0, 1)` fails only `NoSymbolsPredicate` (`valid_circuit` → `False`), while an ordinary measured Bell circuit passes all three.

## Rebases and squashing

TK1 and TK2 are TKET's universal gate families, angles in **half-turns** (multiples of π): `TK1(a,b,c) = Rz(a)·Rx(b)·Rz(c)` (any 1q unitary) and `TK2(a,b,c) = XXPhase(a)·YYPhase(b)·ZZPhase(c)` (any 2q unitary). Optimisation passes emit them; rebasing converts to native gates. `pytket.circuit_library` supplies the decompositions `AutoRebase` picks from (`CX_using_ZZMax`, `TK2_using_CX`, `TK1_to_RzRx`, `SWAP_using_CX_0/1`).

```python
from pytket.passes import (AutoRebase, AutoSquash, RebaseCustom, RebaseTket, RxFromSX,
                           SquashTK1, SquashRzPhasedX, SquashCustom)

AutoRebase({OpType.CZ, OpType.Rz, OpType.Rx}).apply(circ)  # raises if no decomposition
RebaseTket().apply(circ)      # -> {CX, TK1}
RxFromSX().apply(circ)        # SX -> Rx(0.5), SXdg -> Rx(-0.5)
SquashTK1().apply(circ)       # runs of 1q gates -> one TK1
SquashRzPhasedX().apply(circ) # Rz, NOT RZ
AutoSquash({OpType.Rz, OpType.Rx}).apply(circ)

gates = {OpType.Rz, OpType.Ry, OpType.CY, OpType.ZZPhase}
cx_in_cy = Circuit(2).Rz(0.5, 1).CY(0, 1).Rz(-0.5, 1)
def tk1_to_rzry(a: float, b: float, c: float) -> Circuit:
    return Circuit(1).Rz(c + 0.5, 0).Ry(b, 0).Rz(a - 0.5, 0)
RebaseCustom(gates, cx_in_cy, tk1_to_rzry)   # TK2 overload: RebaseCustom(gs, tk2_fn, tk1_fn)
SquashCustom({OpType.Rz, OpType.Ry}, tk1_to_rzry)   # verified output optypes: {CY, Ry, Rz}
```

`AutoSquash({OpType.Rz, OpType.Ry})` **raises** `RuntimeError: No known decomposition from TK1 to available gateset.` — a two-rotation set is not always squashable; use `SquashCustom`. **Do not use** (all confirmed absent from `pytket.passes` in 2.18.4) — use `AutoRebase(gateset)` / `AutoSquash(singleqs)` instead: `RebaseUFR`, `RebaseOQC`, `RebaseUMD`, `RebaseHQS` (removed 1.0.0); `SynthesiseOQC`, `SynthesiseUMD`, `SynthesiseHQS` (removed 1.27–2.0); `GlobalisePhasedX` (removed 2.0.0); `auto_rebase_pass()`, `auto_squash_pass()` (removed 1.36.0); `RebaseTK2`, `Transformations.auto_rebase` (never existed).

## Decomposition

```python
from pytket.passes import (
    DecomposeBoxes, DecomposeMultiQubitsCX, DecomposeSingleQubitsTK1, DecomposeTK2, NormaliseTK2,
    DecomposeArbitrarilyControlledGates, DecomposeClassicalExp, DecomposeSwapsToCXs,
    DecomposeSwapsToCircuit, KAKDecomposition, ThreeQubitSquash, CnXPairwiseDecomposition)

DecomposeBoxes(excluded_types=None, excluded_opgroups=None,
               included_types=None, included_opgroups=None).apply(circ)
KAKDecomposition(target_2qb_gate=OpType.CX, cx_fidelity=1.0, allow_swaps=True)
DecomposeSwapsToCXs(arch, respect_direction=False)
DecomposeSwapsToCircuit(Circuit(2).CX(0, 1).CX(1, 0).CX(0, 1))

c = Circuit(2).add_gate(OpType.TK2, [0.1, 0.2, 0.3], [0, 1])   # all steps verified
NormalisedTK2Predicate().verify(c)          # False
NormaliseTK2().apply(c)
NormalisedTK2Predicate().verify(c)          # True
DecomposeTK2(allow_swaps=True).apply(c)     # -> {CX, S, Sdg, TK1, V, Vdg}
```

`DecomposeBoxes` is a **pass** — `Circuit.decompose_boxes()` does not exist. `DecomposeSingleQubitsTK1` is **plural "Qubits"**. Three-qubit resynthesis is `ThreeQubitSquash` (verified CX 4 → 1), not `ThreeQubitGXX`. `DecomposeBridgedCX` does not exist — use `DecomposeSwapsToCXs` or `Transform.DecomposeBRIDGE`. TK2 must be normalised first.

`Transform` statics do the same work with no predicate checks — all verified present: `DecomposeBRIDGE`, `DecomposeBoxes`, `DecomposeCCX`, `DecomposeCXDirected(arch)`, `DecomposeControlledRys`, `DecomposeNPhasedX`, `DecomposeSWAP`, `DecomposeSWAPtoCX`, `DecomposeTK2`, `CommuteSQThroughSWAP`, `CommuteThroughMultis`; they return `False` when there is nothing to do.

## Architectures

```python
arch = Architecture([[0, 1], [1, 2], [2, 3]])   # 4 nodes, 3 edges: a line
arch.nodes; arch.coupling
arch.get_distance(n0, n3)        # 3
arch.get_adjacent_nodes(n1)      # {node[0], node[2]}
arch.valid_operation((n0, n1))   # True; (n0, n3) -> False
circ.valid_connectivity(arch, directed=False)
SquareGrid(2, 3)   # 6 nodes; squind_to_qind(1,2) -> 5; qind_to_squind(5) -> (1,2)
RingArch(5)        # 5 nodes
```

`Qubit` is a **logical** wire, `Node` a **physical** device qubit; both derive from `UnitID`. Placement renames `Qubit`s into `Node`s — that rename is what `cu.initial_map` / `cu.final_map` record.

**Traps:** `FullyConnected` is **NOT an `Architecture` subclass** (`isinstance(FullyConnected(4), Architecture)` → `False`), so it cannot be passed to placement or routing — build a fully connected `Architecture` instead. There is no `circuit.set_architecture()` and no `circuit.get_qubit_from_node()`: architecture belongs to the *passes*, not the circuit.

## Placement

```python
from pytket.passes import PlacementPass, NaivePlacementPass
from pytket.placement import place_with_map, place_fully_connected, NoiseAwarePlacement

placer = GraphPlacement(arch, maximum_matches=1000, timeout=1000,
                        maximum_pattern_gates=100, maximum_pattern_depth=100)
qmap = placer.get_placement_map(circ)     # -> dict[Qubit, Node]
maps = placer.get_placement_maps(circ, matches=100)
placer.place(circ)                        # in place -> bool
PlacementPass(placer).apply(circ)         # the pass form
NaivePlacementPass(arch).apply(circ)
LinePlacement(arch, maximum_line_gates=100, maximum_line_depth=100).place(circ)
Placement.place_with_map(circ, qmap)
```

Verified: after `PlacementPass(GraphPlacement(arch))` the qubits are `node[0..3]`, `PlacementPredicate(arch).verify(circ)` is `True`, and the map was `{q[0]: node[3], q[1]: node[2], q[2]: node[1], q[3]: node[0]}` — placement is free to relabel, which is why you need the maps. `place_with_map` and `place_fully_connected` are also **module-level functions** (`Placement` statics are exactly `from_dict`, `get_placement_map`, `get_placement_maps`, `place`, `place_with_map`, `to_dict`; `place_fully_connected` is **not** among them). `LinePlacement` may leave qubits in an `unplaced` register — check `circ.q_registers`.

**Do not use:** `TrivialPlacement`, `LargestFirstWLC`, `NoiseAwareQubitPlacement` (none exist; noise-aware placement is `NoiseAwarePlacement` → [references/noise.md](noise.md)). `Placement.modify_config` was removed in 2.0; the user-guide example calling it is stale.

## Routing / mapping

```python
from pytket.passes import (RoutingPass, DefaultMappingPass, FullMappingPass, CustomRoutingPass,
                            CXMappingPass, AASRouting, DelayMeasures, CNotSynthType)
from pytket.mapping import (MappingManager, LexiRouteRoutingMethod, MultiGateReorderRoutingMethod,
                             BoxDecompositionRoutingMethod, AASRouteRoutingMethod,
                             AASLabellingMethod, RoutingMethodCircuit)

RoutingPass(arch).apply(circ)                  # LexiLabelling + LexiRoute
DefaultMappingPass(arch, delay_measures=True)  # GraphPlacement + routing
CXMappingPass(arch, GraphPlacement(arch), directed_cx=False, delay_measures=True)
FullMappingPass(arch, GraphPlacement(arch), [LexiLabellingMethod(), LexiRouteRoutingMethod()])
CustomRoutingPass(arch, config).apply(circ)
AASRouting(arch, lookahead=1, cnotsynthtype=CNotSynthType.Rec).apply(circ)
MappingManager(arch).route_circuit(circ, [LexiLabellingMethod(), LexiRouteRoutingMethod()])
```

`CNotSynthType` lives in **`pytket.passes`**, not `pytket.circuit`; members `SWAP`, `HamPath`, `Rec`. **There is no `seed=` kwarg on routing passes** — `RoutingPass(arch, seed=3)` raises `TypeError`; routing is deterministic. The only seeded pass is `GreedyPauliSimp(seed=0, ...)`.

**Routing costs gates.** Verified — a 4-qubit circuit on a 4-node linear `Architecture`:

```python
arc = Architecture([[0, 1], [1, 2], [2, 3]])
orig = Circuit(4).H(0).CX(0, 3).CX(1, 3).Rz(0.3, 2).CX(2, 0)
cu = CompilationUnit(orig)
SequencePass([DecomposeBoxes(), FullPeepholeOptimise(), RoutingPass(arc),
              AutoRebase({OpType.CX, OpType.Rz, OpType.SX, OpType.X})]).apply(cu)
# CX: 3 -> 6   depth: 3 -> 8   ConnectivityPredicate(arc).verify(cu.circuit) -> True
```

That is why `optimisation_level=0` can inflate a gate count. Routing invalidates `NoMidMeasurePredicate` and `GateSetPredicate` (it inserts SWAPs and moves measurements), so follow with `DelayMeasures(allow_partial=True)` and a rebase or `SynthesiseTket`. All routing passes **ignore edge direction** — on a directed device check `DirectednessPredicate(arch)` and apply `Transform.DecomposeCXDirected(arch)`, or pass `directed_cx=True`. `CliffordSimp(allow_swaps=True)` can introduce implicit wire swaps: clear them with `RemoveImplicitQubitPermutation()` (which may itself create mid-circuit measurements) and inspect `circ.has_implicit_wireswaps` / `circ.implicit_qubit_permutation()`. **`NoiseAwareMappingPass` does not exist.**

## Optimisations

```python
from pytket.passes import (FullPeepholeOptimise, PeepholeOptimise2Q, CliffordSimp,
    CliffordResynthesis, CliffordPushThroughMeasures, RemoveRedundancies, SynthesiseTket,
    SynthesiseTK, PauliSimp, GreedyPauliSimp, PauliSquash, GuidedPauliSimp, PauliExponentials,
    OptimisePhaseGadgets, ComposePhasePolyBoxes, EulerAngleReduction, CommuteThroughMultis,
    ZZPhaseToRz, RoundAngles, RemovePhaseOps, RemoveBarriers, FlattenRegisters,
    FlattenRelabelRegistersPass, RenameQubitsPass, RemoveImplicitQubitPermutation)

FullPeepholeOptimise(allow_swaps=True, target_2qb_gate=OpType.CX)
PeepholeOptimise2Q(allow_swaps=True)
CliffordSimp(allow_swaps=True, target_2qb_gate=OpType.CX)
PauliSimp(strat=PauliSynthStrat.Sets, cx_config=CXConfigType.Snake)
GreedyPauliSimp(discount_rate=0.7, depth_weight=0.3, max_lookahead=500, max_tqe_candidates=500,
                seed=0, allow_zzphase=False, thread_timeout=100, only_reduce=False, trials=1)
EulerAngleReduction(OpType.Ry, OpType.Rz, strict=False)
RoundAngles(n, only_zeros=False)
FlattenRegisters(); FlattenRelabelRegistersPass(label="q")
RenameQubitsPass({Qubit(0): Qubit("z", 0)})
```

`PauliSynthStrat` comes from **`pytket.transform`** (`pytket.circuit` does not export it): `Individual`, `Pairwise`, `Sets` (default), `Greedy`. `CXConfigType` is in both: `Snake` (default, best on linear), `Star` (enables cancellation), `Tree` (optimal depth when fully connected), `MultiQGate`.

**`FullPeepholeOptimise` takes NO architecture** and assumes full connectivity: it destroys your gateset and your routing. **Never use it after routing.** Verified semantics-preserving: `compare_unitaries(c0.get_unitary(), c1.get_unitary())` → `True`. `RemoveRedundancies()` and `SynthesiseTket()` are cheap, introduce no new gate types, and are the only optimisations safe post-routing. Choosing an optimiser — verified on the same 12-gate 4-qubit circuit after `DecomposeBoxes()`:

| Pass | gates | CX |
|---|---:|---:|
| `SynthesiseTket()` | 11 | 5 |
| `FullPeepholeOptimise()` | 11 | 5 |
| `GreedyPauliSimp(seed=0)` | 18 | **4** |
| `PauliSimp()` | **46** | **19** |

Bare `PauliSimp()` on a small circuit with little Pauli structure **explodes** it; it pays off on Pauli-exponential-heavy circuits (ansätze, Trotter steps), not on everything. `GreedyPauliSimp` trades gate count for CX count. **Neither preserves global phase** — avoid them in phase-sensitive algorithms, or track `circ.phase`. `RoundAngles(3)` was verified to delete an `Rx(1e-7)` gate outright. **Do not use:** `RemoveDeadlines`, `MergeUOp`, `ReorderRegisters`, `SatisfyPredicate`, `GreedyPass` — all confirmed absent in 2.18.4.

## Combinators

```python
from pytket.passes import (SequencePass, RepeatPass, RepeatWithMetricPass,
    RepeatUntilSatisfiedPass, CustomPass, CustomPassMap, CombineCondPass, PassSelector,
    SafetyMode, scratch_reg_resize_pass, compilation_pass_from_script, compilation_pass_grammar)

SequencePass([p1, p2], strict=True)   # strict is the DEFAULT
RepeatPass(p, strict_check=False)
RepeatWithMetricPass(SynthesiseTket(), lambda c: c.n_gates_of_type(OpType.CX))
RepeatUntilSatisfiedPass(SynthesiseTket(), GateSetPredicate({OpType.CX, OpType.TK1}))
compilation_pass_from_script("[RemoveBarriers, RemoveRedundancies]")  # -> SequencePass
compilation_pass_from_script("repeat(FullPeepholeOptimise)")          # -> RepeatPass
compilation_pass_from_script("PauliSimp(Pairwise, Tree)")             # enums by Python name
compilation_pass_from_script("CliffordSimpNoSwaps")                   # booleans by modifier
compilation_pass_grammar()   # -> the EBNF

def my_transform(c: Circuit) -> Circuit:      # pytket does NOT check it preserves U
    RemoveRedundancies().apply(c)
    return c
CustomPass(my_transform, label="my-clean").apply(circ)   # -> bool

def my_perm(c):                               # CustomPassMap takes a CALLABLE, not a dict
    perm = {Qubit(0): Qubit(1), Qubit(1): Qubit(0)}
    return c.copy(), (perm, perm)             # -> (circuit, (initial_map, final_map))
cu = CompilationUnit(Circuit(2).H(0).CX(0, 1))
CustomPassMap(my_perm, label="swap").apply(cu)   # -> False
cu.final_map                                     # -> {q[0]: q[1], q[1]: q[0]}

sel = PassSelector([SynthesiseTket(), FullPeepholeOptimise()], lambda c: c.n_gates)
best = sel.apply(circ)   # -> Circuit, NOT a bool (verified: qubits=4, gates=7)
sel.get_scores()         # -> [7, 7]; takes NO arguments, reports the last apply()
```

`strict=True` uses Hoare-style composition logic — each pass's postconditions must satisfy the next pass's preconditions, checked **at construction time**. Verified: `SequencePass([DecomposeBoxes(), PauliSimp()])` raises `RuntimeError: Cannot compose these Compiler Passes due to mismatching Predicates of type: GateSetPredicate`, because `DecomposeBoxes` guarantees no postconditions; pass `strict=False` when you know better. `RepeatPass` **can loop forever**, because resynthesis passes always report change — prefer `RepeatWithMetricPass` with a monotone metric (verified: it returns `False` and leaves CX at 5 when the metric cannot improve, while the `RepeatUntilSatisfiedPass` above returns `True`). `compilation_pass_from_script` takes no semicolons and ignores whitespace. Verified `CustomPassMap` signature: `CustomPassMap(transform: Callable[[Circuit], tuple[Circuit, tuple[Mapping[UnitID,UnitID], Mapping[UnitID,UnitID]]]], label: str = '') -> BasePass`. `PassSelector` prefers lower scores; a pass that raises scores `None`; if all fail you get `RuntimeError("No passes have successfully run on this circuit")`. Also verified: `CombineCondPass()` → `BasePass`, `scratch_reg_resize_pass(2)` → `BasePass`, `SafetyMode` members `Audit` / `Default`. `safety_mode=` is accepted **only** when the first argument is a `CompilationUnit` — `SynthesiseTket().apply(cu, safety_mode=SafetyMode.Audit)` → `True`; with a bare `Circuit` it raises `TypeError`. **`GreedyPass` does not exist.**

## Initial and final maps — `CompilationUnit`

Placement renames logical `Qubit`s to physical `Node`s, and routing (plus `CliffordSimp` with swaps) permutes them mid-circuit: logical `q[0]` may start on `node[1]` and end on `node[2]`. `CompilationUnit` tracks both ends.

```python
from pytket.predicates import CompilationUnit

cu = CompilationUnit(circ)                # or CompilationUnit(circ, [predicate, ...])
pipeline.apply(cu)                        # -> bool; cu.circuit is mutated
cu.circuit                 # PROPERTY — there is no cu.get_circuit()
cu.initial_map             # dict[UnitID, UnitID]: logical -> node at the START
cu.final_map               # dict[UnitID, UnitID]: logical -> node at the END
cu.check_all_predicates()  # -> bool, NO arguments; pass predicates to the constructor
```

Verified on the 4-qubit line routing example: `initial_map` `{q[0]: node[1]}`, `final_map` `{q[0]: node[2]}`, both length 4 — logical `q[0]` moved, and `q[0]`/`q[1]` swapped between the two maps. On the canonical pipeline below the maps also contain the **classical bits** (`c[0]: c[0]`, …) and `q[1]`/`q[2]` swap while `q[0]`/`q[3]` do not. **How to read results.** There is no `circuit.permute_output_measurements()`. Each classical bit of the *compiled* circuit carries whatever routing decided to write there, so index results by the compiled circuit's own bits — that is what `BackendResult.get_counts()` already gives you. Use `cu.final_map` only when you must relate a logical qubit to its final physical location. Partial compilation composes through the final map: `Placement.place_with_map(next_circ, cu.final_map)`.

## Canonical pass order

`DecomposeBoxes()` → strong optimisations → placement → routing → `DelayMeasures()` → rebase. After routing, only connectivity-preserving passes (`SynthesiseTket`, `RemoveRedundancies`). Complete runnable pipeline, **executed** against pytket 2.18.4:

```python
from pytket import Circuit, OpType
from pytket.architecture import Architecture
from pytket.passes import (AutoRebase, DecomposeBoxes, DelayMeasures, PlacementPass, RoutingPass,
                           SequencePass, SynthesiseTket)
from pytket.placement import GraphPlacement
from pytket.predicates import (CompilationUnit, ConnectivityPredicate, GateSetPredicate,
                               NoMidMeasurePredicate, NoSymbolsPredicate, PlacementPredicate)

arch = Architecture([[0, 1], [1, 2], [2, 3]])
TARGET = {OpType.CX, OpType.Rz, OpType.SX, OpType.X, OpType.Measure}
circ = Circuit(4)
circ.H(0).CX(0, 1).CX(1, 2).CX(2, 3).Rz(0.3, 3).CX(0, 2).H(3).CX(1, 3)
circ.measure_all()
cu = CompilationUnit(circ)
pipeline = SequencePass([
    DecomposeBoxes(),
    SynthesiseTket(),                       # strong optimisation, BEFORE mapping
    PlacementPass(GraphPlacement(arch)),
    RoutingPass(arch),
    DelayMeasures(),
    AutoRebase({OpType.CX, OpType.Rz, OpType.SX, OpType.X}),
])
changed = pipeline.apply(cu)                # -> True
compiled = cu.circuit
for pred in (GateSetPredicate(TARGET), ConnectivityPredicate(arch),
             PlacementPredicate(arch), NoMidMeasurePredicate(), NoSymbolsPredicate()):
    assert pred.verify(compiled), type(pred).__name__
```

Verified: gates 12 → 18, CX 5 → 8, depth 8 → 11, all five predicates `True`. The gate count goes **up** — connectivity compliance on a line is expensive, and that is the honest number to report. `DecomposeBoxes()` goes first and must never sit inside a `strict` `SequencePass` with a constrained pass.

## Symbolic compilation

Every backend requires `NoSymbolsPredicate`, so symbolic circuits cannot be submitted — but **compile the parameterised circuit once** and substitute per evaluation rather than recompiling.

```python
a, b = fresh_symbol("a"), fresh_symbol("b")
circ = Circuit(2).Rx(a, 0).Ry(b, 1).CX(0, 1)
circ.free_symbols()      # METHOD, not a property
circ.is_symbolic()       # True
compiled = backend.get_compiled_circuit(circ, optimisation_level=1)
for aval, bval in [(0.25, 0.5), (0.1, 0.9)]:
    state = compiled.copy()
    state.symbol_substitution({a: aval, b: bval})
    assert NoSymbolsPredicate().verify(state)   # True (verified)
    assert backend.valid_circuit(state)         # True (verified)
```

`pytket-qiskit` **removed symbolic conversion in 0.73.0** — `tk_to_qiskit` no longer carries symbols — and its `default_compilation_pass(..., allow_symbolic=False)` rejects them. Compile symbolically inside pytket and substitute before crossing to Qiskit.

## Contextual optimisation

If qubits are known to start in `|0⟩` and are discarded unmeasured, gates acting only on those states can be deleted.

```python
from pytket.passes import (ContextSimp, SimplifyInitial, SimplifyMeasured, RemoveDiscarded,
                           DelayMeasures)

circ.qubit_create_all()      # annotate every qubit as |0>
circ.qubit_discard_all()     # annotate every qubit as discarded
ContextSimp(allow_classical=True, xcirc=None).apply(circ)
# ContextSimp == RemoveDiscarded + SimplifyInitial + SimplifyMeasured + RemoveRedundancies
SimplifyInitial(allow_classical=True, create_all_qubits=False,
                remove_redundancies=True, xcirc=None).apply(circ)
SimplifyMeasured().apply(circ)
RemoveDiscarded().apply(circ)
DelayMeasures(allow_partial=True).apply(circ)

c0, ppcirc = prepare_circuit(circ, allow_classical=True, xcirc=None)
counts = backend.run_circuit(c0, n_shots=1000, seed=11).get_counts(ppcirc=ppcirc)
```

`qubit_discard` takes a **`Qubit`, not an int**. Verified: `SimplifyInitial(allow_classical=False, remove_redundancies=True)` on `Circuit(2).X(0).CX(0,1).Rz(0.25,1)` + `qubit_create_all()` cuts 3 → 2 gates leaving only `OpType.X`; `DelayMeasures(allow_partial=True)` moved a mid-circuit measurement to the end and returned `True`. `prepare_circuit` is `(circ, allow_classical=True, xcirc=None) -> tuple[Circuit, Circuit]`; on a measured Bell circuit the default gives `(c0 2 gates, ppcirc 2 gates)`, `allow_classical=False` gives `(c0 3 gates, ppcirc 1 gate)`, counts keys `[(0,0), (1,1)]`.

**Warning:** with `allow_classical=True` these passes can emit classical set-bit operations that most backends reject — use `allow_classical=False` for hardware, or the `prepare_circuit` + `ppcirc` route. Gate on `backend.supports_contextual_optimisation` (verified `False` on `AerBackend()`), and apply contextual optimisation **before** mapping and routing.

## Measuring compilation quality

```python
before, after = circ.n_gates, compiled.n_gates     # PROPERTIES
circ.n_gates_of_type(OpType.CX)                    # METHOD
circ.n_2qb_gates()                                 # METHOD
circ.depth(); circ.depth_2q(); circ.depth_by_type(OpType.CX)
gate_counts(circ)   # -> {OpType.H: 1, OpType.Rz: 1, OpType.CX: 2, OpType.Measure: 3}
circ.commands_of_type(OpType.CX)
compare_unitaries(circ.get_unitary(), compiled.get_unitary())   # -> True
```

`n_gates`, `n_bits`, `n_qubits` are **properties**; `n_1qb_gates()`, `n_2qb_gates()`, `depth()`, `depth_2q()` are **methods**. `Circuit.width()` and `Circuit.get_two_qubit_gate_count()` do not exist. `compare_unitaries` / `compare_statevectors` take **numpy arrays**, not `Circuit` objects (passing circuits raises `AttributeError: ... has no attribute 'conjugate'`) and ignore global phase. Finish by re-running the predicates and `backend.valid_circuit(compiled)`.

`get_resources()` returns a `ResourceData` with **getter methods only** — `get_op_type_count()`, `get_gate_depth()`, `get_op_type_depth()`, `get_two_qubit_gate_depth()` — each yielding `ResourceBounds` whose only public methods are `get_min()` / `get_max()` (no `.lower` / `.upper`): `res.get_op_type_count()[OpType.CX].get_min()` → `5`, `res.get_gate_depth().get_max()` → `8`, `res.get_two_qubit_gate_depth().get_min()` → `4`.

## ZX-based optimisation

`passes.ZXGraphlikeOptimisation(allow_swaps=True)` is the only ZX pass — there is no `ZXPass` wrapper. It is a **resynthesis** pass: best on Clifford-dense or phase-gadget structure, and it can increase gate counts on an already-good circuit. Its precondition is a restricted gateset, so rebase first:

```python
from pytket.passes import AutoRebase, FullPeepholeOptimise, ZXGraphlikeOptimisation

zx = Circuit(3).H(0).CX(0, 1).S(1).CX(1, 2).H(2)
AutoRebase({OpType.CX, OpType.Rz, OpType.Rx, OpType.H}).apply(zx)  # 5 gates {CX, H, Rz}
ZXGraphlikeOptimisation(allow_swaps=True).apply(zx)                # True, 5 -> 10 gates
FullPeepholeOptimise().apply(zx)                                   # -> 7 gates
```

Verified: `RebaseTket()` is **not** sufficient (`TK1` is outside the allowed set `{Input, H, noop, Output, SWAP, Rz, Rx, X, Z, CX, CZ}`) and raises `RuntimeError: Predicate requirements are not satisfied: GateSetPredicate:{...}`; so does any circuit still carrying `Measure` gates. On a Clifford-dense 4-qubit circuit: rebased 15 → ZX 19 → `FullPeepholeOptimise` **11**. Always follow with peephole passes and re-check routability — ZX output can be harder to route. `references/algorithms.md` owns the ZX-calculus detail.

## Gotchas / rules

- **Passes mutate in place.** `apply()` returns a claim, not a proof. Copy first.
- Only `backend.get_compiled_circuit()` / `get_compiled_circuits()` return new objects.
- `default_compilation_pass` is abstract — inspect `.to_dict()` per backend, never guess.
- Level 2 is the default and can be very slow; level 0 can inflate gate counts.
- `FullPeepholeOptimise` takes no architecture and destroys gateset and connectivity — never after routing. Only `SynthesiseTket` and `RemoveRedundancies` are safe there.
- `SequencePass` is strict by default and fails **at construction**: `SequencePass([DecomposeBoxes(), PauliSimp()])` raises.
- `RepeatPass` can loop forever; use `RepeatWithMetricPass`.
- `PauliSimp` / `GreedyPauliSimp` do not preserve global phase. Bare `PauliSimp()` exploded a 12-gate circuit to 46 gates.
- Routing permutes qubits: track `cu.initial_map` / `cu.final_map`; `cu.circuit` is a property and `cu.check_all_predicates()` takes no arguments.
- No `seed=` on routing passes — routing is deterministic. Only `GreedyPauliSimp` seeds.
- `FullyConnected` is not an `Architecture`: it cannot be placed or routed.
- `backend.required_predicates`, never `required_properties`.
- Spell exactly: `SquashRzPhasedX` (Rz, not RZ), `DecomposeSingleQubitsTK1` (plural), `ThreeQubitSquash`, `FlattenRelabelRegistersPass`.
- Compile symbolic circuits once, then `symbol_substitution` per evaluation.
- Contextual passes can emit set-bit ops most backends reject → `allow_classical=False`.

## Sources

- <https://docs.quantinuum.com/tket/user-guide/manual/manual_compiler.html> · <https://docs.quantinuum.com/tket/user-guide/manual/manual_noise.html>
- <https://docs.quantinuum.com/tket/api-docs/passes.html> · <https://docs.quantinuum.com/tket/api-docs/predicates.html> · <https://docs.quantinuum.com/tket/api-docs/architecture.html>
- <https://docs.quantinuum.com/tket/api-docs/placement.html> · <https://docs.quantinuum.com/tket/api-docs/mapping.html> · <https://docs.quantinuum.com/tket/api-docs/transform.html>
- `tket/pytket/docs/passes.md`, `predicates.md`, `architecture.md`, `placement.md`, `mapping.md`, `transform.md`
- `tket/pytket/pytket/_tket/passes.pyi`, `predicates.pyi`, `placement.pyi`
- `tket/pytket/pytket/backends/backend.py`, `tket/pytket/pytket/passes/passselector.py`, `tket/pytket/pytket/passes/script.py`
