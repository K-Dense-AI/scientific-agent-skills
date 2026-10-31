# Local Tool Contracts

All bundled tools are deterministic Python 3.11+ standard-library CLIs. They make no network, model, image, subprocess, environment-variable, dynamic-code, or pickle calls.

## Shared safety behavior

- Inputs: local JSON, CSV, or Markdown only
- Maximum input size: 4 MiB
- Maximum CSV rows: 5,000
- UTF-8 only; NUL bytes rejected
- Symlink inputs and outputs rejected
- Duplicate JSON keys and CSV headers rejected
- Unknown schema fields rejected by JSON validators
- Existing outputs are not replaced unless `--force` is explicit
- JSON and Markdown outputs are written atomically with owner-only permissions where supported
- Reports contain IDs, counts, rule codes, and line numbers—not raw manuscript, review, claim, title, author, or reference prose

Exit codes:

- `0`: structurally valid or completed
- `1`: a validly parsed audit is blocked or has rule errors
- `2`: malformed input, unsafe path, unsupported field, or CLI validation error

Run tools from the skill directory or use absolute script paths.

## Intake validator

```bash
python3 scripts/validate_review_intake.py \
  assets/review_intake_template.json
```

Purpose:

- Confirm documented authorization and human accountability
- Record role, competence areas and limits, conflicts, target-venue policy, and review model
- Enforce local-only processing, no external service use, no data reuse, and a deletion/retention record
- Gate approved AI assistance on venue policy, permission, and disclosure

The bundled template is intentionally blocked until the human completes the controls.

Top-level JSON fields:

- `schema_version`: `2.0`
- `review_id`: safe local identifier, not a manuscript title
- `material`: status and sensitive-data flag
- `authorization`: basis and documented permissions
- `reviewer`: capacity, accountability, competence, and conflicts
- `venue_policy`: checked status, review model, confidential-note channel
- `ai_use`: policy, plan, permission, disclosure
- `handling`: local-only, external-service, reuse, retention controls
- `scope`: manuscript type, requested focus, limits, specialist needs

The report validates declarations, not their truth.

`reviewer.conflict_status` accepts `not_assessed`, `none_identified`, `disclosed_to_editor`, `editor_cleared`, or `unresolved`. Disclosure alone does not clear a conflict: `disclosed_to_editor` blocks until an editor actually clears participation. The validator cannot verify that clearance.

## Reporting-guideline selector and coverage audit

Selection only:

```bash
python3 scripts/select_reporting_guidelines.py \
  assets/study_profile_template.json
```

Selection plus coverage:

```bash
python3 scripts/select_reporting_guidelines.py \
  assets/study_profile_template.json \
  --coverage assets/reporting_checklist_template.csv
```

Profile fields:

- `schema_version`: `2.0`
- `profile_id`
- `study_types`: identifiers such as `randomized_trial`
- `report_kind`: `results`, `protocol`, `abstract`, or `data_release`
- `features`: for example `ai_based`, `ai_intervention`, `large_language_model`
- `domains`: for example `health`, `genomics`, `proteomics`

Coverage columns:

- `guideline_id`
- `item_id`: aggregate main item number for guidelines with a known main count
- `status`: `reported`, `partly_reported`, `not_reported`, `not_applicable`, `not_assessed`
- `location`: required for reported or partly reported items
- `rationale`: required for not-applicable items

The catalog is `assets/reporting_guidelines.json`, reviewed on the date embedded in that file; source-specific verification limits are in `assets/source_ledger.csv`. It does not fetch live updates. The output deliberately has no percentage or quality score.

For an AI trial protocol use `study_types: ["randomized_trial"]`, `report_kind: "protocol"`, `features: ["ai_intervention"]`, and `domains: ["health"]`; this selects SPIRIT 2025 and SPIRIT-AI 2020. For an LLM development, tuning, prompt-engineering, or evaluation study use `study_types: ["llm_study"]`, `report_kind: "results"`, `features: ["large_language_model"]`, and `domains: ["health"]`. Add `prediction_model` only if that design also applies. Abstracts have different checklists; the bundled catalog has no abstract checklist and a no-match result does not mean no guideline exists.

Main-item rows are an aggregate navigation record. `coverage_record_complete` means those row IDs are present, even if all are `not_assessed`; it does not certify coverage of subitems or a completed review.

## Claim–evidence matrix validator

```bash
python3 scripts/validate_claim_evidence.py \
  assets/claim_evidence_matrix_template.csv
```

Columns:

- `claim_id`
- `location`
- `claim_type`
- `claim_summary`: input-only; never echoed
- `evidence_ids`: semicolon-delimited local IDs
- `support_level`: `supported`, `partly_supported`, `unsupported`, `not_assessed`
- `alignment_issue`: direction, magnitude, population, outcome, timepoint, causal language, scope, uncertainty, selective reporting, other, or none
- `limitation`: input-only; never echoed
- `requested_action`: input-only; never echoed

Rules include:

- Supported claims need evidence IDs and no declared alignment issue.
- Partly supported claims require evidence and an issue code; a missing requested action is a warning that still needs human resolution.
- Unsupported claims need an issue code.
- Claim IDs must be unique.

The tool does not determine whether evidence is true or sufficient.

## Statistics and reproducibility checklist

```bash
python3 scripts/audit_statistics_reproducibility.py \
  assets/statistical_reproducibility_template.json
```

The JSON contains:

- Checklist and study-design IDs
- Specialist-review declaration
- Core item records with category, applicability, status, evidence locations, note, and requested action

Core areas:

- Question/estimand alignment
- Unit, independence, sample size, allocation, and blinding
- Inclusion/exclusion, missing data, and data handling
- Prespecification, method alignment, assumptions, multiplicity, and dependence
- Effect estimates, uncertainty, denominators, outcomes, and harms
- Data/material access, code/environment, and provenance
- Ethics/governance, claim interpretation, and selective reporting

The tool requires the core item IDs but permits additional safe IDs. It reports gaps and specialist-review triggers without a score.

## Citation/reference consistency audit

The Markdown must use Pandoc-style citation keys:

```markdown
The synthetic method is described elsewhere [@ref-synthetic-2026].
Several sources may be grouped [@ref-one; @ref-two].
```

Run:

```bash
python3 scripts/audit_citations.py \
  local-manuscript.md \
  assets/citation_references_template.csv
```

Reference CSV columns:

- `reference_id`
- `title`
- `authors`
- `year`
- `doi`
- `url`
- `verification_status`: `verified_primary`, `verified_secondary`, or `not_verified`

The audit finds:

- Citation keys without reference rows
- Reference rows not cited
- Cited references not marked verified
- References without DOI or URL
- Malformed citation syntax

It validates DOI/URL shape only. It does not resolve identifiers, search the web, verify existence, or determine whether a reference supports a claim.

The parser is a lightweight bracket scanner, not Pandoc. Use single-line groups such as `[@ref-one; @ref-two]` with ASCII letter-leading keys up to 96 characters containing letters, digits, `.`, `_`, `:`, or `-`. Full Pandoc also supports other key characters, braced keys, author-in-text citations, and other constructions that this tool does not support. Multiline groups are not supported; code examples, links, escaped text, or other bracketed `@` text can produce false matches. Review these cases separately using the [official Pandoc citation syntax](https://pandoc.org/MANUAL.html#citation-syntax); a clean report is not proof that every citation was found.

## Review scaffold generator

The intake must pass first:

```bash
python3 scripts/generate_review_scaffold.py \
  completed-intake.json \
  -o private-review.md
```

The generator:

- Reads `assets/review_scaffold_template.md`
- Interpolates only safe intake identifiers
- Never reads or embeds manuscript text
- Separates comments to authors from confidential editor notes
- Provides structured major/minor comment fields
- Includes human-accountability and no-editorial-decision warnings

It refuses unresolved intake controls and implicit overwrite.

## Tone and actionability lint

```bash
python3 scripts/lint_review.py private-review.md
```

Required headings:

- `# Comments to authors`
- `# Confidential comments to editor`

Structured comment headings:

- `### Major comment M1`
- `### Minor comment m1`

Each comment must contain non-placeholder values for:

- `Location`
- `Observation`
- `Evidence or criterion`
- `Why it matters`
- `Requested action`

The linter flags:

- Missing or reversed author/editor channels
- Editor-only markers in the author channel
- Unresolved scaffold placeholders
- A narrow lexicon of abusive or personal language
- Role impersonation and editorial-decision phrases
- Missing actionability fields
- Claims of executed analysis that need provenance

Lexical lint has false positives and false negatives. Human review remains required.

## Private output examples

All JSON-reporting CLIs accept:

```bash
-o local-report.json
```

To replace an existing output deliberately:

```bash
--force
```

Do not place outputs in a synced or shared directory unless the authorization and venue policy permit it. Delete or retain inputs, drafts, and reports according to the documented review policy.
