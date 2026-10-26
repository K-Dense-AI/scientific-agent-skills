# Case file format

One JSON object. Only `buses`, `ext_grids`, `loads` and either `lines` or
`trafos` are needed for a solvable case; every other section may be omitted.
Unknown keys are ignored, so a case can carry notes without breaking the run.

```json
{
  "name": "6bus-110kv-ring-demo",
  "base_mva": 100,
  "buses": [{"id": "B1", "vn_kv": 110}],
  "ext_grids": [{"id": "GRID", "bus": "B1", "vm_pu": 1.02, "va_degree": 0}],
  "gens": [{"id": "G1", "bus": "B2", "p_mw": 30, "vm_pu": 1.01,
            "min_q_mvar": -40, "max_q_mvar": 40}],
  "sgens": [{"id": "PV1", "bus": "B3", "p_mw": 5, "q_mvar": 0}],
  "loads": [{"id": "LD3", "bus": "B3", "p_mw": 25, "q_mvar": 8}],
  "lines": [{"id": "L12", "from": "B1", "to": "B2", "length_km": 20,
             "r_ohm_per_km": 0.06, "x_ohm_per_km": 0.30, "c_nf_per_km": 10,
             "max_i_ka": 0.45, "parallel": 1}],
  "trafos": [{"id": "T45", "hv_bus": "B4", "lv_bus": "B5", "sn_mva": 40,
              "vn_hv_kv": 110, "vn_lv_kv": 10, "vk_percent": 12,
              "vkr_percent": 0.4, "pfe_kw": 30, "i0_percent": 0.1}]
}
```

## Top level

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `name` | string | file stem | Label used in the report |
| `base_mva` | number | `100` | System MVA base. pu quantities in the report are relative to voltages, not to this base, but per-unit impedances inside pandapower are. |
| `buses` | array | required | Nodes, see below |
| `ext_grids` | array | required | Slack sources. One is the normal case; more than one over-constrains the study. |
| `gens` | array | `[]` | PV generators with a voltage setpoint |
| `sgens` | array | `[]` | Static generators (fixed P, Q) — solar, wind, must-run injection |
| `loads` | array | `[]` | Constant-power loads |
| `lines` | array | `[]` | AC overhead/underground lines |
| `trafos` | array | `[]` | Two-winding transformers |

## Buses

| Field | Type | Unit | Meaning |
| --- | --- | --- | --- |
| `id` | string | — | Unique name; every other section refers to buses by this string |
| `vn_kv` | number | kV | Nominal (rated) voltage of the bus, line-to-line |

`vm_pu` and `va_degree` are results, not inputs, except on `ext_grids` and
`gens`.

## External grids (slack)

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `bus` | string | required | Bus the grid connects to |
| `vm_pu` | number | `1.0` | Slack voltage setpoint |
| `va_degree` | number | `0.0` | Slack angle reference |
| `id` | string | `ext{i}` | Label |

## Generators (PV buses)

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `bus` | string | required | Terminal bus |
| `p_mw` | number | required | Active power injection (positive = generation) |
| `vm_pu` | number | `1.0` | Voltage setpoint held by the generator |
| `min_q_mvar`, `max_q_mvar` | number | unset | Reactive limits. Omit both for an unconstrained machine, and say so when the study is about reactive capability. |

## Static generators and loads

`p_mw` and `q_mvar` are signed injections at the bus. For loads, `p_mw` is the
consumption (positive numbers, as usual in a case file); the helper passes them
to `create_load`, which applies them as consumption. A static generator with
`p_mw: 5` injects 5 MW.

## Lines

| Field | Type | Unit | Meaning |
| --- | --- | --- | --- |
| `from`, `to` | string | — | Terminal buses |
| `length_km` | number | km | Route length |
| `r_ohm_per_km`, `x_ohm_per_km` | number | ohm/km | Series resistance and reactance per kilometre, per circuit |
| `c_nf_per_km` | number | nF/km | Shunt capacitance per kilometre; `0` disables charging |
| `max_i_ka` | number | kA | Thermal current limit; drives `loading_percent` |
| `parallel` | integer | `1` | Number of identical circuits in parallel |

`loading_percent` is the maximum of the from- and to-end current divided by
`max_i_ka` (times `parallel`), so it is a current-based thermal loading rather
than an apparent-power loading.

## Two-winding transformers

| Field | Type | Unit | Meaning |
| --- | --- | --- | --- |
| `hv_bus`, `lv_bus` | string | — | High- and low-voltage terminals |
| `sn_mva` | number | MVA | Rated power; the base for `vk_percent`, `vkr_percent`, `i0_percent` |
| `vn_hv_kv`, `vn_lv_kv` | number | kV | Winding rated voltages, not the connected bus voltages |
| `vk_percent` | number | % | Short-circuit voltage |
| `vkr_percent` | number | % | Real (resistive) part of the short-circuit voltage |
| `pfe_kw` | number | kW | Iron (no-load) losses |
| `i0_percent` | number | % | No-load current |

With the magnetising branch given only by `pfe_kw` and `i0_percent`, the
transformer is modelled as the standard T equivalent used by pandapower's
`create_transformer_from_parameters`.

## Validation

Numeric fields are checked before any pandapower object is created, because a
bad number otherwise surfaces as a solver symptom (a singular matrix, an
`invalid value encountered in divide`, or "did not converge after 10
iterations") that hides the actual cause. A rejected run prints one
`[FAIL] invalid case: <section>[<index>].<field>: ...` line and exits `3`.

- Every number must be a finite JSON number. `NaN`, `Infinity`, `-Infinity`
  and strings are rejected; Python's `json` accepts the first three as
  literals, so they are a realistic transcription error.
- `vn_kv`, `length_km`, `x_ohm_per_km`, `max_i_ka`, `parallel`, `sn_mva`,
  `vn_hv_kv`, `vn_lv_kv`, `vk_percent`, `vm_pu` and `base_mva` must be positive;
  `r_ohm_per_km`, `c_nf_per_km`, `pfe_kw` and `i0_percent` may be zero but not
  negative.
- `parallel` must be a whole number and `vkr_percent` must be smaller than
  `vk_percent`.

The limit flags are checked the same way: `--max-n1` must be `>= 1`,
`--vm-min`/`--vm-max` must be finite, positive and ordered
(`0 < vm_min < vm_max`), and `--loading-limit` must be finite and positive.
These also exit `3`, with `[FAIL] invalid arguments: ...`.

## Not modelled by this helper

Three-winding transformers, shunts, SVC/STATCOM, DC lines, switches and
`in_service` flags in the input file are outside the contract. Add them to the
generated network in Python if a study needs them — `run_power_flow.py` builds
the network in `build_network()`, which is safe to import and extend.

## Report shape

```text
versions      pandapower / numpy / pandas versions used for the run
limits        vm_min_pu, vm_max_pu, loading_percent actually applied
power_flow
  converged      true when runpp returned a solution
  iterations     Newton-Raphson iterations reported by the solver
  buses          [{bus, vn_kv, vm_pu (null = de-energized), va_degree}]
  branches       [{element, loading_percent, p_from_mw, q_from_mvar}]
  violations     [{element, quantity, value, limit, kind}]
  summary        vm_min_pu, vm_max_pu, de_energized_buses,
                 max_loading_percent, p_loss_mw
n1            (only with --n1)
  screenings   [{outage, converged, violations, vm_min_pu,
                 de_energized_buses, max_loading_percent, worst[]}]
  targets_total, screened, skipped
  non_converged, with_violations
```

`screened`/`targets_total`/`skipped` make a truncated screening explicit: when
`--max-n1` is smaller than the number of branches, the summary line reads
`N-1: 2/5 outages screened, 3 skipped by --max-n1` instead of silently
reporting fewer contingencies as a complete result.

Violation `kind` is one of `undervoltage`, `overvoltage`, `overload`,
`de_energized` and — appended to `power_flow.violations` when any screening
fails — `n1_failure`. `value` is `null` for a de-energized bus, because
pandapower reports `NaN` there.
