# Bayesian Statistical Analysis

Reviewed 2026-10-01 for PyMC 6.3.2 and ArviZ 1.3.0 (Python 3.12+). The examples are local statistical APIs, with no authentication or service endpoint. PyMC returns xarray `DataTree` groups such as `posterior`, `sample_stats`, `observed_data` and `posterior_predictive`. ArviZ's current API is split across `arviz-stats` and `arviz-plots`, re-exported by `arviz`.

The model fragments below require finite, aligned data supplied by the analyst. Their API mechanics were exercised on small synthetic datasets with short native PyMC NUTS chains, using the Python PyTensor backend on the reviewed Mac. Those runs do not establish convergence or validate the scientific models. On this host C linking failed with missing `-ld64`; `PYTENSOR_FLAGS=cxx=` was an explicit runtime workaround, not evidence of successful C-backend execution.

## Questions, priors and uncertainty

Bayes' theorem gives posterior density proportional to likelihood times prior density. A posterior probability statement is conditional on that likelihood, prior, sampling design and available data. A continuous prior generally assigns zero probability to an exact point null: posterior draws cannot by themselves give a Bayes factor for that null.

Specify the estimand, units, independent sampling unit, censoring/missingness and dependence before choosing a model. Small samples may be weakly identified and sensitive to priors; Bayesian inference does not create information absent from the data.

- Scale priors using meaningful units and external knowledge. A Normal(0, 10) prior is not universally weakly informative. Using the same data to tune priors is an empirical choice that must be disclosed.
- A HalfNormal or HalfCauchy prior on `sigma` is a prior on standard deviation, not variance. Very heavy tails can cause computational problems.
- A flat prior over the real line is improper, not a proper Uniform(-infinity, infinity) distribution; it can yield an improper posterior or undefined marginal likelihood.
- Examine prior predictions, fit the prespecified model, and repeat with scientifically plausible alternative priors. Similar outputs across a few priors do not prove robustness to model misspecification.
- Sequential analysis needs an explicit stopping/decision rule. A fixed-prior Bayes factor has different optional-stopping properties from a posterior-threshold rule; there is no blanket exemption from calibration or multiplicity concerns.

## Two independent normal groups

This estimates a mean difference under a shared residual SD; it is not Welch's unequal-variance model. Set the prior scales to the measurement units. For unequal variances, model separate SDs and state the resulting model.

```python
import numpy as np
import pymc as pm
import arviz as az

with pm.Model() as group_model:
    mu1 = pm.Normal('mu1', mu=0, sigma=10)
    mu2 = pm.Normal('mu2', mu=0, sigma=10)
    sigma = pm.HalfNormal('sigma', sigma=10)
    pm.Normal('y1', mu=mu1, sigma=sigma, observed=group1)
    pm.Normal('y2', mu=mu2, sigma=sigma, observed=group2)
    pm.Deterministic('diff', mu1 - mu2)
    trace = pm.sample(2000, tune=1000, chains=4, cores=1,
                      random_seed=42, nuts_sampler='pymc')

# Explicit interval probability/type; avoid rounded diagnostics for decisions.
print(az.summary(trace, var_names=['mu1', 'mu2', 'diff'],
                 ci_prob=0.95, ci_kind='eti', round_to='none'))
draws = trace.posterior['diff'].values
print(f"P(mu1 > mu2 | data, model) = {np.mean(draws > 0):.3f}")
az.plot_dist(trace, var_names=['diff'], ci_prob=0.95, ci_kind='eti')
```

A posterior directional probability is not a one-sided Bayes factor. Pingouin 0.7 intentionally omits the `BF10` column for a one-sided `ttest`. Its two-sided default uses the documented JZS prior on standardized effect (Cauchy scale `r=0.707`):

```python
import pingouin as pg
result = pg.ttest(group1, group2, correction=False, r=0.707)
bf10 = float(result['BF10'].iloc[0])  # default output may be a formatted string
```

BF10 is the ratio of the data's marginal likelihoods under H1 and H0. Posterior odds equal BF10 times prior odds. BF10=3 means threefold evidence for H1 relative to H0 under those models; it does not by itself mean H1 is three times as probable. Conventional labels (3–10 moderate, 10–30 strong, 30–100 very strong, >100 extreme) are reporting conventions. State both models, priors and sensitivity. The BF printed beside a Welch statistic is not an unequal-variance Bayesian model comparison.

## Credible intervals and practical equivalence

An equal-tailed 95% interval has 2.5% in each tail. A highest-density region favors high-density values and may be disconnected for multimodal posteriors; a single shortest interval need not contain every mode. Neither interval proves the model is correct.

```python
posterior_samples = trace.posterior['diff']
eti = posterior_samples.quantile([0.025, 0.975], dim=('chain', 'draw'))
hdi = az.hdi(posterior_samples, prob=0.95, dim=['chain', 'draw'])
# Define a negligible raw-unit difference BEFORE looking at the result.
rope_lower, rope_upper = -0.1, 0.1
in_rope = ((posterior_samples >= rope_lower) &
           (posterior_samples <= rope_upper)).mean().item()
print(f"Posterior probability inside the prespecified ROPE: {in_rope:.3f}")
```

The ROPE must match the parameter's units: raw mean difference and standardized d cannot use the same threshold without justification. A posterior-mass decision rule and an HDI-inside-ROPE rule are distinct. Prespecify the rule and assess its consequences rather than presenting 95% as a universal decision threshold.

## Hierarchical group comparisons / Bayesian ANOVA

Use integer `group_idx` aligned with `y`, ranging from 0 to `n_groups-1`. The noncentered parameterization below gives partial pooling of group means. Prior scales remain illustrative; compare pooling assumptions and within-group residual distributions.

```python
with pm.Model() as hierarchical_model:
    mu_global = pm.Normal('mu_global', mu=0, sigma=10)
    sigma_between = pm.HalfNormal('sigma_between', sigma=5)
    sigma_within = pm.HalfNormal('sigma_within', sigma=5)
    z_group = pm.Normal('z_group', mu=0, sigma=1, shape=n_groups)
    group_means = pm.Deterministic('group_means', mu_global + sigma_between * z_group)
    pm.Normal('y_obs', mu=group_means[group_idx], sigma=sigma_within, observed=y)
    group_trace = pm.sample(2000, tune=1000, chains=4, cores=1,
                            random_seed=42, nuts_sampler='pymc')

contrast_1_2 = (group_trace.posterior['group_means'].isel(group_means_dim_0=0)
                - group_trace.posterior['group_means'].isel(group_means_dim_0=1))
```

The hierarchy models group intercepts only. Repeated measures may need subject effects, slopes or residual correlation; cluster identity is not optional. Contrasts are posterior estimates, not automatically Bayes factors or multiplicity-calibrated decisions.

## Correlation with uncertainty in location and scale

Standardizing observed data does not make population means and variances known. Infer those nuisance parameters rather than fixing covariance diagonals to one. Here `xy` contains two columns in reasonable units; prior scales must be adapted to those units.

```python
xy = np.column_stack([x, y])
with pm.Model() as correlation_model:
    mu = pm.Normal('mu', mu=0, sigma=10, shape=2)
    chol, corr, sds = pm.LKJCholeskyCov(
        'chol', n=2, eta=2, sd_dist=pm.HalfNormal.dist(sigma=10), compute_corr=True)
    pm.Deterministic('rho', corr[0, 1])
    pm.MvNormal('xy_obs', mu=mu, chol=chol, observed=xy)
    correlation_trace = pm.sample(2000, tune=1000, chains=4, cores=1,
                                  random_seed=42, nuts_sampler='pymc')
print(az.summary(correlation_trace, var_names=['rho'], ci_prob=0.95))
```

The bivariate normal likelihood is a substantive assumption; this is not a distribution-free rank correlation model. LKJ `eta=2` shrinks correlation toward zero.

## Regression, posterior prediction and restoration

`X` is an n-by-p numeric array, `y` an aligned length-n array, and `X_new` has the same p features/coding. Fit any preprocessing on the training data and reuse it. `pm.Data` can change length, not rank; models using named observation coordinates also need updated coordinates via `pm.set_data(..., coords=...)`.

```python
with pm.Model() as regression_model:
    X_data = pm.Data('X', X)
    alpha = pm.Normal('alpha', mu=0, sigma=10)
    beta = pm.Normal('beta', mu=0, sigma=10, shape=X.shape[1])
    sigma = pm.HalfNormal('sigma', sigma=10)
    mu = alpha + pm.math.dot(X_data, beta)
    pm.Normal('y_obs', mu=mu, sigma=sigma, observed=y, shape=mu.shape)
    regression_trace = pm.sample(2000, tune=1000, chains=4, cores=1,
                                 random_seed=42, nuts_sampler='pymc')
    ppc = pm.sample_posterior_predictive(regression_trace, random_seed=43)
    try:
        pm.set_data({'X': X_new})
        predictions = pm.sample_posterior_predictive(
            regression_trace, predictions=True, random_seed=44)
    finally:
        pm.set_data({'X': X})

az.plot_ppc_dist(ppc, var_names=['y_obs'], num_samples=100)
# Noisy future observations are in a separate predictions group.
predictive_interval = predictions.predictions['y_obs'].quantile(
    [0.025, 0.975], dim=('chain', 'draw'))
```

Observed-outcome predictions include residual noise. A posterior interval for the latent mean would be narrower and answers a different question. Do not compare changed-length predictions with the training outcomes as a posterior predictive check.

## Model comparison

PSIS-LOO estimates predictive performance, not evidence for a point null. Compare models for the **same observed outcomes, rows and likelihood units**, with aligned pointwise log-likelihood coordinates. Ordinary observation-wise LOO is inappropriate when prediction targets new clusters or future dependent observations; use the appropriate grouped/temporal validation design.

```python
with regression_model:  # training inputs must have been restored
    pm.compute_log_likelihood(regression_trace, var_names=['y_obs'])
loo = az.loo(regression_trace, var_name='y_obs', pointwise=True)
print(f"Expected log predictive density: {loo.elpd:.2f}")  # higher is better
print(loo.pareto_k, loo.good_k, loo.warning)
```

Investigate Pareto-k values above `good_k`, including refitting troublesome observations or suitable cross-validation. Differences small relative to their uncertainty do not identify a unique best model. For multiple prepared traces, `az.compare({'model1': trace1, 'model2': trace2}, var_name='y_obs')` reports rankings and stacking weights; stacking weights are not posterior model probabilities. ArviZ 1 removed `az.waic`; do not use an old WAIC fallback snippet. Default ArviZ intervals are configuration-dependent (89% in the reviewed defaults), so request `ci_prob=0.95` when needed.

## Diagnostics and posterior predictive checks

- Use multiple independently initialized chains (usually at least four). Inspect finite rank-normalized R-hat, bulk/tail ESS and MCSE for every reported estimand; R-hat near 1, commonly below 1.01, is a screening target, not proof of convergence or identifiability.
- Tail precision requires enough effective draws. An ESS cutoff does not establish precision for an extreme posterior probability. NaN diagnostics are unavailable/failed, not passed.
- Inspect divergences, energy/BFMI and tree-depth warnings when using HMC; trace/rank plots can reveal slow exploration. Solve model geometry/identification problems rather than merely increasing draws.
- Compare posterior replicated data with features relevant to the question: spread, tails, zeros, groups and dependence, not only the overall mean.

```python
print(az.summary(regression_trace, kind='diagnostics', round_to='none'))
az.plot_trace(regression_trace)
az.plot_rank(regression_trace)
az.plot_forest(regression_trace, var_names=['beta'], ci_probs=[0.5, 0.95])
pp = ppc.posterior_predictive['y_obs']
# Mean over observation dimensions, retain chain/draw before aggregating.
obs_dims = [dim for dim in pp.dims if dim not in ('chain', 'draw')]
pred_means = pp.mean(dim=obs_dims)
posterior_predictive_tail = (pred_means >= np.mean(y)).mean().item()
```

This posterior predictive tail area reuses the observed data through the posterior and is not a uniformly calibrated frequentist p-value. Visual distributional checks also do not certify predictive calibration.

## Reporting

Report likelihood, parameterization, prior units/hyperparameters, missingness and dependence handling, chains/tune/draws, sampler/backend and package versions. State the interval type/probability, estimand units, posterior diagnostic results, sensitivity checks and predictive discrepancies. Report a Bayes factor only if actually calculated under explicitly described models; posterior sample fractions do not supply it. Report Bayesian intervals as credible intervals (CrI), not frequentist confidence intervals (CI).

For other front ends, [Bambi](https://bambinos.github.io/bambi/) provides formula-based modeling and [CmdStanPy](https://mc-stan.org/cmdstanpy/) interfaces to Stan (requires a separate CmdStan toolchain). These optional tools are not required or runtime-validated by this workflow. Do not describe PyStan as discontinued; [PyStan 3](https://pystan.readthedocs.io/en/latest/) is a separate supported interface with its own platform requirements.

## Primary API sources

- [PyMC sample](https://www.pymc.io/projects/docs/en/stable/api/generated/pymc.sample.html), [data](https://www.pymc.io/projects/docs/en/stable/api/generated/pymc.Data.html), [posterior prediction](https://www.pymc.io/projects/docs/en/stable/api/generated/pymc.sample_posterior_predictive.html), [LKJ covariance](https://www.pymc.io/projects/docs/en/stable/api/distributions/generated/pymc.LKJCholeskyCov.html).
- [ArviZ summary](https://python.arviz.org/projects/stats/en/stable/api/generated/arviz_stats.summary.html), [HDI](https://python.arviz.org/projects/stats/en/stable/api/generated/arviz_stats.hdi.html), [LOO](https://python.arviz.org/projects/stats/en/stable/api/generated/arviz_stats.loo.html), [comparison](https://python.arviz.org/projects/stats/en/stable/api/generated/arviz_stats.compare.html), [PPC plotting](https://python.arviz.org/projects/plots/en/stable/api/generated/arviz_plots.plot_ppc_dist.html).
- [Pingouin Bayes factor](https://pingouin-stats.org/generated/pingouin.bayesfactor_ttest.html).
