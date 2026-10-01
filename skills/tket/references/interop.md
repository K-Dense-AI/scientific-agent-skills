# Interoperability: OpenQASM, QIR, Quipper, Extensions, Cross-SDK Gotchas

## OpenQASM 2 — `pytket.qasm`

`pytket.qasm` exports **exactly nine functions** — no classes, no options object
(`QASM2Options`, `strict_qasm2`, `opaque_declares` do not exist anywhere in pytket):

```python
from pytket.qasm import (circuit_to_qasm, circuit_to_qasm_str, circuit_to_qasm_io,
                         circuit_from_qasm, circuit_from_qasm_str, circuit_from_qasm_io,
                         circuit_from_qasm_wasm, circuit_from_qasm_str_wasm,
                         circuit_from_qasm_str_wasmmh)
```

| Function | Signature |
|---|---|
| `circuit_from_qasm` | `(input_file, encoding="utf-8", maxwidth=32) -> Circuit` |
| `circuit_from_qasm_str` | `(qasm_str, maxwidth=32) -> Circuit` |
| `circuit_from_qasm_io` | `(stream_in, maxwidth=32) -> Circuit` |
| `circuit_from_qasm_wasm` | `(input_file, wasm_file, encoding="utf-8", maxwidth=32) -> Circuit` |
| `circuit_from_qasm_str_wasm` | `(qasm_str, wasm: bytes, maxwidth=32) -> Circuit` |
| `circuit_from_qasm_str_wasmmh` | `(qasm_str, wasmmh: WasmModuleHandler, maxwidth=32) -> Circuit` |
| `circuit_to_qasm` | `(circ, output_file, header="qelib1", maxwidth=32) -> None` |
| `circuit_to_qasm_str` | `(circ, header="qelib1", include_gate_defs=None, maxwidth=32) -> str` |
| `circuit_to_qasm_io` | `(circ, stream_out, header="qelib1", include_gate_defs=None, maxwidth=32) -> None` |

Exceptions live at **`pytket.qasm.qasm`**, not `pytket.qasm` (the package `__init__` re-exports
only the nine functions; the submodule `qasm` is reachable as an attribute):

```python
from pytket.qasm.qasm import QASMParseError, QASMUnsupportedError
```

**Malformed QASM often surfaces as a Lark error, not `QASMParseError`** — verified:
`circuit_from_qasm_str("this is not qasm")` raises `lark.exceptions.UnexpectedToken`. Catch
broadly: `except (QASMParseError, Exception)` on untrusted input, or at minimum include
`lark.exceptions.LarkError`.

### Parameter semantics

- **`maxwidth` is the maximum CLASSICAL register width (default 32), not a qubit limit.** There
  is no qubit cap in `pytket.qasm`. Exceeding it on export raises
  `QASMUnsupportedError("Circuit contains a classical register larger than {maxwidth}: ...")`.
- **Headers**: `qelib1` (default), `hqslib1`, `hqslib1_dev`. Complex classical ops
  (`SetBits`, `CopyBits`, `RangePredicate`, `MultiBit`, `ExplicitPredicate`, `ExplicitModifier`)
  require `header="hqslib1"`; under `qelib1` export raises (verified message):
  `QASMUnsupportedError: Complex classical gates not supported with qelib1: try converting with
  header=hqslib1`. `hqslib1_dev` additionally round-trips barrier-like `sleep`/`orderN`/`groupN`
  op data. Include resolution is not filesystem-based: only these three header names load; a
  third-party `.inc` or an include search path raises
  `QASMParseError("Header {name} is not known and cannot be loaded.")`.
- `circuit_from_qasm` **requires the `.qasm` file extension** (`TypeError("Can only convert
  .qasm files")`). Non-UTF-8 files need `encoding=`.
- `include_gate_defs` is an **internal recursion hook**: passing a non-`None` set suppresses the
  `OPENQASM`/`include`/`qreg`/`creg` preamble. Do not set it from user code.
- Angles: the writer emits each parameter as `{p}*pi`, the reader parses `({par})/pi` — QASM
  radians map to pytket half-turns automatically. Sympy symbols survive both directions.
- Register names must match `^[a-z][a-zA-Z0-9_]*$` (lowercase letter first; underscores allowed,
  uppercase/digit first is rejected with a "Try renaming the register with `rename_units`" hint).

### What QASM export silently drops

| Dropped | Detail | Fix |
|---|---|---|
| Global phase | `OpType.Phase` skipped ("global phase is ignored in QASM") | Track `.phase` yourself; compare with `compare_unitaries` (phase-insensitive) |
| Implicit qubit permutations | Re-imported circuit is missing the permutation | `passes.RemoveImplicitQubitPermutation()` before export |
| Calls to `opaque` gates | Declaration parses; **calls are dropped** | Do not rely on opaque gates round-tripping |

Export runs `DecomposeBoxes()` on a **copy** first, so boxes never need manual decomposition for
QASM. Custom `gate` definitions are unrolled on export, not preserved as named gates. Unmapped
OpTypes raise `QASMUnsupportedError("Cannot print command of type: ...")`.

## OpenQASM 3 — not in pytket

**pytket 2.18.x has no OpenQASM 3 support.** No `circuit_to_qasm3*`, no `pytket.qasm.qasm3`, no
`circuit_to_qiskit_qasm3`; `pytket.qasm` is QASM 2 only. The historical
`pytket.extensions.qiskit.qiskit_qasm3_import` is gone from pytket-qiskit `main`.

Working route — through Qiskit's (still experimental) QASM 3 parser:

```python
from qiskit import qasm3
from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit

tkc = qiskit_to_tk(qasm3.loads(qasm3_text))   # import
qasm3_text = qasm3.dumps(tk_to_qiskit(tkc))   # export
```

Every Qiskit-side limitation becomes a pytket limitation, and the endianness/angle conversions
below apply twice. Prefer QASM 2 (or JSON, below) for anything that must round-trip exactly.
The modern interchange format Quantinuum itself ships is **QIR**, via `pytket-qir`:
`pytket.qir.pytket_to_qir` — **export only, there is no `qir_to_tk`**.

## Quipper — `pytket.quipper`

**Import only, path only** — the module exports one function:

```python
from pytket.quipper import circuit_from_quipper

circ = circuit_from_quipper(input_file)   # input_file: str — a path, not a string of Quipper
```

No `circuit_to_quipper`, no `_str` variant, no `encoding` argument. To parse a string, write it
to a temp file first. Target format is Quipper ASCII (`Inputs:`/`Outputs:`, `QGate[...]`,
`QRot[...]`, `Subroutine:`). Global phases ignored; no classical ops, no `QMeas`/`QInit`/`QTerm`;
limited controlled-gate support (unsupported control counts raise `NotImplementedError`).

## Native serialisation (portable)

```python
d = circ.to_dict();  circ2 = Circuit.from_dict(d)      # dict form
s = circ.to_json();  circ3 = Circuit.from_json(s)      # JSON added in pytket 2.13 (Feb 2026)
```

These preserve everything QASM drops (global phase, permutations, boxes). Pickle works but is
discouraged for untrusted input.

## Extension converter matrix

Status per the official extension index and each repo, verified 2026-09-30. The old
`pytket-extensions` monorepo is gone; each extension is its own repo under
`github.com/Quantinuum/`.

| Package | Status | Install | Converters / key classes |
|---|---|---|---|
| `pytket-qiskit` 0.78.0 | live | `pip install "pytket-qiskit[aer]"` | `qiskit_to_tk(qcirc, preserve_param_uuid=False)`, `tk_to_qiskit(tkcirc, replace_implicit_swaps=False, perm_warning=True)`; top level also exports `AerBackend`, `AerStateBackend`, `AerUnitaryBackend`, `AerDensityMatrixBackend`, `IBMQBackend`, `IBMQEmulatorBackend`, `set_ibmq_config`. The Qiskit-side wrappers are **submodule only**: `tket_backend.TketBackend`, `tket_pass.TketPass` / `TketAutoPass`, `tket_job.TketJob` |
| `pytket-quantinuum` 0.59.3 | live | `pip install pytket-quantinuum` (`[pecos]` for H2-1LE) | no circuit converter; `QuantinuumBackend(device_name=...)`, `QuantinuumBackendCompilationConfig`, `Language` (QASM/QIR/PQIR, default QIR); hardware submission via `qnexus` since 0.56.0 |
| `pytket-braket` 0.48.0 | live | `pip install pytket-braket` | `tk_to_braket`, `braket_to_tk`; one class `BraketBackend(local=False, ...)` |
| `pytket-iqm` | live | `pip install pytket-iqm` | `IQMBackend` (converter names unverified) |
| `pytket-qir` | live | `pip install pytket-qir` | **export only**: `pytket_to_qir`, `check_circuit`, `QIRFormat`, `QIRProfile`; module is `pytket.qir`; no `qir_to_tk` |
| `pytket-qujax` 0.22.0 | live | `pip install pytket-qujax` | `tk_to_qujax`, `tk_to_qujax_args`, `tk_to_param`; reverse is **`qujax_args_to_tk`** (NOT `qujax_to_tk`); measurements raise `TypeError` |
| `pytket-qulacs` 0.42.0 | live | `pip install pytket-qulacs` | **export only**: `tk_to_qulacs`; `QulacsBackend(result_type="density_matrix")`; no `qulacs_to_tk` |
| `pytket-cutensornet` | live | `pip install pytket-cutensornet` (Linux, CUDA, CC>=7.0) | no converter; `GeneralState`, `GeneralBraOpKet`, `simulate`, `CuTensorNetStateBackend`, `CuTensorNetShotsBackend` |
| `pytket-cirq` | archived-unmaintained | `pip install pytket-cirq` | `cirq_to_tk`, `tk_to_cirq`; `CirqStateSimBackend` etc. |
| `pytket-pyzx` | archived-unmaintained | `pip install pytket-pyzx` | `tk_to_pyzx`, **`pyzx_to_tk`** (NOT `zx_to_tk` — that prefix is core `pytket.zx`) + `_arc`/`_placed_circ` variants |
| `pytket-pennylane` | archived-unmaintained | `pip install pytket-pennylane` | `pennylane_to_tk` only; reverse path is the `PytketDevice` plugin; no `tk_to_pennylane` |
| `pytket-pyquil` 0.40.0 | archived-unmaintained | `pip install pytket-pyquil` | `ForestBackend`, `ForestStateBackend`; needs external `quilc`/`qvm` servers |
| `pytket-stim`, `pytket-quest`, `pytket-pysimplex` | archived-unmaintained | — | converter names unverified |
| `pytket-qsharp` 0.40.0 | stale-pinned | — | pins `pytket ~=1.26`; **uninstallable with pytket 2.x**; `tk_to_qsharp` export-only |
| `pytket-projectq` 0.39.0 | orphaned (absent from official index) | `pip install pytket-projectq` | `tk_to_projectq` export-only, `ProjectQBackend`; do not recommend |
| `pytket-forest`, `pytket-umalqura` | **do not exist** | — | PyPI 404; the Rigetti extension is `pytket-pyquil` |

## Cross-SDK gotchas

These fail **silently** — wrong numbers, not exceptions.

### 1. Angles are half-turns, not radians

pytket parametrised gates take **multiples of π** (`pytket/docs/optype.md:6`: "expect parameters
in multiples of pi (half-turns)"). Qiskit/Cirq/QASM use radians:

```python
import math
theta_halfturns = theta_radians / math.pi
theta_radians   = theta_halfturns * math.pi
```

`c.Rx(0.5, q)` in pytket == `qc.rx(pi/2, q)` in Qiskit. Verified: `Circuit(1).Rx(0.5, 0)` stores
`params == [0.5]` — no error, no warning, just a physically different circuit. Parameters are
also canonicalised into `[0, r)` (e.g. `PhasedX(-0.1, 0.5, 0)` reads back as `[3.9, 0.5]`).
The QASM and Qiskit converters handle the factor of π for you; hand-copied numeric parameters do not.

### 2. Endianness

pytket is **ILO-BE**: `Qubit(0)` is the most significant bit in statevectors, unitaries, and
counts keys. Qiskit is little-endian everywhere. **But gate argument indices are preserved by the
converters** — verified: pytket `CX q[0], q[1]` becomes Qiskit `cx` on `(q[0], q[1])` with the
same control/target. Reversal happens only on *amplitudes, counts/bitstrings, and
`condition_value`*, and the converters do it internally.

| Situation | Symptom / fix |
|---|---|
| Reading pytket counts keys as Qiskit bitstrings | Bit-reversed; pytket key `(1,0,0)` = q0 set |
| Comparing `get_unitary()` across SDKs | Rows/cols opposite order — `pytket.utils.permute_rows_cols_in_unitary(matrix, permutation)` |
| Circuit has an implicit permutation | `tk_to_qiskit(..., replace_implicit_swaps=True)` materialises it (default `False` only warns via `perm_warning=True`); QASM export drops it silently — use `passes.RemoveImplicitQubitPermutation()` first |
| Circuit drawing | Qiskit draws qubit 0 at the bottom; pytket at top — same circuit, different picture |

Rule: never hand-carry a raw integer index or bitstring across an SDK boundary.

### 3. Symbolic circuits

`pytket-qiskit` **removed symbolic conversion in 0.73.0**. Every backend requires
`NoSymbolsPredicate` — bind before submitting:

```python
from pytket.predicates import NoSymbolsPredicate
if not NoSymbolsPredicate().verify(circ):
    circ.symbol_substitution({s: 0.25 for s in circ.free_symbols()})
```

QASM 2 keeps sympy symbols both directions; qujax needs an explicit `symbol_map`; QIR/Qulacs/Q#
are numeric export-only.

### 4. Boxes and rebases in converters

- QASM export auto-decomposes boxes. **Qiskit conversion does not**: unsupported high-level
  Qiskit instructions raise `NotImplementedError` telling you to call
  `QuantumCircuit.decompose()` first.
- `tk_to_qiskit` runs a rebase pass first, so `TK1`, `ZZMax`, `V`, `Vdg` etc. are silently
  re-expressed into Qiskit gates — and some only up to global phase (`V` → `SX` + phase). The
  result is unitarily equivalent, not structurally identical.
- Unitary boxes cap at **3 qubits** (`Unitary1qBox`/`2qBox`/`3qBox` only; synthesis beyond that
  raises `NotImplementedError`).

### 5. Classical logic and WASM are not portable

Complex classical ops need `header="hqslib1"` in QASM and generally do not survive other SDK
boundaries; `condition_value` bit order is little-endian (QASM convention). WASM works only
through the three dedicated `*_wasm*` importers plus `pytket.wasm` handlers; no other SDK reads
it, and `pytket-quantinuum` raises `WasmUnsupported` in some configurations.

## Round-trip verification recipe

```python
import numpy as np
from pytket.circuit import Circuit
from pytket.qasm import circuit_to_qasm_str, circuit_from_qasm_str
from pytket.utils import compare_unitaries

circ = Circuit(2).H(0).CX(0, 1).Rz(0.25, 1).Rx(0.5, 0)
back = circuit_from_qasm_str(circuit_to_qasm_str(circ))

assert compare_unitaries(circ.get_unitary(), back.get_unitary())   # ignores global phase
```

- `compare_unitaries(first, second) -> bool` compares **up to global phase** (verified:
  `np.allclose(a @ b.conj().T, I * (a @ b.conj().T)[0, 0])`); companion
  `compare_statevectors(a, b) = np.isclose(np.abs(np.vdot(a, b)), 1)`.
- `Circuit.get_unitary()` requires no measurements and no classical bits; both circuits need the
  same qubit count and ILO-BE order.
- Stricter, structural form (what pytket's own QASM tests use): `assert c1 == c2`. This fails on
  any re-synthesised gate definition — pick the check that matches the claim.
- If the circuit has an implicit permutation, apply `RemoveImplicitQubitPermutation()` before
  exporting, or the comparison fails for reasons unrelated to QASM.
- For cross-SDK checks, compare `pytket` unitaries only after
  `permute_rows_cols_in_unitary` — never against a raw Qiskit `Operator`.

## Sources

- <https://docs.quantinuum.com/tket/api-docs/qasm.html>,
  <https://docs.quantinuum.com/tket/api-docs/quipper.html>,
  <https://docs.quantinuum.com/tket/api-docs/extensions.html>,
  <https://docs.quantinuum.com/tket/api-docs/faqs.html>
- <https://docs.quantinuum.com/tket/extensions/pytket-qiskit/index.html>,
  <https://docs.quantinuum.com/tket/extensions/pytket-qiskit/api.html>,
  <https://docs.quantinuum.com/tket/extensions/pytket-qiskit/_modules/pytket/extensions/qiskit/qiskit_convert.html>
- <https://github.com/Quantinuum/tket> @ `d2bb207981244205cbf9ddc9ef0257112c366558` —
  repo-relative: `pytket/pytket/qasm/qasm.py` (all nine signatures, header maps, error strings),
  `pytket/pytket/qasm/__init__.py`, `pytket/pytket/quipper/quipper.py`,
  `pytket/pytket/utils/results.py` (`compare_unitaries`, `permute_rows_cols_in_unitary`),
  `pytket/tests/qasm_test.py`, `pytket/docs/optype.md`, `pytket/docs/qasm.md`,
  `pytket/docs/quipper.md`, `pytket/docs/faqs.md`, `pytket/docs/extensions.md`
- Extension repos: `github.com/Quantinuum/pytket-{qiskit,quantinuum,braket,iqm,qir,qujax,qulacs,cutensornet,cirq,pyzx,pennylane,pyquil,qsharp,projectq}`
  (README/docs/changelog on `main`); PyPI JSON for versions; `pytket-forest` and
  `pytket-umalqura` confirmed 404 on PyPI
