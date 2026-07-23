# SHAP Workflows

These workflows target SHAP 0.52.0 and the `shap.Explanation` API. Adapt model-specific code, but preserve the decisions about output, background, masking, validation, and reporting.

## Workflow 1: Reproducible Tabular Audit

### 1. Freeze the predictive context

Record:

- dataset and split identifiers;
- model and preprocessing artifact versions;
- package versions;
- feature schema and order;
- output method/index/name/units;
- background population and sampling rule;
- explainer/masker configuration;
- evaluation row selection.

Do not begin interpretation until predictive performance is acceptable for the intended population.

### 2. Build the background from training/reference data

```python
rng_seed = 7
background = shap.sample(X_train, 100, random_state=rng_seed)
```

Use a shared background for results intended for direct comparison.

### 3. Explain held-out rows

```python
explainer = shap.Explainer(
    model,
    background,
    algorithm="tree",
    seed=rng_seed,
)
all_outputs = explainer(X_test)
```

### 4. Select and validate the output

```python
if all_outputs.values.ndim == 3:
    explanation = all_outputs[..., class_index]
    expected = model.predict_proba(X_test)[:, class_index]
else:
    explanation = all_outputs
    expected = model.predict(X_test)

reconstructed = (
    np.asarray(explanation.base_values)
    + np.asarray(explanation.values).sum(axis=1)
)
max_abs_error = float(np.max(np.abs(reconstructed - expected)))
np.testing.assert_allclose(reconstructed, expected, rtol=1e-5, atol=1e-6)
```

This example is appropriate only when the explainer's selected output matches `predict` or `predict_proba`. For raw-margin models, compute the corresponding margin instead.

### 5. Move from global to local

```python
shap.plots.bar(explanation, max_display=20)
shap.plots.beeswarm(explanation, max_display=20)

global_importance = explanation.abs.mean(0)
top_index = int(np.argmax(global_importance.values))
top_feature = global_importance.feature_names[top_index]
shap.plots.scatter(explanation[:, top_feature], color=explanation)

shap.plots.waterfall(explanation[selected_row])
```

Select local rows using a documented criterion: high error, threshold proximity, representative quantile, or predeclared case.

### 6. Publish an audit record

Include:

- model metric table;
- global attribution distribution;
- selected feature relationships;
- local explanations with selection rules;
- background and masking sensitivity;
- additivity error;
- non-causal and non-fairness caveats.

## Workflow 2: Regression

```python
explainer = shap.Explainer(regressor, background)
explanation = explainer(X_test)

prediction = regressor.predict(X_test)
reconstructed = explanation.base_values + explanation.values.sum(axis=1)
np.testing.assert_allclose(reconstructed, prediction, rtol=1e-5, atol=1e-6)
```

State whether the target was transformed. If the model predicts log target values, SHAP values are in log-target units unless the explained callable reverses the transform.

For transformed targets, choose one:

- explain the model's native output and label units accurately;
- wrap the inverse-transformed prediction in a model-agnostic callable and explain that output;
- provide both and explain why additive decompositions differ.

## Workflow 3: Binary Classification

Binary model outputs vary:

- scikit-learn tree classifiers commonly return one output per class;
- XGBoost/LightGBM raw tree outputs commonly return one margin;
- a model-agnostic `predict_proba` callable returns two columns.

### Explicit probability-space tree explanation

```python
explainer = shap.TreeExplainer(
    model,
    data=background,
    feature_perturbation="interventional",
    model_output="probability",
)
all_outputs = explainer(X_test)

if all_outputs.values.ndim == 3:
    positive = all_outputs[..., positive_class_index]
else:
    positive = all_outputs

expected = model.predict_proba(X_test)[:, positive_class_index]
reconstructed = positive.base_values + positive.values.sum(axis=1)
np.testing.assert_allclose(reconstructed, expected, rtol=1e-5, atol=1e-6)
```

If the model family exposes only one positive-class probability output, do not attempt a second class slice.

### Threshold-focused analysis

```python
probability = model.predict_proba(X_test)[:, positive_class_index]
distance = np.abs(probability - decision_threshold)
near_threshold = np.argsort(distance)[:25]

shap.plots.heatmap(positive[near_threshold])
```

Threshold proximity is a legitimate predeclared selection rule. It does not make SHAP a recourse method.

## Workflow 4: Multiclass or Multi-Output Models

```python
all_outputs = explainer(X_test)
print(all_outputs.values.shape)
print(all_outputs.output_names)

per_output = {
    str(name): all_outputs[..., index]
    for index, name in enumerate(all_outputs.output_names)
}
```

For each output:

1. validate against the corresponding model output;
2. generate its own global summary;
3. keep axis units and scales explicit;
4. report class prevalence and performance.

Do not:

- use `all_outputs[class_index]` to select an output;
- assume old list-of-arrays behavior;
- average signed attributions across classes;
- compare classes after using different backgrounds.

For many outputs, explain only predeclared or top-ranked outputs:

```python
selected = explainer(
    X_subset,
    outputs=shap.Explanation.argsort.flip[:5],
)
```

The `outputs` option is explainer-dependent. Verify selected indexes/names, especially when top outputs can vary by row.

## Workflow 5: Pipelines and Feature Names

Choose whether to explain raw or transformed features.

### Transformed-space, model-specific explanation

```python
X_train_t = preprocessor.transform(X_train)
X_test_t = preprocessor.transform(X_test)
feature_names = preprocessor.get_feature_names_out()

explainer = shap.Explainer(
    model,
    X_train_t[:100],
    feature_names=feature_names.tolist(),
)
explanation = explainer(X_test_t)
```

Benefits: speed and specialized explainer support.

Costs: one source feature may expand into many encoded columns. Aggregate one-hot levels only after preserving signed local contributions and documenting the aggregation:

```python
source_group_value = explanation.values[:, source_column_indices].sum(axis=1)
```

Sum signed values for a local additive group. For global importance, decide whether the quantity is:

- mean absolute value of the summed group; or
- sum of each encoded column's mean absolute value.

They answer different questions.

### Raw-space, end-to-end explanation

```python
def positive_probability(frame):
    return pipeline.predict_proba(frame)[:, positive_class_index]

masker = shap.maskers.Independent(raw_background, max_samples=100)
explainer = shap.PermutationExplainer(
    positive_probability,
    masker,
    feature_names=raw_background.columns.tolist(),
    seed=7,
)
explanation = explainer(
    raw_test,
    max_evals=(2 * raw_test.shape[1] + 1) * 5,
)
```

Benefits: source-level attribution.

Costs: slower model-agnostic evaluation and potentially unrealistic raw-column combinations.

## Workflow 6: Error and Loss Analysis

Attributing predictions is not the same as attributing errors.

### Analyze errors as a cohort

```python
prediction = model.predict(X_test)
error_mask = prediction != y_test.to_numpy()

cohorts = {
    "correct": explanation[~error_mask],
    "incorrect": explanation[error_mask],
}
shap.plots.bar(cohorts, max_display=20)
```

Include group sizes. Different attribution magnitudes do not identify the cause of error by themselves.

### Decompose tree log loss

For supported tree models:

```python
loss_explainer = shap.TreeExplainer(
    model,
    data=background,
    feature_perturbation="interventional",
    model_output="log_loss",
)
loss_exp = loss_explainer(X_test, y_test)
```

Log-loss explanations require labels at call time and decompose loss rather than prediction. Some classifier families retain an output axis, so inspect `loss_exp.values.shape`, select the intended output before plotting, and validate against the model-specific loss quantity on a small batch. Label plots as log-loss contributions.

Use this to investigate:

- features associated with high model loss;
- cohort-specific sources of loss;
- training/test behavior differences.

Do not call a high loss attribution proof of label error; inspect data and model residuals separately.

## Workflow 7: Cohort and Fairness Investigation

```python
cohorts = explanation.cohorts(group_labels)
shap.plots.bar(cohorts.abs.mean(0), max_display=20)
```

For each cohort also compute:

- sample size;
- outcome prevalence;
- score distribution;
- discrimination/performance;
- calibration;
- confusion-matrix rates at operational thresholds;
- missingness and feature distribution.

SHAP contributes descriptive model-use evidence. It does not replace a fairness framework.

Avoid claims such as:

- "protected attribute importance should be zero";
- "the model is unbiased because group plots look similar";
- "remove the proxy feature to guarantee fairness."

Use a shared background for direct comparison. If a cohort-specific baseline is required, report both a shared-background and cohort-background analysis.

## Workflow 8: Model Comparison

Before comparing attribution:

1. evaluate models on identical rows;
2. explain the same target/output and units;
3. use the same background and masking semantics;
4. align feature representations;
5. validate each model separately.

```python
importance = {}

for name, exp in explanations.items():
    importance[name] = pd.Series(
        np.abs(exp.values).mean(axis=0),
        index=exp.feature_names,
        name=name,
    )

importance_frame = pd.concat(importance.values(), axis=1)
```

Compare:

- rank correlation;
- signed feature distributions;
- local agreement on identical rows;
- stability across refits;
- performance and calibration.

Do not treat agreement as truth. Correlated features can cause equivalent models to distribute credit differently.

## Workflow 9: Feature Engineering

Use SHAP to generate hypotheses, then validate them out of sample.

1. Fit a baseline in a training fold.
2. Inspect scatter plots and interaction candidates.
3. Propose a transformation based on domain knowledge.
4. Build the feature inside cross-validation.
5. Compare predictive metrics and calibration on untouched data.
6. Recompute explanations with the same reference design.

Avoid engineering features after repeatedly inspecting the final test set.

For a nonlinear pattern:

```python
shap.plots.scatter(explanation[:, feature_name], color=explanation)
```

For tree interactions:

```python
interaction = tree_explainer.shap_interaction_values(X_subset)
```

Use interaction values as model diagnostics, not proof of real-world synergy.

## Workflow 10: Time Series

Random train/test splits and random backgrounds can leak future information.

1. Use temporal or rolling-origin validation.
2. Build lag/rolling features using past data only.
3. Choose background rows from an allowed historical reference window.
4. Explain a fixed forecast horizon and output.
5. preserve time ordering in monitoring plots.
6. compare seasonal regimes separately.

```python
background = X_train.loc[reference_start:reference_end]
evaluation = X_test.loc[forecast_start:forecast_end]
explanation = explainer(evaluation)
```

Lag features are highly dependent. Compare independent and grouped/domain-constrained maskers, and report instability. A lag attribution is not the causal effect of changing the historical outcome.

For sequence models that consume a time-by-channel tensor, define whether a "feature" is:

- one time point;
- one channel;
- one time-channel cell;
- a grouped time window.

Use a masker consistent with that unit.

## Workflow 11: Text and Images

Use domain maskers and constrain outputs:

```python
# Text
text_masker = shap.maskers.Text(tokenizer)
text_explainer = shap.Explainer(
    text_model_fn,
    text_masker,
    algorithm="partition",
    output_names=class_names,
)
text_exp = text_explainer(text_rows)

# Image
image_masker = shap.maskers.Image("inpaint_telea", image_shape)
image_explainer = shap.Explainer(
    image_model_fn,
    image_masker,
    output_names=class_names,
)
image_exp = image_explainer(
    images,
    max_evals=500,
    batch_size=50,
    outputs=shap.Explanation.argsort.flip[:3],
)
```

See [modalities.md](modalities.md) for model wrappers and interpretation cautions.

## Workflow 12: Stability and Uncertainty

Repeat the analysis across:

- model refits or cross-validation folds;
- background samples;
- approximation seeds/budgets;
- plausible maskers;
- evaluation cohorts.

Example background sensitivity:

```python
importance_runs = []

for seed in range(10):
    background = shap.sample(X_train, 100, random_state=seed)
    exp = shap.Explainer(model, background)(X_test)
    if exp.values.ndim == 3:
        exp = exp[..., class_index]
    importance_runs.append(np.abs(exp.values).mean(axis=0))

importance_runs = np.stack(importance_runs)
importance_mean = importance_runs.mean(axis=0)
importance_low = np.quantile(importance_runs, 0.025, axis=0)
importance_high = np.quantile(importance_runs, 0.975, axis=0)
```

These intervals describe background-sampling variation for a fixed model, not total statistical uncertainty.

## Workflow 13: Production Explanation Service

Production requirements:

- version model, preprocessing, SHAP, background, masker, output, and feature schema together;
- enforce input column order and dtype;
- cap request rows and explanation budgets;
- return output name, units, baseline, contributions, and reconstruction error;
- avoid exposing sensitive raw feature values;
- monitor latency and failure rates;
- test explanations after every model-library or SHAP upgrade.

Prefer rebuilding the explainer from trusted, versioned components in a controlled process. Python pickle/joblib artifacts can execute code; never deserialize an untrusted model or explainer.

Example response construction after validation:

```python
def format_local_explanation(local_exp, prediction, top_n=10):
    values = np.asarray(local_exp.values)
    order = np.argsort(np.abs(values))[::-1][:top_n]

    reconstructed = float(np.asarray(local_exp.base_values) + values.sum())
    return {
        "prediction": float(prediction),
        "base_value": float(np.asarray(local_exp.base_values)),
        "reconstructed_output": reconstructed,
        "max_reconstruction_error": abs(reconstructed - float(prediction)),
        "output_name": local_exp.output_names,
        "contributions": [
            {
                "feature": local_exp.feature_names[index],
                "shap_value": float(values[index]),
            }
            for index in order
        ],
    }
```

Do not truncate contributions before checking reconstruction; omitted values still matter.

## Workflow 14: Attribution Monitoring

Attribution drift can reflect:

- input drift;
- model-version change;
- background change;
- feature pipeline change;
- genuine changes in model use.

Keep the model and reference fixed when detecting input-driven attribution drift.

Numeric summaries:

```python
def attribution_summary(exp):
    values = np.asarray(exp.values)
    return {
        "mean": values.mean(axis=0),
        "mean_abs": np.abs(values).mean(axis=0),
        "q05": np.quantile(values, 0.05, axis=0),
        "q50": np.quantile(values, 0.50, axis=0),
        "q95": np.quantile(values, 0.95, axis=0),
    }
```

Monitor:

- output and baseline distributions;
- attribution distributions, not only means;
- model performance when labels arrive;
- missingness and schema;
- group-specific behavior.

Set thresholds from historical variability and operational consequences, not arbitrary percentage changes.

## Review Checklist

- [ ] The explained output and units are explicit.
- [ ] Background comes from a defensible reference population.
- [ ] The masker matches feature structure.
- [ ] Multi-output results are sliced correctly.
- [ ] Additivity is checked against the correct model output.
- [ ] Local rows and cohorts use documented selection rules.
- [ ] Correlation and background sensitivity are evaluated.
- [ ] Performance accompanies explanations.
- [ ] Fairness, causal, and recourse claims are separated.
- [ ] Version and schema metadata are retained.
- [ ] No untrusted model/explainer artifact is deserialized.

## Sources

- SHAP examples: https://shap.readthedocs.io/en/latest/index.html
- Tabular examples: https://shap.readthedocs.io/en/latest/tabular_examples.html
- API examples: https://shap.readthedocs.io/en/latest/api_examples.html
- TreeExplainer: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html
- Explanation: https://shap.readthedocs.io/en/latest/generated/shap.Explanation.html
- Causal interpretation caution: https://shap.readthedocs.io/en/latest/example_notebooks/overviews/Be%20careful%20when%20interpreting%20predictive%20models%20in%20search%20of%20causal%20insights.html
