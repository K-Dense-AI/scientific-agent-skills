---
name: research-weave
description: Builds claim-level evidence maps to prioritize reading for scoped scientific research questions. Reconstructs intellectual lineages, assesses converging support and evidence dependence, aligns conflicting findings, and connects papers to a specific research decision. Use for reading prioritization or project positioning; not a bare search, single-paper critique, formal systematic review, or novelty verdict.
license: MIT
compatibility: Analytical guidance works with supplied sources. Live discovery needs host-provided search and source access; the optional evidence checker requires Python 3.9+ standard library only.
metadata:
  version: "1.0"
  skill-author: "NeuraLiying"
  source: "https://github.com/NeuraLiying/research-weave-skill"
---

# Research Weave

Help the researcher decide **which papers deserve attention and which research judgments they can change**. Organize around questions and claims rather than flattering paper summaries. A useful result may recommend an old diagnostic paper over a celebrated new method, or conclude that an attractive gap disappears after aligning conditions.

## Start from a decision

Extract the research question, intended decision, target setting, known papers, and constraints from the conversation or supplied artifacts. State a concise working interpretation and proceed. Ask a focused question only if competing interpretations would produce materially different searches; continue useful work meanwhile.

Describe the target operationally: task/population, mechanism, comparator, outcome, resources, and assumptions. Unknowns remain unknown. If only a broad area is supplied, provisionally map its main branches and identify what needs narrowing; do not invent a project mechanism.

| Mode | Use | Working budget, adjustable |
|---|---|---|
| Scout | Orientation or limited reading time | Screen roughly 15–25 candidates; inspect decision-bearing sections in 4–6 |
| Map | Default research positioning | Screen roughly 30–60; inspect 8–12 deeply; expand selectively |
| Update | Existing map plus new papers | Reuse IDs and evidence; investigate changed claims and dependencies |

These are attention budgets, not coverage guarantees or quotas. Report actual counts, access limits, and omitted branches. This workflow does not establish systematic or exhaustive coverage.

## 1. Search across time and viewpoints

Read [evidence-method.md](references/evidence-method.md) for retrieval, quality appraisal, and reading decisions.

Build query channels for the problem and historical aliases; mechanism and evaluation; counterevidence/null results; and a neighboring field with a plausible transferable mechanism. Retrieve historical anchors without a recent-year cutoff, then current work through the actual search date. A date filter on new papers does not silently erase foundations needed to interpret them.

Use available academic search, primary proceedings, publisher pages, or supplied corpora. Verify identity and inspect primary text before accepting a claim. Model recall and reviews supply leads, not verified findings. If tools fail, record failed channels, try a complementary source, and deliver a bounded or corpus-only map.

Follow references backward from diverse anchors and citations forward where available. Search for reproductions, challenges, extensions, and explanations of decision-bearing claims. Inspect different research groups or methodological branches when possible. Preserve useful low-citation, negative, and older work. Merge versions of the same study without erasing which version supplied evidence.

Log queries, exclusions, access failures, and repairs as work proceeds. If an important seed is missed, diagnose vocabulary/source/time filters and rerun the repaired search; inserting the seed alone does not close the blind spot.

## 2. Extract claims before judging papers

Inspect each shortlisted paper's method, relevant result/table/proof, assumptions, and limitations. Abstract-only records remain provisional. Split a headline into claims that may differ in strength.

Each decision-bearing claim needs:

- A source link/version, precise locator, and faithful observation. Include numbers, denominators, uncertainty, comparator, and cost when relevant; mark missing reporting explicitly.
- Conditions: task, model/population, feedback/data access, compute, metric, and other assumptions needed to interpret it.
- Separate **source observation**, **authors' interpretation**, and **our inference**. The third is not an observed finding.
- Evidence strength with a reason, main validity threat, and transfer limits.
- A research role: `fact`, `mechanism`, `method`, `evaluation`, `boundary`, `counterevidence`, or `analogy`; the decision affected and transfer assumption.

Keep credibility, historical influence, and project utility separate. Venue, citations, rhetorical confidence, and suspected AI authorship do not establish quality. A useful hypothesis or analogy is not factual support.

## 3. Weave a claim network and historical account

Use papers for provenance and **claims as the analytical nodes**. Relations are `supports`, `contradicts`, `bounds`, `depends_on`, `imports`, and `supersedes`. Explain each edge, cite its evidence, and label it source-supported or analyst hypothesis. Shared keywords or a citation alone are insufficient.

Track shared datasets, code, models, protocols, and reused results. Distinct papers and authors do not automatically provide independent confirmation. Unknown independence stays unknown; source volume is not a vote.

Explain historical transitions by what changed: problem definition, capability, mechanism, evaluation, or exposed limitation. Calling a work a turning point requires a traceable downstream adoption/challenge or other consequence. Chronology establishes order, not influence. Include competing branches, bridges, and dead ends when relevant. Sparse evidence can produce a sparse graph; do not invent connections.

## 4. Assess converging support

For each decision-bearing proposition, group supporting claims and the strongest counterevidence. Report supporting paper count separately from evidence-family count and confirmed independent tests. More credible, independent, applicable evidence can strengthen support, especially across teams, methods, and conditions. Repeated reports of one result do not add independent confirmation; unknown independence stays unknown.

Before counting a contribution as direct support, align the proposition's scope and quantifier with the evidence. A well-supported local result does not establish a universal proposition; indirect or scope-limited clues belong in candidate evidence for that broader proposition. Record the transfer explicitly.

Describe what converges and under which conditions. Assess breadth together with validity, effect/uncertainty, directness, and counterevidence; do not compute confidence by counting papers or averaging arbitrary quality scores. One sound counterexample can defeat a universal claim while leaving a narrower conditional claim intact. Record proposition-level synthesis as convergent, conditional, contested, or insufficient, with reasons.

## 5. Investigate contradictions

Read [contradictions.md](references/contradictions.md) when findings appear to conflict. Compare scoped claims, not titles.

Align definitions, tasks, comparators, model versions, data/feedback access, compute, selection, metrics, and uncertainty. Classify tensions as `comparable_conflict`, `scope_mismatch`, `inconclusive`, or `not_opposed`. Missing comparability is not equality. Failure to find significance is not proof of no effect.

For consequential unresolved tensions, give competing explanations, a test with controlled variables and distinct predicted outcomes, and an outcome that would make the proposed gap disappear. Search for later resolutions before promoting a frontier. Contradiction is a question to investigate, not proof of novelty or automatic motivation. Zero credible contradictions is valid.

## 6. Prioritize attention and locate the project

Build a short, ordered reading queue. Each recommendation names the section to read, question answered, decision potentially changed, and why it earns attention over alternatives. Actions are `deep_read`, `targeted_read`, `verify_access`, `defer`, and `exclude`, with reasons. Avoid recommending every candidate equally. Balance foundations, competitors, negative/boundary evidence, and bridges according to the question, not fixed slot counts.

Place the project: inherited assumptions → established evidence → unsupported step → closest competing explanation → next useful observation. Distinguish established limitations, untested settings, and speculative mechanisms. Without a concrete project, locate candidate branches instead of inventing its contribution.

After covering relevant branches and a counterevidence search, expand while evidence changes the queue, a consequential claim, or a tension. Normally stop after two expansions yield no such change, or at the stated budget; record which reason applied and residual blind spots. Saturation inside searched channels is not completeness.

## Deliver and check

Follow [output-contract.md](references/output-contract.md). Default to a concise report, reusable `evidence.json`, and search/screening log in one output directory. For small conversational requests, keep traceability inline without forcing files. Match the user's language.

Lead with what to read and what can be concluded. Add a small claim graph when useful; distinguish hypothetical edges visually and explain direction. Cite sources near claims. Updates preserve earlier conclusions and record what changed them.

For saved evidence run:

```bash
python3 <skill-dir>/scripts/check_evidence.py <output-dir>/evidence.json
```

The checker catches reference/provenance errors, not source truth. Manually reopen primary locations behind the strongest conclusions, top priorities, and claimed contradictions. Check at least one weak/excluded near-match to ensure real discrimination. Downgrade unsupported conclusions rather than filling gaps with plausible text.


## Examples

- "I am deciding whether a tool-free revision loop is worth its inference cost. Map the strongest evidence and counterevidence, compare feedback access and budget, and choose three papers to read with a diagnostic that could overturn the motivation."
- "These two papers report opposite effects. Check whether their tasks, model versions, comparators and uncertainty are aligned before calling this a contradiction."
- "Update my evidence map after a corrected paper changes its result. Preserve the old version and identify which propositions and reading priorities change."

The workflow is self-contained. Search tools provide candidates; the claim and proposition ledger supplies the comparison contract. Existing literature-review and scientific-critical-thinking workflows remain useful for their review and appraisal tasks.
