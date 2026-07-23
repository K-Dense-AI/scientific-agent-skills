# SHAP Migration and Compatibility

This guide covers migration to SHAP 0.52.0 and the modern `shap.Explanation` API.

## Version Baseline

| SHAP release | Python requirement | Important compatibility note |
|---|---|---|
| 0.52.0 | `>=3.12` | Current release; NumPy `>=2`; native bindings moved to nanobind/scikit-build-core |
| 0.51.0 | `>=3.11` | Latest release suitable for Python 3.11 |
| 0.50.0 | `>=3.11` | First release after Python 3.9/3.10 support ended |
| 0.49.1 | `>=3.9` | Last release line supporting Python 3.9 and 3.10; fixes the broken 0.49.0 publication |

For a new environment:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install "shap[plots]==0.52.0"
```

For a project that cannot move off Python 3.11:

```bash
uv pip install "shap[plots]==0.51.0"
```

For Python 3.9 or 3.10, upgrade Python if possible. If temporarily constrained:

```bash
uv pip install "shap[plots]==0.49.1"
```

Do not claim 0.49.1 behavior is identical to 0.52. Read the release notes and test model-library compatibility.

## Major Changes Affecting Existing Code

### 0.45.0

- Python 3.8 support ended.
- Multi-output SHAP values changed from a list to a NumPy array with the output dimension last.
- Deprecated `feature_dependence` parameters were removed from `TreeExplainer` and `LinearExplainer`.
- Python 3.12 support was added.

### 0.46.0

- NumPy 2, Keras 3, and TensorFlow 2.16 support was added.
- The deprecated `auto_size_plot` argument to `summary_plot` was removed.

### 0.47.0

- `TreeExplainer(feature_perturbation="auto")` became the default behavior: interventional when background data are supplied, tree-path-dependent otherwise.
- Passing `approximate` to the `TreeExplainer` constructor was deprecated; pass it when calling the explainer.
- Plotting APIs continued moving toward `Explanation` inputs and returned axes.
- Legacy bar plotting gained deprecation guidance.

### 0.49.x

- 0.49.1 repaired the 0.49.0 release publication.
- 0.49.x was the final line supporting Python 3.9 and 3.10.
- C++ categorical-split support expanded.

### 0.50.0–0.51.0

- Python 3.11 became the minimum.
- Type coverage and tree/path-dependent behavior continued to improve.

### 0.52.0

- Python 3.12 became the minimum.
- NumPy 2 became a core minimum requirement.
- Native bindings moved from Cython/setup.py to nanobind with scikit-build-core and CMake.
- Tree/GPU fixes improved missing-value routing, vector-valued XGBoost base scores, and multiclass additivity.
- `TreeExplainer` gained a pandas nullable-dtype fix.
- Plot and documentation examples continued moving to the modern API.

## Explanation API Migration

### Compute explanations

Legacy:

```python
values = explainer.shap_values(X)
```

Modern:

```python
explanation = explainer(X)
values = explanation.values
base_values = explanation.base_values
```

Keep the `Explanation` object instead of immediately extracting `.values`; plots and slicing use its metadata.

### Base values

Legacy:

```python
base_value = explainer.expected_value
```

Modern:

```python
base_values = explanation.base_values
```

`base_values` can be scalar, per-row, per-output, or per-row/per-output. Inspect shape.

### Multi-output values

Pre-0.45 code often assumed a list:

```python
positive_values = values[1]
```

Modern tabular code uses the final output axis:

```python
positive_exp = explanation[..., 1]
positive_values = explanation.values[..., 1]
```

`explanation[1]` selects the second sample, not the second class.

For scikit-learn `RandomForestClassifier`, a typical shape is:

```text
(samples, features, classes)
```

For XGBoost binary classification with default raw output, a typical shape is:

```text
(samples, features)
```

Do not hard-code a binary shape across model families.

## Plot Migration

### Summary plot to beeswarm

Legacy:

```python
shap.summary_plot(values, X)
```

Modern:

```python
shap.plots.beeswarm(explanation)
```

### Summary bar to bar

Legacy:

```python
shap.summary_plot(values, X, plot_type="bar")
```

Modern:

```python
shap.plots.bar(explanation)
```

### Dependence plot to scatter

Legacy:

```python
shap.dependence_plot("age", values, X, interaction_index="bmi")
```

Modern:

```python
shap.plots.scatter(
    explanation[:, "age"],
    color=explanation[:, "bmi"],
)
```

### Force plot

Legacy:

```python
shap.force_plot(
    explainer.expected_value,
    values[row_index],
    X.iloc[row_index],
)
```

Modern:

```python
shap.plots.force(explanation[row_index])
```

### Local waterfall

Legacy code often manually built an `Explanation` from arrays. Modern:

```python
shap.plots.waterfall(explanation[row_index])
```

### Image plot

Legacy:

```python
shap.image_plot(values, images)
```

Modern:

```python
shap.plots.image(explanation)
```

### Decision plot

`shap.plots.decision` remains largely array-oriented:

```python
shap.plots.decision(
    base_value,
    values,
    features=X_display,
    feature_names=feature_names,
)
```

Select one output and compatible base value before calling it.

## TreeExplainer Migration

### `feature_dependence`

Removed:

```python
shap.TreeExplainer(model, feature_dependence="independent")
```

Current:

```python
shap.TreeExplainer(
    model,
    data=background,
    feature_perturbation="interventional",
)
```

Or:

```python
shap.TreeExplainer(
    model,
    feature_perturbation="tree_path_dependent",
)
```

These are not mechanical synonyms for every old setting. Reconfirm the intended game and baseline.

### Default feature perturbation

Old code could rely on an interventional default. Current `"auto"` behavior depends on whether data are passed.

Make reproducibility explicit:

```python
explainer = shap.TreeExplainer(
    model,
    data=background,
    feature_perturbation="interventional",
    model_output="raw",
)
```

### Approximation

Deprecated constructor use:

```python
explainer = shap.TreeExplainer(model, approximate=True)
values = explainer(X)
```

Current:

```python
explainer = shap.TreeExplainer(model)
explanation = explainer(X, approximate=True)
```

Label approximate values and do not treat them as ordinary Tree SHAP.

### Probability output

Use:

```python
explainer = shap.TreeExplainer(
    model,
    data=background,
    feature_perturbation="interventional",
    model_output="probability",
)
explanation = explainer(X)
```

Probability and log-loss output modes are currently supported only under interventional feature perturbation.

## DeepExplainer Output Migration

Pre-0.45 code:

```python
values_by_class = explainer.shap_values(X)
class_values = values_by_class[class_index]
```

Modern one-input, multi-output result:

```python
values = explainer.shap_values(X)
class_values = values[..., class_index]
```

Multiple model inputs still produce a list, one array per input. `ranked_outputs=k` returns `(values, indexes)`; preserve the indexes because selected outputs can differ per row.

## Link and Output Migration

Do not use a display link to pretend an explanation was computed in another space.

```python
shap.plots.force(raw_margin_exp[row], link="logit")
```

This labels raw margins as probabilities for display. It is not equivalent to:

```python
shap.TreeExplainer(
    model,
    data=background,
    feature_perturbation="interventional",
    model_output="probability",
)(X)
```

The two additive decompositions can differ.

## End-to-End Migration Recipe

1. Pin old and new environments.
2. Capture model predictions and existing SHAP outputs on a small immutable fixture.
3. Replace `.shap_values(X)` with `explainer(X)`.
4. Print every result shape.
5. Replace list-based output selection with final-axis slicing.
6. Replace legacy plotting calls.
7. Make tree perturbation and output explicit.
8. Validate additive reconstruction against the exact selected output.
9. Compare baselines and local values; do not require numerical identity if the game/default changed.
10. Run model-library compatibility tests, especially for XGBoost, LightGBM, CatBoost, TensorFlow, Keras, and PyTorch.
11. Update stored report metadata and migration notes.

## Compatibility Diagnostic

```python
import importlib.metadata
import platform

packages = [
    "shap",
    "numpy",
    "pandas",
    "scikit-learn",
    "xgboost",
    "lightgbm",
    "catboost",
    "tensorflow",
    "keras",
    "torch",
]

print("Python", platform.python_version())
for package in packages:
    try:
        print(package, importlib.metadata.version(package))
    except importlib.metadata.PackageNotFoundError:
        pass
```

Attach this output to reproducible bug reports, without environment variables or credentials.

## Sources

- SHAP release notes: https://shap.readthedocs.io/en/latest/release_notes.html
- SHAP 0.52.0 release: https://github.com/shap/shap/releases/tag/v0.52.0
- PyPI metadata: https://pypi.org/project/shap/0.52.0/
- Explanation migration guide: https://shap.readthedocs.io/en/latest/example_notebooks/api_examples/migrating-to-new-api.html
- TreeExplainer API: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html
- Plot API: https://shap.readthedocs.io/en/latest/api.html#plots
