---
name: tket
description: Build, optimise, and execute quantum circuits with TKET (pytket) from Quantinuum. Use for pytket circuit construction, the half-turn angle convention, compilation passes and predicates, architecture-aware placement and routing, rebase to a hardware gateset, local simulation with Aer or pytket-qiskit, shot sampling and expectation values, Pauli measurement reduction, noise tailoring and SPAM mitigation, Quantinuum H2 execution via qnexus, OpenQASM 2 import/export, and conversions between pytket and Qiskit, Braket, IQM, or cutensornet.
license: Apache-2.0
compatibility: Python 3.10+ on a supported 64-bit platform. Core workflows need pytket; local shot simulation needs pytket-qiskit with the [aer] extra (there is no pytket-aer distribution). Quantinuum hardware needs pytket-quantinuum plus qnexus, network access, and a Quantinuum Nexus account. ZNE/CDR/PEC need qermit; ZX tensor simulation needs pytket[zx].
metadata:
  version: "1.0"
  skill-author: Yi-Fan Wu
---

# TKET (pytket)

Use current pytket 2.x APIs to build circuits, compile them against a real coupling graph and gateset, and execute them through a `Backend`.

This skill was verified on **2026-09-30** against the PyPI releases `pytket==2.18.4`, `pytket-qiskit==0.78.0`, `qiskit-aer==0.17.2`, `pytket-quantinuum==0.59.3`, and `qermit==0.9.3`, and against a clone of `Quantinuum/tket` at commit `d2bb207981244205cbf9ddc9ef0257112c366558`. Every snippet below was executed. Check [references/sources.md](references/sources.md) before changing pins or documenting newly released behavior.

## Choose the Right Path

| Goal | Recommended interface |
|---|---|
| Build and inspect circuits | `pytket.circuit.Circuit` |
| Exact statevector or unitary | `AerStateBackend` / `AerUnitaryBackend` |
| Shot sampling, local and free | `AerBackend` (`pytket-qiskit[aer]`) |
| Shot sampling with a device noise model | `AerBackend(noise_model=...)` |
| Compile for a coupling graph | `passes.FullMappingPass` or `backend.default_compilation_pass` |
| Rebase to a hardware gateset | `passes.AutoRebase(gateset)` |
| Expectation values, exact | `backend.get_operator_expectation_value` |
| Expectation values, shot-based | `pytket.utils.get_operator_expectation_value(..., n_shots=...)` |
| Reduce the number of Pauli measurements | `pytket.partition.measurement_reduction` |
| Quantinuum H2 hardware | `pytket-quantinuum` to compile, `qnexus` to submit |
| IBM hardware | Prefer the `qiskit` skill, or `pytket-qiskit` `IBMQBackend` |
| Differentiable quantum ML with autodiff | Prefer the `pennylane` skill |
| Zero-noise extrapolation / CDR / PEC | `qermit` (NOT pytket core) |
| Open-system master-equation dynamics | Prefer the `qutip` skill |

## Installation

Create an isolated environment and install only what the task needs:

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# POSIX:    source .venv/bin/activate

python -m pip install "pytket==2.18.4"
python -m pip install "pytket-qiskit[aer]==0.78.0"   # local shot simulation
```

Add only when needed:

```bash
python -m pip install "pytket-quantinuum==0.59.3"     # Quantinuum compile target
python -m pip install "pytket-quantinuum[pecos]"      # + H2-1LE local emulator
python -m pip install "qnexus"                        # Quantinuum hardware submission
python -m pip install "qermit==0.9.3"                 # ZNE / CDR / PEC
python -m pip install "pytket[zx]"                    # ZX tensor simulation
```

Do **not** install `pytket-aer` — it does not exist on PyPI. The Aer backends ship inside `pytket-qiskit` behind the `[aer]` extra. Do not install `pytket-terra` or `qiskit-terra` (legacy metapackages). On macOS, a conda-provided Python can cap pytket at 1.11.0 (issue tket#926); use an official Python distribution.

For version floors, optional extras, credential handling, and environment repair, read [references/setup.md](references/setup.md).

## Core Workflow

Follow this sequence for every hardware-oriented workload:

1. **Build** the circuit with `Circuit(n_qubits, n_bits)`. Rotation angles are in **half turns**: `Rz(0.25, 0)` is a quarter turn, i.e. π/4 radians.
2. **Decompose** boxes before anything that must see plain gates: `passes.DecomposeBoxes()`.
3. **Optimise** with a TKET pass — `SynthesiseTket()` for a generic pass, `FullPeepholeOptimise()` for maximum gate reduction.
4. **Map** onto the target coupling graph with `FullMappingPass(architecture, placer, routing_methods)`, which places, routes, and records the initial and final maps.
5. **Rebase** to the device gateset with `AutoRebase(gateset)`.
6. **Execute** through a backend: `backend.run_circuit(backend.get_compiled_circuit(circuit), n_shots=..., seed=...)`.
7. **Analyse** the `BackendResult` — `get_counts()` keys are bit-tuples in ILO-BE order.

Apply steps 2–5 as one `SequencePass` to one `CompilationUnit`, not one pass at a time to a bare circuit. The `CompilationUnit` is what carries `initial_map` and `final_map`; without it you lose the qubit relabelling that routing introduced.

For parameterised ansätze, compile the parameterised circuit **once**, then substitute values with `circuit.symbol_substitution({theta: value})`. Do not rebuild and recompile inside every optimiser iteration.

## Quick Local Sampling

```python
from pytket.circuit import Circuit
from pytket.extensions.qiskit import AerBackend

circuit = Circuit(2, 2)
circuit.H(0)
circuit.CX(0, 1)
circuit.measure_all()

backend = AerBackend()
result = backend.run_circuit(backend.get_compiled_circuit(circuit), n_shots=2000, seed=7)
print(result.get_counts())
```

Counts keys are tuples ordered **ILO-BE** — qubit 0 first, so a Bell pair reads `(0, 0)` and `(1, 1)`. Qiskit prints the opposite order, so the same circuit shows `00`/`11` here and reversed bit strings in Qiskit. Pass `basis=BasisOrder.dlo` when you need Qiskit-style ordering. `seed` makes a *simulator* reproducible; it has no effect on a real QPU.

## Quick Local Statevector

```python
from pytket.circuit import Circuit
from pytket.extensions.qiskit import AerStateBackend

circuit = Circuit(2).H(0).CX(0, 1)

backend = AerStateBackend()
result = backend.run_circuit(backend.get_compiled_circuit(circuit), seed=1)
state = result.get_state()          # get_state() is on BackendResult, NOT on Backend
print([round(abs(a), 6) for a in state])
```

`get_state()` lives on `BackendResult`, not on the backend — `AerStateBackend().get_state(circuit)` raises `AttributeError`. State and unitary backends ignore `n_shots` and reject circuits containing measurements, conditionals, `Reset`, or `Collapse`.

## Quick Local Estimation

```python
from pytket.circuit import Circuit
from pytket.extensions.qiskit import AerBackend
from pytket.pauli import Pauli, QubitPauliString
from pytket.utils import QubitPauliOperator, get_operator_expectation_value

ansatz = Circuit(2).Ry(0.25, 0).CX(0, 1)
zz = QubitPauliString([ansatz.qubits[0], ansatz.qubits[1]], [Pauli.Z, Pauli.Z])
hamiltonian = QubitPauliOperator({zz: 1.0})

backend = AerBackend()
compiled = backend.get_compiled_circuit(ansatz)

exact = backend.get_operator_expectation_value(compiled, hamiltonian)
sampled = get_operator_expectation_value(compiled, hamiltonian, backend, n_shots=20000, seed=11)
print(exact.real, sampled.real)
```

Two type traps. `Backend.get_operator_expectation_value(state_circuit, operator)` takes **no `n_shots` keyword** — the shot-based route is the `pytket.utils` helper. And it requires a `QubitPauliOperator`; passing a bare `QubitPauliString` fails deep inside the Aer extension with `AttributeError: 'QubitPauliString' object has no attribute '_dict'`. Use `backend.get_pauli_expectation_value(state_circuit, pauli)` for a single string. Both are typed `-> complex`, so take `.real` rather than calling `float()`.

`QubitPauliOperator` lives in `pytket.utils`, not `pytket.pauli`.

## Quantinuum H2 Execution

As of `pytket-quantinuum` 0.56.0 the extension **no longer submits to Quantinuum devices**. The split is: `pytket-quantinuum` is the compile target and local emulator; `qnexus` is the submission route.

```python
from pytket.circuit import Circuit
from pytket.extensions.quantinuum import QuantinuumBackend
import qnexus as qnx

circuit = Circuit(2, 2).H(0).CX(0, 1).measure_all()

backend = QuantinuumBackend(device_name="H2-1E")   # device_name, NOT machine_name
compiled = backend.get_compiled_circuit(circuit)

qnx.login()                                        # browser; or login_with_credentials()
project = qnx.projects.get_or_create(name="my-project")
circ_ref = qnx.circuits.upload(compiled, name="bell")

job = qnx.start_execute_job(
    programs=[circ_ref],
    n_shots=[1000],
    backend_config=qnx.models.QuantinuumConfig(device_name="H2-1E"),
    name="bell-execute",
    max_cost=10.0,                                 # HQC cap; there is no backend.cost()
)
qnx.jobs.wait_for(job)
result = qnx.jobs.results(job)[0].download_result()  # a pytket BackendResult
print(result.get_counts())
```

Machine-name suffix rule: bare (`H2-1`) = real QPU, `E` = remote emulator, `SC` = syntax checker, `LE` = local emulator (`[pecos]` extra). Validate on `H2-1SC`, iterate on `H2-1LE` or `H2-1E`, and reserve `H2-1` for final runs. All remote H2 targets cap at 56 qubits. `Helios-1` is reachable only through Nexus `HeliosConfig(system_name="Helios-1")`. Credentials come from environment variables or the provider's saved-account mechanism — never hardcode or print a token.

For the full machine table, submission kwargs, cost model, exception list, and other hardware extensions, read [references/backends.md](references/backends.md).

## Non-Negotiable pytket 2.x Rules

- **Angles are half turns.** `Rx(1.0)` is a 180° rotation. Convert with `value / math.pi` when a paper gives radians.
- **Bit ordering is ILO-BE**, the opposite of Qiskit. Counts keys are bit-tuples with qubit 0 first. Pass `basis=BasisOrder.dlo` when comparing against Qiskit output.
- **Compile before submitting.** `process_circuit(s)` runs `valid_check=True` by default and raises `CircuitNotValidError`. Always use `backend.get_compiled_circuit(...)`.
- **`get_state()`, `get_unitary()`, and `get_density_matrix()` are `BackendResult` methods**, not `Backend` methods.
- **`default_compilation_pass` is abstract on `Backend`** and differs per extension. Use the target backend's own pass when compiling for that backend.
- **`FullyConnected` is not an `Architecture` subclass** and cannot be passed to a placer or routing pass. To skip routing, omit the mapping pass entirely.
- **There is no native QFT** and no random-circuit generator. `pytket.circuit_library` is ~120 gate-*decomposition* builders (e.g. `CX_using_ZZMax()`), not a circuit library in the Qiskit sense.
- **`pytket.partition` is Pauli measurement reduction, not circuit cutting.** `Partition`, `SubCircuit`, and `partition_circuit` do not exist.
- **`pytket.qasm` is OpenQASM 2 only** — nine functions, no QASM3 anywhere. `maxwidth` caps the *classical* register width, not the qubit count. Complex classical operations require `header="hqslib1"`.
- **ZNE, CDR, and PEC live in `qermit`**, not pytket. Core pytket offers only `pytket.tailoring.FrameRandomisation` / `PauliFrameRandomisation` / `UniversalFrameRandomisation` (the latter two take **no constructor arguments**).
- **Keep the `ResultHandle`.** Without it there is no way to fetch a result, and a non-persistent backend has none after the session ends.
- **Expectation error scales as `1/sqrt(n_shots)`**, and `expectation_from_counts` uses *every* classical bit — marginalise first.
- Do not write pytket 1.x code: `Placement.modify_config` and similar were removed in 2.0.

## Compilation and Execution Modes

Batch submission sends independent circuits together and is the efficient path for parameter sweeps:

```python
from pytket.circuit import Circuit
from pytket.extensions.qiskit import AerBackend

backend = AerBackend()
circuits = [Circuit(2, 2).H(0).CX(0, 1).measure_all() for _ in range(3)]
compiled_circuits = [backend.get_compiled_circuit(c) for c in circuits]

handles = backend.process_circuits(compiled_circuits, n_shots=1000, seed=5)
results = backend.get_results(handles)          # list[BackendResult], in submission order
print(len(results), results[0].get_counts())
```

Or the shortcut `backend.run_circuits(circuits, n_shots=..., seed=...)`, which returns `list[BackendResult]` directly. Results are immutable once fetched and the cache grows without bound — `pop_result(handle)` or `empty_cache()`.

For a hardware-agnostic script, gate on capability flags rather than on a concrete class:

```python
from pytket.extensions.qiskit import AerBackend

backend = AerBackend()
if backend.supports_state:
    ...   # exact statevector available
if backend.supports_expectation and backend.expectation_allows_nonhermitian:
    ...   # non-Hermitian expectation values available
print(backend.supports_shots, backend.supports_counts)
```

## Reference Map

Read only the files needed for the current task:

| Topic | Reference |
|---|---|
| Versions, installation, credentials, environment repair | [references/setup.md](references/setup.md) |
| Circuit construction, angles, registers, boxes, symbols, QASM I/O | [references/circuits.md](references/circuits.md) |
| Passes, predicates, placement, routing, rebasing, combinators | [references/compilation.md](references/compilation.md) |
| Backends, simulators, results, batch, Quantinuum hardware, qnexus | [references/backends.md](references/backends.md) |
| Expectation values, Pauli algebra, measurement reduction, ZX, tableau, assertions | [references/algorithms.md](references/algorithms.md) |
| Noise models, tailoring, SPAM correction, contextual optimisation | [references/noise.md](references/noise.md) |
| QASM 2, Quipper, Qiskit/Braket/IQM conversion, cross-SDK traps | [references/interop.md](references/interop.md) |
| Upstream docs, extension status, version baseline, refresh procedure | [references/sources.md](references/sources.md) |

## Bundled Scripts

Run from the skill directory:

```bash
# Installed-package, version-drift, and legacy-package checks; no network or credential reads
python scripts/check_environment.py
python scripts/check_environment.py --require-simulator --strict --json

# Runnable local sampling, statevector, expectation-value, and batch examples
python scripts/run_local_simulation.py --shots 2000 --qubits 3 --theta 0.25 --seed 7

# Compile a demo or a QASM file and report gate counts, depth, maps, and predicates
python scripts/compile_and_report.py --demo adder-ish --qubits 5 --architecture linear:6
python scripts/compile_and_report.py --qasm circuit.qasm --optimisation-level 2 --verify-semantics
```

All three scripts answer `--help` without pytket installed and never contact a device, submit a job, or read credentials.

## Final Checklist

Before returning pytket code:

1. Confirm `pytket` and the extension versions with `scripts/check_environment.py`.
2. Run the circuit locally on `AerBackend` before touching hardware.
3. Verify every angle is in half turns, and convert radian values from papers with `/ math.pi`.
4. Compile with the *target backend's* `default_compilation_pass`, or an explicit `SequencePass` ending in `AutoRebase` to the device gateset.
5. Check the compiled circuit against `backend.required_predicates` — a `FAIL` on `NoMidMeasurePredicate`, `DefaultRegisterPredicate`, or `DirectednessPredicate` after routing is usually benign; `ConnectivityPredicate` or `GateSetPredicate` failing is a real problem.
6. Record `initial_map` / `final_map` from the `CompilationUnit` when routing renamed qubits.
7. Read results with ILO-BE bit ordering in mind, and marginalise before `expectation_from_counts`.
8. For Quantinuum hardware, validate on `H2-1SC`, iterate on an emulator, set `max_cost`, and submit through `qnexus`.
9. Never expose tokens in source, logs, notebooks, or version control.

## Citing TKET

If TKET materially contributed to a manuscript, report, presentation, or code release, cite it and tell the user you did so:

> Sivarajah, S., Duncan, R., & Kissinger, A. (2020). TKET: A Retargetable Compiler for NISQ
> Devices. *Quantum Science and Technology*, 6(1), 014003. arXiv:2003.10611.
> https://doi.org/10.48550/arXiv.2003.10611

Companion references for specific features: routing and placement arXiv:1902.08091, phase gadgets arXiv:1906.01734, UCC circuits arXiv:2007.10515. The authoritative machine-readable record is `CITATION.cff` in the `Quantinuum/tket` repository; fetch it before writing the reference and take the author list, year, and version from that record rather than from memory.

If this skill is grafted into K-Dense-AI `scientific-agent-skills`, also add the collection citation given in that repository's contributing guide.
