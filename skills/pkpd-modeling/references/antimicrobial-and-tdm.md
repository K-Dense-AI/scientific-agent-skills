# Antimicrobial PK/PD and research TDM

## Define the target before computing attainment

A target needs the drug, organism, infection, endpoint, patient population, assay/MIC method,
exposure interval and free/total concentration basis. AUC/MIC has time units unless the convention
explicitly normalizes them; Cmax/MIC is a ratio, and fT>MIC is a time fraction or percent.
A preclinical stasis target, clinical efficacy target and toxicity threshold are different endpoints.
Do not transfer a numeric target between those settings without evidence.

For serious MRSA, the 2020 ASHP/IDSA/PIDS/SIDP vancomycin consensus recommends total-drug AUC24
400–600 mg·h/L assuming broth-microdilution MIC 1 mg/L. That is not a universal antimicrobial target,
not a free-AUC target, and not an instruction to increase exposure indefinitely with a higher MIC.
[IDSA guideline](https://www.idsociety.org/practice-guideline/vancomycin/).

## Bayesian estimation

MAP estimation combines the population prior with the observation likelihood. The local helper
uses log CL and log V normal priors (omega inputs are log SDs) and a combined Gaussian residual
model whose objective includes log variance. It reports a point estimate, not a posterior credible
interval. One level does not independently identify both CL and V; the prior can dominate.

The vancomycin-adult parameterization is illustrative, not a validated clinical population model.
Before applying any published model, check population, assay, parameter units, covariates,
renal-function equation, dosing history, external validation and relevant clinical workflow.
A numerically converged fit to one or two levels does not validate those assumptions.

## Bundled dose history and exposure

Levels are entered as concentration@hours after the latest dose start. The helper assumes identical
doses spaced by the stated interval and duration. `--doses-given 20` is a finite history, not a
steady-state guarantee. Missed doses, variable intervals, changing renal function and dialysis are
outside this implementation. Use full event-based modeling for those data.

For a linear one-compartment steady-state system, `AUC24=24*D/(CL*tau)`; peak/trough account for
infusion duration. These exact steady-state calculations are distinct from the finite-dose
concentrations used to fit observations. The model-target dose output is an amount that matches
the requested model AUC, not an individualized clinical recommendation.

## Simulation and target attainment

The simulation helper draws CL and V independently from lognormal distributions specified by CV.
Its omega convention differs from TDM's log SD. It does not propagate population-parameter
uncertainty, correlations, changing physiology or between-occasion variability. Their omission can
raise or lower attainment. Assay error affects observed levels, not the underlying true exposure.

Check multiple intervals for convergence, event-boundary behavior, reproducibility and numerical
integration tolerance. Report the fraction meeting a prespecified target together with sampling
uncertainty and model limitations; simulated attainment is not evidence of patient benefit.
