# Upstream Sources and Version Provenance

## Verification Snapshot

Research completed **2026-09-30** against the `Quantinuum/tket` repository (main branch at commit
`d2bb207981244205cbf9ddc9ef0257112c366558`), the published user guide and API docs, PyPI JSON
metadata, and a real install that was executed end to end.

Method — three layers, in this order:

1. **Name existence.** Every API name in this skill was checked against the authoritative `.pyi`
   stubs and the pybind11 binders in the repository clone
   (`pytket/pytket/_tket/*.pyi`, `pytket/binders/*.cpp`), not against prose documentation.
2. **Signature accuracy.** Signatures were copied from the stubs; doc-page signatures were
   cross-checked, and two documented contradictions were found and recorded (see
   [Known documentation defects](#known-documentation-defects)).
3. **Behaviour.** Three probe scripts were run against the installed release, importing ~140
   documented names and executing the behaviours quoted in this skill (counts, statevectors,
   parameter round-trips, expectation values, compilation maps, error types). Numbers in these
   files are executed output, not paraphrase.

PyPI versions observed:

| Distribution | Version | PyPI | Status |
|---|---:|---|---|
| `pytket` | 2.18.4 | [pytket](https://pypi.org/project/pytket/) | core, maintained |
| `pytket-qiskit` | 0.78.0 | [pytket-qiskit](https://pypi.org/project/pytket-qiskit/) | maintained — supplies all Aer and IBM backends |
| `pytket-quantinuum` | 0.59.3 | [pytket-quantinuum](https://pypi.org/project/pytket-quantinuum/) | maintained as a **compile target only** since 0.56.0 |
| `pytket-braket` | — | [pytket-braket](https://pypi.org/project/pytket-braket/) | maintained |
| `pytket-iqm` | — | [pytket-iqm](https://pypi.org/project/pytket-iqm/) | maintained |
| `pytket-qir` | — | [pytket-qir](https://pypi.org/project/pytket-qir/) | maintained |
| `pytket-cutensornet` | — | [pytket-cutensornet](https://pypi.org/project/pytket-cutensornet/) | maintained |
| `pytket-qulacs` | — | [pytket-qulacs](https://pypi.org/project/pytket-qulacs/) | maintained |
| `pytket-qujax` | — | [pytket-qujax](https://pypi.org/project/pytket-qujax/) | maintained |
| `qermit` | 0.9.3 | [qermit](https://pypi.org/project/qermit/) | maintained — ZNE / CDR / PEC live here, **not** in pytket |
| `qnexus` | — | [qnexus](https://pypi.org/project/qnexus/) | maintained — the supported route to Quantinuum hardware |

Transitive versions resolved alongside the pins above: `qiskit` 2.5.2, `qiskit-aer` 0.17.2,
`qiskit-ibm-runtime` 0.50.0, `numpy` 2.5.3, `scipy` 1.18.1, `sympy` 1.14.0.
Core `pytket` floors: `sympy>=1.12.1`, `numpy>=1.26.4`, `lark>=1.1.9`, `scipy>=1.13.1`,
`networkx>=2.8.8`, `graphviz>=0.20.3`, `jinja2>=3.1.4`, `typing-extensions>=4.12.2`,
`qwasm>=1.0.1`; `zx` extra: `numba>=0.62.1`, `quimb>=1.8.2`, `autoray>=0.6.12`.

**`pytket-aer` does not exist on PyPI.** The Aer backends ship inside `pytket-qiskit` behind the
`[aer]` extra — see [setup.md](setup.md).

## Canonical TKET Sources

- [Quantinuum/tket GitHub repository](https://github.com/Quantinuum/tket) — C++ `tket` core and the
  `pytket` Python interface
- [TKET documentation home](https://docs.quantinuum.com/tket/)
- [pytket API docs](https://docs.quantinuum.com/tket/api-docs/)
- [TKET user guide](https://docs.quantinuum.com/tket/user-guide/)
- [pytket changelog](https://docs.quantinuum.com/tket/api-docs/changelog.html) — local mirror
  `pytket/docs/changelog.md`
- [Installation and troubleshooting](https://docs.quantinuum.com/tket/api-docs/install.html)
- [Extensions index](https://docs.quantinuum.com/tket/api-docs/extensions.html)
- [Quantinuum Nexus documentation](https://docs.quantinuum.com/nexus/)

### Authoritative local mirrors (best for exact signatures)

The docs site renders Sphinx output; the repository carries the same content as plain Markdown plus
typed stubs, which are faster and more reliable to grep:

- `pytket/docs/*.md` — the api-docs sources: `architecture`, `backends`, `changelog`, `circuit`,
  `circuit_class`, `circuit_library`, `classical`, `config`, `display`, `extensions`, `faqs`,
  `getting_started`, `install`, `logging`, `mapping`, `optype`, `partition`, `passes`, `pauli`,
  `placement`, `predicates`, `qasm`, `quipper`, `tableau`, `tailoring`, `transform`, `unit_id`,
  `utils`, `wasm`, `zx`
- `pytket/pytket/_tket/*.pyi` — **the authoritative signatures**; prefer these over any prose
- `pytket/binders/*.cpp` — the pybind11 layer, useful when a stub is ambiguous
- `pytket/tests/` — real usage of every subsystem, including
  `pytket/tests/simulator/tket_sim_backend.py` (a complete minimal `Backend` implementation)

When fetching long user-guide pages, the rendered `.html` can truncate. The verbatim sources are
mirrored under `_sources/` with `.md.txt` / `.ipynb.txt` suffixes, e.g.
`https://docs.quantinuum.com/tket/user-guide/_sources/manual/manual_compiler.md.txt`.

## User Guide Sections

| Page | Covers |
|---|---|
| [manual_intro](https://docs.quantinuum.com/tket/user-guide/manual/manual_intro.html) | NISQ considerations, compilation, platform-agnosticism, installation, citation, support |
| [manual_circuit](https://docs.quantinuum.com/tket/user-guide/manual/manual_circuit.html) | gates, measurements, barriers, registers, composition, statevectors, boxes, import/export, symbolic circuits |
| [manual_backend](https://docs.quantinuum.com/tket/user-guide/manual/manual_backend.html) | backend requirements, shots, simulation, results, expectation values, batch submission, Qiskit embedding |
| [manual_compiler](https://docs.quantinuum.com/tket/user-guide/manual/manual_compiler.html) | predicates, rebases, placement, mapping, decompositions, optimisations, combinators, pass ordering, initial/final maps |
| [manual_noise](https://docs.quantinuum.com/tket/user-guide/manual/manual_noise.html) | noise-aware mapping, noise tailoring, SPAM mitigation |
| [manual_assertion](https://docs.quantinuum.com/tket/user-guide/manual/manual_assertion.html) | projector-based and stabiliser-based assertions |
| [manual_zx](https://docs.quantinuum.com/tket/user-guide/manual/manual_zx.html) | ZX generators, diagrams, tensor evaluation, rewrites, MBQC flow, extraction, compiler passes |

## Worked Examples (notebooks)

- Circuit construction:
  [circuit_analysis](https://docs.quantinuum.com/tket/user-guide/examples/circuit_construction/circuit_analysis_example.html),
  [circuit_generation](https://docs.quantinuum.com/tket/user-guide/examples/circuit_construction/circuit_generation_example.html),
  [conditional_gate](https://docs.quantinuum.com/tket/user-guide/examples/circuit_construction/conditional_gate_example.html)
- Backends:
  [backends](https://docs.quantinuum.com/tket/user-guide/examples/backends/backends_example.html),
  [comparing_simulators](https://docs.quantinuum.com/tket/user-guide/examples/backends/comparing_simulators.html),
  [creating_backends](https://docs.quantinuum.com/tket/user-guide/examples/backends/creating_backends.html),
  [qiskit_integration](https://docs.quantinuum.com/tket/user-guide/examples/backends/qiskit_integration.html)
- Compilation:
  [compilation](https://docs.quantinuum.com/tket/user-guide/examples/circuit_compilation/compilation_example.html),
  [contextual_optimisation](https://docs.quantinuum.com/tket/user-guide/examples/circuit_compilation/contextual_optimisation.html),
  [mapping](https://docs.quantinuum.com/tket/user-guide/examples/circuit_compilation/mapping_example.html),
  [symbolics](https://docs.quantinuum.com/tket/user-guide/examples/circuit_compilation/symbolics_example.html)
- Algorithms and protocols:
  [expectation_value](https://docs.quantinuum.com/tket/user-guide/examples/algorithms_and_protocols/expectation_value_example.html),
  [measurement_reduction](https://docs.quantinuum.com/tket/user-guide/examples/algorithms_and_protocols/measurement_reduction_example.html),
  [phase_estimation](https://docs.quantinuum.com/tket/user-guide/examples/algorithms_and_protocols/phase_estimation.html),
  [ucc_vqe](https://docs.quantinuum.com/tket/user-guide/examples/algorithms_and_protocols/ucc_vqe.html),
  [ansatz_sequence](https://docs.quantinuum.com/tket/user-guide/examples/algorithms_and_protocols/ansatz_sequence_example.html),
  [entanglement_swapping](https://docs.quantinuum.com/tket/user-guide/examples/algorithms_and_protocols/entanglement_swapping.html),
  [qujax classification](https://docs.quantinuum.com/tket/user-guide/examples/algorithms_and_protocols/pytket-qujax-classification.html),
  [qujax Heisenberg VQE](https://docs.quantinuum.com/tket/user-guide/examples/algorithms_and_protocols/pytket-qujax_heisenberg_vqe.html),
  [qujax QAOA](https://docs.quantinuum.com/tket/user-guide/examples/algorithms_and_protocols/pytket-qujax_qaoa.html)

## Extension Documentation

| Extension | Docs | Notes |
|---|---|---|
| `pytket-qiskit` | [index](https://docs.quantinuum.com/tket/extensions/pytket-qiskit/index.html) | `tk_to_qiskit`/`qiskit_to_tk`, `AerBackend`, `AerStateBackend`, `AerUnitaryBackend`, `IBMQBackend`, `IBMQEmulatorBackend`, noise models |
| `pytket-quantinuum` | [index](https://docs.quantinuum.com/tket/extensions/pytket-quantinuum/index.html) | compile target + `H2-1LE` local emulation; **no hardware submission since 0.56.0** |
| `pytket-braket` | [index](https://docs.quantinuum.com/tket/extensions/pytket-braket/index.html) | AWS Braket devices and simulators |
| `pytket-iqm` | [index](https://docs.quantinuum.com/tket/extensions/pytket-iqm/index.html) | IQM Resonance |
| `pytket-qir` | [index](https://docs.quantinuum.com/tket/extensions/pytket-qir/index.html) | QIR export |
| `pytket-cutensornet` | [index](https://docs.quantinuum.com/tket/extensions/pytket-cutensornet/index.html) | `GeneralState`, tensor-network state backends |
| `pytket-qulacs` | [index](https://docs.quantinuum.com/tket/extensions/pytket-qulacs/index.html) | Qulacs simulator |
| `pytket-qujax` | [index](https://docs.quantinuum.com/tket/extensions/pytket-qujax/index.html) | JAX-differentiable circuits |
| `qermit` | [index](https://docs.quantinuum.com/qermit/) | ZNE, CDR, learning-based PEC, frame randomisation |
| `qnexus` | [index](https://docs.quantinuum.com/nexus/) | supported submission path for Quantinuum hardware |

**Archived / unmaintained** (still importable in old environments, do not build new work on them):
`pytket-cirq`, `pytket-pennylane`, `pytket-pyquil`, `pytket-pysimplex`, `pytket-pyzx`,
`pytket-stim`, `pytket-quest`. `pytket-projectq` still publishes 0.39.0 but is absent from the
official extension index. `pytket-qsharp` pins `pytket ~=1.26` and cannot be installed beside
pytket 2.x. `pytket-forest` and `pytket-umalqura` never existed on PyPI.

Because several extensions are unmaintained, the maintained cross-SDK path today is
**pytket ⇄ Qiskit** (`pytket-qiskit`); reach other frameworks through OpenQASM 2 where possible.

## Known Documentation Defects

Recorded because they will cost debugging time if trusted blindly:

1. `manual_noise.html` calls `NoiseAwarePlacement(arc, averaged_readout_errors,
   averaged_node_gate_errors, averaged_edge_gate_errors)` positionally. The real signature is
   `NoiseAwarePlacement(arc, node_errors={}, link_errors={}, readout_errors={}, ...)` — the
   positional order in the guide does not match the stub. **Always pass these by keyword.**
2. `comparing_simulators.html` still documents Forest, ProjectQ and QulacsGPU backends. Those
   extensions are unmaintained or absent; ignore that comparison table.
3. The user-guide `Placement.modify_config` example uses an API removed in pytket 2.0.
4. `pytket/docs/getting_started.md` and several notebooks show `AerBackend` results with
   `(1,1,1)`-style keys but do not emphasise the ordering; pytket is **ILO-BE** and Qiskit is
   OLE-LE, so counts keys are reversed between the two SDKs.

When a doc page and a `.pyi` stub disagree, the stub wins.

## Citation

Default citation for TKET (from the repository and PyPI description):

> S. Khan, A. Maslov, et al., *"TKET: a retargetable compiler for NISQ devices"*,
> [arXiv:2003.10611](https://arxiv.org/abs/2003.10611).

Topic-specific papers to cite instead when that subsystem carries the result:

- Qubit routing and placement — [arXiv:1902.08091](https://arxiv.org/abs/1902.08091)
- Phase-gadget synthesis for shallow circuits — [arXiv:1906.01734](https://arxiv.org/abs/1906.01734)
- UCC compilation strategy — [arXiv:2007.10515](https://arxiv.org/abs/2007.10515)

The repository also ships a machine-readable `CITATION.cff`.

## Support Channels

- `tket-support@quantinuum.com`
- The `tketusers` Slack workspace (invite via the Quantinuum docs site)
- [Quantum Computing Stack Exchange](https://quantumcomputing.stackexchange.com/questions/tagged/pytket), tag `pytket`
- GitHub issues: <https://github.com/Quantinuum/tket/issues>

## How to Refresh This Skill

1. Query PyPI JSON metadata for `pytket` and every extension you depend on
   (`https://pypi.org/pypi/<dist>/json`) and record the versions.
2. Clone `Quantinuum/tket` at the release tag matching that version and note the commit hash.
3. Re-read `pytket/docs/changelog.md` for removals and renames since the last snapshot — pytket
   2.0 removed a large set of names this skill deliberately refuses to use.
4. Re-grep `pytket/pytket/_tket/*.pyi` for every API name mentioned in this skill; drop or flag
   anything that no longer resolves.
5. Check the extension index and each extension's changelog for archival or pin changes, and
   re-check whether `pytket-quantinuum` still refuses hardware submission.
6. Build a fresh environment with all pins resolved in one install command, then run
   `scripts/check_environment.py --strict`.
7. Execute every snippet in `SKILL.md` and `references/`; confirm the quoted numbers
   (counts, statevector magnitudes, gate counts, expectation values, compilation maps).
8. Re-run the three behaviours most likely to regress silently: the half-turn angle convention,
   ILO-BE result ordering, and `Backend.get_operator_expectation_value` taking no `n_shots`.
9. Update the verification date, the version tables, and the documentation-defect list.
10. Increment `metadata.version` in `SKILL.md` and re-run `skills-ref validate skills/tket`.
