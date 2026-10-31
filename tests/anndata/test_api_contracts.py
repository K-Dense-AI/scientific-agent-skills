"""Small scientific-data contracts exercised by the AnnData documentation.

No network or biological datasets; run in the isolated AnnData 0.13.4 environment.
"""

from pathlib import Path
import gzip
import warnings

import pytest

ad = pytest.importorskip("anndata")
np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
sparse = pytest.importorskip("scipy.sparse")
h5py = pytest.importorskip("h5py")
zarr = pytest.importorskip("zarr")

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "anndata"


def example(as_sparse=False):
    values = np.array([[2, 0, 1], [0, 0, 0], [1, 3, 0]], dtype=np.float32)
    data = ad.AnnData(
        sparse.csr_matrix(values) if as_sparse else values,
        obs=pd.DataFrame(
            {"cell_type": pd.Categorical(["T", "B", "T"])},
            index=["c1", "c2", "c3"],
        ),
        var=pd.DataFrame({"gene_symbol": ["A", "B", "C"]}, index=["g1", "g2", "g3"]),
    )
    data.layers["counts"] = data.X.copy()
    data.obsm["X_pca"] = np.arange(6).reshape(3, 2)
    data.varm["loadings"] = np.arange(6).reshape(3, 2)
    data.obsp["connectivities"] = sparse.csr_matrix(np.eye(3))
    data.uns["source"] = {"accession": "synthetic", "matrix_semantics": "counts"}
    data.raw = data.copy()
    return data


def dense(matrix):
    return matrix.toarray() if sparse.issparse(matrix) else np.asarray(matrix)


@pytest.mark.parametrize("as_sparse", [False, True])
def test_layer_alias_copy_on_write_and_raw_axes(as_sparse):
    data = example(as_sparse)
    original = dense(data.X).copy()
    assert data.layers[None] is data.X
    assert set(data.layers) == {None, "counts"}
    view = data[:2, :2]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ad.ImplicitModificationWarning)
        view.X = np.ones((2, 2))
    np.testing.assert_array_equal(dense(data.X), original)
    assert not view.is_view
    assert view.raw.shape == (2, 3)
    assert view.layers["counts"].shape == (2, 2)
    np.testing.assert_array_equal(dense(view.raw.X), original[:2])
    data.layers.clear(keep_x=True)
    np.testing.assert_array_equal(dense(data.X), original)
    assert list(data.layers) == [None]


@pytest.mark.parametrize("as_sparse", [False, True])
@pytest.mark.parametrize("storage", ["h5ad", "zarr"])
def test_native_roundtrip_preserves_annotations_and_provenance(tmp_path, as_sparse, storage):
    data = example(as_sparse)[:2, [0, 2]].copy()
    path = tmp_path / f"data.{storage}"
    if storage == "h5ad":
        data.write_h5ad(path, compression="gzip")
        result = ad.read_h5ad(path)
        with h5py.File(path) as store:
            assert "X" in store
            assert list(store["layers"]) == ["counts"]
    else:
        data.write_zarr(path)
        result = ad.read_zarr(path)
        store = zarr.open_group(path, mode="r")
        assert store.metadata.zarr_format == 3
        assert list(store["layers"].keys()) == ["counts"]
    np.testing.assert_array_equal(dense(result.X), dense(data.X))
    np.testing.assert_array_equal(dense(result.layers["counts"]), dense(data.layers["counts"]))
    np.testing.assert_array_equal(dense(result.raw.X), dense(data.raw.X))
    assert result.obs_names.tolist() == ["c1", "c2"]
    assert result.var_names.tolist() == ["g1", "g3"]
    assert result.raw.var_names.tolist() == ["g1", "g2", "g3"]
    assert isinstance(result.obs["cell_type"].dtype, pd.CategoricalDtype)
    assert result.uns["source"] == data.uns["source"]


def test_backed_dense_persistence_and_sparse_read_only(tmp_path):
    for as_sparse in [False, True]:
        path = tmp_path / f"backed-{as_sparse}.h5ad"
        example(as_sparse).write_h5ad(path)
        backed = ad.read_h5ad(path, backed="r+")
        try:
            backed.obs["transient"] = True
            if as_sparse:
                with pytest.raises(TypeError, match="item assignment"):
                    backed.X[0, 0] = 8
            else:
                backed.X[0, 0] = 8
            subset = backed[:2, :2].to_memory()
        finally:
            backed.file.close()
        reopened = ad.read_h5ad(path)
        assert "transient" not in reopened.obs
        assert dense(reopened.X)[0, 0] == (2 if as_sparse else 8)
        assert subset.shape == (2, 2)
        assert not subset.isbacked


def test_chunks_transpose_categories_and_external_alignment():
    data = example()
    chunks = list(data.chunked_X(2))
    assert [(start, stop) for _, start, stop in chunks] == [(0, 2), (2, 3)]
    np.testing.assert_array_equal(np.vstack([x for x, _, _ in chunks]), data.X)
    transposed = data.copy().T
    assert transposed.raw is None
    assert transposed.obs_names.tolist() == data.var_names.tolist()
    np.testing.assert_array_equal(transposed.obsm["loadings"], data.varm["loadings"])
    rename = {"T": "T_cell", "B": "B_cell"}
    data.rename_categories("cell_type", [rename[c] for c in data.obs["cell_type"].cat.categories])
    assert data.obs["cell_type"].tolist() == ["T_cell", "B_cell", "T_cell"]
    metadata = pd.DataFrame({"score": [30, 10, 20]}, index=["c3", "c1", "c2"])
    data.obs = data.obs.join(metadata, how="left", validate="one_to_one")
    assert data.obs["score"].tolist() == [10, 20, 30]


@pytest.mark.parametrize("as_sparse", [False, True])
def test_zero_count_normalization_and_log1p(as_sparse):
    data = example(as_sparse)
    counts = data.X.copy()
    total_counts = np.asarray(counts.sum(axis=1)).ravel()
    scale = np.divide(1e4, total_counts, out=np.zeros_like(total_counts, dtype=float), where=total_counts > 0)
    normalized = counts.multiply(scale[:, None]).tocsr() if sparse.issparse(counts) else counts * scale[:, None]
    logged = normalized.copy()
    if sparse.issparse(logged):
        logged.data = np.log1p(logged.data)
    else:
        logged = np.log1p(logged)
    np.testing.assert_allclose(dense(normalized).sum(axis=1), [1e4, 0, 1e4])
    np.testing.assert_allclose(dense(logged), np.log1p(dense(normalized)))
    assert np.isfinite(dense(logged)).all()
    np.testing.assert_array_equal(dense(data.layers["counts"]), dense(counts))


def test_concat_feature_presence_merge_and_pairwise():
    a = example(True)[:2, :2].copy()
    b = example(True)[2:, 1:].copy()
    joined = ad.concat({"a": a, "b": b}, join="outer", merge="same", uns_merge="same", label="batch", index_unique="-")
    assert joined.var_names.tolist() == ["g1", "g2", "g3"]
    assert joined.obs["batch"].tolist() == ["a", "a", "b"]
    np.testing.assert_array_equal(dense(joined.X), [[2, 0, 0], [0, 0, 0], [0, 3, 0]])
    assert not joined.obsp
    assert joined.uns["source"]["accession"] == "synthetic"
    no_merge = ad.concat([a, b], join="inner", merge=None)
    assert not len(no_merge.var.columns)
    assert "gene_symbol" in ad.concat([a, b], join="inner", merge="same").var
    graphs = ad.concat([a, b], pairwise=True)
    np.testing.assert_array_equal(dense(graphs.obsp["connectivities"]), np.eye(3))
    a.X = dense(a.X)
    b.X = dense(b.X)
    dense_join = ad.concat([a, b], join="outer")
    assert np.isnan(dense_join.X[0, 2])
    assert np.isnan(dense_join.X[2, 0])


def test_collection_conversion_explicitly_excludes_layers():
    from anndata.experimental import AnnCollection

    collection = AnnCollection([example(), example()], index_unique="-", label="source")
    assert collection.to_adata().X is None
    subset = collection[:2, :].to_adata(ignore_layers=True)
    np.testing.assert_array_equal(subset.X, example().X[:2])
    assert "counts" not in subset.layers
    assert subset.raw is None
    assert "source" in subset.obs


@pytest.mark.parametrize("storage", ["h5ad", "zarr"])
def test_lazy_read_and_element_lifetime(tmp_path, storage):
    pytest.importorskip("dask")
    pytest.importorskip("xarray")
    from anndata.experimental import read_lazy, read_elem_lazy

    data = example(True)
    path = tmp_path / f"lazy.{storage}"
    if storage == "h5ad":
        data.write_h5ad(path)
        with h5py.File(path, "r") as store:
            lazy = read_lazy(store)
            result = lazy[:2, :2].to_memory()
            matrix = read_elem_lazy(store["X"])[:2, :2].compute()
            np.testing.assert_array_equal(dense(matrix), dense(data.X)[:2, :2])
    else:
        data.write_zarr(path)
        lazy = read_lazy(path)
        assert lazy.obs.iloc[:2].to_memory().index.tolist() == ["c1", "c2"]
        result = lazy[:2, :2].to_memory()
    np.testing.assert_array_equal(dense(result.X), dense(data.X)[:2, :2])


def test_concat_on_disk_matches_memory(tmp_path):
    pytest.importorskip("dask")
    from anndata.experimental import concat_on_disk

    a = example(True)[:2, :2].copy()
    b = example(True)[2:, 1:].copy()
    inputs = {}
    for key, value in {"a": a, "b": b}.items():
        inputs[key] = tmp_path / f"{key}.h5ad"
        value.write_h5ad(inputs[key])
    output = tmp_path / "combined.h5ad"
    options = dict(join="outer", merge="same", label="batch", index_unique="-")
    concat_on_disk(inputs, output, max_loaded_elems=6, **options)
    result = ad.read_h5ad(output)
    expected = ad.concat({"a": a, "b": b}, **options)
    np.testing.assert_array_equal(dense(result.X), dense(expected.X))
    assert result.obs_names.equals(expected.obs_names)
    assert result.var_names.equals(expected.var_names)
    np.testing.assert_array_equal(dense(result.layers["counts"]), dense(expected.layers["counts"]))


def test_mtx_text_umi_hdf_and_csv_export(tmp_path):
    from scipy.io import mmwrite

    values = example().X
    mmwrite(tmp_path / "matrix.mtx", sparse.coo_matrix(values.T))
    matrix = ad.io.read_mtx(tmp_path / "matrix.mtx").T
    np.testing.assert_array_equal(dense(matrix.X), values)
    csv_path = tmp_path / "matrix.csv"
    pd.DataFrame(values, index=["c1", "c2", "c3"], columns=["g1", "g2", "g3"]).to_csv(csv_path)
    from_csv = ad.io.read_csv(csv_path, first_column_names=True)
    np.testing.assert_array_equal(from_csv.X, values)
    assert from_csv.obs_names.tolist() == ["c1", "c2", "c3"]
    with gzip.open(tmp_path / "counts.tsv.gz", "wt") as handle:
        handle.write("gene\tcell\tcount\ng1\tc1\t2\ng2\tc2\t3\n")
    umi = ad.io.read_umi_tools(tmp_path / "counts.tsv.gz")
    np.testing.assert_array_equal(dense(umi.X), [[2, 0], [0, 3]])
    with h5py.File(tmp_path / "generic.h5", "w") as store:
        store["matrix"] = values
    np.testing.assert_array_equal(ad.io.read_hdf(tmp_path / "generic.h5", key="matrix").X, values)
    data = example()
    data.write_csvs(tmp_path / "metadata")
    assert not (tmp_path / "metadata" / "X.csv").exists()
    data.write_csvs(tmp_path / "full", skip_data=False)
    assert (tmp_path / "full" / "X.csv").exists()


def test_excel_and_legacy_loom_read(tmp_path):
    pytest.importorskip("openpyxl")
    loompy = pytest.importorskip("loompy")
    frame = pd.DataFrame([[1., 0.], [0., 2.]], index=["c1", "c2"], columns=["g1", "g2"])
    frame.to_excel(tmp_path / "matrix.xlsx")
    data = ad.io.read_excel(tmp_path / "matrix.xlsx", sheet=0)
    np.testing.assert_array_equal(data.X, frame.to_numpy())
    assert data.obs_names.tolist() == frame.index.tolist()
    loompy.create(
        str(tmp_path / "matrix.loom"), frame.to_numpy().T,
        {"Gene": np.array(["g1", "g2"])}, {"CellID": np.array(["c1", "c2"])},
    )
    loom = ad.io.read_loom(tmp_path / "matrix.loom", obs_names="CellID", var_names="Gene")
    np.testing.assert_array_equal(dense(loom.X), frame.to_numpy())
    assert loom.var_names.tolist() == ["g1", "g2"]


def test_write_elem_into_layer_group(tmp_path):
    data = example(True)
    path = tmp_path / "element.h5ad"
    data.write_h5ad(path)
    with h5py.File(path, "r+") as store:
        ad.io.write_elem(store["layers"], "new_layer", data.X.copy())
    result = ad.read_h5ad(path)
    np.testing.assert_array_equal(dense(result.layers["new_layer"]), dense(data.X))
