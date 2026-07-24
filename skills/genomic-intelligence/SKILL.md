---
name: genomic-intelligence
description: Predict regulatory features, gene structure, and expression directly from DNA sequence using Genomic Intelligence's hosted transformer DNA language models — no local GPU or model weights. Six tasks over a REST API and a hosted MCP server (keyless public demo): promoter regions, splice donor/acceptor sites, enhancer activity, chromatin state, sequence-to-expression (log TPM), and de-novo gene annotation, plus a composite find-genes-then-predict-expression workflow. Use when the user has a gene symbol, a genomic region, or a DNA/FASTA sequence and wants any of these predictions, mentions Genomic Intelligence, genomicintelligence.ai, api.genomicintelligence.ai, or mcp.genomicintelligence.ai.
license: MIT
compatibility: Python 3.10+ with the `requests` library for the REST path (no dedicated SDK). Network access required. The REST `/v1` API needs a `GI_API_KEY` (a `gi_` bearer); the hosted MCP server at mcp.genomicintelligence.ai/mcp works keyless against a capped public demo quota, key optional.
metadata: {"version": "1.0", "skill-author": "Genomic Intelligence", "trigger-keywords": "DNA sequence prediction, regulatory genomics, promoter prediction, splice site prediction, enhancer activity, chromatin state, gene expression prediction, sequence to expression, log TPM, gene annotation, transcript prediction, DNA language model, genomic intelligence, hosted inference, Ensembl sequence, FASTA prediction, cis-regulatory, TSS window, DeepSEA, DeepSTARR, BigBird splice, MCP genomics", "openclaw": {"primaryEnv": "GI_API_KEY", "envVars": [{"name": "GI_API_KEY", "required": false, "description": "Optional gi_ bearer key for the REST /v1 API and a higher MCP quota. The hosted MCP demo runs keyless; request a key at contact@genomicintelligence.ai."}]}}
required_environment_variables: [{"name": "GI_API_KEY", "prompt": "Genomic Intelligence API key (gi_ bearer). Optional — the hosted MCP demo works keyless; a key unlocks the REST /v1 API and a higher quota.", "required_for": "optional features"}]
---

# Genomic Intelligence — DNA Sequence Models

Genomic Intelligence (GI) serves transformer DNA language models over six
sequence-analysis tasks on managed GPUs. Give it a **gene symbol**, a **genomic
region**, or a **DNA/FASTA sequence**; it returns structured predictions —
promoter regions, splice sites, enhancer activity, chromatin state, expression
(log TPM), and de-novo gene annotation. Nothing runs locally: no model weights,
no GPU, no heavy Python stack. It is a thin client over a hosted, versioned
inference API.

**Official docs:** [docs.genomicintelligence.ai](https://docs.genomicintelligence.ai) ·
REST contract at [api.genomicintelligence.ai/v1/openapi.json](https://api.genomicintelligence.ai/v1/openapi.json) ·
hosted MCP server at `https://mcp.genomicintelligence.ai/mcp`

## When to use this skill

Use GI when the user has DNA and wants a model prediction:

- **Find promoters** in a genomic region (`promoter`)
- **Predict splice** donor/acceptor sites (`splice`)
- **Score enhancer activity** — developmental & housekeeping (`enhancer`)
- **Annotate chromatin state** across hundreds of tracks (`chromatin`)
- **Predict expression** as log(TPM+1) from a sequence + cell-type context (`expression`)
- **Annotate genes/transcripts** de novo, no reference needed (`annotation`)
- **Find the genes in a region and predict each one's expression** (composite)

Not for local alignment, variant calling, or file I/O — use a local tool
(BioPython, bcftools) for those. GI is for **model inference from sequence**.

> For research and development use, **not clinical or diagnostic decisions**.

## Two ways to call GI

### Hosted MCP server (best for AI agents — keyless)

GI hosts an MCP server at `https://mcp.genomicintelligence.ai/mcp` (Streamable
HTTP). When your agent host supports MCP, prefer it: it works **keyless** against
a capped public demo quota (zero setup), and an optional `gi_` bearer key raises
the quota. It exposes acquisition tools that return a **sequence handle**
(`sequence_ref`) and `predict_*` tools that take that handle — so large sequences
never bloat the context. See [MCP workflow](#mcp-workflow-handle-based) below and
`references/mcp.md`.

### REST API (universal)

Plain HTTP with `requests` against `https://api.genomicintelligence.ai/v1`. The
REST path **requires** a `GI_API_KEY` (a `gi_` bearer). Use it on any host, in
scripts, or when you need the raw envelope. See [Core REST workflow](#core-rest-workflow).

## Access and authentication

1. The **hosted MCP demo is keyless** — try it with nothing set.
2. The **REST `/v1` API needs a key**, sent as `Authorization: Bearer <key>`.
   Request one at [contact@genomicintelligence.ai](mailto:contact@genomicintelligence.ai).
3. **Never hardcode the key.** Read it from the `GI_API_KEY` environment variable
   (or a `.env` via `python-dotenv`). Never commit keys.

```bash
export GI_API_KEY="gi_yourkeyhere"     # optional for MCP; required for REST
export GI_BASE_URL="https://api.genomicintelligence.ai"   # override for staging
```

Keys are scoped to a partner tier with concurrency and per-minute caps. A `429`
means you hit a cap — back off and retry, or ask GI to raise your tier.

## The six tasks

All REST tasks share one shape: `POST /v1/tasks/{task}/predict` with body
`{sequence, sequence_name, model?, options?}`, returning a `{data, meta}`
envelope. What differs per task:

| Task | Mode | Length bound | Notes |
|---|---|---|---|
| `promoter` | sync | 1–500,000 bp | sliding-window promoter regions |
| `splice` | sync | 1–500,000 bp | donor/acceptor sites (long-context BigBird) |
| `enhancer` | sync | 1–500,000 bp | dev + housekeeping scores (DeepSTARR, *Drosophila*) |
| `chromatin` | sync | 1–500,000 bp | hundreds of tracks (DeepSEA) |
| `expression` | sync | **exactly 9,198 bp** | log(TPM+1); needs a cell-type `description` |
| `annotation` | **async** | 1–500,000 bp | de-novo transcripts; submit + poll |

**Omit `model` and the API uses the task's default** — that is the recommended
call. Default model IDs are intentionally **not** documented here: defaults
change and retired IDs fail hard, so never hardcode one. To pin a model, or to
pick a non-human one (Drosophila, yeast, and Arabidopsis models exist for several
tasks), discover IDs at call time with `GET /v1/tasks/{task}/models` (REST) or
`list_models` (MCP) — and **never invent one**. Full per-task output shapes are
in `references/tasks.md`.

Two hard rules the model enforces:

- **`expression` needs exactly 9,198 bp**, a window **centred on the TSS**
  (4,599 upstream + TSS + 4,598 downstream). Any other length is rejected. Use the acquisition helpers below to
  build it — do not truncate by hand.
- **`expression` needs a `description`** — a cell-type / assay string (e.g.
  `"K562 cells"`), passed as `options.description`.

## Sequence acquisition

You rarely start from a raw 9,198 bp string. Acquire sequence first:

- **From a gene symbol** → MCP `fetch_ensembl_sequence(gene=...)`; **from
  coordinates** → `fetch_region(region=...)`. Both fetch public Ensembl reference
  sequence (no key). REST users can query Ensembl REST directly. (`find_genes` is
  the annotation task, not an acquisition tool.)
- **For `expression`** → use the TSS-centred fetch so the window is exactly
  9,198 bp. MCP: `fetch_gene_for_expression` (handles the centring). Do not
  build the window by hand.
- **From a local FASTA** → MCP `store_inline_sequence`, or read the file yourself
  for REST. (`load_local_fasta` exists only in local deployments, not on the
  hosted server.)
- **A demo sequence** → MCP `load_demo_sequence(name=...)` returns a ready handle
  (great for a keyless smoke test); `name` is required.

See `references/sequence-acquisition.md` for the exact Ensembl calls and the
expression-window math.

## Core REST workflow

Sync tasks (promoter, splice, enhancer, chromatin, expression) are one call:

```python
import os, requests

BASE = os.environ.get("GI_BASE_URL", "https://api.genomicintelligence.ai")
HEADERS = {"Authorization": f"Bearer {os.environ['GI_API_KEY']}"}

def predict(task, sequence, sequence_name, model=None, options=None):
    body = {"sequence": sequence, "sequence_name": sequence_name}
    if model:   body["model"] = model
    if options: body["options"] = options
    r = requests.post(f"{BASE}/v1/tasks/{task}/predict", headers=HEADERS, json=body)
    r.raise_for_status()          # 400 invalid; 401 no/bad key; 413 too long; 429 rate limit
    return r.json()               # {"data": {...}, "meta": {...}}

# Promoter:
out = predict("promoter", seq, "TP53_region")
print(out["data"]["summary"])

# Expression — exactly 9,198 bp + a cell-type description:
out = predict("expression", tss_window_9198bp, "HBB",
              options={"description": "K562 cells"})
print(out["data"]["prediction"]["expression_log_tpm"])
```

### Async: annotation

`annotation` is submit-then-poll. Send `Prefer: respond-async`, get a `job_id`,
poll until terminal:

```python
import time

r = requests.post(f"{BASE}/v1/tasks/annotation/predict",
                  headers={**HEADERS, "Prefer": "respond-async"},
                  json={"sequence": seq, "sequence_name": "TP53"})
r.raise_for_status()              # 202 Accepted
job_id = r.json()["data"]["job_id"]

while True:
    j = requests.get(f"{BASE}/v1/tasks/jobs/{job_id}", headers=HEADERS)
    if j.status_code == 200:      # terminal: body is the final {data, meta}
        break
    j.raise_for_status()          # 202 = still running (2xx, won't raise)
    time.sleep(5)                 # ~20 s typical for ~20 kb
transcripts = j.json()["data"]["transcripts"]
```

## MCP workflow (handle-based)

On an MCP host, acquire a handle, then predict against it — sequences stay out of
the context:

```
# 1. Acquire a sequence handle (each returns a sequence_ref):
load_demo_sequence(name="promoter_tp53")  # keyless smoke test; `name` is REQUIRED
fetch_ensembl_sequence(gene="TP53")       # gene symbol or Ensembl ID -> handle
fetch_region(region="chr11:5,225,000-5,235,000")   # coordinates -> handle
fetch_gene_for_expression(gene="HBB")     # TSS-centred 9,198 bp handle for expression

# 2. Predict against the handle:
predict_promoter(sequence_ref=<ref>)
predict_expression(sequence_ref=<ref>, description="K562 cells")
predict_splice(sequence_ref=<ref>)        # + predict_enhancer / predict_chromatin

# 3. Annotation on MCP is `find_genes` (there is no predict_annotation).
#    It takes a handle, not a region, and runs async internally:
find_genes(sequence_ref=<ref>)            # wait=True (default) returns the result
find_genes(sequence_ref=<ref>, wait=False)  # -> job_id; poll get_job(job_id)

# Discover models with list_models(task); reference context lives in the
# gi://models, gi://docs/tasks, and gi://account MCP resources.
```

## Composite: find genes, then predict expression

To answer "what genes are in this region and how are they expressed?", use the
composite:

- **MCP:** `find_genes_and_predict_expression(sequence_ref=..., description=...)`
  — takes a **handle, not a region** (acquire one with `fetch_region` first);
  `description` is required. Finds genes in the sequence and returns an
  expression prediction for each.
- **REST:** call gene discovery, then loop `expression` per gene (build each
  TSS-centred 9,198 bp window via the acquisition helpers).

## Errors

| Code | Meaning | Action |
|---|---|---|
| 400 | Invalid request / bad sequence | Check the body; expression must be exactly 9,198 bp and carry `description` |
| 401 | Missing/invalid key (REST) | Set `GI_API_KEY`; or use the keyless MCP demo |
| 413 | Sequence too long | Stay within the task's length bound (≤500,000 bp) |
| 429 | Rate / concurrency cap | Back off and retry; ask GI to raise your tier |
| 422 | Validation failed (`validation_failed`) | The most common failure: expression not exactly 9,198 bp, or a sequence below the model's minimum length |
| 5xx | Server error | Retry; if persistent, contact support |

## Reference files

- `references/tasks.md` — per-task output shapes, model registries, the async
  annotation contract.
- `references/api-and-auth.md` — REST endpoints, the `{data, meta}` envelope,
  auth, base-URL override, tiers.
- `references/mcp.md` — the hosted MCP tool list, the handle-based flow, and the
  `gi://` resources.
- `references/sequence-acquisition.md` — Ensembl fetch calls and the
  expression-window (9,198 bp, TSS-centred) math.
