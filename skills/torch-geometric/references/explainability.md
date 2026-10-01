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
        return_type='raw',                  # Raw logits; match the actual model output
    ),
)
```

**Mask types explained:**
- `'object'`: One value per node (`[N, 1]`) or per edge (`[E]`).
- `'attributes'`: One mask value per node and feature, shape `[N, F]`.
- `'common_attributes'`: One feature mask shared across all nodes, shape `[1, F]`.
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

explanation = explainer(data.x, data.edge_index, batch=data.batch, index=0)
```

Pass every additional argument required by the model (e.g. graph assignment `batch`, edge weights or supervision edges). For an individual unbatched graph, construct a zero-valued node-to-graph assignment if the model requires it.

## Visualization

```python
# Visualize which features are most important (bar chart)
explanation.visualize_feature_importance(path='feature_importance.png', top_k=10)
# Needs a node feature mask and matplotlib.

# Visualize the important subgraph
explanation.visualize_graph(path='graph.png', backend='networkx')
# Requires an edge mask plus matplotlib/networkx. path=None displays, not saves.
```

## Available Algorithms

### GNNExplainer

Learns soft masks via optimization. Works for node and graph-level tasks. The most widely used algorithm.

```python
from torch_geometric.explain import GNNExplainer

algorithm = GNNExplainer(epochs=200, lr=0.01)
```

### PGExplainer

A parametric (trained) explainer — learns a neural network that generates edge masks. Must be trained before use; generalization to new graphs still needs evaluation. Only supports edge masks (no node masks).

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

# Keep the trained prediction model fixed in evaluation behavior.
model.eval()
# Train the explainer first, using only permitted training targets.
for epoch in range(30):
    for batch in loader:
        loss = explainer.algorithm.train(
            epoch, model, batch.x, batch.edge_index, target=batch.y, batch=batch.batch
        )

# Then explain
explanation = explainer(data.x, data.edge_index, target=data.y,
                        batch=data.batch, index=0)
```

`phenomenon` requires `target=` both during training and explanation. This graph-regression recipe assumes model output and `data.y` have the same shape (for example `[num_graphs, 1]`). Node PGExplainer training also requires a single `index` per call.

### CaptumExplainer

Wraps the [Captum](https://captum.ai/) library, giving access to gradient-based attribution methods. Works with both homogeneous and heterogeneous graphs.

```python
from torch_geometric.explain import CaptumExplainer

# Supports: 'IntegratedGradients', 'Saliency', 'Deconvolution',
#           'ShapleyValueSampling', 'GuidedBackprop', etc.
algorithm = CaptumExplainer('IntegratedGradients')
```

Requires `uv pip install captum==0.9.0` for the reviewed runtime. Avoid blindly installing the PyG `full` extra: its released metadata still pins older Captum.

### AttentionExplainer

Uses supported layers' captured attention coefficients as edge masks, with no explainer training. Support is operator-specific; the tested example uses `GATConv`. A layer having an attention mechanism (e.g. `TransformerConv`) does not alone establish hook compatibility. Attention weights are not causal evidence.

```python
from torch_geometric.explain import AttentionExplainer

algorithm = AttentionExplainer()
```

## Heterogeneous Graph Explanations

For heterogeneous models, compatible algorithms return `HeteroExplanation` with per-type masks. Wrap dict-returning models so the explainer gets one tensor for the node type being explained; `index` then refers to rows of that type:

```python
from torch_geometric.explain import Explainer, CaptumExplainer

class PaperOutput(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model
    def forward(self, x_dict, edge_index_dict):
        return self.model(x_dict, edge_index_dict)['paper']

explainer = Explainer(
    model=PaperOutput(hetero_model),
    algorithm=CaptumExplainer('IntegratedGradients'),
    explanation_type='model',
    node_mask_type='attributes',
    edge_mask_type='object',
    model_config=dict(
        mode='multiclass_classification',
        task_level='node',
        return_type='raw',  # Wrapped model returns paper logits.
    ),
)

hetero_explanation = explainer(
    data.x_dict,
    data.edge_index_dict,
    index=1,  # Explain one target at a time for Captum.
)

# Access per-type masks
hetero_explanation.node_mask_dict    # {'paper': tensor, 'author': tensor, ...}
hetero_explanation.edge_mask_dict    # {('paper','cites','paper'): tensor, ...}
```

## Evaluation Metrics

```python
from torch_geometric.explain import unfaithfulness, fidelity, characterization_score

# Unfaithfulness compares model prediction distributions after masking.
# Lower means closer under this masking experiment.
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
        threshold_type='topk',    # 'topk', 'topk_hard', or 'hard'
        value=10,                  # Top-10 edges for 'topk', threshold value for 'hard'
    ),
)
```

- `'topk'`: Keep only top-k highest-scored elements
- `'hard'`: Binary threshold — elements above `value` are kept
- `'topk_hard'`: Binarize the retained top-k entries.
- Omit `threshold_config` to return continuous masks.

Mask scores and fidelity metrics characterize a model under a chosen baseline/perturbation, not molecular mechanisms or causality. Check stability across seeds and correlated features, and report whether masking creates off-distribution graphs. Fit explainers on training data and reserve evaluation explanations for held-out analysis. Heterogeneous metrics/visualizers need separate support checks.

Sources: [explain interface](https://pytorch-geometric.readthedocs.io/en/latest/modules/explain.html), [PGExplainer](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.explain.algorithm.PGExplainer.html), [CaptumExplainer](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.explain.algorithm.CaptumExplainer.html).
