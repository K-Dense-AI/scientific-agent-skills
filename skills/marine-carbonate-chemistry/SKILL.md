---
name: marine-carbonate-chemistry
description: Solves seawater carbonate chemistry with PyCO2SYS for chemical oceanography, ocean acidification, and marine carbon-cycle research. Use for paired total alkalinity, dissolved inorganic carbon, pH, or seawater pCO2/fCO2 measurements; carbonate speciation; aragonite and calcite saturation; Revelle factors; lab-to-in-situ temperature and pressure corrections; and measurement uncertainty propagation. Applies to carbonate-system calculations, not general aqueous speciation or air-sea gas-flux estimation.
license: MIT
compatibility: Requires Python 3.13 with PyCO2SYS 1.8.3.4 and NumPy. Network access is needed only to install packages or obtain external data; bundled calculations run locally without credentials.
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
  upstream-version: "PyCO2SYS 1.8.3.4"
---

# Marine Carbonate Chemistry

Turn two independent seawater carbonate measurements into a reproducible speciation
table, mineral saturation estimates, and a record of the calculation assumptions.
Targets **PyCO2SYS 1.8.3.4**, tested with Python 3.13 and NumPy 2.5.1. The PyCO2SYS
v2 beta uses a different implementation; do not mix its examples with this pin.

## When to use

- Analyze bottle samples, shipboard carbonate measurements, or acidification experiments.
- Calculate total-scale pH, seawater pCO2/fCO2, carbonate ion, aragonite/calcite
  saturation state, or the Revelle factor from a valid measured pair.
- Convert a system determined at laboratory conditions to specified ocean conditions.
- Quantify how stated measurement uncertainties affect the calculated results.

This workflow concerns seawater carbonate equilibria. Freshwater, porewaters with
substantial uncharacterized alkalinity, brines outside the selected calibration range,
and reaction/transport models require additional chemistry and validation. Do not
infer an air-sea flux or atmospheric carbon removal from a carbonate equilibrium alone.

## Establish the measurement contract

Before running a solver, identify the two measured variables, their units, quality flags,
and their temperature/pressure basis. Retain a separate source table containing station,
depth, timestamps, methods, reference materials, and original QC codes, joined by sample ID.
Do not turn missing values or rejected measurements into zero.

| Quantity | Required convention |
|---|---|
| Total alkalinity (TA), DIC, nutrients | micromol per **kg seawater**, not per litre or kg water |
| Salinity | Practical Salinity, not Absolute Salinity in g/kg |
| Temperature | In-situ/measurement temperature in degrees Celsius, not potential or Conservative Temperature |
| Pressure | Sea pressure in dbar; surface sample is 0, not 1 atmosphere |
| pH | Declared total, seawater, free, or NBS scale, at the declared measurement conditions |
| pCO2 / fCO2 | Seawater partial pressure / fugacity in microatm; these are distinct quantities |

TA and DIC remain constant during the solver's temperature/pressure conversion for a
closed sample. pH and gas parameters change. Two inputs measured at different conditions
cannot simply share one `temperature` value. Establish a consistent measurement basis
first. Temperature correction does not repair sample changes caused by gas exchange,
biology, evaporation, or mineral dissolution/precipitation.

Use two independent carbonate parameters. pCO2 plus fCO2 is not an independent pair.
Three or more measurements enable an overdetermination check: solve independent pairs
and compare predicted versus measured third parameters, including their uncertainty.
Do not average inconsistent solutions to hide a calibration or scale mismatch.

## Install

Create a dedicated environment in the user's working directory:

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python "PyCO2SYS==1.8.3.4" "numpy==2.5.1"
```

On Windows the environment's interpreter is `.venv/Scripts/python.exe`. The commands
below use the POSIX interpreter path. Set the shell variable `SKILL_DIR` to this installed
skill's directory. Keep inputs and generated outputs in the working directory.

## Workflow

1. **Prepare paired measurements.** Use the schema in
   [references/input-and-results.md](references/input-and-results.md). Resolve units and
   quality flags before creating the input file. Supply phosphate and silicate explicitly;
   zero is an assumption to justify, not a missing-data code.
2. **Choose equilibrium constants.** Read
   [references/chemistry-decisions.md](references/chemistry-decisions.md) for pH scales,
   carbonic-acid constants, borate, saturation interpretation, and uncertainty limits.
   Match the study's validated convention and report it. The helper supports carbonic-acid
   options 10 and 15; other systems require a separately verified direct PyCO2SYS call.
3. **Solve with `scripts/solve_carbonate.py`.** It validates the full input table, solves
   the pair, checks finite outputs and DIC species balance, then writes `carbonate.csv`
   and `provenance.json` into a new output directory.
4. **Review flags and consistency.** Inspect input and output calibration-range flags,
   carbonate balance, measured-third-parameter residuals when available, and controls.
   A successful solve does not validate the sample, constants, or measurement method.
5. **Report at the intended conditions.** Results ending `_out` describe the supplied
   output temperature/pressure. Unsuffixed results describe input conditions. Include
   parameter pair, pH scale, units, constants, nutrient assumptions, uncertainty scope,
   software versions, and excluded/flagged samples with the result table.

## Worked example: closed-sample condition correction

The following values are synthetic, not field observations. Save this as `samples.csv`
in a working directory. The two samples differ only in DIC; the second represents a
fixed-alkalinity CO2-addition comparison. Their measurements are at 25 C and 0 dbar;
results are also requested at 10 C and 1000 dbar.

```csv
sample_id,par1,par2,salinity,temperature,pressure,total_phosphate,total_silicate,temperature_out,pressure_out,u_par1,u_par2
baseline,2300,2000,35,25,0,0,0,10,1000,2,2
added_co2,2300,2100,35,25,0,0,0,10,1000,2,2
```

Run from that working directory:

```bash
.venv/bin/python "$SKILL_DIR/scripts/solve_carbonate.py" samples.csv \
  --par1-type alkalinity --par2-type dic --k-carbonic 10 \
  --output-dir carbonate-results
```

For the baseline, the tested version gives input-condition total pH **8.045886**,
pCO2 **396.958 microatm**, and aragonite saturation **3.386201**. At the specified output
conditions, total pH is **8.241241** and aragonite saturation **2.605691**. These rounded
values are regression checks for this exact setup, not universal seawater benchmarks.
With independent 2 micromol/kg uncertainties in TA and DIC only, `u_pH_total` is about
**0.004580**. This excludes equilibrium-constant and other input uncertainty.

For TA + measured pH, use `--par2-type ph --ph-scale total` only if the source explicitly
identifies total-scale pH; replace `par2` and `u_par2` with the measured pH and its absolute
standard uncertainty. A column named merely `pH` is insufficient to establish its scale.

## Uncertainty and interpretation

Optional `u_` input columns contain absolute **one-standard-deviation** uncertainties.
They propagate to total pH, pCO2, and aragonite saturation at each requested condition.
The helper assumes independent errors and treats unlisted inputs/constants as exact.
For covariance, constants uncertainty, or strongly nonlinear uncertainty, follow the
decision guide and validate a tailored propagation instead of calling these outputs a
complete uncertainty budget.

Omega < 1 indicates thermodynamic undersaturation with respect to the named mineral.
It does not establish a dissolution rate or an organism's response. A lower pH across
unmatched samples is not by itself evidence of an anthropogenic acidification trend.

## Sources and validation boundary

- [PyCO2SYS v1 arguments, units, settings, and result keys](https://pyco2sys.readthedocs.io/en/latest/co2sys_nd/)
- [Uncertainty propagation](https://pyco2sys.readthedocs.io/en/latest/uncertainty/)
- [Upstream validation](https://pyco2sys.readthedocs.io/en/latest/validate/)
- [Humphreys et al. (2022), PyCO2SYS v1.8](https://doi.org/10.5194/gmd-15-15-2022)

Repository tests exercise the pinned solver, independent-pair round trips, carbon balance,
pH-scale equivalence, condition correction, uncertainty quadrature, CSV errors, and the
worked example. They establish software behavior, not independent field-data validation.
