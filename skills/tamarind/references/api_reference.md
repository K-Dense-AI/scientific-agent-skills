# Tamarind Bio REST API reference

Reviewed 2026-09-30 against the [current OpenAPI](https://app.tamarind.bio/api/openapi.json),
[REST guide](https://app.tamarind.bio/llms-full.txt), and
[public catalog](https://app.tamarind.bio/tools.json). These are documentation
checks, not authenticated endpoint tests.

All paths below are relative to `https://app.tamarind.bio/api`, or the user's
organization deployment's `/api` base. Requests use `x-api-key` except public
catalog discovery. Do not send the key when downloading a signed storage URL.

## Endpoint map

| Method | Path | Request and response |
|---|---|---|
| GET | `/tools-catalog` | Public catalog; also at host-level `/tools.json`. Optional `type`/`tag` filters; `tools` contains public types and conditional required settings. |
| GET | `/tools` | Account-scoped array with `name`, descriptions, trimmed `settings`, and optional output metadata. `custom=true` selects legacy custom tools only. |
| GET | `/tools/{name}/schema` | JSON Schema for the settings object. Optional `version` pins a custom build. 404 covers missing, inaccessible, and mid-deploy tools. |
| POST | `/validate-job` | `type`, object/array `settings`; optional `jobName` (single), `jobNames` (array), `version`. HTTP 200 contains a `valid` verdict. |
| POST | `/submit-job` | `jobName`, `type`, object `settings`; optional `version`, `projectTag`. 200 is a **plain-text** confirmation. |
| POST | `/submit-batch` | `batchName`, `type`, array `settings`; optional parallel `jobNames`, `version`, `projectTag`. 200 schema has `batchName`, `jobs`, `totalJobs`. |
| GET | `/jobs` | Exact lookup or cursor-paginated listing; shapes below. |
| POST | `/jobs/search` | `jobNames` (up to 1,000), optional `organization`, `includeSubjobs`, `jobEmail`. Returns `jobs`, `notFound`, `statuses`. |
| POST | `/result` | `jobName`; optional `fileName`, `pdbsOnly`, `jobEmail`, `noAsync`. 200 JSON string URL or 202 preparing object. |
| POST | `/stop-job` | `jobName`; stops queued/running work, including stoppable batch children. Returns `message`, `stoppedCount`. |
| DELETE | `/delete-job` | `jobName`; soft-deletes the job/batch children from listings. Result files remain. Unknown name: 400. |
| PUT | `/upload/{filename}` | Binary body; optional `folder`. This route redirects to the upload service; follow redirects. |
| GET | `/files` | Optional `folder`, `includeFolders=true`; complete array of name strings for that folder, no pagination. |
| DELETE | `/delete-file` | Query `filePath` **or** `folder`. A folder request removes its files. |
| GET | `/usage-statistics` | `statistic=hours\|weighted_hours\|jobs`, `scope=user\|organization`; details below. |
| POST | `/submit-pipeline` | Legacy inline execution: `jobName`, `stages`, conditional `initialInputs`, optional `projectTag`. |
| POST | `/run-pipeline` | Legacy saved execution: `jobName`, `pipelineName`, nonempty `initialInputs` array, optional `version`. |

## Discovery and validation

`/tools` is an array, not `{"tools": [...]}`. Each trimmed parameter has `name`
and `required`; optional metadata includes `type`, `description`, `default`,
`options`, `extension`, and `list`. Filter built-ins client-side; arbitrary search
query parameters are not documented. `/tools?custom=true` does not discover
current custom deployments: use the deployed name and `/tools/{name}/schema`.

The latter is a **JSON Schema document**, not the trimmed parameter array and not
an MCP `parameters` envelope. Domain strings may carry `x-tamarind-type`. Numeric
strings and sequence normalization are not fully checked by JSON Schema bounds;
use `/validate-job` for domain validation and file existence. Keep `version`
consistent across schema, validate, and submit for a pinned custom build.

For valid credentials, `/validate-job` returns 200 whether valid or invalid:

- Single success: `{"valid": true, "normalized": {...}}`. Current `normalized`
  contains cleaned settings and defaults intended for submission. Inspect these
  defaults for model/sample-count changes, then submit that settings object.
- Single failure: `valid: false`, `error`, possibly `missing_fields` and `code`.
  `missing_fields` may be empty despite failure. Do not interpret quota/policy
  codes as sequence-format errors.
- `job_name` reflects name normalization when `jobName` was supplied;
  `job_name_changed` indicates a change. Persist this stored name.
- The guide additionally documents `unrecognized_settings`: correct every typo,
  even if `valid` is true. Unknown settings sent directly to submit are carried
  through and may silently leave the intended optional field at its default.
- For array input, inspect **presence of `results`**, not just `valid`.
  `results` holds one verdict per row, with its `index`, and top-level `valid`
  aggregates all rows. If `results` is absent, the whole request was rejected and
  top-level `error` explains why. Array validation supports at most 1,000 rows
  per call and approximately 4.5 MB; large normalized responses can also require
  smaller chunks. Validate all rows, not a representative sample.

Field validation does not reserve compute or re-check every organization policy,
queue constraint, or custom-tool deployment state. A valid verdict can still be
rejected at submission. Do not manually add internal routing settings.

## Names, projects, and batches

Names are sanitized: whitespace becomes `_` and characters outside
`[A-Za-z0-9_.-]` are removed. Send an already-clean, nonempty name of at most 200
characters so exact job lookup works; this is a compatibility limit, not a
100-character submit validator. Parse the actual name from the successful
`<stored-name> submitted to queue.` response. On a lost response, check that
persisted clean name before retrying.

`projectTag` accepts an organization project ID or name. It is normally optional
but required under an organization's project policy. A refusal may include
`availableProjects`; absence does not establish that no projects exist.

Batch `settings` must be a nonempty array. If `jobNames` is supplied it must have
the same length, with no duplicates or child name equal to the parent. Stored
child names may be prefixed/rewritten; enumerate `/jobs?batch=...` rather than
assuming names. The batch cap is **30,000 jobs after design fan-out**, plus a
separate approximately **4.5 MB** request cap. The older `{tool, jobs:[...]}`
alternative is not the current documented contract. Do not rely on undocumented
`weightedHoursBudget`, `maxRuntimeSeconds`, or `gpuType` keys for limits.

## Jobs, status, and pagination

`GET /jobs` query fields: `jobName`, `batch`, `limit` (1–1,000; default 1,000),
`startKey`, `batchOnly`, `includeSubjobs`, `includeSequences`, `organization`, and
`jobEmail`. Use lowercase string `true` for boolean query values.

- Own-account exact `jobName`: row directly, without a `jobs` wrapper.
- Listing or `batch`: `{"jobs": [...], "statuses": {...}, "startKey": ...}`.
  Follow nonempty `startKey` even when a page is short. Batch children paginate.
- `organization=true` exact-name collisions have a legacy exceptional response
  shape; prefer a known owner with `jobEmail`. `/jobs/search` instead selects the
  newest visible match for each requested name, not every member's match.
- `includeSubjobs=true` includes children in ordinary listings. `batchOnly=true`
  selects parents. `includeSequences` is retained for compatibility; do not
  assume it controls `Settings` presence.
- Page `statuses` is generally page-local, but organization queries may return a
  collection-wide tally. Do not sum those tallies to infer batch completion.

Rows require `JobName`, `JobStatus`, `Created`. Other fields are optional:
`Type`, `Started`, `Completed`, `Batch`, `WeightedHours`, `Settings`, `Score`,
`User`, `batchStatus`, `AggregationError`, and result/aggregation metadata.
`Settings` can be JSON text or a structured value; `Score` may be a string,
number, or null. Do not assume every successful tool emits pLDDT or any score.
`/jobs/search` omits large settings/scores/errors and result URLs; fetch individual
details only when needed.

Single-job terminal states are `Complete`, `Stopped`, `Failed`. Handle legacy
`Deleted` and lookup errors; a deleted/missing job need not remain pollable.
A batch parent uses `batchStatus`: `Running`, `Aggregating`, `Complete`, `Stopped`,
`AggregationFailed`. Discriminate by `Type == "batch"`/`batchStatus`, not
`statuses`, which also appears for a single job.

The guide and schema disagree about whether compatibility rows expose a signed
`resultUrl`; the schema makes it optional. Use `/result` for all downloads.

## Results and uploads

Check HTTP status **before** decoding `/result`:

- **200:** `response.json()` is the signed URL string; download with a separate
  GET, no API key. File requests return that file instead of an archive.
- **202:** object with `status: "preparing"`, `jobName`, and `message`; wait and
  repeat the same result call. Do not resubmit compute.
- `noAsync: true` changes a not-yet-built archive to a 400 instead of 202.
- A result request can wait up to approximately 290 seconds for archive assembly;
  use an adequate read timeout and persist the job name to resume later.
- `fileName: "output.log"` is permitted for failed/stopped jobs before completion.

Upload uses `Content-Type: application/octet-stream`; `curl -L --data-binary`
follows the documented upload redirect. The schema describes success fields
`message`, `fileUrl`, `signedUrl`, but verify registered names with `/files` and
pass the **relative stored path** (`target.pdb` or `inputs/target.pdb`) to a tool.
The current guide says a redundant account-email prefix is stripped. Prefer the
relative path; do not construct internal storage keys. Prior results use
`JobName/path/to/file.ext`. Inline text can cause side effects/large bodies during
validation; prefer uploaded paths.

## Usage and pipeline boundaries

Usage defaults to `statistic=hours`, `scope=organization`. The response has
`users` (each with `email`, `total`, per-tool `tools`), `lastUpdated`, and
`metadata.statistic`/`metadata.scope`. Unauthorized organization scope can narrow
to the user: read the applied scope. Weighted hours depend on compute resources;
inspect the current account report rather than assuming a per-job price.

Legacy `/submit-pipeline` requires `jobName` and `stages`; every stage requires
`task` and nonempty `toolSettings` keyed by tool name. `initialInputs` is required
when the first stage uses the `"pipe"` placeholder; file/sequence inputs must
match that stage. Filter names must be in the tool's published `filterMetrics`.
`/run-pipeline` requires `jobName`, `pipelineName`, and `initialInputs` (array of
uploaded PDB filenames or raw sequences with unique basenames), not an `inputs`
alias. Both return plain-text submission confirmations.

For new integrations, consult the [pipeline guide](https://docs.tamarind.bio/tamarind/pipelines.md):
`POST /pipelines/templates` creates a template; `POST /pipelines/validate` checks
the same run body accepted by `POST /pipelines/submit`: required `name`,
`bindings`, and exactly one of `templateId` or inline `pipeline`, plus optional
version and permitted per-node overrides. `idempotencyKey` enables safe retries
on this newer submit surface. Poll
`GET /pipelines/runs/{run_id}` with its lowercase statuses:
`queued`, `running`, `finished`, `partial`, `stopped`, `failed`. Terminal partial
runs need per-step inspection. Pipeline runs are not visible through `/jobs`.
Check the live spec for graph/binding shapes and account feature availability.

## Errors and safe retries

Classic auth rejection is often 400 recovery JSON; jobs use 401 problem JSON or
an earlier gateway 403; usage can return 401. A 403 can also mean policy, quota,
or tool access. Parse the actual error; do not treat every 403 as a budget cap.
Exact unknown job lookup is 400, not a guaranteed 404.

Submit 400 errors may be JSON or plain text, independent of Content-Type.
Ordinary duplicate-name checks return 400; concurrent locks can return 409.
A 413 means the request was rejected before jobs were created (body shape varies
by deployment); split it or upload files. For timeout/5xx ambiguity, inspect the
stored name before retrying a submit. Back off on rate limits, and use batched
status/validation requests instead of flooding per-job calls.
