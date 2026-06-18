# Sequential and Adaptive Designs

A fixed design commits to a single sample size and one analysis at the end.
**Sequential** and **adaptive** designs allow looks at the data *during* the study and
let you stop early (for benefit, harm, or futility) or modify the design — saving
participants, time, and money. The catch: every interim look at the data is another
chance to cross the significance threshold by luck, so the error rate must be
controlled explicitly. Peeking at accumulating data and stopping the first time
p < 0.05 inflates the Type I error rate badly (to ~0.20+ with a few looks) — this is
the core problem these methods solve.

## Why naive peeking fails

If you test at α = 0.05 at each of K interim analyses and stop at the first
significant result, the *overall* false-positive rate is far above 0.05 — roughly
0.08 for 2 looks, ~0.14 for 5, ~0.20 for 10. The fix is to spend your total α across
the looks so the *cumulative* Type I error stays at 0.05.

## Group-sequential designs

Pre-plan a fixed number of interim analyses (e.g. after 25%, 50%, 75%, 100% of data)
and use **adjusted, more stringent boundaries** at each look so the overall α is
preserved. Common boundary families:

- **Pocock:** constant (equally stringent) nominal significance level at every look.
  Easier to stop early, but pays a larger penalty at the final analysis.
- **O'Brien–Fleming:** very stringent early (hard to stop in the first looks), relaxing
  toward the planned final α. Most popular in confirmatory trials because the final
  boundary is close to the unadjusted 0.05 and early stopping is reserved for dramatic
  effects.
- **Alpha-spending functions (Lan–DeMets):** generalize the above by defining how much
  α is "spent" as a function of information accrued, so the number and timing of looks
  need not be fixed in advance — only the spending function is.

You can stop for:
- **Efficacy** — the effect crosses the upper boundary.
- **Futility** — the effect is so small that continuing is unlikely to ever reach
  significance (a non-binding or binding lower boundary / conditional power threshold).
- **Harm** — safety boundary crossed.

Group-sequential designs require a modestly larger maximum sample size than a fixed
design (to pay for the looks), but the *expected* sample size is usually smaller
because many trials stop early.

### Tooling

Python support is thinner than for fixed designs; common options:
- **statsmodels** has limited sequential utilities; for full boundary computation,
  most practitioners call R packages via `rpy2` or a subprocess:
  - R `gsDesign` — the standard for group-sequential boundaries and spending functions.
  - R `rpact` — confirmatory adaptive and group-sequential designs.
- For custom rules, **simulate** the whole sequential procedure (generate data, apply
  the boundaries look by look, repeat) to confirm the realized Type I error and to
  estimate expected sample size and power. This mirrors the simulation approach in the
  **statistical-power** skill and is the most flexible route.

## Adaptive designs

Broader than group-sequential: the design itself can change at an interim based on
accumulating data, within a pre-specified plan that still controls error. Main types:

- **Sample-size re-estimation:** recompute the required n at an interim using the
  observed nuisance parameter (e.g. the variance or control-arm rate), without
  unblinding the treatment effect. Protects against a misjudged variance at planning.
- **Adaptive randomization:** shift allocation probabilities toward the better-
  performing arm as data accrue (response-adaptive), or to improve covariate balance.
- **Drop-the-loser / arm selection:** start with several arms or doses and drop
  inferior ones at interims (seamless phase II/III).
- **Adaptive enrichment:** narrow enrollment to a subgroup that appears to benefit.

Adaptive designs are powerful but easy to get wrong: any adaptation that uses the
unblinded treatment effect can inflate Type I error and bias the final effect estimate
unless the method explicitly corrects for it. Two non-negotiables:
1. **Pre-specify** the adaptation rule and the error-control method before the study.
2. **Validate by simulation** that the *entire* procedure preserves the Type I error
   rate and yields acceptable power and unbiased-enough estimates.

## When to use them

- **Confirmatory trials, expensive or risky enrollment** — group-sequential with
  O'Brien–Fleming boundaries to allow ethical early stopping.
- **Uncertain nuisance parameters at planning** — blinded sample-size re-estimation.
- **Many candidate doses/arms** — adaptive arm selection / seamless designs.
- **Pure exploration / fixed cheap data** — usually not worth the overhead; a fixed
  design is simpler and the analysis is unambiguous.

## Practical checklist

- Decide the **number and timing** of interim analyses (or the spending function).
- Choose a **boundary family** matched to how eager you are to stop early.
- Specify **futility** rules if you want to stop for lack of effect.
- Inflate the **maximum** sample size to cover the looks; report the **expected**
  sample size too.
- Pre-register the full sequential/adaptive plan, including the stopping rules.
- Have an independent **data monitoring committee** look at unblinded interims in
  human trials, not the study team.
- **Simulate** the design end to end to confirm error control before running it.
