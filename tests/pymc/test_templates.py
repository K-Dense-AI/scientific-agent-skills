"""Native API/uncertainty smoke checks; short chains do not validate inference."""
import importlib.util
from pathlib import Path

import pytest

np = pytest.importorskip('numpy')
pm = pytest.importorskip('pymc')
az = pytest.importorskip('arviz')
xr = pytest.importorskip('xarray')
pytest.importorskip('matplotlib').use('Agg')

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'pymc'


def load_template(name):
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / 'assets' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name,n_train,n_pred', [
    ('linear_regression_template', 60, 5),
    ('hierarchical_model_template', 72, 3),
])
def test_complete_templates_resize_restore_and_save_nonblank_plots(tmp_path, name, n_train, n_pred):
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt
    module = load_template(name)
    idata, predictions, model = module.run(draws=80, tune=80, chains=2, output_dir=tmp_path)
    assert idata.log_likelihood['y_obs'].shape == (2, 80, n_train)
    assert predictions.predictions['y_obs'].shape == (2, 80, n_pred)
    assert np.isfinite(predictions.predictions['y_obs']).all()
    with model:
        likelihood = pm.compute_log_likelihood(idata, extend_inferencedata=False, progressbar=False)
    assert likelihood['y_obs'].shape == (2, 80, n_train)
    loaded = az.from_netcdf(tmp_path / 'posterior.nc')
    np.testing.assert_allclose(loaded.posterior['sigma'], idata.posterior['sigma'])
    loaded.close()
    for filename in ['prior_predictive.png', 'posterior_predictive.png', 'trace.png']:
        pixels = mpimg.imread(tmp_path / filename)
        assert pixels[..., :3].min() < .5
    assert plt.get_fignums() == []


def test_unseen_group_includes_group_and_residual_variance():
    module = load_template('hierarchical_model_template')
    shape = (2, 5000)
    posterior = xr.Dataset({name: (('chain', 'draw'), np.full(shape, value)) for name, value in {
        'mu_alpha': 1., 'mu_beta': 2., 'sigma_alpha': 3., 'sigma_beta': 0., 'sigma': 4.
    }.items()})
    mean, outcome = module.predict_new_group(xr.DataTree.from_dict({'posterior': posterior}),
                                            np.array([0., 1.]), random_seed=17)
    np.testing.assert_allclose(mean[..., 1] - mean[..., 0], 2)
    assert mean[..., 0].var() == pytest.approx(9, rel=.05)
    assert outcome[..., 0].var() == pytest.approx(25, rel=.05)
    # Group variation is shared across rows; residual variation is not.
    assert (outcome[..., 1] - outcome[..., 0]).var() == pytest.approx(32, rel=.05)


def test_scaling_rejects_constant_columns_and_reuses_training_transform():
    module = load_template('linear_regression_template')
    with pytest.raises(ValueError, match='constant'):
        module.standardize_predictors(np.ones((4, 2)))
    scaled, mean, scale = module.standardize_predictors(np.array([[1., 2.], [3., 6.]]))
    np.testing.assert_allclose(scaled.mean(0), 0)
    np.testing.assert_allclose(scaled * scale + mean, [[1, 2], [3, 6]])


def test_missing_predictor_assembly_preserves_observed_entries():
    import pytensor
    import pytensor.tensor as pt
    x = np.array([[1., np.nan], [2., 3.], [np.nan, 4.]])
    mask = np.isnan(x)
    missing = pt.vector('missing')
    complete = pt.set_subtensor(pt.as_tensor_variable(np.nan_to_num(x))[mask], missing)
    result = pytensor.function([missing], complete)([10., 20.])
    np.testing.assert_array_equal(result, [[1, 10], [2, 3], [20, 4]])


def test_log_predictive_density_integrates_in_probability_space():
    from scipy.special import logsumexp
    loglik = np.log(np.array([[.1, .9], [.4, .6]]))
    np.testing.assert_allclose(logsumexp(loglik, axis=-1) - np.log(2), np.log([.5, .5]))
    assert not np.allclose(loglik.mean(-1), np.log([.5, .5]))


def test_advi_returns_finite_approximation_draws_without_claiming_convergence():
    with pm.Model():
        theta = pm.Normal('theta', 0, sigma=1)
        pm.Normal('y', theta, sigma=1, observed=np.array([.1, -.1, .2]))
        approximation = pm.fit(n=30, random_seed=3, progressbar=False)
        draws = approximation.sample(draws=12, random_seed=4)
    assert draws.posterior['theta'].shape == (1, 12)
    assert np.isfinite(draws.posterior['theta']).all()
