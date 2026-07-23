# Hosted MCP Server

GI hosts a Model Context Protocol server (Streamable HTTP) at:

```
https://mcp.genomicintelligence.ai/mcp
```

It works **keyless** against a capped public demo quota — no setup. An optional
`gi_` bearer key (`GI_API_KEY`) raises the quota. Prefer MCP on agent hosts that
support it: the tools mirror the six tasks with agent-friendly, handle-based
schemas so large sequences never enter the context.

## The handle-based flow

Acquire a **sequence handle** (`sequence_ref`), then predict against it:

1. **Acquire** — any of these return a `sequence_ref`:
   - `load_demo_sequence()` — a ready demo handle (keyless smoke test)
   - `fetch_ensembl_sequence(region=...)` / `fetch_region(...)` — reference
     sequence for a gene or region (public Ensembl)
   - `fetch_gene_for_expression(gene=...)` — a **TSS-centred 9,198 bp** handle
     for `expression` (does the centring for you)
   - `find_genes(region=...)` — genes in a region
   - `load_local_fasta(path=...)` / `store_inline_sequence(sequence=...)` — from
     a local FASTA or an inline string
2. **Predict** — pass the handle:
   - `predict_promoter`, `predict_splice`, `predict_enhancer`,
     `predict_chromatin`, `predict_expression(..., description=...)`
3. **Async** — `annotation` submits a job; poll `get_job(job_id)` (and
   `list_jobs`) until terminal.

## Discovery & composite

- `list_models(task)` — the model registry for a task (don't invent IDs).
- `find_genes_and_predict_expression(region=..., description=...)` — the
  composite: find genes in a region, predict each one's expression.

## Resources

Reference context lives in MCP resources: `gi://models`, `gi://docs/tasks`,
`gi://sequences`, `gi://account`. Read these instead of hardcoding model lists or
bounds.

## Small sequences

Small sequences may be passed inline via a `sequence` argument on the
`predict_*` tools, but the handle flow above is preferred to keep context small.
