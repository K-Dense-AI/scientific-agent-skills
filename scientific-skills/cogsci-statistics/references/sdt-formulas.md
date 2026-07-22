# SDT Formulas and Computational Details

This reference file supplements the main `SKILL.md` with detailed mathematical formulas, lookup tables, correction methods, and computational procedures for Signal Detection Theory analysis.

## 1. Core Formulas by Paradigm

### 1.1 Yes/No (Single-Interval) Design

**Equal-variance Gaussian model** (Green & Swets, 1966, Ch. 1):

```
d' = z(H) - z(FA)
c = -0.5 * [z(H) + z(FA)]
ln(beta) = d' * c
beta = exp(d' * c)
c' = c / d'
```

Where:
- H = hit rate = P("yes" | signal)
- FA = false alarm rate = P("yes" | noise)
- z() = inverse of the standard normal cumulative distribution function (probit transform)

### 1.2 Two-Alternative Forced Choice (2AFC / 2IFC)

**Standard formula** (Green & Swets, 1966, Ch. 6; Macmillan & Creelman, 2005, Ch. 5):

```
d'(2AFC) = z(PC) * sqrt(2)
```

Where PC = proportion correct across all trials.

**Relationship to yes/no d'**:

```
d'(2AFC) = d'(yes/no) * sqrt(2)
```

This means that for the same underlying sensitivity, 2AFC yields a d' that is sqrt(2) times larger than yes/no. This conversion factor arises because the 2AFC observer effectively takes two independent samples and compares them (Green & Swets, 1966, Ch. 6).

**No independent bias measure** is available in 2AFC because the observer only indicates which interval contained the signal, not whether a signal was present.

### 1.3 Same-Different Paradigm

Two models describe observer strategy (Macmillan & Creelman, 2005, Ch. 6):

**Independent observations model** (used when stimuli are from a fixed, small set):

The observer independently classifies each stimulus and responds "same" if both classifications agree. Hit rate (P("different" | different pair)) and false alarm rate (P("different" | same pair)) are used. d' is obtained from lookup tables (Macmillan & Creelman, 2005, Table A5.3) or numerically because there is no closed-form solution.

**Differencing model** (used when stimuli vary along a continuum / roving design):

The observer computes the perceived difference between stimuli and responds "different" if the difference exceeds a criterion. d' is again obtained via lookup tables (Macmillan & Creelman, 2005, Table A5.4) or numerical computation.

For the differencing model, the relationship between d' and the hit/FA rates involves the non-central chi-squared distribution and requires iterative numerical methods. Software implementations (e.g., R package `psyphy`, Macmillan's `d'plus` program) handle this automatically.

### 1.4 ABX Paradigm

Two stimuli A and B are presented, followed by X (which equals A or B). The observer identifies X. As with same-different, two observer models exist (Macmillan & Creelman, 2005, Ch. 6):

**Independent observations model**:

```
d'(ABX) = z(H) - z(FA)
```

where H = P(correct | X = A) and FA = P(incorrect | X = B), or equivalently using the proportion correct with appropriate lookup tables (Macmillan & Creelman, 2005, Table A5.5).

**Differencing model** (default assumption for roving designs):

d' is obtained from proportion correct via lookup tables (Macmillan & Creelman, 2005, Table A5.6). There is no closed-form solution; numerical methods or published tables are required.

### 1.5 Oddity (3AFC-Odd)

Three stimuli are presented (two identical, one different); the observer identifies the odd one. For the differencing model (Macmillan & Creelman, 2005, Ch. 7):

```
d'(oddity) is obtained from P(correct) via Table A5.7
```

General relationship: d'(oddity) is smaller than d'(2AFC) for the same proportion correct because the task is inherently harder (Macmillan & Creelman, 2005, Ch. 7).

## 2. Correction Methods for Extreme Proportions

### 2.1 The 1/(2N) Rule (Macmillan & Kaplan, 1985)

Applied only to extreme values (0 or 1):

```
If H = 0: H_corrected = 0.5 / N_signal
If H = 1: H_corrected = (N_signal - 0.5) / N_signal
If FA = 0: FA_corrected = 0.5 / N_noise
If FA = 1: FA_corrected = (N_noise - 0.5) / N_noise
```

Where N_signal = number of signal trials, N_noise = number of noise trials.

**Limitations**: Can either overestimate or underestimate true d'; applied asymmetrically (only to extreme cells), which introduces inconsistency (Hautus, 1995).

### 2.2 The Log-Linear Rule (Hautus, 1995) -- Recommended

Applied to all cells unconditionally:

```
H_corrected = (hits + 0.5) / (N_signal + 1)
FA_corrected = (false_alarms + 0.5) / (N_noise + 1)
```

Equivalently, add 0.5 to each cell of the 2x2 matrix:

```
hits_adj = hits + 0.5
misses_adj = misses + 0.5
fa_adj = false_alarms + 0.5
cr_adj = correct_rejections + 0.5

H_corrected = hits_adj / (hits_adj + misses_adj)
FA_corrected = fa_adj / (fa_adj + cr_adj)
```

**Properties** (Hautus, 1995):
- Always underestimates true d' (provides a conservative lower bound)
- Less biased than the 1/(2N) rule across all parameter combinations tested
- Converges to the uncorrected value as N increases
- Should be applied **uniformly** to all participants/conditions for consistency, not only when extremes are present

### 2.3 Worked Example

Suppose an observer has 50 signal trials and 50 noise trials:
- Hits = 50, Misses = 0 (H = 1.0)
- False Alarms = 5, Correct Rejections = 45 (FA = 0.10)

Without correction: d' = z(1.0) - z(0.10) = infinity - (-1.28) = undefined

**1/(2N) correction**:
- H_corrected = (50 - 0.5) / 50 = 0.99
- FA remains 0.10
- d' = z(0.99) - z(0.10) = 2.33 - (-1.28) = 3.61

**Log-linear correction** (applied to all cells):
- H_corrected = 50.5 / 51 = 0.990
- FA_corrected = 5.5 / 51 = 0.108
- d' = z(0.990) - z(0.108) = 2.33 - (-1.24) = 3.57

## 3. ROC Analysis

### 3.1 Constructing an ROC Curve

**From rating data**: If observers use a K-point confidence scale, each scale boundary yields a different (H, FA) pair. With K rating categories, you obtain K-1 ROC points.

Procedure (Macmillan & Creelman, 2005, Ch. 3):

1. For each criterion k (from most conservative to most liberal):
 - H(k) = P(rating >= k | signal)
 - FA(k) = P(rating >= k | noise)
2. Plot FA(k) on x-axis, H(k) on y-axis
3. Add the points (0, 0) and (1, 1) as anchors
4. The resulting curve bows above the diagonal for above-chance performance

### 3.2 Computing Az (Area Under the ROC)

**Parametric estimate** (assuming Gaussian distributions; Swets, 1986):

```
Az = Phi(da / sqrt(2))
```

Where Phi() is the standard normal CDF and da is the sensitivity index from the fitted model.

For the equal-variance model (slope = 1):

```
Az = Phi(d' / sqrt(2))
```

**Nonparametric estimate** (trapezoidal rule):

```
Az_nonpar = sum over k of: 0.5 * (H(k+1) - H(k)) * (FA(k) + FA(k+1))
```

This is equivalent to the Wilcoxon-Mann-Whitney statistic and makes no distributional assumptions.

### 3.3 The zROC and Unequal Variance

Plotting z(H) vs. z(FA) yields the zROC. Under the equal-variance Gaussian model, this is a straight line with slope = 1 and intercept = d'.

Under the **unequal-variance model** (Macmillan & Creelman, 2005, Ch. 3):

```
zROC: z(H) = (1/s) * z(FA) + d_a / s
```

Where:
- s = sigma_noise / sigma_signal (ratio of standard deviations)
- The zROC slope = 1/s
- If slope < 1: signal distribution has greater variance (common in recognition memory)

**Typical finding in recognition memory**: zROC slope ~ **0.80** (i.e., s ~ 0.80, meaning sigma_target / sigma_lure ~ 1.25; Ratcliff, Sheu, & Gronlund, 1992; Mickes, Wixted, & Wais, 2007).

### 3.4 Unequal-Variance Sensitivity: da

When variances are unequal, use da instead of d' (Macmillan & Creelman, 2005, Ch. 3):

```
da = sqrt(2 / (1 + s^2)) * [z(H) - s * z(FA)]
```

Where s = sigma_noise / sigma_signal (the zROC slope).

When s = 1 (equal variance), da reduces to d'. When s != 1, da provides a **criterion-free** sensitivity measure that standard d' does not.

## 4. Nonparametric Sensitivity Measures

### 4.1 A' (A-prime)

Originally proposed by Pollack & Norman (1964) as a nonparametric single-point sensitivity estimate.

**Formula** (corrected version from Zhang & Mueller, 2005):

```
If H >= FA:
 A' = 0.5 + [(H - FA) * (1 + H - FA)] / [4 * H * (1 - FA)]

If FA > H:
 A' = 0.5 - [(FA - H) * (1 + FA - H)] / [4 * FA * (1 - H)]
```

Range: 0.5 (chance) to 1.0 (perfect).

**Caution**: Despite being called "nonparametric," A' implicitly assumes a specific (approximately logistic) distribution model (Macmillan & Creelman, 1996). It is less accurate than parametric measures when the underlying distributions are Gaussian (Macmillan & Creelman, 2005, Ch. 3). Use Az from ROC data when possible.

### 4.2 B''_D (Nonparametric Bias)

The commonly paired nonparametric bias measure (Donaldson, 1992):

```
B''_D = [(1 - H) * (1 - FA) - H * FA] / [(1 - H) * (1 - FA) + H * FA]
```

Range: -1 (extreme liberal) to +1 (extreme conservative). B''_D = 0 indicates no bias.

## 5. Confidence Interval and Variance of d'

### 5.1 Variance of d'

The variance of d' can be approximated as (Gourevitch & Galanter, 1967; Macmillan & Creelman, 2005, Ch. 8):

```
Var(d') = [H*(1-H)] / [N_signal * phi(z(H))^2] + [FA*(1-FA)] / [N_noise * phi(z(FA))^2]
```

Where phi() is the standard normal probability density function.

### 5.2 Approximate 95% Confidence Interval

```
d' +/- 1.96 * sqrt(Var(d'))
```

This approximation works well for moderate sample sizes (N > 20 per stimulus class) and non-extreme rates (Macmillan & Creelman, 2005, Ch. 8).

## 6. Quick Reference: d' Lookup Table (Yes/No)

Selected d' values for common (H, FA) combinations (computed from standard equal-variance model):

| H \ FA | 0.01 | 0.05 | 0.10 | 0.20 | 0.30 | 0.50 |
|--------|------|------|------|------|------|------|
| 0.50 | 2.33 | 1.64 | 1.28 | 0.84 | 0.52 | 0.00 |
| 0.60 | 2.58 | 1.90 | 1.53 | 1.10 | 0.78 | 0.25 |
| 0.70 | 2.86 | 2.17 | 1.80 | 1.37 | 1.05 | 0.52 |
| 0.80 | 3.17 | 2.48 | 2.12 | 1.68 | 1.37 | 0.84 |
| 0.90 | 3.61 | 2.92 | 2.56 | 2.12 | 1.80 | 1.28 |
| 0.95 | 3.97 | 3.29 | 2.92 | 2.48 | 2.17 | 1.64 |
| 0.99 | 4.65 | 3.97 | 3.61 | 3.17 | 2.86 | 2.33 |

## 7. Quick Reference: 2AFC Proportion Correct to d'

| PC (2AFC) | d'(2AFC) |
|-----------|----------|
| 0.55 | 0.18 |
| 0.60 | 0.36 |
| 0.65 | 0.54 |
| 0.70 | 0.74 |
| 0.75 | 0.95 |
| 0.80 | 1.19 |
| 0.85 | 1.47 |
| 0.90 | 1.81 |
| 0.95 | 2.33 |

(Values computed as z(PC) * sqrt(2); Macmillan & Creelman, 2005, Table A5.1)

## 8. Software Implementations

| Software | Language | Key Function / Package | Reference |
|----------|----------|----------------------|-----------|
| `psyphy` | R | `dprime.SD()`, `dprime.ABX()`, `dprime.oddity()` | Knoblauch, 2014 |
| `psychopy` | Python | `data.sdt` module | Peirce et al., 2019 |
| `scipy.stats` | Python | `norm.ppf()` for z-transforms (compute d' manually) | -- |
| `d'plus` | Standalone | All paradigms, bias measures | Macmillan, 2007 |
| `sensR` | R | `d.primeSS()`, `d.prime2AFC()`, `SDT()` | Brockhoff & Christensen, 2010 |
| `MLE_metad` | MATLAB/Python | Type 2 SDT, meta-d' | Maniscalco & Lau, 2012 |

## References

- Donaldson, W. (1992). Measuring recognition memory. *Journal of Experimental Psychology: General*, 121, 275-277.
- Gourevitch, V., & Galanter, E. (1967). A significance test for one parameter isosensitivity functions. *Psychometrika*, 32, 25-33.
- Green, D. M., & Swets, J. A. (1966). *Signal detection theory and psychophysics*. New York: Wiley.
- Hautus, M. J. (1995). Corrections for extreme proportions and their biasing effects on estimated values of d'. *Behavior Research Methods, Instruments, & Computers*, 27, 46-51.
- Macmillan, N. A., & Creelman, C. D. (1996). Triangles in ROC space: History and theory of "nonparametric" measures of sensitivity and response bias. *Psychonomic Bulletin & Review*, 3, 164-170.
- Macmillan, N. A., & Creelman, C. D. (2005). *Detection theory: A user's guide* (2nd ed.). Mahwah, NJ: Erlbaum.
- Macmillan, N. A., & Kaplan, H. L. (1985). Detection theory analysis of group data. *Psychological Bulletin*, 98, 185-199.
- Mickes, L., Wixted, J. T., & Wais, P. E. (2007). A direct test of the unequal-variance signal detection model of recognition memory. *Psychonomic Bulletin & Review*, 14, 858-865.
- Pollack, I., & Norman, D. A. (1964). A nonparametric analysis of recognition experiments. *Psychonomic Science*, 1, 125-126.
- Ratcliff, R., Sheu, C. F., & Gronlund, S. D. (1992). Testing global memory models using ROC curves. *Psychological Review*, 99, 518-535.
- Swets, J. A. (1986). Indices of discrimination or diagnostic accuracy. *Psychological Bulletin*, 99, 100-117.
- Zhang, J., & Mueller, S. T. (2005). A note on ROC analysis and non-parametric estimate of sensitivity. *Psychometrika*, 70, 203-212.
