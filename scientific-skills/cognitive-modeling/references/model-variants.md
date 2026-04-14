# DDM Model Variants

A comprehensive reference for the drift-diffusion model family, covering model specifications, parameter details, applicability, and trade-offs. All numerical parameter ranges cite their authoritative sources.

---

## Table of Contents

1. [Classic DDM (Ratcliff, 1978)](#1-classic-ddm-ratcliff-1978)
2. [Full DDM with Trial-to-Trial Variability](#2-full-ddm-with-trial-to-trial-variability)
3. [EZ-Diffusion Model](#3-ez-diffusion-model)
4. [Hierarchical DDM (HDDM)](#4-hierarchical-ddm-hddm)
5. [Linear Ballistic Accumulator (LBA)](#5-linear-ballistic-accumulator-lba)
6. [Racing Diffusion Model (RDM)](#6-racing-diffusion-model-rdm)
7. [Collapsing Bounds DDM](#7-collapsing-bounds-ddm)
8. [Variant Comparison Summary](#8-variant-comparison-summary)

---

## 1. Classic DDM (Ratcliff, 1978)

### Model Description

The classic drift-diffusion model posits that evidence accumulates continuously over time as a Wiener diffusion process, starting from point z and drifting toward one of two absorbing boundaries separated by distance a. The drift rate v captures the average rate of evidence accumulation, and noise is modeled as a Gaussian diffusion process with diffusion coefficient s (typically fixed to **0.1** as a scaling parameter; Ratcliff, 1978; or to **1.0** in some implementations, Ratcliff & McKoon, 2008, footnote 2).

### Mathematical Formulation

The evidence variable x(t) evolves according to:

```
dx = v dt + s dW
```

where v is the drift rate, s is the diffusion coefficient (noise), and dW is a Wiener process increment. A decision is made when x(t) reaches the upper boundary (a) or the lower boundary (0). The observed RT = decision time + non-decision time (t0).

### Parameters

| Parameter | Symbol | Description | Typical Range | Source |
|-----------|--------|-------------|---------------|--------|
| Drift rate | v | Mean rate of evidence accumulation | **0.1 – 5.0** (with s=0.1); commonly **0.5 – 3.0** | Ratcliff & McKoon, 2008; Voss et al., 2004, Table 2 |
| Boundary separation | a | Distance between decision boundaries | **0.5 – 2.5** (with s=0.1); commonly **0.8 – 2.0** | Ratcliff & McKoon, 2008; Voss et al., 2004, Table 2 |
| Non-decision time | t0 (Ter) | Time for stimulus encoding + motor response | **0.1 – 0.6 s**; commonly **0.2 – 0.5 s** | Ratcliff & McKoon, 2008; Matzke & Wagenmakers, 2009, Table 1 |
| Starting point | z | Starting point of evidence accumulation | **0 – a**; unbiased = **a/2** | Ratcliff & McKoon, 2008; Voss et al., 2013 |
| Diffusion coefficient | s | Within-trial noise (scaling parameter) | Fixed to **0.1** (Ratcliff convention) or **1.0** | Ratcliff, 1978; Ratcliff & McKoon, 2008 |

**Note on scaling**: s is a scaling parameter — it determines the scale of v and a. Fixing s=0.1 (Ratcliff convention) or s=1.0 (some Bayesian implementations) yields different numerical ranges for v and a, but the model is mathematically equivalent (Donkin et al., 2009).

### When to Use

- Two-choice RT tasks with sufficient trials (> **40 per condition**; Ratcliff & Childers, 2015)
- When you want to decompose RT and accuracy into process-level components
- When trial-to-trial variability is not of primary theoretical interest (or when trial counts are insufficient to estimate it)
- When the research question focuses on how experimental manipulations selectively affect drift, boundary, or non-decision time

### Strengths

- Parsimonious: 4 free parameters capture RT distributions for both correct and error responses
- Well-validated across many cognitive domains (Ratcliff & McKoon, 2008)
- Closed-form expressions for first-passage time distribution exist (Navarro & Fuss, 2009)
- Efficient to fit with moderate trial counts

### Limitations

- Cannot account for certain phenomena without trial-to-trial variability (e.g., slow errors require sv > 0; Ratcliff & Rouder, 1998)
- Assumes constant drift rate within a trial
- Limited to two-choice decisions

---

## 2. Full DDM with Trial-to-Trial Variability

### Model Description

The full DDM extends the classic model by allowing three parameters to vary across trials according to specified distributions (Ratcliff & Tuerlinckx, 2002):

- Drift rate varies normally: v ~ N(v, sv)
- Starting point varies uniformly: z ~ U(z - sz/2, z + sz/2)
- Non-decision time varies uniformly: t0 ~ U(t0 - st0/2, t0 + st0/2)

### Additional Parameters

| Parameter | Symbol | Description | Typical Range | Source |
|-----------|--------|-------------|---------------|--------|
| Drift rate variability | sv | SD of cross-trial drift rate distribution | **0 – 2.0** (with s=0.1) | Ratcliff & McKoon, 2008 |
| Starting point variability | sz | Range of cross-trial starting point distribution | **0 – 0.3 × a** | Ratcliff & McKoon, 2008 |
| Non-decision time variability | st0 | Range of cross-trial non-decision time distribution | **0 – 0.3 s** | Ratcliff & McKoon, 2008 |

### Why Trial-to-Trial Variability Matters

- **sv > 0** produces **slow errors**: When drift rate varies across trials, low-drift trials produce both more errors and slower RTs, matching empirical data where errors are often slower than correct responses (Ratcliff & Rouder, 1998; Ratcliff, 1978)
- **sz > 0** produces **fast errors**: Starting point variability means some trials start closer to the wrong boundary, producing fast errors (Laming, 1968; Ratcliff & Rouder, 1998)
- **st0 > 0** accounts for the leading edge of the RT distribution being variable across trials

### When to Use

- When error RTs are systematically faster or slower than correct RTs (requires sv or sz to capture this pattern)
- When you have **> 200 trials per condition** for stable estimation of all 7 parameters (Ratcliff & Childers, 2015)
- When the goal is the most complete characterization of the decision process
- In domains where the full model is standard (e.g., recognition memory, lexical decision; Ratcliff et al., 2004)

### Strengths

- Captures nuanced RT distribution features (e.g., relative speed of correct vs. error responses)
- Most complete account of 2AFC RT data
- Well-established fitting tools available (fast-dm, DMAT)

### Limitations

- 7 free parameters require substantial data (> **200 trials per condition** recommended; Ratcliff & Childers, 2015)
- sv and sz are often poorly identifiable with limited data (Boehm et al., 2018)
- Longer fitting times due to numerical integration (no closed-form solution with variability parameters)
- Risk of overfitting with small datasets

### Identifiability Guidance

When trial counts are moderate (**100-200 per condition**), consider fixing one or more variability parameters:

1. Fix sz = 0 first (least impact on model fits in most domains; Ratcliff & Childers, 2015)
2. Fix st0 = 0 next if needed
3. sv is typically the most important variability parameter to retain (captures slow-error phenomenon)

---

## 3. EZ-Diffusion Model

### Model Description

The EZ-diffusion model (Wagenmakers et al., 2007) provides closed-form equations that map three summary statistics — mean RT for correct responses (MRT), RT variance for correct responses (VRT), and accuracy (Pc) — directly to three DDM parameters (v, a, t0). No iterative fitting is required.

### Parameters Estimated

| Parameter | Symbol | Estimated From | Typical Range | Source |
|-----------|--------|----------------|---------------|--------|
| Drift rate | v | Pc, MRT, VRT | Same as classic DDM | Wagenmakers et al., 2007, Equations 1-3 |
| Boundary separation | a | Pc, VRT | Same as classic DDM | Wagenmakers et al., 2007, Equations 1-3 |
| Non-decision time | t0 | MRT, v, a | Same as classic DDM | Wagenmakers et al., 2007, Equations 1-3 |

### Assumptions

- Starting point is unbiased: z = a/2 (not estimable)
- No trial-to-trial variability: sv = sz = st0 = 0
- Diffusion coefficient s is fixed (default **0.1**; Wagenmakers et al., 2007)

### Edge Correction

When accuracy is exactly 0, 0.5, or 1.0, the EZ equations are undefined. Apply the edge correction: replace extreme accuracy values by shifting them **half a trial** toward 0.5 (Wagenmakers et al., 2007):

```
If Pc = 1: Pc_corrected = 1 - 1/(2N)
If Pc = 0: Pc_corrected = 1/(2N)
If Pc = 0.5: Pc_corrected = 0.5 + 1/(2N)
```

where N is the number of trials.

### When to Use

- Quick exploratory analysis before committing to full model fitting
- Datasets with few trials per condition (**20-40**; Wagenmakers et al., 2007)
- Large-scale individual differences studies where computational efficiency matters
- When response bias is not of theoretical interest (z cannot be estimated)
- As a sanity check: EZ estimates should roughly agree with full DDM estimates

### Strengths

- No iterative fitting: closed-form, instantaneous computation
- Requires very few trials (as few as **20 per condition**; Wagenmakers et al., 2007, simulation results)
- Excellent parameter recovery in simulation studies (Wagenmakers et al., 2007, Table 1)
- Transparent: easy to implement and check

### Limitations

- Cannot estimate starting point bias (z) or trial-to-trial variability parameters
- Assumes no response bias — inappropriate if bias is expected (e.g., cue validity manipulations)
- Does not use error RT information (only uses accuracy and correct RT statistics)
- May not capture all features of the RT distribution

### Extensions

- **EZ2-diffusion** (Grasman et al., 2009): Extends EZ to estimate starting point z using accuracy and error RT statistics in addition to correct RT statistics. Requires error trials to be available.
- **Robust EZ** (Wagenmakers et al., 2007): Applies the model to individual participant data with bootstrapped confidence intervals.

---

## 4. Hierarchical DDM (HDDM)

### Model Description

The Hierarchical DDM (Wiecki et al., 2013) implements the DDM within a hierarchical Bayesian framework. Individual-level parameters are assumed to be drawn from group-level distributions, providing regularization (shrinkage toward group means) and enabling principled individual differences analysis.

### Hierarchical Structure

```
Group level: v_group ~ prior, a_group ~ prior, ...
 ↓
Individual: v_i ~ N(v_group, sigma_v), a_i ~ N(a_group, sigma_a), ...
 ↓
Trial level: RT_ij, accuracy_ij ~ DDM(v_i, a_i, t0_i, z_i)
```

### Default Priors (HDDM Python package)

| Parameter | Prior Distribution | Source |
|-----------|-------------------|--------|
| v (drift rate) | N(2, 3) | Wiecki et al., 2013, Table 1 |
| a (boundary) | Gamma(1.5, 0.75) | Wiecki et al., 2013, Table 1 |
| t0 (non-decision) | N(0.3, 0.5), truncated at 0 | Wiecki et al., 2013, Table 1 |
| z (starting point) | Beta(1, 1) — i.e., Uniform(0,1) as proportion of a | Wiecki et al., 2013, Table 1 |
| sv | Half-Normal | Wiecki et al., 2013 |

**Note**: These are the defaults in the HDDM package (v0.9+). Researchers should perform prior sensitivity analysis, especially for informative priors.

### When to Use

- Group comparisons (patients vs. controls, conditions) where you want to borrow strength across participants
- Moderate per-participant trial counts (**40-100 per condition**) where individual-level fitting is noisy — hierarchical shrinkage improves estimates (Wiecki et al., 2013)
- Individual differences research where you need reliable person-level parameter estimates
- When principled model comparison is needed (DIC, WAIC, Bayes factors)
- When you want full posterior distributions rather than point estimates

### Strengths

- Handles moderate trial counts better than individual-level fitting via hierarchical shrinkage (Wiecki et al., 2013)
- Provides full posterior distributions — natural uncertainty quantification
- Model comparison via DIC/WAIC (Spiegelhalter et al., 2002; Watanabe, 2010)
- Can include regression models on DDM parameters (e.g., linking neural data to drift rate)
- Well-maintained Python package with good documentation

### Limitations

- Computationally intensive: MCMC sampling can take hours for large datasets
- Requires convergence diagnostics (R-hat < **1.1**, effective sample size > **200**; Gelman & Rubin, 1992; Wiecki et al., 2013)
- Prior sensitivity: results can depend on prior choices, especially with small samples
- Group-level normality assumption may not hold for all parameters

### MCMC Diagnostics Checklist

1. **R-hat (Gelman-Rubin statistic)**: Should be < **1.1** for all parameters (Gelman & Rubin, 1992)
2. **Effective sample size**: Should be > **200** for reliable posterior summaries (Wiecki et al., 2013)
3. **Visual trace inspection**: Chains should show good mixing (no trends, no stuck periods)
4. **Posterior predictive checks**: Simulated data from the posterior should match observed RT distributions

---

## 5. Linear Ballistic Accumulator (LBA)

### Model Description

The LBA (Brown & Heathcote, 2008) is an alternative evidence accumulation model where evidence accumulates linearly (no within-trial noise) and deterministically on each trial, but with trial-to-trial variability in both drift rate and starting point. Each response option has its own accumulator racing toward a common threshold.

### Key Difference from DDM

| Feature | DDM | LBA |
|---------|-----|-----|
| Number of accumulators | 1 (single process, two boundaries) | N (one per response option) |
| Within-trial noise | Yes (Wiener diffusion) | No (ballistic/deterministic) |
| Between-trial variability | Source of stochasticity | Primary source of stochasticity |
| Response alternatives | 2 only | 2 or more (natural extension) |

### Parameters

| Parameter | Symbol | Description | Typical Range | Source |
|-----------|--------|-------------|---------------|--------|
| Mean drift rate | v_i | Mean drift for accumulator i | **0 – 5.0** | Brown & Heathcote, 2008, Table 1 |
| Drift rate variability | s_i | SD of drift for accumulator i (across trials) | **0.5 – 2.0** (often fixed to **1.0** for scaling) | Brown & Heathcote, 2008 |
| Response threshold | b | Common threshold for all accumulators | **1.0 – 5.0** | Brown & Heathcote, 2008, Table 1 |
| Starting point range | A | Upper bound of uniform starting point U(0, A) | **0 – b** | Brown & Heathcote, 2008 |
| Non-decision time | t0 | Encoding + motor execution time | **0.1 – 0.5 s** | Brown & Heathcote, 2008, Table 1 |

**Scaling convention**: One s_i (or the drift difference) is typically fixed for identification. Common choice: fix s = 1 for one accumulator (Donkin et al., 2011).

### When to Use

- Tasks with **more than 2 response alternatives** (natural multi-accumulator extension; Brown & Heathcote, 2008)
- When mathematical tractability is important: LBA has closed-form likelihood (Brown & Heathcote, 2008, Equation 1-3), making it fast to fit
- When within-trial noise is not theoretically important for your research question
- As a comparison model to DDM for model selection (Donkin et al., 2011)

### Strengths

- Natural extension to N > 2 alternatives without additional assumptions
- Closed-form likelihood — very fast fitting
- Mathematically simpler than DDM
- Good empirical fits across many paradigms (Donkin et al., 2011)

### Limitations

- No within-trial noise: cannot capture some phenomena that arise from noisy accumulation
- Different cognitive interpretation: stochasticity comes from trial-to-trial variability, not moment-to-moment noise
- Cannot distinguish between some mechanisms that DDM can (e.g., within-trial evidence fluctuations)
- May overfit with too many free parameters in multi-alternative tasks

---

## 6. Racing Diffusion Model (RDM)

### Model Description

The Racing Diffusion Model (Tillman et al., 2020) combines features of the DDM and LBA: multiple accumulators (one per response option) race toward a common boundary, but each accumulator is a diffusion process with within-trial noise (unlike LBA's ballistic accumulation).

### Parameters

| Parameter | Symbol | Description | Typical Range | Source |
|-----------|--------|-------------|---------------|--------|
| Drift rate per accumulator | v_i | Mean drift for accumulator i | **0.5 – 5.0** | Tillman et al., 2020, Table 1 |
| Boundary | a | Common threshold | **0.5 – 3.0** | Tillman et al., 2020, Table 1 |
| Non-decision time | t0 | Encoding + motor time | **0.1 – 0.5 s** | Tillman et al., 2020 |
| Within-trial noise | s | Diffusion coefficient (often fixed to **1.0**) | Fixed as scaling parameter | Tillman et al., 2020 |

### When to Use

- Multi-alternative tasks (> 2 choices) where within-trial noise is theoretically important
- When you believe that momentary evidence fluctuations matter (not just trial-to-trial variability)
- Model comparison studies: RDM vs. LBA to test whether within-trial noise improves fit (Tillman et al., 2020)

### Strengths

- Combines DDM's within-trial noise with multi-accumulator architecture
- More psychologically plausible than LBA for tasks involving noisy sensory evidence
- Can be fit using likelihood-free methods or analytical approximations

### Limitations

- More parameters than LBA for multi-alternative tasks
- No universally available software (though implementations exist in Julia and R)
- Relatively newer model; less empirical validation than DDM or LBA

---

## 7. Collapsing Bounds DDM

### Model Description

In the standard DDM, boundaries are fixed over time. The collapsing bounds variant allows the decision boundary to decrease as a function of time, implementing urgency — the idea that decision-makers become less cautious as time elapses (Hawkins et al., 2015; Palestro et al., 2018).

### Common Boundary Functions

| Function | Formula | Parameters | Source |
|----------|---------|------------|--------|
| Linear collapse | a(t) = a_0 - k × t | a_0 (initial), k (collapse rate) | Hawkins et al., 2015 |
| Exponential collapse | a(t) = a_0 × exp(-k × t) | a_0 (initial), k (collapse rate) | Palestro et al., 2018 |
| Weibull collapse | a(t) = a_0 × (1 - (t/lambda)^k) | a_0, lambda (scale), k (shape) | Hawkins et al., 2015 |

### When to Use

- Tasks with deadlines or response pressure where urgency is expected
- When standard DDM with fixed bounds provides poor fits to slow RT quantiles
- When testing theoretical claims about urgency signals (e.g., Cisek et al., 2009)
- Model comparison: test whether collapsing bounds improve fit over fixed bounds

### Strengths

- Captures urgency and deadline effects
- Can explain certain RT distribution shapes that fixed-bound DDM cannot
- Theoretically motivated by neural urgency signals (Churchland et al., 2008; Cisek et al., 2009)

### Limitations

- Adds at least 1-2 parameters for the boundary function
- Empirical evidence for collapsing bounds vs. fixed bounds is mixed (Hawkins et al., 2015; Palestro et al., 2018 — found limited evidence for collapsing bounds in standard tasks)
- May trade off with trial-to-trial variability parameters (identifiability concern)

---

## 8. Variant Comparison Summary

### Decision Matrix

| Variant | Free Parameters | Min Trials per Condition | Fitting Complexity | Multi-Alternative | Key Use Case |
|---------|-----------------|--------------------------|-------------------|-------------------|--------------|
| Classic DDM | 4 | **40+** (Ratcliff & Childers, 2015) | Moderate | No (2 only) | Standard decomposition |
| Full DDM | 7 | **200+** (Ratcliff & Childers, 2015) | High | No (2 only) | Complete characterization |
| EZ-diffusion | 3 | **20+** (Wagenmakers et al., 2007) | None (closed-form) | No (2 only) | Quick estimation |
| HDDM | 4-7 per person | **40+** per person (Wiecki et al., 2013) | High (MCMC) | No (2 only) | Group studies, individual differences |
| LBA | 5+ | **40+** (Brown & Heathcote, 2008) | Low (closed-form likelihood) | Yes | Multi-alternative tasks |
| Racing Diffusion | 4+ per accumulator | **100+** (Tillman et al., 2020) | High | Yes | Multi-alternative with within-trial noise |
| Collapsing Bounds DDM | 5-6 | **200+** (Hawkins et al., 2015) | High | No (2 only) | Urgency/deadline tasks |

### Quick Selection Guide

```
Start here:
│
├── 2-choice task?
│ ├── YES
│ │ ├── < 40 trials per condition → EZ-diffusion
│ │ ├── 40-200 trials → Classic DDM or HDDM (if group study)
│ │ ├── > 200 trials → Full DDM
│ │ └── Urgency/deadline present? → Consider collapsing bounds
│ │
│ └── NO (> 2 choices)
│ ├── Within-trial noise important? → Racing Diffusion Model
│ └── Otherwise → LBA
│
└── Group-level analysis?
 ├── YES, with moderate per-person data → HDDM
 └── NO, or large per-person data → Fit individually with classic/full DDM
```

---

## References

- Brown, S. D., & Heathcote, A. (2008). The simplest complete model of choice response time: Linear ballistic accumulation. *Cognitive Psychology*, 57(3), 153–178.
- Boehm, U., Annis, J., Frank, M. J., Hawkins, G. E., Heathcote, A., Kellen, D., ... & Wagenmakers, E.-J. (2018). Estimating across-trial variability parameters of the diffusion decision model: Expert advice and recommendations. *Journal of Mathematical Psychology*, 87, 46–75.
- Churchland, A. K., Kiani, R., & Shadlen, M. N. (2008). Decision-making with multiple alternatives. *Nature Neuroscience*, 11(6), 693–702.
- Cisek, P., Puskas, G. A., & El-Murr, S. (2009). Decisions in changing conditions: The urgency-gating model. *Journal of Neuroscience*, 29(37), 11560–11571.
- Donkin, C., Averell, L., Brown, S., & Heathcote, A. (2009). Getting more from accuracy and response time data: Methods for fitting the linear ballistic accumulator. *Behavior Research Methods*, 41(4), 1095–1110.
- Donkin, C., Brown, S., Heathcote, A., & Wagenmakers, E.-J. (2011). Diffusion versus linear ballistic accumulation: Different models but the same conclusions about psychological processes? *Psychonomic Bulletin & Review*, 18(1), 61–69.
- Grasman, R. P. P. P., Wagenmakers, E.-J., & van der Maas, H. L. J. (2009). On the mean and variance of response times under the diffusion model with an application to parameter estimation. *Journal of Mathematical Psychology*, 53(2), 55–68.
- Hawkins, G. E., Forstmann, B. U., Wagenmakers, E.-J., Ratcliff, R., & Brown, S. D. (2015). Revisiting the evidence for collapsing boundaries and urgency signals in perceptual decision-making. *Journal of Neuroscience*, 35(6), 2476–2484.
- Heathcote, A., Brown, S., & Mewhort, D. J. K. (2002). Quantile maximum probability as a method for response time distributions. *Psychonomic Bulletin & Review*, 9(2), 394–401.
- Laming, D. R. J. (1968). *Information theory of choice-reaction times*. London: Academic Press.
- Matzke, D., & Wagenmakers, E.-J. (2009). Psychological interpretation of the ex-Gaussian and shifted Wald parameters: A diffusion model analysis. *Psychonomic Bulletin & Review*, 16(5), 798–817.
- Navarro, D. J., & Fuss, I. G. (2009). Fast and accurate calculations for first-passage times in Wiener diffusion models. *Journal of Mathematical Psychology*, 53(4), 222–230.
- Palestro, J. J., Weichart, E., Sederberg, P. B., & Turner, B. M. (2018). Some task demands induce collapsing bounds: Evidence from a behavioral analysis. *Psychonomic Bulletin & Review*, 25(4), 1225–1248.
- Ratcliff, R. (1978). A theory of memory retrieval. *Psychological Review*, 85(2), 59–108.
- Ratcliff, R., & Childers, R. (2015). Individual differences and fitting methods for the two-choice diffusion model of decision making. *Decision*, 2(4), 237–279.
- Ratcliff, R., Gomez, P., & McKoon, G. (2004). A diffusion model account of the lexical decision task. *Psychological Review*, 111(1), 159–182.
- Ratcliff, R., & McKoon, G. (2008). The diffusion decision model: Theory and data for two-choice decision tasks. *Neural Computation*, 20(4), 873–922.
- Ratcliff, R., & Rouder, J. N. (1998). Modeling response times for two-choice decisions. *Psychological Science*, 9(5), 347–356.
- Ratcliff, R., & Tuerlinckx, F. (2002). Estimating parameters of the diffusion model: Approaches to dealing with contaminant reaction times and parameter variability. *Psychonomic Bulletin & Review*, 9(3), 438–481.
- Tillman, G., Van Zandt, T., & Logan, G. D. (2020). Sequential sampling models without random between-trial variability: The racing diffusion model with its three-boundary extension. *Journal of Mathematical Psychology*, 96, 102368.
- Voss, A., Nagler, M., & Lerche, V. (2013). Diffusion models in experimental psychology: A practical introduction. *Experimental Psychology*, 60(6), 385–402.
- Voss, A., Rothermund, K., & Voss, J. (2004). Interpreting the parameters of the diffusion model: An empirical validation. *Memory & Cognition*, 32(7), 1206–1220.
- Wagenmakers, E.-J., van der Maas, H. L. J., & Grasman, R. P. P. P. (2007). An EZ-diffusion model for response time and accuracy. *Psychonomic Bulletin & Review*, 14(1), 3–22.
- Wiecki, T. V., Sofer, I., & Frank, M. J. (2013). HDDM: Hierarchical Bayesian estimation of the drift-diffusion model in Python. *Frontiers in Neuroinformatics*, 7, 14.
