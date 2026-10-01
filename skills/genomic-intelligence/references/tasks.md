# Tasks Reference

Six DNA-sequence tasks, each its own published REST operation —
`POST /v1/tasks/promoter/predict`, `/v1/tasks/splice/predict`,
`/v1/tasks/enhancer/predict`, `/v1/tasks/chromatin/predict`,
`/v1/tasks/annotation/predict`, `/v1/tasks/expression/predict` — with body
`{sequence, sequence_name?, model?, options?}`, returning a `{data, meta}`
envelope. Each path is a literal string, and each carries its own request schema,
its own `minLength`, and its own closed `options` object; there is no shared
`PredictRequest`. On MCP, use `predict_<task>(sequence_ref=...)`, except annotation is
`find_genes(sequence_ref=...)`.

**Omit `model` to get the task's default** — the API resolves it server-side
(`model` is optional: *"If omitted, the task's default model is used."*). Default
model **IDs are deliberately not listed here**: defaults change and old IDs are
retired, so a hardcoded ID is a future hard failure. Discover them at call time
with `GET /v1/tasks/{task}/models` (REST) or `list_models(task)` (MCP), and
**never invent one**.

Source of truth for bounds: the live OpenAPI at
<https://api.genomicintelligence.ai/v1/openapi.json>.

| Task | Recommended mode | Accepted length | `context_window_bp` | Default architecture |
|---|---|---|---|---|
| promoter | sync | 300–500,000 bp | 2,000 bp | sliding-window; human/mammalian |
| splice | sync | 100–500,000 bp | 15,000 bp | BigBird (long-context) |
| enhancer | sync | 50–500,000 bp | 249 bp | DeepSTARR — ***Drosophila*** |
| chromatin | sync | 200–500,000 bp | 1,000 bp | DeepSEA — hundreds of tracks |
| expression | sync | **9,198–500,000 bp** (scores one 9,198 bp window) | n/a (`trained_window_bp` 9,198) | log(TPM+1) |
| annotation | async | 1,000–500,000 bp | n/a | de-novo transcripts; sync JSON above 200,000 bp (`x-sync-limit-bp`) is `413 sync_too_large` |

`Recommended mode` is guidance, not a constraint — every task accepts both. Omit `Prefer` for a synchronous `200`; send `Prefer: respond-async` for a `202` plus `GET /v1/tasks/jobs/{job_id}`. The one enforced limit is per operation: where `/v1/openapi.json` publishes `x-sync-limit-bp` on a `POST`, a synchronous JSON request above that length is `413 sync_too_large` — 200,000 bp on `annotation` and 50,000 bp on the composite workflow in contract revision 16. Read the field rather than memorising the numbers. Annotation BED/GFF3 remains synchronous above its JSON cap and can time out; the other five predict tasks have no hard sync cap.

The minimum is published as `minLength` on each task's request schema and enforced
before any model loads. There are **no per-model floors**: a task's floor is the
strictest its models need, and every model stays listed and loadable.

**Floor ≠ regime.** A request above the floor but shorter than the selected
model's `bio_spec.context_window_bp` is accepted and scored — against a window
padded out to the context window. Enhancer is the sharp case: the floor is 50 bp
while the context window is 249 bp, so 50–248 bp is scored mostly on padding.
Compare your length against `context_window_bp` to know whether the model saw
real sequence.
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

## Reading outputs

Narrow on `data.task`. The six tasks declare `data.model`, `data.input`, and
`data.summary`; **summary keys are deliberately outside the stable contract**.
Nested region/window/site records are open objects, so inspect actual records
instead of assuming every record has `name` or `strand`. Preserve input
coordinates and orientation separately. Stable counts live in
`meta.task_specific_counts`, not summary aliases:

| Task | Declared data fields | Declared counts |
|---|---|---|
| promoter | `regions`, `window_details` | `windows_processed`, `regions_found` |
| splice | `sites`, `tracks`, `window_details` | `windows_processed`, `sites_found` |
| enhancer | `windows`, `tracks` | `windows_processed` |
| chromatin | `windows`, `tracks` | `windows_processed`, `total_annotations` |
| annotation | `transcripts` | `transcripts_found` |
| expression | `prediction` | `tss_index`, `scored_window` (schema permits null; check before use) |

## promoter

Sliding-window classification, with promoter regions and individual window scores.
Current public discovery includes human, Drosophila, yeast, and Arabidopsis
models. Check the chosen model's organism and window; the default is human.
A predicted region is a model output, not experimentally established promoter
activity or a transcription start site annotation.

## splice

The default BigBird model is strand-specific. Submit transcript orientation;
reverse-complement a minus-strand locus before scoring. The official contract
warns that wrong-strand input still yields plausible, high-scoring sites.
Neither confidence, count, nor the presence of GT/AG motifs validates orientation.
There is no promised strand field on a site; track orientation caller-side.

`start`/`end` bound a scored BPE **token span**, typically 4–8 bases, with
`token_index` identifying the token. They do not identify a base-resolution
junction. GFF3 exports retain this span semantics. Do not report an invented
single-base donor/acceptor coordinate or treat overlap with a reference junction
as exact localization.

More than **20,000 emitted sites** causes `422 validation_failed`; the service
rejects the request rather than returning a truncated list. The check occurs
during inference, so an accepted input length does not guarantee success.
`details` can contain `record_count`, `maximum_records`, `sequence_length`, and
`threshold` instead of `details.errors`. Avoid threshold zero: the official
limits guide recommends `1e-3` for low-threshold exploration. Increasing a
threshold changes recall; record it and do not equate a filtered list with every
biological splice site. This cap is documented in the guide but not represented
as an `x-` extension or typed detail schema in revision 16.

## enhancer

Current DeepSTARR models target **Drosophila**, returning continuous developmental
and housekeeping activity scores per window. The scores are not calibrated
probabilities or human enhancer evidence. `data.windows` and `data.tracks` are
the declared outputs; summary aliases are display-only.

## chromatin

The current DeepSEA models score 919 ENCODE features, grouped into eight track
categories (DNase, CTCF, Pol2, c-Myc, H3K27ac, H3K27me3, H3K4me1, Other).
The API declares `data.windows` and `data.tracks`; do not promise an unfiltered
919-column matrix. `options.threshold` gates reported labels and
`meta.task_specific_counts.total_annotations` counts reported annotations.

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
wrong `tss_index` scores the wrong window with a `200`. `data.input` echoes only `sequence_name`, `description`, and `tss_index`
in revision 16. Read the submitted length from `meta.sequence_length` and the
window from `meta.task_specific_counts.scored_window`; do not read removed
`data.input.scored_window` or `data.input.submitted_sequence_length` fields.
The exact description text conditions the score: hold it fixed in comparisons.
Canonical transcript selection is a reference convention, not proof of the
biologically active TSS in the assayed cell type.

Both `tss_index` failures come from a whole-model validator and so report at
`loc: ["body"]`, **never** `body.tss_index`. Match on
`error.code == "validation_failed"` — never on `loc`.

## annotation
De-novo gene / transcript structure — transcript intervals and strand, no
reference annotation. **Run it async** (`Prefer: respond-async` is available on
every predict operation; annotation is the one that most often needs it):
submit with
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
`options` both required, and `options.description` required in `FindGenesAndPredictExpressionOptions` in revision 16.
A missing/empty description fails validation. Optional: `annotation_model`,
`expression_model`, `batch_size` (1–128, default 8), `shift_coordinates`.

It cuts a TSS-centred 9,198 bp window per discovered gene, padding with `N` up to
half the window rather than dropping an edge gene — the direct expression route
refuses to pad at all. `meta.task_specific_counts` =
`{genes_found, genes_predicted, genes_skipped}` with
`genes_predicted + genes_skipped == genes_found`; per-gene causes in
`data.expression_predictions[].skip_reason`. Check `skipped` before interpreting
the per-gene `expression` (log(TPM+1)) and `expression_tpm` fields; there is no
required nested `prediction` object on a composite gene record.

Above **50,000 bp** (its `x-sync-limit-bp`) it forces async: a synchronous JSON
request over that size is `413 sync_too_large` with
`error.details = {sequence_length, threshold}`. Retry the same body with
`Prefer: respond-async`. `annotation` carries the same guard at 200,000 bp; no
other predict task publishes one today.

The equivalent by hand is `annotation` to discover genes, then one `expression`
call per gene with that gene's window and `tss_index` — useful when you want
per-gene control, though you then own the TSS-centring the composite does for
you.
