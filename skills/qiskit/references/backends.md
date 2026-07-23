# Backends, Runtime Modes, Simulation, and Noise Management

## BackendV2

Qiskit 2.x providers expose hardware and simulators through `BackendV2`. Important public attributes include:

```python
print(backend.name)
print(backend.num_qubits)
print(backend.operation_names)
print(backend.coupling_map)
print(backend.target)
print(backend.status())
```

The `Target` describes operation support, qubit operands, connectivity, and available timing/error metadata.

Do not use `backend.configuration()`, `BackendProperties`, or other BackendV1 patterns in new code.

## Connect to IBM Quantum

Use a securely saved account:

```python
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService()
```

New account configurations use `channel="ibm_quantum_platform"`. See [setup.md](setup.md) for secure credential setup. Never embed or print an API key.

## Discover Backends

Select by requirements, not by a system name copied from a tutorial:

```python
backends = service.backends(
    operational=True,
    simulator=False,
    min_num_qubits=20,
)

for candidate in backends:
    status = candidate.status()
    print(
        candidate.name,
        candidate.num_qubits,
        status.pending_jobs,
    )
```

For exploratory work:

```python
backend = service.least_busy(
    operational=True,
    simulator=False,
    min_num_qubits=20,
)
```

Least busy is not necessarily best. For a production experiment, compare:

- required qubit count,
- connectivity and native two-qubit operations,
- calibration quality on candidate subgraphs,
- control-flow or fractional-gate requirements,
- plan and region,
- queue and expected execution time.

The bundled read-only inspector summarizes one selected backend:

```bash
python scripts/inspect_runtime.py --min-qubits 20
python scripts/inspect_runtime.py --backend BACKEND_NAME --json
```

## Inspect Target Capabilities

```python
target = backend.target

print("operations:", sorted(backend.operation_names))
print("supports if_else:", "if_else" in backend.operation_names)
print("supports reset:", "reset" in backend.operation_names)
print("coupling edges:", list(backend.coupling_map.get_edges()))
```

Operation support can vary by qubit tuple. A name appearing in `operation_names` does not imply every qubit or pair supports it.

## Prepare ISA Circuits

```python
from qiskit.transpiler import generate_preset_pass_manager

pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1,
    seed_transpiler=23,
)
isa_circuit = pass_manager.run(circuit)
```

For Estimator:

```python
isa_observable = observable.apply_layout(isa_circuit.layout)
```

Runtime V2 primitives do not perform this conversion automatically.

## Job Mode

Use job mode for independent one-off primitive calls:

```python
from qiskit_ibm_runtime import SamplerV2 as Sampler

sampler = Sampler(mode=backend)
job = sampler.run([isa_circuit], shots=1024)

job_id = job.job_id()
print("job_id:", job_id)
result = job.result()
```

Persist the ID before blocking. Retrieve later:

```python
service = QiskitRuntimeService()
job = service.job(job_id)
print(job.status())
result = job.result()
```

Cancel only if the experiment should no longer consume allocation:

```python
job.cancel()
```

## Batch Mode

Batch mode is for independent jobs that can be submitted together. It is available to Open Plan users.

```python
from qiskit_ibm_runtime import Batch, SamplerV2 as Sampler

with Batch(backend=backend, max_time="10m") as batch:
    sampler = Sampler(mode=batch)
    jobs = [
        sampler.run([isa_circuit], shots=1024)
        for isa_circuit in isa_circuits
    ]

# The batch accepts no new jobs; submitted jobs can still finish.
results = [job.result() for job in jobs]
```

Batch jobs are scheduled as a group, but do not assume an application-level result order beyond the job list you preserve.

## Session Mode

Session mode is for iterative workloads such as VQE parameter updates:

```python
from qiskit_ibm_runtime import EstimatorV2 as Estimator, Session

with Session(backend=backend, max_time="20m") as session:
    estimator = Estimator(mode=session)
    jobs = [
        estimator.run([pub], precision=0.03)
        for pub in iterative_pubs
    ]
```

Open Plan users cannot submit session jobs; use job or batch mode. Sessions have maximum and interactive time-to-live limits. Close them as soon as submission is complete.

Creating `Estimator(mode=backend)` inside a session context still selects job mode. Use `mode=session`.

## Exact Local Primitives

For small ideal circuits:

```python
from qiskit.primitives import StatevectorEstimator, StatevectorSampler

sampler = StatevectorSampler(seed=23)
estimator = StatevectorEstimator(seed=23)
```

These implementations use local statevector simulation and do not model backend noise.

Memory for a dense statevector grows as \(2^n\). Use an algorithm-appropriate Aer method or tensor-network tooling for larger circuits.

## Aer Simulation

Install the pinned Aer distribution:

```bash
uv pip install "qiskit-aer==0.17.2"
```

Create an ideal Aer backend:

```python
from qiskit_aer import AerSimulator

aer = AerSimulator(method="automatic")
```

Run through Runtime's local-testing primitive interface:

```python
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2 as Sampler

pass_manager = generate_preset_pass_manager(
    backend=aer,
    optimization_level=1,
    seed_transpiler=23,
)
isa_circuit = pass_manager.run(circuit)

sampler = Sampler(
    mode=aer,
    options={"simulator": {"seed_simulator": 23}},
)
result = sampler.run([isa_circuit], shots=1024).result()
```

Most Runtime options other than shots and simulator settings are ignored in local testing. Do not infer that mitigation was simulated merely because an options object accepted the field.

## Approximate a Real Backend in Aer

```python
from qiskit_aer import AerSimulator

noisy_aer = AerSimulator.from_backend(backend)
pass_manager = generate_preset_pass_manager(
    backend=noisy_aer,
    optimization_level=1,
    seed_transpiler=23,
)
noisy_isa = pass_manager.run(circuit)

sampler = Sampler(
    mode=noisy_aer,
    options={"simulator": {"seed_simulator": 23}},
)
result = sampler.run([noisy_isa], shots=4096).result()
```

This captures a subset of backend properties at model-construction time. It does not reproduce drift, all crosstalk, or every Runtime service behavior.

## Fake Backends

Fake backends provide a local `BackendV2` target and calibration-like snapshot:

```python
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

fake_backend = FakeSherbrooke()
```

Use them to test target-aware transpilation and Runtime local mode. Fake-backend class names can change; inspect the installed `qiskit_ibm_runtime.fake_provider` module before selecting one.

## Estimator Noise Management

Runtime Estimator exposes increasing levels of built-in mitigation:

```python
from qiskit_ibm_runtime import EstimatorV2 as Estimator

estimator = Estimator(
    mode=backend,
    options={"resilience_level": 1},
)
```

Current supported resilience levels:

- `0`: disable built-in resilience.
- `1`: measurement mitigation.
- `2`: measurement mitigation plus additional techniques such as ZNE, according to current defaults.

There is no resilience level 3 in the current V2 API.

Configure explicit techniques when the experiment requires control:

```python
estimator = Estimator(mode=backend)
estimator.options.dynamical_decoupling.enable = True
estimator.options.dynamical_decoupling.sequence_type = "XpXm"

estimator.options.twirling.enable_gates = True
estimator.options.twirling.num_randomizations = 32
estimator.options.twirling.shots_per_randomization = 100

estimator.options.resilience.zne_mitigation = True
estimator.options.resilience.zne.noise_factors = (1, 3, 5)
estimator.options.resilience.zne.extrapolator = "exponential"
```

Mitigation adds bias assumptions, circuit variants, shots, classical processing, and cost. It is not guaranteed to improve an observable.

## Sampler Noise Management

Sampler returns sampled classical data and does not use Estimator resilience levels:

```python
sampler = Sampler(mode=backend)
sampler.options.dynamical_decoupling.enable = True
sampler.options.dynamical_decoupling.sequence_type = "XpXm"
sampler.options.twirling.enable_gates = True
```

Measurement and gate-twirling defaults differ between Sampler and Estimator and can change. Record the resolved options for every experiment.

## Feature Compatibility

Some combinations are restricted. Current examples include incompatibilities among:

- fractional gates,
- gate twirling,
- probabilistic error amplification (PEA),
- probabilistic error cancellation (PEC),
- gate-folding zero-noise extrapolation (ZNE),
- some dynamic-circuit features.

Always consult the current Estimator/Sampler options and backend target. Do not copy a mitigation configuration between Runtime versions without revalidation.

## Fractional Gates

Request a backend target that exposes fractional gates when the algorithm benefits:

```python
backend = service.backend(
    backend_name,
    use_fractional_gates=True,
)
```

Compile against the returned object. `use_fractional_gates` changes the target and can affect compatibility with control flow and mitigation.

Qiskit Pulse is not an alternative; `qiskit.pulse` was removed in Qiskit 2.0.

## Third-Party Providers

Qiskit can target non-IBM providers through separately installed provider packages. Each provider controls:

- authentication,
- backend discovery,
- supported `BackendV2` features,
- whether native V2 primitives exist,
- transpilation plugins,
- result and cost semantics.

Prefer the provider's current documentation. If only `BackendV2` is available, adapt it with `BackendSamplerV2` or `BackendEstimatorV2`. Do not assume IBM Runtime options, sessions, or mitigation are portable.

## Operational Checklist

Before submitting:

1. Verify the account, plan, instance, and region.
2. Select a backend by circuit width and capabilities.
3. Compile and test locally against a fake/noisy backend.
4. Apply the circuit layout to Estimator observables.
5. Estimate the number of PUBs, circuits after randomization/mitigation, shots, and maximum execution time.
6. Choose job, batch, or session mode.
7. Save job IDs immediately.
8. Store versions, backend, target timestamp, compiler seed, primitive options, and metadata.

## Common Failures

- **Authentication failure**: use `ibm_quantum_platform`, verify the saved account, API key, and instance access.
- **Backend not found**: list accessible backends; systems and account entitlements change.
- **Circuit not ISA-compatible**: submit the circuit returned by the backend-specific pass manager.
- **Open Plan session error**: use job or batch mode.
- **Unsupported option combination**: check the current feature-compatibility table.
- **Unexpected queue/cost**: inspect the plan, mode TTL, precision, shots, mitigation, and twirling expansion.
- **Simulation differs from QPU**: document the model snapshot and unmodeled effects rather than tuning until outputs match.
