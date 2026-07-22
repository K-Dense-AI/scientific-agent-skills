# Statistical Analysis Guide for Self-Paced Reading Data

This reference covers the statistical analysis pipeline specific to self-paced reading (SPR) data, from raw reading times to final inference. SPR data have distinctive properties (right-skewed distributions, nested structure, spillover autocorrelation) that require analysis approaches different from standard cognitive tasks.

---

## 1. Data Cleaning Pipeline

Apply these steps in order before any statistical analysis.

### 1.1 Exclude Participants Based on Comprehension Accuracy

**Criterion**: Exclude participants with overall comprehension question accuracy **below 80%** (Jegerski, 2014; common practice across the SPR literature).

**Rationale**: Low accuracy indicates the participant was not reading for comprehension. Their reading times are not interpretable as measures of linguistic processing.

**Implementation**:
- Calculate accuracy across all comprehension questions (experimental + filler)
- Log the number of excluded participants and their accuracy rates
- Report the exclusion criterion and how many participants were removed

### 1.2 Exclude Trials with Incorrect Comprehension Responses

**Convention**: For experimental items that have a comprehension question, exclude the reading time data from trials where the participant answered incorrectly.

**Rationale**: An incorrect answer suggests the participant may not have been attending to the sentence on that trial. Including those RTs adds noise (Jegerski, 2014).

**Note**: This step is debated. Some researchers argue that excluding incorrect trials biases the sample toward easier items. If you choose not to exclude incorrect trials, report this decision and consider analyzing accuracy as a separate dependent variable.

### 1.3 Apply Absolute RT Cutoffs

Remove reading times that are implausibly fast or slow. These reflect motor errors (accidental button presses) or distraction (forgetting to press), not linguistic processing.

| Cutoff | Value | Rationale |
|---|---|---|
| **Lower bound** | **100 ms** | Below 100 ms, it is physically impossible to have read and processed a word; this reflects an accidental button press (Rayner, 1998; Jegerski, 2014) |
| **Upper bound** | **2000-3000 ms** | Above 2000-3000 ms for a single word, the participant was likely distracted or disengaged. The exact value depends on population: use 2000 ms for L1 adults, 2500-3000 ms for L2 or clinical populations (Jegerski, 2014; Marsden, Thompson, & Plonsky, 2018) |

**Important**: Define these cutoffs a priori (before looking at the data). Report the cutoffs and the percentage of data removed. Removing more than **5-10%** of data points suggests a problem with the task or participant population (Ratcliff, 1993).

### 1.4 Apply SD-Based Trimming (Optional, Used with ANOVAs)

If using traditional ANOVA rather than mixed-effects models, apply SD-based trimming after absolute cutoffs:

| Method | Procedure | Typical Threshold |
|---|---|---|
| **By-participant, by-condition** | For each participant in each condition, remove RTs beyond +/- **2.5 SD** from that participant's condition mean | 2.5 SD (Ratcliff, 1993) |
| **By-participant only** | For each participant, remove RTs beyond +/- **2.5 SD** from their overall mean | 2.5 SD |

**Note on mixed-effects models**: When using linear mixed-effects models (LMMs), aggressive SD-based trimming is often unnecessary because LMMs are more robust to outliers than ANOVAs. If using LMMs, apply absolute cutoffs (Step 1.3) and consider log-transforming RTs (Step 2) instead of SD trimming. Alternatively, remove data points with residuals exceeding +/- 2.5 SD from the fitted model (Baayen, Davidson, & Bates, 2008).

---

## 2. RT Transformation

Raw reading times are right-skewed (bounded at zero, with a long positive tail). This violates the normality assumption of linear models.

### 2.1 Log-Transformation

**Recommended as the default**: Apply natural log (ln) or log base 10 transformation to all reading times.

```
log_RT = log(RT)
```

**Advantages**:
- Reduces right skew, making residuals more normally distributed
- Converts multiplicative effects to additive ones (appropriate because many reading time effects are proportional, not absolute)
- Standard in the SPR literature (Baayen et al., 2008)

**Disadvantage**: Effects are on the log scale, making raw millisecond interpretation less intuitive. Report back-transformed means for descriptive statistics.

### 2.2 Inverse (Reciprocal) Transformation

**Alternative**: Use -1000/RT (negative reciprocal scaled by 1000).

```
inv_RT = -1000 / RT
```

**Advantages**:
- Often produces better normality than log transformation for reading time data (Box & Cox, 1964)
- Recommended by some psycholinguists (e.g., Vasishth & Nicenboim, 2016)

**Disadvantage**: Even less intuitive than log RT. Negative values mean that larger (less negative) values correspond to faster reading.

### 2.3 No Transformation (With Caveats)

If using generalized linear mixed models (GLMMs) with a log link or Gamma family, no transformation of the raw RTs is needed because the model handles the skew internally.

```
glmer(RT ~ condition + (1 | subject) + (1 | item), family = Gamma(link = "identity"), data = d)
```

This approach is increasingly recommended (Lo & Andrews, 2015) but requires more computational resources and expertise to implement correctly.

---

## 3. Statistical Models

### 3.1 Linear Mixed-Effects Models (Recommended)

Use linear mixed-effects models with crossed random effects for subjects and items (Baayen, Davidson, & Bates, 2008). This is the current standard for SPR analysis.

#### Minimal Model Structure

```r
library(lme4)

model <- lmer(log_RT ~ condition +
 (1 + condition | subject) +
 (1 + condition | item),
 data = data)
```

#### Random Effects Structure

The random effects structure is critical and often a source of error:

| Structure | When to Use | Reference |
|---|---|---|
| **Maximal** (random intercepts + slopes for all fixed effects, by subject and item) | Default recommendation; prevents anti-conservative p-values | Barr, Levy, Scheepers, & Tily (2013) |
| **Parsimonious** (remove random correlations first, then slopes with near-zero variance) | When maximal model fails to converge | Bates, Kliegl, Vasishth, & Baayen (2015); Matuschek, Kliegl, Vasishth, Baayen, & Bates (2017) |
| **Intercepts only** | Only as a last resort; may be anti-conservative | Baayen et al. (2008) |

**Common convergence issues**: SPR data often produce convergence warnings with maximal models. Follow this simplification hierarchy:
1. Remove random correlations (use `||` instead of `|` in lme4 formula)
2. Remove random slopes with the smallest variance estimate
3. If still non-convergent, use a different optimizer (e.g., `bobyqa` with increased iterations)

#### Covariates to Include

| Covariate | Why | How to Include |
|---|---|---|
| **Word length (characters)** | Longer words take longer to read (~30-40 ms/character; Ferreira & Clifton, 1986) | `scale(nchar)` as fixed effect |
| **Log word frequency** | Less frequent words are slower (~20-40 ms per log unit; Rayner, 1998) | `scale(log_freq)` as fixed effect |
| **Trial order** | Reading speed increases with practice across the experiment | `scale(trial_number)` as fixed effect |
| **Previous word RT** | Controls for spillover autocorrelation | `scale(lag_RT)` as fixed effect (but see Section 5) |
| **Word position in sentence** | First and last words have inflated RTs | Include as fixed effect or exclude those positions |

### 3.2 Traditional ANOVA (By-Subjects and By-Items)

If using ANOVA, you must run two separate analyses:

1. **By-subjects (F1)**: Average RTs per condition for each participant; participant is the random factor
2. **By-items (F2)**: Average RTs per condition for each item; item is the random factor

Both F1 and F2 must be significant for the effect to be considered reliable (Clark, 1973).

**Limitations**: By-subjects + by-items ANOVA is less powerful than LMMs, cannot handle unbalanced data (e.g., from trial exclusion), and does not generalize simultaneously over both subjects and items (Baayen et al., 2008). Use LMMs when possible.

### 3.3 Bayesian Mixed-Effects Models

For studies where null effects are theoretically informative:

```r
library(brms)

model <- brm(log_RT ~ condition +
 (1 + condition | subject) +
 (1 + condition | item),
 data = data,
 family = lognormal())
```

**Advantages**: Provides evidence for null effects (via Bayes factors or posterior distributions), handles convergence issues better than frequentist LMMs, and naturally handles the lognormal distribution of RTs.

**Reference**: Nicenboim & Vasishth (2016); Vasishth, Mertzen, Jager, & Rabe (2019).

---

## 4. Residual Reading Time Analysis

Residual reading times (Ferreira & Clifton, 1986; Trueswell, Tanenhaus, & Garnsey, 1994) remove variance due to word length (and optionally frequency), isolating variance due to the experimental manipulation.

### Procedure

1. For each participant, fit a simple linear regression predicting RT from word length (in characters) across all filler items:

 ```r
 participant_model <- lm(RT ~ nchar, data = fillers_for_this_participant)
 ```

2. Use this regression to predict expected RT for each word in the experimental items:

 ```r
 predicted_RT <- predict(participant_model, newdata = experimental_items)
 ```

3. Compute residual RT:

 ```r
 residual_RT <- observed_RT - predicted_RT
 ```

4. Analyze residual RTs as the dependent variable.

### When to Use

- When critical regions differ in word length across conditions and matching is impossible
- As a robustness check alongside raw or log RT analyses
- When you want to ensure that your effect is not driven by word length differences

### When NOT to Use

- When word length is perfectly matched across conditions (residualization is unnecessary)
- When using LMMs with word length as a covariate (this achieves the same goal within the model)
- As the sole analysis -- always report at least one analysis on the raw or log-transformed scale alongside residual RTs

---

## 5. Spillover Region Analysis

Spillover is the hallmark of SPR data. Effects at a critical word frequently appear on subsequent words, not the critical word itself (Mitchell, 2004; Rayner, 1998).

### Which Regions to Analyze

| Region | Label | Typical Pattern |
|---|---|---|
| Critical word (CW) | CW or R0 | Effect may or may not appear here |
| CW + 1 | Spillover 1 | Often the largest effect in SPR |
| CW + 2 | Spillover 2 | Effect may still be present |
| CW + 3 | Spillover 3 | Rarely significant, but worth checking |
| Sentence-final word | Wrap-up | Inflated by wrap-up; do NOT treat as spillover |

### Analysis Approaches

#### Approach A: Region-by-Region Analysis

Run a separate statistical model for each region (CW, CW+1, CW+2). This is the most common approach.

**Advantage**: Simple, easy to interpret.
**Disadvantage**: Inflates familywise error rate due to multiple comparisons. Apply correction (e.g., report whether effects survive Bonferroni or Holm correction across regions).

#### Approach B: Region as a Factor

Include region (CW, CW+1, CW+2) as a factor in a single model:

```r
model <- lmer(log_RT ~ condition * region +
 (1 + condition * region | subject) +
 (1 + condition * region | item),
 data = data)
```

**Advantage**: Controls familywise error; the condition x region interaction directly tests whether the effect changes across regions.
**Disadvantage**: Model complexity; may not converge with full random effects.

#### Approach C: Including Previous-Region RT as a Covariate

Include the RT from the previous region as a predictor to control for spillover autocorrelation:

```r
model <- lmer(log_RT ~ condition + scale(prev_RT) +
 (1 + condition | subject) +
 (1 + condition | item),
 data = data)
```

**Advantage**: Partials out autocorrelation; a significant condition effect in this model indicates processing difficulty above and beyond what is explained by the previous word.
**Disadvantage**: Removes some variance that is part of the effect of interest; use with caution and always report alongside the model without this covariate.

---

## 6. Handling Missing Data

### Sources of Missing Data in SPR

| Source | Typical Rate | How to Handle |
|---|---|---|
| **Timeouts** (if using a response deadline) | 1-5% | Treat as missing; do not substitute an arbitrary value. Report the timeout rate per condition -- if it differs between conditions, the timeout rate itself may be informative |
| **Incorrect comprehension trials** | 5-15% | See Section 1.2 above |
| **RT trimming** (absolute + SD cutoffs) | 2-5% | Already handled by the trimming pipeline |
| **Technical errors** (software crashes, key misregistration) | <1% | Exclude those trials |

### What NOT to Do

- **Do not replace missing RTs with the condition mean.** This artificially reduces variance and inflates power.
- **Do not replace missing RTs with the participant mean.** Same problem.
- **Do not use listwise deletion** (removing the entire sentence if one word is missing). This is wasteful. LMMs handle missing data naturally by estimating from available observations.

### What to Do

- Use **linear mixed-effects models**, which handle unbalanced data and missing observations without requiring imputation (Baayen et al., 2008).
- **Report** the amount and pattern of missing data. If missing data is concentrated in one condition (e.g., more timeouts in the harder condition), this is informative and should be discussed.

---

## 7. Reporting Standards

### What to Report in an SPR Analysis

| Element | Details |
|---|---|
| **RT trimming criteria** | Lower cutoff (e.g., 100 ms), upper cutoff (e.g., 2500 ms), and any SD-based trimming |
| **Percentage of data excluded** | At each trimming step and in total |
| **Number of participants excluded** | With reason (accuracy threshold, technical issues) |
| **RT transformation** | Log, inverse, or none; justify the choice |
| **Model specification** | Full model formula including random effects structure |
| **Convergence** | Whether the model converged; if simplification was needed, what was removed |
| **Results by region** | Report statistics for the critical region AND at least 2 spillover regions |
| **Effect direction** | Report mean RTs (not just test statistics) for each condition at each region |
| **Descriptive statistics** | Mean RT per condition per region with standard errors, ideally plotted |
| **Comprehension accuracy** | Overall and by condition |

### Visualization

Plot mean reading times by region and condition. The standard figure is a **region-by-region plot** with:
- X-axis: word position or region label
- Y-axis: mean reading time (ms) -- use raw ms even if the analysis used log RT, for interpretability
- Separate lines for each condition
- Error bars: standard error of the mean (computed across participants)

This plot allows readers to see the time course of the effect, including whether it appears at the critical word, spills over, or is delayed.

---

## 8. Effect Size Benchmarks

SPR effects are typically smaller than effects in speeded choice tasks (e.g., Stroop, lexical decision). Calibrate your expectations:

| Effect Type | Typical Effect Size (ms) | Example |
|---|---|---|
| **Garden-path effect** (strong) | **40-100 ms** at disambiguation point | Reduced relative clause (Ferreira & Clifton, 1986) |
| **Plausibility mismatch** | **30-80 ms** | Implausible agent/patient (Garnsey et al., 1997) |
| **Agreement violation** | **20-60 ms**, often mostly in spillover | Number attraction (Pearlmutter et al., 1999) |
| **Frequency effect** | **20-40 ms per log unit** | High vs. low frequency words (Rayner, 1998) |
| **Subtle pragmatic effect** | **10-30 ms** | Scalar implicature, presupposition (Bott & Noveck, 2004) |

These benchmarks should inform power analysis. For a typical 30 ms effect with within-participant SD of ~200 ms, you need approximately **24-32 items per condition** and **40+ participants** for 80% power in a mixed-effects model (Brysbaert & Stevens, 2018).

---

## References

- Baayen, R. H., Davidson, D. J., & Bates, D. M. (2008). Mixed-effects modeling with crossed random effects for subjects and items. *Journal of Memory and Language, 59*, 390-412.
- Barr, D. J., Levy, R., Scheepers, C., & Tily, H. J. (2013). Random effects structure for confirmatory hypothesis testing. *Journal of Memory and Language, 68*, 255-278.
- Bates, D., Kliegl, R., Vasishth, S., & Baayen, H. (2015). Parsimonious mixed models. arXiv:1506.04967.
- Bott, L., & Noveck, I. A. (2004). Some utterances are underinformative. *Journal of Memory and Language, 51*, 437-457.
- Box, G. E. P., & Cox, D. R. (1964). An analysis of transformations. *Journal of the Royal Statistical Society, Series B, 26*, 211-252.
- Brysbaert, M., & Stevens, M. (2018). Power analysis and effect size in mixed effects models. *Journal of Cognition, 1*(1), 9.
- Clark, H. H. (1973). The language-as-fixed-effect fallacy. *Journal of Verbal Learning and Verbal Behavior, 12*, 335-359.
- Ferreira, F., & Clifton, C. (1986). The independence of syntactic processing. *Journal of Memory and Language, 25*, 348-368.
- Garnsey, S. M., Pearlmutter, N. J., Myers, E., & Lotocky, M. A. (1997). The contributions of verb bias and plausibility to the comprehension of temporarily ambiguous sentences. *Journal of Memory and Language, 37*, 58-93.
- Jegerski, J. (2014). Self-paced reading. In J. Jegerski & B. VanPatten (Eds.), *Research methods in second language psycholinguistics*. Routledge.
- Lo, S., & Andrews, S. (2015). To transform or not to transform: Using generalized linear mixed models to analyse reaction time data. *Frontiers in Psychology, 6*, 1171.
- Marsden, E., Thompson, S., & Plonsky, L. (2018). A methodological synthesis of self-paced reading in second language research. *Applied Psycholinguistics, 39*, 861-904.
- Matuschek, H., Kliegl, R., Vasishth, S., Baayen, H., & Bates, D. (2017). Balancing Type I error and power in linear mixed models. *Journal of Memory and Language, 94*, 305-315.
- Mitchell, D. C. (2004). On-line methods in language processing. In M. Carreiras & C. Clifton (Eds.), *The on-line study of sentence comprehension*. Psychology Press.
- Nicenboim, B., & Vasishth, S. (2016). Statistical methods for linguistic research. *Language, Cognition and Neuroscience, 31*, 748-767.
- Pearlmutter, N. J., Garnsey, S. M., & Bock, K. (1999). Agreement processes in sentence comprehension. *Journal of Memory and Language, 41*, 427-456.
- Ratcliff, R. (1993). Methods for dealing with reaction time outliers. *Psychological Bulletin, 114*, 510-532.
- Rayner, K. (1998). Eye movements in reading and information processing. *Psychological Bulletin, 124*, 372-422.
- Trueswell, J. C., Tanenhaus, M. K., & Garnsey, S. M. (1994). Semantic influences on parsing. *Journal of Memory and Language, 33*, 285-318.
- Vasishth, S., Mertzen, D., Jager, L. A., & Rabe, A. (2019). The statistical significance filter leads to overoptimistic expectations of replicability. *Journal of Memory and Language, 108*, 104027.
- Vasishth, S., & Nicenboim, B. (2016). Statistical methods for linguistic research: Foundational ideas - Part I. *Language and Linguistics Compass, 10*, 349-369.
