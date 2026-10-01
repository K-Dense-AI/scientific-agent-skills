# Additional DeepChem workflows

All templates here target stable 2.8.0. External-data/backend-dependent examples are
illustrative unless [review.md](review.md) lists an executed check. Use the executable
scripts for molecular property training; the reference contracts in
[api_reference.md](api_reference.md) apply to every route.

## 1. Property prediction and 2. MoleculeNet benchmarks

Follow [typical_workflows.md](typical_workflows.md). Define one consistent target
family per model, preserve missing-label masks, and use one feature representation
throughout training and prediction. Never combine a toxicity label and a solubility
value in a single regression example without a justified multi-head loss.

For a binary graph benchmark, the input must match the selected Torch model:

```python
# Illustrative: downloads BBBP and requires compatible Torch/DGL/DGL-LifeSci.
import deepchem as dc
featurizer = dc.feat.MolGraphConvFeaturizer()
tasks, datasets, transformers = dc.molnet.load_bbbp(
    featurizer=featurizer, splitter='scaffold', reload=True)
train, valid, test = datasets
model = dc.models.GCNModel(n_tasks=len(tasks), mode='classification')
model.fit(train, nb_epoch=20)
metric = dc.metrics.Metric(dc.metrics.roc_auc_score)
# Inspect class support in each task before interpreting this aggregate.
score = model.evaluate(test, [metric], transformers=transformers)
```

## 3. Hyperparameter search

The following uses numeric data and the real callable/return contract. `train` and
`valid` must already be independently defined, fully labeled single-task datasets;
this template minimizes original-unit MAE. The test split is untouched.

```python
import deepchem as dc
from sklearn.ensemble import RandomForestRegressor

def builder(n_estimators, max_depth, model_dir=None):
    estimator = RandomForestRegressor(n_estimators=n_estimators,
                                      max_depth=max_depth, random_state=7)
    return dc.models.SklearnModel(estimator, model_dir=model_dir)

search = dc.hyper.GridHyperparamOpt(builder)
metric = dc.metrics.Metric(dc.metrics.mean_absolute_error)
best_model, best_params, all_scores = search.hyperparam_search(
    {'n_estimators': [8, 16], 'max_depth': [2, None]},
    train, valid, metric, output_transformers=[], use_max=False)
print(best_params, all_scores)
```

## 4. Transfer learning

Use the shipped transfer script to construct HF network/tokenizer objects or load
a compatible GROVER encoder component before training. `model_dir` alone loads
nothing. The model card for `seyonec/ChemBERTa-zinc-base-v1` describes a RoBERTa
encoder trained on 100k ZINC strings, not a 77M-molecule ChemBERTa model.
[ChemBERTa card](https://huggingface.co/seyonec/ChemBERTa-zinc-base-v1)

The current [MoLFormer card](https://huggingface.co/ibm-research/MoLFormer-XL-both-10pct)
identifies the 10% ZINC/10% PubChem variant and its Transformers 5 implementation.
For Transformers 4 it specifies `revision='compat-v4'`. Resolve that branch and pass
its immutable commit SHA to the bundled helper. Record the resolved commit,
review its repository code before `trust_remote_code=True`, and match chemical
canonicalization to the encoder's training inputs. A newly initialized property
head is expected; it has not inherited measured property calibration.

The helper requires a full commit SHA whenever repository code is enabled, following
the [Hugging Face custom-model revision guidance](https://huggingface.co/docs/transformers/models).

GROVER checkpoint architecture, featurization and tensor dimensions must match.
Only the encoder is restored by the shipped helper; this is deliberate transfer
into a new task head. A synthetic checkpoint round-trip verifies loading mechanics,
not any public pretrained model's performance.
[Released GROVER implementation](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/models/torch_models/grover.py)

## 5. Molecular generation

`BasicMolGANModel` consumes graph tensors, not a normal GraphConv dataset. Use
`MolGanFeaturizer`, check atom vocabulary and maximum atom count, then one-hot encode
adjacency bond categories and node categories. The Torch `fit_gan` consumes a
batch iterator of `{gan.data_inputs[0]: adjacency, gan.data_inputs[1]: nodes}`;
epochs belong in that iterator, not an unsupported `nb_epoch` argument.
`nodes` is the number of atom categories (an integer), not hidden layer sizes.
`predict_gan_generator` returns `GraphMatrix` objects; convert using
`featurizer.defeaturize`, retain failures, and separately calculate validity,
uniqueness, novelty and applicability. It does not promise valid or synthesizable
molecules. The stable implementation's `conditional_inputs` is documented unused;
`conditional=True` does not implement property-conditioned generation.

Use the released [Torch MolGAN worked example](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/models/torch_models/molgan.py)
as the backend-specific starting point. Full GAN optimization was not run here.

## 6. Materials prediction

Use `pymatgen.core.Structure.from_file` for CIF input, then
`dc.feat.CGCNNFeaturizer().featurize(structures)` and an explicitly labeled
`NumpyDataset`. `CGCNNModel(n_tasks=1, mode='regression')` requires DGL; verify its
model/feature dimensions and convergence cutoff. Validate composition, periodic
cell, occupancy, structure identity, target units and calculation provenance.
Split related compositions/structures together when measuring transfer. There is
no stable `CIFLoader` or universal `load_bandgap` shortcut in this workflow.
[CGCNN featurizer](https://deepchem.readthedocs.io/en/2.8.0/api_reference/featurizers.html#cgcnnfeaturizer)

## 7. Protein sequence analysis

For supervised protein prediction, construct raw sequence strings **with labels**;
FASTA alone does not provide those labels. For ProtBERT the official tokenizer input
uses space-separated uppercase residues, with uncommon residues handled according
to its model card. Load a tokenizer and a task-specific model object via Transformers,
then wrap in `HuggingFaceModel`. The same single-task, complete-label and logits
limitations apply. Cluster/split homologs before model selection, record sequence
length handling, and do not silently truncate biologically decisive regions.
[ProtBERT model card](https://huggingface.co/Rostlab/prot_bert)

## 8. Custom model integration

Numeric scikit-learn models can be wrapped in `SklearnModel`. For a custom Torch
network, this correct DeepChem loss contract retains sample weights:

```python
import torch
import deepchem as dc
model = dc.models.TorchModel(
    model=torch.nn.Linear(2048, 1),
    loss=dc.models.losses.L2Loss(),
    output_types=['prediction'], device='cpu')
# train must contain 2048 numeric features and one continuous target.
model.fit(train, nb_epoch=1, checkpoint_interval=0)
```

A reduced scalar `torch.nn.MSELoss` passed as a custom DeepChem callable has the
wrong `(outputs, labels, weights)` contract. For complex custom losses, explicitly
verify masking and normalization with a zero-weight synthetic example.
[Released TorchModel](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/models/torch_models/torch_model.py)
