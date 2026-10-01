from pathlib import Path
import csv
import importlib.util
import json
import os
import zipfile

import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "tellurium"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
os.environ.setdefault("MPLBACKEND", "Agg")
np = pytest.importorskip("numpy")
te = pytest.importorskip("tellurium")
libsbml = pytest.importorskip("libsbml")
pytest.importorskip("libsedml")
pytest.importorskip("libcombine")
spec = importlib.util.spec_from_file_location("kinetic_experiment", SKILL_ROOT / "scripts" / "kinetic_experiment.py")
kinetics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kinetics)


def read_curve(path):
    with path.open() as handle:
        return np.asarray([[float(v) for v in row] for row in list(csv.reader(handle))[1:]])


def test_real_antimony_analytic_conservation_perturbation_and_archive(tmp_path):
    report = kinetics.run(SKILL_ROOT / "assets" / "first-order.ant", "antimony",
                          SKILL_ROOT / "assets" / "experiment.json", tmp_path / "result")
    assert report["sbml_validation_findings"] == []
    assert report["sedml_parse_findings"] == []
    for scenario, k in (("baseline", .2), ("double_k", .4)):
        values = read_curve(tmp_path / "result" / f"{scenario}.csv")
        np.testing.assert_allclose(values[:, 1], np.exp(-k * values[:, 0]), atol=2e-8, rtol=2e-8)
        np.testing.assert_allclose(values[:, 1] + values[:, 2], 1., atol=1e-10)
        assert report["archive_replay_max_absolute_difference"][scenario] < 1e-10
    with zipfile.ZipFile(tmp_path / "result" / "experiment.omex") as archive:
        assert {"model_baseline.xml", "model_double_k.xml", "experiment.sedml", "manifest.xml"} <= set(archive.namelist())
    assert report["units"]["time"] == "second"
    assert "litre (exponent = -1" in report["units"]["species"]["A"]


def test_sbml_input_and_independent_conditions(tmp_path):
    source = tmp_path / "model.xml"
    source.write_text(te.antimonyToSBML((SKILL_ROOT / "assets" / "first-order.ant").read_text()))
    config = json.loads((SKILL_ROOT / "assets" / "experiment.json").read_text())
    config["scenarios"] = {"double_k": {"k": .4}, "baseline": {}}
    experiment = tmp_path / "experiment.json"; experiment.write_text(json.dumps(config))
    kinetics.run(source, "sbml", experiment, tmp_path / "result")
    baseline = read_curve(tmp_path / "result" / "baseline.csv")
    assert baseline[-1, 1] == pytest.approx(np.exp(-2), rel=1e-7)


def test_preserve_unit_warnings_and_reject_invalid_model(tmp_path):
    source = tmp_path / "unitless.ant"
    source.write_text("model unitless()\nA -> B; k*A; A=1; B=0; k=0.2; end")
    _, issues = kinetics.model_document(source, "antimony")
    assert issues and any("unit" in issue["message"].lower() for issue in issues)
    source.write_text("<not_sbml />")
    with pytest.raises(ValueError, match="no SBML"):
        kinetics.model_document(source, "sbml")


def test_reject_unknown_or_amount_species_and_bad_parameter():
    document, _ = kinetics.model_document(SKILL_ROOT / "assets" / "first-order.ant", "antimony")
    config = json.loads((SKILL_ROOT / "assets" / "experiment.json").read_text())
    config["scenarios"]["bad"] = {"A": .2}
    with pytest.raises(ValueError, match="constant global"):
        kinetics.validate_experiment(config, document.getModel())
    config["scenarios"].pop("bad")
    document.getModel().getSpecies("A").setHasOnlySubstanceUnits(True)
    with pytest.raises(ValueError, match="amount-only"):
        kinetics.validate_experiment(config, document.getModel())
    document.getModel().getSpecies("A").setHasOnlySubstanceUnits(False)
    config["points"] = 1
    with pytest.raises(ValueError, match="points"):
        kinetics.validate_experiment(config, document.getModel())
