# Quick start: executable synthetic examples

Run the four blocks in order with the stack in SKILL.md. The generated data are
mechanical smoke checks, not evidence that a model fits a real scientific problem.

## OLS: design alignment and uncertainty targets

```python
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

rng = np.random.default_rng(42)
n = 240
X_data = pd.DataFrame(rng.normal(size=(n, 2)), columns=["x1", "x2"])
X = sm.add_constant(X_data)
y = 1 + 0.7 * X_data.x1 - 0.4 * X_data.x2 + rng.normal(size=n)
results = sm.OLS(y, X, missing="raise").fit()
assert np.linalg.matrix_rank(X) == X.shape[1]
print(results.summary())

# One new row needs an explicit intercept; preserve training column order.
X_new_data = pd.DataFrame({"x1": [0.0], "x2": [1.0]})
X_new = sm.add_constant(X_new_data, has_constant="add")[X.columns]
pred_summary = results.get_prediction(X_new).summary_frame()
print(pred_summary[["mean", "mean_ci_lower", "mean_ci_upper",
                    "obs_ci_lower", "obs_ci_upper"]])
# OLS mean CI and new-observation interval rely on their covariance/error assumptions.

from statsmodels.stats.diagnostic import het_breuschpagan
print("Breusch-Pagan/Koenker p-value:", het_breuschpagan(results.resid, X)[1])
plt.scatter(results.fittedvalues, results.resid)
plt.axhline(0, color="r", linestyle="--")
plt.xlabel("Fitted values")
plt.ylabel("Residuals")
plt.show()
```

## Binary logit: average marginal effects and held-out evaluation

```python
from scipy.special import expit
from sklearn.metrics import roc_auc_score, log_loss

# Toy independent rows; real repeated units need group-aware splitting.
y_binary = rng.binomial(1, expit(-0.3 + 0.8 * X_data.x1 - 0.5 * X_data.x2))
train, test = np.arange(180), np.arange(180, n)
logit_result = sm.Logit(y_binary[train], X.iloc[train], missing="raise").fit(disp=0)
assert logit_result.mle_retvals["converged"]
print("Odds ratios:", np.exp(logit_result.params))
print("Odds-ratio intervals:", np.exp(logit_result.conf_int()))
print(logit_result.get_margeff(at="overall").summary())  # Average over observations
# at="mean" instead evaluates effects at the mean predictor vector.
probs = logit_result.predict(X.iloc[test])
print("Held-out AUC:", roc_auc_score(y_binary[test], probs))
print("Held-out log loss:", log_loss(y_binary[test], probs))
# Select any classification threshold on training/validation data, not this test set.
```

## ARIMA: chronological validation and forecast intervals

```python
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.stats.diagnostic import acorr_ljungbox
from sklearn.metrics import mean_squared_error

# Stationary AR(1) toy process, with a daily index and known generating order.
values = np.zeros(240)
noise = rng.normal(size=240)
for t in range(1, len(values)):
    values[t] = 0.6 * values[t - 1] + noise[t]
y_series = pd.Series(values, index=pd.date_range("2025-01-01", periods=240, freq="D"))
train_series, test_series = y_series.iloc[:200], y_series.iloc[200:]
adf = adfuller(train_series, result_object=True)
kpss_result = kpss(train_series, regression="c", result_object=True)
print("Unit-root null p:", adf.pvalue, "Level-stationarity null p:", kpss_result.pvalue)
# KPSS can report a boundary p-value with an interpolation warning.
# Do not automatically choose d from one test; inspect trend/seasonality and design.
ts_result = ARIMA(train_series, order=(1, 0, 0)).fit()
assert ts_result.mle_retvals["converged"]
forecast = ts_result.get_forecast(steps=len(test_series))
print(forecast.summary_frame())  # Model-based forecast-error intervals
print("Test RMSE:", np.sqrt(mean_squared_error(test_series, forecast.predicted_mean)))
innov = ts_result.filter_results.standardized_forecasts_error[0]
innov = innov[ts_result.loglikelihood_burn:]
print(acorr_ljungbox(innov, lags=[10], model_df=1, return_df=True))
```

## Poisson GLM: exposure and conditional mean intervals

```python
exposure = rng.uniform(0.5, 2.0, n)
mu = exposure * np.exp(0.2 + 0.3 * X_data.x1)
y_counts = rng.poisson(mu)
poisson_result = sm.GLM(y_counts, X, family=sm.families.Poisson(),
                        exposure=exposure, missing="raise").fit(cov_type="HC0")
assert poisson_result.converged
print("Rate ratios:", np.exp(poisson_result.params))
print("Pearson dispersion:", poisson_result.pearson_chi2 / poisson_result.df_resid)
# The dispersion statistic can flag misspecification/dependence, not just NB variation.
new_exposure = np.array([2.0])
mean_prediction = poisson_result.get_prediction(
    X_new, exposure=new_exposure, which="mean")
print(mean_prediction.summary_frame())
print("Conditional mean CI:", mean_prediction.conf_int())
# This interval omits future count noise; it is not an observation prediction interval.
```
