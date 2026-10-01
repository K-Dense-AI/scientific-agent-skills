"""Native small games: output units, aggregation axes, masking and reconstruction."""
from types import SimpleNamespace

import pytest

np = pytest.importorskip("numpy")
shap = pytest.importorskip("shap")
pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


@pytest.fixture
def game():
    rng = np.random.default_rng(7)
    background = rng.normal(size=(12, 3))
    rows = rng.normal(size=(3, 3))
    weights = np.array([0.5, -0.25, 0.125])
    return background, rows, weights


def assert_reconstructs(exp, expected, axis=1, atol=1e-6):
    assert np.isfinite(exp.values).all()
    assert np.isfinite(exp.base_values).all()
    np.testing.assert_allclose(exp.base_values + exp.values.sum(axis=axis), expected, atol=atol)


def test_exact_linear_and_additive_agree_with_analytic_game(game):
    background, rows, weights = game
    model_fn = lambda x: x @ weights + 0.2
    masker = shap.maskers.Independent(background)
    model = LinearRegression().fit(background, model_fn(background))
    for explainer in (
        shap.ExactExplainer(model_fn, masker),
        shap.LinearExplainer(model, masker),
        shap.AdditiveExplainer(model_fn, masker),
    ):
        exp = explainer(rows)
        np.testing.assert_allclose(exp.values, (rows - background.mean(0)) * weights, atol=1e-10)
        assert_reconstructs(exp, model_fn(rows))


def test_correlation_aware_linear_preserves_the_selected_output(game):
    background, rows, weights = game
    model = LinearRegression().fit(background, background @ weights)
    np.random.seed(7)
    exp = shap.LinearExplainer(model, shap.maskers.Impute(background), nsamples=100)(rows)
    assert_reconstructs(exp, model.predict(rows))


def test_permutation_names_outputs_and_requires_a_complete_pass(game):
    background, rows, weights = game
    model_fn = lambda x: np.stack([x @ weights, -x @ weights], axis=1)
    explainer = shap.Explainer(model_fn, background, algorithm="permutation", output_names=["a", "b"], seed=7)
    with pytest.raises(ValueError, match="max_evals"):
        explainer(rows, max_evals=6)
    exp = explainer(rows, max_evals=21, error_bounds=True)
    assert exp.values.shape == (3, 3, 2)
    assert_reconstructs(exp, model_fn(rows))
    exp.output_names = ["a", "b"]  # 0.52 selector does not retain these for permutation.
    np.testing.assert_allclose(exp[..., 1].values, -exp[..., 0].values)


def test_logit_link_reconstructs_log_odds_not_probability(game):
    background, rows, weights = game
    probability = lambda x: 1 / (1 + np.exp(-(x @ weights)))
    exp = shap.Explainer(probability, background, algorithm="permutation", link=shap.links.logit, seed=7)(rows, max_evals=21)
    assert_reconstructs(exp, shap.links.logit(probability(rows)))
    np.testing.assert_allclose(exp.base_values, shap.links.logit(probability(background).mean()))


def test_partition_reconstructs_a_grouped_nonlinear_game(game):
    background, rows, weights = game
    model_fn = lambda x: x @ weights + x[:, 0] * x[:, 1] * x[:, 2]
    masker = shap.maskers.Partition(background, clustering="correlation")
    exp = shap.PartitionExplainer(model_fn, masker)(rows, max_evals=100)
    assert exp.clustering.shape == (3, 2, 4)
    assert_reconstructs(exp, model_fn(rows))


def test_kernel_explicit_budget_and_link(game):
    background, rows, weights = game
    probability = lambda x: 1 / (1 + np.exp(-(x @ weights)))
    explainer = shap.KernelExplainer(probability, background, link="logit")
    values = explainer.shap_values(rows, nsamples=32, l1_reg=0, silent=True)
    np.testing.assert_allclose(explainer.expected_value + values.sum(1), shap.links.logit(probability(rows)), atol=1e-6)
    modern = explainer(rows, l1_reg=0, silent=True)
    assert_reconstructs(modern, shap.links.logit(probability(rows)))


def test_tree_interactions_reconstruct_same_path_dependent_game(game):
    background, rows, weights = game
    model = RandomForestClassifier(n_estimators=8, max_depth=3, random_state=7).fit(background, background @ weights > 0)
    explainer = shap.TreeExplainer(model, model_output="raw", feature_perturbation="tree_path_dependent")
    ordinary = explainer(rows)
    interaction = explainer.shap_interaction_values(rows)
    assert interaction.shape == (3, 3, 3, 2)
    np.testing.assert_allclose(interaction.sum(2), ordinary.values, atol=1e-8)
    np.testing.assert_allclose(interaction, interaction.swapaxes(1, 2), atol=1e-8)
    assert_reconstructs(ordinary, model.predict_proba(rows))


def test_raw_numeric_pipeline_restores_columns_and_loss_uses_fixed_label(game):
    background, rows, weights = game
    frame = pd.DataFrame(background, columns=["a", "b", "c"])
    test = pd.DataFrame(rows, columns=frame.columns)
    pipeline = make_pipeline(ColumnTransformer([("scale", StandardScaler(), frame.columns.tolist())]), LogisticRegression()).fit(frame, background @ weights > 0)
    def probabilities(masked):
        return pipeline.predict_proba(pd.DataFrame(masked, columns=frame.columns))
    probability_exp = shap.PermutationExplainer(probabilities, frame, seed=7)(test, max_evals=21)
    assert_reconstructs(probability_exp, pipeline.predict_proba(test))
    for class_index in range(2):
        def loss(masked):
            return -np.log(probabilities(masked)[:, class_index])
        exp = shap.PermutationExplainer(loss, frame, seed=7)(test, max_evals=21)
        assert_reconstructs(exp, -np.log(pipeline.predict_proba(test)[:, class_index]))
        np.testing.assert_allclose(exp.base_values, loss(frame).mean())


def test_text_partition_shapes_and_output_names():
    model_fn = lambda batch: np.asarray([[s.count("good"), s.count("bad")] for s in batch], dtype=float)
    rows = ["good bad", "good good"]
    exp = shap.Explainer(model_fn, shap.maskers.Text(), algorithm="partition", output_names=["good", "bad"])(rows, max_evals=100)
    assert exp.values.shape == (2, 2, 2)
    assert_reconstructs(exp, model_fn(rows))
    assert exp[..., list(exp.output_names).index("good")].values.shape == (2, 2)


def test_constant_image_masker_needs_no_opencv_and_preserves_output_selection():
    rows = np.arange(8, dtype=float).reshape(2, 2, 2, 1)
    def model_fn(images):
        sums = images.sum(axis=(1, 2, 3))
        return np.stack([sums, 2 * sums], axis=1)
    exp = shap.Explainer(model_fn, shap.maskers.Image(0, (2, 2, 1)), algorithm="partition", output_names=["sum", "double"])(rows, max_evals=100, outputs=[1])
    assert exp.values.shape == (2, 2, 2, 1, 1)
    assert_reconstructs(exp, model_fn(rows)[:, [1]], axis=(1, 2, 3))
    assert exp.output_names == ["double"]


def test_transformers_wrapper_uses_all_scores_and_one_vs_rest_log_odds():
    class PipelineStub:
        model = SimpleNamespace(config=SimpleNamespace(label2id={"a": 0, "b": 1}, id2label={0: "a", 1: "b"}))
        def __call__(self, rows):
            return [[{"label": "a", "score": 0.2}, {"label": "b", "score": 0.8}] for _ in rows]
    wrapped = shap.models.TransformersPipeline(PipelineStub(), rescale_to_logits=True)
    np.testing.assert_allclose(wrapped(["test"]), np.log(np.array([[0.2, 0.8]]) / np.array([[0.8, 0.2]])))
