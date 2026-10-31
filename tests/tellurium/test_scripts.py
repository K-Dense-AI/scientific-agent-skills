from pathlib import Path
import csv
import importlib.util
import json
import os
import io
import xml.etree.ElementTree as ET
import zipfile

import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "tellurium"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
os.environ.setdefault("MPLBACKEND", "Agg")
np = pytest.importorskip("numpy")
te = pytest.importorskip("tellurium")
libsbml = pytest.importorskip("libsbml")
libsedml = pytest.importorskip("libsedml")
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
        np.testing.assert_allclose(values[:, 0], np.linspace(0., 10., 101), atol=1e-12, rtol=0.)
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


def test_archive_xpath_namespace_and_solver_semantics(tmp_path):
    output = tmp_path / "result"
    kinetics.run(SKILL_ROOT / "assets" / "first-order.ant", "antimony",
                 SKILL_ROOT / "assets" / "experiment.json", output)
    content = (output / "experiment.sedml").read_bytes()
    # iterparse emits (event, (prefix, URI)) pairs.
    ns = dict(pair for _, pair in ET.iterparse(io.BytesIO(content), events=["start-ns"]))
    assert ns["sbml"] == "http://www.sbml.org/sbml/level3/version2/core"
    sed = libsedml.readSedMLFromString(content.decode())
    algorithm = sed.getSimulation(0).getAlgorithm()
    parameters = {p.getKisaoID(): p.getValue() for p in algorithm.getListOfAlgorithmParameters()}
    assert parameters["KISAO:0000571"] == "1e-12"
    assert parameters["KISAO:0000671"] == "true"
    assert parameters["KISAO:0000656"] == "false"
    assert "KISAO:0000211" not in parameters
    for dg in sed.getListOfDataGenerators():
        variable = dg.getVariable(0)
        if variable.isSetTarget():
            task = sed.getTask(variable.getTaskReference())
            model = sed.getModel(task.getModelReference())
            tree = ET.parse(output / model.getSource())
            xpath = variable.getTarget().replace("/sbml:sbml/", "./", 1)
            matches = tree.findall(xpath, ns)
            assert len(matches) == 1 and matches[0].get("id") in {"A", "B"}


def test_nonunit_volume_initial_amount_and_scaled_tolerance(tmp_path):
    document, _ = kinetics.model_document(SKILL_ROOT / "assets" / "first-order.ant", "antimony")
    model = document.getModel()
    model.getCompartment("cell").setSize(5.)
    model.getSpecies("A").setInitialAmount(10.)
    source = tmp_path / "model.xml"
    source.write_text(libsbml.writeSBMLToString(document))
    report = kinetics.run(source, "sbml", SKILL_ROOT / "assets" / "experiment.json", tmp_path / "result")
    for scenario, k in (("baseline", .2), ("double_k", .4)):
        values = read_curve(tmp_path / "result" / f"{scenario}.csv")
        np.testing.assert_allclose(values[:, 1], 2 * np.exp(-k * values[:, 0]), rtol=2e-8, atol=2e-8)
        np.testing.assert_allclose(5 * (values[:, 1] + values[:, 2]), 10., atol=1e-9)
        assert report["initial_state_absolute_tolerances"][scenario] == pytest.approx({"A": 1e-11, "B": 5e-12})


@pytest.mark.parametrize("changes", [
    {"species": "AB"}, {"species": {"A": 1}}, {"species": ["A", 2]}, {"species": [[]]},
    {"species": ["A", "A"]}, {"species": []}, {"species": ["missing"]},
    {"points": True}, {"points": 2.5}, {"end_time": float("nan")}, {"absolute_tolerance": 0},
    {"scenarios": {"baseline": {}, "bad/path": {}}}, {"scenarios": {"baseline": {}, 5: {}}},
    {"scenarios": {"baseline": {"k": 1}}}, {"scenarios": {"baseline": {}, "bad": {"k": True}}},
    {"scenarios": {"baseline": {}, "bad": {2: 1}}},
])
def test_reject_malformed_experiments(changes):
    document, _ = kinetics.model_document(SKILL_ROOT / "assets" / "first-order.ant", "antimony")
    config = json.loads((SKILL_ROOT / "assets" / "experiment.json").read_text())
    config.update(changes)
    with pytest.raises(ValueError):
        kinetics.validate_experiment(config, document.getModel())


@pytest.mark.parametrize("config", [None, [], "experiment", 2])
def test_require_config_object(config):
    with pytest.raises(ValueError, match="requires exactly"):
        kinetics.validate_experiment(config, None)


def test_duplicate_json_key_rejected_before_output(tmp_path):
    source = tmp_path / "experiment.json"
    source.write_text('{"scenarios": {"baseline": {}, "baseline": {"k": 9}}}')
    with pytest.raises(ValueError, match="Duplicate JSON key: baseline"):
        kinetics.run(SKILL_ROOT / "assets" / "first-order.ant", "antimony", source, tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_initial_assignment_cannot_be_overridden():
    document, _ = kinetics.model_document(SKILL_ROOT / "assets" / "first-order.ant", "antimony")
    assignment = document.getModel().createInitialAssignment()
    assignment.setSymbol("k"); assignment.setMath(libsbml.parseL3Formula("0.3"))
    config = json.loads((SKILL_ROOT / "assets" / "experiment.json").read_text())
    with pytest.raises(ValueError, match="initial assignment"):
        kinetics.validate_experiment(config, document.getModel())


def test_existing_output_is_preserved(tmp_path):
    output = tmp_path / "result"; output.mkdir()
    marker = output / "keep.txt"; marker.write_text("existing data")
    with pytest.raises(FileExistsError):
        kinetics.run(SKILL_ROOT / "assets" / "first-order.ant", "antimony",
                     SKILL_ROOT / "assets" / "experiment.json", output)
    assert marker.read_text() == "existing data"


def test_species_named_time_is_distinct_from_time_symbol():
    config = json.loads((SKILL_ROOT / "assets" / "experiment.json").read_text())
    config["species"] = ["time"]
    sed = kinetics.make_sedml(config, ["baseline"], "http://www.sbml.org/sbml/level3/version2/core")
    assert sed.getDataGenerator("dg_baseline_0").getVariable(0).getSymbol() == "urn:sedml:symbol:time"
    variable = sed.getDataGenerator("dg_baseline_1").getVariable(0)
    assert not variable.isSetSymbol() and variable.getTarget().endswith("[@id='time']")


def test_rate_rules_and_zero_dimensional_concentrations_rejected():
    document, _ = kinetics.model_document(SKILL_ROOT / "assets" / "first-order.ant", "antimony")
    model = document.getModel()
    config = json.loads((SKILL_ROOT / "assets" / "experiment.json").read_text())
    model.getCompartment("cell").setSpatialDimensions(0)
    with pytest.raises(ValueError, match="spatial dimensions"):
        kinetics.validate_experiment(config, model)
    model.getCompartment("cell").setSpatialDimensions(3)
    rule = model.createRateRule(); rule.setVariable("k"); rule.setMath(libsbml.parseL3Formula("0.1"))
    with pytest.raises(ValueError, match="Rate-rule"):
        kinetics.validate_experiment(config, model)


def test_sbml_level2_namespace_and_replay(tmp_path):
    document, _ = kinetics.model_document(SKILL_ROOT / "assets" / "first-order.ant", "antimony")
    assert document.setLevelAndVersion(2, 4)
    source = tmp_path / "level2.xml"; source.write_text(libsbml.writeSBMLToString(document))
    output = tmp_path / "result"
    report = kinetics.run(source, "sbml", SKILL_ROOT / "assets" / "experiment.json", output)
    sed = libsedml.readSedMLFromFile(str(output / "experiment.sedml"))
    assert sed.getNamespaces().getURI("sbml") == "http://www.sbml.org/sbml/level2/version4"
    assert report["archive_replay_max_absolute_difference"]["baseline"] < 1e-10
