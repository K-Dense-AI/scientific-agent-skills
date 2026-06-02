# Using Hugging Science Spaces (interactive demos)

A **Hugging Face Space** is a hosted web app — usually Gradio or Streamlit — that wraps a model behind a UI. The `hugging-science` org maintains ~27 of these, and many catalog entries point to a Space rather than (or in addition to) raw weights. Spaces are the fastest way to get scientific output without managing models or GPUs yourself.

Spaces are not just web pages — every Gradio Space exposes a programmatic API. You can call them from Python with `gradio_client` and parse the result as a normal Python value.

## When to call a Space (vs. running the model locally)

Reach for a Space when:
- The user wants a one-shot result, not a fine-tuning loop.
- The model is huge (40B+) and the user has no GPU.
- The model has private weights and the Space is the only public interface.
- The Space already implements complex orchestration (tokenization, sampling, post-processing) you'd otherwise reimplement.

Reach for local execution instead when:
- You'll call it many times in a loop (Spaces have rate limits and queues).
- You're fine-tuning, batching at scale, or need offline reproducibility.
- The Space is private/gated and you can't get access.

## Setup

```bash
uv pip install gradio_client python-dotenv    # or: uv add gradio_client python-dotenv
```

For private/gated Spaces, store the token in `.env` and load it at startup:

```
# .env (gitignored)
HF_TOKEN=hf_...
```

```python
from dotenv import load_dotenv
load_dotenv()    # gradio_client picks up HF_TOKEN automatically
```

## The general pattern

```python
from gradio_client import Client

client = Client("hugging-science/<space-name>")

# Find the API endpoints exposed by this Space:
print(client.view_api())

# Call the endpoint named in view_api(), e.g. "/predict":
result = client.predict(
    "argument_one",
    42,
    api_name="/predict",
)
print(result)
```

`view_api()` is the discovery step — it prints every exposed endpoint with parameter names and types. Always run it once when wrapping a new Space; the function signature varies between Spaces and isn't always obvious from the UI.

## Worked example: BoltzGen (protein/peptide/nanobody binder design)

BoltzGen is one of the flagship Spaces in the `hugging-science` org. It generates designed binders against a target protein.

```python
from gradio_client import Client, file

client = Client("hugging-science/boltzgen-demo")
print(client.view_api())   # inspect first

# Typical call shape (verify against view_api() — endpoint names evolve):
result = client.predict(
    target_pdb=file("/path/to/target.pdb"),
    binder_type="protein",         # or "peptide", "nanobody"
    n_designs=8,
    api_name="/generate",
)
# result is usually a list of generated sequences/structures or a path
# to a downloadable file inside the Space's tmp dir.
```

When the Space returns a file path, `gradio_client` downloads the file to a local temp location and returns the path — handy for pipelines that need the actual output (`.pdb`, `.fasta`).

## File inputs

Many scientific Spaces take structured file inputs (PDB, CIF, FASTA, NIfTI, FITS). Wrap them with `gradio_client.file(...)`:

```python
from gradio_client import file
result = client.predict(file("target.pdb"), api_name="/predict")
```

Don't pass raw paths as strings — Gradio uploads files differently from text and the type wrapper signals which is which.

## Other notable Spaces in `hugging-science`

These are good defaults to know about. Always check `view_api()` for the current signature.

| Space | Purpose |
|---|---|
| `hugging-science/boltzgen-demo` | Protein / peptide / nanobody binder design |
| `hugging-science/anatomy-of-boltzgen` | Educational walkthrough of BoltzGen architecture |
| `hugging-science/dataset-quest` | Browse and submit community scientific datasets |
| `hugging-science/science-release-heatmap` | Visualize AI4Science contributors across orgs and domains |
| `hugging-science/HuggingMod` | Community moderation tooling |

The full live list lives at `huggingface.co/hugging-science` (Spaces tab). If a Space name 404s, the org may have renamed it — search the org page or check the catalog entry.

## Rate limits and queue behavior

Free Spaces share a community GPU queue. For interactive use this is fine; for any kind of batching:

- Expect occasional `queue is full` or timeout errors. Add retry-with-backoff.
- For large workloads, duplicate the Space into your own account (the "Duplicate" button on the Space page) to get private compute.
- Or: run the underlying model locally if weights are public — usually preferable for >10s of calls.

## When the Space has no API

A small minority of Spaces disable the API or are Streamlit-based without a clean programmatic interface. In that case, fall back to local model execution (`using-models.md`) or surface the limitation to the user — don't try to scrape the UI.
