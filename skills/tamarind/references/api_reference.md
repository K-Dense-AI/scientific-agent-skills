# Tamarind Bio REST API reference

**Spec:** the OpenAPI spec at `https://app.tamarind.bio/openapi.yaml` (3.0, auth `ApiKeyAuth`) covers the 8 **core job endpoints** (`/submit-job`, `/submit-batch`, `/jobs`, `/result`, `/upload/{filename}`, `/files`, `/delete-job`, `/delete-file`) — fetch it for those exact shapes. It does **not** include the discovery/management endpoints (`/tools`, `/usage-statistics`, `/submit-pipeline`, `/run-pipeline`, `/stop-job`) — for those, use this file + the live MCP `getAvailableTools`/`getJobSchema`/`getJobs`. This file also adds the behaviors no spec spells out (response-shape-by-query, two-step result download, batch aggregation polling, REST-vs-MCP field differences).

Base URL: `https://app.tamarind.bio/api/`
Authentication: `x-api-key: <YOUR_KEY>` header on every request.
Interactive docs: [app.tamarind.bio/api-docs](https://app.tamarind.bio/api-docs) · markdown docs at [docs.tamarind.bio](https://docs.tamarind.bio)

These REST recipes use `requests` (Python) or `curl`. The official `tamarind-cli` distribution also provides a Python client for Custom Tools; consult the current SDK reference for supported methods. An MCP server (`https://mcp.tamarind.bio/mcp`, `X-API-Key` header) exposes the same operations with agent-friendly schemas.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/tools` | List available tools and their inline parameter schemas. Returns the **full list** (no server-side filtering — filter client-side). |
| POST | `/submit-job` | Submit one job. Body: `jobName`, `type`, `settings` (+ optional `projectTag`). |
| POST | `/submit-batch` | Submit many jobs of the same tool. See payload shapes below. |
| GET | `/jobs` | List/inspect jobs. Query: `jobName`, `batch`, `limit`, `startKey`, `organization`, `includeSubjobs`, `jobEmail`. |
| POST | `/result` | Get a presigned download URL for job results (two-step — see below). Body: `jobName` (+ optional `fileName`, `pdbsOnly`, `jobEmail`). |
| POST | `/stop-job` | Stop a running or queued job. Body: `jobName`. |
| DELETE | `/delete-job` | Delete a job and its data. Body: `jobName`. |
| PUT | `/upload/{filename}` | Upload a file (`--data-binary`; add `?folder=` to file it). Or get a presigned URL via MCP `uploadFile`. |
| GET | `/files` | List your account's uploaded files as a flat array of filename strings. Query: `folder`, `includeFolders=true`. Does **not** enumerate a specific job's outputs — use MCP `listJobFiles` for that. |
| DELETE | `/delete-file` | Remove a file/folder. Query: `filePath` or `folder`. |
| POST | `/submit-pipeline` | Run a multi-step pipeline defined inline via `stages[]`. |
| POST | `/run-pipeline` | Run a pipeline saved in the UI. Body: `pipelineName`, `initialInputs`/`inputs`. |
| GET | `/usage-statistics` | Usage/billing. Query: `statistic` (`weighted_hours`/`jobs`), `scope` (`user`/org). |

## Request shapes

### GET /tools

Returns a JSON **array**. Each element:

```json
{
  "name": "alphafold",
  "displayName": "AlphaFold",
  "description": "Accurate and quick protein structure prediction ...",
  "github": "https://github.com/...",
  "paper": "https://...",
  "settings": [ { "name": "sequence", "type": "sequence", "required": true, "description": "..." }, ... ]
}
```

In each `settings` param, only `name` and `required` are guaranteed; `type`, `default`, `description`, `options` are present only when applicable (about 60% of params carry `type`). Read them with `param.get("type")`, not `param["type"]`.

`settings` is the tool's inline parameter schema — read it directly, no separate schema endpoint over REST. The REST list is not filtered by query params; filter client-side on `name`/`displayName`/`description`. (The MCP `getAvailableTools` wraps the list as `{"totalTools", "tools":[...]}` and adds `categories`/`tags` per tool plus server-side `search`/`category`/`tag` filtering.)

### POST /submit-job

```json
{
  "jobName": "my-protein-analysis",
  "type": "alphafold",
  "settings": { "sequence": "MKT...", "numRecycles": 3 },
  "projectTag": "proj_xxxxxxxx"
}
```

- `jobName` — unique, `^[a-zA-Z0-9_-]+$`, 1-100 chars.
- `type` — a tool name from `/tools`. The list changes often; never hardcode.
- `settings` — tool-specific; match the schema from `/tools` (or MCP `getJobSchema`).
- `projectTag` — optional `proj_...` ProjectId to file the job under a project.

Response (200): a confirmation string like `myJobName submitted to queue.`

### POST /submit-batch

Two payload shapes appear in the official docs — the **Python** form uses parallel arrays; the **curl** form uses a `jobs[]` array of objects with a `tool` key. The parallel-array form matches the MCP `submitBatch` and is the recommended one:

```json
{
  "batchName": "egfr-screen",
  "type": "alphafold",
  "jobNames": ["seq1", "seq2"],
  "settings": [{ "sequence": "..." }, { "sequence": "..." }],
  "maxRuntimeSeconds": 3600,
  "weightedHoursBudget": 100
}
```

curl-form alternative (same endpoint): `{ "tool": "<type>", "batchName": ..., "jobs": [{ "jobName": ..., "settings": {...} }, ...] }`.

- `jobNames` and `settings` are parallel arrays, same length, 1-100 items, all using the same tool.
- `maxRuntimeSeconds` — optional per-job timeout. `weightedHoursBudget` — optional budget cap.
- The MCP `submitBatch` schema exposes `maxRuntimeSeconds` + `weightedHoursBudget`. Some accounts/tools may accept an optional `gpuType` (seen in the docs UI), but it isn't in `openapi.yaml` or the MCP schema — treat it as unverified and confirm with support before relying on it.

### GET /jobs

**Response shape depends on the query:**
- **List / batch query** (no `jobName`, or `?batch=`/`?organization=`) → `{ "jobs": [...], "startKey": "...", "statuses": {...} }`.
- **By-name** (`?jobName=<name>`) → the **job row object directly** (no `jobs` wrapper). Don't index `["jobs"][0]` on this response.

Each job row includes `JobName`, `Type`, `JobStatus`, `Created`, `Started`, `Completed`, `Settings` (JSON string), `Score` (JSON string, tool metrics), `WeightedHours`. Use `startKey` for pagination past the `limit` (default 1000). Only top-level jobs return by default; add `includeSubjobs=true` for batch subjobs.

**Batch parent rows** have `Type: "batch"` and carry `batchStatus`. Fetched by name (`?jobName=<batchName>`), a complete batch parent also includes `resultUrl` (presigned download). `batchStatus` transitions: `Running` → `Aggregating` → `Complete` (or `AggregationFailed`, with `AggregationError`). Poll the parent's `batchStatus`, not subjob `JobStatus` — subjobs go `Complete` before the aggregated output is ready.

**Discriminate batch vs single by `Type == "batch"` (or presence of `batchStatus`), not by `statuses`.** A by-name response can carry a `statuses` tally even for a single (non-batch) job, so `statuses` presence is not a reliable batch signal.

### POST /result (two-step download)

POST returns a presigned URL as a **bare string** (not JSON). Fetch that URL with a second GET to download the results zip:

```python
url = requests.post(f"{BASE}/result", headers=H, json={"jobName": "myJob"}).text.strip('"')
open("myJob.zip", "wb").write(requests.get(url).content)
```

Optional body fields: `fileName` (one file instead of the zip), `pdbsOnly: true` (PDB outputs only), `jobEmail` (a teammate's job, if permitted).

## Status codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Bad request — invalid parameters/settings |
| 401 | Unauthorized — invalid/missing `x-api-key` |
| 403 | Budget exceeded (org/team) |
| 429 | Rate limited |
| 404 | Not found (e.g. unknown job) |
| 500 | Server error |

## Field-handling rules (important)

**The REST and MCP schemas expose different fields.** The REST `/tools` entry
gives a trimmed per-param view — `{name, type, required, default, description, options}`.
The advanced gating keys `exclude` and `conditionals` appear **only in MCP
`getJobSchema`**, not in REST `/tools` (`restrictOrgs` is no longer returned by
either surface — see below). So don't try to hand-derive what to strip from REST
schema keys — they aren't there. The reliable guard on
both surfaces is **`validateJob`** (MCP): it runs `/submit-job`'s exact validation
without submitting and returns the first error.

- **Build your submit from your own settings, not `validateJob`'s `normalized` output.**
  `normalized` is informational (defaults filled in, sometimes platform-managed
  fields). Submit the same clean settings you validated, not the normalized echo.
- **Platform-internal routing fields** — `submit_method`, `monomer_msa`, `msa` are
  set by the platform. Never pass them.
- **`restrictOrgs`** — org-gated parameters. `getJobSchema` no longer returns this
  key (it's stripped server-side): a parameter your account isn't authorized for is
  dropped from the schema entirely, and any param you do see is one you may set. So
  you won't encounter `restrictOrgs` in a response — don't look for it.
- **`conditionals`** (MCP schema only) — a field only applies when another field
  has a given value (e.g. `pairMode` applies only when `useMSA` is `true`). Don't
  send conditioned fields when their condition isn't met.
- **`exclude: [...]`** (MCP schema only) — marks a field as UI/pipeline-only for a
  surface. Treat it as advisory; `validateJob` is the authority on what a given
  submission accepts.
- **`required: true`** — must be present. Some tools require more than `sequence`
  (e.g. `boltz` requires `inputFormat`). Run `validateJob` to get the first
  missing/invalid field before submitting.
- **File-typed fields with a plain string value are treated as INLINE CONTENT**,
  not a path. To reference an **uploaded file**, use its **bare filename**
  (`target.pdb`) — the platform scopes it to your account, so do NOT email-prefix
  it. The `{email}/{filename}` form is the underlying S3 key, and passing it makes
  `submit-job` 400 with `"The following files have not been uploaded: <email>/<file>"`.
  To reference a **prior job's output**, use `JobName/path/to/file.ext`. Confirm the
  exact registered name with `getFiles` / `GET /files` (a flat list of bare names).

## Authentication and secrets

- Read the key from `TAMARIND_API_KEY` (env or `.env`); never hardcode or commit it.
- The same key authenticates REST (`x-api-key`) and the MCP server (`X-API-Key`).
- Query operations are scoped to the authenticated account (and, with `organization=true`/`jobEmail`, to your org if permitted).
