"""Small native TorchDrug 0.2.1 checks; no remote datasets or weights."""
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "torchdrug"
torch = pytest.importorskip("torch")
pytest.importorskip("torchdrug")
from torchdrug import core, data, models, tasks, transforms


@core.Registry.register("datasets.TorchdrugSkillFixture")
class Fixture(data.MoleculeDataset, core.Configurable):
    def __init__(self, features="default"):
        self.load_smiles(
            ["CCO", "CCN", "C#N", "CCCl", "c1ccccc1", "c1ccncc1", "CC(=O)O", "C1CCCCC1"],
            {"label": [0, 1, 0, 1, 0, 1, 0, 1]},
            atom_feature=features,
            bond_feature="pretrain" if features == "pretrain" else "default",
            kekulize=True,
        )


def molecules(features="default"):
    return Fixture(features)


def gin(dataset):
    return models.GIN(dataset.node_feature_dim, [8, 8], edge_input_dim=dataset.edge_feature_dim)


def test_molecule_collation_and_roundtrip():
    ds = molecules()
    packed = data.graph_collate([ds[0], ds[1]])["graph"]
    assert packed.to_smiles() == ["CCO", "CCN"]
    assert len(packed.unpack()) == 2
    assert int(packed.num_edge) == 8
    output = gin(ds)(packed, packed.node_feature.float())
    assert output["graph_feature"].shape == (2, 8)
    assert output["node_feature"].shape == (6, 8)


def test_property_engine_train_predict_checkpoint(tmp_path):
    ds = molecules()
    task = tasks.PropertyPrediction(gin(ds), task=ds.tasks, criterion="bce", metric=("auroc", "auprc"))
    optimizer = torch.optim.Adam(task.parameters(), lr=1e-3)
    solver = core.Engine(task, ds, ds, ds, optimizer, batch_size=4)
    solver.train(num_epoch=1, batch_per_epoch=1)
    metric = solver.evaluate("valid")
    assert all(torch.isfinite(value) for value in metric.values())
    batch = data.graph_collate([ds[0], ds[1]])
    task.eval()
    with torch.no_grad():
        pred = task.predict(batch)
    assert pred.shape == (2, 1)
    assert ((torch.sigmoid(pred) >= 0) & (torch.sigmoid(pred) <= 1)).all()
    path = str(tmp_path / "solver.pth")
    solver.save(path)
    solver.load(path)
    assert set(torch.load(path, map_location="cpu")) >= {"model", "optimizer"}
    import json
    restored = core.Configurable.load_config_dict(json.loads(json.dumps(solver.config_dict())))
    restored.load(path)
    restored.model.eval()
    with torch.no_grad():
        assert torch.allclose(pred, restored.model.predict(batch))


def test_regression_original_scale():
    ds = molecules()
    ds.targets["label"] = [10., 20., 30., 40., 50., 60., 70., 80.]
    task = tasks.PropertyPrediction(gin(ds), task=ds.tasks, criterion="mse")
    task.preprocess(ds, None, None)
    for param in task.mlp.parameters():
        torch.nn.init.zeros_(param)
    pred = task.predict(data.graph_collate([ds[0], ds[1]]))
    assert torch.allclose(pred, torch.full((2, 1), 45.))


def test_scaffold_partition_has_no_overlap():
    ds = molecules()
    torch.manual_seed(1)
    parts = data.scaffold_split(ds, [4, 2, 2])
    groups = [{sample["graph"].to_scaffold() for sample in part} for part in parts]
    assert sum(map(len, parts)) == len(ds)
    assert not any(groups[i] & groups[j] for i in range(3) for j in range(i + 1, 3))


def test_masking_and_infograph_transfer_prefixes():
    ds = molecules("pretrain")
    encoder = gin(ds)
    masking = tasks.AttributeMasking(encoder, mask_rate=0.15)
    masking.preprocess(ds, None, None)
    loss, _ = masking(data.graph_collate([ds[0], ds[1]]))
    assert torch.isfinite(loss)
    downstream = tasks.PropertyPrediction(gin(ds), task=ds.tasks, criterion="bce")
    result = downstream.load_state_dict(masking.state_dict(), strict=False)
    assert not any(key.startswith("model.") for key in result.missing_keys)
    info = tasks.Unsupervised(models.InfoGraph(gin(ds), separate_model=False))
    prefix = "model.model."
    state = {key[len(prefix):]: value for key, value in info.state_dict().items() if key.startswith(prefix)}
    assert state
    gin(ds).load_state_dict(state, strict=True)
    loss, _ = info(data.graph_collate([ds[0], ds[1]]))
    assert torch.isfinite(loss)


def test_protein_residue_view_and_vector_targets():
    proteins = [data.Protein.from_sequence(seq, atom_feature=None, bond_feature=None)
                for seq in ["MKTAY", "AGWT"]]
    assert [int(p.num_atom) for p in proteins] == [0, 0]
    assert [int(p.num_residue) for p in proteins] == [5, 4]
    samples = [{"graph": p, "targets": torch.tensor(target, dtype=torch.float)}
               for p, target in zip(proteins, [[1, 0], [0, 1]])]
    model = models.ProteinCNN(proteins[0].residue_feature.shape[-1], [8, 8], readout="mean")
    task = tasks.MultipleBinaryClassification(model, task=[0, 1], metric=("auprc@micro", "f1_max"))
    task.preprocess(samples, None, None)
    batch = data.graph_collate(samples)
    loss, _ = task(batch)
    assert torch.isfinite(loss)
    assert task.predict(batch).shape == (2, 2)
    assert torch.equal(task.target(batch), torch.tensor([[1., 0.], [0., 1.]]))
    atom_protein = data.Protein.from_sequence("AG", atom_feature=None, bond_feature=None, residue_feature=None)
    assert atom_protein.view == "atom"
    viewed = transforms.ProteinView(view="residue")({"graph": atom_protein})["graph"]
    assert viewed.view == "residue"


def test_fast_protein_unknown_residue_is_not_preserved():
    with pytest.warns(UserWarning, match="Unknown residue"):
        protein = data.Protein.from_sequence("AX", atom_feature=None, bond_feature=None)
    symbols = "".join(data.Protein.id2residue_symbol[int(i)] for i in protein.residue_type)
    assert symbols == "AG"
    # No bonds exist in the fast path, so to_sequence treats each residue as a component.
    assert protein.to_sequence() == "A.G"


def test_generation_tasks_construct_and_nll():
    ds = molecules("symbol")
    model = models.RGCN(ds.node_feature_dim, [8], num_relation=ds.num_bond_type)
    task = tasks.GCPNGeneration(model, ds.atom_types, max_node=8, max_edge_unroll=8, criterion="nll")
    task.preprocess(ds, None, None)
    loss, _ = task(data.graph_collate([ds[0], ds[1]]))
    assert torch.isfinite(loss)
    from torchdrug.layers import distribution
    model = models.RGCN(ds.num_atom_type, [8], num_relation=ds.num_bond_type)
    node = models.GraphAF(model, distribution.IndependentGaussian(torch.zeros(ds.num_atom_type), torch.ones(ds.num_atom_type)), num_layer=1)
    edge_dim = ds.num_bond_type + 1
    edge = models.GraphAF(model, distribution.IndependentGaussian(torch.zeros(edge_dim), torch.ones(edge_dim)), use_edge=True, num_layer=1)
    task = tasks.AutoregressiveGeneration(node, edge, max_node=8, max_edge_unroll=8, criterion="nll")
    task.preprocess(ds, None, None)
    loss, _ = task(data.graph_collate([ds[0], ds[1]]))
    assert torch.isfinite(loss)


def test_kg_filtered_all_entity_ranking_and_fact_split():
    ds = data.KnowledgeGraphDataset()
    ds.load_triplet([(0, 1, 0), (1, 2, 0), (2, 3, 1), (3, 0, 1), (0, 2, 0), (1, 3, 1)])
    train = torch.utils.data.Subset(ds, [0, 1, 2, 3])
    valid = torch.utils.data.Subset(ds, [4])
    test = torch.utils.data.Subset(ds, [5])
    task = tasks.KnowledgeGraphCompletion(models.RotatE(ds.num_entity, ds.num_relation, 8, max_score=9), num_negative=2, fact_ratio=.5, sample_weight=False)
    reduced, _, _ = task.preprocess(train, valid, test)
    assert len(reduced) == 2
    assert int(task.fact_graph.num_edge) == 2
    batch = torch.stack([ds[4], ds[5]])
    pred = task.predict(batch)
    assert pred.shape == (2, 2, ds.num_entity)
    assert all(torch.isfinite(v) for v in task.evaluate(pred, task.target(batch)).values())
    task.full_batch_eval = True
    assert torch.allclose(pred, task.predict(batch))


def test_retrosynthesis_checkpoint_contract():
    model = models.RGCN(3, [4], num_relation=3)
    center = tasks.CenterIdentification(model, feature=("graph", "atom", "bond"))
    synthon = tasks.SynthonCompletion(models.RGCN(3, [4], num_relation=3), feature=("graph",))
    task = tasks.Retrosynthesis(center, synthon, center_topk=2, num_synthon_beam=5, max_prediction=10)
    task.load_state_dict(center.state_dict())
    task.load_state_dict(synthon.state_dict())
    with pytest.raises(ValueError, match="strict=True"):
        task.load_state_dict(center.state_dict(), strict=False)
    with pytest.raises(RuntimeError, match="Neither"):
        task.load_state_dict(task.state_dict())
