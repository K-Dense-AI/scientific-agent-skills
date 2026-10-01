import hashlib
import importlib.util
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
    assert subprocess.run(command, capture_output=True, text=True, timeout=120).returncode != 0
