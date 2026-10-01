"""Small, offline checks against the installed PyTDC runtime, never dataset servers."""
from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pytdc"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
tdc = pytest.importorskip("tdc")
import numpy as np
import pandas as pd
from tdc import Evaluator, metadata
from tdc.utils import create_fold, create_fold_setting_cold, create_scaffold_split
import benchmark_evaluation as benchmark
import load_and_split_data as loader
import molecular_generation as molecular


@pytest.fixture(autouse=True)
def no_http(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("offline test attempted HTTP")
    monkeypatch.setattr("requests.sessions.Session.request", fail)


def test_public_tasks_and_metadata_contracts():
    for task, (module, name, registry) in loader.TASKS.items():
        cls = getattr(importlib.import_module(module), name)
        assert registry in metadata.dataset_names, task
        assert {"name", "path"} <= inspect.signature(cls).parameters.keys()
        split = inspect.signature(cls.get_split).parameters
        assert split["seed"].default == 42
        assert split["method"].default == "random"
    assert "caco2_wang" in metadata.dataset_names["ADME"]
    assert metadata.bm_metric_names["admet_group"]["caco2_wang"] == "mae"
    assert metadata.name2id["primekg"] == 6180626


def test_label_selection_is_explicit():
    assert loader.validate_label("Tox", "tox21", "nr-ar") == "NR-AR"
    with pytest.raises(ValueError, match="requires --label-name"):
        loader.validate_label("Tox", "tox21", None)
    with pytest.raises(ValueError, match="unknown label"):
        loader.validate_label("Tox", "tox21", "wrong-target")


def test_local_adme_loader_and_split(tmp_path):
    frame = pd.DataFrame({"Drug_ID": range(20), "Drug": ["CCO"] * 20, "Y": np.arange(20.)})
    frame.to_csv(tmp_path / ("caco2_wang." + metadata.name2type["caco2_wang"]), sep="\t", index=False)
    result = loader.execute_split(task="ADME", dataset="caco2_wang", method="random", seed=42,
        fractions=(.7,.1,.2), columns=[], time_column=None, data_dir=tmp_path,
        preview=1, package_version="1.1.15")
    assert [result["partitions"][k]["rows"] for k in ["train","valid","test"]] == [14,2,4]


def test_random_zero_test_has_fixed_validation():
    frame = pd.DataFrame({"id": range(40)})
    a = create_fold(frame, 1, [.875,.125,0])
    b = create_fold(frame, 2, [.875,.125,0])
    pd.testing.assert_frame_equal(a["valid"], b["valid"])


def test_multicolumn_cold_split_discards_cross_pairs():
    frame = pd.DataFrame([(a,b) for a in range(20) for b in range(20)], columns=["Drug","Target"])
    split = create_fold_setting_cold(frame, 42, [.7,.1,.2], ["Drug","Target"])
    assert sum(map(len, split.values())) < len(frame)
    for column in frame:
        assert not (set(split["train"][column]) & set(split["test"][column]))
        assert not (set(split["valid"][column]) & set(split["test"][column]))


def test_scaffold_keeps_groups_and_omits_invalid():
    from rdkit import Chem
    from rdkit.Chem.Scaffolds import MurckoScaffold
    frame = pd.DataFrame({"Drug": ["c1ccccc1","Cc1ccccc1","C1CCCCC1","CC1CCCCC1","c1ccncc1","CCO","invalid"]})
    split = create_scaffold_split(frame, 42, [.6,.2,.2], "Drug")
    assert sum(map(len, split.values())) == 6
    sets = [{MurckoScaffold.MurckoScaffoldSmiles(mol=Chem.MolFromSmiles(s), includeChirality=False)
             for s in split[k].Drug} for k in ("train","valid","test")]
    assert not (sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])


def test_evaluator_threshold_defaults_and_average_precision():
    truth = [0,1,0,1]
    scores = [.1,.2,.3,.4]
    assert Evaluator("PR@K")(truth, scores) == 1
    assert Evaluator("PR@K")(truth, scores, threshold=.9) == pytest.approx(2/3)
    assert Evaluator("RP@K")(truth, scores) == 1
    assert Evaluator("RP@K")(truth, scores, threshold=.9) == .5
    assert Evaluator("accuracy")([0,1], [.5,.51]) == 1
    assert Evaluator("pr-auc")(truth, scores) == pytest.approx(5/6)
    assert Evaluator("MAE")([0,2], [1,2]) == .5
    assert Evaluator("RMSE")([0,2], [1,2]) == pytest.approx(np.sqrt(.5))
    assert Evaluator("PCC")([0,1,2], [1,2,3]) == pytest.approx(1)


def test_native_kl_failure_and_legacy_histogram_compatibility(monkeypatch):
    import scipy
    molecules = ["CCO","CCC","CCCC","CCN","CCCO","CC(=O)O","CC(=O)N","c1ccccc1",
                 "Cc1ccccc1","Oc1ccccc1","c1ccncc1","C1CCCCC1","CCCl","CCBr","CCS","CCOC"]
    shifted = molecules[:12] + molecules[:4]
    evaluator = Evaluator("kl_divergence")
    if not hasattr(scipy, "histogram"):
        with pytest.raises(ImportError, match="histogram"):
            evaluator(molecules, molecules)
    # Explicitly test the old NumPy-reexport compatibility bridge. This is not
    # evidence that unpatched PyTDC runs KL with modern SciPy.
    monkeypatch.setattr(scipy, "histogram", np.histogram, raising=False)
    same = evaluator(molecules, molecules)
    other = evaluator(shifted, molecules)
    assert same == pytest.approx(1)
    assert 0 <= other < same


def test_fcd_backend_transform_with_controlled_model_outputs(monkeypatch):
    from types import SimpleNamespace
    chemistry = importlib.import_module("tdc.chem_utils.evaluator")
    fake = SimpleNamespace(canonical_smiles=lambda x:x,
        get_predictions=lambda model,x:np.array([[0.,0.],[1.,1.],[2.,3.]]),
        calculate_frechet_distance=lambda **kwargs:2.)
    monkeypatch.setattr(chemistry, "chemnet", object(), raising=False)
    monkeypatch.setattr(chemistry, "fcd", fake, raising=False)
    assert chemistry.fcd_distance_tf(["CCO"], ["CCN"]) == pytest.approx(np.exp(-.4))
    monkeypatch.setitem(sys.modules, "fcd_torch", SimpleNamespace(FCD=lambda **kwargs:lambda *args:2.))
    assert chemistry.fcd_distance_torch(["CCO"], ["CCN"]) == 2.


def test_kabsch_wrapper_does_not_forward_translate():
    p = np.array([[0.,0,0],[1.,0,0],[0.,1,0]])
    q = p + 10
    assert Evaluator("kabsch_rmsd")(p,q,translate=True) > 1
    from tdc.evaluator import kabsch_rmsd
    assert kabsch_rmsd(p,q,translate=True) == pytest.approx(0,abs=1e-12)


def test_qed_helper_retains_invalid_positions(tmp_path):
    result = molecular.execute_scores(oracle_name="qed", category="local_scalar",
        smiles=["CCO","invalid","","c1ccccc1"], runtime_dir=tmp_path,
        download_acknowledged=False,package_version="1.1.15")
    rows = result["results"]
    assert [r["index"] for r in rows] == [0,1,2,3]
    assert [r["valid"] for r in rows] == [True,False,False,True]
    assert rows[1]["score"] is None and rows[2]["score"] is None
    assert rows[0]["score"] == pytest.approx(.40680796565539457)
    assert not (tmp_path / "oracle").exists()


def test_local_benchmark_aggregation_and_count_check(tmp_path):
    target = tmp_path / "admet_group" / "caco2_wang"
    target.mkdir(parents=True)
    frame = pd.DataFrame({"Drug": ["CCO","CCN"],"Y":[0.,1.]})
    frame.to_csv(target / "train_val.csv",index=False)
    frame.to_csv(target / "test.csv",index=False)
    result = benchmark.execute_evaluation(group="admet_group",dataset="caco2_wang",mode="many",
        predictions=[{"caco2_wang":[i/10,1+i/10]} for i in range(5)],
        run_seeds=list(range(5)),data_dir=tmp_path,package_version="1.1.15")
    assert result["results"] == {"caco2_wang":[.2,.141]}
    with pytest.raises(ValueError, match="requires 2 test predictions"):
        benchmark.execute_evaluation(group="admet_group",dataset="caco2_wang",mode="single",
            predictions={"caco2_wang":[0.]},run_seeds=[None],data_dir=tmp_path,package_version="1.1.15")


def test_primekg_local_artifact_and_lossy_name_graph(tmp_path):
    from tdc.resource import PrimeKG
    frame = pd.DataFrame({"x_id":[1,2],"x_type":["drug","drug"],"x_name":["same","same"],
        "x_source":["source","source"],"y_id":[3,3],"y_type":["disease","disease"],
        "y_name":["condition","condition"],"y_source":["source","source"],
        "relation":["indication","contraindication"]})
    frame.to_csv(tmp_path / "primekg.tab",index=False)
    kg = PrimeKG(path=str(tmp_path))
    assert list(kg.get_node_list(node_type="drug")) == [1,2]
    assert len(kg.get_data()) == 2
    graph = kg.to_nx()
    assert not graph.is_directed() and not graph.is_multigraph()
    assert graph.number_of_edges() == 1
    assert graph["same"]["condition"]["relation"] == "contraindication"
