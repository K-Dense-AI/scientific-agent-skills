"""Execute documented circuits and check independent numerical invariants."""
from pathlib import Path
import re
import runpy

import pytest

qml = pytest.importorskip("pennylane")
import numpy as np

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pennylane"


def blocks(path):
    return re.findall(r"```python\n(.*?)```", (SKILL_ROOT / path).read_text(), re.S)


def run_blocks(tmp_path, path, indices=None):
    snippets = blocks(path)
    if indices is not None:
        snippets = [snippets[i] for i in indices]
    script = tmp_path / "documented_example.py"
    script.write_text("\n\n".join(snippets))
    return runpy.run_path(str(script))


def test_quick_start_analytic_gradient_and_minimum(tmp_path):
    result = run_blocks(tmp_path, "SKILL.md")
    assert result["final_energy"] == pytest.approx(-1.0, abs=1e-6)


@pytest.mark.parametrize("index", range(3))
def test_getting_started_values_samples_broadcasting_and_rng(tmp_path, index):
    run_blocks(tmp_path, "references/getting_started.md", [index])


@pytest.mark.parametrize("index", range(4))
def test_circuit_controls_feedback_qft_and_transforms(tmp_path, index):
    run_blocks(tmp_path, "references/quantum_circuits.md", [index])


@pytest.mark.parametrize("index", range(4))
def test_optimization_gradients_spsa_qaoa_and_qubo(tmp_path, index):
    run_blocks(tmp_path, "references/optimization.md", [index])


def test_qubo_nonsymmetric_and_three_variable_objectives(tmp_path):
    result = run_blocks(tmp_path, "references/optimization.md", [3])
    fn = result["qubo_hamiltonian"]
    Q = np.array([[1, -3, 2], [4, 0.5, 6], [-1, 0, -2]])
    H = fn(Q)
    diag = np.diag(qml.matrix(H, wire_order=range(3)))
    for i in range(8):
        x = np.array([int(bit) for bit in f"{i:03b}"])
        assert diag[i] == pytest.approx(x @ Q @ x)
    for bad in [[], [[1, 2]], [[float("nan")]], [[float("inf")]]]:
        with pytest.raises(ValueError):
            fn(bad)


def test_h2_uccsd_sector_reference_and_dipole(tmp_path):
    result = run_blocks(tmp_path, "references/quantum_chemistry.md")
    assert result["n_qubits"] == 4
    assert result["reference_energy"] == pytest.approx(-1.136, abs=0.002)
    assert result["final_energy"] < result["hf_energy"] - 0.01
    assert np.allclose(result["mu_au"], 0, atol=1e-6)


def test_coordinate_units_define_same_hamiltonian():
    coords = qml.numpy.array([[0, 0, 0], [0, 0, 1.4]], requires_grad=False)
    bohr = qml.qchem.Molecule(["H", "H"], coords, unit="bohr")
    angstrom = qml.qchem.Molecule(["H", "H"], coords * 0.529177210903, unit="angstrom")
    H1, n = qml.qchem.molecular_hamiltonian(bohr)
    H2, _ = qml.qchem.molecular_hamiltonian(angstrom)
    assert np.allclose(qml.matrix(H1, wire_order=range(n)), qml.matrix(H2, wire_order=range(n)), atol=1e-8)


def test_torch_batch_and_gradients(tmp_path):
    pytest.importorskip("torch")
    result = run_blocks(tmp_path, "references/quantum_ml.md", [0])
    assert result["layer"].weights.grad.norm() > 0


def test_jax_vectorized_loss_and_gradients(tmp_path):
    pytest.importorskip("jax")
    run_blocks(tmp_path, "references/quantum_ml.md", [1])


def test_autograd_classifier_finite_loss_gradient(tmp_path):
    run_blocks(tmp_path, "references/quantum_ml.md", [2])


@pytest.mark.parametrize("index", [0, 1, 4])
def test_templates_noise_and_single_bit_flip_recovery(tmp_path, index):
    run_blocks(tmp_path, "references/advanced_features.md", [index])


def test_pulse_evolution_and_infidelity_gradient(tmp_path):
    pytest.importorskip("jax")
    result = run_blocks(tmp_path, "references/advanced_features.md", [2])
    assert result["grad"][0] == pytest.approx(-np.pi * np.sin(2 * np.pi * 0.4), abs=1e-6)


def test_local_backends_match_analytic_value_and_gradient(tmp_path):
    run_blocks(tmp_path, "references/devices_backends.md", [0])
