# Hosted MCP Server

GI hosts a Model Context Protocol server (Streamable HTTP) at:

```
https://mcp.genomicintelligence.ai/mcp
```

It works **keyless** against a capped public demo quota, with no setup. An
optional `gi_` bearer key (`GI_API_KEY`) raises the quota. Prefer MCP on agent
hosts that support it: the tools use agent-friendly, handle-based schemas so large
sequences never enter the context.

The hosted server exposes **15 tools**. Verify with `tools/list` rather than
assuming; the list below is a point-in-time snapshot.

## The handle-based flow

Acquire a **sequence handle** (`sequence_ref`), then predict against it.

### 1. Acquire (each returns a handle)

| Tool | Required | Notes |
|---|---|---|
| `fetch_ensembl_sequence` | `gene` | Gene **symbol or Ensembl ID** (e.g. `"TP53"`). Also `species`, `flank_bp`. Not for coordinates. |
| `fetch_region` | `region` | Coordinate range, e.g. `"chr8:127,680,000-127,800,000"`. Also `species`, `strand`, `flank_bp`. Plus strand by default, which is what gene finding expects. |
| `fetch_gene_for_expression` | `gene` | Builds the **TSS-centred 9,198 bp** window `expression` needs. Also `species`. |
| `load_demo_sequence` | `name` | **`name` is required.** Valid names: `promoter_tp53`, `splice_hbb`, `enhancer_eve`, `chromatin_active_promoter_chr19`, `expression_hbb_k562`, `annotation_hbb_chr11`. |
| `store_inline_sequence` | `sequence` | Store an inline string; optional `name`. |

There is **no `load_local_fasta` on the hosted server** — it only exists in local
deployments. Over REST, read the file yourself.

### 2. Predict (pass the handle)

`predict_promoter`, `predict_splice`, `predict_enhancer`, `predict_chromatin`,
`predict_expression`. Each takes `sequence_ref` **or** `sequence` (mutually
exclusive), plus optional `model` and `sequence_name`.

`predict_expression` additionally needs `description` (cell type / assay, e.g.
`"K562 cells"`).

### 3. Gene finding (the annotation task on MCP)

**There is no `predict_annotation` tool.** The annotation task is surfaced as
**`find_genes`**, which takes `sequence_ref` or `sequence` — **not** a `region`.
Acquire a region handle with `fetch_region` first, then pass the handle.

`find_genes` runs async internally (~8-25 s). With `wait=True` (the default) it
blocks and returns the result directly, never a job id. With `wait=False` it
returns `{data: {job_id, status}}` to poll with `get_job(job_id)`.

## Composite

`find_genes_and_predict_expression` takes `sequence_ref` or `sequence` plus a
**required** `description`. It has **no `region` parameter** — acquire a handle
with `fetch_region` first. It finds genes in the sequence, then predicts
expression off each discovered TSS. Use it whenever you want expression for a
whole region: `predict_expression` cannot run on one, because it needs a single
per-gene 9,198 bp window.

## Jobs and discovery

- `get_job(job_id)` (required `job_id`) and `list_jobs` — poll detached work.
- `list_models(task)` — the model registry for a task. Do not invent model IDs,
  and do not hardcode a default; omit `model` and the server resolves it.

## Resources

Reference context lives in MCP resources: `gi://models`, `gi://docs/tasks`,
`gi://sequences`, `gi://account`. Read these instead of hardcoding model lists or
bounds.

## Small sequences

Small sequences may be passed inline via `sequence` on the `predict_*` tools, but
the handle flow above is preferred to keep context small.

## Worked example

```
# region -> handle -> genes -> expression per gene
h = fetch_region(region="chr11:5,225,000-5,235,000")
find_genes(sequence_ref=h.ref)
find_genes_and_predict_expression(sequence_ref=h.ref, description="K562 cells")

# gene -> handle -> promoter
g = fetch_ensembl_sequence(gene="TP53")
predict_promoter(sequence_ref=g.ref)

# keyless smoke test
d = load_demo_sequence(name="promoter_tp53")
predict_promoter(sequence_ref=d.ref)
```
