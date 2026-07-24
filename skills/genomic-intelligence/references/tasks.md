# Tasks Reference

Six DNA-sequence tasks, one shared REST shape: `POST /v1/tasks/{task}/predict`
with body `{sequence, sequence_name, model?, options?}`, returning a
`{data, meta}` envelope. On MCP, the equivalent is `predict_<task>(sequence_ref, ...)`.

**Omit `model` to get the task's default** — the API resolves it server-side
(`model` is optional: *"If omitted, the task's default model is used."*). Default
model **IDs are deliberately not listed here**: defaults change and old IDs are
retired, so a hardcoded ID is a future hard failure. Discover them at call time
with `GET /v1/tasks/{task}/models` (REST) or `list_models(task)` (MCP), and
**never invent one**.

Source of truth for bounds: the live OpenAPI at
<https://api.genomicintelligence.ai/v1/openapi.json>.

| Task | Mode | Length | Default architecture |
|---|---|---|---|
| promoter | sync | 1–500,000 bp | sliding-window; human/mammalian |
| splice | sync | 1–500,000 bp | BigBird (long-context) |
| enhancer | sync | 1–500,000 bp | DeepSTARR — ***Drosophila*** |
| chromatin | sync | 1–500,000 bp | DeepSEA — hundreds of tracks |
| expression | sync | **exactly 9,198 bp** | log(TPM+1) |
| annotation | **async** | 1–500,000 bp | de-novo transcripts |

## promoter
Promoter regions over a sliding window. `data.summary` reports
`promoter_windows` / `total_windows`; `data.regions` lists windows with `name`,
`start`, `end`, `score`, `strand`. Non-human models exist (Drosophila, yeast,
Arabidopsis) — pass `model`. Default targets human/mammalian sequence.

## splice
Splice **donor** and **acceptor** sites. `data.sites` lists each with `name`,
`start`, `end`, `site_type` (donor/acceptor), `score`, `strand`. The default is a
BigBird long-context model.

## enhancer
Enhancer activity. The default (DeepSTARR) reports **developmental**
and **housekeeping** scores — `summary.dev_score_max` / `summary.hk_score_max`
per window. DeepSTARR is a *Drosophila* model — match the species to the model.

## chromatin
Chromatin state across a large panel of tracks (histone marks, DNase, ATAC, TF
binding). The default (DeepSEA) covers hundreds of features.
`summary.total_annotations` is the headline; the full per-track matrix is in
`data`.

## expression
Expression as **log(TPM+1)** from a fixed window. Two enforced requirements:

1. **Exactly 9,198 bp** — a window **centred on the TSS** (4,599 upstream +
   TSS + 4,598 downstream). Other
   lengths are rejected. Build it with the acquisition helpers
   (`fetch_gene_for_expression` on MCP), not by hand — see
   `sequence-acquisition.md`.
2. **`options.description`** — a cell-type / assay string (e.g. `"K562 cells"`).
   Required.

Result: `data.prediction.expression_log_tpm` (and `expression_tpm`).

## annotation
De-novo gene / transcript structure — transcript intervals and strand, no
reference annotation. **Async only**: submit with
`Prefer: respond-async` → `job_id`; poll `GET /v1/tasks/jobs/{job_id}` until it
returns `200`. `data.transcripts` lists each transcript with `name`, `start`,
`end`, `strand`, `score`, plus structure fields (`length`, `tss_position`,
`polya_position`, `transcript_type`, `exons`, `introns`, `cds`).

## Composite: find genes + predict expression
"What genes are in this region, and how are they expressed?" — MCP
`find_genes_and_predict_expression(sequence_ref, description)` takes a **handle,
not a region** (acquire one with `fetch_region` first); `description` is
required. It finds genes in the sequence
and returns an expression prediction per gene. Over REST, discover genes then
loop `expression` per gene (build each TSS-centred 9,198 bp window first).
