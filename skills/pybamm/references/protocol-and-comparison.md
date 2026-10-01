# Protocol and curve contract

The helper accepts `model` (`SPM` or `DFN`), `parameter_set` (an installed PyBaMM set),
`initial_soc` in (0,1], positive `temperature_K`, positive `sample_period_s`, a nonempty `steps`
list, and optional numeric `parameter_overrides`. Unknown fields are rejected; there is no implicit
`cycles` or repeated-cycle option. Repeat the desired steps explicitly when needed. The example
set Chen2020 is tested; other sets require chemistry/geometry compatibility checks.

Each step contains `kind` and positive `duration_s`. `charge` and `discharge` also require positive
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
overrides of initial/ambient temperature are rejected to avoid contradictory settings. Existing
numeric PyBaMM parameter keys may be overridden, and the full effective values are serialized.
Do not use `parameter_overrides` to inject functions or arbitrary executable code.

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
samples, not the adaptive solver's internal step size.

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
