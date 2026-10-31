# Datasets

Use the
[TorchDrug 0.2.1 dataset reference](https://torchdrug.ai/docs/api/datasets.html)
as the class inventory and signature source. Dataset constructors download and
cache data under the path supplied by the caller.

These are release-era loaders, not live database clients. There is no API token,
query pagination, or current-release discovery. Constructors can fetch large
archives as a side effect. Check the selected loader's source URL, expected
checksum, size, and dataset license before starting a download.

## ClinTox download repair

The 0.2.1 class embeds a legacy DeepChem HTTP URL that returned HTTP 400 during
this review. DeepChem's current official loader uses the HTTPS URL below. Its
19,870-byte gzip was fetched and matches TorchDrug's MD5 exactly; it has 1,484
raw rows before molecular sanitization/filtering. Populate the cache once before
running any ClinTox example in this skill:

```python
from pathlib import Path
from torchdrug import datasets, utils

cache = Path("~/molecule-datasets/").expanduser()
cache.mkdir(parents=True, exist_ok=True)
archive = utils.download(
    "https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/clintox.csv.gz",
    str(cache),
    md5=datasets.ClinTox.md5,
)
if utils.compute_md5(archive) != datasets.ClinTox.md5:
    raise RuntimeError("ClinTox checksum mismatch; do not train on this cache")
```

`utils.download(..., md5=...)` checks an existing cache before deciding whether
to fetch. In this release it does **not** verify freshly downloaded bytes, hence
the explicit post-download check. MD5 here identifies the historical benchmark
asset; record a SHA-256 for project provenance as well.

The old URLs for BACE, BBBP, HIV, MUV, SIDER, Tox21, ToxCast, QM8, QM9, and
Lipophilicity also failed during endpoint probes. Do not blindly replace a host
and assume equivalent contents: verify each current official loader and checksum
or load a separately versioned local dataset with `data.MoleculeDataset.load_csv`.
FreeSolv's old S3 route returned an unresolved HTTP 301. These are observed
download failures, not evidence that the datasets themselves have been retired.

## Dataset families

### Molecule property prediction

Documented classes include:

- Classification: `BACE`, `BBBP`, `ClinTox`, `HIV`, `MUV`, `SIDER`, `Tox21`,
  `ToxCast`
- Regression / quantum properties: `FreeSolv`, `Lipophilicity`, `QM8`, `QM9`,
  `PCQM4M`
- Pretraining / generation: `ChEMBLFiltered`, `ZINC250k`, `ZINC2m`, `MOSES`

The official property tutorial uses `ClinTox`; the pretraining tutorial uses
`ClinTox` for a small demonstration and recommends larger data such as `ZINC2m`
for real pretraining; the generation tutorial uses `ZINC250k`.

```python
from torchdrug import datasets

dataset = datasets.ClinTox(
    "~/molecule-datasets/",
    atom_feature="default",
    bond_feature="default",
)
print(dataset.tasks)
print(dataset.node_feature_dim)
print(dataset.edge_feature_dim)
```

Common molecule options include `atom_feature`, `bond_feature`, `mol_feature`,
`with_hydrogen`, and `kekulize`. Availability varies by class; inspect the class
signature before adding options.

### Protein properties and structure

Documented families include:

- Sequence / property: `BetaLactamase`, `BinaryLocalization`,
  `SubcellularLocalization`
- Structure / function: `EnzymeCommission`, `GeneOntology`, `AlphaFoldDB`
- Structure labels: `Fold`, `SecondaryStructure`
- Protein-protein: `HumanPPI`, `YeastPPI`, `PPIAffinity`
- Protein-ligand: `BindingDB`, `PDBBind`

```python
dataset = datasets.EnzymeCommission(
    "~/protein-datasets/",
    atom_feature=None,
    bond_feature=None,
    residue_feature="default",
)
train_set, valid_set, test_set = dataset.split()
```

Protein datasets can be expensive to parse. Where supported, `lazy=True` trades
lower startup memory for slower item loading. For sequence-only models, omitting
atom and bond features avoids unnecessary atom-level construction.

### Knowledge graphs

Documented classes:

- `FB15k`
- `FB15k237`
- `WN18`
- `WN18RR`
- `Hetionet`

```python
dataset = datasets.FB15k237("~/kg-datasets/")
train_set, valid_set, test_set = dataset.split()

print(dataset.num_entity)
print(dataset.num_relation)
```

These datasets provide predefined benchmark splits. Preserve those splits for
comparable evaluation.

### Retrosynthesis

`USPTO50k` contains 50,017 reactions across 10 reaction classes. The official
G2Gs workflow loads two views:

```python
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
```

Reaction mode yields reactant/product pairs for center identification. Synthon
mode yields reactant/synthon pairs for synthon completion.

## Splitting correctly

Some benchmark datasets expose predefined splits:

```python
train_set, valid_set, test_set = dataset.split()
```

For the property-prediction tutorial's random 80/10/10 split, use PyTorch:

```python
import torch

lengths = [int(0.8 * len(dataset)), int(0.1 * len(dataset))]
lengths.append(len(dataset) - sum(lengths))
train_set, valid_set, test_set = torch.utils.data.random_split(dataset, lengths)
```

Do not assume `dataset.split([0.8, 0.1, 0.1])` is a documented universal API.

For paired retrosynthesis views, reset the same seed before each `split()`:

```python
torch.manual_seed(1)
reaction_train, reaction_valid, reaction_test = reaction_dataset.split()
torch.manual_seed(1)
synthon_train, synthon_valid, synthon_test = synthon_dataset.split()
```

The two views can have different row counts because one reaction yields several
synthons. This is source-reaction partition alignment, not row-by-row alignment.
Verify it explicitly after preprocessing/filtering:

```python
def source_ids(dataset, subset):
    return {dataset.targets["sample id"][i] for i in subset.indices}

reaction_parts = (reaction_train, reaction_valid, reaction_test)
synthon_parts = (synthon_train, synthon_valid, synthon_test)
ids = [source_ids(reaction_dataset, part) for part in reaction_parts]
for expected, part in zip(ids, synthon_parts):
    if expected != source_ids(synthon_dataset, part):
        raise ValueError("Reaction/synthon source IDs differ; split by common IDs")
if any(ids[i] & ids[j] for i in range(3) for j in range(i + 1, 3)):
    raise ValueError("Reaction source IDs leak across partitions")
```

## Feature configuration

Dataset dimensions depend on feature choices. Construct models from the loaded
dataset rather than hard-coding dimensions:

```python
from torchdrug import models

model = models.GIN(
    input_dim=dataset.node_feature_dim,
    hidden_dims=[256, 256, 256],
    edge_input_dim=dataset.edge_feature_dim,
)
```

Generation and retrosynthesis often require specialized feature sets:

- Pretraining: `atom_feature="pretrain"`, `bond_feature="pretrain"`
- GCPN / GraphAF: `atom_feature="symbol"`, `kekulize=True`
- Center identification: `atom_feature="center_identification"`
- Synthon completion: `atom_feature="synthon_completion"`

Do not mix checkpoint weights across incompatible feature configurations.

## Data integrity and evaluation

- Cache datasets in a controlled project or user data directory.
- Record TorchDrug version, feature arguments, split method, and random seed.
- Preserve predefined KG splits.
- For molecular benchmarks, use the split protocol required by the benchmark;
  do not claim a random split is a scaffold split.
- Inspect downloaded data licenses and provenance before redistribution.
- Validate labels, missing-value masks, and task names before training.
- `EnzymeCommission` and `GeneOntology` return `sample["targets"]` vectors;
  their `dataset.tasks` names are not separate sample dictionary keys. Use
  `MultipleBinaryClassification(task=list(range(len(dataset.tasks))))`.
- `AlphaFoldDB` in this release is pinned to historical **v2** proteome archives,
  not the current AlphaFold DB. The embedded zebrafish URL returned 404; do not
  silently relabel a newer archive as v2.
- HEAD probes reached ZINC250k, USPTO50k, all FB15k237 split files, and the
  EnzymeCommission archive (about 1 GB), but do not validate bytes or parsing.
  None of those large datasets or pretrained weights were downloaded in this audit.

## Source links

- [Dataset API](https://torchdrug.ai/docs/api/datasets.html)
- [Property prediction tutorial](https://torchdrug.ai/docs/tutorials/property_prediction.html)
- [Pretraining tutorial](https://torchdrug.ai/docs/tutorials/pretrain.html)
- [Generation tutorial](https://torchdrug.ai/docs/tutorials/generation.html)
- [Retrosynthesis tutorial](https://torchdrug.ai/docs/tutorials/retrosynthesis.html)
- [Knowledge graph tutorial](https://torchdrug.ai/docs/tutorials/reasoning.html)
- [Current DeepChem ClinTox loader](https://github.com/deepchem/deepchem/blob/master/deepchem/molnet/load_function/clintox_datasets.py)
- [Released dataset source](https://github.com/DeepGraphLearning/torchdrug/tree/v0.2.1/torchdrug/datasets)
