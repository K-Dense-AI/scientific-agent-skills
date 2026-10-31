# Final report template

Produce this when the run ends (budget spent, frontier exhausted, or progress
stalled). The point is an honest, auditable account — not a victory lap. Keep it
concise and grounded in the tree.

```markdown
# Arbor run report: [objective]

## Result
- **Best artifact**: [git branch/ref of M_best, e.g. `arbor/best`]
- **Gate score**: [score of M_best] vs. initial [score of M_0] → delta [Δ]
- **Final untouched evaluation**: [score/protocol, or explicitly not performed]
- **Evidence**: [commit, evaluator/data versions, seeds, repetitions, raw logs]
- **How to check it out**: `git checkout [ref]`
- One-line summary of the change that won.

## What was tried (audit trail)
[Paste `python "$ARBOR_TREE" status` — the tree shows every direction,
which were pruned, which merged, with dev/test scores.]

## How understanding evolved
2-4 bullets tracing the main hypothesis shifts: which early nodes tested broad
mechanisms, what they confirmed or ruled out, and how that reshaped later
hypotheses. The story should explain *why* the final design looks the way it
does — i.e. the constraints the run discovered.

## Dev vs. test (overfitting check)
- Nodes that improved **dev**: [count]
- Nodes that passed the **test merge gate**: [count]
- Comment on the gap: were there high-dev / low-test candidates? What did
  rejecting them tell you? How many gate queries were made, and was the
  same holdout reused for selection? An honest gap here is more trustworthy than a clean
  "everything worked".

## Open directions
What you'd explore with more budget, and any direction that seemed to need a
new high-level formulation rather than further refinement (HTR's known weak
spot — flag it for the human).
```

Always leave `M_best` as a real, runnable artifact on a named git branch.
