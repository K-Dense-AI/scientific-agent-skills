# Molecular Generation

The official
[TorchDrug 0.2.1 generation tutorial](https://torchdrug.ai/docs/tutorials/generation.html)
implements GCPN and GraphAF on ZINC250k. It pretrains with negative
log-likelihood (NLL), then optionally fine-tunes with proximal policy optimization
(PPO) for QED or penalized logP.
Full ZINC250k training and generation are illustrative. Source review and tiny
CPU checks do not establish validity rates, optimization quality, or convergence.

## Shared dataset

```python
from torchdrug import datasets

dataset = datasets.ZINC250k(
    "~/molecule-datasets/",
    kekulize=True,
    atom_feature="symbol",
)
```

The tutorial assumes:

- maximum graph size: 38 atoms
- 9 atom types
- 3 bond types
- `max_edge_unroll=12`

If using another dataset, recompute these assumptions instead of copying the
ZINC250k values.

## GCPN

### Pretraining task

```python
import torch
from torchdrug import core, models, tasks

model = models.RGCN(
    input_dim=dataset.node_feature_dim,
    num_relation=dataset.num_bond_type,
    hidden_dims=[256, 256, 256, 256],
    batch_norm=False,
)
task = tasks.GCPNGeneration(
    model,
    dataset.atom_types,
    max_edge_unroll=12,
    max_node=38,
    criterion="nll",
)

optimizer = torch.optim.Adam(task.parameters(), lr=1e-3)
solver = core.Engine(
    task,
    dataset,
    None,
    None,
    optimizer,
    batch_size=128,
    log_interval=10,
)
solver.train(num_epoch=1)
solver.save("gcpn-zinc250k.pth")
```

Use `gpus=(0,)` or `gpus=[0]` only on supported CUDA hardware.

### Generate samples

```python
solver.load("gcpn-zinc250k.pth")
task.eval()
results = task.generate(num_sample=32, max_resample=5)
print(results.to_smiles())
```

`results` is a packed molecule object. Validate all returned structures before
downstream use. Set `task.eval()` before generation; both generation methods
disable gradients internally but do not automatically disable training-mode
batch normalization. Record requested/returned counts and bounded resampling.

### Goal-directed fine-tuning

The documented optimization tasks are `"qed"` and `"plogp"`. The task does not
accept an arbitrary `reward_function=` callback in 0.2.1.

```python
task = tasks.GCPNGeneration(
    model,
    dataset.atom_types,
    max_edge_unroll=12,
    max_node=38,
    task="plogp",
    criterion="ppo",
    reward_temperature=1,
    agent_update_interval=3,
    gamma=0.9,
)

optimizer = torch.optim.Adam(task.parameters(), lr=1e-5)
solver = core.Engine(
    task,
    dataset,
    None,
    None,
    optimizer,
    batch_size=16,
    log_interval=10,
)
solver.load("gcpn-zinc250k.pth", load_optimizer=False)
solver.train(num_epoch=10)
```

For mixed supervised/RL training, the tutorial also uses:

```python
criterion = ("ppo", "nll")
```

or a weighted criterion mapping where supported by the task.

## GraphAF

GraphAF has three distinct layers:

1. an `RGCN` representation model,
2. node and edge flow models exposed as `models.GraphAF`,
3. `tasks.AutoregressiveGeneration` as the training objective.

The representation model uses discrete atom-type input:

```python
model = models.RGCN(
    input_dim=dataset.num_atom_type,
    num_relation=dataset.num_bond_type,
    hidden_dims=[256, 256, 256],
    batch_norm=True,
)
```

Create the node and edge priors exactly as shown in the upstream tutorial, then
construct one flow for nodes and one for edges:

```python
from torchdrug.layers import distribution

num_atom_type = dataset.num_atom_type
num_bond_type = dataset.num_bond_type + 1  # one extra class for no edge

node_prior = distribution.IndependentGaussian(
    torch.zeros(num_atom_type),
    torch.ones(num_atom_type),
)
edge_prior = distribution.IndependentGaussian(
    torch.zeros(num_bond_type),
    torch.ones(num_bond_type),
)
node_flow = models.GraphAF(
    model,
    node_prior,
    num_layer=12,
)
edge_flow = models.GraphAF(
    model,
    edge_prior,
    use_edge=True,
    num_layer=12,
)

task = tasks.AutoregressiveGeneration(
    node_flow,
    edge_flow,
    max_node=38,
    max_edge_unroll=12,
    criterion="nll",
)
```

Do not omit the documented prior construction. The node and edge prior shapes
must match the dataset's atom and bond vocabularies.

Train and generate through the task:

```python
optimizer = torch.optim.Adam(task.parameters(), lr=1e-3)
solver = core.Engine(
    task,
    dataset,
    None,
    None,
    optimizer,
    batch_size=128,
    log_interval=10,
)
solver.train(num_epoch=10)
solver.save("graphaf-zinc250k.pth")

solver.load("graphaf-zinc250k.pth")
task.eval()
results = task.generate(num_sample=32)
print(results.to_smiles())
```

For PPO fine-tuning, rebuild `AutoregressiveGeneration` with `task="qed"` or
`task="plogp"`, a PPO criterion, and the tutorial's reward/baseline settings;
then load the pretrained checkpoint with `load_optimizer=False`.

## What the API does not provide

Avoid these unsupported patterns:

```python
# Not a TorchDrug 0.2.1 API
tasks.GCPNGeneration(model, reward_function=my_reward, criterion="ppo")
```

TorchDrug 0.2.1's built-in generation task names are limited to QED and penalized
logP. A custom objective requires extending the task implementation rather than
passing a callback shown in another library.

The tutorial does not document generic scaffold-conditioned or
fragment-conditioned constructors. Do not claim those capabilities without a
separate implementation.

## Evaluation and safety

At minimum report:

- validity
- uniqueness
- novelty against the training set
- duplicate-aware property distributions
- failure and resampling rates

Also:

- canonicalize and sanitize with a chemistry toolkit,
- reject disconnected or chemically implausible structures as appropriate,
- screen structural alerts and undesirable substructures,
- assess synthetic accessibility separately,
- avoid presenting QED or penalized logP as evidence of efficacy or safety,
- keep generated structures out of automated synthesis without expert review.

## Source links

- [Generation tutorial](https://torchdrug.ai/docs/tutorials/generation.html)
- [Generation benchmark](https://torchdrug.ai/docs/benchmark/generation.html)
- [Generation task API](https://torchdrug.ai/docs/api/tasks.html#molecule-generation-tasks)
- [Flow model API](https://torchdrug.ai/docs/api/models.html#normalizing-flows)
