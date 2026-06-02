# Link Prediction — Full Reference

Link prediction is the task of predicting missing or future edges in a graph. Common applications: social network friend suggestion, knowledge graph completion, drug-target interaction.

## Edge Splitting

Use `RandomLinkSplit` to split edges into train/val/test while maintaining graph structure:

```python
import torch_geometric.transforms as T

transform = T.RandomLinkSplit(
    num_val=0.1,              # 10% of edges for validation
    num_test=0.1,             # 10% of edges for test
    is_undirected=True,       # Set True for undirected graphs
    add_negative_train_samples=False,  # Generate negatives on-the-fly during training
    neg_sampling_ratio=1.0,   # 1 negative per positive edge
)
train_data, val_data, test_data = transform(data)
```

After splitting, each split contains:
- `edge_index`: message-passing edges (train edges only — no data leakage)
- `edge_label_index`: supervision edges `[2, num_supervision_edges]` — the edges to predict
- `edge_label`: binary labels — 1 for positive (real) edges, 0 for negative (fake) edges

For the training split with `add_negative_train_samples=False`, only positive edges are in `edge_label_index` and negatives are sampled during training. Val/test splits always include both positive and negative edges.

## Encoder-Decoder Pattern

The standard approach:
1. **Encode** — use a GNN to produce node embeddings from the message-passing edges
2. **Decode** — score candidate edges using the node embeddings

```python
import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv

class LinkEncoder(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super().__init__()
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index)
        return x

def decode(z, edge_label_index):
    """Dot-product decoder: score = z_src . z_dst for each edge."""
    src, dst = edge_label_index
    return (z[src] * z[dst]).sum(dim=1)
```

## Full-Batch Training Loop

```python
from torch_geometric.utils import negative_sampling

model = LinkEncoder(data.num_features, 128, 64)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

def train(train_data):
    model.train()
    optimizer.zero_grad()

    # Encode using message-passing edges only
    z = model(train_data.x, train_data.edge_index)

    # Sample negative edges for this batch
    neg_edge_index = negative_sampling(
        edge_index=train_data.edge_index,
        num_nodes=train_data.num_nodes,
        num_neg_samples=train_data.edge_label_index.size(1),
    )

    # Combine positive and negative supervision edges
    edge_label_index = torch.cat([train_data.edge_label_index, neg_edge_index], dim=1)
    edge_label = torch.cat([
        torch.ones(train_data.edge_label_index.size(1)),
        torch.zeros(neg_edge_index.size(1)),
    ])

    # Decode and compute loss
    pred = decode(z, edge_label_index)
    loss = F.binary_cross_entropy_with_logits(pred, edge_label)
    loss.backward()
    optimizer.step()
    return loss.item()

@torch.no_grad()
def test(data_split):
    model.train(False)  # Inference mode (disables dropout; not Python eval)
    z = model(data_split.x, data_split.edge_index)
    pred = decode(z, data_split.edge_label_index).sigmoid()
    # AUC is the standard metric for link prediction
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(data_split.edge_label.cpu(), pred.cpu())
```

## Graph Autoencoders (GAE / VGAE)

PyG provides `GAE` and `VGAE` for unsupervised link prediction:

```python
from torch_geometric.nn import GAE, VGAE, GCNConv

class Encoder(torch.nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv1 = GCNConv(in_channels, 2 * out_channels)
        self.conv2 = GCNConv(2 * out_channels, out_channels)
        # For VGAE, also define conv_mu and conv_logstd

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        return self.conv2(x, edge_index)

# GAE wraps your encoder and provides train/test methods
model = GAE(Encoder(data.num_features, 64))
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

def train():
    model.train()
    optimizer.zero_grad()
    z = model.encode(train_data.x, train_data.edge_index)
    loss = model.recon_loss(z, train_data.edge_label_index)
    # For VGAE, add KL divergence:
    # loss = loss + (1 / data.num_nodes) * model.kl_loss()
    loss.backward()
    optimizer.step()
    return loss.item()

@torch.no_grad()
def test(data_split):
    model.train(False)  # Inference mode (disables dropout; not Python eval)
    z = model.encode(data_split.x, data_split.edge_index)
    return model.test(z, data_split.edge_label_index[0],  # positive edges
                         data_split.edge_label_index[1])   # negative edges
```

For VGAE, the encoder must return `mu` and `logstd` instead of a single embedding. Use the VGAE-specific encoder pattern:

```python
class VariationalEncoder(torch.nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv1 = GCNConv(in_channels, 2 * out_channels)
        self.conv_mu = GCNConv(2 * out_channels, out_channels)
        self.conv_logstd = GCNConv(2 * out_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        return self.conv_mu(x, edge_index), self.conv_logstd(x, edge_index)

model = VGAE(VariationalEncoder(data.num_features, 64))
```

## Mini-Batch Link Prediction with LinkNeighborLoader

For large graphs, use `LinkNeighborLoader` — it samples subgraphs around supervision edges:

```python
from torch_geometric.loader import LinkNeighborLoader

train_loader = LinkNeighborLoader(
    data=train_data,
    num_neighbors=[20, 10],         # Sample neighbors per hop
    edge_label_index=train_data.edge_label_index,
    edge_label=train_data.edge_label,
    batch_size=128,                  # Number of supervision edges per batch
    neg_sampling_ratio=1.0,          # 1 negative per positive
    shuffle=True,
)

for batch in train_loader:
    # batch.edge_label_index: supervision edges (pos + neg)
    # batch.edge_label: 1 for positive, 0 for negative
    # batch.edge_index: message-passing edges (from neighbor sampling)
    z = model(batch.x, batch.edge_index)
    pred = decode(z, batch.edge_label_index)
    loss = F.binary_cross_entropy_with_logits(pred, batch.edge_label)
```

## Heterogeneous Link Prediction

For heterogeneous graphs (e.g., user-item recommendation):

```python
transform = T.RandomLinkSplit(
    num_val=0.1,
    num_test=0.1,
    neg_sampling_ratio=1.0,
    add_negative_train_samples=False,
    edge_types=('user', 'rates', 'movie'),              # Which edge type to predict
    rev_edge_types=('movie', 'rev_rates', 'user'),       # Its reverse
)
train_data, val_data, test_data = transform(data)

# Supervision edges are in:
# train_data['user', 'rates', 'movie'].edge_label_index
# train_data['user', 'rates', 'movie'].edge_label
```

## Evaluation Metrics

- **AUC-ROC**: Standard metric — area under the ROC curve
- **Average Precision (AP)**: Area under the precision-recall curve
- **Hits@K**: Fraction of positive edges ranked in top K (used in knowledge graphs)
- **MRR**: Mean reciprocal rank of positive edges

```python
from sklearn.metrics import roc_auc_score, average_precision_score

auc = roc_auc_score(edge_label.cpu(), pred.cpu())
ap = average_precision_score(edge_label.cpu(), pred.cpu())
```

## Common Pitfalls

1. **Data leakage**: Never include val/test edges in the message-passing graph during training. `RandomLinkSplit` handles this correctly — `edge_index` in train_data only contains training edges.
2. **Negative sampling quality**: Using random negatives is standard but can be too easy. For harder negatives, sample from 2-hop neighbors.
3. **Undirected graphs**: Set `is_undirected=True` in `RandomLinkSplit` — otherwise it will treat each direction independently and leak information.
4. **Decoding**: Dot-product is simplest but not always best. Consider MLP decoders or DistMult for heterogeneous/knowledge graphs.
