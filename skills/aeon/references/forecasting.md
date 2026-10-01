# Time Series Forecasting

The experimental `aeon.forecasting` module uses array-native estimators, not sktime's `fh` or `ForecastingHorizon` API. This reference targets aeon 1.6. Check capability tags before supplying multivariate data or exogenous variables; the statistical examples here are univariate.

## Imports and model families

- `from aeon.forecasting import NaiveForecaster, RegressionForecaster`
- `from aeon.forecasting.stats import ARIMA, AutoARIMA, ETS, AutoETS, Theta, TAR, AutoTAR, TVP`
- `from aeon.forecasting.deep_learning import TCNForecaster, DeepARForecaster`

`NaiveForecaster` offers `"last"`, `"mean"`, `"seasonal_last"`, and (new in 1.6) `"drift"`. Supply a positive `seasonal_period` with enough historical observations for `seasonal_last`. `RegressionForecaster` requires a `window` and learns an h-step target with a sklearn/aeon regressor. ARIMA takes `p`, `d`, `q`, not `order=`. ETS/AutoETS are native aeon implementations; automatic selection has documented stability/efficiency limitations and should be checked against a baseline.

Deep forecasters require **TensorFlow**, not PyTorch. `DeepARNetwork` still exists as the underlying architecture; it is not a former name of `DeepARForecaster`. A DeepAR architecture alone does not establish calibrated predictive uncertainty. Optional deep-training examples are illustrative and were not executed in this review.

## Single horizon versus a forecast path

For models that expose `horizon`, `predict(history)` produces **one value** h steps beyond the history. `horizon=3` does not mean return the next three values. `last` and `mean` return their constant baseline regardless of horizon; drift and seasonal-last use the horizon.

```python
import numpy as np
from aeon.forecasting import NaiveForecaster
from aeon.forecasting.stats import ARIMA, AutoETS

y = np.arange(1.0, 31.0)
naive = NaiveForecaster(strategy="drift", horizon=3)
naive.fit(y)
y_at_3 = naive.predict(y)
assert y_at_3 == 33.0

# iterative_forecast fits once internally and returns a vector.
# The estimator must have horizon=1 (the default).
path = NaiveForecaster(strategy="last").iterative_forecast(y, 3)
assert np.array_equal(path, [30.0, 30.0, 30.0])
arima_path = ARIMA(p=1, d=1, q=1).iterative_forecast(y, 3)

# AutoETS does not accept horizon=; use the multi-step helper.
ets_path = AutoETS().iterative_forecast(y, 3)
```

`direct_forecast(y, prediction_horizon)` fits separate models for each horizon, using estimators with `capability:horizon=True`, such as `RegressionForecaster`. `iterative_forecast` feeds earlier predictions back into the history and accumulates error. Do not call `fit` immediately before this helper expecting it to preserve a pre-fitted model: the helper fits internally.

## Exogenous variables without target leakage

ARIMA supports target-time regressors: training rows align with observed `y`, and prediction needs the covariates for the future target time. Historical exogenous effects require explicit lagged features. Use only covariates known at forecast issuance, or model their uncertainty separately.

```python
import numpy as np
from aeon.forecasting.stats import ARIMA

exog_train = np.arange(30.0)[:, None]
y_train = 2.0 + 3.0 * exog_train[:, 0]
future_exog = np.arange(30.0, 33.0)[:, None]
forecaster = ARIMA(p=0, d=0, q=0)
forecaster.fit(y_train, exog=exog_train)
y_next = forecaster.predict(y_train, exog=future_exog[:1])
path = forecaster.iterative_forecast(
    y_train, prediction_horizon=3,
    exog=exog_train, future_exog=future_exog,
)
```

Keep observed history in `predict(y_train, ...)`; passing held-out target values as that history leaks future information. In aeon 1.6 the recursive helper requires both historical `exog` and `future_exog` when either is supplied.

## Evaluation

Use rolling-origin or chronological holdouts. Compare against naive and seasonal-naive baselines, keeping the same forecast horizons and available covariates. Report errors per horizon before aggregating. Align arrays explicitly, then use sklearn `mean_absolute_error`, `mean_squared_error`, or `root_mean_squared_error`. Avoid random shuffling of overlapping forecasting windows.

Sources: [forecasting API](https://www.aeon-toolkit.org/en/stable/api_reference/forecasting.html), [1.6 source and helper contracts](https://github.com/aeon-toolkit/aeon/blob/v1.6.0/aeon/forecasting/base.py), [ARIMA source](https://github.com/aeon-toolkit/aeon/blob/v1.6.0/aeon/forecasting/stats/_arima.py). Synthetic checks exercised all non-deep examples above.
