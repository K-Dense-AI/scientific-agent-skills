# GNN Explainability — Full Reference

PyG provides `torch_geometric.explain` for interpreting GNN predictions. The module includes a unified `Explainer` interface, several explanation algorithms, visualization, and evaluation metrics.

## The Explainer Interface

The `Explainer` class is the central entry point. Configure it with:
1. An explanation **algorithm** (GNNExplainer, PGExplainer, CaptumExplainer, etc.)
2. An **explanation type** (`"model"` — explain model predictions, or `"phenomenon"` — explain dataset patterns)
3. **Mask types** — which parts of the input to explain (nodes, edges, features)
4. **Post-processing** — how to threshold masks (top-k, hard, etc.)

```python
from torch_geometric.explain import Explainer, GNNExplainer

explainer = Explainer(
    model=model,
    algorithm=GNNExplainer(epochs=200),
    explanation_type='model',          # 'model' or 'phenomenon'
    node_mask_type='attributes',       # 'object', 'common_attributes', 'attributes', or None
    edge_mask_type='object',           # 'object' or None
    model_config=dict(
        mode='multiclass_classification',  # 'binary_classification', 'multiclass_classification', 'regression'
        task_level='node',                  # 'node', 'edge', 'graph'
        return_type='log_probs',            # 'log_probs', 'probs', 'raw'
    ),
)
```

**Mask types explained:**
- `'object'`: One mask value per node/edge (which nodes/edges matter?)
- `'attributes'`: One mask value per node feature dimension (which features matter?)
- `'common_attributes'`: Same feature mask shared across all nodes
- `None`: Don't generate this mask type

## Generating Explanations

### Node classification

```python
# Explain prediction for node at index 10
explanation = explainer(data.x, data.edge_index, index=10)

print(explanation.node_mask)   # [num_nodes, num_features] — importance per feature per node
print(explanation.edge_mask)   # [num_edges] — importance per edge
```

### Graph classification

```python
explainer = Explainer(
    model=model,
    algorithm=GNNExplainer(epochs=200),
    explanation_type='model',
    edge_mask_type='object',
    model_config=dict(
        mode='multiclass_classification',
        task_level='graph',
        return_type='raw',
    ),
)

explanation = explainer(data.x, data.edge_index)
```

## Visualization

```python
# Visualize which features are most important (bar chart)
explanation.visualize_feature_importance(top_k=10)
# Saves to 'feature_importance.png' by default, or pass path=

# Visualize the important subgraph
explanation.visualize_graph()
# Saves to 'graph.png' by default, or pass path=
```

## Available Algorithms

### GNNExplainer

Learns soft masks via optimization. Works for node and graph-level tasks. The most widely used algorithm.

```python
from torch_geometric.explain import GNNExplainer

algorithm = GNNExplainer(epochs=200, lr=0.01)
```

### PGExplainer

A parametric (trained) explainer — learns a neural network that generates edge masks. Must be trained before use, but then generalizes to new graphs. Only supports edge masks (no node masks).

```python
from torch_geometric.explain import PGExplainer

explainer = Explainer(
    model=model,
    algorithm=PGExplainer(epochs=30, lr=0.003),
    explanation_type='phenomenon',     # PGExplainer explains phenomena
    edge_mask_type='object',
    model_config=dict(
        mode='regression',
        task_level='graph',
        return_type='raw',
    ),
    threshold_config=dict(threshold_type='topk', value=10),
)

# Train the explainer first
for epoch in range(30):
    for batch in loader:
        loss = explainer.algorithm.train(
            epoch, model, batch.x, batch.edge_index, target=batch.target
        )

# Then explain
explanation = explainer(data.x, data.edge_index)
```

### CaptumExplainer

Wraps the [Captum](https://captum.ai/) library, giving access to gradient-based attribution methods. Works with both homogeneous and heterogeneous graphs.

```python
from torch_geometric.explain import CaptumExplainer

# Supports: 'IntegratedGradients', 'Saliency', 'Deconvolution',
#           'ShapleyValueSampling', 'GuidedBackprop', etc.
algorithm = CaptumExplainer('IntegratedGradients')
```

Requires `uv pip install captum` (or `uv add captum`).

### AttentionExplainer

Uses attention weights from attention-based GNNs (GATConv, TransformerConv) as edge explanations. No training needed — just reads existing attention scores.

```python
from torch_geometric.explain import AttentionExplainer

algorithm = AttentionExplainer()
```

## Heterogeneous Graph Explanations

For heterogeneous models, the explainer returns `HeteroExplanation` with per-type masks:

```python
from torch_geometric.explain import Explainer, CaptumExplainer

explainer = Explainer(
    model=hetero_model,
    algorithm=CaptumExplainer('IntegratedGradients'),
    explanation_type='model',
    node_mask_type='attributes',
    edge_mask_type='object',
    model_config=dict(
        mode='multiclass_classification',
        task_level='node',
        return_type='probs',
    ),
)

hetero_explanation = explainer(
    data.x_dict,
    data.edge_index_dict,
    index=torch.tensor([1, 3]),
)

# Access per-type masks
hetero_explanation.node_mask_dict    # {'paper': tensor, 'author': tensor, ...}
hetero_explanation.edge_mask_dict    # {('paper','cites','paper'): tensor, ...}
```

## Evaluation Metrics

```python
from torch_geometric.explain import unfaithfulness, fidelity, characterization_score

# Unfaithfulness: how much does the explanation change the prediction?
# Lower is better (0 = perfectly faithful)
score = unfaithfulness(explainer, explanation)

# Fidelity: measures explanation quality via positive/negative fidelity
pos_fidelity, neg_fidelity = fidelity(explainer, explanation)

# Characterization score: combined metric
char_score = characterization_score(pos_fidelity, neg_fidelity)
```

## Post-Processing Masks

Control how raw mask values are converted to final explanations:

```python
explainer = Explainer(
    ...,
    threshold_config=dict(
        threshold_type='topk',    # 'topk', 'hard', or None
        value=10,                  # Top-10 edges for 'topk', threshold value for 'hard'
    ),
)
```

- `'topk'`: Keep only top-k highest-scored elements
- `'hard'`: Binary threshold — elements above `value` are kept
- `None`: Return raw continuous mask values
