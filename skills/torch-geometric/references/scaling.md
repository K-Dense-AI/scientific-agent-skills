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

The primary approach for large single-graph training. Recursively samples a fixed number of neighbors per hop, bounding fan-out per seed (not a global memory limit). Requires compatible `pyg-lib` or `torch-sparse`; backend support differs for induced, disjoint and temporal sampling. Start with `num_workers=0` for debugging.

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
from torch_geometric.nn import GraphSAGE
model = GraphSAGE(in_channels, hidden_channels, num_layers=2, out_channels=out_channels)

for batch in loader:
    batch = batch.to(device)
    out = model(batch.x, batch.edge_index)
    # CRITICAL: only first batch_size nodes are seed nodes
    loss = F.cross_entropy(out[:batch.batch_size], batch.y[:batch.batch_size])
```

**Important details:**
- Nodes are sorted: first `batch.batch_size` nodes are the seed nodes
- `batch.n_id` maps local indices back to original node IDs
- Multiple hops can grow neighborhoods rapidly; fan-out and overlap determine the actual cost
- Keep `len(num_neighbors) == num_gnn_layers` for efficiency
- PyG 2.7 adds `BidirectionalSampler` and forward+reverse edge sampling on `NeighborSampler` for undirected graphs

### LinkNeighborLoader (for link prediction)

Samples subgraphs around supervision edges:

```python
from torch_geometric.loader import LinkNeighborLoader

loader = LinkNeighborLoader(
    train_data,
    num_neighbors=[20, 10],
    edge_label_index=train_data.edge_label_index,
    edge_label=train_data.edge_label,
    batch_size=256,
    neg_sampling=None,  # This example assumes fixed positive AND negative labels.
    shuffle=True,
)
```

### HGTLoader (type-aware heterogeneous sampling)

Samples a node budget per type per hop following the HGT paper; requires `torch-sparse` (illustrative):

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

Partitions the graph into clusters using METIS (`pyg-lib` with METIS or `torch-sparse`), then trains on batches of partitions. Boundary edges can be omitted; it is not full-graph message passing (illustrative):

```python
from torch_geometric.loader import ClusterData, ClusterLoader

cluster_data = ClusterData(data, num_parts=1500)
loader = ClusterLoader(cluster_data, batch_size=20, shuffle=True)

for batch in loader:
    # Mask supervised nodes; do not compute an empty-mask loss.
    if not batch.train_mask.any():
        continue
    out = model(batch.x, batch.edge_index)
    loss = F.cross_entropy(out[batch.train_mask], batch.y[batch.train_mask])
```

### GraphSAINTSampler

Samples subgraphs via random walks, nodes, or edges with importance-based normalization:

```python
from torch_geometric.loader import GraphSAINTRandomWalkSampler

loader = GraphSAINTRandomWalkSampler(
    data, batch_size=6000, walk_length=2, num_steps=5, sample_coverage=100,
)
```

`GraphSAINT` requires `torch-sparse`. With positive `sample_coverage`, use its `edge_norm` in the message operator and `node_norm` in the unreduced supervised loss as in the official GraphSAINT example; merely constructing the sampler does not apply normalization.

### ShaDowKHopSampler

Extracts K-hop induced subgraphs around seed nodes — decouples depth from scope:

```python
from torch_geometric.loader import ShaDowKHopSampler

loader = ShaDowKHopSampler(
    data, depth=2, num_neighbors=5, batch_size=64,
    node_idx=data.train_mask,
)
```

ShaDow requires `torch-sparse`. Seed outputs are at `batch.root_n_id`, not the NeighborLoader prefix; node labels are already indexed to roots in the returned batch.

## 3. Multi-GPU / Distributed Training

`torch_geometric.distributed` is deprecated as of PyG 2.7 — use standard PyTorch DDP below.

### DistributedDataParallel (DDP)

Standard DDP replicates model parameters and synchronizes gradients; it does not automatically partition/store a giant graph. The following single-machine CUDA recipe is illustrative. Launch it with `torchrun --standalone --nproc_per_node=4 train.py`, and supply your already prepared CPU `data` and class count. The distributed sampler pads to equal per-rank counts (possibly repeating a few seeds), preventing unequal backward-call counts.

```python
import os
import torch
import torch.nn.functional as F
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data.distributed import DistributedSampler
from torch_geometric.loader import NeighborLoader
from torch_geometric.nn import GraphSAGE

def run(data, num_classes):
    local_rank = int(os.environ['LOCAL_RANK'])
    torch.cuda.set_device(local_rank)
    dist.init_process_group('nccl')
    rank, world_size = dist.get_rank(), dist.get_world_size()
    device = torch.device('cuda', local_rank)
    train_idx = data.train_mask.nonzero(as_tuple=False).view(-1)
    if train_idx.numel() == 0:
        raise ValueError('Empty training seed set')
    seed_sampler = DistributedSampler(train_idx, num_replicas=world_size,
                                      rank=rank, shuffle=True, drop_last=False)
    model = GraphSAGE(data.num_features, 64, num_layers=2,
                      out_channels=num_classes).to(device)
    model = DistributedDataParallel(model, device_ids=[local_rank])
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    for epoch in range(10):
        seed_sampler.set_epoch(epoch)
        rank_seeds = train_idx[torch.tensor(list(seed_sampler))]
        loader = NeighborLoader(data, input_nodes=rank_seeds,
                                num_neighbors=[25, 10], batch_size=1024,
                                num_workers=0, shuffle=False)
        model.train()
        for batch in loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            out = model(batch.x, batch.edge_index)[:batch.batch_size]
            loss = F.cross_entropy(out, batch.y[:batch.batch_size])
            loss.backward()
            optimizer.step()
        # All ranks reach both barriers. If evaluating only on rank 0,
        # use model.module under no_grad and aggregate metrics correctly;
        # invoking only one rank's DDP wrapper can hang its collectives.
        dist.barrier()
        dist.barrier()
    dist.destroy_process_group()
```

For multi-node launch, use the launcher's rendezvous and global rank environment; `LOCAL_RANK` only selects a device on its own host. Avoid hardcoded localhost rendezvous or floor-sized slicing that drops remaining seeds. The graph is still replicated in this recipe; estimate host/GPU memory before launching.

### PyTorch Lightning Integration

PyG provides wrappers under `torch_geometric.data.lightning`. Use a real `LightningModule` implementing training/validation steps and optimizers, not a bare GNN. The neighbor/GPU Trainer example is illustrative:

```python
import lightning as L
from torch_geometric.data.lightning import LightningNodeData

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
trainer.fit(lightning_model, datamodule=datamodule)
```

Also available: `LightningLinkData` for link prediction, `LightningDataset` for graph-level tasks.

## 4. torch.compile Support

PyG supports `torch.compile`; speedups depend on shapes, backend and warmup. This optimizing-compiler example is illustrative; an eager-backend capture smoke does not establish optimized CPU/CUDA performance:

```python
from torch_geometric.nn import GCN
model = GCN(in_channels, hidden_channels=64, num_layers=2, out_channels=out_channels)
model = torch.compile(model, dynamic=True)

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

- **num_workers**: Benchmark workers and memory use; start with zero, then increase. On spawn-based platforms use a main guard.
- **pin_memory**: Use `pin_memory=True` in loaders for faster CPU-to-GPU transfer
- **Sparse tensors**: Some layers benefit from `torch_sparse.SparseTensor`; pass transposed adjacency (`adj_t`, target rows/source columns) and verify numerical parity.
- **Profiling**: Use `torch_geometric.profile` to measure time and memory of individual layers
- **Mixed precision**: Standard PyTorch AMP works with PyG:
  ```python
  from torch.amp import autocast, GradScaler
  scaler = GradScaler("cuda")
  optimizer.zero_grad()
  with autocast('cuda'):
      out = model(batch.x, batch.edge_index)
      loss = F.cross_entropy(out[:batch.batch_size], batch.y[:batch.batch_size])
  scaler.scale(loss).backward()
  scaler.step(optimizer)
  scaler.update()
  ```
- **Reduce sampling**: Fewer neighbors per hop = faster but noisier. Start with `[15, 10]` for 2-layer GNNs.
- **Avoid unnecessary computation**: With NeighborLoader, only the first `batch_size` outputs matter — don't compute metrics on sampled-only nodes.

Sources: [loaders](https://pytorch-geometric.readthedocs.io/en/latest/modules/loader.html), [DDP tutorial](https://pytorch-geometric.readthedocs.io/en/latest/tutorial/multi_gpu_vanilla.html), [compile guidance](https://pytorch-geometric.readthedocs.io/en/latest/advanced/compile.html), [LightningNodeData](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.data.lightning.LightningNodeData.html).
