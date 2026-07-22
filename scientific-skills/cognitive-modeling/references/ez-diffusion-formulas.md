# EZ-Diffusion Formulas and Worked Examples

This reference file supplements the main `SKILL.md` with the closed-form equations for EZ-diffusion (Wagenmakers et al., 2007) and worked examples.

## 1. Input Requirements

EZ-diffusion requires three summary statistics per experimental condition:

- **Pc**: Proportion correct (accuracy), where 0.5 < Pc <= 1.0
- **MRT**: Mean response time for correct responses (in seconds)
- **VRT**: Variance of response times for correct responses (in seconds squared)

## 2. Closed-Form Equations

The following equations yield the three EZ-diffusion parameters from the summary statistics (Wagenmakers et al., 2007, Eq. 1-3).

### Step 1: Compute drift rate (v)

```
Define: s = constant scaling parameter (typically s = 0.1; Ratcliff, 1978)

L = logit(Pc) = ln(Pc / (1 - Pc))

x = L * (L * Pc^2 - L * Pc + Pc - 0.5) / VRT

v = sign(Pc - 0.5) * s * x^(1/4)
```

### Step 2: Compute boundary separation (a)

```
y = -v * L / (Pc^2 * (s^2 / (2*v^2)) * (exp(-2 * v * L * s^(-2)) - 1))

Wait -- using the cleaner formulation from Wagenmakers et al. (2007):

a = s^2 * L / v
```

Note: The sign convention ensures a > 0 when Pc > 0.5.

### Step 3: Compute non-decision time (Ter)

```
Ter = MRT - (a / (2 * v)) * ((1 - exp(-v * a / s^2)) / (1 + exp(-v * a / s^2)))
```

## 3. Edge Correction

When Pc = 0.5 (chance) or Pc = 1.0 (perfect), the equations break down (Wagenmakers et al., 2007).

**Correction for Pc = 1.0**:
```
Pc_corrected = 1 - 1 / (2 * N)
```

**Correction for Pc = 0.5**:
```
Pc_corrected = 0.5 + 1 / (2 * N)
```

Where N = number of trials in that condition. Apply these corrections before computing EZ parameters.

## 4. Robust EZ (REZ)

Robust EZ (Grasman et al., 2009) addresses two limitations of basic EZ:

1. Uses **median RT** instead of mean RT (more robust to outliers)
2. Uses a **quantile-based variance estimate** (interquartile range) instead of sample variance

Equations are similar but use robust estimators. See Grasman, Wagenmakers, & van der Maas (2009) for details.

## 5. Worked Example

### Example Data

A participant in a lexical decision task:
- Condition: High frequency words
- Trials: 100 correct out of 120 total
- Pc = 100/120 = 0.833
- MRT (correct) = 0.623 s
- VRT (correct) = 0.018 s^2

### Step-by-step Computation

Using scaling parameter s = 0.1 (Ratcliff, 1978):

```
L = ln(0.833 / 0.167) = ln(4.988) = 1.607

v = sign(0.833 - 0.5) * 0.1 * (1.607 * (1.607 * 0.833^2 - 1.607 * 0.833 + 0.833 - 0.5) / 0.018)^(1/4)
 = 0.1 * (1.607 * (1.115 - 1.339 + 0.333) / 0.018)^(1/4)
 = 0.1 * (1.607 * 0.109 / 0.018)^(1/4)
 = 0.1 * (9.731)^(1/4)
 = 0.1 * 1.766
 = 0.177

a = 0.01 * 1.607 / 0.177
 = 0.091

Ter = 0.623 - (0.091 / (2 * 0.177)) * ((1 - exp(-0.177 * 0.091 / 0.01)) / (1 + exp(-0.177 * 0.091 / 0.01)))
 = 0.623 - 0.257 * ((1 - exp(-1.611)) / (1 + exp(-1.611)))
 = 0.623 - 0.257 * ((1 - 0.200) / (1 + 0.200))
 = 0.623 - 0.257 * 0.667
 = 0.623 - 0.171
 = 0.452 s
```

### Interpretation

- **v = 0.177**: Moderate drift rate, indicating reasonable evidence accumulation for high-frequency words
- **a = 0.091**: Boundary separation reflecting the speed-accuracy tradeoff setting
- **Ter = 0.452 s**: Non-decision time, encompassing stimulus encoding and motor execution

## 6. Comparison: When EZ Diverges from Full DDM

EZ-diffusion assumes:
- No across-trial variability in drift rate (sv = 0)
- No across-trial variability in starting point (sz = 0)
- No across-trial variability in non-decision time (st0 = 0)

When these variability parameters are non-zero in reality (Ratcliff, 1978):
- EZ drift rate estimates tend to be **underestimates** of true drift rate
- EZ boundary estimates remain relatively accurate
- EZ non-decision time can be **overestimated**

The mismatch is most problematic when:
- Error RTs are substantially faster or slower than correct RTs (indicating sv > 0; Ratcliff & McKoon, 2008)
- There is strong a priori bias toward one response (indicating sz > 0)

For designs where these variabilities are theoretically important, use the full DDM instead.

## References

- Grasman, R. P. P. P., Wagenmakers, E.-J., & van der Maas, H. L. J. (2009). On the mean and variance of response times under the diffusion model with an application to parameter estimation. *Journal of Mathematical Psychology*, 53, 55-68.
- Ratcliff, R. (1978). A theory of memory retrieval. *Psychological Review*, 85, 59-108.
- Ratcliff, R., & McKoon, G. (2008). The diffusion decision model: Theory and data for two-choice decision tasks. *Neural Computation*, 20, 873-922.
- Wagenmakers, E.-J., van der Maas, H. L. J., & Grasman, R. P. P. P. (2007). An EZ-diffusion model for response time and accuracy. *Psychonomic Bulletin & Review*, 14, 3-22.
