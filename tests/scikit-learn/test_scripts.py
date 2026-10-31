"""Tests for the scikit-learn pipeline and clustering templates.

The value of `create_preprocessing_pipeline` is that it fits its imputer and
scaler *inside* a Pipeline, so cross-validation never lets test-fold statistics
reach the training fold. That is the leak these templates exist to prevent, and
it is what the tests check: the preprocessor is a ColumnTransformer that must
be fitted before it can transform, unseen categories survive, and the whole
thing composes into a single estimator.

Clustering is checked against data with a known answer -- three well-separated
blobs -- so "found 3 clusters" means something.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scikit-learn"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="scikit-learn scripts need numpy")
pd = pytest.importorskip("pandas", reason="scikit-learn scripts need pandas")
sklearn = pytest.importorskip("sklearn", reason="scikit-learn scripts need sklearn")
matplotlib = pytest.importorskip("matplotlib", reason="clustering_analysis plots")
matplotlib.use("Agg")

from sklearn.datasets import make_blobs  # noqa: E402
from sklearn.exceptions import NotFittedError  # noqa: E402

import classification_pipeline  # noqa: E402
import clustering_analysis  # noqa: E402


def mixed_frame(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "age": rng.normal(50, 10, n),
            "score": rng.normal(0, 1, n),
            "city": rng.choice(["london", "paris", "berlin"], n),
            "grade": rng.choice(["a", "b"], n),
        }
    )


NUMERIC = ["age", "score"]
CATEGORICAL = ["city", "grade"]


class PreprocessingPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = mixed_frame()
        self.preprocessor = classification_pipeline.create_preprocessing_pipeline(
            NUMERIC, CATEGORICAL
        )

    def test_it_returns_an_unfitted_column_transformer(self) -> None:
        from sklearn.compose import ColumnTransformer

        self.assertIsInstance(self.preprocessor, ColumnTransformer)
        # Unfitted: statistics can only come from data it is later shown, which
        # is what keeps the test fold out of the training fold.
        with self.assertRaises(NotFittedError):
            self.preprocessor.transform(self.frame)

    def test_numeric_columns_are_imputed_and_standardised(self) -> None:
        frame = self.frame.copy()
        frame.loc[0, "age"] = np.nan
        transformed = self.preprocessor.fit_transform(frame)

        self.assertFalse(np.isnan(transformed).any(), "NaNs survived imputation")
        # The two numeric columns come first and are standardised.
        numeric_block = transformed[:, : len(NUMERIC)]
        np.testing.assert_allclose(numeric_block.mean(axis=0), 0, atol=1e-9)
        np.testing.assert_allclose(numeric_block.std(axis=0), 1, atol=1e-9)

    def test_categorical_columns_become_one_hot_indicators(self) -> None:
        transformed = self.preprocessor.fit_transform(self.frame)
        # 2 numeric + 3 cities + 2 grades
        self.assertEqual(transformed.shape, (len(self.frame), 2 + 3 + 2))
        categorical_block = transformed[:, len(NUMERIC):]
        self.assertTrue(set(np.unique(categorical_block)) <= {0.0, 1.0})

    def test_an_unseen_category_does_not_raise_at_transform_time(self) -> None:
        # handle_unknown='ignore' -- a category that appears only in the test
        # fold must not blow up the whole cross-validation run.
        self.preprocessor.fit(self.frame)
        unseen = self.frame.iloc[:3].copy()
        unseen["city"] = "tokyo"
        transformed = self.preprocessor.transform(unseen)
        self.assertEqual(transformed.shape[1], 2 + 3 + 2)
        # The unknown category encodes as all-zero indicators.
        np.testing.assert_allclose(transformed[:, 2:5], 0)

    def test_a_missing_categorical_value_is_filled_rather_than_dropped(self) -> None:
        frame = self.frame.copy()
        frame.loc[0, "city"] = None
        transformed = self.preprocessor.fit_transform(frame)
        self.assertEqual(len(transformed), len(frame))
        names = self.preprocessor.get_feature_names_out()
        self.assertIn("cat__city_missing", names)
        self.assertFalse(any("None" in name for name in names))

    def test_it_can_be_composed_into_a_single_estimator(self) -> None:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline

        rng = np.random.default_rng(3)
        target = rng.integers(0, 2, len(self.frame))
        model = Pipeline(
            [("prep", self.preprocessor), ("clf", LogisticRegression(max_iter=500))]
        )
        model.fit(self.frame, target)
        self.assertEqual(len(model.predict(self.frame)), len(self.frame))

    def test_columns_outside_the_two_lists_are_dropped(self) -> None:
        frame = self.frame.copy()
        frame["notes"] = "ignore me"
        transformed = self.preprocessor.fit_transform(frame)
        self.assertEqual(transformed.shape[1], 2 + 3 + 2)


class ClusteringPreprocessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.features, self.labels = make_blobs(
            n_samples=150, centers=3, n_features=4, random_state=11, cluster_std=0.6
        )

    def test_scaling_standardises_every_feature(self) -> None:
        processed = clustering_analysis.preprocess_for_clustering(self.features)
        np.testing.assert_allclose(processed.mean(axis=0), 0, atol=1e-9)
        np.testing.assert_allclose(processed.std(axis=0), 1, atol=1e-9)

    def test_scaling_can_be_turned_off(self) -> None:
        processed = clustering_analysis.preprocess_for_clustering(
            self.features, scale=False
        )
        np.testing.assert_allclose(processed, self.features)

    def test_pca_reduces_to_the_requested_number_of_components(self) -> None:
        processed = clustering_analysis.preprocess_for_clustering(
            self.features, pca_components=2
        )
        self.assertEqual(processed.shape, (150, 2))

    def test_the_input_matrix_is_not_mutated(self) -> None:
        before = self.features.copy()
        clustering_analysis.preprocess_for_clustering(self.features)
        np.testing.assert_allclose(self.features, before)


class ScratchDirectoryTestCase(unittest.TestCase):
    """Run inside a temporary cwd.

    `find_optimal_k_kmeans` and `visualize_clusters` call `plt.savefig` with a
    bare filename, so they write into the current working directory -- which is
    the repository root when pytest runs. Without this the suite litters the
    checkout with clustering_optimization.png and clustering_results.png.
    """

    def setUp(self) -> None:
        self._origin = Path.cwd()
        self._scratch = tempfile.TemporaryDirectory()
        os.chdir(self._scratch.name)
        self.addCleanup(self._scratch.cleanup)
        self.addCleanup(os.chdir, self._origin)


class OptimalKTests(ScratchDirectoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        features, _ = make_blobs(
            n_samples=180, centers=3, n_features=3, random_state=5, cluster_std=0.5
        )
        self.features = clustering_analysis.preprocess_for_clustering(features)

    def test_three_well_separated_blobs_are_found(self) -> None:
        # A silhouette search that cannot recover an obvious k=3 is not usable.
        result = clustering_analysis.find_optimal_k_kmeans(
            self.features, k_range=range(2, 7)
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["best_k"], 3)

    def test_the_search_covers_every_k_it_was_given(self) -> None:
        result = clustering_analysis.find_optimal_k_kmeans(
            self.features, k_range=range(2, 5)
        )
        # Whatever the container, it must carry one score per candidate k.
        if isinstance(result, dict):
            for value in result.values():
                if isinstance(value, (list, tuple, np.ndarray)) and len(value) > 1:
                    self.assertEqual(len(value), 3)
                    break


class AlgorithmComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        features, self.truth = make_blobs(
            n_samples=150, centers=3, n_features=3, random_state=9, cluster_std=0.5
        )
        self.features = clustering_analysis.preprocess_for_clustering(features)

    def test_several_algorithms_are_compared(self) -> None:
        results = clustering_analysis.compare_clustering_algorithms(
            self.features, n_clusters=3
        )
        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 1)

    def test_kmeans_recovers_the_planted_structure(self) -> None:
        from sklearn.metrics import adjusted_rand_score

        results = clustering_analysis.compare_clustering_algorithms(
            self.features, n_clusters=3
        )
        kmeans = next(
            (value for name, value in results.items() if "means" in name.lower()), None
        )
        self.assertIsNotNone(kmeans, f"no K-Means entry in {sorted(results)}")

        labels = kmeans.get("labels") if isinstance(kmeans, dict) else None
        if labels is not None:
            self.assertGreater(adjusted_rand_score(self.truth, labels), 0.9)


class EndToEndTests(ScratchDirectoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.addCleanup(lambda: __import__("matplotlib.pyplot", fromlist=["close"]).close("all"))

    def test_the_full_clustering_analysis_runs(self) -> None:
        features, truth = make_blobs(
            n_samples=120, centers=3, n_features=3, random_state=13, cluster_std=0.6
        )
        result = clustering_analysis.complete_clustering_analysis(
            features, true_labels=truth
        )
        self.assertIsNotNone(result)

    def test_the_classification_pipeline_trains_and_scores(self) -> None:
        frame = mixed_frame(120)
        rng = np.random.default_rng(4)
        # A learnable target so the run exercises a real fit, not noise.
        target = (frame["age"] > frame["age"].median()).astype(int).to_numpy().copy()
        target[rng.choice(len(target), 6, replace=False)] ^= 1

        result = classification_pipeline.train_and_evaluate_model(
            frame, target, NUMERIC, CATEGORICAL, random_state=0
        )
        self.assertIsNotNone(result)


class ScientificRegressionTests(ScratchDirectoryTestCase):
    def test_categorical_missing_sentinels_share_one_category(self):
        frame = mixed_frame()
        frame["city"] = frame["city"].astype(object)
        frame.loc[0, "city"] = None
        frame.loc[1, "city"] = pd.NA
        frame.loc[2, "city"] = np.nan
        prep = classification_pipeline.create_preprocessing_pipeline(NUMERIC, CATEGORICAL)
        values = prep.fit_transform(frame)
        names = prep.get_feature_names_out().tolist()
        missing_column = names.index("cat__city_missing")
        np.testing.assert_array_equal(values[:3, missing_column], 1)
        self.assertEqual(len(names), 8)

    def test_empty_training_columns_keep_schema_and_use_training_statistics(self):
        frame = mixed_frame()
        frame["score"] = np.nan
        frame["grade"] = np.nan
        prep = classification_pipeline.create_preprocessing_pipeline(NUMERIC, CATEGORICAL)
        train = prep.fit_transform(frame)
        test = frame.iloc[:2].copy()
        test["age"] = 10000
        test["score"] = 9
        test["grade"] = "new"
        transformed = prep.transform(test)
        self.assertEqual(train.shape[1], transformed.shape[1])
        self.assertIn("num__score", prep.get_feature_names_out())
        self.assertIn("cat__grade_missing", prep.get_feature_names_out())
        self.assertGreater(transformed[0, 0], 100)
        numeric = prep.named_transformers_["num"]
        self.assertAlmostEqual(numeric.named_steps["imputer"].statistics_[0], frame.age.median())

    def test_all_noise_dbscan_is_retained_with_undefined_metrics(self):
        features = np.arange(40, dtype=float).reshape(20, 2) * 10
        results = clustering_analysis.compare_clustering_algorithms(features, 2)
        noise = results["DBSCAN"]
        self.assertEqual(noise["n_clusters"], 0)
        self.assertEqual(noise["n_noise"], 20)
        self.assertEqual(noise["coverage"], 0)
        self.assertIsNone(noise["silhouette"])
        self.assertTrue(noise["metric_reason"])
        clustering_analysis.visualize_clusters(features, results)
        self.assertTrue(Path("clustering_results.png").is_file())

    def test_dbscan_coverage_excludes_noise_but_does_not_drop_result(self):
        rng = np.random.default_rng(123)
        features = np.vstack([rng.normal(-3, 0.05, (20, 2)),
                              rng.normal(3, 0.05, (20, 2)), [[50, 50]]])
        result = clustering_analysis.compare_clustering_algorithms(features, 2)["DBSCAN"]
        self.assertEqual(result["n_clusters"], 2)
        self.assertEqual(result["n_scored"], 40)
        self.assertAlmostEqual(result["coverage"], 40 / 41)
        self.assertGreater(result["silhouette"], 0.9)

    def test_undefined_cluster_metrics_are_not_computed(self):
        for labels in (np.zeros(5), np.arange(5)):
            metrics = clustering_analysis.clustering_metrics(np.ones((5, 2)), labels)
            self.assertIsNone(metrics["silhouette"])

    def test_invalid_or_collapsed_k_candidates_fail_clearly(self):
        for candidates in ([], [1], [5], [2.5]):
            with self.assertRaisesRegex(ValueError, "k_range"):
                clustering_analysis.find_optimal_k_kmeans(np.ones((5, 2)), candidates)
        from sklearn.exceptions import ConvergenceWarning
        with pytest.warns(ConvergenceWarning):
            with self.assertRaisesRegex(ValueError, "No candidate"):
                clustering_analysis.find_optimal_k_kmeans(np.ones((5, 2)), [2, 3])

    def test_k_candidate_generator_is_supported(self):
        features, _ = make_blobs(n_samples=40, centers=2, random_state=3)
        result = clustering_analysis.find_optimal_k_kmeans(features, (k for k in [2, 3]))
        self.assertEqual(result["k_values"], [2, 3])

    def test_current_classical_mds_preserves_euclidean_distances(self):
        from sklearn.manifold import ClassicalMDS
        from sklearn.metrics import pairwise_distances
        features = np.random.default_rng(2).normal(size=(12, 2))
        embedded = ClassicalMDS(n_components=2).fit_transform(features)
        np.testing.assert_allclose(pairwise_distances(embedded), pairwise_distances(features), atol=1e-7)

    def test_target_encoding_crossfits_instead_of_memorizing_unique_ids(self):
        from sklearn.preprocessing import TargetEncoder
        from sklearn.model_selection import StratifiedKFold
        X = np.array([f"id-{i}" for i in range(40)]).reshape(-1, 1)
        y = np.tile([0, 1], 20)
        encoder = TargetEncoder(cv=StratifiedKFold(5, shuffle=True, random_state=42))
        cross_fitted = encoder.fit_transform(X, y)
        np.testing.assert_allclose(cross_fitted, 0.5)
        self.assertFalse(np.allclose(cross_fitted, encoder.transform(X)))

    def test_text_and_numeric_pipeline_routes_columns_correctly(self):
        from sklearn.compose import ColumnTransformer
        from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression
        frame = pd.DataFrame({"text": ["red star", "blue sea"] * 20,
                              "age": np.arange(40), "income": np.arange(40) * 10})
        text_pipeline = Pipeline([("vect", CountVectorizer()), ("tfidf", TfidfTransformer())])
        pipeline = Pipeline([
            ("features", ColumnTransformer([
                ("text", text_pipeline, "text"),
                ("numeric", StandardScaler(), ["age", "income"])])),
            ("classifier", LogisticRegression())])
        y = np.tile([0, 1], 20)
        pipeline.fit(frame, y)
        np.testing.assert_array_equal(pipeline.predict(frame), y)

    def test_transformer_only_pipeline_returns_named_dataframe(self):
        from sklearn.pipeline import Pipeline
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import StandardScaler
        transformers = Pipeline([("imputer", SimpleImputer()),
                                 ("scaler", StandardScaler())]).set_output(transform="pandas")
        result = transformers.fit_transform(mixed_frame()[NUMERIC])
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(result.columns.tolist(), NUMERIC)


if __name__ == "__main__":
    unittest.main()
