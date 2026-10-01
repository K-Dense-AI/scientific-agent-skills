# Prepare a forecast without changing its time axis

TimesFM 2.5 sees positions, not timestamps. Give a list of finite one-dimensional
float arrays, one regular univariate history per array. Variable lengths are
allowed; each series needs its own known cadence and forecast origin. A batch
horizon of 12 means 12 steps, not a shared wall-clock duration across cadences.

## CSV/DataFrame recipe

The bundled helper sorts dates, validates uniqueness and checks the full grid.
Use it directly for CSVs; when adapting DataFrames apply the same checks.

```python
# Run from the skill scripts directory, or put that directory on sys.path.
from forecast_csv import load_csv, prepare_inputs
frame, columns, date_column = load_csv(
    "monthly_sales.csv", date_col="date", value_cols=["sales"], freq="MS"
)
inputs = prepare_inputs(frame, columns, missing="error")
```

Select target columns explicitly when numeric IDs/metadata exist. Two or fewer
dates cannot establish a unique frequency, so declare it. Do not silently
resample: a sum for counts, mean for intensities and last value for stock levels
represent different targets. Record timezone and daylight-saving decisions.
For long-format data, group by series ID, validate each grid separately and
retain a parallel ordered ID list. Do not use `.dropna()` to build histories.

Pandas input adapters: `read_excel(..., engine="openpyxl")` needs openpyxl;
`read_parquet(..., engine="pyarrow")` needs pyarrow. These optional adapters were
source-checked, not exercised in this refresh. JSON/NumPy input must still be
checked for finite values, shape, cadence and origin.

## Missing values and transformations

The release's base forecast strips leading NaNs and interpolates later NaNs,
including trailing last-value extension. This is computational convenience,
not a missing-data model. Reject all-missing, empty, infinite or overflowed
float32 inputs. Choose a documented missingness policy before forecasting.

The CLI rejects missing data by default. `--missing interpolate` fills internal
gaps only and retains the same array length; leading/trailing gaps fail because
they make the forecast origin or observed history ambiguous. Impute separately
inside each training cutoff. Interpolation across a held-out target leaks future
information. Imputed observations should not become “actuals” for coverage.

Validate clipping/outlier handling scientifically; do not erase real events to
improve a score. Fit scalers, detrending and feature selection on training data
only, reverse transformations for evaluation, and retain units. Constant or short
series deserve a naive baseline; there is no universal 32-point model minimum
or guarantee that more history improves accuracy.

## XReg inputs

For each series i with context length Li and requested horizon H:

- target is `(Li,)`, containing only observations available at origin;
- each dynamic feature is `(Li+H,)`, with the future segment known at origin;
- each static feature supplies one value per series;
- feature names, series order, time positions and inferred horizons agree.

A weather forecast issued at origin can be a future covariate; the weather later
observed at that date cannot be used for a realistic backtest. Planned prices
and holiday schedules are conditional assumptions, not causal effects. Numeric
and categorical covariates are processed by pooled linear XReg, not native
multivariate target attention. The distinct 3.0 API supports past-only features.
