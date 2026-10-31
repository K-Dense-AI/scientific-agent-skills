# Local CLI Reference

All bundled commands use only the Python standard library. They:

- accept explicit UTF-8 JSON, CSV, or Markdown files;
- reject symbolic-link inputs;
- cap file size, records, fields, JSON nodes, and nesting;
- make no network calls;
- read no environment variables or `.env` files;
- perform no dynamic evaluation or pickle loading;
- report issue codes, IDs, and line numbers without echoing manuscript or source text.

Run from the skill directory with Python 3.11 or newer.

## Scaffold

```bash
python3 scripts/scaffold_manuscript.py \
  --output-dir ./draft-workspace \
  --document-id local-draft \
  --study-design randomized_trial \
  --guideline consort-2025
```

The output directory must not exist. The command never overwrites files. Generated
documents are explicitly incomplete and not submission-ready.

## Manifest validation

```bash
python3 scripts/validate_manifest.py manuscript_manifest.json --kind manuscript
python3 scripts/validate_manifest.py source_manifest.json --kind source
python3 scripts/validate_manifest.py source_manifest.json --kind source --require-verified
```

The validator checks structure, IDs, verification gates, confidentiality status, and
required-statement status. It does not read files named inside the manifest.

## Reporting-guideline routing and coverage

```bash
python3 scripts/select_reporting_guidelines.py select --study-design systematic_review
python3 scripts/select_reporting_guidelines.py check reporting_coverage.json
```

Selection and coverage are non-scoring. Open the official guideline after selection.

## Claim and citation audit

```bash
python3 scripts/audit_claims.py manuscript.md claims.csv source_manifest.json
```

Required CSV headers:

```text
claim_id,section,claim_kind,claim_text_sha256,evidence_ids,verification_status,uncertainty,analysis_intent
```

Separate multiple evidence IDs with semicolons in CSV. Use inline Markdown markers:

```text
[claim:C001] [evidence:E001,E002]
```

Use exactly one claim per physical line. The audit checks the SHA-256 digest against
that line after removing `[claim:...]`, `[evidence:...]`, and `[@E...]` markers
and collapsing whitespace.
It also validates source-manifest verification metadata and flags numeric content
without a claim marker. See `evidence_workflow.md` for normalization and limits.

## Numeric and methods-results consistency

```bash
python3 scripts/check_consistency.py consistency_manifest.json
```

The command checks duplicate concepts across sections, units, percentages against
numerators and denominators, sample sizes, evidence IDs, declared methods, outcome
mappings, and confirmatory or exploratory status.

## Reference identifiers and duplicates

```bash
python3 scripts/check_references.py source_manifest.json
```

The command checks local syntax and duplicates for DOI, PMID, PMCID, ISBN, URL, and
normalized title. It never resolves an identifier; a human must compare each value with
the opened source.

## Authorship and disclosure

```bash
python3 scripts/validate_authorship.py authorship.json
```

The command checks human authorship criteria, exact CRediT role names, corresponding
author and guarantor IDs, final approval, declaration-hash syntax, AI disclosure, human
verification, journal-policy review, and authorization gates for restricted material.
Its authorship criteria are ICMJE-style local gates, not all journals' criteria.
Declaration hashes are not compared with manuscript text; manually reconcile the
actual statements. Recorded dates must be valid calendar dates in YYYY-MM-DD form.

## Language, placeholder, and confidentiality lint

```bash
python3 scripts/lint_manuscript.py manuscript.md \
  --manifest manuscript_manifest.json
```

Possible sensitive-content findings are review prompts, not a de-identification
certificate. The linter intentionally fails on unresolved placeholders.

## Exit behavior

- exit `0`: no error-level findings;
- exit `1`: invalid input or one or more error-level findings.

Warnings still require human review. JSON output is deterministic for the same inputs.
