# Population Pharmacokinetic Analysis Plan

> Template. Every bracketed field is a decision to make and record **before** the analysis starts.
> A plan written after the modelling is not an analysis plan, and the difference is visible to a
> reviewer.

**Study/programme:** [ ]  **Compound:** [ ]  **Plan version and date:** [ ]
**Author:** [ ]  **Reviewers:** [ ]

---

## 1. Objectives

Primary objective: [ ]

Each objective must name the decision it informs — a dose for the next study, a label statement, a
covariate adjustment, a waiver. "Characterise the population pharmacokinetics" is not an objective;
it is an activity.

Secondary objectives: [ ]

**Intended use of the model:** [ ] — regulators evaluate a model against its intended use, and the
required rigour follows from it.

## 2. Data

| Item | Specification |
| --- | --- |
| Studies included | [ ] |
| Analysis population | [ ] |
| Analyte and matrix | [ ] |
| Assay and LLOQ | [ ] (see the bioanalytical validation report) |
| Time reference | actual elapsed time from a subject/occasion origin; TAD separate |
| Dataset specification | [ reference the document ] |
| Derivation script | [ path / repository ] |

**Exclusions**, defined now and applied blind to the model:

- [ ] Records with no matching dose record
- [ ] Concentrations flagged by the bioanalytical laboratory
- [ ] Subjects with documented non-compliance
- [ ] Pre-dose concentrations in a first-dose profile above [ ]% of Cmax
- [ ] Other: [ ]

**BLQ handling:** [ M1 / M3 / other ]. Justification: [ ]. Expected BLQ fraction: [ ]%.
Prespecified sensitivity analysis for alternative censoring assumptions: [ ].

**Missing covariates:** [ imputation rule, or exclusion ]. Missingness will be tabulated before
imputation.

## 3. Software

| | |
| --- | --- |
| Estimation | [ NONMEM 7.x / Monolix / nlmixr2 ] version [ ] |
| Orchestration and post-processing | [ Pharmpy / PsN / R ] version [ ] |
| Estimation method | [ FOCE-I / SAEM followed by IMP ] |
| Environment | [ container / lockfile reference ] |

## 4. Structural model

Starting point: [ ] compartments, [ ] absorption, [ ] elimination.

Candidate structures to be evaluated: [ ]

Parameterisation is clearance-based (CL, V, Q, Vp) in all candidates.

Selection criteria: [physiological plausibility, residual patterns, uncertainty, predictive checks,
and justified model-comparison method]. Boundary parameters and unidentified nuisance parameters
can invalidate a nominal likelihood-ratio reference distribution; specify calibration/simulation
where needed. Do not replace identifiability assessment with an arbitrary RSE cutoff.

## 5. Between-subject and between-occasion variability

- IIV on: [ ] Distribution: [ exponential ]
- Correlations estimated between: [ ]
- IOV on: [ ], with an occasion defined as [ ]
- Rule for removing a variance component: [ ]

## 6. Residual error

Candidates: [ proportional / additive / combined / log-transform-both-sides ]. Separate error
models by [ study / assay / matrix ]: [ yes / no, with justification ].

## 7. Covariate model

**Covariates included a priori on mechanistic grounds, not tested:**

- Body size: allometric scaling on CL (exponent [0.75], [fixed]) and V (exponent [1.0], [fixed])
- Maturation, if paediatric subjects are included: [ function, parameters, fixed or estimated ]
- Other: [ ]

**Covariates to be evaluated:**

| Covariate | Parameter(s) | Functional form | Rationale |
| --- | --- | --- | --- |
| [ ] | [ ] | [ ] | [ ] |

**Procedure:** [ stepwise covariate modelling / full model estimation ].
If stepwise: forward inclusion at p < [0.05] (ΔOFV > 3.84), backward elimination at p < [0.001]
(ΔOFV > 10.83). Note that stepwise selection biases effect sizes upward and narrows intervals; a
full-model approach is preferred where the objective is to quantify an effect.

Clinical relevance threshold: a covariate effect is reported as relevant if it changes [ exposure
metric ] by more than [ ]% across the [5th–95th] percentile of the covariate.

## 8. Model evaluation

- Goodness-of-fit: DV vs PRED and IPRED; CWRES vs time and vs PRED; |IWRES| vs IPRED
- Eta shrinkage reported for every eta, with SD/variance convention and limitations for covariate plots
- Prediction-corrected VPC, [ n ] replicates, stratified by [ ]
- NPDE with tests of mean, variance and normality
- Parameter uncertainty by [ covariance step / bootstrap (n = ) / SIR / log-likelihood profiling ]
- Sensitivity rank, condition number with scaling, boundaries and profile checks reported

**Acceptance criteria for the final model:** [ ]

## 9. Simulations

Purpose: [ ]  Scenarios: [ ]  Replicates: [ ]  Population sampled from: [ ]
Uncertainty in fixed effects propagated: [ yes / no ]  Endpoint summarised: [ ]

## 10. Deviations

Any departure from this plan is recorded in the report with its reason and the date it was decided.
Post hoc analyses are labelled as such and reported separately from the pre-specified analysis.

---

**Approvals**

| Role | Name | Signature | Date |
| --- | --- | --- | --- |
| Author | | | |
| Reviewer | | | |
| Clinical pharmacology | | | |
