---
name: consciousness-council
description: Structures a multi-perspective council exercise for decisions, research trade-offs, and creative challenges. Simulates thinking archetypes, separates evidence from assumptions and values, and synthesizes a conditional recommendation. Use when the user requests a council, panel, devil's advocate analysis, "mind council", or deliberate comparison of perspectives on a difficult choice.
license: MIT license
metadata:
  version: "1.2"
  skill-author: AHK Strategies (ashrafkahoush-ux)
  last-reviewed: "2026-09-30"
---

# Consciousness Council

A structured exercise that simulates several thinking archetypes, each emphasizing different assumptions and priorities, then synthesizes their perspectives. These are generated viewpoints from one system, not independent experts or independent evidence. Label factual claims, assumptions, and value judgments separately; verify consequential factual claims against external sources.

## When to use

Use for a requested comparison of competing priorities or assumptions, including research planning decisions. The output is a decision aid: a conditional recommendation, unresolved questions, and a next step. It does not establish scientific validity by agreement or by the number of perspectives.

This skill runs within the current conversation. It has no bundled code, service API, credentials, or MindBook connection; use the host's available research tools when factual verification is needed. Do not claim that it creates hosted sessions, stores persistent memories, or contacts real experts.

## Before deliberation

1. State the decision, feasible options (including postponement when relevant), constraints, and the user's objective. Use supplied context; state material missing information as an assumption or a question.
2. Create a short evidence brief: **given facts**, **externally verified facts with sources**, **assumptions**, **unknowns**, and **value judgments**. All perspectives use this same brief.
3. Verify facts that could change the recommendation using original sources or supplied data. If verification is unavailable, keep the conclusion conditional and identify what must be checked; a simulated Empiricist is not a source.
4. Select a response budget: quick (3 perspectives), standard (4–6), or deep (6). These counts organize the output; they are not validated accuracy settings.

## How It Works

The Council has three phases:

### Phase 1 — Summon the Council

Based on the user's question, select 4–6 Council Members from the archetypes below unless the user requests another configuration. Choose lenses that examine different assumptions, constraints, or values. Agreement supported by the evidence is a valid outcome.

**The 12 Archetypes:**

| #   | Archetype          | Thinking Style                         | Asks                                         | Blind Spot                                |
| --- | ------------------ | -------------------------------------- | -------------------------------------------- | ----------------------------------------- |
| 1   | **The Architect**  | Systems thinking, structure-first      | "What's the underlying structure?"           | Can over-engineer simple problems         |
| 2   | **The Contrarian** | Inversion, devil's advocate            | "What if the opposite is true?"              | Can be contrarian for its own sake        |
| 3   | **The Empiricist** | Data-driven, evidence-first            | "What does the evidence actually show?"      | Can miss what can't be measured           |
| 4   | **The Ethicist**   | Values-driven, consequence-aware       | "Who benefits and who is harmed?"            | Can paralyze action with moral complexity |
| 5   | **The Futurist**   | Long-term, second-order effects        | "What does this look like in 10 years?"      | Can discount present realities            |
| 6   | **The Pragmatist** | Action-oriented, resource-aware        | "What can we actually do by Friday?"         | Can sacrifice long-term for short-term    |
| 7   | **The Historian**  | Pattern recognition, precedent         | "When has this been tried before?"           | Can fight the last war                    |
| 8   | **The Empath**     | Human-centered, emotional intelligence | "How will people actually feel about this?"  | Can prioritize comfort over progress      |
| 9   | **The Outsider**   | Cross-domain, naive questions          | "Why does everyone assume that?"             | Can lack domain depth                     |
| 10  | **The Strategist** | Game theory, competitive dynamics      | "What are the second and third-order moves?" | Can overthink simple situations           |
| 11  | **The Minimalist** | Simplification, constraint-seeking     | "What can we remove?"                        | Can oversimplify complex problems         |
| 12  | **The Creator**    | Divergent thinking, novel synthesis    | "What hasn't been tried yet?"                | Can chase novelty over reliability        |

**Selection heuristic:** Match the question type to the most productive tension:

- **Business decisions** → Strategist + Pragmatist + Ethicist + Futurist + Contrarian
- **Technical architecture** → Architect + Minimalist + Empiricist + Outsider
- **Personal dilemmas** → Empath + Contrarian + Futurist + Pragmatist
- **Creative challenges** → Creator + Outsider + Historian + Minimalist
- **Ethical questions** → Ethicist + Contrarian + Empiricist + Empath + Historian
- **Strategy/competition** → Strategist + Historian + Futurist + Contrarian + Pragmatist

These are starting points — adapt based on the specific question. The goal is to expose decision-relevant trade-offs and evidence gaps without a quota for disagreement or consensus.

### Phase 2 — Deliberation

Each Council Member delivers their perspective in this format:

```
🎭 [ARCHETYPE NAME]

Position: [One-sentence stance]

Reasoning: [2-4 sentences explaining their logic from their specific lens]

Basis: [Which given/verified facts, assumptions, or values support the position]

Key Risk They See: [The danger others might miss]

Decision Check: [Evidence or a changed constraint that would alter this position]
```

**Critical rules for deliberation:**

- Seek substantive differences in assumptions, evidence, and values, but do not manufacture factual disagreement. When evidence supports agreement, record it and examine remaining uncertainty or decision trade-offs.
- Distinguish the lenses even when they reach the same recommendation; avoid repeating one argument in different voices.
- The Contrarian tests the strongest assumption behind the leading option and may conclude that it withstands scrutiny. Do not invent contrary evidence.
- Keep each member's contribution focused and sharp. Depth over breadth.

### Phase 3 — Synthesis

After all members speak, deliver:

```
⚖️ COUNCIL SYNTHESIS

Points of Convergence: [Shared conclusions, with their evidence and assumptions; agreement alone is not a confidence signal]

Core Tension: [The decision-relevant trade-off, or state that no substantive disagreement remains]

Open Question: [An overlooked issue or missing evidence; say if none was identified]

Recommended Path: [Conditional recommendation, next step, and what would change the choice]

Confidence Level: [Qualitative High / Medium / Low with reasons, tied to a specific claim; no percentage inferred from votes or rhetoric]

One Question to Sit With: [The question the user should keep thinking about after this session]
```

Before delivering the synthesis, check that every consequential factual claim traces to the evidence brief, each recommendation respects the constraints, and uncertainties are still visible. A critical unverified premise prevents a high-confidence recommendation. Distinguish confidence in the proposed next step from confidence in the eventual outcome. Record supported agreement and unresolved disagreements; do not resolve them by majority vote.

This is a qualitative review by the agent, not an automated validation gate or proof that the premises are true. Report unresolved checks explicitly.

## Council Configurations

The user can customize the Council:

- **"Quick council"** or **"fast deliberation"** → Use 3 members, shorter responses
- **"Deep council"** or **"full deliberation"** → Use 6 members, extended reasoning
- **"Add [archetype]"** → Include a specific archetype
- **"Without [archetype]"** → Exclude a specific archetype
- **"Custom council: [list]"** → User picks exact members
- **"Anonymous council"** → Use neutral labels until synthesis. This is a presentation option; no bias-reduction effect is established for this skill.
- **"Devil's advocate mode"** → Stress-test the intuitive choice with plausible failure cases and label hypothetical premises. Retain facts that survive the challenge.
- **"Rounds mode"** → After initial positions, members respond to each other for a second round

See [advanced configurations](references/advanced-configurations.md) for domain mixes, optional editorial scoring, and bounded multi-round or synthesis-only output.

## What Makes a Good Council Question

The Council works best on questions where:

- There's genuine uncertainty or trade-offs
- Multiple valid perspectives exist
- The user is stuck or going in circles
- The stakes are high enough to warrant multi-angle thinking
- The user's own bias might be limiting their view

The Council adds less value on:

- Pure factual questions with clear answers
- Questions where the user has already decided and just wants validation
- Trivial choices with low stakes

If the question seems too simple for a full Council, say so — and offer a quick 2-perspective contrast instead.

## Tone and Quality

- Write each archetype's voice with enough distinctiveness that the user could identify them without labels.
- The Synthesis should feel like genuine integration, not just a list of what each member said.
- "Core Tension" is the most important part of the synthesis — it should name the real trade-off the user faces.
- "One Question to Sit With" should be genuinely thought-provoking, not generic.
- Preserve substantive trade-offs without staging conflict. Evidence-based agreement is useful too.

## Worked example: pilot or full study

**User:** "Quick council: should we run a pilot or begin the full experiment? We have ten weeks and 100 budget units. The pilot costs 20 units and takes two weeks; the full study costs 80 units and takes eight weeks. We don't know whether our assay is reproducible."

This is a fictional, manually worked illustration, not an experimentally validated outcome. The costs, durations, and uncertainty are given facts within the scenario. Assume sequential scheduling, no overlap, and that the pilot would assess the assay conditions needed for the study. Protecting interpretable results is a stated decision priority, not an empirical finding.

| Perspective | Position and basis | Risk and decision check |
| --- | --- | --- |
| Empiricist | Prefer the pilot because assay reproducibility is unknown. Define fit-for-purpose acceptance criteria before observing pilot results. | A pilot using different conditions may not answer the study's question. Change the position if relevant existing validation resolves that uncertainty. |
| Pragmatist | The pilot followed by the full study exactly uses 100 units and ten weeks under the stated assumptions. | There is no contingency for repeats or delays. Check whether the deadline and budget allow a staged decision. |
| Contrarian | Challenge whether this pilot can change the go/no-go decision; if it cannot, redesign it before spending 20 units. | A reassuring pilot could still leave the key uncertainty unresolved. Specify what result would stop or modify the full study. |

**Synthesis:** All three lenses support resolving the assay uncertainty; this agreement adds no independent evidence. The core tension is learning before commitment versus leaving no schedule or budget margin. The open question is whether the pilot's acceptance criteria can answer the reproducibility question under study conditions. Recommend defining those criteria and a stop rule before committing to either path. Confidence is medium in that next step and low in successful completion of the full study within the current limits. One question to resolve: "Which pilot result would actually change our decision?"

**Sensitivity check:** If the pilot costs 25 units, the sequential plan costs 105 and is infeasible without a scope or budget change. If relevant assay validation already exists, revisit whether a new pilot is needed. These changes should alter the recommendation even if every archetype initially agreed.

## Evidence and limits

This specific prompt workflow and its optional scoring have not been benchmarked for decision accuracy. Multi-agent studies do not directly validate several voices generated in one conversation. [Baltaji et al. (2024)](https://arxiv.org/abs/2405.03862) report persona inconsistency and conformity in their tested collaborations. A [September 2026 preprint by Ferreira et al.](https://arxiv.org/abs/2609.35875) reports that debate did not reliably beat budget-matched sampling in its small-model setting. These bounded findings motivate checking evidence and assumptions; they do not establish a universal benefit or failure of council exercises.

## Attribution

Originally created by [AHK Strategies](https://www.ahkstrategies.net/), with inspiration from [MindBook](https://themindbook.app/). The [current MindBook FAQ](https://themindbook.app/help), reviewed 2026-09-30, distinguishes its 12-archetype Council Chamber from a separate six-mind Mind Council. This repository's standalone exercise retains its own 3/4–6/6-perspective configurations; it is not a client for either hosted feature.
