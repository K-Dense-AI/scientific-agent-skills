# Using scientific datasets from the catalog

Hugging Science dataset entries always link to a Hugging Face Hub dataset (`huggingface.co/datasets/<org>/<name>`). You load them with the standard `datasets` library. The interesting part is what makes scientific datasets *different* from typical NLP/vision datasets — that's what this file is about.

## Install

Use `uv` for all installs:

```bash
uv pip install datasets huggingface_hub      # in an active venv
# or, project-style:
uv add datasets huggingface_hub
# one-off:
uv run --with datasets python my_script.py
```

For private/gated datasets, authenticate via `HF_TOKEN`. **Prefer loading from `.env`:**

```bash
# .env (in project root, gitignored)
HF_TOKEN=hf_...
```

```python
from dotenv import load_dotenv
load_dotenv()                # picks up HF_TOKEN before any HF call
from datasets import load_dataset
ds = load_dataset("opig/OAS")
```

If `python-dotenv` isn't installed: `uv add python-dotenv` (or `uv pip install python-dotenv`).

A surprising number of biomedical datasets are gated (clinical PHI proxies, antibody repertoires from named patients). Check the dataset card before assuming open access.

## Default loading pattern

```python
from datasets import load_dataset

ds = load_dataset("arcinstitute/opengenome2")
print(ds)            # see splits and columns
print(ds["train"][0]) # peek at one row
```

## Use streaming for large datasets — by default

Many scientific corpora are 10 GB to many TB. `load_dataset(..., streaming=True)` returns an `IterableDataset` that pulls shards on demand instead of materializing the whole thing on disk:

```python
ds = load_dataset("arcinstitute/opengenome2", split="train", streaming=True)
for example in ds.take(10):
    ...
```

Rule of thumb: if the dataset card mentions billions of tokens, millions of images, or "TB", default to streaming and only switch to full download when the user explicitly wants offline reproducibility.

## Inspect schema before assuming columns

Generic datasets have predictable columns (`text`, `label`, `image`). Scientific datasets often don't. Before writing preprocessing code, look at one example:

```python
sample = next(iter(load_dataset("opig/OAS", split="train", streaming=True)))
print(sample.keys())
```

Common surprises:
- **Genomics**: columns can be `sequence`, `species`, `taxonomy`, `accession` rather than `text`.
- **Materials**: rows may contain serialized `pymatgen` `Structure` objects or CIF strings — not numeric tensors.
- **Imaging**: medical/astronomy images can be FITS, DICOM, or NIfTI rather than PNG/JPEG. The `image` column may be raw bytes that need a domain-specific decoder.
- **Time series / signals**: EEG, audio, weather often have variable-length arrays under a column like `signal` or `array`; the dtype matters (`float16` vs `float32`) for memory.

## Splits and subsets

- Many scientific datasets ship multiple **configs** (e.g., `load_dataset("Merck/TEDDY", "single_cell")`). If `load_dataset` errors with "Please pick a config", read the dataset card or run `get_dataset_config_names("...")`.
- Some have non-standard split names (`pretrain`, `held_out_species`, `test_chr1`). Don't assume `train/validation/test`.

## Filtering and subsetting

For very large datasets, prefer `filter` on a streaming iterator over downloading and slicing:

```python
ds = load_dataset("opig/OAS", split="train", streaming=True)
human_only = ds.filter(lambda ex: ex.get("species") == "human")
```

To convert a streaming subset into an in-memory dataset for training:

```python
from datasets import Dataset
subset = Dataset.from_list(list(human_only.take(10_000)))
```

## Train/eval handoff to `transformers`

Once shaped correctly, scientific datasets feed `Trainer`/`SFTTrainer` like any other. The bridge is usually a tokenizer or feature extractor that's specific to the domain:

- DNA: tokenizer from the matching DNA model (e.g., `AutoTokenizer.from_pretrained("arcinstitute/evo2_7b", trust_remote_code=True)`).
- Proteins: `AutoTokenizer.from_pretrained("facebook/esm2_t33_650M_UR50D")`.
- SMILES: usually a character-level or BPE tokenizer; check the model card.

If a model and dataset come from the same org, their tokenizers/preprocessors are usually compatible by design — that's a strong signal to pair them.

## Caveats specific to scientific data

- **License**: Some datasets are CC-BY-NC (research only). Check before any commercial deployment suggestion.
- **Versioning**: Major scientific datasets revise their splits over time. Pin a `revision=` if reproducibility matters.
- **Preprocessing must match training**: For foundation models, the catalog's blog posts often document the *exact* preprocessing used in pretraining (tokenizer config, normalization). When fine-tuning, replicate it — small mismatches (e.g., reverse complement augmentation for DNA) can wreck downstream performance.
