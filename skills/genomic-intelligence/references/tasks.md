# Tasks Reference

Six DNA-sequence tasks, each its own published REST operation —
`POST /v1/tasks/promoter/predict`, `/v1/tasks/splice/predict`,
`/v1/tasks/enhancer/predict`, `/v1/tasks/chromatin/predict`,
`/v1/tasks/annotation/predict`, `/v1/tasks/expression/predict` — with body
`{sequence, sequence_name?, model?, options?}`, returning a `{data, meta}`
envelope. The URLs are the same strings clients already send; what changed is that
each has its own request schema, its own `minLength`, and its own closed `options`
object (there is no shared `PredictRequest` any more). On MCP, the equivalent is
`predict_<task>(sequence_ref, ...)`.

**Omit `model` to get the task's default** — the API resolves it server-side
(`model` is optional: *"If omitted, the task's default model is used."*). Default
model **IDs are deliberately not listed here**: defaults change and old IDs are
retired, so a hardcoded ID is a future hard failure. Discover them at call time
with `GET /v1/tasks/{task}/models` (REST) or `list_models(task)` (MCP), and
**never invent one**.

Source of truth for bounds: the live OpenAPI at
<https://api.genomicintelligence.ai/v1/openapi.json>.

| Task | Mode | Accepted length | `context_window_bp` | Default architecture |
|---|---|---|---|---|
| promoter | sync | 300–500,000 bp | 2,000 bp | sliding-window; human/mammalian |
| splice | sync | 100–500,000 bp | 15,000 bp | BigBird (long-context) |
| enhancer | sync | 50–500,000 bp | 249 bp | DeepSTARR — ***Drosophila*** |
| chromatin | sync | 200–500,000 bp | 1,000 bp | DeepSEA — hundreds of tracks |
| expression | sync | **9,198–500,000 bp** (scores one 9,198 bp window) | n/a (`trained_window_bp` 9,198) | log(TPM+1) |
| annotation | **async** | 1,000–500,000 bp | n/a | de-novo transcripts |

The minimum is published as `minLength` on each task's request schema and enforced
before any model loads. There are **no per-model floors**: a task's floor is the
strictest its models need, and every model stays listed and loadable.

**Floor ≠ regime.** A request above the floor but shorter than the selected
model's `bio_spec.context_window_bp` is accepted and scored — against a window
padded out to the context window. Enhancer is the sharp case: the bound is 50 bp
(DeepSTARR's admission gate; `dnabert-deepstarr` tolerates 16) while the context
window is 249 bp, so 50–248 bp is scored mostly on padding. Compare your length
against `context_window_bp` to know whether the model saw real sequence.
Longer-than-context input is fine — the scanner steps a prediction window at a
time and pads only the final partial window.

Under the floor and over the cap are both `422 validation_failed` at
`loc ["body","sequence"]`; over-length is **not** a `413`. All lengths are
measured after whitespace is stripped.

`options` is typed and closed (`additionalProperties: false`) per task — an
unknown key is a hard `422` (`type: "extra_forbidden"`), never ignored:

| Task | `options` keys |
|---|---|
| promoter | `threshold` (0–1, default 0.5) |
| splice | `threshold` (0–1, default 0.5), `site_types` (subset of `["donor","acceptor"]`, default both) |
| enhancer | *(none)* |
| chromatin | `threshold` (0–1, default 0.5) |
| annotation | `batch_size` (1–128, default 8), `shift_coordinates`, `reverse_complement` (default true) |
| expression | `description` — **required**, and the only key |
| composite | `description`, `annotation_model`, `expression_model`, `batch_size`, `shift_coordinates` |

Per-task output `format` values (an unsupported one is `415 unsupported_format`,
never a silent fallback to JSON; text formats are synchronous-only): promoter
`json|bed|bedgraph`, splice `json|bed|gff3`, enhancer `json|bedgraph`, chromatin
`json|bed`, annotation `json|bed|gff3`, expression JSON only.

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
Expression as **log(TPM+1)** from a fixed window. Its operation is
`POST /v1/tasks/expression/predict`, schema `ExpressionPredictRequest` — alone
among the six it requires `options` as well as `sequence`. Body:
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

Both `tss_index` failures come from a `model_validator(mode="after")` and so
report at `loc: ["body"]`, **never** `body.tss_index`. Match on
`error.code == "validation_failed"` — never on `loc`.

## annotation
De-novo gene / transcript structure — transcript intervals and strand, no
reference annotation. **Run it async** (`Prefer: respond-async` is available on
every predict operation; annotation is the one that needs it): submit with
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
`tss_index`.

Over REST it is a single published operation:
`POST /v1/workflows/find-genes-and-predict-expression`, request
`FindGenesAndPredictExpressionRequest` — `sequence` 1,000–500,000 bp and
`options` both required, and `options.description` required too (enforced at
runtime rather than marked `required` in `FindGenesAndPredictExpressionOptions`,
so a missing or empty value is `422 validation_failed`, *"options.description is
required (cell type / assay context)"*). Optional: `annotation_model`,
`expression_model`, `batch_size` (1–128, default 8), `shift_coordinates`.

It cuts a TSS-centred 9,198 bp window per discovered gene, padding with `N` up to
half the window rather than dropping an edge gene — the direct expression route
refuses to pad at all. `meta.task_specific_counts` =
`{genes_found, genes_predicted, genes_skipped}` with
`genes_predicted + genes_skipped == genes_found`; per-gene causes in
`data.expression_predictions[].skip_reason`.

Above **50,000 bp** it forces async: a synchronous request over that size is
`413 sync_too_large` with `error.details = {sequence_length, threshold}`. Retry
the same body with `Prefer: respond-async`.
