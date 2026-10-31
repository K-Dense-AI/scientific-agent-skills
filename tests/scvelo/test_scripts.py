"""Native kinetic fixtures, file round trips and preprocessing failure shields."""
from pathlib import Path
import os
import subprocess
import sys

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scvelo"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

np = pytest.importorskip("numpy")
scv = pytest.importorskip("scvelo")
sc = pytest.importorskip("scanpy")
ad = pytest.importorskip("anndata")
pytest.importorskip("loompy")
import loompy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import sparse
import rna_velocity_workflow as workflow
import skill_contract

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def kinetic_counts(seed=1):
    """Simulated induction/repression kinetics followed by Poisson sampling."""
    data = scv.datasets.simulation(n_obs=100, n_vars=16, noise_level=0.2, random_seed=seed)
    rng = np.random.default_rng(seed)
    for key in ("spliced", "unspliced"):
        data.layers[key] = sparse.csr_matrix(rng.poisson(10 * data.layers[key]).astype(np.float32))
    data.X = data.layers["spliced"].copy()
    data = data[np.asarray(data.X.sum(axis=1)).ravel() > 0].copy()
    data.obs_names = [f"cell{i}" for i in range(data.n_obs)]
    data.var_names = [f"gene{i}" for i in range(data.n_vars)]
    data.obs["clusters"] = np.where(data.obs["true_t"] < data.obs["true_t"].median(), "early", "late")
    data.obs["clusters"] = data.obs["clusters"].astype("category")
    return data


@pytest.fixture(scope="module", params=["deterministic", "dynamical"])
def native_run(request, tmp_path_factory):
    data = kinetic_counts()
    original = data.copy()
    # Prove old processed X/PCA/neighbors are not silently used for the new gene set.
    data.X = np.full(data.shape, -3, dtype=np.float32)
    data.uns["log1p"] = {"base": None}
    data.obsm["X_pca"] = np.full((data.n_obs, 2), np.nan)
    directory = tmp_path_factory.mktemp(request.param)
    result = workflow.run_velocity_analysis(
        data, groupby="clusters", n_top_genes=12, n_neighbors=12,
        n_pcs=5, mode=request.param, recover_max_iter=5, output_dir=directory,
    )
    return request.param, result, original, directory


def test_native_results_and_provenance(native_run):
    mode, result, original, directory = native_run
    assert result.n_obs == original.n_obs
    assert 3 <= result.n_vars <= 12
    assert np.isfinite(result.obsm["X_pca"]).all()
    assert result.uns["neighbors"]["params"]["n_neighbors"] == 12
    for key in ("spliced", "unspliced"):
        expected = original[:, result.var_names].layers[key].toarray()
        np.testing.assert_array_equal(result.layers[f"{key}_counts"].toarray(), expected)
        assert np.isfinite(result.layers[key].data).all()
    mask = result.var["velocity_genes"].to_numpy()
    assert mask.sum() >= 2
    assert np.isfinite(result.layers["velocity"][:, mask]).all()
    assert result.uns["velocity_graph"].shape == (result.n_obs, result.n_obs)
    assert result.uns["velocity_graph"].nnz > 0
    assert result.uns["velocity_workflow"]["mode"] == mode
    assert "rank_velocity_genes" in result.uns


def test_relative_times_fits_and_transition_matrix(native_run):
    mode, result, _, _ = native_run
    for key in ["velocity_pseudotime"] + (["latent_time"] if mode == "dynamical" else []):
        values = result.obs[key].to_numpy()
        assert np.isfinite(values).all()
        assert values.min() >= -1e-6
        assert values.max() <= 1 + 1e-6
        # Automatic root inference can yield a degenerate deterministic ordering;
        # the workflow must record it rather than present it as informative time.
        assert result.uns["velocity_workflow"]["diagnostics"][f"{key}_constant"] == bool(np.ptp(values) == 0)
        if key == "latent_time":
            assert np.ptp(values) > 0
    coherence = result.obs["velocity_confidence"].to_numpy()
    assert np.isfinite(coherence).all()
    assert coherence.min() >= 0
    assert coherence.max() <= 1 + 1e-6
    transition = scv.utils.get_transition_matrix(result)
    assert (transition.data >= 0).all()
    np.testing.assert_allclose(np.asarray(transition.sum(axis=1)).ravel(), 1, atol=1e-5)
    if mode == "dynamical":
        assert np.isfinite(result.var["fit_likelihood"]).any()
        assert result.layers["fit_t"].shape == result.shape
    else:
        assert "latent_time" not in result.obs


def test_native_pngs_and_h5ad_round_trip(native_run):
    mode, result, _, directory = native_run
    names = {"velocity_stream.png", "velocity_arrows.png", "pseudotime.png", "velocity_quality.png"}
    if mode == "dynamical":
        names |= {"latent_time.png", "dynamical_gene_heatmap.png"}
    assert {p.name for p in directory.glob("*.png")} == names
    for name in names:
        pixels = plt.imread(directory / name)
        assert pixels.shape[0] > 100 and pixels.shape[1] > 100
        assert np.ptp(pixels) > 0.5
    loaded = ad.read_h5ad(directory / "adata_velocity.h5ad")
    np.testing.assert_allclose(loaded.layers["velocity"], result.layers["velocity"])
    assert loaded.uns["velocity_workflow"]["packages"]["scvelo"] == scv.__version__
    assert not plt.get_fignums()


@pytest.mark.parametrize("layer", ["spliced", "unspliced"])
def test_missing_layer_rejected_without_output(layer, tmp_path):
    data = kinetic_counts()
    del data.layers[layer]
    with pytest.raises(ValueError, match=layer):
        workflow.run_velocity_analysis(data, output_dir=tmp_path / "absent")
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("bad", [np.nan, np.inf, -1])
def test_invalid_counts_rejected(bad):
    data = kinetic_counts()
    data.layers["unspliced"][0, 0] = bad
    with pytest.raises(ValueError, match="finite nonnegative"):
        workflow.validate_layers(data)


def test_duplicate_identifiers_rejected():
    data = kinetic_counts()
    data.obs_names = ["duplicate"] * data.n_obs
    with pytest.raises(ValueError, match="unique"):
        workflow.validate_layers(data)


def test_missing_group_is_explicit_before_mutation(tmp_path):
    data = kinetic_counts()
    original = data.X.copy()
    with pytest.raises(ValueError, match="Grouping column"):
        workflow.run_velocity_analysis(data, groupby="absent", output_dir=tmp_path)
    np.testing.assert_array_equal(data.X.toarray(), original.toarray())


def test_processed_layers_cannot_be_normalized_twice(native_run, tmp_path):
    _, result, _, _ = native_run
    with pytest.raises(ValueError, match="fresh raw layers"):
        workflow.run_velocity_analysis(result, groupby="clusters", output_dir=tmp_path)


def test_stochastic_numpy2_rejected_before_mutation(tmp_path):
    if int(np.__version__.split(".")[0]) < 2:
        pytest.skip("This guard applies to NumPy 2")
    data = kinetic_counts()
    with pytest.raises(RuntimeError, match="stochastic GLS"):
        workflow.run_velocity_analysis(data, mode="stochastic", output_dir=tmp_path)
    assert "spliced_counts" not in data.layers


def test_all_zero_counts_rejected():
    data = kinetic_counts()
    data.layers["unspliced"] = sparse.csr_matrix(data.shape)
    with pytest.raises(ValueError, match="no positive"):
        workflow.validate_layers(data)


def test_absent_groups_and_no_plot_run(tmp_path):
    data = kinetic_counts()
    workflow.run_velocity_analysis(data, groupby=None, mode="deterministic", n_top_genes=12,
                                    n_neighbors=12, output_dir=tmp_path, make_plots=False)
    assert "rank_velocity_genes" not in data.uns
    assert not list(tmp_path.glob("*.png"))
    assert "velocity_umap" not in data.obsm
    assert (tmp_path / "adata_velocity.h5ad").exists()


def make_loom(path, data):
    # Native writer avoids AnnData 0.13 write_loom's unrelated layers[None] issue.
    loompy.create(str(path), {"": data.X.T, "spliced": data.layers["spliced"].T,
                             "unspliced": data.layers["unspliced"].T},
                  {"Gene": data.var_names.to_numpy()}, {"CellID": data.obs_names.to_numpy()})


def test_native_loom_read_and_exact_reordered_alignment(tmp_path):
    original = kinetic_counts()
    loom = tmp_path / "counts.loom"
    make_loom(loom, original)
    loaded = workflow.load_from_loom(loom)
    np.testing.assert_array_equal(loaded.layers["spliced"].toarray(), original.layers["spliced"].toarray())
    processed = original[::-1, ::-1].copy()
    processed.X = np.ones(processed.shape)
    processed_path = tmp_path / "processed.h5ad"
    processed.write_h5ad(processed_path)
    merged = workflow.load_from_loom(loom, processed_path)
    assert merged.obs_names.tolist() == processed.obs_names.tolist()
    np.testing.assert_array_equal(merged.layers["unspliced"].toarray(), processed.layers["unspliced"].toarray())
    np.testing.assert_array_equal(merged.X, processed.X)


def test_mismatched_loom_ids_do_not_silently_intersect(tmp_path):
    data = kinetic_counts()
    loom = tmp_path / "counts.loom"
    make_loom(loom, data)
    data.obs_names = ["wrong-" + value for value in data.obs_names]
    processed = tmp_path / "wrong.h5ad"
    data.write_h5ad(processed)
    with pytest.raises(ValueError, match="do not all match"):
        workflow.load_from_loom(loom, processed)


@pytest.mark.parametrize("file_format", ["h5ad", "loom"])
def test_cli_analyzes_local_counts_without_downloads(file_format, tmp_path):
    data = kinetic_counts()
    input_path = tmp_path / f"input.{file_format}"
    if file_format == "loom":
        make_loom(input_path, data)
    else:
        # Exercise dense matrices as well as the sparse native fixture.
        for key in ("spliced", "unspliced"):
            data.layers[key] = data.layers[key].toarray()
        data.write_h5ad(input_path)
    output = tmp_path / "cli-output"
    completed = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "rna_velocity_workflow.py"),
         str(input_path), "--mode", "deterministic", "--no-plots",
         "--n-top-genes", "12", "--n-neighbors", "12", "--output-dir", str(output)],
        capture_output=True, text=True, timeout=90,
        env={**os.environ, "MPLBACKEND": "Agg", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    saved = ad.read_h5ad(output / "adata_velocity.h5ad")
    assert saved.uns["velocity_workflow"]["mode"] == "deterministic"
