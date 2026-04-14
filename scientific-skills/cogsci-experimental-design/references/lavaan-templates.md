# lavaan Model Templates for Creativity Mediation Analysis

## Basic Mediation Model

### CSE Mediating AI Condition → Creativity (Lee & Chung, 2024)

```r
library(lavaan)

# ---- Data Preparation ----
# condition: 0 = no assistance, 1 = ChatGPT (or dummy-coded for 3 conditions)
# cse: mean of 3 CSE items (Tierney & Farmer, 2002)
# creativity: AUT originality score, semantic distance, or composite

# ---- Model Specification ----
med_model <- '
 # Path a: Condition → Creative Self-Efficacy
 cse ~ a * condition

 # Path b: CSE → Creativity (controlling for condition)
 # Path c_prime: Condition → Creativity (direct effect)
 creativity ~ b * cse + cprime * condition

 # Defined parameters
 indirect := a * b # Indirect (mediated) effect
 total := cprime + a * b # Total effect
'

# ---- Estimation ----
fit <- sem(med_model, data = df,
 se = "bootstrap",
 bootstrap = 5000,
 estimator = "ML")

# ---- Results ----
summary(fit, ci = TRUE, standardized = TRUE)
parameterEstimates(fit, boot.ci.type = "bca.simple",
 level = 0.95, ci = TRUE)
```

## Multi-Condition Mediation (3 conditions)

When comparing ChatGPT, Web Search, and No Assistance:

```r
# Create dummy codes (No Assistance = reference)
df$chatgpt <- ifelse(df$condition == "chatgpt", 1, 0)
df$websearch <- ifelse(df$condition == "websearch", 1, 0)

multi_med_model <- '
 # Path a: Each condition → CSE
 cse ~ a1 * chatgpt + a2 * websearch

 # Path b and direct effects
 creativity ~ b * cse + c1 * chatgpt + c2 * websearch

 # Indirect effects for each condition
 indirect_chatgpt := a1 * b
 indirect_websearch := a2 * b

 # Total effects
 total_chatgpt := c1 + a1 * b
 total_websearch := c2 + a2 * b

 # Contrast: ChatGPT vs Web Search indirect effect
 indirect_diff := (a1 - a2) * b
'

fit_multi <- sem(multi_med_model, data = df,
 se = "bootstrap", bootstrap = 5000)
```

## Moderated Mediation

### Baseline Creativity (RAT) Moderating the a-path

```r
# Center the moderator
df$rat_c <- scale(df$rat_score, center = TRUE, scale = FALSE)

# Create interaction term
df$cond_x_rat <- df$condition * df$rat_c

modmed_model <- '
 # Moderated path a: condition effect on CSE depends on RAT
 cse ~ a1 * condition + a2 * rat_c + a3 * cond_x_rat

 # Path b and direct effect
 creativity ~ b * cse + cprime * condition + b2 * rat_c

 # Conditional indirect effects
 # At mean RAT (rat_c = 0):
 indirect_mean := a1 * b

 # Note: For indirect effects at +/- 1 SD of RAT,
 # compute manually:
 # indirect_high = (a1 + a3 * SD_rat) * b
 # indirect_low = (a1 - a3 * (-SD_rat)) * b
'

fit_modmed <- sem(modmed_model, data = df,
 se = "bootstrap", bootstrap = 5000)
```

### Probing the Interaction (Simple Slopes)

```r
library(emmeans)

# Using linear regression for simple slopes
lm_model <- lm(cse ~ condition * rat_c, data = df)

# Simple slopes at ±1 SD of RAT
emtrends(lm_model, ~ condition, var = "rat_c")

# Or use Johnson-Neyman technique
library(interactions)
johnson_neyman(lm_model, pred = condition, modx = rat_c)
```

## Latent Variable Version

When CSE is modeled as a latent variable (recommended if alpha < 0.85):

```r
latent_med_model <- '
 # Measurement model
 CSE =~ cse1 + cse2 + cse3

 # Structural model
 CSE ~ a * condition
 creativity ~ b * CSE + cprime * condition

 # Effects
 indirect := a * b
 total := cprime + a * b
'

fit_latent <- sem(latent_med_model, data = df,
 se = "bootstrap", bootstrap = 5000)
```

## Model Fit Evaluation

### Fit Indices (for models with measurement component)

| Index | Good Fit | Acceptable | Source |
|-------|----------|------------|--------|
| CFI | ≥ 0.95 | ≥ 0.90 | Hu & Bentler, 1999 |
| TLI | ≥ 0.95 | ≥ 0.90 | Hu & Bentler, 1999 |
| RMSEA | ≤ 0.06 | ≤ 0.08 | Hu & Bentler, 1999 |
| SRMR | ≤ 0.08 | ≤ 0.10 | Hu & Bentler, 1999 |

```r
fitMeasures(fit, c("cfi", "tli", "rmsea", "srmr"))
```

### For Saturated Path Models

- Path-only mediation models (no latent variables, no constraints) are **saturated** (df = 0)
- Fit indices are undefined for saturated models
- Evaluate by: significance of paths, R-squared, indirect effect CIs

## Required R Packages

```r
install.packages(c("lavaan", "emmeans", "interactions", "boot"))

# Version requirements
# lavaan >= 0.6-12 (for bootstrap CI types)
# R >= 4.0
```
