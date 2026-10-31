# Evidence Hierarchy and Quality Assessment

## Traditional Evidence Hierarchy (Medical/Clinical)

This is a teaching shorthand for some intervention questions, not a universal ranking.
Choose designs for the question: prevalence, prognosis, diagnostic accuracy, harms, and
mechanisms have different evidence needs. A review synthesizes its underlying studies;
meta-analysis alone does not increase certainty. Reporting quality, risk of bias,
applicability, and certainty must be assessed separately. Current sources are recorded in
[review_sources.md](review_sources.md).

### Level 1: Systematic Reviews and Meta-Analyses
**Description:** Comprehensive synthesis of all available evidence on a question.

**Strengths:**
- Combines multiple studies for greater power
- Reduces impact of single-study anomalies
- Can identify patterns across studies
- May quantify a pooled effect if studies and estimands can meaningfully be combined

**Weaknesses:**
- Quality depends on included studies ("garbage in, garbage out")
- Publication bias can distort findings
- Heterogeneity may make pooling inappropriate
- Can mask important differences between studies

**Critical evaluation:**
- Was search comprehensive (multiple databases, grey literature)?
- Were inclusion criteria appropriate and prespecified?
- Was study quality assessed?
- Was heterogeneity explored?
- Were missing studies/results sought in registries and protocols? If funnel-plot methods
  were appropriate, were alternative explanations for asymmetry considered? Fail-safe N
  is not a reliable assessment of missing-evidence bias.
- Were appropriate statistical methods used?

### Level 2: Randomized Controlled Trials (RCTs)
**Description:** Experimental studies with random assignment to conditions.

**Strengths:**
- Strong design for estimating intervention effects when implemented and analysed appropriately
- Balances prognostic factors in expectation, not necessarily in each realized sample
- Minimizes selection bias
- Enables causal inference

**Weaknesses:**
- May not be ethical or feasible
- Artificial settings may limit generalizability
- Often short-term with selected populations
- Expensive and time-consuming

**Critical evaluation:**
- Was randomization adequate (sequence generation, allocation concealment)?
- Was blinding implemented (participants, providers, assessors)?
- Was sample size adequate (power analysis)?
- Was intention-to-treat analysis used?
- Was attrition rate acceptable and balanced?
- Are results generalizable?

### Level 3: Cohort Studies
**Description:** Observational studies following groups over time.

**Types:**
- **Prospective:** Follow forward from exposure to outcome
- **Retrospective:** Look backward at existing data

**Strengths:**
- Can study multiple outcomes
- Establishes temporal sequence
- Can calculate incidence and relative risk
- More feasible than RCTs for many questions

**Weaknesses:**
- Susceptible to confounding
- Selection bias possible
- Attrition can bias results
- Causal interpretation requires explicit identification assumptions and sensitivity analysis

**Critical evaluation:**
- Were cohorts comparable at baseline?
- Was exposure measured reliably?
- Was follow-up adequate and complete?
- Were potential confounders measured and controlled?
- Was outcome assessment blinded to exposure?

### Level 4: Case-Control Studies
**Description:** Compare people with outcome (cases) to those without (controls), looking back at exposures.

**Strengths:**
- Efficient for rare outcomes
- Relatively quick and inexpensive
- Can study multiple exposures
- Useful for generating hypotheses

**Weaknesses:**
- Usually cannot estimate absolute incidence from sampled case/control counts alone
- Susceptible to recall bias
- Selection of controls is challenging
- Causal interpretation depends on the sampling design and control of relevant biases

**Critical evaluation:**
- Were cases and controls defined clearly?
- Were controls appropriate (same source population)?
- Was matching appropriate?
- How was exposure ascertained (records vs. recall)?
- Were potential confounders controlled?
- Could recall bias explain findings?

### Level 5: Cross-Sectional Studies
**Description:** Snapshot observation at single point in time.

**Strengths:**
- Quick and inexpensive
- Can assess prevalence
- Useful for hypothesis generation
- Can study multiple outcomes and exposures

**Weaknesses:**
- Cannot establish temporal sequence
- Cannot determine causation
- Prevalence-incidence bias
- Survival bias

**Critical evaluation:**
- Was sample representative?
- Were measures validated?
- Could reverse causation explain findings?
- Are confounders acknowledged?

### Level 6: Case Series and Case Reports
**Description:** Description of observations in clinical practice.

**Strengths:**
- Can identify new diseases or effects
- Hypothesis-generating
- Details rare phenomena
- Quick to report

**Weaknesses:**
- No control group
- Descriptive uncertainty may be estimable; uncontrolled counts do not identify a comparative effect
- Highly susceptible to bias
- Cannot establish causation or frequency

**Use:** Primarily for hypothesis generation and clinical description.

### Level 7: Expert Opinion
**Description:** Statements by recognized authorities.

**Strengths:**
- Synthesizes experience
- Useful when no research available
- May integrate multiple sources

**Weaknesses:**
- Subjective and potentially biased
- May not reflect current evidence
- Appeal to authority fallacy risk
- Individual expertise varies

**Use:** Lowest level of evidence; should be supported by data when possible.

## Nuances and Limitations of Traditional Hierarchy

### When Lower-Level Evidence Can Be Strong
1. **Well-designed observational studies** with:
   - Large effects that plausible bias cannot explain (size alone does not establish this)
   - Dose-response relationships
   - Consistent findings across contexts
   - Biological plausibility
   - Explicitly justified confounding and selection assumptions, with sensitivity analyses

2. **Multiple converging lines of evidence** from different study types

3. **Natural experiments** approximating randomization

### When Higher-Level Evidence Can Be Weak
1. **Poor-quality RCTs** with:
   - Inadequate randomization
   - High attrition
   - No blinding when feasible
   - Design, conduct, or reporting problems associated with sponsor influence

2. **Biased meta-analyses**:
   - Publication bias
   - Selective inclusion
   - Inappropriate pooling
   - Poor search strategy

3. **Not addressing the right question**:
   - Wrong population
   - Wrong comparison
   - Wrong outcome
   - Too artificial to generalize

## Alternative: GRADE System

GRADE assesses certainty in a **body of evidence for a specified outcome and comparison**.
Choose the relevant GRADE application, target population and decision threshold; retain
effect estimates and uncertainty alongside domain judgments. The current GRADE Book is
being released progressively; consult its updated chapters and the handbook only for
sections not yet replaced.

For intervention effects, the traditional approach starts randomized evidence at high and
non-randomized evidence at low certainty. When using the ROBINS-I-integrated approach,
start at high and assess bias from confounding/selection explicitly, usually rating down
substantially. Do not penalize lack of randomization twice. Specify the approach before
rating. Consider risk of bias, inconsistency, indirectness, imprecision, and missing-evidence
bias, and justify any large-effect, dose-response, or opposing-confounding considerations.

These levels are judgments about certainty, not numerical probabilities or recommendation strength:

### High Certainty
**Definition:** High confidence that the effect is on the specified side of a threshold
or within the target range.

**Characteristics:**
- No important unresolved concerns across the applicable certainty domains
- Neither an RCT label nor a large effect alone establishes high certainty

### Moderate Certainty
**Definition:** Moderate confidence in that target; the effect could be in another range.

**Downgrades from high:**
- Some risk of bias
- Inconsistency across studies
- Indirectness (different populations/interventions)
- Imprecision relative to the specified threshold/range of important effects
- Publication bias suspected

### Low Certainty
**Definition:** Limited confidence in that target; the effect may be in a different range.

**Downgrades:**
- Serious limitations in above factors
- Observational studies without special strengths

### Very Low Certainty
**Definition:** Very little confidence in that target; substantial uncertainty remains
about the effect's range.

**Characteristics:**
- Very serious limitations
- Evidence may be too sparse or indirect to support an effect estimate at all; do not
  invent a numerical estimate or GRADE rating for an unsupported opinion
- Multiple serious flaws

Document threshold magnitudes and their rationale. For intervention decisions use absolute
effects with an appropriate baseline risk and its uncertainty. Rate down/up only when a
concern changes confidence in the target range; do not double-count the same underlying
problem across domains. Have independent assessors reconcile formal judgments.

## Study Quality Assessment Criteria

### Internal Validity (Bias Control)
**Questions:**
- Was randomization adequate?
- Was allocation concealed?
- Were groups similar at baseline?
- Was blinding implemented?
- Could missingness depend on the unobserved outcome? Low or balanced attrition alone
  does not establish low risk of bias.
- Was intention-to-treat used?
- Were all outcomes reported?

### External Validity (Generalizability)
**Questions:**
- Is sample representative of target population?
- Are inclusion/exclusion criteria too restrictive?
- Is setting realistic?
- Are results applicable to other populations?
- Are effects consistent across subgroups?

### Statistical Conclusion Validity
**Questions:**
- Was sample size adequate (power)?
- Were statistical tests appropriate?
- Were assumptions checked?
- Were effect sizes and confidence intervals reported?
- Were multiple comparisons addressed?
- Was analysis prespecified?

### Construct Validity (Measurement)
**Questions:**
- Were measures validated and reliable?
- Was outcome defined clearly and appropriately?
- Were assessors blinded?
- Were exposures measured accurately?
- Was timing of measurement appropriate?

## Critical Appraisal Tools

### For Different Study Types

**RCTs:**
- Cochrane RoB 2 — recommended for randomized trials in Cochrane intervention reviews;
  assess a result, use the correct parallel/cluster/crossover variant, and retain reasons
- PEDro Scale — used for physiotherapy trials; its score is not interchangeable with RoB 2
- Legacy RoB 1 and Jadad ratings in older reviews should be identified as such

**Observational Studies:**
- ROBINS-I applies to non-randomized **intervention effects**, not every observational question.
  Specify the 2016 version or November 2025 ROBINS-I V2 draft for follow-up/cohort studies;
  do not combine version-specific signalling questions or domains.
- Newcastle-Ottawa Scale has cohort and case-control forms; record the chosen form and
  item judgments, not an unexplained universal good/poor star cutoff.

**Diagnostic Studies:**
- QUADAS-3 (current tool v1.2, published February 2026) assesses bias and applicability
  for individual accuracy estimates against defined synthesis questions and an ideal
  test accuracy trial. QUADAS-2 is the previous version.

**Systematic Reviews:**
- AMSTAR 2 appraises systematic reviews of healthcare interventions; assess critical
  weaknesses rather than calculating a total score.
- PRISMA 2020 assesses reporting completeness; it is not a risk-of-bias instrument.

**Design-specific general appraisal:**
- CASP supplies separate checklists for supported study designs; select the matching one.
  Do not assume every design has the same domains or numerical score.

## Domain-Specific Considerations

### Basic Science Research
**Consider together, without imposing a fixed ranking:**
1. Multiple convergent lines of evidence
2. Mechanistic understanding
3. Reproducible experiments
4. Established theoretical framework

**Key considerations:**
- Replication essential
- Mechanistic plausibility
- Consistency across model systems
- Convergence of methods

### Psychological Research
**Additional concerns:**
- Replication crisis
- Publication bias particularly problematic
- Small effect sizes often expected
- Cultural context matters
- Measures often indirect (self-report)

**Strong evidence includes:**
- Preregistered studies
- Large samples
- Multiple measures
- Behavioral (not just self-report) outcomes
- Cross-cultural replication

### Epidemiology
**Causal inference frameworks:**
- Bradford Hill criteria
- Rothman's causal pies
- Directed Acyclic Graphs (DAGs)

**Strong observational evidence:**
- Dose-response relationships
- Temporal consistency
- Biological plausibility
- Specificity can inform interpretation but is not necessary for causation
- Consistency across populations
- Large effects assessed against plausible confounding and selection mechanisms

### Social Sciences
**Challenges:**
- Complex interventions
- Context-dependent effects
- Measurement challenges
- Ethical constraints on RCTs

**Strengthening evidence:**
- Mixed methods
- Natural experiments
- Instrumental variables
- Regression discontinuity designs
- Multiple operationalizations

## Synthesizing Evidence Across Studies

### Consistency
**Strong evidence:**
- Multiple studies, different investigators
- Different populations and settings
- Different research designs converge
- Different measurement methods

**Weak evidence:**
- Single study
- Only one research group
- Conflicting results
- Publication bias evident

### Biological/Theoretical Plausibility
**Strengthens evidence:**
- Known mechanism
- Consistent with other knowledge
- Dose-response relationship
- Coherent with animal/in vitro data

**Weakens evidence:**
- No plausible mechanism
- Contradicts established knowledge
- Biological implausibility

### Temporality
**Essential for causation:**
- Cause must precede effect
- Cross-sectional studies cannot establish
- Reverse causation must be ruled out

### Specificity
**Moderate indicator:**
- Specific cause → specific effect strengthens causation
- But lack of specificity doesn't rule out causation
- Most causes have multiple effects

### Strength of Association
**Strong evidence:**
- Large effects with plausible confounding, selection, and measurement explanations examined
- Dose-response relationships
- All-or-none effects

**Caution:**
- Small effects may still be real
- Large effects can still be confounded

## Red Flags in Evidence Quality

### Study Design Red Flags
- No control group
- Self-selected participants
- No randomization when feasible
- No blinding when feasible
- Very small sample
- Inappropriate statistical tests

### Reporting Red Flags
- Selective outcome reporting
- No study registration/protocol
- Missing methodological details
- No conflicts of interest statement
- Cherry-picked citations
- Results don't match methods

### Interpretation Red Flags
- Causal language from correlational data
- Claiming "proof"
- Ignoring limitations
- Overgeneralizing
- Spinning negative results
- Post hoc rationalization

### Context Red Flags
- Industry funding without independence
- Single study in isolation
- Contradicts preponderance of evidence
- No replication
- Published in predatory journal
- Press release before peer review

## Practical Decision Framework

### When Evaluating Evidence, Ask:

1. **What type of study is this?** (Design)
2. **How well was it conducted?** (Quality)
3. **What does it actually show?** (Results)
4. **How likely is bias?** (Internal validity)
5. **Does it apply to my question?** (External validity)
6. **How does it fit with other evidence?** (Context)
7. **Are the conclusions justified?** (Interpretation)
8. **What are the limitations?** (Uncertainty)

### Making Decisions with Imperfect Evidence

Certainty does not itself authorize changing practice or policy. A high-certainty estimate
may show negligible benefit or important harm. Low-certainty evidence may still inform a
decision when delay or alternatives carry costs. A separate evidence-to-decision process
considers absolute benefits/harms, values, resources, equity, acceptability, and feasibility.
State whose decision and setting are involved; an appraisal is not an individual clinical
recommendation. Identify the information most likely to change the decision.

### When Evidence is Conflicting

**Strategies:**
1. Weight by study quality
2. Look for systematic differences (population, methods)
3. Consider publication bias
4. Update with most recent, rigorous evidence
5. Conduct/await systematic review
6. Consider if question is well-formed

## Communicating Evidence Strength

**Avoid:**
- Absolute certainty ("proves")
- False balance (equal weight to unequal evidence)
- Ignoring uncertainty
- Cherry-picking studies

**Better:**
- Quantify uncertainty
- Describe strength of evidence
- Acknowledge limitations
- Present range of evidence
- Distinguish established from emerging findings
- Be clear about what is/isn't known
