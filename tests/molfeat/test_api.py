"""Offline behavioral checks for the Molfeat 1.0 workflows documented by the skill."""
from pathlib import Path
import json

import pytest

molfeat = pytest.importorskip("molfeat", minversion="1.0.0")
import datamol as dm
import numpy as np
from rdkit import DataStructs
from molfeat.calc import (
    CATS, FPCalculator, Pharmacophore2D, RDKitDescriptors2D,
    RDKitDescriptors3D, USRDescriptors, ScaffoldKeyCalculator,
)
from molfeat.trans import FeatConcat, MoleculeTransformer
from molfeat.trans.fp import FPVecTransformer
from molfeat.store import ModelStore
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, cross_val_score

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "molfeat"


@pytest.mark.parametrize("name", [
    name for name in FPCalculator.available_fingerprints() if name != "map4"
])
def test_core_fingerprint_dimensions_and_finiteness(name):
    calc = FPCalculator(name)
    fp = calc("CCCO")
    assert fp.shape == (len(calc),)
    assert np.isfinite(fp).all()


def test_ecfp_radius_aliases_and_explicit_width():
    reference = FPCalculator("ecfp", radius=2, fpSize=2048)("CCCO")
    np.testing.assert_array_equal(FPCalculator("ecfp")("CCCO"), reference)
    np.testing.assert_array_equal(FPVecTransformer("ecfp:4", length=2048)(["CCCO"])[0], reference)
    np.testing.assert_array_equal(FPVecTransformer("morgan:2", length=2048)(["CCCO"])[0], reference)
    assert FPVecTransformer()("CCCO").shape == (1, 2000)


def test_chirality_is_an_explicit_choice():
    smiles = ["C[C@H](O)F", "C[C@@H](O)F"]
    achiral = FPCalculator("ecfp", includeChirality=False)
    chiral = FPCalculator("ecfp", includeChirality=True)
    np.testing.assert_array_equal(achiral(smiles[0]), achiral(smiles[1]))
    assert not np.array_equal(chiral(smiles[0]), chiral(smiles[1]))


def test_invalid_rows_remain_aligned_with_labels():
    transformer = MoleculeTransformer(FPCalculator("ecfp"), dtype=np.float32)
    smiles = ["CCO", "invalid", "CC(=O)O"]
    labels = np.array([1, 999, 2])
    with pytest.raises(ValueError, match="index 1"):
        transformer(smiles)
    X, positions = transformer(smiles, ignore_errors=True)
    assert positions == [0, 2]
    assert labels[positions].tolist() == [1, 2]
    assert X.shape == (2, 2048) and X.dtype == np.float32
    preserved = transformer.transform(smiles, ignore_errors=True)
    assert len(preserved) == 3 and preserved[1] is None
    np.testing.assert_array_equal(preserved[2], X[1])


def test_configuration_roundtrip_preserves_output(tmp_path):
    transformer = MoleculeTransformer(
        FPCalculator("ecfp", radius=3, fpSize=1024, includeChirality=True), dtype=np.float32,
    )
    for suffix in ["json", "yaml"]:
        path = tmp_path / f"features.{suffix}"
        getattr(transformer, f"to_state_{suffix}_file")(str(path))
        restored = getattr(MoleculeTransformer, f"from_state_{suffix}_file")(str(path))
        np.testing.assert_array_equal(transformer(["CCCO"]), restored(["CCCO"]))
        assert restored.featurizer.params["radius"] == 3


def test_concat_uses_transformers_and_components_roundtrip(tmp_path):
    parts = [FPVecTransformer("maccs"), FPVecTransformer("ecfp:4", length=2048)]
    combined = FeatConcat(parts, dtype=np.float32)
    X = combined(["CCO", "CC"], enforce_dtype=True)
    assert X.shape == (2, 2215) and combined.length == 2215
    assert len(combined) == 2
    np.testing.assert_array_equal(X[:, :167], parts[0](["CCO", "CC"]))
    for i, part in enumerate(parts):
        part.to_state_json_file(str(tmp_path / f"component_{i}.json"))
    restored = FeatConcat([
        MoleculeTransformer.from_state_json_file(str(tmp_path / f"component_{i}.json"))
        for i in range(2)
    ])
    np.testing.assert_array_equal(restored(["CCO", "CC"]), X)


def test_preprocess_is_explicit_and_ids_preserved():
    rows = [("a", "CCO"), ("bad", "invalid"), ("b", "CC(=O)O")]
    accepted, rejected = [], []
    for record_id, smiles in rows:
        mol = dm.to_mol(smiles)
        if mol is None or mol.GetNumAtoms() == 0:
            rejected.append(record_id)
            continue
        accepted.append((record_id, dm.standardize_mol(mol)))
    X = MoleculeTransformer(FPCalculator("ecfp"), dtype=np.float32)([m for _, m in accepted])
    assert X.shape == (2, 2048)
    assert [i for i, _ in accepted] == ["a", "b"] and rejected == ["bad"]


def test_descriptor_names_and_cats_bins():
    calc = RDKitDescriptors2D()
    values = calc("CCO")
    assert len(values) == len(calc.columns) == len(calc)
    assert np.isfinite(values).all()
    cats = CATS(use_3d_distances=False, scale="raw")
    assert cats("CCO").shape == (189,)
    assert len(CATS(bins=[0, 1])) == 42
    assert Pharmacophore2D(factory="gobbi", length=2048)("c1ccccc1O").shape == (2048,)
    assert len(ScaffoldKeyCalculator()("c1ccccc1O")) == 42


def test_3d_coordinates_and_shapes():
    mol = dm.conformers.generate(
        dm.to_mol("CCCO"), n_confs=1, random_seed=42,
        minimize_energy=True, num_threads=1,
    )
    assert mol is not None and mol.GetNumConformers() == 1
    for calc, width in [(USRDescriptors(), 12), (USRDescriptors("USRCAT"), 60),
                        (CATS(use_3d_distances=True), 126)]:
        values = calc(mol)
        assert values.shape == (width,) and np.isfinite(values).all()
    calc = RDKitDescriptors3D()
    assert calc(mol).shape == (len(calc),)
    with pytest.raises(ValueError):
        USRDescriptors()(dm.to_mol("CCCO"))


def test_tanimoto_preserves_identity_ranking():
    calc = FPCalculator("ecfp", radius=2, includeChirality=True)
    query = calc("CCO", raw=True)
    fps = [calc(s, raw=True) for s in ["CCO", "CCCO", "c1ccccc1"]]
    scores = np.asarray(DataStructs.BulkTanimotoSimilarity(query, fps))
    assert scores[0] == 1.0 and np.argmax(scores) == 0
    assert np.all((scores >= 0) & (scores <= 1))


def test_toy_grouped_qsar_pipeline():
    smiles = ["CCO", "CCCO", "CCCCO", "CCCCCO", "CCN", "CCCN", "CCCCN", "CCCCCN"]
    pipeline = Pipeline([
        ("features", MoleculeTransformer(RDKitDescriptors2D(), dtype=np.float64)),
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()), ("regress", Ridge(alpha=1.0)),
    ])
    scores = cross_val_score(
        pipeline, smiles, np.arange(8, dtype=float), groups=[0, 0, 1, 1, 2, 2, 3, 3],
        cv=GroupKFold(4), scoring="neg_mean_absolute_error", error_score="raise",
    )
    assert scores.shape == (4,) and np.isfinite(scores).all()


def test_modelstore_local_metadata_exact_search_and_load_contract(tmp_path):
    card = {
        "name": "fixture-ecfp", "type": "hand-crafted", "submitter": "test",
        "description": "Synthetic metadata only", "representation": "vector",
        "authors": ["test"], "group": "all", "version": 0,
    }
    folder = tmp_path / "all" / card["name"] / "0"
    folder.mkdir(parents=True)
    (folder / "metadata.json").write_text(json.dumps(card))
    (folder / "model.save").write_text(json.dumps({"fixture": [1, 2, 3]}))
    store = ModelStore(model_store_root=str(tmp_path))
    assert store._available_models is None
    assert len(store.available_models) == 1
    assert store.search(name="fixture") == []
    matches = store.search(name="fixture-ecfp")
    assert len(matches) == 1 and isinstance(matches[0].usage(), str)
    artifact, loaded_card = store.load(
        "fixture-ecfp", download_output_dir=tmp_path / "cache",
        load_fn=lambda path: json.loads(Path(path).read_text()),
    )
    assert artifact == {"fixture": [1, 2, 3]} and loaded_card.name == "fixture-ecfp"
