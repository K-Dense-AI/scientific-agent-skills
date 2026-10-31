#!/usr/bin/env python3
"""Run closed adiabatic ideal-gas ignition with numerical and conservation checks."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import cantera as ct
import numpy as np


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return float(value)


def validate(config):
    keys = {"mechanism", "phase", "reactor", "temperature_k", "pressure_pa", "mole_amounts",
            "end_time_s", "samples", "rtol", "atol", "max_time_step_s", "minimum_temperature_rise_k",
            "tracked_species", "delay_relative_tolerance"}
    if set(config) != keys:
        raise ValueError(f"Missing settings: {sorted(keys-set(config))}; unknown: {sorted(set(config)-keys)}")
    for name in keys - {"mechanism", "phase", "reactor", "mole_amounts", "samples", "tracked_species"}:
        number(config[name], name)
    n = config["samples"]
    if isinstance(n, bool) or not isinstance(n, int) or not 11 <= n <= 100000:
        raise ValueError("samples must be an integer from 11 through 100000")
    if config["reactor"] not in ("constant-volume", "constant-pressure"):
        raise ValueError("reactor must be constant-volume or constant-pressure")
    if not isinstance(config["mole_amounts"], dict) or not config["mole_amounts"]:
        raise ValueError("mole_amounts must be a nonempty species-to-amount mapping")
    amounts = config["mole_amounts"]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v < 0 for v in amounts.values()) or sum(amounts.values()) <= 0:
        raise ValueError("mole_amounts must be finite, nonnegative, and have a positive sum")
    if not isinstance(config["tracked_species"], list) or len(set(config["tracked_species"])) != len(config["tracked_species"]):
        raise ValueError("tracked_species must be a list of unique names")


def load_gas(config):
    gas = ct.Solution(config["mechanism"], config["phase"])
    if gas.thermo_model != "ideal-gas":
        raise ValueError("This helper supports only ideal-gas phases")
    unknown = (set(config["mole_amounts"]) | set(config["tracked_species"])) - set(gas.species_names)
    if unknown:
        raise ValueError(f"Unknown species: {sorted(unknown)}")
    gas.TPX = config["temperature_k"], config["pressure_pa"], config["mole_amounts"]
    return gas


def delay_from_history(time, temperature, minimum_rise):
    rise = float(np.max(temperature) - temperature[0])
    rate = np.gradient(temperature, time, edge_order=2)
    index = int(np.argmax(rate))
    status = "resolved"
    if rise < minimum_rise:
        status = "temperature-rise-not-reached"
    elif index < 2 or index >= len(time) - 2:
        status = "derivative-maximum-at-boundary"
    return {"status": status, "delay_s": float(time[index]) if status == "resolved" else None,
            "maximum_temperature_rise_k": rise, "peak_heating_rate_k_per_s": float(rate[index]),
            "output_spacing_s": float(time[1] - time[0])}


def simulate(config):
    validate(config)
    gas = load_gas(config)
    reactor_type = ct.IdealGasReactor if config["reactor"] == "constant-volume" else ct.IdealGasConstPressureReactor
    reactor = reactor_type(gas, energy="on", volume=1.0, clone=True)
    network = ct.ReactorNet([reactor])
    network.rtol, network.atol = config["rtol"], config["atol"]
    network.max_time_step = config["max_time_step_s"]
    network.max_steps = 100000
    times = np.linspace(0, config["end_time_s"], config["samples"])
    rows, elements = [], []
    species_indices = [gas.species_index(name) for name in config["tracked_species"]]
    minimum_y = 0.0
    normalization_error = 0.0
    for time in times:
        if time:
            network.advance(float(time))
        phase = reactor.phase
        rows.append([time, reactor.T, phase.P, reactor.volume, reactor.mass,
                     reactor.mass * phase.int_energy_mass, reactor.mass * phase.enthalpy_mass,
                     *phase.X[species_indices]])
        elements.append([phase.elemental_mass_fraction(name) for name in phase.element_names])
        minimum_y = min(minimum_y, float(phase.Y.min()))
        normalization_error = max(normalization_error, abs(float(phase.Y.sum()) - 1))
    history = np.asarray(rows)
    if not np.isfinite(history).all():
        raise ValueError("Integrator returned a nonfinite state")
    energy_col = 5 if config["reactor"] == "constant-volume" else 6
    conserved = history[:, energy_col]
    conservation = {
        "mass_relative_drift": float(np.max(np.abs(history[:, 4] / history[0, 4] - 1))),
        "element_mass_fraction_absolute_drift": float(np.max(np.abs(np.asarray(elements) - elements[0]))),
        "conserved_quantity": "total_internal_energy_j" if energy_col == 5 else "total_enthalpy_j",
        "energy_scaled_drift": float(np.max(np.abs(conserved - conserved[0])) / max(abs(conserved[0]), 1.0)),
        "energy_denominator_j": max(abs(float(conserved[0])), 1.0),
        "minimum_species_mass_fraction": minimum_y,
        "mass_fraction_sum_error": normalization_error,
    }
    conservation["passed"] = (conservation["mass_relative_drift"] < 1e-8 and
                               conservation["element_mass_fraction_absolute_drift"] < 1e-8 and
                               conservation["energy_scaled_drift"] < 1e-6 and
                               minimum_y > -1e-10 and normalization_error < 1e-8)
    result = delay_from_history(history[:, 0], history[:, 1], config["minimum_temperature_rise_k"])
    result.update(conservation=conservation, final_temperature_k=float(history[-1, 1]),
                  samples=config["samples"], rtol=config["rtol"], atol=config["atol"],
                  max_time_step_s=config["max_time_step_s"], end_time_s=config["end_time_s"],
                  thermo_temperature_range_k=[gas.min_temp, gas.max_temp],
                  within_thermo_temperature_range=bool(history[:, 1].min() >= gas.min_temp and history[:, 1].max() <= gas.max_temp))
    return history, result


def run(config_path, output_dir):
    config_path, output_dir = Path(config_path), Path(output_dir)
    if output_dir.exists():
        raise ValueError("Output directory exists; choose a new directory")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate(config)
    if config["samples"] > 50000:
        raise ValueError("CLI samples must be at most 50000 to permit refinement runs")
    # Local relative mechanism paths resolve against the configuration, before built-in lookup.
    local = config_path.parent / config["mechanism"]
    effective = dict(config)
    if local.is_file():
        effective["mechanism"] = str(local.resolve())
    gas = load_gas(effective)
    # Hash the exact bytes written, including on platforms with CRLF text translation.
    snapshot = gas.write_yaml(precision=17).encode("utf-8")
    source = next((Path(d) / effective["mechanism"] for d in ct.get_data_directories()
                   if (Path(d) / effective["mechanism"]).is_file()), None)
    variants = {
        "baseline": effective,
        "finer_output": {**effective, "samples": 2 * effective["samples"] - 1},
        "tighter_solver": {**effective, "rtol": effective["rtol"] / 10,
                           "atol": effective["atol"] / 10,
                           "max_time_step_s": effective["max_time_step_s"] / 2},
        "longer_horizon": {**effective, "end_time_s": 2 * effective["end_time_s"],
                           "samples": 2 * effective["samples"] - 1},
    }
    results, histories = {}, {}
    for name, conditions in variants.items():
        history, summary = simulate(conditions)
        histories[name], results[name] = history, summary
    baseline_delay = results["baseline"]["delay_s"]
    sensitivity = {}
    for name, result in results.items():
        if name == "baseline":
            continue
        delay = result["delay_s"]
        sensitivity[name] = (abs(delay - baseline_delay) / baseline_delay
                             if baseline_delay is not None and delay is not None else None)
    converged = all(value is not None and value <= config["delay_relative_tolerance"] for value in sensitivity.values())
    report = {
        "versions": {"cantera": ct.__version__, "numpy": np.__version__}, "settings": config,
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "mechanism": {"requested": config["mechanism"], "phase": gas.name,
                      "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest() if source else None,
                      "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
                      "species_count": gas.n_species, "reaction_count": gas.n_reactions,
                      "initial_normalized_mole_fractions": {name: float(x) for name, x in zip(gas.species_names, gas.X) if x > 0}},
        "definition": "Time of global maximum finite-difference dT/dt on a uniform output grid; requires the specified temperature rise and an interior maximum",
        "runs": results, "delay_relative_changes": sensitivity,
        "numerically_resolved": converged and all(r["conservation"]["passed"] for r in results.values()),
        "mechanism_experimental_validity": "not_assessed",
    }
    output_dir.mkdir(parents=True)
    (output_dir / "mechanism.yaml").write_bytes(snapshot)
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for name, history in histories.items():
        with (output_dir / f"{name}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["time_s", "temperature_k", "pressure_pa", "volume_m3", "mass_kg",
                             "internal_energy_j", "enthalpy_j", *[f"X_{s}" for s in config["tracked_species"]]])
            writer.writerows(history)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path, help="New output directory")
    args = parser.parse_args()
    try:
        report = run(args.config, args.output)
    except (ValueError, OSError, KeyError, TypeError, ct.CanteraError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), "numerically_resolved": report["numerically_resolved"],
                      "delay_s": report["runs"]["baseline"]["delay_s"]}))


if __name__ == "__main__":
    main()
