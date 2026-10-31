# Maintenance and verification ledger

Reviewed 2026-10-01 against **statsmodels 0.15.0**, with Python 3.13.3,
NumPy 2.5.3, SciPy 1.18.1, pandas 3.0.6, matplotlib 3.11.2 and
scikit-learn 1.9.1. The package itself supports Python 3.10+; this exact numerical
stack requires 3.12+. No remote service endpoint, authentication or pagination is
part of these statistical workflows.

The current [release notes](https://www.statsmodels.org/stable/release/version0.15.0.html)
and [tagged source](https://github.com/statsmodels/statsmodels/tree/v0.15.0/statsmodels)
were checked with the installed wheel. Forty-seven source files covering the model,
diagnostic, graphics and treatment imports matched the release tag byte for byte.
The API audit included constructors, fitting options, result attributes and prediction
semantics in every reference. Source inspection is distinct from numerical execution.

The quick start is executable in order. Other references contain contextual fragments:
provide their named inputs and retain the appropriate model result for each section;
they are not single scripts to concatenate. Native synthetic checks cover the corrected
contracts, linear/GLM/discrete/time-series models and diagnostics. They establish API
behavior and numerical identities, not estimator calibration, power for a real study,
causal identification, or validity of a fitted scientific model. Optional custom
MLEModel subclasses, manual proportional-odds tests and arbitrary user datasets remain
illustrative and require separate validation.

## Primary API sources and consequential contracts

- [OLS](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html),
  [robust covariance](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html),
  [RecursiveLS](https://www.statsmodels.org/stable/generated/statsmodels.regression.recursive_ls.RecursiveLS.html),
  [MixedLM.fit](https://www.statsmodels.org/stable/generated/statsmodels.regression.mixed_linear_model.MixedLM.fit.html):
  intercept/design alignment; recursive estimates are expanding-window estimates;
  ML versus REML and covariance assumptions matter.
- [GLM.fit](https://www.statsmodels.org/stable/generated/statsmodels.genmod.generalized_linear_model.GLM.fit.html),
  [GLM prediction](https://www.statsmodels.org/stable/generated/statsmodels.genmod.generalized_linear_model.GLMResults.get_prediction.html),
  [pseudo R-squared](https://www.statsmodels.org/stable/generated/statsmodels.genmod.generalized_linear_model.GLMResults.pseudo_rsquared.html):
  specify robust covariance during fit, request the intended prediction target, use
  likelihood-based pseudo-R² and `bic_llf`, and preserve exposure for new data.
- [Marginal effects](https://www.statsmodels.org/stable/generated/statsmodels.discrete.discrete_model.DiscreteResults.get_margeff.html),
  [ZIP prediction](https://www.statsmodels.org/stable/generated/statsmodels.discrete.count_model.ZeroInflatedPoisson.predict.html),
  [OrderedModel](https://www.statsmodels.org/stable/generated/statsmodels.miscmodels.ordinal_model.OrderedModel.html),
  [ConditionalLogit](https://www.statsmodels.org/stable/generated/statsmodels.discrete.conditional_models.ConditionalLogit.html),
  [hurdle](https://www.statsmodels.org/stable/generated/statsmodels.discrete.truncated_model.HurdleCountModel.html):
  `overall` gives AME; `atexog` keys are column numbers; inflation differs from
  observing zero; ordinal/conditional models prohibit a constant; ordinal threshold
  increments need transformation. Hurdle zero/count processes share exog.
- [ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html),
  [KPSS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html),
  [SARIMAX forecasting](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.get_forecast.html),
  [Ljung-Box](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html),
  [VARMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.varmax.VARMAX.html):
  use named result objects, distinguish test nulls, supply future exog, account for
  fitted dynamic parameters and initialization, and avoid unidentified unrestricted
  VARMA specifications. `MarkovRegression.order` does not add AR coefficients.
- [RESET](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.linear_reset.html),
  [AnovaRM](https://www.statsmodels.org/stable/generated/statsmodels.stats.anova.AnovaRM.html),
  [pairwise comparisons](https://www.statsmodels.org/stable/generated/statsmodels.stats.multicomp.pairwise_tukeyhsd.html),
  [proportion effect size](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_effectsize.html),
  [SciPy Levene](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.levene.html):
  RESET returns a result object; repeated-measures ANOVA requires balanced data and
  lacks sphericity corrections; 0.15 adds Games-Howell via `use_var="unequal"`;
  proportion power uses Cohen's h, and CompareMeans has no `test_equal_var` method.
- [TreatmentEffect](https://www.statsmodels.org/stable/generated/statsmodels.treatment.treatment_effects.TreatmentEffect.html)
  and its [released implementation](https://github.com/statsmodels/statsmodels/blob/v0.15.0/statsmodels/treatment/treatment_effects.py):
  OLS outcome modeling remains the supported route. `ipw_ra`/`aipw_wls` GMM still
  slice the final six selection parameters; non-six-parameter designs raise a shape
  error. The point-estimate-only route does not provide standard errors. Do not change
  a scientific design to accommodate that implementation bug.

## Executed checks and limits

The isolated suite runs eight native tests, including all 173 Python fenced blocks
with explicit synthetic contexts (some blocks only import or explain a workflow).
Assertions cover design shapes, OLS interval width, GLM mean uncertainty and robust
covariance, AME derivatives, ZIP mixture probabilities, ordinal thresholds, multinomial
results, selected ARIMA convergence and preserved forecast dates, and treatment-effect
identities plus the known GMM failure.

The broad ARIMA grid emits expected nonconvergence warnings for some candidates;
selection excludes those candidates and retains the selected result. KPSS reports
table-boundary p-values. Gamma inverse/binomial log links emit domain warnings and
need an explicit support check on real data. Johansen testing emitted complex-to-real
cast warnings in the tested NumPy stack; the synthetic eigenvalues had exactly zero
imaginary parts and finite trace/max-eigenvalue statistics. That fixture check is not
a general justification to discard complex components on other data. Plotting was
exercised with the noninteractive Agg backend; no publication-layout certification
or empirical interval coverage study was performed.
