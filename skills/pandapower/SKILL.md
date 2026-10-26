---
name: pandapower
description: Runs AC power flow on transmission and distribution networks with pandapower, reports bus voltages, line and transformer loadings, losses and limit violations, and screens N-1 branch outages for islanding and post-contingency overloads. Use for load-flow studies, voltage and thermal limit checks, contingency screening, and validating a network case expressed in kV, MW, Mvar and per-unit.
license: MIT
compatibility: Requires Python 3.12 and pandapower 3.5.6 with its NumPy, pandas, SciPy and networkx dependencies. Network is needed for installation only; bundled cases run locally with no credentials. numba is optional and deliberately disabled for determinism.
metadata:
  version: "1.0"
  skill-author: william-xue
  upstream-version: "3.5.6"
  last-reviewed: "2026-10-20"
---

# Power flow and N-1 screening with pandapower

## When to use

Use this skill to answer questions a solved AC load flow answers: what the bus
voltages are under a given dispatch, which line or transformer is the binding
thermal constraint, how much active power the network loses, and what a single
branch outage would do to voltages, loadings, or connectivity. It handles
balanced positive-sequence steady state only — one slack (external grid), PV
generators, constant-power loads, static generators, AC lines and two-winding
transformers.

Do not use it for unbalanced or three-phase faults, short-circuit ratings,
dynamics, or economic dispatch. pandapower ships those solvers (`shortcircuit`,
`runopp`, `runpp_3ph`); this helper exercises only `runpp`, so state explicitly
when a question needs one of the others instead of stretching a load flow to
cover it.

## Runtime and tested case

```bash
uv venv --python 3.12 pf-env
uv pip install --python pf-env/bin/python "pandapower==3.5.6"
```

Verified on Python 3.12.11 with pandapower 3.5.6, NumPy 2.4.6, pandas 2.3.3 and
SciPy 1.18.1. numba is not required: the helper calls
`pp.runpp(..., numba=False)` so results do not depend on whether llvmlite is
installed and the run does not print pandapower's numba warning. Refer to the
**v3.5.6** documentation links below; `latest` documents unreleased APIs.

## Case contract

A case is one JSON file in engineering units: kV for nominal voltages, MW and
Mvar for injections, km plus ohm/km for lines, percent for transformer
impedances. Field-by-field rules, units and defaults are in
[references/case-format.md](references/case-format.md).

```json
{
  "buses": [{"id": "B1", "vn_kv": 110}],
  "ext_grids": [{"bus": "B1", "vm_pu": 1.02}],
  "loads": [{"bus": "B1", "p_mw": 15, "q_mvar": 5}]
}
```

`assets/case-6bus-ring.json` is a worked 5-bus, 110/10 kV example: a 110 kV ring
fed by one external grid, a 30 MW PV generator, and a 40 MVA transformer
supplying a 10 kV load bus.

## Workflow

1. **Fix the electrical skeleton first.** Every bus needs its nominal voltage;
   every branch needs both ends, a length and an impedance; the case needs at
   least one external grid. A case that silently mixes 110 kV and 10 kV buses
   without a transformer will either diverge or produce nonsense voltages, so
   check the topology before reading any result.
2. **Separate the slack from the PV buses.** The external grid sets the slack
   voltage; generators are PV buses with a voltage setpoint and, optionally,
   reactive limits. If no generator is given a `min_q_mvar`/`max_q_mvar` pair,
   its reactive output is unconstrained — say so when the study is about
   reactive capability.
3. **Run the power flow and read convergence before numbers.** Non-convergence
   usually means an infeasible case (islanded bus, impossible voltage setpoint,
   branch parameter error), not a solver setting to loosen. A bus with `n/a`
   voltage in the report is de-energized, i.e. no path back to a voltage source.
4. **Check limits that match the question.** Voltage bands are a study
   assumption, not a physical constant: pass `--vm-min`/`--vm-max` for the
   voltage level you are studying (0.95–1.05 pu is the default). Thermal limits
   come from `max_i_ka` per line and `sn_mva` per transformer; loading above the
   `--loading-limit` (100% default) is reported as an overload.
5. **Screen N-1 as a screening step, not a compliance claim.** `--n1` trips each
   line and transformer in turn. It answers "does this single outage violate a
   limit or island a bus" for the given case and limits. It does not cover
   multiple outages, protection behaviour, or remedial action, and it caps the
   number of screenings (`--max-n1`, default 40, must be >= 1) on large
   networks. The report states how many contingencies were screened out of how
   many branches, so a capped run is never read as a complete one.
6. **Report the assumptions with the numbers.** MVA base, voltage limits,
   loading limit, slack setpoint and the pandapower version all change the
   answer's meaning; the JSON report records each of them.

## Run and inspect

```bash
pf-env/bin/python scripts/run_power_flow.py assets/case-6bus-ring.json
pf-env/bin/python scripts/run_power_flow.py assets/case-6bus-ring.json \
  --n1 --json-out ring-report.json
pf-env/bin/python scripts/run_power_flow.py case.json \
  --vm-min 0.97 --vm-max 1.03 --loading-limit 90
```

Exit codes: `0` converged with no violation, `2` converged but at least one
limit violation (or an N-1 finding), `3` invalid arguments, invalid case or
non-convergent solve.
The JSON report holds `versions`, `limits`, `power_flow` (buses, branches,
violations, summary) and, with `--n1`, one entry per outage.

Reference run of the bundled case (`--n1`, measured on the versions above):

| Quantity | Value |
| --- | --- |
| Iterations | 3 |
| Bus voltages (pu) B1 / B2 / B3 / B4 / B5 | 1.0200 / 1.0100 / 1.0076 / 1.0113 / 0.9974 |
| Highest loading | transformer T45, 31.80% |
| Active losses | 0.1769 MW |
| N-1, line L23 out | converges, min voltage 0.99176 pu, max loading 46.19% |
| N-1, transformer T45 out | B5 is de-energized, exit code 2 |

The 10 kV bus sits 0.26% below nominal with the transformer at 31.8% loading,
and stays inside the default band; the same case with the 10 kV load raised to
20 MW and line limits tightened (`tests/pandapower/fixtures/case-overload.json`)
puts L23 at 177.55%, L12 at 143.16% and L14 at 116.21% — exit code 2 with three
overloads. Both numbers are regression-checked, not illustrative.

## Traps worth knowing

- **Transformer and line result tables do not share column names.** Lines report
  `p_from_mw`/`q_from_mvar`/`p_to_mw`; two-winding transformers report
  `p_hv_mw`/`q_hv_mvar`/`p_lv_mw`. Reading `p_from_mw` on `res_trafo` raises
  `KeyError`, which is easy to mistake for a missing result.
- **An isolated bus is `NaN`, not zero.** After an outage that cuts a bus off,
  `res_bus.vm_pu` is `NaN`; a plain `vm < limit` comparison then reads as "not
  undervoltage" and the bus disappears from the study. The helper reports such a
  bus as `de_energized` and counts it in the summary.
- **`c_nf_per_km` is capacitance in nanofarads per kilometre**, not per unit
  length in SI. Leaving it at 0 makes short lines look slightly inductive; for
  long 110 kV or 220 kV lines it changes charging and voltage profile
  materially.
- **Transformer `vk_percent`/`vkr_percent` are percentages on the transformer's
  own `sn_mva`**, and `vn_hv_kv`/`vn_lv_kv` are winding ratings, not bus
  voltages. Mixing them up rescales the impedance by the square of the ratio.
- **Slack and PV buses decide feasibility.** A case with two external grids is
  over-determined for this helper's purposes; a case with none, or with a
  generator whose voltage setpoint cannot be met, is not a numerical problem to
  tune around.

## Primary references

- [pandapower v3.5.6 documentation](https://pandapower.readthedocs.io/en/v3.5.6/)
- [Line element parameters](https://pandapower.readthedocs.io/en/v3.5.6/elements/line.html)
- [Two-winding transformer parameters](https://pandapower.readthedocs.io/en/v3.5.6/elements/trafo.html)
- [AC power flow and solver options](https://pandapower.readthedocs.io/en/v3.5.6/powerflow/ac.html)
