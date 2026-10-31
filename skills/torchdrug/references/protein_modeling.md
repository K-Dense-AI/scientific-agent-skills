# Protein Modeling

TorchDrug 0.2.1 documents protein data structures, datasets, sequence encoders,
and geometry-aware graph models in its
[data](https://torchdrug.ai/docs/api/data.html),
[dataset](https://torchdrug.ai/docs/api/datasets.html), and
[model](https://torchdrug.ai/docs/api/models.html) APIs. The primary tutorial
index focuses on molecular and knowledge-graph workflows, so avoid inventing a
protein tutorial API that upstream does not provide.

Large dataset and pretrained-weight examples are source-verified illustrations;
this review does not download protein archives or pretrained ESM weights.

## Build protein objects

### From sequence

```python
from torchdrug import data

protein = data.Protein.from_sequence(
    "MKTAYIAKQRQISFVKSHFSRQ",
    atom_feature=None,
    bond_feature=None,
    residue_feature="default",
)
print(protein.to_sequence())
```

For sequence-only work, setting atom and bond features to `None` avoids the cost
of constructing a full atom-level representation.
In that fast path, 0.2.1 converts unknown residue symbols to glycine with a
warning. Validate sequences against the supported 20-residue alphabet first;
do not allow `X`, gaps, or chain separators to become silently altered biology.
Also preserve the original sequence separately: the fast path creates no bonds,
so `to_sequence()` inserts component separators between residues (for example,
`"M.K.T.A.Y"`). It is not a faithful chain-annotated round trip of this input.

### From PDB

```python
protein = data.Protein.from_pdb(
    "protein.pdb",
    atom_feature="default",
    bond_feature="default",
    residue_feature="default",
)
```

Use trusted local PDB files and validate chain selection, missing residues,
alternate locations, and nonstandard residues before training.

Documented conversion methods include:

- `Protein.from_sequence`
- `Protein.from_pdb`
- `Protein.from_molecule`
- `Protein.to_sequence`
- `Protein.to_pdb`
- `Protein.to_molecule`

Packed equivalents operate on lists:

- `PackedProtein.from_sequence(sequences)`
- `PackedProtein.from_pdb(pdb_files)`
- `PackedProtein.from_molecule(mols)`

## Protein datasets

Documented dataset families include:

- Property / sequence: `BetaLactamase`, `BinaryLocalization`,
  `SubcellularLocalization`
- Function / structure: `EnzymeCommission`, `GeneOntology`, `AlphaFoldDB`
- Structure labels: `Fold`, `SecondaryStructure`
- Protein-protein: `HumanPPI`, `YeastPPI`, `PPIAffinity`
- Protein-ligand: `BindingDB`, `PDBBind`

Example:

```python
from torchdrug import datasets, transforms

dataset = datasets.EnzymeCommission(
    "~/protein-datasets/",
    atom_feature=None,
    bond_feature=None,
    residue_feature="default",
    transform=transforms.ProteinView(view="residue"),
)
train_set, valid_set, test_set = dataset.split()
```

Unlike sequence-only construction, loading a PDB with `atom_feature=None` still
creates atoms and an atom view. `ProteinView` exposes residue features as
`graph.node_feature` to sequence models. EC and GO samples contain a single
multi-hot `"targets"` tensor; see the matching task below. Keep `lazy=False`
(the default) for EnzymeCommission: its released lazy `get_item` passes the
options dictionary positionally to `Protein.from_pdb`, an upstream defect.

Class signatures differ. Options such as `branch`, `test_cutoff`, `lazy`, or
species/split IDs are dataset-specific; check the API before using them.

## Sequence encoders

### ESM

`models.ESM` is the alias for `EvolutionaryScaleModeling`. The constructor takes
a directory for downloaded weights, not a checkpoint filename:

```python
from torchdrug import models

model = models.ESM(
    path="~/model-weights/esm/",
    model="ESM-2-150M",
    readout="mean",
)
```

TorchDrug 0.2.1 supports these ESM-2 names:

- `ESM-2-8M`
- `ESM-2-35M`
- `ESM-2-150M`
- `ESM-2-650M`
- `ESM-2-3B`
- `ESM-2-15B`

It also supports `ESM-1b` and `ESM-1v`. Maximum sequence input is 1022 residues
before special tokens. Large checkpoints require substantial memory; start with
`ESM-2-8M` or `ESM-2-35M` for pipeline validation.
The wrapper warns and truncates each longer sequence to its **first** 1022
residues; the returned residue features no longer cover the original full chain.
Use an explicit cropping/chunking policy and retain residue offsets. Its `esm`
import comes from `fair-esm==2.0.0`, not the modern `esm` SDK. Checkpoint URLs are
public static files on `dl.fbaipublicfiles.com`; successful HEAD requests do not
verify their checksums or model inference.

### Other sequence models

Documented classes include:

- `models.ProteinCNN`
- `models.ProteinResNet`
- `models.ProteinLSTM`
- `models.ProteinBERT`

These models require explicit input/hidden dimensions. Derive input dimensions
from the dataset's residue feature configuration.

## Structure encoders

Documented structure-aware models include:

- `models.GearNet`
- `models.SchNet`
- general graph models such as `GCN`, `GAT`, `GIN`, and `RGCN`

`SchNet` requires `node_position`. `GearNet` requires a graph whose relation and
geometric feature configuration matches its constructor.

Use TorchDrug graph-construction and geometry layers to create sequential,
radius, and nearest-neighbor relations. Do not use a nonexistent
`protein.residue_graph(...)` method.

Before training a structure model, inspect:

```python
print(protein.num_node)
print(protein.num_residue)
print(protein.node_position.shape)
print(protein.residue_feature.shape)
```

Confirm whether nodes represent atoms or residues and ensure the model input
matches that choice.

## Property-prediction task

For the EnzymeCommission dataset above, use integer indices into its target
vector and a sequence encoder. This is an illustrative training setup:

```python
from torchdrug import models, tasks

model = models.ProteinCNN(
    input_dim=dataset[0]["graph"].residue_feature.shape[-1],
    hidden_dims=[64, 64],
    readout="mean",
)
task = tasks.MultipleBinaryClassification(
    model,
    task=list(range(len(dataset.tasks))),
    criterion="bce",
    metric=("auprc@micro", "f1_max"),
)
```

Construct an optimizer and `Engine` to preprocess/train this task. For datasets
that instead return separately named scalar targets, `PropertyPrediction` with
`task=dataset.tasks` is appropriate. Choose criteria from the actual target:

- binary or multi-label classification: BCE, AUPRC/AUROC
- multiclass classification: CE with `"acc"` or `"mcc"`
- regression: MSE, MAE/RMSE

Vector labels require the matching task even for a small dataset; target schema,
not dataset size, determines the choice. `MultipleBinaryClassification` does
not implement `PropertyPrediction`'s NaN label mask. Do not feed missing labels
as NaN or silently replace unknown annotation status with negative labels.

## Workflow checks

1. Decide sequence-only versus structure-aware modeling.
2. Configure protein features to match that representation.
3. Verify dataset splits and sequence identity cutoffs.
4. Check maximum sequence length before selecting ESM.
5. Build graph relations explicitly for structure models.
6. Derive dimensions from the loaded dataset.
7. Smoke-test one batch before long training.
8. Record checkpoint name, feature settings, split, and TorchDrug version.

## Common failures

### ESM constructor error

Use `models.ESM(path=<directory>, model=<supported-name>)`. Do not pass a
downloaded `.pt` filename as `path`.

### Out-of-memory error

Choose a smaller ESM model, reduce batch size, crop or filter long sequences, or
freeze the encoder and precompute embeddings.

### Missing coordinates

Sequence-created proteins do not acquire experimental 3D coordinates. Load a PDB
or another validated structure source before using coordinate-dependent models.

### Relation mismatch

Build the same relation types expected by the structure model and set
`num_relation` accordingly.

## Source links

- [Protein data API](https://torchdrug.ai/docs/api/data.html#protein)
- [Protein datasets](https://torchdrug.ai/docs/api/datasets.html#protein-property-prediction-datasets)
- [Protein sequence encoders](https://torchdrug.ai/docs/api/models.html#protein-sequence-encoders)
- [Graph neural networks](https://torchdrug.ai/docs/api/models.html#graph-neural-networks)
- [TorchDrug 0.2.1 release notes](https://github.com/DeepGraphLearning/torchdrug/releases/tag/v0.2.1)
