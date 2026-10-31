# Using scientific models from the catalog

A Hub repository stores artifacts; it does not guarantee a Transformers loader or a
hosted inference service. Read the model card, library, input alphabet, head, and
license before choosing an execution path.

| Path | Use when | Check first |
|---|---|---|
| Local Transformers | Architecture is supported, such as ESM2 | Matching tokenizer, pinned revision, memory and sequence length |
| Author's native package | Model requires its own runtime, such as Evo2, STACK, TEDDY or AVEX | Author installation and preprocessing requirements |
| Inference Providers | The exact model **and task** have a live provider mapping | Provider, permissions, quotas and billing |
| Dedicated endpoint | A compatible model has already been deployed | Endpoint URL, deployed revision and task contract |
| Space | A reviewed app exposes the required function | Runtime, SDK and current `view_api()` schema |

Inference Providers includes `hf-inference`, the successor to the old serverless
Inference API. A public model or Space is not a promise of free, available compute.

## Local ESM2 embeddings

The combined local workflow was tested with Python 3.13, Transformers 5.18.0,
Torch 2.14.1, Datasets 5.0.1, Hub 1.33.0 and Gradio Client 2.7.1. Datasets 5.0.1
requires `huggingface-hub<2`; installing every package's latest release together
is incompatible. Use a separate project environment:

```bash
uv pip install 'transformers==5.18.0' 'torch==2.14.1' 'datasets==5.0.1' 'huggingface-hub==1.33.0' 'gradio-client==2.7.1' python-dotenv
```

The following pretrained download is illustrative; validation used a tiny random
ESM2 model and local vocabulary, without downloading weights. It produces both
per-residue and sequence embeddings, excluding BOS, EOS and padding. These are
features, not calibrated mutation effects or folded structures.

```python
from dotenv import load_dotenv
load_dotenv()  # before importing Hub-dependent libraries
import torch
from transformers import AutoModel, AutoTokenizer

model_id = "facebook/esm2_t12_35M_UR50D"
revision = "6fbf070e65b0b7291e7bbcd451118c216cff79d8"
tok = AutoTokenizer.from_pretrained(model_id, revision=revision)
model = AutoModel.from_pretrained(model_id, revision=revision).eval()
sequences = ["MKTAYIAKQR", "ACDE"]
# Explicitly reject empty/invalid input; do not silently truncate residues.
if any(not s or any(c not in "ACDEFGHIKLMNPQRSTVWYBXZUO" for c in s) for s in sequences):
    raise ValueError("Expected nonempty uppercase protein sequences")
if any(len(s) > 1022 for s in sequences):
    raise ValueError("Choose an explicit long-sequence strategy before embedding")
inputs = tok(sequences, padding=True, return_tensors="pt", return_special_tokens_mask=True)
residue_mask = inputs.pop("special_tokens_mask").eq(0) & inputs["attention_mask"].bool()
with torch.inference_mode():
    hidden = model(**inputs).last_hidden_state
per_residue = [h[m] for h, m in zip(hidden, residue_mask)]
mean_embeddings = torch.stack([h.mean(dim=0) for h in per_residue])
assert [len(h) for h in per_residue] == [len(s) for s in sequences]
```

ESM2 is a masked language model. Sequence generation, variant scoring and
folding require different heads/procedures; `AutoModel` embeddings alone do not
perform those tasks. For downstream evaluation, split by protein family or
homology clusters when relevant, rather than allowing close homologs across folds.

## Native scientific runtimes and custom code

Evo2 uses `from evo2 import Evo2` and its own tokenizer/Vortex runtime. The Arc
repositories are **not** drop-in `AutoModel`/`AutoTokenizer` checkpoints. The
current author instructions distinguish 7B BF16 models from 1B/20B/40B models
requiring FP8/Transformer Engine and Hopper hardware; 40B needs multiple H100s.
Follow the [Evo2 source instructions](https://github.com/ArcInstitute/evo2),
including their numerical checks. No Evo2 runtime was installed for this review.

Some other Hub architectures require `trust_remote_code=True`; use it only when
the selected card actually requires it, after reviewing the named repository and
pinning the code revision. It executes repository Python. Existing task authorization
may cover that execution; otherwise obtain authorization before running it. Being
listed in the catalog does not establish code safety or scientific validity.

Memory estimates must include weights, dtype, activations, batch size, sequence
length and framework overhead. Two bytes per parameter estimates FP16/BF16 weights
only. A parameter-count threshold or fixed training multiplier cannot guarantee
that a scientific model fits or is numerically supported on a particular GPU.

## Check hosting before using InferenceClient

This metadata-only example is publicly executable and downloads no weights:

```python
from huggingface_hub import HfApi
model_id = "facebook/esm2_t33_650M_UR50D"
info = HfApi(token=False).model_info(model_id, expand=["inferenceProviderMapping"])
mapping = info.inference_provider_mapping or []
live = {route.provider: route for route in mapping if route.status == "live"}
print({name: route.task for name, route in live.items()})
```

On 2026-10-01 the ESM2 repository mapped to `hf-inference` for **fill-mask**,
not feature extraction. `arcinstitute/evo2_40b` had an empty mapping; do not route
it to Together or infer availability from its size. Mappings change; check again
at execution time. Arc documents a separate NVIDIA hosted option.

Illustrative authenticated inference, **not executed in this review**:

```python
import os
from dotenv import load_dotenv
load_dotenv()
from huggingface_hub import InferenceClient

# First confirm the live mapping above still supports this exact task.
with InferenceClient(provider="hf-inference", model=model_id,
                     token=os.environ["HF_TOKEN"], timeout=60) as client:
    candidates = client.fill_mask("MKT<mask>YIAKQR")
for candidate in candidates:
    print(candidate.token_str, candidate.score)
```

The client routes the task request and parses a list of fill-mask result objects.
These scores describe masked-token probabilities, not experimental activity.
For other tasks use their documented input/return contracts; `text_generation`
is not a generic interface for DNA models. `HF_TOKEN` is used for HF-routed
requests; a provider's own key uses that provider's direct billing. Check current
permission and pricing requirements before a paid call. Dedicated endpoint URLs
are an alternative to `provider`, not an additional provider selector.

Sources: [ESM API](https://huggingface.co/docs/transformers/model_doc/esm),
[Inference guide](https://huggingface.co/docs/huggingface_hub/guides/inference),
[HfApi](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api),
[ESM2 card](https://huggingface.co/facebook/esm2_t12_35M_UR50D).
