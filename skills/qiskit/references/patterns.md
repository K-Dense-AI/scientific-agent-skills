# End-to-End Qiskit Patterns

Use a four-stage workflow:

```text
Map -> Optimize -> Execute -> Analyze
```

Keep these stages separate so circuit construction, compilation, paid execution, and interpretation can each be tested and reproduced.

## Pattern 1: Local Bell-State Baseline

### Map

```python
from qiskit import QuantumCircuit

circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure_all()
```

### Optimize

Local statevector primitives accept abstract circuits. A pass manager is still useful for testing the same workflow shape:

```python
from qiskit.transpiler import generate_preset_pass_manager

pass_manager = generate_preset_pass_manager(
    optimization_level=1,
    seed_transpiler=31,
)
compiled = pass_manager.run(circuit)
```

### Execute

```python
from qiskit.primitives import StatevectorSampler

sampler = StatevectorSampler(seed=31)
pub_result = sampler.run([compiled], shots=2048).result()[0]
```

### Analyze

```python
counts = pub_result.data.meas.get_counts()
total = sum(counts.values())
probabilities = {
    bitstring: count / total
    for bitstring, count in counts.items()
}

unexpected = sum(
    probability
    for state, probability in probabilities.items()
    if state not in {"00", "11"}
)
print(probabilities, unexpected)
```

Use this ideal baseline before adding a noise model or QPU.

## Pattern 2: IBM QPU Sampling

### Map

```python
from qiskit import QuantumCircuit

circuit = QuantumCircuit(3)
circuit.h(0)
circuit.cx(0, 1)
circuit.cx(1, 2)
circuit.measure_all()
```

### Select and Optimize

```python
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService()
backend = service.least_busy(
    operational=True,
    simulator=False,
    min_num_qubits=circuit.num_qubits,
)

pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1,
    seed_transpiler=31,
)
isa_circuit = pass_manager.run(circuit)

print("depth:", isa_circuit.depth())
print("operations:", isa_circuit.count_ops())
print("layout:", isa_circuit.layout)
```

### Execute

```python
from qiskit_ibm_runtime import SamplerV2 as Sampler

sampler = Sampler(mode=backend)
job = sampler.run([isa_circuit], shots=4096)
job_id = job.job_id()
print("job_id:", job_id)
pub_result = job.result()[0]
```

### Analyze

```python
counts = pub_result.data.meas.get_counts()
shots = sum(counts.values())
ghz_support = (
    counts.get("000", 0) + counts.get("111", 0)
) / shots

record = {
    "job_id": job_id,
    "backend": backend.name,
    "shots": shots,
    "ghz_support": ghz_support,
    "result_metadata": pub_result.metadata,
}
```

Do not present GHZ support as state fidelity without a justified measurement protocol.

## Pattern 3: Parameter Sweep with One Compilation

Build and compile one parameterized circuit:

```python
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.transpiler import generate_preset_pass_manager

theta = Parameter("theta")
circuit = QuantumCircuit(2)
circuit.ry(theta, 0)
circuit.cx(0, 1)
circuit.measure_all()

pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1,
    seed_transpiler=31,
)
isa_circuit = pass_manager.run(circuit)

parameter_values = np.linspace(0, np.pi, 21).reshape(-1, 1)
```

Submit values through one PUB:

```python
sampler = Sampler(mode=backend)
pub_result = sampler.run(
    [(isa_circuit, parameter_values)],
    shots=1024,
).result()[0]

counts_by_point = [
    pub_result.data.meas.get_counts(index)
    for index in range(len(parameter_values))
]
```

This preserves a consistent layout and avoids repeated compilation.

## Pattern 4: Variational Estimator Loop

Use a parameterized ansatz and map the observable after compilation:

```python
import numpy as np
from qiskit.circuit.library import efficient_su2
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler import generate_preset_pass_manager

ansatz = efficient_su2(
    num_qubits=2,
    reps=1,
    entanglement="linear",
)
hamiltonian = SparsePauliOp.from_list(
    [
        ("ZI", 1.0),
        ("IZ", 1.0),
        ("XX", 0.2),
    ]
)

pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1,
    seed_transpiler=31,
)
isa_ansatz = pass_manager.run(ansatz)
isa_hamiltonian = hamiltonian.apply_layout(isa_ansatz.layout)
initial_point = np.zeros(ansatz.num_parameters)
```

Run iterative Estimator calls. Session mode requires an eligible paid plan:

```python
from scipy.optimize import minimize
from qiskit_ibm_runtime import EstimatorV2 as Estimator, Session

history = []

with Session(backend=backend, max_time="20m") as session:
    estimator = Estimator(
        mode=session,
        options={"resilience_level": 1},
    )

    def objective(parameters):
        pub = (
            isa_ansatz,
            isa_hamiltonian,
            [parameters],
        )
        pub_result = estimator.run(
            [pub],
            precision=0.03,
        ).result()[0]
        value = float(np.asarray(pub_result.data.evs).reshape(-1)[0])
        history.append(
            {
                "parameters": parameters.copy(),
                "value": value,
                "metadata": pub_result.metadata,
            }
        )
        return value

    optimum = minimize(
        objective,
        initial_point,
        method="COBYLA",
        options={"maxiter": 25},
    )
```

For Open Plan access, instantiate `Estimator(mode=backend)` and use job mode. The circuit remains compiled once in either case.

## Pattern 5: Independent Experiments in a Batch

Compile all circuits against the same target:

```python
pass_manager = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1,
    seed_transpiler=31,
)
isa_circuits = pass_manager.run(circuits)
```

Submit independent jobs:

```python
from qiskit_ibm_runtime import Batch, SamplerV2 as Sampler

with Batch(backend=backend, max_time="10m") as batch:
    sampler = Sampler(mode=batch)
    jobs = [
        sampler.run([circuit], shots=2048)
        for circuit in isa_circuits
    ]

job_records = [
    {
        "job_id": job.job_id(),
        "result": job.result(),
    }
    for job in jobs
]
```

Keep the job list aligned with an explicit experiment manifest.

## Pattern 6: Ideal, Noisy, and Hardware Ladder

Evaluate in three stages:

1. `StatevectorSampler` or `StatevectorEstimator`.
2. Aer or a fake backend using a recorded noise/target snapshot.
3. The selected QPU with the same logical inputs and analysis.

Do not force every stage to use identical compiled circuits: simulator and QPU targets differ. Preserve the same logical circuit and compile separately for each target.

Compare:

- ideal application metric,
- noisy-model application metric,
- QPU application metric,
- compiler layout and native operation counts,
- uncertainty and metadata.

Avoid claiming a noise model predicts QPU output merely because the two results are close once.

## Pattern 7: Mitigation A/B Test

Run an unmitigated baseline:

```python
from qiskit_ibm_runtime import EstimatorV2 as Estimator

baseline_estimator = Estimator(
    mode=backend,
    options={"resilience_level": 0},
)
baseline = baseline_estimator.run(
    [(isa_circuit, isa_observable)],
    precision=0.03,
).result()[0]
```

Run a mitigated configuration:

```python
mitigated_estimator = Estimator(
    mode=backend,
    options={"resilience_level": 2},
)
mitigated = mitigated_estimator.run(
    [(isa_circuit, isa_observable)],
    precision=0.03,
).result()[0]
```

Compare both against a justified ideal or classically verifiable reference. Report uncertainty, usage, and total circuit/shot overhead. Do not assume the mitigated value is closer.

## Experiment Manifest

Persist enough information to reconstruct the workflow:

```python
from importlib.metadata import version

manifest = {
    "packages": {
        "qiskit": version("qiskit"),
        "qiskit-ibm-runtime": version("qiskit-ibm-runtime"),
    },
    "backend": backend.name,
    "job_ids": job_ids,
    "seed_transpiler": 31,
    "optimization_level": 1,
    "shots": 4096,
    "primitive_options": resolved_options,
    "logical_parameter_order": [
        parameter.name for parameter in logical_circuit.parameters
    ],
    "compiled_layout": str(isa_circuit.layout),
    "compiled_operations": dict(isa_circuit.count_ops()),
}
```

Store logical and ISA circuits in QPY, and store the manifest in a text format such as JSON after converting Qiskit-specific objects to explicit strings or dictionaries.

Never serialize credentials, service account objects, raw environments, or API request headers.

## Preflight Before Paid Execution

1. Run the local primitive example.
2. Validate circuit width, parameter order, and classical-register names.
3. Check observable width and apply the final layout.
4. Compile against the exact backend object and inspect native two-qubit operations.
5. Test against a fake or Aer backend.
6. Estimate PUB expansion from parameter arrays, observables, mitigation, and twirling.
7. Select an allowed execution mode and bounded `max_time`.
8. Persist job IDs immediately.
9. Analyze the application metric, not only raw counts or expectation values.
