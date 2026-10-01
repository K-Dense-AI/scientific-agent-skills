# GRADE Evidence Profiles

## Purpose

An evidence profile transparently records a human panel's judgments about a body of evidence for each important outcome. It is not an article-scoring shortcut and does not produce a patient-care recommendation.

Use the current [GRADE Book](https://book.gradepro.org/) and the [GRADE Working Group](https://www.gradeworkinggroup.org/) as the controlling methodology. The GRADE Book is replacing the older handbook with progressively updated content.

## Non-Automation Rule

Never:

- infer certainty from keywords, abstracts, p-values, journal name, or study design alone;
- count checklist items to calculate certainty;
- treat one study's risk-of-bias judgment as certainty in a body of evidence;
- equate certainty with recommendation strength;
- assign recommendation strength without an Evidence-to-Decision process and a responsible panel;
- invent source citations or downgrade/upgrade rationales.

The bundled checker verifies structure, allowed labels, human attribution, rationale, and source linkage. It does not alter or endorse a judgment.

## Unit of Assessment

Rate certainty separately for every critical or important outcome. Include desirable and undesirable effects. Different outcomes may have different:

- bodies of evidence;
- risk-of-bias concerns;
- directness;
- precision;
- reporting bias;
- certainty.

Do not collapse all outcomes into a single study-level grade.

## Required Profile Fields

### Question

- Population
- Intervention/exposure/index approach
- Comparator/reference
- Outcomes and time horizons
- Setting and decision context

### Sources

For every source include:

- stable source ID;
- full citation;
- URL or DOI;
- publication type;
- version/date;
- access date when content is living.

### Effect

For each outcome record:

- measure and direction;
- absolute and relative effects when appropriate;
- confidence or credible interval;
- participants and studies;
- follow-up/horizon;
- missingness;
- whether the estimate is adjusted;
- applicability limits.

Do not convert an effect into a clinical instruction.

## Certainty Domains

Every domain entry requires a judgment, rationale, source IDs, and human reviewer role.

### Risk of Bias

Use a design-appropriate tool. Describe how limitations could change the estimated effect. Do not use a numeric quality score as a substitute.

### Inconsistency

Examine the direction and magnitude of effects, interval overlap, heterogeneity, and plausible explanations. A statistical heterogeneity value alone is not the judgment.

### Indirectness

Compare population, intervention/exposure, comparator, outcome, time horizon, setting, and evidence pathway with the framed question.

### Imprecision

Use the [current GRADE Book imprecision chapter](https://book.gradepro.org/guideline/imprecision): record the target of certainty, prespecified thresholds, and absolute-effect intervals where appropriate. Its human judgments can include `extremely_serious` concerns (three levels); the checker accepts that label for imprecision without deriving the final certainty. Do not import universal event counts, invent clinical cut points, or count a shared concern twice across domains.

### Dissemination Bias (Publication Bias)

The [current GRADE Book](https://book.gradepro.org/guideline/dissemination-bias) uses dissemination bias to cover selective availability of evidence, including unpublished and obscurely published results. Consider missing studies/results, small-study effects, time/language effects, sponsorship, registrations, and protocols. Separate selective results within a study from missing evidence across the body of evidence and document overlap with risk of bias. The JSON key remains `publication_bias` for compatibility; record the broader assessment in its rationale.

### Upgrading Considerations

When the selected GRADE approach permits, a panel may consider large effects, dose-response gradients, or plausible residual confounding. Each requires explicit methodology, rationale, and citations. “Statistically significant” is not an upgrading reason.

## Final Certainty

Allowed labels:

- high;
- moderate;
- low;
- very low.

Record:

- the final human judgment;
- who made it and in what role;
- date;
- domain-to-final-rating rationale;
- dissent or unresolved issues;
- source IDs.

The label describes confidence in an estimate for an outcome in a defined context. It is not a recommendation and does not imply safety, effectiveness, or authorization.

## Evidence to Decision

Recommendation development is outside the automated helper. A qualified panel using an applicable GRADE Evidence-to-Decision framework must explicitly consider, as relevant:

- priority of the problem;
- desirable and undesirable effects;
- certainty of evidence;
- values and variability;
- resources and cost effectiveness;
- equity;
- acceptability;
- feasibility.

Keep the evidence profile and any later recommendation record separate and traceable.

## Quality-Control Checklist

- [ ] Search and selection methods are documented.
- [ ] Outcome definitions and horizons match the question.
- [ ] All important benefits and harms are represented.
- [ ] Effect estimates include uncertainty.
- [ ] Each domain has a human judgment and rationale.
- [ ] Every rationale links to source IDs.
- [ ] The final certainty is outcome-specific.
- [ ] Conflicts of interest and panel roles are recorded.
- [ ] Disagreements and updates are versioned.
- [ ] No patient-specific or treatment directive appears.

## Helper

```bash
python3 scripts/evidence_profile_check.py assets/evidence_profile_template.json
```

The distributed template intentionally contains unresolved judgments. A non-zero result is expected until qualified humans complete it.
