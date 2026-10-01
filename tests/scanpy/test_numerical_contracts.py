"""Small native numerical and data-integrity checks, not biological validation."""
from pathlib import Path
import sys

import pytest
np = pytest.importorskip("numpy")
sc = pytest.importorskip("scanpy")
import anndata as ad
import pandas as pd
from scipy import sparse

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scanpy"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import _common
import pseudobulk


def counts_fixture(sparse_input=False):
    rng = np.random.default_rng(128)
    counts = rng.poisson(np.linspace(0.5, 8, 80), size=(60, 80)).astype(np.float64)
    counts[:30, :8] += 12
    counts[30:, 8:16] += 12
    a = ad.AnnData(sparse.csr_matrix(counts) if sparse_input else counts)
    a.obs_names = [f"c{i}" for i in range(a.n_obs)]
    a.var_names = [f"g{i}" for i in range(a.n_vars)]
    a.obs["sample"] = pd.Categorical(["s0"] * 15 + ["s1"] * 15 + ["s2"] * 15 + ["s3"] * 15)
    a.obs["condition"] = ["a"] * 30 + ["b"] * 30
    return a


def dense(x):
    return x.toarray() if sparse.issparse(x) else np.asarray(x)


@pytest.mark.parametrize("sparse_input", [False, True])
def test_counts_and_raw_are_independent_and_normalization_is_numerically_correct(sparse_input):
    a = counts_fixture(sparse_input)
    expected = dense(a.X).copy()
    _common.prepare_counts(a)
    _common.normalize_hvg(sc, a, n_top_genes=25)
    normalized = np.log1p(expected / expected.sum(axis=1, keepdims=True) * 1e4)
    np.testing.assert_allclose(dense(a.X), normalized)
    np.testing.assert_array_equal(dense(a.layers["counts"]), expected)
    sc.pp.scale(a)
    np.testing.assert_allclose(dense(a.raw.X), normalized)
    np.testing.assert_array_equal(dense(a.layers["counts"]), expected)
    assert a.raw.n_vars == a.n_vars == 80
    assert np.isfinite(dense(a.X)).all()


@pytest.mark.parametrize("value", [-1, 0.25, np.nan, np.inf])
def test_invalid_counts_fail_closed(value):
    x = np.array([[1., 2.], [3., value]])
    for arr in (x, sparse.csr_matrix(x)):
        with pytest.raises(SystemExit):
            _common.validate_counts(arr)


def test_no_overwrite_of_original_counts_or_double_normalization():
    a = counts_fixture()
    _common.prepare_counts(a)
    original = a.layers["counts"].copy()
    _common.normalize_hvg(sc, a, n_top_genes=25)
    with pytest.raises(SystemExit):
        _common.prepare_counts(a)
    np.testing.assert_array_equal(a.layers["counts"], original)
    _common.prepare_counts(a, "counts")
    np.testing.assert_array_equal(a.X, original)
    assert "log1p" not in a.uns


@pytest.mark.parametrize("flavor", ["seurat_v3", "seurat_v3_paper"])
def test_v3_hvg_uses_counts_with_batches(flavor):
    pytest.importorskip("skmisc")
    a = counts_fixture(True)
    expected = a.copy()
    sc.pp.highly_variable_genes(expected, n_top_genes=25, flavor=flavor, batch_key="sample")
    _common.prepare_counts(a)
    _common.normalize_hvg(sc, a, n_top_genes=25, flavor=flavor, batch_key="sample")
    np.testing.assert_array_equal(a.var["highly_variable"], expected.var["highly_variable"])
    assert np.isfinite(dense(a.raw.X)).all()


def test_pca_uses_selected_genes_and_neighbors_caps_available_components():
    a = counts_fixture(True)
    _common.prepare_counts(a)
    _common.normalize_hvg(sc, a, n_top_genes=8)
    n_selected = a.var.highly_variable.sum()
    n = _common.compute_pca(sc, a, 50)
    assert n == n_selected - 1
    assert a.obsm["X_pca"].shape == (60, n)
    np.testing.assert_array_equal(a.varm["PCs"][~a.var.highly_variable], 0)
    _common.build_neighbors(sc, a, n_pcs=40, n_neighbors=8)
    assert a.uns["neighbors"]["params"]["n_pcs"] == n
    graph = a.obsp["connectivities"]
    assert graph.shape == (60, 60)
    np.testing.assert_allclose(graph.toarray(), graph.T.toarray())
    sc.tl.leiden(a, flavor="igraph", directed=False, n_iterations=2, random_state=0)
    assert isinstance(a.obs.leiden.dtype, pd.CategoricalDtype)
    assert not a.obs.leiden.isna().any()


def test_pseudobulk_exact_sums_collision_free_ids_and_metadata():
    a = ad.AnnData(sparse.csr_matrix([[1, 2], [3, 4], [5, 6], [7, 8]], dtype=np.int64))
    a.obs["sample"] = ["a_b", "a_b", "a", "a"]
    a.obs["cell_type"] = ["c", "c", "b_c", "b_c"]
    a.obs["donor"] = ["001", "001", "002", "002"]
    a.layers["counts"] = a.X.copy()
    a.X = a.X.astype(float) * 0.1  # must not be summed
    counts, meta = pseudobulk.aggregate_counts(a, ["sample", "cell_type"], metadata=["donor"])
    assert counts.columns.is_unique
    assert list(meta.index) == list(counts.columns)
    np.testing.assert_array_equal(counts.to_numpy(), [[4, 12], [6, 14]])
    assert list(meta.donor) == ["001", "002"]
    assert list(meta.n_cells) == [2, 2]
    a.obs.loc[a.obs_names[0], "donor"] = "003"
    with pytest.raises(SystemExit):
        pseudobulk.aggregate_counts(a, ["sample", "cell_type"], metadata=["donor"])


def test_pseudobulk_missing_counts_and_metadata_do_not_fall_back():
    a = counts_fixture()
    with pytest.raises(SystemExit):
        pseudobulk.aggregate_counts(a, ["sample"])
    a.layers["counts"] = a.X.copy()
    a.obs.loc[a.obs_names[0], "sample"] = None
    with pytest.raises(SystemExit):
        pseudobulk.aggregate_counts(a, ["sample"])


def test_marker_cli_uses_full_raw_and_named_reference(tmp_path, monkeypatch):
    import find_markers
    a = counts_fixture()
    _common.prepare_counts(a)
    _common.normalize_hvg(sc, a, n_top_genes=20)
    a = a[:, a.var.highly_variable].copy()
    sc.pp.scale(a)
    source = tmp_path / "in.h5ad"
    output = tmp_path / "out.h5ad"
    a.write_h5ad(source)
    monkeypatch.setattr(sys, "argv", ["find_markers.py", str(source), "-o", str(output),
       "--groupby", "condition", "--groups", "b", "--reference", "a", "--no-plots",
       "--csv-dir", str(tmp_path / "markers"), "--figdir", str(tmp_path / "figures")])
    find_markers.main()
    result = ad.read_h5ad(output)
    rank = result.uns["rank_genes_groups"]
    assert rank["params"]["use_raw"]
    assert rank["params"]["reference"] == "a"
    assert rank["names"].dtype.names == ("b",)
    assert rank["names"].shape == (80,)
    assert np.all((rank["pvals_adj"]["b"] >= 0) & (rank["pvals_adj"]["b"] <= 1))
    assert (tmp_path / "markers" / "markers_condition_b.csv").is_file()
    assert not (tmp_path / "markers" / "markers_condition_a.csv").exists()


def test_qc_with_no_mitochondrial_names(tmp_path, monkeypatch):
    import qc_analysis
    a = counts_fixture()
    source = tmp_path / "in.h5ad"
    a.write_h5ad(source)
    output = tmp_path / "out.h5ad"
    monkeypatch.setattr(sys, "argv", ["qc_analysis.py", str(source), "-o", str(output),
       "--min-genes", "1", "--min-cells", "1", "--no-plots", "--figdir", str(tmp_path / "figs")])
    qc_analysis.main()
    result = ad.read_h5ad(output)
    np.testing.assert_array_equal(result.X, a.X)
    assert "pct_counts_mt" not in result.obs


def test_full_pipeline_retains_full_gene_counts_and_pca_metadata(tmp_path, monkeypatch):
    import run_pipeline
    a = counts_fixture(True)
    source = tmp_path / "counts.h5ad"
    output = tmp_path / "out.h5ad"
    a.write_h5ad(source)
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", str(source), "-o", str(output),
       "--min-genes", "1", "--min-cells", "1", "--n-top-genes", "20", "--n-pcs", "40",
       "--n-neighbors", "8", "--skip-markers", "--figdir", str(tmp_path / "figures")])
    run_pipeline.main()
    result = ad.read_h5ad(output)
    assert result.shape == a.shape
    np.testing.assert_array_equal(dense(result.layers["counts"]), dense(a.X))
    assert result.raw.n_vars == 80
    assert result.varm["PCs"].shape == (80, result.obsm["X_pca"].shape[1])
    assert np.isfinite(result.obsm["X_umap"]).all()
    assert {"neighbors", "pca", "umap", "leiden"} <= set(result.uns)
    assert list((tmp_path / "figures").glob("*.png"))


def test_backed_view_requires_explicit_memory_copy_and_retains_raw_axis(tmp_path):
    a = counts_fixture()
    _common.prepare_counts(a)
    _common.normalize_hvg(sc, a, n_top_genes=20)
    path = tmp_path / "backed.h5ad"
    a.write_h5ad(path)
    backed = ad.read_h5ad(path, backed="r")
    try:
        view = backed[:5, :7]
        assert view.is_view and view.isbacked
        in_memory = view.to_memory()
    finally:
        backed.file.close()
    assert not in_memory.isbacked
    assert in_memory.shape == (5, 7)
    assert in_memory.raw.shape == (5, 80)
    assert in_memory.layers["counts"].shape == (5, 7)


def test_clearing_stale_graph_clears_distances_loadings_and_markers():
    a = counts_fixture()
    a.obsm["X_pca"] = np.zeros((60, 2))
    a.varm["PCs"] = np.zeros((80, 2))
    a.obsp["connectivities"] = sparse.eye(60, format="csr")
    for k in ["pca", "neighbors", "rank_genes_groups", "dendrogram_leiden"]:
        a.uns[k] = {}
    _common.clear_graph(a, clear_pca=True)
    assert "PCs" not in a.varm
    assert "X_pca" not in a.obsm
    assert "connectivities" not in a.obsp
    assert not a.uns


def test_harmony_current_native_output_is_cells_by_components():
    pytest.importorskip("harmonypy")
    a = counts_fixture()
    _common.prepare_counts(a)
    _common.normalize_hvg(sc, a, n_top_genes=25)
    _common.compute_pca(sc, a, 8)
    old_x = a.X.copy()
    old_pca = a.obsm["X_pca"].copy()
    _common.integrate_harmony(a, "sample")
    assert a.obsm["X_pca_harmony"].shape == (60, 8)
    assert np.isfinite(a.obsm["X_pca_harmony"]).all()
    np.testing.assert_array_equal(a.X, old_x)
    np.testing.assert_array_equal(a.obsm["X_pca"], old_pca)
    _common.build_neighbors(sc, a, use_rep="X_pca_harmony", n_pcs=40)
    assert a.uns["neighbors"]["params"]["use_rep"] == "X_pca_harmony"


def test_bbknn_native_changes_graph_not_expression():
    pytest.importorskip("bbknn")
    a = counts_fixture()
    _common.prepare_counts(a)
    _common.normalize_hvg(sc, a, n_top_genes=25)
    _common.compute_pca(sc, a, 8)
    old_x = a.X.copy()
    sc.external.pp.bbknn(a, batch_key="sample", n_pcs=8, approx=False, use_faiss=False)
    assert a.obsp["connectivities"].shape == (60, 60)
    assert "bbknn" in a.uns["neighbors"]["params"]
    np.testing.assert_array_equal(a.X, old_x)


def test_combat_native_preserves_stashed_counts_and_raw():
    a = counts_fixture()
    _common.prepare_counts(a)
    _common.normalize_hvg(sc, a, n_top_genes=25)
    old_counts = a.layers["counts"].copy()
    old_log = a.raw.X.copy()
    sc.pp.combat(a, key="sample")
    assert np.isfinite(a.X).all()
    np.testing.assert_array_equal(a.layers["counts"], old_counts)
    np.testing.assert_array_equal(a.raw.X, old_log)


def test_scrublet_native_score_contract_on_small_synthetic_counts():
    pytest.importorskip("skimage")
    a = counts_fixture()
    old_counts = a.X.copy()
    # Explicit threshold avoids implying calibration from a synthetic score histogram.
    sc.pp.scrublet(a, n_prin_comps=8, threshold=0.2, random_state=0)
    assert np.isfinite(a.obs["doublet_score"]).all()
    assert a.obs["predicted_doublet"].dtype == bool
    np.testing.assert_array_equal(a.X, old_counts)


def test_dask_sum_returns_named_layer_with_same_values():
    da = pytest.importorskip("dask.array")
    a = counts_fixture()
    a.X = da.from_array(a.X, chunks=(15, 80))
    pb = sc.get.aggregate(a, by="sample", func="sum")
    expected = counts_fixture().X.reshape(4, 15, 80).sum(axis=1)
    mat = pb.layers["sum"]
    if hasattr(mat, "compute"):
        mat = mat.compute()
    np.testing.assert_allclose(mat, expected)
    assert pb.X is None


def test_mapping_csv_preserves_lexical_cluster_ids(tmp_path):
    import annotate
    path = tmp_path / "mapping.csv"
    path.write_text("cluster,cell_type\n001,Type A\n002,Type B\n")
    assert annotate.load_mapping(str(path)) == {"001": "Type A", "002": "Type B"}


def test_marker_logreg_exports_only_returned_group(tmp_path, monkeypatch):
    import find_markers
    a = counts_fixture()
    _common.prepare_counts(a)
    _common.normalize_hvg(sc, a, n_top_genes=25)
    source = tmp_path / "in.h5ad"
    a.write_h5ad(source)
    monkeypatch.setattr(sys, "argv", ["find_markers.py", str(source), "--groupby", "condition",
        "--method", "logreg", "--no-plots", "--csv-dir", str(tmp_path / "out"),
        "--figdir", str(tmp_path / "figs")])
    find_markers.main()
    table = pd.read_csv(tmp_path / "out" / "markers_condition_all.csv")
    assert "scores" in table
    assert "pvals_adj" not in table
    assert table.group.nunique() == 1


def test_umap_and_dotplot_return_different_saveable_objects(tmp_path):
    import matplotlib.pyplot as plt
    a = counts_fixture()
    _common.prepare_counts(a)
    _common.normalize_hvg(sc, a, n_top_genes=25)
    a.obsm["X_umap"] = np.random.default_rng(3).normal(size=(60, 2))
    fig = sc.pl.umap(a, color="sample", return_fig=True, show=False)
    fig.savefig(tmp_path / "umap.png")
    dot = sc.pl.dotplot(a, ["g0", "g1"], groupby="sample", use_raw=True, return_fig=True)
    dot.savefig(tmp_path / "dotplot.png")
    assert (tmp_path / "umap.png").stat().st_size > 100
    assert (tmp_path / "dotplot.png").stat().st_size > 100
    plt.close("all")


def test_mtx_dispatch_preserves_orientation_and_values(tmp_path):
    import scipy.io
    x = sparse.csr_matrix([[1, 0, 2], [0, 3, 0]])
    path = tmp_path / "counts.mtx"
    scipy.io.mmwrite(path, x)
    a = _common.load_anndata(path)
    assert a.shape == (2, 3)
    np.testing.assert_array_equal(dense(a.X), dense(x))
