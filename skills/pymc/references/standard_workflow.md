# Standard Bayesian Workflow

This self-contained example was executed with PyMC 6.3.2, PyTensor 3.3.2 and
ArviZ 1.3.0. It tests the API and changing prediction row counts with small
synthetic data. Two short chains cannot validate a scientific inference.
For a real analysis, stop after the prior predictive plot to inspect it, and
choose sampling effort using numerical diagnostics and the estimand's MCSE.

```python
import arviz as az
import numpy as np
import pymc as pm

rng = np.random.default_rng(7)
x = np.linspace(-1, 1, 30)
y = 0.5 + 1.2 * x + rng.normal(0, 0.3, len(x))
with pm.Model(coords={"obs_id": np.arange(len(y))}) as model:
    x_data = pm.Data("x", x, dims="obs_id")
    alpha = pm.Normal("alpha", 0, sigma=1)
    beta = pm.Normal("beta", 0, sigma=1)
    sigma = pm.HalfNormal("sigma", sigma=1)
    mu = pm.Deterministic("mu", alpha + beta * x_data, dims="obs_id")
    pm.Normal("y_obs", mu, sigma=sigma, observed=y,
              shape=x_data.shape[0], dims="obs_id")
    prior = pm.sample_prior_predictive(draws=50, random_seed=7)

prior_plot = az.plot_ppc_dist(prior, group="prior_predictive", num_samples=20)
with model:
    idata = pm.sample(draws=80, tune=80, chains=2, cores=1,
                      nuts_sampler="pymc", target_accept=.9,
                      random_seed=7, progressbar=False)
    pm.compute_log_likelihood(idata, progressbar=False)
    pm.sample_posterior_predictive(idata, extend_inferencedata=True,
                                  random_seed=8, progressbar=False)

summary = az.summary(idata, var_names=["alpha", "beta", "sigma"], round_to="none")
print(summary)
posterior_plot = az.plot_ppc_dist(idata, num_samples=20)
assert idata.log_likelihood["y_obs"].shape == (2, 80, 30)

x_new = np.array([-0.5, 0., 0.5, 1.5])
with model:
    pm.set_data({"x": x_new}, coords={"obs_id": np.arange(len(x_new))})
    predictions = pm.sample_posterior_predictive(
        idata, var_names=["mu", "y_obs"], predictions=True,
        random_seed=9, progressbar=False)
    pm.set_data({"x": x}, coords={"obs_id": np.arange(len(x))})

assert predictions.predictions["y_obs"].shape == (2, 80, 4)
mean = predictions.predictions["y_obs"].mean(("chain", "draw"))
interval = az.hdi(predictions.predictions["y_obs"], prob=.95)
print(mean, interval.sel(ci_bound="lower"), interval.sel(ci_bound="upper"))
```

For saved figures use `prior_plot.savefig("prior.png")` and the equivalent for
the posterior plot. For Matplotlib, close the actual figure with
`plt.close(prior_plot.viz["figure"].item())` after importing `matplotlib.pyplot`.
The runnable templates save/close plots and serialize posterior and prediction
trees separately.

## Data and prediction contract

`pm.Data` can change values and shape, but not array rank. With ordinary PyMC
`dims`, labels document axes; they do not perform xarray-style symbolic alignment.
Tie the likelihood's row count to the predictor shape, and supply replacement
coordinates when a named dimension changes length. Update all data containers
sharing that dimension in one `pm.set_data` call. `mutable=True`, `MutableData`,
and `coords_mutable` are unnecessary legacy patterns for this target.

Store out-of-sample results in the `predictions` group. `var_names` selects
returned variables; it does not force posterior variables to be resampled.
Deterministics depending on changed data are recomputed. `sample_vars` explicitly
resamples named variables and `freeze_vars` deliberately reuses them; review
warnings about changed data and posterior variables rather than suppressing them.

`mu` represents uncertainty about the conditional mean; `y_obs` also includes
observation noise. Neither automatically accounts for model misspecification,
selection bias, or distribution shift at extrapolated predictors.

## Diagnostics and scientific interpretation

Use the bundled diagnostic helper with the selected parameters, inspect traces
and joint posteriors, and evaluate MCSE for the actual scientific contrast. R-hat
needs multiple independent chains. A NaN R-hat, absent sampler statistics or a
constant parameter is not a pass. Low ESS calls for investigating geometry as
well as increasing sampling effort. Divergences require explanation and repair;
there is no generally acceptable nonzero quota.

Prior predictive checks test implied assumptions; posterior predictive checks
can reveal inadequacy of those assumptions. Neither proves parameter
identifiability or generalization. Use prior sensitivity, simulated recovery and
appropriate held-out validation where the scientific conclusion requires them.

Sources: [Data](https://www.pymc.io/projects/docs/en/stable/api/generated/pymc.Data.html),
[forward sampling](https://www.pymc.io/projects/docs/en/stable/_modules/pymc/sampling/forward.html),
[log likelihood](https://www.pymc.io/projects/docs/en/stable/api/generated/pymc.stats.compute_log_likelihood.html).
