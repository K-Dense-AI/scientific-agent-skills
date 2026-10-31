# Cirq review evidence

Reviewed 2026-09-30. Local target: Cirq and its vendor packages **1.7.0** on
Python 3.13. The official release adds IonQ v0.4 support and retains Python 3.11+
compatibility. Azure is checked separately with **qdk 1.32.3**, **azure-quantum
3.13.0**, and their required **Cirq 1.6.1** stack.

## Executed locally

The repository suite at `tests/cirq/test_examples.py` executes the main Python
examples and all local reference examples, with these scientific checks:

- Bell state amplitudes, measurement support, density matrices, reduced states,
  parameter Product/Zip sweeps, noisy ensembles, and Clifford simulation.
- Matrix-gate unitarity, QASM/JSON parsing, QFT equivalence for 2-4 qubits, and
  qutrit cyclic evolution.
- Custom H decomposition, CZ compilation of independent random 4x4 unitaries,
  routing with final permutations, and local Google device validation.
- T1 population and T2 coherence decay, invalid relaxation inputs, asymmetric
  readout-matrix orientation, singular calibration rejection, and ZNE intercept.
- Current `single_qubit_rb`/`RBParameters`, linear XEB API, VQE against exact
  diagonalization, reversed observable ordering, MaxCut angle/sign/node mapping,
  and all eight exactly representable three-bit QPE phases.
- Two-qubit Willow QVM using bundled median noise, AQT's offline ideal simulator,
  and a local Pasqal NamedQubit device. No QPU or remote simulator jobs.

The isolated Azure environment was imported and signatures were inspected:
`qdk.azure.Workspace`, `qdk.azure.cirq.AzureQuantumService`, `create_job(program=...)`,
and `run(program=...)`; a local Cirq 1.6.1 Bell circuit passed. No workspace was
accessed and no Azure job was submitted. Installation compatibility and Python
signatures do not establish live authentication or service behavior.

## Provider contract findings

| Provider | Evidence and limit |
| --- | --- |
| Google | Current access/IAM/project documentation and 1.7.0 Engine source reviewed; local QVM/device compilation executed. Actual project membership, assigned processor, live calibration, and jobs untested. |
| IonQ | Current v0.4 job/backend/characterization/result documentation plus installed 1.7.0 client source checked. `target` maps to `backend`; apiKey auth, job polling and probability result routes confirmed in source. Old calibration helper still uses `/calibrations/current`, absent from current v0.4 documentation; removed as a recommended workflow. No authenticated request made. |
| AQT | Live public OpenAPI **1.1.1** and 1.7.0 adapter source agree on Arnica workspace/resource submission, Bearer auth, and result polling. Offline ideal sampler executed. Released HTTP/polling code has no finite timeout and does not terminate on the current API's `cancelled` state. No authenticated workspace/result request or job. |
| Azure | Current Microsoft quickstart, both released distributions' dependency metadata and source, and isolated import/signature check. Current Cirq extra requires `<1.7`; separate environment documented. Targets/auth/results untested against a workspace. |
| Pasqal | Released sampler source and current official provider/Cloud SDK documentation checked. Legacy raw-Authorization/Cirq-JSON simulator routes are not a verified current Cloud contract; TLS verification is disabled in that adapter. Removed guessed cloud host and remote execution recipe; local device validated only. |

ReCirq's current repository was reviewed for its role as a collection of
research experiments; no ReCirq experiment dependency stack or research dataset
was installed. Toy VQE, QAOA and XEB examples are scoped as API/numerical checks,
not validated chemistry, optimization advantage, or hardware-fidelity claims.

## Official sources

- [Cirq 1.7.0 release](https://github.com/quantumlib/Cirq/releases/tag/v1.7.0)
- [Cirq release metadata](https://pypi.org/pypi/cirq/1.7.0/json)
- [Simulation](https://quantumai.google/cirq/simulate/simulation), [sweeps](https://quantumai.google/cirq/simulate/params), [partial trace](https://quantumai.google/reference/python/cirq/partial_trace)
- [Transformers](https://quantumai.google/cirq/transform/transformers), [RouteCQC](https://quantumai.google/reference/python/cirq/RouteCQC), [MatrixGate](https://quantumai.google/reference/python/cirq/MatrixGate)
- [Noise representation](https://quantumai.google/cirq/noise/representing_noise), [phase damping](https://quantumai.google/reference/python/cirq/PhaseDampingChannel)
- [Released RB implementation](https://github.com/quantumlib/Cirq/blob/v1.7.0/cirq-core/cirq/experiments/qubit_characterizations.py), [released fidelity estimators](https://github.com/quantumlib/Cirq/blob/v1.7.0/cirq-core/cirq/experiments/fidelity_estimation.py)
- [Google QVM](https://quantumai.google/cirq/simulate/quantum_virtual_machine), [access](https://quantumai.google/cirq/google/access)
- [IonQ create job](https://docs.ionq.com/api-reference/v0.4/jobs/create-job), [list jobs](https://docs.ionq.com/api-reference/v0.4/jobs/get-jobs), [result formats](https://docs.ionq.com/api-reference/v0.4/schemas/results-formats), [backends](https://docs.ionq.com/api-reference/v0.4/backends/get-backends), [characterization](https://docs.ionq.com/api-reference/v0.4/backends/get-a-characterization)
- [AQT OpenAPI](https://arnica.aqt.eu/api/v1/openapi.json), [released adapter](https://github.com/quantumlib/Cirq/blob/v1.7.0/cirq-aqt/cirq_aqt/aqt_sampler.py)
- [Azure quickstart](https://learn.microsoft.com/en-us/azure/quantum/quickstart-microsoft-cirq), [QDK metadata](https://pypi.org/pypi/qdk/1.32.3/json), [Azure metadata](https://pypi.org/pypi/azure-quantum/3.13.0/json)
- [Pasqal legacy sampler](https://quantumai.google/cirq/hardware/pasqal/sampler), [released adapter](https://github.com/quantumlib/Cirq/blob/v1.7.0/cirq-pasqal/cirq_pasqal/pasqal_sampler.py), [current Cloud SDK](https://docs.pasqal.com/cloud/pasqal-cloud/api/sdk/)
- [ReCirq](https://github.com/quantumlib/ReCirq)
