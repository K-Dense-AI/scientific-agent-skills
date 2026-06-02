# Medical codes & tokenizers

PyHealth ships utilities for working with medical coding systems directly — no external API, just bundled mappings.

## InnerMap: lookup within a coding system

`InnerMap` lets you look up code descriptions and traverse the code hierarchy (parents/ancestors).

```python
from pyhealth.medcode import InnerMap

icd9cm = InnerMap.load("ICD9CM")
icd9cm.lookup("428.0")
# → 'Congestive heart failure, unspecified'

icd9cm.get_ancestors("428.0")
# → ['428', '420-429.99', '390-459.99', '001-999.99']
```

Supported coding systems:

| System | Domain |
|---|---|
| `ICD9CM`, `ICD10CM` | Diagnoses |
| `ICD9PROC`, `ICD10PCS` | Procedures |
| `ATC` | WHO Anatomical Therapeutic Chemical (drugs) |
| `NDC` | National Drug Code (US) |
| `RxNorm` | Normalized drug names |
| `CCSCM`, `CCSPROC` | Clinical Classifications Software (single-level) |

```python
atc = InnerMap.load("ATC")
atc.lookup("M01AE51")
# → 'ibuprofen, combinations'
```

## CrossMap: translate between systems

`CrossMap` converts codes from one system to another. Many mappings are one-to-many — the result is always a list.

```python
from pyhealth.medcode import CrossMap

# Diagnoses: ICD-9-CM → CCS (rolls fine-grained codes up to ~280 categories)
cm = CrossMap.load("ICD9CM", "CCSCM")
cm.map("428.0")
# → ['108']

# Drugs: NDC → RxNorm (normalized drug name)
cm = CrossMap.load("NDC", "RxNorm")
cm.map("50580049698")
# → ['209387']
```

Common cross-mappings:
- `ICD9CM ↔ ICD10CM` — ICD version conversion
- `ICD9CM → CCSCM`, `ICD10CM → CCSCM` — dimensionality reduction (~14k → 280 codes)
- `NDC → RxNorm` — drug normalization
- `NDC → ATC` — pharmacology grouping
- `RxNorm → ATC` — drug therapeutic classification

When to use cross-mapping: when the user has codes in one system but wants to predict or feature-engineer in another (e.g., training on ICD-9 from MIMIC-III but evaluating on ICD-10 from MIMIC-IV).

## Tokenizer

`pyhealth.tokenizer.Tokenizer` converts code lists to integer indices and back. Most pipelines don't need to call it directly — `set_task` and the models handle tokenization internally — but it's exposed when you need batch encoding for custom models.

```python
from pyhealth.tokenizer import Tokenizer

vocab = ['A01A', 'A02A', 'A02B', 'A03C', 'A03D', 'A04A']
tok = Tokenizer(tokens=vocab, special_tokens=["<pad>", "<unk>"])

# 2D = batch of code lists, one per sample
tokens = [['A03C', 'A03D'], ['A04A', 'B035']]   # 'B035' is OOV
indices = tok.batch_encode_2d(tokens)
# → [[5, 6], [7, 1]]    (1 = <unk>)

# 3D = batch of visits, each with code lists
tokens = [[['A03C', 'A03D'], ['A04A']], [['B035']]]
indices = tok.batch_encode_3d(tokens)

# Decode is symmetric
tok.batch_decode_2d(indices)
```

Reserved indices: `0 = <pad>`, `1 = <unk>` when both special tokens are passed (in that order).

## When to surface this to the user

- **Reduce label cardinality**: ICD-9 → CCS turns 14,000 sparse labels into 280 — drug-rec and ICD-coding tasks often benefit.
- **Cross-version compatibility**: training on MIMIC-III (ICD-9) and inferring on MIMIC-IV (ICD-10) requires a cross-map.
- **Drug normalization**: NDC codes are vendor-specific; map to RxNorm or ATC for stable features.
- **Interpretability**: after a prediction, use `InnerMap.lookup` to render code IDs as human-readable descriptions in the output.
