---
name: torch-geometric
description: PyTorch Geometric (PyG) for graph neural networks — node/link/graph classification, message passing (GCN, GAT, GraphSAGE, GIN), heterogeneous graphs, neighbor sampling, and custom datasets. Use when working with torch_geometric, not for general NetworkX analytics or non-graph PyTorch models.
license: MIT license
compatibility: Requires Python 3.10+, PyTorch 2.6+, and torch-geometric 2.7.x. Optional extension wheels (pyg-lib, torch-scatter, torch-sparse, torch-cluster) must match your PyTorch/CUDA build from https://data.pyg.org/whl.
metadata: {"version": "1.1", "skill-author": "K-Dense Inc."}
---

# PyTorch Geometric (PyG)

PyG is the standard library for Graph Neural Networks built on PyTorch. It provides data structures for graphs, 60+ GNN layer implementations, scalable mini-batch training, and support for heterogeneous graphs.

## Installation

Tested against **torch-geometric 2.7.x** (Oct 2025). Requires **Python 3.10+** and **PyTorch 2.6+**.

```bash
# 1. Install PyTorch first (match your CUDA/CPU setup — see https://pytorch.org/get-started/locally/)
uv pip install torch

# 2. Core PyG (no extension wheels required for basic usage)
uv pip install torch_geometric
```

Optional accelerated ops (`pyg-lib`, `torch-scatter`, `torch-sparse`, `torch-cluster`) are **not required** for basic PyG usage (since PyG 2.3). Install version-matched wheels from the [PyG wheel index](https://data.pyg.org/whl) after checking your PyTorch and CUDA versions:

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda)"
# Then install wheels for your torch+CUDA combo, e.g.:
uv pip install pyg-lib torch-scatter torch-sparse torch-cluster \
  -f https://data.pyg.org/whl/torch-2.8.0+cu128.html
```

Check your version:

```python
import torch_geometric
print(torch_geometric.__version__)
```

**Conda:** the `pyg` conda channel is no longer maintained for PyTorch >2.5 — use `uv pip install` and the wheel index above instead.

### PyG 2.7 notes

PyG 2.7 dropped Python 3.9 and PyTorch ≤2.5. See the [2.7.0 release notes](https://github.com/pyg-team/pytorch_geometric/releases/tag/2.7.0) for PyTorch 2.6–2.8 compatibility tables. `torch_geometric.distributed` is deprecated — use standard `torch.distributed` DDP (see `references/scaling.md`).

## Core Concepts

### Graph Data: `Data` and `HeteroData`

A graph lives in a `Data` object. The key attributes:

```python
from torch_geometric.data import Data

data = Data(
    x=node_features,          # [num_nodes, num_node_features]
    edge_index=edge_index,     # [2, num_edges] — COO format, dtype=torch.long
    edge_attr=edge_features,   # [num_edges, num_edge_features]
    y=labels,                  # node-level [num_nodes, *] or graph-level [1, *]
    pos=positions,             # [num_nodes, num_dimensions] (for point clouds/spatial)
)
```

**`edge_index` format is critical**: it's a `[2, num_edges]` tensor where `edge_index[0]` = source nodes, `edge_index[1]` = target nodes. It is NOT a list of tuples. If you have edge pairs as rows, transpose and call `.contiguous()`:

```python
# If edges are [[src1, dst1], [src2, dst2], ...] — transpose first:
edge_index = edge_pairs.t().contiguous()
```

For undirected graphs, include both directions: edge (0,1) needs both `[0,1]` and `[1,0]` in edge_index.

For heterogeneous graphs, use `HeteroData` — see the Heterogeneous Graphs section below.

### Datasets

PyG bundles many standard datasets that auto-download and preprocess:

```python
from torch_geometric.datasets import Planetoid, TUDataset

# Single-graph node classification (Cora, Citeseer, Pubmed)
dataset = Planetoid(root='./data', name='Cora')
data = dataset[0]  # single graph with train/val/test masks

# Multi-graph classification (ENZYMES, MUTAG, IMDB-BINARY, etc.)
dataset = TUDataset(root='./data', name='ENZYMES')
# dataset[0], dataset[1], ... are individual graphs
```

Common datasets by task:
- **Node classification**: Planetoid (Cora/Citeseer/Pubmed), OGB (ogbn-arxiv, ogbn-products, ogbn-mag)
- **Graph classification**: TUDataset (MUTAG, ENZYMES, PROTEINS, IMDB-BINARY), OGB (ogbg-molhiv)
- **Link prediction**: OGB (ogbl-collab, ogbl-citation2)
- **Molecular**: QM7, QM9, MoleculeNet
- **Point cloud/mesh**: ShapeNet, ModelNet10/40, FAUST

### Transforms

Transforms preprocess or augment graph data, analogous to torchvision transforms:

```python
import torch_geometric.transforms as T

# Common transforms
T.NormalizeFeatures()    # Row-normalize node features to sum to 1
T.ToUndirected()         # Add reverse edges to make graph undirected
T.AddSelfLoops()         # Add self-loop edges
T.KNNGraph(k=6)          # Build k-NN graph from point cloud positions
T.RandomJitter(0.01)     # Random noise augmentation on positions
T.Compose([...])         # Chain multiple transforms

# Apply as pre_transform (once, saved to disk) or transform (every access)
dataset = ShapeNet(root='./data', pre_transform=T.KNNGraph(k=6),
                   transform=T.RandomJitter(0.01))
```

## Building GNN Models

### Quick Start: Using Built-in Layers

The fastest way to build a GNN — stack conv layers from `torch_geometric.nn`:

```python
import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv

class GCN(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super().__init__()
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.conv2(x, edge_index)
        return x
```

**Important**: PyG conv layers do NOT include activation functions — apply them yourself after each layer. This is by design for flexibility.

### Choosing a Conv Layer

Pick based on your task and graph structure:

| Layer | Best for | Key idea |
|-------|----------|----------|
| `GCNConv` | Homogeneous, semi-supervised node classification | Spectral-inspired, degree-normalized aggregation |
| `GATConv` / `GATv2Conv` | When neighbor importance varies | Attention-weighted messages |
| `SAGEConv` | Large graphs, inductive settings | Sampling-friendly, learnable aggregation |
| `GINConv` | Graph classification, maximizing expressiveness | As powerful as WL test |
| `TransformerConv` | Rich edge features, complex interactions | Multi-head attention with edge features |
| `EdgeConv` | Point clouds, dynamic graphs | MLP on edge features (x_i, x_j - x_i) |
| `RGCNConv` | Heterogeneous with many relation types | Relation-specific weight matrices |
| `HGTConv` | Heterogeneous graphs | Type-specific attention |

All conv layers accept `(x, edge_index)` at minimum. Many also accept `edge_attr` for edge features.

### Lazy Initialization

Use `-1` for input channels to let PyG infer dimensions automatically — especially useful for heterogeneous models:

```python
conv = SAGEConv((-1, -1), 64)  # Input dims inferred on first forward pass
# Initialize lazy modules:
with torch.no_grad():
    out = model(data.x, data.edge_index)
```

### High-Level Model APIs

For common architectures, PyG provides ready-made model classes:

```python
from torch_geometric.nn import GraphSAGE, GCN, GAT, GIN

model = GraphSAGE(
    in_channels=dataset.num_features,
    hidden_channels=64,
    out_channels=dataset.num_classes,
    num_layers=2,
)
```

### Custom Layers via MessagePassing

To implement a novel GNN layer, subclass `MessagePassing`. The framework is:

1. `propagate()` orchestrates the message passing
2. `message()` defines what info flows along each edge (the phi function)
3. `aggregate()` combines messages at each node (sum/mean/max)
4. `update()` transforms the aggregated result (the gamma function)

```python
from torch_geometric.nn import MessagePassing
from torch_geometric.utils import add_self_loops, degree

class MyConv(MessagePassing):
    def __init__(self, in_channels, out_channels):
        super().__init__(aggr='add')  # "add", "mean", or "max"
        self.lin = torch.nn.Linear(in_channels, out_channels)

    def forward(self, x, edge_index):
        # Pre-processing before message passing
        x = self.lin(x)
        # Start message passing
        return self.propagate(edge_index, x=x)

    def message(self, x_j):
        # x_j: features of source nodes for each edge [num_edges, features]
        # The _j suffix auto-indexes source nodes, _i indexes target nodes
        return x_j
```

**The `_i` / `_j` convention**: any tensor passed to `propagate()` can be auto-indexed by appending `_i` (target/central node) or `_j` (source/neighbor node) in the `message()` signature. So if you pass `x=...` to propagate, you can access `x_i` and `x_j` in message().

Read `references/message_passing.md` for the full GCN and EdgeConv implementation examples.

## Task-Specific Patterns

### Node Classification

```python
# Full-batch training on a single graph (e.g., Cora)
model.train()
for epoch in range(200):
    optimizer.zero_grad()
    out = model(data.x, data.edge_index)
    loss = F.cross_entropy(out[data.train_mask], data.y[data.train_mask])
    loss.backward()
    optimizer.step()

# Evaluation — train(False) puts the model in inference mode (disables dropout/BN)
model.train(False)
pred = model(data.x, data.edge_index).argmax(dim=1)
acc = (pred[data.test_mask] == data.y[data.test_mask]).float().mean()
```

### Graph Classification

Multiple graphs — use `DataLoader` for mini-batching and global pooling to get graph-level representations:

```python
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GCNConv, global_mean_pool

loader = DataLoader(dataset, batch_size=32, shuffle=True)

class GraphClassifier(torch.nn.Module):
    def __init__(self, in_ch, hidden_ch, out_ch):
        super().__init__()
        self.conv1 = GCNConv(in_ch, hidden_ch)
        self.conv2 = GCNConv(hidden_ch, hidden_ch)
        self.lin = torch.nn.Linear(hidden_ch, out_ch)

    def forward(self, x, edge_index, batch):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index).relu()
        x = global_mean_pool(x, batch)  # [num_graphs_in_batch, hidden_ch]
        return self.lin(x)

# Training loop
for data in loader:
    out = model(data.x, data.edge_index, data.batch)
    loss = F.cross_entropy(out, data.y)
```

PyG's `DataLoader` batches multiple graphs by creating block-diagonal adjacency matrices. The `batch` tensor maps each node to its graph index. Pooling ops (`global_mean_pool`, `global_max_pool`, `global_add_pool`) use this to aggregate per-graph.

### Link Prediction

Split edges into train/val/test, use negative sampling:

```python
from torch_geometric.transforms import RandomLinkSplit

transform = RandomLinkSplit(
    num_val=0.1,
    num_test=0.1,
    is_undirected=True,
    add_negative_train_samples=False,
)
train_data, val_data, test_data = transform(data)

# Encode nodes, then score edges
z = model.encode(train_data.x, train_data.edge_index)
# Positive edges
pos_score = (z[train_data.edge_label_index[0]] * z[train_data.edge_label_index[1]]).sum(dim=1)
```

Read `references/link_prediction.md` for the complete link prediction guide: GAE/VGAE autoencoders, full training loops, LinkNeighborLoader for large graphs, heterogeneous link prediction, and evaluation metrics.

## Scaling to Large Graphs

For graphs that don't fit in GPU memory, use neighbor sampling via `NeighborLoader`:

```python
from torch_geometric.loader import NeighborLoader

train_loader = NeighborLoader(
    data,
    num_neighbors=[15, 10],     # Sample 15 neighbors in hop 1, 10 in hop 2
    batch_size=128,              # Number of seed nodes per batch
    input_nodes=data.train_mask, # Which nodes to sample from
    shuffle=True,
)

for batch in train_loader:
    batch = batch.to(device)
    out = model(batch.x, batch.edge_index)
    # Only use first batch_size nodes for loss (these are the seed nodes)
    loss = F.cross_entropy(out[:batch.batch_size], batch.y[:batch.batch_size])
```

**Key points about NeighborLoader**:
- `num_neighbors` list length should match GNN depth (number of message passing layers)
- Seed nodes are always the first `batch.batch_size` nodes in the output
- `batch.n_id` maps relabeled indices back to original node IDs
- Works for both `Data` and `HeteroData`
- For link prediction, use `LinkNeighborLoader` instead
- Sampling more than 2-3 hops is generally infeasible (exponential blowup)

Other scalability options: `ClusterLoader` (ClusterGCN), `GraphSAINTSampler`, `ShaDowKHopSampler`. For multi-GPU training, DDP, PyTorch Lightning integration, and `torch.compile` support, read `references/scaling.md`.

## Heterogeneous Graphs

For graphs with multiple node and edge types (social networks, knowledge graphs, recommendation):

```python
from torch_geometric.data import HeteroData

data = HeteroData()

# Node features — indexed by node type string
data['user'].x = torch.randn(1000, 64)
data['movie'].x = torch.randn(500, 128)

# Edge indices — indexed by (src_type, edge_type, dst_type) triplet
data['user', 'rates', 'movie'].edge_index = torch.randint(0, 500, (2, 3000))
data['user', 'follows', 'user'].edge_index = torch.randint(0, 1000, (2, 5000))

# Access convenience dicts
data.x_dict        # {'user': tensor, 'movie': tensor}
data.edge_index_dict  # {('user','rates','movie'): tensor, ...}
data.metadata()    # ([node_types], [edge_types])
```

### Three ways to build heterogeneous GNNs

**1. Auto-convert with `to_hetero()`** — write a homogeneous model, convert automatically:

```python
from torch_geometric.nn import SAGEConv, to_hetero

class GNN(torch.nn.Module):
    def __init__(self, hidden_channels, out_channels):
        super().__init__()
        self.conv1 = SAGEConv((-1, -1), hidden_channels)
        self.conv2 = SAGEConv((-1, -1), out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index)
        return x

model = GNN(64, dataset.num_classes)
model = to_hetero(model, data.metadata(), aggr='sum')

# Now accepts dicts:
out = model(data.x_dict, data.edge_index_dict)
```

Use `(-1, -1)` for bipartite input channels (source, target may differ). Lazy init handles the rest.

**2. `HeteroConv` wrapper** — different conv per edge type:

```python
from torch_geometric.nn import HeteroConv, GCNConv, SAGEConv, GATConv

conv = HeteroConv({
    ('paper', 'cites', 'paper'): GCNConv(-1, 64),
    ('author', 'writes', 'paper'): SAGEConv((-1, -1), 64),
    ('paper', 'rev_writes', 'author'): GATConv((-1, -1), 64, add_self_loops=False),
}, aggr='sum')
```

**3. Native heterogeneous operators** like `HGTConv`:

```python
from torch_geometric.nn import HGTConv
conv = HGTConv(hidden_channels, hidden_channels, data.metadata(), num_heads=4)
```

**Important for heterogeneous graphs**:
- Use `T.ToUndirected()` to add reverse edge types for bidirectional message flow
- Disable `add_self_loops` in bipartite conv layers (different source/dest types) — use skip connections instead: `conv(x, edge_index) + lin(x)`
- For NeighborLoader on HeteroData, specify `input_nodes` as `('node_type', mask)` tuple
- `num_neighbors` can be a dict keyed by edge type for fine-grained control

Read `references/heterogeneous.md` for complete examples including training loops and NeighborLoader usage with heterogeneous graphs.

## Custom Datasets

For loading your own data into PyG:

- **Quick (no class needed)**: Create `Data` objects directly and pass a list to `DataLoader`
- **Reusable (fits in RAM)**: Subclass `InMemoryDataset` — override `raw_file_names`, `processed_file_names`, `download()`, `process()`
- **Large (disk-backed)**: Subclass `Dataset` — also override `len()` and `get()`
- **From CSV**: Load node/edge tables with pandas, build mappings to consecutive indices, assemble into `Data` or `HeteroData`
- **From NetworkX**: `from_networkx(G)` converts a NetworkX graph directly
- **From scipy sparse**: `from_scipy_sparse_matrix(adj)` extracts edge_index

Read `references/custom_datasets.md` for complete examples with all patterns, CSV loading with encoders, and the MovieLens walkthrough.

## Explainability

PyG provides `torch_geometric.explain` for interpreting GNN predictions:

```python
from torch_geometric.explain import Explainer, GNNExplainer

explainer = Explainer(
    model=model,
    algorithm=GNNExplainer(epochs=200),
    explanation_type='model',
    node_mask_type='attributes',
    edge_mask_type='object',
    model_config=dict(
        mode='multiclass_classification',
        task_level='node',
        return_type='log_probs',
    ),
)

explanation = explainer(data.x, data.edge_index, index=10)
explanation.visualize_graph()           # Important subgraph
explanation.visualize_feature_importance(top_k=10)  # Feature importance
```

Available algorithms: `GNNExplainer` (optimization-based), `PGExplainer` (parametric, trained), `CaptumExplainer` (gradient-based via Captum), `AttentionExplainer` (attention weights). Works for both homogeneous and heterogeneous graphs.

Read `references/explainability.md` for all algorithms, heterogeneous explanations, evaluation metrics, and PGExplainer training.

## Common Pitfalls

1. **edge_index shape**: Must be `[2, num_edges]`, not `[num_edges, 2]`. Transpose if needed.
2. **Forgetting activations**: Conv layers don't include ReLU/etc — add them manually.
3. **Self-loops in hetero bipartite**: Don't use `add_self_loops=True` when source and dest node types differ. Use skip connections instead.
4. **NeighborLoader slicing**: Only the first `batch.batch_size` nodes are your seed nodes. Slice predictions and labels accordingly.
5. **Undirected graphs**: If your graph is undirected, include edges in both directions in `edge_index`, or use `T.ToUndirected()`.
6. **Lazy init**: Models with `-1` input channels need one forward pass with `torch.no_grad()` before training to initialize parameters.
7. **Global pooling for graph tasks**: Use `global_mean_pool(x, batch)` (not manual reshape) to aggregate node features to graph-level.
8. **num_neighbors alignment**: Keep `len(num_neighbors)` equal to the number of GNN layers. More hops than layers wastes compute; fewer means wasted model capacity.
