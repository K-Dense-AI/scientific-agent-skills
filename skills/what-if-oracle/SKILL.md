---
name: what-if-oracle
description: Supports structured what-if scenario analysis for research planning, experimental contingencies, and scientific project decisions. Explores favorable, reference, adverse, wild-card, contrarian, and second-order scenarios with explicit assumptions, evidence, and decision triggers. Use to stress-test a research plan under uncertainty; scenario narratives do not estimate causal effects or calibrated forecast probabilities.
license: CC BY-NC-SA 4.0
metadata:
  version: "1.3"
  last-reviewed: "2026-10-01"
  skill-author: AHK Strategies (ashrafkahoush-ux)
  upstream: https://github.com/ashrafkahoush-ux/claude-consciousness-skills
  research-doi: 10.5281/zenodo.18736841, 10.5281/zenodo.18807387
---

# What-If Oracle — Research Scenario Planning

Explore a bounded set of possible futures before committing research resources. The output is a scenario comparison, an evidence ledger, and a contingency plan. It does not cover the full possibility space or establish that a narrated mechanism will occur.

The six branch prompts and **0·IF·1** mnemonic come from the upstream What-If framework. Treat the mnemonic as a framing aid: a potential change (**0**), a stated condition (**IF**), and a resulting scenario (**1**). It is not a scientific law or a computational model.

The author's [What-If Paradigm](https://doi.org/10.5281/zenodo.18736841) and [Unified Theory of Digital Consciousness](https://doi.org/10.5281/zenodo.18807387) are catalogued by Zenodo as preprints. Their deposit and DOI establish provenance, not forecasting accuracy or empirical validation of this workflow.

## When to use

Use for questions such as:

- What if sample attrition is higher than planned?
- What if a method fails to transfer to a new instrument, cohort, or site?
- What if a key reagent, dataset, or measurement becomes unavailable?
- Which research option remains feasible under competing hypotheses or resource constraints?

Keep the analysis attached to a scientific decision. This is not a general business, personal advice, or software architecture skill. If the question requires an intervention effect, a power calculation, or a numerical simulation, identify the required design/model and evidence; do not manufacture those results with scenario prose.

No package, API endpoint, credential, or network connection is required for the qualitative workflow. Verify current external facts when they matter, or label the analysis as based only on supplied material. For research-specific prompts and a worked example, see [references/scenario-templates.md](references/scenario-templates.md).

## Phase 1 — Frame the question and evidence

Write one operational question containing:

- **Decision and comparator:** what can be changed, and what happens under the current plan?
- **Perturbation:** the main variable, magnitude, units, and any coupled changes. Do not assume other variables remain fixed when the mechanism links them.
- **Horizon and system:** population, site, protocol, and time window to which the answer applies.
- **Outcome and constraints:** measurable success/failure criteria, budget, capacity, and irreversible consequences.
- **Baseline:** observations and their dates, separated from assumptions and desired targets.

For example: "If the usable-sample fraction is 60% rather than the planned 80%, can a batch of 100 samples deliver 80 usable samples this month, and which contingency should we prepare?" Both fractions may be planning assumptions until supported by data.

Use the user's supplied framing when sufficient. State reasonable working assumptions and proceed; ask for a missing fact only when it materially changes the analysis.

Maintain a short evidence ledger: claim, source or data version/date, relevant population/protocol, uncertainty, and status (**observed**, **model-derived**, or **assumed**). Record conflicting evidence. An LLM-generated rationale is not an additional observation or an independent expert assessment.

## Phase 2 — Explore scenario branches

Select distinct scenarios suited to the question, usually four to six. A short screening can use favorable, reference, and adverse scenarios. The labels below are exploration lenses, not mutually exclusive outcomes or a probability distribution.

| Lens | What to examine | Scientific boundary |
| --- | --- | --- |
| **Ω Favorable (best case)** | Favorable conditions within justified bounds | Not a proven upper limit; specify whose outcome improves |
| **α Reference case** | A stated baseline or central set of assumptions | Call it "likely" only if comparative evidence supports that ranking |
| **Δ Adverse (worst case)** | Plausible failures, including dependent failures | Not a proven lower limit or the worst imaginable outcome |
| **Ψ Wild card** | A concrete disruption outside the main assumptions | Do not claim to enumerate unknowable events or assign a rarity from the label |
| **Φ Contrarian** | An alternative to a dominant hypothesis | Evaluate supporting and disconfirming evidence; disagreement alone is not support |
| **∞ Second order** | Downstream effects, delays, feedback, or changed behavior | Can occur within any other scenario; mark untested mechanisms as hypotheses |

Retain important shared drivers and correlations across branches. Avoid implausible combinations created by independently toggling quantities that share a cause. Use descriptive scenario names in the final output so favorable/adverse labels do not substitute for evaluation.

## Phase 3 — Analyze and challenge each branch

Use a compact record:

```text
Scenario: [name and lens]
Condition and horizon: [operational definition]
Assumptions: [including dependencies and boundary conditions]
Evidence: [source/data version, supporting and conflicting observations]
Mechanism: [conditional narrative; identify untested causal links]
Consequences: [outcomes, units, range, and relevant time points]
Likelihood: [not estimated, or justified estimate with method and uncertainty]
Evidence confidence: [reasoned assessment, separate from event likelihood]
Discriminating observation: [what would weaken this scenario or favor another]
Trigger and response: [observable measure, threshold, review time, owner, action]
Residual risk: [what this response does not resolve]
```

For quantitative claims, show inputs, units, method, assumptions, and whether the calculation was executed. Distinguish variation in future outcomes from uncertainty in the inputs or model. Sensitivity checks should vary decision-critical assumptions, including plausible joint changes, and identify where the preferred action changes.

For causal claims, specify the intervention, comparator, population, outcome, and horizon. An observational association or a changed prediction is not by itself an intervention effect. State the identification assumptions and supporting design; for observational adjustment these include consistency, exchangeability, and positivity. A scenario can motivate a controlled pilot or measurement, but cannot replace that evidence. See the author's maintained [Causal Inference: What If](https://miguelhernan.org/whatifbook), especially Chapters 1–3, for this distinction.

## Phase 4 — Compare responses and define the next check

Compare candidate actions against the scenarios using a table of outcome, cost, feasibility, reversibility, and unresolved assumptions. Include the current plan. State which objective or trade-off determines the recommendation.

- **Robust actions:** identify actions that remain acceptable across the tested scenarios, with their costs and exceptions. Robustness within the tested set is not a guarantee across all futures.
- **Contingencies:** specify conditional actions and lead times; account for the cost of preparing a backup even when it is never used.
- **Decision triggers:** record the measurement, threshold, review date, and responsible role. A trigger can be a practical operating rule without being a statistical test or proof of a mechanism.
- **Next evidence:** identify the smallest feasible pilot, control, or observation that could change the choice. If none of the current evidence distinguishes scenarios, say so.

Do not turn a recommendation into an executed experiment, purchase, or protocol change. The deliverable is the analysis and proposed response unless the user separately requested execution.

## Probability and confidence

Use **"not estimated"** when evidence cannot support a numerical probability. If a probability is useful, define the event and horizon, identify a relevant base rate or fitted model, and record estimation uncertainty and transfer limitations. Qualitative plausibility is not a hidden numeric score. Confidence concerns the strength and consistency of evidence; it is not the probability that an event happens. This distinction is also used in the [IPCC uncertainty guidance](https://www.ipcc.ch/site/assets/uploads/2017/08/AR5_Uncertainty_Guidance_Note.pdf).

Normalize only a mutually exclusive, collectively exhaustive outcome partition under the same conditioning assumptions and horizon. For example, the final number of usable samples from one fixed batch of 100 can be partitioned as 0–59, 60–79, and 80–100. That defines valid outcome bins, but supplies no probabilities for them. The six scenario lenses do not form such a partition.

Keep resource allocation separate from event likelihood. A 61.8/38.2 golden-ratio allocation is not justified by this workflow. Choose allocations from evidence, consequences, costs, capacity, reversibility, and the stated objective.

## Modes

- **Quick screening:** three distinct scenarios, critical assumptions, and the next observation. Brevity does not establish evidence quality.
- **Detailed analysis:** more scenarios and explicit sensitivity/decision comparisons; allocate time to evidence gathering as needed, without promising a high-stakes analysis in minutes.
- **Scenario chain:** expand a decision-relevant branch, including adverse or ambiguous ones. Keep each child conditional on its parent. For probabilities, use `P(A and B) = P(A) × P(B given A)`, not a product of marginal probabilities without justified independence. Stop when added detail cannot change the action or lacks evidence.
- **Reverse planning:** work backward from a target to candidate prerequisites and test their feasibility. A plausible path is not proof of necessity, sufficiency, or likelihood.
- **Stakeholder comparison:** evaluate the same scientific scenarios from researcher, participant, facility, or funder perspectives. Different preferences are not independent corroborating evidence.

## Method and source boundaries

The current [Government Office for Science Futures Toolkit](https://www.gov.uk/government/publications/futures-toolkit-for-policy-makers-and-analysts/the-futures-toolkit-html) distinguishes scenarios from predictions and describes stress-testing options across possible futures. This skill adapts those general distinctions to research contingencies; the toolkit does not validate these six particular lenses, their probabilities, or a prescribed number of branches.

This documentation-only skill contains no forecast engine or causal estimator. Its worked example is synthetic and illustrates planning arithmetic, not demonstrated improvement in real research outcomes.

## License and adaptation

© 2026 Ashraf Hussein Kahoush / AHK Strategies. Licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Commercial use requires a license from the author. This repository adaptation narrows the workflow to research planning and revises evidence, probability, and causal-claim guidance; it preserves attribution to the upstream framework and preprints.
