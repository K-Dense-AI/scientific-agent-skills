# Time Series Forecasting

The `aeon.forecasting` module provides forecasters for univariate and multivariate series. In aeon **1.x**, forecasting was rebuilt on array-native `BaseForecaster` estimators (replacing the old sktime-style `fh` API). The module is marked **experimental** — expect API evolution between releases.

Import paths (aeon 1.4+):

- `from aeon.forecasting import NaiveForecaster, RegressionForecaster`
- `from aeon.forecasting.stats import ARIMA, AutoARIMA, ETS, AutoETS, Theta, TAR, AutoTAR, TVP`
- `from aeon.forecasting.deep_learning import TCNForecaster, DeepARForecaster`

List all forecasters: `aeon.utils.discovery.all_estimators(type_filter="forecaster")`.

## Naive and Baseline Methods

- `NaiveForecaster` — `strategy` in `"last"`, `"mean"`, `"seasonal_last"`; set `horizon` and `seasonal_period` in the constructor
  - **Use when**: Establishing baselines or simple patterns

## Statistical Models

- `ARIMA` / `AutoARIMA` — `p`, `d`, `q` orders (not `order=(p,d,q)`); supports exogenous variables via `exog`
- `ETS` / `AutoETS` — exponential smoothing (native implementations in aeon 1.4+)
- `Theta` — classical Theta method
- `TAR` / `AutoTAR` — threshold autoregressive models for regime switching
- `TVP` — time-varying parameter (Kalman-style) models

## Deep Learning Forecasters

Requires `aeon[all_extras]` (PyTorch stack):

- `TCNForecaster` — temporal convolutional network
- `DeepARForecaster` — probabilistic RNN forecaster (replaces legacy `DeepARNetwork` naming)

## Regression-Based Forecasting

- `RegressionForecaster` — sliding `window` over history, `horizon` steps ahead, any sklearn/aeon regressor

## Quick Start

```python
import numpy as np
from aeon.forecasting import NaiveForecaster
from aeon.forecasting.stats import ARIMA, AutoETS

y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

# Naive — horizon is a constructor argument; predict(y) forecasts from series y
naive = NaiveForecaster(strategy="last", horizon=3)
naive.fit(y)
pred_naive = naive.predict(y)

# ARIMA — one-step by default; multi-step via iterative_forecast
arima = ARIMA(p=1, d=1, q=1)
arima.fit(y)
pred_arima = arima.iterative_forecast(y, prediction_horizon=3)

# Auto model selection
auto_ets = AutoETS(horizon=3)
auto_ets.fit(y)
pred_ets = auto_ets.predict(y)
```

## Forecasting Horizon

In aeon 1.x, set `horizon` on the estimator (number of steps ahead). `predict(y)` returns the forecast `horizon` steps beyond the end of `y`.

Multi-step strategies:

- **`iterative_forecast(y, prediction_horizon)`** — reuse one fitted model, feed predictions back (ARIMA, many stats models)
- **`direct_forecast(y, prediction_horizon)`** — refit per horizon (requires `capability:horizon` tag; e.g. `RegressionForecaster`)
- **`NaiveForecaster`** — set `horizon>1` directly when `strategy` supports it

There is no `ForecastingHorizon` / `fh=[1,2,3]` API in aeon 1.x.

## Model Selection

- **Baseline**: `NaiveForecaster(strategy="seasonal_last", seasonal_period=12, horizon=h)`
- **Linear / stationary**: `ARIMA`, `AutoARIMA`
- **Trend + seasonality**: `ETS`, `AutoETS`
- **Regime changes**: `TAR`, `AutoTAR`
- **Complex patterns**: `TCNForecaster`, `RegressionForecaster` with aeon regressors
- **Probabilistic**: `DeepARForecaster`

## Evaluation Metrics

Use scikit-learn or standard numpy metrics on hold-out forecasts:

```python
from sklearn.metrics import mean_absolute_error, mean_squared_error

mae = mean_absolute_error(y_true, y_pred)
mse = mean_squared_error(y_true, y_pred)
```

## Exogenous Variables

Pass aligned exogenous arrays as `exog` (not `X`):

```python
forecaster.fit(y_train, exog=exog_train)
y_pred = forecaster.predict(y_test, exog=exog_test)
```

## Base Classes

- `BaseForecaster` — `horizon`, `axis`, `fit`, `predict`, `forecast`
- `DirectForecastingMixin` / `IterativeForecastingMixin` — multi-step helpers
- `BaseDeepForecaster` — deep learning forecasters

Extend `BaseForecaster` for custom forecasters.
