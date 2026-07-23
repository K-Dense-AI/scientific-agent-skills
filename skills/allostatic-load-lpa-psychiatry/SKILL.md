---
name: allostatic-load-lpa-psychiatry
description: Perform Latent Profile Analysis (LPA) on Allostatic Load Index (ALI) multi-system biomarkers and conduct complex-sample weighted regression to analyze relationships with psychiatric outcomes (depression, stress, quality of life) including gender moderation.
metadata:
  version: "1.0"
---

# Allostatic Load LPA and Psychiatric Outcome Analysis

## When to Use

Use this skill when you need to perform **Latent Profile Analysis (LPA)** to identify heterogeneous subgroups (latent classes) of physiological stress wear-and-tear (**Allostatic Load**) based on multi-system clinical biomarkers, and subsequently evaluate their associations with psychiatric outcomes (such as depression, subjective stress, and health-related quality of life) using **complex-sample survey designs** and **gender moderation (interaction terms)**.

This is highly relevant for epidemiological datasets containing multi-system clinical measures (Cardiovascular, Metabolic, Inflammatory/Immune) and standardized psychiatric scales (e.g., PHQ-9, EQ-5D) such as the **Korea National Health and Nutrition Examination Survey (KNHANES)** or **Midlife in the United States (MIDUS)**.

## Workflow

1. **Cohort & Biomarker Preprocessing**:
   - Filter the dataset for the target population (typically adult cohort, age $\ge$ 19).
   - Gather continuous multi-system biomarkers. Standardize them (Z-score) using `as.numeric(scale(.))` to eliminate scale discrepancies.
     - *Cardiovascular*: Systolic Blood Pressure (SBP), Diastolic Blood Pressure (DBP), Heart Rate (HR).
     - *Metabolic*: BMI, Waist Circumference (WC), Fasting Glucose, HbA1c, Total Cholesterol, HDL-Cholesterol, Triglycerides.
     - *Inflammatory*: WBC count, hs-CRP (High-Sensitivity C-Reactive Protein).
2. **Outcome & Covariate Recoding**:
   - Continuous outcomes (e.g., PHQ-9 score, EQ-5D Index).
   - Binary outcomes (e.g., Clinical Depression [PHQ-9 $\ge$ 10], Subjective High Stress).
   - Covariates (Age, Income, Education, Smoking, Drinking, Physical Activity, Medication use).
   - Recode sex/gender into binary `female` (0=Male, 1=Female) for clean interaction term modeling.
3. **Latent Profile Analysis (LPA)**:
   - Run LPA models with classes ranging from 1 to 4 using R package `tidyLPA`.
   - Evaluate model fit indices:
     - **BIC / SSABIC**: Lower is better.
     - **Entropy**: Higher is better (values $\ge$ 0.80 indicate highly precise classification).
     - **BLRT / LMR-LRT**: Check p-values ($p < 0.05$) to see if $k$-class model significantly improves upon the $k-1$ class model.
   - Assign individuals to their optimal latent profile.
4. **Complex Sample Survey Specification**:
   - Set up the survey design utilizing the `survey` package in R, accounting for **stratification (`kstrata`)**, **clustering (`psu`)**, and **integrated health exam weights (`wt_tot` or similar)**.
5. **Weighted Regression & Moderation Modeling**:
   - Execute weighted generalized linear models (`svyglm`).
   - Run linear regression for continuous outcomes (PHQ-9 score, EQ-5D) and logistic regression for binary outcomes (depression status, stress).
   - Include interaction terms (`profile * female`) to statistically test the moderating role of gender on the relationship between biological stress profiles and psychiatric outcomes.

## Examples

Below is a complete, execution-tested R pipeline demonstrating the exact preprocessing, LPA model estimation, fit comparisons, survey design declaration, and weighted moderation regression.

```R
# ==============================================================================
# Allostatic Load LPA & Complex-Sample Psychiatric Regression Script
# ==============================================================================

library(tidyverse)
library(tidyLPA)
library(survey)

# 1. Load Preprocessed Clean Dataset
data_path <- "knhanes_clean_adults.csv"
df <- read_csv(data_path)

# Define continuous biomarkers across 3 physiological systems
biomarkers <- c(
  "HE_sbp", "HE_dbp", "HE_heart_rate",                              # Cardiovascular
  "HE_BMI", "HE_wc", "HE_glu", "HE_HbA1c", "HE_chol", "HE_HDL_st2", "HE_TG", # Metabolic
  "HE_WBC", "HE_hsCRP"                                              # Inflammatory/Immune
)

# Extract complete-case cohort for precise biological profiling
df_lpa <- df %>% drop_na(all_of(biomarkers))
cat("LPA Sample Size (N):", nrow(df_lpa), "\n")

# ------------------------------------------------------------------------------
# 2. Standardize Biomarkers & Run LPA Models
# ------------------------------------------------------------------------------
# Force continuous vectors (avoiding R scale matrix class constraints)
df_lpa_std <- df_lpa %>%
  mutate(across(all_of(biomarkers), ~as.numeric(scale(.))))

# Fit latent profile models (Classes 1 to 4)
# Model 1 uses equal variances and covariance fixed to 0 (Standard Diagonal Model)
lpa_models <- df_lpa_std %>%
  select(all_of(biomarkers)) %>%
  estimate_profiles(1:4, models = 1)

# Compare Model Fits (Check BIC, SSABIC, Entropy)
print(compare_solutions(lpa_models))

# ------------------------------------------------------------------------------
# 3. Class Assignation and Survey Design Declaration
# ------------------------------------------------------------------------------
# Choose optimal classes (e.g., 3-Class solution: Healthy, Metabolic Risk, Diabetic Risk)
optimal_classes <- 3
final_lpa <- df_lpa_std %>%
  select(all_of(biomarkers)) %>%
  estimate_profiles(optimal_classes, models = 1)

# Merge profiles back to original data
df_survey_data <- df_lpa %>% 
  mutate(profile = as.factor(get_data(final_lpa)$Class)) %>%
  drop_na(wt_tot) # Drop missing survey weights

# Declare Complex Survey Design (Stratum: kstrata, Cluster: psu, Weight: wt_tot)
knhanes_design <- svydesign(
  ids = ~psu,
  strata = ~kstrata,
  weights = ~wt_tot,
  data = df_survey_data,
  nest = TRUE
)

# ------------------------------------------------------------------------------
# 4. Weighted Moderated Regression Analysis
# ------------------------------------------------------------------------------

# (1) Continuous Outcome: Depression Score (PHQ-9 Score) with Profile * Gender interaction
model_dep_linear <- svyglm(
  phq9_score ~ profile * female + age + income + education + smoker + drinker + physical_act + med_hypertension + med_dyslipidemia + med_diabetes,
  design = knhanes_design
)
summary(model_dep_linear)

# (2) Binary Outcome: Clinical Depression (PHQ-9 >= 10) Logistic Regression
model_dep_logistic <- svyglm(
  depression_binary ~ profile * female + age + income + education + smoker + drinker + physical_act + med_hypertension + med_dyslipidemia + med_diabetes,
  design = knhanes_design,
  family = quasibinomial()
)
summary(model_dep_logistic)
# Calculate Odds Ratios and 95% Confidence Intervals
exp(coef(model_dep_logistic))
exp(confint(model_dep_logistic))

# (3) Continuous Outcome: Health Related Quality of Life (EQ-5D) Regression
model_eq5d <- svyglm(
  eq5d ~ profile * female + age + income + education + smoker + drinker + physical_act + med_hypertension + med_dyslipidemia + med_diabetes,
  design = knhanes_design
)
summary(model_eq5d)
```
