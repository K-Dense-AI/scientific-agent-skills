---
name: tamarind
description: Provides access to a collection of open-source molecular design and structural biology tools on the Tamarind Bio platform, via its REST API or MCP server — no local GPUs required. Tamarind bundles popular open-source models for structure prediction (AlphaFold, Boltz, Chai, ESMFold), protein, binder, and de novo design (RFdiffusion, ProteinMPNN, BoltzGen), antibody and nanobody design and developability, protein-ligand docking (DiffDock, Autodock Vina), binding-affinity prediction, MSA generation, and molecular dynamics. Use when the user mentions Tamarind or tamarind.bio, wants to run any of these open-source tools in the cloud, references app.tamarind.bio/api or the x-api-key header, or needs to submit batches of sequences for structural or biophysical characterization.
license: MIT
compatibility: Requires Python 3.10+, a Tamarind Bio account, and an API key from app.tamarind.bio. Uses the `requests` library against the public REST API (these recipes use HTTP directly). Network access required. Optional MCP server at mcp.tamarind.bio/mcp for agent hosts.
metadata:
  version: "1.3"
  last-reviewed: "2026-09-30"
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

Tamarind runs molecular-design and structural-biology tools on managed compute:
structure prediction, protein and antibody design, docking, binding-affinity
prediction, MSA generation, and molecular dynamics. Use it when the user requests
Tamarind, its REST API/MCP server, or cloud execution of these scientific tools.
For local sequence processing or molecular descriptors, use a local library.

## Sources and review scope

The REST contracts and public catalog were reviewed on **2026-09-30**. Examples are
illustrative until validated against the user's account; this review did not run
authenticated jobs or establish scientific accuracy for any model.

- [API index](https://app.tamarind.bio/llms.txt) and
  [complete guide](https://app.tamarind.bio/llms-full.txt).
- [Current OpenAPI](https://app.tamarind.bio/api/openapi.json) includes discovery,
  validation, jobs, files, and newer pipeline/custom-tool surfaces.
  [openapi.yaml](https://app.tamarind.bio/openapi.yaml) is also available. Check that
  needed paths exist: the merged spec can return HTTP 200 with only its classic
  surface when the backend spec cannot be fetched.
- [Public catalog](https://app.tamarind.bio/tools.json) needs no key; query `?type=`
  or `?tag=`. It documents public tools and conditional required settings, not
  every optional parameter or account entitlement.
- [Product documentation index](https://docs.tamarind.bio/llms.txt) links to
  Markdown pages, including the [MCP guide](https://docs.tamarind.bio/tamarind/mcp-server.md).

Fetch the account's current schemas before composing a run. Where the prose guide
and OpenAPI differ, prefer the operation/schema for field shapes, and record any
unresolved difference rather than guessing.

## Access

1. Use the user's Tamarind deployment. The shared base is
   `https://app.tamarind.bio/api`; a dedicated organization deployment has its own
   host and account data. Every relative REST path below is under `/api`.
2. Obtain a key from the deployment's API settings and read it from
   `TAMARIND_API_KEY`; send it as `x-api-key`. Keep keys out of files and logs.
3. Check the account's current allowance and compute budget before scaling up.
   Free usage is a monthly allowance, not an unconditional promise of ten jobs
   forever; billing and entitlements can change.

```bash
# Public discovery requires no credential.
curl --fail-with-body 'https://app.tamarind.bio/tools.json?type=alphafold'
# Account-scoped discovery:
curl --fail-with-body 'https://app.tamarind.bio/api/tools' \
  -H "x-api-key: $TAMARIND_API_KEY"
```

For REST examples install `requests` in the execution environment. The official
CLI distribution is **`tamarind-cli`**, and its Custom Tools Python client imports
as `from tamarind import Tamarind`; the unrelated package named `tamarind` is not
this client. See the [SDK reference](https://app.tamarind.bio/api-docs/custom-tools-sdk-reference).
Core job recipes below use HTTP directly.

## Workflow

1. **Discover.** Read `GET /tools` and match the user's scientific task to the tool
   description. Built-ins return an array; `?custom=true` lists legacy custom
   tools only. Current custom deployments can be missing from this list: use the
   known deployed name and its schema before concluding that it is unavailable.
2. **Read the schema.** `GET /tools/{name}/schema` returns a JSON Schema for the
   `settings` object. `GET /tools` also supplies a trimmed `settings` parameter
   list. Check task-dependent fields, file extensions, list values, and defaults.
3. **Validate.** Send `POST /validate-job` with `type`, `settings`, and optional
   `jobName`. Check HTTP status first, then JSON `valid`. On success, inspect and
   use `normalized` as the settings to submit. Address `unrecognized_settings`
   if returned, even alongside `valid: true`: an optional-field typo can otherwise
   silently leave the default in effect. Validation checks fields, not all submit
   policies, queue limits, or deployment readiness.
4. **Submit once.** `POST /submit-job` takes `jobName`, `type`, `settings`, optional
   `version` for a custom-tool build, and optional/organization-required
   `projectTag`. Persist the submitted name and settings. A successful response
   is plain text, not a JSON receipt. Use the returned stored name.
5. **Poll.** `GET /jobs?jobName=...` returns a row directly. Single-job terminal
   states are `Complete`, `Stopped`, and `Failed`; handle legacy `Deleted` or an
   exact-lookup error without looping indefinitely. Poll batch parents using
   `batchStatus`, and poll newer pipelines on their own run endpoint.
6. **Download and inspect.** `POST /result` returns a JSON string URL on **200**,
   or **202** with `status: "preparing"`. Retry result retrieval after 202, without
   resubmitting compute. GET the signed URL without the Tamarind API-key header.
   Download the archive only for successful runs; request `fileName: "output.log"`
   for stopped/failed jobs. Verify the scientific outputs after downloading.

[Workflow recipes](references/workflows.md) implement validation, stored names,
bounded polling, 202 handling, batch validation, and pagination. They are locally
smoke-tested with simulated responses; authenticated execution remains untested.

## Picking tools and interpreting results

Select by inputs, intended output, and modeling assumptions, then confirm the
candidate in the live catalog. These are anchors, not a guaranteed catalog:

| Task | Candidates and decisions |
|---|---|
| Protein/complex structure | `alphafold` for AF2 monomers/multimers; `boltz`, `chai`, or `protenix` for cofolding including ligands/nucleic acids; `esmfold` for fast single-sequence protein folding. Check `esmfold2` separately: its current catalog includes protein, DNA, RNA, and ligand complexes. |
| Binder/motif design | `bindcraft`, `boltzgen`, `rfdiffusion`; choose by target type, scaffold constraints, and required structure inputs. |
| Inverse folding | `proteinmpnn`/`ligandmpnn` consume structures and design sequences. Re-fold designs and compare to the intended backbone/interface. |
| Small-molecule docking | `autodock-vina` for a fixed receptor and search box; `diffdock` for diffusion docking; `boltz`/`chai` for cofolding. Choose the modeling approach for the task, not to avoid supplying a required input. |
| Antibody/developability/MSA/MD | Filter descriptions and schemas for the specific task; availability and inputs differ by tool. |

Confidence scores describe model confidence, not experimental binding, specificity,
or affinity. Compare designed backbones, interfaces, clashes, chain/residue mapping,
and developability. Check ligand chemistry and stereochemistry; docking scores
are not interchangeable with measured binding free energies. Record tool/model,
input provenance, chain mapping, seeds/samples, MSA/template choices, normalized
settings, and any user-selected filtering thresholds.

Honor the user's selected tool and budget. Use authorized defaults for routine
choices; surface unresolved choices that materially affect the scientific task or
compute scope before a large campaign. Never silently substitute a different
scientific task because its inputs are easier to supply.

## File inputs and chaining

- Upload a structure with `PUT /upload/{filename}` (binary body; follow the
  documented redirect), then reference the registered relative name, e.g.
  `target.pdb` or `inputs/target.pdb` when `?folder=inputs` was used.
- Confirm names using `GET /files`; it returns a non-paginated array for the
  selected folder, not a list of a job's outputs.
- Prefer these paths over inline file content. The current guide says redundant
  account-email prefixes are stripped; there is no longer a universal
  double-prefix failure. Arbitrary strings are not necessarily file references.
- Reuse a completed job's file as `JobName/path/to/file.ext`, matching the next
  parameter's supported extensions and list/scalar shape. Do not guess filenames.
- ProteinMPNN designs must feed a folding tool's **sequence** field. A structural
  template field does not mean "fold this designed sequence". Read generated
  FASTA/CSV sequences and validate one folding settings object per sequence.
- Do not author internal fields such as `submit_method`, `msa`, or `monomer_msa`.

## Batches and pipelines

`POST /submit-batch` accepts one `type`, a nonempty `settings` array, `batchName`,
and optional parallel `jobNames`. Validate **every** row using array-mode
`/validate-job` (up to 1,000 rows per call), and use each row's normalized settings.
Submission allows up to **30,000 expanded jobs**, counting design fan-out, and
has a separate approximately **4.5 MB** request limit. Split on both constraints.
Do not assume old `weightedHoursBudget`, `maxRuntimeSeconds`, or `gpuType` request
fields enforce a cap: they are absent from the current batch schema. Use confirmed
account controls and an agreed job/sample count.

Poll `GET /jobs?jobName=<batchName>` until `batchStatus` is `Complete`, `Stopped`,
or `AggregationFailed`. Subjobs can finish before aggregation. Fetch the archive
through `/result` and handle 202; `resultUrl` is optional and is not a reliable
readiness signal. Page `GET /jobs?batch=...` using `startKey` to inspect children.

For new saved workflows use the template/run API under `/pipelines`: read the
current pipeline graph contract, validate the proposed run with
`POST /pipelines/validate`, submit with `POST /pipelines/submit` (required
`name`, `bindings`, and one of `templateId`/`pipeline`), and poll
`GET /pipelines/runs/{run_id}`. Its statuses are lowercase and separate from job
statuses. The legacy `/submit-pipeline` and `/run-pipeline` remain documented;
[API reference](references/api_reference.md) gives their actual required fields.

## MCP alternative

Connect to `https://mcp.tamarind.bio/mcp` with OAuth 2.1 or the `x-api-key` header.
The official guide confirms `submitJob`, `submitBatch`, `getJobs`, `getResult`,
`uploadFile`, and `getFiles`. Read the connected server's `tools/list` schemas
before using signatures or interpreting result envelopes.

If the connection advertises discovery/validation helpers such as
`getAvailableTools`, `getJobSchema`, or `validateJob`, use their current schemas.
Extra helpers, filter vocabularies, `submitBatch(fromJob=...)`, and upload-through-
MCP variants are not guaranteed by the public guide. This review's anonymous
`tools/list` request returned 401, so their current contracts were not verified.
Use the documented REST equivalents when needed.

## Recovery

HTTP auth failures differ by route: classic endpoints can answer **400**, jobs
can answer **401** or gateway **403**, and usage can answer **401**. A 403 is not
proof of a budget error. Check status and the actual response body before changing
settings. Submission errors may be JSON or plain text regardless of Content-Type.

A timeout/5xx on submit does not prove that nothing queued. Look up the persisted
name before retrying; for campaigns use `POST /jobs/search` with up to 1,000 names
per request. Respect rate limits and avoid one-request-per-job polling at scale.
A 413 rejects the oversized request before creating jobs; split the body or upload
file content separately. `DELETE /delete-job` is a **soft delete**: it hides the
job and leaves stored result files intact.

## Reference files

- [API reference](references/api_reference.md): endpoint shapes, validation,
  pagination, authentication differences, and legacy/new pipeline boundaries.
- [Tool catalog](references/tool_catalog.md): schema interpretation and discovery.
- [Examples](references/examples.md): current catalog-backed settings examples
  and tool-specific caveats, explicitly bounded by verification scope.
- [Workflows](references/workflows.md): executable HTTP recipes with local mocked
  verification; no authenticated scientific jobs were run for this review.
