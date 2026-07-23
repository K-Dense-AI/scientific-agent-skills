# Facilitation Workflows and Records

These workflows make a session reproducible without turning facilitation into
an automatic scientific decision. Adapt timing and accessibility needs, but
record adaptations.

## Minimum session record

Create one record with:

- session ID, date, title, focal question, and decision owner;
- facilitator, participant pseudonyms, represented perspectives, missing
  perspectives, and relevant conflicts;
- in-scope/out-of-scope boundaries and constraints;
- information and examples shown before independent generation;
- idea, assumption, cluster, criterion, review, evidence-check, gate, and
  decision-log entries;
- method, timing, anonymization, voting, merge, and stopping rules;
- AI tool/version/purpose when used, without storing sensitive prompt content;
- deviations from the planned process and their reasons.

Use `scripts/session_scaffold.py` to create a deterministic JSON starting
point. It intentionally omits a generated timestamp: provide `--date` when a
date belongs in the record.

## Provenance templates

### Idea

```json
{
  "id": "I001",
  "statement": "A concise candidate research direction.",
  "provenance": {
    "origin": "human",
    "contributor_ids": ["P01"],
    "recorded_stage": "independent",
    "source_refs": [],
    "ai_tool": null
  },
  "assumption_ids": ["A001"],
  "predicted_observations": ["What would be expected if the idea were useful"],
  "uncertainties": ["The main unresolved uncertainty"],
  "evidence_status": "not-checked",
  "status": "candidate"
}
```

Allowed origin labels in the bundled validator are `human`, `ai-assisted`,
`literature-inspired`, `mixed`, and `other`. An origin label documents process;
it does not determine quality or ownership.

### Assumption

```json
{
  "id": "A001",
  "statement": "The measurement reflects the proposed construct.",
  "category": "measurement",
  "status": "untested",
  "test_or_check": "Compare with an orthogonal measure.",
  "owner_id": "P01",
  "evidence_refs": []
}
```

Useful categories include `causal`, `mechanistic`, `measurement`, `sampling`,
`operational`, `statistical`, `feasibility`, `ethical`, and `value`.

### Literature check

```json
{
  "idea_id": "I001",
  "checked_on": "2026-07-23",
  "queries": ["Exact query or protocol identifier"],
  "sources_screened": ["DOI or stable URL"],
  "support": [],
  "challenges": [],
  "search_limits": ["Databases, date, language, or access limits"],
  "status": "search-incomplete",
  "reviewer_id": "P02"
}
```

Do not store copyrighted full text, confidential reviews, credentials, or
personal data in the register.

## 30-minute individual or pair workflow

### Minute 0–5: scope

1. Write one question and one decision the session can inform.
2. List real and assumed constraints separately.
3. Check whether clinical, ethics, safety, dual-use, privacy, or regulatory
   concerns require a different process.

### Minute 5–12: independent generation

- Work silently, even as a pair.
- Generate one idea per record.
- Attach at least one assumption and one uncertainty.
- Do not search or ask an AI system during this first round unless the session
  explicitly studies AI anchoring.

### Minute 12–17: share and expand

- Read ideas without ranking.
- Clarify wording.
- Run a second two-minute private round for additions and contradictions.

### Minute 17–23: cluster and criteria

- Cluster by one declared relation.
- Define three to five criteria with directions and scale anchors.
- Identify any noncompensatory safety or ethics gates.

### Minute 23–28: challenge

- Write one disconfirming observation and one alternative explanation for each
  leading candidate.
- Mark literature work as `not-checked` unless a real search was performed.

### Minute 28–30: log

- Select the next information-gathering action, not a scientific conclusion.
- Record owner, due/revisit condition, and unresolved concerns.

## 60–90 minute facilitated group workflow

### Before the session

- Obtain a neutral focal question from the decision owner.
- Recruit complementary perspectives and identify missing voices.
- Send constraints and definitions, not example solutions.
- Choose an anonymous contribution path.
- Predeclare how ideas are retained, clustered, rated, and escalated.
- Decide what information must not enter shared notes or external tools.

### Opening (10 minutes)

- State purpose, boundaries, and what the session cannot establish.
- Explain the sequence: independent generation, sharing, clustering,
  evaluation, challenge, then next-step logging.
- Ask leaders and sponsors to withhold preferences.
- Invite conflict and accessibility disclosures.

### Independent round (10–15 minutes)

- Same prompt and time for all.
- Require stable idea IDs, assumptions, and uncertainty.
- Allow private submission to the facilitator.

### Round robin and second round (15–20 minutes)

- One item per person per turn; passing is permitted.
- Clarify without advocacy.
- Display all items simultaneously only after initial capture.
- Add a short second private generation round.

### Clustering (10–15 minutes)

- Name the relationship used for each cluster.
- Keep originals visible.
- Log every merge and preserve minority interpretations.
- Do not use lexical similarity as a claim of semantic equivalence.

### Independent evaluation (10 minutes)

- Publish criteria, definitions, directions, and weights first.
- Rate privately; permit uncertainty ranges and abstention.
- Reveal distributions before discussion.

### Challenge and gate (15 minutes)

- Assign each candidate to a non-originator.
- Record falsifiers, alternatives, bias risks, harm/misuse potential, and
  mitigations.
- Route triggered reviews to the responsible office; do not resolve them by
  vote.

### Close (5–10 minutes)

- Log candidate dispositions and dissent.
- Assign literature, feasibility, consultation, or protocol tasks.
- State that any score or rank is provisional.
- Schedule a revisit after evidence checks or external review.

## Asynchronous workflow

Use for distributed teams or when status differences make live contribution
difficult.

1. Freeze the prompt, definitions, scope, and deadline.
2. Collect independent entries without showing the current pool.
3. Release a de-identified pool at the same time to all participants.
4. Collect clarification requests and second-round ideas.
5. Publish a merge log and let originators contest merges.
6. Collect ratings and rationales independently.
7. Return distributions, dissenting reasons, and missing responses.
8. Collect revisions once; more rounds require a stated stopping rule.
9. Record attrition and whether late participants saw different information.

If iterative anonymous judgment and convergence are the actual objective, use
a documented Delphi design rather than calling any online survey “Delphi.”

## Literature-aware reopening workflow

This pattern reduces premature literature anchoring while keeping ideation
connected to evidence.

1. Complete and freeze an independent human-first idea set.
2. Run a documented search for each shortlisted idea.
3. Separate located evidence, interpretations, and unknowns.
4. Record search limits and contradictory or null findings.
5. Give all participants the same bounded evidence packet.
6. Run a new private round asking for revisions, alternatives, and
   disconfirming studies.
7. Link new ideas to their parent IDs without overwriting the initial record.

Never label an idea “novel” solely because no result appeared in one search.

## Leader and authority controls

- The most senior person speaks after independent capture.
- The facilitator is not the scientific decision owner when avoidable.
- Ask for ratings before discussion and show distributions.
- Provide a confidential dissent channel.
- Separate factual corrections from preference statements.
- Record who can veto and on what grounds.
- Ask an external reviewer to challenge ideas favored by the sponsor.
- Do not force consensus; retain “no consensus” as a valid outcome.

## Accessibility and inclusion

- Offer spoken, typed, asynchronous, and private contribution modes.
- Define jargon and distribute materials in accessible formats.
- Allow processing time and breaks.
- Do not infer silence as agreement.
- Compensate or acknowledge stakeholder and lived-experience contributions
  under applicable policy.
- Record whose participation was constrained by language, time zone,
  technology, hierarchy, or access.

## Sensitive and unpublished work

Before the session, classify what may be recorded and shared. Minimize detail:

- use abstracted mechanisms instead of controlled operational parameters;
- use participant IDs instead of personal identifiers;
- store unpublished ideas only in approved systems with appropriate access;
- do not paste unpublished manuscripts, grant reviews, patient information,
  proprietary methods, security-sensitive details, or controlled data into
  public AI or collaboration services;
- follow contractual, institutional, community, and Indigenous data-governance
  obligations.

If safe abstraction would make the question meaningless, stop and use an
approved closed process.

## Decision-log entry

```json
{
  "decision_id": "D001",
  "date": "2026-07-23",
  "owner_id": "P01",
  "candidate_ids": ["I001", "I002"],
  "decision": "Advance I001 to a bounded literature review; no study approved.",
  "rationale": "Reason linked to criteria and qualitative review.",
  "dissent": ["P02 preferred I002 because ..."],
  "uncertainties": ["Feasibility estimate has not been checked."],
  "gate_status": {
    "ethics": "not-assessed",
    "biosafety_or_dual_use": "not-applicable",
    "regulatory": "not-assessed"
  },
  "next_action": "Run and document the search protocol.",
  "revisit_when": "Evidence check and methods consultation are complete."
}
```

The log should make the decision reconstructable, not merely defensible after
the fact.
