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
| expression | sync | **9,198–500,000 bp** (scores one 9,198 bp window) | log(TPM+1) |
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
Expression as **log(TPM+1)** from a fixed window. Since 2026-08-18 this task has
its own published OpenAPI operation (`POST /v1/tasks/expression/predict`,
schema `ExpressionPredictRequest`) rather than the generic
`/v1/tasks/{task}/predict` body — codegen consumers must regenerate. Body:
`{sequence, options, tss_index?, sequence_name?, model?}`, closed to unknown
fields. Three enforced requirements, each a `422` when violated:

1. **9,198–500,000 bp.** The model scores exactly one 9,198 bp window
   **centred on the TSS** — `sequence[tss_index-4599 : tss_index+4599]` — but
   the endpoint accepts up to 500 kb and slices for you. Below 9,198 bp is
   rejected; nothing is padded or truncated.
2. **`tss_index`** — 0-based TSS offset into the **whitespace-stripped**
   sequence. Required unless the sequence is exactly 9,198 bp (where it defaults
   to 4,599, the only legal value). Bounds:
   `4599 ≤ tss_index ≤ len(sequence) − 4599`. The server does not find the TSS
   for you and does not reverse-complement — submit gene-sense.
3. **`options.description`** — a cell-type / assay string (e.g. `"K562 cells"`).
   Required, and the only key `options` accepts here.

Whitespace is stripped before lengths and `tss_index` are interpreted, so a
line-wrapped FASTA *body* can be pasted verbatim — but a `>` header line cannot
(it fails the A/C/G/T/N alphabet check), and offsets must be counted on the
stripped string, not on file characters.

Result: `data.prediction.expression_log_tpm` (and `expression_tpm`).
`meta.task_specific_counts` carries `tss_index` and `scored_window`
(`[start, end]`, always 9,198 wide) — assert on it, because an in-range but
wrong `tss_index` scores the wrong window with a `200`. `data.input` echoes
`tss_index`, `scored_window`, and `submitted_sequence_length`; note
`data.input.sequence_length` is the **scored** 9,198, not what you submitted.

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
and returns an expression prediction per gene. The composite does its own gene
finding and windowing, so it has **no** 9,198 bp floor and takes **no**
`tss_index`. Over REST, discover genes then loop `expression` per gene (build
each TSS-centred 9,198 bp window, or pass the locus plus a `tss_index`).
