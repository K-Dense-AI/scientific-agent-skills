# Chemistry decisions that affect the answer

## Constant sets and seawater composition

The helper requires `--k-carbonic`; it does not infer a constant set from the dataset.
Its two supported options are:

| Option | Carbonic-acid parameterization | Documented calibration interval |
|---|---|---|
| 10 | Lueker, Dickson & Keeling (2000) | 2 < T < 35 C; 19 < Practical Salinity < 43 |
| 15 | Waters, Millero & Woosley (2014) | 0 < T < 45 C; 0 < Practical Salinity < 45 |

These temperature/salinity intervals come from the [PyCO2SYS v1 settings documentation](https://pyco2sys.readthedocs.io/en/latest/co2sys_nd/).
They are checks on one part of the model, not proof that all chemical assumptions are
valid. Pressure corrections do not remove the need to assess constants and sample
composition. Boundary values are flagged conservatively. Both measurement and output
conditions are checked.

Choose the convention established for the study, and explain changes. The helper's
`--total-borate 1` uses Uppstrom (1974); `2` uses Lee et al. (2010). Neither automatically
handles an altered boron-to-salinity ratio. Calcium, sulfate, and fluoride are inferred
by the library's seawater relationships. Freshwater mixing, unusual ionic composition,
and substantial organic alkalinity can violate these assumptions even if the selected
carbonic-acid constants permit that salinity. Use direct composition-aware calculations
when those terms matter; do not substitute salinity zero into a normal-seawater recipe.

## Measurement-scale checks

Total, seawater, free, and NBS pH are not interchangeable. The scale belongs to the
method and calibration record, not a numerical guess. NBS electrode readings in
seawater warrant particular attention to calibration and activity conventions.
PyCO2SYS accepts the declared input scale; the bundled report consistently emits total pH.

Gas measurements must specify seawater pCO2 or fCO2 and the equilibrator/measurement
temperature. Atmospheric mole fraction in ppm is not a seawater pCO2 observation.
The helper intentionally omits gas-flux calculations: a flux additionally requires
consistent air/water gas quantities and an appropriate gas-transfer model.

For a closed sample, convert both known parameters at their actual input conditions
and request output temperature/pressure. Never set laboratory-measured pH's input
temperature to the ocean temperature just because the desired result is in situ.

## Uncertainty that matches the claim

The helper forwards explicitly supplied standard uncertainties to PyCO2SYS v1's
finite-difference propagation. Its reported u values assume independent input errors.
Missing u columns imply zero uncertainty for that input. Constant uncertainty,
method bias, preservation error, and unmodeled solutes are absent from that budget.

For a more complete analysis:

1. Define which measured quantities share calibration or preparation errors. TA and
   DIC errors may covary; also avoid treating the same temperature measurement as two
   independent uncertain inputs merely because input/output columns both exist.
2. With independent errors, a tailored `pyco2.sys` call can use
   `uncertainty_into` and `uncertainty_from`, including suitable equilibrium-constant
   uncertainties. Upstream provides `pyco2.uncertainty_OEDG18`; inspect its assumptions
   before adopting it. Input/output constant uncertainties require deliberate treatment
   of their shared errors; see upstream's `_both` keys.
3. With covariance or appreciable nonlinearity, use a scientifically justified joint
   error model, propagate paired Monte Carlo draws through the solver, and check output
   quantiles and invalid draws. Document distributions, correlations, seed, convergence,
   and any truncation. This extension is not implemented by the bundled helper.
4. Compare replicate precision and certified-reference-material results with the
   assumed uncertainties. Numerical propagation cannot recover unknown measurement bias.

Read the [upstream uncertainty guide](https://pyco2sys.readthedocs.io/en/latest/uncertainty/)
when implementing those extensions. Keep helper u values labeled as **conditional,
independent-input uncertainty**, not a complete accuracy claim.

## Interpret at the right level

- Saturation state describes thermodynamics relative to a named mineral; it is not a
  kinetic dissolution model, coral health score, or universal biological threshold.
- The Revelle factor describes the local relative pCO2 sensitivity to relative DIC
  change at constant TA and conditions. Use an explicit new equilibrium for a large
  perturbation rather than extending a local linear sensitivity indefinitely.
- A controlled increase in DIC at fixed TA can illustrate a carbonate response to CO2
  addition. It does not reproduce all drivers of a real ocean acidification time series.
- Alkalinity addition scenarios require mixing, precipitation, and gas-exchange
  accounting before making carbon-removal claims; the closed-equilibrium solver alone
  establishes none of these budgets.

For methods context and solver validation, cite [Humphreys et al. (2022)](https://doi.org/10.5194/gmd-15-15-2022)
and the relevant constants/measurement-method references for the actual study.
