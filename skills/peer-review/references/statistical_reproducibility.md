# Statistical, Methods, and Reproducibility Review

This guide supports structured questions; it does not replace a statistician, methodologist, domain expert, or independent reanalysis. Sources reviewed on **2026-10-01**, with source-specific verification limits, are recorded in `assets/source_ledger.csv`.

## Evidence hierarchy for the review

Use, in order:

1. The stated research question and target population
2. Protocol, registration, analysis plan, and amendments
3. Reported design and data-generating process
4. Methods, code, tables, figures, supplements, and repository records
5. Applicable primary method or regulatory guidance
6. Current reporting guidance
7. Target venue policy

Do not reject a method merely because another method is more familiar. Explain the estimand, assumption, error, or interpretation at stake.

## Core review sequence

### 1. Define what is being estimated

Write down:

- Unit of inference
- Population
- Intervention, exposure, test, or predictors
- Comparator or reference condition
- Outcome and time horizon
- Target effect, association, accuracy, or predictive performance
- Intercurrent events, censoring, and missing observations where relevant

Then trace whether design, data collection, analysis, result, and claim target the same quantity.

For applicable clinical trials, ICH E9(R1) provides a framework for estimands and sensitivity analyses. It is not a universal rule for every study.

### 2. Reconstruct the design

Identify:

- Prospective, retrospective, cross-sectional, longitudinal, experimental, or observational structure
- Recruitment or sampling frame
- Experimental/observational unit
- Pairing, nesting, clustering, repeated measures, sites, batches, and time
- Allocation, concealment, blinding, matching, or weighting
- Primary and secondary outcomes
- Prespecified versus exploratory analyses

If the design cannot be reconstructed, first request missing reporting. Do not label the design invalid solely because details are absent.

### 3. Trace every denominator

Reconcile:

- Eligible, enrolled, assigned, treated/exposed, followed, measured, and analyzed units
- Outcome-specific denominators
- Exclusions before and after allocation or measurement
- Missing values and reasons
- Complete-case, imputed, weighted, or model-based analysis populations
- Figure, table, abstract, text, and supplement totals

Report the exact mismatch and locations; do not infer why counts differ.

### 4. Assess analysis–design alignment

Ask whether the method accounts for:

- Outcome scale and distribution
- Pairing and repeated measures
- Clustering and multilevel structure
- Unequal follow-up, censoring, or competing events
- Sampling weights or matched designs
- Baseline adjustment and prespecified covariates
- Multiplicity and outcome hierarchy
- Model tuning and validation
- Missingness assumptions

The name of a statistical test is not enough. The report should state inputs, model form, uncertainty method, software/version, and relevant diagnostics.

### 5. Assess estimates and interpretation

Prefer:

- Effect or performance estimates with units
- Compatible uncertainty intervals
- Absolute as well as relative quantities when decision-relevant
- Exact denominators and analysis sets
- Assumption and sensitivity context
- Clinical, biological, policy, or practical relevance distinct from statistical compatibility

The ASA’s six p-value principles include:

- A p-value is about incompatibility with a specified model, not the probability a hypothesis is true.
- Threshold crossing alone should not determine scientific conclusions.
- Transparent reporting of all relevant analyses is required.
- Statistical significance does not measure effect size or importance.
- A p-value alone is not a good measure of evidence.

SAMPL provides concise biomedical statistical reporting guidance. Apply it as reporting guidance, not a universal analysis recipe.

## Topic-specific checks

### Sample size and precision

Look for:

- Prospective calculation or precision rationale
- Target effect or interval width
- Variance, event rate, prevalence, or accuracy assumptions
- Type I error, power, sidedness, and multiplicity when applicable
- Design effect, clustering, attrition, noncompliance, and missingness
- Model complexity and effective sample size
- Simulation details for complex designs

Do not request observed/post hoc power as a remedy for an imprecise result. Examine the estimate and uncertainty.

### Randomized trials

Check:

- Allocation sequence and concealment
- Prespecified estimand and analysis population
- Protocol/registry/outcome consistency
- Baseline adjustment and stratification factors
- Intercurrent events, adherence, treatment switching, and missing data
- Harms and unintended effects
- Sensitivity and supplementary analyses
- Non-inferiority/equivalence margin and interpretation if relevant

Use CONSORT 2025 and SPIRIT 2025 for reporting. Use ICH E9/E9(R1) only when its scope and decision context fit.

### Observational causal analyses

Check:

- Causal question and target contrast
- Time zero, eligibility, treatment/exposure assignment, follow-up, and outcome timing
- Confounder rationale and measurement timing
- Positivity/overlap
- Exchangeability and consistency assumptions
- Missingness, censoring, selection, and measurement error
- Model specification and balance diagnostics
- Sensitivity to unmeasured confounding or alternative specifications

Avoid judging causal identification from adjusted versus unadjusted p-values.

### Diagnostic accuracy

Check:

- Intended use, setting, and participant spectrum
- Index test and reference standard
- Threshold prespecification
- Blinding and timing
- Indeterminate/missing results
- Verification and incorporation bias
- Two-by-two denominators and uncertainty
- External applicability

STARD/STARD-AI describe reporting; use an appropriate risk-of-bias framework separately.

### Prediction models

Check:

- Intended use, prediction time, outcome, and target population
- Data source and participant flow
- Predictor availability at intended use
- Missing-data and preprocessing leakage
- Sample size relative to outcome information and complexity
- Internal validation and optimism correction
- Independent evaluation and dataset shift
- Calibration, discrimination, decision utility, and uncertainty
- Hyperparameter tuning separated from evaluation
- Reproducible model specification and preprocessing
- Subgroup performance tied to plausible use and harms

TRIPOD+AI replaces TRIPOD 2015 for regression and machine-learning prediction model reporting. STARD-AI is more appropriate when diagnostic accuracy of an index test is the primary aim.

### Systematic reviews and meta-analyses

Check:

- Protocol and registration
- Eligibility criteria and information sources
- Reproducible search dates and strategies
- Duplicate screening/extraction processes or justified alternatives
- Risk-of-bias assessment
- Effect measure and synthesis model
- Heterogeneity and prediction intervals when appropriate
- Dependence among estimates
- Small-study and reporting biases
- Certainty assessment, if claimed
- Transparent deviations and unavailable data

PRISMA 2020 assesses reporting. Do not substitute PRISMA coverage for review-conduct appraisal.

### Clustered and longitudinal data

Check:

- Level of assignment, measurement, and inference
- Within-cluster/subject correlation
- Number and distribution of clusters
- Small-cluster corrections where needed
- Time structure, nonlinear change, and irregular measurement
- Informative visit, dropout, or censoring processes
- Cluster-level versus individual-level covariates

Repeated observations do not increase independent sample size one-for-one.

### Multiplicity

Identify the inferential family before recommending adjustment:

- Multiple primary outcomes
- Multiple intervention arms or contrasts
- Repeated time points
- Subgroups and interactions
- Interim analyses
- High-dimensional features
- Model selection

Possible responses include hierarchical testing, family-wise control, false-discovery control, multilevel modeling, transparent exploratory labeling, or emphasis on estimates and uncertainty. The remedy depends on the claim and decision rule.

### Missing data

Check:

- Missingness by group, variable, outcome, and time
- Reasons and relation to intercurrent events
- Information used by imputation or weighting
- Number of imputations and pooling when applicable
- Compatibility of imputation and analysis models
- Uncertainty propagation
- Sensitivity to plausible departures from assumptions

Avoid demanding one preferred technique without considering the estimand and missingness process.

## Reproducibility review

### Materials and provenance

Check:

- Stable identifiers for datasets, samples, models, protocols, and materials
- Raw-to-processed provenance
- Exclusion and transformation records
- Versioned analysis inputs and outputs
- Repository accession numbers
- Data dictionary, units, and coding
- Domain metadata standard where applicable

Legacy domain standards and their current status are summarized in `references/reporting_standards.md`.

### Code and computational environment

Check:

- Executable code for central analyses when sharing is permitted
- Dependency versions or lock/environment file
- Operating-system or hardware requirements that affect results
- Random seeds and nondeterminism
- Parameter, configuration, and model checkpoints
- Run order and instructions
- Tests or validation of custom code
- License and access restrictions

Code availability does not prove that the code generated the reported result. Provenance and a reproducible run record are separate evidence.

### Data and access

Open sharing may be limited by consent, privacy, indigenous/community governance, security, contracts, or licensing. A useful statement should identify:

- What exists
- Where it is held
- Who can request access
- Criteria and process
- Expected timeline
- Restrictions and rationale
- Whether code or synthetic/aggregate alternatives are available

Do not request disclosure that would violate ethics, law, consent, or governance.

### Independent reproduction

Claim independent reproduction only if the reviewer actually:

1. Obtained authorized inputs.
2. Recorded versions and environment.
3. Ran documented commands.
4. Preserved content hashes or equivalent provenance.
5. Compared prespecified outputs.
6. Recorded deviations and failures.

A static consistency audit is not reproduction.

## When to request specialist review

Escalate when a central conclusion depends on methods outside competence, including:

- Complex adaptive, Bayesian, causal, survival, multilevel, spatial, or longitudinal methods
- High-dimensional omics or multiple-testing procedures
- Diagnostic, prediction, or AI evaluation
- Survey weighting or complex sampling
- Economic modeling
- Meta-analysis with dependent effects or network structure
- Unfamiliar qualitative or mixed-methods methodology
- Image forensics, biosecurity, privacy, or domain-specific ethics

Say what expertise is needed and which claim depends on it. Do not mask uncertainty with an automated score.

## Using the local checklist

Copy `assets/statistical_reproducibility_template.json`, record evidence locations without pasting manuscript prose into report fields, and run:

```bash
python3 scripts/audit_statistics_reproducibility.py local-checklist.json
```

Statuses:

- `verified_present`
- `partly_documented`
- `missing`
- `not_assessed`
- `not_applicable` with rationale

The tool reports item IDs and counts. It does not calculate merit, rerun analyses, or certify reproducibility.
