import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
import skill_contract

np = pytest.importorskip("numpy")
ct = pytest.importorskip("cantera")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "cantera"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
spec = importlib.util.spec_from_file_location("cantera_ignition", SKILL_ROOT / "scripts" / "ignition_delay.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def config():
    return json.loads((SKILL_ROOT / "assets" / "hydrogen-ignition.json").read_text())


@pytest.mark.parametrize("reactor,equilibrium_constraint", [("constant-volume", "UV"), ("constant-pressure", "HP")])
def test_hydrogen_ignition_conservation_and_independent_equilibrium(reactor, equilibrium_constraint):
    conditions = config()
    conditions["reactor"] = reactor
    history, report = module.simulate(conditions)
    assert report["status"] == "resolved"
    assert report["conservation"]["passed"]
    assert report["conservation"]["element_mass_fraction_absolute_drift"] < 1e-10
    equilibrium = module.load_gas(conditions)
    equilibrium.equilibrate(equilibrium_constraint)
    assert history[-1, 1] == pytest.approx(equilibrium.T, abs=0.02)
    if reactor == "constant-volume":
        assert report["delay_s"] == pytest.approx(0.000313, abs=2e-6)
        assert history[:, 3] == pytest.approx(np.ones(len(history)))
    else:
        assert history[:, 2] == pytest.approx(np.full(len(history), conditions["pressure_pa"]), rel=1e-8)


def test_unreached_ignition_is_not_a_reported_delay():
    conditions = config()
    conditions.update(temperature_k=500, end_time_s=0.001, samples=101)
    _, report = module.simulate(conditions)
    assert report["delay_s"] is None
    assert report["status"] == "temperature-rise-not-reached"


def test_boundary_maximum_is_unresolved():
    times = np.linspace(0, 1, 21)
    report = module.delay_from_history(times, 1000 + 500 * times**3, 200)
    assert report["delay_s"] is None
    assert report["status"] == "derivative-maximum-at-boundary"


@pytest.mark.parametrize("change", [{"pressure_pa": -1}, {"samples": 3},
                                      {"mole_amounts": {"H2": -1}}, {"mole_amounts": {"H2": 0}},
                                      {"mole_amounts": {"NOT_A_SPECIES": 1}}, {"rtol": float("nan")}])
def test_invalid_conditions_rejected(change):
    conditions = config()
    conditions.update(change)
    with pytest.raises(ValueError):
        module.simulate(conditions)


def test_cli_refinement_provenance_and_replay(tmp_path):
    path = SKILL_ROOT / "assets" / "hydrogen-ignition.json"
    command = [sys.executable, str(SKILL_ROOT / "scripts" / "ignition_delay.py"), str(path), str(tmp_path / "run")]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    out = tmp_path / "run"
    report = json.loads((out / "report.json").read_text())
    assert report["numerically_resolved"]
    assert set(report["delay_relative_changes"]) == {"finer_output", "tighter_solver", "longer_horizon"}
    assert all(delta <= 0.01 for delta in report["delay_relative_changes"].values())
    assert report["mechanism"]["snapshot_sha256"] == hashlib.sha256((out / "mechanism.yaml").read_bytes()).hexdigest()
    original = module.load_gas(config())
    replay = ct.Solution(str(out / "mechanism.yaml"), "ohmech")
    np.testing.assert_allclose(replay.forward_rate_constants, original.forward_rate_constants, rtol=1e-12)
    assert len((out / "baseline.csv").read_text().splitlines()) == 3002
    assert subprocess.run(command, capture_output=True, text=True, timeout=60).returncode != 0
