---
name: statistical-power
description: Sample-size and statistical power calculations for planning studies. Use whenever someone asks "how many subjects/samples/replicates do I need", wants an a priori power analysis, a minimum detectable effect (MDE), a power curve, or needs to justify a sample size for a grant, IRB protocol, or pre-registration. Covers closed-form power for t-tests, ANOVA, proportions, correlations, chi-square, and regression, plus simulation-based (Monte Carlo) power for designs with no formula — logistic/Poisson regression, mixed models, cluster-randomized trials, survival, and interactions. Use this skill even when the request only mentions an effect size, alpha, or "80% power" without saying "power analysis" explicitly. For laying out the study (randomization, blocking, factorial/DOE, crossover, sequential designs) use experimental-design; for analyzing data already collected and reporting it use statistical-analysis.
allowed-tools: Read Write Edit Bash
compatibility: Requires Python >=3.10. Examples target statsmodels >=0.14.6, scipy >=1.11, pingouin >=0.6, numpy >=1.26, and matplotlib. Optional extras are statsmodels mixed models and lifelines for simulation-based power.
license: MIT license
metadata: {"version": "1.0", "skill-author": "K-Dense Inc."}
---

# Statistical Power & Sample Size

## Overview

Power analysis answers one of the most consequential questions in study planning: **how large a sample do you need to reliably detect an effect of a given size, and what could you detect with the sample you can afford?** An underpowered study wastes resources and produces inconclusive or irreproducible results; an overpowered one wastes participants, money, and (in clinical work) exposes more people to risk than necessary. Getting this right *before* data collection is the single highest-leverage statistical decision in a project.

Four quantities are locked together for any given test: **sample size (n)**, **effect size**, **significance level (α)**, and **power (1 − β)**. Fix any three and the fourth is determined. Every calculation in this skill is some rearrangement of that relationship.

This skill covers the two ways to do power analysis:
- **Closed-form** formulas (fast, exact for standard tests) — see `references/closed_form_recipes.md`.
- **Simulation / Monte Carlo** (works for *any* design or model you can simulate and analyze) — see `references/simulation_based_power.md`.

For choosing and converting effect sizes — usually the hardest part — see `references/effect_sizes.md`.

## When to Use This Skill

- Determining required sample size before collecting data (a priori power analysis)
- Finding the minimum detectable effect (MDE) for a fixed, already-determined sample size
- Producing power curves (power vs. n, or power vs. effect size) for a grant or protocol
- Justifying a sample size for an IRB submission, grant, or pre-registration
- Powering designs with unequal group sizes or non-1:1 allocation
- Powering anything without a textbook formula (mixed models, logistic/Poisson regression, cluster-randomized trials, survival analysis, mediation, interactions) via simulation
- Accounting for multiple comparisons, attrition/dropout, or clustering in the sample-size estimate

## Installation

Use **uv**. Pin versions in production; unpinned is fine for exploration.

```bash
uv pip install "statsmodels>=0.14.6" "scipy>=1.11" "pingouin>=0.6" "numpy>=1.26" matplotlib pandas
# For simulation-based power of advanced models (optional, add as needed):
uv pip install lifelines            # survival
# mixed models and GLMs come with statsmodels
```

**Compatibility note:** use `statsmodels>=0.14.6` with `scipy>=1.11` to avoid `_lazywhere` import errors on SciPy 1.16+. Pingouin 0.5+ renamed power-function arguments to match the names used below.

---

## The one decision that drives everything: the effect size

Power calculations are only as trustworthy as the effect size you feed them. **Do not invent a number.** Use, in rough order of preference:

1. A **minimally important effect** — the smallest effect that would actually change a decision or matter scientifically/clinically (the "smallest effect size of interest", SESOI). This is the most defensible basis: you power to detect what matters, not what you hope to see.
2. A **pilot or prior-study estimate**, but shrink it — published and pilot effects are inflated by publication bias and the winner's curse. Powering on a raw pilot estimate routinely underpowers the real study.
3. A **convention** (Cohen's small/medium/large) only as a last resort, and say so explicitly.

Whatever you pick, run a **sensitivity analysis**: report how required n changes across a plausible range of effect sizes, not a single point. A power analysis presented as one number hides its biggest source of uncertainty. See `references/effect_sizes.md` for benchmarks and conversions between d, f, r, η², odds ratios, and Cohen's h/w.

> **Avoid post-hoc ("observed") power.** Computing power from the effect size you just estimated is circular: it is a deterministic function of the p-value and tells you nothing new. If a study is already done and you want to know what it could have detected, report a **sensitivity analysis** (MDE at the achieved n) or, better, the confidence interval around the observed effect. This is a common reviewer complaint — do not produce observed power even if asked without flagging the issue.

---

## Quick recipes (closed-form)

The bundled `scripts/power.py` wraps statsmodels into one consistent interface so you don't have to remember which solver belongs to which test. Run from the skill directory or add `scripts/` to `sys.path`.

```python
from power import sample_size, power, mde, power_curve

# 1. How many per group to detect Cohen's d = 0.5, two-sided, 80% power?
sample_size(test="t_ind", effect_size=0.5, power=0.80, alpha=0.05)
# -> required n per group

# 2. Two groups, 3:1 allocation (e.g. more controls than cases)
sample_size(test="t_ind", effect_size=0.5, power=0.80, ratio=3.0)

# 3. Fixed n=30/group — what's the minimum detectable d at 80% power?
mde(test="t_ind", nobs1=30, power=0.80, alpha=0.05)

# 4. One-way ANOVA, 4 groups, detect Cohen's f = 0.25
sample_size(test="anova", effect_size=0.25, k_groups=4, power=0.80)

# 5. Two proportions: 0.40 vs 0.55 (auto-converts to Cohen's h)
sample_size(test="two_proportions", prop1=0.40, prop2=0.55, power=0.80)

# 6. Correlation: detect r = 0.30
sample_size(test="correlation", effect_size=0.30, power=0.80)

# 7. Power curve for the grant figure
power_curve(test="t_ind", effect_size=0.5, n_range=range(10, 120, 5),
            save="power_curve.png")
```

Supported `test=` values: `t_ind` (two independent means), `t_paired`/`t_one` (paired or one-sample mean), `anova` (one-way), `two_proportions`, `one_proportion`, `correlation`, `chi2` (goodness-of-fit / contingency via effect size *w*), `linear_regression` (R² increment / f²). Full argument tables and the underlying statsmodels calls are in `references/closed_form_recipes.md`.

---

## When there is no formula: simulate

Closed-form power exists only for a handful of simple tests. For **logistic/Poisson regression, mixed-effects / repeated-measures models, cluster-randomized trials, survival analysis, mediation, multi-way interactions, or any non-standard analysis**, the right tool is simulation. The logic is always the same three steps:

1. **Simulate** a dataset from your assumed truth (the effect you want to detect, plus realistic noise, baseline rates, cluster structure, etc.).
2. **Analyze** it with the *exact* test/model you plan to use on the real data.
3. **Repeat** many times (≥1,000; 5,000–10,000 for a stable estimate near 80%). Power is the fraction of replicates in which the test is significant.

`scripts/simulate_power.py` provides a reusable harness plus worked examples (two-group difference, logistic regression, cluster-randomized trial with an ICC, and a linear mixed model). The core is just:

```python
from simulate_power import simulate_power

def gen_and_test(n, rng):
    # build a dataset of size n under the assumed effect, run the planned test,
    # return True if the result is significant
    ...

est = simulate_power(gen_and_test, n=200, n_sims=2000, alpha=0.05)
print(f"Power at n=200: {est.power:.3f} (95% CI {est.ci_low:.3f}-{est.ci_high:.3f})")
```

Report the **Monte Carlo confidence interval** on the estimate (the harness returns it) so the reader knows whether 0.81 vs. 0.79 is signal or simulation noise. See `references/simulation_based_power.md` for the full patterns, including how to search for the n that hits target power and how to model dropout and clustering.

---

## Adjustments people forget

These routinely make the difference between an adequately powered study and an underpowered one. Apply them explicitly and state that you did.

- **Multiple comparisons.** If the analysis tests *m* hypotheses with a Bonferroni-style correction, power each test at the corrected α (e.g. α/m), which raises n. Better: power on the family-wise or FDR-controlled procedure directly via simulation. Ignoring this silently underpowers every secondary endpoint.
- **Attrition / dropout / unusable samples.** Power gives the n you need *analyzed*. Inflate the *enrolled* n: `n_enroll = ceil(n_analyzed / (1 − dropout_rate))`. A 20% dropout rate means enrolling 25% more than the formula returns.
- **Clustering (design effect).** When observations are nested (patients within clinics, cells within animals, repeated measures within subject), the effective sample size is smaller than the raw count. Inflate by the design effect `DEFF = 1 + (m − 1)·ICC`, where *m* is cluster size and ICC the intraclass correlation. Treating clustered data as independent is **pseudoreplication** and badly overstates power — for cluster-randomized designs, simulate instead.
- **One- vs. two-sided.** Two-sided is the default and almost always the right choice; a one-sided test buys power only by refusing to detect an effect in the unexpected direction. Justify any one-sided test.
- **Unequal allocation.** Equal groups are most efficient for a fixed total n. If allocation is fixed by design (e.g. 2:1 treatment:control), pass `ratio=` so the calculation reflects it.

---

## Workflow

1. **State the design and the planned analysis.** The test you will run determines the power method. If the analysis is a mixed model or GLM, go straight to simulation.
2. **Choose the effect size** on a defensible basis (SESOI > shrunk pilot > convention) and write down the justification.
3. **Set α and target power.** Conventional defaults are α = 0.05 (two-sided) and power = 0.80; 0.90 is common for confirmatory/clinical work. State them.
4. **Compute** with `scripts/power.py` (closed-form) or `scripts/simulate_power.py` (simulation).
5. **Sensitivity analysis.** Recompute across a range of plausible effect sizes and produce a power curve. This is the deliverable, not a single number.
6. **Apply adjustments** for dropout, clustering, and multiplicity.
7. **Report** following the template below.

---

## Reporting template

A defensible power statement contains every input, so a reader could reproduce it. Adapt:

```
A priori power analysis was conducted to determine the sample size needed to detect
a [between-group difference of Cohen's d = 0.50], which we considered the smallest
effect of clinical interest. With α = .05 (two-sided) and power = .80, a two-sample
t-test requires n = 64 per group (128 total; computed with statsmodels 0.14).
Allowing for 20% attrition, we will enrol 160 participants. A sensitivity analysis
showed required n ranges from 45 to 105 per group across plausible effects
d = 0.40–0.60 (Figure X).
```

For simulation: also state the data-generating assumptions (baseline rate, residual SD, ICC, cluster sizes), the number of simulations, and the Monte Carlo CI.

---

## Common pitfalls

1. **Inventing the effect size** or copying an inflated pilot estimate — the most common way power analyses go wrong.
2. **Reporting a single n** instead of a sensitivity range / power curve.
3. **Post-hoc / observed power** — circular and uninformative; use sensitivity analysis or the effect-size CI instead.
4. **Ignoring clustering** (pseudoreplication) — counting cells/measurements as if they were independent subjects.
5. **Forgetting dropout** — powering the analyzed n but enrolling the same number.
6. **Confusing α with power**, or one-sided with two-sided.
7. **Powering only the primary endpoint** while reporting secondary/interaction tests that need far larger n.
8. **Using a t-test formula for a model you won't actually fit** (e.g. planning a logistic regression with a means-based calculation) — match the power method to the planned analysis.

---

## Resources

### Scripts
- `scripts/power.py` — unified closed-form interface (`sample_size`, `power`, `mde`, `power_curve`) over statsmodels/pingouin for all standard tests.
- `scripts/simulate_power.py` — Monte Carlo power harness with `simulate_power()` and `find_sample_size()`, plus worked examples (two-group, logistic regression, cluster-randomized, linear mixed model).

### References
- `references/closed_form_recipes.md` — per-test argument tables and exact statsmodels/pingouin calls, including proportions, chi-square, and regression.
- `references/simulation_based_power.md` — full simulation patterns for GLMs, mixed models, cluster designs, survival, and dropout.
- `references/effect_sizes.md` — choosing effect sizes (SESOI), Cohen's benchmarks, and conversions between d, f, r, η²/f², OR, h, and w.

### Related skills
- **experimental-design** — once you know n, lay out the actual study (randomization, blocking, factorial/DOE, crossover, sequential designs).
- **statistical-analysis** — assumption checks, running the test, effect sizes, and APA reporting after data collection.
- **statsmodels** / **pymc** — fitting the models referenced here.

### Key references
- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.).
- Lakens, D. (2022). *Sample Size Justification*. Collabra: Psychology, 8(1).
- Arnold, B. F. et al. (2011). Simulation methods to estimate design power. *BMC Medical Research Methodology*, 11:94.
