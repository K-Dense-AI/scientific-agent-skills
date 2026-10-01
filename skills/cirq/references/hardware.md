# Hardware integration

Reviewed against Cirq 1.7.0 and current provider documentation on 2026-09-30.
Cloud snippets are **illustrative, not authenticated end-to-end tests**. They may
submit chargeable work, including remote simulators. Use a specifically selected
provider, assigned target, and shot budget. Local validation is demonstrated
separately and does not establish credentials or hardware availability.

## Device preparation and calibration

A `cirq.Circuit` does not accept `device=`. Choose physical qubits, compile to the
advertised target gateset, then validate. Sorted adjacent entries in a qubit list
need not be physically connected. This helper uses one actual device edge:

```python
import cirq
import cirq_google as cg
import numpy as np
import networkx as nx

def prepare_google_bell(device):
    a, b = next(iter(device.metadata.nx_graph.edges))
    circuit = cirq.Circuit(
        cirq.H(a), cirq.CNOT(a, b), cirq.measure(a, b, key="result")
    )
    target = device.metadata.compilation_target_gatesets[0]
    compiled = cirq.optimize_for_target_gateset(circuit, gateset=target)
    device.validate_circuit(compiled)
    return compiled

# Local topology/compiler check, no remote execution.
local_device = cg.engine.create_device_from_processor_id("willow_pink")
local_circuit = prepare_google_bell(local_device)
local_result = cirq.Simulator(seed=42).run(local_circuit, repetitions=100)
```

For larger logical circuits, use `cirq.RouteCQC(device.metadata.nx_graph)` and
preserve the returned initial and final permutations before compiling. See
[transformation.md](transformation.md). A connected set is not necessarily a path
or a grid; route to its actual induced graph.

```python
def select_connected_qubits(device, n_qubits):
    if n_qubits < 1:
        raise ValueError("Expected a positive qubit count")
    graph = device.metadata.nx_graph.to_undirected()
    for component in nx.connected_components(graph):
        if len(component) >= n_qubits:
            # A BFS prefix is connected, unlike an arbitrary node-list slice.
            root = min(component)
            return list(nx.bfs_tree(graph.subgraph(component), root))[:n_qubits]
    raise ValueError("No sufficiently large connected component")

def single_qubit_errors(calibration, metric="single_qubit_rb_average_error_per_gate"):
    if metric not in calibration:
        raise KeyError(f"Missing calibration metric: {metric}")
    # Metric -> {(qubit,): [value]}, not qubit -> metric -> value.
    return {qs[0]: float(values[0]) for qs, values in calibration[metric].items()
            if len(qs) == 1 and len(values) == 1 and np.isfinite(values[0])}
```

Use real available metric names and units. Lowest single-qubit error alone does
not select a good connected subgraph; include two-qubit errors and readout, and
record calibration timestamp. Missing metrics are missing data, not zero error.

## Google Quantum Engine

Requires a project and user approved for Quantum Computing Service, the
`quantum.googleapis.com` API enabled, appropriate IAM roles, and Application
Default Credentials. This uses Google's generated Quantum Engine client and
its resource names, not hand-built REST paths.

```bash
gcloud auth application-default login
# Set GOOGLE_CLOUD_PROJECT and GOOGLE_QUANTUM_PROCESSOR to assigned values.
```

Illustrative authenticated workflow:

```python
import os
import cirq_google as cg

engine = cg.Engine(project_id=os.environ["GOOGLE_CLOUD_PROJECT"])
print([p.processor_id for p in engine.list_processors()])
processor_id = os.environ["GOOGLE_QUANTUM_PROCESSOR"]
processor = engine.get_processor(processor_id)
device = processor.get_device()
circuit = prepare_google_bell(device)
sampler = engine.get_sampler(processor_id=processor_id)
# Submission; requires approved access and an intentional shot budget.
result = sampler.run(circuit, repetitions=100)
```

Do not default to `weber`, `willow`, or a bundled QVM processor name for cloud
submission. For an offline hardware-like workflow use the
[QVM example](simulation.md). Engine processor/program/job objects have distinct
interfaces; use provider job objects if you need durable job IDs and resumption,
not the generic `Sampler.run` result as if it were a job.

## IonQ API v0.4

`cirq-ionq==1.7.0` defaults to `https://api.ionq.co/v0.4` and reads `IONQ_API_KEY`.
The SDK sends `Authorization: apiKey ...`; do not substitute Bearer auth. A
configured `IONQ_REMOTE_HOST` overrides the default, so confirm its intended
host without printing credentials.

Illustrative submission:

```python
import os
import cirq_ionq as ionq

q0, q1 = cirq.LineQubit.range(2)
circuit = cirq.Circuit(cirq.H(q0), cirq.CNOT(q0, q1), cirq.measure(q0, q1, key="result"))
service = ionq.Service(api_version="v0.4")
# Set an available concrete backend from the IonQ console/API; "simulator" is remote.
target = os.environ["IONQ_TARGET"]
job = service.create_job(circuit, repetitions=100, target=target)
print(job.job_id(), job.status())
provider_result = job.results(timeout_seconds=300, polling_seconds=2)
result = provider_result.to_cirq_result()  # single-circuit job
```

Use `service.run(circuit, repetitions=100, target=target)` when only a Cirq result
is needed. The SDK's `target` argument becomes v0.4 `backend` in `POST /jobs`;
`repetitions` becomes `shots`, and the payload includes `type`, `input`, and
measurement metadata. `Job.results` polls `GET /jobs/{id}` and downloads
`/jobs/{id}/results/probabilities` (aggregated route for batch jobs). Simulator
probabilities may be sampled locally by the adapter; record this when interpreting
returned counts. `wait_until_complete()` is not a Cirq IonQ Job method.

Current v0.4 provider docs use `GET /backends` and backend-specific
`/backends/{backend}/characterizations/{characterization}`. The released
`Service.get_current_calibration()` still requests `/calibrations/current`, a
legacy path not listed in the current v0.4 contract. **Do not rely on that helper**
for current characterization; use the provider's documented backend/characterization
workflow. A successful SDK import does not verify that legacy endpoint. Discover
actual backend IDs rather than assuming the generic `qpu` alias is available.

The job list (`GET /jobs`) paginates using `limit` and a `next` cursor; stop when
response `next` is null. Do not apply job pagination assumptions to `/backends`. This guide submits a selected backend and does not implement custom
list pagination or assume an SDK helper repairs a changed service contract.

## Azure Quantum: separate supported environment

Current Microsoft guidance uses `qdk.azure.cirq.AzureQuantumService`. The released
QDK 1.32.3 and azure-quantum 3.13.0 Cirq extras require `cirq-core>=1.6.1,<1.7`
and `cirq-ionq>=1.6.1,<1.7`. Keep this environment separate from Cirq 1.7.0.

```bash
uv venv .venv-azure-cirq --python 3.13
uv pip install --python .venv-azure-cirq/bin/python "qdk[azure,cirq]==1.32.3" "azure-quantum==3.13.0"
```

Illustrative authenticated setup/submission:

```python
import os
from qdk.azure import Workspace
from qdk.azure.cirq import AzureQuantumService

workspace = Workspace(
    resource_id=os.environ["AZURE_QUANTUM_RESOURCE_ID"],
    location=os.environ["AZURE_QUANTUM_LOCATION"],
)
service = AzureQuantumService(workspace)
print([target.name for target in service.targets()])
job = service.create_job(
    program=circuit, repetitions=100, target=os.environ["AZURE_QUANTUM_TARGET"]
)
print(job.status())
provider_result = job.results()
```

Authenticate to the workspace with an Azure-supported credential flow. The
`program` keyword is required by this adapter; `circuit=` is not its run/create
argument. Discover compatible targets rather than hardcoding retired Honeywell
names. Workspace endpoints, identity tokens, storage, and provider conversion are
handled by the Azure SDK. Results may be provider-native; inspect their type
before using Cirq histogram methods. Released source/signatures and isolated imports were checked; no Azure job was
submitted in this review.

## AQT: Arnica workspace/resource API

Cirq 1.7.0 `AQTSampler` requires `workspace`, `resource`, and `access_token`.
Its base is `https://arnica.aqt.eu/api/v1/`, not `gateway.aqt.eu`. It uses Bearer
credentials, `GET /workspaces`, `POST /submit/{workspace}/{resource}`, and
`GET /result/{job_id}`. The current public OpenAPI returns the workspace list
without a pagination parameter. The SDK parses `job.job_id`, polls
`response.status` for `finished`/`error`, then reads `response.result["0"]` as shot
bit arrays. Select device versus simulator at construction, not `run(target=...)`.

Entirely local smoke example:

```python
import cirq_aqt
from cirq_aqt.aqt_device import get_aqt_device

device, qubits = get_aqt_device(2)
aqt_circuit = cirq.Circuit(cirq.XX(*qubits)**0.5)
device.validate_circuit(aqt_circuit)
aqt_local = cirq_aqt.AQTSamplerLocalSimulator(simulate_ideal=True)
aqt_result = aqt_local.run(aqt_circuit, repetitions=100)
print(aqt_result.histogram(key="m"))
```

The adapter implicitly measures every qubit at the end with key `m`; it supports
at most one explicit terminal measurement. Compile gates to the AQT gateset before
submission; arbitrary H/CNOT circuits are not directly native.

Illustrative authenticated setup (construction itself does not submit):

```python
import os
workspaces = cirq_aqt.AQTSampler.fetch_resources(os.environ["AQT_TOKEN"])
sampler = cirq_aqt.AQTSampler(
    workspace=os.environ["AQT_WORKSPACE"], resource=os.environ["AQT_RESOURCE"],
    access_token=os.environ["AQT_TOKEN"],
)
# sampler.run(aqt_circuit, repetitions=100) submits remote work.
```

The released adapter's requests and result-poll loop have no finite timeout.
The current API also returns `cancelled`, which this loop does not treat as
terminal. Use bounded external job supervision for actual remote runs and persist
job information; do not describe the adapter as having a configurable timeout.

## Pasqal: local device modeling; legacy remote adapter limitation

```python
import cirq_pasqal

qubits = [cirq.NamedQubit("a"), cirq.NamedQubit("b")]
device = cirq_pasqal.PasqalDevice(qubits=qubits)
pasqal_circuit = cirq.Circuit(cirq.X(qubits[0]), cirq.measure(*qubits, key="result"))
device.validate_circuit(pasqal_circuit)
pasqal_result = cirq.Simulator(seed=42).run(pasqal_circuit, repetitions=100)
```

The released `PasqalSampler` implements an old contract:
`POST {remote_host}/simulate/no-noise/submit` with Cirq JSON, raw Authorization and
Repetitions headers, a text task ID, then `GET /get-result/{id}` returning Cirq
JSON. Its requests explicitly disable TLS verification and its poll loop has no
timeout. Current Cirq provider documentation describes this API as private and
virtual-device-only. Current Pasqal Cloud SDK documentation uses a different
project/token-provider and batch/job contract. There is **no verified mapping**
from this adapter to `https://api.pasqal.cloud`; do not invent that endpoint or
send a cloud token to the legacy adapter. Use local modeling here and obtain a
currently supported integration from Pasqal for cloud execution.

## Data handling and batching

Persist target, circuit, parameters, qubit/measurement order, versions, shot count,
calibration provenance, durable job ID, and raw result. Generic `run_batch` returns
a list per circuit and a result per resolver; it need not submit as one provider
job. `run_async` returns an awaitable, not a concurrent Future with `.result()`.
Avoid unbounded concurrent submission and nested retries after an uncertain
submission response.

Readout mitigation requires measured calibration probabilities and uncertainty.
See [noise.md](noise.md); a placeholder function that returns uncorrected samples
must not be called an implemented mitigation routine.

## Official sources

- [Google access](https://quantumai.google/cirq/google/access) and [Engine](https://quantumai.google/reference/python/cirq_google/Engine)
- [Cirq 1.7.0 release](https://github.com/quantumlib/Cirq/releases/tag/v1.7.0)
- [IonQ create-job contract](https://docs.ionq.com/api-reference/v0.4/jobs/create-job), [backends](https://docs.ionq.com/api-reference/v0.4/backends/get-backends), [characterization](https://docs.ionq.com/api-reference/v0.4/backends/get-a-characterization)
- [Azure current quickstart](https://learn.microsoft.com/en-us/azure/quantum/quickstart-microsoft-cirq), [QDK metadata](https://pypi.org/pypi/qdk/1.32.3/json), [Azure metadata](https://pypi.org/pypi/azure-quantum/3.13.0/json)
- [AQT public OpenAPI](https://arnica.aqt.eu/api/v1/openapi.json) and [released adapter](https://github.com/quantumlib/Cirq/blob/v1.7.0/cirq-aqt/cirq_aqt/aqt_sampler.py)
- [Pasqal Cirq sampler](https://quantumai.google/cirq/hardware/pasqal/sampler), [released source](https://github.com/quantumlib/Cirq/blob/v1.7.0/cirq-pasqal/cirq_pasqal/pasqal_sampler.py), [current Cloud SDK](https://docs.pasqal.com/cloud/pasqal-cloud/api/sdk/)
