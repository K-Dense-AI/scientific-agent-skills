# Models

All PyHealth models are PyTorch modules with a unified constructor: they take a `SampleDataset` (the output of `base.set_task(...)`) as the first argument, plus model-specific hyperparameters. The model auto-configures input/output dimensions from the dataset's schema — you don't wire layers by hand.

```python
model = Transformer(dataset=samples, hidden_dim=128)
```

If you pass a `BaseDataset` instead of a `SampleDataset`, the model can't introspect schemas and will error or misbehave.

## Choosing a model

Pick by data shape and task type, not by recency. The "newest" model is rarely the right answer.

### EHR sequential codes (diagnoses, procedures, prescriptions across visits)

| Model | When to pick it |
|---|---|
| `Transformer` | Strong default. Long visit histories, attention over codes. |
| `RNN` (LSTM/GRU) | Smaller datasets; faster than Transformer; sensible baseline. |
| `RETAIN` | When **interpretability** matters — produces visit-level and code-level attention weights. |
| `Deepr` | CNN-over-codes; readmission-style tasks. |
| `TCN` | Long-range temporal patterns where causality matters. |
| `AdaCare` | Adaptive feature extraction across irregular time intervals. |
| `ConCare` | Contextualized representations across visits. |
| `StageNet` | Disease-progression staging from irregular vitals. |
| `EHRMamba` | State-space alternative to Transformer for long sequences. |

### Drug recommendation (multilabel)

| Model | When to pick it |
|---|---|
| `GAMENet` | Drug-rec baseline with memory networks; pairs with `DrugRecommendation*` tasks. |
| `SafeDrug` | Models drug-drug interactions / safety constraints via molecular structure. |
| `MICRON` | Predicts **medication change** between visits, not the full set. |
| `MoleRec` | Substructure-aware molecular drug recommendation. |

### Static / tabular features

| Model | When to pick it |
|---|---|
| `LogisticRegression` | Strong, fast baseline. Always run this first. |
| `MLP` | Static numeric vectors, no sequence order. |

### Imaging / signals

| Model | When to pick it |
|---|---|
| `CNN` | Generic convolutional baseline for images and 1D signals. |
| `ContraWR` | Contrastive learning for biosignals. |
| `SparcNet` | Sparse signal prediction (seizure, sleep staging). |
| `BIOT` | Biosignal transformer. |

### Graph-structured data

| Model | When to pick it |
|---|---|
| `GNN` | Generic graph neural net baseline. |
| `GraphCare` | EHR codes augmented with external medical knowledge graphs (UMLS/SNOMED). |
| `GRASP` | Patient-similarity graph representations. |

### Text

| Model | When to pick it |
|---|---|
| `TransformersModel` | Pretrained HuggingFace transformer (BERT-family) — clinical notes, transcripts. |
| `TransformerDeID` | De-identification NER head on top of a transformer. |
| `MedLink` | Medical entity linking. |

### Generative / representation

| Model | When to pick it |
|---|---|
| `VAE` | Synthetic EHR generation, anomaly detection. |
| `GAN` | Synthetic data with adversarial training. |

### Reinforcement learning

| Model | When to pick it |
|---|---|
| `Agent` | Treatment recommendation framed as RL. |

### Multimodal

| Model | When to pick it |
|---|---|
| `MultimodalRNN` | Mix of sequential codes and static tensors in one sample. |

## Common arguments

Most clinical models accept:

- `dataset` — the `SampleDataset` (required, positional)
- `hidden_dim` — embedding/hidden width (default ≈128)
- `embedding_dim` — separate embedding width if exposed
- `dropout` — dropout rate
- `num_layers` — for RNN/Transformer/TCN

Refer to the docstring (`help(Transformer)`) for model-specific knobs (e.g., `rnn_type` for `RNN`, `num_filters` for `CNN`, `latent_dim` for `VAE`).

## Recommended progression

When starting on a new task, work up the model ladder rather than jumping to the most exotic option:

1. **`LogisticRegression`** — sanity check + floor.
2. **`MLP`** if features are static, **`RNN`** if sequential.
3. **`Transformer`** — strong general default.
4. **Specialized model** (RETAIN, GAMENet, StageNet, etc.) — only if the task has a property that motivates it (interpretability, drug structure, irregular time, etc.).

Stop as soon as a model does the job. A working `Transformer` beats a half-debugged `MoleRec`.

## Custom models

Subclass `BaseModel` if nothing fits. The dataset object provides feature extractors via `dataset.input_processors` — use them to keep tokenization consistent with the rest of the pipeline rather than rolling custom encoders.
