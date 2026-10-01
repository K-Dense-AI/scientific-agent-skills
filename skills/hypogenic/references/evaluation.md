# Local output inspection and evaluation

Reviewed 2026-10-01 against the unchanged 0.3.5 output serializer.
All bundled operations in this reference are deterministic and model-free.
They do not establish scientific truth.

## Hypothesis-bank inspection

The pinned upstream serializer writes a JSON object whose keys are hypothesis
text and whose values contain:

- `hypothesis`: same text as the object key;
- `acc`: finite number in `[0, 1]`;
- `reward`: finite ranking value;
- `num_visits`: non-negative integer;
- `correct_examples`: `[row_index, label]` pairs;
- optionally `num_select` in some literature/union outputs.

Inspect without echoing text:

```bash
python3 scripts/inspect_outputs.py hypotheses \
  --input outputs/hypotheses.json \
  --root .
```

The report includes file SHA-256, bank size, normalized duplicate counts,
length/statistic ranges, and a bounded sample of hypothesis SHA-256 values.
Candidate strings are never printed or interpreted, including duplicate-key
error messages.

Stored `acc` and `reward` are algorithm state from the generation/update
workflow. They are not an independently reproduced evaluation and should not
be described as p-values, confidence intervals, causal effects, or scientific
validation.

## Strict saved-result schema

The upstream inference CLI logs metrics but does not define a durable
prediction artifact. This skill therefore uses a small local interchange
schema:

```json
{
  "schema_version": "1.0",
  "dataset_manifest_sha256": "<64 lowercase hex>",
  "hypothesis_bank_sha256": "<64 lowercase hex>",
  "split": "test",
  "records": [
    {
      "id": "stable-nonsecret-id",
      "label": "class-a",
      "prediction": "class-a"
    }
  ]
}
```

`prediction` may be `null` for an abstention or extraction failure. IDs must be
unique; duplicate-ID errors identify the record index without printing the ID.
Do not store prompts, chain-of-thought, provider responses, credentials,
or raw sensitive features in this file. Replace the placeholder hashes in
`assets/result.example.json` with hashes of the exact reviewed artifacts.

Inspect structure:

```bash
python3 scripts/inspect_outputs.py results \
  --input results/test_predictions.json \
  --root .
```

The report redacts IDs, labels, and predictions; category values are represented
by short SHA-256 fingerprints.

## Evaluation plan

Freeze a plan before looking at test metrics:

```bash
python3 scripts/evaluate_local.py plan \
  --config reviewed_run_config.json \
  --manifest dataset_manifest.json \
  --root .
```

The plan records:

- immutable data source revision and manifest hash;
- provider/model/destination;
- train, validation, and test roles;
- row and hypothesis caps;
- planned metrics;
- required provenance and interpretation limits.

It does not read dataset rows or invoke a model.

## Metrics report

```bash
python3 scripts/evaluate_local.py report \
  --results results/test_predictions.json \
  --root . \
  --expected-split test
```

Implemented metrics:

- `coverage`: non-null predictions divided by all records;
- `accuracy_all_records`: exact matches divided by all records; null predictions
  count as incorrect;
- `accuracy_covered_records`: exact matches among non-null predictions;
- `macro_f1_all_records`: unweighted mean of per-label F1 over the union of
  observed true and non-null predicted labels;
- redacted confusion matrix, with a separate `<missing>` prediction column.

All arithmetic uses the supplied saved strings exactly. There is no label
normalization beyond schema validation. A custom label extractor must be frozen
before test evaluation and its behavior documented.

## Reporting checklist

Report at minimum:

1. `hypogenic` version, source commit, and artifact hash;
2. dataset repository, immutable revision, manifest SHA-256, and file hashes;
3. task config hash, provider wrapper, exact model, and data destination;
4. train/validation/test/OOD roles and sample counts;
5. generation/inference settings, seeds, hypothesis count, and selection rule;
6. token/request/cost caps and actual provider usage when available;
7. result and hypothesis-bank hashes;
8. coverage, accuracy, macro-F1, class support, and uncertainty across seeds;
9. duplicate/leakage audit results;
10. failures, exclusions, abstentions, retries, and deviations;
11. provider retention/privacy terms reviewed for the run;
12. a statement that generated hypotheses are candidates, not evidence.

The local tool does not calculate confidence intervals or significance tests.
Choose those methods from a prespecified design that respects dependence,
repeated seeds, multiple comparisons, class imbalance, and the data-generating
process.

## Scientific interpretation limits

Predictive benchmark performance can show that a textual heuristic was useful
for a declared classification setup. It does not by itself establish:

- that the proposed mechanism is true or causal;
- that the pattern generalizes beyond the sampled population/time/domain;
- novelty relative to all scientific literature;
- robustness to paraphrases, near duplicates, annotation artifacts, or
  distribution shift;
- clinical, policy, or safety validity;
- absence of data leakage or provider/model memorization.

Validate promising candidates using independent data, domain-expert review,
appropriate controls, alternative explanations, sensitivity analyses, and,
where warranted, prospective or experimental tests.
