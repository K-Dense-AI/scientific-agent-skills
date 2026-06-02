# Custom Message Passing Layers

Full reference for implementing custom GNN layers via the `MessagePassing` base class.

## MessagePassing API

```python
MessagePassing(aggr="add", flow="source_to_target", node_dim=-2)
```

- `aggr`: Aggregation scheme — `"add"`, `"mean"`, or `"max"`
- `flow`: Message direction — `"source_to_target"` (default) or `"target_to_source"`
- `node_dim`: Axis along which to propagate

### Methods to override

- `message(...)`: Constructs messages for each edge. Access source/target node features via `_j`/`_i` suffixes.
- `aggregate(inputs, index)`: Aggregates messages (usually handled by `aggr` parameter).
- `update(aggr_out, ...)`: Post-aggregation transform on each node.
- `propagate(edge_index, size=None, **kwargs)`: Orchestrates the full pipeline. Call this from `forward()`.

Any tensor passed to `propagate()` can be auto-indexed in `message()` by appending `_i` (target) or `_j` (source). E.g., passing `x=features` lets you use `x_i` and `x_j` in the message function.

For bipartite graphs, pass `size=(N, M)` to `propagate()` and provide features as tuples: `x=(x_src, x_dst)`.

## Example: GCN Layer from Scratch

```python
import torch
from torch.nn import Linear, Parameter
from torch_geometric.nn import MessagePassing
from torch_geometric.utils import add_self_loops, degree

class GCNConv(MessagePassing):
    def __init__(self, in_channels, out_channels):
        super().__init__(aggr='add')
        self.lin = Linear(in_channels, out_channels, bias=False)
        self.bias = Parameter(torch.empty(out_channels))
        self.reset_parameters()

    def reset_parameters(self):
        self.lin.reset_parameters()
        self.bias.data.zero_()

    def forward(self, x, edge_index):
        # 1. Add self-loops
        edge_index, _ = add_self_loops(edge_index, num_nodes=x.size(0))
        # 2. Linear transform
        x = self.lin(x)
        # 3. Compute normalization coefficients
        row, col = edge_index
        deg = degree(col, x.size(0), dtype=x.dtype)
        deg_inv_sqrt = deg.pow(-0.5)
        deg_inv_sqrt[deg_inv_sqrt == float('inf')] = 0
        norm = deg_inv_sqrt[row] * deg_inv_sqrt[col]
        # 4-5. Message passing
        out = self.propagate(edge_index, x=x, norm=norm)
        # 6. Add bias
        return out + self.bias

    def message(self, x_j, norm):
        # x_j: source node features for each edge [num_edges, out_channels]
        # norm: normalization coefficients [num_edges]
        return norm.view(-1, 1) * x_j
```

## Example: EdgeConv Layer

```python
import torch
from torch.nn import Sequential as Seq, Linear, ReLU
from torch_geometric.nn import MessagePassing

class EdgeConv(MessagePassing):
    def __init__(self, in_channels, out_channels):
        super().__init__(aggr='max')
        self.mlp = Seq(
            Linear(2 * in_channels, out_channels),
            ReLU(),
            Linear(out_channels, out_channels),
        )

    def forward(self, x, edge_index):
        return self.propagate(edge_index, x=x)

    def message(self, x_i, x_j):
        # x_i: target node features [num_edges, in_channels]
        # x_j: source node features [num_edges, in_channels]
        return self.mlp(torch.cat([x_i, x_j - x_i], dim=1))
```

## Example: Dynamic EdgeConv (recomputes graph each layer)

```python
from torch_geometric.nn import knn_graph

class DynamicEdgeConv(EdgeConv):
    def __init__(self, in_channels, out_channels, k=6):
        super().__init__(in_channels, out_channels)
        self.k = k

    def forward(self, x, batch=None):
        edge_index = knn_graph(x, self.k, batch, loop=False, flow=self.flow)
        return super().forward(x, edge_index)
```

## Utility Functions

```python
from torch_geometric.utils import (
    add_self_loops,      # Add self-loop edges
    remove_self_loops,   # Remove self-loop edges
    degree,              # Compute node degrees
    softmax,             # Sparse softmax over neighborhoods
    to_dense_adj,        # Convert edge_index to dense adjacency matrix
    to_undirected,       # Make edge_index undirected
    contains_self_loops, # Check for self-loops
    is_undirected,       # Check if graph is undirected
    scatter,             # Scatter operations (sum, mean, max)
)
```
