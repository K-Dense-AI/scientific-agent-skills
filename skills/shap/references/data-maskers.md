# Background Data and Maskers

SHAP values are defined relative to a cooperative game. The background data and masker define what hidden features mean and therefore help define the question being answered. They are not merely performance parameters.

## Start With the Estimand

For a row `x`, an explanation decomposes a model output relative to a baseline:

```text
explained output = base value + sum(feature attributions)
```

The baseline and attributions depend on the reference distribution used when features are hidden.

Examples of distinct questions:

- **Population-relative:** Why is this prediction different from the training population?
- **Current-production-relative:** Why is it different from recent production traffic?
- **Control-relative:** Why is it different from a clinically meaningful reference cohort?
- **Case-relative:** Why do two otherwise comparable cases receive different scores?

These questions can produce different baselines, signs, magnitudes, and rankings. State the intended question before sampling background rows.

## Background Selection

Use background data that:

- comes from the population relevant to the explanation question;
- passed the same preprocessing and schema validation as explained rows;
- excludes targets, post-outcome information, identifiers, and leakage fields;
- includes valid values and missingness patterns;
- is independent of the specific examples selected for storytelling;
- is versioned or reproducibly sampled.

Do not use:

- the explained row itself as the only background unless a pairwise contrast is explicitly intended;
- the test target to choose "representative" rows;
- the full dataset automatically;
- synthetic mean rows that violate categorical, compositional, or physiological constraints;
- production rows collected after an outcome if that changes the interpretation.

## Size and Convergence

Larger backgrounds increase cost for interventional tree, deep, kernel, and permutation methods. Current SHAP maskers default to at most 100 tabular background rows in several APIs.

Treat size as an empirical convergence choice:

1. Choose a reproducible candidate pool.
2. Compare baselines and top attribution summaries at increasing sizes, such as 25, 50, 100, and 250.
3. Repeat with multiple seeds when random sampling is used.
4. Stop when conclusions are stable enough for the use case.
5. Record the selected rows or a deterministic selection rule.

`shap.sample` samples without replacement:

```python
background = shap.sample(X_train, 100, random_state=7)
```

For heterogeneous populations, stratified sampling may be more appropriate:

```python
background = (
    training_frame.groupby("site", group_keys=False)
    .sample(n=20, random_state=7)
    .drop(columns="site")
)
```

Only stratify on information legitimately available at the prediction time and relevant to the reference population.

## Tabular Maskers

### `Independent`

```python
masker = shap.maskers.Independent(background, max_samples=100)
```

Hidden features are replaced by values from background rows and integrated over that marginal reference distribution.

Use when:

- interventional/marginal semantics match the question;
- the model accepts independently combined columns;
- a general callable needs a standard tabular masker.

Risk: combining observed and background columns can create off-manifold or impossible rows when features are dependent.

### `Partition`

```python
masker = shap.maskers.Partition(
    background,
    max_samples=100,
    clustering="correlation",
)
```

`Partition` constrains coalitions using a hierarchical feature tree. With `PartitionExplainer`, this produces Owen values for the constrained game.

Use when:

- feature groups should enter together;
- a hierarchy is scientifically meaningful;
- correlated or redundant features need grouped interpretation;
- text tokens or image regions have structure.

`clustering` can be:

- a SciPy pairwise-distance metric string; SHAP recommends `"correlation"` for common tabular use;
- a precomputed linkage matrix encoding a domain-defined hierarchy.

Correlation clustering is descriptive, not causal. Review the tree rather than assuming automatically derived groups are scientifically valid.

### `Impute`

```python
masker = shap.maskers.Impute(background, method="linear")
```

`Impute` estimates hidden features conditional on observed features. It is commonly paired with `LinearExplainer` for correlation-aware allocations.

Conditional games can give attribution to a feature the model does not directly use because that feature carries information about a used feature. Do not interpret such an attribution as a model coefficient or intervention effect.

### `Fixed` and composite maskers

- `Fixed`: leaves an input unchanged; useful for fixed labels or auxiliary arguments.
- `Composite`: joins maskers for multiple model inputs.
- `FixedComposite`: returns both masked and original inputs.
- `OutputComposite`: combines masking with a model output used by an explanation algorithm.

Use these only after verifying the model's full call signature with a one-row test.

## Domain Maskers

### Text

```python
masker = shap.maskers.Text(tokenizer)
```

Text masking respects tokenizer boundaries and can create a token hierarchy for `PartitionExplainer`. The mask token, collapse behavior, and tokenizer special tokens affect the explanation.

### Image

```python
masker = shap.maskers.Image("inpaint_telea", image_shape)
```

Supported masking approaches include blurring, inpainting, and constant values. Each asks a different counterfactual question. Inpainting may create plausible local texture but does not guarantee an in-distribution image.

See [modalities.md](modalities.md) for full workflows.

## Correlated and Redundant Features

There is no universally correct single-feature allocation when inputs share information.

### Marginal/interventional allocation

An independent masker asks how model output changes while integrating hidden features over a marginal reference. It can expose the model's functional dependence, including behavior on unrealistic combinations.

### Conditional allocation

A conditional masker asks how model output changes under an estimated conditional distribution. It stays closer to the observed manifold but can allocate credit to unused correlated features.

### Grouped allocation

A partition game attributes to hierarchical coalitions, reducing arbitrary competition among related features. Individual values remain conditional on the chosen hierarchy.

For important correlated features:

1. document correlations and domain relationships;
2. compare at least two defensible masker/background choices;
3. report grouped importance where individual allocation is unstable;
4. avoid causal language;
5. avoid choosing the masker only because it supports a preferred narrative.

## One-Hot, Encoded, and Engineered Features

If a model consumes transformed columns, SHAP explains those transformed inputs unless the entire preprocessing pipeline is wrapped in the model callable.

### Explain transformed space

Advantages:

- specialized model explainers can remain available;
- additivity is easy to validate;
- attribution matches the model's actual features.

Requirements:

- preserve transformed feature names;
- group one-hot levels when reporting the source variable;
- document scaling, imputation, and interactions.

```python
feature_names = preprocessor.get_feature_names_out()
X_background_t = preprocessor.transform(X_background)
X_eval_t = preprocessor.transform(X_eval)

explainer = shap.Explainer(
    model,
    X_background_t,
    feature_names=feature_names.tolist(),
)
exp = explainer(X_eval_t)
```

Only attach names when their order exactly matches the transformed matrix.

### Explain raw input space

Wrap the full pipeline in a callable:

```python
def predict_positive(frame):
    return fitted_pipeline.predict_proba(frame)[:, 1]

masker = shap.maskers.Independent(raw_background, max_samples=100)
explainer = shap.PermutationExplainer(
    predict_positive,
    masker,
    feature_names=raw_background.columns.tolist(),
    seed=7,
)
exp = explainer(raw_eval, max_evals=2 * raw_eval.shape[1] + 1)
```

This attributes raw columns but may be much slower and uses model-agnostic masking. Ensure the callable preserves DataFrame columns and dtypes.

## Missing Values

Distinguish:

- naturally missing values the model was trained to handle;
- values hidden by the SHAP masker;
- values imputed by preprocessing.

Do not manually replace masked values with `NaN` unless the masker and model are designed for that operation. For tree models, missing-value routing can be model-library-specific. Validate explanations after upgrading SHAP or the tree library.

## Backgrounds for Cohort Comparisons

Use a shared background when comparing cohorts if the goal is to compare model behavior against one common reference. Separate cohort-specific backgrounds change both baselines and attributions, confounding reference-population differences with model-use differences.

If separate backgrounds are scientifically necessary:

- present each baseline;
- avoid direct magnitude comparisons without qualification;
- run a shared-background sensitivity analysis.

## Fairness and Protected Attributes

A background distribution can change subgroup explanations but cannot establish fairness.

Do not infer:

- "the model is fair" because a protected feature has low mean absolute SHAP;
- "the model does not use race/sex/age" because the explicit column is absent;
- "removing the feature fixed bias";
- "equal mean SHAP implies equal treatment."

Proxy features, calibration, base rates, thresholds, error rates, and label quality require separate analysis.

## Reproducibility Record

Store:

- a hash or immutable identifier for background rows;
- sampling code and seed;
- raw and transformed feature schemas;
- masker class and parameters;
- output method, index, names, and units;
- model and preprocessing versions;
- SHAP and dependency versions;
- explanation row identifiers in a separate, access-controlled artifact if identifiers are sensitive.

Do not place secrets, protected health information, or direct identifiers into plot labels or exported explanation JSON.

## Sources

- Masker API: https://shap.readthedocs.io/en/latest/api.html#maskers
- Independent masker: https://shap.readthedocs.io/en/latest/generated/shap.maskers.Independent.html
- Partition masker: https://shap.readthedocs.io/en/latest/generated/shap.maskers.Partition.html
- Impute masker: https://shap.readthedocs.io/en/latest/generated/shap.maskers.Impute.html
- Causal interpretation caution: https://shap.readthedocs.io/en/latest/example_notebooks/overviews/Be%20careful%20when%20interpreting%20predictive%20models%20in%20search%20of%20causal%20insights.html
