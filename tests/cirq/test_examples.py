"""Execute documented local circuits and check scientific invariants.

Cloud submission blocks are deliberately excluded; no provider credentials are needed.
"""
from pathlib import Path
import re

import pytest

cirq = pytest.importorskip("cirq")
np = pytest.importorskip("numpy")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "cirq"


def blocks(reference):
    text = (SKILL_ROOT / "references" / reference).read_text()
    return re.findall(r"```python\n(.*?)```", text, flags=re.S)


def execute(reference, indices=None, namespace=None):
    namespace = {} if namespace is None else namespace
    for index, code in enumerate(blocks(reference)):
        if indices is None or index in indices:
            exec(compile(code, f"{reference}:block{index}", "exec"), namespace)
    return namespace


@pytest.fixture(scope="module")
def noise():
    return execute("noise.md")


@pytest.fixture(scope="module")
def experiments():
    return execute("experiments.md")


def test_simulation_examples():
    pytest.importorskip("cirq_google")
    ns = execute("simulation.md")
    assert sum(ns["virtual_result"].histogram(key="result").values()) == 100
    np.testing.assert_allclose(ns["reduced"], np.eye(2) / 2)


def test_transformation_examples():
    pytest.importorskip("cirq_google")
    ns = execute("transformation.md")
    # Several independent matrices expose phase/sign mistakes hidden by Bell histograms.
    for seed in range(3):
        unitary = cirq.testing.random_unitary(4, random_state=seed)
        compiled = ns["compile_two_qubit_unitary"](unitary, cirq.LineQubit.range(2))
        cirq.testing.assert_allclose_up_to_global_phase(unitary, cirq.unitary(compiled), atol=1e-7)
    q = cirq.LineQubit(0)
    fractional = cirq.Circuit(cirq.H(q)**0.5)
    assert ns["HToZRy"]()(fractional) == fractional


def test_building_examples():
    pytest.importorskip("ply")
    ns = execute("building.md")
    for n in (2, 3, 4):
        qubits = cirq.LineQubit.range(n)
        cirq.testing.assert_allclose_up_to_global_phase(
            cirq.unitary(ns["qft_circuit"](qubits)), cirq.unitary(cirq.qft(*qubits)), atol=1e-7
        )
    qutrit = cirq.LineQid(0, dimension=3)
    cycle = cirq.Circuit(ns["QutritXGate"]()(qutrit))
    state = cirq.Simulator().simulate(cycle).final_state_vector
    np.testing.assert_allclose(state, [0, 1, 0])


def test_noise_examples(noise):
    assert len(noise["rb"].data) == 4
    assert np.isfinite(noise["xeb"])


@pytest.mark.parametrize("T1,T2,t", [(5, 3, 0.7), (5, 10, 1), (5, 3, 0)])
def test_thermal_population_and_coherence(noise, T1, T2, t):
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit(cirq.I(q)).with_noise(noise["ThermalNoise"](T1, T2, t))
    sim = cirq.DensityMatrixSimulator(dtype=np.complex128)
    excited = sim.simulate(circuit, initial_state=1).final_density_matrix
    np.testing.assert_allclose(excited[1, 1], np.exp(-t/T1), atol=1e-12)
    plus = sim.simulate(circuit, initial_state=np.array([1, 1])/np.sqrt(2)).final_density_matrix
    np.testing.assert_allclose(plus[0, 1], 0.5*np.exp(-t/T2), atol=1e-12)


@pytest.mark.parametrize("args", [(1, 3, 0.1), (0, 1, 0.1), (1, 1, -0.1)])
def test_thermal_rejects_unphysical_input(noise, args):
    with pytest.raises(ValueError):
        noise["ThermalNoise"](*args)


def test_readout_orientation_and_singular_matrix(noise):
    matrix = np.array([[0.95, 0.05], [0.3, 0.7]])
    truth = np.array([0.1, 0.9])
    corrected = noise["mitigate_readout_probabilities"](matrix.T @ truth, matrix)
    np.testing.assert_allclose(corrected, truth)
    with pytest.raises(ValueError):
        noise["mitigate_readout_probabilities"]([0.5, 0.5], np.full((2, 2), 0.5))


def test_zne_uses_zero_argument_not_asymptote(noise):
    x = np.linspace(0, 1, 8)
    y = 0.6*np.exp(-1.3*x) + 0.2
    extrapolated, _, _ = noise["extrapolate_exponential"](x, y)
    assert extrapolated == pytest.approx(0.8, abs=1e-7)


def test_experiment_examples(experiments):
    assert experiments["exact_ground"] == pytest.approx(-1)
    assert experiments["optimum"].fun == pytest.approx(-1, abs=1e-3)


def test_expectation_with_reversed_order(experiments):
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(cirq.X(q0), cirq.I(q1), cirq.measure(q0, q1))
    value = experiments["calculate_expectation_value"](circuit, cirq.Z(q0), cirq.Simulator(), [q1, q0])
    assert value == pytest.approx(-1)
    mid = cirq.Circuit(cirq.H(q0), cirq.measure(q0), cirq.X(q0))
    with pytest.raises(ValueError):
        experiments["calculate_expectation_value"](mid, cirq.Z(q0), cirq.Simulator(), [q0])


def test_qaoa_cost_unitary_and_node_mapping(experiments):
    import networkx as nx
    graph = nx.Graph([("a", "b"), ("b", "c")])
    gamma = 0.6
    circuit, nodes, qubits = experiments["qaoa_circuit"](graph, [gamma, 0], 1, measure=False)
    state = cirq.Simulator(dtype=np.complex128).simulate(circuit, qubit_order=qubits).final_state_vector
    costs = np.array([sum(bits[nodes.index(u)] != bits[nodes.index(v)] for u, v in graph.edges())
                      for bits in [cirq.big_endian_int_to_bits(i, bit_count=3) for i in range(8)]])
    expected = np.exp(-1j*gamma*costs) / np.sqrt(8)
    cirq.testing.assert_allclose_up_to_global_phase(state, expected, atol=1e-7)
    # Big-endian histogram index 4 means column 0 is one, cutting only edge a-b.
    result = cirq.ResultDict(measurements={"result": np.array([[1, 0, 0]], dtype=np.uint8)})
    assert experiments["mean_maxcut"](result, graph, nodes) == 1


@pytest.mark.parametrize("numerator", range(8))
def test_qpe_exact_binary_phases(experiments, numerator):
    circuit = experiments["qpe_circuit"](cirq.ZPowGate(exponent=numerator/4), cirq.X, 3)
    result = cirq.Simulator(seed=3).run(circuit, repetitions=20)
    assert result.histogram(key="phase") == {numerator: 20}


def test_local_provider_examples():
    pytest.importorskip("cirq_google")
    pytest.importorskip("cirq_aqt")
    pytest.importorskip("cirq_pasqal")
    # Only local blocks: preparation, selectors, AQT local, Pasqal local.
    ns = execute("hardware.md", indices={0, 1, 5, 7})
    assert sum(ns["aqt_result"].histogram(key="m").values()) == 100
    assert ns["pasqal_result"].histogram(key="result") == {2: 100}
    chosen = ns["select_connected_qubits"](ns["local_device"], 5)
    import networkx as nx
    assert nx.is_connected(ns["local_device"].metadata.nx_graph.subgraph(chosen))
    q = cirq.GridQubit(0, 0)
    calibration = {"single_qubit_rb_average_error_per_gate": {(q,): [0.02]}}
    assert ns["single_qubit_errors"](calibration) == {q: 0.02}


def test_skill_quickstart_and_templates():
    text = (SKILL_ROOT / "SKILL.md").read_text()
    namespace = {}
    for index, code in enumerate(re.findall(r"```python\n(.*?)```", text, flags=re.S)):
        exec(compile(code, f"SKILL.md:block{index}", "exec"), namespace)
    assert set(namespace["results"]) == {0.0, 0.001, 0.01, 0.05, 0.1}
    assert all(sum(row["histogram"].values()) == 1000 for row in namespace["results"].values())
