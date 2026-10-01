"""Synthetic hierarchical regression with existing- and new-group predictions.

Targets PyMC 6.3.2 / ArviZ 1.3. This model assumes independent group intercept
and slope effects. For correlated effects use an LKJ Cholesky model instead.
Short runs exercise APIs, not scientific validation.
"""

import argparse
from pathlib import Path

import arviz as az
import matplotlib.pyplot as plt
import numpy as np
import pymc as pm


def build_model(x, groups, y, group_names):
    with pm.Model(coords={'groups': group_names, 'obs': np.arange(len(y))}) as model:
        x_data = pm.Data('X_data', x, dims='obs')
        groups_data = pm.Data('groups_data', groups, dims='obs')
        mu_alpha = pm.Normal('mu_alpha', mu=0, sigma=5)
        sigma_alpha = pm.HalfNormal('sigma_alpha', sigma=2)
        mu_beta = pm.Normal('mu_beta', mu=0, sigma=2)
        sigma_beta = pm.HalfNormal('sigma_beta', sigma=1)
        alpha_offset = pm.Normal('alpha_offset', 0, 1, dims='groups')
        beta_offset = pm.Normal('beta_offset', 0, 1, dims='groups')
        alpha = pm.Deterministic('alpha', mu_alpha + sigma_alpha * alpha_offset, dims='groups')
        beta = pm.Deterministic('beta', mu_beta + sigma_beta * beta_offset, dims='groups')
        sigma = pm.HalfNormal('sigma', 1)
        mu = alpha[groups_data] + beta[groups_data] * x_data
        pm.Normal('y_obs', mu, sigma=sigma, observed=y, shape=x_data.shape[0], dims='obs')
    return model


def predict_new_group(idata, x_new, random_seed=42):
    """Predict several observations sharing ONE previously unseen group.

    Draw new group effects once per posterior draw and reuse across x_new;
    add independent residual noise per observation. Returns (mean, outcome)
    arrays with shape (chain, draw, new_observation).
    """
    x_new = np.asarray(x_new, dtype=float)
    if x_new.ndim != 1 or not np.isfinite(x_new).all():
        raise ValueError("x_new must be a finite vector")
    rng = np.random.default_rng(random_seed)
    posterior = idata.posterior
    mu_a, mu_b = posterior['mu_alpha'].values, posterior['mu_beta'].values
    alpha_new = mu_a + posterior['sigma_alpha'].values * rng.normal(size=mu_a.shape)
    beta_new = mu_b + posterior['sigma_beta'].values * rng.normal(size=mu_b.shape)
    mean = alpha_new[..., None] + beta_new[..., None] * x_new
    outcome = mean + posterior['sigma'].values[..., None] * rng.normal(size=mean.shape)
    return mean, outcome


def run(draws=1000, tune=1000, chains=4, output_dir='hierarchical_results'):
    rng = np.random.default_rng(42)
    n_groups, n_per_group = 6, 12
    group_names = [f'group_{i}' for i in range(n_groups)]
    groups = np.repeat(np.arange(n_groups), n_per_group)
    x = rng.normal(size=len(groups))
    alpha = rng.normal(1, .6, n_groups)
    beta = rng.normal(1.5, .3, n_groups)
    y = alpha[groups] + beta[groups] * x + rng.normal(0, .5, len(x))
    model = build_model(x, groups, y, group_names)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    def save(collection, name):
        collection.savefig(output / name, dpi=150, bbox_inches='tight')
        plt.close(collection.viz['figure'].item())

    with model:
        prior = pm.sample_prior_predictive(draws=100, random_seed=40)
    save(az.plot_ppc_dist(prior, group='prior_predictive', num_samples=30), 'prior_predictive.png')
    # Inspect prior implications before fitting real data.
    with model:
        idata = pm.sample(draws=draws, tune=tune, chains=chains, cores=1,
                          nuts_sampler='pymc', target_accept=.95, random_seed=42,
                          progressbar=False)
        pm.compute_log_likelihood(idata, progressbar=False)
        pm.sample_posterior_predictive(idata, extend_inferencedata=True,
                                      random_seed=43, progressbar=False)
    variables = ['mu_alpha', 'sigma_alpha', 'mu_beta', 'sigma_beta', 'sigma']
    summary = az.summary(idata, var_names=variables + ['alpha', 'beta'],
                         round_to='none', ci_kind='hdi', ci_prob=.95)
    print(summary)
    print('[INFO] Inspect diagnostics and prior sensitivity; six groups weakly constrain group scales.')
    save(az.plot_trace_dist(idata, var_names=variables), 'trace.png')
    save(az.plot_ppc_dist(idata, num_samples=30), 'posterior_predictive.png')
    save(az.plot_forest(idata, var_names=['alpha', 'beta'], combined=True,
                        ci_kind='hdi', ci_probs=[.5, .95]), 'group_parameters.png')
    new_x, new_groups = np.array([-1., 0., 1.]), np.array([0, 2, 4])
    with model:
        pm.set_data({'X_data': new_x, 'groups_data': new_groups}, coords={'obs': np.arange(3)})
        predictions = pm.sample_posterior_predictive(idata, predictions=True,
                                                   random_seed=44, progressbar=False)
        pm.set_data({'X_data': x, 'groups_data': groups}, coords={'obs': np.arange(len(y))})
    interval = az.hdi(predictions.predictions['y_obs'], prob=.95)
    interval.to_dataframe(name='prediction_interval').to_csv(output / 'existing_group_intervals.csv')
    new_mean, new_outcome = predict_new_group(idata, new_x)
    np.savez(output / 'new_group_predictions.npz', x=new_x, mean=new_mean, outcome=new_outcome)
    idata.to_netcdf(output / 'posterior.nc')
    predictions.to_netcdf(output / 'predictions.nc')
    summary.to_csv(output / 'summary.csv')
    return idata, predictions, model


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draws', type=int, default=1000)
    parser.add_argument('--tune', type=int, default=1000)
    parser.add_argument('--chains', type=int, default=4)
    parser.add_argument('--output-dir', default='hierarchical_results')
    run(**vars(parser.parse_args()))
