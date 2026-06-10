# SDT Application Guide: Domain-Specific Uses

This reference file supplements the main `SKILL.md` with detailed guidance on applying Signal Detection Theory in specific cognitive science domains.

## 1. Recognition Memory

### The Old/New Paradigm

The most common application of SDT in memory research. Participants study a list of items, then are tested with a mix of old (studied) and new (unstudied) items, responding "old" or "new."

**Mapping to SDT** (Macmillan & Creelman, 2005, Ch. 2):
- Signal = old item; Noise = new item
- Hit = correctly responding "old" to an old item
- False Alarm = incorrectly responding "old" to a new item
- d' reflects **memory strength** (discriminability of old from new)
- c reflects **response criterion** (willingness to endorse items as "old")

### The Mirror Effect

A robust finding: variables that increase hit rates also decrease false alarm rates (e.g., high-frequency words produce both lower H and higher FA than low-frequency words). This "mirror effect" (Glanzer & Adams, 1985) is naturally explained by SDT if both distributions shift (Stretch & Wixted, 1998).

### Unequal Variance: The Default in Recognition Memory

Standard d' assumes equal variance, but recognition memory data **almost always** violate this assumption (Ratcliff, Sheu, & Gronlund, 1992):

- **zROC slopes** in recognition memory are typically **0.80** (range: 0.70-0.90 across studies; Ratcliff, Sheu, & Gronlund, 1992; Mickes, Wixted, & Wais, 2007)
- This means sigma_old / sigma_new ~ **1.25** (old items have more variable memory strength)
- The encoding variability hypothesis explains this: items are encoded with variable strength, increasing the variance of the old-item distribution (Wixted, 2007)

**Practical recommendation**: When analyzing recognition memory data:
1. Collect confidence ratings (e.g., 6-point scale: sure new, probably new, maybe new, maybe old, probably old, sure old)
2. Construct the zROC and estimate the slope
3. If slope deviates from 1.0 (it will), compute da rather than d'
4. Report the slope and variance ratio alongside sensitivity

### The Remember/Know Paradigm

Participants indicate whether they "remember" specific details (recollection) or "know" the item was studied based on familiarity. Under the dual-process SDT model (Yonelinas, 1994):

- **Recollection** (R) is modeled as a threshold process: P(R) = proportion of old items exceeding a recollection threshold
- **Familiarity** is modeled as a continuous Gaussian SDT process: d'(familiarity) is estimated after removing recollected items

**Estimation** (Yonelinas, 2002):
- Recollection = P("remember" | old) - P("remember" | new)
- Familiarity d' = z(P("know" | old) / (1 - P("remember" | old))) - z(P("know" | new) / (1 - P("remember" | new)))

**Critical pitfall**: The independence assumption underlying these formulas (that "know" responses come only from non-recollected items) is debated. The redundancy model (Wixted & Mickes, 2010) argues recollection and familiarity are not independent. Report which model was assumed.

## 2. Perception and Psychophysics

### Threshold Estimation

SDT was originally developed for perceptual detection (Green & Swets, 1966). The "threshold" in SDT is typically defined as the stimulus intensity yielding a criterion level of d':

- **d' = 1.0** is the most common threshold definition in yes/no tasks (Green & Swets, 1966, Ch. 4)
- **76% correct** is the equivalent threshold in 2AFC (corresponding to d'(2AFC) ~ 1.0; Green & Swets, 1966, Ch. 6)

Other threshold conventions exist:
- 75% correct in 2AFC (d' ~ 0.95) -- used in some adaptive staircase methods
- d' = 2.0 for clinical hearing tests -- a more conservative threshold

### Psychometric Functions and SDT

The psychometric function (proportion correct vs. stimulus intensity) is related to SDT:

- At each stimulus intensity, the observer has a particular d'
- Plotting d' vs. stimulus intensity yields the psychometric function in SDT units
- The slope of this function reflects how rapidly sensitivity changes with stimulus strength

**Adaptive methods** (staircases, QUEST, PEST) estimate the stimulus level corresponding to a target d' or proportion correct (Watson & Pelli, 1983; Taylor & Creelman, 1967).

### Signal Detection in Vision Research

Common visual paradigms and their SDT implementations:

| Task | SDT Design | Sensitivity Measure |
|------|-----------|-------------------|
| Contrast detection | Yes/no with noise intervals | d' |
| Orientation discrimination | 2AFC (which interval had tilted grating?) | d'(2AFC) |
| Change detection | Yes/no ("did something change?") | d' or Cowan's K (Cowan, 2001) |
| Visual search | Yes/no ("target present?") | d' (separate for each set size) |

**Visual search and SDT**: In visual search, d' typically decreases linearly with the logarithm of set size for inefficient search, but remains constant for efficient ("pop-out") search (Palmer, Verghese, & Pavel, 2000).

### Signal Detection in Auditory Research

Common auditory paradigms:

| Task | SDT Design | Notes |
|------|-----------|-------|
| Tone detection in noise | Yes/no or 2IFC | Classic SDT paradigm (Green & Swets, 1966) |
| Frequency discrimination | 2IFC or same-different | Use appropriate paradigm-specific formula |
| Speech in noise | Open-set (word identification) | SDT less applicable; use percent correct or SRT |
| Audiometric threshold | Adaptive staircase | Target d' varies by clinical standard |

## 3. Clinical Psychology and Diagnostic Accuracy

### SDT Framework for Diagnosis

Any diagnostic decision can be framed as signal detection (Swets, 1988; Swets, Dawes, & Monahan, 2000):

- **Signal** = condition present (e.g., disease, disorder, threat)
- **Noise** = condition absent
- **Hit** = true positive (correctly detecting condition)
- **False Alarm** = false positive (incorrectly diagnosing condition when absent)
- **Sensitivity** (d' or AUC) = diagnostic accuracy of the test/clinician
- **Criterion** (c) = diagnostic threshold (how much evidence is required before diagnosing)

### AUC Benchmarks for Clinical Instruments

From Swets (1988) and Swets, Dawes, & Monahan (2000):

| AUC | Clinical Interpretation |
|-----|------------------------|
| 0.50 | No diagnostic value (chance) |
| 0.50 - 0.70 | Low accuracy; rarely useful clinically |
| 0.70 - 0.80 | Fair accuracy; may be useful as one of several indicators |
| 0.80 - 0.90 | Good accuracy; clinically useful |
| 0.90 - 1.00 | Excellent accuracy; high diagnostic value |

**Benchmark context**: Strong psychological assessment measures routinely yield AUC estimates around 0.70 (Youngstrom, 2014). An AUC of 0.80 is a reasonable target for clinically useful individual-level prediction.

### Clinical Applications

**Violence risk assessment** (Swets, Dawes, & Monahan, 2000):
- Actuarial risk instruments (e.g., VRAG) achieve AUC ~ 0.70-0.76
- Clinical judgment alone: AUC ~ 0.55-0.65
- SDT analysis reveals that clinicians tend to have a conservative criterion (low FA but many misses)

**Depression screening** (e.g., PHQ-9):
- At cutoff score >= 10: sensitivity ~ 0.88, specificity ~ 0.88 (Kroenke, Spitzer, & Williams, 2001)
- The cutoff score represents the criterion in SDT terms
- Different cutoffs trade off sensitivity vs. specificity along the ROC curve

**Medical imaging** (Swets, 1988):
- Radiologist mammography reading: AUC ~ 0.80-0.90
- Computer-aided detection systems: AUC ~ 0.85-0.95
- SDT separates the radiologist's perceptual ability from their decision threshold

### Base Rate Effects on Clinical Decisions

A critical SDT insight for clinical work: the **optimal criterion shifts with base rate** (Green & Swets, 1966, Ch. 2).

- In rare conditions (low base rate), the optimal criterion is conservative (high c)
- In common conditions (high base rate), the optimal criterion is liberal (low c)
- Clinicians often fail to adjust sufficiently for base rates, leading to systematic over-diagnosis of rare conditions and under-diagnosis of common ones (Swets, Dawes, & Monahan, 2000)

**Positive predictive value** (PPV) depends on base rate even when sensitivity and specificity are constant:

```
PPV = (sensitivity * base_rate) / (sensitivity * base_rate + (1 - specificity) * (1 - base_rate))
```

For a test with sensitivity = 0.90 and specificity = 0.90:
- Base rate 50%: PPV = 0.90
- Base rate 10%: PPV = 0.50
- Base rate 1%: PPV = 0.08

This dramatic drop in PPV at low base rates is a key SDT-informed insight that clinicians without SDT training often miss.

## 4. Metacognition and Confidence Ratings

### Type 1 vs. Type 2 SDT

**Type 1 SDT**: How well does the observer discriminate external stimulus states (signal vs. noise)?
- Measures: d', c, Az

**Type 2 SDT**: How well does the observer discriminate their own correct from incorrect responses?
- Measures: type 2 d', type 2 AUC, meta-d' (Maniscalco & Lau, 2012)

### Meta-d' (Maniscalco & Lau, 2012)

Meta-d' is the type 1 d' that would produce the observed type 2 (metacognitive) performance under ideal SDT assumptions. It answers: "How much signal-to-noise information is available for metacognitive judgments?"

**Key properties**:
- Meta-d' is expressed in the same units as d', enabling direct comparison
- If meta-d' = d': metacognition is ideal (all information available for the type 1 task is also used for metacognition)
- If meta-d' < d': metacognitive inefficiency (some information is lost or unavailable for confidence judgments)
- If meta-d' > d' (rare): suggests additional information sources for metacognition beyond the type 1 decision variable

**Metacognitive efficiency** (M-ratio):

```
M-ratio = meta-d' / d'
```

- M-ratio = 1: ideal metacognition
- M-ratio < 1: suboptimal metacognition (typical finding; Maniscalco & Lau, 2012)
- Typical values in perceptual tasks: **M-ratio ~ 0.6 - 0.8** (Fleming & Lau, 2014)

### Computing Meta-d'

Meta-d' cannot be computed with a simple formula. It requires fitting a model to the type 2 data (confidence rating distributions conditioned on accuracy). Two approaches:

1. **Maximum likelihood estimation** (Maniscalco & Lau, 2012): fit meta-d' to maximize the likelihood of observed type 2 hit and FA rates at each confidence level
2. **Hierarchical Bayesian estimation** (Fleming, 2017): preferred for group-level analysis; handles individual differences and small trial counts better

Software: Available at https://github.com/smfleming/HMeta-d (MATLAB and Python).

### Confidence Calibration vs. Metacognitive Sensitivity

These are distinct concepts often confused:

- **Calibration**: Do confidence ratings match objective accuracy? (e.g., when someone says "80% sure," are they correct 80% of the time?)
- **Resolution/sensitivity**: Can the observer distinguish correct from incorrect responses, regardless of absolute calibration?

SDT-based measures (meta-d', type 2 AUC) measure **resolution**, not calibration. Calibration requires separate analysis (e.g., calibration curves).

## 5. Eyewitness Identification

### SDT in Lineup Research

SDT has been applied to eyewitness identification (Wixted & Mickes, 2012):

- **Signal** = target-present lineup
- **Noise** = target-absent lineup
- **Hit** = correct identification from target-present lineup
- **False Alarm** = incorrect identification from target-absent lineup (filler or foil identification)

### Lineup Procedure Effects

SDT analysis reveals that different lineup procedures (simultaneous vs. sequential) primarily affect criterion placement, not discriminability (Wixted & Mickes, 2012):

- **Simultaneous lineups**: more liberal criterion (higher H and higher FA)
- **Sequential lineups**: more conservative criterion (lower H and lower FA)
- **d' (discriminability)**: similar across procedures in many studies

This SDT insight has important policy implications: sequential lineups were once recommended as superior, but SDT analysis shows they primarily make witnesses more conservative, not more accurate at discrimination (Wixted & Mickes, 2012).

## 6. Decision Making Under Uncertainty

### SDT and Optimal Decision Rules

The optimal SDT observer sets the criterion to maximize expected utility (Green & Swets, 1966, Ch. 2):

```
beta_optimal = [P(noise) / P(signal)] * [(V_CR + C_FA) / (V_H + C_M)]
```

Where:
- P(noise), P(signal) = prior probabilities
- V_CR, V_H = values of correct decisions
- C_FA, C_M = costs of incorrect decisions

When base rates are equal and payoffs symmetric, beta_optimal = 1 (unbiased).

### SDT and the Utility of Caution

A key insight from "utilized" SDT (Lynn & Barrett, 2014): maximizing accuracy and maximizing utility are **not** always the same. There are situations where the optimal strategy is deliberately inaccurate:

- When misses are far more costly than false alarms (e.g., smoke detector design), the optimal criterion is very liberal, maximizing hits at the expense of many false alarms
- When false alarms are far more costly than misses (e.g., criminal conviction), the optimal criterion is very conservative

## References

- Cowan, N. (2001). The magical number 4 in short-term memory. *Behavioral and Brain Sciences*, 24, 87-114.
- Fleming, S. M. (2017). HMeta-d: Hierarchical Bayesian estimation of metacognitive efficiency from confidence ratings. *Neuroscience of Consciousness*, 3(1), nix007.
- Fleming, S. M., & Lau, H. C. (2014). How to measure metacognition. *Frontiers in Human Neuroscience*, 8, 443.
- Glanzer, M., & Adams, J. K. (1985). The mirror effect in recognition memory. *Memory & Cognition*, 13, 8-20.
- Green, D. M., & Swets, J. A. (1966). *Signal detection theory and psychophysics*. New York: Wiley.
- Kroenke, K., Spitzer, R. L., & Williams, J. B. (2001). The PHQ-9: Validity of a brief depression severity measure. *Journal of General Internal Medicine*, 16, 606-613.
- Lynn, S. K., & Barrett, L. F. (2014). "Utilizing" signal detection theory. *Psychological Science*, 25, 1663-1673.
- Macmillan, N. A., & Creelman, C. D. (2005). *Detection theory: A user's guide* (2nd ed.). Mahwah, NJ: Erlbaum.
- Maniscalco, B., & Lau, H. (2012). A signal detection theoretic approach for estimating metacognitive sensitivity from confidence ratings. *Consciousness and Cognition*, 21, 422-430.
- Mickes, L., Wixted, J. T., & Wais, P. E. (2007). A direct test of the unequal-variance signal detection model of recognition memory. *Psychonomic Bulletin & Review*, 14, 858-865.
- Palmer, J., Verghese, P., & Pavel, M. (2000). The psychophysics of visual search. *Vision Research*, 40, 1227-1268.
- Ratcliff, R., Sheu, C. F., & Gronlund, S. D. (1992). Testing global memory models using ROC curves. *Psychological Review*, 99, 518-535.
- Stretch, V., & Wixted, J. T. (1998). On the difference between strength-based and frequency-based mirror effects in recognition memory. *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 24, 1379-1396.
- Swets, J. A. (1988). Measuring the accuracy of diagnostic systems. *Science*, 240, 1285-1293.
- Swets, J. A., Dawes, R. M., & Monahan, J. (2000). Psychological science can improve diagnostic decisions. *Psychological Science in the Public Interest*, 1, 1-26.
- Taylor, M. M., & Creelman, C. D. (1967). PEST: Efficient estimates on probability functions. *Journal of the Acoustical Society of America*, 41, 782-787.
- Watson, A. B., & Pelli, D. G. (1983). QUEST: A Bayesian adaptive psychometric method. *Perception & Psychophysics*, 33, 113-120.
- Wixted, J. T. (2007). Dual-process theory and signal-detection theory of recognition memory. *Psychological Review*, 114, 152-176.
- Wixted, J. T., & Mickes, L. (2010). A continuous dual-process model of remember/know judgments. *Psychological Review*, 117, 1025-1054.
- Wixted, J. T., & Mickes, L. (2012). The field of eyewitness memory should abandon probative value and embrace receiver operating characteristic analysis. *Perspectives on Psychological Science*, 7, 275-278.
- Yonelinas, A. P. (1994). Receiver-operating characteristics in recognition memory: Evidence for a dual-process model. *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 20, 1341-1354.
- Yonelinas, A. P. (2002). The nature of recollection and familiarity: A review of 30 years of research. *Journal of Memory and Language*, 46, 441-517.
- Youngstrom, E. A. (2014). A primer on receiver operating characteristic analysis and diagnostic efficiency statistics for pediatric psychology. *Journal of Pediatric Psychology*, 39, 204-221.
