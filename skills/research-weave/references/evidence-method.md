# Discovery, evidence, and attention

## Search by uncertainty

Create a question ledger: what is known, what the project assumes, what would reverse a design choice, and what a skeptical reviewer would cite. Give each consequential uncertainty a query. These are query patterns, not fixed database syntax.

| Channel | Vocabulary | What it can recover |
|---|---|---|
| Historical | old task names, original formulation, foundational mechanism | An idea before its current branding |
| Current problem | task + bottleneck + latest terminology | Close contemporaries |
| Mechanism/evaluation | technical operation + matched-budget baseline, benchmark or measurement | Competitors outside the topic label; evaluation pitfalls |
| Challenge | failure, null, replication, limitation, ablation, critique | Evidence weakening the preferred account |
| Bridge | same mechanism in a neighboring field | Transferable insight under an explicit assumption |

A first sweep can start from a review/landmark and a recent close work from different lineages, then inspect cited foundations and later critiques. Reviews are indexes and interpretive sources. Inspect original results before using their attributed findings as facts. Record unperformed forward-citation searches instead of implying they occurred.

Date searches; record queries, sources, filters, actual candidates examined, retained IDs, and failures. A search engine's estimated hits are not the screened pool. If only abstracts or excerpts are accessible, offer provisional triage and identify the needed section. Two empty searches on one vocabulary are not coverage of a field. Reopen retrieval when decisive evidence exposes an uncovered branch, new alias, or later resolution.

## What counts as valuable?

Judge the claim used by the project. One method paper can have a weak causal explanation and a strong reproducible implementation result. A benchmark can be valuable because it exposes a measurement error without proposing a new model.

Use three separate judgments, not a weighted popularity score:

1. **Evidence credibility:** supported, provisional, or unsupported for this claim, with a concrete reason.
2. **Historical role:** introduced a formulation, enabled a capability, changed evaluation, exposed a boundary, connected branches, or has no demonstrated downstream role yet.
3. **Project utility:** which belief, baseline, measurement, method, or experiment changes after reading, subject to which transfer conditions.

| Work type | Load-bearing checks |
|---|---|
| Empirical ML / agents | matched model and budget; tuning/selection fairness; leakage; evaluator reliability; independent task/seed counts; variance; all-in cost; baseline strength |
| Mechanistic/causal | interventions or controls discriminating alternatives; correlation vs mechanism; untested mediators |
| Theory | definitions and assumptions; proof status; applicability to the actual algorithm; asymptotic vs finite-regime interpretation |
| Dataset/evaluation | construct validity; sampling/annotation; contamination; subgroups; whether metrics reward the intended behavior |
| Systems | end-to-end cost/reliability; hardware/software context; artifacts; integration effects |
| Other domains | appropriate design/validity criteria; do not impose an ML benchmark or biomedical hierarchy automatically |

Missing reporting is uncertainty, not proof a procedure was omitted. Missing code limits reproducibility but does not automatically invalidate theory. A null result constrains an effect only to the tested sensitivity and conditions. A paper's fame is a discovery lead until identity and relevant text are verified.

For decision-bearing sources check later versions, corrections, withdrawals, independent tests, and rebuttals where discoverable. Record checked sources and unresolved status. A failed search does not establish clean status. A valid publisher record establishes identity, not scientific support.

## Evidence card

> P3 / C7 — scoped claim. URL/version and section/table/proof locator. Observation with comparator and uncertainty. Authors infer X; we infer Y under assumption Z. Evidence strength/reason. Main validity threat. Research role and project decision. Access status and shared evidence family.

Prefer short faithful paraphrases to long quotations. A locator without an observation is a weak audit trail. A number without metric, baseline, denominator, or conditions is unusable.

## Relevance is a relationship

| Role | Question | Transfer check |
|---|---|---|
| fact | Does this establish the bottleneck? | Same construct and applicable conditions |
| mechanism | Does this discriminate explanations? | Intervention/argument identifies the proposed mechanism |
| method | Can we reuse or compare the operation? | Inputs, access, cost, objectives compatible |
| evaluation | Should this change how success is measured? | Metric and test population fit target |
| boundary | Where does a general claim stop working? | Boundary variable matters to target |
| counterevidence | What would defeat our motivation/assumption? | Strongest fair competing setup |
| analogy | Does another field suggest a new perspective? | Explicit bridge assumption; not direct empirical support |

Complete: “If this holds in our setting, we change ___ because ___; transfer requires ___.” Without a meaningful completion, deprioritize even a topically close paper. Preserve inconvenient threats. Without a project, use a question or branch-level decision.

## Independence and influence

Distinguish bibliographic records, paper versions, studies, and evidence families. Multiple papers can reuse one experiment. A survey repeating a result, an extension on the same test set, and an independent replication have different roles. Record overlap and uncertainty; avoid paper-count confidence.

Use adoption, reproduced baselines, changed task definitions, or documented challenges to support influence. Citation counts guide discovery; concrete relationships explain intellectual history. Histories branch, merge, revisit ideas, and stop. Avoid definitive “first” claims without adequate priority search.

## Convergence: how much support does a proposition have?

Aggregate at the proposition level, with its scope fixed. Report separately:

- Supporting papers actually inspected and the claims they contribute.
- Distinct evidence families and **confirmed independent** tests/derivations; leave the latter unknown when overlap is unresolved. Different authors or family labels alone do not prove independence.
- Breadth across teams, tasks/populations, methods, measurement, and time, showing robustness and the boundaries of generality.
- Credibility, direct applicability, effect direction/magnitude and precision when available, and strongest counterevidence.

Three independent, well-controlled studies can provide stronger convergence than one; ten summaries repeating one experiment still contain one primary result. Weak or misaligned studies need not outweigh a strong directly applicable counterexample. Preserve both counts and the qualitative judgment.

Use `convergent`, `conditional`, `contested`, or `insufficient`, with reasons. Convergent means multiple relevant contributions align after overlap/validity checks, not that a theorem has been proved by vote. Conditional specifies supported settings; contested retains consequential credible counterevidence; insufficient includes poor access or weak direct evidence. These are not calibrated probabilities.

Do not pool incompatible outcomes or dependent samples. Formal meta-analysis requires its own protocol. For theory compare assumptions/proof independence; repeating one theorem is not several proofs. One valid in-scope counterexample can refute a universal claim despite many positive cases; an average-effect claim requires a different interpretation.

## Reading decisions

Prioritize by expected decision change, credibility, missing information, redundancy, and reading effort. These are qualitative judgments, not calibrated probabilities. Prefer coverage of distinct consequential uncertainties over several repetitions of one evidence family.

- `deep_read`: reconstruct a central method/argument. If provisional, state why promising rather than endorsing it.
- `targeted_read`: a table, definition, diagnostic, proof assumption, or evaluation detail answers the question.
- `verify_access`: potentially consequential but not yet assessable; name missing source material.
- `defer`: relevant but redundant, low decision impact, or useful later.
- `exclude`: outside scope, wrong construct, duplicate version, or unusable for intended claim; preserve reason.

With a small budget explain the tradeoff and remaining uncertainty. Do not discard counterevidence for low prestige/citations or for threatening the project.
