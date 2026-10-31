# Models and Architectures

This is a selection guide for the
[TorchDrug 0.2.1 model API](https://torchdrug.ai/docs/api/models.html). Verify
constructor signatures on that page before generating code; similarly named
models in other graph libraries are not API-compatible.

## Graph representation models

Documented graph neural networks include:

- `models.GCN`
- `models.GAT`
- `models.GIN`
- `models.MPNN`
- `models.NFP`
- `models.RGCN`
- `models.ChebNet`
- `models.SchNet`
- `models.GearNet`

Their forward methods generally accept:

```python
output = model(graph, input, all_loss=None, metric=None)
```

Graph encoders return a dictionary containing node- and/or graph-level
representations. Inspect the selected model's documented return fields.

### GIN for molecular properties

The official property tutorial uses:

```python
model = models.GIN(
    input_dim=dataset.node_feature_dim,
    hidden_dims=[256, 256, 256, 256],
    short_cut=True,
    batch_norm=True,
    concat_hidden=True,
)
```

The pretraining tutorial includes bond features:

```python
model = models.GIN(
    input_dim=dataset.node_feature_dim,
    hidden_dims=[300, 300, 300, 300, 300],
    edge_input_dim=dataset.edge_feature_dim,
    batch_norm=True,
    readout="mean",
)
```

Use the exact feature configuration that produced
`dataset.node_feature_dim` and `dataset.edge_feature_dim`.

### RGCN for typed edges

The official generation and retrosynthesis tutorials use `RGCN`:

```python
model = models.RGCN(
    input_dim=dataset.node_feature_dim,
    hidden_dims=[256, 256, 256, 256],
    num_relation=dataset.num_bond_type,
    batch_norm=False,
)
```

`num_relation` must match the graph relation vocabulary. For molecule graphs in
these tutorials, it comes from `dataset.num_bond_type`.

### 3D and protein structure models

- `SchNet` requires a `node_position` graph attribute.
- `GearNet` is the documented geometry-aware relational model for protein
  structures.

Use graph-construction layers to create required spatial and sequential edges;
do not assume loading a PDB automatically creates every relation a structure
model expects.

## Protein sequence encoders

Documented classes and aliases include:

- `models.ESM` (`EvolutionaryScaleModeling`)
- `models.ProteinCNN`
- `models.ProteinResNet`
- `models.ProteinLSTM`
- `models.ProteinBERT`

The 0.2.1 ESM constructor is:

```python
model = models.ESM(
    path="~/model-weights/esm/",
    model="ESM-1b",
    readout="mean",
)
```

The released source supports `ESM-2-8M`, `ESM-2-35M`, `ESM-2-150M`,
`ESM-2-650M`, `ESM-2-3B`, and `ESM-2-15B`. These use `fair-esm==2.0.0`;
constructor calls download pretrained weights and remain illustrative here.
Do not use the unsupported
pattern `models.ESM(path="checkpoint-file.pt")`; `path` is the directory where
TorchDrug stores model weights.

Protein sequence encoders return residue and graph features. Respect the model's
maximum input length and tokenization behavior.

## Knowledge graph models

Embedding models:

- `models.TransE`
- `models.DistMult`
- `models.ComplEx`
- `models.SimplE`
- `models.RotatE`

Neural reasoning models:

- `models.NeuralLP` (alias of `NeuralLogicProgramming`)
- `models.KBGAT`

The official embedding tutorial uses:

```python
model = models.RotatE(
    num_entity=dataset.num_entity,
    num_relation=dataset.num_relation,
    embedding_dim=2048,
    max_score=9,
)
```

The official NeuralLP tutorial uses:

```python
model = models.NeuralLP(
    num_relation=dataset.num_relation,
    hidden_dim=128,
    num_step=3,
    num_lstm_layer=2,
)
```

Both are wrapped by `tasks.KnowledgeGraphCompletion`; model construction alone
does not define negative sampling or evaluation.

## Generative and self-supervised models

### GCPN

GCPN is exposed as a task rather than a `models.GCPN` class:

```python
task = tasks.GCPNGeneration(
    model,
    dataset.atom_types,
    max_edge_unroll=12,
    max_node=38,
    criterion="nll",
)
```

The `model` argument is the graph representation model, normally `RGCN` in the
official tutorial.

### GraphAF

GraphAF uses two flow models:

- node flow: `models.GraphAF(..., use_edge=False, ...)`
- edge flow: `models.GraphAF(..., use_edge=True, ...)`

Wrap both in:

```python
task = tasks.AutoregressiveGeneration(
    node_flow,
    edge_flow,
    max_node=38,
    max_edge_unroll=12,
    criterion="nll",
)
```

`models.GraphAF` is an alias for `GraphAutoregressiveFlow`. It is not itself the
training task.

### Self-supervised encoders

The official pretraining tutorial documents:

- `models.InfoGraph` wrapped by `tasks.Unsupervised`
- a base GNN wrapped directly by `tasks.AttributeMasking`

Other API-documented self-supervised components include `MultiviewContrast`.
Do not infer a task constructor from a paper name; check whether the component
lives under `models` or `tasks`.

## Model selection checklist

1. Identify the graph/data type.
2. Check required graph attributes and relation counts.
3. Build dimensions from the loaded dataset.
4. Confirm whether the algorithm is a model or a task.
5. Match checkpoint architecture and feature configuration exactly.
6. Wrap the model in the task used by the official tutorial or API.
7. Start with a small batch and one epoch before scaling.

## Source links

- [Model API](https://torchdrug.ai/docs/api/models.html)
- [Task API](https://torchdrug.ai/docs/api/tasks.html)
- [Property tutorial](https://torchdrug.ai/docs/tutorials/property_prediction.html)
- [Pretraining tutorial](https://torchdrug.ai/docs/tutorials/pretrain.html)
- [Generation tutorial](https://torchdrug.ai/docs/tutorials/generation.html)
- [Reasoning tutorial](https://torchdrug.ai/docs/tutorials/reasoning.html)
