import hashlib
import importlib.util
from importlib.resources import files
import json
from pathlib import Path
import subprocess
import sys

import pytest
import skill_contract

np = pytest.importorskip("numpy")
pc = pytest.importorskip("pycalphad")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pycalphad"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
spec = importlib.util.spec_from_file_location("pycalphad_equilibrate", SKILL_ROOT / "scripts" / "equilibrate.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DATABASE = SKILL_ROOT / "assets" / "ideal-cu-ni.tdb"


def settings():
    return json.loads((SKILL_ROOT / "assets" / "equilibrium.json").read_text())


def test_analytic_tie_line_lever_rule_and_gibbs_energy():
    config = settings()
    config["temperatures_k"] = [1100.0]
    config["independent_mole_fractions"] = {"NI": 0.49}
    report = module.calculate(pc.Database(str(DATABASE)), config)
    assert report["all_checks_passed"]
    result = report["points"][0]["baseline"]
    phases = {vertex["phase"]: vertex for vertex in result["vertices"]}
    # Independent common-tangent solution for the original ideal model.
    rt = 8.3145 * 1100  # Gas constant used by pycalphad's thermodynamic models.
    x_liquid = 1 / (1 + np.exp(1000 / rt))
    x_solid = 1 - x_liquid
    solid_fraction = (0.49 - x_liquid) / (x_solid - x_liquid)
    assert phases["LIQUID"]["mole_fractions"]["NI"] == pytest.approx(x_liquid, abs=1e-7)
    assert phases["FCC_A1"]["mole_fractions"]["NI"] == pytest.approx(x_solid, abs=1e-7)
    assert phases["FCC_A1"]["mole_phase_fraction"] == pytest.approx(solid_fraction, abs=1e-6)
    mixing = lambda x: rt * (x * np.log(x) + (1 - x) * np.log(1 - x))
    expected_gm = solid_fraction * mixing(x_solid) + (1 - solid_fraction) * (mixing(x_liquid) - 1000 + 2000 * x_liquid)
    assert result["gibbs_energy_j_per_mol"] == pytest.approx(expected_gm, abs=1e-4)
    assert result["mass_balance_absolute_error"] < 1e-8


def test_single_phase_limits_and_refinement():
    config = settings()
    report = module.calculate(pc.Database(str(DATABASE)), config)
    assert report["all_checks_passed"]
    low, middle, high = [r["baseline"] for r in report["points"]]
    assert low["phase_totals"]["FCC_A1"] == pytest.approx(1)
    assert high["phase_totals"]["LIQUID"] == pytest.approx(1)
    assert middle["phase_totals"]["LIQUID"] == pytest.approx(0.5, abs=1e-6)


def test_miscibility_gap_preserves_distinct_same_phase_vertices():
    # Original regular-solution perturbation produces FCC/FCC separation.
    db = pc.Database(DATABASE.read_text() + "\nPARAMETER L(FCC_A1,CU,NI;0) 298.15 30000; 2000 N !\n")
    config = settings()
    config.update(phases=["FCC_A1"], temperatures_k=[900.0])
    report = module.calculate(db, config)
    result = report["points"][0]["baseline"]
    assert report["all_checks_passed"]
    vertices = result["vertices"]
    assert len(vertices) == 2
    assert {p["phase"] for p in vertices} == {"FCC_A1"}
    assert vertices[0]["mole_fractions"]["NI"] != pytest.approx(vertices[1]["mole_fractions"]["NI"])
    for vertex in vertices:
        x = vertex["mole_fractions"]["NI"]
        assert abs(8.3145 * 900 * np.log(x / (1 - x)) + 30000 * (1 - 2 * x)) < 0.1
        assert vertex["mole_phase_fraction"] == pytest.approx(0.5, abs=1e-6)


@pytest.mark.parametrize("change", [{"composition_basis": "mass_fraction"},
                                      {"independent_mole_fractions": {"NI": 1.1}},
                                      {"independent_mole_fractions": {"NI": 0.5, "CU": 0.5}},
                                      {"phases": ["UNKNOWN"]}, {"components": ["CU", "NI", "FE"]},
                                      {"temperatures_k": [2500]}, {"pressure_pa": -1},
                                      {"dependent_component": "VA"}, {"temperatures_k": [float("nan")]}])
def test_invalid_scientific_conditions_rejected(change):
    config = settings()
    config.update(change)
    with pytest.raises(ValueError):
        module.calculate(pc.Database(str(DATABASE)), config)


def test_cli_exports_both_density_runs_and_hashes(tmp_path):
    command = [sys.executable, str(SKILL_ROOT / "scripts" / "equilibrate.py"), str(DATABASE),
               str(SKILL_ROOT / "assets" / "equilibrium.json"), str(tmp_path / "result")]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "result" / "report.json").read_text())
    assert report["all_checks_passed"]
    assert report["database_sha256"] == hashlib.sha256(DATABASE.read_bytes()).hexdigest()
    csv = (tmp_path / "result" / "phase-equilibria.csv").read_text()
    assert "baseline" in csv and "refined" in csv
    assert report["phase_fraction_basis"].startswith("molar")
    assert report["database_experimental_validity"] == "not_evaluated_by_helper"
    assert subprocess.run(command, capture_output=True, text=True, timeout=120).returncode != 0


@pytest.mark.parametrize("x", [0.0, 1.0])
def test_endpoint_clipping_is_reported_without_replacing_requested_composition(x):
    config = settings()
    config.update(temperatures_k=[900.0], independent_mole_fractions={"NI": x},
                  mass_balance_tolerance=1e-12)
    report = module.calculate(pc.Database(str(DATABASE)), config)
    point = report["points"][0]["baseline"]
    assert report["bulk_mole_fractions"]["NI"] == x
    imposed = min(max(x, 1e-10), 1 - 1e-10)
    assert point["solver_bulk_mole_fractions"]["NI"] == imposed
    assert sum(point["solver_bulk_mole_fractions"].values()) == pytest.approx(1)
    assert point["composition_condition_adjustment_absolute_error"] == pytest.approx(1e-10, abs=1e-16)
    assert point["reconstructed_bulk_mole_fractions"]["NI"] == pytest.approx(imposed, abs=1e-13)
    assert not point["balance_passed"]
    assert not report["all_checks_passed"]


def test_model_sampling_and_workspace_have_distinct_consistent_energy_contracts():
    db = pc.Database(str(DATABASE))
    config = settings()
    model = pc.Model(db, config["components"], "FCC_A1")
    conditions = {module.v.T: 900, module.v.P: 101325, module.v.N: 1, module.v.X("NI"): 0.5}
    wks = pc.Workspace(db, config["components"], config["phases"], conditions)
    substitution = {module.v.T: 900, **{sf: 0.5 for sf in model.site_fractions}}
    gm_symbolic = float(model.GM.subs(substitution))
    sampled = pc.calculate(db, config["components"], ["FCC_A1"], T=900, P=101325,
                           N=1, points=[[0.5, 0.5]], output="GM")
    expected = -8.3145 * 900 * np.log(2)
    assert gm_symbolic == pytest.approx(expected, abs=1e-8)
    assert sampled.GM.values.item() == pytest.approx(expected, abs=1e-8)
    assert wks.get("GM").item() == pytest.approx(expected, abs=1e-8)
    assert wks.get("HM").item() == pytest.approx(0, abs=1e-8)
    assert wks.get("SM").item() == pytest.approx(8.3145 * np.log(2), abs=1e-8)
    assert np.isnan(wks.get("NP(LIQUID)").item())


def test_equilibrium_enthalpy_derivative_is_not_fixed_constitution_heat_capacity():
    config = settings()
    delta = 1e-3
    wks = pc.Workspace(pc.Database(str(DATABASE)), config["components"], config["phases"],
                       {module.v.T: [1100 - delta, 1100, 1100 + delta], module.v.P: 101325,
                        module.v.N: 1, module.v.X("NI"): 0.5})
    enthalpies = wks.get("HM")
    difference = (enthalpies[2] - enthalpies[0]) / (2 * delta)
    derivative = wks.get("HM.T")[1]
    assert derivative == pytest.approx(difference, rel=1e-5)
    assert derivative > 1000  # Phase fractions change strongly inside the narrow lens.
    assert np.allclose(wks.get("CPM"), 0)


def test_workspace_expands_same_phase_composition_sets():
    db = pc.Database(DATABASE.read_text() + "\nPARAMETER L(FCC_A1,CU,NI;0) 298.15 30000; 2000 N !\n")
    wks = pc.Workspace(db, settings()["components"], ["FCC_A1"],
                       {module.v.T: 900, module.v.P: 101325, module.v.N: 1, module.v.X("NI"): 0.5})
    amounts = wks.get_dict("NP(FCC_A1)")
    compositions = wks.get_dict("X(FCC_A1,NI)")
    assert len(amounts) == len(compositions) == 2
    assert all("#" in str(key) for key in amounts)
    assert sum(a.item() for a in amounts.values()) == pytest.approx(1)
    endpoints = sorted(x.item() for x in compositions.values())
    assert endpoints[0] < 0.03 and endpoints[1] > 0.97
    assert isinstance(wks.get("X(FCC_A1,NI)"), list)


def test_mass_fraction_conversion_uses_tdb_masses():
    db = pc.Database(str(DATABASE))
    converted = module.v.get_mole_fractions({module.v.W("NI"): 0.5}, "CU", db)
    expected = (0.5 / 58.6934) / (0.5 / 58.6934 + 0.5 / 63.546)
    assert converted[module.v.X("NI")] == pytest.approx(expected, abs=1e-12)


def test_released_alni_database_order_disorder_selection_and_equilibrium():
    # Upstream release fixture, not a proprietary or newly redistributed database.
    db = pc.Database(files("pycalphad.tests.databases").joinpath("alni_dupin_2001.tdb").read_text())
    config = settings()
    config.update(components=["AL", "NI", "VA"], phases=["FCC_A1", "FCC_L12"],
                  dependent_component="NI", independent_mole_fractions={"AL": 0.25},
                  temperatures_k=[1000.0], database_temperature_range_k=None)
    with pytest.raises(ValueError, match="order-disorder-filtered"):
        module.calculate(db, config)
    config["phases"] = ["AL3NI1", "AL3NI2", "AL3NI5", "BCC_B2", "FCC_L12", "LIQUID"]
    report = module.calculate(db, config)
    point = report["points"][0]["baseline"]
    assert report["all_checks_passed"]
    assert point["phase_totals"]["FCC_L12"] == pytest.approx(1)
    assert point["reconstructed_bulk_mole_fractions"]["AL"] == pytest.approx(0.25, abs=1e-8)
    liquid_only = dict(config, phases=["LIQUID"])
    liquid = module.calculate(db, liquid_only)["points"][0]["baseline"]
    assert point["gibbs_energy_j_per_mol"] < liquid["gibbs_energy_j_per_mol"]
