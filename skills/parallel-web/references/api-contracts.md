# CLI 0.9.3 API contracts

Reviewed 2026-09-30 against the official release source, installed command help,
and current API documentation. This is a map for debugging the CLI workflows;
use the capability references for commands. No authenticated research jobs or
monitor mutations were executed during this review.

## Authentication and installation

`parallel-web-tools[cli]==0.9.3` supplies `parallel-cli`; `parallel-web` is the
separate SDK dependency. Python package installation requires Python 3.10+.
Data APIs use `https://api.parallel.ai` and the `x-api-key` header. The CLI uses
`PARALLEL_API_KEY` before stored credentials. `login` uses device OAuth, with
`--no-browser` for a headless machine, and can provision a data API key. The
OAuth control token is separate from the data API key. Do not manually copy
control bearer tokens into data API requests. `auth` checks local authentication
state; it is not proof that a paid data API request will succeed.

Sources: [release 0.9.3](https://github.com/parallel-web/parallel-web-tools/releases/tag/v0.9.3),
[CLI source](https://github.com/parallel-web/parallel-web-tools/blob/v0.9.3/parallel_web_tools/cli/commands.py),
[authentication source](https://github.com/parallel-web/parallel-web-tools/blob/v0.9.3/parallel_web_tools/core/auth.py),
[Account API](https://docs.parallel.ai/integrations/account-api).

## Endpoint and response map

All POST bodies below are JSON except the device OAuth exchanges handled by
`login`. Paths retain their documented version; FindAll and Ingest have not
moved to `/v1` merely because Search and Extract have.

| CLI workflow | HTTP contract | Response and pagination |
|---|---|---|
| `search` | `POST /v1/search`; requires nonempty `search_queries`; optional `objective`, `mode`, `max_chars_total`, `session_id`, `client_model`. Source/fetch policy, per-result excerpt bounds, location and result limit are nested under `advanced_settings`. | `results`, `search_id`, `session_id`, optional warnings/usage; no cursor. CLI inserts `status: "ok"`. |
| `extract` | `POST /v1/extract`; `urls` required (up to 20); optional objective, queries, total excerpt bound, session/model. Fetch policy, per-result bounds and full-content option are under `advanced_settings`. | `results` plus per-URL `errors`, IDs, warnings/usage. Partial failure can still be an HTTP/CLI success. |
| `research run` | `POST /v1/tasks/runs`; `input`, `processor`, optional `task_spec.output_schema` and `previous_interaction_id`. CLI `--text` uses a text schema; default uses auto schema. | HTTP 202 returns a Task Run with `run_id`, `interaction_id`, `status`, `is_active`. |
| `research status`, `poll` | `GET /v1/tasks/runs/{run_id}`; once completed, `GET /v1/tasks/runs/{run_id}/result`. The result endpoint's server wait parameter is `timeout`; CLI `--timeout` bounds its own polling loop. | API result has `run` and typed `output` (`content`, `basis`). CLI flattens run metadata. Saved text results use `output.content_file` pointing to the Markdown sibling, including in `--json` stdout. |
| `enrich suggest`, `--intent` | `POST /v1beta/tasks/suggest` with `user_intent`; then `POST /v1beta/tasks/suggest-processor` with `task_spec`. | First returns raw input/output JSON schemas; second returns `recommended_processors`. CLI converts output properties into column definitions and falls back to `core-fast` if processor suggestion fails. |
| `enrich run` | `POST /v1/tasks/groups`; then `POST /v1/tasks/groups/{taskgroup_id}/runs` with `default_task_spec` and `inputs`. | CLI asynchronous launch returns `taskgroup_id`, `num_runs`, `url`; it does not write the target table. |
| `enrich status`, `poll` | `GET /v1/tasks/groups/{taskgroup_id}`; then `GET /v1/tasks/groups/{taskgroup_id}/runs?include_input=true&include_output=true`. | Group status contains counts and `is_active`. Runs are an SSE stream, with optional `last_event_id` resumption, not cursor-paginated JSON. CLI poll reduces this to input/output/error records, losing basis and run IDs. |
| `findall run --dry-run` | `POST /v1beta/findall/ingest` with `objective`. | Returns schema suggestions; this is an API call even though no discovery run is created. |
| `findall run` | Ingest, then `POST /v1beta/findall/runs` with objective, entity type, match conditions, generator, match limit, optional exclude list. | Returns `findall_id`, nested status, generator, timestamps. CLI flattens status and metrics. |
| `findall status`, `poll`, `result`, `cancel` | `GET /v1beta/findall/runs/{findall_id}`, `GET /v1beta/findall/runs/{findall_id}/result`, `POST /v1beta/findall/runs/{findall_id}/cancel`. | Result is the current `run` plus `candidates` snapshot; no cursor and no wait-for-completion guarantee. Cancel returns HTTP 204; CLI generates a cancellation acknowledgement. |
| `monitor create` | `POST /v1/monitors`; required `type`, `frequency`, `settings`; optional processor/webhook/metadata. Event-stream query is `settings.query`; snapshot baseline is `settings.task_run_id`. | HTTP 201 Monitor object; settings stay nested, status uses `active`/`cancelled`. |
| `monitor list`, `get`, `events` | `GET /v1/monitors`, `GET /v1/monitors/{monitor_id}`, `GET /v1/monitors/{monitor_id}/events`. | List uses `monitors`/`next_cursor`, defaults to active only (100 per page). Events use `events`/`next_cursor` (20 per page, max 100). CLI fetches one page. Event-group filtering ignores pagination. |
| `monitor update`, `cancel`, `trigger` | `POST /v1/monitors/{monitor_id}/update`, `/cancel`, `/trigger`. Update body contains only changes; `settings` requires `type: "event_stream"`. | Update/cancel return Monitor; trigger returns HTTP 204, meaning queued execution, not completed results. CLI exposes fewer update fields than the API. |

Inspect exit status, JSON error envelopes, and warnings. A successful launch
means work was accepted, not that results exist. Do not repeat a creation
request merely because the local poll timed out. Retrieve the original ID.

## Official references and review limits

- [Current OpenAPI](https://docs.parallel.ai/docs-latest-openapi.json): Search,
  Extract, Tasks/Groups, FindAll and Monitor request/response schemas. Ingest
  suggestion routes are documented separately and absent from this schema.
- [Search migration](https://docs.parallel.ai/search/search-migration-guide):
  V1 required queries, four native modes, nesting, and raw API defaults.
- [Extract migration](https://docs.parallel.ai/extract/extract-migration-guide):
  V1 limits and always-returned server-side excerpts.
- [Task Ingest](https://docs.parallel.ai/task-api/ingest-api): suggestion routes
  and raw schemas. [Task Groups](https://docs.parallel.ai/task-api/group-api)
  explains the streaming result retrieval.
- [Processors](https://docs.parallel.ai/task-api/guides/choose-a-processor):
  standard processors are preferred for new Task workloads; CLI defaults can lag.
- [FindAll candidates](https://docs.parallel.ai/findall-api/core-concepts/findall-candidates):
  match status, conditions, and evidence.
- [Monitor migration](https://docs.parallel.ai/monitor-api/monitor-migration-guide):
  current verbs, nested settings, event types, dates, and pagination.
- [Snapshot prerequisites](https://docs.parallel.ai/monitor-api/quickstart-snapshot):
  a completed Task Run is the baseline.

The CLI guide and some source comments retain legacy authentication or API
wording. For CLI flag availability use the reviewed executable help/source;
for raw HTTP shapes use the current OpenAPI and migration guides. Offline CLI
checks establish argument and serialization behavior, not service access,
account permissions, current billing, or scientific accuracy of returned data.
