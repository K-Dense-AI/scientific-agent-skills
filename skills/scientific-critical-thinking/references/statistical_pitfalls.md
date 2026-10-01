# Common Statistical Pitfalls

Use the estimand, sampling design, and assumptions to judge an analysis; the examples
below are illustrative. Primary guidance is linked in [review_sources.md](review_sources.md).

## P-Value Misinterpretations

### Pitfall 1: P-Value = Probability Hypothesis is True
**Misconception:** p = .05 means 5% chance the null hypothesis is true.

**Reality:** A p-value is a tail probability for the specified test statistic under the
null and the rest of the statistical model, including the sampling/analysis procedure.
It is not a posterior probability that a hypothesis is true.

**Correct interpretation:** "Under this null model and analysis procedure, a test statistic
at least this extreme has probability .05." Selection or unaccounted optional stopping
can invalidate this calibration.

### Pitfall 2: Non-Significant = No Effect
**Misconception:** p > .05 proves there's no effect.

**Reality:** Absence of evidence ≠ evidence of absence. Non-significant results may indicate:
- Insufficient statistical power
- True effect too small to detect
- High variability
- Small sample size

**Better approach:**
- Report confidence intervals
- Compare the interval with effects of practical importance; do not calculate power
  from the observed effect to explain this result
- Consider equivalence testing with scientifically justified, prespecified bounds

### Pitfall 3: Significant = Important
**Misconception:** Statistical significance means practical importance.

**Reality:** With large samples, effects too small to matter for the decision can become
"significant." Judge magnitude against a justified practical threshold.

**Better approach:**
- Report effect sizes
- Consider practical significance
- Use confidence intervals

### Pitfall 4: P = .049 vs. P = .051
**Misconception:** These are meaningfully different because one crosses the .05 threshold.

**Reality:** These represent nearly identical evidence. The .05 threshold is arbitrary.

**Better approach:**
- Interpret p-values continuously as model-compatibility summaries, not stand-alone evidence scores
- Report exact p-values
- Consider context and prior evidence

### Pitfall 5: One-Tailed Tests Without Justification
**Misconception:** One-tailed tests are free extra power.

**Reality:** A one-sided test addresses a directional hypothesis; the opposite direction
need not be impossible. Choosing the tail after seeing data invalidates the nominal error rate.

**When appropriate:** Prespecify a directional decision and error criterion (for example,
a justified non-inferiority margin). Still report estimates, uncertainty, and possible harm.

## Multiple Comparisons Problems

### Pitfall 6: Multiple Testing Without Correction
**Problem:** For 20 independent tests of true nulls at alpha .05, the probability of at
least one false rejection is `1 - 0.95**20 = 0.6415` (about 64%). Dependence changes this value.

**Examples:**
- Testing many outcomes
- Testing many subgroups
- Conducting multiple interim analyses
- Testing at multiple time points

**Solutions:**
- Bonferroni correction (divide α by number of tests)
- False Discovery Rate (FDR) control
- Prespecify primary outcome
- Treat exploratory analyses as hypothesis-generating

Define the hypothesis family and error target first. FWER limits the probability of any
false rejection; FDR limits the expected false-discovery proportion (zero when there are
no discoveries). Neither is the probability that a particular discovery is false. A named
primary outcome does not resolve multiplicity across doses, time points, interim looks,
subgroups, or data-selected analysis choices.

### Pitfall 7: Subgroup Analysis Fishing
**Problem:** Testing many subgroups until finding significance.

**Why problematic:**
- Inflates false positive rate
- Often reported without disclosure
- A significant result in women and a non-significant result in men does not establish
  a difference between groups; estimate and test the interaction directly

**Solutions:**
- Prespecify subgroups
- Use interaction tests, not separate tests
- Require replication
- Correct for multiple comparisons

### Pitfall 8: Outcome Switching
**Problem:** Analyzing many outcomes, reporting only significant ones.

**Detection signs:**
- Secondary outcomes emphasized
- Incomplete outcome reporting
- Discrepancy between registration and publication

**Solutions:**
- Preregister all outcomes
- Report all planned outcomes
- Distinguish primary from secondary

## Sample Size and Power Issues

### Pitfall 9: Underpowered Studies
**Problem:** Small samples have low probability of detecting true effects.

**Consequences:**
- High false negative rate
- Among selected significant findings, the false-discovery fraction depends on power,
  prior prevalence of real effects, bias, and multiplicity; low power alone does not
  increase a correctly calibrated test's Type I error above its alpha
- Overestimated effect sizes (when significant)

**Solutions:**
- Conduct a priori power analysis
- Justify power or precision targets for the decision; 80-90% are conventions, not guarantees
- Use a meaningful effect and plausible variance; assess uncertainty in small pilot estimates

### Pitfall 10: Post-Hoc Power Analysis
**Problem:** Calculating "observed power" using the observed effect and the same test is
circular and uninformative. This does not prohibit design sensitivity calculations at an
independently justified effect size.

**Why useless:**
- Non-significant results always have low "post-hoc power"
- It recapitulates the p-value without new information

**Better approach:**
- Calculate confidence intervals
- Plan replication with adequate sample
- Conduct prospective power analysis for future studies

### Pitfall 11: Small Sample Fallacy
**Problem:** Trusting results from very small samples.

**Issues:**
- High sampling variability
- Outliers have large influence
- Distributional approximations may be unreliable; small n alone is not an assumption violation
- Confidence intervals very wide

**Guidelines:**
- There is no universal n = 30 validity threshold; count independent units and inspect precision
- Check assumptions carefully
- Choose methods for the estimand and design; non-parametric methods also have assumptions
- Replicate findings

## Effect Size Misunderstandings

### Pitfall 12: Ignoring Effect Size
**Problem:** Focusing only on significance, not magnitude.

**Why problematic:**
- Significance ≠ importance
- Can't compare across studies
- Doesn't inform practical decisions

**Solutions:**
- Always report effect sizes
- Report effects in interpretable original units or absolute risks; add standardized
  measures (Cohen's d, r, η²) when they answer the comparison of interest
- Interpret using field conventions
- Consider minimum clinically important difference

### Pitfall 13: Misinterpreting Standardized Effect Sizes
**Problem:** Treating Cohen's d = 0.5 as "medium" without context.

**Reality:**
- Field-specific norms vary
- Some fields have larger typical effects
- Real-world importance depends on context

**Better approach:**
- Compare to effects in same domain
- Consider practical implications
- Look at raw effect sizes too

### Pitfall 14: Confusing Explained Variance with Importance
**Problem:** "Only explains 5% of variance" = unimportant.

**Reality:**
- A small explained-variance fraction can still matter for an important outcome
- Complex phenomena have many small contributors
- Predictive accuracy ≠ causal importance

**Consideration:** Context matters more than percentage alone.

## Correlation and Causation

### Pitfall 15: Correlation Implies Causation
**Problem:** Inferring causation from correlation.

**Alternative explanations:**
- Reverse causation (B causes A, not A causes B)
- Confounding (C causes both A and B)
- Coincidence
- Selection bias

**Causal appraisal:** Specify the intervention/exposure contrast, population, and outcome.
Assess temporality, exchangeability/confounding, positivity, consistency, selection, and
measurement assumptions. Observational causal inference is possible under defensible
assumptions; randomization does not repair missing outcomes or post-randomization selection.

### Pitfall 16: Ecological Fallacy
**Problem:** Inferring individual-level relationships from group-level data.

**Example:** Countries with more chocolate consumption have more Nobel laureates doesn't mean eating chocolate makes you win Nobels.

**Why problematic:** Group-level correlations may not hold at individual level.

### Pitfall 17: Simpson's Paradox
**Problem:** Trend appears in groups but reverses when combined (or vice versa).

**Example:** Treatment appears worse overall but better in every subgroup.

**Cause:** Different group weights can reverse marginal and conditional associations.
The stratifying variable is not automatically a confounder; it may be a mediator or collider.

**Solution:** Choose adjustment from the causal question and temporal structure, not
from whichever stratification gives the preferred answer.

## Regression and Modeling Pitfalls

### Pitfall 18: Overfitting
**Problem:** Model fits sample data well but doesn't generalize.

**Causes:**
- Too many predictors relative to sample size
- Fitting noise rather than signal
- No cross-validation

**Solutions:**
- Use cross-validation with all learned preprocessing and tuning inside training folds
- Penalized regression (LASSO, ridge)
- Independent test set
- Simpler models

### Pitfall 19: Extrapolation Beyond Data Range
**Problem:** Predicting outside the range of observed data.

**Why dangerous:**
- Relationships may not hold outside observed range
- Increased uncertainty not reflected in predictions

**Solution:** Label extrapolation, justify transport/model assumptions, and assess
sensitivity. In-range predictions can also fail under population or measurement shifts.

### Pitfall 20: Ignoring Model Assumptions
**Problem:** Using statistical tests without checking assumptions.

**Common violations:**
- Incorrect distributional assumptions for the relevant errors/conditional outcomes;
  not all parametric models require normally distributed raw data
- Heteroscedasticity (unequal variances)
- Non-independence
- Linearity
- Rank deficiency or unstable coefficient estimation; some predictor correlation is allowed

**Solutions:**
- Check assumptions with diagnostics
- Use robust methods
- Transform data
- Use appropriate non-parametric alternatives

### Pitfall 21: Treating Non-Significant Covariates as Eliminating Confounding
**Problem:** "We controlled for X and it wasn't significant, so it's not a confounder."

**Reality:** Non-significant covariates can still be important confounders. Significance ≠ confounding.

**Solution:** Prespecify an appropriate adjustment set from causal knowledge; do not
select confounders by p-values or automatically adjust for mediators/colliders.

### Pitfall 22: Collinearity Masking Effects
**Problem:** When predictors are highly correlated, true effects may appear non-significant.

**Manifestations:**
- Large standard errors
- Unstable coefficients
- Sign changes when adding/removing variables

**Detection:**
- Variance Inflation Factors (VIF)
- Correlation matrices

**Solutions:**
- Remove redundant predictors
- Combine correlated variables
- Use regularization methods

Regularization may stabilize prediction but does not make a non-identifiable effect
identified by the data. Check design rank, parameter symmetries, profiles/sensitivity,
and dependence on constraints or priors. Good fit and convergence are insufficient.

## Specific Test Misuses

### Pitfall 23: Uncontrolled Pairwise Comparisons
**Problem:** Treating many unadjusted pairwise tests as one confirmatory analysis.

**Correct approach:** Prespecify contrasts and an appropriate familywise or other error
strategy. An omnibus ANOVA is useful for its own question but is not a universal prerequisite
for planned contrasts, and a significant omnibus test does not authorize all unadjusted pairs.

### Pitfall 24: Pearson Correlation for Non-Linear Relationships
**Problem:** Using Pearson's r for curved relationships.

**Why misleading:** r measures linear relationships only.

**Solutions:**
- Check scatterplots first
- Use Spearman's ρ for monotonic relationships
- Consider polynomial or non-linear models

### Pitfall 25: Chi-Square with Small Expected Frequencies
**Problem:** Relying on an asymptotic chi-square approximation with sparse expected counts.
The often-used count-of-five rule is a heuristic, not a universal validity boundary.

**Solutions:**
- Fisher's exact test
- Combine categories only for a prespecified substantive reason, not to obtain significance
- Increase sample size

### Pitfall 26: Paired vs. Independent Tests
**Problem:** Using independent samples test for paired data (or vice versa).

**Why wrong:**
- Ignoring real dependence can misestimate uncertainty in either direction
- Inventing pairs changes the estimand and may discard data or distort uncertainty

**Solution:** Match test to design.

## Confidence Interval Misinterpretations

### Pitfall 27: 95% CI = 95% Probability True Value Inside
**Misconception:** "95% chance the true value is in this interval."

**Reality:** For a correctly calibrated frequentist 95% interval procedure under its
assumptions, 95% of intervals across repetitions cover the fixed parameter. An individual
interval does not assign a 95% posterior probability to that parameter.

**Better reporting:** Give the estimate, interval, confidence level, assumptions, and
whether the interval excludes effects important to the scientific decision.

### Pitfall 28: Overlapping CIs = No Difference
**Problem:** Assuming overlapping confidence intervals mean no significant difference.

**Reality:** Overlapping CIs are less stringent than difference tests. Two CIs can overlap while the difference between groups is significant.

**Guideline:** Estimate the contrast and its interval directly, accounting for covariance.
Neither overlap heuristic substitutes for that calculation.

### Pitfall 29: Ignoring CI Width
**Problem:** Focusing only on whether CI includes zero, not precision.

**Why important:** Wide CIs indicate high uncertainty. "Significant" effects with huge CIs are less convincing.

**Consider:** Both significance and precision.

## Bayesian vs. Frequentist Confusions

### Pitfall 30: Mixing Bayesian and Frequentist Interpretations
**Problem:** Making Bayesian statements from frequentist analyses.

**Examples:**
- "Probability hypothesis is true" (Bayesian) from p-value (frequentist)
- "Evidence for no meaningful effect" from a non-significant test alone; frequentist
  equivalence tests can address prespecified bounds, not prove an exact point null

**Solution:**
- Be clear about framework
- Use Bayesian methods for Bayesian questions
- For Bayes factors, specify competing models and priors and examine prior sensitivity

### Pitfall 31: Ignoring Prior Probability
**Problem:** Treating all hypotheses as equally likely initially.

**Reality:** Extraordinary claims need extraordinary evidence. Prior plausibility matters.

**Consider:**
- Plausibility given existing knowledge
- Mechanism plausibility
- Base rates

## Data Transformation Issues

### Pitfall 32: Dichotomizing Continuous Variables
**Problem:** Splitting continuous variables at arbitrary cutoffs.

**Consequences:**
- Loss of information and power
- Arbitrary distinctions
- Discarding individual differences

**Exceptions:** Clinically meaningful cutoffs with strong justification.

**Better:** Model the continuous relationship, including nonlinear terms when justified;
adding arbitrary categories still loses information.

### Pitfall 33: Trying Multiple Transformations
**Problem:** Testing many transformations until finding significance.

**Why problematic:** Inflates Type I error, is a form of p-hacking.

**Better approach:**
- Prespecify transformations
- Use theory-driven transformations
- Correct for multiple testing if exploring

## Missing Data Problems

### Pitfall 34: Listwise Deletion by Default
**Problem:** Automatically deleting all cases with any missing data.

**Consequences:**
- Reduced power
- Potential bias if data not missing completely at random (MCAR)

**Better approaches:**
- Multiple imputation
- Maximum likelihood methods
- Analyze missingness patterns

### Pitfall 35: Ignoring Missing Data Mechanisms
**Problem:** Not considering why data are missing.

**Types:**
- MCAR: missingness independent of observed and unobserved data; deletion can lose precision
- MAR: conditional on the observed variables used, missingness is independent of missing
  values; imputation/likelihood methods still require correctly specified, compatible models
- MNAR: residual dependence on missing values; examine plausible sensitivity scenarios

**Solution:** Record reasons, timing, and assumptions. Observed missingness patterns cannot
establish MAR versus MNAR. Pool imputation uncertainty; single mean imputation is not a fix.

## Publication and Reporting Issues

### Pitfall 36: Selective Reporting
**Problem:** Only reporting significant results or favorable analyses.

**Consequences:**
- Literature appears more consistent than reality
- Meta-analyses biased
- Wasted research effort

**Solutions:**
- Preregistration
- Report all analyses
- Use reporting guidelines (CONSORT, PRISMA, etc.)

### Pitfall 37: Rounding to p < .05
**Problem:** Reporting exact p-values selectively (e.g., p = .049 but p < .05 for .051).

**Why problematic:** Obscures values near threshold, enables p-hacking detection evasion.

**Better:** Always report exact p-values.

### Pitfall 38: No Data Sharing
**Problem:** Not making data available for verification or reanalysis.

**Consequences:**
- Can't verify results
- Some independent checks or individual-participant-data analyses may be impossible;
  published aggregate estimates can still support an appropriate meta-analysis
- Hinders scientific progress

**Best practice:** Share data unless privacy concerns prohibit.

## Cross-Validation and Generalization

### Pitfall 39: No Cross-Validation
**Problem:** Testing model on same data used to build it.

**Consequence:** Overly optimistic performance estimates.

**Solutions:**
- Split data (train/test)
- K-fold cross-validation
- Independent validation sample

### Pitfall 40: Data Leakage
**Problem:** Information from test set leaking into training.

**Examples:**
- Normalizing before splitting
- Feature selection on full dataset
- Including temporal information

**Consequence:** Inflated performance metrics.

**Prevention:** Fit learned preprocessing only on the training portion of each fold; tune
within that boundary and reserve an untouched evaluation set. Split by independent subject,
site, batch, or time as the deployment question requires; technical replicates must not leak.

## Meta-Analysis Pitfalls

### Pitfall 41: Apples and Oranges
**Problem:** Combining studies with different designs, populations, or measures.

**Balance:** Need homogeneity but also comprehensiveness.

**Solutions:**
- Clear inclusion criteria
- Subgroup analyses
- Meta-regression for moderators

### Pitfall 42: Ignoring Publication Bias
**Problem:** Published studies overrepresent significant results.

**Consequences:** Overestimated effects in meta-analyses.

**Assessment:** Compare protocols/registries and reported outcomes; seek eligible unpublished
results. Funnel asymmetry indicates small-study effects, not necessarily publication bias.
Asymmetry tests generally need at least ten studies with varying precision and a method
appropriate to the effect measure; a negative test cannot exclude missing evidence.

**Sensitivity analysis:** Trim-and-fill, selection models, PET-PEESE, and p-curve have
different assumptions and targets. Do not describe adjusted estimates as recovered truth
or treat fail-safe N as a reliability certificate.

### Pitfall 43: Pseudoreplication and Changing Denominators
Repeated measurements, cells from one donor, or wells from one culture are not automatically
independent biological replicates. Identify assignment and sampling units; use an appropriate
hierarchical/repeated-measures analysis or justified aggregation. Report independent-unit n
separately from measurement count. A mean of group percentages differs from the pooled
numerator/denominator when group sizes differ; state weighting, evaluable counts, and exclusions.

## General Best Practices

1. **Preregister studies** - Distinguish confirmatory from exploratory
2. **Report transparently** - All analyses, not just significant ones
3. **Check assumptions** - Don't blindly apply tests
4. **Use appropriate tests** - Match test to data and design
5. **Report effect sizes** - Not just p-values
6. **Consider practical significance** - Not just statistical
7. **Replicate findings** - One study is rarely definitive
8. **Share data and code** - Enable verification
9. **Use confidence intervals** - Show uncertainty
10. **Think causally carefully** - Most research is correlational
