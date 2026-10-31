# Common Biases in Scientific Research

These are prompts to examine mechanisms, not evidence of misconduct. Connect a concern
to the particular result and its likely consequences; use the matching formal tool when
needed. Sources and current tool scopes are in [review_sources.md](review_sources.md).

## Cognitive Biases Affecting Researchers

### 1. Confirmation Bias
**Description:** Tendency to search for, interpret, and recall information that confirms preexisting beliefs.

**Manifestations:**
- Designing studies that can only support the hypothesis
- Interpreting ambiguous results as supportive
- Remembering hits and forgetting misses
- Selectively citing literature that agrees

**Mitigation:**
- Preregister hypotheses and analysis plans
- Actively seek disconfirming evidence
- Use blinded data analysis
- Consider alternative hypotheses

### 2. Hindsight Bias (I-Knew-It-All-Along Effect)
**Description:** After an event, people perceive it as having been more predictable than it actually was.

**Manifestations:**
- HARKing (Hypothesizing After Results are Known)
- Claiming predictions that weren't made
- Underestimating surprise at results

**Mitigation:**
- Document predictions before data collection
- Preregister studies
- Distinguish exploratory from confirmatory analyses

### 3. Publication Bias (File Drawer Problem)
**Description:** Positive/significant results are more likely to be published than negative/null results.

**Manifestations:**
- Literature appears to support effects that don't exist
- Overestimation of effect sizes
- Inability to estimate true effects from published literature

**Mitigation:**
- Publish null results
- Use preregistration and registered reports
- Conduct systematic reviews with grey literature
- When appropriate, examine funnel asymmetry as a small-study-effects diagnostic;
  asymmetry does not uniquely diagnose publication bias

### 4. Anchoring Bias
**Description:** Over-reliance on the first piece of information encountered.

**Manifestations:**
- Initial hypotheses unduly influence interpretation
- First studies in a field set expectations
- Pilot data biases main study interpretation

**Mitigation:**
- Consider multiple initial hypotheses
- Evaluate evidence independently
- Use structured decision-making

### 5. Availability Heuristic
**Description:** Overestimating likelihood of events based on how easily examples come to mind.

**Manifestations:**
- Overemphasizing recent or dramatic findings
- Neglecting base rates
- Anecdotal evidence overshadowing statistics

**Mitigation:**
- Consult systematic reviews, not memorable papers
- Consider base rates explicitly
- Use statistical thinking, not intuition

### 6. Bandwagon Effect
**Description:** Adopting beliefs because many others hold them.

**Manifestations:**
- Following research trends without critical evaluation
- Citing widely-cited papers without reading
- Accepting "textbook knowledge" uncritically

**Mitigation:**
- Evaluate evidence independently
- Read original sources
- Question assumptions

### 7. Belief Perseverance
**Description:** Maintaining beliefs even after evidence disproving them.

**Manifestations:**
- Defending theories despite contradictory evidence
- Finding ad hoc explanations for discrepant results
- Dismissing replication failures

**Mitigation:**
- Explicitly consider what evidence would change your mind
- Update beliefs based on evidence
- Distinguish between theories and ego

### 8. Outcome Bias
**Description:** Judging decisions based on outcomes rather than the quality of the decision at the time.

**Manifestations:**
- Valuing lucky guesses over sound methodology
- Dismissing good studies with null results
- Rewarding sensational findings over rigorous methods

**Mitigation:**
- Evaluate methodology independently of results
- Value rigor and transparency
- Recognize role of chance

## Experimental and Methodological Biases

### 9. Selection Bias
**Description:** Selection can impair representativeness or create biased exposure-outcome
associations by conditioning on participation, survival, or another common effect. These
are related but distinct problems; a nonrepresentative sample is not automatically biased
for every within-sample contrast.

**Types:**
- **Sampling bias:** Non-random sample
- **Attrition bias:** Systematic dropout
- **Volunteer bias:** Self-selected participants differ
- **Berkson's bias:** Conditioning on hospitalization influenced by both exposure and
  disease can create an association (collider bias)
- **Survivorship bias:** Only examining "survivors"

**Detection:**
- Compare characteristics of participants vs. target population
- Analyze dropout patterns
- Consider who is missing from the sample

**Mitigation:**
- Random sampling
- Track and analyze non-responders
- Use strategies to minimize dropout
- Report participant flow diagrams

### 10. Observer Bias (Detection Bias)
**Description:** Researchers' expectations influence observations or measurements.

**Manifestations:**
- Measuring outcomes differently across groups
- Interpreting ambiguous results based on group assignment
- Unconsciously cueing participants

**Mitigation:**
- Blinding of observers/assessors
- Objective, automated measurements
- Standardized protocols
- Inter-rater reliability checks

### 11. Performance Bias
**Description:** Systematic differences in care provided to comparison groups.

**Manifestations:**
- Treating experimental group differently
- Providing additional attention to one group
- Differential adherence to protocols

**Mitigation:**
- Standardize all procedures
- Blind participants and providers
- Use placebo controls
- Monitor protocol adherence

### 12. Measurement Bias (Information Bias)
**Description:** Systematic errors in how variables are measured.

**Types:**
- **Recall bias:** Systematic differences in accuracy of recall
- **Social desirability bias:** Responding in socially acceptable ways
- **Interviewer bias:** Interviewer's characteristics affect responses
- **Instrument bias:** Measurement tools systematically err

**Mitigation:**
- Use validated, objective measures
- Standardize data collection
- Blind participants to hypotheses
- Verify self-reports with objective data

### 13. Confounding Bias
**Description:** Effect of extraneous variable mixed with the variable of interest.

**Examples:**
- Age confounding relationship between exercise and health
- Socioeconomic status confounding education and outcomes
- Indication bias in treatment studies

**Mitigation:**
- Randomization
- Matching
- Statistical adjustment
- Stratification
- Restriction

Choose adjustment using the causal question and temporal structure. Adjusting every
measured variable can induce collider bias or remove part of the effect through a mediator;
matching and regression do not eliminate unmeasured confounding by themselves.

### 14. Reporting Bias
**Description:** Selective reporting of results.

**Types:**
- **Outcome reporting bias:** Selectively reporting outcomes
- **Time-lag bias:** Delayed publication of negative results
- **Language bias:** Publishing positive results in English
- **Citation bias:** Preferentially citing positive studies

**Mitigation:**
- Preregister all outcomes
- Report all planned analyses
- Distinguish primary from secondary outcomes
- Use study registries

### 15. Spectrum Bias
**Description:** Test performance varies depending on the spectrum of disease severity in the sample.

**Manifestations:**
- Diagnostic tests appearing more accurate in extreme cases
- Treatment effects differing by severity

**Mitigation:**
- Test in representative samples
- Report performance across disease spectrum
- Avoid unrepresentative two-gate diagnostic samples of extreme cases and healthy controls
  when the target is accuracy among patients presenting for testing

### 16. Lead-Time Bias
**Description:** Apparent survival benefit due to earlier detection, not improved outcomes.

**Example:**
- Screening detecting disease earlier makes survival seem longer, even if death occurs at same age

**Mitigation:**
- Measure mortality, not just survival from diagnosis
- Use randomized screening trials
- Consider length-time and overdiagnosis bias

### 17. Length-Time Bias
**Description:** Screening disproportionately detects slower-growing, less aggressive cases.

**Example:**
- Slow-growing cancers detected more often than fast-growing ones, making screening appear beneficial

**Mitigation:**
- Randomized trials with mortality endpoints
- Consider disease natural history

### 18. Response Bias
**Description:** Systematic pattern in how participants respond.

**Types:**
- **Acquiescence bias:** Tendency to agree
- **Extreme responding:** Always choosing extreme options
- **Neutral responding:** Avoiding extreme responses
- **Demand characteristics:** Responding based on perceived expectations

**Mitigation:**
- Mix positive and negative items
- Use multiple response formats
- Blind participants to hypotheses
- Use behavioral measures

## Statistical and Analysis Biases

### 19. P-Hacking (Data Dredging)
**Description:** Manipulating data or analyses until significant results emerge.

**Manifestations:**
- Collecting data until significance reached
- Testing multiple outcomes, reporting only significant ones
- Trying multiple analysis methods
- Excluding "outliers" to reach significance
- Subgroup analyses until finding significance

**Detection:**
- Clustering just below .05 can motivate further checks; it is not proof of p-hacking
- Many researcher degrees of freedom
- Undisclosed analyses
- Fishing expeditions

**Mitigation:**
- Preregister analysis plans
- Report all analyses conducted
- Correct for multiple comparisons
- Distinguish exploratory from confirmatory

### 20. HARKing (Hypothesizing After Results are Known)
**Description:** Presenting post hoc hypotheses as if they were predicted a priori.

**Why problematic:**
- Inflates apparent evidence
- Conflates exploration with confirmation
- Misrepresents the scientific process

**Mitigation:**
- Preregister hypotheses
- Clearly label exploratory analyses
- Require replication of unexpected findings

### 21. Base Rate Neglect
**Description:** Ignoring prior probability when evaluating evidence.

**Example:**
- With prevalence 1%, sensitivity 95%, and specificity 95%, the positive predictive value
  is `0.95*0.01 / (0.95*0.01 + 0.05*0.99) = 0.1610` (16.1%). Overall "accuracy"
  alone is insufficient; this teaching calculation assumes these quantities apply to
  the tested population.

**Mitigation:**
- Always consider base rates/prior probability
- Use Bayesian reasoning
- Report positive and negative predictive values

### 22. Regression to the Mean
**Description:** Extreme measurements tend to be followed by less extreme ones.

**Manifestations:**
- Treatment effects in extreme groups may be regression artifacts
- "Sophomore slump" in high performers

**Mitigation:**
- Use control groups
- Consider natural variation
- Don't select based on extreme baseline values without controls

### 23. Texas Sharpshooter Fallacy
**Description:** Selecting data after seeing patterns, like shooting arrows then drawing targets around clusters.

**Manifestations:**
- Finding patterns in random data
- Subgroup analyses selected post hoc
- Geographic clustering studies without correction

**Mitigation:**
- Prespecify hypotheses
- Correct for multiple comparisons
- Replicate findings in independent data

## Reducing Bias: Best Practices

### Study Design
1. Randomization
2. Blinding specified by role and information concealed
3. Control groups
4. Adequate sample size
5. Preregistration

### Data Collection
1. Standardized protocols
2. Validated instruments
3. Objective measures when possible
4. Multiple observers/raters
5. Complete data collection

### Analysis
1. Analysis aligned to assignment/adherence estimand, with explicit missing-data assumptions
2. Prespecified analyses
3. Appropriate statistical tests
4. Multiple comparison corrections
5. Sensitivity analyses

### Reporting
1. Complete transparency
2. CONSORT, PRISMA, or similar guidelines
3. Report all outcomes
4. Distinguish exploratory from confirmatory
5. Share data and code

### Meta-Level
1. Adversarial collaboration
2. Replication studies
3. Open science practices
4. Peer review
5. Systematic reviews
