"""Exercise documented Census query contracts with a small local SOMA experiment."""
from pathlib import Path
import re

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "cellxgene-census"
census_api = pytest.importorskip("cellxgene_census")
soma = pytest.importorskip("tiledbsoma")
import anndata as ad
import numpy as np
import pandas as pd
import pyarrow as pa
from scipy import sparse


@pytest.fixture
def census(tmp_path):
    matrix = np.array([[0, 2, 0], [4, 0, 0], [0, 6, 0], [8, 0, 0]], dtype=np.float32)
    data = ad.AnnData(
        sparse.csr_matrix(matrix),
        obs=pd.DataFrame({
            "cell_type": ["B cell", "T cell", "B cell", "T cell"],
            "is_primary_data": [True, True, True, False],
            "dataset_id": ["a", "a", "b", "b"],
            "disease": ["COVID-19", "normal", "COVID-19 || diabetes mellitus", "normal"],
        }, index=["c0", "c1", "c2", "c3"]),
        var=pd.DataFrame({"feature_id": ["id0", "id1", "id2"],
                          "feature_name": ["DUP", "DUP", "ZERO"]},
                         index=["id0", "id1", "id2"]),
    )
    exp_uri = str(tmp_path / "experiment")
    # Native SOMA writes avoid the unrelated from_anndata / AnnData 0.13
    # ingestion incompatibility (layers.items() now includes the None/X layer).
    with soma.Experiment.create(exp_uri) as experiment:
        obs = pa.Table.from_pandas(data.obs.reset_index(drop=True).assign(soma_joinid=range(4)), preserve_index=False)
        var = pa.Table.from_pandas(data.var.reset_index(drop=True).assign(soma_joinid=range(3)), preserve_index=False)
        experiment.add_new_dataframe("obs", schema=obs.schema, index_column_names=["soma_joinid"], domain=[(0, 3)]).write(obs)
        measurement = experiment.add_new_collection("ms").add_new_collection("RNA", kind=soma.Measurement)
        measurement.add_new_dataframe("var", schema=var.schema, index_column_names=["soma_joinid"], domain=[(0, 2)]).write(var)
        raw = measurement.add_new_collection("X").add_new_sparse_ndarray("raw", type=pa.float32(), shape=(4, 3))
        rows, cols = np.nonzero(matrix)
        raw.write(pa.Table.from_pydict({"soma_dim_0": rows, "soma_dim_1": cols, "soma_data": matrix[rows, cols]}))
        presence = experiment.ms["RNA"].add_new_sparse_ndarray(
            "feature_dataset_presence_matrix", type=pa.uint8(), shape=(2, 3)
        )
        presence.write(pa.Table.from_pydict({
            "soma_dim_0": [0, 0, 0, 1, 1], "soma_dim_1": [0, 1, 2, 1, 2],
            "soma_data": pa.array([1] * 5, type=pa.uint8()),
        }))
    uri = str(tmp_path / "census")
    with soma.Collection.create(uri) as collection:
        data_collection = collection.add_new_collection("census_data")
        with soma.Experiment.open(exp_uri) as experiment:
            data_collection.set("homo_sapiens", experiment)
    with soma.Collection.open(uri) as collection:
        yield collection, matrix


def test_metadata_filter_and_duplicate_symbols(census):
    collection, _ = census
    obs = census_api.get_obs(collection, "Homo sapiens", value_filter="is_primary_data == True", column_names=["soma_joinid"])
    assert obs.soma_joinid.tolist() == [0, 1, 2]
    genes = census_api.get_var(collection, "homo_sapiens", value_filter="feature_name == 'DUP'", column_names=["feature_id"])
    assert genes.feature_id.tolist() == ["id0", "id1"]


def test_global_coordinates_and_matrix_orientation(census):
    collection, matrix = census
    result = census_api.get_anndata(collection, "homo_sapiens", obs_coords=[1, 3], var_coords=[0, 2])
    assert result.shape == (2, 2)
    np.testing.assert_array_equal(result.X.toarray(), matrix[[1, 3]][:, [0, 2]])
    obs = census_api.get_obs(collection, "homo_sapiens", coords=slice(0, 1))
    assert len(obs) == 2  # SOMA slices include the endpoint.


def test_presence_prevents_treating_unmeasured_gene_as_zero(census):
    collection, _ = census
    presence = census_api.get_presence_matrix(collection, "homo_sapiens")
    measured_dataset_ids = np.array(["a", "b"])[presence[:, [0]].toarray().all(axis=1)]
    assert measured_dataset_ids.tolist() == ["a"]
    result = census_api.get_anndata(collection, "homo_sapiens", obs_value_filter=f"dataset_id in {measured_dataset_ids.tolist()!r}", var_coords=[0])
    assert result.n_obs == 2
    assert float(result.X.mean()) == 2.0


def test_streamed_statistics_include_zeros_and_keep_genes_separate(census):
    from cellxgene_census.experimental.pp import mean_variance
    collection, matrix = census
    with collection["census_data"]["homo_sapiens"].axis_query("RNA") as query:
        result = mean_variance(query, layer="raw", axis=0, calculate_mean=True,
                               calculate_variance=True, ddof=1, nnz_only=False)
        np.testing.assert_allclose(result["mean"], matrix.mean(axis=0))
        np.testing.assert_allclose(result["variance"], matrix.var(axis=0, ddof=1), rtol=1e-6)
        assert result.loc[2, "mean"] == result.loc[2, "variance"] == 0


def test_compound_disease_labels_are_not_lost(census):
    collection, _ = census
    values = census_api.get_obs(collection, "homo_sapiens", column_names=["disease"])["disease"].unique()
    matching = [value for value in values if "COVID-19" in value.split(" || ")]
    result = census_api.get_obs(collection, "homo_sapiens", value_filter=f"disease in {matching!r} and is_primary_data == True")
    assert result.soma_joinid.tolist() == [0, 2]


def test_ml_batches_are_numpy_and_pandas_and_splits_disjoint(census):
    ml = pytest.importorskip("tiledbsoma_ml")
    collection, _ = census
    with collection["census_data"]["homo_sapiens"].axis_query("RNA") as query:
        dataset = ml.ExperimentDataset(query=query, layer_name="raw", obs_column_names=["soma_joinid", "cell_type"], batch_size=2, shuffle=False)
        dataset.set_epoch(0)
        X, obs = next(iter(ml.experiment_dataloader(dataset, num_workers=0)))
        assert isinstance(X, np.ndarray) and isinstance(obs, pd.DataFrame)
        assert X.shape == (2, 3)
        train, test = dataset.random_split(0.5, 0.5, seed=42)
        assert set(train.query_ids.obs_joinids).isdisjoint(test.query_ids.obs_joinids)
        assert len(train.query_ids.obs_joinids) + len(test.query_ids.obs_joinids) == 4
        with pytest.raises(ValueError):
            ml.experiment_dataloader(dataset, batch_size=2)


def test_scanorama_receives_concatenated_anndata_with_batch_key():
    sc = pytest.importorskip("scanpy")
    pytest.importorskip("scanorama")
    import scanpy.external as sce
    rng = np.random.default_rng(7)
    inputs = [ad.AnnData(rng.poisson(2, (30, 12)).astype(float)) for _ in range(2)]
    combined = ad.concat(inputs, label="batch", keys=["a", "b"], index_unique="-", join="inner")
    sc.pp.normalize_total(combined, target_sum=1e4)
    sc.pp.log1p(combined)
    sc.pp.pca(combined, n_comps=5)
    sce.pp.scanorama_integrate(combined, key="batch", knn=5, approx=False)
    assert combined.obsm["X_scanorama"].shape == (60, 5)
    assert np.isfinite(combined.obsm["X_scanorama"]).all()


def test_documented_python_blocks_parse():
    for path in SKILL_ROOT.rglob("*.md"):
        for index, code in enumerate(re.findall(r"```python\n(.*?)```", path.read_text(), re.S)):
            compile(code, f"{path.name}:block{index}", "exec")
