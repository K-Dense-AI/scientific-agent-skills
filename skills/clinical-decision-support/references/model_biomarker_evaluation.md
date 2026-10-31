# Aggregate Model and Biomarker Evaluation

## Boundary

Evaluate a locked model, assay, or prespecified biomarker rule using synthetic or aggregate validation summaries. Do not:

- ingest individual records;
- discover or optimize a threshold;
- assign a class or risk to a person;
- match a person to a test or intervention;
- state clinical validity, utility, safety, or fitness for deployment.

## Define the Target

Record:

- evaluation target and version;
- biomarker category using FDA-NIH BEST terminology;
- intended research purpose;
- target population, setting, prevalence, and outcome horizon;
- intended user and non-clinical decision role;
- inputs, output, threshold, and threshold provenance;
- development, tuning, internal-test, and external-validation datasets;
- whether evaluation is temporal, geographic, site-based, or population-based.

Do not call a random split from one source “external validation.”

## Analytical and Clinical Questions

Keep separate:

1. **Analytical validation** — measurement accuracy, precision, detection limits, reproducibility, interference, specimen stability.
2. **Clinical validation** — association or predictive performance for the defined context.
3. **Clinical utility** — whether use improves meaningful outcomes compared with alternatives.

The bundled evaluator addresses only selected aggregate clinical-validation performance summaries. It cannot establish any of the three.

## Performance Dimensions

### Discrimination

Depending on the target:

- sensitivity and specificity;
- predictive values, with prevalence/context;
- likelihood ratios;
- C statistic/AUC with uncertainty;
- time-dependent discrimination for censored outcomes.

Do not report accuracy alone when classes are imbalanced.

### Calibration

Calibration asks whether predicted probabilities agree with observed frequencies. Evaluate:

- calibration-in-the-large;
- calibration slope;
- calibration plots with uncertainty;
- observed versus predicted risk across meaningful ranges;
- integrated or absolute calibration error when justified.

The standard-library helper accepts calibration bins and reports a weighted absolute gap. Its `calibration_in_the_large_gap` field is mean predicted probability minus observed event proportion on the probability scale; it is not the logistic calibration intercept. Bin totals and observed events must match the same group and confusion matrix, including when disclosure suppression applies. Binning loses information and does not replace individual-level calibration analysis in an approved environment.

Primary overview: [Van Calster et al., calibration](https://pubmed.ncbi.nlm.nih.gov/31842878).

### Overall Accuracy and Utility

Use proper scoring rules and decision-curve/net-benefit methods only with a prespecified, defensible decision context. Do not imply utility from AUC or accuracy. Utility evaluation that changes care is outside this skill.

### Uncertainty

Report intervals for performance estimates and explain resampling or analytic methods. A zero denominator is undefined, not zero performance: the helper emits `null` estimates/interval endpoints. Balanced accuracy requires both observed outcome classes, otherwise it is `null` and excluded from subgroup differences. The helper uses Wilson intervals for aggregate proportions. It does not model correlated observations, clustering, repeated measurements, censoring, or verification bias.

## External Validation

Apply the original locked model without refitting. Document:

- differences in case mix, prevalence, setting, workflow, and measurement;
- eligibility and missingness;
- sample-size rationale based on precision targets, not a blanket event rule;
- calibration, discrimination, and any prespecified utility measure;
- subgroup performance;
- model failures and unusable inputs;
- whether recalibration was separate from validation.

See [BMJ 2024 external-validation guidance](https://www.bmj.com/content/384/bmj-2023-074820) and [sample-size methodology](https://pmc.ncbi.nlm.nih.gov/articles/PMC8352630).

## Subgroup and Fairness Evaluation

Before analysis:

- identify groups based on intended use, evidence, and stakeholder input;
- document category provenance and limitations;
- set minimum precision and disclosure rules;
- plan intersectional analyses where feasible;
- define metrics and acceptable uncertainty;
- evaluate measurement and label validity;
- plan investigation and mitigation, not only detection.

Report:

- representation and missingness;
- performance and calibration with intervals;
- data quality and failure rates;
- distribution shift;
- human-AI interaction where relevant;
- observed differences without declaring a group deficient.

No single parity metric establishes fairness. Equal metrics can coexist with inequitable outcomes, and unequal metrics may reflect case mix, measurement, structural conditions, or model behavior that requires investigation.

## Biomarker-Specific Controls

- Pre-specify specimen, assay, platform, software, quality controls, units, and threshold.
- Preserve continuous information where appropriate.
- Separate prognostic association from treatment-effect interaction.
- Blind assay assessment to outcome when feasible.
- Account for batch/site effects and failed measurements.
- Validate thresholds independently.
- Report analytical validity before clinical interpretation.
- Use REMARK for tumor prognostic markers.

## Change Control and Monitoring

For each release record:

- immutable model/assay version;
- data and code versions;
- planned changes and rationale;
- validation protocol and acceptance criteria;
- subgroup/calibration regression tests;
- human-factors impact;
- approval and rollback;
- monitoring cadence and drift triggers;
- incident handling and retirement.

Never update a threshold or model silently after viewing performance.

## Aggregate Evaluator

Input contains only:

- group labels and aggregate denominators;
- confusion counts;
- aggregate calibration bins;
- provenance and validation metadata.

Output contains bounded descriptive metrics, uncertainty, suppression, and documented gaps. Invalid inputs return failure diagnostics with no partial group metrics. The helper emits JSON only; it does not produce calibration plots, bin-level Wilson intervals, forest plots, or fitted calibration models. It never outputs a person-level class or recommendation.

```bash
python3 scripts/model_biomarker_evaluation.py \
  assets/aggregate_model_evaluation_template.json
```
