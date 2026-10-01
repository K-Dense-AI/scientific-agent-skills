---
name: genomic-intelligence
description: "Predicts regulatory features, gene structure, and expression directly from DNA sequence using Genomic Intelligence's hosted transformer DNA language models — no local GPU or model weights. Six tasks over a REST API and a hosted MCP server (keyless public demo): promoter regions, splice donor/acceptor sites, enhancer activity, chromatin state, sequence-to-expression (log TPM), and de-novo gene annotation, plus a composite find-genes-then-predict-expression workflow. Use when the user has a gene symbol, a genomic region, or a DNA/FASTA sequence and wants any of these predictions, mentions Genomic Intelligence, genomicintelligence.ai, api.genomicintelligence.ai, or mcp.genomicintelligence.ai."
license: MIT
compatibility: Python 3.10+ with the `requests` library for the REST examples. Network access required. The REST `/v1` API needs a `GI_API_KEY` (a `gi_` bearer); the hosted MCP server at mcp.genomicintelligence.ai/mcp works keyless against a rate- and concurrency-limited public demo tier, key optional.
metadata:
  version: "1.4"
  last-reviewed: "2026-10-01"
  skill-author: Genomic Intelligence
  trigger-keywords: DNA sequence prediction, regulatory genomics, promoter prediction, splice site prediction, enhancer activity, chromatin state, gene expression prediction, sequence to expression, log TPM, gene annotation, transcript prediction, DNA language model, genomic intelligence, hosted inference, Ensembl sequence, FASTA prediction, cis-regulatory, TSS window, DeepSEA, DeepSTARR, BigBird splice, MCP genomics
  openclaw:
    primaryEnv: GI_API_KEY
    envVars:
    - name: GI_API_KEY
      required: false
      description: Optional gi_ bearer key for the REST /v1 API and higher MCP rate and concurrency limits. The hosted MCP demo runs keyless; request a key at contact@genomicintelligence.ai.
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

> Research and development use. Not for clinical or diagnostic decisions.

## Two ways to call GI

### Hosted MCP server (keyless; preferred on MCP hosts)

GI hosts an MCP server at `https://mcp.genomicintelligence.ai/mcp` (Streamable
HTTP). When your agent host supports MCP, prefer it: it works **keyless** against
a rate- and concurrency-limited public demo tier, and an optional `gi_` bearer
key raises those limits. It exposes acquisition tools that return a **sequence handle**
(`sequence_ref`) and `predict_*` tools that take that handle, so large sequences
stay out of the context. See [MCP workflow](#mcp-workflow-handle-based) below and
`references/mcp.md`.

### REST API (universal)

Plain HTTP with `requests` against `https://api.genomicintelligence.ai/v1`. The
REST path **requires** a `GI_API_KEY` (a `gi_` bearer). Use it on any host, in
scripts, or when you need the raw envelope. See [Core REST workflow](#core-rest-workflow).

## Access and authentication

1. The **hosted MCP demo is keyless** — try it with nothing set.
2. REST prediction and job operations need a key, sent as `Authorization: Bearer <key>`.
   Public `GET /v1/tasks/{task}/models` discovery needs no key and is rate-limited
   by source IP; inspect model windows and bounds before requesting access.
   See the [current authentication contract](https://docs.genomicintelligence.ai/).
   Request a prediction key at [contact@genomicintelligence.ai](mailto:contact@genomicintelligence.ai).
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
`/v1/tasks/annotation/predict`, `/v1/tasks/expression/predict`. Each path is a
literal string, so nothing needs to be constructed, and there is no shared
`PredictRequest` schema. Body is `{sequence, sequence_name?, model?,
options?}`, returning a `{data, meta}` envelope. What differs per task:

| Task | Recommended mode | Accepted length | `context_window_bp` | Notes |
|---|---|---|---|---|
| `promoter` | sync | 300–500,000 bp | 2,000 bp | sliding-window promoter regions |
| `splice` | sync | 100–500,000 bp | 15,000 bp | donor/acceptor sites (long-context BigBird); strand-specific — feed transcript orientation |
| `enhancer` | sync | 50–500,000 bp | 249 bp | dev + housekeeping scores (DeepSTARR, *Drosophila*) |
| `chromatin` | sync | 200–500,000 bp | 1,000 bp | hundreds of tracks (DeepSEA) |
| `expression` | sync | **9,198–500,000 bp** | n/a (`trained_window_bp` 9,198) | log(TPM+1); needs `tss_index` unless exactly 9,198 bp, plus a cell-type `description` |
| `annotation` | async | 1,000–500,000 bp | n/a | de-novo transcripts; submit + poll; sync JSON above 200,000 bp is `413 sync_too_large` |

`Recommended mode` is guidance, not a constraint — every task accepts both. Omit `Prefer` for a synchronous `200`; send `Prefer: respond-async` for a `202` plus `GET /v1/tasks/jobs/{job_id}`. The one enforced limit is per operation: where `/v1/openapi.json` publishes `x-sync-limit-bp` on a `POST`, a synchronous JSON request above that length is `413 sync_too_large` — 200,000 bp on `annotation` and 50,000 bp on the composite workflow in contract revision 16. Read the field rather than memorising the numbers. Annotation BED/GFF3 stays synchronous at any admitted length and can time out; the other five predict tasks have no hard sync cap.

**The minimum is admission control, not regime.** A request above the floor but
shorter than the selected model's `bio_spec.context_window_bp` is *accepted and
scored* — against a window padded out to the context window. Enhancer is the
sharp case: the floor is 50 bp but the context window is 249 bp, so 50–248 bp is
scored mostly on padding. Compare your length against
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
and on the composite, not just `annotation` — see [Async](#async-any-task-recommended-for-annotation).

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

> Note: the legal `tss_index` range is wide, so an offset that is merely
> *wrong* (counted over raw FASTA characters including newlines, or relative to
> a locus start rather than the submitted slice) does not error — it returns a
> confident `200` for the wrong window. Assert on
> `meta.task_specific_counts.scored_window` / `.tss_index` in the response.
> The submitted length is `meta.sequence_length`; the scored width is always
> 9,198, i.e. `scored_window[1] - scored_window[0]`. In revision 16,
> `data.input` contains only `sequence_name`, `description`, and `tss_index`;
> it does not contain the submitted length or scored window.
>
> Both `tss_index` violations — "required unless exactly 9,198 bp" and the range
> check — come from a whole-model validator, so they surface at the body level
> rather than under `tss_index`. Match on `error.code == "validation_failed"`
> and use the message for display only. Any `loc` tuple quoted in this skill is
> illustrative of that shape, not part of the contract: it is not published in
> the schema and must not be branched on.

## Sequence acquisition

You rarely start from a raw 9,198 bp string. Acquire sequence first:

- **From a gene symbol** → MCP `fetch_ensembl_sequence(gene=...)`; **from
  coordinates** → `fetch_region(region=...)`. Both acquire public reference sequence (no key), using a bundled coordinate
  catalog, cache, UCSC, or Ensembl; retain the returned provenance. REST users can query Ensembl REST directly. (`find_genes` is
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
  for a keyless smoke test; `name` is required.

See `references/sequence-acquisition.md` for the exact Ensembl calls and the
expression-window math.

## Core REST workflow

The following transport recipe was tested with mocked responses, not authenticated
inference. Supply a task-appropriate `seq` before calling it. Use the exact
expression-context wording consistently when comparing predictions.

```python
import os
import time
import requests

BASE = os.environ.get("GI_BASE_URL", "https://api.genomicintelligence.ai").rstrip("/")
HEADERS = {"Authorization": f"Bearer {os.environ['GI_API_KEY']}"}
TASKS = {"promoter", "splice", "enhancer", "chromatin", "annotation", "expression"}

def predict(task, sequence, sequence_name, model=None, options=None, tss_index=None):
    if task not in TASKS:
        raise ValueError("Unknown GI task")
    body = {"sequence": sequence, "sequence_name": sequence_name}
    if model is not None:
        body["model"] = model
    if options is not None:
        body["options"] = options
    if tss_index is not None:
        if task != "expression":
            raise ValueError("tss_index is expression-only")
        body["tss_index"] = tss_index
    r = requests.post(f"{BASE}/v1/tasks/{task}/predict", headers=HEADERS,
                      json=body, timeout=(10, 300))
    r.raise_for_status()
    if r.status_code != 200:
        raise RuntimeError(f"Unexpected prediction status {r.status_code}")
    return r.json()

# After acquiring and checking an appropriate promoter sequence:
# out = predict("promoter", seq, "TP53_region")
# print(out["meta"]["task_specific_counts"]["regions_found"])

# A validated gene-sense expression window, or longer locus with known TSS:
# out = predict("expression", locus_seq, "HBB", tss_index=tss_offset,
#               options={"description": "polyA plus RNA-seq; Homo sapiens K562"})
# assert out["meta"]["sequence_length"] == len("".join(locus_seq.split()))
# assert out["meta"]["task_specific_counts"]["scored_window"] == [tss_offset-4599, tss_offset+4599]
# print(out["data"]["prediction"]["expression_log_tpm"])
```

`data.summary` is for display: its keys may change without a contract revision.
Use the declared fields in `data` and `meta.task_specific_counts` for computation.
A timeout or proxy error may have a non-JSON body; it does not establish that the
inference never ran. Preserve the request ID and avoid blind POST resubmission.

### Async (any task; recommended for annotation)

Send `Prefer: respond-async` on any of the six tasks or the composite. A `202`
is `{data: {job_id, status: "accepted", links}, meta}`. `Content-Location` and
`X-Job-Id` identify the same job. Async is JSON-only; text format plus async is
`400`. Save the job ID before polling. This bounded polling example surfaces
HTTP failures (including `429` and `410`) for the caller to handle:

```python
def submit_annotation(sequence, sequence_name):
    r = requests.post(f"{BASE}/v1/tasks/annotation/predict",
                      headers={**HEADERS, "Prefer": "respond-async"},
                      json={"sequence": sequence, "sequence_name": sequence_name},
                      timeout=(10, 30))
    r.raise_for_status()
    if r.status_code != 202:
        raise RuntimeError(f"Unexpected submission status {r.status_code}")
    return r.json()["data"]["job_id"]

def wait_for_job(job_id, max_polls=120):
    if max_polls < 1:
        raise ValueError("max_polls must be positive")
    for attempt in range(max_polls):
        r = requests.get(f"{BASE}/v1/tasks/jobs/{job_id}", headers=HEADERS,
                         timeout=(10, 30))
        r.raise_for_status()  # failed job -> its underlying 4xx/5xx, not 200
        if r.status_code == 200:
            return r.json()
        if r.status_code != 202:
            raise RuntimeError(f"Unexpected polling status {r.status_code}")
        if attempt + 1 < max_polls:
            time.sleep(5)
    raise TimeoutError(f"Polling stopped; resume this job rather than resubmit: {job_id}")

# job_id = submit_annotation(seq, "TP53_region")  # persist this ID
# result = wait_for_job(job_id)
# assert result["data"]["task"] == "annotation"
# transcripts = result["data"]["transcripts"]
```

`200` is completion; `202` contains `data.status` and `data.progress`.
Unknown/not-owned jobs are `404`; expired jobs are `410 job_expired`.
Results are documented as retained 24 hours from last activity; save results
locally. Job listing is a recent, bounded list, not a paginated archive.

## MCP workflow (handle-based)

On an MCP host, acquire a handle, then predict against it — sequences stay out of
the context:

```
# 1. Acquire a sequence handle (each returns data.ref, passed as sequence_ref):
load_demo_sequence(name="promoter_tp53")  # keyless smoke test; name is required
fetch_ensembl_sequence(gene="TP53", flank_bp=5000)  # include regulatory context
fetch_region(region="chr11:5,225,000-5,235,000")   # coordinates -> handle
fetch_gene_for_expression(gene="HBB")     # TSS-centred 9,198 bp handle for expression

# 2. Predict against the handle:
predict_promoter(sequence_ref=<ref>)
predict_expression(sequence_ref=<ref>, description="K562 cells")
predict_splice(sequence_ref=<ref>)        # + predict_enhancer / predict_chromatin

# 3. Annotation on MCP is `find_genes` (there is no predict_annotation).
#    It takes a handle, not a region, and runs async internally:
find_genes(sequence_ref=<ref>)            # wait=True (default) returns the result
find_genes(sequence_ref=<ref>, wait=False)  # own key only -> job_id; poll get_job(job_id)

# Acquisition returns data.ref; use that value as sequence_ref.
# Discover models with list_models(task); reference context lives in the
# gi://models, gi://docs/tasks, and gi://account MCP resources.
```

The shared demo disables `get_job`, `list_jobs`, and detached `wait=False`.
Keep `wait=True` there; a wait timeout is an error, not a recoverable job handle.
See [MCP details](references/mcp.md) for resources, result envelopes and lifetimes.

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
  `data.expression_predictions[].skip_reason`. Above **50,000 bp** (its `x-sync-limit-bp`) it forces
  async: a synchronous request over that size is `413 sync_too_large` with
  `error.details = {sequence_length, threshold}` — retry the same body with
  `Prefer: respond-async`.

The API also publishes a separate, under-development VCF workflow. Its outputs
are not established model results when `meta.model` is absent; see
[the bounded contract note](references/api-and-auth.md#vcf-workflow-boundary).

## Errors

| Code | `error.code` | Meaning | Action |
|---|---|---|---|
| 400 | `bad_request` | Malformed request | Check the body shape |
| 401 / 403 | `unauthorized` / `forbidden` | Missing/invalid key (REST) | Set `GI_API_KEY`; or use the keyless MCP demo |
| 404 | `not_found` | **Unknown task** (`/v1/tasks/bogus/predict`) or unknown job | Check the task name — an unrecognised task is a 404, not a 422 |
| 413 | `payload_too_large` | Raw request body over **16 MiB** | Split the input — this is the body cap, not the sequence cap |
| 410 | `job_expired` | Result retention elapsed | Recover saved results or deliberately submit new work |
| 413 | `sync_too_large` | Synchronous JSON request above the operation's `x-sync-limit-bp` (200,000 bp on `annotation`, 50,000 bp on the composite) | Retry with `Prefer: respond-async` |
| 415 | `unsupported_format` | Unsupported `format` query value | Use a format the task supports; there is no silent fallback to JSON |
| 422 | `validation_failed` | The most common failure: sequence **under the task floor or over 500,000 bp**, expression below 9,198 bp, a missing/out-of-range `tss_index`, a missing `options.description`, or **any unknown body or `options` key**; also the splice response cap | Read the message; fix the body |
| 429 | `rate_limited` / `too_many_requests` | Rate / concurrency cap | Back off (honour `Retry-After`); ask GI to raise your tier |
| 5xx | `internal_error` / `service_unavailable` / `model_loading` / `timeout` | Server error | Preserve request/job IDs; retry polling with backoff, avoid blind POST resubmission |

`error.code` is a closed 21-value enum (`bad_request`, `unauthorized`,
`forbidden`, `not_found`, `conflict`, `job_expired`, `payload_too_large`,
`sync_too_large`, `unsupported_format`, `validation_failed`,
`too_many_requests`, `rate_limited`, `internal_error`, `timeout`,
`insufficient_memory`, `model_not_found`, `task_not_supported_by_model`,
`model_loading`, `service_unavailable`, `http_error`, `unknown`); treat an
unlisted value as a generic failure, not a parse error.

**Branch first on `code`, never on message text or `loc`.** Pydantic request
failures usually carry `details.errors`; the splice response cap instead carries
`record_count`, `maximum_records`, `sequence_length`, and `threshold`. Handle
these as distinct optional detail shapes. More than 20,000 splice records causes
`422 validation_failed`, not a truncated result; raise the threshold and record
that changed analysis setting. See [task caveats](references/tasks.md).

For correlation, `error.request_id` and the `X-Request-Id` **header** are both
documented on API responses, and success envelopes carry `meta.request_id`. Reading
the header first remains a safe default.
API responses document `RateLimit-Limit`, `RateLimit-Remaining`,
`RateLimit-Reset`, `RateLimit-Policy`; a `429` adds `Retry-After`. The limit is a
burst bucket, not rpm: the published `x-rate-limit-burst-divisor` is 6, so the
sustained minute allowance is six times that header. Proxy failures may omit
these headers and the usual JSON error envelope.

Reviewed 2026-10-01 against live OpenAPI `info.version` **2026.09.22.2
(af902d84)**, `x-contract-revision: 16`, and `gi-mcp` **0.1.0a21**.
Record the contract revision, resolved model ID, assembly, strand/TSS
provenance, options, and experimental description with results. Hash the exact
submitted bases when available. A handle-only MCP acquisition returns a preview,
not the full bases or a checksum: preserve its acquisition parameters and source
release metadata, and do not invent a hash or claim byte-level verification.
[Review evidence and limits](references/review.md) distinguish public discovery,
source review, and mocked examples from inference validation.

## Reference files

- `references/tasks.md` — per-task output shapes, model registries, the async
  annotation contract.
- `references/api-and-auth.md` — REST endpoints, the `{data, meta}` envelope,
  auth, base-URL override, tiers.
- `references/mcp.md` — the hosted MCP tool list, the handle-based flow, and the
  `gi://` resources.
- `references/sequence-acquisition.md` — Ensembl fetch calls and the
  expression-window (9,198 bp, TSS-centred) math, including `tss_index`.
