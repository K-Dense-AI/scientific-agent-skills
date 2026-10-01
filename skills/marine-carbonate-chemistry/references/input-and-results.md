# Input table and output contract

## Input CSV

Use UTF-8 CSV with one row per sample, a header, and a unique nonempty `sample_id`.
All numeric cells must be finite; blanks, NaN, infinity, duplicate headers/IDs, extra
fields, and unknown columns are errors. Convert source missing-value codes before
selecting valid rows; a sentinel such as -999 is not recognized as missing.

Required numeric columns:

| Column | Meaning |
|---|---|
| `par1`, `par2` | Measurements identified by `--par1-type` and `--par2-type` |
| `salinity` | Practical Salinity, dimensionless |
| `temperature`, `pressure` | Input-condition temperature (C) and sea pressure (dbar) |
| `total_phosphate`, `total_silicate` | Total nutrients in micromol/kg seawater |

Parameter types are `alkalinity`, `dic`, `ph`, `pco2`, and `fco2`. Concentrations are
micromol/kg seawater, gas parameters microatm, and pH is on `--ph-scale`. A batch has
one parameter-pair definition and one pH-scale definition. Split mixed-method tables
when their measurement conventions differ. DIC and gas inputs must be positive;
this marine helper supports 0 < input pH < 14. TA may be signed, but a mathematical
solution still requires inspection for chemical plausibility.

Optional numeric columns:

- `temperature_out` **and** `pressure_out`: provide both or neither, for every row.
  Requiring both avoids accidentally retaining laboratory pressure during an ocean
  temperature correction. Output salinity is the input salinity.
- `total_ammonia`, `total_sulfide`: default to zero if absent, recorded in provenance.
  Use measured values when relevant; the helper does not model unspecified organic
  alkalinity. Anoxic and nonstandard waters need additional assessment.
- `u_` followed by any supplied numeric input name: absolute 1-sigma uncertainty in
  that variable's units. All uncertainty values must be nonnegative. `u_temperature_out`
  and `u_pressure_out` are accepted only when their corresponding inputs are supplied.

The helper does not infer units, source QC meanings, pH scales, depth-to-pressure
conversions, or which measurements to discard. Keep extra survey metadata in a
separate table linked by `sample_id`; unknown input columns are rejected to catch typos.

## Results

`carbonate.csv` retains `sample_id` and every supplied input prefixed with `input_`.
Calculated columns use PyCO2SYS v1 names:

- `alkalinity`, `dic`, `aqueous_CO2`, `bicarbonate`, `carbonate`: micromol/kg seawater.
- `pH_total`: total-scale pH, regardless of the supplied input pH scale.
- `pCO2`, `fCO2`: microatm; never equate the two.
- `saturation_aragonite`, `saturation_calcite`, `revelle_factor`: dimensionless.
- `_out` versions of the condition-dependent columns when output conditions exist.
  TA and DIC have no `_out` columns because this is a closed-sample correction.
- `u_pH_total`, `u_pCO2`, `u_saturation_aragonite` and their `_out` forms when any
  uncertainties were supplied. These are standard uncertainties, not 95% intervals.
- `qc_flags`: semicolon-separated `outside_k_carbonic_input_range` / `_output_range`
  and `gas_pressure_correction_disabled_input` / `_output` flags. A gas flag is emitted
  whenever the corresponding sea pressure is greater than zero.

An empty flag field means the helper's checks found no flags; it is not a measurement
QC grade. Values outside a range are retained and visibly flagged so the analyst can
reconsider the constant set. They should not be reported as validated predictions.

`provenance.json` records the input filename and SHA-256, sample count, software versions,
parameter types, explicit solver options, zero-solute assumptions, uncertainty sources,
units, gas-pressure convention, and sample-specific flags. Archive it with the input and output tables.
All rows are validated before output creation. Existing output directories are refused.

The helper's fixed options are bisulfate 1, fluoride 1, gas constant 3, buffer mode 1,
atmospheric pressure 1 atm, and `opt_pressured_kCO2=0`. It records these explicitly.
The last option disables hydrostatic corrections to **both CO2 solubility and fugacity**,
while pressure still affects acid dissociation and mineral saturation. Nonzero-pressure
pCO2/fCO2 are therefore not fully pressure-corrected in situ gas values. If a study requires
those corrections, use a separately tested direct call with `opt_pressured_kCO2=1` and
the correct sea pressure. Do not substitute water-column pressure into
`pressure_atmosphere`, which is barometric pressure in atm. Record the convention for
both measured and calculated gas quantities before comparing them. This behavior is
confirmed by the [v1.8 release notes](https://pyco2sys.readthedocs.io/en/latest/versions/)
and [pinned fugacity implementation](https://github.com/mvdh7/PyCO2SYS/blob/v1.8.3.4/PyCO2SYS/gas.py).
