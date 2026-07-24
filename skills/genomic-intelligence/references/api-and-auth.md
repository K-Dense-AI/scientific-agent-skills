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

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/tasks/{task}/predict` | Run a task (sync, or async for `annotation` with `Prefer: respond-async`) |
| GET | `/v1/tasks/jobs/{job_id}` | Poll an async job (202 running → 200 terminal) |
| GET | `/v1/tasks/{task}/models` | List available model IDs for a task |

## Request / response

Request body: `{sequence, sequence_name, model?, options?}`. `options` is
task-specific — most notably `options.description` (required for `expression`).

Success is a `{data, meta}` envelope; `data` is task-specific (see `tasks.md`),
`meta` carries model + request info. Errors use an `{error}` envelope carrying
`code`, `message`, `status` and `request_id`; the most common is `422`
`validation_failed` (wrong sequence length).

## Partner tiers

Keys are scoped to a tier with concurrency and per-minute caps. A `429` means a
cap was hit — back off and retry, or ask GI to raise the tier.
