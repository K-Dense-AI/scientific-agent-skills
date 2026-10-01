# Knowledge Graph Reasoning

The official
[TorchDrug 0.2.1 reasoning tutorial](https://torchdrug.ai/docs/tutorials/reasoning.html)
covers two workflows:

- knowledge graph embeddings with RotatE,
- neural inductive logic programming with NeuralLP.

Both use `tasks.KnowledgeGraphCompletion`.
Full benchmark runs are illustrative; a tiny local graph can verify batching
and loss/ranking semantics without downloading these datasets.

## Datasets

Documented knowledge graph datasets:

- `FB15k`: 14,951 entities, 1,345 relations, 592,213 triplets
- `FB15k237`: 14,541 entities, 237 relations, 310,116 triplets
- `WN18`: 40,943 entities, 18 relations, 151,442 triplets
- `WN18RR`: 40,943 entities, 11 relations, 93,003 triplets
- `Hetionet`: 45,158 entities, 24 relations, 2,025,177 triplets

Use predefined splits:

```python
from torchdrug import datasets

dataset = datasets.FB15k237("~/kg-datasets/")
train_set, valid_set, test_set = dataset.split()
```

## RotatE embedding workflow

### Model

```python
import torch
from torchdrug import core, models, tasks

model = models.RotatE(
    num_entity=dataset.num_entity,
    num_relation=dataset.num_relation,
    embedding_dim=2048,
    max_score=9,
)
```

`embedding_dim=2048` follows the tutorial and may be reduced for memory or speed.

### Task

```python
task = tasks.KnowledgeGraphCompletion(
    model,
    num_negative=256,
    adversarial_temperature=1,
)
```

- `num_negative` controls negative samples per positive.
- `adversarial_temperature` enables score-weighted negative sampling.

### Train and evaluate

```python
optimizer = torch.optim.Adam(task.parameters(), lr=2e-5)
solver = core.Engine(
    task,
    train_set,
    valid_set,
    test_set,
    optimizer,
    batch_size=1024,
)
solver.train(num_epoch=200)
solver.evaluate("valid")
```

Add `gpus=[0]` for a supported CUDA device. Reduce the epoch count for smoke
tests.

## NeuralLP workflow

NeuralLP learns weighted chain-like rules up to a configured maximum length.

```python
model = models.NeuralLP(
    num_relation=dataset.num_relation,
    hidden_dim=128,
    num_step=3,
    num_lstm_layer=2,
)

task = tasks.KnowledgeGraphCompletion(
    model,
    fact_ratio=0.75,
    num_negative=256,
    sample_weight=False,
)
```

`fact_ratio=0.75` reserves 75% of training facts for the background graph used
for reasoning and uses the remaining training triples as supervised labels.
`Engine` adopts that reduced training subset returned by `preprocess()`.

```python
optimizer = torch.optim.Adam(task.parameters(), lr=1e-3)
solver = core.Engine(
    task,
    train_set,
    valid_set,
    test_set,
    optimizer,
    batch_size=64,
)
solver.train(num_epoch=10)
solver.evaluate("valid")
```

## Other documented models

Embedding models:

- `models.TransE`
- `models.DistMult`
- `models.ComplEx`
- `models.SimplE`
- `models.RotatE`

Graph-attention model:

- `models.KBGAT`

Verify each constructor in the
[model API](https://torchdrug.ai/docs/api/models.html#knowledge-graph-reasoning-models).
Do not transfer argument names from PyKEEN, DGL-KE, or PyTorch Geometric.

## Task behavior

`KnowledgeGraphCompletion` owns:

- negative sampling,
- fact-graph construction,
- loss computation,
- head and tail prediction,
- filtered ranking evaluation.

Important constructor options include:

- `criterion`
- `metric`
- `num_negative`
- `margin`
- `adversarial_temperature`
- `strict_negative`
- `fact_ratio`
- `sample_weight`
- `filtered_ranking` (default `True`)
- `full_batch_eval`

TorchDrug 0.2.1 added full-batch evaluation support. Choose it according to graph
size and available memory.

## Evaluation

Use filtered ranking metrics:

- mean rank (MR)
- mean reciprocal rank (MRR)
- Hits@1
- Hits@3
- Hits@10

Filtered evaluation removes other known true triples before ranking. Preserve
training, validation, and test facts exactly as the task expects to avoid leakage
or incorrect filtering.

Also report:

- results by relation,
- head vs tail prediction,
- variance across seeds,
- memory/runtime settings,
- whether reciprocal relations were added.

## Biomedical use

Hetionet supports biomedical link-prediction experiments, but a high model score
does not establish a new treatment, causal mechanism, or validated association.

For drug-repurposing analysis:

1. define the exact relation being predicted,
2. preserve entity and relation type constraints,
3. exclude known positives correctly,
4. check for train/test leakage through inverse or duplicate relations,
5. calibrate or rank model scores,
6. validate candidates against independent evidence and domain experts.

TorchDrug's generic `KnowledgeGraphCompletion` API does not automatically apply
biomedical type constraints or causal interpretation.

## Common failures

### Entity/relation mismatch

Build model sizes from `dataset.num_entity` and `dataset.num_relation`.

### Evaluation out of memory

Lower batch size or disable full-batch evaluation. With `full_batch_eval=False`,
`num_negative` also sets the chunk size for scoring candidate entities during
evaluation. All entities are still ranked, and score/mask tensors scale with
batch size times the entity count; chunking does not make this sampled evaluation.

### NeuralLP produces invalid shapes

Use `num_relation=dataset.num_relation` and let
`KnowledgeGraphCompletion.preprocess()` construct the fact graph.

### Inflated metrics

Check for inverse-relation leakage, duplicate triples, accidental use of test
facts, and raw rather than filtered ranking.

## Source links

- [Reasoning tutorial](https://torchdrug.ai/docs/tutorials/reasoning.html)
- [Knowledge graph datasets](https://torchdrug.ai/docs/api/datasets.html#knowledge-graph-datasets)
- [Knowledge graph models](https://torchdrug.ai/docs/api/models.html#knowledge-graph-reasoning-models)
- [KnowledgeGraphCompletion task](https://torchdrug.ai/docs/api/tasks.html#knowledge-graph-completion)
