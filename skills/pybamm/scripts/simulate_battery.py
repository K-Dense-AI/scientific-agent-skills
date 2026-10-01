"""Run a validated constant-current/rest battery experiment with numerical checks."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path

# Simulation is local; do not send usage telemetry when the library imports.
os.environ.setdefault("PYBAMM_DISABLE_TELEMETRY", "true")


def validate_protocol(protocol):
    def finite(name, value, low=0, high=math.inf):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low < value <= high:
            raise ValueError(f"{name} must be finite and in ({low}, {high}]")
    allowed = {"model", "parameter_set", "initial_soc", "temperature_K", "sample_period_s", "steps", "parameter_overrides"}
    if set(protocol) - allowed:
        raise ValueError(f"Unsupported protocol fields: {sorted(set(protocol) - allowed)}")
    if protocol.get("model") not in {"SPM", "DFN"}:
        raise ValueError("model must be SPM or DFN")
    if not isinstance(protocol.get("parameter_set"), str) or not protocol["parameter_set"]:
        raise ValueError("parameter_set is required")
    finite("initial_soc", protocol.get("initial_soc"), high=1)
    finite("temperature_K", protocol.get("temperature_K"))
    finite("sample_period_s", protocol.get("sample_period_s"))
    steps = protocol.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("steps must be a nonempty list")
    for index, step in enumerate(steps):
        if set(step) - {"kind", "duration_s", "c_rate", "until_voltage_V"}:
            raise ValueError(f"step {index}: unsupported field")
        if step.get("kind") not in {"discharge", "charge", "rest"}:
            raise ValueError(f"step {index}: kind must be discharge, charge or rest")
        finite(f"step {index} duration_s", step.get("duration_s"))
        if protocol["sample_period_s"] > step["duration_s"]:
            raise ValueError("sample_period_s exceeds a step duration")
        if step["kind"] != "rest":
            finite(f"step {index} c_rate", step.get("c_rate"))
            if "until_voltage_V" in step:
                finite(f"step {index} until_voltage_V", step["until_voltage_V"])
        elif "c_rate" in step or "until_voltage_V" in step:
            raise ValueError("Rest steps cannot specify c_rate or voltage cutoff")
    for key, value in protocol.get("parameter_overrides", {}).items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Override {key}: only finite numeric existing parameters are supported")
    return protocol


def solve_protocol(protocol, mesh_points=20, rtol=1e-6, atol=1e-8):
    import pybamm
    import numpy as np
    validate_protocol(protocol)
    if not isinstance(mesh_points, int) or mesh_points < 5:
        raise ValueError("mesh_points must be an integer >=5")
    if not (0 < rtol < 1 and 0 < atol < 1):
        raise ValueError("Solver tolerances must be between zero and one")
    parameters = pybamm.ParameterValues(protocol["parameter_set"])
    overrides = protocol.get("parameter_overrides", {})
    unknown = set(overrides) - set(parameters.keys())
    if unknown:
        raise ValueError(f"Unknown parameter overrides: {sorted(unknown)}")
    if {"Ambient temperature [K]", "Initial temperature [K]"} & set(overrides):
        raise ValueError("Set temperature_K instead of temperature overrides")
    parameters.update(overrides)
    parameters.update({"Ambient temperature [K]": protocol["temperature_K"],
                       "Initial temperature [K]": protocol["temperature_K"]})
    capacity = float(parameters["Nominal cell capacity [A.h]"])
    lower, upper = (float(parameters[key]) for key in ("Lower voltage cut-off [V]", "Upper voltage cut-off [V]"))
    if not (capacity > 0 and 0 < lower < upper):
        raise ValueError("Invalid nominal capacity or voltage limits in parameter set")
    steps = []
    for step in protocol["steps"]:
        current = 0 if step["kind"] == "rest" else step["c_rate"] * capacity * (1 if step["kind"] == "discharge" else -1)
        cutoff = step.get("until_voltage_V")
        if cutoff is not None and not lower <= cutoff <= upper:
            raise ValueError("Protocol voltage cutoff exceeds the parameter-set limits")
        steps.append(pybamm.step.current(current, duration=step["duration_s"],
                     termination=f"{cutoff} V" if cutoff is not None else None,
                     period=protocol["sample_period_s"], skip_ok=False))
    model = {"SPM": pybamm.lithium_ion.SPM, "DFN": pybamm.lithium_ion.DFN}[protocol["model"]](options={"thermal": "isothermal"})
    mesh = {key: mesh_points for key in ("x_n", "x_s", "x_p", "r_n", "r_p")}
    simulation = pybamm.Simulation(model, parameter_values=parameters,
        experiment=pybamm.Experiment([tuple(steps)]), var_pts=mesh,
        solver=pybamm.IDAKLUSolver(rtol=rtol, atol=atol))
    solution = simulation.solve(initial_soc=protocol["initial_soc"])
    segments = [segment for cycle in solution.cycles for segment in cycle.steps]
    if len(segments) != len(steps) or any(isinstance(s, pybamm.EmptySolution) for s in segments):
        raise RuntimeError("Protocol ended early or skipped a step; do not interpret as a complete experiment")
    rows, terminations = [], []
    for index, segment in enumerate(segments):
        t = np.asarray(segment["Time [s]"].entries)
        v = np.asarray(segment["Voltage [V]"].entries)
        current = np.asarray(segment["Current [A]"].entries)
        charge = np.asarray(segment["Discharge capacity [A.h]"].entries)
        requested = protocol["steps"][index]
        if t[-1] - t[0] < requested["duration_s"] - 1e-5:
            cutoff = requested.get("until_voltage_V")
            if cutoff is None or abs(float(v[-1]) - cutoff) > 1e-4:
                raise RuntimeError(f"Step {index} ended before its duration without reaching the requested cutoff")
        if not np.isfinite(np.column_stack([t, v, current, charge])).all():
            raise RuntimeError("Nonfinite simulation output")
        rows.extend(zip([index] * len(t), t, v, current, charge))
        terminations.append({"step": index, "kind": protocol["steps"][index]["kind"],
                             "start_s": float(t[0]), "end_s": float(t[-1]), "termination": segment.termination})
    return {"solution": solution, "segments": segments, "rows": rows, "terminations": terminations,
            "parameters": parameters.to_json(), "mesh_points": mesh_points, "rtol": rtol, "atol": atol,
            "nominal_capacity_Ah": capacity, "voltage_limits_V": [lower, upper]}


def compare_runs(first, second):
    import numpy as np
    differences = []
    for index, (a, b) in enumerate(zip(first["segments"], second["segments"])):
        duration_a, duration_b = a.t[-1] - a.t[0], b.t[-1] - b.t[0]
        local = np.linspace(0, min(duration_a, duration_b), 101)
        va = a["Voltage [V]"](a.t[0] + local)
        vb = b["Voltage [V]"](b.t[0] + local)
        differences.append({"step": index, "max_voltage_difference_V": float(np.max(np.abs(va-vb))),
                            "end_time_difference_s": float(abs(duration_a-duration_b))})
    return {"max_voltage_difference_V": max(d["max_voltage_difference_V"] for d in differences),
            "steps": differences}


def compare_measurement(rows, measurement_path, residual_path):
    import numpy as np
    with Path(measurement_path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["time_s", "voltage_V", "current_A"]:
            raise ValueError("Measured CSV columns must be time_s,voltage_V,current_A")
        measured = np.asarray([[float(r[k]) for k in reader.fieldnames] for r in reader])
    if measured.ndim != 2 or len(measured) < 2 or not np.isfinite(measured).all() or (np.diff(measured[:, 0]) <= 0).any():
        raise ValueError("Need finite measurements and strictly increasing times")
    simulated = np.asarray(rows)
    if measured[0, 0] < simulated[0, 1] or measured[-1, 0] > simulated[-1, 1]:
        raise ValueError("Measurement times exceed simulated interval; no extrapolation")
    predicted = np.interp(measured[:, 0], simulated[:, 1], simulated[:, 2])
    predicted_current = np.interp(measured[:, 0], simulated[:, 1], simulated[:, 3])
    residual = predicted - measured[:, 1]
    with Path(residual_path).open("w", newline="") as handle:
        writer = csv.writer(handle); writer.writerow(["time_s", "predicted_voltage_V", "measured_voltage_V", "residual_V", "current_difference_A"])
        writer.writerows(zip(measured[:, 0], predicted, measured[:, 1], residual, predicted_current-measured[:, 2]))
    return {"samples": len(measured), "rmse_V": float(np.sqrt(np.mean(residual**2))),
            "mae_V": float(np.mean(np.abs(residual))), "bias_V": float(np.mean(residual)),
            "current_rmse_A": float(np.sqrt(np.mean((predicted_current-measured[:, 2])**2))),
            "measurement_sha256": hashlib.sha256(Path(measurement_path).read_bytes()).hexdigest(),
            "comparison_interval_s": [float(measured[0, 0]), float(measured[-1, 0])]}


def run(protocol_path, output, measured=None, mesh_points=20):
    import pybamm
    protocol_path, output = Path(protocol_path), Path(output)
    protocol = validate_protocol(json.loads(protocol_path.read_text()))
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    baseline = solve_protocol(protocol, mesh_points)
    tight = solve_protocol(protocol, mesh_points, rtol=1e-8, atol=1e-10)
    refined = solve_protocol(protocol, mesh_points * 2, rtol=1e-8, atol=1e-10)
    output.mkdir(parents=True)
    for name, result in (("curve", baseline), ("tight-tolerance", tight), ("refined-mesh", refined)):
        with (output / f"{name}.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["step", "time_s", "voltage_V", "current_A", "net_discharge_capacity_Ah"])
            writer.writerows(result["rows"])
    (output / "parameters.json").write_text(json.dumps(baseline["parameters"], indent=2) + "\n")
    report = {"pybamm_version": pybamm.__version__, "solver": "IDAKLUSolver", "protocol": protocol,
        "versions": {name: importlib.metadata.version(name) for name in ("pybamm", "pybammsolvers", "numpy", "casadi")},
        "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        "parameter_set_description": pybamm.parameter_sets.get_docstring(protocol["parameter_set"]),
        "nominal_capacity_Ah": baseline["nominal_capacity_Ah"], "voltage_limits_V": baseline["voltage_limits_V"],
        "mesh_points": mesh_points, "baseline_tolerances": {"rtol": 1e-6, "atol": 1e-8},
        "tight_tolerances": {"rtol": 1e-8, "atol": 1e-10}, "refined_mesh_points": mesh_points * 2,
        "terminations": baseline["terminations"], "solver_sensitivity": compare_runs(baseline, tight),
        "mesh_sensitivity": compare_runs(tight, refined)}
    if measured:
        report["measurement_comparison"] = compare_measurement(baseline["rows"], measured, output / "measurement-residuals.csv")
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--measured", type=Path)
    parser.add_argument("--mesh-points", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(run(args.protocol, args.output, args.measured, args.mesh_points), indent=2))


if __name__ == "__main__":
    main()
