# Sequential and Adaptive Designs

A fixed design commits to a single sample size and one analysis at the end.
**Sequential** and **adaptive** designs allow looks at the data *during* the study and
let you stop early (for benefit, harm, or futility) or modify the design — saving
participants, time, and money. The catch: every interim look at the data is another
chance to cross the significance threshold by luck, so the error rate must be
controlled explicitly. Peeking at accumulating data and stopping the first time
p < 0.05 can inflate the Type I error rate; the amount depends on the number and timing
of looks, test, and correlation. This is the core problem these methods solve.

## Why naive peeking fails

If you test at α = 0.05 at each of K interim analyses and stop at the first
significant result, the *overall* false-positive rate generally exceeds 0.05.
There is no universal inflation value for K looks. Calibrate the joint procedure
(e.g. alpha spending with its required assumptions) so the cumulative error is
controlled, then verify it under realistic null scenarios.

## Group-sequential designs

Pre-plan a fixed number of interim analyses (e.g. at information fractions 25%, 50%, 75%, 100%)
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
  can vary under a pre-specified, valid monitoring plan. Information fractions
  represent statistical information, not automatically enrolled-patient fractions.
  Do not choose extra looks because an unblinded effect is nearly significant;
  spending alone does not license such outcome-dependent monitoring. See the
  [FDA adaptive-design guidance](https://www.fda.gov/media/78495/download).

You can stop for:
- **Efficacy** — the effect crosses the upper boundary.
- **Futility** — the effect is so small that continuing is unlikely to ever reach
  significance (a non-binding or binding lower boundary / conditional power threshold).
- **Harm** — safety boundary crossed.

Group-sequential designs require a modestly larger maximum sample size than a fixed
design (to pay for the looks), but the *expected* sample size is usually smaller
under scenarios where trials often stop early; report it under both null and
plausible alternatives.

### Tooling

Use purpose-built boundary calculations; the bundled Python helpers generate
allocation/DOE layouts, not interim boundaries. Official current options are:
- R [`gsDesign::gsDesign`](https://keaven.github.io/gsDesign/reference/gsDesign.html):
  `k` includes the final analysis, `timing` specifies information fractions, and
  `test.type` distinguishes one-sided, symmetric two-sided, and binding/nonbinding
  futility designs. Do not assume the default `alpha=0.025` is a two-sided 0.05 test.
- R [`rpact::getDesignGroupSequential`](https://docs.rpact.org/reference/getDesignGroupSequential.html):
  configure `kMax`, `informationRates`, `sided`, `alpha`, `typeOfDesign`, and
  futility explicitly. These are documentation-verified pointers; this skill does
  not ship or runtime-test an R boundary calculation.
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
   rate and yields acceptable power, estimator bias, confidence-interval coverage,
   and expected/maximum sample sizes; report Monte Carlo uncertainty.

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
