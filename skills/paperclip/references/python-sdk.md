# GXL Paperclip Python SDK and HTTP contracts

Reviewed on 2026-09-30 against **gxl_paperclip 0.7.92** installed client/source, request-construction
smoke tests with fake HTTP responses, and the public
[OpenAPI 3.1 schema](https://paperclip.gxl.ai/api/v1/openapi.json). Public metadata/unauthenticated
probes were checked; authenticated retrieval, LLM execution, account permissions, uploads, and
repository mutations were not exercised. Remote examples below are illustrative.

## Install and connect

Install the official wheel in an environment you control; the managed CLI's private library is not
on an arbitrary Python interpreter's path. See [installation.md](installation.md).

```bash
uv pip install https://paperclip.gxl.ai/paperclip.whl
```

```python
import gxl_paperclip
from gxl_paperclip import PaperclipClient

print(gxl_paperclip.__version__)
client = PaperclipClient.from_env(no_color=True)
```

Ordinary `from_env()` precedence is `PAPERCLIP_BEARER_TOKEN`, `PAPERCLIP_API_KEY`, then stored OAuth.
It also accepts `base_url`, `timeout`, `user_agent`, `session`, and `no_color`. API keys use
`X-API-Key`; bearer auth uses `Authorization`. `FileCredentialsAuth` can refresh stored OAuth on
401 and retry once. Do not print credentials, authorization headers, or a complete private config.

Explicit auth is useful when a notebook must select exactly one configured identity:

```python
import os
from gxl_paperclip import APIKeyAuth, PaperclipClient

client = PaperclipClient(auth=APIKeyAuth(os.environ["PAPERCLIP_API_KEY"]), no_color=True)
```

The ordinary request timeout is 120 seconds. In this version map defaults to 1,500 seconds,
structured/exhaustive maps have separate longer defaults, and reduce/ask-image default to 300.
These can be environment-configured. Pass a **per-call** `timeout` to override a slow command;
setting the constructor timeout alone does not override every command-specific default.

## Structured search and lookup

```python
result = client.search("CRISPR delivery", source="pmc", limit=5)
if result.exit_code != 0 or result.output.lstrip().startswith("ERR:"):
    raise RuntimeError(result.output)
for paper in result.papers:
    doc_id = paper.get("document_id") or paper.get("id") or paper.get("paper_id")
    if not doc_id:
        raise ValueError("Search hit has no document identifier")
    print(doc_id, paper.get("title"), paper.get("doi"))
print(result.result_id)
```

`ExecuteResult` has `output`, `exit_code`, `elapsed_ms`, `result_id`, `result_data`, `raw`, `cwd`,
`download_url`, and `download_filename`. Newer `papers` and `count` properties expose structured
search/lookup hits. `papers` reads the `papers` or `results` array in `result_data`; `count` uses its
length when nonempty, otherwise a declared count. It is not an independent completeness check.
Search/lookup attempt saved-result hydration if data is absent/truncated; hydration failures can
leave a preview. Compare declared counts/truncation with retrieved rows before calling a cohort
complete. Do not parse ANSI-colored terminal titles to reconstruct IDs.

Supported `search` keyword arguments in 0.7.92:

```text
limit, source, exact, since, sort, author, journal, year, type, category,
mode, min_embedding_similarity, min_bm25_score, all, timeout
```

The wrapper serializes `mode` as `-m`; the CLI's documented spelling is `--ranking`.
The score floors also exist as CLI flags and affect only their respective retrieval legs.
Source/date/ranking caveats are in [search-and-retrieval.md](search-and-retrieval.md).

```python
identified = client.lookup("doi", "10.1073/pnas.2307796121", limit=1)
counts = client.sql("SELECT source, COUNT(*) AS n FROM documents GROUP BY source")
protein_count = client.sql("SELECT COUNT(*) FROM uniprot_v.proteins", source="proteins")
```

Load the current protein domain reference before constructing protein queries. SQL output remains
an `ExecuteResult`, not a guaranteed pandas table.

## Reading and arbitrary commands

```python
import json

path = "/papers/PMC10945750"
metadata_result = client.papers.cat(f"{path}/meta.json")
if metadata_result.exit_code != 0 or metadata_result.output.lstrip().startswith("ERR:"):
    raise RuntimeError(metadata_result.output)
meta = json.loads(metadata_result.output)
opening = client.papers.head(f"{path}/content.lines", lines=40)
ending = client.papers.tail(f"{path}/content.lines", lines=20)
sections = client.papers.ls(f"{path}/sections/")
hits = client.papers.grep("lipid nanoparticle", f"{path}/content.lines", ignore_case=True)
scanned = client.papers.scan(f"{path}/content.lines", ["IC50", "EC50", "dose"])
```

These typed methods preserve argument boundaries and support per-call `timeout`. `papers.grep`
also accepts `extended=True`. Do not assume every metadata source has `journal` or `pub_year`; inspect
keys and use optional access for nullable source-specific fields. `L<n>` prefixes in text are the
source for line citations.

```python
client.execute("grep", ["-n", "-C", "3", "IC50", "/papers/PMC10945750/content.lines"])
```

Use `execute(command, args)` for commands without a wrapper. `bash(script)` exists for server-side
pipelines, but old versions failed on this path and current authenticated behavior was not tested.
Prefer argument lists and local Python composition. `ask_image(path, question=None, fn=None)` returns
an `ExecuteResult`; list the figure directory first. `pull(target, dest=None)` returns textual
metadata and any server-provided download URL; **the SDK does not stream image bytes to `dest`**.
Never interpret `exit_code == 0` as proof that a local image was written.

## Map events and schemas

```python
from gxl_paperclip import MapProgressEvent, MapResultEvent

schema = {
    "type": "object",
    "required": ["effect"],
    "additionalProperties": False,
    "properties": {"effect": {"type": ["number", "null"]}},
}
for event in client.map_(
    "Extract the reported effect; use null when absent.",
    from_results="s_ID", output_schema=schema, timeout=1500.0,
):
    if isinstance(event, MapProgressEvent):
        print(event.completed, event.failed, event.total)
    elif isinstance(event, MapResultEvent):
        if event.exit_code:
            raise RuntimeError(event.output)
        print(event.result_id, event.output)
```

Use `isinstance`; these dataclasses do not provide the `event.type` used in an old website example.
`map_` returns an iterator. On the unified `paperclip.gxl.ai` host, API-key and OAuth maps use the
streaming REST route; a direct `mcp.*` host with API-key auth emits only a final result event.
The typed wrapper accepts `from_results`, `output_schema`, and `timeout`, not worker/repo parameters;
use `stream("map", argv)` for specialized options after inspecting the relevant workflow.

```python
summary = client.reduce("Compare the effects", from_map="m_ID", strategy="table", columns=["paper", "effect"])
```

A schema validates JSON shape; source evidence still needs scientific checks. See
[map-reduce.md](map-reduce.md).

## Results and pagination

```python
recent = client.results.list(limit=10)
saved = client.results.get("s_ID")
page = client.results.page("s_ID", cursor=0, limit=500)
sample = client.results.sample("s_ID", count=10, seed=42)
```

`list()` returns `ResultRow` objects (recent results, not hit pages); `get()` returns `ResultData`
with `output` and `raw`. `page()` returns a dict with `papers`, total `count`, and `next_cursor`.
The initial cursor is integer **0**, page size is **1–500**, and `next_cursor is None` terminates.
These contracts are taken from the SDK and bundled cohort exporter, not an authenticated page.
A 404 can mean missing results or a server lacking cohort-page support.

Bound traversal and reject a nonadvancing cursor or an inconsistent count:

```python
def saved_papers(client, result_id, max_pages=20):
    cursor = 0
    rows = []
    expected = None
    for _ in range(max_pages):
        page = client.results.page(result_id, cursor=cursor, limit=500)
        batch = page.get("papers")
        count = page.get("count")
        if not isinstance(batch, list) or isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Invalid saved-cohort page")
        if expected is None:
            expected = count
        if count != expected:
            raise ValueError("Cohort changed during pagination")
        rows.extend(batch)
        next_cursor = page.get("next_cursor")
        if next_cursor is None:
            if len(rows) != expected:
                raise ValueError("Incomplete saved cohort")
            return rows
        if isinstance(next_cursor, bool) or not isinstance(next_cursor, int) or next_cursor <= cursor:
            raise ValueError("Invalid cohort cursor")
        cursor = next_cursor
    raise ValueError("Saved cohort exceeded the page budget")
```

This retrieves a saved cohort; it does not extend the original search into unsaved hits.
`results.sample` accepts 1–100 papers and an integer seed. The CLI portable bundle exporter uses
these pages, verifies count/cursor advancement, and caps exports at 10,000 rows in 0.7.92.

## SDK transport and workspace contracts

The SDK is not a wrapper around the newer `/api/v1/search` API. Inspected 0.7.92 routing:

| Operation | Method/path and request | Response contract |
|---|---|---|
| Ordinary command with OAuth | `POST /api/cli/execute`, JSON `command`, shell-quoted `raw` | Execute response; 404 can fall back to MCP |
| Ordinary command with API key, unified host | `POST /mcp`, JSON-RPC `tools/call`, legacy tool `paperclip`, `arguments.command` | Text blocks; result ID extracted and search/lookup hydrated |
| Direct `mcp.*` hostname | MCP uses `/papers` | Compatibility path, not the public `/api/v1` contract |
| Map on unified host | `POST /api/cli/execute?stream=1`, JSON `command=map`, `raw` | Progress/result NDJSON, or one normalized JSON result |
| Recent/saved results | `GET /api/cli/results?limit=N`; `GET /api/cli/results/{id}` | Array of rows; saved-result object |
| Saved cohort page | `GET /api/cli/results/{id}/page?cursor=0&limit=500` | `papers`, `count`, `next_cursor` |
| Artifact upload | `POST /api/user/upload` multipart `file`, form `folder_path` | Server response dict; do not assume a fixed success field |

The legacy MCP text parser can report `exit_code=0` even when returned text contains a virtual-shell
error; this is still visible in the 0.7.92 implementation. HTTP status, typed exceptions, command
status, and expected result content all matter. The SDK `health()` dispatches authenticated `status`;
it is not the public `/health` probe used by CLI config.

Repo/library methods return mostly raw dicts and accept internal repo/entry IDs rather than CLI
names. Examples are **mutations** and require the corresponding user task:

```python
repo = client.repos.create_repo("my-review", "Delivery vectors")
client.repos.add_papers(repo["id"], [{"paper_id": "PMC10945750"}])
```

The item key is `paper_id`, not the old example's `document_id`. Resolve an existing repo with
`get_repo_by_name()` and handle `None` before use. The route mapping for the formerly documented
SDK operations is:

| SDK operation | Route/body or query |
|---|---|
| `repos.get_repo_by_name(name)` | `GET /api/paper-repos/by-name/{name}`; 404 becomes `None` |
| `repos.create_repo(name, description)` | `POST /api/paper-repos/`, JSON name/description |
| `repos.add_papers(repo_id, items, branch=None)` | `POST /api/paper-repos/{id}/papers`, JSON items/branch |
| `repos.annotate_paper(repo_id, entry_id, note, lines=...)` | `PATCH .../{id}/papers/{entry_id}`, `append_annotation: {note, lines}` |
| `repos.commit(repo_id, message)` | `POST .../{id}/commits`, JSON message/branch |
| `repos.get_status(repo_id)` | `GET .../{id}/status`, optional branch query |
| `repos.create_branch(repo_id, name)` | `POST .../{id}/branches`, JSON name/from_branch |
| `repos.merge_branches(repo_id, source, target)` | `POST .../{id}/merge`, JSON source/target |
| `repos.export(repo_id, format)` | `GET .../{id}/export`, format/branch query; returns bytes |
| `library.list_papers(page=1, per_page=50, search=...)` | `GET /api/library/`, one-based page/per_page plus sort_by/sort_dir; raw dict |
| `library.upload_pdfs([(name, bytes)])` | `POST /api/library/import/pdf`, multipart repeated `files`; job_id/status dict |
| `library.poll_import_job(job_id, timeout_s=900)` | Repeated `GET /api/library/import/jobs/{id}`; returns completed `result`, raises on failure/timeout |
| `library.delete_paper(id)` | `DELETE /api/library/{id}`; returns `None`, tolerates 404 |

SDK `repos.commit()` only sends the commit request; it does not run the CLI's client-side verifier
or its scientific gates. Do not substitute it for `paperclip repo commit` and claim equivalent
verification. Permissions are not established merely because a method exists:
`client.list_paper_repos()` explicitly rejects API-key auth, while `client.repos.list_repos()`
dispatches directly. This inconsistency was not resolved with live account tests. Library and repo
history paging are separate one-based APIs; do not reuse the cohort's zero-based cursor.

## Public JSON API

For stable search/metadata JSON without the CLI transport, the current public contract is based at
`https://paperclip.gxl.ai/api/v1` and accepts `X-API-Key` or an API key as `Authorization: Bearer ...`.
The OpenAPI security declaration lists HTTPBearer; both key forms are described in its info and
the official HTTP guide. These endpoints are distinct from SDK command transport.

| Endpoint | Request and response |
|---|---|
| `POST /search` | JSON `query`, explicit `sources`, `num_results` 1–200 (default 50), `ranking` hybrid/bm25/vector, optional `filters`; response has `papers`, `results`, `usage`, and optional `search_id` |
| `POST /lookup` | One identifier/metadata key (e.g. `pmid`) or `field` plus `value`; `num_results` 1–100 (default 25); response has query/papers/results/usage |
| `GET /documents/{doc_id}` | Document metadata (id/object/title/url plus optional identifiers, abstract, metadata); not a full-text download |

`/search` defaults to `abstracts`, not PMC. The schema describes that default index as residual
PubMed/Crossref title/abstract content; do not assume the CLI's broader `-s abstracts` wording.
`analogical` is not a v1 ranking enum even though the CLI supports it. Neither search nor lookup
exposes a page, cursor, or offset in this schema: increasing `num_results` is bounded retrieval,
not arbitrary pagination. Year bounds are inclusive; records with unknown year are retained by the
published filter contract. `published_after/before` are **year-granular aliases**, not day precision.

Illustrative request, schema-checked locally but not submitted with credentials:

```python
import os
import requests

response = requests.post(
    "https://paperclip.gxl.ai/api/v1/search",
    headers={"X-API-Key": os.environ["PAPERCLIP_API_KEY"]},
    json={"query": "CRISPR delivery", "sources": ["pmc"], "num_results": 5, "ranking": "hybrid"},
    timeout=120,
)
response.raise_for_status()
papers = response.json()["papers"]
```

Public schema and health reads returned 200 during review; unauthenticated document/results reads
returned 401. That verifies authentication boundaries, not successful retrieval or billing behavior.

## Errors

Catch `PaperclipError` and its subclasses: `AuthError` (401), `ForbiddenError` (403),
`RateLimitError` (429), `NotFoundError`, `ServerError`, `RequestTimeoutError`, and `NetworkError`.
Do not retry bad credentials or forbidden operations automatically. Bound retries for transient
failures; do not restart a mutation whose outcome is unknown without reconciling server state.
Inspect typed command status and returned content as well as exceptions. Never log request headers
or credential-bearing diagnostics when reporting an error.
