# Preregistration, Registered Reports, and Open Science

## Purpose

Preregistration records a time-stamped plan before the relevant data are collected or analyzed. Its main value is making planned and data-dependent work distinguishable.

Preregistration does not:

- guarantee a valid design or analysis;
- prevent all researcher degrees of freedom;
- make a hypothesis true;
- forbid exploration or justified adaptation;
- replace ethics, safety, data, or regulatory review;
- require public release of restricted information.

## What to preregister

### Administrative

- title and project ID;
- accountable owner and roles;
- registration date and repository;
- study status and prior access to relevant data;
- conflicts, funding, and sponsor roles.

### Question and candidates

- observation and provenance;
- research question and claim type;
- candidate hypotheses and mechanisms;
- rivals and alternative explanations;
- causal estimands where applicable;
- boundary conditions and uncertainty.

### Predictions and controls

- prediction IDs and parent candidates;
- conditions, measurements, expected patterns, and timing;
- falsifiers and indeterminate outcomes;
- discriminating expectations for rivals;
- null hypotheses;
- positive, procedural, and negative controls.

### Design

- population/system and sampling;
- experimental and analysis units;
- allocation, randomization, concealment, and masking;
- interventions/exposures and comparators;
- inclusion, exclusion, attrition, and stopping;
- sample-size or precision rationale;
- outcomes and measurement timing;
- ethics, safety, data, and regulatory status.

### Analysis

- analysis populations;
- transformations and data exclusions;
- models, contrasts, estimators, and effect/summary measures;
- uncertainty intervals or other inferential summaries;
- missing-data and intercurrent-event handling;
- multiplicity;
- assumptions and diagnostics;
- sensitivity and robustness analyses;
- rules for interpreting support, challenge, and indeterminacy.

### Transparency

- data, code, materials, and metadata plans;
- restrictions and controlled-access process;
- software/environment versions;
- AI/tool use;
- deviation log and reporting plan.

## Timing and prior access

State what had already occurred:

- no data collected;
- data collected but target outcomes unseen;
- data available but analyst blinded;
- summary statistics viewed;
- exploratory analysis already performed;
- existing dataset reused.

When data have already informed the plan, label the work transparently and use independent data, a held-out set, or a new replication for confirmatory testing where feasible.

## Confirmatory versus exploratory

### Confirmatory

- planned before checking the target result;
- tied to specified outcomes and analyses;
- reported whether favorable, unfavorable, or null.

### Exploratory

- generated after or while viewing data;
- useful for discovery;
- labeled as data-dependent;
- treated as a source of future predictions.

Do not call exploratory work “post hoc confirmation.”

## HARKing

Kerr defined HARKing as presenting a post hoc hypothesis as if it were a priori. Prevent it by:

- preserving dated versions;
- separating planned and unplanned analyses;
- reporting all prespecified outcomes and tests;
- documenting when each candidate was generated;
- not rewriting unexpected results as predictions;
- seeking independent replication.

## Deviations

Preregistration is a plan, not a prison. For every material deviation record:

- date;
- affected section and IDs;
- original plan;
- change;
- reason;
- who made the decision;
- whether the target result was known;
- likely effect on bias or interpretation;
- whether the original analysis is still reported.

Do not silently replace the registration. Preserve the original and append amendments.

On OSF, use the documented registration-update workflow when available and retain its change justification. Distinguish an updated registration from an editable project and inspect the version history; a later update does not make a data-informed prediction prospective. Consult the [current OSF registration guide](https://help.osf.io/article/330-welcome-to-registrations) for the selected registry's options.

## Registered Reports

Registered Reports add journal peer review before results are known:

1. Stage 1 protocol submission;
2. review of question, methods, and analysis;
3. in-principle acceptance under the journal’s conditions;
4. study conduct;
5. Stage 2 review focused on adherence, justified deviations, and interpretation.

Check the current journal policy. In-principle acceptance is not ethics approval, funding, regulatory authorization, or assurance of a favorable result.

## Intervention trials

For randomized intervention hypotheses:

- use current registration requirements for the applicable jurisdiction, funder, and venue;
- use SPIRIT 2025 for protocol reporting;
- align objectives, estimands, outcomes, harms, intervention details, statistical methods, and data sharing;
- use CONSORT 2025 for completed-trial reporting;
- report important changes, including non-prespecified outcomes or analyses.

The preregistration scaffold in this skill is generic and is not a trial-registry submission, SPIRIT checklist, protocol, statistical analysis plan, or regulatory document.

## Reproducibility and replicability

Use the National Academies definitions:

- **reproducibility:** obtaining consistent computational results with the same data, code, methods, and analysis conditions;
- **replicability:** obtaining consistent results in a new study addressing the same question with new data.

Plan for:

- stable identifiers and version control;
- code and environment capture;
- provenance and decision logs;
- independent replication;
- exact and conceptual replication;
- boundary-condition and transport tests;
- publication of null and challenging results.

Non-replication does not automatically imply misconduct or that the original study was invalid. Differences can reveal heterogeneity, measurement limitations, context, or sampling variation.

## Open-science limits

Use [TOP 2025](https://www.cos.io/initiatives/top-guidelines) for current transparency planning rather than treating the original 2015 policy as the latest framework. For this hypothesis package, record separately whether the registration, protocol, analysis plan, materials, code, data, and reporting checklist are disclosed, shared and cited, or independently certified. Sharing a plan does not establish independent verification or certify its scientific validity. Apply the target journal or funder's actual policy.

“Open” does not override:

- participant consent and privacy;
- Indigenous or community data governance;
- contractual or intellectual-property restrictions;
- export controls;
- biosafety and dual-use review;
- endangered-species or sensitive-location protections;
- security-sensitive vulnerabilities.

Share the maximum responsibly permitted, not the maximum technically possible. Use metadata, synthetic examples, controlled access, or redacted protocols when full release is unsafe.

## Scaffold generation

Generate a local draft only after the hypothesis record validates:

```bash
python3 scripts/generate_preregistration_scaffold.py \
  local-hypothesis-record.json \
  -o local-preregistration.md
```

The result:

- is marked as an unregistered draft;
- labels the input record's update date without claiming a generation or registration timestamp;
- includes every candidate without ranking;
- carries unresolved placeholders;
- requires human review and repository-specific completion;
- does not submit, register, upload, or transmit anything.
