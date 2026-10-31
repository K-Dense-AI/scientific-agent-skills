# Exploratory ARIMA forecasts of RELSA

The [2026 foRcast paper](https://doi.org/10.3389/fphys.2026.1869563) predicts a RELSA score at
an already specified future observation time. It does not fit a survival model, estimate a
probability of death, or establish a validated time-to-humane-endpoint predictor.

The bundled Python helper is an independent nonseasonal approximation of that workflow.
Current [R forecast::auto.arima documentation](https://pkg.robjhyndman.com/forecast/reference/auto.arima.html)
includes seasonality, separate mean/drift controls, transformations, alternative unit-root
tests and approximation policies not replicated here. Do not label results R/foRcast-equivalent.

## Selection and time semantics

`auto_arima()` chooses differencing via KPSS, then searches bounded p/q orders using AICc.
`stepwise=False` searches the configured p/q grid at the selected d. The SARIMAX likelihood,
KPSS lag selection and neighbor search differ from R. The helper now uses statsmodels'
`results.aicc` (effective observations and parameter accounting), rejects unconverged fits,
and disallows a constant when d > 1. A constant at d=0 is an intercept; at d=1 it is drift.
A finite criterion and numerical convergence do not establish stationarity, calibration or
biological adequacy. Inspect residuals and compare against a simple last-observation forecast
on held-out animals. Do not select a model from its evaluation endpoint errors.

[statsmodels SARIMAXResults](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.html)
provides `get_forecast(steps=...)`; `conf_int(alpha=...)` is read from that prediction result,
not from parameter confidence intervals on the fitted results object.

- Training and requested targets must use one finite time unit and unique observation times.
- Interpolation defaults to 0.1 **input time units**. All finite observed times and targets
  must align with that grid. Off-grid requests fail, rather than receive a neighboring
  horizon's forecast labeled with the requested time.
- With `interpolate_step=None` (CLI `--interpolate-step 0`), observed times must be regular,
  and each target must be an integer observation step after the last training observation.
- Missing measurements are excluded; interpolation bridges only gaps between available
  training points. Inspect gap length and missingness before fitting. Never interpolate
  using an observation later than the forecast cutoff.
- The two-observation minimum under interpolation is a computational allowance, not evidence
  of forecast reliability. Fewer than four genuine observations generate a warning.
- `predict_endpoint(..., endpoints={id: time})` uses only times strictly earlier than each
  recorded endpoint. Omitting `endpoints` evaluates the last available observation and warns
  that it is not necessarily a humane endpoint. `rolling_forecast` sorts times first.

## Uncertainty and validation

Interpolation adds no independent observations. It imposes smoothness and changes the fitted
correlation structure, so extra grid points cannot justify stronger confidence. Narrowing an
interval does not itself improve coverage. Compare results across defensible interpolation
steps, aggregation intervals and observed-only models where enough observations exist.

The returned Gaussian prediction interval is conditional on the fitted model, parameters,
preprocessing and reference. It omits reference-estimation and model-selection uncertainty.
The default floors means and bounds at zero to match the score's nonnegative support; this
is clipping, not a fitted truncated probability distribution. Use `clip_at_zero=False` to
inspect the raw Gaussian output. Reference scores and forecasts are not capped at one.

Inspect the upper bound and interval width as well as observed welfare signs; no bound is
an automatic care, euthanasia or wait decision. A smooth trajectory cannot predict an
unobserved abrupt deterioration. Handling must follow the approved study criteria.

Before prospective evaluation, freeze reference extrema, measurement encodings, baseline
rules and candidate KDE thresholds using development animals. Split at animal level, and
where relevant cage/study level, before tuning. Endpoint-selected calibration on evaluation
animals is retrospective leakage. Repeated observations do not increase the independent
animal sample size. Evaluate missed endpoints, false alerts, lead time and failure rates
under a prespecified monitoring policy before claiming operational utility.

`forecast_indirect()` separately forecasts measurements then recomputes the composite. It
accepts exactly one animal, warns on failed component fits and supplies a point forecast only;
it does not propagate joint uncertainty or covariance. Inspect missing components before
comparing against a direct forecast. The paper's direct-versus-indirect result is specific
to its sepsis analysis, not a general dominance theorem.

## Metrics and the published aggregation caveat

Report `n` (point-evaluable), `n_interval` (interval-evaluable) and forecast failures with:

- RMSE: square root of mean squared point error on finite actual/prediction pairs.
- PICP: percentage of actual values inside finite ordered bounds on evaluable predictions.
- MPIW: mean bound width on the same interval-evaluable predictions, in RELSA units.

A single forecast has either 0% or 100% observed coverage; neither establishes calibration.
Group comparisons must disclose pooled-observation versus equal-animal weighting. Include
uncertainty using animal-level resampling, not independent resampling of repeated time points.

The paper's Table 1 contains the following historical results (not reproduced in this review):

| Model | Animals | RMSE | PICP (%) | MPIW |
| --- | --- | --- | --- | --- |
| Sepsis | 2 | 0.009 | 100 | 0.30 |
| 1.5% DSS + restraint | 2 | 0.007 | 100 | 0.66 |
| 1% DSS + blood sampling | 4 | 0.046 | 75 | 0.53 |
| 1.5% DSS + blood sampling | 2 | 0.065 | 100 | 0.84 |
| 1.5% DSS | 1 | 0.095 | 100 | 1.64 |
| Pancreatic cancer | 1 | 0.177 | 100 | 7.35 |
| Neurosurgery | 1 | 0.082 | 100 | 0.54 |
| Published overall | 13 | 0.069 | 96 | 1.69 |

The overall values are consistent with unweighted means of model rows: PICP is 96.43%,
whereas pooled animal coverage is 12/13 = 92.31%. The helper's summary pools predictions and
will not recreate the published overall row merely by reproducing individual forecasts.
MPIW 1.69 means 1.69 reference scale units, not 169% of a bounded biological severity range.
Native Python synthetic tests validate arithmetic and mechanics only. R is not installed in
this review environment; native R forecasting and full published datasets remain unexecuted.
