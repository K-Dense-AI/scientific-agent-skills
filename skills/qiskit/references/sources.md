# Upstream Sources and Version Provenance

## Verification Snapshot

Reviewed **2026-10-01** using current official IBM Quantum documentation, tagged Qiskit source, released installed packages, and PyPI metadata. All skill and supporting files were reviewed. Hardware, account setup, and optional application workflows remain illustrative where stated.

PyPI versions observed:

| Distribution | Version | PyPI |
|---|---:|---|
| Qiskit SDK | 2.5.2 | [qiskit](https://pypi.org/project/qiskit/) |
| Qiskit IBM Runtime | 0.50.0 | [qiskit-ibm-runtime](https://pypi.org/project/qiskit-ibm-runtime/) |
| Qiskit Aer | 0.17.2 | [qiskit-aer](https://pypi.org/project/qiskit-aer/) |
| Qiskit Algorithms | 0.4.0 | [qiskit-algorithms](https://pypi.org/project/qiskit-algorithms/) |
| Qiskit Nature | 0.8.0 | [qiskit-nature](https://pypi.org/project/qiskit-nature/) |
| Qiskit Nature PySCF | 0.4.0 | [qiskit-nature-pyscf](https://pypi.org/project/qiskit-nature-pyscf/) |
| Qiskit Machine Learning | 0.9.1 | [qiskit-machine-learning](https://pypi.org/project/qiskit-machine-learning/) |
| Qiskit Optimization | 0.7.0 | [qiskit-optimization](https://pypi.org/project/qiskit-optimization/) |

The executable core baseline is Qiskit 2.5.2, Runtime 0.50.0, Aer 0.17.2, and Algorithms 0.4.0 on Python 3.13. The table also lists documentation-reviewed optional packages; it does not claim they were all installed together.

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
- [Client-side Sampler API](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/executor-sampler-sampler)
- [Client-side Estimator API](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/executor-estimator-estimator)
- [Client-side option models](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/options-models)
- [Set up IBM Quantum Platform](https://quantum.cloud.ibm.com/docs/guides/cloud-setup)
- [Runtime execution modes](https://quantum.cloud.ibm.com/docs/guides/execution-modes)
- [Run jobs in a batch](https://quantum.cloud.ibm.com/docs/guides/run-jobs-batch)
- [Run jobs in a session](https://quantum.cloud.ibm.com/docs/guides/run-jobs-session)
- [Runtime local testing mode](https://quantum.cloud.ibm.com/docs/guides/local-testing-mode)
- [Sampler options](https://quantum.cloud.ibm.com/docs/guides/sampler-options)
- [Estimator options](https://quantum.cloud.ibm.com/docs/guides/estimator-options)
- [Error mitigation and suppression](https://quantum.cloud.ibm.com/docs/guides/error-mitigation-and-suppression-techniques)

Runtime 0.50 deprecates top-level `SamplerV2`/`EstimatorV2` in favor of the client-side modules above. V2 PUBs, `mode=...`, and explicit target compilation remain relevant. Options moved to Pydantic `options_models` in 0.49; use `model_dump()`.

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
| `qiskit-addon-sqd` | 0.13.1 |
| `qiskit-addon-obp` | 0.3.0 |
| `qiskit-addon-mpf` | 0.3.0 |
| `qiskit-addon-aqc-tensor` | 0.3.1 |

## Executed coverage and discrepancies

The repository suite executes the three script CLIs, package inspection, analytic two-qubit sampling/expectations, fake Manila inspection, multi-register correlations and order, parameter broadcasting, measurement permutations, forced nontrivial observable layout, QPY round trips, and positive-precision synthetic noise. It also executes the Runtime 0.50 client-side Sampler/Estimator on Aer, a deterministic readout-noise model, option finalization, rejected unequal shots/input boxes, tiny VQE against dense diagonalization, and text/Matplotlib/Bloch/histogram exports. A separate isolated Optimization 0.7.0 smoke run executed the corrected two-variable QAOA example and returned `[0, 1]`, objective `1`, SUCCESS.

- [SamplerPubResult source, 2.5.2](https://github.com/Qiskit/qiskit/blob/2.5.2/qiskit/primitives/containers/sampler_pub_result.py) delegates to [BitArray source](https://github.com/Qiskit/qiskit/blob/2.5.2/qiskit/primitives/containers/bit_array.py). Runtime confirms the first named register occupies the least-significant bits. Its docstring incorrectly describes left-to-right displayed concatenation.
- [StatevectorEstimator API](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.primitives.StatevectorEstimator) and [released implementation](https://github.com/Qiskit/qiskit/blob/2.5.2/qiskit/primitives/statevector_estimator.py): unitary zero-precision results are exact, positive precision adds Gaussian noise, and `stds` stay zero.
- [Runtime Sampler preparation source](https://github.com/Qiskit/qiskit-ibm-runtime/blob/0.50.0/qiskit_ibm_runtime/executor_sampler/prepare.py) rejects input boxes even when twirling is enabled; the current API page documents a weaker restriction. Executed both branches.
- [Fractional-gate guide](https://quantum.cloud.ibm.com/docs/en/guides/fractional-gates) contains a `least_busy(fractional_gates=True)` typo. The [service API](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service) and released signature use `use_fractional_gates`.
- [Optimization 0.7 migration](https://qiskit-community.github.io/qiskit-optimization/migration/03_migration_guide_to_v0.7.html) requires its own QAOA/optimizer/result types for `MinimumEigenOptimizer`; the corrected example was run separately.
- [Qiskit Dynamics](https://github.com/qiskit-community/qiskit-dynamics) was archived October 31, 2025 and is no longer maintained; removed its unqualified recommendation as a current pulse replacement.
- `Statevector.to_bloch()` does not exist in 2.5.2. Pauli X/Y/Z expectations give the validated single-qubit Bloch vector.

No cloud credentials were loaded or saved, no account/backend queries authenticated, and no remote jobs (including server dry runs), cancellations, sessions, or batches were executed. Local Aer does not validate IBM scheduling, cost, access, or hardware mitigation. Optional Nature/PySCF, Machine Learning, addons, QASM3 import, TeX, notebook, and backend-map examples are documentation-checked and illustrative.

## IBM HTTP contract behind the SDK

Use the SDK for request serialization and result decoding. These contracts were reviewed against [REST introduction](https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest), [OpenAPI](https://quantum.cloud.ibm.com/api/openapi.json), and [Runtime 0.50 source](https://github.com/Qiskit/qiskit-ibm-runtime/tree/0.50.0/qiskit_ibm_runtime/api). They were not authenticated end-to-end tests. A direct unauthenticated Python OpenAPI download returned HTTP 403; the browser research tool could read the schema. HTTP status alone was not used to infer a contract.

The standard public base is `https://quantum.cloud.ibm.com/api/v1` for us-east, or `https://eu-de.quantum.cloud.ibm.com/api/v1` for eu-de. The instance CRN drives region selection. Runtime 0.50 sends `IBM-API-Version: 2026-04-15`; some REST page snippets still show an older header. IBM IAM exchanges the API key at `POST https://iam.cloud.ibm.com/identity/token` using a form body (`grant_type=urn:ibm:params:oauth:grant-type:apikey`, `apikey`). Quantum requests use `Authorization: Bearer ...` and `Service-CRN`, plus the version header. Let the SDK manage expiry; never log headers.

| SDK behavior | HTTP contract checked in schema/released adapter |
|---|---|
| List and inspect backends | `GET /backends` returns a `devices` array; no cursor pagination. `GET /backends/{name}/configuration`, `/properties`, `/status` return backend data. Calibration queries accept `calibration_id`; properties also use `updated_before`. Status adapter translates raw `state`, `status`, `length_queue` to `operational`, `status_msg`, `pending_jobs`. |
| Submit a primitive | `POST /jobs` with SDK-encoded `program_id`, `params`, backend and optional session/tags/cost fields; response contains `id`. New client-side primitives submit Executor programs. Do not handcraft a legacy sampler body for them. |
| Retrieve and decode | `GET /jobs/{id}` (optional `exclude_params`) returns job information; `GET /jobs/{id}/results` returns encoded result text which the SDK decodes using the job's program/semantic role. `GET /jobs/{id}/metrics` backs usage/metadata. |
| List jobs | `GET /jobs` uses `limit` (1–200), `offset`, backend/program/session/tags/status/time filters. SDK `skip` maps to `offset`. The SDK handles paging; this is distinct from cursor-based `/workloads`. |
| Cancel a job | `POST /jobs/{id}/cancel`; a remote mutation, never a connectivity test. |
| Batch/session lifecycle | `POST /sessions` with backend, `max_ttl`, and mode (`batch` or `dedicated`); returns `id`. `GET /sessions/{id}` reads state. Context exit closes via `PATCH /sessions/{id}` with `accepting_jobs=false`, allowing accepted work to finish. `DELETE /sessions/{id}/close` cancels queued work and differs from graceful close. |

SDK account discovery may additionally use IBM Cloud IAM, Global Search, Global Catalog, and Resource Controller APIs; this skill delegates that to the released SDK rather than constructing those requests. Instance names and permissions were source-reviewed, not tested against a user account.

## How to Refresh This Skill

1. Query PyPI JSON metadata for every pinned distribution.
2. Compare PyPI with GitHub releases and official release notes.
3. Read Qiskit major/minor migration and deprecation sections.
4. Read Runtime release notes independently.
5. Recheck valid channel names, account setup, plan restrictions, and option compatibility.
6. Run all bundled scripts in an isolated environment.
7. Execute relevant core/application/visualization snippets; mark every unexecuted optional workflow illustrative.
8. Update the verification date and version tables.
9. Increment `metadata.version` in `SKILL.md`.
10. Run `uv run skills-ref validate skills/qiskit` and the local security scan.
