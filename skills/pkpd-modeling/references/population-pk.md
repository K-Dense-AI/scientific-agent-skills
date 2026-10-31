# Population PK: estimation and diagnostic limits

## Plan and construct data

State the context of use, populations, analytes, estimands, exclusions and decisions before model
selection. Reconcile dose records, actual sampling times, route, infusion duration, assay and BLQ
flags. Keep missing/censored observations distinct. See [dataset standards](dataset-standards.md)
and [analysis plan](../assets/popk-analysis-plan.md).

Use an NLME engine (NONMEM, Monolix, nlmixr2 or a qualified alternative) to estimate population
parameters, between-subject/occasion variability and residual error. Fitting subjects separately
with this skill's WLS helper is not population estimation. Record estimator, approximation,
starting values, bounds, seed, covariance method and software version.

## Structural and variability model

Use identifiable structure supported by the sampling design. Lognormal individual parameters are
convenient for positive CL/V, but are not universally correct. Check random-effect correlations,
occasion definitions, time-varying covariates and residual variance assumptions. High condition
numbers depend on scaling; a universal cutoff does not establish identifiability.

BLQ exclusion (M1), substitution and censored-likelihood (commonly M3) can differ materially.
Select by censoring pattern, assay and intended use, then examine sensitivity. A fixed BLQ fraction
alone is insufficient to choose a method. Missing DV is not interchangeable with a censored DV.

Covariate inference needs uncertainty, plausible ranges, multiplicity/selection considerations and
clinical relevance. Sparse empirical Bayes estimates can hide or manufacture covariate patterns.
Do not select the final model using an arbitrary shrinkage threshold alone.

## Diagnostics

- Plot observed vs population/individual predictions and appropriate residuals by time, predictions,
  assay, dose, subgroup and study. Residual definitions depend on estimation method.
- Report shrinkage convention: SD shrinkage `1-SD(eta_hat)/omega` differs from variance shrinkage
  `1-Var(eta_hat)/omega²`. Pharmpy defaults to variance (`sd=False`); use `sd=True` for SD.
- Simulation diagnostics (VPC/pcVPC, NPC/NPDE where appropriate) must reproduce dose, sampling,
  covariates and censoring. Prediction correction itself has assumptions.
- Assess uncertainty with covariance, bootstrap, likelihood profiles or another justified method;
  record failures and boundary estimates, not only successful replicates.
- Evaluate predictive performance in data independent of calibration when available and relevant.
  Good internal fit does not establish performance in a new population or dosing scenario.

The [FDA 2022 population PK guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/population-pharmacokinetics)
frames evaluation around intended application; [ICH M15](regulatory-guidance.md) adds a general
model-informed development framework. Neither turns diagnostic thresholds into automatic approval.

## Pharmpy shrinkage interface

Documentation-verified call; it needs real fitted outputs and was not executed against an NLME fit:

```python
# Illustrative: model and both estimates tables must come from the same fit.
from pharmpy.modeling import calculate_eta_shrinkage
shrinkage = calculate_eta_shrinkage(model, parameter_estimates, individual_estimates, sd=True)
```

`parameter_estimates` is a pandas Series; `individual_estimates` is a DataFrame. Check parameter
names and individual alignment. [API](https://pharmpy.github.io/latest/api/pharmpy.modeling.calculate_eta_shrinkage.html).
