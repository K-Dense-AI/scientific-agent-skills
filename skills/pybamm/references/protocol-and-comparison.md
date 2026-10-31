# Protocol and curve contract

The helper accepts `model` (`SPM` or `DFN`), `parameter_set` (an installed PyBaMM set),
`initial_soc` in (0,1], positive `temperature_K`, positive `sample_period_s`, a nonempty `steps`
list, and optional numeric `parameter_overrides`. Unknown fields are rejected; there is no implicit
`cycles` or repeated-cycle option. Repeat the desired steps explicitly when needed. The example
set Chen2020 is tested; other sets require chemistry/geometry compatibility checks.

The root, each step and `parameter_overrides` must be JSON objects. Each step contains `kind`
and positive `duration_s`. `charge` and `discharge` also require positive
`c_rate`, and may contain `until_voltage_V` within the set's lower/upper cutoffs. `rest` has no rate
or cutoff. A sample period cannot exceed a step's duration. For example:

```json
{
  "kind": "discharge",
  "c_rate": 0.5,
  "duration_s": 3600,
  "until_voltage_V": 3.0
}
```

Current is ±C-rate times nominal Ah capacity. All duration and timestamp values are seconds;
temperatures are Kelvin, never Celsius. Use `temperature_K` for the uniform isothermal setting;
overrides of initial/ambient temperature are rejected to avoid contradictory settings. The helper
is single-cell only: the series-cell count must be one. Upstream voltage step events use
`Battery voltage [V]`, while the exported `Voltage [V]` is cell voltage; these differ in a string
of cells. Nominal capacity changes the C-rate-to-current conversion, not the electrode geometry
or active material inventory. Reconcile those independently when reparameterizing a cell.

Existing scalar numeric PyBaMM parameters may be overridden; functional OCP and transport laws
cannot be replaced through this helper. `Current function [A]` overrides and initial electrode
concentration overrides are rejected because the experiment and `initial_soc` would replace them.
Use the exact installed parameter keys (`list(parameters.keys())`); current upstream
`ParameterValues.update()` permits new keys, so it is not itself a typo detector. The helper
explicitly checks membership. Do not inject functions or executable code through JSON.

`initial_soc` sets electrode concentrations through PyBaMM's parameterization-dependent initial
state solver; it is not a universal concentration multiplier or a guarantee of feasible terminal
voltage under load. A discharge cutoff must lie below the loaded starting voltage; a charge cutoff
must lie above it. `skip_ok=False` rejects an already-satisfied step condition. The helper accepts
SOC in (0,1] as a deliberately narrower contract than upstream's [0,1].

`parameters.json` serializes `simulation.parameter_values` after `solve(initial_soc=...)`, using
`ParameterValues.to_json()`. The original parameter object still has its original concentrations
and must not be mistaken for that snapshot. Load the snapshot with
`pybamm.ParameterValues.from_json(path)`; retain the protocol because each step overrides the base
`Current function [A]`. It is a parameter snapshot, not a saved solution or a model definition.

Voltage holds (CCCV), power control, thermal dynamics and degradation are available in upstream
PyBaMM but are outside this helper's tested protocol. Extend using the upstream step APIs and test
against a physically appropriate case rather than translating a voltage hold into constant current.

## Numerical comparisons

The baseline uses IDAKLU `rtol=1e-6, atol=1e-8`; the tightened run uses `1e-8, 1e-10`. Both use the
same mesh. The third run doubles all `x_n,x_s,x_p,r_n,r_p` point counts at the tightened tolerances.
Only relevant spatial dimensions enter each model (SPM and DFN use different physics).

Voltage is compared at 101 positions over the shared elapsed interval of each corresponding step.
This avoids interpolating across a current discontinuity. Event duration differences are reported
separately because cutoff shifts change later absolute step times. Always check these alongside the
voltage metric, especially near a steep end-of-discharge drop. The output period controls saved
samples, not the adaptive solver's internal step size. For a duration not divisible by the period,
26.9.0.0 distributes samples uniformly over the duration using a rounded point count, so the
spacing need not equal the requested period exactly. Read the actual time column. The comparisons
interpolate saved samples; also reduce the output period when interpolation error could dominate.

`net_discharge_capacity_Ah` integrates signed current. It decreases during charging and is not
cumulative charge throughput, remaining capacity, a cycle count, or measured state of health.

## Measured curves

The CSV has exactly:

```csv
time_s,voltage_V,current_A
0,3.98,2.5
120,3.93,2.5
300,3.90,2.5
```

Require finite values and strictly increasing time. These rows are illustrative, not measured data.
Convert raw instrument units and polarity explicitly upstream and retain their provenance. The
helper interpolates the baseline at measurement times only inside the simulated interval; it never
extrapolates. If only an overlapping segment is intended, select and document that segment upstream.

Align experiment start from acquisition evidence; do not optimize a time shift solely to improve
fit unless that is an explicit fitting parameter with uncertainty. Samples right at a current switch
can represent either side of an instantaneous ohmic change; align acquisition semantics and inspect
the current-difference column before comparing those voltages. RMSE gives each supplied sample equal
weight, so oversampling a long rest changes its contribution. Resample deliberately if a time-weighted
or phase-balanced score is desired, and retain the original curve.

Report residual structure across charge, rest and discharge, not just a single score. Temperature,
SOC, capacity calibration and hysteresis can dominate mismatches. Parameter fitting should compare
identifiability and uncertainty against independent experiments rather than treating a lower error
on the same curve as sufficient validation.

## Optional upstream datasets

For a public reference dataset, PyBaMM 26.9.0.0 exposes `DataLoader()` with no version argument,
`show_registry()` returning a filename list, and `get_data(filename)` returning a local `Path`.
There is no `fetch_data()` method. The shipped loader pins the **separate data release v1.0.2**
and uses Pooch to cache and verify each file against its registered SHA-256 hash.

```python
import hashlib
import pybamm

loader = pybamm.DataLoader()
filename = "Ecker_1C.csv"
assert filename in loader.show_registry()
path = loader.get_data(filename)
print(loader.version, path.name, hashlib.sha256(path.read_bytes()).hexdigest())
```

This recipe fetched the 1,049-byte public file and verified hash
`428dc5113a6430492f430fb9e895f67d3e20f5643dc49a1cc0a922b92a5a8e01` on the review date.
The network operation is an unauthenticated HTTPS GET of the release asset at
`https://github.com/pybamm-team/pybamm-data/releases/download/v1.0.2/Ecker_1C.csv`, which may
redirect to GitHub's asset storage. It returns file bytes, not a paginated JSON API. An unknown
filename raises `ValueError` before fetching; network or checksum failures are not missing data.
Do not edit loader internals to invent a dataset-version constructor option.

Ecker data concerns a Kokam cell, not the Chen2020 LG M50 example. This file has two headerless
columns and lacks the helper's required current column. Check the source experiment and units
before constructing a comparison CSV; downloading and hashing it does not validate a model.
The bundled helper does not fetch datasets automatically.

## Release contracts

- [Step units, skip behavior and voltage terminations](https://docs.pybamm.org/en/pybamm-v26.9.0.0/source/api/experiment/experiment_steps.html)
- [Simulation API](https://docs.pybamm.org/en/pybamm-v26.9.0.0/source/api/simulation/simulation.html)
- [Parameter updates, initial state and JSON serialization](https://docs.pybamm.org/en/pybamm-v26.9.0.0/source/api/parameters/parameter_values.html)
- [DataLoader API](https://docs.pybamm.org/en/pybamm-v26.9.0.0/source/api/pybamm_data.html)
- [Versioned data registry source](https://github.com/pybamm-team/PyBaMM/blob/pybamm-v26.9.0.0/packages/pybamm/src/pybamm/pybamm_data.py)
