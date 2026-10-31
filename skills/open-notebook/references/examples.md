# Open Notebook Examples

These examples target the official **v1.14.0** contracts documented in
[the API reference](api_reference.md). Run from this skill's `scripts/` directory
with `requests` installed and `OPEN_NOTEBOOK_URL` pointing to the backend.
The shared client adds `OPEN_NOTEBOOK_PASSWORD` as a Bearer token when set,
checks HTTP errors, and uses finite timeouts. Examples are illustrative for a live
instance; mocked tests verify request bodies, pagination, status handling, and
response parsing without performing real ingestion or model calls.

## Research workflow with explicit context

The caller supplies an accessible source URL. Respect access rights; an abstract
page or a paywall response is not the full paper. Set `embed=True` only when a
configured embedding model should process the text. This example uses full text
for chat and keyword search, so it does not request embeddings.

```python
from _common import record_path, request_json
from notebook_management import create_notebook
from source_ingestion import add_url_source, wait_for_processing
from chat_interaction import build_context, create_chat_session, send_chat_message


def research_workflow(source_url):
    notebook = create_notebook("Study design review", "Inspect primary methods evidence")
    source = add_url_source(notebook["id"], source_url, embed=False)
    wait_for_processing(source["id"])
    extracted = request_json("GET", "/sources/" + record_path(source["id"]))
    if not (extracted.get("full_text") or "").strip():
        raise RuntimeError("Extraction produced no research text")
    built = build_context(notebook["id"], source_ids=[source["id"]], note_ids=[])
    selected = built["context"]["sources"]
    if not selected or not any(item.get("full_text") for item in selected):
        raise RuntimeError("Full source text was not included in chat context")
    session = create_chat_session(notebook["id"], "Methods review")
    answer = send_chat_message(
        session["id"], "Extract the study design and sample size; cite the source. "
        "State what is missing and distinguish reported facts from inference.",
        built["context"],
    )
    ai_messages = [m for m in answer["messages"] if m["type"] == "ai"]
    if not ai_messages:
        raise RuntimeError("Chat returned no AI message")
    note = request_json("POST", "/notes", json={
        "notebook_id": notebook["id"], "title": "Methods extraction - unverified draft",
        "note_type": "ai", "content": ai_messages[-1]["content"],
    })
    return {"notebook": notebook, "source": extracted, "note": note,
            "context_tokens": built["token_count"]}
```

Review source extraction and citations before interpreting the note as evidence.
For sensitive projects, inspect the assembled context before invoking chat. Keep
records after the workflow for provenance; cleanup is an explicit later action.

## Uploads and complete source listing

```python
from source_ingestion import upload_file_source, wait_for_processing, iter_sources


def upload_papers(notebook_id, file_paths):
    uploaded = []
    for path in file_paths:
        source = upload_file_source(notebook_id, path, process_async=True, embed=False)
        wait_for_processing(source["id"])
        uploaded.append(source["id"])
    return uploaded


def all_notebook_sources(notebook_id):
    return list(iter_sources(notebook_id, page_size=100))
```

The upload helper sends `type=upload` and multipart bytes; it never assumes that
a client file path exists on the server. Long audio/video or OCR may require a
longer polling deadline and optional extraction dependencies. A completed source
can still lack embeddings; inspect `embedded_chunks` before vector retrieval.

## Search and Ask

```python
from _common import request_json
from chat_interaction import search_knowledge_base, ask_question


def search_and_answer(query):
    results = search_knowledge_base(query, search_type="vector", limit=10)
    defaults = request_json("GET", "/models/defaults")
    model_id = defaults.get("default_chat_model")
    if not model_id or not defaults.get("default_embedding_model"):
        raise RuntimeError("Configure chat and embedding models first")
    answer = ask_question(query, model_id, model_id, model_id)
    return results["total_count"], results["results"], answer["answer"]
```

This searches **all** eligible materials on v1.14.0. The Ask call performs its own
retrieval; it does not synthesize only the ten preceding search results. Do not
pass `source_ids` and claim source-restricted retrieval. Main after the release
adds notebook scoping, but it must be verified in the installed OpenAPI schema.
Select explicit source context for a bounded notebook chat on v1.14.0 instead.

## Custom transformation

```python
from _common import request_json


def extract_methods(text, model_id):
    transformation = request_json("POST", "/transformations", json={
        "name": "review_methods", "title": "Review Methods",
        "description": "Extract reported methods with provenance and omissions",
        "prompt": "Extract study design, sample size, variables and statistical "
                  "methods. Quote short supporting passages. Mark missing details; "
                  "do not invent values or infer a design from the conclusions.",
        "apply_default": False,
    })
    result = request_json("POST", "/transformations/execute", json={
        "transformation_id": transformation["id"], "input_text": text,
        "model_id": model_id,
    })
    return result["output"]
```

Select `model_id` from `GET /api/models?type=language`, matching a suitable registered
model. Execution returns text without automatically persisting a note. Record the
source/model/transformation IDs with any saved analysis and verify quantitative
claims against original tables, figures, and units.

## Podcast generation from reviewed text

Choose names from `GET /api/episode-profiles` and `GET /api/speaker-profiles`.
One speaker profile contains the cast; the API does not accept a speaker ID list.
The profile's language and speech models must already be configured. This operation
can incur provider charges.

```python
from pathlib import Path
import time
from _common import record_path, request, request_json


def generate_podcast(content, episode_profile, speaker_profile, output_path,
                     timeout=1800):
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    job = request_json("POST", "/podcasts/generate", json={
        "episode_profile": episode_profile, "speaker_profile": speaker_profile,
        "episode_name": "Reviewed methods discussion", "content": content,
    })
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Podcast job {job['job_id']} still pending")
        status = request_json("GET", "/podcasts/jobs/" + record_path(job["job_id"]),
                              timeout=min(30, remaining))
        if status["status"] in {"failed", "error", "canceled", "cancelled"}:
            raise RuntimeError(status.get("error_message") or "Podcast generation failed")
        if status["status"] == "completed":
            episode_id = (status.get("result") or {}).get("episode_id")
            if not episode_id:
                raise RuntimeError("Completed job returned no episode_id")
            break
        time.sleep(min(5, max(0, deadline - time.monotonic())))
    audio_path = "/podcasts/episodes/" + record_path(episode_id) + "/audio"
    with request("GET", audio_path, stream=True) as response:
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
        if content_type != "audio/mpeg":
            raise RuntimeError(f"Unexpected podcast content type: {content_type}")
        with Path(output_path).open("xb") as handle:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    handle.write(chunk)
    return episode_id
```

Use a new output filename. A download interrupted after writing begins leaves a
partial file; inspect it before reuse. Fetch the episode and review its transcript
and scientific claims before distributing the audio. A timed-out generation request
may still run on the server—inspect jobs/episodes rather than submitting duplicates.
