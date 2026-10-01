# Models and training

Reviewed against PyHealth 2.0.2 exports, constructors and implementations. All model
choices below require checking the actual sample schema and a forward pass; a shared
`dataset=` parameter does not make modalities or hyperparameters interchangeable.

## Choosing a compatible architecture

| Input/task | Candidate exports | Contract to check |
|---|---|---|
| Code sequences | `Transformer`, `RNN`, `RETAIN`, `Deepr`, `TCN` | Flat versus nested sequences, label processor and pooling semantics |
| Irregular clinical series | `AdaCare`, `ConCare`, `StageNet`, `EHRMamba` | Required processors, numeric features and time inputs |
| Medication sets | `GAMENet`, `SafeDrug`, `MICRON`, `MoleRec` | Visit histories, ATC level 3 labels, DDI/molecular resources |
| Simple baselines | `LogisticRegression`, `MLP` | PyHealth's LogisticRegression learns embeddings with a linear head; it is not automatically a fixed bag-of-codes baseline |
| Signals/images | `CNN`, `ContraWR`, `SparcNet`, `BIOT` | Expected channels, sample rate, length and model-specific transforms |
| Graphs | `GCN`, `GAT`, `GraphCare`, `GRASP` | Graph construction and optional graph dependencies; there is no exported `GNN` class in 2.0.2 |
| Text | `TransformersModel`, `TransformerDeID`, `MedLink` | Tokenizers/checkpoints, text or retrieval schema; MedLink links de-identified patient records using retrieval; it is not a terminology cross-map |
| Generative | `VAE`, `GAN` | Architecture-specific generation/training contract |
| Learned feature selection | `Agent` | Uses RL within a predictive model; it is not a ready-made treatment-policy optimizer |
| Mixed inputs | `MultimodalRNN` | Supported sequence/tensor processors |

RETAIN attention may help inspect associations but is not by itself a causal
explanation. MICRON models medication changes internally yet returns probabilities
for the medication set; do not interpret its output as change labels automatically.
DDI loss terms do not make a recommendation clinically safe. Build GAMENet from the
training dataset because its EHR adjacency is learned from dataset records.

## Constructor examples

```python
from pyhealth.models import Transformer, RNN, RETAIN
model = Transformer(dataset=train, embedding_dim=32, heads=2,
                    num_layers=1, dropout=0.1)
rnn = RNN(dataset=train, embedding_dim=32, hidden_dim=64, rnn_type="GRU")
retain = RETAIN(dataset=train, embedding_dim=32, dropout=0.1)
```

`Transformer` does not accept `hidden_dim`. RNN passes extra arguments to `RNNLayer`;
RETAIN passes its extra arguments to `RETAINLayer`. Use `inspect.signature` and the
[model-specific documentation](https://pyhealth.readthedocs.io/en/latest/api/models.html)
for additional parameters. Model dimensions come from fitted input/output processors.
Most predictive models require exactly one output field. Inspect its schema rather
than adding obsolete `feature_keys`, `label_key`, or `mode` kwargs from 1.x tutorials.

A minimal forward check after creating the loader:

```python
batch = next(iter(train_loader))
output = model(**batch)
assert output["loss"].isfinite().all()
assert output["y_prob"].shape[0] == output["y_true"].shape[0]
```

For drug recommendation, the built-in MIMIC task supplies nested conditions,
procedures and historical medications plus `drugs: multilabel`. It converts NDCs to
ATC level 3. Validate mapped coverage and the availability of resource tables before
trying molecular models. Their initialization can perform network downloads.
GAMENet, SafeDrug and MICRON passed small synthetic forward checks, including
ATC resource loading; they were not benchmarked on clinical data. A concrete
2.0.2 caveat: GAMENet's `generate_ehr_adj` skips tensor-valued medication labels.
Processed sample datasets normally contain tensors, and the smoke fixture with
co-occurring drugs produced an all-zero EHR adjacency. Inspect this matrix and
resolve the upstream behavior before claiming the EHR graph is active. Other
specialized architectures were reviewed in source only.

## Trainer contract

```python
from pyhealth.trainer import Trainer
trainer = Trainer(model=model, metrics=["pr_auc", "roc_auc"], device="cpu",
                  output_path="./output", exp_name="mortality")
trainer.train(train_dataloader=train_loader, val_dataloader=val_loader,
              epochs=30, monitor="pr_auc", monitor_criterion="max", patience=5)
scores = trainer.evaluate(test_loader)
y_true, y_prob, mean_loss = trainer.inference(test_loader)
```

For binary AUC, verify both classes occur in the evaluation cohort. Multiclass and
multilabel metrics need their corresponding names; see [tasks](tasks.md). Missing
monitor keys cause `KeyError`; unsupported metric names cause metric evaluation
errors. They do not silently choose a different checkpoint. Include the monitored
metric in `metrics` and verify `trainer.evaluate(val_loader)` before a long run.

With logging enabled, checkpoints are stored under `output_path/exp_name/` as
`best.ckpt` and `last.ckpt`. Best weights are restored at training end by default.
`enable_logging=False` suppresses checkpoint writing, so do not promise persistent
best-model restoration in that mode. `Trainer.train` returns no score dictionary;
use `evaluate` afterward. Avoid passing the test loader to every tuning run.

```python
trainer.load_ckpt("./output/mortality/best.ckpt")
```

This restores weights only: recreate the same architecture **and the original
processors/vocabularies**, since token-index changes can silently invalidate a model.
Persist data split IDs, schema, processor artifacts, code version and dependency lock
with the checkpoint. `save_processors`/`load_processors` exist in `pyhealth.datasets`;
only load trusted local processor artifacts (they use pickle).

[Official Trainer API](https://pyhealth.readthedocs.io/en/latest/api/trainer.html).
