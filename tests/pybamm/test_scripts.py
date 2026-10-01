from pathlib import Path
import copy
import csv
import importlib.util
import json
import os

import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pybamm"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
os.environ["PYBAMM_DISABLE_TELEMETRY"] = "true"
np = pytest.importorskip("numpy")
pytest.importorskip("pybamm")
spec = importlib.util.spec_from_file_location("simulate_battery", SKILL_ROOT / "scripts" / "simulate_battery.py")
battery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(battery)


@pytest.fixture
def protocol():
    return json.loads((SKILL_ROOT / "assets" / "chen2020-protocol.json").read_text())


def test_real_charge_discharge_and_numerical_studies(protocol, tmp_path):
    source = tmp_path / "protocol.json"
    source.write_text(json.dumps(protocol))
    reference = Path(__file__).resolve().parent / "fixtures" / "chen2020-reference.csv"
    report = battery.run(source, tmp_path / "result", measured=reference)
    assert report["nominal_capacity_Ah"] == 5.0
    assert report["solver_sensitivity"]["max_voltage_difference_V"] < 1e-4
    assert report["mesh_sensitivity"]["max_voltage_difference_V"] < .003
    assert report["measurement_comparison"]["rmse_V"] < .003
    assert report["measurement_comparison"]["current_rmse_A"] < 1e-9
    with (tmp_path / "result" / "curve.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    discharge_end = next(r for r in reversed(rows) if r["step"] == "0")
    assert float(discharge_end["net_discharge_capacity_Ah"]) == pytest.approx(2.5 * 600 / 3600, abs=1e-8)
    assert float(rows[-1]["net_discharge_capacity_Ah"]) == pytest.approx(0, abs=1e-8)
    assert {float(r["current_A"]) for r in rows} == {-2.5, 0., 2.5}
    assert all(2.5 < float(r["voltage_V"]) < 4.2 for r in rows)
    assert report["terminations"][-1]["end_s"] == pytest.approx(1320)


def test_real_dfn_and_voltage_termination(protocol):
    protocol["model"] = "DFN"
    protocol["steps"] = [{"kind": "discharge", "c_rate": .5, "duration_s": 600, "until_voltage_V": 3.9}]
    result = battery.solve_protocol(protocol)
    assert 0 < result["terminations"][0]["end_s"] < 600
    assert result["rows"][-1][2] == pytest.approx(3.9, abs=1e-5)
    assert "Voltage" in result["terminations"][0]["termination"] or "voltage" in result["terminations"][0]["termination"]
    duration = result["terminations"][0]["end_s"]
    assert result["rows"][-1][4] == pytest.approx(2.5 * duration / 3600, abs=1e-7)


@pytest.mark.parametrize("change", [
    {"initial_soc": 1.1}, {"temperature_K": 0}, {"sample_period_s": float("nan")},
    {"cycles": 5}, {"model": "unknown"}, {"steps": [{"kind": "rest", "duration_s": 2, "c_rate": 1}]},
])
def test_reject_bad_protocol(protocol, change):
    protocol.update(change)
    with pytest.raises(ValueError):
        battery.validate_protocol(protocol)


def test_unknown_parameter_and_out_of_range_reference(protocol, tmp_path):
    protocol["parameter_overrides"] = {"misspelled conductivity": 1.}
    with pytest.raises(ValueError, match="Unknown parameter"):
        battery.solve_protocol(protocol)
    bad = tmp_path / "outside.csv"
    bad.write_text("time_s,voltage_V,current_A\n0,4,1\n11,4,1\n")
    with pytest.raises(ValueError, match="no extrapolation"):
        battery.compare_measurement([(0, 0., 4., 1., 0.), (0, 10., 3.9, 1., .01)], bad, tmp_path / "residuals.csv")


def test_detect_global_limit_before_requested_duration(protocol):
    protocol["steps"] = [{"kind": "discharge", "c_rate": 1., "duration_s": 14400.}]
    with pytest.raises(RuntimeError, match="ended before"):
        battery.solve_protocol(protocol)
