"""Small, offline behavioral checks for the aeon skill's documented workflows."""
from pathlib import Path

import pytest

pytest.importorskip("aeon")
import numpy as np

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "aeon"


def test_rocket_classification_regression_and_preprocessing():
    from aeon.classification.convolution_based import RocketClassifier
    from aeon.regression.convolution_based import RocketRegressor
    from aeon.transformations.collection import MinMaxScaler, Normalizer, SimpleImputer
    from aeon.transformations.collection.compose import CollectionTransformerPipeline
    from aeon.transformations.collection.convolution_based import Rocket
    from aeon.transformations.collection.feature_based import Catch22
    from aeon.transformations.series.smoothing import MovingAverage
    from sklearn.pipeline import Pipeline

    rng = np.random.default_rng(42)
    X = rng.normal(size=(16, 1, 32))
    y = np.tile([0, 1], 8)
    model = Pipeline([("normalize", Normalizer()),
                      ("classify", RocketClassifier(n_kernels=20, random_state=42))])
    model.fit(X, y)
    assert model.predict(X[:3]).shape == (3,)
    reg = RocketRegressor(n_kernels=20, random_state=42).fit(X, X.mean(axis=(1, 2)))
    assert np.isfinite(reg.predict(X[:3])).all()
    features = Rocket(n_kernels=20, random_state=42).fit_transform(X)
    assert features.shape == (16, 40)
    assert Catch22(replace_nans=True).fit_transform(X).shape == (16, 22)
    X[0, 0, 1] = np.nan
    pre = CollectionTransformerPipeline([
        ("imputer", SimpleImputer(strategy="mean")), ("scaler", MinMaxScaler())
    ])
    scaled = pre.fit_transform(X)
    assert np.isfinite(scaled).all()
    assert np.min(scaled) >= 0 and np.max(scaled) <= 1
    smooth = MovingAverage(window_size=3).fit_transform(np.arange(6.0))
    np.testing.assert_allclose(smooth, [[1, 2, 3, 4]])


def test_distance_cost_path_and_precomputed_orientation():
    from aeon.distances import (dtw_distance, dtw_alignment_path, dtw_cost_matrix,
                                dtw_pairwise_distance, erp_distance, twe_distance,
                                lcss_distance, get_distance_function)
    from aeon.transformations.collection import Normalizer
    from sklearn.neighbors import KNeighborsClassifier

    x = np.array([0., 1., 2., 1., 0.])
    y = np.array([0., 0., 1., 2., 0.])
    path, cost = dtw_alignment_path(x, y)
    assert path[0] == (0, 0) and path[-1] == (4, 4)
    assert cost == dtw_distance(x, y) == dtw_cost_matrix(x, y)[-1, -1]
    # DTW returns squared local costs, not the Euclidean norm.
    assert dtw_distance(np.array([0., 0.]), np.array([2., 2.])) == 8.0
    assert np.isfinite(dtw_distance(x, y, itakura_max_slope=0.5))
    xy = Normalizer().fit_transform(np.stack([x, y])[:, None, :])
    assert np.isfinite(dtw_distance(xy[0], xy[1]))
    for f, kwargs in [(erp_distance, {"g": .5}), (twe_distance, {"nu": .001, "lmbda": 1.}),
                      (lcss_distance, {"epsilon": .5}), (get_distance_function("dtw"), {"window": .1})]:
        assert np.isfinite(f(x, y, **kwargs))
    X = np.stack([x, y, x + 5, y + 5])[:, None, :]
    model = KNeighborsClassifier(n_neighbors=1, metric="precomputed").fit(
        dtw_pairwise_distance(X), [0, 0, 1, 1])
    D_test = dtw_pairwise_distance(X[[0, 2]], X)
    assert D_test.shape == (2, 4)
    np.testing.assert_array_equal(model.predict(D_test), [0, 1])


def test_scalar_and_recursive_forecasts_with_future_covariates():
    from aeon.forecasting import NaiveForecaster, RegressionForecaster
    from aeon.forecasting.stats import ARIMA, AutoETS

    y = np.arange(1., 31.)
    assert NaiveForecaster(strategy="drift", horizon=3).fit(y).predict(y) == 33.
    np.testing.assert_array_equal(
        NaiveForecaster(strategy="last").iterative_forecast(y, 3), [30., 30., 30.])
    for model in [ARIMA(p=1, d=1, q=1), AutoETS()]:
        result = model.iterative_forecast(y, 3)
        assert result.shape == (3,) and np.isfinite(result).all()
    assert RegressionForecaster(window=5).direct_forecast(y, 3).shape == (3,)
    exog = np.arange(30.)[:, None]
    observed = 2. + 3. * exog[:, 0]
    future = np.arange(30., 33.)[:, None]
    arima = ARIMA(p=0, d=0, q=0).fit(observed, exog=exog)
    assert arima.predict(observed, exog=future[:1]) == pytest.approx(92.)
    np.testing.assert_allclose(arima.iterative_forecast(
        observed, 3, exog=exog, future_exog=future), [92, 95, 98])


def test_mass_self_exclusion_and_ann_score_semantics():
    from aeon.similarity_search.subsequence import MASS
    from aeon.similarity_search.whole_series import SimHashIndexANN

    rng = np.random.default_rng(42)
    X = rng.normal(size=(4, 1, 80))
    query = X[0, :, 10:30].copy()
    searcher = MASS(length=20, normalize=True).fit(X)
    profile = searcher.compute_distance_profile(query)
    assert profile.shape == (4, 61)
    assert profile[0, 10] == pytest.approx(0., abs=1e-6)
    indices, distances = searcher.predict(query, k=3, X_index=(0, 10))
    assert indices.shape == (3, 2) and distances.shape == (3,)
    assert not any(case == 0 and abs(start - 10) <= 10 for case, start in indices)
    ann = SimHashIndexANN(n_tables=20, n_bits_per_table=4, random_state=42).fit(X)
    indices, scores = ann.predict(X[0], k=3)
    assert len(indices) == len(scores) and 0 in indices
    # The identical query collides in all 20 tables; its score is not zero.
    assert scores[np.flatnonzero(indices == 0)[0]] == pytest.approx(1 / 20)


def test_matrix_profile_motif_and_timepoint_anomaly_scores():
    pytest.importorskip("stumpy")
    from aeon.transformations.series import MatrixProfileTransformer
    from aeon.anomaly_detection.series.distance_based import STOMP
    from aeon.similarity_search.subsequence import MASS

    y = np.random.default_rng(42).normal(size=160)
    y[100:120] = y[20:40]
    profile = MatrixProfileTransformer(window_length=20).fit_transform(y)
    assert profile.shape == (141,)
    assert profile[20] == pytest.approx(0., abs=1e-6)
    start = int(np.argmin(profile))
    partners, distances = MASS(length=20, normalize=True).fit(y[None, None, :]).predict(
        y[None, start:start+20], k=1, X_index=(0, start), exclusion_factor=.5)
    assert len(partners) == 1 and distances[0] == pytest.approx(0., abs=1e-6)
    scores = STOMP(window_size=20).fit_predict(y)
    assert scores.shape == y.shape and np.isfinite(scores).all()


def test_segmentation_boundaries_versus_dense_states():
    from aeon.segmentation import ClaSPSegmenter, InformationGainSegmenter, HMMSegmenter
    from scipy.stats import norm

    y = np.concatenate([np.sin(np.linspace(0, 10, 100)), np.cos(np.linspace(0, 10, 100)),
                        np.sin(2*np.linspace(0, 10, 100))])
    cps = ClaSPSegmenter(period_length=20, n_cps=2).fit_predict(y)
    assert len(cps) <= 2 and np.all((cps >= 0) & (cps < len(y)))
    X = np.random.default_rng(42).uniform(.1, 1, (2, 100))
    labels = InformationGainSegmenter(k_max=3).fit_predict(X, axis=1)
    assert labels.shape == (100,)
    assert len(np.flatnonzero(np.diff(labels) != 0) + 1) <= 3
    hmm = HMMSegmenter(
        emission_funcs=[(norm.pdf, {"loc": 0, "scale": .5}),
                        (norm.pdf, {"loc": 5, "scale": .5})],
        transition_prob_mat=np.array([[.95, .05], [.05, .95]]))
    labels = hmm.fit_predict(np.array([.1, -.1, .2, 4.9, 5.1, 5.]))
    np.testing.assert_array_equal(labels, [0, 0, 0, 1, 1, 1])
    np.testing.assert_array_equal(np.flatnonzero(np.diff(labels) != 0) + 1, [3])


def test_clustering_and_matching_accuracy():
    from aeon.clustering import TimeSeriesKMeans
    from aeon.benchmarking.metrics.clustering import clustering_accuracy_score

    X = np.random.default_rng(42).normal(scale=.1, size=(8, 1, 16))
    X[4:] += 5
    for distance, average in [("euclidean", "mean"), ("dtw", "ba")]:
        model = TimeSeriesKMeans(n_clusters=2, n_init=1, max_iter=3,
                                 random_state=42, distance=distance, averaging_method=average)
        labels = model.fit_predict(X)
        assert model.cluster_centers_.shape == (2, 1, 16)
        assert clustering_accuracy_score([0]*4 + [1]*4, labels) == 1.


def test_local_dataset_roundtrip_and_resampling(tmp_path):
    from aeon.datasets import (save_to_ts_file, load_from_ts_file, load_from_tsv_file,
                               load_from_tsf_file, load_from_arff_file,
                               load_from_timeeval_csv_file)
    from aeon.benchmarking.resampling import stratified_resample_data

    X = np.arange(48.).reshape(8, 1, 6)
    y = np.tile([0, 1], 4)
    save_to_ts_file(X, y, label_type="classification", path=str(tmp_path), problem_name="Tiny")
    loaded, labels = load_from_ts_file(str(tmp_path / "Tiny.ts"))
    np.testing.assert_allclose(loaded, X)
    np.testing.assert_array_equal(labels, y.astype(str))
    train_X, train_y, test_X, test_y = stratified_resample_data(X[:4], y[:4], X[4:], y[4:], 42)
    assert train_X.shape == test_X.shape == (4, 1, 6)
    np.testing.assert_array_equal(np.bincount(train_y), [2, 2])
    np.testing.assert_array_equal(np.bincount(test_y), [2, 2])
    tsv = tmp_path / "tiny.tsv"
    tsv.write_text("0\t1\t2\t3\n1\t4\t5\t6\n")
    assert load_from_tsv_file(str(tsv))[0].shape == (2, 1, 3)
    tsf = tmp_path / "tiny.tsf"
    tsf.write_text("@attribute series_name string\n@frequency yearly\n@horizon 1\n@missing false\n@equallength true\n@data\na:1,2,3\n")
    frame, meta = load_from_tsf_file(str(tsf))
    np.testing.assert_array_equal(frame.iloc[0]["series_value"], [1, 2, 3])
    assert meta["forecast_horizon"] == 1
    arff = tmp_path / "tiny.arff"
    arff.write_text("@relation Tiny\n@attribute a numeric\n@attribute b numeric\n@attribute target {A,B}\n@data\n1,2,A\n3,4,B\n")
    assert load_from_arff_file(str(arff))[0].shape == (2, 1, 2)
    csv = tmp_path / "tiny.csv"
    csv.write_text("timestamp,value,is_anomaly\n0,1.0,0\n1,4.0,1\n")
    _, labels = load_from_timeeval_csv_file(csv)
    np.testing.assert_array_equal(labels, [0, 1])


def test_metrics_and_statistical_test_outputs():
    from aeon.benchmarking.metrics.anomaly_detection import (
        range_roc_auc_score)
    from aeon.benchmarking.metrics.segmentation import count_error, hausdorff_error
    from aeon.benchmarking.stats import check_friedman, nemenyi_test, wilcoxon_test
    from scipy.stats import rankdata

    labels = np.array([0, 0, 1, 1, 0, 0, 1, 1, 0, 0])
    assert range_roc_auc_score(labels, labels.astype(float), buffer_size=0) == 1
    assert count_error([3, 6], [3, 5, 8]) == 1
    assert hausdorff_error([3, 6], [3, 5]) == 1
    scores = np.array([[.81,.77,.75],[.72,.75,.68],[.92,.88,.85],
                       [.69,.66,.70],[.83,.81,.79],[.76,.73,.71]])
    ranks = rankdata(-scores, axis=1)
    assert 0 <= check_friedman(ranks.T) <= 1
    cliques = nemenyi_test(np.sort(ranks.mean(axis=0)), len(scores), .05)
    assert len(cliques) > 0
    p_values = wilcoxon_test(scores, ["A", "B", "C"])
    assert p_values.shape == (3, 3)
    assert 0 <= p_values[0, 1] <= 1
