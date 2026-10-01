# PyMC Workflows and Scientific Checks

Targets PyMC 6.3.2 / ArviZ 1.3.0. The complete regression workflow is in
`standard_workflow.md`; runnable linear and hierarchical templates are under
`assets/` at the skill root. The fragments here are illustrative building blocks
requiring the displayed inputs. Missing-predictor assembly and log predictive
scoring have small numerical tests; these are not missingness-model validation.

## Train-only scaling and units

Estimate means/scales inside each training split, retain the values, and apply
them unchanged to held-out or prediction data. Reject zero-scale columns and
check design rank; standardization does not remove collinearity. Do not blindly
standardize binary/categorical codes, exposure offsets, or scientifically fixed
reference scales. Centering/scaling outcomes changes the meaning of prior scales
and predicted quantities.

For `x_scaled = (x - x_mean) / x_scale`, transform posterior coefficients as
`beta_original = beta_scaled / x_scale` and
`alpha_original = alpha_scaled - sum(beta_scaled * x_mean / x_scale)` when the
outcome is unchanged. If the outcome is standardized too, multiply coefficients
by its training scale and add its training mean to the intercept.

## Missing predictors

`pm.Data` rejects NaN/masked inputs; it does not automatically create a predictor
imputation model. Model the missing values explicitly and assemble them with
PyTensor indexed assignment:

```python
import numpy as np
import pymc as pm
import pytensor.tensor as pt

x = np.array([[1., np.nan], [2., 3.], [np.nan, 4.]])
mask = np.isnan(x)
with pm.Model() as model:
    missing = pm.Normal("x_missing", 0, sigma=1, shape=int(mask.sum()))
    x_complete = pt.set_subtensor(pt.as_tensor_variable(np.nan_to_num(x))[mask], missing)
    # Use x_complete in the scientific likelihood.
```

A `switch(mask, missing_vector, full_array)` does not broadcast or place the
missing values correctly. The independent Normal imputation above is only an
illustration: predictors can need joint distributions and missing-not-at-random
mechanisms. NaNs supplied directly to supported likelihood `observed` arrays
can trigger automatic imputation; inspect resulting variables and likelihood
factorization before LOO. Missing outcomes are not extra measured observations.

## Hierarchical and mixture identification

Check that group IDs map to integer positions consistently at training and
prediction time. Predictions for existing groups condition on those group
posteriors. Predictions for new groups integrate over the population distribution
and its uncertainty. Reuse each sampled new group effect across all rows of that
group, and separately add observation noise. Independent new effects for every
row accidentally model separate groups.

In mixture models, exchanging component labels can leave the likelihood
unchanged. Raw component means and R-hat can be misleading; use scientifically
justified identification constraints or label-invariant predictive quantities.
A good predictive fit can coexist with unresolved component labels or parameter
combinations. Simulated recovery checks should cover the actual data design and
noise scale, not only a favorable toy case.

## Model comparison and held-out scoring

`pm.compute_log_likelihood(idata, model=model)` adds pointwise contributions for
observed RVs while the model contains the current data. It does not automatically
turn a `Potential` into pointwise likelihood. Inspect dimensions and confirm one
contribution per intended holdout unit. Time series, multivariate observations,
imputation, and hierarchical groups need particular care.

ArviZ 1 uses:

```python
loo = az.loo(idata, var_name="y_obs", pointwise=True)
problem_units = (~np.isfinite(loo.pareto_k)) | (loo.pareto_k > loo.good_k)
comparison = az.compare({"model_a": idata_a, "model_b": idata_b},
                        var_name="y_obs", round_to="none")
```

ELPD is a predictive score, not a Bayes factor. Stacking weights optimize a
predictive combination, not posterior model probabilities. Compare models on the
same observed values, ordering, density measure and predictive unit. If responses
were transformed differently, include the log-Jacobian to return to a common
scale. High Pareto-k requires investigation, exact refits/moment matching where
supported, or suitable K-fold validation. WAIC is not a fallback cure.

For K-fold, split by the independent scientific unit and fit preprocessing only
on training data. `KFold(..., random_state=42)` uses `random_state`, not
`random_seed`; group or temporal splitters are often needed instead of random
rows. After a model is fitted and diagnosed, update **both** predictor and
outcome data containers to the held-out fold and resize their shared coordinates.
Compute held-out likelihood without overwriting the training likelihood group:

```python
with fitted_model:
    pm.set_data({"x": x_test, "y_data": y_test},
                coords={"obs_id": np.arange(len(y_test))})
    heldout = pm.compute_log_likelihood(idata, extend_inferencedata=False,
                                        progressbar=False)
```

The likelihood must have been defined with `observed=pm.Data("y_data", ...)`.
This fragment is schematic and needs the corresponding training model. Restore
training values/coordinates afterward. For independent held-out rows:

```python
from scipy.special import logsumexp
log_lik = heldout["y_obs"].stack(sample=("chain", "draw"))
log_predictive = logsumexp(log_lik.values, axis=-1) - np.log(log_lik.sizes["sample"])
elpd = log_predictive.sum()
```

Integrate over posterior uncertainty using **log mean exp**, not the mean or sum
of log likelihoods over draws. For a joint held-out group, first sum within-group
log likelihood for each posterior draw, then integrate. New-group scoring must
also integrate new group effects. A row-level score and a group-level score
answer different questions. Retain per-unit paired differences and uncertainty.

## Predictive combinations

For a predictive mean, align model weights by name and sum weighted mean
predictions. For intervals or full predictive draws, sample a model using its
weight, then a full predictive draw from that model. Averaging unrelated draw
pairs shrinks variance and can invent unsupported outcomes between modes. The
bundled `model_averaging` implements the mixture and validates matching
coordinates. Evaluate the ensemble on held-out data when possible.

## Saving and reporting

```python
idata.to_netcdf("posterior.nc")
predictions.to_netcdf("predictions.nc")
loaded = az.from_netcdf("posterior.nc")
```

DataTree files contain draws/data, not an executable model definition. Keep model
source, dependency lockfile, priors/units, training preprocessing, data versions,
seeds, sampler/backend configuration, diagnostics and failed checks beside them.
Rebuild a model from source for predictions. Pickled model graphs are not a stable
cross-version interchange format.

Report uncertainty with the interval kind and probability (`ci_kind="hdi"`,
`ci_prob=.95` for summaries; `prob=.95` for `az.hdi`). Do not label an ArviZ
default equal-tail interval as an HDI. Posterior checks, model comparison,
convergence diagnostics and external scientific validation answer distinct
questions and should be reported separately.

Sources: [log likelihood](https://www.pymc.io/projects/docs/en/stable/api/generated/pymc.stats.compute_log_likelihood.html),
[LOO](https://python.arviz.org/projects/stats/en/stable/api/generated/arviz_stats.loo.html),
[comparison](https://python.arviz.org/projects/stats/en/stable/api/generated/arviz_stats.compare.html),
[summary](https://python.arviz.org/projects/stats/en/stable/api/generated/arviz_stats.summary.html).
