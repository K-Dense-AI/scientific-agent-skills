# Custom graph datasets

Use explicit node IDs, tensor dtypes and label shapes. `Data.validate()` checks graph structure but cannot detect a feature row attached to the wrong biological entity. Preserve the original ID-to-row mapping and test it separately. Fit feature encoders on the training data when the evaluation protocol requires an inductive split.

## InMemoryDataset

This local example reads a list of tensor dictionaries from `root/raw/graphs.pt`; it performs no download. Each dictionary can contain `x`, `edge_index`, `y`, and an integer `num_nodes`. Create that file yourself from reviewed raw data before instantiating the class. Only load trusted artifacts, even when using restricted deserialization.

```python
import torch
from torch_geometric.data import Data, InMemoryDataset

class MyDataset(InMemoryDataset):
    def __init__(self, root, transform=None, pre_transform=None, pre_filter=None,
                 force_reload=False):
        super().__init__(root, transform, pre_transform, pre_filter,
                         force_reload=force_reload)
        self.load(self.processed_paths[0])

    @property
    def raw_file_names(self):
        return ['graphs.pt']

    @property
    def processed_file_names(self):
        return ['data.pt']

    def process(self):
        records = torch.load(self.raw_paths[0], weights_only=True, map_location='cpu')
        graphs = []
        for record in records:
            graph = Data.from_dict(record)
            graph.validate(raise_on_error=True)
            if self.pre_filter is not None and not self.pre_filter(graph):
                continue
            if self.pre_transform is not None:
                graph = self.pre_transform(graph)
            graph.validate(raise_on_error=True)
            graphs.append(graph)
        if not graphs:
            raise ValueError('No graphs remain after filtering')
        self.save(graphs, self.processed_paths[0])
```

`process()` is cached by `processed_file_names`; `transform` runs on access, `pre_transform` only during processing. Use a versioned cache or `force_reload=True` when raw files, feature vocabulary or preprocessing changes. `InMemoryDataset.save/load` is the current paired API; saved PyG objects are not interchangeable with an arbitrary tensor-only `torch.load` payload.

## Disk-backed Dataset

This example has one tensor dictionary per `raw/graph_*.pt`; graphs are loaded and processed one at a time. A manifest indexes only the graphs retained by `pre_filter`, avoiding gaps and a false hardcoded length. Save tensor dictionaries so current `torch.load(weights_only=True)` can read them without loading a pickled `Data` class.

```python
import json
from pathlib import Path
import torch
from torch_geometric.data import Data, Dataset

class LargeDataset(Dataset):
    def __init__(self, root, transform=None, pre_transform=None, pre_filter=None,
                 force_reload=False):
        super().__init__(root, transform, pre_transform, pre_filter,
                         force_reload=force_reload)
        self.files = json.loads(Path(self.processed_paths[0]).read_text())
        if any(not (Path(self.processed_dir) / name).is_file() for name in self.files):
            raise FileNotFoundError('Processed graph missing; rebuild this cache')

    @property
    def raw_file_names(self):
        names = sorted(p.name for p in Path(self.raw_dir).glob('graph_*.pt'))
        if not names:
            raise FileNotFoundError('Put tensor dictionaries in raw/graph_*.pt')
        return names

    @property
    def processed_file_names(self):
        return ['index.json']

    def process(self):
        files = []
        for raw_path in self.raw_paths:
            graph = Data.from_dict(torch.load(raw_path, weights_only=True,
                                              map_location='cpu'))
            graph.validate(raise_on_error=True)
            if self.pre_filter is not None and not self.pre_filter(graph):
                continue
            if self.pre_transform is not None:
                graph = self.pre_transform(graph)
            graph.validate(raise_on_error=True)
            name = f'data_{len(files)}.pt'
            torch.save(graph.to_dict(), Path(self.processed_dir) / name)
            files.append(name)
        Path(self.processed_paths[0]).write_text(json.dumps(files))

    def len(self):
        return len(self.files)

    def get(self, idx):
        record = torch.load(Path(self.processed_dir) / self.files[idx],
                            weights_only=True, map_location='cpu')
        return Data.from_dict(record)
```

`get()` returns an untransformed graph; public `dataset[idx]` applies `transform`. This is a local single-writer cache example, not a concurrent or transactional database. Rebuild/version the cache when source files change.

## CSV node/edge alignment

Use a node table with unique, non-null IDs for feature-bearing nodes. A repeated interaction table can supply a featureless node universe only after explicit deduplication. Preserve string identifiers and leading zeros through `dtype=` when needed.

```python
import pandas as pd
import torch

def load_node_csv(path, index_col, encoders=None, dtype=None):
    df = pd.read_csv(path, index_col=index_col, dtype=dtype)
    if df.index.hasnans or not df.index.is_unique:
        raise ValueError('Node IDs must be unique and non-null')
    mapping = {node_id: i for i, node_id in enumerate(df.index)}
    x = None
    if encoders:
        columns = [encoder(df[col]) for col, encoder in encoders.items()]
        if any(t.ndim != 2 or t.size(0) != len(df) for t in columns):
            raise ValueError('Every encoder must return [num_nodes, features]')
        x = torch.cat(columns, dim=-1)
    return x, mapping

def load_edge_csv(path, src_index_col, src_mapping, dst_index_col, dst_mapping,
                  encoders=None, dtype=None):
    df = pd.read_csv(path, dtype=dtype)
    src = df[src_index_col].map(src_mapping)
    dst = df[dst_index_col].map(dst_mapping)
    if src.isna().any() or dst.isna().any():
        raise ValueError('Unknown or null edge endpoint')
    edge_index = torch.tensor([src.tolist(), dst.tolist()], dtype=torch.long)
    edge_attr = None
    if encoders:
        columns = [encoder(df[col]) for col, encoder in encoders.items()]
        if any(t.ndim != 2 or t.size(0) != len(df) for t in columns):
            raise ValueError('Every encoder must return [num_edges, features]')
        edge_attr = torch.cat(columns, dim=-1)
    return edge_index, edge_attr

class IdentityEncoder:
    def __init__(self, dtype=torch.float32):
        self.dtype = dtype
    def __call__(self, series):
        return torch.as_tensor(series.to_numpy(copy=True), dtype=self.dtype).reshape(-1, 1)

class GenresEncoder:
    def __init__(self, categories, sep='|'):
        self.mapping = {name: i for i, name in enumerate(sorted(set(categories)))}
        self.sep = sep
    def __call__(self, series):
        x = torch.zeros(len(series), len(self.mapping))
        for i, value in enumerate(series):
            if not isinstance(value, str):
                raise ValueError('Missing/non-string genre')
            for name in value.split(self.sep):
                if name not in self.mapping:
                    raise ValueError(f'Unknown genre: {name}')
                x[i, self.mapping[name]] = 1
        return x
```

For MovieLens-shaped local tables, use a persisted genre vocabulary, a deduplicated `users.csv`, and explicit node counts:

```python
from torch_geometric.data import HeteroData

movie_x, movies = load_node_csv('movies.csv', 'movieId',
    encoders={'genres': GenresEncoder(['Action', 'Comedy', 'Drama'])})
_, users = load_node_csv('users.csv', 'userId')
edge_index, ratings = load_edge_csv('ratings.csv', 'userId', users,
    'movieId', movies, encoders={'rating': IdentityEncoder()})
data = HeteroData()
data['user'].num_nodes = len(users)
data['movie'].num_nodes = len(movies)
data['movie'].x = movie_x
data['user', 'rates', 'movie'].edge_index = edge_index
data['user', 'rates', 'movie'].rating = ratings.view(-1)  # Regression target
assert data.validate(raise_on_error=True)
```

Featureless users still need model inputs (e.g. learned embeddings); a node count alone cannot be fed to `SAGEConv`. Rating prediction and binary link existence have different targets/splits. Do not feed held-out ratings as `edge_attr`, copy them into reverse message edges, or cast fractional ratings to integer classes.

Optional text features (illustrative; model weights were not downloaded):

```python
from sentence_transformers import SentenceTransformer

encoder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
# texts is a sequence of strings in exactly the persisted node-table order.
x = encoder.encode(texts, convert_to_tensor=True).cpu()
```

Record the model revision, truncation and preprocessing; the model's tokenizer length can silently truncate long node descriptions.

## Conversions

```python
import networkx as nx
from torch_geometric.utils import from_networkx, from_scipy_sparse_matrix

G = nx.Graph()
G.add_node('isolated', feature=[1.0, 0.0])
G.add_node('connected', feature=[0.0, 1.0])
node_order = list(G.nodes())  # PyG row order; persist this mapping.
data = from_networkx(G, group_node_attrs=['feature'])
```

`from_networkx` preserves attributes under their names by default; it does **not** automatically assign `x`/`edge_attr`. Group numeric attributes explicitly (`group_node_attrs`, `group_edge_attrs`); all nodes/edges must have the same attribute keys. An undirected NetworkX graph becomes both directed edge orientations. Check node order, isolates and multiedge policy after conversion.

```python
edge_index, edge_weight = from_scipy_sparse_matrix(adj_matrix)
data = Data(x=features, edge_index=edge_index, edge_weight=edge_weight,
            num_nodes=adj_matrix.shape[0])
```

Rows are sources and columns targets for this COO conversion; scalar adjacency values are edge weights, and stored zeros remain edges. Confirm square shape for a homogeneous graph. Native sparse message passing may instead expect transposed adjacency (`adj_t`). One-hot node IDs or learned ID embeddings can memorize seen nodes and do not automatically generalize to new entities.

Sources: [dataset tutorial](https://pytorch-geometric.readthedocs.io/en/latest/tutorial/create_dataset.html), [CSV tutorial](https://pytorch-geometric.readthedocs.io/en/latest/tutorial/load_csv.html), [conversion utilities](https://pytorch-geometric.readthedocs.io/en/latest/modules/utils.html), [SentenceTransformer API](https://sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html).
