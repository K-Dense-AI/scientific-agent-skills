"""Small numerical regressions for the current SDK and client-side primitives."""
from io import BytesIO
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("qiskit")
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, qpy
from qiskit.circuit import Parameter
from qiskit.primitives import StatevectorEstimator, StatevectorSampler
from qiskit.quantum_info import Pauli, SparsePauliOp, Statevector
from qiskit.transpiler import CouplingMap, Target, generate_preset_pass_manager

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "qiskit"


def test_joint_registers_keep_correlations_and_explicit_order():
    q = QuantumRegister(2, "q")
    left, right = ClassicalRegister(1, "left"), ClassicalRegister(1, "right")
    circuit = QuantumCircuit(q, left, right)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.x(1)  # anti-correlation detects erroneous multiplication of marginals
    circuit.measure(0, left)
    circuit.measure(1, right)
    result = StatevectorSampler(seed=11).run([circuit], shots=128).result()[0]
    assert set(result.join_data(["left", "right"]).get_counts()) == {"01", "10"}
    deterministic = QuantumCircuit(q, left, right)
    deterministic.x(0)
    deterministic.measure(0, left)
    deterministic.measure(1, right)
    out = StatevectorSampler(seed=11).run([deterministic], shots=16).result()[0]
    assert out.join_data(["left", "right"]).get_counts() == {"01": 16}
    assert out.join_data(["right", "left"]).get_counts() == {"10": 16}


def test_measurement_permutation_is_not_qubit_order():
    circuit = QuantumCircuit(2, 2)
    circuit.x(0)
    circuit.measure([0, 1], [1, 0])
    result = StatevectorSampler(seed=1).run([circuit], shots=16).result()[0]
    assert result.data.c.get_counts() == {"10": 16}  # q0=1 but c0=0
    state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
    assert state.expectation_value(Pauli("IZ")) == -1
    assert state.expectation_value(Pauli("ZI")) == 1


def test_measure_all_adds_register_even_if_classical_bits_exist():
    circuit = QuantumCircuit(2, 2)
    circuit.measure_all()
    assert [r.name for r in circuit.cregs] == ["c", "meas"]
    assert circuit.num_clbits == 4


def test_parameter_broadcast_and_counts_do_not_merge_sweep_points():
    theta = Parameter("theta")
    circuit = QuantumCircuit(2)
    circuit.ry(theta, 0)
    circuit.cx(0, 1)
    values = [[0], [np.pi / 2], [np.pi]]
    observables = [[SparsePauliOp("ZI")], [SparsePauliOp("XX")]]
    result = StatevectorEstimator().run([(circuit, observables, values)]).result()[0]
    np.testing.assert_allclose(result.data.evs, [[1, 0, -1], [0, 1, 0]], atol=1e-12)
    assert result.data.evs.shape == (2, 3)
    circuit.measure_all()
    shots = StatevectorSampler(seed=7).run([(circuit, values)], shots=32).result()[0].data.meas
    assert shots.get_counts(0) == {"00": 32}
    assert shots.get_counts(2) == {"11": 32}
    assert sum(shots.get_counts().values()) == 96


def test_layout_mapping_preserves_asymmetric_observable():
    circuit = QuantumCircuit(2)
    circuit.x(0)
    target = Target.from_configuration(
        num_qubits=3, basis_gates=["cz", "sx", "rz"], coupling_map=CouplingMap.from_line(3)
    )
    manager = generate_preset_pass_manager(
        target=target, initial_layout=[2, 0], optimization_level=1, seed_transpiler=17
    )
    isa = manager.run(circuit)
    observable = SparsePauliOp("IZ")
    mapped = observable.apply_layout(isa.layout)
    estimator = StatevectorEstimator()
    assert estimator.run([(circuit, observable)]).result()[0].data.evs == pytest.approx(-1)
    assert estimator.run([(isa, mapped)]).result()[0].data.evs == pytest.approx(-1)
    assert estimator.run([(isa, SparsePauliOp("IIZ"))]).result()[0].data.evs == pytest.approx(1)
    for item in isa.data:
        qargs = tuple(isa.find_bit(q).index for q in item.qubits)
        assert target.instruction_supported(item.operation.name, qargs)


def test_qpy_preserves_parameters_metadata_and_unitary():
    circuit = QuantumCircuit(2, name="roundtrip")
    circuit.ry(Parameter("theta"), 0)
    circuit.cx(0, 1)
    circuit.metadata = {"measurement_basis": "Z", "synthetic": True}
    stream = BytesIO()
    qpy.dump(circuit, stream)
    stream.seek(0)
    loaded = qpy.load(stream)[0]
    assert loaded == circuit
    assert loaded.metadata == circuit.metadata
    assert list(loaded.parameters) == list(circuit.parameters)


def test_statevector_positive_precision_is_synthetic_noise_with_zero_stds():
    circuit = QuantumCircuit(1)
    result = StatevectorEstimator(seed=7).run([(circuit, SparsePauliOp("Z"))], precision=0.1).result()[0]
    expected = np.random.default_rng(7).normal(1, 0.1)
    assert result.data.evs == pytest.approx(expected)
    assert result.data.stds == 0


def runtime_stack():
    pytest.importorskip("qiskit_ibm_runtime")
    pytest.importorskip("qiskit_aer")
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.executor_sampler import Sampler
    from qiskit_ibm_runtime.executor_estimator import Estimator
    return AerSimulator, Sampler, Estimator


def test_client_side_runtime_sampler_and_estimator_locally():
    AerSimulator, Sampler, Estimator = runtime_stack()
    backend = AerSimulator()
    circuit = QuantumCircuit(2)
    circuit.x(0)
    circuit.cx(0, 1)
    manager = generate_preset_pass_manager(backend=backend, optimization_level=1, seed_transpiler=7)
    isa = manager.run(circuit)
    measured = isa.copy()
    measured.measure_all()
    sampler = Sampler(mode=backend, options={"simulator": {"seed_simulator": 7}})
    result = sampler.run([measured], shots=64).result()[0]
    assert result.data.meas.get_counts() == {"11": 64}
    estimator = Estimator(mode=backend, options={"resilience_level": 0, "simulator": {"seed_simulator": 7}})
    result = estimator.run([(isa, SparsePauliOp("ZI"))], precision=0.1).result()[0]
    assert result.data.evs == pytest.approx(-1)
    assert result.data.stds == pytest.approx(0)


def test_client_side_runtime_rejects_unequal_shots_and_boxes():
    AerSimulator, Sampler, _ = runtime_stack()
    from qiskit_ibm_runtime.exceptions import IBMInputValueError
    circuit = QuantumCircuit(1)
    circuit.measure_all()
    sampler = Sampler(mode=AerSimulator())
    with pytest.raises(IBMInputValueError, match="same number of shots"):
        sampler.run([(circuit, None, 16), (circuit, None, 32)])
    boxed = QuantumCircuit(1)
    with boxed.box():
        boxed.x(0)
    boxed.measure_all()
    for enabled in (False, True):
        sampler.options.twirling.enable_gates = enabled
        with pytest.raises(IBMInputValueError, match="BoxOp"):
            sampler.run([boxed], shots=16)


def test_client_side_options_finalize_mitigation_and_reject_invalid_level():
    AerSimulator, _, Estimator = runtime_stack()
    from qiskit_ibm_runtime.options_models import EstimatorOptions
    from pydantic import ValidationError
    options = EstimatorOptions(resilience_level=2, resilience={"zne_mitigation": True, "zne": {"noise_factors": [1, 3, 5]}})
    est = Estimator(mode=AerSimulator(), options=options)
    est.options.update(dynamical_decoupling={"enable": True, "sequence_type": "XpXm"})
    finalized = est.finalize_options()
    assert finalized.resilience.measure_mitigation
    assert finalized.resilience.zne_mitigation
    assert finalized.twirling.enable_measure
    assert finalized.twirling.enable_gates
    assert finalized.dynamical_decoupling.sequence_type == "XpXm"
    with pytest.raises(ValidationError):
        EstimatorOptions(resilience_level=3)


def test_aer_readout_noise_changes_known_classical_output():
    AerSimulator, Sampler, _ = runtime_stack()
    from qiskit_aer.noise import NoiseModel, ReadoutError
    noise = NoiseModel()
    noise.add_all_qubit_readout_error(ReadoutError([[0, 1], [1, 0]]))
    backend = AerSimulator(noise_model=noise)
    circuit = QuantumCircuit(1)
    circuit.measure_all()
    result = Sampler(mode=backend, options={"simulator": {"seed_simulator": 9}}).run([circuit], shots=32).result()[0]
    assert result.data.meas.get_counts() == {"1": 32}


def test_vqe_matches_tiny_exact_diagonalization():
    pytest.importorskip("qiskit_algorithms")
    from qiskit.circuit.library import efficient_su2
    from qiskit_algorithms import VQE
    from qiskit_algorithms.optimizers import SLSQP
    hamiltonian = SparsePauliOp.from_list([("ZI", 1), ("IZ", 1), ("XX", 0.2)])
    ansatz = efficient_su2(2, reps=1, entanglement="linear")
    vqe = VQE(StatevectorEstimator(), ansatz, SLSQP(maxiter=100), initial_point=[0.0] * ansatz.num_parameters)
    energy = float(vqe.compute_minimum_eigenvalue(hamiltonian).eigenvalue.real)
    assert energy == pytest.approx(np.linalg.eigvalsh(hamiltonian.to_matrix())[0], abs=1e-5)


def test_bloch_components_and_matplotlib_drawers(tmp_path):
    matplotlib = pytest.importorskip("matplotlib")
    pytest.importorskip("pylatexenc")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from qiskit.visualization import plot_bloch_vector, plot_histogram
    state = Statevector.from_label("+")
    bloch = [float(state.expectation_value(Pauli(axis)).real) for axis in "XYZ"]
    np.testing.assert_allclose(bloch, [1, 0, 0], atol=1e-12)
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    assert "H" in str(circuit.draw(output="text"))
    figures = [plot_bloch_vector(bloch), circuit.draw(output="mpl", style="iqp"), plot_histogram({"00": 16, "11": 16})]
    for index, figure in enumerate(figures):
        destination = tmp_path / f"plot-{index}.svg"
        figure.savefig(destination)
        assert "<svg" in destination.read_text()
        plt.close(figure)
