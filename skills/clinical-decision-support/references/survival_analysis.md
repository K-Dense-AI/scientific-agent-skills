# Survival-Analysis Planning

## Scope

The bundled script validates a plan. It does not read time-to-event rows, fit models, draw curves, or provide an individual prognosis.

## Start With the Estimand

Align:

1. **Population** — eligibility and analysis set.
2. **Condition/comparison** — intervention, exposure, or groups being contrasted.
3. **Variable/endpoint** — event definition and ascertainment.
4. **Intercurrent-event strategy** — how events such as discontinuation, rescue therapy, switching, or competing events relate to the question.
5. **Population-level summary** — risk, survival probability, restricted mean survival time, hazard contrast, quantile, or another justified measure.
6. **Time horizon** — clinically and statistically justified.

Record time zero, delayed entry, time scale, follow-up end, and calendar/data-cut date.

## Endpoint Definition

Specify:

- exact event;
- competing events;
- recurrent events if relevant;
- ascertainment schedule and adjudication;
- censoring rules;
- handling of same-day and tied events;
- loss to follow-up;
- administrative censoring;
- endpoint changes and versioning.

Do not treat a competing event as ordinary independent censoring when the target is absolute event probability.

## Descriptive Estimation

Kaplan-Meier estimates are suitable for survival from the event of interest under appropriate censoring assumptions. Report:

- numbers at risk;
- events and censoring;
- estimates at prespecified times with intervals;
- median only if estimable;
- follow-up distribution using an appropriate method;
- truncation where risk sets become uninformative.

When competing events exist, use cumulative-incidence methods for event probabilities. Naively censoring competing events in Kaplan-Meier can overestimate absolute incidence.

## Group Comparisons

The log-rank test compares event-time distributions and is most powerful under proportional alternatives. It does not quantify an effect. Pre-specify alternatives if curves may cross or effects may be delayed.

A Cox model estimates a hazard contrast conditional on model specification. Before presenting a single hazard ratio:

- assess proportional hazards graphically and analytically;
- examine functional forms;
- evaluate influential observations and interactions;
- define adjustment variables a priori;
- account for clustering or stratification;
- avoid interpreting `1 − HR` as a reduction in cumulative risk.

If proportional hazards is doubtful, consider:

- time-varying coefficients;
- piecewise effects;
- landmark effects;
- restricted mean survival time at a justified horizon;
- survival or cumulative-incidence differences at prespecified times;
- accelerated failure-time or flexible parametric models.

Report why the selected summary answers the research question.

## Competing Risks

Distinguish:

- cause-specific hazard questions;
- cumulative-incidence/absolute-risk questions;
- subdistribution-hazard modeling.

State which question the method answers. A subdistribution hazard ratio is not directly a risk ratio. When modeling several event types, check that resulting probability estimates are coherent.

Primary reference: [Austin, Lee, and Fine, competing risks](https://pmc.ncbi.nlm.nih.gov/articles/PMC4741409/).

## Bias and Missingness

Plan for:

- informative censoring;
- delayed entry/left truncation;
- immortal time;
- time-dependent confounding;
- interval censoring;
- outcome misclassification;
- missing covariates;
- competing events;
- informative visit schedules;
- treatment switching and rescue treatment;
- site and calendar effects.

Specify sensitivity analyses tied to plausible departures from assumptions. A “best/worst case” alone is rarely sufficient.

## Prediction Models

For time-to-event prediction:

- preserve the locked model and prediction horizon;
- evaluate calibration at prespecified times;
- report time-dependent discrimination with uncertainty;
- use appropriate handling of censoring;
- evaluate overall and subgroup performance;
- perform external validation in relevant settings;
- avoid selecting a horizon after viewing results.

Use TRIPOD+AI and PROBAST+AI.

## Biomarker Evaluation

For a prognostic biomarker:

- analyze continuous form where scientifically justified;
- pre-specify transformations and threshold;
- avoid minimum-p-value cut-point searches;
- report assay and specimen handling;
- adjust for established prognostic factors;
- validate externally.

For a predictive biomarker, estimate and report a treatment-by-biomarker interaction in an appropriate design. Separate prognostic association from treatment-effect modification.

## Uncertainty and Multiplicity

Include:

- confidence intervals for every primary effect;
- uncertainty in calibration/discrimination;
- prespecified alpha or interval interpretation;
- multiplicity strategy for outcomes, times, subgroups, and models;
- bootstrap or cross-validation details if used;
- sensitivity analyses;
- model optimism and overfitting assessment.

Do not turn a threshold-crossing p-value into clinical importance.

## Primary Method Sources

- [ICH E9(R1) estimands and sensitivity analysis](https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf)
- [Royston and Parmar, restricted mean survival time](https://pubmed.ncbi.nlm.nih.gov/24314264/)
- [Austin and Fine, reporting competing-risk analyses](https://pmc.ncbi.nlm.nih.gov/articles/PMC5698744/)

## Plan Validator

```bash
python3 scripts/survival_plan_validator.py assets/survival_analysis_plan_template.json
```

An exit code of zero means required planning fields and selected consistency rules passed. It is not statistical approval.
