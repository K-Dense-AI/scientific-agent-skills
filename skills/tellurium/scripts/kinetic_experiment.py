"""Simulate local SBML/Antimony models and verify replay of a generated COMBINE archive."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re


def model_document(path, model_format):
    import libsbml
    import tellurium as te
    source = Path(path).read_text()
    sbml = te.antimonyToSBML(source) if model_format == "antimony" else source
    document = libsbml.readSBMLFromString(sbml)
    if document.getModel() is None:
        raise ValueError("Input has no SBML model")
    document.checkConsistency()
    issues = [{"id": document.getError(i).getErrorId(), "severity": document.getError(i).getSeverityAsString(),
               "message": document.getError(i).getMessage().strip()} for i in range(document.getNumErrors())]
    if any(issue["severity"] in {"Error", "Fatal"} for issue in issues):
        raise ValueError("SBML validation errors: " + json.dumps(issues))
    return document, issues


def validate_experiment(config, model):
    allowed = {"end_time", "points", "relative_tolerance", "absolute_tolerance", "species", "scenarios"}
    if set(config) != allowed:
        raise ValueError(f"Experiment requires exactly {sorted(allowed)}")
    for name in ("end_time", "relative_tolerance", "absolute_tolerance"):
        value = config[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be positive and finite")
    if isinstance(config["points"], bool) or not isinstance(config["points"], int) or config["points"] < 2:
        raise ValueError("points must be an integer >=2 (including both endpoints)")
    species = config["species"]
    if not species or len(set(species)) != len(species) or any(model.getSpecies(s) is None for s in species):
        raise ValueError("species must contain unique SBML species IDs")
    # SED-ML species targets below use SBML concentration semantics.
    if any(model.getSpecies(s).getHasOnlySubstanceUnits() for s in species):
        raise ValueError("This archive workflow selects concentrations; amount-only species need an explicit amount workflow")
    scenarios = config["scenarios"]
    if not isinstance(scenarios, dict) or scenarios.get("baseline") != {}:
        raise ValueError("scenarios must include an unchanged baseline mapping")
    for name, changes in scenarios.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) or not isinstance(changes, dict):
            raise ValueError("Scenario names must be SBML-style identifiers and changes must be a mapping")
        for symbol, value in changes.items():
            parameter = model.getParameter(symbol)
            if parameter is None or not parameter.getConstant() or model.getInitialAssignmentBySymbol(symbol) is not None:
                raise ValueError(f"{symbol}: perturbations require a constant global parameter without an initial assignment")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{symbol}: perturbation must be a finite number")
    return config


def make_sedml(config, names):
    import libsedml
    sed = libsedml.SedDocument(1, 3)
    simulation = sed.createUniformTimeCourse(); simulation.setId("simulation")
    simulation.setInitialTime(0.); simulation.setOutputStartTime(0.)
    simulation.setOutputEndTime(config["end_time"]); simulation.setNumberOfPoints(config["points"] - 1)
    algorithm = simulation.createAlgorithm(); algorithm.setKisaoID("KISAO:0000019")
    for kisao, value in (("KISAO:0000209", config["relative_tolerance"]), ("KISAO:0000211", config["absolute_tolerance"])):
        parameter = algorithm.createAlgorithmParameter(); parameter.setKisaoID(kisao); parameter.setValue(str(value))
    for scenario in names:
        model = sed.createModel(); model.setId(f"model_{scenario}")
        model.setSource(f"model_{scenario}.xml"); model.setLanguage("urn:sedml:language:sbml")
        task = sed.createTask(); task.setId(f"task_{scenario}")
        task.setModelReference(f"model_{scenario}"); task.setSimulationReference("simulation")
        report = sed.createReport(); report.setId(f"report_{scenario}")
        for index, symbol in enumerate(["time"] + config["species"]):
            generator = sed.createDataGenerator(); generator.setId(f"dg_{scenario}_{index}")
            variable = generator.createVariable(); variable.setId(f"v_{scenario}_{index}")
            variable.setTaskReference(f"task_{scenario}")
            if symbol == "time":
                variable.setSymbol("urn:sedml:symbol:time")
            else:
                variable.setTarget(f"/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='{symbol}']")
            generator.setMath(libsedml.parseFormula(variable.getId()))
            dataset = report.createDataSet(); dataset.setId(f"ds_{scenario}_{index}")
            dataset.setLabel(symbol); dataset.setDataReference(generator.getId())
    return sed


def run(model_path, model_format, experiment_path, output):
    import libsbml
    import libsedml
    import numpy as np
    import tellurium as te
    model_path, experiment_path, output = Path(model_path), Path(experiment_path), Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    document, issues = model_document(model_path, model_format)
    config = validate_experiment(json.loads(experiment_path.read_text()), document.getModel())
    output.mkdir(parents=True)
    selections = ["time"] + [f"[{s}]" for s in config["species"]]
    results, model_files = {}, []
    for scenario, changes in config["scenarios"].items():
        # Fresh SBML per condition avoids reset/state carryover ambiguity.
        condition = document.clone()
        for symbol, value in changes.items():
            condition.getModel().getParameter(symbol).setValue(value)
        sbml = libsbml.writeSBMLToString(condition)
        model_file = output / f"model_{scenario}.xml"; model_file.write_text(sbml); model_files.append(model_file)
        runner = te.loadSBMLModel(sbml)
        runner.setIntegrator("cvode")
        runner.integrator.relative_tolerance = config["relative_tolerance"]
        runner.integrator.absolute_tolerance = config["absolute_tolerance"]
        runner.integrator.stiff = True
        values = np.asarray(runner.simulate(0., config["end_time"], config["points"], selections))
        if values.shape != (config["points"], len(selections)) or not np.isfinite(values).all():
            raise RuntimeError(f"{scenario}: invalid simulation output")
        results[scenario] = values
        with (output / f"{scenario}.csv").open("w", newline="") as handle:
            writer = csv.writer(handle); writer.writerow(selections); writer.writerows(values)
    sed = make_sedml(config, config["scenarios"])
    sed_path = output / "experiment.sedml"
    libsedml.writeSedMLToFile(sed, str(sed_path))
    parsed_sed = libsedml.readSedMLFromFile(str(sed_path))
    sed_issues = [{"severity": parsed_sed.getError(i).getSeverityAsString(), "message": parsed_sed.getError(i).getMessage()}
                  for i in range(parsed_sed.getNumErrors())]
    if any(issue["severity"] in {"Error", "Fatal"} for issue in sed_issues):
        raise ValueError("Generated SED-ML failed validation")
    archive = output / "experiment.omex"
    te.createCombineArchive(str(archive), [str(p) for p in model_files] + [str(sed_path)],
        [p.name for p in model_files] + [sed_path.name],
        ["http://identifiers.org/combine.specifications/sbml"] * len(model_files) + ["http://identifiers.org/combine.specifications/sed-ml"],
        [False] * len(model_files) + [True])
    # Replay only this generated archive; no arbitrary archive extraction entry point.
    replay = te.executeCombineArchive(str(archive), createOutputs=False)
    if len(replay) != 1:
        raise RuntimeError("Expected one SED-ML document in generated archive")
    generators = next(iter(replay.values()))["dataGenerators"]
    replay_errors = {}
    for scenario, values in results.items():
        replayed = np.column_stack([generators[f"dg_{scenario}_{i}"].reshape(-1) for i in range(len(selections))])
        np.testing.assert_allclose(replayed, values, rtol=config["relative_tolerance"] * 10,
                                   atol=config["absolute_tolerance"] * 10)
        replay_errors[scenario] = float(np.max(np.abs(replayed - values)))
    model = document.getModel()
    units = {"time": model.getTimeUnits(), "substance": model.getSubstanceUnits(), "volume": model.getVolumeUnits(),
             "species": {s: libsbml.UnitDefinition.printUnits(model.getSpecies(s).getDerivedUnitDefinition()) for s in config["species"]}}
    report = {"versions": {**dict(te.getVersionInfo()), "libcombine": importlib.metadata.version("python-libcombine")}, "integrator": "cvode", "stiff": True, "experiment": config,
              "source_model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
              "experiment_sha256": hashlib.sha256(experiment_path.read_bytes()).hexdigest(),
              "sbml_validation_findings": issues, "sedml_parse_findings": sed_issues, "units": units,
              "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
              "archive_replay_max_absolute_difference": replay_errors,
              "minimum_concentration": {s: float(v[:, 1:].min()) for s, v in results.items()}}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--format", choices=["sbml", "antimony"], required=True)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.model, args.format, args.experiment, args.output), indent=2))


if __name__ == "__main__":
    main()
