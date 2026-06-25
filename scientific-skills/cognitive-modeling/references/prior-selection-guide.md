# Prior Selection Guide for Bayesian Cognitive Models

This reference provides detailed prior recommendations for cognitive model parameters, organized by model family. Every numerical recommendation includes a citation or justification.

## General Prior Selection Workflow

1. **Identify the parameter type** (location, scale, probability, positive continuous, bounded)
2. **Check the domain-specific table below** for your model family
3. **Run a prior predictive check** to verify plausibility (see procedure at bottom)
4. **Document your prior choices** with justifications in your manuscript

## Prior Families Overview

### Normal / Gaussian

- **Use for**: Unbounded continuous parameters (regression coefficients, latent abilities, d')
- **Parameterization**: Normal(mean, sd)
- **Weakly informative default**: Center at theoretically neutral value (often 0), set sd to cover plausible range such that 95% prior mass spans roughly 2x the expected parameter range (Gelman et al., 2008)

### Student-t

- **Use for**: Unbounded continuous parameters when robustness to outliers is desired
- **Parameterization**: Student-t(df, location, scale)
- **Recommendation**: df=3 for heavy tails, df=7 for moderate tails (Gelman et al., 2013, Ch. 2)
- **Note**: Converges to Normal as df increases; Cauchy is the special case df=1

### Half-Normal / Half-Cauchy

- **Use for**: Standard deviation (scale) parameters, which must be positive
- **Half-Normal(0, sd)**: Recommended when you have a reasonable expectation for the scale; more informative than Half-Cauchy (Gelman, 2006)
- **Half-Cauchy(0, sd)**: Heavier tails; recommended as a default for group-level SDs when little is known; largely superseded by Half-Normal with thoughtful sd choice (Polson & Scott, 2012)
- **Current recommendation**: Half-Normal is generally preferred over Half-Cauchy for hierarchical SDs (Stan Prior Choice Recommendations wiki, 2023)

### Beta

- **Use for**: Parameters bounded in [0, 1] (probabilities, learning rates, proportions)
- **Parameterization**: Beta(alpha, beta)
- **Key shapes**:
 - Beta(1, 1) = Uniform on [0,1] -- non-informative (Kruschke, 2015, Ch. 6)
 - Beta(1.1, 1.1) -- weakly informative, gently regularizes away from 0 and 1
 - Beta(2, 2) -- weakly informative, mildly peaked at 0.5
 - Beta(a, b) with a, b > 2 -- increasingly informative toward a/(a+b)

### Gamma / Inverse-Gamma

- **Use for**: Positive continuous parameters (rate parameters, precision)
- **Parameterization**: Gamma(shape, rate) where mean = shape/rate
- **Caution**: Inverse-Gamma priors on variance parameters can be overly informative near zero; prefer Half-Normal or Half-Cauchy on SD parameters instead (Gelman, 2006)

### Lognormal

- **Use for**: Positive continuous parameters where multiplicative effects are expected (reaction times, neural firing rates)
- **Parameterization**: Lognormal(mu, sigma) where the parameter's log is Normal(mu, sigma)
- **Advantage**: Natural for parameters that span orders of magnitude; provides soft lower bound at zero

### LKJ (Lewandowski-Kurowicka-Joe)

- **Use for**: Correlation matrices in multivariate hierarchical models
- **Parameterization**: LKJ(eta)
- **Key values**:
 - eta = 1: Uniform over valid correlation matrices (Lewandowski et al., 2009)
 - **eta = 2**: Weakly informative; mildly favors smaller correlations; **Stan's recommended default** (Stan User's Guide, Section 1.13)
 - eta > 2: Increasingly concentrates around the identity matrix (zero correlations)
- **Implementation note**: Always use the Cholesky factor parameterization (`lkj_corr_cholesky` in Stan, `LKJCholeskyCov` in PyMC) for numerical stability

### Dirichlet

- **Use for**: Probability vectors that sum to 1 (mixture weights, multinomial probabilities)
- **Parameterization**: Dirichlet(alpha_1, ..., alpha_K)
- **Key shapes**:
 - All alpha_k = 1: Uniform on the simplex (Gelman et al., 2013, Ch. 2)
 - All alpha_k = 0.5: Jeffreys prior; concentrates near vertices (sparse)
 - All alpha_k = 2: Weakly informative; concentrates toward center (1/K, ..., 1/K)

---

## Cognitive-Domain-Specific Prior Tables

### Drift-Diffusion Model (DDM) Parameters

All ranges below assume the within-trial noise scaling parameter s = 1.0 (Navarro & Fuss, 2009 convention). If using s = 0.1 (Ratcliff, 1978 convention), divide all values by 10.

| Parameter | Symbol | Constraint | Recommended Prior | Justification | Source |
|-----------|--------|------------|-------------------|---------------|--------|
| Drift rate | v | Unbounded (typically -5 to 5) | Normal(0, 2) | Centers at no evidence; 95% mass covers -4 to 4, matching empirical range | Matzke & Wagenmakers, 2009; Wiecki et al., 2013 |
| Boundary separation | a | Positive (typically 0.5 to 2.5) | Half-Normal(0, 1) or Gamma(2, 2) | Must be positive; empirical values cluster around 0.5-2.0 | Matzke & Wagenmakers, 2009; Wiecki et al., 2013 |
| Non-decision time | t | Positive (typically 0.1 to 0.5 s) | Uniform(0.1, 1.0) or Gamma(4, 15) | Lower bound reflects minimum sensory+motor time (~100 ms); upper bound prevents absorbing observed RT | Matzke & Wagenmakers, 2009; Ratcliff & McKoon, 2008 |
| Starting point bias | z | (0, 1) as proportion of a | Beta(5, 5) centered at 0.5 | Weakly informative around no bias; allows moderate deviations | Wiecki et al., 2013 |
| Drift rate variability | sv | Positive | Half-Normal(0, 1) | Across-trial variability; can be difficult to estimate -- consider fixing to 0 if data are sparse | Ratcliff & McKoon, 2008 |
| Non-decision time variability | st | Positive, < t | Uniform(0, 0.3) or Half-Normal(0, 0.1) | Typically small; bounded by non-decision time itself | Ratcliff & McKoon, 2008 |

### Signal Detection Theory (SDT) Parameters

| Parameter | Symbol | Constraint | Recommended Prior | Justification | Source |
|-----------|--------|------------|-------------------|---------------|--------|
| Sensitivity | d' | Unbounded (typically 0 to 4) | Normal(0, 2) | Weakly informative; covers typical experimental range; allows negative d' for below-chance performance | Macmillan & Creelman, 2005; Rouder & Lu, 2005 |
| Criterion | c | Unbounded (typically -2 to 2) | Normal(0, 1.5) | Centered at no bias; covers liberal to conservative range | Macmillan & Creelman, 2005 |
| Hit rate | H | (0, 1) | Beta(1, 1) | Uniform; let data inform | Rouder & Lu, 2005 |
| False alarm rate | F | (0, 1) | Beta(1, 1) | Uniform; let data inform | Rouder & Lu, 2005 |
| Unequal variance ratio | sigma_s/sigma_n | Positive | Lognormal(0, 0.5) centered near 1 | Typical values 1.0-1.5 in recognition memory | Mickes et al., 2007 |

### Reinforcement Learning (RL) Parameters

| Parameter | Symbol | Constraint | Recommended Prior | Justification | Source |
|-----------|--------|------------|-------------------|---------------|--------|
| Learning rate | alpha | (0, 1) | Beta(1.1, 1.1) | Weakly informative; allows full range; gently regularizes away from 0 and 1 | Daw, 2011; Gershman, 2016 |
| Inverse temperature | beta | Positive (typically 0.5 to 20) | Gamma(2, 1) or Lognormal(1, 1) | Must be positive; empirical values commonly 1-10; higher values rare | Daw, 2011 |
| Decay rate | gamma | (0, 1) | Beta(2, 2) | Weakly informative centered at 0.5; values near 0 or 1 are unlikely in most tasks | Sutton & Barto, 2018, Ch. 3 |
| Perseveration | rho | Unbounded | Normal(0, 1) | Centered at no perseveration; can be positive (stay) or negative (switch) | Lau & Glimcher, 2005 |
| Dual learning rates (pos/neg PE) | alpha+, alpha- | (0, 1) each | Beta(1.1, 1.1) each | Same rationale as single learning rate; allows asymmetric updating | Frank et al., 2007 |

### Multinomial Processing Tree (MPT) Parameters

| Parameter | Symbol | Constraint | Recommended Prior | Justification | Source |
|-----------|--------|------------|-------------------|---------------|--------|
| Processing probabilities | p_i | (0, 1) | Beta(1, 1) for non-informative; Beta(a, b) from prior literature | Each processing path probability is independently bounded | Klauer, 2010 |
| Latent-trait (probit-transformed) | Phi^(-1)(p_i) | Unbounded | Normal(0, 1) | Standard probit prior for hierarchical MPT | Klauer, 2010 |
| Correlation of latent traits | R | Correlation matrix | LKJ(2) | Weakly informative; regularizes toward independence | Klauer, 2010; Stan User's Guide |

### Item Response Theory (IRT) Parameters

| Parameter | Symbol | Constraint | Recommended Prior | Justification | Source |
|-----------|--------|------------|-------------------|---------------|--------|
| Person ability | theta | Unbounded | Normal(0, 1) by convention | Identifies the scale; standard in IRT | de Boeck & Wilson, 2004 |
| Item difficulty | b | Unbounded | Normal(0, 2) | Weakly informative; typical range -3 to 3 on the logit scale | de Boeck & Wilson, 2004 |
| Item discrimination | a | Positive | Lognormal(0, 0.5) | Must be positive; typical range 0.5-3.0; Lognormal prevents negative values | de Boeck & Wilson, 2004; Buerkner, 2020 |
| Guessing parameter | c | (0, 0.5) | Beta(5, 23) | Peaked near 0.2 (1/5 for 5-option MC); upper bound reflects that guessing above chance is rare | de Boeck & Wilson, 2004 |

### Neural/Electrophysiological Parameters

| Parameter | Symbol | Constraint | Recommended Prior | Justification | Source |
|-----------|--------|------------|-------------------|---------------|--------|
| Firing rate | lambda | Positive | Gamma(2, 0.1) or Lognormal(2, 1) | Must be positive; typical cortical rates 1-100 Hz; allows wide range | Dayan & Abbott, 2001, Ch. 1 |
| ERP amplitude | A | Unbounded | Normal(0, 10) in microvolts | ERP components typically -15 to +15 uV; generous coverage | Luck, 2014, Ch. 1 |
| ERP latency | tau | Positive (ms) | Normal(expected_peak, 50) truncated at 0 | Component-specific: e.g., N400 expected at 400 ms; truncation enforces positivity | Luck, 2014, Ch. 2 |

---

## Hierarchical Prior Structure

For any parameter theta with individual-level values theta_j (j = 1, ..., J participants):

### Standard Two-Level Hierarchy

```
Group level:
 mu_theta ~ [weakly informative prior from tables above]
 sigma_theta ~ Half-Normal(0, sd_hyper)

Individual level (non-centered):
 eta_j ~ Normal(0, 1)
 theta_j = mu_theta + sigma_theta * eta_j
```

### Choosing sd_hyper for Group-Level SD

The hyperprior on sigma_theta (the between-participant SD) is often the most consequential prior choice. Recommendations:

- **Half-Normal(0, 1)**: Safe default when parameters are on a standardized scale (Gelman, 2006)
- **Half-Normal(0, sd)** where sd is set to roughly the expected magnitude of individual differences. For example, if you expect drift rates to vary by roughly 0.5 across participants, use Half-Normal(0, 0.5) (Gelman, 2006)
- **Exponential(1)**: Alternative that assigns more mass near zero; useful when you suspect small individual differences (Gelman et al., 2013, Ch. 5)

> **Warning**: Do not use Inverse-Gamma(epsilon, epsilon) (e.g., Inverse-Gamma(0.001, 0.001)) as a "non-informative" prior on variance. This is a legacy BUGS/JAGS practice that creates an informative prior concentrated away from zero, distorting hierarchical shrinkage (Gelman, 2006).

---

## Prior Predictive Checking Procedure

### Step-by-Step Protocol

1. **Define the full generative model** including all priors and hyperpriors
2. **Sample N_sim = 500-1000 parameter sets** from the prior (no data involved)
3. **For each parameter set, simulate a complete dataset** with the same structure as your real data (same number of participants, trials, conditions)
4. **Compute summary statistics** on each simulated dataset:
 - For RT models: mean RT, SD of RT, quantiles (0.1, 0.5, 0.9), proportion of RTs < 100 ms, proportion > 5 s
 - For accuracy models: overall accuracy, accuracy by condition
 - For learning models: learning curve shape, final performance level
5. **Visualize the distribution of summary statistics** across simulations
6. **Check for absurdities**:

| Red Flag | Likely Cause | Fix |
|----------|-------------|-----|
| Negative RTs or RTs > 60 s | Non-decision time prior too diffuse, or drift rate prior allows values near 0 | Tighten lower bound on t; ensure v prior has reasonable mass away from 0 |
| Accuracy always near 50% | Drift rate prior centered at 0 with small SD | Widen drift rate prior or add condition-specific means |
| Accuracy always near 100% | Boundary separation prior too high relative to drift | Lower the upper tail of boundary separation prior |
| Learning rate = 0 or 1 for most draws | Beta prior concentrating at boundaries | Use Beta(1.1, 1.1) or Beta(2, 2) |
| Predicted firing rates > 1000 Hz | Gamma/Lognormal prior too diffuse | Tighten the rate prior; cortical neurons rarely exceed 200 Hz (Dayan & Abbott, 2001) |

7. **Iterate** until prior predictive distributions cover the plausible data space without substantial mass on implausible values
8. **Document** the final prior specification and the prior predictive check results

### Example: Prior Predictive Check for Hierarchical DDM

```
# Pseudocode for prior predictive check
for i in 1:1000:
 mu_v ~ Normal(0, 2) # Group mean drift rate
 sigma_v ~ Half-Normal(0, 1) # Between-participant SD
 mu_a ~ Half-Normal(0, 1) # Group mean boundary
 sigma_a ~ Half-Normal(0, 0.5)
 mu_t ~ Uniform(0.1, 1.0) # Group mean non-decision time
 sigma_t ~ Half-Normal(0, 0.1)

 for j in 1:30: # 30 simulated participants
 v_j = mu_v + sigma_v * Normal(0,1)
 a_j = |mu_a + sigma_a * Normal(0,1)| # enforce positive
 t_j = clip(mu_t + sigma_t * Normal(0,1), 0.05, 2.0)

 Simulate 100 DDM trials with (v_j, a_j, t_j)

 Store summary statistics (mean RT, accuracy, RT quantiles)

Plot distributions of summary statistics
Check: Are simulated RTs in [0.2, 5.0] s? Is accuracy in [0.5, 1.0]?
```

## References

- Buerkner, P. C. (2020). Bayesian item response modeling in R with brms and Stan. *arXiv:1905.09501*.
- Daw, N. D. (2011). Trial-by-trial data analysis using computational models. In *Decision Making, Affect, and Learning*. Oxford University Press.
- Dayan, P., & Abbott, L. F. (2001). *Theoretical Neuroscience*. MIT Press.
- de Boeck, P., & Wilson, M. (2004). *Explanatory Item Response Models*. Springer.
- Frank, M. J., Moustafa, A. A., Haughey, H. M., Curran, T., & Hutchison, K. E. (2007). Genetic triple dissociation reveals multiple roles for dopamine in reinforcement learning. *PNAS*, 104(41), 16311-16316.
- Gelman, A. (2006). Prior distributions for variance parameters in hierarchical models. *Bayesian Analysis*, 1(3), 515-534.
- Gelman, A., Jakulin, A., Pittau, M. G., & Su, Y. S. (2008). A weakly informative default prior distribution for logistic and other regression models. *Annals of Applied Statistics*, 2(4), 1360-1383.
- Gelman, A., et al. (2013). *Bayesian Data Analysis* (3rd ed.). Chapman and Hall/CRC.
- Gershman, S. J. (2016). Empirical priors for reinforcement learning models. *Journal of Mathematical Psychology*, 71, 1-6.
- Klauer, K. C. (2010). Hierarchical multinomial processing tree models: A latent-trait approach. *Psychometrika*, 75(1), 70-98.
- Kruschke, J. K. (2015). *Doing Bayesian Data Analysis* (2nd ed.). Academic Press.
- Lau, B., & Glimcher, P. W. (2005). Dynamic response-by-response models of matching behavior in rhesus monkeys. *Journal of the Experimental Analysis of Behavior*, 84(3), 555-579.
- Lewandowski, D., Kurowicka, D., & Joe, H. (2009). Generating random correlation matrices based on vines and extended onion method. *Journal of Multivariate Analysis*, 100(9), 1989-2001.
- Luck, S. J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.). MIT Press.
- Macmillan, N. A., & Creelman, C. D. (2005). *Detection Theory: A User's Guide* (2nd ed.). Lawrence Erlbaum Associates.
- Matzke, D., & Wagenmakers, E. J. (2009). Psychological interpretation of the ex-Gaussian and shifted Wald parameters: A diffusion model analysis. *Psychonomic Bulletin & Review*, 16, 798-817.
- Mickes, L., Wixted, J. T., & Wais, P. E. (2007). A direct test of the unequal-variance signal detection model of recognition memory. *Psychonomic Bulletin & Review*, 14(5), 858-865.
- Polson, N. G., & Scott, J. G. (2012). On the half-Cauchy prior for a global scale parameter. *Bayesian Analysis*, 7(4), 887-902.
- Ratcliff, R. (1978). A theory of memory retrieval. *Psychological Review*, 85(2), 59-108.
- Ratcliff, R., & McKoon, G. (2008). The diffusion decision model: Theory and data for two-choice decision tasks. *Neural Computation*, 20(4), 873-922.
- Rouder, J. N., & Lu, J. (2005). An introduction to Bayesian hierarchical models with an application in the theory of signal detection. *Psychonomic Bulletin & Review*, 12, 573-604.
- Sutton, R. S., & Barto, A. G. (2018). *Reinforcement Learning: An Introduction* (2nd ed.). MIT Press.
- Wiecki, T. V., Sofer, I., & Frank, M. J. (2013). HDDM: Hierarchical Bayesian estimation of the drift-diffusion model in Python. *Frontiers in Neuroinformatics*, 7, 14.
