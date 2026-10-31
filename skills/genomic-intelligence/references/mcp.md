# Hosted MCP server

Connect a Streamable HTTP client to `https://mcp.genomicintelligence.ai/mcp`.
Anonymous calls use a shared, rate-limited demo principal. For own quotas and job
access send `Authorization: Bearer <GI_API_KEY>` (or the documented `X-GI-Key`
header). Local `gi-mcp` is a thin client: sequences used for predictions still
travel to the hosted REST inference service.

Reviewed hosted discovery on 2026-10-01: 15 tools and six static resources.
Initialize/retain the MCP session and let the host negotiate protocol support;
the read-only probe negotiated `2025-11-25`. Do not assume another server's
protocol version or HTTP framing. The reviewed local package is `gi-mcp`
0.1.0a21 (Python >=3.10); source below a18 has a minus-strand expression-window
one-base shift. Pin a reviewed release when using a local deployment.

## Acquisition and handles

| Tool | Required | Notes |
|---|---|---|
| `fetch_ensembl_sequence` | `gene` | Gene symbol or supported Ensembl ID; optional `species`, nonnegative `flank_bp`. For direct stable-ID REST lookup use `/lookup/id/{id}`. |
| `fetch_region` | `region` | 1-based inclusive range; optional `species`, `strand` (1 or -1), `flank_bp`. Plus strand is the default. |
| `fetch_gene_for_expression` | `gene` | Gene-sense 9,198 bp window; verify `data.tss_source`, strand, assembly and source metadata. |
| `load_demo_sequence` | `name` | Discover task-specific names from `gi://sequences`; avoid ambiguous gene aliases (HBB has both splice and expression demos). |
| `store_inline_sequence` | `sequence` | Optional `name`; whitespace stripped. The inline bases necessarily pass through the calling context. |

Acquisition returns a GI envelope **`{data: {ref, name, length, ...}, meta}`**.
Use `data.ref` as the next tool's `sequence_ref`; it is not a top-level `ref`.
At the MCP transport layer this is inside `result.structuredContent` on the
reviewed server, also serialized in text content. Check MCP `isError` and any
GI error object before reading a success payload: an HTTP 200 can be a tool
failure. Hosted demo job listing, for example, returns `isError: true` and
`code: unavailable`, outside the REST error-code enum.

Handles are server/session-local, in memory, TTL/capacity-limited, and disappear
on restart or eviction. They are not durable sequence accessions. Preserve
acquisition parameters and sequence provenance so a lost handle can be recreated.
The hosted tool list excludes `load_local_fasta`; that tool is local-only.
The handle summary contains only a sequence preview and no checksum. In this
handle-only workflow verify returned length/TSS/strand/source metadata and tool
errors; do not claim to have checked every base or computed a sequence hash.
For exact byte-level provenance, separately acquire and hash the full reference
bases from the recorded assembly/region, checking that source provenance matches.

Despite acquisition tool names, bases can come from the bundled cache, UCSC,
or Ensembl. `meta.source`, `meta.locus_source`, `meta.assembly`,
`meta.catalog_release`, and optional stale metadata reveal this; `data.source`
may be only the acquisition channel. See [sequence acquisition](sequence-acquisition.md).

## Prediction

`predict_promoter`, `predict_splice`, `predict_enhancer`, `predict_chromatin`,
`predict_expression` each take **exactly one** of `sequence_ref` or `sequence`,
plus optional `model` and `sequence_name`. With a handle, its stored name wins.
Expression also needs `description` and, for longer-than-9,198-bp input,
`tss_index`. These two semantic requirements are described by the tools even
where JSON Schema does not mark the arguments required.

Current hosted prediction schemas do **not** expose REST `options.threshold`,
`site_types`, `format`, or an async preference. Use REST when those controls are
needed; do not invent corresponding MCP keyword arguments.

Annotation is `find_genes`, not `predict_annotation`. It takes a sequence or
handle, not a `region`. `find_genes_and_predict_expression` likewise takes a
sequence/handle plus required experimental `description`, with no region or
`tss_index` argument. Both run async internally. `wait=True` (default) returns
the result or a timeout error, not a detached job handle.

**The anonymous demo disables `get_job`, `list_jobs`, and `wait=False`.** With
an own-key session, `wait=False` returns `{data: {job_id, status: "submitted"}}`
to poll with `get_job(job_id)`. This MCP status differs from REST submission's
`"accepted"`. `list_jobs(limit=...)` accepts 1–100 (default 20), whereas REST
allows up to 500. Neither surface exposes pagination.

## Discovery and resources

`list_models(task)` returns the flat `{task, default_model, models}` object.
Discover and record the resolved model ID, organism, window and request bounds.
Resources are `gi://models`, `gi://docs/tasks`, `gi://openapi.json`,
`gi://sequences`, `gi://jobs/recent`, and `gi://account`. The account resource
identifies demo/byok mode; recent jobs is unavailable in demo mode. A resource
being listed does not prove that the current principal may read its content.

## Worked sequence of tool calls

This is host pseudocode, not a Python SDK. Discovery/acquisition was exercised;
the inference calls below are illustrative and consume inference quota.

```text
h = fetch_region(region="chr11:5,225,000-5,235,000")
find_genes(sequence_ref=h.data.ref, wait=True)
find_genes_and_predict_expression(sequence_ref=h.data.ref,
    description="polyA plus RNA-seq; Homo sapiens K562", wait=True)

w = fetch_gene_for_expression(gene="HBB")
# Check w.data.length == 9198 and w.data.tss_source == "canonical-transcript".
# Retain w.meta assembly/source and w.data strand/TSS/region.
predict_expression(sequence_ref=w.data.ref,
    description="polyA plus RNA-seq; Homo sapiens K562")

# No inference: inspect/load the public positive-control sequence.
d = load_demo_sequence(name="promoter_tp53")
# Inference only when requested:
predict_promoter(sequence_ref=d.data.ref)
```
