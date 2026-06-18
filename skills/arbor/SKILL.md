---
name: arbor
description: Autonomously improve a real artifact (code, training recipe, agent harness, data pipeline, prompt) against an objective and an evaluator, using Hypothesis Tree Refinement (HTR) from the Arbor paper. Use this whenever someone wants to iteratively optimize something over many experiments without overfitting — e.g. "get my model's eval score up", "improve this agent/harness", "tune this pipeline", "beat the baseline on this benchmark", "run a search over approaches and keep the best", "do an MLE-bench / Kaggle-style optimization", or any long-horizon "make this artifact better and don't just memorize the dev set" task. Trigger it even when the user doesn't say "Arbor" or "hypothesis tree" but describes repeated experiment-and-evaluate loops, branching exploration of competing ideas, or worries about a dev/test gap. Runs Claude itself as the coordinator with subagent executors in isolated git worktrees; for the standalone `arbor` CLI tool see references/arbor-upstream.md.
allowed-tools: Read Write Edit Bash Agent
license: MIT license
metadata: {"version": "1.0", "skill-author": "K-Dense Inc."}
---

# Arbor — Autonomous Optimization via Hypothesis Tree Refinement

## Overview

This skill runs an **Autonomous Optimization (AO)** loop: starting from an existing artifact and a measurable objective, improve it through many rounds of experiment and evaluation — without step-by-step human supervision and without overfitting to the feedback signal. It's the right tool when the bottleneck isn't writing one good change, but *organizing dozens of trials* so that lessons accumulate instead of evaporating.

It implements **Hypothesis Tree Refinement (HTR)** from *Arbor* (Jin et al., 2026). The key idea: keep the research state in a persistent **hypothesis tree** rather than in conversation history. Each node binds a hypothesis, the distilled insight it produced, and a pointer to the artifact version that realizes it. You play the long-lived **coordinator** that owns this tree and decides where to search; short-lived **executor** subagents test one hypothesis each in isolated git worktrees and report back. A **held-out merge gate** admits a change only when it improves on a *test* evaluator the search never optimized against. This is what turns trial-and-error into cumulative, auditable research.

Use the `scripts/tree.py` state manager for all the bookkeeping (creating nodes, writing evidence, propagating insights, pruning, the merge gate, the Observe projection). It keeps the state consistent and frees you to spend judgment on what the evidence *means*.

## When to use this skill

Reach for Arbor when the task is **iterative improvement of a concrete artifact under an evaluator**:
- Model training: optimizer/architecture/recipe changes to lower loss or hit a target in fewer steps.
- Harness/agent engineering: raising pass rate or accuracy of an agent loop, search harness, or tool-use scaffold.
- Data synthesis: improving a generation/filtering pipeline judged by downstream model behavior.
- Benchmark optimization: MLE-bench / Kaggle-style "improve the submission" tasks.
- Prompt/system optimization where you can score outputs automatically.

The distinguishing signals: there's an **artifact you can modify**, an **objective**, a way to **score** candidates, and you expect to run **many experiments**. If the user only wants a single fix or a one-shot answer, this is overkill — just do the work directly. If they want open-ended ideation with no evaluator, use `hypothesis-generation` or `scientific-brainstorming` instead.

## The AO setup — pin this down first

Before any experiments, establish the task tuple `(M_0, O, E_dev, E_test)`. Getting this right matters more than any later decision, so confirm it explicitly:

- **M_0 — initial material**: the artifact to improve (a repo, a script, a config, a prompt). Make sure it's under git and currently runs.
- **O — objective**: the natural-language goal and the metric *direction* (maximize accuracy? minimize loss/steps?).
- **E_dev — development evaluator**: a command you can run freely during search to score a candidate. Fast, repeatable.
- **E_test — held-out test evaluator**: a *separate* evaluator (different seeds, different split, or a larger run) used only at the merge gate. It must not be used as a search oracle — that's the whole point.

If the user hasn't given you a clean dev/test split, **construct one and say so**. The dev/test separation is the mechanism that catches overfitting: a candidate that wins on dev but not on test isn't a success, it's a warning that you're exploiting the feedback signal. Without it, autonomous search reliably overfits.

Initialize the run:

```bash
python scripts/tree.py init \
  --objective "Improve BrowseComp answer accuracy on the search harness" \
  --dev-eval "python eval.py --split dev --n 50" \
  --test-eval "python eval.py --split test --n 300" \
  --material "." --metric-direction max --branching 3 --max-depth 2 --budget 12
```

`--branching` is how many sibling hypotheses you propose per parent; `--max-depth 2` keeps directions at depth 1 and concrete interventions at depth 2 (the paper's default); `--budget` is the number of coordinator cycles. Start small (10–20 cycles) — structured search beats brute force, and you can extend if progress is still being made.

## The coordinator loop

You run repeated cycles of six steps. This is the heart of HTR; do not collapse it into ad-hoc editing. Run `python scripts/tree.py cycle` once per cycle to track the budget.

### 1. Observe
Begin every cycle by re-grounding in the tree, not in your memory of the conversation:

```bash
python scripts/tree.py observe
```

This prints the objective, global insights, the active frontier (selectable hypotheses), executed nodes with their evidence, pruned lessons (negative constraints), and the current best artifact. Treating the tree as the source of truth is what keeps you coherent over a long run, after context compression has thrown away the details.

### 2. Ideate
Pick a promising parent and propose a few child hypotheses under it. **Condition on the tree's evidence** — this is the difference between Arbor and random search:
- Validated insights are assumptions you can build on.
- Pruned nodes are dead ends to avoid.
- A "half-right" result is a *starting point for a sharper hypothesis*, not a reason to abandon the direction.

Each hypothesis should be a **falsifiable claim about how changing the artifact will move the metric**, not a vague intention. Depth-1 nodes are broad directions ("the search harness loses correct answers it already retrieved"); depth-2 nodes are concrete, executable interventions ("run K=5 independent rollouts and aggregate by evidence dossier instead of majority vote").

```bash
python scripts/tree.py add-node --parent n0 --hypothesis "Verification, not retrieval, is the bottleneck: candidates are found but discarded"
python scripts/tree.py add-node --parent n4 --hypothesis "Decompose the question into atomic constraints and verify each independently"
```

### 3. Select
Choose which pending leaves to run next. **Selection is not pure score-maximization** — pick a hypothesis because it has strong prior evidence, because it would resolve an ambiguity its siblings exposed, or because its failure would clarify an important assumption. Frontier control under delayed feedback rewards informative experiments, not just promising ones.

### 4. Dispatch
Run each selected hypothesis as an **executor subagent in an isolated worktree** (use the Agent tool with `isolation: "worktree"`, or have the executor create one with `git worktree add`). Isolation matters: parallel experiments must not clobber each other or the current best, and exploratory changes stay quarantined until they pass the merge gate.

Dispatch siblings **in parallel** (multiple Agent calls in one message) when they're independent — comparative evidence within one direction is exactly what makes later pruning and abstraction possible.

Give each executor a tight, **hypothesis-bound** brief. See `references/executor-brief.md` for the full template. The contract that makes HTR work: **the executor may not change the hypothesis when the metric stalls.** It repairs its own code and reruns, but `h_n` is fixed — otherwise the returned score is no longer evidence about the assigned node and the tree's semantics break. The executor returns exactly four things:
- **dev_score** — the dev evaluator result (for selection);
- **result** — a factual summary of what happened;
- **insight** — the distilled, reusable lesson (*why* the result supports, weakens, or bounds the hypothesis);
- **branch_ref** — the git branch/commit/worktree path holding the artifact.

Mark a node `running` before dispatch (`tree.py set-status --node n5 --status running`) so the Observe projection stays accurate.

### 5. Backpropagate
When an executor returns, write its report into the node, then **abstract the lesson upward**:

```bash
python scripts/tree.py set-evidence --node n5 --dev-score 70.0 \
  --result "K=5 dossier aggregation recovers answers in minority rollouts" \
  --insight "Correct answers often appear in a minority of rollouts; aggregation beats majority vote" \
  --branch-ref "wt/n5"

python scripts/tree.py propagate --node n5 \
  --insight "Candidate coverage, not verification, limits this direction" --to-root
```

This is the step that makes the tree more than a log. A leaf-level observation ("data-interface mismatch") should become a direction-level constraint and, if it generalizes, a global prior that shapes future ideation. **Insight propagation is the component that drives most of HTR's gains** — in the paper's MLE-Bench Lite ablation, a tree *without* insight feedback scored even lower than a flat experiment queue with no tree at all (54.5% vs. 63.6% any-medal, against 81.8% for the full system). Hierarchy alone isn't enough: the semantic memory is what matters. So spend real thought on the abstraction; don't just copy the leaf insight upward verbatim.

### 6. Decide
Decide what to do with the new evidence: keep expanding a direction, prune a falsified subtree, or attempt to merge a candidate.

- **Prune** dead ends, recording *why* — the reason becomes a negative constraint:
  ```bash
  python scripts/tree.py prune --node n7 --reason "search-augmented judge overfits dev questions; no test transfer"
  ```
- **Merge gate** — promote a candidate to the new best **only if it improves on `E_test`**. Run the test evaluator in a *fresh* worktree (not the dev worktree, to avoid leakage), then:
  ```bash
  python scripts/tree.py merge --node n5 --test-score 67.67 --branch-ref "wt/n5"
  ```
  If the gate rejects it, that's informative: a high-dev / low-test candidate is evidence the direction may be exploiting the dev signal rather than producing a transferable improvement. Record that lesson; don't quietly promote it anyway.

Repeat until the budget is spent, the frontier is exhausted, or progress has clearly stalled.

## Finishing the run

When you stop, produce a short report (see `references/report-template.md`) covering:
- the final best artifact, its test score, and its delta over `M_0`;
- the tree (`python scripts/tree.py status`) as the audit trail of what was tried;
- the main hypothesis shifts — how task understanding deepened across the run (early nodes test broad mechanisms; later nodes find their limits; ancestor insights compress these into the constraints behind the final design);
- merged vs. explored: many nodes improve dev, far fewer pass the test gate — report that gap honestly rather than overstating dev wins.

Always leave `M_best` as a real, runnable artifact on a named branch, and tell the user how to check it out.

## Principles that make this work (not rote rules)

These come from the paper's analysis; understanding *why* matters more than following them mechanically.

- **The tree is the memory; conversation is not.** Over a long horizon your context gets compressed. Re-Observe each cycle so decisions rest on durable evidence, not a lossy summary.
- **Structured search, not more sampling.** Arbor's gains come from how the budget is *organized* — maintaining competing hypotheses, comparing siblings, carrying lessons forward — not from spending more tokens. Don't fan out aimlessly; each experiment should be conditioned on what the tree already knows.
- **Dev guides, test admits.** Use dev feedback freely to steer exploration, but never let a dev win into the final artifact without test confirmation. The dev/test disagreement is itself a signal worth reading.
- **Executors are hypothesis-bound.** Local engineering flexibility (edit, debug, rerun) is fine; silently changing the hypothesis to chase a better number is not — it destroys the meaning of the evidence.
- **Failures are constraints, not noise.** A falsified hypothesis tells you what the solution must avoid. Pruned-with-a-reason is more valuable than pruned-and-forgotten.

## Reference files

- `references/htr-methodology.md` — deeper explanation of HTR, the node structure, the six steps, and the paper's empirical lessons (ablations, transfer, cost). Read when you want the rationale behind a design choice.
- `references/executor-brief.md` — the template for the brief you hand each executor subagent.
- `references/report-template.md` — the final-report structure.
- `references/arbor-upstream.md` — how to install and run the standalone `arbor` CLI from RUC-NLPIR/Arbor instead of orchestrating it natively, and when to prefer each.
