"""Runnable synthetic PyMC 6.3.2 / ArviZ 1.3 linear regression template.

Replace the synthetic data with your measurements, preserve training scaling,
and choose priors in outcome units. Short runs only exercise the workflow.
"""

import argparse
from pathlib import Path

import arviz as az
import matplotlib.pyplot as plt
import numpy as np
import pymc as pm


def standardize_predictors(x):
    """Fit a scaling transform to finite, nonconstant training columns."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError("Predictors must be a finite 2D array")
    mean, scale = x.mean(axis=0), x.std(axis=0)
    if (scale == 0).any():
        raise ValueError("Remove constant columns before standardizing")
    return (x - mean) / scale, mean, scale


def build_model(x_scaled, y, predictor_names):
    coords = {'predictors': predictor_names, 'obs_id': np.arange(len(y))}
    with pm.Model(coords=coords) as model:
        x_data = pm.Data('X_scaled', x_scaled, dims=('obs_id', 'predictors'))
        alpha = pm.Normal('alpha', mu=0, sigma=1)
        beta = pm.Normal('beta', mu=0, sigma=1, dims='predictors')
        sigma = pm.HalfNormal('sigma', sigma=1)
        mu = pm.Deterministic('mu', alpha + pm.math.dot(x_data, beta), dims='obs_id')
        pm.Normal('y_obs', mu=mu, sigma=sigma, observed=y,
                  shape=x_data.shape[0], dims='obs_id')
    return model


def run(draws=1000, tune=1000, chains=4, output_dir='linear_results'):
    rng = np.random.default_rng(42)
    x = rng.normal(size=(60, 3))
    y = 0.5 + x @ np.array([1.5, -0.8, 2.1]) + rng.normal(0, 0.5, len(x))
    x_scaled, x_mean, x_scale = standardize_predictors(x)
    names = ['predictor1', 'predictor2', 'predictor3']
    model = build_model(x_scaled, y, names)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    def save(collection, name):
        collection.savefig(output / name, dpi=150, bbox_inches='tight')
        plt.close(collection.viz['figure'].item())

    with model:
        prior = pm.sample_prior_predictive(draws=100, random_seed=41)
    save(az.plot_ppc_dist(prior, group='prior_predictive', num_samples=30), 'prior_predictive.png')
    # Inspect the prior predictive plot before fitting real data.
    with model:
        idata = pm.sample(draws=draws, tune=tune, chains=chains, cores=1,
                          nuts_sampler='pymc', target_accept=0.9, random_seed=42,
                          progressbar=False)
        pm.compute_log_likelihood(idata, progressbar=False)
        pm.sample_posterior_predictive(idata, extend_inferencedata=True,
                                      random_seed=43, progressbar=False)
    summary = az.summary(idata, var_names=['alpha', 'beta', 'sigma'], round_to='none',
                         ci_kind='hdi', ci_prob=0.95)
    print(summary)
    print('[INFO] Check R-hat, bulk/tail ESS, MCSE, divergences and BFMI before interpretation.')
    save(az.plot_trace_dist(idata, var_names=['alpha', 'beta', 'sigma']), 'trace.png')
    save(az.plot_ppc_dist(idata, num_samples=30), 'posterior_predictive.png')
    save(az.plot_dist(idata, var_names=['alpha', 'beta', 'sigma'], ci_kind='hdi', ci_prob=.95), 'posterior.png')
    save(az.plot_forest(idata, var_names=['beta'], combined=True, ci_kind='hdi', ci_probs=[.5, .95]), 'coefficients.png')

    x_new = rng.normal(size=(5, 3))
    with model:
        pm.set_data({'X_scaled': (x_new - x_mean) / x_scale},
                    coords={'obs_id': np.arange(len(x_new))})
        predictions = pm.sample_posterior_predictive(
            idata, var_names=['mu', 'y_obs'], predictions=True, random_seed=44,
            progressbar=False)
        # Restore the fitting state before any further training log-likelihood work.
        pm.set_data({'X_scaled': x_scaled}, coords={'obs_id': np.arange(len(y))})
    # mu is conditional mean uncertainty; y_obs includes observation noise.
    interval = az.hdi(predictions.predictions['y_obs'], prob=.95)
    interval.to_dataframe(name='prediction_interval').to_csv(output / 'prediction_intervals.csv')
    idata.to_netcdf(output / 'posterior.nc')
    predictions.to_netcdf(output / 'predictions.nc')
    summary.to_csv(output / 'summary.csv')
    np.savez(output / 'training_scaling.npz', mean=x_mean, scale=x_scale)
    return idata, predictions, model


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draws', type=int, default=1000)
    parser.add_argument('--tune', type=int, default=1000)
    parser.add_argument('--chains', type=int, default=4)
    parser.add_argument('--output-dir', default='linear_results')
    run(**vars(parser.parse_args()))
