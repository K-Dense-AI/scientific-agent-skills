# Scaling GNNs — Full Reference

Techniques for training GNNs on large graphs that don't fit in GPU memory, multi-GPU training, and performance optimization.

## Table of Contents
1. Neighbor Sampling (NeighborLoader)
2. Other Sampling Strategies
3. Multi-GPU / Distributed Training
4. torch.compile Support
5. Performance Tips

---

## 1. Neighbor Sampling (NeighborLoader)

The primary approach for large single-graph training. Recursively samples a fixed number of neighbors per hop, bounding the computation graph.

```python
from torch_geometric.loader import NeighborLoader

loader = NeighborLoader(
    data,
    num_neighbors=[15, 10],       # Max neighbors per hop (hop 1: 15, hop 2: 10)
    batch_size=1024,               # Number of seed nodes per batch
    input_nodes=data.train_mask,   # Which nodes to sample from
    shuffle=True,
    num_workers=4,                 # Parallel data loading
    replace=False,                 # Sample without replacement
)
```

**Key parameters:**
- `num_neighbors`: List of max neighbors per hop. Length should match GNN depth. Use `-1` to sample all neighbors for a hop.
- `input_nodes`: Seed nodes — can be a mask, tensor of indices, or `('node_type', mask)` tuple for hetero graphs.
- `subgraph_type`: `"directional"` (default), `"bidirectional"` (add reverse edges), or `"induced"` (full induced subgraph).
- `disjoint`: If `True`, don't fuse neighborhoods across seed nodes (uses more memory but can be needed).

**Training pattern:**
```python
model = GraphSAGE(in_channels, hidden_channels, out_channels, num_layers=2)

for batch in loader:
    batch = batch.to(device)
    out = model(batch.x, batch.edge_index)
    # CRITICAL: only first batch_size nodes are seed nodes
    loss = F.cross_entropy(out[:batch.batch_size], batch.y[:batch.batch_size])
```

**Important details:**
- Nodes are sorted: first `batch.batch_size` nodes are the seed nodes
- `batch.n_id` maps local indices back to original node IDs
- Sampling >2-3 hops is generally infeasible (exponential neighborhood growth)
- Keep `len(num_neighbors) == num_gnn_layers` for efficiency
- PyG 2.7 adds `BidirectionalSampler` and forward+reverse edge sampling on `NeighborSampler` for undirected graphs

### LinkNeighborLoader (for link prediction)

Samples subgraphs around supervision edges:

```python
from torch_geometric.loader import LinkNeighborLoader

loader = LinkNeighborLoader(
    data,
    num_neighbors=[20, 10],
    edge_label_index=train_data.edge_label_index,
    edge_label=train_data.edge_label,
    batch_size=256,
    neg_sampling_ratio=1.0,
    shuffle=True,
)
```

### HGTLoader (type-aware heterogeneous sampling)

Samples a fixed number of nodes per type per hop, following HGT paper:

```python
from torch_geometric.loader import HGTLoader

loader = HGTLoader(
    data,
    num_samples=[512] * 2,        # Nodes per type per hop
    batch_size=128,
    input_nodes=('paper', data['paper'].train_mask),
)
```

## 2. Other Sampling Strategies

### ClusterLoader (ClusterGCN)

Partitions the graph into clusters, trains on full subgraphs. Better for deeper GNNs since messages flow freely within clusters:

```python
from torch_geometric.loader import ClusterData, ClusterLoader

cluster_data = ClusterData(data, num_parts=1500)
loader = ClusterLoader(cluster_data, batch_size=20, shuffle=True)

for batch in loader:
    # batch is a full subgraph — no slicing needed
    out = model(batch.x, batch.edge_index)
    loss = F.cross_entropy(out[batch.train_mask], batch.y[batch.train_mask])
```

### GraphSAINTSampler

Samples subgraphs via random walks, nodes, or edges with importance-based normalization:

```python
from torch_geometric.loader import GraphSAINTRandomWalkSampler

loader = GraphSAINTRandomWalkSampler(
    data, batch_size=6000, walk_length=2, num_steps=5,
)
```

### ShaDowKHopSampler

Extracts K-hop induced subgraphs around seed nodes — decouples depth from scope:

```python
from torch_geometric.loader import ShaDowKHopSampler

loader = ShaDowKHopSampler(
    data, depth=2, num_neighbors=5, batch_size=64,
    input_nodes=data.train_mask,
)
```

## 3. Multi-GPU / Distributed Training

`torch_geometric.distributed` is deprecated as of PyG 2.7 — use standard PyTorch DDP below.

### DistributedDataParallel (DDP)

Standard PyTorch DDP works with PyG. Each GPU gets a partition of the seed nodes:

```python
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel
import torch.multiprocessing as mp

def run(rank, world_size, dataset):
    # Initialize process group
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12345'
    dist.init_process_group('nccl', rank=rank, world_size=world_size)

    data = dataset[0]

    # Split training nodes across GPUs
    train_idx = data.train_mask.nonzero().view(-1)
    train_idx = train_idx.split(train_idx.size(0) // world_size)[rank]

    loader = NeighborLoader(
        data,
        input_nodes=train_idx,
        num_neighbors=[25, 10],
        batch_size=1024,
        num_workers=4,
        shuffle=True,
    )

    # Wrap model in DDP
    model = GraphSAGE(...).to(rank)
    model = DistributedDataParallel(model, device_ids=[rank])
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(10):
        model.train()
        for batch in loader:
            batch = batch.to(rank)
            optimizer.zero_grad()
            out = model(batch.x, batch.edge_index)[:batch.batch_size]
            loss = F.cross_entropy(out, batch.y[:batch.batch_size])
            loss.backward()
            optimizer.step()

        # Synchronize before evaluation
        dist.barrier()

        if rank == 0:
            # Evaluate on rank 0 only
            ...

    dist.destroy_process_group()

# Launch
if __name__ == '__main__':
    dataset = Reddit('./data/Reddit')
    world_size = torch.cuda.device_count()
    mp.spawn(run, args=(world_size, dataset), nprocs=world_size, join=True)
```

**Key points:**
- Initialize dataset before `mp.spawn()` — data auto-moves to shared memory
- Each rank creates its own NeighborLoader with a subset of seed nodes
- Call `dist.barrier()` to synchronize before evaluation
- Evaluate on rank 0 only for simplicity
- Clean up with `dist.destroy_process_group()`

### PyTorch Lightning Integration

PyG provides Lightning wrappers for minimal boilerplate. PyG 2.7 supports the `lightning` package (not only legacy `pytorch-lightning`):

```python
import lightning as L
from torch_geometric.data import LightningNodeData

datamodule = LightningNodeData(
    data,
    input_train_nodes=data.train_mask,
    input_val_nodes=data.val_mask,
    input_test_nodes=data.test_mask,
    loader='neighbor',
    num_neighbors=[25, 10],
    batch_size=1024,
)

# Use with any Lightning Trainer
trainer = L.Trainer(devices=4, accelerator='gpu', strategy='ddp')
trainer.fit(model, datamodule)
```

Also available: `LightningLinkData` for link prediction, `LightningDataset` for graph-level tasks.

## 4. torch.compile Support

PyG supports `torch.compile` for faster execution:

```python
model = GCN(...)
model = torch.compile(model)

# Works with standard training loops
out = model(data.x, data.edge_index)
```

**What works:**
- Most GNN layers (GCNConv, SAGEConv, GATConv, etc.)
- Standard training/inference pipelines
- Both CPU and CUDA backends

**Limitations:**
- Dynamic shapes (varying graph sizes per batch) may trigger recompilation
- Some specialized layers or custom MessagePassing subclasses may not compile
- Use `torch.compile(model, dynamic=True)` if batch graph sizes vary significantly

## 5. Performance Tips

- **num_workers**: Set `num_workers=4` (or more) in data loaders for CPU-side parallelism
- **pin_memory**: Use `pin_memory=True` in loaders for faster CPU-to-GPU transfer
- **Sparse tensors**: Use `SparseTensor` from `torch_sparse` instead of `edge_index` for faster message passing on some layers
- **Profiling**: Use `torch_geometric.profile` to measure time and memory of individual layers
- **Mixed precision**: Standard PyTorch AMP works with PyG:
  ```python
  from torch.amp import autocast, GradScaler
  scaler = GradScaler()
  with autocast('cuda'):
      out = model(batch.x, batch.edge_index)
      loss = F.cross_entropy(out[:batch.batch_size], batch.y[:batch.batch_size])
  scaler.scale(loss).backward()
  scaler.step(optimizer)
  scaler.update()
  ```
- **Reduce sampling**: Fewer neighbors per hop = faster but noisier. Start with `[15, 10]` for 2-layer GNNs.
- **Avoid unnecessary computation**: With NeighborLoader, only the first `batch_size` outputs matter — don't compute metrics on sampled-only nodes.
