---
name: tamarind
description: Access a collection of open-source molecular design and structural biology tools on the Tamarind Bio platform, via its REST API or MCP server — no local GPUs required. Tamarind bundles popular open-source models for structure prediction (AlphaFold, Boltz, Chai, ESMFold), protein, binder, and de novo design (RFdiffusion, ProteinMPNN, BoltzGen), antibody and nanobody design and developability, protein-ligand docking (DiffDock, Autodock Vina), binding-affinity prediction, MSA generation, and molecular dynamics. Use when the user mentions Tamarind or tamarind.bio, wants to run any of these open-source tools in the cloud, references app.tamarind.bio/api or the x-api-key header, or needs to submit batches of sequences for structural or biophysical characterization.
license: MIT
compatibility: Requires Python 3.10+, a Tamarind Bio account, and an API key from app.tamarind.bio. Uses the `requests` library against the public REST API (these recipes use HTTP directly). Network access required. Optional MCP server at mcp.tamarind.bio/mcp for agent hosts.
metadata:
  version: "1.2"
  skill-author: Tamarind Bio
  trigger-keywords: protein structure prediction, AlphaFold, Boltz, Chai, ESMFold, protein design, binder design, de novo design, antibody design, nanobody, protein-ligand docking, DiffDock, Autodock Vina, binding affinity, MSA generation, inverse folding, ProteinMPNN, RFdiffusion, BoltzGen, cloud GPU biology, structure prediction API, x-api-key, developability, adme, enzyme, peptide, protein language models, molecular design
  openclaw:
    primaryEnv: TAMARIND_API_KEY
    envVars:
    - name: TAMARIND_API_KEY
      required: true
      description: Tamarind Bio API key sent as the x-api-key header.
---

# Tamarind Bio

Tamarind Bio is a cloud platform that runs computational biology tools — structure prediction, protein and antibody design, docking, binding-affinity, MSA generation, and molecular dynamics — on managed GPUs. Users submit sequences or structures and get back predicted structures, designs, and biophysical scores, without provisioning their own hardware. It exposes hundreds of tools (AlphaFold, Boltz-2, Chai-1, RFdiffusion, ProteinMPNN, BoltzGen, ESMFold2, DiffDock, Autodock Vina, and many more) through one uniform job API.

**Official docs:** [app.tamarind.bio/api-docs](https://app.tamarind.bio/api-docs) · platform UI at [app.tamarind.bio](https://app.tamarind.bio)

## Canonical sources — fetch these, don't rely on a stale copy

Tamarind publishes live, machine-readable sources. Prefer fetching them at runtime over trusting any hardcoded list — tool names, schemas, and endpoints change frequently:

- **`https://app.tamarind.bio/llms.txt`** — LLM index: links to the spec, API docs, and MCP guide.
- **`https://app.tamarind.bio/openapi.yaml`** — OpenAPI 3.0 spec for the 8 core job endpoints (submit-job/-batch, jobs, result, upload, files, delete-job/-file; auth `ApiKeyAuth`). Fetch it for those exact shapes. Discovery/management endpoints (`/tools`, `/usage-statistics`, pipelines, …) aren't in it — use the MCP/REST discovery tools for those.
- **`https://docs.tamarind.bio/llms.txt`** — documentation index; every page has a `.md` form (e.g. `docs.tamarind.bio/tamarind/batch.md`, `/tamarind/api.md`, `/tamarind/pipelines.md`).
- **Live tool discovery** — `GET /tools` (REST) or MCP `getAvailableTools` + `getJobSchema(jobType)` are the source of truth for what tools exist and their parameters.

This skill teaches the surface + the non-obvious behaviors those sources don't spell out (see the reference files). When in doubt about a shape, fetch `openapi.yaml`.

## When to use this skill

Use Tamarind when the user wants to:

- **Predict structure** of a protein, complex, or protein-ligand system (AlphaFold, Boltz-2, Chai-1, ESMFold2, Chai/Boltz cofolding)
- **Design proteins or binders** (RFdiffusion, BoltzGen, BindCraft, ProteinMPNN/LigandMPNN inverse folding)
- **Design or characterize antibodies/nanobodies** (sequence generation, humanization, developability, immunogenicity)
- **Dock small molecules** to a protein (DiffDock, Autodock Vina) or predict **binding affinity**
- **Generate MSAs** for downstream folding
- **Run molecular dynamics** or other biophysical workflows on managed GPUs
- **Batch-screen** many sequences or designs through the same tool
- **Chain tools** into pipelines (e.g. design → fold → score) using the output of one job as the input of the next

This skill is the right fit when the work should run on Tamarind's managed cloud rather than on a local install. For purely local cheminformatics or one-off sequence I/O, use a local library (RDKit, BioPython) instead.

## Access and authentication

1. Sign in at [app.tamarind.bio](https://app.tamarind.bio) and create an API key from the account/API settings.
2. Authenticate every REST request with the `x-api-key` header.
3. **Never hardcode the key.** Read it from the `TAMARIND_API_KEY` environment variable or a `.env` file (use `python-dotenv`). Never commit keys to source control.

**Pricing:** Every user gets **10 free jobs**. For larger usage, contact [info@tamarind.bio](mailto:info@tamarind.bio) to purchase a subscription.

```bash
export TAMARIND_API_KEY="your_api_key"
# List available tools
curl https://app.tamarind.bio/api/tools \
  -H "x-api-key: $TAMARIND_API_KEY"
```

**Base URL:** `https://app.tamarind.bio/api/`

These recipes use plain `requests` against the REST API, or the MCP server for agent hosts. Tamarind now documents an official Python client in the **`tamarind-cli`** distribution for Custom Tools (imported as `tamarind`); follow its [SDK reference](https://app.tamarind.bio/api-docs/custom-tools-sdk-reference) when using that surface. Do not substitute the unrelated PyPI distribution named `tamarind`.

## Two ways to call Tamarind

### MCP server (best for AI agents)

Tamarind hosts an MCP server at `https://mcp.tamarind.bio/mcp` (API-key auth via the `X-API-Key` header). When your agent host supports MCP, prefer it — the tools mirror the REST API with agent-friendly schemas:

- `listModalities()` / `listTags()` — the live filter vocabulary (molecule type / function) with labels + tool counts; call these to learn valid `modality`/`function` values instead of hardcoding
- `getAvailableTools(modality?, function?, search?, custom?)` — discover tools (`category`/`tag` are deprecated aliases still honored)
- `getJobSchema(jobType)` — exact parameter schema for a tool, plus an `exampleJob` starting payload (validate it before submitting)
- `validateJob(jobName, type, settings)` — dry-run validation before submitting
- `submitJob(jobName, type, settings)` / `submitBatch(batchName, type, settings[], jobNames[])`
- `getJobs(jobName?, batch?, limit?, includeSequences?)` — list/inspect jobs and statuses (the bulky per-job input blob is omitted by default; pass `includeSequences=true` to keep it)
- `getJobLogs(jobName)` — fetch output logs for debugging
- `listJobFiles(jobName)` — list output files (returns `s3Path` for chaining)
- `getResult(jobName, fileName?)` — download results
- `uploadFile(filename)` — presigned upload URL; or `uploadFileContent(filename, content, encoding?)` to send file content through MCP when the host can't reach S3 (sandboxed agents)

Scope note: MCP query tools (`getJobs`, `getResult`, `listJobFiles`, …) are scoped to the authenticated account.

### REST API (universal)

Use plain HTTP with `requests` — the endpoint shapes are in `openapi.yaml`. The core loop is below; `references/workflows.md` has full recipes.

## Core workflow

Always follow discover → schema → validate → submit → poll → results. Do not hardcode tool names or settings — the catalog changes frequently.

```python
import os, time, requests

BASE = "https://app.tamarind.bio/api"
HEADERS = {"x-api-key": os.environ["TAMARIND_API_KEY"]}

# 1. Discover tools. REST /tools returns the full list; filter client-side.
tools = requests.get(f"{BASE}/tools", headers=HEADERS).json()
alphafold = next(t for t in tools if t["name"] == "alphafold")

# 2. Get the exact schema for the chosen tool.
#    REST: each /tools entry already includes its inline `settings` schema
#          (parameter list) — find the entry whose name == your job type.
#    MCP:  getJobSchema(jobType) returns the same per-tool detail.

# 3. Submit a job. `settings` is tool-specific — match the schema exactly.
payload = {
    "jobName": "my-alphafold-run",          # ^[a-zA-Z0-9_-]+$, <=100 chars, unique
    "type": "alphafold",
    "settings": {
        "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        "numRecycles": 3,
    },
}
resp = requests.post(f"{BASE}/submit-job", headers=HEADERS, json=payload)
resp.raise_for_status()   # 200 ok; 400 bad request; 403 budget exceeded; 401 unauthorized

# 4. Poll for completion.
#    NOTE the response shape: GET /jobs?jobName=<name> returns the job ROW
#    directly (no "jobs" wrapper); the list query (no jobName) returns
#    {"jobs": [...]}. Don't index ["jobs"][0] on the by-name response.
while True:
    job = requests.get(f"{BASE}/jobs", headers=HEADERS,
                       params={"jobName": "my-alphafold-run"}).json()
    if job["JobStatus"] in ("Complete", "Stopped", "Deleted"):
        break
    time.sleep(30)

# 5. Retrieve results. POST /result returns a presigned URL *string*;
#    GET that URL to download the actual results zip (two-step).
url = requests.post(f"{BASE}/result", headers=HEADERS,
                    json={"jobName": "my-alphafold-run"}).text.strip('"')
open("my-alphafold-run.zip", "wb").write(requests.get(url).content)
```

For the agentic version of this loop using MCP tools, and for richer examples, see `references/workflows.md`.

## Discovering tools

The catalog has hundreds of tools. Always enumerate at runtime — never rely on a hardcoded list.

**REST** `GET /tools` returns the **full list** (it does not filter server-side); each item is `{name, displayName, github, paper, description, settings}` where `settings` is that tool's inline parameter schema. Filter client-side:

```python
tools = requests.get(f"{BASE}/tools", headers=HEADERS).json()   # a list
boltz = [t for t in tools if "boltz" in t["name"].lower()]
```

Note: both surfaces return one row per tool name — REST `/tools` and MCP `getAvailableTools` are both deduplicated (the MCP keeps the newest tool version), so a name match returns a single row.

**MCP** `getAvailableTools(search=..., modality=..., function=...)` filters server-side and adds `categories`/`tags` per tool (`category`/`tag` are deprecated aliases of `modality`/`function`, still honored). Don't hardcode the vocabulary — it drifts. Get the live values from `listModalities()` / `listTags()` (each returns `value`, `label`, `description`, and `toolCount`), or read the `availableCategories` / `availableTags` facet arrays returned on every `getAvailableTools` response. Modalities are molecule types (protein, antibody, peptide, small-molecule, nucleic-acid, …); functions are what a tool does (structure-prediction, binder-design, protein-ligand-docking, …).

A representative set of widely-used tools (verify with `/tools`): `alphafold`, `boltz` (Boltz-2), `chai` (Chai-1), `esmfold` / `esmfold2`, `rfdiffusion`, `proteinmpnn`, `ligandmpnn`, `boltzgen`, `bindcraft`, `diffdock`. See `references/tool_catalog.md` for the full category/tag map and how to read tool metadata.

## Choosing the right tool

The catalog has many tools per task; **don't hardcode a favorite — filter by `function` (and `modality`), then read each candidate's `description` and match it to the user's actual goal** (input you have, output you need, constraints like speed or "no MSA"). The `description` and `tags` fields are the public "what it's for" signal; let them, plus `validateJob`, drive the pick. Quick orientation by task:

- **Fold a single protein / complex** (`function=structure-prediction`): the AlphaFold3-class reproductions — `boltz`/`chai`/`openfold`/`protenix`/`intfold` — are the accurate default for **everything**, including protein-only systems; they also handle **nucleic-acid + small-molecule complexes**, so reach for them whenever a ligand/RNA/DNA is part of the system (and `boltz` adds binding-affinity). `alphafold` (AF2) remains a solid choice for monomers + multimers (join chains with `:`). `esmfold` is single-sequence (no MSA) and fast — reach for it when you want speed and have no MSA; `esmfold2` is newer and conditions on an MSA by default (its `model` setting offers a faster single-sequence mode). Specialized folders exist for antibodies (`abodybuilder`, `immunebuilder`), cyclic peptides (`highfold`), and conformational ensembles (`afcluster`, `alphaflow`) — filter and read descriptions.
- **Design a binder** (`function=binder-design`): `bindcraft` (de novo miniprotein binders) and `boltzgen` (binders for protein **and** small-molecule targets, incl. nanobodies/antibodies/peptides) are the go-to de novo binder tools; `rfdiffusion` also does binder design and is the pick for **motif scaffolding** / diversifying an existing backbone. Antibody-specific generators live under `function=antibody-design`.
- **Design sequence for a known backbone** (`function=inverse-folding`): `proteinmpnn` (general), `ligandmpnn` (ligand-aware), plus thermostable/soluble/antibody MPNN variants. Inverse folding takes a **structure** and emits **sequences** — fold them back to verify (see chaining).
- **Dock a small molecule** (`function=protein-ligand-docking`): prefer `boltz`/`chai` — they co-fold the ligand into the complex and predict the bound structure rather than docking into a fixed receptor; reach for `autodock-vina` when you need fast, large-scale screening against a known pocket.
- **Predict binding affinity** (`function=binding-affinity`) or **generate an MSA** (search `msa`) — filter and read.

When the user names a specific tool, evaluate that one **and** sanity-check the alternatives in its `tag` group — a faster or more appropriate sibling often exists. When unsure, `getJobSchema`/`validateJob` to confirm a candidate actually accepts the input you have before committing.

## Job settings, schemas, and validation

Each tool has its own `settings` schema. Fetch it before submitting:

- **REST** `/tools` entry: each `settings` param is a **trimmed** dict. Only `name` and `required` are always present; `type`, `default`, `description`, `options` appear only when relevant (≈60% have `type`) — so use `param.get("type")`, not `param["type"]`. The advanced gating keys (`exclude`, `conditionals`) are **NOT in the REST response** at all.
- **MCP** `getJobSchema(jobType)`: the **full** schema, including `exclude`, `conditionals`, and bounds. Use MCP when you need to reason about those gating keys. (`restrictOrgs` is stripped on both surfaces — an org-gated param you can't use is simply omitted; see `references/api_reference.md`.)

**Validate before submitting:** use `validateJob` (MCP) or `POST /api/validate-job` (REST) with `type`, `settings`, and the planned `jobName`. Check the JSON `valid` flag and errors even on HTTP 200; this endpoint does not queue a job. It runs the same validation as `/submit-job` without submitting, and surfaces the first missing/invalid field. Don't try to hand-derive which fields to strip from the schema keys (over REST you can't see them anyway) — let `validateJob` tell you. (The response may include a `source` field, e.g. `"static-fallback"` — an internal note on which schema source validated; `valid: true/false` is the signal you act on.)

`validateJob` echoes a `normalized` view of your settings with defaults filled in. Submit the same clean `settings` you validated; treat `normalized` as informational (it can carry defaults you didn't set, and for some tools platform-managed fields), so build your submit from your own settings rather than the normalized blob.

**Sequences:** amino-acid string; separate chains of a multimer with a colon (`:`), e.g. `"MVLS...:EVQL..."`. Note that some tools (e.g. `boltz`, `chai`) require more than `sequence` — `boltz` also requires `inputFormat` (and accepts `yamlFile`/`molecules`). Always `getJobSchema`/`validateJob` to learn a tool's required fields; don't assume `sequence` alone suffices.

**Platform-internal fields** — never set these yourself; the platform owns them: `submit_method`, `monomer_msa`, `msa`. See `references/api_reference.md` for the full field-handling rules.

**Surface consequential choices before submitting, don't default silently.** When the request fully specifies what to run, proceed. But when it's open-ended, or when a setting materially changes the results, runtime, or cost (model/variant, number of samples or seeds, MSA on/off, GPU tier, batch size), present the meaningful options plus the default you'd otherwise apply and let the user pick **before** you submit — rather than choosing silently and reporting it after the job is queued. `getJobSchema` and `validateJob`'s `normalized` show exactly which knobs you're filling in on the user's behalf, so you can flag the few worth a quick confirm. This matters most for **batches**, where one shared-settings choice multiplies across every job.

## File inputs (PDB, CIF, SDF, …)

Tools with file parameters accept input three ways:

1. **Upload first, then reference by bare filename.** `PUT /upload/{filename}`, or MCP `uploadFile` → presigned URL → `curl -X PUT -T file "<url>"`. If your host can't reach S3 (a sandboxed agent with no outbound network), use MCP `uploadFileContent(filename, content, encoding?)` to send the file's content through the MCP channel instead — text by default, `encoding="base64"` for binary. The object lands at the S3 key `{email}/{filename}`, **but you reference it in `settings` by the bare `filename` only** (e.g. `"targetFile": "GLP1R_ECD.pdb"`) — the platform scopes it to your account automatically. **Do NOT prefix the email**: passing `{email}/{filename}` double-prefixes the lookup and `submit-job` 400s with `"The following files have not been uploaded: <email>/<file>"`. Confirm the exact name the store registered with MCP `getFiles(search=...)` / REST `GET /files` (a flat list of bare names).
2. **Reference a prior job's output** by its path: `JobName/path/to/file.ext` (this is how you chain jobs — see below).
3. **Inline content.** Send the file's text content directly as the field value.

**Foot-gun:** for a file-typed parameter, a **plain string value is treated as inline file content**, not as a path to an existing object. To point at an already-uploaded file, use the bare `filename` (not the `{email}/...` S3 key) or, for a prior job's output, the `JobName/...` path form — not a bare string you expect to resolve to new content.

**`validateJob` notes.** The response may carry a `source` field (e.g. `"static-fallback"`) — it labels how the tool's *schema* was resolved (built-in tools always report `static-fallback`), **not** whether the validator was reachable, so act on `valid`, not `source`. For file params: reference an uploaded file by its **bare filename** (above) — a bare name resolves to your account-scoped object, whereas an email-prefixed string can be read as inline content and fail the file-type check (`"... must contain ATOM records"`). And passing **inline** file content makes `validateJob` upload it synchronously before validating, which can be slow; prefer referencing an uploaded file by name (above). If a dry-run is slow, skip it and let `submit-job` validate.

## Chaining jobs into pipelines

A finished job's output becomes the next job's input — no download/re-upload. **Match the input type the next tool actually wants:** a sequence-design tool (ProteinMPNN) emits *sequences*, so you fold them by passing each as a `sequence`; a tool that takes a *file* parameter takes a path.

The cleanest design→fold chain is the MCP `submitBatch(fromJob=...)`, which reads a completed design job's generated sequences and folds each as one job:

```
# ProteinMPNN designs sequences -> fold every one with AlphaFold, one call:
submitBatch(batchName="verify-designs", type="alphafold", fromJob="my-proteinmpnn-job")
```

For a **file** input (e.g. a tool that takes a `.pdb`/`.cif`), reference a prior job's output by the path form `JobName/path/to/file.ext` in that file parameter. Two cautions, both confirmed by validation: (1) match the parameter's required **file type** — e.g. AlphaFold's `templateFiles` accepts only `.cif` and is a list, and is gated behind `templateMode: "custom"`; (2) `templateFiles` is for *structural templates*, not for "fold this designed sequence" — to fold a sequence, pass `sequence`. Always `getJobSchema`/`validateJob` to confirm a file param's type/conditions before chaining into it.

To discover a job's exact output paths, use MCP `listJobFiles(job1)` — it returns each file's `s3Path`, usable directly in the next `submitJob`. (The REST `GET /files` lists your account's *uploaded* files as a flat name list; it does not enumerate a job's outputs.) Tamarind also supports saved **pipelines**: build one in the UI, then drive it with `/run-pipeline` (`{pipelineName, initialInputs, inputs}`) or define `stages[]` inline via `/submit-pipeline` (each stage names a `task` + `toolSettings`, using `"pdbFile": "pipe"` to thread one stage's output into the next). See `references/workflows.md`.

## Batch submission

Submit many jobs of the **same tool** in one call. The Python form uses parallel `settings[]` and `jobNames[]` arrays (same length, up to 100):

```python
requests.post(f"{BASE}/submit-batch", headers=HEADERS, json={
    "batchName": "egfr-binder-screen",
    "type": "alphafold",
    "jobNames": ["seq1", "seq2", "seq3"],
    "settings": [{"sequence": "..."}, {"sequence": "..."}, {"sequence": "..."}],
    # optional: "maxRuntimeSeconds": 3600, "weightedHoursBudget": 100,
    # (some accounts also accept an optional "gpuType" — confirm with support)
})
```

**Poll the batch *parent* on `batchStatus`, not subjob `JobStatus`.** A batch creates a parent job (`Type: "batch"`) plus subjobs. Subjobs flip to `Complete` as soon as they finish computing, but the batch then spends a few minutes **aggregating** results into the final downloadable output. Fetch the parent by name and watch `batchStatus`:

```python
import time
while True:
    # ?jobName= returns the parent ROW directly (no "jobs" wrapper)
    parent = requests.get(f"{BASE}/jobs", headers=HEADERS,
                          params={"jobName": "egfr-binder-screen"}).json()
    bs = parent.get("batchStatus")
    if bs == "Complete":
        break
    if bs in ("Stopped", "AggregationFailed"):
        raise RuntimeError(parent.get("AggregationError", bs))
    time.sleep(15)   # Running / Aggregating -> keep waiting
# When Complete, the parent carries a presigned `resultUrl` and a `statuses`
# subjob tally ({Complete, Running, In Queue, Stopped}).
open("batch.zip", "wb").write(requests.get(parent["resultUrl"]).content)
```

Add `includeSubjobs=true` to `GET /jobs?batch=<name>` to list per-subjob rows.

## Job status lifecycle

Single jobs report `JobStatus`; batch parents report `batchStatus` (poll that for batches — see above).

| Status | Meaning |
|---|---|
| `In Queue` | Accepted, waiting for capacity |
| `Running` | Executing on a worker |
| `Complete` | Finished successfully — results available |
| `Stopped` | Stopped (failure, timeout, manual stop, or budget) |
| `Deleted` | Job was deleted out-of-band |
| `Aggregating` | (batch parent only) subjobs done; building the final output |
| `AggregationFailed` | (batch parent only) aggregation step failed |

Completed jobs carry a `Score` (tool-specific metrics, e.g. pLDDT/pTM/ipTM for folding) and `WeightedHours`. Treat `Complete`/`Stopped`/`Deleted` (and `AggregationFailed` for batches) as terminal; poll on a 15-30s interval. **Break your poll loop on any terminal status, not just `Complete`/`Stopped`** — a job that goes `Deleted` mid-poll would otherwise loop forever. For a `Stopped` job, fetch `getJobLogs(jobName)` to see why. `WeightedHours` is the usage unit billed per job; cap a batch with `weightedHoursBudget`, and a `403` on submit means a budget was hit (see `references/api_reference.md` and the `/usage-statistics` endpoint).

## Error handling

| Code | Meaning | Action |
|---|---|---|
| 400 | Bad request / invalid settings | Re-check against the schema; run `validateJob` first |
| 401 | Unauthorized | Check `x-api-key` |
| 403 | Budget exceeded (org/team) | Lower scope or raise the budget |
| 429 | Rate limited | Back off and retry |
| 500 | Server error | For submission errors/timeouts, inspect the persisted job name with `/jobs` or `/jobs/search` before retrying; a lost response does not prove the job was not queued. Back off for safe reads. |

## Reference files

The `openapi.yaml` spec is the source of truth for endpoint shapes; these files add the behaviors and gotchas the spec doesn't spell out:

- `references/examples.md` — **validated** `settings` payloads per common tool (alphafold/boltz/diffdock/autodock-vina/proteinmpnn/batch), a copy-paste self-check, the "what fails and the exact error" list, and output-shape notes. Start here for a working payload.
- `references/api_reference.md` — endpoint quick-reference + the non-obvious shapes: `/jobs` by-name returns a bare row (not `{jobs:[...]}`), `/result` is a two-step download, batch parents poll on `batchStatus`, `/files` is a flat name list, the `settings` field-handling rules.
- `references/tool_catalog.md` — category/tag map, how to read tool + parameter metadata, common tool families.
- `references/workflows.md` — end-to-end recipes: fold a sequence, validate-before-submit, upload + reference a file, design→fold chaining, batch screen with aggregation polling, usage stats, pagination, and the non-blocking submit-now/check-later pattern for long jobs.
