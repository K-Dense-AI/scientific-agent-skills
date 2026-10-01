# Common Model Patterns and Comparison

Reusable model structures (hierarchical, regression variants, mixtures, time series) and
then predictive model comparison. Targets PyMC 6.3.2 / ArviZ 1.3.0.
Fragments below are illustrative and require the named data/dimensions; native
regression and hierarchical template execution is tested separately.

## Common Model Patterns

### Linear Regression

For continuous outcomes with linear relationships:

```python
with pm.Model() as linear_model:
    alpha = pm.Normal('alpha', mu=0, sigma=10)
    beta = pm.Normal('beta', mu=0, sigma=10, shape=n_predictors)
    sigma = pm.HalfNormal('sigma', sigma=1)

    mu = alpha + pm.math.dot(X, beta)
    y = pm.Normal('y', mu=mu, sigma=sigma, observed=y_obs)
```

**Use template:** `assets/linear_regression_template.py`

### Logistic Regression

For binary outcomes:

```python
with pm.Model() as logistic_model:
    alpha = pm.Normal('alpha', mu=0, sigma=10)
    beta = pm.Normal('beta', mu=0, sigma=10, shape=n_predictors)

    logit_p = alpha + pm.math.dot(X, beta)
    y = pm.Bernoulli('y', logit_p=logit_p, observed=y_obs)
```

### Hierarchical Models

For grouped data (non-centering is often helpful for weakly informed group effects):

```python
with pm.Model(coords={'groups': group_names}) as hierarchical_model:
    # Hyperpriors
    mu_alpha = pm.Normal('mu_alpha', mu=0, sigma=10)
    sigma_alpha = pm.HalfNormal('sigma_alpha', sigma=1)

    # Group-level (non-centered)
    alpha_offset = pm.Normal('alpha_offset', mu=0, sigma=1, dims='groups')
    alpha = pm.Deterministic('alpha', mu_alpha + sigma_alpha * alpha_offset, dims='groups')

    # Observation-level
    mu = alpha[group_idx]
    sigma = pm.HalfNormal('sigma', sigma=1)
    y = pm.Normal('y', mu=mu, sigma=sigma, observed=y_obs)
```

**Use template:** `assets/hierarchical_model_template.py`

**Check geometry:** Compare centered/non-centered parameterizations when necessary;
non-centering is not a guarantee against divergences or weak identification.

### Poisson Regression

For count data:

```python
with pm.Model() as poisson_model:
    alpha = pm.Normal('alpha', mu=0, sigma=10)
    beta = pm.Normal('beta', mu=0, sigma=10, shape=n_predictors)

    log_lambda = alpha + pm.math.dot(X, beta)
    y = pm.Poisson('y', mu=pm.math.exp(log_lambda), observed=y_obs)
```

For overdispersed counts, use `NegativeBinomial` instead.

### Time Series

For autoregressive processes:

```python
with pm.Model() as ar_model:
    sigma = pm.HalfNormal('sigma', sigma=1)
    rho = pm.Normal('rho', mu=0, sigma=0.5, shape=ar_order)
    init_dist = pm.Normal.dist(mu=0, sigma=sigma)

    y = pm.AR('y', rho=rho, sigma=sigma, init_dist=init_dist, observed=y_obs)
```

## Model Comparison

### Comparing Models

Use PSIS-LOO for this helper; ArviZ 1 `compare` does not accept a WAIC selector:

```python
from scripts.model_comparison import compare_models, check_loo_reliability

# Fit models with log_likelihood
models = {
    'Model1': idata1,
    'Model2': idata2,
    'Model3': idata3
}

# Compare using LOO
comparison = compare_models(models, ic='loo')

# Check reliability
check_loo_reliability(models)
```

**Interpretation:** ArviZ 1 reports `elpd_diff` relative to the best model;
0 is best, and negative values are lower predictive scores. Interpret paired
score differences with their uncertainty and the scientific predictive target.
Fixed difference thresholds do not establish evidence for a causal mechanism.

**Check Pareto-k values:** Use the threshold reported by the installed ArviZ version and inspect influential observations when the importance-sampling diagnostic fails. Refit problematic leave-one-out cases or use appropriately structured K-fold validation; switching to WAIC is not a repair for unreliable PSIS-LOO. Record the predictive unit (observation, patient/group, or future time block), because holding out rows can answer a different question from predicting new groups or future data.

### Model Averaging

To combine predictive distributions, sample a mixture (weights are not model probabilities):

```python
from scripts.model_comparison import model_averaging

averaged_pred, weights = model_averaging(models, var_name='y_obs', random_seed=42)
```

For AR models, unconstrained independent Normal coefficients do not enforce
stationarity. Define initial conditions and the desired stationary/nonstationary
process explicitly; future-block validation generally differs from leaving out
individual time points. Wide Normal priors on log/logit coefficients can imply
extreme rates/probabilities: inspect their prior predictive implications.
