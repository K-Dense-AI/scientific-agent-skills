# Transparent Idea Evaluation

Evaluation narrows a candidate set; it does not convert ideas into evidence.
Use explicit criteria, independent ratings, uncertainty, qualitative review,
adversarial checks, and noncompensatory gates.

## Define criteria before viewing scores

For every criterion record:

- name and decision relevance;
- direction (`higher` or `lower`);
- observable anchors for the minimum, midpoint, and maximum;
- weight and who set it;
- evidence required for a rating;
- uncertainty representation;
- conflicts or overlap with other criteria.

Possible criteria include information gain, ability to distinguish mechanisms,
importance to stakeholders, feasibility, reversibility, novelty relative to a
documented search, methodological rigor, cost, time, equity, safety, and
dual-use burden.

Avoid:

- “impact” or “quality” without anchors;
- counting correlated criteria twice;
- silently converting missing information to a zero;
- changing weights after seeing which idea wins;
- averaging away an ethics, safety, regulatory, or feasibility veto.

## Rating process

1. Train raters on two neutral examples that are not session candidates.
2. Ask raters to score independently and cite the reason or source.
3. Allow `not assessable` and abstention rather than forced precision.
4. Collect a central score and plausible low/high values when uncertainty is
   material.
5. Reveal distributions and reasons.
6. Discuss disagreements, then retain both original and revised ratings.
7. Resolve factual errors separately from preference differences.

Do not report inter-rater agreement as evidence that an idea is correct.
Agreement can reflect shared information or shared bias.

## Weighted additive matrix

The bundled `scripts/evaluate_matrix.py` uses a simple, fully disclosed model.
For criterion \(j\), observed score \(x_{ij}\), minimum \(L_j\), maximum \(U_j\),
and positive weight \(w_j\):

- higher-is-better: \(n_{ij}=(x_{ij}-L_j)/(U_j-L_j)\)
- lower-is-better: \(n_{ij}=(U_j-x_{ij})/(U_j-L_j)\)
- normalized weight: \(p_j=w_j/\sum_j w_j\)
- displayed score: \(100\sum_j p_j n_{ij}\)

This compensatory formula means a high value on one criterion can offset a low
value on another. Keep hard gates outside the formula.

### Criteria configuration

```json
{
  "schema_version": "1.0",
  "criteria": [
    {
      "name": "information_gain",
      "description": "Ability to discriminate plausible mechanisms",
      "weight": 3,
      "direction": "higher",
      "minimum": 1,
      "maximum": 5
    },
    {
      "name": "resource_burden",
      "description": "Relative time, cost, and scarce-resource burden",
      "weight": 2,
      "direction": "lower",
      "minimum": 1,
      "maximum": 5
    }
  ]
}
```

Weights must be explicit, finite, and positive. They need not sum to one; the
script reports both supplied and normalized values.

### Scores CSV

```csv
idea_id,information_gain,information_gain_low,information_gain_high,resource_burden,resource_burden_low,resource_burden_high,qualitative_review,uncertainties,evidence_status,ethics_status
I001,4,3,5,3,2,4,"Distinguishing prediction is clear","Assay performance unknown",search-incomplete,review-required
I002,3,2,4,2,2,3,"Lower burden but less discriminating","Population transfer uncertain",mixed,not-assessed
```

Required columns are `idea_id`, every configured criterion,
`qualitative_review`, and `uncertainties`. Low/high columns are optional but
must appear as pairs and contain `low <= score <= high`. Extra columns are
preserved as qualitative context.

Run:

```bash
python scripts/evaluate_matrix.py scores.csv \
  --config criteria.json \
  --weight-delta 0.10 \
  --output matrix.json
```

The output includes:

- raw and normalized criterion scores;
- supplied and normalized weights;
- base score and deterministic presentation rank;
- score interval implied by input low/high values;
- minimum/maximum score and rank when each weight is perturbed one at a time
  by the requested fraction and all weights are renormalized;
- qualitative fields, limitations, formula, and tie rule;
- `decision: null` and an explicit notice that no scientific conclusion or
  automatic selection was made.

The sensitivity analysis is local and one-factor-at-a-time. It does not explore
all possible weights, criterion dependence, model-form uncertainty, correlated
ratings, or uncertainty in the scale anchors.

## Interpreting sensitivity

Treat a ranking as fragile when:

- rank changes under small, plausible weight perturbations;
- score intervals overlap materially;
- one criterion dominates the result;
- rankings change after a reasonable alternative definition;
- missing evidence is driving optimistic ratings;
- qualitative review or a gate conflicts with the numeric order.

Do not “fix” fragility by choosing weights that stabilize a preferred result.
Use it to identify value judgments, missing information, or candidates that
need further comparison.

## Adversarial review template

For every shortlisted idea record:

```text
Idea ID:
Reviewer (not an originator):
Strongest version of the idea:
Observation that would count against it:
At least two alternative explanations:
Measurement or analysis failure:
Sampling or generalizability failure:
Prior evidence that challenges it:
Potential harm, inequity, or misuse:
Mitigation:
Residual uncertainty:
Disposition: retain / revise / pause / stop / external review
```

Review the strongest version before attacking it. Avoid performative “devil's
advocacy” with no follow-up; every challenge needs a response, owner, and
status.

## Literature check

For each idea:

1. Translate the idea into searchable concepts and alternative terminology.
2. Search primary literature, systematic reviews, methods guidance, negative
   findings, and adjacent disciplines.
3. Record databases, exact queries, dates, filters, and screening limits.
4. Verify each source, DOI, sample, design, and relevant result.
5. Separate:
   - directly relevant evidence;
   - indirect analogy;
   - conflicting or null evidence;
   - expert opinion;
   - no direct evidence located in this search.
6. Update assumptions and ratings without overwriting the original record.

Do not use citation counts as a validity score. Do not let an AI-generated
summary substitute for reading the source.

## Feasibility and rigor gate

Ask a relevant methods expert to review:

- research question, unit of inference, and proposed comparison;
- discriminating predictions and plausible alternatives;
- sampling frame, controls, randomization, blinding, and replication;
- measurement validity and resource authentication;
- nuisance variables, batch effects, missingness, and analytic flexibility;
- sample-size or information requirements;
- feasibility, dependencies, cost, skills, and failure recovery;
- value and interpretability of null or contradictory outcomes.

This is a gate to protocol development, not approval to collect data.

### NIH-funded biomedical work

When NIH guidance applies, the later application or protocol should address:

- rigor of prior published and unpublished research;
- robust and unbiased design, methodology, analysis, interpretation, and
  reporting;
- relevant biological variables;
- authentication of key biological or chemical resources.

NIH's SABV policy expects sex to be considered in research questions, design,
analysis, and reporting for vertebrate animal and human studies, with strong
justification for a single-sex scope. “Include both sexes” alone is not an
analysis plan, and an inappropriate underpowered comparison can reduce rather
than improve rigor. Consult current NIH instructions and program staff.

## Ethics, safety, and regulatory gate

Ask whether the idea involves:

- people, identifiable or sensitive data, vulnerable groups, or clinical care;
- animals;
- pathogens, toxins, engineered biological systems, or environmental release;
- dual-use capabilities, dangerous optimization, or security-sensitive
  details;
- controlled technologies, export restrictions, or research-security duties;
- Indigenous, community, cultural, or data-sovereignty obligations;
- proprietary information or unpublished work;
- environmental, distributive, or accessibility harms.

Record `not-assessed`, `not-applicable`, `review-required`, `approved under
identifier ...`, `redesign-required`, or `stop`. Only the authorized body can
issue approval. Current policies vary by jurisdiction and can change.

## Decision log

Record the decision while alternatives and uncertainty are still visible:

- date, owner, and decision scope;
- candidate IDs and versions;
- criteria, anchors, weights, and sensitivity settings;
- raw ratings, ranges, dissent, missing ratings, and abstentions;
- evidence-check protocol and results;
- adversarial review and responses;
- feasibility and ethics/safety/regulatory gate status;
- selected next action and why;
- rejected or deferred alternatives and why;
- revisit trigger, owner, and deadline.

Do not rewrite the log after outcomes are known. Append corrections and
reasons.

## Preregistration and open science handoff

Ideation is normally exploratory. When a candidate becomes a confirmatory
study:

1. distinguish hypotheses formed before versus after seeing relevant outcomes;
2. specify design, primary outcomes, exclusions, stopping, and analysis
   decisions before outcome inspection;
3. use a time-stamped registry appropriate to the field;
4. document amendments and label departures and new analyses as exploratory;
5. consider a Registered Report when protocol review before results is useful;
6. follow consent, privacy, intellectual-property, security, and community
   constraints when sharing.

Preregistration supports transparency; it does not guarantee a good question,
adequate power, correct analysis, reproducibility, ethics approval, or truthful
execution. Exploratory research remains valuable when reported as exploratory.
