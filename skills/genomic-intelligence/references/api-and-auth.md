# REST API & Authentication

Base URL: `https://api.genomicintelligence.ai` (override with `GI_BASE_URL` for
staging). Live contract: <https://api.genomicintelligence.ai/v1/openapi.json>.

## Authentication

Every `/v1/*` REST call needs a partner bearer key, sent as
`Authorization: Bearer <key>`. Public routes needing no key: `/health`, `/docs`,
`/redoc`, `/v1/openapi.json`.

```bash
export GI_API_KEY="gi_yourkeyhere"
```

Keys begin with `gi_`. Request one at contact@genomicintelligence.ai. Read the
key from the environment (or a `.env` via `python-dotenv`); never hardcode or
commit it.

> The hosted **MCP** server (`mcp.genomicintelligence.ai/mcp`) is different: it
> runs **keyless** against a capped public demo quota, with the key optional for
> a higher quota. Only the **REST** path strictly requires a key. See `mcp.md`.

## Endpoints

Eleven operations are published. The six predict paths are **literal, one per
task** — the templated `/v1/tasks/{task}/predict` is no longer in the document
(the URLs are unchanged, so nothing a client builds needs to change).

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/tasks/promoter/predict` | `PromoterPredictRequest` |
| POST | `/v1/tasks/splice/predict` | `SplicePredictRequest` |
| POST | `/v1/tasks/enhancer/predict` | `EnhancerPredictRequest` |
| POST | `/v1/tasks/chromatin/predict` | `ChromatinPredictRequest` |
| POST | `/v1/tasks/annotation/predict` | `AnnotationPredictRequest` |
| POST | `/v1/tasks/expression/predict` | `ExpressionPredictRequest` (also requires `options`) |
| POST | `/v1/workflows/find-genes-and-predict-expression` | Composite: find genes, predict each one's expression |
| GET | `/v1/tasks/jobs` | List async jobs |
| GET | `/v1/tasks/jobs/{job_id}` | Poll an async job (202 running → 200 terminal) |
| GET | `/v1/tasks/{task}/models` | List available model IDs for a task |
| GET | `/health` | Public liveness |

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

Hand-built requests are unaffected, but a client **generated** from the OpenAPI
document must be regenerated: the shared `PredictRequest` model it was built
from no longer exists.

Success is a `{data, meta}` envelope; `data` is task-specific (see `tasks.md`),
`meta` carries model + request info. **Exception:** `GET /v1/tasks/{task}/models`
is *not* enveloped — it returns a flat
`{task, default_model, models: [{id, name, description, is_default, bio_spec}]}`.

Errors use an `{error}` envelope carrying `code`, `message`, `request_id` and an
optional `details`; the most common is `422 validation_failed` (wrong sequence
length — under the floor *or* over 500,000 bp; over-length is not a `413`).

## `bio_spec` (from `GET /v1/tasks/{task}/models`)

- `request_max_bp` — the enforced ceiling: 500,000 for every model.
- `context_window_bp` — the model's own sliding window; `null` for annotation and
  expression. Live: promoter `g0-promoter-2000bp` 2,000 (300 bp promoter models
  300), splice 15,000, enhancer 249, chromatin 1,000. Compare your sequence length
  against this to know whether the model scored real sequence or padding.
- `trained_window_bp` — fixed receptive field; 9,198 for `g0-expression`, `null`
  for sliding-window models.
- `max_seq_length_bp` — legacy, ambiguous, and being withdrawn. It reads 500,000
  everywhere **except** `g0-expression`, where it is 9,198 — the trained window,
  not a request cap, so reading it as one wrongly rejects the 9,198–500,000 bp
  range expression actually accepts. Never gate on it; use `request_max_bp`.

There is no `strand_sensitive` flag. The splice model is strand-specific in
practice — feed transcript orientation.

## Partner tiers

Keys are scoped to a tier with concurrency and per-minute caps. A `429` means a
cap was hit — back off and retry, or ask GI to raise the tier.
