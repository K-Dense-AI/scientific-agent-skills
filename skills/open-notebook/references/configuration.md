# Open Notebook Configuration Guide

Reviewed against [v1.14.0 Compose](https://github.com/lfnovo/open-notebook/blob/v1.14.0/docker-compose.yml),
[current environment reference](https://github.com/lfnovo/open-notebook/blob/3127f14ea9dbb519f0e4ddc64a0742ca644ba6ef/docs/5-CONFIGURATION/environment-reference.md),
and [source installation](https://github.com/lfnovo/open-notebook/blob/v1.14.0/docs/1-INSTALLATION/from-source.md)
on 2026-09-30. Commands below are illustrative deployment examples; no containers
or authenticated provider calls were launched for this review.

## Docker deployment and persistence

Use the upstream `docker-compose.yml`, which has services **`surrealdb`** and
**`open_notebook`**, rather than substituting an unverified image location. The
reviewed application image is `lfnovo/open_notebook:v1-latest`, and the database
image is `surrealdb/surrealdb:v2`. Record resolved image digests for reproducibility;
these tags can change. Do not replace the database with an arbitrary `latest` major.

```bash
curl --fail --location --output docker-compose.yml \
  https://raw.githubusercontent.com/lfnovo/open-notebook/v1.14.0/docker-compose.yml
```

The downloaded file contains a **literal** encryption-key placeholder. Replace it
in the file, or change that environment entry to
`OPEN_NOTEBOOK_ENCRYPTION_KEY=${OPEN_NOTEBOOK_ENCRYPTION_KEY:?Set a key}` and supply
the variable through your deployment's secret mechanism. A shell export alone
cannot override a literal Compose environment entry. Add the password to the
application environment if authentication is needed; it is not in the default
Compose application environment automatically.

```bash
docker compose up -d
docker compose logs --tail=100 open_notebook
docker compose stop
```

Application UI/API ports are 8502/5055. For a local-only installation bind them to
`127.0.0.1`; use HTTPS and authenticated access when operating remotely. The upstream
SurrealDB debug port binds to loopback, while the application reaches it on the
Compose network. Use matching database credentials for both services.

Persistent mounts in this file are:

| Host directory | Container path | Content |
| --- | --- | --- |
| `./surreal_data` | `/mydata` | SurrealDB data using RocksDB |
| `./notebook_data` | `/app/data` | Uploads, podcasts, SQLite chat checkpoints, runtime caches |

The source uses `./data/uploads`, not an `UPLOAD_DIR=/app/uploads` configuration.
Preserving only uploads loses podcast files and chat checkpoints.

## Environment variables

| Variable | Scope and meaning |
| --- | --- |
| `OPEN_NOTEBOOK_ENCRYPTION_KEY` | Server secret for stored provider credentials. Keep unchanged and back it up separately; it does not encrypt source documents. `_FILE` supports Docker secrets. |
| `OPEN_NOTEBOOK_PASSWORD` | Optional server instance password. API uses `Authorization: Bearer <password>`. Authentication is disabled if unset. `_FILE` is supported server-side. |
| `SURREAL_URL` | Compose connection `ws://surrealdb:8000/rpc`. |
| `SURREAL_USER`, `SURREAL_PASSWORD` | Must match database service; local upstream defaults are root/root. `SURREAL_PASS` is not the variable. |
| `SURREAL_NAMESPACE`, `SURREAL_DATABASE` | Upstream Compose values `open_notebook`. |
| `API_URL` | Browser-visible backend location when configured. Do not use a container-only hostname here for remote browsers. |
| `INTERNAL_API_URL` | Backend used by Next.js server-side proxying; default localhost:5055 in the combined container. |
| `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` | Server body limit, default 100; a reverse proxy may impose a smaller limit. |
| `OPEN_NOTEBOOK_WORKER_MAX_TASKS` | Worker concurrency, default 5; set in worker process/container environment. |
| `OPEN_NOTEBOOK_ENABLE_DOCLING` | Optional heavy document/OCR runtime; default false, first start downloads dependencies. |
| `OPEN_NOTEBOOK_ENABLE_CRAWL4AI` | Optional local crawling runtime; default false. |

The bundled Python **client helpers** additionally read `OPEN_NOTEBOOK_URL`
(default backend `http://localhost:5055`) and `OPEN_NOTEBOOK_PASSWORD`. They do not
need database credentials or the encryption key. `OPEN_NOTEBOOK_URL` is a helper
setting, not a replacement for the server's `API_URL`.

Provider key environment variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GOOGLE_API_KEY`, and `GROQ_API_KEY` remain legacy fallbacks. Upstream now deprecates
that mechanism; configure stored credentials through **Manage → Models** or the
credential API for new automation.

## AI provider setup

Use the UI to add a configuration, test it, discover models, and select models for
registration. A provider supporting language models does not necessarily support
embeddings, transcription, or speech. Inspect `/api/models/providers` and the
chosen model's capabilities. Model/credential tests may invoke paid provider APIs.

The following Python example is illustrative. Run from the skill's `scripts/`
directory. It reads an existing provider secret from the environment only to submit
it to the user's own Open Notebook credential store; it does not print the secret.
Choose a **language-model name returned by discovery** before calling the function.
Do not automatically register every discovered name as a language model.

```python
import os
from _common import record_path, request_json


def register_openai_language_model(selected_name):
    credential = request_json("POST", "/credentials", json={
        "name": "Research provider", "provider": "openai",
        "api_key": os.environ["OPENAI_API_KEY"],
        "modalities": ["language"],
    })
    credential_path = "/credentials/" + record_path(credential["id"])
    check = request_json("POST", credential_path + "/test")
    if not check["success"]:
        raise RuntimeError(check["message"])
    discovery = request_json("POST", credential_path + "/discover")
    selected = next(
        model for model in discovery["discovered"] if model["name"] == selected_name
    )
    registered = request_json("POST", credential_path + "/register-models", json={
        "models": [{"name": selected["name"], "provider": selected["provider"],
                    "model_type": "language"}],
    })
    return credential["id"], registered
```

Discovery returns `discovered`, not `models`; those objects have names, not model
record IDs. Registration returns counts, not IDs. Retrieve registered records with
`GET /api/models?type=language` and choose the matching name, provider, and credential.
Register a suitable embedding model separately. Explicitly assign defaults using
`PUT /api/models/defaults`, for example `default_chat_model` and
`default_embedding_model` with their registered IDs. `/api/models/auto-assign` fills
only these two required slots and can select a cloud provider; review that selection.
Speech and other optional slots need explicit assignment when desired.

Deleting a credential without `migrate_to` also deletes its linked models; a failed
connection test is not a reason to delete an existing credential automatically.

## Ollama and local processing

Use upstream's [Ollama Compose example](https://github.com/lfnovo/open-notebook/blob/v1.14.0/examples/docker-compose-ollama.yml)
for a matching network and volume definition. A provider URL such as
`http://ollama:11434` works only when that service name exists on the application's
network. A model server on the Docker host needs the appropriate host route rather
than `localhost` inside the application container. Register both a language and
an embedding model actually installed in the local server.

Local inference avoids provider API charges, but still consumes local compute.
Check all stages: content extraction, transcription, embeddings, chat, and speech
can use separate remote providers. Confirm these settings before restricted data
is ingested or a podcast is generated.

## Running from source

Docker is a convenient deployment, not a mandatory application runtime. Follow
upstream's source installation and its lockfile for interpreter/dependency versions.
Its documented setup uses `uv sync`, a SurrealDB service, a Next.js frontend, and
separate API/worker processes. In the upstream checkout, after configuring `.env`:

```bash
make api
```

In a separate terminal:

```bash
make worker
```

A working `/health` endpoint does not prove the worker is running. Without it,
background ingestion/embedding/podcast jobs remain pending. The source frontend's
development port is 3000, unlike Docker's 8502. No separate Python client SDK is
required by this skill; the bundled requests wrappers call the REST API directly.

## Backup and restore

Keep a consistent copy of **both** persistent directories and retain the encryption
key separately. For a local deployment using the upstream bind mounts, a cold
filesystem backup is an illustrative option: stop both services, archive the data,
then restart. Use a fresh backup path; do not overwrite the only prior backup.

```bash
docker compose stop
tar -czf open-notebook-backup-YYYYMMDD.tar.gz notebook_data surreal_data
docker compose start
```

To restore, stop the services, preserve the current directories, restore the archive
into the same Compose directory, and use the same encryption key and compatible
image/database versions before starting. Test restoration on a separate deployment.
A database-only export is insufficient for files and SQLite conversation state.
