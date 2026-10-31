"""Native 0.28 contracts on small synthetic censored outcomes."""

from pathlib import Path
import sys

import pytest

pytest.importorskip("sksurv")
import numpy as np
import pandas as pd
from numpy.testing import assert_allclose
from sksurv.util import Surv

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scikit-survival"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import _common
import competing_risk_cif as cif_helper
import evaluate_survival_metrics as metrics_helper
import train_survival_model as trainer


@pytest.fixture
def sample():
    rng = np.random.default_rng(31)
    X = rng.normal(size=(40, 3))
    y = Surv.from_arrays(np.arange(40) % 3 != 0, np.exp(-X[:, 0] + rng.normal(size=40)))
    return X, y


def test_ipcridge_predictions_are_original_time_and_score_reverses(sample):
    from sksurv.linear_model import IPCRidge
    from sksurv.metrics import concordance_index_censored, as_concordance_index_ipcw_scorer

    X, y = sample
    model = IPCRidge(alpha=1).fit(X, y)
    prediction = model.predict(X)
    assert_allclose(prediction, np.exp(X @ model.coef_ + model.intercept_))
    assert_allclose(model.score(X, y), concordance_index_censored(y["event"], y["time"], -prediction)[0])
    # The wrapper calls raw predict; users need a risk adapter for time models.
    wrapped = as_concordance_index_ipcw_scorer(model, tau=np.quantile(y["time"], .7)).fit(X, y)
    from sksurv.metrics import concordance_index_ipcw
    assert_allclose(wrapped.score(X, y), concordance_index_ipcw(y, y, wrapped.predict(X), tau=wrapped.tau)[0])


def test_coxnet_baseline_requires_fitted_alpha(sample):
    from sksurv.linear_model import CoxnetSurvivalAnalysis
    X, y = sample
    model = CoxnetSurvivalAnalysis(alphas=[.2, .05], fit_baseline_model=True).fit(X, y)
    assert model.predict(X, alpha=.1).shape == (40,)
    with pytest.raises(ValueError, match="alpha must"):
        model.predict_survival_function(X, alpha=.1)
    p = model.predict_survival_function(X[:2], alpha=.05, return_array=True)
    assert p.shape == (2, len(model.unique_times_))
    assert np.all(np.diff(p, axis=1) <= 1e-12)


@pytest.mark.parametrize("name", ["coxph", "coxnet", "random-forest", "extra-trees", "gradient-boosting"])
def test_all_bundled_models_export_valid_probability_curves(name):
    frame, numeric, categorical = _common.synthetic_survival_frame(rows=140)
    model, train, test, _ = trainer.train_and_report(
        frame, event_column="event", time_column="time", numeric_columns=numeric,
        categorical_columns=categorical, model_name=name, test_fraction=.25,
        seed=_common.DEFAULT_SEED, tune=False, outer_folds=2, inner_folds=2,
    )
    arrays = trainer.prediction_archive(model, test[0], train[1], test[1], test[2])
    assert "survival" in arrays
    report = metrics_helper.evaluate(arrays)
    assert np.isfinite(report["metrics"]["integrated_brier_score"])


@pytest.mark.parametrize("kind", ["linear", "kernel"])
@pytest.mark.parametrize("ratio", [0., .5, 1.])
def test_svm_original_time_or_risk_direction(sample, kind, ratio):
    from sksurv.svm import FastSurvivalSVM, FastKernelSurvivalSVM
    X, y = sample
    cls = FastSurvivalSVM if kind == "linear" else FastKernelSurvivalSVM
    kwargs = {} if kind == "linear" else {"kernel": "linear"}
    model = cls(rank_ratio=ratio, max_iter=1000, tol=1e-6, random_state=17, **kwargs).fit(X, y)
    linear = X @ model.coef_ if kind == "linear" else (X @ X.T) @ model.coef_
    expected = -linear if ratio == 1 else np.exp(linear)
    assert_allclose(model.predict(X), expected)


@pytest.mark.parametrize("name", ["HingeLossSurvivalSVM", "MinlipSurvivalAnalysis", "NaiveSurvivalSVM"])
def test_small_additional_svm_solvers(sample, name):
    import sksurv.svm as svm
    X, y = sample
    model = getattr(svm, name)().fit(X[:12], y[:12])
    assert np.isfinite(model.predict(X[:3])).all()


@pytest.mark.parametrize("loss", ["coxph", "ipcwls", "squared"])
@pytest.mark.parametrize("name", ["GradientBoostingSurvivalAnalysis", "ComponentwiseGradientBoostingSurvivalAnalysis"])
def test_boosting_losses_and_probability_capability(sample, loss, name):
    import sksurv.ensemble as ensemble
    X, y = sample
    if loss == "ipcwls":
        # Reproduce the release defect before exercising its supported branch.
        with pytest.raises(ValueError, match="smaller zero"):
            getattr(ensemble, name)(loss=loss, n_estimators=2).fit(X, y)
        y = y.copy()
        y["time"] *= 100.0  # tiny fixture only; not a scientific workaround
    model = getattr(ensemble, name)(loss=loss, n_estimators=12, random_state=17).fit(X, y)
    pred = model.predict(X[:3])
    assert np.isfinite(pred).all()
    if loss == "coxph":
        p = model.predict_survival_function(X[:3], return_array=True)
        assert np.all((p >= 0) & (p <= 1))
    else:
        assert np.all(pred > 0)
        with pytest.raises(ValueError):
            model.predict_survival_function(X[:3])
    if loss == "ipcwls":
        changed = y.copy()
        changed["event"] = True
        alternate = getattr(ensemble, name)(loss=loss, n_estimators=12, random_state=17).fit(X, changed)
        # 0.28 logs IPC-weighted loss, but its gradient omits those weights.
        assert_allclose(model.predict(X), alternate.predict(X))


def test_forest_low_memory_and_tree_nan_support(sample):
    from sksurv.ensemble import RandomSurvivalForest
    from sksurv.tree import SurvivalTree
    from sklearn.inspection import permutation_importance
    X, y = sample
    missing = X.copy(); missing[::7, 0] = np.nan
    assert np.isfinite(SurvivalTree(max_depth=2).fit(missing, y).predict(missing)).all()
    model = RandomSurvivalForest(n_estimators=8, low_memory=True, random_state=17).fit(X, y)
    assert np.isfinite(model.predict(X)).all()
    with pytest.raises(NotImplementedError):
        model.predict_survival_function(X)
    result = permutation_importance(model, X, y, n_repeats=2, random_state=17)
    assert result.importances.shape == (3, 2)


def test_fitted_clinical_kernel_keeps_training_ranges():
    from sksurv.kernels import clinical_kernel, ClinicalKernelTransform
    train = pd.DataFrame({"x": [0., 1., 2.]})
    test = pd.DataFrame({"x": [1., 4.]})
    transform = ClinicalKernelTransform().fit(train)
    a = transform.transform(test)
    assert_allclose(a[0], transform.transform(test.iloc[:1])[0])
    assert not np.allclose(clinical_kernel(test, train)[0], clinical_kernel(test.iloc[:1], train)[0])
    assert a.min() < 0  # upstream has no clipping for values beyond fitted ranges


def test_csv_duplicate_headers_rejected_before_pandas_mangles(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("event,time,time\n1,2,200\n")
    with pytest.raises(_common.CliError, match="unique before parsing"):
        _common.read_csv(p)


@pytest.mark.parametrize("variance", ["Aalen", "Dinse", "Dinse_Approx"])
def test_cif_total_interval_matches_requested_km_level(variance):
    from sksurv.nonparametric import kaplan_meier_estimator
    event = np.array([1, 2, 0, 1, 2, 0]); time = np.arange(1., 7.)
    _, arrays = cif_helper.estimate_cif(event, time, confidence=True, confidence_level=.8, variance_type=variance)
    t, s, ci = kaplan_meier_estimator(event > 0, time, conf_type="log-log", conf_level=.8)
    assert_allclose(arrays["time"], t)
    assert_allclose(arrays["cumulative_incidence"][0], 1 - s)
    assert_allclose(arrays["confidence_interval"][0], 1 - ci[::-1])
    intervals = arrays["confidence_interval"]
    assert np.all(intervals[:, 0] <= intervals[:, 1])


def test_cif_conditional_time_and_extrapolation_fail_clearly():
    event = [1, 2, 0, 1, 2, 0]; time = np.arange(1., 7.)
    with pytest.raises(_common.CliError, match="conditional CIF"):
        cif_helper.estimate_cif(event, time, time_min=2.5)
    with pytest.raises(_common.CliError, match="observed follow-up"):
        cif_helper.estimate_cif(event, time, horizons=[7.])
    with pytest.raises(_common.CliError, match="must not exceed"):
        cif_helper.normalize_competing_event([0, 1, 1e30])


def test_auc_no_cases_rejected():
    arrays = metrics_helper.synthetic_metric_inputs()
    arrays["test_event"] = arrays["test_time"] > arrays["times"][-1]
    with pytest.raises(_common.CliError, match="observed case"):
        metrics_helper.evaluate(arrays)


def test_prediction_archive_does_not_hide_survival_failure(sample):
    class BrokenProbabilityModel:
        def predict_survival_function(self, X):
            raise ValueError("unsupported horizon")
    X, y = sample
    with pytest.raises(_common.CliError, match="could not export"):
        trainer.prediction_archive(BrokenProbabilityModel(), X, y, y, X[:, 0])


def test_metric_scorer_wrappers_and_ibs_integral(sample):
    from sksurv.metrics import as_cumulative_dynamic_auc_scorer, as_integrated_brier_score_scorer
    from sksurv.linear_model import CoxPHSurvivalAnalysis
    X, y = sample
    times = np.quantile(y["time"], [.3, .5, .7])
    for cls in [as_cumulative_dynamic_auc_scorer, as_integrated_brier_score_scorer]:
        wrapped = cls(CoxPHSurvivalAnalysis(alpha=.1), times=times).fit(X, y)
        assert np.isfinite(wrapped.score(X, y))
    report = metrics_helper.evaluate(metrics_helper.synthetic_metric_inputs())
    bs = report["metrics"]["brier_score"]
    expected = np.trapezoid(bs["values"], bs["times"]) / np.ptp(bs["times"])
    assert_allclose(report["metrics"]["integrated_brier_score"], expected)


def test_surv_encoder_and_metadata_routing(sample):
    from sklearn import config_context
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sksurv.linear_model import CoxnetSurvivalAnalysis
    from sksurv.preprocessing import OneHotEncoder
    frame = pd.DataFrame({"event": [1, 0, 1], "time": [1., 2., 3.]})
    y = Surv.from_dataframe("event", "time", frame)
    assert y.dtype.names == ("event", "time")
    features = pd.DataFrame({"x": [1., 2., 3.], "g": pd.Categorical(["a", "b", "a"])})
    encoded = OneHotEncoder().fit_transform(features)
    assert encoded.shape == (3, 2)
    X, y = sample
    with config_context(enable_metadata_routing=True):
        model = CoxnetSurvivalAnalysis(alphas=[.2, .05]).set_predict_request(alpha=True)
        pipe = make_pipeline(StandardScaler(), model).fit(X, y)
        assert pipe.predict(X, alpha=.2).shape == (40,)


def test_raw_arff_keeps_training_values_while_standardized_loader_pools(tmp_path):
    from sksurv.io import loadarff
    from sksurv.datasets import load_arff_files_standardized
    header = "@relation synthetic\n@attribute x numeric\n@attribute event {yes,no}\n@attribute time numeric\n@data\n"
    train = tmp_path / "train.arff"; test = tmp_path / "test.arff"
    train.write_text(header + "0,yes,1\n2,no,2\n")
    test.write_text(header + "100,yes,1.5\n200,no,3\n")
    raw = loadarff(train)
    assert_allclose(raw["x"], [0., 2.])
    pooled, _, _, _ = load_arff_files_standardized(train, ["event", "time"], pos_label="yes", path_testing=test)
    expected = (np.array([0., 2.]) - np.mean([0., 2., 100., 200.])) / np.std([0., 2., 100., 200.], ddof=1)
    assert_allclose(pooled["x"], expected)


def test_uno_tau_does_not_imply_auc_followup_support():
    from sksurv.metrics import concordance_index_ipcw, cumulative_dynamic_auc
    train = Surv.from_arrays([True, False, True, False], [1., 2., 3., 4.])
    test = Surv.from_arrays([True, False, True], [1.5, 2.5, 5.])
    risk = np.array([3., 2., 1.])
    assert np.isfinite(concordance_index_ipcw(train, test, risk, tau=3.)[0])
    with pytest.raises(ValueError, match="censoring survival"):
        cumulative_dynamic_auc(train, test, risk, [2., 3.])
