"""Native regression checks for the skill's release-specific UMAP contracts.

Small synthetic inputs exercise geometry/API semantics, not visual island shape
or claims about biological clusters. Run this suite in its isolated environment.
"""
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "umap-learn"
np = pytest.importorskip("numpy")
umap = pytest.importorskip("umap")

from scipy import sparse
from sklearn.datasets import make_blobs
from sklearn.manifold import trustworthiness
from sklearn.metrics import adjusted_rand_score, pairwise_distances
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.utils import check_random_state
from umap.umap_ import (
    find_ab_params, fuzzy_simplicial_set, nearest_neighbors, simplicial_set_embedding,
)
from numba import njit


@pytest.fixture(scope="module")
def samples():
    X, y = make_blobs(n_samples=120, n_features=12, centers=3,
                      cluster_std=0.5, random_state=17)
    return StandardScaler().fit_transform(X).astype(np.float32), y


def reducer(**kwargs):
    return umap.UMAP(**{"n_neighbors": 10, "n_epochs": 50,
                       "random_state": 42, "n_jobs": 1, **kwargs})


def test_seeded_fit_transform_keeps_training_coordinates(samples):
    X, _ = samples
    model = reducer().fit(X[:90])
    original = model.embedding_.copy()
    predicted = model.transform(X[90:])
    assert predicted.shape == (30, 2)
    assert np.isfinite(predicted).all()
    np.testing.assert_array_equal(model.embedding_, original)
    np.testing.assert_array_equal(reducer().fit_transform(X[:90]), original)
    assert trustworthiness(X[:90], original, n_neighbors=5) > 0.85
    assert model.get_feature_names_out().tolist() == ["umap0", "umap1"]


def test_pipeline_is_supervised_even_at_zero_categorical_target_weight():
    X = np.random.default_rng(17).normal(size=(60, 5)).astype(np.float32)
    y = np.arange(60) % 3
    model = Pipeline([("scale", StandardScaler()),
                      ("umap", reducer(target_weight=0.0)), ("svc", SVC())])
    model.fit(X, y)
    scaled = model.named_steps["scale"].transform(X)
    plain = reducer(target_weight=0.0).fit(scaled)
    supervised = model.named_steps["umap"]
    assert (plain.graph_ != supervised.graph_).nnz > 0
    assert model.predict(X[:4]).shape == (4,)
    with pytest.raises(ValueError, match="supervised"):
        supervised.update(scaled[:4])


def test_semisupervised_unknowns_and_regression_metric(samples):
    X, y = samples
    semi = y.copy()
    semi[::3] = -1
    for targets, metric in ((semi, "categorical"), (X[:, 0], "l2")):
        result = reducer(target_metric=metric).fit_transform(X, y=targets)
        assert result.shape == (len(X), 2)
        assert np.isfinite(result).all()


def test_density_outputs_and_unsupported_new_transform(samples):
    X, _ = samples
    model = reducer(densmap=True, output_dens=True)
    embedding, original_radii, embedded_radii = model.fit_transform(X[:90])
    assert embedding.shape == (90, 2)
    assert original_radii.shape == embedded_radii.shape == (90,)
    assert np.isfinite(original_radii).all() and np.isfinite(embedded_radii).all()
    np.testing.assert_array_equal(original_radii, model.rad_orig_)
    with pytest.raises(NotImplementedError, match="densMAP"):
        model.transform(X[90:])
    with pytest.raises(ValueError, match="densMAP"):
        model.inverse_transform(embedding[:2])


def test_graph_mode_returns_training_and_bipartite_graphs(samples):
    X, _ = samples
    model = reducer(transform_mode="graph")
    graph = model.fit_transform(X[:90])
    new_graph = model.transform(X[90:])
    assert sparse.issparse(graph) and graph.shape == (90, 90)
    assert sparse.issparse(new_graph) and new_graph.shape == (30, 90)
    assert np.isfinite(new_graph.data).all()
    assert not hasattr(model, "embedding_")


def test_precomputed_distance_transform_uses_training_columns(samples):
    X, _ = samples
    train = pairwise_distances(X[:90])
    cross = pairwise_distances(X[90:], X[:90])
    model = reducer(metric="precomputed").fit(train)
    transformed = model.transform(cross)
    assert transformed.shape == (30, 2) and np.isfinite(transformed).all()
    with pytest.raises(AssertionError):
        model.transform(pairwise_distances(X[90:]))
    with pytest.raises(ValueError, match="precomputed"):
        model.update(cross)


def test_neighbor_reuse_requires_search_index_for_transform(samples):
    X, _ = samples
    neighbors = nearest_neighbors(X[:90], 10, "euclidean", {}, False,
                                  check_random_state(42), n_jobs=1)
    model = reducer(precomputed_knn=neighbors).fit(X[:90])
    assert np.isfinite(model.transform(X[90:])).all()
    without_index = reducer(precomputed_knn=neighbors[:2]).fit(X[:90])
    with pytest.raises(NotImplementedError, match="No search index"):
        without_index.transform(X[90:])


def test_low_level_helpers_return_tuples(samples):
    X, _ = samples
    distances = pairwise_distances(X[:40])
    idx, dists, search = nearest_neighbors(distances, 10, "precomputed", {},
                                          False, check_random_state(42), n_jobs=1)
    assert search is None
    graph, sigmas, rhos = fuzzy_simplicial_set(
        X[:40], 10, check_random_state(42), "euclidean",
        knn_indices=idx, knn_dists=dists)
    assert graph.shape == (40, 40) and sigmas.shape == rhos.shape == (40,)
    extended = fuzzy_simplicial_set(X[:40], 10, check_random_state(42), "euclidean",
                                   knn_indices=idx, knn_dists=dists, return_dists=False)
    assert len(extended) == 4 and extended[-1] is None
    a, b = find_ab_params(1.0, 0.1)
    embedding, aux = simplicial_set_embedding(
        X[:40], graph, 2, 1.0, a, b, 1.0, 5, 30, "random",
        check_random_state(42), "euclidean", {}, False, {}, False)
    assert embedding.shape == (40, 2) and np.isfinite(embedding).all()
    assert isinstance(aux, dict)


def test_update_mutates_and_returns_none(samples):
    X, _ = samples
    model = reducer().fit(X[:90])
    assert model.update(X[90:]) is None
    assert model.embedding_.shape == (120, 2)
    assert np.isfinite(model.embedding_).all()


def test_inverse_restores_feature_shape_and_sparse_is_unsupported(samples):
    X, _ = samples
    model = reducer().fit(X)
    reconstructed = model.inverse_transform(model.embedding_[:3])
    assert reconstructed.shape == (3, 12) and np.isfinite(reconstructed).all()
    sparse_model = reducer().fit(sparse.csr_matrix(X))
    with pytest.raises(ValueError, match="sparse"):
        sparse_model.inverse_transform(sparse_model.embedding_[:3])


@njit()
def manhattan_custom(x, y):
    result = 0.0
    for i in range(x.shape[0]):
        result += abs(x[i] - y[i])
    return result


def test_custom_metric_and_alternative_initialization(samples):
    X, _ = samples
    result = reducer(metric=manhattan_custom, init="pca").fit_transform(X)
    assert result.shape == (120, 2) and np.isfinite(result).all()
    result = reducer(init="tswspectral").fit_transform(X)
    assert np.isfinite(result).all()


def test_hdbscan_recipe_has_known_synthetic_answer(samples):
    hdbscan = pytest.importorskip("hdbscan")
    X, y = samples
    embedding = reducer(n_neighbors=30, n_components=10, min_dist=0.0).fit_transform(X)
    labels = hdbscan.HDBSCAN(min_cluster_size=15, min_samples=5).fit_predict(embedding)
    assert adjusted_rand_score(y, labels) > 0.9
    assert set(labels) == {0, 1, 2}


def test_aligned_update_relates_previous_rows_to_new_rows(samples):
    X, _ = samples
    base = X[:40]
    permutation = np.roll(np.arange(40), 7)
    second = base[permutation] + 0.01
    relation = {int(old): int(new) for new, old in enumerate(permutation)}
    model = umap.AlignedUMAP(n_neighbors=10, n_epochs=30,
                            random_state=42, alignment_window_size=1)
    fitted = model.fit([base, second], relations=[relation])
    assert fitted is model
    assert len(model.embeddings_) == 2
    # Second-slice row i represents original row permutation[i].
    back_to_original_order = {int(i): int(original) for i, original in enumerate(permutation)}
    assert model.update(base + 0.02, relations=back_to_original_order) is None
    assert model.dict_relations_[-1] == back_to_original_order
    assert len(model.embeddings_) == 3
    assert all(e.shape == (40, 2) and np.isfinite(e).all() for e in model.embeddings_)
