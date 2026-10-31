# Script recipes

Run from the skill root after installing the selected model's dependencies.
These external-data training commands are illustrative; the review records the
actual offline synthetic tests and dependency limits.

## Solubility

```bash
python scripts/predict_solubility.py --epochs 50
python scripts/predict_solubility.py --data measured.csv \
  --smiles-col smiles --target-col logS --epochs 50 --predict CCO c1ccccc1
```

The benchmark path loads ESOL; the custom path requires complete finite continuous
targets. Both use 2048-bit circular fingerprints and a Torch multitask regressor,
train-only target normalization, and original-unit metrics/predictions. Custom
units are whatever the input column encodes; the script does not convert them.

## Graph network

```bash
python scripts/graph_neural_network.py --model dmpnn --dataset bbbp --epochs 20
python scripts/graph_neural_network.py --model attentivefp --data molecules.csv \
  --targets activity --task-type regression --epochs 50
```

DMPNN needs torch-geometric in stable 2.8.0. The other four graph choices need a
compatible DGL and DGL-LifeSci stack. The same model-specific featurizer is used for
benchmark and custom input. Classification requires binary observed labels; empty
splits fail early and class-deficient holdout tasks get undefined AUC, not a made-up
value. Regression benchmark transforms are inverted for evaluation.

## Pretrained encoder

```bash
python scripts/transfer_learning.py --model chemberta --dataset bbbp --epochs 10
python scripts/transfer_learning.py --model chemberta --data measured.csv \
  --target logS --task-type regression --model-id ./local-chemberta --local-files-only
```

HF training supports one fully observed, unweighted task. Tox21 is rejected for
this route because the bundled stable HF wrapper does not implement masked
multitask loss. Strings, tokenizer and sequence-classification model objects are
kept separate. Classification logits are converted with softmax before scoring.
Pin the Hub revision for reproducibility; a new task head needs supervised training.

For MoLFormer, use `--model molformer --trust-remote-code --revision <reviewed-commit>`
with the current IBM repository. Its current card targets Transformers 5;
`compat-v4` is the documented branch for Transformers 4: resolve it to the reviewed
40-character commit SHA before passing it to this script. Moving branch names do
not pin code. Review/pin both code and weights; the script does not enable repository
code implicitly.

For GROVER, provide `--model grover --checkpoint encoder.pt --grover-config architecture.json`.
The JSON must match the checkpoint encoder, for example `{"hidden_size":128,
"num_attn_heads":4,"depth":1}` only when those were its training settings.
The checkpoint must contain DeepChem's `embedding` state dictionary; the script
loads it strictly with `weights_only=True` and initializes a fresh task head.
Original external GROVER checkpoints require a separately verified conversion;
they are not assumed to match DeepChem's layout. Fixed 151/165 graph feature widths
and 2048 additional fingerprint features must match the intended pipeline.
