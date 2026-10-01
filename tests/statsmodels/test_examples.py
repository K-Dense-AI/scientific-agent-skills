"""Execute the contextual documentation with small deterministic native fixtures.

These are API/numerical regression checks, not tests of scientific calibration.
Each reference is run in its own namespace; row/result fixtures are selected for
its documented model family. All shipped Python examples are exercised.
"""
from pathlib import Path
import re

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
sm = pytest.importorskip("statsmodels.api")
pytest.importorskip("sklearn")
matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from scipy.special import expit
import statsmodels.formula.api as smf
from statsmodels.discrete.discrete_model import Logit, Probit, MNLogit, Poisson, NegativeBinomial
from statsmodels.discrete.count_model import ZeroInflatedPoisson
from statsmodels.tsa.arima.model import ARIMA

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "statsmodels"


def blocks(name):
    return re.findall(r"```python\n(.*?)```", (SKILL_ROOT / "references" / name).read_text(), re.S)


def run(block, namespace, label):
    exec(compile(block, label, "exec"), namespace)
    plt.close("all")


@pytest.fixture
def data():
    rng = np.random.default_rng(42)
    n = 240
    X_data = pd.DataFrame(rng.normal(size=(n, 3)), columns=["x1", "x2", "x3"])
    X = sm.add_constant(X_data)
    y = pd.Series(1 + 0.6 * X_data.x1 - 0.2 * X_data.x2 + rng.normal(size=n))
    y_binary = pd.Series(rng.binomial(1, expit(-0.3 + 0.5 * X_data.x1)))
    y_counts = pd.Series(rng.negative_binomial(2, 2 / (2 + np.exp(0.8 + 0.25 * X_data.x1))))
    y_positive = pd.Series(rng.gamma(5, 0.5, n))
    group_ids = np.repeat(np.arange(30), 8)
    groups = np.repeat(["a", "b", "c"], n // 3)
    df = X_data.copy()
    df["x"] = df.x1
    df["y"] = y_binary
    df["count"] = y_counts
    df["success"] = y_binary
    df["category"] = groups
    df["group"] = groups
    df["response"] = y
    df["factor1"] = np.tile(["a", "b"], n // 2)
    df["factor2"] = groups
    df["subject_id"] = np.repeat(np.arange(n // 3), 3)
    df["time"] = np.tile([0, 1, 2], n // 3)
    df["score"] = y
    df["treatment"] = rng.binomial(1, 0.5, n)
    df["post"] = np.tile([0, 1], n // 2)
    df["outcome"] = y
    df["unit_id"] = np.repeat(np.arange(n // 2), 2)
    ols = sm.OLS(y, X).fit()
    logit = Logit(y_binary, X).fit(disp=0)
    poisson = Poisson(y_counts, X).fit(disp=0)
    new_features = X_data.iloc[:1].copy()
    X_new = sm.add_constant(new_features, has_constant="add")
    y_multi = pd.Series(rng.integers(0, 3, n), name="choice")
    df["choice"] = y_multi
    namespace = dict(np=np, pd=pd, sm=sm, smf=smf, plt=plt, stats=stats, rng=rng,
                     X_data=X_data, X=X, y=y, df=df, n=n, X_new_data=new_features,
                     new_features=new_features, X_new=X_new, new_df=df.iloc[:2],
                     results=ols, model1=ols, model2=ols, model1_results=ols,
                     model2_results=ols, model3_results=ols, full_model=ols,
                     reduced_model=sm.OLS(y, X.iloc[:, :2]).fit(),
                     X_restricted=X.iloc[:, :2], X_reduced=X.iloc[:, :2], X_full=X,
                     y_binary=y_binary, y_counts=y_counts, y_cost=y_positive,
                     y_positive=y_positive, y_multi=y_multi, y_ordered=y_multi,
                     n_categories=3, exposure=rng.uniform(0.8, 2, n),
                     weights=np.ones(n), error_variance=np.ones(n), Sigma=np.eye(n),
                     group_ids=group_ids, cluster_ids=group_ids, X_random=X.iloc[:, :2],
                     groups=groups, data=np.asarray(y), group1=np.asarray(y[:80]),
                     group2=np.asarray(y[80:160]), group3=np.asarray(y[160:]),
                     before=np.asarray(y[:80]), after=np.asarray(y[80:160]), mu_0=0,
                     variable1=np.tile([0, 1], n // 2), variable2=groups,
                     residuals=ols.resid, exog=X, influence=ols.get_influence(),
                     Logit=Logit, Probit=Probit, MNLogit=MNLogit, Poisson=Poisson,
                     NegativeBinomial=NegativeBinomial, ZeroInflatedPoisson=ZeroInflatedPoisson,
                     logit_results=logit, probit_results=Probit(y_binary, X).fit(disp=0),
                     X_inflation=X.iloc[:, :1], X_count=X, claims=y_counts,
                     customer_features=X_data, purchased=y_binary, mode_choice=y_multi,
                     num_visits=y_counts, new_patient_X=X_new, predictions=(logit.predict(X) > .5).astype(int),
                     probs=logit.predict(X), family=sm.families.Poisson(),
                     confounders=X_data, treatment=df.treatment, outcome=y,
                     a=20, b=5, c=10, d=30, tables_list=[np.array([[20,5],[10,30]])]*3)
    return namespace, dict(ols=ols, logit=logit, poisson=poisson, y=y, X=X,
                           y_binary=y_binary, y_counts=y_counts, y_positive=y_positive,
                           df=df, y_multi=y_multi)


def test_quick_start():
    namespace = {}
    for i, code in enumerate(blocks("quick_start_guide.md"), 1):
        run(code, namespace, f"quick-start:{i}")
    assert namespace["X_new"].shape == (1, 3)
    assert namespace["mean_prediction"].conf_int().shape == (1, 2)
    assert namespace["forecast"].predicted_mean.index.equals(namespace["test_series"].index)
    p = namespace["pred_summary"]
    assert (p.obs_ci_upper - p.obs_ci_lower > p.mean_ci_upper - p.mean_ci_lower).all()


def test_linear_reference(data):
    ns, base = data
    for i, code in enumerate(blocks("linear_models.md"), 1):
        if i in (13, 14, 15, 16, 17, 18, 19):
            ns.update(results=base["ols"], X=base["X"])
        if i == 12:
            ns["y"] = (base["y"] + ns["rng"].normal(size=30)[ns["group_ids"]]
                       + ns["rng"].normal(size=30)[ns["group_ids"]] * ns["X_data"].x1)
        run(code, ns, f"linear-models:{i}")
    assert np.allclose(ns["results_hc3"].params, base["ols"].params)
    assert ns["params_over_time"].shape == (4, 240)
    assert ns["rolling_params"].iloc[59:].notna().all().all()
    assert ns["pred_new"].predicted_mean.shape == (1,)


def test_glm_reference(data):
    ns, base = data
    glm = sm.GLM(base["y_counts"], base["X"], family=sm.families.Poisson()).fit()
    for i, code in enumerate(blocks("glm.md"), 1):
        ns.update(X=base["X"], y=base["y_counts"], results=glm, family=sm.families.Poisson())
        if i in (1, 2, 11, 20, 22):
            ns.update(y=base["y_binary"], family=sm.families.Binomial())
            ns["results"] = sm.GLM(base["y_binary"], base["X"], family=sm.families.Binomial()).fit()
        if i == 6: ns["y"] = base["y"]
        if i in (7, 8, 9): ns["y"] = base["y_positive"]
        if i == 20:
            ns.update(model1_results=ns["results"], model2_results=ns["results"], model3_results=ns["results"])
        run(code, ns, f"glm:{i}")
    assert ns["mean_ci"].shape == (1, 2)
    assert np.isclose(ns["pseudo_r2"], 1 - glm.llf / glm.llnull)
    assert np.allclose(ns["results_robust"].params, glm.params)
    assert np.isfinite(ns["results_cluster"].bse).all()
    assert np.isfinite(ns["d_fitted_scaled"]).all()


def test_discrete_reference(data):
    ns, base = data
    multinomial = MNLogit(base["y_multi"], base["X"]).fit(disp=0)
    ordinal = None
    zip_result = None
    for i, code in enumerate(blocks("discrete_choice.md"), 1):
        ns.update(X=base["X"], y=base["y_binary"], results=base["logit"])
        if i in (8, 9, 10, 26, 33): ns.update(y=base["y_multi"], results=multinomial)
        if i in (12, 13, 14, 15, 16, 17, 27, 28, 34): ns.update(results=base["poisson"])
        if i == 11:
            ns.update(X_alternatives=ns["X_data"], choice_set_id=np.repeat(np.arange(80),3),
                      y_choice=np.tile([1,0,0],80))
        if i == 19: ns["zip_results"] = zip_result
        if i == 22: ns["results"] = ordinal
        run(code, ns, f"discrete:{i}")
        if i == 18: zip_result = ns["zip_results"]
        if i == 21: ordinal = ns["results"]
    assert np.all(np.diff(ns["cutpoints"]) > 0)
    assert np.all(ns["zero_probs"] >= ns["inflation_probs"])
    mu = zip_result.predict(base["X"], exog_infl=ns["X_inflation"], which="mean-main")
    pi = ns["inflation_probs"]
    assert np.allclose(ns["zero_probs"], pi + (1-pi) * np.exp(-mu))
    assert ns["params_df"].shape == (4, 4)
    assert ns["predicted_mode"].shape == (1,)
    p = base["logit"].predict(base["X"])
    expected = np.mean(p * (1-p)) * np.asarray(base["logit"].params)[1:]
    assert np.allclose(ns["marginal_effects"].margeff, expected)
    assert np.isclose(ns["expected"].sum(), np.asarray(ns["pmf"]).sum())


def test_diagnostics_reference(data):
    ns, base = data
    for i, code in enumerate(blocks("stats_diagnostics.md"), 1):
        ns.update(results=base["ols"], y=base["y"], X=base["X"], exog=base["X"])
        if i == 48:
            ns["anova_table"] = sm.stats.anova_lm(smf.ols("response ~ C(factor1)", data=base["df"]).fit())
        run(code, ns, f"diagnostics:{i}")
    assert 0 <= ns["eta_sq"] <= 1
    assert np.isclose(ns["f_pval"], ns["reset_test"].pvalue)
    assert np.isfinite(ns["games_howell"].pvalues).all()
    assert np.allclose(ns["res"].effect[0], ns["res"].effect[2] - ns["res"].effect[1])


def test_model_selection_reference(data):
    ns, _ = data
    for i, code in enumerate(blocks("model_selection.md"), 1):
        run(code, ns, f"model-selection:{i}")
    assert len(ns["cv_scores"]) == 5
    assert 0 <= ns["p_value"] <= 1


def test_time_series_reference(data):
    ns, base = data
    rng = ns["rng"]
    n = 120
    noise = rng.normal(size=(n, 3))
    series = np.zeros((n, 3))
    for t in range(1, n): series[t] = 0.55 * series[t-1] + noise[t]
    index = pd.date_range("2000-01-01", periods=n, freq="MS")
    frame = pd.DataFrame(series, index=index, columns=["series1", "series2", "series3"])
    y = frame.series1
    exog = pd.DataFrame(rng.normal(size=(n, 1)), index=index, columns=["external"])
    ns.update(y=y, y1=frame.series1, y2=frame.series2, y3=frame.series3, df_multivariate=frame,
              X_exog=exog, X=exog, X_future=exog.iloc[:10], d=0, h=10, split_point=100,
              y_stationary=y, monthly_sales=y + 10,
              hourly_series=pd.Series(rng.normal(size=24*7*3)), ARIMA=ARIMA)
    arima = ARIMA(y, order=(1,1,1)).fit()
    var_result = None
    for i, code in enumerate(blocks("time_series.md"), 1):
        ns["y"] = y
        if i in (16, 17): ns["results"] = var_result
        if i in (23, 25, 26, 28): ns["results"] = arima
        if i == 33:
            common = np.cumsum(rng.normal(size=n))
            ns["df_multivariate"] = pd.DataFrame({
                "a": common + rng.normal(scale=.2, size=n),
                "b": common + rng.normal(scale=.2, size=n),
            }, index=index)
        run(code, ns, f"time-series:{i}")
        if i == 7:
            assert ns["results"].mle_retvals["converged"]
            assert ns["results"] is ns["best_result"]
            assert ns["results"].aic == ns["best_aic"]
        if i == 14: var_result = ns["results"]
    assert np.isfinite(ns["forecasts"]).all()
    assert len(ns["forecasts"]) == 24
    assert ns["forecast_df"].shape == (10,4)
    assert np.isfinite(ns["lb_test"].lb_pvalue).all()
    assert np.allclose(np.asarray(ns["regime_probs"]).sum(axis=1), 1)


def test_treatment_known_bug_and_point_route(data):
    """A regression guard for the documented released-code limitation, not a patch."""
    from statsmodels.treatment.treatment_effects import TreatmentEffect
    ns, base = data
    select = sm.Probit(ns["treatment"], base["X"]).fit(disp=0)
    te = TreatmentEffect(sm.OLS(ns["outcome"], base["X"]), ns["treatment"], results_select=select)
    for name in ("aipw_wls", "ipw_ra"):
        method = getattr(te, name)
        estimate = method(return_results=False)
        assert np.isfinite(estimate).all()
        assert np.isclose(estimate[0], estimate[2] - estimate[1])
        with pytest.raises(ValueError, match="shapes|aligned|matmul|mismatch"):
            method()
