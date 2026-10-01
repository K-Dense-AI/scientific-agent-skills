# Retrosynthesis

The official
[TorchDrug 0.2.1 retrosynthesis tutorial](https://torchdrug.ai/docs/tutorials/retrosynthesis.html)
implements the G2Gs workflow:

1. identify reaction centers,
2. split products into synthons,
3. complete synthons into reactants,
4. combine both trained tasks for end-to-end prediction.

This is a single-step reactant prediction pipeline. Multi-step route search,
commercial availability, conditions, yields, and cost optimization are not
provided by `tasks.Retrosynthesis`.
The long training/beam-search examples are source-verified illustrations, not
completed benchmark experiments from this review.

## Prepare synchronized datasets

```python
import torch
from torchdrug import datasets

reaction_dataset = datasets.USPTO50k(
    "~/molecule-datasets/",
    atom_feature="center_identification",
    kekulize=True,
)
synthon_dataset = datasets.USPTO50k(
    "~/molecule-datasets/",
    as_synthon=True,
    atom_feature="synthon_completion",
    kekulize=True,
)

torch.manual_seed(1)
reaction_train, reaction_valid, reaction_test = reaction_dataset.split()
torch.manual_seed(1)
synthon_train, synthon_valid, synthon_test = synthon_dataset.split()
```

The repeated seed follows upstream's split protocol. Verify source `"sample id"`
sets as shown in [datasets](datasets.md#splitting-correctly), because filtering
or different graph-conversion outcomes can break alignment. Row counts across
the two views need not match.

- Reaction mode stores `(reactants, product)` pairs.
- Synthon mode stores `(reactant, synthon)` pairs.

## Center identification

The official tutorial uses RGCN and three feature groups:

```python
from torchdrug import core, models, tasks

reaction_model = models.RGCN(
    input_dim=reaction_dataset.node_feature_dim,
    hidden_dims=[256, 256, 256, 256, 256, 256],
    num_relation=reaction_dataset.num_bond_type,
    concat_hidden=True,
)
reaction_task = tasks.CenterIdentification(
    reaction_model,
    feature=("graph", "atom", "bond"),
)

reaction_optimizer = torch.optim.Adam(
    reaction_task.parameters(),
    lr=1e-3,
)
reaction_solver = core.Engine(
    reaction_task,
    reaction_train,
    reaction_valid,
    reaction_test,
    reaction_optimizer,
    batch_size=128,
)
reaction_solver.train(num_epoch=50)
reaction_solver.evaluate("valid")
reaction_solver.save("g2gs-reaction.pth")
```

`CenterIdentification` predicts reaction centers. Its
`predict_synthon(batch, k=...)` method returns **one dictionary**, despite the
release docstring's `list of dict` annotation. Its keys are `synthon`,
`num_synthon`, `reaction_center`, `log_likelihood`, and `reaction`; packed graph
attributes carry product/split IDs.

## Synthon completion

The official tutorial again uses RGCN:

```python
synthon_model = models.RGCN(
    input_dim=synthon_dataset.node_feature_dim,
    hidden_dims=[256, 256, 256, 256, 256, 256],
    num_relation=synthon_dataset.num_bond_type,
    concat_hidden=True,
)
synthon_task = tasks.SynthonCompletion(
    synthon_model,
    feature=("graph",),
)

synthon_optimizer = torch.optim.Adam(
    synthon_task.parameters(),
    lr=1e-3,
)
synthon_solver = core.Engine(
    synthon_task,
    synthon_train,
    synthon_valid,
    synthon_test,
    synthon_optimizer,
    batch_size=128,
)
synthon_solver.train(num_epoch=10)
synthon_solver.evaluate("valid")
synthon_solver.save("g2gs-synthon.pth")
```

Do not substitute a GIN constructor copied from another implementation unless
you intentionally redesign and validate the model.

## End-to-end task

Combine the **tasks**, not the raw models:

```python
task = tasks.Retrosynthesis(
    reaction_task,
    synthon_task,
    center_topk=2,
    num_synthon_beam=5,
    max_prediction=10,
)
```

If neither subtask has been attached to an `Engine`, preprocess them manually
before composition:

```python
reaction_task.preprocess(reaction_train, None, None)
synthon_task.preprocess(synthon_train, None, None)
```

The `Retrosynthesis` constructor accepts:

- `center_identification`
- `synthon_completion`
- `center_topk`
- `num_synthon_beam`
- `max_prediction`
- top-k metrics

It does not accept `model=`, `synthon_model=`, or a raw GNN pair.

## Checkpoint loading

The official workflow saves each subtask and loads checkpoints without optimizer
state when composing the pipeline:

```python
optimizer = torch.optim.Adam(task.parameters(), lr=1e-3)
solver = core.Engine(
    task,
    reaction_train,
    reaction_valid,
    reaction_test,
    optimizer,
    batch_size=32,
)
solver.load("g2gs-reaction.pth", load_optimizer=False)
solver.load("g2gs-synthon.pth", load_optimizer=False)
solver.evaluate("valid")
```

Keep model architectures, feature sets, and dataset metadata identical to the
training run. The composite's `load_state_dict` matches the exact key set of one
subtask and requires `strict=True`; it cannot restore its own combined state dict
through this override. Keep the two individual solver checkpoints. Load only
trusted files because this PyTorch 2.0 path uses pickle.

## Prediction output

The end-to-end task returns packed reactant predictions and a count per input:

```python
from torchdrug import data

batch = data.graph_collate([reaction_valid[i] for i in range(min(4, len(reaction_valid)))])
task.eval()
with torch.no_grad():
    predictions, num_prediction = task.predict(batch)

top1_index = num_prediction.cumsum(0) - num_prediction
for index, count in zip(top1_index.tolist(), num_prediction.tolist()):
    if count == 0:
        print("No reactant prediction")
        continue
    reactants = predictions[index].connected_components()[0]
    print(reactants.to_smiles())
```

Call `utils.cuda` only when the task/models are on CUDA. Keep the batch on CPU
for CPU execution.
Validate that `len(num_prediction)` equals the number of input products and
that `num_prediction.sum() == len(predictions)` before associating outputs with
inputs. Empty beam-search results may also raise inside the released task;
record these failures rather than reporting a candidate for the next product.

## Evaluation

The end-to-end task supports top-k exact-match metrics such as top-1, top-3,
top-5, and top-10. Also inspect:

- chemical validity,
- duplicate predictions,
- performance by reaction class,
- atom-map consistency,
- stereochemistry retention,
- uncertainty or score gaps.

Top-k exact match against USPTO50k is not proof that a reaction is practical.

## Scope and safety

TorchDrug's tutorial predicts reactant connectivity. It does not directly
predict:

- reagents, catalysts, solvent, temperature, or pressure,
- yield or selectivity,
- commercial availability,
- multi-step search trees,
- process safety or scale-up feasibility.

Treat outputs as model proposals requiring forward validation, literature
precedent, and expert chemistry review.

## Common failures

### Reaction and synthon samples do not align

Reset the same seed immediately before each `split()`.

### Feature dimension mismatch

Use the dedicated `center_identification` and `synthon_completion` atom features
and derive model dimensions from each corresponding dataset.

### End-to-end constructor error

Pass `reaction_task` and `synthon_task`, not their models.

### Uninitialized metadata

Construct each subtask's engine first or call `preprocess()` manually.

## Source links

- [Retrosynthesis tutorial](https://torchdrug.ai/docs/tutorials/retrosynthesis.html)
- [Retrosynthesis tasks](https://torchdrug.ai/docs/api/tasks.html#retrosynthesis-tasks)
- [USPTO50k dataset](https://torchdrug.ai/docs/api/datasets.html#uspto50k)
