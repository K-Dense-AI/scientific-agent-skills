# Using scientific models from the catalog

Hugging Science model entries link to standard Hugging Face Hub repos. There are three sensible execution paths. Pick based on model size and whether the user is doing one-off inference or a long batch job.

## Decision: where to run the model

| Path | When to use | What it costs |
|---|---|---|
| **Local with `transformers`** | Models ≤ ~7B params, user has a GPU or wants offline use, or doing fine-tuning | Disk + VRAM; free |
| **HF Inference API (serverless)** | Quick one-off inference on smaller hosted models, no GPU needed | Free tier exists, then pay-per-call |
| **HF Inference Providers** | Very large models (Evo-2 40B, Kimina-Prover 72B), or when you need throughput | Pay-per-token; routed to third-party providers |
| **HF Space (gradio_client)** | The model has an interactive demo and you want easy structured I/O without managing weights | Free if Space is public; see `using-spaces.md` |

Always check the model card first — some entries are *only* available as Spaces (no public weights), and some are gated and require approval before download.

## Local with `transformers`

Use `uv` for installs:

```bash
uv pip install transformers torch accelerate python-dotenv    # in an active venv
# or project-style:
uv add transformers torch accelerate python-dotenv
```

For gated models, put the token in `.env` rather than running `huggingface-cli login`:

```
# .env (gitignored)
HF_TOKEN=hf_...
```

```python
from dotenv import load_dotenv
load_dotenv()    # reads HF_TOKEN before any HF call

from transformers import AutoModel, AutoTokenizer

model_id = "facebook/esm2_t33_650M_UR50D"
tok = AutoTokenizer.from_pretrained(model_id)
model = AutoModel.from_pretrained(model_id)

inputs = tok("MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ", return_tensors="pt")
embeddings = model(**inputs).last_hidden_state
```

### `trust_remote_code=True` is normal here

A large fraction of scientific models — Evo-2, many Nucleotide Transformer variants, single-cell foundation models, several materials models — ship custom modeling code in their repo. `transformers` will refuse to load them without `trust_remote_code=True`:

```python
model = AutoModel.from_pretrained("arcinstitute/evo2_7b", trust_remote_code=True)
```

Tell the user when you set this flag and why. It executes Python from the repo, so the user should trust the org. The catalog only lists reputable orgs (Arc Institute, Meta/Facebook AI, EleutherAI, SandboxAQ, Merck, etc.), but the user gets to make the call.

### Sizing the GPU

Rough memory for inference at fp16 (very approximate — quantization changes this):

- 35M–650M params (most ESM2 variants): runs on a laptop GPU or even CPU.
- 1B–7B (Evo-2 7B, Nucleotide Transformer 2.5B, STACK Large): single 24 GB GPU is fine.
- 40B+ (Evo-2 40B, Kimina-Prover): needs multi-GPU or A100/H100; almost always better via Inference Providers unless the user has the hardware.

For training/fine-tuning, multiply by ~3–4× for activations and optimizer state.

## HF Inference API (serverless)

Fast for tiny one-off jobs without setting up a GPU. The model has to be supported on the serverless tier (smaller models, popular pipelines).

```bash
uv pip install huggingface_hub python-dotenv     # or: uv add huggingface_hub python-dotenv
```

Put your token in `.env` rather than exporting per-shell:

```
# .env (gitignored)
HF_TOKEN=hf_...
```

```python
from dotenv import load_dotenv
load_dotenv()    # InferenceClient reads HF_TOKEN from env

from huggingface_hub import InferenceClient

client = InferenceClient(model="facebook/esm2_t33_650M_UR50D")
result = client.feature_extraction("MKTAYIAKQR")
```

The serverless API supports tasks like `feature_extraction`, `text_generation`, `image_classification`, `token_classification`. For non-standard scientific tasks (e.g., DNA sequence generation), you may need Inference Providers or local execution instead.

## HF Inference Providers

For very large models or when you want production throughput. Inference Providers route requests to vetted backends (Together, Fireworks, Replicate, Sambanova, etc.) that host frontier models.

```python
from huggingface_hub import InferenceClient

client = InferenceClient(provider="together", model="arcinstitute/evo2_40b")
output = client.text_generation("ATCGGCTA", max_new_tokens=64)
```

Check the model card for which providers host it. Not every catalog model is available — many are research-only and only hosted by their authors as a Space.

## After loading: standard pipelines apply

Once the model is loaded, scientific models behave like any other `transformers` model — you embed sequences, generate, classify, or fine-tune. The unique steps are:

1. **Use the matching tokenizer/feature extractor.** Don't try to feed protein sequences to a DNA tokenizer; the alphabets are different and the model will silently produce garbage.
2. **Match the preprocessing from pretraining.** For fine-tuning, the catalog's blog posts often spell out exact preprocessing recipes (special tokens, normalization, augmentation). Read them before training.
3. **Mind the output head.** Many scientific foundation models are masked-LM by default; classification or regression downstream tasks usually need an extra head layered on `model.last_hidden_state`.

## When you can't run a model anywhere

Some catalog models are demo-only — the authors host a Space but never published weights. In that case:

- See `using-spaces.md` and call the Space via `gradio_client`.
- Or surface this constraint to the user and offer the next-best fully-open alternative from the same topic file.
