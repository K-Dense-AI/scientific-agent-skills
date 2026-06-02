# Custom Datasets — Full Reference

How to create your own graph datasets and load graph data from raw sources (CSV, pandas, numpy, etc.).

## Quick: No Dataset Class Needed

For synthetic data or one-off graphs, skip the dataset machinery — just create `Data` objects and pass them to `DataLoader`:

```python
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

data_list = [Data(x=..., edge_index=..., y=...) for _ in range(100)]
loader = DataLoader(data_list, batch_size=32)
```

## InMemoryDataset (fits in RAM)

For reusable datasets that fit in CPU memory. Override 4 methods:

```python
from torch_geometric.data import InMemoryDataset, download_url

class MyDataset(InMemoryDataset):
    def __init__(self, root, transform=None, pre_transform=None, pre_filter=None):
        super().__init__(root, transform, pre_transform, pre_filter)
        self.load(self.processed_paths[0])

    @property
    def raw_file_names(self):
        # Files in raw_dir that must exist to skip download()
        return ['data.csv']

    @property
    def processed_file_names(self):
        # Files in processed_dir that must exist to skip process()
        return ['data.pt']

    def download(self):
        # Download raw files to self.raw_dir
        # Use trusted sources only; verify checksums or signatures before loading.
        download_url('https://example.com/data.csv', self.raw_dir)

    def process(self):
        # Read raw data and create a list of Data objects
        data_list = [...]

        if self.pre_filter is not None:
            data_list = [d for d in data_list if self.pre_filter(d)]
        if self.pre_transform is not None:
            data_list = [self.pre_transform(d) for d in data_list]

        # save() collates list into one big Data + slices dict, then saves
        self.save(data_list, self.processed_paths[0])
```

**Directory structure created automatically:**
```
root/
├── raw/          # raw_dir — downloaded files go here
│   └── data.csv
└── processed/    # processed_dir — processed .pt files go here
    └── data.pt
```

**Key behaviors:**
- `download()` runs only if files in `raw_file_names` are missing from `raw_dir`
- `process()` runs only if files in `processed_file_names` are missing from `processed_dir`
- If you change `pre_transform`, delete the `processed/` directory to reprocess

## Dataset (doesn't fit in RAM)

For very large datasets, save each graph individually:

```python
import os.path as osp
import torch
from torch_geometric.data import Dataset, download_url

class LargeDataset(Dataset):
    def __init__(self, root, transform=None, pre_transform=None):
        super().__init__(root, transform, pre_transform)

    @property
    def raw_file_names(self):
        return ['graph_data.csv']

    @property
    def processed_file_names(self):
        return [f'data_{i}.pt' for i in range(1000)]

    def download(self):
        download_url('...', self.raw_dir)

    def process(self):
        for idx in range(1000):
            data = Data(...)  # Build graph from raw data
            if self.pre_filter is not None and not self.pre_filter(data):
                continue
            if self.pre_transform is not None:
                data = self.pre_transform(data)
            torch.save(data, osp.join(self.processed_dir, f'data_{idx}.pt'))

    def len(self):
        return 1000

    def get(self, idx):
        return torch.load(osp.join(self.processed_dir, f'data_{idx}.pt'))
```

## Loading Graphs from CSV

A common pattern: load node/edge data from CSV files into a HeteroData object.

### Step 1: Load node features

```python
import pandas as pd
import torch

def load_node_csv(path, index_col, encoders=None):
    df = pd.read_csv(path, index_col=index_col)
    # Map original IDs to consecutive 0..N-1 indices
    mapping = {idx: i for i, idx in enumerate(df.index.unique())}

    x = None
    if encoders is not None:
        xs = [encoder(df[col]) for col, encoder in encoders.items()]
        x = torch.cat(xs, dim=-1)

    return x, mapping
```

### Step 2: Load edges

```python
def load_edge_csv(path, src_index_col, src_mapping, dst_index_col, dst_mapping,
                  encoders=None):
    df = pd.read_csv(path)
    src = [src_mapping[idx] for idx in df[src_index_col]]
    dst = [dst_mapping[idx] for idx in df[dst_index_col]]
    edge_index = torch.tensor([src, dst])

    edge_attr = None
    if encoders is not None:
        edge_attrs = [encoder(df[col]) for col, encoder in encoders.items()]
        edge_attr = torch.cat(edge_attrs, dim=-1)

    return edge_index, edge_attr
```

### Step 3: Assemble HeteroData

```python
from torch_geometric.data import HeteroData

# Load nodes
movie_x, movie_mapping = load_node_csv('movies.csv', 'movieId',
    encoders={'genres': GenresEncoder()})
_, user_mapping = load_node_csv('ratings.csv', 'userId')

# Load edges
edge_index, edge_label = load_edge_csv('ratings.csv',
    src_index_col='userId', src_mapping=user_mapping,
    dst_index_col='movieId', dst_mapping=movie_mapping,
    encoders={'rating': IdentityEncoder(dtype=torch.long)})

# Build HeteroData
data = HeteroData()
data['user'].num_nodes = len(user_mapping)
data['movie'].x = movie_x
data['user', 'rates', 'movie'].edge_index = edge_index
data['user', 'rates', 'movie'].edge_label = edge_label
```

### Common Encoders

```python
class IdentityEncoder:
    """Encode a numeric column as-is."""
    def __init__(self, dtype=None):
        self.dtype = dtype
    def __call__(self, df):
        return torch.from_numpy(df.values).view(-1, 1).to(self.dtype)

class GenresEncoder:
    """Multi-hot encode a pipe-separated categorical column."""
    def __init__(self, sep='|'):
        self.sep = sep
    def __call__(self, df):
        genres = set(g for col in df.values for g in col.split(self.sep))
        mapping = {genre: i for i, genre in enumerate(genres)}
        x = torch.zeros(len(df), len(mapping))
        for i, col in enumerate(df.values):
            for genre in col.split(self.sep):
                x[i, mapping[genre]] = 1
        return x
```

For text features, use sentence-transformers:

```python
from sentence_transformers import SentenceTransformer

class SequenceEncoder:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
    @torch.no_grad()
    def __call__(self, df):
        return self.model.encode(df.values, convert_to_tensor=True).cpu()
```

## From NetworkX

```python
from torch_geometric.utils import from_networkx
import networkx as nx

G = nx.karate_club_graph()
data = from_networkx(G)
# Node attributes become data.x, edge attributes become data.edge_attr
```

## From scipy sparse adjacency matrix

```python
from torch_geometric.utils import from_scipy_sparse_matrix

edge_index, edge_attr = from_scipy_sparse_matrix(adj_matrix)
data = Data(x=features, edge_index=edge_index)
```

## Featureless Nodes

If nodes have no features, common options:
- Use `torch.nn.Embedding` to learn features during training
- Set `data['node_type'].num_nodes = N` (for HeteroData)
- Use structural features: degree, clustering coefficient, etc.
- Use `data.x = torch.eye(num_nodes)` (one-hot, only for small graphs)
