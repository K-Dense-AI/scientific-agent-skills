# Evaluation Framework

## What ScholarEval is—and is not

The paper currently referenced by this skill is Moussa et al.,
[*ScholarEval: Research Idea Evaluation Grounded in
Literature*](https://arxiv.org/abs/2510.16234), arXiv:2510.16234v2,
revised 2026-02-28.

The preprint describes an experimental retrieval-augmented system for evaluating
research ideas on:

- **soundness:** whether existing literature empirically supports proposed
  methods; and
- **contribution:** how an idea advances beyond prior work along comparison
  dimensions.

It reports a 117-idea, four-discipline dataset, coverage comparisons with
expert-annotated review points, and a user study. Those studies evaluate that
framework. They do **not** validate the generalized rubric in this skill as a
psychometric instrument, establish stable score meaning across disciplines, or
authorize use in consequential decisions.

As of the dated source review, arXiv and the official project repository were
the verified primary publication records. No peer-reviewed publication status
was verified. Cite it as an arXiv preprint unless a later primary record is
checked. See `references/source_ledger.md`.

## Relationship to this skill

This skill borrows the useful discipline of:

1. defining what is being assessed;
2. grounding judgments in traceable literature and work evidence;
3. separating soundness-like questions from contribution-like questions; and
4. auditing whether generated feedback covers expert concerns.

It does not reproduce ScholarEval's model pipeline, prompts, retrieval system,
dataset, or reported metrics. The bundled scripts do not call ScholarEval,
search the web, invoke a model, or evaluate private documents.

The template is a **locally governed developmental rubric**. Its default
construct is:

> Traceable support for a scholarly work's claims and methods: the degree to
> which a work states a bounded question, situates its contribution, uses
> fit-for-purpose methods, aligns analysis with claims, and documents
> transparent and responsible practices using traceable evidence.

This construct must be reviewed and adapted by relevant disciplinary experts.

## Five template criteria

### 1. Question and scope

Review:

- a clear, bounded question or objective;
- significance rationale appropriate to the field and work stage;
- assumptions, boundary conditions, and success conditions; and
- feasibility of the proposed or reported scope.

Do not treat fashionable topics, institutional affiliation, or venue
expectations as evidence of significance.

### 2. Literature grounding and contribution claim

Review:

- source-selection or search boundaries;
- engagement with relevant and contrary evidence;
- traceable primary sources for comparison claims;
- comparison dimensions used to define the contribution; and
- limits on novelty or advancement claims.

Failure to find prior work does not establish novelty. Search coverage varies by
database, language, date, indexing, terminology, discipline, and access.

### 3. Method and design fit

Review:

- alignment between question, design, data or materials, and method;
- sampling, corpus, inclusion, exclusion, and measurement choices;
- alternatives and design rationale;
- validity threats, bias, and mitigation;
- ethics, consent, privacy, safety, and governance; and
- detail sufficient for appropriate checking or reproduction.

Use discipline-specific reporting and methods standards. Do not reward
complexity for its own sake.

### 4. Analysis, claims, and uncertainty

Review:

- fit of analytical methods to data and inferential target;
- assumptions and diagnostics;
- robustness, sensitivity, negative cases, and alternative explanations;
- appropriate statistical or qualitative uncertainty;
- alignment between results and claims; and
- explicit limits on generalization and causal language.

The rubric's `uncertainty` value is a rater-supplied bounded judgment range. It
is not a sampling confidence interval, posterior interval, or standard error.

### 5. Transparency, integrity, and reproducibility

Review:

- complete reporting, provenance, and stable evidence locators;
- protocols, registrations, data, code, materials, and justified restrictions;
- negative, null, and contradictory findings where relevant;
- conflicts, limitations, corrections, and research-integrity safeguards;
- accessible communication; and
- transparent attribution of contributions.

Open practice is not an absolute requirement when privacy, consent, safety,
security, Indigenous data governance, commercial constraints, or other
legitimate restrictions apply. Assess whether restrictions are justified and
whether safe access or metadata alternatives are provided.

## Scale semantics

The template uses an ordinal 0–4 scale:

- **0 — observed lack of support**
- **1 — limited support**
- **2 — mixed support**
- **3 — substantial support**
- **4 — strong support**

These are evidence anchors, not labels of a person or universal levels of
research quality. The rubric defines criterion-specific anchors. Raters must use
the anchor text, not intuition about what a number “usually means.”

Do not convert the score to:

- accept/reject or publication readiness;
- exceptional/poor labels;
- predicted success or impact;
- person ranking; or
- funding, hiring, promotion, tenure, admissions, award, or discipline advice.

## Rating statuses

Each criterion has exactly one status:

- `rated`: score, uncertainty, evidence identifiers, and rationale reference
  are required;
- `missing`: evidence needed for assessment is absent or unavailable; score and
  uncertainty are null; or
- `not_applicable`: the criterion does not apply to this work under a documented
  rationale; score and uncertainty are null.

A rated zero must cite inspected evidence demonstrating lack of support or a
contradiction. An inaccessible section or unassessed evidence is `missing`, not
zero. Do not encode missing or not-applicable as zero.

## Transparent score math

Numeric averaging additionally assumes meaningful spacing between anchors and
compensatory tradeoffs between criteria. Ordinal labels alone do not justify
these assumptions. Use a composite only when the local rubric owner documents
them for the stated developmental purpose; otherwise retain criterion findings.

For rated criteria \(R\), score \(s_i\), and predeclared weight \(w_i\):

\[
\text{descriptive score}
=
\frac{\sum_{i \in R} w_i s_i}
     {\sum_{i \in R} w_i}
\]

The score report separately provides:

- total, applicable, rated, missing, and not-applicable weight;
- coverage of applicable weight;
- each weighted contribution;
- the normalized descriptive score; and
- a bounded aggregation of criterion uncertainty ranges.

The uncertainty aggregation is not a confidence interval. Normalization does
not make incomplete evaluations comparable. Review missingness before looking
at any score.

## Rubric development record

Before replacing `content_validity_status: not_established`, document:

1. the exact discipline, work type, language, stage, and intended use;
2. construct definition and excluded constructs;
3. literature and standard review used to draft criteria;
4. disciplinary expert and stakeholder selection;
5. systematic mapping of criteria to construct components;
6. cognitive interviews or rater response-process evidence;
7. accessibility and translation review;
8. pilot sample and evidence-availability analysis;
9. revisions, dissent, unresolved gaps, and approval; and
10. the limits of any validity claim.

Rubric provenance must identify the version, owner role, source identifiers,
review date, and content-evidence reference.

## Rater protocol

At minimum:

1. select qualified raters with relevant disciplinary and methods expertise;
2. disclose conflicts and recuse where required;
3. train on construct boundaries, anchors, evidence rules, missingness,
   accessibility, bias, and privacy;
4. calibrate on synthetic or authorized examples;
5. rate independently before discussion;
6. record evidence identifiers and uncertainty;
7. summarize agreement and investigate systematic disagreements;
8. resolve only through documented evidence and rationale, not forced averaging;
9. monitor drift over time; and
10. retrain, revise, or suspend the rubric when evidence warrants.

The bundled agreement script compares raters only within the same criterion,
work, and evaluation round. It reports exact agreement, within-one-step agreement,
and mean absolute difference, pooling rater pairs. More heavily rated rounds
contribute more pairs; pairs sharing a rater/work are dependent observations. Those summaries do not replace a
design-appropriate reliability analysis. The rubric therefore separately
records `inter_rater_reliability_status` and
`inter_rater_reliability_ref`; the template leaves reliability not established.

## Evidence traceability

Each rated criterion must point to one or more entries in the evidence manifest.
Each entry records:

- pseudonymous evidence identifier;
- linked criterion identifiers;
- source type;
- local stable locator;
- local claim reference;
- access status; and
- verification status.

Never place an excerpt or raw private document in the manifest. Keep source
content in the authorized source system.

## Weight sensitivity and order instability

Weights are value judgments. Predeclare and justify them. Run
`scripts/weight_sensitivity.py` before interpreting a composite.

The script increases and decreases one weight at a time and renormalizes the
weights. It reports score ranges and whether pairwise ordinal relationships
among scholarly works change, using unrounded scores and a stated numerical
tolerance. Tied pairs are explicit. Different applicable or rated criterion sets
limit comparability even at 100% applicable coverage. Instability is evidence that an apparent order
depends on contestable weights.

The output must not be used to rank people or decide a high-impact outcome.
Even stable ordering does not establish validity.

## Interpretation template

For each criterion, qualified reviewers should record:

1. status and evidence references;
2. observed evidence;
3. interpretation against the anchor;
4. score and uncertainty, if rated;
5. missing or not-applicable rationale;
6. disciplinary and stage context;
7. strengths and limitations; and
8. non-prescriptive improvement options.

Conclude with construct, provenance, coverage, agreement, sensitivity, bias,
privacy, accessibility, and validity limitations—not a decision recommendation.
