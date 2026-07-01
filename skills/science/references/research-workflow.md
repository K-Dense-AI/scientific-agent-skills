# Research Workflow

## Literature Workflow

1. Convert the user request into a precise research question.
2. Search primary sources first, then use reviews for context.
3. Track search terms, databases/sites, and date searched.
4. Extract only decision-relevant fields.
5. Group studies by design and model before comparing effects.
6. Explain conflicts by population, assay, timing, endpoint, power, or analysis choices.
7. End with confidence and gaps, not a one-sided conclusion.

## Dataset Workflow

1. Identify accession, source URL, license/terms, assay, organism, tissue/cell type, perturbation, and sample labels.
2. Verify downloaded files with checksums or size/date records when available.
3. Build a sample sheet from structured metadata, not titles or abstracts.
4. Quarantine ambiguous samples before analysis.
5. Run QC before normalization or modeling.
6. Keep raw, processed, and final outputs separate.
7. Save scripts, environment details, and result manifests.

## Analysis Workflow

1. State the estimand or comparison before coding.
2. Choose tests/models appropriate for the data shape and design.
3. Handle pairing, repeated measures, batches, covariates, and missingness explicitly.
4. Correct for multiple testing when testing multiple hypotheses/features.
5. Include negative controls, positive controls, or null/randomization checks when feasible.
6. Prefer interpretable baselines before complex models.
7. Confirm that figure labels, table columns, and text claims match generated outputs.

## Experiment Workflow

1. Define the causal model and falsifiable predictions.
2. Pick the simplest system that can test the prediction.
3. Specify controls before conditions.
4. Define primary endpoint, secondary endpoints, exclusion rules, and blinding/randomization.
5. Specify what result would refute or deprioritize the hypothesis.
6. Keep protocols high-level unless the user has asked for appropriate, safe operational detail.

## Writing Workflow

1. Make a claim ledger: each major claim gets evidence, caveat, and source/artifact path.
2. Put methods and limitations near the results they qualify.
3. Avoid novelty inflation; state exactly what is new.
4. Make figures answer one question each.
5. Re-read source artifacts before finalizing manuscripts, responses, or summaries.
