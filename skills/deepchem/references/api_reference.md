# DeepChem 2.8.0 API contracts

Reviewed 2026-09-30 against the released wheel/source and current official docs.
`latest` documentation describes development builds; it is not the stable API.
This is a selected contract reference, not a complete package catalogue.

## Data and representations

`CSVLoader(tasks=[...], feature_field='smiles', featurizer=...)` produces a
`DiskDataset`. `NumpyDataset(X, y, w, ids)` wraps arrays. Keep all four aligned.
Empty CSV labels are stored as placeholder zeros with zero weights; they are
unmeasured, not negative assay results. Failed features can cause row removal.
The bundled `load_csv` checks raw headers, numeric labels, SMILES and row counts.

`SDFLoader`, `JsonLoader`, `ImageLoader`, `FASTALoader`, `FASTQLoader`, and alignment
loaders have separate format contracts and optional dependencies. FASTA does not
supply supervised property labels. `FASTALoader`'s legacy default is nucleotide
encoding, not a ready-made protein-transformer input pipeline. There is no stable
`dc.data.CIFLoader`: parse CIF with pymatgen and use a materials featurizer.

| Model | Matching representation | Additional backend |
|---|---|---|
| `SklearnModel`, `MultitaskRegressor/Classifier` | `CircularFingerprint(size=2048)` or numeric descriptors | scikit-learn; Torch for multitask networks |
| `GraphConvModel` | `ConvMolFeaturizer` (`'GraphConv'` MoleculeNet alias) | TensorFlow |
| `GCNModel`, `GATModel` | `MolGraphConvFeaturizer()` (`GraphData`, 30 atom features) | Torch, DGL, DGL-LifeSci |
| `AttentiveFPModel`, Torch `MPNNModel` | `MolGraphConvFeaturizer(use_edges=True)` (11 bond features) | Torch, DGL, DGL-LifeSci |
| `DMPNNModel` | `DMPNNFeaturizer()` (133 atom, 14 bond features) | Torch, torch-geometric in 2.8.0 |
| `GroverModel` | `GroverFeaturizer(features_generator=...)` | Torch |
| `HuggingFaceModel` | Strings via `DummyFeaturizer`; tokenizer supplied separately | Torch, Transformers |
| `BasicMolGANModel` | `MolGanFeaturizer`, adjacency/node tensors | Explicit Torch or TensorFlow implementation |
| `CGCNNModel` | `CGCNNFeaturizer` on pymatgen `Structure` objects | pymatgen, Torch, DGL |

Import Torch `MPNNModel`, `GroverModel`, and `BasicMolGANModel` from
`deepchem.models.torch_models`; top-level aliases can be absent or select TensorFlow.
Graph features are not interchangeable merely because their classes all represent molecules.
`GroverFeaturizer` computes graph descriptors; it does not itself load learned embeddings.

MoleculeNet `'ECFP'` means **1024** bits; the `CircularFingerprint` class defaults to
**2048**. Pass an explicit object to keep training and prediction consistent.
`'Raw'` constructs `RawFeaturizer()` whose default output is an RDKit Mol, not a
SMILES string. Use `DummyFeaturizer()` for HF inputs or explicit
`RawFeaturizer(smiles=True)` when canonicalized strings are intended.

`RDKitDescriptors` feature inventory depends on the installed RDKit version;
record feature names/order. `CoulombMatrix` needs conformer coordinates, units,
and a consistent maximum atom count. `PowerTransformer` raises values to specified
powers; it is not scikit-learn's Box-Cox/Yeo-Johnson transformer.

## Splitting and transforms

`ScaffoldSplitter` reads SMILES from **dataset.ids**. It keeps equal Bemis-Murcko
scaffolds together; acyclic molecules can share an empty scaffold, causing very
unequal or empty partitions. It does not remove duplicate measurements or prevent
all chemical, temporal, assay, or patient leakage. Choose temporal/group/scaffold
splits for the deployment question, check overlap and per-task class support, and
save the actual IDs. `RandomStratifiedSplitter` balances nonzero task labels; it
is not a general-purpose stratifier for arbitrary continuous outcomes.

Fit `NormalizationTransformer(transform_y=True, dataset=train)` on training data
only for continuous targets, then transform each split. Pass the same transformers
to `model.predict(..., transformers=...)` and `model.evaluate(..., transformers=...)`
for original-unit outputs. Do not normalize binary class labels. For missing-label
regression, verify how your selected transformer estimates statistics; the bundled
solubility custom-data path requires complete targets.

## MoleculeNet loader contract

`load_*(featurizer=..., splitter=..., transformers=..., reload=True)` normally
returns `(tasks, (train, valid, test), fitted_transformers)`. `reload=True` reuses
cached processed data; **False** rebuilds processing. It does not guarantee a new
raw download. Record raw-source identity, local cache path, split IDs and package
versions; a requested splitter is not proof of a paper's published split.

Verified loader names used by the scripts:

| Name | Loader | Task |
|---|---|---|
| Tox21 | `load_tox21` | 12 binary assays with missing labels |
| BBBP | `load_bbbp` | binary |
| BACE | `load_bace_classification` | binary; `load_bace_regression` is separate |
| HIV | `load_hiv` | binary |
| ESOL | `load_delaney` | log10 aqueous solubility in mol/L |
| FreeSolv | `load_freesolv` | hydration free energy |
| Lipophilicity | `load_lipo` | experimental logD |

There is no `load_bace` alias. Other families include QM7/8/9, PDBbind,
perovskite, `load_mp_formation_energy`, `load_mp_metallicity`, and USPTO; check the
individual release-specific loader's source, featurizer, units, licensing and
split options before use. No direct hosted inference API is called by these scripts.
MoleculeNet loaders download public dataset files; HF `from_pretrained` resolves
Hub repository assets, not an inference endpoint.

## Models, metrics and search

`MultitaskRegressor` is a Torch model in this release. `SklearnModel` wraps numeric
estimators; sparse multitask labels require one properly masked estimator per task
or a model with verified masked-loss support. Do not feed binary and continuous
outputs into the same plain regressor and call both scientifically equivalent tasks.

Set `DMPNNModel(n_classes=2, mode='classification', ...)` for binary tasks; its
released default is three classes. HF `HuggingFaceModel(model=network,
tokenizer=tokenizer, task=...)` takes **objects**, not a Hub ID. The stable wrapper
returns logits and uses the HF model's loss without applying `dataset.w`; the
bundled HF path therefore rejects multiple tasks, missing labels and nonunit weights.
GROVER uses `task='finetuning', mode='classification'/'regression'` and requires
explicit feature dimensions and architecture. `model_dir` is an output/checkpoint
location, not evidence that any pretrained weights were loaded.

Use continuous probabilities for ROC-AUC/PR metrics and thresholded labels for
accuracy/F1. Report the threshold and observed examples per task. AUC is undefined
with one observed class; don't silently score it as zero. The bundled scorer reports
per-task metrics and the number of valid tasks in each macro average. It reports
average precision (scikit-learn), not a renamed trapezoidal PR AUC.
`pearson_r2_score` is squared correlation, not R-squared; high correlation need not
mean calibrated predictions. RMSE/MAE need original target units.

`GridHyperparamOpt(model_builder)` invokes `model_builder(**model_params)`.
`hyperparam_search(..., output_transformers=transformers, use_max=False)` minimizes
an error metric. It returns `(best_model, best_params, all_scores)` where
`all_scores` maps parameter combinations to validation scores; there is no
`'best_validation_score'` special key. Keep the test set outside model selection.
For custom Torch networks, use `dc.models.losses.L2Loss()` or a callable with the
DeepChem `(outputs, labels, weights)` contract; `nn.MSELoss()` is not that callable.

## Official sources

- [Release metadata](https://pypi.org/project/deepchem/2.8.0/)
- [Featurizers](https://deepchem.readthedocs.io/en/2.8.0/api_reference/featurizers.html)
- [Models](https://deepchem.readthedocs.io/en/2.8.0/api_reference/models.html)
- [Splitters](https://deepchem.readthedocs.io/en/2.8.0/api_reference/splitters.html)
- [MoleculeNet](https://deepchem.readthedocs.io/en/2.8.0/api_reference/moleculenet.html)
- [Released alias registry](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/molnet/load_function/molnet_loader.py)
- [Released HF wrapper](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/models/torch_models/hf_models.py)
- [Released hyperparameter search](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/hyper/grid_search.py)
