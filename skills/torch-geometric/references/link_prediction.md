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
    add_negative_train_samples=True,   # Fixed negatives, excluded from known positives
    disjoint_train_ratio=0.2, # Supervision positives excluded from train messages
    neg_sampling_ratio=1.0,   # 1 negative per positive edge
)
train_data, val_data, test_data = transform(data)
```

For an unlabeled binary graph, each split has `edge_label_index` of shape `[2, E_label]` and `edge_label` of shape `[E_label]` (`1` observed, `0` sampled absent). This example uses fixed negatives generated against the original graph. `disjoint_train_ratio=0.2` reserves part of the training positives for supervision; the remainder supplies training messages.

`edge_index` differs by split: training uses its message subset, validation uses **all training positives**, and test uses **training plus validation positives**. The last behavior is PyG's default evaluation protocol, not a universal no-leakage guarantee. If validation edges would be unavailable at prediction time, explicitly use a train-only message graph for both evaluations. Never use test positives for training or checkpoint selection. For temporal prediction, construct time-respecting splits instead of this random transform.

An undirected input must have both edge directions; `is_undirected=True` keeps positive reverse pairs together but returns one orientation per positive label. Bipartite relations need paired `edge_types`/`rev_edge_types` instead. If there are too few nonedges, the realized negative ratio shrinks: verify both label classes before AUC. Existing categorical edge labels are shifted to reserve zero for negatives; binary BCE here assumes no such labels. Continuous ratings are regression targets, not valid `RandomLinkSplit` class labels.

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
model = LinkEncoder(data.num_features, 128, 64)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

def train(train_data):
    model.train()
    optimizer.zero_grad()
    z = model(train_data.x, train_data.edge_index)
    edge_label_index = train_data.edge_label_index
    edge_label = train_data.edge_label.to(device=z.device, dtype=z.dtype)

    # Decode and compute loss
    pred = decode(z, edge_label_index)
    loss = F.binary_cross_entropy_with_logits(pred, edge_label)
    loss.backward()
    optimizer.step()
    return loss.item()

@torch.no_grad()
def test(data_split):
    model.eval()
    z = model(data_split.x, data_split.edge_index)
    pred = decode(z, data_split.edge_label_index).sigmoid()
    # Report the candidate/negative distribution alongside ranking metrics.
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(data_split.edge_label.cpu(), pred.cpu())
```

## Graph Autoencoders (GAE / VGAE)

PyG provides `GAE` and `VGAE` for graph reconstruction/link prediction. Separate positive and negative **edge columns**, not the source and destination rows:

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

# GAE wraps the encoder with reconstruction and evaluation helpers
model = GAE(Encoder(data.num_features, 64))
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

def train():
    model.train()
    optimizer.zero_grad()
    z = model.encode(train_data.x, train_data.edge_index)
    pos = train_data.edge_label_index[:, train_data.edge_label == 1]
    neg = train_data.edge_label_index[:, train_data.edge_label == 0]
    loss = model.recon_loss(z, pos, neg)
    # For VGAE, add KL divergence:
    # loss = loss + (1 / data.num_nodes) * model.kl_loss()
    loss.backward()
    optimizer.step()
    return loss.item()

@torch.no_grad()
def test(data_split):
    model.eval()
    z = model.encode(data_split.x, data_split.edge_index)
    pos = data_split.edge_label_index[:, data_split.edge_label == 1]
    neg = data_split.edge_label_index[:, data_split.edge_label == 0]
    return model.test(z, pos, neg)  # (ROC-AUC, average precision); each index is [2,E]
```

Do not call `recon_loss` on mixed positive/negative labels as if all were edges. Its default negative sampler only knows the supplied positives; pass explicit negatives under your chosen evaluation protocol. For VGAE, the encoder must return `mu` and `logstd` instead of a single embedding. Use the VGAE-specific encoder pattern:

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

For large graphs, `LinkNeighborLoader` samples around supervision edges and requires a compatible sampling extension. This illustrative example reuses fixed labels from the disjoint split, so it adds no further negatives:

```python
from torch_geometric.loader import LinkNeighborLoader

train_loader = LinkNeighborLoader(
    data=train_data,
    num_neighbors=[20, 10],         # Sample neighbors per hop
    edge_label_index=train_data.edge_label_index,
    edge_label=train_data.edge_label,
    batch_size=128,                  # Number of supervision edges per batch
    neg_sampling=None,              # Already have positive and negative labels
    shuffle=True,
)

for batch in train_loader:
    # batch.edge_label_index: supervision edges (pos + neg)
    # batch.edge_label: 1 for positive, 0 for negative
    # batch.edge_index: message-passing edges (from neighbor sampling)
    z = encoder(batch.x, batch.edge_index)  # encoder = LinkEncoder(...)
    pred = decode(z, batch.edge_label_index)
    loss = F.binary_cross_entropy_with_logits(pred, batch.edge_label)
```

`LinkNeighborLoader` does not remove supervision edges from its input graph. Keep them disjoint yourself (as above). If choosing dynamic sampling instead, use `NegativeSampling(mode="binary", amount=1.0)` from `torch_geometric.sampler`, do not double-sample existing negatives, and note that loader sampling is approximate and can produce false negatives. Even `negative_sampling(train_data.edge_index)` may select held-out true edges, or disjoint training positives omitted from that adjacency. Exact known-positive exclusion needs the specified candidate universe; unavailable future positives cannot be used as an oracle.

## Heterogeneous Link Prediction

For heterogeneous binary relations (e.g., observed user-item interactions), create reverse edges before splitting and pair them below. Remove any copied rating/target attributes from reverse edges, and keep regression ratings in a separate supervised pipeline:

```python
transform = T.RandomLinkSplit(
    num_val=0.1,
    num_test=0.1,
    neg_sampling_ratio=1.0,
    add_negative_train_samples=True,
    disjoint_train_ratio=0.2,
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
- **Average Precision (AP)**: Recall-increment-weighted precision; not trapezoidal PR area
- **Hits@K**: Rank-based metric whose candidate set, filtering and tie handling must follow the benchmark
- **MRR**: Mean reciprocal rank of positive edges

```python
from sklearn.metrics import roc_auc_score, average_precision_score

auc = roc_auc_score(edge_label.cpu(), pred.cpu())
ap = average_precision_score(edge_label.cpu(), pred.cpu())
```

## Common Pitfalls

1. **Data leakage**: Validate actual edge sets and reverse relations, including derived edge features. Distinguish training message/supervision overlap from validation/test leakage.
2. **Negative sampling quality**: Absent edges are not verified biological/physical negatives. Random or hard negatives define different tasks and can change AUC/AP substantially.
3. **Undirected graphs**: Set `is_undirected=True` in `RandomLinkSplit` — otherwise it will treat each direction independently and leak information.
4. **Decoding**: Dot products and DistMult are symmetric, so they cannot express arbitrary directed relations. Use an appropriate ordered/relational decoder; sigmoid scores are not automatically calibrated probabilities.

Sources: [RandomLinkSplit](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.transforms.RandomLinkSplit.html), [loaders](https://pytorch-geometric.readthedocs.io/en/latest/modules/loader.html), [GAE](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.models.GAE.html).
