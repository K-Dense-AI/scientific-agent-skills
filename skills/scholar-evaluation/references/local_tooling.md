# Local Deterministic Tooling

## Security properties

Every bundled script:

- uses only the Python standard library;
- reads bounded local `.json` or `.csv` files;
- rejects symbolic-link inputs, duplicate JSON keys, excessive depth or size,
  non-finite numbers, unknown schema fields, and common private-application
  fields;
- uses fixed schemas and never executes supplied text;
- has no network, model, credential, environment-file, dynamic-code,
  executable-serialization, or child-process behavior;
- writes only minimized JSON reports and refuses to overwrite by default; and
- does not copy evidence excerpts or raw source documents.

Inputs are limited to 2 MiB, JSON depth 20, 25,000 structure nodes, 50 rubric
criteria, 50 comparison evaluations, and 20,000 agreement rows. Outputs are
limited to 2 MiB.

Use an authorized local directory. Keep private source documents in the
institution's records system and reference them with opaque local identifiers.

## Templates

- `assets/rubric_template.json` — valid structure, but deliberately records
  content validity as not established.
- `assets/evaluation_template.json` — structurally valid all-missing example.
- `assets/evidence_manifest_template.json` — synthetic local-reference records.
- `assets/process_checklist_template.json` — fail-closed unconfirmed controls.
- `assets/ratings_template.csv` — pseudonymous synthetic agreement data.

Copy a template into an authorized working directory before editing it. Do not
replace synthetic identifiers with names or contact information.

## 1. Rubric schema validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_rubric.py \
  --rubric assets/rubric_template.json
```

The validator checks:

- fixed intended use and scholarly-work unit;
- complete prohibited-use list;
- construct, boundaries, limitations, and provenance;
- content-validity status and reference;
- bounded scale and complete anchors;
- unique criteria and weights summing to one;
- absence of common scored proxy measures;
- required rater training, calibration, agreement, separately recorded
  inter-rater reliability status, and drift controls; and
- committee, conflict, appeal, accessibility, data-protection, subgroup, and
  review-cycle governance.

A rubric can be structurally `valid` while warning that content validity is not
documented. Structural validity is not psychometric validity.

## 2. Bounded descriptive scoring

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/calculate_scores.py \
  --rubric assets/rubric_template.json \
  --evaluation assets/evaluation_template.json \
  --output /tmp/scholar-score.json
```

The evaluation contains one entry for every criterion:

```json
{
  "criterion_id": "method_design",
  "status": "rated",
  "score": 3,
  "uncertainty": 0.5,
  "evidence_ids": ["EVIDENCE-SYNTHETIC-METHOD"],
  "rationale_ref": "LOCAL-RATING-RATIONALE-METHOD"
}
```

For `missing` or `not_applicable`, `score` and `uncertainty` must be null and
`evidence_ids` must be empty. A local rationale reference remains required.

The output reports weighted contributions, coverage, missing and
not-applicable weight, normalized score, and a bounded uncertainty range. It
contains no quality label, threshold, decision, or recommendation.

## 3. Evidence traceability

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_traceability.py \
  --rubric assets/rubric_template.json \
  --evaluation assets/evaluation_template.json \
  --evidence assets/evidence_manifest_template.json
```

The checker verifies that:

- manifest, evaluation, work, and classification identifiers match;
- every evidence identifier is unique;
- every rated evidence reference resolves;
- evidence is linked to the criterion that cites it;
- source and access types are allowed; and
- evidence is available and verified.

It reports identifiers, paths, and counts only. It never opens or copies the
referenced source.

## 4. Weight sensitivity and rank instability

Provide two to 50 evaluation JSON files for distinct scholarly works:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/weight_sensitivity.py \
  --rubric assets/rubric_template.json \
  --evaluation /tmp/work-a-evaluation.json \
  --evaluation /tmp/work-b-evaluation.json \
  --delta 0.2 \
  --output /tmp/weight-sensitivity.json
```

For each criterion, the script multiplies its weight by `1-delta` and
`1+delta`, renormalizes all weights to one, and recomputes descriptive scores.
It reports:

- every scenario and its floating-point weights;
- each work's score and coverage per scenario;
- score ranges;
- base ordinal order and explicit tied pairs; and
- pairwise order changes.

Comparisons use unrounded scores with absolute tolerance `1e-9`; displayed
scores and ranges are rounded to six decimals and can appear equal. This is a
computational tolerance, not a threshold of meaningful scientific difference.
Different criterion-status patterns generate a comparability warning.

The base order is included solely to detect instability. It is not a ranking
recommendation and must never be used for people or high-impact decisions.

## 5. Inter-rater agreement summaries

The CSV header must be exactly:

```text
evaluation_id,work_id,rater_id,criterion_id,status,score
```

Use pseudonymous rater identifiers. One `evaluation_id` identifies a frozen
work revision and evaluation round; all raters in that round use the same ID.
Different rounds need different IDs. One evaluation ID cannot name two works.
Ratings from separate rounds are never paired or overwritten. Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/summarize_agreement.py \
  --rubric assets/rubric_template.json \
  --ratings assets/ratings_template.csv \
  --output /tmp/agreement-summary.json
```

For each criterion and overall, the report includes:

- pair observations;
- exact agreement rate;
- within-one-scale-step agreement rate;
- mean absolute difference;
- overlap, rated, missing, and not-applicable counts.

Summaries pool all rater pairs within each work/round/criterion; a round with
three rated raters contributes three pairs, and a round with two contributes
one. Histograms avoid materializing the quadratic pair list. Missing and
not-applicable statuses are excluded from score-pair denominators; omitted CSV
rows have unknown status. Minimum-rater shortfalls are reported per rated
round/criterion, even if the dataset has enough distinct raters overall.

Rater identifiers are not emitted. These are descriptive agreement summaries,
not chance-corrected reliability, generalizability, validity, or fairness
evidence.

## 6. Bias and process checklist

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_process.py \
  --process assets/process_checklist_template.json
```

The template is intentionally unconfirmed and therefore does not pass. Complete
it only from documented local records. The checker covers:

- qualified committee and training;
- conflicts and recusal;
- appeal and correction;
- accessibility and accommodations;
- purpose limitation, minimization, access, retention, and output controls;
- construct, provenance, content evidence, rater quality, agreement,
  inter-rater reliability review, uncertainty, missingness, traceability, and
  sensitivity;
- stakeholder, disciplinary, subgroup, and protected-attribute safeguards;
- no automation, person ranking, or decision recommendation; and
- drift, unintended-consequence, and periodic review.

`high_impact_use: true` or any unconfirmed decision control blocks the process.
The checklist does not authorize a prohibited use.

## 7. Report scaffold

Generate a minimized scaffold:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/generate_report_scaffold.py \
  --rubric assets/rubric_template.json \
  --evaluation assets/evaluation_template.json \
  --output /tmp/developmental-report-scaffold.json
```

Optional companion reports:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/generate_report_scaffold.py \
  --rubric assets/rubric_template.json \
  --evaluation /tmp/work-a-evaluation.json \
  --traceability /tmp/traceability.json \
  --agreement /tmp/agreement-summary.json \
  --sensitivity /tmp/weight-sensitivity.json \
  --process /tmp/process-check.json \
  --output /tmp/developmental-report-scaffold.json
```

Agreement and sensitivity companions must list the current work/evaluation in
`evaluation_records`; regenerate reports from older skill versions before using
them as companions. Identifier checks do not detect content edited in place:
freeze inputs and regenerate all checks after changes. The process checklist
is a separate attestation and is not cryptographically bound to a work.

The scaffold includes:

- construct and provenance status;
- descriptive scores and uncertainty;
- empty local-reference slots for evidence, strengths, limitations, and
  improvement options;
- minimized quality-assurance statuses; and
- fixed limitations and human-review fields.

It does not draft findings from source documents or issue a decision.

## Exit behavior

- exit `0`: requested calculation or validation completed successfully;
- exit `2`: invalid, blocked, incomplete, failed traceability, or unsafe input.

Errors contain only stable codes and JSON paths, never supplied values. Use
`--force` only when replacing a known local report.
