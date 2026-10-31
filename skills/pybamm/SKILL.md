---
name: pybamm
description: Simulates lithium-ion battery charge, discharge and rest experiments with PyBaMM, records parameter-set provenance, checks mesh and solver sensitivity, and compares predicted voltage curves with measured cycling data. Use for SPM or DFN electrochemical battery modeling, C-rate protocols, voltage cutoffs, parameter studies and numerical validation of battery simulations.
license: MIT
compatibility: Requires Python 3.12 with PyBaMM 26.9.0.0 and pybammsolvers 0.10.0 (IDAKLU). NumPy and CasADi are supplied by PyBaMM. Network is needed for installation and optional upstream dataset retrieval; bundled simulations and CSV comparisons run locally without credentials.
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
  upstream-version: "26.9.0.0"
  last-reviewed: "2026-10-01"
---

# PyBaMM battery experiments

## When to use

Use this skill to model single-cell constant-current charge/discharge and rest, examine voltage and charge
trajectories, or compare SPM/DFN predictions to cycling measurements. The helper runs real PyBaMM
experiments and three numerical resolutions; it does not control a battery cycler or establish an
operating envelope for hardware.

## Runtime and tested case

```bash
uv venv --python 3.12 battery-env
uv pip install --python battery-env/bin/python pybamm==26.9.0.0 pybammsolvers==0.10.0
```

This release requires `pybammsolvers>=0.10.0`, NumPy 2 or newer, and CasADi 3.8.1.
The tested environment used Python 3.12.10, NumPy 2.5.3 and SciPy 1.18.1. IDAKLU is the
recommended solver; `CasadiSolver` and `ScipySolver` are deprecated in this release. Refer to
the **26.9.0.0** manual below, since `latest` can describe unreleased APIs.

The included [assets/chen2020-protocol.json](assets/chen2020-protocol.json) is a synthetic
isothermal 298.15-K SPM case: 80% initial SOC, discharge at 0.5C for 600 s, rest for 120 s,
charge at 0.5C for 600 s. Chen2020 supplies an LG M50 parameterization with 5-Ah nominal capacity;
here 0.5C means 2.5 A. This is an executable reference example, not a claim that an arbitrary
user's cell has those parameters. The helper disables PyBaMM usage telemetry unless the caller
has already explicitly configured that variable.

## Workflow

1. Establish the cell chemistry, geometry, nominal capacity, initial state, temperature and
   current-sign convention. Use an appropriate parameter set and explain its source. Distinguish
   a paper's fitted parameters from measurements of this particular cell. Do not transplant
   degradation parameters without checking their meaning and applicable conditions.
2. Convert the requested protocol to the JSON contract in
   [references/protocol-and-comparison.md](references/protocol-and-comparison.md). Positive
   simulation current discharges; negative current charges. Every step has a finite duration.
   A specified voltage cutoff can end it earlier; the report records actual termination times.
   C-rates use the selected set's nominal capacity. A change in that capacity changes current.
3. Choose SPM when its reduced transport assumptions are adequate; use DFN when resolving
   electrolyte/electrode transport matters. The helper's tested models are isothermal and exclude
   aging, mechanics, plating and pack control. Increasing rate can invalidate SPM predictions
   even if numerical convergence is excellent.
4. Run the helper. It validates protocol fields, rejects unknown or overridden-by-protocol
   parameter inputs, uses IDAKLU, and snapshots the base parameters **after SOC initialization**.
   Keep the protocol with that snapshot: experiment steps supply their own currents.
   Infeasible or skipped steps are errors,
   rather than silently presenting a partial protocol as complete.
5. Read the two numerical comparisons separately: baseline versus tighter tolerances isolates
   solver error; tight tolerances on the original versus doubled mesh isolates discretization.
   Compare voltage differences and event-time differences against the accuracy the question
   needs. Refine again when these are too large; one doubling does not prove convergence.
6. If measurements are available, check current, time origin, temperature, SOC and capacity
   before interpreting residuals. Supply matching seconds, volts and amps. The helper reports
   voltage RMSE/MAE/bias and current RMSE, preserving residuals. A small voltage error under a
   mismatched input current does not validate the model. This workflow compares curves; it
   does not claim to identify unique kinetic parameters from voltage alone.

## Run and inspect

From the skill directory, point `battery-env/bin/python` at the environment created above:

```bash
battery-env/bin/python scripts/simulate_battery.py assets/chen2020-protocol.json \
  --output battery-reference

# measured.csv is user data with time_s,voltage_V,current_A columns.
battery-env/bin/python scripts/simulate_battery.py protocol.json \
  --measured measured.csv --mesh-points 30 --output battery-comparison
```

The first command was executed as written with an external output location. The second uses
illustrative user filenames; the measurement path was exercised against a frozen synthetic
reference curve in the tests. Output directories must be new.

| Artifact | Interpretation |
| --- | --- |
| `curve.csv` | Baseline time, step, voltage, current and **net** discharge capacity |
| `tight-tolerance.csv` | Same mesh, tighter solver |
| `refined-mesh.csv` | Doubled mesh with tighter solver |
| `parameters.json` | Base parameters after SOC initialization; step currents remain in the protocol |
| `report.json` | Protocol/checksum, package versions, parameter source, numerical comparisons and terminations |
| `measurement-residuals.csv` | Prediction minus measurement and current mismatch, when measurements were supplied |

The reference case conserved integrated charge: 600 s at 2.5 A yielded 0.4166667 Ah, then equal
charge returned net discharge capacity to zero. Voltage stayed within the Chen2020 limits in this
case. Tightening tolerances changed voltage by about 1 microvolt; doubling mesh from 20 to 40
points changed it by about **2.17 mV**, so claiming sub-millivolt mesh accuracy would be unjustified.
A separate real DFN test stopped at the requested 3.9-V event and verified its charge integral.
Native tests also exercise charge cutoff, infeasible discharge, capacity-to-current conversion,
and replay of the exported SOC-adjusted parameters without reinitializing SOC.
The frozen reference is numerical regression evidence, not measured-cell validation.

## Primary references

- [PyBaMM experiment API examples](https://docs.pybamm.org/en/pybamm-v26.9.0.0/source/examples/notebooks/getting_started/tutorial-5-run-experiments.html)
- [Mesh refinement workflow](https://docs.pybamm.org/en/pybamm-v26.9.0.0/source/examples/notebooks/getting_started/tutorial-9-changing-the-mesh.html)
- [IDAKLU solver options](https://docs.pybamm.org/en/pybamm-v26.9.0.0/source/api/solvers/idaklu_solver.html)
- [Release source and changes](https://github.com/pybamm-team/PyBaMM/blob/pybamm-v26.9.0.0/CHANGELOG.md)

The linked release manuals, bundled helper, parameter serialization and optional DataLoader
recipe in the reference were verified against PyBaMM 26.9.0.0.
