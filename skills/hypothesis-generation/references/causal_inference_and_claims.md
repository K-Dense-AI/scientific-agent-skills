# Causal Inference and Claim Discipline

## Start with the scientific target

Association, prediction, intervention effects, and mechanisms answer different questions:

- **Descriptive:** What is the distribution or pattern?
- **Associational:** How do measured variables co-vary in the observed data?
- **Predictive:** How well does information predict outcomes in a target setting?
- **Causal:** What would differ under specified interventions or exposure conditions?
- **Mechanistic:** Through which process would the causal change occur?

A model can predict accurately without identifying a causal effect. A randomized effect estimate can identify an intervention contrast without establishing the complete mechanism.

## Define a causal estimand

Following the causal-question and ICH E9(R1) principles where applicable, specify:

1. **Population/system:** To whom or what does the contrast apply?
2. **Intervention/exposure:** What condition is set, assigned, or contrasted?
3. **Comparator:** What alternative condition is compared?
4. **Outcome:** What variable is affected and how is it measured?
5. **Time horizon:** When is the outcome assessed?
6. **Population summary:** Mean difference, risk ratio, quantile contrast, survival summary, or another target.
7. **Intercurrent events:** How are post-assignment events handled when they affect interpretation or measurement?
8. **Treatment versions:** Are interventions sufficiently well defined?

The estimand should exist before choosing an estimator or model.

## Counterfactual contrast

Causal effects compare outcomes under different conditions for the same target units, although both conditions cannot usually be observed for one unit. Identification therefore depends on design and assumptions.

For observational data, state:

- target-trial analogue or other design logic;
- consistency/well-defined intervention assumptions;
- exchangeability/no-unmeasured-confounding assumptions;
- positivity/overlap;
- interference assumptions;
- measurement and missingness assumptions;
- model assumptions introduced by estimation.

Do not write “controlled for confounding” as if adjustment proves exchangeability.

## Bias pathways

### Confounding

A common cause of exposure/intervention and outcome can create or obscure an association. Address through design, randomization where ethical/feasible, restriction, matching, measurement and adjustment of justified common causes, negative controls, sensitivity analysis, or triangulation.

Risks:

- unmeasured or poorly measured common causes;
- time-varying confounders affected by prior treatment;
- inappropriate adjustment for instruments, mediators, or colliders;
- residual confounding after coarse categorization.

### Selection bias

Selection into the sample, analysis, follow-up, or observed outcome can depend on causes of exposure and outcome. Record:

- sampling and eligibility;
- participation and consent;
- exclusions;
- attrition and censoring;
- complete-case restrictions;
- availability of measurements;
- conditioning introduced by data linkage.

### Collider bias

A collider is a common effect of two variables. Conditioning on it or its descendant can open a non-causal path. Common sources include:

- selection into a study or subgroup;
- restricting to diagnosed, hospitalized, tested, or surviving participants;
- adjusting for a post-exposure variable affected by another cause of the outcome;
- using complete cases when missingness is jointly caused.

More covariates are not automatically better.

### Reverse causation

The outcome or its precursors may influence the exposure or measurement. Cross-sectional order is especially weak evidence of direction. Use temporal design, lagged measurements, incident outcomes, intervention, negative controls, or explicit bidirectional candidates where appropriate.

### Measurement bias

Measurement error can:

- attenuate or inflate estimates;
- differ by exposure or outcome;
- induce apparent interactions;
- distort covariate adjustment;
- affect selection into analysis.

Operationalization and validation are part of causal design, not a later documentation task.

## Mediators and effect modifiers

- A **mediator** lies on a causal pathway. Adjusting for it changes the target from total to a direct or controlled effect and introduces additional assumptions.
- An **effect modifier** describes variation in a causal contrast across strata. It is not synonymous with statistical interaction in every scale.
- A **confounder** is defined relative to a target causal contrast and design, not simply by association with the outcome.

Label the intended role before analysis and justify it with domain knowledge and a causal structure.

## Negative controls

Lipsitch, Tchetgen Tchetgen, and Cohen distinguish negative-control exposures and outcomes:

- A negative-control exposure should not cause the target outcome but should share relevant confounding/bias pathways.
- A negative-control outcome should not be caused by the target exposure but should share relevant bias pathways. Excluding only the proposed mechanism is insufficient if another causal pathway from exposure to control outcome remains.

Specify:

- why the target mechanism cannot operate;
- which biases should be shared;
- expected result;
- implication of control failure;
- alternative reasons for a non-null control result.

Negative controls detect some biases under assumptions; they do not prove absence of bias. A non-null control can reflect a violated exclusion or shared-bias assumption, and its effect size does not generally quantify bias in the target estimate.

## Claim-language rules

### Associational

Use:

- “was associated with”;
- “co-varied with”;
- “predicted in the evaluated dataset”;
- “the adjusted association.”

State design, population, timing, effect/summary measure, uncertainty, and limitations.

### Causal

Use causal verbs only when:

- the causal estimand is explicit;
- design/identification logic is stated;
- assumptions and sensitivity are visible;
- confounding, selection, collider, reverse-causation, and measurement risks are addressed;
- language is calibrated to the evidence.

For observational work, “estimated causal effect under the stated assumptions” is often more accurate than an unqualified causal declaration.

### Mechanistic

Distinguish:

- direct evidence for process steps;
- mediation or intermediate measurements;
- perturbation/rescue evidence;
- temporal ordering;
- analogy or plausibility only.

A causal intervention effect does not by itself verify the proposed pathway.

## Markdown claim annotations

The bundled linter recognizes line-level annotations:

```markdown
[claim:associational] Exposure X was associated with outcome Y in the observed cohort.

[claim:causal][estimand:E1][identification:observational_assumption_dependent][confounding:unresolved][selection:assessed][collider:assessed][reverse-causation:assessed] Under the stated assumptions, intervention X would reduce outcome Y over 12 months.
```

Allowed risk states are `assessed`, `unresolved`, and `not_applicable`. “Assessed” records that a human evaluation exists; it does not mean the risk is absent.

Run:

```bash
python3 scripts/lint_causal_claims.py local-draft.md
```

The linter is lexical. It can miss causal language, flag benign phrases, and cannot judge whether a design identifies an effect.

## Intervention-trial context

For intervention hypotheses:

- align objectives, estimands, outcomes, timing, harms, and analysis;
- use SPIRIT 2025 for protocol reporting and CONSORT 2025 for trial-result reporting;
- preserve access to protocol and statistical analysis plan;
- report important post-start changes and non-prespecified outcomes/analyses;
- include harms and participant/public involvement where applicable.

Reporting completeness is not proof of ethical approval, design validity, regulatory compliance, or treatment efficacy.
