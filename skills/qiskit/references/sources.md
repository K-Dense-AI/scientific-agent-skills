# Upstream Sources and Version Provenance

## Verification Snapshot

Research completed **2026-07-23** using official IBM Quantum documentation, Qiskit repositories and releases, PyPI metadata, Context7's Qiskit indexes, and Parallel web search/extraction.

PyPI versions observed:

| Distribution | Version | PyPI |
|---|---:|---|
| Qiskit SDK | 2.5.0 | [qiskit](https://pypi.org/project/qiskit/) |
| Qiskit IBM Runtime | 0.48.0 | [qiskit-ibm-runtime](https://pypi.org/project/qiskit-ibm-runtime/) |
| Qiskit Aer | 0.17.2 | [qiskit-aer](https://pypi.org/project/qiskit-aer/) |
| Qiskit Algorithms | 0.4.0 | [qiskit-algorithms](https://pypi.org/project/qiskit-algorithms/) |
| Qiskit Nature | 0.8.0 | [qiskit-nature](https://pypi.org/project/qiskit-nature/) |
| Qiskit Nature PySCF | 0.4.0 | [qiskit-nature-pyscf](https://pypi.org/project/qiskit-nature-pyscf/) |
| Qiskit Machine Learning | 0.9.0 | [qiskit-machine-learning](https://pypi.org/project/qiskit-machine-learning/) |
| Qiskit Optimization | 0.7.0 | [qiskit-optimization](https://pypi.org/project/qiskit-optimization/) |

The Qiskit GitHub repository published [2.5.1](https://github.com/Qiskit/qiskit/releases/tag/2.5.1) on 2026-07-23, shortly before this update. At verification time, PyPI metadata still reported 2.5.0, so executable examples use the available `qiskit==2.5.0` pin. Recheck both sources before updating.

## Canonical Qiskit SDK Sources

- [IBM Quantum documentation](https://quantum.cloud.ibm.com/docs/)
- [Qiskit quickstart](https://quantum.cloud.ibm.com/docs/guides/quick-start)
- [Install Qiskit](https://quantum.cloud.ibm.com/docs/guides/install-qiskit)
- [Qiskit SDK API reference](https://quantum.cloud.ibm.com/docs/api/qiskit)
- [Qiskit SDK release notes](https://quantum.cloud.ibm.com/docs/api/qiskit/release-notes)
- [Qiskit 2.5 release notes](https://quantum.cloud.ibm.com/docs/api/qiskit/release-notes/2.5)
- [Qiskit GitHub repository](https://github.com/Qiskit/qiskit)
- [Qiskit GitHub releases](https://github.com/Qiskit/qiskit/releases)

Use `quantum.cloud.ibm.com/docs` for current guides. Old `qiskit.org/learn`, `qiskit.org/ecosystem/...`, and legacy documentation URLs can be stale or redirect.

## Core User Guides

### Circuits and quantum information

- [Construct circuits](https://quantum.cloud.ibm.com/docs/guides/construct-circuits)
- [Circuit library API](https://quantum.cloud.ibm.com/docs/api/qiskit/circuit_library)
- [Quantum information API](https://quantum.cloud.ibm.com/docs/api/qiskit/quantum_info)
- [QPY serialization API](https://quantum.cloud.ibm.com/docs/api/qiskit/qpy)
- [OpenQASM 2 API](https://quantum.cloud.ibm.com/docs/api/qiskit/qasm2)
- [OpenQASM 3 API](https://quantum.cloud.ibm.com/docs/api/qiskit/qasm3)

### Primitives

- [Introduction to primitives](https://quantum.cloud.ibm.com/docs/guides/primitives)
- [Primitive input and output](https://quantum.cloud.ibm.com/docs/guides/primitive-input-output)
- [Exact simulation with SDK primitives](https://quantum.cloud.ibm.com/docs/guides/simulate-with-qiskit-sdk-primitives)
- [Primitives API](https://quantum.cloud.ibm.com/docs/api/qiskit/primitives)

### Transpilation

- [Introduction to transpilation](https://quantum.cloud.ibm.com/docs/guides/transpile)
- [Compare transpiler settings](https://quantum.cloud.ibm.com/docs/guides/circuit-transpilation-settings)
- [Transpiler API](https://quantum.cloud.ibm.com/docs/api/qiskit/transpiler)
- [Preset pass managers API](https://quantum.cloud.ibm.com/docs/api/qiskit/transpiler_preset)

### Visualization

- [Visualization API](https://quantum.cloud.ibm.com/docs/api/qiskit/visualization)

## Migration Sources

- [Qiskit 2.0 migration guide](https://quantum.cloud.ibm.com/docs/migration-guides/qiskit-2.0)
- [Qiskit 1.0 feature changes](https://quantum.cloud.ibm.com/docs/guides/qiskit-1.0-features)
- [Qiskit package-structure migration](https://quantum.cloud.ibm.com/docs/guides/metapackage-migration)
- [Migrate BackendV1 to BackendV2](https://quantum.cloud.ibm.com/docs/guides/qiskit-backendv1-to-v2)
- [Migrate to V2 Runtime primitives](https://quantum.cloud.ibm.com/docs/guides/v2-primitives)
- [Migrate Qiskit Pulse to fractional gates](https://quantum.cloud.ibm.com/docs/guides/pulse-migration)
- [Migrate from IBM Quantum Platform Classic](https://quantum.cloud.ibm.com/docs/migration-guides/classic-iqp-to-cloud-iqp)

Qiskit 2.0 removed `qiskit.pulse`, legacy instruction conditions, V1 reference primitive implementations, and several BackendV1-era interfaces. Runtime V1 primitive support was removed earlier. Read both SDK and Runtime migration guides because they version independently.

## IBM Quantum Runtime Sources

- [Qiskit IBM Runtime repository](https://github.com/Qiskit/qiskit-ibm-runtime)
- [Runtime client release notes](https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/release-notes)
- [QiskitRuntimeService API](https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/qiskit-runtime-service)
- [Runtime SamplerV2 API](https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/sampler-v2)
- [Runtime EstimatorV2 API](https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/estimator-v2)
- [Set up IBM Quantum Platform](https://quantum.cloud.ibm.com/docs/guides/cloud-setup)
- [Runtime execution modes](https://quantum.cloud.ibm.com/docs/guides/execution-modes)
- [Run jobs in a batch](https://quantum.cloud.ibm.com/docs/guides/run-jobs-batch)
- [Run jobs in a session](https://quantum.cloud.ibm.com/docs/guides/run-jobs-session)
- [Runtime local testing mode](https://quantum.cloud.ibm.com/docs/guides/local-testing-mode)
- [Sampler options](https://quantum.cloud.ibm.com/docs/guides/sampler-options)
- [Estimator options](https://quantum.cloud.ibm.com/docs/guides/estimator-options)
- [Error mitigation and suppression](https://quantum.cloud.ibm.com/docs/guides/error-mitigation-and-suppression-techniques)

Runtime 0.48 uses `ibm_quantum_platform`, V2 primitives, `mode=...`, implementation-specific options, and explicit ISA circuits.

## Simulation

- [Qiskit Aer documentation](https://qiskit.github.io/qiskit-aer/)
- [Aer simulator API](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html)
- [Aer primitives API](https://qiskit.github.io/qiskit-aer/apidocs/aer_primitives.html)

The Aer documentation landing page can lag the newest patch label. Use PyPI and GitHub releases for the install pin, then use versioned API behavior from the installed package.

## Application-Package Documentation

- [Qiskit Algorithms 0.4](https://qiskit-community.github.io/qiskit-algorithms/)
- [Qiskit Nature 0.8](https://qiskit-community.github.io/qiskit-nature/)
- [Qiskit Nature getting started](https://qiskit-community.github.io/qiskit-nature/getting_started.html)
- [Qiskit Machine Learning 0.9](https://qiskit-community.github.io/qiskit-machine-learning/)
- [Qiskit Machine Learning migration guide](https://qiskit-community.github.io/qiskit-machine-learning/migration/index.html)
- [Qiskit Optimization 0.7](https://qiskit-community.github.io/qiskit-optimization/)
- [Qiskit Optimization migration guides](https://qiskit-community.github.io/qiskit-optimization/migration/index.html)

Application packages release independently. Check their requirements before changing the core Qiskit pin.

## Addon Documentation

- [Qiskit addon: circuit cutting](https://qiskit.github.io/qiskit-addon-cutting/)
- [Qiskit addon: sample-based quantum diagonalization](https://qiskit.github.io/qiskit-addon-sqd/)
- [Qiskit addon: operator backpropagation](https://qiskit.github.io/qiskit-addon-obp/)
- [Qiskit addon: multi-product formulas](https://qiskit.github.io/qiskit-addon-mpf/)
- [Qiskit addon: AQC-Tensor](https://qiskit.github.io/qiskit-addon-aqc-tensor/)
- [IBM guide to Qiskit addons](https://quantum.cloud.ibm.com/docs/guides/addons)

Addon versions observed on PyPI:

| Distribution | Version |
|---|---:|
| `qiskit-addon-cutting` | 0.10.0 |
| `qiskit-addon-sqd` | 0.12.1 |
| `qiskit-addon-obp` | 0.3.0 |
| `qiskit-addon-mpf` | 0.3.0 |
| `qiskit-addon-aqc-tensor` | 0.3.1 |

## Research Queries Used

The refresh used focused Parallel searches for:

- current Qiskit, Runtime, Aer, and application-package versions,
- Qiskit 2.x removals, deprecations, and migration guides,
- current Runtime authentication, execution modes, and option models,
- current circuit, primitive, transpilation, simulation, and serialization guides,
- current ecosystem and addon package APIs.

Canonical pages were then extracted directly. Specific API patterns were cross-checked with Context7 and executed in isolated `uv` environments pinned to the versions above.

## How to Refresh This Skill

1. Query PyPI JSON metadata for every pinned distribution.
2. Compare PyPI with GitHub releases and official release notes.
3. Read Qiskit major/minor migration and deprecation sections.
4. Read Runtime release notes independently.
5. Recheck valid channel names, account setup, plan restrictions, and option compatibility.
6. Run all bundled scripts in an isolated environment.
7. Execute the core, Algorithms, Optimization, Machine Learning, and visualization snippets.
8. Update the verification date and version tables.
9. Increment `metadata.version` in `SKILL.md`.
10. Run `uv run skills-ref validate skills/qiskit` and the local security scan.
