# Core Concepts and Data Structures

This reference follows the
[TorchDrug 0.2.1 data API](https://torchdrug.ai/docs/api/data.html),
[quick start](https://torchdrug.ai/docs/quick_start.html), and
[notes](https://torchdrug.ai/docs/notes/).
External-file and checkpoint examples require user-supplied trusted inputs;
they are illustrative unless listed in [review evidence](review.md).

## Component hierarchy

TorchDrug separates four concerns:

- `torchdrug.data`: tensor-backed `Graph`, `Molecule`, `Protein`, and packed
  variants.
- `torchdrug.datasets`: downloadable datasets whose samples contain graphs and
  targets.
- `torchdrug.models`: reusable graph, sequence, embedding, flow, and
  self-supervised encoders.
- `torchdrug.tasks`: objectives that wrap models and implement prediction, loss,
  and evaluation.
- `torchdrug.core.Engine`: preprocessing, batching, optimization, checkpointing,
  and evaluation.

Keep these layers separate. A model creates representations; a task defines what
to learn; an engine executes the experiment.

## Graphs and molecules

```python
import torchdrug as td
from torchdrug import data

edge_list = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0]]
graph = data.Graph(edge_list, num_node=6)

mol = data.Molecule.from_smiles(
    "CCOC(=O)N",
    atom_feature="default",
    bond_feature="default",
)
print(mol.node_feature.shape)
print(mol.edge_feature.shape)

node_in, node_out, _ = mol.edge_list.t()
carbon_edge = (mol.atom_type[node_in] == td.CARBON) | (
    mol.atom_type[node_out] == td.CARBON
)
carbon_subgraph = mol.edge_mask(carbon_edge)
```

Molecular bonds are represented by two directed edges. Do not assume a stable
ordering of those edges.

Useful conversions:

- `data.Molecule.from_smiles(smiles)`
- `data.Molecule.from_molecule(rdkit_mol)`
- `molecule.to_smiles()`
- `molecule.to_molecule()`
- `data.PackedMolecule.from_smiles(smiles_list)`
- `data.PackedMolecule.from_molecule(rdkit_mols)`

`PackedMolecule.to_smiles()` and `.to_molecule()` return lists.

## Proteins

```python
from torchdrug import data

sequence_protein = data.Protein.from_sequence(
    "MKTAYIAKQRQISFVKSHFSRQ",
    atom_feature=None,
    bond_feature=None,
    residue_feature="default",
)
structure_protein = data.Protein.from_pdb(
    "protein.pdb",
    residue_feature="default",
)

print(sequence_protein.to_sequence())
```

For sequence-only work, setting `atom_feature=None` and `bond_feature=None`
avoids constructing unnecessary atom-level features and can substantially reduce
loading cost.
The fast path has no bonds: `to_sequence()` consequently inserts dots between
residues. Preserve the input sequence and chain boundaries separately. Unknown
symbols become glycine with a warning; reject or explicitly map ambiguous
residues before construction. See [protein modeling](protein_modeling.md).

Documented protein constructors and conversions include:

- `Protein.from_sequence`
- `Protein.from_pdb`
- `Protein.from_molecule`
- `Protein.to_sequence`
- `Protein.to_pdb`
- `Protein.to_molecule`

Protein graph construction is handled by the documented geometry/graph
construction layers. `Protein` does not provide a `residue_graph()` method in
0.2.1.

## Packed graphs and collation

Graphs of different sizes are packed into a block-diagonal representation:

```python
from torchdrug import data

graphs = [
    data.Molecule.from_smiles("CCO"),
    data.Molecule.from_smiles("c1ccccc1"),
]
batch = data.Graph.pack(graphs)
restored = batch.unpack()
```

For dataset samples, use:

```python
batch = data.graph_collate(samples)
```

`graph_collate` recursively collates nested containers and uses `Graph.pack` for
graph values. Prefer it to PyTorch's default collator for manual inference.

Packed graph operations include:

- `subbatch(index)` for selecting graphs
- `node_mask(index, compact=...)`
- `edge_mask(index)`
- `graph_mask(index, compact=...)`
- `repeat(count)` / `repeat_interleave(repeats)`
- `unpack()`

## Attributes and references

TorchDrug graph attributes carry semantic scopes. When adding custom attributes,
register them in the matching context:

```python
with mol.atom():
    mol.is_carbon = mol.atom_type == td.CARBON

with mol.edge():
    mol.is_single_bond = mol.bond_type == td.SINGLE
```

Use node, edge, graph, and reference contexts so masking, packing, and device
transfer update custom values correctly. See
[Deal with References](https://torchdrug.ai/docs/notes/reference.html).

## Model interface

Graph representation models use this general call shape:

```python
output = model(graph, graph.node_feature)
graph_feature = output["graph_feature"]
node_feature = output["node_feature"]
```

Protein sequence models may return `residue_feature` instead of `node_feature`.
Inspect the selected model's API page rather than assuming every model returns
the same keys.

Most models accept optional `all_loss` and `metric` accumulators:

```python
output = model(graph, graph.node_feature, all_loss=all_loss, metric=metric)
```

Tasks use those accumulators for auxiliary losses and metrics.

## Task and Engine lifecycle

The normal lifecycle is:

1. construct model,
2. construct task,
3. construct optimizer over `task.parameters()`,
4. construct `core.Engine`,
5. call `solver.train()` and `solver.evaluate()`.

When `Engine` is created, it calls task preprocessing against the supplied
train/validation/test sets. This matters because tasks may infer target
statistics or metadata during preprocessing.

```python
import torch

optimizer = torch.optim.Adam(task.parameters(), lr=1e-3)
solver = core.Engine(
    task,
    train_set,
    valid_set,
    test_set,
    optimizer,
    batch_size=128,
)
solver.train(num_epoch=10)
metrics = solver.evaluate("valid")
```

Use `gpus=[0]` for one supported CUDA device. Omit it on CPU. For manual nested
batches, `torchdrug.utils.cuda(batch)` moves all tensors and graphs together.

## Configuration and checkpoints

`core.Configurable` serializes component constructor configuration:

```python
import json
from torchdrug import core

with open("solver.json", "w") as fout:
    json.dump(solver.config_dict(), fout)
solver.save("solver.pth")

with open("solver.json") as fin:
    restored_solver = core.Configurable.load_config_dict(json.load(fin))
restored_solver.load("solver.pth")
```

For transfer learning, a solver checkpoint stores model state under `"model"`:

```python
checkpoint = torch.load("pretrained.pth", map_location="cpu")["model"]
transfer = task.load_state_dict(checkpoint, strict=False)
print(transfer.missing_keys, transfer.unexpected_keys)
```

Use `strict=False` only when intentionally transferring a compatible subset, such
as a pretrained encoder into a property-prediction task.
Verify that encoder keys actually matched: InfoGraph introduces an additional
`model.` nesting level compared with AttributeMasking. Never count a successful
`strict=False` call as proof of weight transfer. PyTorch 2.0 checkpoint loading
uses pickle; only load files from trusted sources. The special `Retrosynthesis`
task requires the two individual subtask checkpoints, not a generic combined
round trip (see [retrosynthesis](retrosynthesis.md#checkpoint-loading)).

## Feature naming in 0.2.1

Prefer:

- `atom_feature`
- `bond_feature`
- `residue_feature`
- `mol_feature`

The older `node_feature`, `edge_feature`, and `graph_feature` constructor names
are deprecated aliases where documented. Runtime properties such as
`dataset.node_feature_dim` and `graph.node_feature` remain valid.
