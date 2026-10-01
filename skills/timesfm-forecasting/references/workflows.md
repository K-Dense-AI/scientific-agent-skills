# Forecast and evaluate on withheld future observations

## Single or many independent series

Validate inputs before expensive loading. Use `forecast_csv.py` for a regular
wide CSV. For manually batched arrays preserve IDs/origins separately and pass
a fresh list to 2.5 `model.forecast` because it appends dummy batch-padding series.
Use `return_backcast=False` for ordinary forecasting. Do not join different
series end-to-end or imply a univariate batch is a joint multivariate model.

## Rolling-origin validation

Illustrative pretrained recipe; no pretrained accuracy was evaluated in this refresh.
Choose origins/horizon before model tuning and keep a final untouched evaluation
period. Here `values` is a finite regular-grid series and `model` is compiled
for at least H; it must have `return_backcast=False`.

```python
import numpy as np

H, season = 12, 12
origins = range(60, len(values) - H + 1, H)
records = []
for origin in origins:
    train = values[:origin].copy()
    actual = values[origin:origin + H]
    # Fit any imputation/transformation on this train slice only.
    point, q = model.forecast(horizon=H, inputs=[train])
    pred = point[0]
    baseline = np.tile(train[-season:], int(np.ceil(H / season)))[:H]
    assert np.isfinite(q).all() and np.isfinite(actual).all()
    lower, upper = q[0, :, 1], q[0, :, 9]
    records.append({
        "origin": origin,
        "mae": float(np.mean(np.abs(actual - pred))),
        "rmse": float(np.sqrt(np.mean((actual - pred)**2))),
        "seasonal_naive_mae": float(np.mean(np.abs(actual - baseline))),
        "nominal_80_coverage": float(np.mean((actual >= lower) & (actual <= upper))),
        "mean_interval_width": float(np.mean(upper - lower)),
    })
if not records:
    raise ValueError("not enough history for the prespecified origins")
```

Report origin count, observed target count and aggregation units; pooled points,
series-weighted means and origin-weighted means are different estimands. For
multiple horizons also report per-horizon MAE, pinball loss, coverage and width.
Do not divide by zeros/near-zero targets for MAPE. For scaled errors use a
training-only baseline denominator and report when it is zero.

Overlapping origins generate dependent errors; naive IID confidence intervals
are not justified. Tune context, feature sets and post-hoc calibration on a
validation period, then assess the frozen procedure on a later test period.
Model-pretraining overlap is separate from leakage in your local split.

For interval screening, outside q10-q90 is a nominal 80% band exceedance, not
“90% confidence of anomaly.” Validate alarm rates, temporal dependence and the
costs of false alarms in the intended application. The example Z-score screen
fits on the entire context and is explicitly retrospective.
