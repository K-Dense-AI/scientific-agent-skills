# Sample Size Guide for Cognitive Science and Neuroscience

This guide provides detailed sample size recommendations organized by research modality, along with power analysis methods, tools, and reporting templates.

---

## 1. Power Analysis Methods by Design Type

### 1.1 Analytic (Closed-Form) Solutions

Best for simple, well-understood designs where statistical distributions are known.

| Design | Test | Tool / Function | Key Parameters |
|--------|------|----------------|----------------|
| Two-group comparison | Independent t-test | G*Power; `pwr::pwr.t.test()` in R | d, alpha, power, allocation ratio |
| Paired comparison | Paired t-test | G*Power; `pwr::pwr.t.test(type="paired")` | d_z, alpha, power |
| One-way k-group | One-way ANOVA | G*Power; `pwr::pwr.anova.test()` | f, k, alpha, power |
| Factorial ANOVA | F-test (interaction) | G*Power | f, df_numerator, df_denominator |
| Correlation | Pearson r | G*Power; `pwr::pwr.r.test()` | r, alpha, power |
| Regression | Multiple regression | G*Power; `pwr::pwr.f2.test()` | f², num_predictors, alpha, power |
| Proportion | Chi-square / Fisher | G*Power; `pwr::pwr.chisq.test()` | w, df, alpha, power |

**Converting between effect size metrics for analytic power analysis:**

- Cohen's f = d / 2 (for two groups)
- Cohen's f² = R²_change / (1 - R²_full)
- Partial eta² = f² / (1 + f²)

(See `effect-sizes.md` for the full conversion table; formulas from Borenstein et al., 2009; Lakens, 2013.)

### 1.2 Simulation-Based Power Analysis

Required for complex designs where analytic solutions are unavailable or inaccurate.

**When to use simulation:**
- Mixed-effects / multilevel models
- Non-normal data or ceiling/floor effects
- Complex repeated-measures designs with missing data
- Mediation / moderation analyses
- Machine learning classification accuracy
- Any design where the test statistic's distribution is not well-characterized

**Recommended tools:**

| Tool | Language | Best For | Reference |
|------|----------|----------|-----------|
| **simr** | R | Linear/generalized mixed-effects models | Green & MacLeod, 2016 |
| **Superpower** | R / Shiny | Factorial ANOVA, repeated measures | Lakens & Caldwell, 2021 |
| **paramtest** | R | General parameter recovery simulation | Hughes, 2017 |
| **fMRIpower** | MATLAB/R | fMRI group-level analyses | Mumford & Nichols, 2008 |
| **NeuroPowerTools** | Web app | fMRI power for whole-brain analyses | Durnez et al., 2016 |
| **PANGEA** | Web app | Mixed-effects models for psycholinguistics | Westfall, 2016 |

**Basic simulation workflow (pseudocode):**

```
for i in 1:10000:
 data = simulate_data(N=planned_N, effect=expected_effect, noise=expected_noise)
 result = run_analysis(data)
 store(result.p_value)

power = mean(p_values < alpha)
```

Minimum **10,000 iterations** recommended for stable power estimates (with 95% CI width < 1%; Morris et al., 2019).

### 1.3 Sensitivity Analysis

Always complement a prospective power analysis with a sensitivity analysis:

- **Question**: "Given my planned N, what is the minimum effect size I can detect with 80% power?"
- **Why**: Helps evaluate whether the detectable effect is theoretically meaningful
- **Tool**: All tools above support sensitivity analysis by solving for effect size given N and power

---

## 2. Sample Size Recommendations by Modality

### 2.1 Behavioral Studies

**Source basis**: Brysbaert (2019) "How many participants do we really need?" — comprehensive review of effect sizes in experimental psychology.

#### Between-Subjects Designs

| Expected Effect Size | Required N per Group (80% power) | Required N per Group (90% power) | Source |
|---------------------|--------------------------------|--------------------------------|--------|
| Large (d = 0.8) | n = 26 | n = 34 | G*Power calculation; Cohen, 1988 |
| Medium (d = 0.5) | n = 64 | n = 86 | G*Power calculation; Brysbaert, 2019 |
| Small-medium (d = 0.4) | n = 100 | n = 133 | G*Power calculation; Brysbaert, 2019 |
| Small (d = 0.2) | n = 394 | n = 527 | G*Power calculation; Cohen, 1988 |

> **Brysbaert's (2019) recommendation**: For typical between-subjects behavioral experiments, plan for d = 0.4 and recruit **n = 100 per group** for 80% power, or **n = 130 per group** for 90% power. The median published effect in psychology is d = 0.4 after correcting for publication bias.

#### Within-Subjects Designs

Within-subjects designs are more powerful due to the elimination of between-subject variance. The relevant effect size is d_z (standardized mean difference of within-subject difference scores).

| Expected d_z | Required N (80% power) | Required N (90% power) | Source |
|---|---|---|---|
| Large (d_z = 0.8) | n = 15 | n = 19 | G*Power calculation |
| Medium (d_z = 0.5) | n = 34 | n = 44 | G*Power calculation; Brysbaert, 2019 |
| Small-medium (d_z = 0.4) | n = 52 | n = 68 | G*Power calculation; Brysbaert, 2019 |
| Small (d_z = 0.2) | n = 199 | n = 265 | G*Power calculation |

> **Brysbaert's (2019) recommendation**: For typical within-subjects behavioral experiments, plan for d_z = 0.4 and recruit **n = 50-65** for 80% power. The within-subjects advantage typically converts a between-subjects d of 0.4 to d_z of 0.4-0.6, depending on the correlation between conditions.

#### Interaction Effects

Interaction effects are typically **half the size** of main effects in factorial designs (Brysbaert, 2019; Simonsohn, 2014). This means:

- If main effect d = 0.5, expect interaction d ≈ 0.25
- Sample sizes for interactions are **~4x larger** than for main effects
- **Recommendation**: N = 100-200 per cell for between-subjects interactions (Brysbaert, 2019)

### 2.2 EEG / ERP Studies

**Source basis**: Boudewyn et al. (2018), Clayson et al. (2019), Luck (2014).

#### Participant-Level Recommendations

| Effect Type | Recommended N | Basis | Source |
|---|---|---|---|
| Large ERP effect (e.g., P300 oddball, N400 strong violation) | n = 15-25 | d > 1.0, within-subjects | Boudewyn et al., 2018 |
| Medium ERP effect (e.g., N400 priming, LPP) | n = 25-40 | d = 0.5-1.0, within-subjects | Boudewyn et al., 2018 |
| Small ERP effect or between-group comparison | n = 40-80 | d = 0.3-0.5 | Clayson et al., 2019; Luck, 2014 |
| ERP individual differences / correlational | n = 50-100+ | r = 0.20-0.30 | Clayson et al., 2019 |
| Oscillatory power (within-subjects) | n = 20-40 | d = 0.5-1.0 | Cohen, 2014 (Analyzing Neural Time Series Data) |
| EEG clinical group comparison | n = 30-50 per group | d = 0.3-0.6 | Barry et al., 2003; Umbricht & Krljes, 2005 |

#### Trial-Level Considerations

ERP power depends on **both** participant N and trial count per condition. The signal-to-noise ratio of the ERP average improves as sqrt(trial count).

| Component | Minimum Trials per Condition | Recommended Trials | Source |
|---|---|---|---|
| P300 (oddball) | 20-30 | 36+ | Boudewyn et al., 2018; Cohen & Polich, 1997 |
| N400 | 20-30 | 40+ | Boudewyn et al., 2018 |
| ERN/Pe | 6-8 (minimum) | 15+ | Olvet & Hajcak, 2009; Pontifex et al., 2010 |
| N170 | 30-40 | 50+ | Rossion & Jacques, 2011 |
| MMN | 100+ (standard/deviant ratio) | 150+ deviants | Duncan et al., 2009 |
| LPP | 20-30 | 40+ | Hajcak et al., 2010 |
| N2pc | 100+ | 200+ | Luck, 2012 |

> **Key insight**: Increasing trial count is often more efficient than increasing participant count for ERP research, especially when the dominant source of noise is within-subject trial-to-trial variability (Luck, 2014, Ch. 4; Boudewyn et al., 2018).

#### EEG-Specific Power Analysis Approach

No standard power analysis tool exists for EEG/ERP. Recommended approaches:

1. **Simulation**: Generate synthetic ERP data with expected component amplitude, latency jitter, and noise level; simulate N participants with T trials; run planned analysis; repeat (Baker et al., 2021)
2. **Pilot-based**: Use pilot data to estimate within-condition variability; compute d_z; use standard paired t-test power formula (but account for measurement noise)
3. **Literature-based**: Use effect sizes from `effect-sizes.md` Section 2 with standard within-subjects formulas

### 2.3 fMRI Studies

**Source basis**: Cremers et al. (2017), Poldrack et al. (2017), Marek et al. (2022), Mumford & Nichols (2008).

#### Task-Based fMRI

| Analysis Type | Recommended N | Basis | Source |
|---|---|---|---|
| Within-subjects contrast (robust, e.g., motor/visual) | n = 20-30 | d > 1.0 in target region | Desmond & Glover, 2002 |
| Within-subjects contrast (cognitive, e.g., WM, inhibition) | n = 30-50 | d = 0.5-0.8 in target region | Cremers et al., 2017; Poldrack et al., 2017 |
| Between-group comparison (e.g., patient vs. control) | n = 30-50 per group | d = 0.5-0.8 | Button et al., 2013 |
| Whole-brain analysis (with FWE/FDR correction) | 1.5-2x ROI N | Correction reduces effective power | Mumford & Nichols, 2008 |
| Multivariate (MVPA) classification | n = 30-40+ | Depends on within-subject classification accuracy | Varoquaux, 2018 |

> **Whole-brain vs. ROI**: Whole-brain analyses with cluster-based or voxel-wise correction require larger samples than ROI analyses. A study powered for an ROI analysis (N = 25) may have only 30-50% power for whole-brain analysis of the same effect (Mumford & Nichols, 2008).

#### fMRI Individual Differences and Brain-Behavior Associations

| Analysis Type | Recommended N | Basis | Source |
|---|---|---|---|
| Brain-behavior correlation (single ROI) | n = 80-100 (minimum) | Expected r = 0.20-0.30 | Cremers et al., 2017 |
| Brain-wide association study (BWAS) | n = 1,000-2,000+ | Expected r = 0.05-0.15 with correction | Marek et al., 2022 |
| Structural brain-cognition correlation | n = 100+ | Expected r = 0.10-0.20 | Marek et al., 2022 |
| Functional connectivity-behavior | n = 200+ | Expected r = 0.05-0.15 | Marek et al., 2022 |
| Prediction / machine learning (cross-validated) | n = 200+ | Stability of prediction accuracy | Varoquaux, 2018 |

> **Marek et al. (2022) warning**: In the ABCD dataset (N ~ 4,000), brain-behavior effect sizes were nearly all r < 0.16. Studies with N < 100 produced inflated and unreplicable correlations. Brain-wide association studies require **thousands** of participants for reproducibility.

#### fMRI Power Analysis Tools

| Tool | What It Does | Source |
|---|---|---|
| **fMRIpower** | Estimates power for fMRI group analyses based on pilot data, accounting for temporal autocorrelation and spatial smoothness | Mumford & Nichols, 2008 |
| **NeuroPowerTools** | Web-based calculator for peak-level and cluster-level power in whole-brain analysis | Durnez et al., 2016 |
| **PowerMap** | Voxel-wise power maps from pilot fMRI data | Joyce & Hayasaka, 2012 |

#### fMRI-Specific Considerations

- **Scanner time constraints**: Each participant typically requires 1-2 hours. Budget recruitment accordingly.
- **Run structure**: More runs per participant can improve within-subject reliability (Roth et al., 2021)
- **Test-retest reliability**: Task fMRI has moderate reliability (ICC ≈ 0.30-0.60; Elliott et al., 2020), which attenuates observed correlations. Correct for unreliability when estimating required N for correlational analyses: r_observed = r_true * sqrt(ICC_x * ICC_y) (Spearman, 1904).

### 2.4 Clinical and Developmental Studies

**Source basis**: Button et al. (2013), Leucht et al. (2015), Mills & Tamnes (2014).

#### Clinical Group Comparisons

| Study Type | Recommended N per Group | Expected Effect | Source |
|---|---|---|---|
| Patient vs. control (large effect, e.g., Alzheimer's memory) | n = 15-25 | d = 1.0-2.0 | Backman et al., 2005 |
| Patient vs. control (medium effect, e.g., depression cognition) | n = 30-50 | d = 0.5-0.8 | Button et al., 2013; Snyder, 2013 |
| Patient vs. control (small effect, e.g., at-risk groups) | n = 80-100+ | d = 0.2-0.4 | Button et al., 2013 |
| Pharmacological RCT (active vs. placebo) | n = 50-100+ per arm | d = 0.3-0.5 (typical drug effect) | Leucht et al., 2015; Cipriani et al., 2018 |
| Psychotherapy RCT | n = 30-60 per arm | d = 0.5-1.0 | Hofmann & Smits, 2008 |

> **Recruitment reality**: Clinical populations have inherent recruitment constraints. When N cannot reach the ideal target, consider: (1) within-subjects designs to increase power, (2) Bayesian sequential designs that allow early stopping, (3) multi-site collaboration (Button et al., 2013).

#### Developmental Studies

| Design | Recommended N per Age Group | Consideration | Source |
|---|---|---|---|
| Cross-sectional age comparison (2 groups) | n = 25-40 per group | Between-groups, moderate effect | Mills & Tamnes, 2014 |
| Cross-sectional (3+ age groups) | n = 20-30 per group | One-way ANOVA, medium f | Mills & Tamnes, 2014 |
| Longitudinal (2 time points) | n = 30-50 (plan for 20-30% attrition) | Paired comparison, account for dropout | Mills & Tamnes, 2014 |
| Longitudinal (3+ time points) | n = 50-100+ (plan for cumulative attrition) | Growth curve modeling | Curran et al., 2010 |
| Accelerated longitudinal | n = 20-30 per cohort, 3+ cohorts | Mixed-effects model | Duncan et al., 2006 |

> **Attrition planning**: Developmental studies should recruit 20-30% above the target N to account for attrition, especially in longitudinal designs spanning years (Mills & Tamnes, 2014). For infant studies, expect 30-50% data loss from fussiness and motion (Stets et al., 2012).

---

## 3. Rules of Thumb Summary Table

A single-page reference for quick sample size estimation. **These are starting points, not substitutes for formal power analysis.**

| Modality | Design | Rule of Thumb N | Effect Size Assumption | Source |
|---|---|---|---|---|
| Behavioral | Between-groups, medium | 30-50 per group | d = 0.5-0.8 | Brysbaert, 2019 |
| Behavioral | Between-groups, small | 80-100 per group | d = 0.2-0.4 | Brysbaert, 2019 |
| Behavioral | Within-subjects, medium | 30-50 total | d_z = 0.4-0.6 | Brysbaert, 2019 |
| Behavioral | Interaction | 100-200 per cell | d = 0.2-0.3 (interaction) | Brysbaert, 2019; Simonsohn, 2014 |
| EEG/ERP | Within-subjects, large component | 15-25 | d > 1.0 | Boudewyn et al., 2018 |
| EEG/ERP | Within-subjects, medium component | 25-40 | d = 0.5-1.0 | Boudewyn et al., 2018 |
| EEG/ERP | Group comparison | 30-50 per group | d = 0.3-0.6 | Clayson et al., 2019 |
| fMRI | Task, within-subjects | 30-50 | d = 0.5-1.0 | Cremers et al., 2017; Poldrack et al., 2017 |
| fMRI | Task, between-groups | 30-50 per group | d = 0.5-0.8 | Button et al., 2013 |
| fMRI | Individual differences / correlation | 100+ (ideally 200+) | r = 0.10-0.20 | Marek et al., 2022 |
| fMRI | Brain-wide association (BWAS) | 1,000-2,000+ | r < 0.16 | Marek et al., 2022 |
| Clinical | Patient vs. control | 30-50 per group | d = 0.5-0.8 | Button et al., 2013 |
| Clinical | Pharmacological RCT | 50-100 per arm | d = 0.3-0.5 | Leucht et al., 2015 |
| Developmental | Cross-sectional | 25-40 per age group | d = 0.5-1.0 | Mills & Tamnes, 2014 |
| Developmental | Longitudinal | 50-100 (plan +30% attrition) | varies | Mills & Tamnes, 2014 |

---

## 4. Power Analysis Reporting for Preregistration

### 4.1 Required Elements

A complete power analysis report (for preregistration, grant applications, or methods sections) must include all of the following (Lakens, 2022):

1. **Effect size estimate and justification**
 - The specific effect size value used (e.g., d = 0.5, r = 0.20)
 - How it was obtained: meta-analysis, pilot study, SESOI, or literature
 - The specific source (author, year, study/meta-analysis)

2. **Statistical test planned**
 - The exact test to be used (e.g., paired t-test, mixed ANOVA, linear mixed model)
 - Any corrections for multiple comparisons

3. **Alpha level**
 - Typically 0.05 (two-tailed)
 - If one-tailed, justify the directional hypothesis
 - If adjusted (e.g., 0.025 for two primary outcomes), explain

4. **Target power level**
 - 80% (minimum acceptable) or 90% (recommended)
 - Justify the choice

5. **Resulting sample size**
 - The computed N from the power analysis
 - Adjustments for expected attrition, exclusion, or data quality loss

6. **Tool and method used**
 - Name and version of software (e.g., G*Power 3.1.9.7, simr R package v1.0.7)
 - For simulations: number of iterations, data generation model

7. **Sensitivity analysis** (recommended)
 - Minimum detectable effect at the planned N

### 4.2 Reporting Template

> **Power analysis**: We determined our target sample size based on [meta-analytic estimate / pilot data / smallest effect size of interest]. [Author (Year)] reported an effect size of [d/r/f = X] for [specific paradigm]. Using [G*Power 3.1 / simr / simulation], we computed the required sample size for a [specific test] with alpha = [.05], power = [.80/.90], [two-tailed/one-tailed]. The analysis indicated a minimum of N = [X] per [group/condition]. To account for an anticipated [X]% [attrition/exclusion] rate, we plan to recruit N = [adjusted X] participants [per group / total].
>
> A sensitivity analysis indicated that with our planned sample of N = [X], we would have 80% power to detect effects as small as [d/r = X], which is [smaller than / comparable to / larger than] the expected effect.

### 4.3 Common Mistakes in Power Analysis Reporting

| Mistake | Why It Is Wrong | Correct Approach |
|---|---|---|
| "Based on Cohen (1988), we used a medium effect size (d = 0.5)" | Cohen's benchmarks are generic, not calibrated to any specific paradigm | Use paradigm-specific meta-analytic estimates or SESOI |
| "Based on our pilot study (N = 12), d = 1.2" | Pilot effect sizes are unreliable and inflated | Use lower CI bound or apply shrinkage; prefer meta-analytic estimates (Albers & Lakens, 2018) |
| "We will recruit 20 participants" (no justification) | No power analysis reported | Conduct and report formal power analysis |
| Power analysis for main effect, but primary hypothesis is interaction | Interactions require ~4x the N of main effects | Power the study for the interaction (Brysbaert, 2019) |
| "G*Power indicated N = 34, so we will run 34" | Does not account for attrition or data quality exclusions | Add 10-30% buffer depending on modality |
| Post-hoc power analysis ("observed power") | Observed power is a direct function of the p-value; it provides no additional information | Use prospective power analysis; for non-significant results, report confidence intervals instead (Hoenig & Heisey, 2001) |

---

## 5. Software Reference

### 5.1 G*Power

- **Platform**: Windows, macOS (free)
- **Download**: https://www.psychologie.hhu.de/arbeitsgruppen/allgemeine-psychologie-und-arbeitspsychologie/gpower
- **Best for**: Simple designs (t-tests, ANOVA, correlations, regression)
- **Limitation**: Cannot handle mixed-effects models, non-standard designs
- **Reference**: Faul et al. (2007). G*Power 3: A flexible statistical power analysis program. *Behavior Research Methods*, 39(2), 175-191.

### 5.2 pwr (R package)

- **Install**: `install.packages("pwr")`
- **Best for**: Same as G*Power but scriptable and reproducible
- **Key functions**: `pwr.t.test()`, `pwr.r.test()`, `pwr.anova.test()`, `pwr.f2.test()`
- **Reference**: Champely, S. (2020). pwr: Basic functions for power analysis. R package.

### 5.3 simr (R package)

- **Install**: `install.packages("simr")`
- **Best for**: Power analysis for linear mixed-effects models (lme4)
- **Workflow**: Fit model to pilot data -> modify effect size -> `powerSim()` -> `powerCurve()`
- **Reference**: Green, P., & MacLeod, C. J. (2016). SIMR: An R package for power analysis of generalized linear mixed models by simulation. *Methods in Ecology and Evolution*, 7(4), 493-498.

### 5.4 Superpower (R package / Shiny app)

- **Install**: `install.packages("Superpower")`
- **Web app**: https://arcstats.io/shiny/anova-power/
- **Best for**: Factorial ANOVA designs, within/between/mixed, with exact or simulation-based power
- **Reference**: Lakens, D., & Caldwell, A. R. (2021). Simulation-based power analysis for factorial ANOVA designs. *Advances in Methods and Practices in Psychological Science*, 4(1).

### 5.5 fMRIpower

- **Platform**: MATLAB, R
- **Best for**: Power for fMRI second-level (group) analyses
- **Approach**: Uses pilot fMRI data to estimate effect variability; accounts for temporal autocorrelation
- **Reference**: Mumford, J. A., & Nichols, T. E. (2008). Power calculation for group fMRI studies accounting for arbitrary design and temporal autocorrelation. *NeuroImage*, 39(1), 261-268.

### 5.6 NeuroPowerTools

- **Platform**: Web-based (http://neuropowertools.org)
- **Best for**: Peak-level and cluster-level inference power for whole-brain fMRI
- **Reference**: Durnez, J., et al. (2016). Power and sample size calculations for fMRI studies based on the prevalence of active peaks. *bioRxiv*, 049429.

### 5.7 PANGEA

- **Platform**: Web-based
- **Best for**: Power analysis for psycholinguistic experiments with crossed random effects (participants and items)
- **Reference**: Westfall, J. (2016). PANGEA: Power ANalysis for GEneral Anova designs. Working paper.

---

## References

- Albers, C., & Lakens, D. (2018). When power analyses based on pilot data are biased. *JESP*, 74, 187-195.
- Backman, L., et al. (2005). Cognitive impairment in preclinical Alzheimer's disease. *Brain*, 128(9), 2026-2044.
- Baker, D. H., et al. (2021). Power contours: Optimising sample size and precision in experimental psychology and human neuroscience. *Psychological Methods*, 26(3), 295-314.
- Barry, R. J., et al. (2003). A review of electrophysiology in ADHD. *Clinical Neurophysiology*, 114(2), 184-198.
- Borenstein, M., et al. (2009). *Introduction to Meta-Analysis*. Wiley.
- Boudewyn, M. A., et al. (2018). How many trials does it take to get a significant ERP effect? *Psychophysiology*, 55(6), e13049.
- Brysbaert, M. (2019). How many participants do we really need? *Journal of Cognition*, 2(1), 16.
- Button, K. S., et al. (2013). Power failure. *Nature Reviews Neuroscience*, 14(5), 365-376.
- Cipriani, A., et al. (2018). Comparative efficacy of antidepressants. *The Lancet*, 391(10128), 1357-1366.
- Clayson, P. E., et al. (2019). Methodological reporting behavior and statistical power in ERP studies. *Psychophysiology*, 56(11), e13437.
- Cohen, M. X. (2014). *Analyzing Neural Time Series Data*. MIT Press.
- Cohen, D. B., & Polich, J. (1997). On the number of trials needed for P300. *International Journal of Psychophysiology*, 25(3), 249-255.
- Cremers, H. R., et al. (2017). The relation between statistical power and inference in fMRI. *PLoS ONE*, 12(11), e0184923.
- Curran, P. J., et al. (2010). The disaggregation of within-person and between-person effects in longitudinal models. *Annual Review of Psychology*, 61, 583-607.
- Desmond, J. E., & Glover, G. H. (2002). Estimating sample size in functional MRI (fMRI) neuroimaging studies. *Journal of Neuroscience Methods*, 118(2), 115-128.
- Duncan, C. C., et al. (2009). Event-related potentials in clinical research: Guidelines for eliciting, recording, and quantifying mismatch negativity, P300, and N400. *Clinical Neurophysiology*, 120(11), 1883-1908.
- Duncan, T. E., et al. (2006). *An Introduction to Latent Variable Growth Curve Modeling* (2nd ed.). Psychology Press.
- Durnez, J., et al. (2016). Power and sample size calculations for fMRI studies. *bioRxiv*, 049429.
- Elliott, M. L., et al. (2020). What is the test-retest reliability of common task-functional MRI measures? *Psychological Science*, 31(7), 792-806.
- Faul, F., et al. (2007). G*Power 3: A flexible statistical power analysis program. *Behavior Research Methods*, 39(2), 175-191.
- Green, P., & MacLeod, C. J. (2016). SIMR. *Methods in Ecology and Evolution*, 7(4), 493-498.
- Hajcak, G., et al. (2010). The late positive potential. In *Oxford Handbook of ERP Components*.
- Hoenig, J. M., & Heisey, D. M. (2001). The abuse of power: The pervasive fallacy of power calculations for data analysis. *American Statistician*, 55(1), 19-24.
- Hofmann, S. G., & Smits, J. A. (2008). Cognitive-behavioral therapy for adult anxiety disorders. *JCCP*, 76(2), 278-286.
- Hughes, J. (2017). paramtest: Run a function iteratively while varying parameters. R package.
- Joyce, K. E., & Hayasaka, S. (2012). Development of PowerMap: A software package for statistical power calculation in neuroimaging studies. *Neuroinformatics*, 10(4), 351-365.
- Lakens, D. (2013). Calculating and reporting effect sizes. *Frontiers in Psychology*, 4, 863.
- Lakens, D. (2022). Sample size justification. *Collabra: Psychology*, 8(1), 33267.
- Lakens, D., & Caldwell, A. R. (2021). Simulation-based power analysis for factorial ANOVA designs. *AMPPS*, 4(1).
- Leucht, S., et al. (2015). Putting the efficacy of psychiatric and general medicine medication into perspective. *BJP*, 200(2), 97-106.
- Luck, S. J. (2012). Electrophysiological correlates of the focusing of attention. In *Cognitive Electrophysiology of Attention*.
- Luck, S. J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.). MIT Press.
- Marek, S., et al. (2022). Reproducible brain-wide association studies require thousands of individuals. *Nature*, 603, 654-660.
- Mills, K. L., & Tamnes, C. K. (2014). Methods and considerations for longitudinal structural brain imaging analysis across development. *Developmental Cognitive Neuroscience*, 9, 172-190.
- Morris, T. P., et al. (2019). Using simulation studies to evaluate statistical methods. *Statistics in Medicine*, 38(11), 2074-2102.
- Mumford, J. A., & Nichols, T. E. (2008). Power calculation for group fMRI studies. *NeuroImage*, 39(1), 261-268.
- Noble, S., et al. (2019). A decade of test-retest reliability of functional connectivity. *NeuroImage*, 203, 116157.
- Olvet, D. M., & Hajcak, G. (2009). The stability of error-related brain activity with increasing numbers of trials. *Psychophysiology*, 46(5), 957-961.
- Poldrack, R. A., et al. (2017). Scanning the horizon. *Nature Reviews Neuroscience*, 18(2), 115-126.
- Pontifex, M. B., et al. (2010). On the number of trials necessary for stabilization of error-related brain activity across the life span. *Psychophysiology*, 47(4), 767-773.
- Rossion, B., & Jacques, C. (2011). The N170. In *Oxford Handbook of ERP Components*.
- Roth, Z. N., et al. (2021). Natural scene statistics account for the representation of scene categories in human visual cortex. *Neuron*, 109(8), 1451-1461.
- Simonsohn, U. (2014). No-way interactions. Working paper. Available at SSRN.
- Snyder, H. R. (2013). Major depressive disorder and executive function. *Neuropsychology*, 27(2), 152-169.
- Spearman, C. (1904). The proof and measurement of association between two things. *American Journal of Psychology*, 15(1), 72-101.
- Stets, M., et al. (2012). Infant ERP data quality. *Developmental Neuropsychology*, 37(3), 209-225.
- Umbricht, D., & Krljes, S. (2005). Mismatch negativity in schizophrenia: A meta-analysis. *Schizophrenia Research*, 76(1), 1-23.
- Varoquaux, G. (2018). Cross-validation failure: Small sample sizes lead to large error bars. *NeuroImage*, 180, 68-77.
- Westfall, J. (2016). PANGEA: Power ANalysis for GEneral Anova designs. Working paper.
- Wykes, T., et al. (2011). A meta-analysis of cognitive remediation for schizophrenia. *AJP*, 168(5), 472-485.
