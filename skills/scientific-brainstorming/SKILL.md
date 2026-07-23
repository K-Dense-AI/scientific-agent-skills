---
name: scientific-brainstorming
description: Facilitates evidence-aware scientific ideation with independent generation, structured discussion, explicit assumptions, transparent evaluation, adversarial review, and decision logs. Use for early-stage research brainstorming or prioritizing candidate directions; hand off empirical validation, study design, ethics or regulatory review, and clinical questions to appropriate experts or skills.
license: MIT
compatibility: Core guidance works in any Agent Skills-compatible host. Optional bundled CLIs require Python 3.11+ and use only the standard library; they make no network or LLM calls and require no credentials.
metadata:
  version: "1.1"
  skill-author: "K-Dense Inc."
---

# Scientific Brainstorming

## Purpose and boundaries

Use this skill to create, organize, challenge, and transparently prioritize
candidate research directions. Treat every output as a **proposal**, not a
finding. Creativity methods can alter participation and idea yield, but no
method universally improves originality, usefulness, or scientific validity.
The evidence base and its limits are summarized in
`references/sources.md`.

Keep these activities separate:

- **Ideation** creates questions, mechanisms, alternatives, or study concepts.
- **Evidence assessment** checks what reliable literature and data support.
- **Hypothesis validation** requires observations, predictions, suitable
  designs, analyses, and independent scrutiny; brainstorming cannot validate a
  hypothesis.
- **Ethics, biosafety, dual-use, regulatory, and institutional review** require
  the relevant authorized reviewers. A brainstorm is never approval.
- **Clinical advice** requires qualified clinicians and patient-specific
  context. Do not turn research ideas into diagnosis or treatment guidance.

For an observation-led testable hypothesis, hand off to
`hypothesis-generation`. For study architecture, use `experimental-design`;
for sample size, `statistical-power`; for existing evidence,
`literature-review`; and for analysis, `statistical-analysis`.

## Operating rules

1. Label claims as **idea**, **assumption**, **prediction**, **located
   evidence**, or **decision**. Never blur these categories.
2. Generate independently before exposing participants to other people's or
   AI-generated ideas. Face-to-face turn-taking can block production, and
   examples can anchor later output.
3. Preserve minority views, negative evidence, uncertainty, and abstentions.
   Consensus is not truth and vote counts are not effect sizes.
4. Record provenance without exposing confidential, personal, controlled, or
   unpublished information.
5. Define evaluation criteria and directions before scoring. Keep raw ratings,
   reasons, ranges, and disagreement visible.
6. Search the literature **after an initial independent round** when practical,
   then deliberately reopen ideation. This reduces early anchoring without
   mistaking an incomplete search for a research gap.
7. Do not automatically select a “winner.” Scores are traceable decision aids;
   qualitative judgment, uncertainty, feasibility, and ethics gates remain
   controlling.

## Reproducible workflow

### 1. Scope the session

Write one focal question and record:

- purpose, audience, decision owner, and time horizon;
- in-scope and out-of-scope topics;
- constraints that are real, assumed, negotiable, or unknown;
- current knowledge, unresolved observations, and prohibited outputs;
- whether human participants, animals, clinical care, sensitive data,
  pathogens, controlled technologies, or environmental release could be
  implicated.

If the request seeks patient-specific care, evasion of oversight, harmful
optimization, or operationally enabling dual-use details, stop ideation and
route to the appropriate professional or institutional process.

### 2. Diversify perspectives deliberately

Invite relevant methodological, domain, implementation, statistical, safety,
ethics, stakeholder, and lived-experience perspectives. Diversity is not a
guarantee of creativity: explain whose perspective is represented, missing, or
structurally disadvantaged. Use accessible participation modes and
pseudonymous participant IDs where appropriate.

The facilitator should disclose conflicts, avoid offering a preferred answer
first, prevent senior members from dominating, and ask leaders to contribute
after the independent round.

### 3. Generate independently

Give everyone the same neutral prompt, constraints, and fixed time window.
Participants write ideas privately and in parallel before discussion. For each
idea, capture:

- a stable ID and one-sentence statement;
- contributor ID(s) and stage (`independent`, `discussion`, or `post-check`);
- origin (`human`, `AI-assisted`, `literature-inspired`, `mixed`, or `other`);
- assumptions, predicted observations, uncertainties, and possible
  disconfirming evidence;
- source identifiers for literature-inspired ideas and tool/purpose disclosure
  for AI assistance.

Do not show example solutions before this round unless examples are necessary;
if they are, record them as potential anchors.

### 4. Share without immediate evaluation

Use round-robin or pooled silent sharing. Clarify wording without advocacy.
Permit a private or anonymous channel. Ask each participant what is missing,
what contradicts the dominant framing, and which idea became less obvious
after hearing the group.

### 5. Cluster structurally

Group ideas by an explicit relation such as shared outcome, mechanism,
population, scale, or method. Keep original IDs and text. Record merges and
splits. Similar wording is not proof of semantic equivalence; retain distinct
ideas when their assumptions, intervention, population, or predictions differ.
See `references/facilitation_workflows.md`.

### 6. Define transparent criteria

Before rating, define each criterion, direction, scale anchors, evidence
needed, conflicts, and explicit weights. Common dimensions include:

- potential information gain and discriminating predictions;
- relevance to the scoped question;
- originality relative to the checked literature, not merely to the room;
- feasibility, resources, and reversibility;
- methodological rigor and vulnerability to bias;
- ethics, safety, equity, dual-use, and regulatory burden;
- value if the result is null or contradicts the favored mechanism.

Use ranges or confidence labels where assessors are uncertain. Do not hide
vetoes inside an averaged score. See `references/idea_evaluation.md`.

### 7. Run adversarial review

Assign a reviewer who did not originate each shortlisted idea. Ask:

- What observation would make this idea wrong or uninformative?
- Which alternative explanation fits the same predicted result?
- What hidden dependency, measurement failure, confounder, or selection effect
  could dominate?
- Are authority, anchoring, group loyalty, publication incentives, or an
  attractive technology driving preference?
- Could this cause harm, worsen inequity, expose sensitive information, or
  enable misuse?

Record the response, mitigation, residual uncertainty, and whether the idea was
revised—not just pass/fail.

### 8. Check literature and evidence

Search authoritative databases, primary studies, methods guidance, negative
results, and adjacent fields. Verify every citation at its source. For each
idea, record query/date, sources screened, evidence for and against, and search
limits. Use statuses such as `not-checked`, `search-incomplete`,
`support-located`, `challenge-located`, or `mixed`.

Absence from a bounded search does not establish novelty, and supportive
literature does not validate a new mechanism. Reopen one short independent
generation round after the evidence check.

### 9. Apply feasibility, rigor, and ethics gates

Before advancing an idea, identify the appropriate domain review:

- For biomedical work, consider rigor of prior research, robust design,
  relevant biological variables, and resource authentication. When NIH policy
  applies, sex as a biological variable should be considered from the research
  question through design, analysis, and reporting; justify a single-sex scope
  with relevant evidence.
- Route human-subjects, animal, biosafety, data-governance, export-control,
  clinical, environmental, and other regulated work to the relevant office.
- Screen life-science and enabling-technology ideas for dual-use or misuse
  potential early. Current U.S. oversight is evolving; consult the institution
  and current agency policy rather than relying on a static checklist.
- Do not upload sensitive, unpublished, proprietary, controlled, or personal
  information to an external AI service.

An ethics or feasibility concern may require redesign, controlled handling, or
stopping. A high creativity score never overrides a gate.

### 10. Decide and log

The accountable human decision owner records:

- candidates considered and criteria/weights used;
- raw ratings, uncertainty ranges, dissent, abstentions, and sensitivity
  results;
- literature and review dates;
- gate outcomes and required approvals;
- decision, rationale, rejected alternatives, unresolved risks, owner, and
  revisit trigger.

Label the next action correctly: further search, consultation, simulation,
pilot design, protocol development, preregistration, or no action. If a
confirmatory study is planned, preregister hypotheses and analysis decisions
before outcomes are known; report later deviations and exploratory work
transparently. Preregistration improves transparency but is not peer review,
ethical approval, or proof of validity.

## Bias and failure controls

- **Production blocking:** private parallel generation before oral discussion.
- **Anchoring and design fixation:** no leader answer or AI examples until the
  independent round; reopen generation after evidence review.
- **Authority and status effects:** leader-last sharing, anonymous input,
  independent ratings, and visible dissent.
- **Groupthink:** assign a genuine alternative-generation role, invite outside
  review, and document rejected options. Treat “groupthink” as a family of
  risks, not a single universally established diagnosis.
- **Evaluation apprehension:** separate contribution from attribution where
  possible; critique ideas, not contributors.
- **Premature convergence:** fixed divergence window followed by an explicit
  transition and predeclared criteria.
- **False precision:** use anchored scales, uncertainty ranges, sensitivity
  analysis, and narrative review.
- **Research-gap inflation:** record search boundaries and use “no direct
  evidence located,” not “never studied.”
- **AI hallucination or homogenization:** human-first ideation, provenance,
  independent verification, multiple non-AI perspectives, and comparison for
  suspiciously repeated frames. See `references/responsible_ai.md`.

## Optional local CLIs

The scripts are deterministic, standard-library utilities. They do not call a
network service, LLM, or scientific database and do not make scientific
conclusions.

```bash
python scripts/session_scaffold.py --help
python scripts/validate_register.py --help
python scripts/evaluate_matrix.py --help
```

Create a session register:

```bash
python scripts/session_scaffold.py \
  --session-id "microbiome-01" \
  --title "Microbiome mechanism ideation" \
  --question "Which mechanisms could explain the scoped observation?" \
  --participant P01 --participant P02 \
  --output session.json
```

Validate structure and provenance:

```bash
python scripts/validate_register.py session.json --output validation.json
```

Calculate a fully disclosed weighted matrix from CSV, including score intervals
and one-at-a-time weight sensitivity:

```bash
python scripts/evaluate_matrix.py scores.csv \
  --config criteria.json \
  --weight-delta 0.10 \
  --output matrix.json
```

Outputs refuse symlinks and existing files unless `--force` is explicit; inputs
and collection sizes are bounded. The validator checks structure, not truth.
The matrix preserves qualitative review and uncertainty and leaves
`decision` null. Input formats and interpretation are documented in
`references/idea_evaluation.md`.

## Reference index

- `references/brainstorming_methods.md` — evidence-calibrated method selection,
  nominal groups, Delphi, structured elicitation, and creative prompts.
- `references/facilitation_workflows.md` — ready-to-run individual, group, and
  asynchronous session protocols plus provenance templates.
- `references/idea_evaluation.md` — criteria, scoring formula, uncertainty,
  sensitivity analysis, gates, and decision logs.
- `references/responsible_ai.md` — accountable AI assistance, confidentiality,
  hallucination, homogenization, disclosure, dual-use, and integrity.
- `references/sources.md` — dated primary studies and official guidance
  consulted for this version.
