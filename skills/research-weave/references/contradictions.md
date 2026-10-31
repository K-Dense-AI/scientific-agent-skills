# From disagreement to a testable question

Normalize each claim:

> Under conditions S, intervention X relative to comparator B changes outcome Y by direction/magnitude D, with uncertainty U.

For theory use formal definitions/assumptions and propositions. Unknown fields stay explicit. Compare findings rather than one headline with another paper's limitations.

| Alignment axis | Typical false conflict |
|---|---|
| Definition/scope | “Can improve” vs “does not reliably improve”; existence vs universality |
| Task/distribution | preference vs exact accuracy; in-domain vs shifted data |
| Information access | intrinsic feedback vs tools, labels, oracle correctness, external verifier |
| Model/training | frozen model vs trained critic; different snapshots |
| Baseline/selection | best-of-N vs first answer; oracle vs realistic early stopping |
| Resources | more samples vs equal total compute; hidden tuning |
| Measurement | pass@k pool vs selected pass@1; different evaluators |
| Precision | noisy estimates, selected subgroups, low power; significant vs nonsignificant |
| Theory assumptions | worst-case vs average-case; different formal objects |

Classify:

- `comparable_conflict`: opposing conclusions under sufficiently aligned conditions with inspected evidence. State remaining uncertainty; neither author is thereby proven wrong.
- `scope_mismatch`: conditions explain the apparent opposition. A boundary study may still be useful, but direct contradiction is unestablished.
- `inconclusive`: access, reporting, or precision prevents a determination.
- `not_opposed`: different questions or compatible claims.

A possible reconciliation is not a proven causal moderator. Label it hypothetical unless established. Nonsignificance is not zero effect; opposite point estimates alone do not establish conflict.

## Tension card

For each consequential tension record:

1. Claim IDs, primary locations, and decision at stake.
2. Aligned/different conditions and unknown fields.
3. Classification and reason, including independence/precision.
4. At least two explanations when unresolved; one may be measurement or selection.
5. A separating test: load-bearing variable, controls, metrics/cost, distinct predictions.
6. A gap-killing outcome that would abandon or narrow the motivation.
7. Later-resolution searches with query/source/date/results. “Not found here” is narrower than “unresolved in literature.”

Elevate to **candidate frontier** only if consequential, surviving available alignment, testable, and not already resolved in inspected later work. An untested regime can matter without contradiction. An experiment is not automatically a novel method; novelty auditing is separate.

## Worked example — fictional, not literature evidence

A reports no gains from intrinsic critique by a frozen model on exact-answer tasks. B reports gains using execution traces. Feedback access differs: `scope_mismatch`. Hypothesize that informative external evidence explains the difference.

Use the same initial answers, model, split, revision prompt, and all-in budget; randomize no feedback, informative execution feedback, and shuffled-feedback negative control. Measure wrong-to-right rescue, right-to-wrong damage, final accuracy, and cost. An information-content account predicts informative feedback beats controls; an extra-deliberation account predicts gains without informative feedback. If matched-budget resampling matches all gains, the special feedback mechanism motivation weakens. This tests a boundary; it does not make A and B inconsistent.

If A and C instead show opposing precise effects with the same model snapshot, prompts, task IDs, budget, and evaluator, inspect artifacts for a candidate `comparable_conflict`. A metric bug or version change resolving the conflict removes it as an unresolved gap. Missing alignment fields require `inconclusive`.
