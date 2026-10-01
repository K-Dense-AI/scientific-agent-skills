# Open Notebook API Reference

Reviewed 2026-09-30 against **v1.14.0** and main commit
`3127f14ea9dbb519f0e4ddc64a0742ca644ba6ef`. Routes below are from the official
[router source](https://github.com/lfnovo/open-notebook/tree/v1.14.0/api/routers),
[request/response models](https://github.com/lfnovo/open-notebook/blob/v1.14.0/api/models.py),
and [podcast service](https://github.com/lfnovo/open-notebook/blob/v1.14.0/api/podcast_service.py).
Source verification and local mocked tests are not authenticated end-to-end tests.
The installed instance's `/openapi.json` is authoritative for its version.

## Transport and authentication

Base: `http://localhost:5055/api`. Tables use full `/api` paths. Interactive docs
are `/docs` and `/redoc` on the backend origin, not below `/api`.
If `OPEN_NOTEBOOK_PASSWORD` is set on the server, send
`Authorization: Bearer <instance-password>` on every protected request, including
downloads. Otherwise authentication is disabled. The encryption key is for server
credential storage; it is neither a bearer token nor a client requirement.

The [middleware configuration](https://github.com/lfnovo/open-notebook/blob/v1.14.0/api/main.py)
excludes `/`, `/health`, `/docs`, `/openapi.json`, `/redoc`, `/api/auth/status`, and
`/api/config`; CORS `OPTIONS` is also exempt. There is no OAuth token exchange in
this password mechanism.

Use finite HTTP timeouts, check status before parsing, preserve record IDs returned
by the server (`notebook:...`, `source:...`, `model:...`), and URL-encode path segments.
Mutating requests have no documented idempotency-key contract; do not blindly retry
a timed-out creation or generation request. Check for an existing record/job first.
Most responses are JSON with success status 200; credential creation is 201.

## Notebooks

| Method and path | Inputs and response |
| --- | --- |
| `GET /api/notebooks` | Optional `archived` boolean; `order_by` defaults to `updated desc`, accepts `name`, `created`, `updated` with optional `asc`/`desc`. Returns an array; no limit/offset. |
| `POST /api/notebooks` | JSON required `name`, optional `description` default `""`; returns notebook. |
| `GET /api/notebooks/{notebook_id}` | Returns notebook; also records its last-viewed timestamp. |
| `PUT /api/notebooks/{notebook_id}` | JSON optional `name`, `description`, `archived`; returns notebook. |
| `GET /api/notebooks/{notebook_id}/delete-preview` | Returns `notebook_id`, `notebook_name`, `note_count`, `exclusive_source_count`, `shared_source_count`. |
| `DELETE /api/notebooks/{notebook_id}` | Query `delete_exclusive_sources=false`. Always removes associated notes/chat sessions, unlinks shared sources, optionally deletes exclusive sources. Returns `message`, `deleted_notes`, `deleted_sources`, `unlinked_sources`, `deleted_chat_sessions`. |
| `POST /api/notebooks/{notebook_id}/sources/{source_id}` | No body; links source and returns `message`. Verify membership before repeated calls; do not depend on duplicate-link prevention. |
| `DELETE /api/notebooks/{notebook_id}/sources/{source_id}` | No body; removes association, returns `message`. Does not delete the source. |

Notebook objects have `id`, `name`, `description`, `archived`, `created`, `updated`,
`source_count`, and `note_count`. There is no `updated_at` sort field or
`delete_sources` query parameter. The source-link handler's existing-reference
lookup uses the reverse edge direction from its insertion at this reviewed version;
its advertised idempotence is therefore not treated as a reliable contract here.

## Sources

| Method and path | Inputs and response |
| --- | --- |
| `GET /api/sources` | Optional `notebook_id`; `limit=50` (1–100), `offset=0` (nonnegative), `sort_by=updated`, `sort_order=desc`. Allowed sorts: `type`, `title`, `created`, `updated`, `insights_count`, `embedded`. Array of summaries, no total/cursor. |
| `POST /api/sources` | Form fields below; multipart when uploading bytes. Returns source. |
| `POST /api/sources/json` | JSON `SourceCreate` with equivalent native booleans/lists; legacy supported JSON route. Server `file_path` is allowed only within its uploads directory; local client paths do not upload files. |
| `GET /api/sources/{source_id}` | Full source including `full_text`, notebook associations and processing fields; records a view. |
| `PUT /api/sources/{source_id}` | JSON optional `title`, `topics` (list of strings, plural); returns source. |
| `DELETE /api/sources/{source_id}` | Deletes source; returns `message`. |
| `GET /api/sources/{source_id}/status` | Returns nullable `status`, `message`, nullable `processing_info`, nullable `command_id`. |
| `GET /api/sources/{source_id}/download` | Binary original uploaded file; 404 if missing, 403 if outside allowed storage. |
| `HEAD /api/sources/{source_id}/download` | 200 without body if file is available; same access/existence checks. |
| `POST /api/sources/{source_id}/retry` | No body; returns newly queued source with `command_id`. Requires notebook association and reusable content. Retry requests embeddings regardless of original `embed`. |
| `GET /api/sources/{source_id}/insights` | Array with `id`, `source_id`, `insight_type`, `content`, nullable `created`/`updated`. |

Form contract:

| Field | Meaning |
| --- | --- |
| `type` | Required: `link`, `upload`, or `text`. |
| `url` | Required for `link`; server fetches it and rejects disallowed destinations. |
| `file` | Multipart bytes for `upload`. |
| `content` | Required for `text`; `text` is not this field. |
| `title` | Optional source title. |
| `notebooks` | JSON-encoded list of notebook IDs, max 50. |
| `notebook_id` | Deprecated single-notebook alternative; do not combine with `notebooks`. |
| `transformations` | JSON-encoded list of transformation IDs, max 50; default `[]`. |
| `embed` | String boolean, default `false`; explicitly enable for vector retrieval. |
| `delete_source` | String boolean, default `false`; deletes original uploaded file after processing when enabled. |
| `async_processing` | String boolean, default `false`; `process_async` is ignored. |

Source objects include `id`, nullable `title`, `topics`, `asset` (`file_path`, `url`),
`full_text`, `embedded`, `embedded_chunks`, nullable `file_available`, `created`,
`updated`, nullable `command_id`, `status`, `processing_info`, and `notebooks`.
List summaries omit `full_text`/`notebooks` and include `insights_count`.
Paginate until a short/empty page, using fixed sort order; offset pages can shift
if the collection is modified during traversal.

For asynchronous processing, expect new/queued/running/completed/failed states; other
worker states can appear. Only completed is a positive job result. Unknown/missing
statuses must not imply success. A synchronous/legacy source may have `status=null`
and no command: fetch it and inspect text. Successful extraction is distinct from
embedding completion. Inspect errors before an explicit retry; the reviewed retry
handler can swallow its own active-job check, so clients should refuse active jobs.

## Notes

| Method and path | Inputs and response |
| --- | --- |
| `GET /api/notes` | Optional `notebook_id`; array, no pagination. |
| `POST /api/notes` | JSON required `content`; optional `title`, `note_type` default `human`, `notebook_id`. Returns note. |
| `GET /api/notes/{note_id}` | Returns note. |
| `PUT /api/notes/{note_id}` | JSON optional `title`, `content`, `note_type`; returns note. |
| `DELETE /api/notes/{note_id}` | Deletes note; returns `message`. |

Use `human` or `ai` for `note_type`. An AI note with content and no title invokes a
model to generate the title. Responses have `id`, nullable `title`, `content`,
`note_type`, `created`, `updated`, and nullable `command_id` for background work.

## Chat

| Method and path | Inputs and response |
| --- | --- |
| `GET /api/chat/sessions` | **Required** query `notebook_id`; returns session array. |
| `POST /api/chat/sessions` | JSON required `notebook_id`, optional `title`, `model_override`; returns session. |
| `GET /api/chat/sessions/{session_id}` | Session plus `messages[]`. |
| `PUT /api/chat/sessions/{session_id}` | JSON optional `title`, `model_override`; returns session. |
| `DELETE /api/chat/sessions/{session_id}` | Returns `{success, message}`. |
| `POST /api/chat/context` | Required JSON `notebook_id`, `context_config`; returns `{context, token_count, char_count}`. |
| `POST /api/chat/execute` | Required JSON `session_id`, `message`, `context`; optional `model_override`; returns `{session_id, messages}` JSON. |

A session has `id`, `title`, nullable `notebook_id`, `created`, `updated`, nullable
`message_count` and `model_override`. Messages use `id`, `type` (`human`/`ai`),
`content`, nullable `timestamp`—not a `role` key. Execute returns updated history;
take the last AI message rather than expecting a top-level `response` string.

Explicit context configuration:

```json
{
  "notebook_id": "notebook:example",
  "context_config": {
    "sources": {"source:example": "full content"},
    "notes": {}
  }
}
```

Source states are `full content`, `insights`, `not in context`; notes support full
content or exclusion. `{}` requests all notebook items with short context;
`{"sources": {}, "notes": {}}` selects none. The server can skip unavailable IDs
without failing the request. Check returned IDs/content and token count. Pass
only the returned `context` member into Execute. `include_sources`/`include_notes`
and top-level source/note ID lists are not a context-building protocol.

## Search and Ask

| Method and path | Inputs and response |
| --- | --- |
| `POST /api/search` | JSON below; returns `{results: [...], total_count, search_type}`. |
| `POST /api/search/ask/simple` | Required `question`, `strategy_model`, `answer_model`, `final_answer_model`; returns `{answer, question}`. |
| `POST /api/search/ask` | Same Ask body; returns `text/event-stream`. |

```json
{
  "query": "treatment allocation",
  "type": "vector",
  "limit": 10,
  "search_sources": true,
  "search_notes": true,
  "minimum_score": 0.2
}
```

`type` defaults to `text`; vector mode requires a configured default embedding
model and embedded content. `limit` is 1–1000 (default 100), `minimum_score` is 0–1
(default 0.2). `total_count` is the length of the returned list, not the total number
of matching corpus records. Results are dictionaries; vector results can include
`similarity`. No offset/cursor pagination is exposed by this search endpoint.

The v1.14.0 schema has **no notebook or source filters**. `search_type`,
`source_ids`, `note_ids`, and `min_similarity` in request bodies can be silently
ignored. Current main adds `notebook_id` and `notebook_ids` (max 50) to both Search
and Ask; omit/empty means global. This is a post-v1.14.0 addition, verified in
[main's schema at the reviewed commit](https://github.com/lfnovo/open-notebook/blob/3127f14ea9dbb519f0e4ddc64a0742ca644ba6ef/api/models.py).
Check the **deployed** schema before relying on scope; never silently retry globally.

Ask's three model values must be registered `model:...` IDs; using the same language
model for all three is allowed. Ask also requires an embedding model. Streaming
messages are `data: <JSON>` events with `type`: `strategy`, `answer`, `final_answer`,
`complete`, or `error`. Read `content` for answer events, `final_answer` on complete,
and `message` on error. An HTTP 200 stream can still end in an error event.

## Podcasts

| Method and path | Inputs and response |
| --- | --- |
| `GET /api/episode-profiles` | Array of profile records, including `name`; choose an existing profile. |
| `GET /api/speaker-profiles` | Array of profiles with `name` and `speakers`; one profile can contain multiple speakers. |
| `POST /api/podcasts/generate` | Body below; returns `job_id`, `status="submitted"`, `message`, `episode_profile`, `episode_name`. |
| `GET /api/podcasts/jobs/{job_id}` | `job_id`, `status`, nullable `result`, `error_message`, `created`, `updated`, `progress`. Completed result contains `episode_id`. |
| `GET /api/podcasts/episodes` | Array; no pagination/filter contract. |
| `GET /api/podcasts/episodes/{episode_id}` | Episode including `id`, `name`, profile snapshots, `briefing`, optional audio/transcript/outline, `job_status`, `error_message`. |
| `GET /api/podcasts/episodes/{episode_id}/audio` | Binary `audio/mpeg`; 404 if audio missing. |
| `POST /api/podcasts/episodes/{episode_id}/retry` | Only failed/error episodes; deletes failed episode/audio and submits a new job. Returns `{job_id, message}`; prior episode ID is not retained. |
| `DELETE /api/podcasts/episodes/{episode_id}` | Deletes episode and audio; returns `{message, episode_id}`. |

```json
{
  "episode_profile": "Existing episode profile name",
  "speaker_profile": "Existing speaker profile name",
  "episode_name": "Methods review",
  "content": "Reviewed research text to narrate"
}
```

`episode_profile`, `speaker_profile`, and `episode_name` are required. Profiles are
selected by **name**, not `episode_profile_id`/`speaker_profile_ids`. `content` or
`notebook_id` supplies material; `briefing_suffix` is optional. Prefer explicit
reviewed content: the notebook-only path has an upstream fallback to a string/ID if
context gathering fails. Poll with a deadline and handle failed/error/unknown
states; do not access a top-level `episode_id` on the job response.

## Transformations

| Method and path | Inputs and response |
| --- | --- |
| `GET /api/transformations` | Array, no pagination. |
| `POST /api/transformations` | Required `name`, `title`, `description`, `prompt`; optional `apply_default=false`, `model_id`; returns transformation. |
| `GET /api/transformations/{transformation_id}` | Transformation object. |
| `PUT /api/transformations/{transformation_id}` | Same fields, all optional; returns transformation. |
| `DELETE /api/transformations/{transformation_id}` | Returns `message`. |
| `POST /api/transformations/execute` | Required `transformation_id`, `input_text`; optional `model_id`; returns `output`, `transformation_id`, nullable `model_id`. |
| `GET /api/transformations/default-prompt` | Returns `{transformation_instructions}`. |
| `PUT /api/transformations/default-prompt` | Required JSON `transformation_instructions`; returns same shape. |

Transformation records add `id`, `created`, and `updated` to their input fields.
Executing raw text returns output; it does not automatically create a persisted
note or insight. Preserve provenance when saving generated text.

## Models

| Method and path | Inputs and response |
| --- | --- |
| `GET /api/models` | Optional query `type`: `language`, `embedding`, `speech_to_text`, `text_to_speech`; array. |
| `POST /api/models` | JSON required `name`, `provider`, `type`; optional credential record ID in `credential`. Returns model; duplicates fail. |
| `DELETE /api/models/{model_id}` | Returns `message`. |
| `POST /api/models/{model_id}/test` | No body; returns `success`, `message`, nullable `details`; can contact the provider. |
| `GET /api/models/defaults` | Default slot object below. |
| `PUT /api/models/defaults` | Partial object of slots; omitted fields unchanged, explicit null clears optional slots. Chat/embedding cannot be cleared. |
| `GET /api/models/providers` | `{available: [...], unavailable: [...], supported_types: {provider: [...]}}`. |
| `GET /api/models/discover/{provider}` | Array of `{name, provider, model_type, description}`; no registration. |
| `POST /api/models/sync/{provider}` | Discovers/registers models; returns `{provider, discovered, new, existing}` counts. |
| `POST /api/models/sync` | Returns `{results: {provider: counts}, total_discovered, total_new}`. |
| `POST /api/models/auto-assign` | Assigns only empty **chat and embedding** required slots; returns `{assigned, skipped, missing}`. |
| `GET /api/models/count/{provider}` | `{provider, counts: {type: count}, total}`. |
| `GET /api/models/by-provider/{provider}` | Array of registered model records. |

Model records have `id`, `name`, `provider`, `type`, nullable `credential`, `created`,
`updated`. Use registered IDs for chat/Ask/default assignments, provider model names
for model registration. Default slots are `default_chat_model`,
`default_transformation_model`, `large_context_model`, `default_text_to_speech_model`,
`default_speech_to_text_model`, `default_embedding_model`, `default_tools_model`.
There are no `podcast` or `summary` slots. Explicitly assign optional speech models;
auto-assign does not populate them. Verify provider data flow before assigning defaults.

## Credentials

| Method and path | Inputs and response |
| --- | --- |
| `GET /api/credentials/status` | `{configured: {provider: bool}, source: {provider: database/environment/none}, encryption_configured}`. |
| `GET /api/credentials/env-status` | Map of provider to environment-configuration boolean. |
| `GET /api/credentials` | Optional `provider`; array of safe credential records. |
| `GET /api/credentials/by-provider/{provider}` | Credential array for provider. |
| `POST /api/credentials` | Required JSON `name`, `provider`; provider-specific settings below. 201 credential record. |
| `GET /api/credentials/{credential_id}` | Safe credential record. |
| `PUT /api/credentials/{credential_id}` | Optional mutable settings; provider cannot be changed. Returns safe record. |
| `DELETE /api/credentials/{credential_id}` | Optional query `migrate_to` credential ID; otherwise **cascade-deletes linked models**. Returns `{message, deleted_models}`. |
| `POST /api/credentials/{credential_id}/test` | `{provider, success, message}`; check success, not just HTTP status. Some provider tests only validate key format. |
| `POST /api/credentials/{credential_id}/discover` | `{credential_id, provider, discovered: [{name, provider, model_type, description}]}`; model_type can be null. |
| `POST /api/credentials/{credential_id}/register-models` | JSON `{models: [{name, provider, model_type}]}`; returns `{created, existing}` counts. |

Settings include `modalities`, `api_key`, `base_url`; Azure has `endpoint`,
`api_version`; separate endpoints may use `endpoint_llm`, `endpoint_embedding`,
`endpoint_stt`, `endpoint_tts`; Vertex uses `project`, `location`, `credentials_path`;
Ollama supports `num_ctx`. Validate the chosen provider in the instance schema;
requirements differ by provider. Stored API keys are encrypted server-side and
never returned. Responses expose `has_api_key`, `model_count`, and nullable
`decryption_error` plus non-secret configuration and timestamps. Do not print
credential request bodies or copy keys into examples.

## Errors

Always check HTTP status before parsing a success shape. FastAPI validation uses
422 with a `detail` list of field errors; other handlers commonly return a `detail`
string. Not every failure has the same JSON structure. Expected categories include
400 invalid input, 401 missing/invalid instance password, 403 denied file access,
404 missing resource, 413 oversized upload, 422 schema/configuration failure,
429 provider rate limits, 500 backend/job submission errors, and 502 provider errors.
A queued source, HTTP 200 test response with `success=false`, and SSE `error` event
are unsuccessful operations despite their HTTP response being successful.
