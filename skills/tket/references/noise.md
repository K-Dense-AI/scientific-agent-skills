# Noise

Noise modelling and mitigation in the TKET ecosystem. Verified by execution against pytket 2.18.4, pytket-qiskit 0.78.0 (qiskit-aer 0.17.2) and qermit 0.9.3. Backend submission, results and bit ordering → [references/backends.md](backends.md); compilation passes → [references/compilation.md](compilation.md).

## Package provenance

**pytket core contains no ZNE, PEA, CDR or identity-insertion wrappers.** Assume nothing is in `pytket` until you have checked this table.

| Capability | Package | Install |
|---|---|---|
| Frame randomisation / twirling | `pytket.tailoring` | core pytket |
| SPAM characterisation and correction | `pytket.utils.spam` | core pytket |
| Pauli measurement reduction | `pytket.partition`, `pytket.utils` | core pytket |
| Noise-aware qubit placement | `pytket.placement.NoiseAwarePlacement` | core pytket |
| Contextual optimisation passes | `pytket.passes` | core pytket |
| Device calibration data | `BackendInfo` error fields | core pytket |
| Noise **models** and noisy simulation | `pytket.extensions.qiskit` | `pip install "pytket-qiskit[aer]"` |
| ZNE, CDR, DFSC, learning-based PEC | `qermit` | `pip install qermit` |
| Leakage detection, `postprocess`, `simplify_initial` | `pytket.extensions.quantinuum` | `pip install pytket-quantinuum` |

**Assumed name → reality.** Every name in the left column is absent from pytket 2.18.4 (grep over the clone plus `git log -S`: zero hits).

| Assumed | Reality |
|---|---|
| `ZeroNoiseExtrapolation` | `qermit.zero_noise_extrapolation.gen_ZNE_MitEx` |
| `ProbabilisticErrorAmplification` | nothing under that name; nearest is `qermit.probabilistic_error_cancellation.gen_PEC_learning_based_MitEx` |
| `CliffordDataRegression` | `qermit.clifford_noise_characterisation.gen_CDR_MitEx` |
| `IdentityInsertion` | `qermit` `Folding.gate` / `Folding.two_qubit_gate` |
| `PauliFrameSampling` | `pytket.tailoring.PauliFrameRandomisation().sample_circuits(circ, n)` |
| `passes.SpamRelabel` | `pytket.utils.spam.SpamCorrecter` |
| `passes.LeakageReduction` | `pytket-quantinuum`: `process_circuits(..., leakage_detection=True)` + `prune_shots_detected_as_leaky(result)` |
| `passes.NoiseAwareMappingPass`, `NoiseAwareQubitPlacement` | `pytket.placement.NoiseAwarePlacement` fed to `PlacementPass` / `FullMappingPass` |
| `Backend.get_expectation_value` | `Backend.get_pauli_expectation_value` / `get_operator_expectation_value` (state-exact, no `n_shots`) |
| `utils.expectation_value_from_samples` | `pytket.utils.expectation_from_shots`, `expectation_from_counts` |
| `MeasuredBasis`, `MeasuredOperator`, `MeasurementSplits`, `GenShotMitigation` | nothing; Pauli measurement reduction is `pytket.partition` |
| a `sample_allowance` kwarg anywhere | no such parameter exists |

tket defines **no noise-model class of its own**: `NoiseModel` is Qiskit Aer's.

## Noise models

```python
from qiskit_aer.noise import NoiseModel
from qiskit_aer.noise.errors import depolarizing_error
from pytket.extensions.qiskit import AerBackend, AerDensityMatrixBackend

nm = NoiseModel()
for q in (0, 1, 2):                                          # per-qubit, per-gate
    nm.add_quantum_error(depolarizing_error(0.05, 1), ["rz", "sx", "x"], [q])
    nm.add_readout_error([[0.95, 0.05], [0.05, 0.95]], [q])
for q0, q1 in ((0, 1), (1, 2)):                              # per-edge 2q error
    nm.add_quantum_error(depolarizing_error(0.05, 2), ["cx"], [q0, q1])

noisy = AerBackend(noise_model=nm)   # signature: (noise_model=None, simulation_method="automatic",
                                     #             crosstalk_params=None, n_qubits=40)
density = AerDensityMatrixBackend(noise_model=nm, n_qubits=40)
```

`AerStateBackend` and `AerUnitaryBackend` take **no** noise model — a pure state or unitary does not exist under noise.

**Traps, all verified:**

- `nm.add_all_qubit_quantum_error(...)` / `add_all_qubit_readout_error(...)` make `AerBackend` **raise** `RuntimeWarning: Please define NoiseModel without using the add_all_qubit_quantum_error() or add_all_qubit_readout_error() method.` — it is an exception of type `RuntimeWarning`, not a warning. Build the model per gate and per qubit with the loop above.
- An empty `NoiseModel()` is accepted but silently mapped to `None` internally — you get a noiseless run with no error.
- `noisy.get_pauli_expectation_value(circ, pauli)` raises `RuntimeError: Snapshot based expectation value not supported with noise model. Use shots.` Same for `get_operator_expectation_value`.

Verified result, 3-qubit GHZ at 2000 shots, seed 7, compiled at `optimisation_level=1`: with **5% single-qubit depolarising on `rz`/`sx`/`x` only** the counts stay in the code space — `{(0, 0, 0): 1016, (1, 1, 1): 984}`, exactly 2 distinct outcomes. Add 5% two-qubit depolarising on CX and 5% readout error on all three qubits and you get **8** distinct outcomes: `{(0,0,0): 827, (1,1,1): 797, (1,0,0): 81, (0,1,1): 75, (0,0,1): 60, (0,1,0): 58, (1,1,0): 53, (1,0,1): 49}`. Single-qubit depolarising alone is a weak noise model — always model readout and the 2q gate too.

### Reading device noise for real hardware

```python
info = backend.backend_info
info.all_node_gate_errors        # dict[Node, dict[OpType, float]] | None
info.all_edge_gate_errors        # dict[tuple[Node, Node], dict[OpType, float]] | None
info.all_readout_errors          # dict[Node, list[list[float]]] | None
info.averaged_node_gate_errors   # dict[Node, float] | None
info.averaged_edge_gate_errors   # dict[tuple[Node, Node], float] | None
info.averaged_readout_errors     # dict[Node, float] | None
info.misc                        # plain dict, default {'characterisation': None}
info.get_misc(key)               # KeyError when absent; info.add_misc(key, val) -> None
info.to_dict()                   # BackendInfo.from_dict(d) reverses it
```

All six error fields default to **`None`** — guard every access (`AerBackend()` with no noise model returns `None` for all of them). Edge errors are **directional**: on the model above `{(node[0], node[1]): {OpType.CX: 0.046875}}` while the reverse edge reads `0.091552734375`, modelled as `1 - fidelity**2`. Passing a noise model also makes `backend_info.architecture` reflect the model's coupling map (`<tket::Architecture, nodes=3>`) and populates every error field: `all_node_gate_errors` → `{node[0]: {OpType.Rz: 0.0375, OpType.SX: 0.0375, OpType.X: 0.0375}, ...}`, `all_readout_errors` → `{node[0]: [[0.95, 0.05], [0.05, 0.95]], ...}`, `averaged_readout_errors` → `{node[0]: 0.05, ...}`.

## Noise-aware placement

```python
from pytket.circuit import Node
from pytket.placement import NoiseAwarePlacement
from pytket.passes import PlacementPass, FullMappingPass
from pytket.mapping import LexiLabellingMethod, LexiRouteRoutingMethod

info = backend.backend_info
placer = NoiseAwarePlacement(
    arc=info.architecture,
    node_errors=info.averaged_node_gate_errors or {},
    link_errors=info.averaged_edge_gate_errors or {},
    readout_errors=info.averaged_readout_errors or {},
    maximum_matches=1000, timeout=1000,
    maximum_pattern_gates=100, maximum_pattern_depth=100,
)
PlacementPass(placer).apply(circ)                                   # in place -> bool
FullMappingPass(info.architecture, placer,
                [LexiLabellingMethod(), LexiRouteRoutingMethod()]).apply(circ)
placer.get_placement_map(circ)      # -> dict[Qubit, Node]
NoiseAwarePlacement.from_dict(placer.to_dict())   # snapshot the placement for a report
```

**Use keyword arguments only.** The official `manual_noise.html` passes the three error dictionaries positionally in the order `(arc, averaged_readout_errors, averaged_node_gate_errors, averaged_edge_gate_errors)`, which contradicts the real signature `(arc, node_errors, link_errors, readout_errors, ...)` — a documented bug. Positional use silently swaps your readout errors into the node-error slot. `link_errors` keys are **directed** `(Node, Node)` tuples.

Verified: keyword construction succeeds, `.get_placement_map(circ)` returns `{q[0]: node[0], q[1]: node[1], ...}`, `PlacementPass(nap)` renames the qubits to `node[0..3]`, and `FullMappingPass(arch, nap, [LexiLabellingMethod(), LexiRouteRoutingMethod()])` leaves a 3-gate circuit satisfying `ConnectivityPredicate(arch)`. Missing node or edge entries are treated as fidelity 1, so without calibration data the placer degenerates to ordinary graph placement. Error rates drift — re-fetch them per run. A circuit with no two-qubit gates is placed on the lowest-error nodes. **`NoiseAwareMappingPass` and `NoiseAwareQubitPlacement` do not exist.**

## Frame randomisation (core pytket)

Conjugating a circuit by random Paulis averages its noise channel over the Pauli group, turning coherent error (which accumulates as the square root of the average) into stochastic Pauli error (which accumulates roughly as the average). That is twirling: it does **not** reduce the noise, it makes it Pauli-like so a Pauli-aware mitigation step becomes valid. Reference: Wallman & Emerson, *Phys. Rev. A* **94**, 052325 (2016).

```python
from pytket.tailoring import (FrameRandomisation, PauliFrameRandomisation,
                              UniversalFrameRandomisation, apply_clifford_basis_change,
                              apply_clifford_basis_change_tensor)

pfr = PauliFrameRandomisation()      # NO constructor arguments
ufr = UniversalFrameRandomisation()  # NO constructor arguments
all_circuits = pfr.get_all_circuits(circ)      # exhaustive: 4**n_cycles circuits
sampled = pfr.sample_circuits(circ, 8)         # -> 8 Circuit objects (verified)

cfr = FrameRandomisation(            # custom: (cycle_types, frame_types, cycle_frame_actions)
    {OpType.CX}, {OpType.Y},
    {OpType.CX: {(OpType.Y, OpType.Y): (OpType.X, OpType.Z)}},   # Y(0)Y(1)CX(0,1)X(0)Z(1) == CX(0,1)
)
```

`PauliFrameRandomisation` cycles `{CX, H, S}` with frames `{X, Y, Z, noop}`. `UniversalFrameRandomisation` cycles `{CX, H, Rz}` and preserves the unitary by adjusting the `Rz` angles; its stochastic-Pauli guarantee additionally requires incoherent noise independent of the rotation angle. On `Circuit(2).H(0).CX(0,1).Rz(0.3,1).CX(0,1)` the exhaustive counts are `len(pfr.get_all_circuits(circ)) == 256` and `len(ufr.get_all_circuits(circ)) == 16`, unchanged by a prior `AutoRebase({CX, H, Rz})` — the cost scales with the number of cycles, not the gate count.

**Traps, both verified:**

- `sample_circuits()` returns circuits with **no `Measure` gates**, so running them as-is yields `get_counts()` → `{(): N}` (empty-tuple keys). Call `s.measure_all()` on each sampled circuit yourself.
- **`PauliFrameSampling` does not exist.** There is also no pass wrapper: frame randomisation returns a list of circuits, never a `BasePass`.

Aggregation is manual, and the shot budget multiplies. Executed end to end:

```python
from collections import Counter

n_samples, shots_per_circuit = 8, 500
averaged = []
for s in pfr.sample_circuits(circ, n_samples):
    s.measure_all()                     # required: sampled circuits carry no measurements
    averaged.append(s)
handles = noisy.process_circuits(noisy.get_compiled_circuits(averaged),
                                 n_shots=shots_per_circuit, seed=1234)
pfr_counts: Counter = Counter()
for result in noisy.get_results(handles):
    pfr_counts.update(result.get_counts())
# total shot spend = n_samples * shots_per_circuit = 4000
```

Verified output on a noisy 2-qubit `AerBackend`: `{(0, 0): 2037, (1, 0): 1963}` against an unmitigated baseline at the **same 4000 shots** of `{(0, 0): 1997, (1, 0): 2003}`. That is the honest picture: PFR changed the channel without visibly improving these counts. Apply it after optimisation (barriers block gate merging), compare at equal total shots, and never judge efficacy from counts alone.

Two helpers conjugate an observable instead of a circuit:

```python
from pytket.pauli import Pauli, QubitPauliString, QubitPauliTensor
cliff = Circuit(1).H(0)
pauli = QubitPauliString([cliff.qubits[0]], [Pauli.Z])
apply_clifford_basis_change(pauli, cliff)              # -> (Xq[0]); DROPS a -1 phase
apply_clifford_basis_change_tensor(QubitPauliTensor(pauli), cliff)   # .string (Xq[0]), .coeff (1+0j)
```

`QubitPauliTensor`'s coefficient is a **`complex`**, not a sympy expression — `QubitPauliTensor(pauli, sympy.Symbol("c"))` raises `TypeError`. Overloads: `(coeff=1.0)`, `(qubit, pauli, coeff=1.0)`, `(qubits, paulis, coeff=1.0)`, `(map, coeff=1.0)`, `(string, coeff=1.0)`.

## qermit mitigation

Everything in this section needs `pip install qermit`; the API below was verified against 0.9.3. **Give qermit its own environment.** Every released qermit pins the extensions, not just pytket — 0.9.3 demands `pytket-qiskit>=0.73,<0.78` **and** `pytket-quantinuum[pecos]>=0.41,<0.59` (0.8.5 is tighter still: `>=0.73,<0.74` and `<0.55`) — so **no released qermit is compatible with pytket-qiskit 0.78.0 or pytket-quantinuum 0.59.x**. Resolving them together does not fail loudly: pip **silently backtracks to qermit 0.7.1**, a release that predates the API documented here. Full pin table and the two workarounds: [setup.md — The `qermit` conflict](setup.md#the-qermit-conflict-verified-2026-10-01).

Always print the version that actually landed before trusting any documented API, because `qermit.__version__` does not exist:

```python
import importlib.metadata as md
print(md.version("qermit"), md.version("pytket"), md.version("pytket-qiskit"))
```

`scripts/check_environment.py` detects this automatically: its `KNOWN_PIN_CONFLICTS` table names both pins and the check emits a warning when an installed qermit is incompatible with the installed extensions.

```python
from qermit import AnsatzCircuit, ObservableExperiment, ObservableTracker, SymbolsDict, MitEx, MitRes
from pytket.utils import QubitPauliOperator
from qermit.zero_noise_extrapolation import gen_ZNE_MitEx, Folding, Fit
from qermit.clifford_noise_characterisation import gen_CDR_MitEx, gen_DFSC_MitEx
from qermit.frame_randomisation import gen_Frame_Randomisation_MitRes, FrameRandomisation
from qermit.probabilistic_error_cancellation import gen_PEC_learning_based_MitEx

op = QubitPauliOperator({QubitPauliString(ansatz.qubits, [Pauli.Z] * 3): 1.0})
experiment = [ObservableExperiment(AnsatzCircuit(ansatz, 8000, SymbolsDict()), ObservableTracker(op))]

zne = gen_ZNE_MitEx(backend=noisy, noise_scaling_list=[3, 5, 7],
                    folding_type=Folding.circuit, fit_type=Fit.linear)
result: list = zne.run(experiment)          # -> list[QubitPauliOperator]
value = result[0].get_dict()                # {(Zq[0], Zq[1], Zq[2]): 0.380041666666667}
```

Two hard requirements, both verified by failure: `ObservableTracker` takes a **`pytket.utils.QubitPauliOperator`**, not a `QubitPauliTensor` (a tensor raises `AttributeError: ... has no attribute '_dict'`), and `AnsatzCircuit` must contain **no `Measure` gates** (it raises `RuntimeError: Cannot compute dagger: Measure`). `MitEx.run` returns one `QubitPauliOperator` per experiment — read values with `.get_dict()`, never `complex(...)`.

Generators and their verified signatures (`inspect.signature`, which works on these unlike the nanobind-bound pytket ones):

| Generator | Signature |
|---|---|
| `gen_ZNE_MitEx` | `(backend: Backend, noise_scaling_list: list[float], **kwargs) -> MitEx` |
| `gen_CDR_MitEx` | `(device_backend: Backend, simulator_backend: Backend, n_non_cliffords: int, n_pairs: int, total_state_circuits: int, **kwargs) -> MitEx` |
| `gen_PEC_learning_based_MitEx` | `(device_backend: Backend, simulator_backend: Backend, **kwargs) -> MitEx` |
| `gen_DFSC_MitEx` | `(backend: Backend, **kwargs) -> MitEx` |
| `gen_Frame_Randomisation_MitRes` | `(backend: Backend, samples: int, **kwargs) -> MitRes` |

`Folding.{gate, circuit, odd_gate, two_qubit_gate, noise_aware}` and `Fit.{linear, polynomial, exponential, poly_exponential, richardson, cube_root}` are **plain callables, not enum members** — you cannot iterate them. `Folding.circuit` requires **odd integer** noise-scaling factors; `Folding.gate` and `Folding.two_qubit_gate` accept floats but need `allow_approx_fold=True`. ZNE also takes `deg=` (fit degree) and `experiment_mitres=` / `experiment_mitex=` to nest further mitigation. Verified: `Folding.gate` + `Fit.exponential` + `allow_approx_fold=True` runs on the same experiment.

CDR's extra kwargs are `model=_PolyCDRCorrect(1)`, `likelihood_function=LikelihoodFunction.none`, `tolerance`, `distance_tolerance`, `calibration_fraction`, `states_simulator_mitex`, `states_device_mitex`, `experiment_mitex`. **`_PolyCDRCorrect` and `LikelihoodFunction` are not re-exported** by `qermit.clifford_noise_characterisation` (importing them from there raises `ImportError`) — use `from qermit.clifford_noise_characterisation.cdr_post import _PolyCDRCorrect` and `from qermit.clifford_noise_characterisation.ccl import LikelihoodFunction`. `LikelihoodFunction` has no enum members either; its names are static callables. All four generators construct without network access.

Inspect a pipeline with `mitex.decompose_TaskGraph_nodes()` — it returns **`None`** and decomposes in place, so never wrap it in `len()` — then `mitex.get_task_graph()`, which returns a `graphviz.Digraph`. Prefer PEC/PEA in the low-noise regime, where variance grows more slowly than ZNE's; ZNE extrapolation becomes ill-conditioned when the scaled points sit close together.

Worked comparison, all three numbers executed on the same 3-qubit ansatz `Ry(0.3,0).Ry(0.5,1).Ry(0.2,2).CX(0,1).CX(1,2)` with observable `<ZZZ>`, 3% single-qubit depolarising, 5% readout error and 3% two-qubit depolarising:

| Estimator | `<ZZZ>` | Shot budget |
|---|---:|---|
| ideal statevector | `0.47552825814757704` | 0 |
| raw noisy, 8000 shots | `0.333` | 8 000 |
| ZNE `[3,5,7]`, `Folding.circuit`, `Fit.linear` | `0.380041666666667` | 8 000 × 3 = 24 000 |

ZNE moved the estimate towards the ideal value but did not reach it, at three times the shots. A repeat run of the identical configuration at 4000 shots per scaling point gave `0.356125` — quote one seed per configuration, or report the spread, never both as a single number.

## SPAM mitigation (core pytket)

```python
from pytket.circuit import Node
from pytket.utils.spam import SpamCorrecter, compress_counts

subsets = [[Node(0), Node(1)]]                 # one list = all qubits in it fully correlated
spam = SpamCorrecter(subsets, backend=None)    # backend=None is fine
cal = spam.calibration_circuits()              # -> 4 circuits for a 2-qubit subset (2**n)
spam.calculate_matrices(backend.run_circuits(cal, n_shots=4000, seed=3))
spam.characterisation_matrices               # -> [array of shape (4, 4)], column-normalised

comp = backend.get_compiled_circuit(main, optimisation_level=1)
result = backend.run_circuit(comp, n_shots=8000, seed=5)
parallel_measures = spam.get_parallel_measure(comp)   # -> [{node[0]: c[0], node[1]: c[1]}]
fixed = spam.correct_counts(result, parallel_measures, method="bayesian")  # -> BackendResult
inverted = spam.correct_counts(result, parallel_measures, method="invert")
SpamCorrecter.from_dict(spam.to_dict())        # snapshot for a report
```

Verified end to end with an asymmetric readout model (`[[0.92, 0.08], [0.05, 0.95]]` per qubit): raw counts `{(0,0): 3367, (0,1): 476, (1,0): 515, (1,1): 3642}` became `{(0,0): 3948, (0,1): 15, (1,0): 55, (1,1): 3984}` under `method="bayesian"` and `{(0,0): 3968, (1,0): 41, (1,1): 3993}` under `method="invert"` — inversion dropped the tiny `(0,1)` bin entirely, because it produced negative probabilities that were compressed away. `compress_counts(counts, tol=1e-6, round_to_int=False)` collapses negligible bins; `compress_counts({(0,0): 900, (0,1): 100, (1,1): 1}, round_to_int=True)` passes such a distribution through unchanged.

**Rules, all verified or load-bearing:**

- Calibration circuits must be run **uncompiled** and their results returned **in the same order** as `calibration_circuits()` produced them.
- One list means every qubit in it is correlated with every other; several lists means correlated only within each list. `n` fully correlated qubits need `2**n` calibration circuits, so partition large devices into disjoint nearest-neighbour groups:
  ```python
  nodes = backend.backend_info.architecture.nodes
  subsets = [nodes[i:i + 2] for i in range(0, len(nodes) - 1, 2)]
  ```
- Subsets must be mutually disjoint: `SpamCorrecter([[Node(0), Node(1)], [Node(1), Node(2)]])` raises `ValueError: Qubit subsets are not mutually disjoint.` **at construction**, not at `calibration_circuits()`.
- Calling `calculate_matrices` before `calibration_circuits` raises `AttributeError: 'SpamCorrecter' object has no attribute 'state_infos'` (at `pytket/utils/spam.py:385`) — not the `RuntimeError` the docs imply.
- `method` must be `"bayesian"` or `"invert"`; anything else raises `ValueError`. The old `"minimise"` was removed in 0.7.0.
- Characterise **after** placement and routing, and translate with `CompilationUnit.final_map` or `circuit.qubit_readout` — the corrector is keyed on physical `Node`s.
- The model assumes SPAM noise is independent of the computation. It fails when leakage dominates.
- tket ships no measurement-error-mitigation matrix routine beyond `SpamCorrecter`; the rest of `pytket.utils.spam` is private (renamed in 2.4.0 "to indicate they are not intended for external usage").

**Leakage on Quantinuum hardware is not a pass.** It is a submission option: `backend.process_circuits(circuits, n_shots=1000, leakage_detection=True, n_leakage_detection_qubits=2)` then `prune_shots_detected_as_leaky(backend.get_result(handle))`, both from `pytket.extensions.quantinuum`. The same kwargs path also carries `postprocess`, `simplify_initial`, `noisy_simulation` and `seed` — they arrive through `**kwargs`, so the declared signature `(self, circuits, n_shots=None, valid_check=True, **kwargs)` never shows them and `inspect.signature` will not either (verified by grepping the installed source). **`passes.SpamRelabel` and `passes.LeakageReduction` do not exist.** Since pytket-quantinuum 0.56.1 the backend refuses hardware submission outright — target the remote noisy emulator (`H2-1E`), or submit through `qnexus` (→ [references/backends.md](backends.md)).

## Measurement reduction (core pytket)

The largest legitimate shot-saver in core pytket: commuting Pauli terms are measured together, so one shot yields a parity for **every** term in its group. A 5-term operator that needs 5 executions can need 2 — roughly 2.5× the statistics for the same shot budget, or 2.5× fewer shots for the same error bar. `pytket.partition` is **Pauli measurement reduction only** — it has nothing to do with circuit cutting; there is no `SubCircuit` or `partition_circuit` in pytket.

```python
from pytket.partition import (PauliPartitionStrat, GraphColourMethod, MeasurementSetup,
                              MeasurementBitMap, measurement_reduction, term_sequence)
from pytket.utils import get_operator_expectation_value

val = get_operator_expectation_value(          # -> complex (verified)
    state_circuit, operator, backend, n_shots=20000,
    partition_strat=PauliPartitionStrat.CommutingSets,
    colour_method=GraphColourMethod.LargestFirst,
)
```

Verified signature: `get_operator_expectation_value(state_circuit: Circuit, operator: QubitPauliOperator, backend: Backend, n_shots: int | None = None, partition_strat: PauliPartitionStrat | None = None, colour_method: GraphColourMethod = GraphColourMethod.LargestFirst, **kwargs) -> complex`. `partition_strat=None` means one circuit per term; `n_shots=None` falls back to the state-exact `backend.get_operator_expectation_value` when `supports_expectation`, otherwise `run_circuit(...).get_state()` plus `operator.state_expectation(state)`. `n_shots` is **per measurement circuit, not per term**. `state_circuit` must use the default `q` register with contiguous indices (`ValueError("Non-default qubit register")` otherwise), and the operator must be symbol-free when shots are used.

Reference numbers, all executed on `c = Circuit(5).H(4).V(2)` (compiled) with `op = 0.1*Z0 + 0.4*Y0Z1X2X3Y4 + 0.2*X0X1`:

| Route | Value |
|---|---|
| exact, `AerStateBackend` | `0.10000000000000005` |
| 20 000 shots, `partition_strat=None` | `0.09632000000000006+0j` |
| 20 000 shots, `NonConflictingSets` | `0.09450000000000003+0j` |
| 20 000 shots, `CommutingSets` + `LargestFirst` | `0.09838000000000001+0j` |

Low-level route, for when you need the grouping itself:

```python
id_string = QubitPauliString()
strings = [p for p in operator.get_dict() if p != id_string]
setup: MeasurementSetup = measurement_reduction(
    strings, PauliPartitionStrat.CommutingSets,
    method=GraphColourMethod.LargestFirst, cx_config=CXConfigType.Snake)
setup.verify()                 # -> True
len(setup.measurement_circs)   # -> 2 circuits for 3 terms
bm = setup.results[strings[0]][0]     # MeasurementBitMap(circ_index, bits, invert=False)
bm.circ_index, bm.bits, bm.invert     # read-only: 0, [0], False
setup.add_measurement_circuit(circ); setup.add_result_for_term(term, bitmap)
MeasurementSetup.from_dict(setup.to_dict())
groups = term_sequence(strings, PauliPartitionStrat.CommutingSets,
                       GraphColourMethod.LargestFirst)   # -> grouping only, no circuits
```

Verified on that example: `CommutingSets` + `LargestFirst` gives **2** measurement circuits with CX counts `[0, 1]`, while `NonConflictingSets` + `Lazy` gives **3** with CX counts `[0, 0, 0]`; `term_sequence` returns 2 groups of sizes `[1, 2]`. Enum members are exactly `PauliPartitionStrat` = `NonConflictingSets` | `CommutingSets` (nothing else — no `Default`, `Unwire`, `Comm`, `QubitWise`) and `GraphColourMethod` = `Lazy` | `LargestFirst` | `Exhaustive`. `Lazy` builds no graph and keeps input order; `LargestFirst` is greedy on highest degree; `Exhaustive` minimises colours with exponential worst case. `inspect.signature(term_sequence)` is useless — nanobind reports `(*args, **kwargs)`.

Extract the expectation values yourself, because pytket ships no variance routine:

```python
id_string = QubitPauliString()          # the identity term: a constant, no measurement
energy = complex(operator.get_dict().get(id_string, 0))
variance = 0.0
for pauli, coeff in operator.get_dict().items():
    if pauli == id_string:
        continue
    for bm in setup.results[pauli]:
        counts = results[bm.circ_index].get_counts()
        n = sum(counts.values())
        odd = sum(cnt for bits, cnt in counts.items()
                  if sum(bits[i] for i in bm.bits) % 2)
        e = ((-1) ** bm.invert) * (-2 * odd / n + 1)
        energy += complex(coeff) * e
        variance += abs(complex(coeff)) ** 2 * max(0.0, (1 - e * e)) / n
```

Executed on the 5-qubit example: `energy = (0.10334+0j)`, `variance**0.5 = 0.0031621417267415457`. Note the identity term is added as a constant, never measured. **Treat the variance as a lower bound** — terms sharing a measurement circuit have correlated noise, so the independence assumption fails; bootstrap the counts for real error bars.

`NonConflictingSets` groups only terms that put the same Pauli (or `I`) on every qubit, so it is exact and costs zero extra CX but groups less. `CommutingSets` groups more but inserts diagonalising CX gates — count `n_gates_of_type(OpType.CX)` per measurement circuit before choosing. The grouping is **exact for the set produced**, not an approximation of the operator; the only new risk is that the added diagonalisation gates are themselves noisy. For a single Pauli term, `pytket.utils.append_pauli_measurement(pauli_string, circ)` followed by `expectation_from_counts(result.get_counts())` or `expectation_from_shots(result.get_shots())` is enough — verified `1.0` for `<ZZ>` on a Bell state.

## Contextual optimisation as noise reduction

Gates acting on qubits known to be in `|0⟩`, or on qubits whose output is discarded, do nothing but accumulate error. Removing them cuts depth, and depth is the noise budget.

```python
from pytket.passes import ContextSimp, SimplifyInitial, SimplifyMeasured, RemoveDiscarded, DelayMeasures
from pytket.utils import prepare_circuit

circ.qubit_create_all()      # every qubit starts in |0>
circ.qubit_discard_all()     # every qubit's output is discarded
ContextSimp(allow_classical=False, xcirc=None).apply(circ)
SimplifyInitial(allow_classical=True, create_all_qubits=False,
                remove_redundancies=True, xcirc=None).apply(circ)
SimplifyMeasured().apply(circ); RemoveDiscarded().apply(circ); DelayMeasures(allow_partial=True).apply(circ)

c0, ppcirc = prepare_circuit(circ, allow_classical=True, xcirc=None)
counts = backend.run_circuit(c0, n_shots=1000, seed=11).get_counts(ppcirc=ppcirc)
```

Verified: `SimplifyInitial(allow_classical=False, remove_redundancies=True)` on `Circuit(2).X(0).CX(0,1).Rz(0.25,1)` after `qubit_create_all()` cuts 3 → 2 gates leaving only `OpType.X`. On a measured Bell circuit `prepare_circuit` gives `(c0 2 gates, ppcirc 2 gates)` by default and `(c0 3 gates, ppcirc 1 gate)` with `allow_classical=False`; signature `(circ, allow_classical=True, xcirc=None) -> tuple[Circuit, Circuit]`.

**On hardware use `allow_classical=False`.** The default lets these passes replace a measurement on a known state with a classical set-bit operation, which most backends reject. Gate on `backend.supports_contextual_optimisation` (`False` on `AerBackend()`) and apply contextual optimisation **before** mapping and routing. `RemoveDiscarded` never removes a `Measure` whose classical output is in the causal future — only unmeasured discarded qubits. Once a circuit carries created/discarded annotations it cannot be freely composed. pytket-quantinuum exposes the same idea as `process_circuits(..., postprocess=True, simplify_initial=True)`.

## Verification and reporting

1. Compare **three** estimators on the same observable: ideal (statevector or `AerStateBackend`), noisy baseline, mitigated. A mitigation number without both anchors means nothing.
2. Compare at **equal total shot budget**, not equal shots per circuit: PFR spends `shots_per_circuit × n_averaging_circuits`, ZNE spends `shots × len(noise_scaling_list)`, SPAM spends `2**k` calibration circuits per correlated subset, CDR spends `total_state_circuits` extra executions.
3. Report every knob: `folding_type`, `fit_type`, `noise_scaling_list`, `deg`, number of PFR samples, SPAM subset structure, `partition_strat`, `colour_method`, `cx_config`, `correct_counts(method=...)`, `optimisation_level`, `maximum_pattern_gates`, `timeout`, and every seed.
4. Run at least three seeds and report mean ± std. Single-seed mitigation numbers are noise.
5. Snapshot calibration data in the report — `spam.to_dict()`, `placer.to_dict()`, `setup.to_dict()` and `backend_info.to_dict()` are all JSON-serialisable.
6. State the caveats honestly: mitigation is estimator-dependent, bias reduction costs variance, ZNE extrapolation and matrix-inversion SPAM amplify statistical noise and can return values outside `[-1, 1]`, PFR changes the noise channel rather than shrinking it, and calibration data drifts.

## Gotchas / rules

- Nothing in pytket core does ZNE, CDR or PEC. Check the provenance table before you import.
- `AerStateBackend` and `AerUnitaryBackend` take no noise model; snapshot expectations raise `RuntimeError` under one.
- Never build a noise model with `add_all_qubit_quantum_error` / `add_all_qubit_readout_error` — `AerBackend` raises. An empty model silently becomes `None`.
- All six `BackendInfo` error fields default to `None`; edge errors are directional.
- `NoiseAwarePlacement` takes keyword arguments only — the user guide's positional order is wrong.
- `PauliFrameRandomisation()` / `UniversalFrameRandomisation()` take no constructor arguments, and `sample_circuits()` returns unmeasured circuits: add `measure_all()` yourself.
- Frame randomisation costs `4**n_cycles` for the exhaustive set and multiplies your shot budget by the sample count.
- qermit: `ObservableTracker` needs a `QubitPauliOperator`; `AnsatzCircuit` must carry no `Measure` gates; `MitEx.run` returns operators, read them with `.get_dict()`.
- `decompose_TaskGraph_nodes()` returns `None`; `get_task_graph()` needs graphviz.
- SPAM calibration circuits run uncompiled, in order; subsets must be disjoint; `2**n` circuits per correlated group.
- `calculate_matrices` before `calibration_circuits` raises `AttributeError`, not `RuntimeError`.
- `method="invert"` can drop bins via negative-probability compression — use `compress_counts` and say so.
- `n_shots` in `get_operator_expectation_value` is per measurement circuit, not per term.
- `PauliPartitionStrat` has only two members; pytket ships no variance routine and the naive one is a lower bound.
- Contextual passes can emit classical set-bit ops → `allow_classical=False` on hardware.
- Leakage reduction is a `pytket-quantinuum` submission kwarg, not a pass.

## Sources

- <https://docs.quantinuum.com/tket/user-guide/manual/manual_noise.html> · <https://docs.quantinuum.com/tket/api-docs/tailoring.html> · <https://docs.quantinuum.com/tket/api-docs/utils.html>
- <https://docs.quantinuum.com/tket/user-guide/examples/algorithms_and_protocols/measurement_reduction_example.html> · <https://docs.quantinuum.com/tket/user-guide/examples/circuit_compilation/contextual_optimisation.html>
- <https://docs.quantinuum.com/tket/api-docs/_sources/partition.md.txt> · <https://quantinuum.github.io/Qermit/> · <https://github.com/CQCL/Qermit>
- <https://docs.quantinuum.com/tket/extensions/pytket-quantinuum/index.html> · <https://docs.quantinuum.com/tket/extensions/pytket-quantinuum/api.html> · <https://raw.githubusercontent.com/CQCL/pytket-qiskit/main/pytket/extensions/qiskit/backends/aer.py>
- <https://iopscience.iop.org/article/10.1088/2058-9565/ab8e92> (tket overview §7.1) · Wallman & Emerson, *Phys. Rev. A* **94**, 052325 (2016)
- `tket/pytket/docs/tailoring.md` · `pauli.md` · `mapping.md` · `placement.md` · `passes.md` · `changelog.md`
- `tket/pytket/pytket/_tket/placement.pyi` · `partition.pyi` · `tailoring.pyi`; `tket/pytket/pytket/utils/spam.py` · `expectations.py` · `prepare.py`
- `tket/pytket/pytket/backends/backend.py` · `backendinfo.py`; `tket/pytket/binders/tailoring.cpp` · `partition.cpp` · `placement.cpp` · `passes.cpp`; `tket/pytket/tests/mitigation_test.py` · `placement_test.py`
