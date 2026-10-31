# Review evidence — 2026-09-30

## Release and executed environment

The current PyPI stable release remains **DeepChem 2.8.0** (Python >=3.7,<3.12).
The audit used isolated **Python 3.11.11**, **Torch 2.14.1**, **Transformers 5.18.0**,
**torch-geometric 2.8.0.post1**, **NumPy 2.4.6**, **scikit-learn 1.9.1**, and
**RDKit 2026.3.6**. These are the executed versions, not universal compatibility
claims. The current DeepChem nightly is a different installation target.

DeepChem logs skipped optional TensorFlow/JAX/DGL/Lightning modules. Its bundled
`Chemberta` class also imports an obsolete Transformers tokenizer submodule under
Transformers 5; the tested script uses the working generic `HuggingFaceModel`
wrapper with Transformers model/tokenizer objects instead. Missing optional-class
warnings did not prevent the tested core paths.

## Executed synthetic checks

The repository test suite exercises:

- 2048-bit fingerprints, MoleculeNet alias differences, all five graph feature
  contracts and GROVER feature dimensions.
- CSV duplicate headers, invalid structures, non-finite labels, missing-label masks,
  split row conservation, and HF rejection of unsupported sparse/multitask input.
- One-epoch CPU solubility regression plus new-molecule prediction, with target
  normalization undone. The script reshapes the released regressor's trailing
  singleton output to one value per molecule.
- Binary DMPNN fit/predict and scoring. Single-task predictions have shape `(n,2)`;
  the shared scorer handles that and `(n,tasks,2)` without confusing classes/tasks.
- Tiny local randomly initialized RoBERTa classification and regression checkpoints,
  locally saved tokenizer/model loading, HF fit and logits-aware scoring.
- A synthetic GROVER encoder state dictionary restored strictly into a matching
  architecture, followed by CPU classification and regression fits. This checks transfer mechanics,
  not a public pretrained GROVER model.
- Original-unit regression metrics, one-class AUC handling, numeric RF baseline,
  keyword-based grid search, and a custom Torch network using DeepChem `L2Loss`.
- All three command-line help paths and conflicting-input rejection.

A separate tiny **MoLFormer** smoke used the current official repository's Python
source at commit `361063d0ad524ef77cf39b08469f6be770dc550f`, reviewed before importing,
with a reduced random configuration and synthetic tokenizer. The local checkpoint
was loaded and fine-tuned through the script on CPU. No public model weights were
downloaded. MoLFormer does not accept `token_type_ids`; the script selects only
`input_ids`/`attention_mask` and enables `deterministic_eval=True`.

Synthetic fits prove executable interfaces only. They do not measure generalization,
convergence, chemical applicability, model quality or scientific benchmark scores.

## Live public read probes

The seven released MoleculeNet source URLs used by the scripts returned **HTTP 206**
for a bounded first-2048-byte request. CSV or decompressed gzip headers matched
ESOL, Tox21, BBBP, BACE, HIV, FreeSolv and Lipophilicity task/SMILES fields. These were
unauthenticated partial content probes, not full dataset downloads or benchmark
training. No API credentials or paid scientific service calls were used.

The current MoLFormer Hub configuration and Python source files resolved at the
same commit; the configuration supplies `AutoModelForSequenceClassification`.
The former `ibm/...` model URL redirects to `ibm-research/...`. Its generic fast
tokenizer is configured by `tokenizer_config.json`; a guessed
`tokenization_molformer.py` returned 404 and is not required or referenced by the
shipped workflow. The current card documents a `compat-v4` branch for Transformers 4.

## Unexecuted routes

DGL/DGL-LifeSci were absent on this macOS host: GCN, GAT, AttentiveFP and Torch MPNN
constructors/training were checked against released source, while their featurizers
ran locally. Current framework versions alone do not establish DGL binary ABI
compatibility. Use the [DGL platform matrix](https://www.dgl.ai/pages/start.html)
and validate the chosen environment before expensive training.

No TensorFlow/JAX backend, public pretrained weight download, full MoleculeNet run,
full GAN training, CIF/materials model training or ProtBERT training was executed.
Those workflows are bounded, source-verified templates. No GPU or scientific
performance claims follow from this CPU review.

## Primary sources

- [Stable metadata](https://pypi.org/project/deepchem/2.8.0/)
- [Versioned DeepChem APIs and source links](api_reference.md)
- [Released model exports](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/models/__init__.py)
- [Released loss/weight behavior](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/models/torch_models/hf_models.py)
- [Released GROVER](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/models/torch_models/grover.py)
- [Current MoLFormer model card](https://huggingface.co/ibm-research/MoLFormer-XL-both-10pct)
- [Current MoLFormer configuration](https://huggingface.co/ibm-research/MoLFormer-XL-both-10pct/blob/main/config.json)
- [ChemBERTa checkpoint provenance](https://huggingface.co/seyonec/ChemBERTa-zinc-base-v1)
- [ProtBERT tokenizer and sequence conventions](https://huggingface.co/Rostlab/prot_bert)
