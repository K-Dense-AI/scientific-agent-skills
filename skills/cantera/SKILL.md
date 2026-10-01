---
name: cantera
description: Runs Cantera homogeneous chemical reactors and evaluates ignition delay with mechanism provenance, conservation checks, and numerical refinement. Use for combustion kinetics, closed adiabatic ideal-gas constant-volume or constant-pressure ignition, temperature histories, or mechanism-specific ignition-delay comparisons.
license: MIT
compatibility: Requires Python 3.12-3.14, Cantera 3.2.0, and NumPy. Installation needs network access; simulations run locally without credentials. Custom mechanisms must be available as Cantera YAML files.
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
  tested-package-version: "3.2.0"
  last-reviewed: "2026-09-30"
---

# Cantera: homogeneous ignition calculations

## When to use

Use for a closed, adiabatic, homogeneous ideal-gas reactor with a known kinetic mechanism,
initial temperature, pressure, and mole composition. The bundled helper runs both constant
volume and constant pressure cases and reports a precisely defined temperature-based delay.
It is not a flame solver or a general reactor-network builder.

A calculation completing successfully establishes numerical execution, not mechanism
validity for the fuel, pressure, temperature, diluent, or measured ignition observable.
Read [references/interpretation.md](references/interpretation.md) when choosing a mechanism,
comparing experiments, or interpreting unresolved/two-stage ignition.

## Workflow

1. Identify the mechanism and its validated condition range. Preserve its source, version,
   citation, and any modifications. Check that its phase is `ideal-gas` and that every
   reactant, diluent, and tracked species exists. For custom YAML with imports, retain the
   original dependency files as well as the generated phase snapshot. Custom Python rate
   extensions additionally need their original code and environment for replay.
2. Choose constant volume or constant pressure from the physical experiment. Supply K,
   Pa, seconds, and mole amounts explicitly. `mole_amounts` is normalized to mole fractions;
   it is not a mass-fraction mapping. The report includes the normalized initial composition.
3. Copy [assets/hydrogen-ignition.json](assets/hydrogen-ignition.json) and change its conditions.
   The supplied H2/O2/Ar case uses Cantera's bundled `h2o2.yaml` for an executable numerical
   example; it is not a recommendation for every hydrogen experiment.
4. Set a time horizon long enough to observe the temperature rise and the decline of the
   heating-rate peak. Choose output spacing fine enough to locate that peak. Set a minimum
   temperature rise to distinguish ignition from negligible heating or numerical noise.
5. Run the helper and inspect all four histories and the report. Refine again if the delay
   changes materially, if the maximum approaches a time boundary, or if conservation fails.
   Compare the temperature and tracked-species histories with the actual ignition definition.
6. Report the condition set, mechanism hash, reactor constraint, delay definition, output
   spacing, numerical changes, and scientific limits together with the delay.

## Execute the tested example

From the collection root:

```bash
uv run --no-project --python 3.12 --with cantera==3.2.0 --with numpy==2.5.3 \
  python skills/cantera/scripts/ignition_delay.py \
  skills/cantera/assets/hydrogen-ignition.json hydrogen-result
```

Tested on Python 3.12, Cantera 3.2.0, and NumPy 2.5.3. No external solver executable or
credentials are needed. Local relative mechanism paths resolve against the configuration
file directory before Cantera's built-in data search. Use a new output directory each run.

The 1000 K, 101325 Pa, H2:O2:Ar = 2:1:7 constant-volume example gives about **0.313 ms**
using the stated `max(dT/dt)` definition. At 3 ms its temperature is approximately
2920.67 K and agrees with a separate `UV` equilibrium calculation. These are package
regression values, not experimental validation data.

## Exact delay and refinement contract

Delay is the time of the global maximum of `numpy.gradient(T, time, edge_order=2)` on
a uniform output grid. It is reported only if the maximum temperature rise reaches
`minimum_temperature_rise_k` and the maximum is at least two sample indices from each
boundary. Otherwise `delay_s` is null and a status explains why. No delay beyond the
simulation horizon is extrapolated.

The helper explicitly uses Cantera 3.2's `clone=True` and reads evolving properties from
`reactor.phase`. The original `Solution` retains the initial state; do not read it as
the reactor's final state. `ReactorNet.advance(t)` requests an absolute time, and no
advance limits are configured, so the output grid remains uniform.

It runs four independent fresh reactors:

| Run | Change from configured conditions |
| --- | --- |
| baseline | Original settings |
| finer_output | Half output spacing, same horizon and solver controls |
| tighter_solver | Both solver tolerances divided by ten; maximum internal time step halved |
| longer_horizon | Twice the horizon with the original output spacing |

`numerically_resolved` requires all runs to yield delays, relative delay changes within
`delay_relative_tolerance`, and all conservation checks to pass. Agreement on a discrete
grid is not a statistical error bar: also report the output spacing. The baseline samples
must be between 11 and 50000, leaving room for refinement. Runtime grows with mechanism
size, stiffness, and the chosen horizon; integration failures retain Cantera's error text.

## Outputs and checks

- `report.json`: all input settings, package versions, configuration and mechanism hashes,
  normalized starting composition, four delay estimates, numerical changes, conservation,
  and mechanism thermodynamic temperature bounds.
- `baseline.csv`, `finer_output.csv`, `tighter_solver.csv`, `longer_horizon.csv`: time,
  temperature, pressure, volume, mass, total internal energy, total enthalpy, and requested
  species mole fractions.
- `mechanism.yaml`: a Cantera-written snapshot of the loaded phase, species, and reactions.
  The helper requests `write_yaml(precision=17)` and saves the exact UTF-8 bytes it hashes,
  without platform newline conversion. The report also hashes the located original
  mechanism file. Imported source dependencies are not separately hashed; the snapshot
  captures the loaded model. Its generated header includes a date, so the snapshot hash
  identifies the saved artifact and need not match between otherwise identical reruns.

Closed reactors conserve mass and elemental mass fractions. The constant-volume case
checks total internal energy; the constant-pressure case checks total enthalpy. Energy
error is divided by `max(abs(initial_energy_J), 1 J)`. Diagnostic tolerances are mass
relative drift <1e-8, elemental absolute drift <1e-8, energy scaled drift <1e-6, species
mass-fraction sum error <1e-8, and species mass fractions >-1e-10. These checks expose
numerical issues and do not measure kinetic-model uncertainty.

Check `within_thermo_temperature_range` separately: it checks saved output states, not
every internal integration state. Numerical resolution does not mean species thermodynamic
fits stayed within their temperature bounds. The helper cannot assess pressure-dependent
kinetic validity from these bounds.

## Scope and upstream references

The suite covers both reactor constraints, conservation, final-state agreement with
independent Cantera equilibrium, nonigniting conditions, unresolved boundary maxima,
refinement, snapshot replay, and invalid composition/conditions. It does not validate
shock-tube heat loss, real-gas effects, surfaces, flow devices, flames, or multistage
experimental ignition definitions. Build those models only with the necessary physics
and their own checks; do not relabel this helper's result as one of them.

- [Reactor model equations](https://cantera.org/stable/reference/reactors/index.html)
- [Python reactor API](https://cantera.org/stable/python/zerodim.html)
- [Thermodynamic properties and equilibrium](https://cantera.org/stable/python/thermo.html)
- [Phase serialization API](https://cantera.org/stable/python/importing.html#cantera.Solution.write_yaml)
- [Custom extension registration](https://cantera.org/stable/python/utilities.html#cantera.extension)
- [Cantera 3.2 release notes](https://cantera.org/stable/reference/releasenotes/v3.2.html)
- [Upstream ignition example](https://cantera.org/stable/examples/python/reactors/non_ideal_shock_tube.html)
  uses a species mass-fraction peak; its delay definition differs from this helper's dT/dt peak.
