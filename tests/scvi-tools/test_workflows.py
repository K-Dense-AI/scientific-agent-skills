"""Small CPU API-contract checks; these do not validate biological inference."""
from pathlib import Path

import pytest

scvi = pytest.importorskip("scvi")
import anndata as ad
import mudata as md
import numpy as np
import pandas as pd
import torch

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scvi-tools"


@pytest.fixture
def counts():
    scvi.settings.seed = 0
    torch.set_num_threads(1)
    rng = np.random.default_rng(0)
    obs = pd.DataFrame({
        "batch": pd.Categorical(["a", "b"] * 60),
        "cell_type": pd.Categorical(["T", "B", "Unknown"] * 40),
        "condition": pd.Categorical(["control", "treated"] * 60),
    }, index=[f"cell{i}" for i in range(120)])
    x = rng.poisson(3, size=(120, 16)).astype(np.float32)
    a = ad.AnnData(x, obs=obs, var=pd.DataFrame(index=[f"g{i}" for i in range(16)]))
    a.layers["counts"] = x.copy()
    return a


def fit(model, **kwargs):
    model.train(max_epochs=2, accelerator="cpu", devices=1, batch_size=32,
                train_size=0.8, early_stopping=False, check_val_every_n_epoch=1,
                enable_checkpointing=False, enable_progress_bar=False,
                **kwargs)
    return model


@pytest.fixture
def rna_model(counts):
    scvi.model.SCVI.setup_anndata(counts, layer="counts", batch_key="batch")
    return fit(scvi.model.SCVI(counts, n_hidden=16, n_latent=3, gene_likelihood="nb"),
               plan_kwargs={"lr": 1e-3})


def test_scvi_de_and_persistence(rna_model, tmp_path):
    m = rna_model
    z = m.get_latent_representation()
    assert z.shape == (120, 3) and np.isfinite(z).all()
    norm = m.get_normalized_expression(library_size=1e4, n_samples=2)
    assert norm.shape == (120, 16) and np.isfinite(norm.to_numpy()).all()
    np.testing.assert_allclose(norm.sum(axis=1), 1e4, rtol=1e-5)
    de = m.differential_expression(groupby="condition", group1="treated", group2="control",
                                  mode="change", test_mode="two", delta=0.5,
                                  n_samples_overall=32, pseudocounts=0.1, silent=True)
    assert {"lfc_mean", "proba_de", "bayes_factor", "is_de_fdr_0.05"} <= set(de)
    assert de["proba_de"].between(0, 1).all()
    assert np.isfinite(float(m.history["elbo_validation"].iloc[-1, 0]))
    assert np.isfinite(float(m.get_elbo(indices=m.validation_indices)))
    m.save(tmp_path / "saved", save_anndata=True)
    restored = scvi.model.SCVI.load(tmp_path / "saved", accelerator="cpu")
    np.testing.assert_allclose(z, restored.get_latent_representation(), atol=1e-5)


def test_scanvi_probabilities_and_minification(rna_model, tmp_path):
    scanvi = scvi.model.SCANVI.from_scvi_model(rna_model, labels_key="cell_type",
                                            unlabeled_category="Unknown")
    fit(scanvi)
    probs = scanvi.predict(soft=True)
    assert probs.shape == (120, 2)
    np.testing.assert_allclose(probs.sum(axis=1), 1, atol=1e-6)
    assert set(scanvi.predict()) <= {"T", "B"}
    qzm, qzv = rna_model.get_latent_representation(return_dist=True)
    rna_model.adata.obsm["X_latent_qzm"] = qzm
    rna_model.adata.obsm["X_latent_qzv"] = qzv
    assert rna_model.minify_adata() is None
    assert rna_model.adata is not None
    rna_model.save(tmp_path / "mini", save_anndata=True)
    restored = scvi.model.SCVI.load(tmp_path / "mini", accelerator="cpu")
    assert restored.get_latent_representation().shape == (120, 3)


def test_totalvi_tuple_and_modality_de(counts):
    rng = np.random.default_rng(1)
    counts.obsm["protein_expression"] = pd.DataFrame(
        rng.poisson(3, size=(120, 4)).astype(np.float32),
        index=counts.obs_names, columns=[f"p{i}" for i in range(4)],
    )
    scvi.model.TOTALVI.setup_anndata(counts, layer="counts", batch_key="batch",
                                   protein_expression_obsm_key="protein_expression")
    m = fit(scvi.model.TOTALVI(counts, n_latent=3, n_hidden=16,
                               empirical_protein_background_prior=False))
    rna, protein = m.get_normalized_expression(n_samples=2, return_mean=True)
    assert rna.shape == (120, 16) and protein.shape == (120, 4)
    assert np.isfinite(rna.to_numpy()).all() and np.isfinite(protein.to_numpy()).all()
    for fields, expected in [(["rna"], set(counts.var_names)),
                             (["protein"], {f"p{i}_protein" for i in range(4)})]:
        de = m.differential_expression(groupby="condition", group1="treated", group2="control",
                                      use_field=fields, mode="change", n_samples_overall=32,
                                      pseudocounts=0.1, silent=True)
        assert set(de.index) == expected


def test_multivi_paired_counts(counts):
    rng = np.random.default_rng(2)
    atac = ad.AnnData(rng.poisson(1, (120, 12)).astype(np.float32), obs=counts.obs.copy(),
                     var=pd.DataFrame(index=[f"peak{i}" for i in range(12)]))
    atac.layers["counts"] = atac.X.copy()
    mdata = md.MuData({"rna": counts, "atac": atac})
    mdata.obs["batch"] = counts.obs["batch"].reindex(mdata.obs_names)
    scvi.model.MULTIVI.setup_mudata(mdata, rna_layer="counts", atac_layer="counts",
                                  batch_key="batch",
                                  modalities={"rna_layer": "rna", "atac_layer": "atac"})
    m = fit(scvi.model.MULTIVI(mdata, n_latent=3, n_hidden=16, fully_paired=True))
    assert m.get_latent_representation().shape == (120, 3)
    assert m.get_normalized_expression().shape == (120, 16)
    a = m.get_normalized_accessibility()
    assert a.shape == (120, 12) and np.isfinite(np.asarray(a)).all()


def test_methylvi_coverage_and_context(counts):
    rng = np.random.default_rng(3)
    counts.layers["cov"] = np.full(counts.shape, 10, dtype=np.float32)
    counts.layers["mc"] = rng.binomial(10, 0.4, counts.shape).astype(np.float32)
    mdata = md.MuData({"mCG": counts})
    scvi.external.METHYLVI.setup_mudata(mdata, mc_layer="mc", cov_layer="cov",
                                       methylation_contexts=["mCG"])
    m = fit(scvi.external.METHYLVI(mdata, n_latent=3, n_hidden=16))
    values = m.get_normalized_methylation()
    assert set(values) == {"mCG"}
    methylation = m.get_normalized_methylation(context="mCG")
    assert methylation.shape == counts.shape
    assert ((np.asarray(methylation) >= 0) & (np.asarray(methylation) <= 1)).all()


@pytest.mark.parametrize("model_class", [scvi.model.PEAKVI, scvi.external.POISSONVI])
def test_atac_accessibility_contract(counts, model_class):
    if model_class is scvi.external.POISSONVI:
        counts.layers["counts"] = np.random.default_rng(4).poisson(0.5, counts.shape).astype(np.float32)
    model_class.setup_anndata(counts, layer="counts", batch_key="batch")
    model = fit(model_class(counts, n_latent=3, n_hidden=16))
    values = model.get_normalized_accessibility()
    assert values.shape == counts.shape and np.isfinite(np.asarray(values)).all()


def test_count_preserving_hvg_preparation():
    import scanpy as sc
    rng = np.random.default_rng(5)
    means = np.linspace(0.5, 8, 256)
    x = rng.negative_binomial(3, 3 / (3 + means), size=(120, 256)).astype(np.float32)
    a = ad.AnnData(x)
    a.obs["batch"] = pd.Categorical(["a", "b"] * 60)
    a.layers["counts"] = x.copy()
    sc.pp.filter_genes(a, min_cells=3)
    sc.pp.highly_variable_genes(a, layer="counts", flavor="seurat_v3", batch_key="batch",
                               n_top_genes=64, subset=True)
    selected = a.var_names.astype(int).to_numpy()
    np.testing.assert_array_equal(a.layers["counts"], x[:, selected])
    assert a.shape == (120, 64)


def test_poissonvi_small_input_guard(counts):
    with pytest.raises(ValueError, match="at least 100 observations"):
        scvi.external.POISSONVI.setup_anndata(counts[:50].copy(), layer="counts")


def test_multiome_helper_anndata013_limitation(counts):
    # 1.5.1's optional unpaired branch calls removed AnnData.concatenate.
    if hasattr(ad.AnnData, "concatenate"):
        pytest.skip("This compatibility guard applies to AnnData 0.13+")
    with pytest.raises(AttributeError, match="concatenate"):
        scvi.data.organize_multiome_anndatas(counts, rna_anndata=counts.copy())
