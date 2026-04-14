# Research Planning Template

Use this template before beginning any analysis. Fill in each section completely. Present the completed plan to the user and wait for confirmation before proceeding.

---

## Research Plan

### 1. Research Question

**Question**: [State the specific, testable research question in one sentence]

**Type**: [ ] Confirmatory (pre-specified hypothesis) / [ ] Exploratory (hypothesis-generating)

**PICOS Breakdown**:
- **Population**: [Who is being studied? Demographics, clinical status, inclusion/exclusion criteria]
- **Intervention/Exposure**: [What manipulation, variable, or condition is of interest?]
- **Comparison**: [What is the control or reference condition?]
- **Outcome**: [What is being measured? How is it operationalized?]
- **Study Design**: [Within-subjects, between-subjects, mixed, longitudinal, cross-sectional, etc.]

---

### 2. Hypotheses

**H1 (Primary hypothesis)**: [Specific, directional or non-directional prediction]

**H0 (Null hypothesis)**: [What would be true if H1 is wrong — typically no effect or no difference]

**Alternative explanations to rule out**: [List confounds, alternative mechanisms, or third-variable explanations that could produce the same pattern of results]

**Expected effect size**: [Based on prior literature or smallest effect of interest. Cite the source.] (Cohen, 1992; or domain-specific meta-analysis)

---

### 3. Method Selection

**Chosen method**: [Name the specific analysis — e.g., "2x3 mixed-effects ANOVA with Greenhouse-Geisser correction"]

**Why this method**:
- [Explain why this method matches the research question]
- [Explain why it is appropriate for the data type and design]

**Alternatives considered**:
| Alternative Method | Reason for Rejection |
|---|---|
| [e.g., Paired t-test] | [e.g., Design has more than two conditions] |
| [e.g., Non-parametric Kruskal-Wallis] | [e.g., Data are approximately normal with sufficient N] |
| [e.g., Bayesian mixed model] | [e.g., Frequentist approach is standard in the field and sufficient for the question] |

---

### 4. Expected Outcomes

**If H1 is supported**: [Describe the specific pattern — e.g., "A significant main effect of condition, F > critical value, p < .05, with a medium effect size (partial eta-squared > .06). Post-hoc comparisons would show that condition A > condition B > condition C."]

**If H0 is supported**: [Describe — e.g., "No significant effects, p > .05. Bayesian analysis would show BF01 > 3, providing moderate evidence for the null."]

**Ambiguous results would look like**: [Describe — e.g., "A marginally significant effect, p between .05 and .10, with a small effect size. Or a significant omnibus test but non-significant post-hoc comparisons."]

**Smallest effect of interest (SESOI)**: [State the minimum effect size that would be theoretically or practically meaningful, with justification]

---

### 5. Assumptions

| Assumption | How It Will Be Checked | Plan If Violated |
|---|---|---|
| [e.g., Normality of residuals] | [e.g., Shapiro-Wilk test, Q-Q plot] | [e.g., Use Welch's ANOVA or permutation test] |
| [e.g., Homogeneity of variance] | [e.g., Levene's test] | [e.g., Use Welch's correction] |
| [e.g., Sphericity (repeated measures)] | [e.g., Mauchly's test] | [e.g., Apply Greenhouse-Geisser correction] |
| [e.g., Independence of observations] | [e.g., Design review — are there nested factors?] | [e.g., Use mixed-effects model with appropriate random effects] |
| [e.g., No multicollinearity (regression)] | [e.g., VIF < 5] | [e.g., Remove or combine correlated predictors] |

---

### 6. Limitations

**Design limitations**:
- [e.g., "Convenience sample of university students limits generalizability"]
- [e.g., "Cross-sectional design cannot establish causation"]

**Measurement limitations**:
- [e.g., "Self-report measures are subject to demand characteristics"]
- [e.g., "EEG has limited spatial resolution"]

**Statistical limitations**:
- [e.g., "Sample size provides 80% power to detect d = 0.5 but may miss smaller effects"]
- [e.g., "Multiple comparisons across ROIs increase Type I error risk"]

---

### 7. Analysis Pipeline

Describe each step in order. For each step, note whether it involves a researcher degree of freedom.

| Step | Action | Researcher Degree of Freedom? | Justification |
|---|---|---|---|
| 1 | [e.g., Data import and quality check] | No | Standard preprocessing |
| 2 | [e.g., Artifact rejection: threshold = 100 uV] | Yes — threshold choice | [Cite source: Luck, 2014] |
| 3 | [e.g., Baseline correction: -200 to 0 ms] | Yes — window choice | [Cite source or convention] |
| 4 | [e.g., Compute grand averages per condition] | No | Standard |
| 5 | [e.g., Run ANOVA on mean amplitude in 300-500 ms window] | Yes — window choice | [Cite source for time window] |
| 6 | [e.g., Post-hoc pairwise comparisons with Bonferroni correction] | Yes — correction method | [Justify choice over alternatives] |

---

### 8. Decision Points Requiring User Input

List every point in the pipeline where the user must confirm before the agent proceeds.

- [ ] **Exclusion criteria**: Approve participant/trial exclusion before removing data
- [ ] **Assumption check results**: Review assumption test results and approve the chosen remedy (if any)
- [ ] **Model specification**: Confirm the final model before fitting
- [ ] **Multiple comparisons strategy**: Approve the correction method
- [ ] **Unexpected patterns**: If results are unexpected, discuss before interpreting
- [ ] **Post-hoc analyses**: Any exploration beyond the pre-specified plan must be approved and labeled

---

### 9. Preregistration Checklist (if confirmatory)

- [ ] Hypotheses written before data access
- [ ] Analysis plan specified before data access
- [ ] Primary outcome variable defined
- [ ] Sample size justified (power analysis or resource constraints documented)
- [ ] Exclusion criteria defined
- [ ] Correction for multiple comparisons specified
- [ ] Plan registered on a public platform (e.g., OSF, AsPredicted)

---

## Post-Analysis Checklist

After the analysis is complete, verify:

- [ ] Results compared to expected outcomes from Section 4
- [ ] All preregistered analyses reported (not just significant ones)
- [ ] Any deviations from the plan are documented and labeled
- [ ] Exploratory analyses are clearly separated from confirmatory analyses
- [ ] Effect sizes and confidence intervals reported alongside p-values
- [ ] Limitations from Section 6 revisited and updated if needed
- [ ] Raw data and analysis scripts prepared for sharing (where possible)
