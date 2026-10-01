# Clinical Decision-Support References

Version 2.0 is the breaking safety redesign dated 2026-07-23. It replaces
the former recommendation-oriented templates, references, and scripts with
offline research-evaluation and governance artifacts.

## Boundary

These references support aggregate or synthetic research evaluation, methods documentation, evidence profiles, privacy review, and governance traceability. They do not support diagnosis, treatment recommendations, dosing, triage, alarms, bedside use, autonomous decisions, or patient-specific output.

No reference or script establishes regulatory authorization, HIPAA compliance, clinical validity, or fitness for live use. Route care decisions to licensed professionals using validated and appropriately authorized systems.

## Navigation

| File | Purpose |
|---|---|
| `safety_and_scope.md` | Refusal rules, escalation, and intended-use language |
| `regulatory_and_governance.md` | FDA CDS/AI, ONC HTI-1, and ICH context |
| `evidence_profiles.md` | Human GRADE evidence-profile workflow |
| `study_reporting.md` | STROBE/RECORD, TRIPOD+AI, CONSORT-AI, SPIRIT-AI, DECIDE-AI, STARD-AI, REMARK, and PROBAST+AI |
| `cohort_evaluation.md` | Aggregate cohort reporting and disclosure-aware tables |
| `survival_analysis.md` | Estimand-led time-to-event planning |
| `model_biomarker_evaluation.md` | Aggregate validation, calibration, uncertainty, and subgroup review |
| `privacy_and_disclosure.md` | HHS de-identification methods and output controls |
| `decision_logic_traceability.md` | Research/governance logic matrices |
| `sources.md` | Authoritative source ledger checked 2026-09-30 |
| `security_validation.md` | Baseline remediation, scan results, and accepted LOW findings |

## Assets

All assets are JSON skeletons. They contain no patient rows or real identifiers:

- `artifact_intended_use_template.json`
- `evidence_profile_template.json`
- `aggregate_model_evaluation_template.json`
- `aggregate_cohort_table_template.json`
- `survival_analysis_plan_template.json`
- `decision_logic_traceability_template.json`
- `deidentification_checklist_template.json`

Every template includes intended use, prohibited uses, limitations, data level, and human-review fields.

## Scripts

The standard-library scripts read bounded local JSON and produce bounded local JSON, Markdown, or CSV:

- `validate_cds_artifact.py`
- `evidence_profile_check.py`
- `model_biomarker_evaluation.py`
- `cohort_table_generator.py`
- `survival_plan_validator.py`
- `decision_logic_traceability.py`
- `deidentification_checklist.py`

They do not use networks, API keys, environment variables, dynamic evaluation, serialization formats that execute code, LLMs, or image services.

## Method Selection

Use the study design and evaluation stage—not the presence of “AI” in a title—to select a framework. Reporting checklists are minimum disclosure guidance. Risk-of-bias tools require informed human judgments. GRADE certainty is outcome-specific and cannot be inferred from text.

For an actual protocol, product, regulated submission, certified health IT module, or data release, obtain review from the relevant methodologist, privacy official, legal/regulatory counsel, governance owner, and domain experts.

