# Devices and backend boundaries

PennyLane 0.45.1 is the tested core. Provider integrations below were checked
against official docs/released source, **not authenticated hardware jobs**.
Install each provider/compiler in a separate environment and resolve its declared
requirements; a plugin version number does not guarantee all current backend APIs.

## Local simulators and reusable circuits

```python
import pennylane as qml
from pennylane import numpy as np

def quantum_function(theta):
    qml.RY(theta, wires=0)
    qml.CNOT(wires=[0, 1])
    return qml.expval(qml.Z(1))

results = {}
for name in ["default.qubit", "lightning.qubit", "default.mixed"]:
    dev = qml.device(name, wires=2)
    circuit = qml.QNode(quantum_function, dev, diff_method="parameter-shift")
    theta = np.array(0.3, requires_grad=True)
    results[name] = float(circuit(theta))
    assert np.allclose(results[name], np.cos(theta))
    assert np.allclose(qml.grad(circuit)(theta), -np.sin(theta))
```

`default.mixed` supports explicit channels; changing to it does not automatically
apply a realistic hardware noise model. Lightning speedups depend on circuit size
and overhead. `lightning.gpu` requires its separate CUDA/cuQuantum-compatible
plugin and hardware; no GPU fallback should silently change a reported benchmark.
`default.clifford` needs Stim and accepts only its supported Clifford operations
and measurements (some Pauli rotations at Clifford angles may be supported).
There is no universal fixed qubit limit or provider noise ranking.

Use `dev.name`, `dev.wires` and `len(dev.wires)` when wires are allocated. New
Device API objects do not universally expose legacy `num_wires`, `operations`,
`observables` or `apply`. Some use dynamic wires or optional capabilities objects.
Inspect each device's documented preprocessing and derivative support; run a tiny
representative circuit. For custom devices implement the current execution and
preprocessing protocol, not an obsolete `DefaultQubit.apply` override. A custom
operator can implement `compute_decomposition`; registering an arbitrary attribute
on `qml.ops` is not plugin registration.

## Provider installation targets

These released versions were source/metadata checked on 2026-10-01. Commands are
illustrative dependency setup, not a tested combined environment:

```bash
# Choose one provider per environment.
uv pip install "pennylane==0.45.1" "pennylane-qiskit==0.45.0"
uv pip install "pennylane==0.45.1" "amazon-braket-pennylane-plugin==1.35.2"
uv pip install "pennylane==0.45.1" "pennylane-cirq==0.44.0"
uv pip install "pennylane==0.45.1" "pennylane-ionq==0.45.0"
```

Rigetti's last published plugin is 0.40.0, with `pyquil<4` and `networkx<3`;
resolve and validate it in its own legacy stack instead of installing it into the
current core/ML environment. Current QCS hardware availability requires provider
verification. Strawberry Fields' plugin documentation targets 0.29.1; an old
`strawberryfields.remote`/Borealis recipe is not evidence of compatibility or a
currently accessible backend with PennyLane 0.45.1.

## IBM Quantum: backend object and finite shots

`qiskit.aer` is a local simulator plugin. `qiskit.remote` accepts a Qiskit backend
object and uses EstimatorV2/SamplerV2. Allocate only the logical wires needed,
within backend capacity. Its execution is sampled; do not promise analytic results.

Illustrative authenticated setup, not executed:

```python
import os
import pennylane as qml
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService(
    channel="ibm_quantum_platform",
    token=os.environ["IBM_QUANTUM_API_KEY"],
    instance=os.environ["IBM_QUANTUM_INSTANCE"],
)
backend = service.least_busy(operational=True, simulator=False, min_num_qubits=2)
dev = qml.device("qiskit.remote", wires=2, backend=backend)
@qml.set_shots(1024)
@qml.qnode(dev, diff_method="parameter-shift")
def hardware_circuit(theta):
    qml.RY(theta, wires=0)
    qml.CNOT(wires=[0, 1])
    return qml.expval(qml.Z(1))
# Calling hardware_circuit submits work; record backend, calibration, shots and job metadata.
```

The environment variable names here are application-defined inputs, not automatic
SDK credential discovery. Saved credentials are another option:
`QiskitRuntimeService.save_account(...)` saves configuration; then construct
`QiskitRuntimeService()` separately. Do not assign `save_account`'s return value as
the service. The SDK resolves the IBM platform URL and handles authentication;
this skill does not implement a parallel REST client. Source docs and released
plugin source differ on the behavior of unspecified shots, so set an explicit
finite integer. Shot vectors are not supported by this plugin release.

## Amazon Braket

The plugin provides `braket.local.qubit` for local execution and
`braket.aws.qubit` for cloud tasks. Cloud construction uses `device_arn`, `wires`
and optional `s3_destination_folder=(bucket, prefix)`; use a bucket the account
owns/accesses. AWS SDK credentials and correct region are required for cloud use.
Discover the currently available device ARN with the Braket console/SDK and check
status, supported operations, shots and result types before selecting it. Do not
copy a historical Harmony ARN or an example bucket name into a live request.
The documented SV1 ARN is `arn:aws:braket:::device/quantum-simulator/amazon/sv1`;
a cloud simulator can still incur cost. No Braket task was submitted here.

## Cirq, Rigetti and photonics

The Cirq 0.44.0 plugin registers `cirq.simulator`, `cirq.mixedsimulator`,
`cirq.qsim`, `cirq.qsimh` and `cirq.pasqal`. qsim requires its optional native
package. **`cirq.pasqal` describes Pasqal neutral-atom devices, not Google's
Rainbow hardware.** Google Quantum Engine access needs an appropriate current
provider integration and access; do not infer it from installing the Cirq plugin.

Rigetti's legacy entry points include `rigetti.qvm`, `rigetti.qpu` and wavefunction
simulators. A QVM needs its runtime/services; a QPU needs current QCS credentials
and a currently accessible processor. Do not hardcode retired Aspen targets or
assume a QPU's number of qubits from an old example. Photonic workflows use different
state spaces/operations; confirm the dedicated plugin/runtime instead of swapping
a qubit QNode's device string to Borealis.

## IonQ: explicit current backend target

The released `pennylane-ionq==0.45.0` package registers `ionq.simulator` and
`ionq.qpu`. It reads an explicit `api_key`, then `PENNYLANE_IONQ_API_KEY`, then
`IONQ_API_KEY`. Its client uses IonQ API v0.4 and `Authorization: apiKey ...`.
An `ionq.simulator` circuit still uses the remote service and credentials.

For hardware, provide a currently discovered `target` explicitly. The released
plugin's generic `target="qpu"` fallback still rewrites to `qpu.aria-1`, while
current v0.4 create-job documentation lists Forte targets. That fallback is not
verified as usable. Do not interpret plugin defaults as current availability.
The source creates JSON jobs with `type`, `backend` and `input`; the service returns
a job ID/status and requires polling/result retrieval. The plugin handles those
contracts. No authentication or paid execution was attempted in this refresh.

## Shots, reproducibility and operations

Use `qml.set_shots(circuit, shots=1000)` to produce a configured QNode and
`shots=None` only on devices supporting analytic execution. A seeded simulator
advances its RNG between calls; recreating the device reproduces the sequence.
Do not globally cache one stateful device across independent concurrent experiments
without understanding its state, random stream and backend thread safety.

Before hardware execution, budget parameter shifts, measurement groups, repetitions
and shots, record the job identifier, and inspect failed/pending jobs before
retrying. Blind resubmission can duplicate charged work. Provider queue/calibration
and device topology drift require live checks. A matched local output establishes
circuit semantics only, not hardware fidelity or access.

## Primary sources

- [Device API](https://docs.pennylane.ai/en/stable/code/api/pennylane.devices.Device.html)
- [Lightning](https://docs.pennylane.ai/projects/lightning/en/stable/)
- [Qiskit remote device](https://docs.pennylane.ai/projects/qiskit/en/stable/devices/remote.html)
- [IBM runtime service](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service)
- [Released Qiskit device source](https://github.com/PennyLaneAI/pennylane-qiskit/blob/v0.45.0/pennylane_qiskit/qiskit_device.py)
- [Braket plugin](https://amazon-braket-pennylane-plugin-python.readthedocs.io/en/latest/)
- [Cirq entry points](https://github.com/PennyLaneAI/pennylane-cirq/blob/v0.44.0/setup.py)
- [Rigetti release](https://pypi.org/project/PennyLane-Rigetti/0.40.0/)
- [Strawberry Fields plugin](https://docs.pennylane.ai/projects/strawberryfields/en/latest/)
- [IonQ release](https://pypi.org/project/PennyLane-IonQ/0.45.0/)
- [IonQ v0.4 create-job contract](https://docs.ionq.com/api-reference/v0.4/jobs/create-job)
