#!/usr/bin/env python3
"""Compute TDB-based equilibria at one bulk mole composition over temperatures."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pycalphad as pc
from pycalphad import variables as v
from pycalphad.core.utils import filter_phases, unpack_species


def finite(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    return float(value)


def validate(db, settings):
    keys = {"components", "phases", "composition_basis", "dependent_component", "independent_mole_fractions",
            "temperatures_k", "pressure_pa", "database_temperature_range_k", "pdens",
            "mass_balance_tolerance", "phase_fraction_tolerance", "gibbs_energy_tolerance_j_per_mol"}
    if set(settings) != keys:
        raise ValueError(f"Missing settings: {sorted(keys-set(settings))}; unknown: {sorted(set(settings)-keys)}")
    for key in ("components", "phases"):
        values = settings[key]
        if not isinstance(values, list) or not values or any(not isinstance(s, str) for s in values) or len(set(values)) != len(values):
            raise ValueError(f"{key} must be a nonempty list of unique names")
    comps = settings["components"]
    phases = settings["phases"]
    if set(comps) - db.elements:
        raise ValueError(f"Components absent from database elements: {sorted(set(comps) - db.elements)}")
    if set(phases) - set(db.phases):
        raise ValueError(f"Unknown phases: {sorted(set(phases) - set(db.phases))}")
    active = filter_phases(db, unpack_species(db, comps), phases)
    if set(active) != set(phases):
        raise ValueError(f"Incompatible or order-disorder-filtered phases: {sorted(set(phases) - set(active))}")
    if settings["composition_basis"] != "mole_fraction":
        raise ValueError("Only elemental mole_fraction conditions are accepted; convert mass fractions explicitly")
    material = set(comps) - {"VA"}
    dependent = settings["dependent_component"]
    if dependent not in material:
        raise ValueError("dependent_component must be a non-vacancy selected element")
    fractions = settings["independent_mole_fractions"]
    if not isinstance(fractions, dict) or set(fractions) != material - {dependent}:
        raise ValueError("Specify exactly one mole fraction for each nondependent, non-vacancy component")
    fractions = {name: finite(value, name) for name, value in fractions.items()}
    if any(value < 0 or value > 1 for value in fractions.values()) or sum(fractions.values()) > 1:
        raise ValueError("Mole fractions must be in [0,1] and sum to at most one")
    bulk = {**fractions, dependent: 1 - sum(fractions.values())}
    temperatures = settings["temperatures_k"]
    if not isinstance(temperatures, list) or not temperatures or len(temperatures) > 1000:
        raise ValueError("temperatures_k must contain between 1 and 1000 explicit temperatures")
    for temperature in temperatures:
        finite(temperature, "temperature_k", True)
    if len(set(temperatures)) != len(temperatures):
        raise ValueError("Duplicate temperatures are not accepted")
    bounds = settings["database_temperature_range_k"]
    if bounds is not None:
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError("database_temperature_range_k must be [low, high] or null if unknown")
        low, high = [finite(x, "database temperature bound", True) for x in bounds]
        if low >= high or min(temperatures) < low or max(temperatures) > high:
            raise ValueError("Requested temperatures lie outside the declared database range")
    for name in ("pressure_pa", "mass_balance_tolerance", "phase_fraction_tolerance", "gibbs_energy_tolerance_j_per_mol"):
        finite(settings[name], name, True)
    pdens = settings["pdens"]
    if isinstance(pdens, bool) or not isinstance(pdens, int) or not 10 <= pdens <= 10000:
        raise ValueError("pdens must be an integer from 10 through 10000")
    return bulk


def solve_point(db, settings, bulk, temperature, pdens):
    conditions = {v.T: temperature, v.P: settings["pressure_pa"], v.N: 1}
    conditions.update({v.X(name): value for name, value in settings["independent_mole_fractions"].items()})
    result = pc.equilibrium(db, settings["components"], settings["phases"], conditions, calc_opts={"pdens": pdens})
    energy = float(result.GM.values.item())
    names = result.Phase.values.ravel()
    amounts = result.NP.values.ravel()
    components = [str(c) for c in result.component.values]
    compositions = result.X.values.reshape(-1, len(components))
    if not np.isfinite(energy) or set(components) != set(bulk):
        raise ValueError("Equilibrium failed: nonfinite energy or unexpected output components")
    vertices = []
    reconstructed = {name: 0.0 for name in bulk}
    phase_sums = {name: 0.0 for name in settings["phases"]}
    for index, (name, amount, composition) in enumerate(zip(names, amounts, compositions)):
        if name == "":
            continue  # pycalphad pads unused vertices with blank names and NaN amounts.
        if name not in phase_sums or not np.isfinite(amount) or not np.isfinite(composition).all():
            raise ValueError("Equilibrium contains an invalid or fictitious stable vertex")
        if amount < -1e-10 or amount > 1 + 1e-10 or np.min(composition) < -1e-10 or abs(composition.sum() - 1) > 1e-7:
            raise ValueError("Equilibrium has invalid phase fraction or composition")
        fractions = dict(zip(components, map(float, composition)))
        vertices.append({"vertex": index, "phase": str(name), "mole_phase_fraction": float(amount), "mole_fractions": fractions})
        phase_sums[str(name)] += float(amount)
        for component, fraction in fractions.items():
            reconstructed[component] += float(amount) * fraction
    if not vertices:
        raise ValueError("Equilibrium produced no stable phases")
    amount_error = abs(sum(phase_sums.values()) - 1)
    mass_error = max(abs(reconstructed[c] - bulk[c]) for c in bulk)
    return {"temperature_k": temperature, "gibbs_energy_j_per_mol": energy, "vertices": vertices,
            "phase_totals": phase_sums, "reconstructed_bulk_mole_fractions": reconstructed,
            "phase_fraction_sum_error": amount_error, "mass_balance_absolute_error": mass_error,
            "balance_passed": amount_error <= settings["mass_balance_tolerance"] and mass_error <= settings["mass_balance_tolerance"]}


def calculate(db, settings):
    bulk = validate(db, settings)
    points = []
    for temperature in settings["temperatures_k"]:
        baseline = solve_point(db, settings, bulk, temperature, settings["pdens"])
        refined = solve_point(db, settings, bulk, temperature, 2 * settings["pdens"])
        fraction_change = max(abs(baseline["phase_totals"][p] - refined["phase_totals"][p]) for p in settings["phases"])
        energy_change = abs(baseline["gibbs_energy_j_per_mol"] - refined["gibbs_energy_j_per_mol"])
        points.append({"baseline": baseline, "refined": refined,
                       "maximum_phase_fraction_change": fraction_change,
                       "gibbs_energy_change_j_per_mol": energy_change,
                       "checks_passed": baseline["balance_passed"] and refined["balance_passed"] and
                       fraction_change <= settings["phase_fraction_tolerance"] and energy_change <= settings["gibbs_energy_tolerance_j_per_mol"]})
    return {"bulk_mole_fractions": bulk, "points": points,
            "all_checks_passed": all(point["checks_passed"] for point in points),
            "excluded_database_phases": sorted(set(db.phases) - set(settings["phases"]))}


def run(database_path, settings_path, output_dir):
    database_path, settings_path, output_dir = map(Path, (database_path, settings_path, output_dir))
    if output_dir.exists():
        raise ValueError("Output directory already exists; choose a new directory")
    settings = json.loads(settings_path.read_text())
    db = pc.Database(str(database_path))
    report = calculate(db, settings)
    report.update(versions={"pycalphad": pc.__version__, "numpy": np.__version__}, settings=settings,
                  database_sha256=hashlib.sha256(database_path.read_bytes()).hexdigest(),
                  settings_sha256=hashlib.sha256(settings_path.read_bytes()).hexdigest(),
                  phase_fraction_basis="molar, N=1; vacancies excluded from bulk composition",
                  database_experimental_validity="not_assessed",
                  refinement="pdens doubled; phase totals and GM compared; not a proof of the global minimum")
    output_dir.mkdir(parents=True)
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    with (output_dir / "phase-equilibria.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        components = sorted(report["bulk_mole_fractions"])
        writer.writerow(["run", "temperature_k", "vertex", "phase", "mole_phase_fraction", "gibbs_energy_j_per_mol", *[f"X_{c}" for c in components]])
        for point in report["points"]:
            for variant in ("baseline", "refined"):
                result = point[variant]
                for vertex in result["vertices"]:
                    writer.writerow([variant, result["temperature_k"], vertex["vertex"], vertex["phase"],
                                     vertex["mole_phase_fraction"], result["gibbs_energy_j_per_mol"],
                                     *[vertex["mole_fractions"][c] for c in components]])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Thermodynamic TDB database")
    parser.add_argument("settings", type=Path, help="Conditions JSON")
    parser.add_argument("output", type=Path, help="New output directory")
    args = parser.parse_args()
    try:
        report = run(args.database, args.settings, args.output)
    except (ValueError, OSError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), "all_checks_passed": report["all_checks_passed"]}))


if __name__ == "__main__":
    main()
