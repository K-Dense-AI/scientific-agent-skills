# Open Notebook Architecture

Reviewed 2026-09-30 using
[application wiring](https://github.com/lfnovo/open-notebook/blob/v1.14.0/api/main.py),
[storage paths](https://github.com/lfnovo/open-notebook/blob/v1.14.0/open_notebook/config.py),
and [source installation](https://github.com/lfnovo/open-notebook/blob/v1.14.0/docs/1-INSTALLATION/from-source.md).
These are source-level findings, not live deployment verification.

## Runtime components

- **Next.js/React frontend:** Docker exposes port 8502; source development uses 3000.
- **FastAPI backend:** default port 5055, business routes below `/api`, live schemas
  at `/openapi.json`. Pydantic models validate known fields, but extra request fields
  may be silently ignored. Use the deployed schema when relying on a filter.
- **SurrealDB v2:** notebook/source/note/model/credential records, graph relations,
  full-text/vector retrieval, background command records, and schema migrations.
  The upstream Compose file persists its RocksDB data under `/mydata`.
- **Background worker:** `surreal-commands-worker` processes extraction, embeddings,
  and podcast work. It is a separate process even when bundled in the app container.
  API health alone cannot demonstrate processing readiness.
- **LangChain/LangGraph:** AI chains and conversation state. Chat checkpoint state
  also uses SQLite under the application data directory, not just SurrealDB.
- **Esperanto and processing libraries:** connect to independently configured
  language, embedding, transcription, speech, and extraction providers.

## Ingestion and evidence

1. A request specifies link/upload/text content and notebook associations.
2. The backend validates content type and path/URL policy, creates a source, and
   either runs processing synchronously or submits a background command.
3. Extraction produces text; optional transformations produce insights; requested
   embeddings enable vector retrieval.
4. Poll status and retrieve the source to inspect text, errors, and embedding
   coverage. A successful queue submission does not show completion.

PDF extraction, OCR, tables, and transcripts can lose important scientific detail.
Compare extracted measurements, units, and section boundaries with the original
before using an AI summary as evidence. Preserve source IDs and selected context
with analysis outputs; generated notes are derivative material, not independent data.

## Chat versus Ask

Notebook chat first builds a context object from explicit source/note selections,
then submits that object with a message to `/api/chat/execute`. The endpoint returns
JSON message history. An empty context configuration has special meaning: it
includes all notebook items in short form. Explicit ID selections and verification
of returned content prevent accidental reliance on missing/full-text-free context.
The context builder can skip individual unavailable records without failing.

Ask searches the knowledge base with an embedding model and uses strategy, answer,
and final-answer language models. It can return JSON or an SSE stream depending on
the route. The release v1.14.0 Search/Ask API is global. Current main adds notebook
scoping; a field silently ignored by an older server cannot enforce that boundary.

## Podcasts and persistence

Podcast jobs combine an episode profile, one multi-speaker profile, supplied
content, language models for scripts, and speech models for audio. They create an
episode and audio under `/app/data/podcasts` in the container. A retry of a failed
episode deletes its record/audio and starts a new job. Inspect the returned job
result for the new episode ID.

Back up SurrealDB **and** `/app/data`, which contains uploads, podcasts, SQLite
checkpoints, and caches. Stored provider keys use the server's
`OPEN_NOTEBOOK_ENCRYPTION_KEY`; changing or losing it can make credentials unreadable.
This is not encryption of every stored document.

## Data boundaries

Self-hosted storage and local AI inference are separate choices. Cloud models,
embedding providers, transcription, speech, or external extraction services can
receive research content. Source ingestion can also fetch public URLs from the
server. Use only intended source URLs and inspect the selected provider for each
stage. The password middleware is instance-wide bearer-password protection; it
does not create per-notebook user permissions.

## Source navigation

| Upstream location | Responsibility |
| --- | --- |
| `api/main.py`, `api/auth.py` | Router mounting, middleware, password checks |
| `api/models.py`, `api/routers/` | Request/response schemas and endpoints |
| `api/podcast_service.py` | Podcast submission and job-result contract |
| `open_notebook/domain/` | Notebook/source/note records and relationships |
| `open_notebook/graphs/` | Chat, Ask, transformation and processing flows |
| `open_notebook/utils/context_builder.py` | Source/note context selection |
| `commands/` | Background jobs |
| `frontend/` | Next.js client |
| `docker-compose.yml` | Services and persistent mounts |
