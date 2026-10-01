# ESMC embeddings: esm 3.4.1.post1

## Current local interface

Use `EsmcForMaskedLM` and `EsmcTokenizer` from `esm.models.esmc`. Local checkpoints
are `biohub/ESMC-300M`, `biohub/ESMC-600M`, and `biohub/ESMC-6B`. Their published
hidden dimensions/layers are 960/30, 1152/36, and 2560/80. ESMC 6B is now
open-weight; the old assertion that it is hosted-only is obsolete.

Illustrative pretrained inference:

```python
import torch
from esm.models.esmc import EsmcForMaskedLM, EsmcTokenizer

model = EsmcForMaskedLM.from_pretrained("biohub/ESMC-300M", device="cpu").eval()
tokenizer = EsmcTokenizer()
sequences = ["MPRTKEIND", "ACDE"]
inputs = tokenizer(sequences, return_tensors="pt", padding=True,
                   return_special_tokens_mask=True, truncation=False)
special = inputs.pop("special_tokens_mask")
inputs = {key: value.to(model.device) for key, value in inputs.items()}
with torch.inference_mode():
    output = model(**inputs, output_hidden_states=True)

# One vector for each residue, excluding CLS/EOS/padding.
keep = inputs["attention_mask"].bool() & ~special.to(model.device).bool()
residues = [states[mask].cpu() for states, mask in zip(output.last_hidden_state, keep)]
assert [len(item) for item in residues] == [len(item) for item in sequences]
```

The current model cards specify a 2048-token context. For plain single-chain
inputs with CLS/EOS, the helper limits sequences to 2046 residues and raises on
longer input. It never truncates silently.

The native output contains:

| Field | Shape/meaning |
| --- | --- |
| `last_hidden_state` | `(B,T,D)`, final normalized representations |
| `logits` | `(B,T,64)` for the masked-LM class |
| `hidden_states` | `(N+1,B,T,D)` when requested; embedding layer plus block outputs, final state normalized |
| `attentions` | Per-layer tuple of `(B,H,T,T)` when `output_attentions=True` |

`T` includes the boundary tokens and any padding. Attentions can be expensive
and are not causal explanations. The native SDK's `hidden_states` is a stacked
tensor, not necessarily the same container as another Transformers model.

For repeated embedding extraction, use `embed_sequences()` from
`scripts/esm_embeddings.py` (add that directory to `PYTHONPATH`). It validates
plain single-chain sequences, never silently truncates, and pools only residues.
Do not concatenate separately generated fragments and call that full-protein
inference: fragmentation removes long-range context.

## Tiny CPU contract check

This construction was executed without pretrained weights or network access.
The result tests shapes and code behavior; random weights have no biological
predictive meaning.

```python
import torch
from esm.models.esmc import EsmcConfig, EsmcForMaskedLM, EsmcTokenizer
from esm_embeddings import embed_sequences

torch.manual_seed(0)
model = EsmcForMaskedLM(EsmcConfig(
    hidden_size=32, num_attention_heads=4, num_hidden_layers=2,
)).eval()
features = embed_sequences(model, EsmcTokenizer(), ["MPRT", "AC"])
assert features.shape == (2, 32) and torch.isfinite(features).all()
```

## Hosted ESMC

Use `esmc_client`, not the ESM3 factory. The current ESM3 factory rejects
non-ESM3 names. Dated hosted IDs are distinct from Hugging Face repository IDs.
Illustrative authenticated inference:

```python
import os
from esm.sdk import esmc_client
from esm.sdk.api import ESMProtein, ESMProteinError, LogitsConfig
from esm.models.esmc import EsmcTokenizer
from esm_embeddings import sdk_residue_embeddings, validate_sequence

sequence = "MPRTKEINDAGLIVHSPQWFYK"
validate_sequence(sequence)
with esmc_client(model="esmc-600m-2024-12", url="https://biohub.ai",
                 token=os.environ["ESM_API_KEY"], request_timeout=120) as model:
    encoded = model.encode(ESMProtein(sequence=sequence))
    if isinstance(encoded, ESMProteinError):
        raise encoded
    output = model.logits(encoded, LogitsConfig(sequence=True, return_embeddings=True))
    if isinstance(output, ESMProteinError):
        raise output
    residues = sdk_residue_embeddings(
        encoded.sequence, output.embeddings, EsmcTokenizer(), len(sequence),
    )
    pooled = residues.mean(dim=0).cpu()
    sequence_logits = output.logits.sequence
```

The SDK returns `LogitsOutput`: **`output.logits.sequence`** is a tensor;
`output.logits` is a per-track container. A single-chain tensor response normally
has `(1,L+2,D)` embeddings and `(1,L+2,64)` sequence logits. Validate against the
encoded token count and strip boundary tokens; do not assume `(1,L,D)`.

`LogitsConfig(return_hidden_states=True, ith_hidden_layer=k)` requests a layer
with embedding-layer index 0. Hosted ESMC6B requires an explicit layer rather
than `-1` for all layers. `return_mean_embedding` and
`return_mean_hidden_states` exist, but a client-side explicit residue mask makes
the pooling convention reviewable. Check account limits before large batches.

## Legacy compatibility and fine tuning

The deprecated `ESMC` wrapper still supports `encode`/`logits`; keep it only for
existing pipelines. Its low-level `forward` consumes token tensors, not an
`ESMProteinTensor`, and returns an output object, not embeddings directly. The
native API above avoids that ambiguity. Hidden-state indexing also changed:
legacy compatibility states omit the embedding layer and use the pre-final-norm
last state, so old layer-index caches cannot be reused without conversion.

The older `fair-esm` package also imports as `esm`, but exposes ESM2/ESMFold1 APIs.
Use another environment for it. ESMC is a replacement representation model, not
a drop-in API or numerical substitute. Refit and validate downstream models.

For trainable fine tuning use the native PyTorch forward path with a defined
supervised loss and optimizer. Do not call an inference helper decorated with
`torch.inference_mode()` and expect gradients. Fine-tuning quality, GPU memory
budgets and pretrained attention maps were not validated here.

Cache sequence features with model/checkpoint revision, SDK version, layer,
pooling convention, dtype and preprocessing in the key. Store numerical arrays
without arbitrary-object deserialization, preserve source IDs, and split homologs
before training to reduce leakage. Similarity and cluster membership alone do
not establish function.

Sources: [released SDK](https://pypi.org/project/esm/3.4.1.post1/),
[native model](https://github.com/Biohub/esm/blob/main/esm/models/esmc/model.py),
[tokenizer](https://github.com/Biohub/esm/blob/main/esm/models/esmc/tokenizer.py),
[compatibility layer](https://github.com/Biohub/esm/blob/main/esm/models/esmc/compatibility.py),
[ESMC model card](https://huggingface.co/biohub/ESMC-6B).
