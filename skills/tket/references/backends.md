# Backends: Simulators, Results, and Hardware Access

A `Backend` is pytket's uniform interface to a simulator, emulator, or QPU. Core pytket
ships **no** backends; every one comes from an extension package. Workflow: build →
compile → process → retrieve → interpret. Verified against pytket 2.18.4 +
pytket-qiskit 0.78.0 (executed).

## The `Backend` abstraction

```python
from pytket.backends import Backend, StatusEnum, CircuitStatus, ResultHandle
from pytket.backends.backendresult import BackendResult   # NOT pytket.backends
from pytket.backends.backendinfo import BackendInfo       # NOT pytket.backends
```

Public surface (verified by execution):

| Member | Meaning |
| --- | --- |
| `default_compilation_pass(optimisation_level=2)` | abstract; pass guaranteeing `required_predicates`. Contents differ per extension — never assume. |
| `get_compiled_circuit(circuit, optimisation_level=2)` | returns a **NEW** circuit (verified: `is not c`); `get_compiled_circuits` for a list |
| `valid_circuit(circuit) -> bool` | checks all `required_predicates` (**NOT** `required_properties`) |
| `required_predicates` | `list[Predicate]` the circuit must satisfy |
| `backend_info` | `BackendInfo` (name, architecture, `gate_set`, `n_cl_reg`, error dicts, `.misc`) |
| `process_circuit(c, n_shots=None, valid_check=True, **kwargs)` | submit one → `ResultHandle` |
| `process_circuits(cs, ...)` | submit many → `list[ResultHandle]`, input order |
| `get_result(handle)` / `get_results(handles)` | blocks until ready → `BackendResult` / list |
| `run_circuit(...)` / `run_circuits(...)` | process + get in one call |
| `get_pauli_expectation_value(state_circuit, pauli)` | native fast path (see below) |
| `get_operator_expectation_value(state_circuit, operator)` | native fast path (see below) |
| `circuit_status(handle)` / `cancel(handle)` | job lifecycle (see below) |

Capability flags (properties, all default `False`): `supports_shots`, `supports_counts`,
`supports_state`, `supports_unitary`, `supports_density_matrix`, `supports_expectation`,
`supports_contextual_optimisation` (**NOT** `supports_contextual_expectation`), plus
`expectation_allows_nonhermitian` and `persistent_handles`. Query at runtime instead of
branching on backend type:

```python
assert backend.supports_counts
```

`optimisation_level`: 0 = minimum to satisfy device constraints, 1 = light, 2 = heavier
(default). Some extensions also accept 3.

### Canonical flow (verified, executed)

```python
from pytket import Circuit
from pytket.extensions.qiskit import AerBackend

circ = Circuit(2, 2).H(0).CX(0, 1)
circ.measure_all()

backend = AerBackend()
compiled = backend.get_compiled_circuit(circ, optimisation_level=1)
assert backend.valid_circuit(compiled)

handle = backend.process_circuit(compiled, n_shots=1000)
result = backend.get_result(handle)
counts = result.get_counts()          # Counter({(0,0): ~500, (1,1): ~500})
```

Shorter form: `result = backend.run_circuit(compiled, n_shots=1000, seed=23)`.
Compilation cannot fix paradigm constraints (e.g. `NoMidMeasurePredicate`): pick a
backend that allows what the algorithm needs. Pass details: `references/compilation.md`.

## Simulator choice

| Backend | Package / install | Returns | Noise | When to use |
| --- | --- | --- | --- | --- |
| `AerBackend` | `pip install "pytket-qiskit[aer]"` | shots / counts | optional `noise_model=` | default all-purpose sampling |
| `AerStateBackend` | same | `get_state()` — shape `(4,)` for 2 qubits (verified) | none | exact amplitudes, small circuits |
| `AerUnitaryBackend` | same | `get_unitary()` — shape `(4,4)` (verified) | none | verifying a reusable subcircuit |
| `AerDensityMatrixBackend` | same | density matrix | optional | mixed states under noise |
| `CuTensorNetStateBackend` / `CuTensorNetShotsBackend` | `pytket-cutensornet` (Linux, Py 3.10–3.12, NVIDIA CC≥7.0) | statevector / shots | none | very large circuits on GPUs |
| `QulacsBackend(result_type="density_matrix")` | `pytket-qulacs` | shots / state / density | configurable | lightweight alternative |
| `BraketBackend(local=True)` | `pytket-braket` | shots / counts | local sims | offline AWS Braket development |
| `IBMQBackend` / `IBMQEmulatorBackend` | `pytket-qiskit` | shots / counts | real hw / Aer model from live device data | IBM QPU + dry runs |
| `QuantinuumBackend("H2-1LE")` | `pytket-quantinuum[pecos]` | shots / counts | noiseless local emulation | offline Quantinuum-targeted work |

Import: `from pytket.extensions.qiskit import AerBackend, AerStateBackend,
AerUnitaryBackend, AerDensityMatrixBackend, IBMQBackend, IBMQEmulatorBackend`.

Verified `AerBackend` facts: `supports_shots/counts/expectation == True`,
`supports_state/unitary == False`; `backend_info.name == "AerBackend"`, 40 nodes,
`gate_set` size 46. Constructor: `AerBackend(noise_model=None,
simulation_method="automatic", crosstalk_params=None, n_qubits=40)`. A `NoiseModel`
(from `qiskit_aer.noise`) also adds connectivity constraints, so
`default_compilation_pass` starts routing. Noise models in general: `references/noise.md`.

**Traps:**
- `pytket-aer` **does not exist**. Without the `[aer]` extra, importing `AerBackend`
  raises `ImportError`.
- The class is `IBMQBackend`, **not** `IBMBackend`.
- `BraketBackend` is **one** class (`local=` kwarg); `BraketAwsBackend`/`BraketLocalBackend`
  do not exist.
- `CutensornetBackend` does not exist — it is `CuTensorNetStateBackend` /
  `CuTensorNetShotsBackend`.
- `ForestBackend`, `ForestStateBackend`, `ProjectQBackend`, `QulacsGPUBackend` appear
  only in the **stale** `comparing_simulators.html` notebook and belong to
  archived/absent extensions. Do not recommend. Extension status matrix:
  `references/interop.md`.

## Shots, results, and bit ordering

```python
handle = backend.process_circuit(compiled, n_shots=2000, seed=23)
result = backend.get_result(handle)

shots = result.get_shots()    # np.ndarray shape (n_shots, n_bits), dtype uint8 (verified)
counts = result.get_counts()  # Counter[tuple[int, ...], int]
```

`n_shots`: one int broadcast to all circuits, or a per-circuit sequence (mismatch →
`ValueError`); `None` for state/unitary backends, which ignore shots entirely.
`seed`: verified reproducible — two `run_circuit(..., n_shots=200, seed=123)` calls give
identical counts. Backends that do not use a kwarg silently ignore it (so QPU runs are
never made deterministic by a seed).

`BackendResult` accessors (all verified present in `backendresult.py`):
`get_counts()`, `get_shots()`, `get_state()`, `get_unitary()`, `get_density_matrix()`,
`get_result(...)` (generic accessor), `get_empirical_distribution()`,
`get_probability_distribution()`, `get_debug_info()`, `to_dict()` /
`BackendResult.from_dict(d)`. With contextual post-processing (`postprocess=True`):
`get_counts(ppcirc=...)` / `get_shots(ppcirc=...)`.

### Ordering: pytket is ILO-BE — the opposite of Qiskit

Counts keys are `tuple`s of ints ordered by classical bit index **ascending** (ILO),
and `q[0]` is the **leftmost / most-significant** element (big-endian). Verified:

- `X(0)` only, measured 0→0, 1→1, 2→2 → `Counter({(1,0,0): 100})`
- 3-qubit GHZ → `Counter({(0,0,0): 514, (1,1,1): 486})`

```python
from pytket.circuit import BasisOrder   # exactly two members: ilo, dlo

result.get_counts()                        # ILO (default)
result.get_counts(basis=BasisOrder.dlo)    # reversed, Qiskit-style
```

Marginalise / permute by passing explicit ids: `result.get_counts([Bit(1), Bit(2)])`,
`result.get_state([Qubit(1), Qubit(0)])` (state/unitary results accept only a
*permutation of all* qubits; a subset raises `ValueError`).

Helpers (`pytket.utils`, import paths verified): `readout_counts(result)`,
`counts_from_shot_table(shot_table)`, `probs_from_counts(counts)`,
`OutcomeArray` (from `pytket.utils.outcomearray`). Compare simulated outputs up to
global phase with `pytket.utils.compare_statevectors` / `compare_unitaries`, never
elementwise.

## Expectation values

Pauli algebra (`QubitPauliString`, `QubitPauliOperator`, `.state_expectation`) →
`references/algorithms.md`. The backend-specific rule:

**`Backend.get_operator_expectation_value(state_circuit, operator)` and
`Backend.get_pauli_expectation_value(state_circuit, pauli)` take NO `n_shots` kwarg**
(verified: passing one raises `TypeError`; the Aer override signature is
`(state_circuit, operator, valid_check=True)`). They are state-exact, gated on
`backend.supports_expectation`; `expectation_allows_nonhermitian` says whether complex
coefficients are accepted.

For **shot-based** values use the module-level utilities:

```python
from pytket.utils import get_operator_expectation_value

val = get_operator_expectation_value(
    circ, op, backend, n_shots=2000,
    partition_strat=None,                 # or PauliPartitionStrat.* (references/algorithms.md)
    colour_method=None,                   # GraphColourMethod.LargestFirst default
)
```

Verified numbers: Bell state `<ZZ>` → `1.0000000000000002`; 3-term Hamiltonian exact
`0.05877852522924734` vs raw shots `0.05768` vs measurement-reduced `0.05826`.
Snapshot expectation methods raise `RuntimeError` when the `AerBackend` carries a noise
model (no pure state exists). Mitigation → `references/noise.md`.

## Batch submission

```python
compiled_list = backend.get_compiled_circuits(circ_list)
handles = backend.process_circuits(
    compiled_list, n_shots=100, postprocess=True, seed=5
)                                # -> list[ResultHandle]   (verified type)
results = backend.get_results(handles)   # -> list[BackendResult]
# verified: 3 handles -> 3 results, 100 shots each
```

**There is no `ResultBundle` in pytket** — that is a `qnexus` concept. pytket batching
is `list[ResultHandle]` + `list[BackendResult]`.

Batching pays off on queued devices (IBM, Braket); local simulators just loop.
`postprocess=True` attaches a classical postprocessing circuit to the result and only
takes effect when `backend.supports_contextual_optimisation` is true (off by default);
retrieve with `get_counts(ppcirc=...)` when handling it manually.

Hardware-agnostic code rules: check `supports_*` before calling; compile with the
backend's own `get_compiled_circuit(s)`; keep handles so results can be fetched later;
never assume a simulator's gateset; split "state circuit" from "measurement circuits"
so statevector backends get the state circuit alone; extra kwargs are silently ignored
by backends that do not use them (fine for `seed`, **not** fine for cost-bearing
parameters like `max_cost`).

## Job lifecycle

```python
from pytket.backends import ResultHandle, StatusEnum
from pytket.backends.status import WAITING_STATUS   # {QUEUED, SUBMITTED, RUNNING}

status = backend.circuit_status(handle)   # -> CircuitStatus (NamedTuple)
if status.status is StatusEnum.COMPLETED:
    counts = backend.get_result(handle).get_counts()
backend.cancel(handle)                    # NotImplementedError unless overridden
```

`StatusEnum` (8 members, verified in `status.py`): `COMPLETED`, `QUEUED`, `SUBMITTED`,
`RUNNING`, `RETRYING`, `CANCELLING`, `CANCELLED`, `ERROR`. `CircuitStatus` fields:
`status`, `message`, `error_detail`, timestamps (`queued_time`, `submitted_time`,
`running_time`, `completed_time`, `cancelled_time`, `error_time`), `queue_position`,
plus `to_dict()`/`from_dict()`.

**Save the handle before waiting.** If `backend.persistent_handles`, handles survive
sessions:

```python
s = str(handle)                       # "('5e8f3dcb…', 0)"
handle = ResultHandle.from_str(s)
result = backend.get_result(handle)   # from a fresh backend instance
```

`get_result` blocks until completion; free the result cache with
`backend.pop_result(handle)` / `backend.empty_cache()` (`run_circuits` pops
automatically).

## Quantinuum hardware — the current reality

**As of pytket-quantinuum 0.56.0 the extension no longer allows submission to
Quantinuum devices — use the `qnexus` package.** (Quoting the official index page.)
Latest is 0.59.3 (2026-09-15); a 0.55.x maintenance line still ships for the legacy
submission path. So: **pytket-quantinuum = compile target + local emulator; qnexus =
submission route.**

```bash
pip install pytket-quantinuum          # compile target
pip install "pytket-quantinuum[pecos]" # + H2-1LE local emulator (noiseless)
pip install qnexus                     # actual hardware submission
```

### Machine naming

| Name | What it is | Notes |
| --- | --- | --- |
| `H2-1` | real QPU | submission via qnexus only |
| `H2-1E` | remote noisy emulator | runs on Quantinuum servers |
| `H2-1SC` | syntax checker | validates without executing; `NoSyntaxChecker` if unavailable |
| `H2-1LE` | **local** emulator | `[pecos]` extra; noiseless; accepts `seed` + `multithreading`; `QuantinuumBackend.is_local_emulator` |
| `Helios-1` | newer-generation QPU | reachable only via Nexus `HeliosConfig(system_name="Helios-1")` |

Suffix rule: bare = QPU, `E` = remote emulator, `SC` = syntax checker, `LE` = local
emulator. All remote H2 targets cap at **56 qubits** (`MaxNQubitsPredicate`). `H2`
device data: `n_qubits=56, n_cl_reg=4000, gate_set={Rz, PhasedX, ZZMax, ZZPhase, TK2}`,
default 2qb gate `ZZPhase`. `H1-1`/`H1-1E` survive only in stale docs.

### Compile target

```python
from pytket.extensions.quantinuum import QuantinuumBackend

backend = QuantinuumBackend(device_name="H2-1E")   # parameter is device_name, NOT machine_name
compiled = backend.get_compiled_circuit(circ)
```

Key names: `QuantinuumBackendData`, `QuantinuumBackendCompilationConfig`, `H2`,
`QuantinuumAPI`, `QuantinuumAPIOffline`. `default_compilation_pass(optimisation_level=2,
timeout=300)` accepts **0–3** (3 adds `RemoveBarriers()` + `GreedyPauliSimp()`, whose
per-thread timeout defaults to 5 minutes). Native gateset `{Rz, PhasedX, ZZMax, ZZPhase}`
via `AutoRebase`, squashed to `{PhasedX, Rz}` via `AutoSquash`. Submission language:
`Language` enum `QASM`/`QIR`/`PQIR`, default **QIR**.

### Auth and credentials

`QuantinuumConfig` fields: `username`, `refresh_token`, `id_token`,
`refresh_token_timeout`, `id_token_timeout` — **no `api_token`**.
`set_quantinuum_config(username)` writes the username to the shared pytket config file.
Credentials come from environment variables only — never hardcode, never print:

```python
import os
token = os.environ["NEXUS_API_TOKEN"]   # illustrative name; never a literal
```

### Submission kwargs, cost, exceptions

`process_circuits(..., postprocess=, simplify_initial=, noisy_simulation=,
leakage_detection=True, n_leakage_detection_qubits=N, seed=)` (the last two emulator /
device-specific); prune flagged shots with `prune_shots_detected_as_leaky(result)`.
Cost is **capped**, not quoted: `max_cost` (HQC) on `process_circuits` /
`qnx.execute` / `qnx.start_execute_job` — **there is no `backend.cost()`**.
Exceptions: `BackendOfflineError`, `BatchingUnsupported`, `DeviceNotAvailable`,
`GetResultFailed`, `LanguageUnsupported`, `MaxShotsExceeded`, `NoSyntaxChecker`,
`WasmUnsupported`, `QuantinuumAPIError`.

### qnexus submission flow

```python
import qnexus as qnx

qnx.login()                                   # browser; or qnx.login_with_credentials()
project = qnx.projects.get_or_create(name="my-project")
circ_ref = qnx.circuits.upload(backend.get_compiled_circuit(circ), name="bell")

job = qnx.start_execute_job(
    programs=[circ_ref], n_shots=[1000],
    backend_config=qnx.models.QuantinuumConfig(device_name="H2-1E"),
    name="my-execute-job", max_cost=10.0,
)
qnx.jobs.wait_for(job)
result = qnx.jobs.results(job)[0].download_result()   # a pytket BackendResult
counts = result.get_counts()
```

Also: `qnx.execute(...)` (blocking variant), `qnx.jobs.cancel(job)` (requested, not
guaranteed — re-check status), `qnx.filesystem.save(path=..., ref=job)` /
`qnx.filesystem.load(path=...)` to persist job refs across sessions. Iterate on
`H2-1SC` (syntax) and `H2-1LE`/`H2-1E` (emulation); reserve `H2-1` for final runs.

## Other hardware extensions

- **IBM** (`pytket-qiskit`): `IBMQBackend(backend_name, instance=None, monitor=True,
  service=None, token=None, sampler_options=None, use_fractional_gates=False)`;
  `IBMQEmulatorBackend` (needs a real IBM account — pulls device characterisation
  live); `set_ibmq_config(...)` — token from a variable, never a literal.
- **AWS Braket** (`pytket-braket`): one class
  `BraketBackend(local=False, local_device='default', device=None, region='',
  s3_bucket=None, s3_folder=None, device_type=None, provider=None, aws_session=None,
  verbatim=False)`.
- **IQM** (`pytket-iqm`): `IQMBackend`.

Full extension/converter matrix: `references/interop.md`.

## Embedding into Qiskit

`pytket-qiskit` ships four Qiskit-side wrappers. **None of them is re-exported at the
`pytket.extensions.qiskit` top level** — importing them from there raises `ImportError`.
Use the submodule paths below (verified against the installed 0.78.0 wheel, which has no
`__all__`). Spelling is `Tket…`, **not** `TKet…`.

| class | import from | signature |
|---|---|---|
| `TketBackend` | `pytket.extensions.qiskit.tket_backend` | `(backend: Backend, comp_pass: BasePass \| None = None)` — wraps any pytket `Backend` as a Qiskit `BackendV2` |
| `TketPass` | `pytket.extensions.qiskit.tket_pass` | `(tket_pass: BasePass)` — a tket pass inside a Qiskit transpile sequence |
| `TketAutoPass` | `pytket.extensions.qiskit.tket_pass` | `(backend: BackendV2, optimisation_level: int = 2, instance: str \| None = None, token: str \| None = None)` |
| `TketJob` | `pytket.extensions.qiskit.tket_job` | wraps `ResultHandle`s as a Qiskit job |

Always pass the tket compilation pass explicitly — the default is `None`, which leaves the
circuit unrebased for the wrapped device:

```python
from pytket.extensions.qiskit.tket_backend import TketBackend

qis_backend = TketBackend(backend, backend.default_compilation_pass(optimisation_level=2))
```

## Writing your own `Backend`

Subclass `pytket.backends.Backend`; set the `_supports_*` class flags; implement the
abstract members: `required_predicates`, `rebase_pass`, `default_compilation_pass`,
`_result_id_type`, `process_circuits`, `circuit_status`. The base `__init__` creates
`self._cache`; store finished results at `self._cache[handle]["result"]` and the
inherited `get_result`/`get_results`/`run_circuits`/`pop_result` all work. Condensed
from the in-repo reference `TketSimBackend` / `TketSimShotBackend`
(`tket/pytket/tests/simulator/tket_sim_backend.py:72` and `:145`).
**Illustrative skeleton — not executed as part of this document.**

```python
from collections.abc import Sequence
from uuid import uuid4

from pytket.backends.backend import Backend
from pytket.backends.backend_exceptions import CircuitNotRunError
from pytket.backends.backendresult import BackendResult
from pytket.backends.resulthandle import ResultHandle, _ResultIdTuple
from pytket.backends.status import CircuitStatus, StatusEnum
from pytket.circuit import Circuit, OpType
from pytket.passes import AutoRebase, BasePass, DecomposeBoxes, SequencePass, SynthesiseTket
from pytket.predicates import NoClassicalControlPredicate, NoFastFeedforwardPredicate, Predicate
from pytket.utils.results import KwargTypes

_GATE_SET = {OpType.CX, OpType.CZ, OpType.Rz, OpType.Rx, OpType.H, OpType.S, OpType.T, OpType.X}


class MyStateBackend(Backend):
    _supports_state = True
    _persistent_handles = False

    @property
    def _result_id_type(self) -> _ResultIdTuple:
        return (str,)

    @property
    def required_predicates(self) -> list[Predicate]:
        return [NoClassicalControlPredicate(), NoFastFeedforwardPredicate()]

    def rebase_pass(self) -> BasePass:
        return AutoRebase(_GATE_SET)

    def default_compilation_pass(self, optimisation_level: int = 1) -> BasePass:
        assert optimisation_level in range(3)
        seq = [DecomposeBoxes()]
        if optimisation_level >= 1:
            seq.append(SynthesiseTket())
        seq.append(self.rebase_pass())
        return SequencePass(seq)

    def process_circuits(
        self,
        circuits: Sequence[Circuit],
        n_shots: int | Sequence[int] | None = None,
        valid_check: bool = True,
        **kwargs: KwargTypes,
    ) -> list[ResultHandle]:
        circuits = list(circuits)
        if valid_check:
            self._check_all_circuits(circuits)
        handles = []
        for circuit in circuits:
            state = circuit.get_statevector()
            handle = ResultHandle(str(uuid4()))
            self._cache[handle] = {
                "result": BackendResult(q_bits=sorted(circuit.qubits), state=state)
            }
            handles.append(handle)
        return handles

    def circuit_status(self, handle: ResultHandle) -> CircuitStatus:
        if handle in self._cache:
            return CircuitStatus(StatusEnum.COMPLETED)
        raise CircuitNotRunError(handle)
```

Expose `backend_info` too: `BackendInfo("MyStateBackend", "MySimulator", "1.0",
FullyConnected(4), _GATE_SET | {OpType.Measure}, supports_midcircuit_measurement=False,
misc={...})`.

Rules easy to get wrong: pass `q_bits` most-significant first and `c_bits` in
left-to-right readout order; apply `circuit.phase` and
`circuit.implicit_qubit_permutation()` for statevector results; for a shots backend set
`_supports_shots = _supports_counts = True`, validate with
`Backend._get_n_shots_as_list(n_shots, len(circuits), optional=False)`, and build
results with `OutcomeArray.from_readouts(readouts)`; `_persistent_handles = True` only
if a handle resolves from a fresh instance; for remote backends, submit and return
without waiting, poll in `circuit_status`.

## Gotchas / rules

- **Compile before submitting**: `process_circuit(s)` runs `valid_check=True` by
  default and raises `CircuitNotValidError` naming the index and failed predicate;
  `valid_check=False` sends an invalid circuit to the device. Check with
  `backend.valid_circuit` first.
- **Keep the handles**: without a `ResultHandle` there is no way to fetch a result; on
  a non-persistent backend none after the session ends.
- **State/unitary backends ignore shots** and reject measurements, conditionals,
  `Reset`, `Collapse`.
- **Simulator seeds do not make QPU results deterministic** — unsupported kwargs are
  ignored silently.
- **Device specifics live in `backend.backend_info.misc`** (JSON-serialisable map;
  `get_misc(key)`, `add_misc(key, val)` raises `KeyError` on duplicates).
- **Never embed tokens/usernames/instance CRNs** — `os.environ` or the provider's
  saved-account mechanism only.
- **`default_compilation_pass` differs per extension** (it is abstract on `Backend`);
  always compile with the target backend's own pass.
- **Results are immutable once fetched**: re-calling `get_result` on a cached handle
  returns the cached object, not a fresh device query. Fetch once; serialise with
  `to_dict()` for a durable record. The cache grows without bound — `pop_result` /
  `empty_cache`.
- **Bit ordering is ILO-BE**, the opposite of Qiskit — pass `basis=BasisOrder.dlo`
  when comparing.
- Expectation-value error scales as `1/sqrt(n_shots)`; marginalise before
  `expectation_from_counts` (it uses **every** classical bit).

## Sources

- <https://docs.quantinuum.com/tket/api-docs/backends.html>
- <https://docs.quantinuum.com/tket/api-docs/extensions.html>
- <https://docs.quantinuum.com/tket/user-guide/manual/manual_backend.html>
- <https://docs.quantinuum.com/tket/user-guide/examples/backends/backends_example.html>
- <https://docs.quantinuum.com/tket/user-guide/examples/backends/creating_backends.html>
- <https://docs.quantinuum.com/tket/extensions/pytket-quantinuum/index.html>
- <https://docs.quantinuum.com/tket/extensions/pytket-qiskit/index.html>
- <https://docs.quantinuum.com/nexus/nexus_api/execute.html>
- <https://pypi.org/project/pytket-quantinuum/> · <https://pypi.org/project/pytket-qiskit/> · <https://pypi.org/project/qnexus/>
- Repo paths (local tket clone, @ `d2bb207`): `tket/pytket/pytket/backends/backend.py`,
  `backendresult.py`, `backendinfo.py`, `status.py`, `resulthandle.py`;
  `tket/pytket/pytket/utils/expectations.py`, `outcomearray.py`, `results.py`;
  `tket/pytket/tests/simulator/tket_sim_backend.py`;
  `tket/pytket/docs/backends.md`, `extensions.md`.
