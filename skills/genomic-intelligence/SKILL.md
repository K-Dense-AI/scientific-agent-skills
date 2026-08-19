---
name: genomic-intelligence
description: "Predict regulatory features, gene structure, and expression directly from DNA sequence using Genomic Intelligence's hosted transformer DNA language models — no local GPU or model weights. Six tasks over a REST API and a hosted MCP server (keyless public demo): promoter regions, splice donor/acceptor sites, enhancer activity, chromatin state, sequence-to-expression (log TPM), and de-novo gene annotation, plus a composite find-genes-then-predict-expression workflow. Use when the user has a gene symbol, a genomic region, or a DNA/FASTA sequence and wants any of these predictions, mentions Genomic Intelligence, genomicintelligence.ai, api.genomicintelligence.ai, or mcp.genomicintelligence.ai."
license: MIT
compatibility: Python 3.10+ with the `requests` library for the REST path (no dedicated SDK). Network access required. The REST `/v1` API needs a `GI_API_KEY` (a `gi_` bearer); the hosted MCP server at mcp.genomicintelligence.ai/mcp works keyless against a capped public demo quota, key optional.
metadata:
  version: "1.1"
  skill-author: Genomic Intelligence
  trigger-keywords: DNA sequence prediction, regulatory genomics, promoter prediction, splice site prediction, enhancer activity, chromatin state, gene expression prediction, sequence to expression, log TPM, gene annotation, transcript prediction, DNA language model, genomic intelligence, hosted inference, Ensembl sequence, FASTA prediction, cis-regulatory, TSS window, DeepSEA, DeepSTARR, BigBird splice, MCP genomics
  openclaw:
    primaryEnv: GI_API_KEY
    envVars:
    - name: GI_API_KEY
      required: false
      description: Optional gi_ bearer key for the REST /v1 API and a higher MCP quota. The hosted MCP demo runs keyless; request a key at contact@genomicintelligence.ai.
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

Each task is **its own published operation** with its own request schema, its own
minimum length, and its own closed `options` object — `POST
/v1/tasks/promoter/predict`, `/v1/tasks/splice/predict`,
`/v1/tasks/enhancer/predict`, `/v1/tasks/chromatin/predict`,
`/v1/tasks/annotation/predict`, `/v1/tasks/expression/predict`. The URLs are the
same strings clients already POST to, so no URL construction changes; the shared
`PredictRequest` schema is gone. Body is `{sequence, sequence_name?, model?,
options?}`, returning a `{data, meta}` envelope. What differs per task:

| Task | Recommended mode | Accepted length | `context_window_bp` | Notes |
|---|---|---|---|---|
| `promoter` | sync | 300–500,000 bp | 2,000 bp | sliding-window promoter regions |
| `splice` | sync | 100–500,000 bp | 15,000 bp | donor/acceptor sites (long-context BigBird); strand-specific — feed transcript orientation |
| `enhancer` | sync | 50–500,000 bp | 249 bp | dev + housekeeping scores (DeepSTARR, *Drosophila*) |
| `chromatin` | sync | 200–500,000 bp | 1,000 bp | hundreds of tracks (DeepSEA) |
| `expression` | sync | **9,198–500,000 bp** | n/a (`trained_window_bp` 9,198) | log(TPM+1); needs `tss_index` unless exactly 9,198 bp, plus a cell-type `description` |
| `annotation` | async | 1,000–500,000 bp | n/a | de-novo transcripts; submit + poll |

`Recommended mode` is guidance, not a constraint — every task accepts both. Omit `Prefer` for a synchronous `200`; send `Prefer: respond-async` for a `202` plus `GET /v1/tasks/jobs/{job_id}`. Only the composite workflow enforces a mode, rejecting sync above 50,000 bp with `413 sync_too_large`.

**The minimum is admission control, not regime.** A request above the floor but
shorter than the selected model's `bio_spec.context_window_bp` is *accepted and
scored* — against a window padded out to the context window. Enhancer is the
sharp case: the bound is 50 bp (DeepSTARR's gate) but the context window is
249 bp, so 50–248 bp is scored mostly on padding. Compare your length against
`context_window_bp` from `GET /v1/tasks/{task}/models` to know whether the model
saw real sequence. Longer-than-context input is fine — the scanner steps a
prediction window at a time and pads only the final partial window.

Under the floor and over the 500,000 bp cap are **both `422 validation_failed`**
at `loc ["body","sequence"]`; over-length is *not* a `413`. All lengths are
measured after whitespace is stripped, so a line-wrapped FASTA body can be pasted
verbatim (a `>` header line still fails the alphabet check).

`options` is typed and **closed** (`additionalProperties: false`) per task — an
unknown key is a hard `422 validation_failed` with `type: "extra_forbidden"`,
never ignored:

| Task | `options` keys |
|---|---|
| promoter | `threshold` (0–1, default 0.5) |
| splice | `threshold` (0–1, default 0.5), `site_types` (subset of `["donor","acceptor"]`, default both) |
| enhancer | *(none)* |
| chromatin | `threshold` (0–1, default 0.5) |
| annotation | `batch_size` (1–128, default 8), `shift_coordinates`, `reverse_complement` (default true) |
| expression | `description` — **required**, and the only key |

`Prefer: respond-async` is a declared header on **all six** predict operations
and on the composite, not just `annotation` — see [Async](#async-any-task-annotation-always).

**Omit `model` and the API uses the task's default** — that is the recommended
call. Default model IDs are intentionally **not** documented here: defaults
change and retired IDs fail hard, so never hardcode one. To pin a model, or to
pick a non-human one (Drosophila, yeast, and Arabidopsis models exist for several
tasks), discover IDs at call time with `GET /v1/tasks/{task}/models` (REST) or
`list_models` (MCP) — and **never invent one**. Full per-task output shapes are
in `references/tasks.md`.

`expression` is the strictest of the six: alone among them its schema requires
`options` as well as `sequence`. Three hard rules it enforces — every violation
is a `422`, nothing is padded or clamped, and there is no opt-out flag, header,
or query parameter:

- **It always scores exactly one 9,198 bp TSS-centred window** —
  `sequence[tss_index-4599 : tss_index+4599]`. The endpoint itself accepts
  **9,198–500,000 bp**; anything below 9,198 bp is rejected outright.
- **`tss_index` is required unless the sequence is exactly 9,198 bp.** It is the
  0-based TSS offset into the **whitespace-stripped** sequence, bounded by
  `4599 ≤ tss_index ≤ len(sequence) − 4599`. At exactly 9,198 bp it defaults to
  4,599, the only legal value there. So you may submit a whole locus (up to
  500 kb) and let the server cut the window — but the server does **not**
  discover the TSS for you (that is the composite workflow's job), and does
  **not** reverse-complement: submit gene-sense sequence.
- **`options.description`** — a cell-type / assay string (e.g. `"K562 cells"`) —
  is required, and is the **only** key `expression` accepts inside `options`.
  Unknown top-level body fields are rejected too.

> Gotcha: the legal `tss_index` range is wide, so an offset that is merely
> *wrong* (counted over raw FASTA characters including newlines, or relative to
> a locus start rather than the submitted slice) does not error — it returns a
> confident `200` for the wrong window. Assert on
> `meta.task_specific_counts.scored_window` / `.tss_index` in the response.
> Also note `data.input.sequence_length` is the **scored** length (always
> 9,198); the length you submitted is `data.input.submitted_sequence_length`
> (and `meta.sequence_length`).
>
> Both `tss_index` violations — "required unless exactly 9,198 bp" and the range
> check — come from a whole-model validator, so they report at `loc: ["body"]`,
> **never** `body.tss_index`. Match on `error.code == "validation_failed"`; use
> the message for display only, and never branch on `loc`.

## Sequence acquisition

You rarely start from a raw 9,198 bp string. Acquire sequence first:

- **From a gene symbol** → MCP `fetch_ensembl_sequence(gene=...)`; **from
  coordinates** → `fetch_region(region=...)`. Both fetch public Ensembl reference
  sequence (no key). REST users can query Ensembl REST directly. (`find_genes` is
  the annotation task, not an acquisition tool.)
- **For `expression`** → use the TSS-centred fetch so the window is exactly
  9,198 bp. MCP: `fetch_gene_for_expression` (handles the centring). Otherwise
  fetch a wider locus and pass the TSS as `tss_index` so the server cuts the
  window — but compute that offset on the stripped nucleotide string, not on
  file characters.
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

def predict(task, sequence, sequence_name, model=None, options=None, tss_index=None):
    body = {"sequence": sequence, "sequence_name": sequence_name}
    if model:   body["model"] = model
    if options: body["options"] = options
    if tss_index is not None: body["tss_index"] = tss_index   # expression only
    # Each task is its own published operation, but the URL string is unchanged.
    r = requests.post(f"{BASE}/v1/tasks/{task}/predict", headers=HEADERS, json=body)
    # 422 validation_failed  — sequence under the task floor OR over 500,000 bp,
    #                          bad tss_index, missing options.description,
    #                          or ANY unknown body/options key (options is closed)
    # 401 no/bad key · 404 unknown task · 413 body over 16 MiB · 429 rate limit
    r.raise_for_status()
    return r.json()               # {"data": {...}, "meta": {...}}

# Promoter:
out = predict("promoter", seq, "TP53_region")
print(out["data"]["summary"])

# Expression — a pre-cut 9,198 bp TSS-centred window (tss_index defaults to 4,599):
out = predict("expression", tss_window_9198bp, "HBB",
              options={"description": "K562 cells"})
print(out["data"]["prediction"]["expression_log_tpm"])

# Expression — a whole locus; the server slices ±4,599 bp around the TSS you name.
# tss_index is 0-based into the whitespace-stripped sequence.
out = predict("expression", locus_seq, "HBB",
              options={"description": "K562 cells"}, tss_index=tss_offset_in_locus)
print(out["meta"]["task_specific_counts"]["scored_window"])   # confirm the window scored
```

### Async (any task; annotation always)

`Prefer: respond-async` is a declared header parameter on all six predict
operations and on the composite. A `202` carries the same `{data, meta}` envelope
as a sync `200`, with `data = {job_id, status: "accepted", links}`; the job id is
also in the `Content-Location` and `X-Job-Id` response headers. Async is
JSON-only — combining it with a text `format` is rejected. `annotation` is the
task that needs it:

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
- **REST:** one call — `POST /v1/workflows/find-genes-and-predict-expression`,
  body `{sequence, options}` with `sequence` 1,000–500,000 bp and
  `options.description` (cell type / assay) required; a missing or empty
  description is a `422 validation_failed`. It annotates, centres a 9,198 bp
  window on each discovered gene's TSS (padding with `N` up to half the window
  rather than dropping an edge gene), and returns a prediction per gene.
  `meta.task_specific_counts` = `{genes_found, genes_predicted, genes_skipped}`
  with `genes_predicted + genes_skipped == genes_found`; per-gene causes in
  `data.expression_predictions[].skip_reason`. Above **50,000 bp** it forces
  async: a synchronous request over that size is `413 sync_too_large` with
  `error.details = {sequence_length, threshold}` — retry the same body with
  `Prefer: respond-async`.

## Errors

| Code | `error.code` | Meaning | Action |
|---|---|---|---|
| 400 | `bad_request` | Malformed request | Check the body shape |
| 401 / 403 | `unauthorized` / `forbidden` | Missing/invalid key (REST) | Set `GI_API_KEY`; or use the keyless MCP demo |
| 404 | `not_found` | **Unknown task** (`/v1/tasks/bogus/predict`) or unknown job | Check the task name — an unrecognised task is a 404, not a 422 |
| 413 | `payload_too_large` | Raw request body over **16 MiB** | Split the input — this is the body cap, not the sequence cap |
| 413 | `sync_too_large` | Composite called synchronously above 50,000 bp | Retry with `Prefer: respond-async` |
| 415 | `unsupported_format` | Unsupported `format` query value | Use a format the task supports; there is no silent fallback to JSON |
| 422 | `validation_failed` | The most common failure: sequence **under the task floor or over 500,000 bp**, expression below 9,198 bp, a missing/out-of-range `tss_index`, a missing `options.description`, or **any unknown body or `options` key** | Read the message; fix the body |
| 429 | `rate_limited` / `too_many_requests` | Rate / concurrency cap | Back off (honour `Retry-After`); ask GI to raise your tier |
| 5xx | `internal_error` / `service_unavailable` / `model_loading` / `timeout` | Server error | Retry; if persistent, contact support |

`error.code` is a closed 21-value enum (`bad_request`, `unauthorized`,
`forbidden`, `not_found`, `conflict`, `job_expired`, `payload_too_large`,
`sync_too_large`, `unsupported_format`, `validation_failed`,
`too_many_requests`, `rate_limited`, `internal_error`, `timeout`,
`insufficient_memory`, `model_not_found`, `task_not_supported_by_model`,
`model_loading`, `service_unavailable`, `http_error`, `unknown`); treat an
unlisted value as a generic failure, not a parse error.

**Branch on `code`, never on `details` or `loc`.** `details` is keyed on the
sibling `code`, and its shape for `validation_failed` has been in flux — some
deployments return the `{errors: […]}` object the schema declares, others a bare
FastAPI error array (`[{loc, msg, type}, …]`). Treat it as display-only and
accept either shape; `code` is the stable discriminator.

For correlation, prefer the `X-Request-Id` **header**: it is set on every
response, whereas `error.request_id` is absent on some error paths (`413`
historically omitted it). Reading the header first is correct on every
deployment.
Every response carries `RateLimit-Limit`, `RateLimit-Remaining`,
`RateLimit-Reset`, `RateLimit-Policy`; a `429` adds `Retry-After`.

> This describes the contract served from `2026.08.19.4`, verified live. The API
> is pre-GA and still moving; `info.version` in `/v1/openapi.json` reports what a
> given deployment actually serves, and is the arbiter if anything here disagrees.

## Reference files

- `references/tasks.md` — per-task output shapes, model registries, the async
  annotation contract.
- `references/api-and-auth.md` — REST endpoints, the `{data, meta}` envelope,
  auth, base-URL override, tiers.
- `references/mcp.md` — the hosted MCP tool list, the handle-based flow, and the
  `gi://` resources.
- `references/sequence-acquisition.md` — Ensembl fetch calls and the
  expression-window (9,198 bp, TSS-centred) math, including `tss_index`.
