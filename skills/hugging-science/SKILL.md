---
name: hugging-science
description: Use when the user is doing AI/ML work in a scientific domain such as biology, chemistry, physics, astronomy, climate, genomics, materials, medicine, ecology, energy, engineering, math, drug discovery, protein design, weather modeling, theorem proving, single-cell, or PDE solving. Hugging Science is a curated catalog of scientific datasets, models, blog posts, and interactive Spaces. This skill helps discover and use resources via `datasets`, `transformers`, the HF Inference API, `gradio_client`, and methodology citations.
metadata: {"version": "1.1", "skill-author": "K-Dense Inc."}
---

# Hugging Science

Hugging Science is a curated, LLM-friendly index of scientific datasets, models, blog posts, and interactive demos for ML researchers. Use it when a scientific ML question lands in front of you — it's much higher signal than generic search and the entries are pre-filtered for quality and openness.

There are two related surfaces, and you should use both:

- **The catalog at `huggingscience.co`** — a static, parseable index of resources across 17 scientific domains. It exposes `llms.txt` (compact), `llms-full.txt` (full content), and `topics/<slug>.md` (per-domain). These are markdown files designed to be fetched and read.
- **The `hugging-science` Hugging Face organization** — `huggingface.co/hugging-science` — community-submitted datasets, a few models, and ~27 interactive Spaces (notably BoltzGen for protein/binder design, Dataset Quest for submissions, and Science Release Heatmap for ecosystem visualization).

The catalog *points to* resources hosted on the broader Hugging Face Hub. So an entry like `arcinstitute/opengenome2` is a regular HF dataset that you load with the `datasets` library; an entry like `facebook/esm2_t33_650M_UR50D` is a regular HF model you load with `transformers`. The catalog's job is curation and discovery; usage goes through standard Hugging Face APIs.

## When to use this skill

Engage this skill when the user's task involves AI/ML applied to science. Common signals:

- Names a scientific domain (protein, genome, molecule, crystal, weather, climate, galaxy, EEG, microbiome, pathology, plasma, …)
- Asks "is there a dataset/model for X" where X is scientific
- Wants to fine-tune on scientific data, evaluate on scientific benchmarks, or reproduce a scientific ML paper
- Asks about specific known scientific models (Evo-2, ESM2, BoltzGen, Nucleotide Transformer, AlphaFold-derived, etc.)
- Needs an interactive demo for a scientific task (binder design, theorem proving, etc.)

If the task is generic ML (recommendation systems, chatbot RAG, vision on cats and dogs), this skill is **not** the right tool — defer to general HF Hub knowledge instead.

## Core workflow

Most invocations follow this five-step loop. Don't skip discovery — the value of Hugging Science is that it has already filtered hundreds of resources down to high-signal picks per domain.

### 1. Identify the domain(s)

Map the user's task to one or more of the 17 topic slugs:

`astronomy` · `benchmark` · `biology` · `biotechnology` · `chemistry` · `climate` · `conservation` · `earth-science` · `ecology` · `energy` · `engineering` · `genomics` · `materials-science` · `mathematics` · `medicine` · `physics` · `scientific-reasoning`

Some tasks span multiple topics (e.g., drug discovery → `chemistry` + `biology` + `medicine`). Fetch each relevant topic.

### 2. Fetch the relevant catalog content

Use the bundled script for clean, structured access:

```bash
python scripts/fetch_catalog.py topic biology
python scripts/fetch_catalog.py topic materials-science --filter models
python scripts/fetch_catalog.py search "protein language model"
python scripts/fetch_catalog.py all     # full llms-full.txt
```

You can also fetch the raw markdown directly:

- `https://huggingscience.co/llms.txt` — compact index
- `https://huggingscience.co/llms-full.txt` — every entry, every domain
- `https://huggingscience.co/topics/<slug>.md` — one domain (slug is hyphenated, e.g. `materials-science.md`, `earth-science.md`, `scientific-reasoning.md`)

Each entry is a markdown block with `Type`, `Tags`, `HuggingFace` URL (or `Link` for blogs), and a one-line description. See `references/topics-and-slugs.md` for the entry schema and slug list.

### 3. Pick the right resource(s)

Read the descriptions and tags. Match to the user's task with judgment, not keyword overlap. Things to weigh:

- **Scale fit** — Evo-2 40B is overkill for a quick sequence classification on a laptop; ESM2 35M might be perfect.
- **License and access** — most are open, but check the underlying HF model card.
- **Modality alignment** — DNA vs. protein vs. SMILES vs. crystal structure; many "biology" models are not interchangeable.
- **Recency / supersession** — if both an older and newer entry cover the same task, prefer newer unless there's a reason not to.

If you're not sure which resource to pick, briefly present the top 2–3 candidates to the user with their tradeoffs, then proceed once they choose. Don't pick silently when the choice materially changes the work.

For domain-specific go-to picks (the "if in doubt, start here" entries), see `references/flagship-resources.md`.

### 4. Use the resource

The mechanics depend on resource type. Read the matching reference file before writing code:

- **Datasets** → `references/using-datasets.md` — loading via `datasets`, streaming for huge corpora, common columns, splits
- **Models** → `references/using-models.md` — local `transformers`, Hugging Face Inference API, Inference Providers for very large models, GPU sizing
- **Spaces (interactive demos)** → `references/using-spaces.md` — `gradio_client` pattern with a worked BoltzGen example

The reference files are short and focused. If you're already fluent in the relevant API, skim; if not, read fully before writing code. The patterns are different from generic HF usage in a few important places (e.g., `trust_remote_code` requirements, scientific-data dtype gotchas).

### 5. Cite the methodology

When the catalog has a blog post matching the task (`Type: blog` or in the Blog Posts section of a topic file), include its URL when you explain your approach to the user. Methodology blogs are written by the dataset/model authors and answer "why this design" questions that model cards usually skip. Treat them like citations — a one-line "see <link> for the methodology behind X" is plenty.

## Authentication: HF_TOKEN

Many catalog resources are gated (clinical data, large foundation models, private Spaces). Authenticate via the `HF_TOKEN` environment variable.

**Load `HF_TOKEN` from a `.env` file when available** — that's where the user keeps secrets. Use `python-dotenv` at the top of any script that hits the HF API:

```python
from dotenv import load_dotenv
load_dotenv()    # picks up HF_TOKEN from .env in cwd or any parent dir
```

If `.env` doesn't exist or doesn't define `HF_TOKEN`, fall back gracefully — many resources are public and work without it. Don't hard-code tokens, don't echo them, and don't suggest `huggingface-cli login` as the primary path; the user prefers `.env`.

The `.env` file should contain a line like:

```
HF_TOKEN=hf_...
```

If you're creating a new project, also add `.env` to `.gitignore` if it isn't already there.

## A few important things to remember

**The catalog is curated, not exhaustive.** If a user needs a specific resource and Hugging Science doesn't list it, that doesn't mean it doesn't exist on HF Hub. Search HF Hub directly as a fallback. But always *start* with the catalog when the domain matches — the curation is the value.

**The entries are pointers.** Don't try to "use Hugging Science" as if it were an API. There is no Hugging Science inference endpoint. Every actionable resource lives on HF Hub or as a HF Space, and you use it via the standard HF tooling.

**Many scientific models require `trust_remote_code=True`.** Custom architectures (Evo-2, many genomics/materials models) ship custom modeling code. This is normal in this ecosystem. Pass the flag and inform the user.

**Scientific datasets are often large and weirdly-shaped.** Genomics corpora can be billions of tokens; cosmology images can be hundreds of GB; materials datasets contain non-standard objects (crystal structures, graphs). Use streaming (`streaming=True` on `load_dataset`) by default for anything claimed to be over a few GB, and inspect schema before assuming columns.

**Spaces are great for one-off scientific generations.** If the user wants to design a binder for a target protein or run inference on a hosted model demo, calling the Space via `gradio_client` is faster and cheaper than spinning up the model locally. Check `references/using-spaces.md` first — `huggingface.co/hugging-science` has ~27 of these.

**The catalog itself may evolve.** Entries get added regularly; occasionally entries change slugs. If a URL 404s, refetch the topic file or `llms.txt` to get the current state — don't paper over the failure.

## Bundled resources

- `scripts/fetch_catalog.py` — fetch and filter catalog content. Run with `--help` for full usage. Use this in preference to ad-hoc WebFetch calls when you need structured access.
- `references/topics-and-slugs.md` — exact topic slugs, what each covers, and the entry schema.
- `references/using-datasets.md` — patterns and gotchas for loading scientific datasets.
- `references/using-models.md` — running scientific models locally, via Inference API, or via Inference Providers.
- `references/using-spaces.md` — calling HF Spaces (notably BoltzGen) programmatically with `gradio_client`.
- `references/flagship-resources.md` — go-to dataset/model picks per domain when the user wants a sensible default.
