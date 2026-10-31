# REST API & Authentication

Base URL: `https://api.genomicintelligence.ai` (override with `GI_BASE_URL` for
staging). Live contract: <https://api.genomicintelligence.ai/v1/openapi.json>.

## Authentication

Prediction and job REST calls need a partner bearer key, sent as
`Authorization: Bearer <key>`. Public routes needing no key: `/health`, `/docs`,
`/redoc`, `/v1/openapi.json`, and `GET /v1/tasks/{task}/models`. The
[official overview](https://docs.genomicintelligence.ai/) documents capability
discovery as public and rate-limited per source IP.

```bash
export GI_API_KEY="gi_yourkeyhere"
```

Keys begin with `gi_`. Request one at contact@genomicintelligence.ai. Read the
key from the environment (or a `.env` via `python-dotenv`); never hardcode or
commit it.

> The hosted **MCP** server (`mcp.genomicintelligence.ai/mcp`) is different: it
> runs **keyless** against a rate- and concurrency-limited public demo tier, with
> the key optional for higher limits. REST prediction requires a key, but
> public model discovery does not. See `mcp.md`.

## Endpoints

Twelve operations are published in contract revision 16. The six predict paths are **literal, one per
task**; the published document has no templated `/v1/tasks/{task}/predict`
operation.

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/tasks/promoter/predict` | `PromoterPredictRequest` |
| POST | `/v1/tasks/splice/predict` | `SplicePredictRequest` |
| POST | `/v1/tasks/enhancer/predict` | `EnhancerPredictRequest` |
| POST | `/v1/tasks/chromatin/predict` | `ChromatinPredictRequest` |
| POST | `/v1/tasks/annotation/predict` | `AnnotationPredictRequest` |
| POST | `/v1/tasks/expression/predict` | `ExpressionPredictRequest` (also requires `options`) |
| POST | `/v1/workflows/find-genes-and-predict-expression` | Composite: find genes, predict each one's expression |
| GET | `/v1/tasks/jobs` | Recent own jobs, `limit=1..500` (default 50); flat `{jobs, count}`, no cursor/offset |
| GET | `/v1/tasks/jobs/{job_id}` | Poll an async job (202 running → 200 terminal) |
| GET | `/v1/tasks/{task}/models` | List available model IDs for a task |
| GET | `/health` | Public liveness; does not validate a prediction key |
| POST | `/v1/workflows/genomic-variant-interpretation` | Separate async-only VCF workflow; see boundary below |

There is no usable templated route to fall back on: the six literal paths are
matched first, and any other task segment is `404 not_found`
(`"Unknown task: bogus"`), never a `422`.

`Prefer: respond-async` is a declared header parameter on all six predict
operations and on the composite — it is not an annotation-only extra. Omit it
for a synchronous `200`; send it for a `202` carrying
`{data: {job_id, status: "accepted", links}, meta}`, with the id also in
`Content-Location` and `X-Job-Id`, then poll `GET /v1/tasks/jobs/{job_id}`.
Async is JSON-only: combining it with a text `format` is a `400`.

## Request / response

Request body: `{sequence, sequence_name?, model?, options?}` — but there is no
longer a shared `PredictRequest`. Each task has its own request model with its own
`minLength` (promoter 300, splice 100, enhancer 50, chromatin 200, annotation
1,000, expression 9,198, composite 1,000; `maxLength` 500,000 for all), and every
one is `additionalProperties: false`. `options` is likewise typed and closed per
task, so an unknown key is `422 validation_failed` with `type: "extra_forbidden"`
at `loc ["body","options","<key>"]`.

**`expression` differs further**: its body is
`{sequence, options, tss_index?, sequence_name?, model?}`, `options` is required
(`ExpressionOptions.required = ["description"]`, the only key it accepts), and
`tss_index` is required unless `sequence` is exactly 9,198 bp. See
`tasks.md#expression`.

Hand-built requests are unaffected. A client **generated** from an older OpenAPI
document must be regenerated against the current one: the shared `PredictRequest`
model such clients were built from is not in the published document.

Success is a `{data, meta}` envelope; `data` is task-specific (see `tasks.md`),
`meta` carries model + request info. **Exceptions:** job listing is flat `{jobs, count}`; `GET /v1/tasks/{task}/models`
is also *not* enveloped — it returns a flat
`{task, default_model, models: [{id, name, description, is_default, bio_spec}]}`.

Errors use an `{error}` envelope carrying `code`, `message`, `request_id` and an
optional `details`; the most common is `422 validation_failed` (wrong sequence
length — under the floor *or* over 500,000 bp; over-length is not a `413`).

## `bio_spec` (from `GET /v1/tasks/{task}/models`)

- `request_max_bp` — the enforced ceiling: 500,000 for every model.
- `context_window_bp` — the model's own sliding window; `null` for annotation and
  expression. The promoter default reports 2,000 (the 300 bp promoter models
  report 300), splice 15,000, enhancer 249, chromatin 1,000. Compare your sequence
  length against this to know whether the model scored real sequence or padding.
- `trained_window_bp` — fixed receptive field; 9,198 for the expression model,
  `null` for sliding-window models.
- The legacy `max_seq_length_bp` is not part of `bio_spec` and is absent from the
  response. It was ambiguous — it read 9,198 for the expression model, the trained
  window rather than a request cap, so gating on it wrongly rejected the
  9,198–500,000 bp range expression accepts. Use `request_max_bp`.

There is no `strand_sensitive` flag. The splice model is strand-specific in
practice — feed transcript orientation.

## Partner tiers

Keys are scoped to a tier with concurrency and per-minute caps. A `429` means a
cap was hit — back off and retry, or ask GI to raise the tier.

## Job lifecycle and response stability

`GET /v1/tasks/jobs/{job_id}` returns 202 while accepted/running, 200 for a
successful result, the underlying 4xx/5xx for a failed job, 404 for unknown or
not-owned work, and 410 for expiration. Completed bodies differ across the six
tasks, the composite, and VCF receipts: branch on **`data.task`**, not first-match
union deserialization. Results are documented as retained 24 hours from last
activity; listing is only a recent list, not a way to page through all history.

`data.summary` keys can change without a revision. `data.input` is an input-label
echo, not a general metadata bag: expression has `sequence_name`, `description`,
`tss_index`; the other five have only `sequence_name`. Use
`meta.sequence_length` and expression's `meta.task_specific_counts.scored_window`.

Record both `info.version` and top-level `x-contract-revision`. The latter is
16 in the reviewed deployment and is the intended contract-change indicator.
`x-sync-limit-bp` applies to JSON delivery. Annotation text formats stay sync
above the threshold and may hit gateway timeouts. An edge-generated 504/reset
may carry no API JSON envelope. Bounded requests and polling do not cancel
server-side work or make a POST retry idempotent.

## VCF workflow boundary

The official API also publishes `POST /v1/workflows/genomic-variant-interpretation`.
This is distinct from calling variants or the sequence tasks above. It requires
bearer auth and `Prefer: respond-async`; its closed request contains `input`
(`type: "s3_object"`, `uri` naming a VCF), required `options.genome_build`
(currently **GRCh37 only**), and optional `client_ref`. Optional settings include
`window` (1–100,000; default 5,000), `tissues` (1–16 strings), and `genes`
(1–1,000 symbols/Ensembl gene IDs; omit for all nearby genes, never an empty list).
The service reads the object and writes an annotated copy beside it; use the
returned `data.output.uri` rather than constructing a filename.

This workflow is **under development** in the current official guide. When
`meta.model` is absent, per-tissue values are not established model results;
an HTTP 200 receipt is not biological validation. Its input build differs from
the GRCh38 default used by human sequence acquisition. Identical requests reuse
a job; changing `client_ref` changes submission identity. Do not infer that
idempotency rule for the six sequence tasks. No VCF submission or object-storage
write was executed in this review. Read the [current workflow contract](https://docs.genomicintelligence.ai/tasks#genomic-variant-interpretation)
before attempting this separate workflow.
