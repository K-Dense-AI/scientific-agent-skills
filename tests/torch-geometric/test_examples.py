"""Run the documented recipes on small graphs, without datasets or weights."""
from __future__ import annotations

import ast
import importlib.util
import math
from pathlib import Path
import re
import sys

import pytest

torch = pytest.importorskip('torch')
pyg = pytest.importorskip('torch_geometric')
from torch_geometric.data import Data, Batch, HeteroData
from torch_geometric.nn import GCNConv, SAGEConv, GAE, VGAE, to_hetero
from torch_geometric.transforms import RandomLinkSplit, ToUndirected
from torch_geometric.utils import to_undirected

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'torch-geometric'


def recipe(tmp_path, relative, marker, namespace=None, definitions_only=True):
    """Import the actual fenced recipe (or its definitions), not a reimplementation."""
    text = (SKILL_ROOT / relative).read_text()
    block = next(b for b in re.findall(r'```python\n(.*?)```', text, re.S) if marker in b)
    tree = ast.parse(block)
    if definitions_only:
        tree.body = [n for n in tree.body if isinstance(n, (
            ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef))]
    source = ast.unparse(tree)
    path = tmp_path / f'recipe_{len(list(tmp_path.glob("recipe_*.py")))}.py'
    path.write_text(source)
    name = f'pyg_doc_{id(path)}'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    module.__dict__.update({'torch': torch, **(namespace or {})})
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def graph():
    torch.manual_seed(42)
    src = torch.arange(30)
    edge_index = to_undirected(torch.stack([src, (src + 1) % 30]))
    return Data(x=torch.randn(31, 4), edge_index=edge_index,
                y=torch.arange(31) % 3, num_nodes=31)


def split(graph):
    torch.manual_seed(10)
    return RandomLinkSplit(num_val=0.2, num_test=0.2, is_undirected=True,
                           disjoint_train_ratio=0.25,
                           add_negative_train_samples=True)(graph)


def pairs(edges, undirected=False):
    return {tuple(sorted(p)) if undirected else tuple(p) for p in edges.t().tolist()}


def test_gcn_and_graph_pooling_recipes(tmp_path, graph):
    m = recipe(tmp_path, 'SKILL.md', 'class GCN(')
    model = m.GCN(4, 8, 3)
    out = model(graph.x, graph.edge_index)
    assert out.shape == (31, 3)
    loss = torch.nn.functional.cross_entropy(out[:10], graph.y[:10])
    loss.backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
    m = recipe(tmp_path, 'SKILL.md', 'class GraphClassifier(')
    classifier = m.GraphClassifier(4, 8, 2)
    batched = Batch.from_data_list([graph, graph.clone()])
    assert classifier(batched.x, batched.edge_index, batched.batch).shape == (2, 2)
    assert batched.edge_index[:, graph.num_edges:].min() == graph.num_nodes


def test_custom_gcn_matches_native_with_existing_loop(tmp_path, graph):
    m = recipe(tmp_path, 'references/message_passing.md', 'class GCNConv(')
    custom, native = m.GCNConv(4, 5), GCNConv(4, 5)
    native.load_state_dict(custom.state_dict())
    edges = torch.cat([graph.edge_index, torch.tensor([[0], [0]])], dim=1)
    torch.testing.assert_close(custom(graph.x, edges), native(graph.x, edges))
    assert custom(graph.x, torch.empty((2, 0), dtype=torch.long)).shape == (31, 5)


def test_message_direction_and_edgeconv(tmp_path):
    m = recipe(tmp_path, 'SKILL.md', 'class MyConv(')
    conv = m.MyConv(1, 1)
    with torch.no_grad():
        conv.lin.weight.fill_(1)
        conv.lin.bias.zero_()
    x, edge = torch.tensor([[2.], [3.], [5.]]), torch.tensor([[0, 1], [2, 2]])
    torch.testing.assert_close(conv(x, edge), torch.tensor([[0.], [0.], [5.]]))
    m = recipe(tmp_path, 'references/message_passing.md', 'class EdgeConv(')
    assert m.EdgeConv(1, 4)(x, edge).shape == (3, 4)


def test_link_split_sets_and_negative_universe(graph):
    train, val, test = split(graph)
    all_pos = pairs(graph.edge_index, True)
    train_pos = pairs(train.edge_label_index[:, train.edge_label == 1], True)
    train_mp = pairs(train.edge_index, True)
    val_pos = pairs(val.edge_label_index[:, val.edge_label == 1], True)
    test_pos = pairs(test.edge_label_index[:, test.edge_label == 1], True)
    assert train_pos.isdisjoint(train_mp)
    assert pairs(val.edge_index, True) == train_mp | train_pos
    assert pairs(test.edge_index, True) == train_mp | train_pos | val_pos
    assert test_pos.isdisjoint(pairs(test.edge_index, True))
    for g in [train, val, test]:
        assert pairs(g.edge_label_index[:, g.edge_label == 0], True).isdisjoint(all_pos)
        assert set(g.edge_label.tolist()) == {0., 1.}


def test_link_training_and_gae_metrics(tmp_path, graph):
    train, val, _ = split(graph)
    m = recipe(tmp_path, 'references/link_prediction.md', 'class LinkEncoder(')
    model = m.LinkEncoder(4, 8, 4)
    n = recipe(tmp_path, 'references/link_prediction.md', 'def train(train_data)',
               vars(m) | {'model': model, 'optimizer': torch.optim.Adam(model.parameters())})
    assert math.isfinite(n.train(train))
    assert 0 <= n.test(val) <= 1
    g = recipe(tmp_path, 'references/link_prediction.md', 'class Encoder(')
    model = GAE(g.Encoder(4, 4))
    g.model, g.train_data = model, train
    g.optimizer = torch.optim.Adam(model.parameters())
    assert math.isfinite(g.train())
    auc, ap = g.test(val)
    assert 0 <= auc <= 1 and 0 <= ap <= 1
    v = recipe(tmp_path, 'references/link_prediction.md', 'class VariationalEncoder(',
               {'GCNConv': GCNConv})
    vae = VGAE(v.VariationalEncoder(4, 4))
    z = vae.encode(train.x, train.edge_index)
    assert z.shape == (31, 4) and torch.isfinite(vae.kl_loss())


@pytest.fixture
def hetero():
    d = HeteroData()
    d['paper'].x = torch.randn(6, 4)
    d['author'].x = torch.randn(4, 3)
    d['paper', 'cites', 'paper'].edge_index = torch.tensor([[0, 1, 2], [1, 2, 3]])
    d['author', 'writes', 'paper'].edge_index = torch.tensor([[0, 1, 2, 3], [0, 1, 2, 3]])
    return ToUndirected()(d)


def test_heterogeneous_model_recipes(tmp_path, hetero):
    m = recipe(tmp_path, 'references/heterogeneous.md', 'class GNN(')
    model = to_hetero(m.GNN(8, 3), hetero.metadata())
    out = model(hetero.x_dict, hetero.edge_index_dict)
    assert out['paper'].shape == (6, 3) and out['author'].shape == (4, 3)
    m = recipe(tmp_path, 'references/heterogeneous.md', 'class GAT(')
    out = to_hetero(m.GAT(8, 3), hetero.metadata())(hetero.x_dict, hetero.edge_index_dict)
    assert out['paper'].shape == (6, 3)
    m = recipe(tmp_path, 'references/heterogeneous.md', 'class HeteroGNN(')
    assert m.HeteroGNN(8, 3, 2)(hetero.x_dict, hetero.edge_index_dict).shape == (6, 3)
    m = recipe(tmp_path, 'references/heterogeneous.md', 'class HGT(', {'data': hetero})
    assert m.HGT(8, 3, 2, 2)(hetero.x_dict, hetero.edge_index_dict).shape == (6, 3)


def test_heterogeneous_link_reverse_split():
    d = HeteroData()
    d['user'].x, d['movie'].x = torch.randn(8, 3), torch.randn(9, 4)
    e = ('user', 'rates', 'movie')
    rev = ('movie', 'rev_rates', 'user')
    d[e].edge_index = torch.tensor([[i for i in range(8) for _ in range(2)],
                                  [(i + j) % 9 for i in range(8) for j in range(2)]])
    d = ToUndirected()(d)
    for g in RandomLinkSplit(num_val=2, num_test=2, disjoint_train_ratio=0.25,
                             edge_types=e, rev_edge_types=rev)(d):
        torch.testing.assert_close(g[e].edge_index, g[rev].edge_index.flip(0))
        assert g.validate()


def test_csv_alignment_empty_edges_and_rejections(tmp_path):
    pd = pytest.importorskip('pandas')
    m = recipe(tmp_path, 'references/custom_datasets.md', 'def load_node_csv')
    nodes = tmp_path / 'nodes.csv'
    pd.DataFrame({'id': ['001', '009'], 'f': [2., 5.]}).to_csv(nodes, index=False)
    x, ids = m.load_node_csv(nodes, 'id', {'f': m.IdentityEncoder()}, dtype={'id': str})
    assert ids == {'001': 0, '009': 1} and x.tolist() == [[2.], [5.]]
    edges = tmp_path / 'edges.csv'
    pd.DataFrame({'src': ['009'], 'dst': ['001']}).to_csv(edges, index=False)
    ei, _ = m.load_edge_csv(edges, 'src', ids, 'dst', ids, dtype=str)
    assert ei.tolist() == [[1], [0]]
    pd.DataFrame(columns=['src', 'dst']).to_csv(edges, index=False)
    ei, _ = m.load_edge_csv(edges, 'src', ids, 'dst', ids)
    assert ei.shape == (2, 0) and ei.dtype == torch.long
    pd.DataFrame({'src': ['unknown'], 'dst': ['001']}).to_csv(edges, index=False)
    with pytest.raises(ValueError, match='Unknown'):
        m.load_edge_csv(edges, 'src', ids, 'dst', ids, dtype=str)
    pd.DataFrame({'src': [None], 'dst': ['001']}).to_csv(edges, index=False)
    with pytest.raises(ValueError, match='Unknown'):
        m.load_edge_csv(edges, 'src', ids, 'dst', ids, dtype=str)
    pd.DataFrame({'id': [1, 1], 'f': [2, 3]}).to_csv(nodes, index=False)
    with pytest.raises(ValueError, match='unique'):
        m.load_node_csv(nodes, 'id')
    enc = m.GenresEncoder(['Drama', 'Comedy'])
    assert enc(pd.Series(['Drama|Comedy', 'Drama'])).tolist() == [[1., 1.], [0., 1.]]
    with pytest.raises(ValueError, match='Unknown genre'):
        enc(pd.Series(['unseen']))


def test_inmemory_and_disk_cache_filter_roundtrip(tmp_path, graph):
    root = tmp_path / 'memory'
    (root / 'raw').mkdir(parents=True)
    torch.save([graph.to_dict(), graph.to_dict()], root / 'raw/graphs.pt')
    m = recipe(tmp_path, 'references/custom_datasets.md', 'class MyDataset(')
    ds = m.MyDataset(str(root))
    assert len(ds) == 2 and ds[1].num_nodes == 31
    torch.testing.assert_close(ds[1].x, graph.x)
    root = tmp_path / 'disk'
    (root / 'raw').mkdir(parents=True)
    for i in range(3):
        g = graph.clone()
        g.keep = torch.tensor(i != 1)
        torch.save(g.to_dict(), root / f'raw/graph_{i}.pt')
    m = recipe(tmp_path, 'references/custom_datasets.md', 'class LargeDataset(')
    ds = m.LargeDataset(str(root), pre_filter=lambda g: bool(g.keep))
    assert len(ds) == 2 and ds.files == ['data_0.pt', 'data_1.pt']
    torch.testing.assert_close(ds[1].edge_index, graph.edge_index)
    (root / 'processed/data_1.pt').unlink()
    with pytest.raises(FileNotFoundError, match='Processed graph'):
        m.LargeDataset(str(root))


def test_conversions_and_isolate_preservation():
    nx = pytest.importorskip('networkx')
    from scipy.sparse import coo_matrix
    from torch_geometric.utils import from_networkx, from_scipy_sparse_matrix
    g = nx.Graph()
    g.add_node('isolated', feature=[1., 0.])
    g.add_node('a', feature=[0., 1.])
    g.add_node('b', feature=[1., 1.])
    g.add_edge('a', 'b', weight=0.)
    d = from_networkx(g, group_node_attrs=['feature'], group_edge_attrs=['weight'])
    assert d.num_nodes == 3 and pairs(d.edge_index) == {(1, 2), (2, 1)}
    assert d.edge_attr.shape == (2, 1) and d.x.shape == (3, 2)
    ei, ew = from_scipy_sparse_matrix(coo_matrix(([0., 2.], ([0, 1], [1, 2])), shape=(4, 4)))
    assert ei.shape == (2, 2) and ew.tolist() == [0., 2.]


def test_neighbor_and_link_sampler_contracts(graph):
    pytest.importorskip('pyg_lib')
    from torch_geometric.loader import NeighborLoader, LinkNeighborLoader
    loader = NeighborLoader(graph, input_nodes=torch.tensor([2, 4]),
                            num_neighbors=[2, 2], batch_size=2, shuffle=False)
    b = next(iter(loader))
    assert b.batch_size == 2 and b.n_id[:2].tolist() == [2, 4]
    assert b.validate() and b.edge_index.max() < b.num_nodes
    train, _, _ = split(graph)
    b = next(iter(LinkNeighborLoader(train, num_neighbors=[2, 2],
             edge_label_index=train.edge_label_index, edge_label=train.edge_label,
             neg_sampling=None, batch_size=4)))
    torch.testing.assert_close(b.n_id[b.edge_label_index], train.edge_label_index[:, :4])
    torch.testing.assert_close(b.edge_label, train.edge_label[:4])


def test_dynamic_knn_does_not_cross_graphs(tmp_path):
    pytest.importorskip('pyg_lib')
    m = recipe(tmp_path, 'references/message_passing.md', 'class EdgeConv(')
    d = recipe(tmp_path, 'references/message_passing.md', 'class DynamicEdgeConv(', vars(m))
    x = torch.tensor([[0.], [1.], [2.], [0.1], [1.1], [2.1]])
    batch = torch.tensor([0, 0, 0, 1, 1, 1])
    e = d.knn_graph(x, 1, batch, loop=False)
    assert torch.equal(batch[e[0]], batch[e[1]])
    assert d.DynamicEdgeConv(1, 3, k=1)(x, batch).shape == (6, 3)
    from torch_geometric.transforms import KNNGraph
    assert KNNGraph(k=2)(Data(pos=torch.randn(7, 3))).edge_index.shape == (2, 14)


def test_gnn_explainer_pgexplainer_and_metrics(tmp_path, graph):
    from torch_geometric.explain import Explainer, GNNExplainer, PGExplainer
    from torch_geometric.explain import unfaithfulness, fidelity
    m = recipe(tmp_path, 'SKILL.md', 'class GCN(')
    model = m.GCN(4, 8, 3)
    config = dict(mode='multiclass_classification', task_level='node', return_type='raw')
    explainer = Explainer(model, GNNExplainer(epochs=2), 'model', config,
                          node_mask_type='attributes', edge_mask_type='object')
    e = explainer(graph.x, graph.edge_index, index=2)
    assert e.node_mask.shape == (31, 4) and e.edge_mask.shape == (60,)
    assert math.isfinite(unfaithfulness(explainer, e))
    assert len(fidelity(explainer, e)) == 2
    model.eval()
    p = Explainer(model, PGExplainer(epochs=2), 'phenomenon', config, edge_mask_type='object')
    for epoch in range(2):
        assert math.isfinite(p.algorithm.train(epoch, model, graph.x, graph.edge_index,
                                               target=graph.y, index=2))
    assert p(graph.x, graph.edge_index, target=graph.y, index=2).edge_mask.shape == (60,)


def test_heterogeneous_captum_output_wrapper(tmp_path, hetero):
    pytest.importorskip('captum')
    from torch_geometric.explain import Explainer, CaptumExplainer
    m = recipe(tmp_path, 'references/heterogeneous.md', 'class GNN(')
    model = to_hetero(m.GNN(8, 3), hetero.metadata())
    model(hetero.x_dict, hetero.edge_index_dict)
    wrapper = recipe(tmp_path, 'references/explainability.md', 'class PaperOutput(').PaperOutput(model)
    ex = Explainer(wrapper, CaptumExplainer('IntegratedGradients', n_steps=3), 'model',
                   dict(mode='multiclass_classification', task_level='node', return_type='raw'),
                   node_mask_type='attributes', edge_mask_type='object')
    e = ex(hetero.x_dict, hetero.edge_index_dict, index=1)
    assert e.node_mask_dict['paper'].shape == (6, 4)
    assert set(e.edge_mask_dict) == set(hetero.edge_types)


def test_lightning_namespace_and_full_batch(graph):
    pytest.importorskip('lightning')
    from torch_geometric.data.lightning import LightningNodeData, LightningLinkData, LightningDataset
    dm = LightningNodeData(graph, input_train_nodes=torch.arange(10), loader='full')
    assert next(iter(dm.train_dataloader())).num_nodes == graph.num_nodes
    assert LightningLinkData and LightningDataset


def test_compile_eager_parity(graph):
    from torch_geometric.nn import GraphSAGE
    model = GraphSAGE(4, 8, num_layers=2, out_channels=3).eval()
    compiled = torch.compile(model, backend='eager', dynamic=True)
    torch.testing.assert_close(compiled(graph.x, graph.edge_index), model(graph.x, graph.edge_index))


def test_listed_layers_and_transforms(graph):
    from torch_geometric.nn import GATConv, GATv2Conv, GINConv, TransformerConv, RGCNConv
    from torch_geometric.nn import GraphSAGE, GCN, GAT, GIN
    from torch_geometric.transforms import NormalizeFeatures, AddSelfLoops, RandomJitter, Compose
    for cls in [GATConv, GATv2Conv, TransformerConv, SAGEConv]:
        assert cls(4, 8)(graph.x, graph.edge_index).shape == (31, 8)
    assert GINConv(torch.nn.Linear(4, 8))(graph.x, graph.edge_index).shape == (31, 8)
    relation = torch.arange(graph.num_edges) % 2
    assert RGCNConv(4, 8, num_relations=2)(graph.x, graph.edge_index, relation).shape == (31, 8)
    for cls in [GraphSAGE, GCN, GAT, GIN]:
        assert cls(4, 8, num_layers=2, out_channels=3)(graph.x, graph.edge_index).shape == (31, 3)
    d = NormalizeFeatures()(Data(x=torch.tensor([[2., 3.], [2., 2.]])))
    torch.testing.assert_close(d.x, torch.tensor([[0., 1.], [0., 0.]]))
    d = Compose([AddSelfLoops(), RandomJitter(0.01)])(Data(
        x=graph.x, edge_index=graph.edge_index, pos=torch.zeros(31, 3)))
    assert d.num_edges == graph.num_edges + 31 and d.pos.abs().max() <= 0.01


def test_attention_and_visualization_outputs(tmp_path, graph):
    from torch_geometric.nn import GAT
    from torch_geometric.explain import Explainer, AttentionExplainer, GNNExplainer
    from torch_geometric.explain import characterization_score
    model = GAT(4, 8, num_layers=2, out_channels=3)
    config = dict(mode='multiclass_classification', task_level='node', return_type='raw')
    a = Explainer(model, AttentionExplainer(), 'model', config, edge_mask_type='object')
    assert a(graph.x, graph.edge_index, index=2).edge_mask.shape == (graph.num_edges,)
    e = Explainer(model, GNNExplainer(epochs=2), 'model', config,
                   node_mask_type='attributes', edge_mask_type='object')(graph.x, graph.edge_index, index=2)
    pytest.importorskip('matplotlib')
    e.visualize_graph(path=str(tmp_path / 'graph.png'), backend='networkx')
    e.visualize_feature_importance(path=str(tmp_path / 'features.png'), top_k=4)
    assert (tmp_path / 'graph.png').stat().st_size > 0
    assert (tmp_path / 'features.png').stat().st_size > 0
    assert math.isfinite(characterization_score(0.8, 0.2))
