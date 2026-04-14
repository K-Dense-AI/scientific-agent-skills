# Experimental Design Principles for Cognitive Psychology

This reference covers the core principles of designing rigorous cognitive experiments, including design type selection, trial estimation, practice and catch trials, counterbalancing, and confound control.

---

## 1. Between-Subjects vs. Within-Subjects Design

### Decision Framework

| Factor | Favors Within-Subjects | Favors Between-Subjects |
|---|---|---|
| **Individual differences** | Large individual variability in baseline performance (e.g., RT tasks with 200+ ms between-person spread) (Keppel & Wickens, 2004, Ch. 17) | Individual differences are small relative to the manipulation effect |
| **Carry-over / order effects** | No carry-over effects (or easily counterbalanced) | Conditions produce lasting carryover (e.g., learning, strategy shifts, emotional priming) |
| **Demand characteristics** | Participants cannot easily detect the hypothesis by seeing all conditions | Transparent contrast between conditions increases demand (e.g., explicit priming manipulation) |
| **Sample size efficiency** | Greater statistical power per participant: within-subjects designs remove between-subject variance, often requiring ~50% fewer participants for equivalent power (Maxwell & Delaney, 2004, Ch. 11) | When carry-over is unavoidable, between-subjects avoids contamination |
| **Number of conditions** | Few conditions (2-4); more conditions increase fatigue and session length | Many conditions (>4) that would create excessively long within-subjects sessions |
| **Practical constraints** | Participants are scarce (clinical populations, special populations) | Large participant pool is available |

### When to Use Mixed (Split-Plot) Designs

Use a mixed design when one factor must be between-subjects (e.g., patient group vs. control) and another varies within-subjects (e.g., stimulus condition). Mixed designs are standard in clinical cognitive research (Keppel & Wickens, 2004, Ch. 19).

### Statistical Considerations

- **Within-subjects advantage**: The error term in repeated-measures ANOVA excludes between-subject variance, increasing F values. This advantage is captured by the correlation among conditions: the higher the correlation, the greater the power gain (Maxwell & Delaney, 2004, Ch. 11).
- **Sphericity**: Within-subjects designs with 3+ levels require checking Mauchly's test; use Greenhouse-Geisser or Huynh-Feldt correction when violated (epsilon < 0.75 use G-G, otherwise H-F) (Girden, 1992).
- **Effect size for within-subjects**: Report Cohen's d_z (= mean_diff / SD_diff) for paired comparisons, not d_s (Lakens, 2013).

---

## 2. Trial Number Estimation

### General Principles

The number of trials per condition is determined by:
1. The expected **effect size** of the manipulation
2. The **within-subject variability** (trial-to-trial noise)
3. The desired **statistical power** (conventionally 0.80; Cohen, 1988)

### Effect Size Benchmarks for Common Paradigms

| Paradigm | Typical Effect Size (Cohen's d) | Recommended Minimum Trials/Condition | Source |
|---|---|---|---|
| Stroop interference | d ~ **1.0-1.5** (large) | **40-60** | MacLeod (1991); Hedge et al. (2018) |
| Flanker congruency | d ~ **0.8-1.2** (large) | **40-60** | Hedge et al. (2018) |
| Posner validity effect | d ~ **0.5-1.0** (medium-large) | **40-80** | Fan et al. (2002) |
| Visual search slope | d ~ **0.5-0.8** (medium) | **20-40 per set size** | Wolfe (1998) |
| Attentional blink | d ~ **0.8-1.5** (large) | **50-80 per lag** | Martens & Wyble (2010) |
| Priming (semantic) | d ~ **0.3-0.6** (small-medium) | **40-80** | Lucas (2000); McNamara (2005) |
| Switch cost (RT) | d ~ **0.5-1.0** (medium-large) | **80-100** | Monsell (2003) |
| Working memory capacity (K) | r ~ **0.80** (reliability) | **150+ total** (~75 change, 75 no-change) | Rouder et al. (2011) |
| Stop-signal (SSRT) | ICC ~ **0.7** at 200 trials | **160-200 total** (~40-50 stop trials) | Verbruggen et al. (2019) |
| N-back d' | d ~ **0.5-1.0** per load level | **40-60 per load** | Owen et al. (2005) |

### Baker et al. (2021) Power Contour Approach

Rather than focusing solely on participant N, Baker et al. (2021, *Psychological Methods*) showed that increasing trials per condition also improves power by reducing per-participant measurement noise:
- Each participant's mean is estimated more precisely with more trials, reducing the sample SD
- The effective Cohen's d = M / sigma_s, where sigma_s decreases with sqrt(k) trials per participant
- **Practical implication**: Doubling trials per condition can be as beneficial as substantially increasing participant N, especially when between-subject variance is moderate

### Sample Size (Participants) Rules of Thumb

- **Two-condition within-subjects** (d = 0.4, alpha = .05, power = .80): **~52 participants** (Brysbaert & Stevens, 2018)
- **Two-group between-subjects** (d = 0.5, alpha = .05, power = .80): **~64 per group** (128 total) (Cohen, 1988)
- **2 x 2 interaction** (f = 0.25, power = .80): **~100-180 participants** depending on design (Brysbaert & Stevens, 2018)
- For published cognitive psychology studies, the median effect size is approximately **d = 0.4** (Open Science Collaboration, 2015; Camerer et al., 2018)

### Sensitivity Analysis

Always conduct a sensitivity analysis alongside a priori power analysis:
- Given your planned N and alpha, what is the minimum detectable effect size?
- Use G*Power (Faul et al., 2007) or the R package `pwr` (Champely, 2020) for formal computation

---

## 3. Practice Trials

### Purpose

Practice trials serve to:
1. **Familiarize** participants with the task, stimuli, and response mappings
2. **Stabilize** performance by allowing learning of the task interface to reach asymptote before experimental trials begin
3. **Identify** participants who fail to understand the task (accuracy below chance in practice)

### Guidelines

| Parameter | Recommendation | Rationale / Source |
|---|---|---|
| **Minimum practice trials** | **10-20 trials** for simple tasks (e.g., button-press RT); **20-40 trials** for complex tasks (e.g., task-switching, N-back) | Performance typically stabilizes within 10-20 trials for simple RT tasks (Luce, 1986); complex tasks require more |
| **Practice block accuracy criterion** | **>80% accuracy** before proceeding; re-administer practice if not met | Ensures task comprehension (standard in many labs; see Verbruggen et al., 2019 for stop-signal) |
| **Use different stimuli** | Practice items should differ from experimental items to avoid pre-exposure effects | Prevents item-specific learning from contaminating experimental data |
| **Gradual difficulty increase** | For adaptive tasks (e.g., N-back), start at the easiest level and increase | Standard protocol in N-back studies (Jaeggi et al., 2010) |
| **Feedback during practice** | Provide accuracy feedback during practice trials; **remove feedback** during experimental trials (unless feedback is the manipulation) | Feedback accelerates learning during practice but can alter strategy during experiment (Kluger & DeNisi, 1996) |
| **Warm-up block** | Include a brief warm-up block (~5-10 trials) at the start of each new experimental block to re-engage task set | Reduces start-of-block instability; first 2-5 trials of each block are typically excluded from analysis (Monsell, 2003) |

### When to Exclude More Practice

- **Tasks with steep learning curves** (e.g., psychophysical staircase, IGT): May need **50-100** familiarization trials before stable performance (Watson & Pelli, 1983)
- **Dual-task paradigms**: Require separate practice on each component task, then combined practice
- **EEG/fMRI**: Include extra practice outside the scanner/cap to reduce artifact from novelty-related movements

---

## 4. Catch Trials

### Purpose

Catch trials (also called "blank trials," "no-go trials," or "no-target trials") prevent anticipatory or habitual responses and ensure that participants are genuinely processing the stimuli.

### Types and Proportions

| Type | Description | Recommended Proportion | Source |
|---|---|---|---|
| **No-target catch trials** | Trials with no target present; participant should withhold response | **10-20%** of total trials | Posner (1980); standard in detection tasks |
| **No-go trials** | In Go/No-Go paradigms, trials requiring response inhibition | **20-30%** of total trials | Wessel (2018) |
| **Comprehension probes** | After-sentence questions in reading paradigms to verify comprehension | **30-50%** of sentences followed by a probe | Just et al. (1982); Keating & Jegerski (2015) |
| **Manipulation check trials** | Probe awareness or strategy (e.g., in masked priming: "Did you see the prime?") | **5-10%** of trials, interspersed or post-experiment block | Forster & Davis (1984) |

### Design Considerations

- Catch trials should be **randomly interspersed**, not blocked separately
- If catch trials are too frequent, they become a secondary task and alter the primary strategy
- In signal detection tasks, the "catch trial" proportion effectively sets the base rate and directly affects criterion placement (Macmillan & Creelman, 2005)
- For stop-signal tasks, **25%** stop trials is standard; higher proportions lead to proactive slowing of Go responses, contaminating SSRT (Verbruggen et al., 2019)

---

## 5. Counterbalancing

### Purpose

Counterbalancing controls for order effects, sequence effects, and stimulus-response mapping confounds in within-subjects designs.

### Methods

#### 5.1 Full Counterbalancing

- **All possible orders** of conditions are represented
- For k conditions: **k!** orderings needed
- Feasible only for **2-3 conditions** (2! = 2, 3! = 6 orders)
- Each participant receives one order; N should be a multiple of k!

#### 5.2 Latin Square

- **k orderings for k conditions**: Each condition appears in each ordinal position exactly once
- Requires N to be a multiple of k
- **Example** for 4 conditions:

 | Order | Pos 1 | Pos 2 | Pos 3 | Pos 4 |
 |---|---|---|---|---|
 | 1 | A | B | C | D |
 | 2 | B | C | D | A |
 | 3 | C | D | A | B |
 | 4 | D | A | B | C |

- **Balanced Latin Square** (Williams, 1949): Additionally controls for first-order carry-over effects (each condition precedes each other condition equally often). Requires **2k** participants for even k, **2k** for odd k.
- **Recommended for 4+ conditions** in within-subjects designs (Keppel & Wickens, 2004, Ch. 18)

#### 5.3 Counterbalancing Stimulus-Response Mappings

- When arbitrary S-R mappings are used (e.g., left key = "old," right key = "new"), **counterbalance across participants**: half use one mapping, half the other
- In lateralized tasks (e.g., Posner cueing), ensure equal numbers of left and right targets within each condition
- For handedness-sensitive tasks, record dominant hand and counterbalance response hand assignment (Oldfield, 1971, Edinburgh Handedness Inventory)

#### 5.4 Pseudo-Randomization Constraints

Within blocks, trial order should be pseudo-randomized with constraints:
- **No more than 3-4 consecutive trials** of the same condition (to prevent expectation-based strategies)
- **Equal transitions** between conditions: Each condition follows each other condition approximately equally often (prevents sequential confounds like the Gratton effect in conflict tasks; Gratton et al., 1992)
- **Minimum distance between identical stimuli**: At least **4-5 intervening trials** (to prevent immediate repetition priming; Mayr & Kliegl, 2003)

---

## 6. Common Confounds and Control Methods

### 6.1 Speed-Accuracy Tradeoff (SAT)

- **Problem**: Faster responses at the cost of more errors (or vice versa); a condition may appear "faster" only because participants adopted a riskier criterion
- **Controls**:
 - Report **both RT and accuracy** (never RT alone) (Wickelgren, 1977)
 - Use **inverse efficiency score (IES)**: IES = RT / (1 - error rate) (Townsend & Ashby, 1978) — though IES has limitations when accuracy varies substantially
 - Apply **drift-diffusion modeling** (Ratcliff & McKoon, 2008) to decompose drift rate, boundary separation, and non-decision time
 - Set a **response deadline** to constrain criterion variability
 - Instruct participants equally to emphasize speed **and** accuracy

### 6.2 Practice and Fatigue Effects

- **Problem**: Performance improves with practice or degrades with fatigue across the session
- **Controls**:
 - **Counterbalance condition order** across participants (see Section 5)
 - **Discard the first 2-5 trials** of each block ("warm-up" exclusion) (Monsell, 2003)
 - Include **rest breaks** every **50-100 trials** or every **5-10 minutes**; cognitive tasks show fatigue effects after **~15-20 minutes** of continuous performance (Ackerman & Kanfer, 2009)
 - Use **ABBA** or **randomized block** designs for two conditions to balance linear practice trends

### 6.3 Stimulus Confounds

- **Problem**: Conditions differ in low-level stimulus properties (luminance, spatial frequency, word length, etc.) rather than the variable of interest
- **Controls**:
 - Match stimuli on **word frequency, length, concreteness, familiarity** using normative databases (e.g., SUBTLEX-US for word frequency, Brysbaert & New, 2009; MRC Psycholinguistic Database)
 - For visual stimuli: equate **luminance, contrast, size, spatial frequency** (Willenbockel et al., 2010, SHINE toolbox)
 - Use **the same physical stimuli** across conditions (e.g., in Stroop, the same words appear in congruent and incongruent conditions)
 - When matching is insufficient, include the stimulus property as a **covariate** in analysis

### 6.4 Demand Characteristics and Expectation Effects

- **Problem**: Participants infer the experimenter's hypothesis and adjust behavior accordingly
- **Controls**:
 - Use **cover stories** that do not reveal the true hypothesis (APA ethics permitting)
 - Employ **between-subjects manipulations** for transparent conditions
 - Include **post-experiment questionnaires** probing awareness of the hypothesis (funnel debriefing; Bargh & Chartrand, 2000)
 - For priming studies: **low relatedness proportion** (e.g., 20-25% related pairs) reduces strategic expectancy (Neely et al., 1989)

### 6.5 Multiple Comparisons

- **Problem**: Inflated Type I error rate when testing multiple dependent variables or conditions
- **Controls**:
 - **Bonferroni correction**: alpha_adj = alpha / m comparisons; overly conservative when tests are correlated (Bland & Altman, 1995)
 - **Holm-Bonferroni**: Sequential step-down procedure, uniformly more powerful than Bonferroni (Holm, 1979)
 - **FDR correction** (Benjamini & Hochberg, 1995): Controls false discovery rate; preferred for exploratory analyses with many tests (standard in neuroimaging)
 - **Planned contrasts**: Pre-register specific comparisons instead of omnibus tests followed by post-hoc corrections

### 6.6 Response Bias and Criterion Shifts

- **Problem**: Participants adopt different response criteria across conditions (e.g., more conservative for difficult trials)
- **Controls**:
 - Use **SDT measures** (d' and criterion c) rather than raw accuracy (Macmillan & Creelman, 2005)
 - Use **forced-choice (2AFC)** paradigm, which is criterion-free (Green & Swets, 1966)
 - Equalize **base rates** (50% signal, 50% noise) unless base-rate manipulation is the research question
 - Report **ROC curves** when response bias is a concern

### 6.7 Ceiling and Floor Effects

- **Problem**: Performance at maximum or minimum, preventing detection of between-condition differences
- **Controls**:
 - **Pilot test** to calibrate difficulty to ~**70-85% accuracy** (the most informative range for SDT analyses) (Macmillan & Creelman, 2005)
 - Use **adaptive staircases** (e.g., QUEST, 1-up/2-down) to titrate difficulty to individual thresholds
 - Avoid using stimuli that are trivially easy or impossibly hard; verify performance is above chance and below ceiling in all conditions
 - For RT tasks, check that mean RT is well above the **150-200 ms** anticipation threshold and well below the **response deadline**

---

## 7. Essential Reporting Checklist

Based on APA reporting standards and Simmons, Nelson, & Simonsohn (2011, "False-Positive Psychology"):

- [ ] Report **all conditions** tested (including those that "did not work")
- [ ] Report **sample size determination** method (a priori power analysis with assumed effect size, or stopping rule)
- [ ] Report **all measures** collected (do not selectively report DVs)
- [ ] Report **exclusion criteria** and how many participants/trials were excluded
- [ ] Report **both RT and accuracy** for speeded tasks
- [ ] Report **effect sizes** with confidence intervals (not just p-values)
- [ ] Specify the **statistical model** used (t-test, ANOVA, mixed-effects model, Bayesian, etc.)
- [ ] State whether analyses were **pre-registered** (and provide the registration link)
- [ ] Report counterbalancing scheme and stimulus randomization method
