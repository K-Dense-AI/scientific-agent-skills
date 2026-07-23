---
name: shap
description: Explain and audit machine-learning predictions with SHAP. Use for selecting SHAP explainers and maskers, computing and validating feature attributions, handling multi-output explanations, and producing local or global SHAP visualizations.
license: MIT
compatibility: Requires Python 3.12+ and uv for SHAP 0.52.0; model-specific libraries are optional.
allowed-tools: "Read Bash"
metadata:
  version: "2.0"
  skill-author: K-Dense Inc.
---

# SHAP

Use SHAP to describe how a fitted predictive model maps inputs to outputs. Work from the modern `shap.Explanation` API, make the explained output and background distribution explicit, and validate every explanation before interpreting it.

This skill is aligned with **SHAP 0.52.0** (released 2026-05-28). That release requires Python 3.12 or newer.

## Operating Rules

1. Explain a fixed, evaluated model; do not use SHAP as a substitute for predictive validation.
2. Use held-out or clearly labeled analysis rows for explanations. Choose background rows only from an appropriate training or reference population.
3. State the explained output: regression value, raw margin, probability, log loss, logit, or another model method.
4. Keep explanations as `shap.Explanation` objects. Call `explainer(X)`; use `.shap_values(X)` only when maintaining legacy code.
5. For multi-output models, select one output before using tabular plots: `explanation[..., output_index]`.
6. Check `base_values + values.sum(...)` against the exact model output being explained.
7. Treat SHAP as a description of model behavior under a masking/background choice. It does not establish causality, fairness, recourse, or scientific mechanism.
8. Never silence an additivity failure until input shape, preprocessing, model version, output space, and row ordering have been checked.
9. Do not load untrusted pickle, joblib, model, or explainer artifacts; those formats can execute code during deserialization.

## Install

Create an isolated environment and pin the documented release:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install "shap[plots]==0.52.0"
```

`shap[plots]` installs the plotting dependencies. Add the fitted model's package at a version compatible with the project. For older Python compatibility, read [references/migration.md](references/migration.md) instead of silently installing a different SHAP release.

Confirm the environment before debugging an API mismatch:

```python
import platform
import shap

print("Python:", platform.python_version())
print("SHAP:", shap.__version__)
```

## Standard Workflow

### 1. Define the explanation target

Record:

- model and preprocessing version;
- exact callable or model method being explained;
- output name/index and units;
- evaluation rows;
- background/reference population;
- masker and explainer algorithm;
- SHAP and model-library versions.

For classifiers, decide whether the task needs raw margins or probabilities. Defaults differ by model family; never infer units from the plot color or sign.

### 2. Select an explainer and masker

Start with `shap.Explainer(model, masker)` when automatic dispatch is sufficient. Instantiate a specialized explainer when its assumptions or output controls matter.

| Situation | Preferred choice | Important constraint |
|---|---|---|
| Supported tree ensemble | `TreeExplainer` | `model_output="probability"` and `"log_loss"` require interventional masking and background data |
| Linear model | `LinearExplainer` | The masker determines interventional versus correlation-aware behavior |
| Small feature space | `ExactExplainer` | Cost grows quickly with unconstrained feature count |
| General tabular callable | `PermutationExplainer` | Budget at least one full forward/reverse permutation |
| Hierarchical feature groups, text, or image | `PartitionExplainer` | The partition tree changes the cooperative game |
| Differentiable neural network | `DeepExplainer` or `GradientExplainer` | Framework support, output shape, and background choice require testing |
| Legacy Kernel SHAP workflow | `KernelExplainer` | Usually much slower than model-specific methods |

Use the detailed decision guide in [references/explainers.md](references/explainers.md). Use [references/data-maskers.md](references/data-maskers.md) when features are correlated, structured, sparse, or semantically grouped.

### 3. Compute a modern `Explanation`

This complete binary-classification example uses an explicit background and selects the positive-class output:

```python
import numpy as np
import shap
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

X, y = load_breast_cancer(as_frame=True, return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    stratify=y,
    random_state=7,
)

model = RandomForestClassifier(
    n_estimators=200,
    min_samples_leaf=3,
    random_state=7,
    n_jobs=-1,
).fit(X_train, y_train)

background = shap.sample(X_train, 100, random_state=7)
explainer = shap.Explainer(model, background, algorithm="tree")
all_outputs = explainer(X_test)

# sklearn tree classifiers expose one output per class.
positive = all_outputs[..., 1]
assert positive.values.shape == X_test.shape

reconstructed = np.asarray(positive.base_values) + positive.values.sum(axis=1)
expected = model.predict_proba(X_test)[:, 1]
np.testing.assert_allclose(reconstructed, expected, rtol=1e-5, atol=1e-6)

shap.plots.beeswarm(positive, max_display=15)
shap.plots.waterfall(positive[0], max_display=15)
```

Output shape is model-dependent:

- one tabular output: `(samples, features)`;
- multiple tabular outputs: `(samples, features, outputs)`;
- multiple model inputs: often a list of arrays or explanations;
- image/text explanations: feature axes follow the input representation, with output selection on the final axis when present.

Do not use the pre-0.45 pattern `values[class_index]` for a modern multi-output array. Use `values[..., class_index]` or slice the `Explanation` itself.

### 4. Control tree output semantics when needed

For a supported tree classifier, probability-space explanations must be explicit:

```python
background = shap.sample(X_train, 200, random_state=7)

explainer = shap.TreeExplainer(
    model,
    data=background,
    feature_perturbation="interventional",
    model_output="probability",
)
probability_exp = explainer(X_test)
```

In SHAP 0.52:

- `feature_perturbation="auto"` uses interventional semantics when background data is supplied and tree-path-dependent semantics otherwise;
- probability and log-loss output modes are supported only with interventional semantics;
- pass `approximate=True` to `explainer(X, approximate=True)` if deliberately using the lower-fidelity tree approximation; do not pass it to the constructor.

### 5. Use a model-agnostic callable deliberately

Pass the exact callable whose outputs will be interpreted:

```python
masker = shap.maskers.Independent(background, max_samples=100)
explainer = shap.Explainer(
    model.predict_proba,
    masker,
    algorithm="permutation",
    output_names=[str(label) for label in model.classes_],
    seed=7,
)

budget = 2 * X_test.shape[1] + 1
all_outputs = explainer(X_test.iloc[:20], max_evals=budget)
positive = all_outputs[..., 1]
```

Increase `max_evals` to average over more permutations when estimates are unstable. Keep the seed, background sample, and evaluation budget in the report.

### 6. Visualize the question, not merely the available plot

| Question | Plot |
|---|---|
| Which features have the largest average attribution magnitude? | `shap.plots.bar(exp)` |
| How do direction, magnitude, and observed values vary globally? | `shap.plots.beeswarm(exp)` |
| Why did one prediction differ from its baseline? | `shap.plots.waterfall(exp[i])` |
| How does one feature's attribution vary over its values? | `shap.plots.scatter(exp[:, feature])` |
| Do explanations form sample-level patterns? | `shap.plots.heatmap(exp)` |
| How do predefined cohorts differ descriptively? | `shap.plots.bar(exp.cohorts(labels).abs.mean(0))` |
| Which tokens or image regions contribute to an output? | `shap.plots.text(exp)` or `shap.plots.image(exp)` |

Read [references/plots.md](references/plots.md) before customizing or saving figures.

### 7. Report limitations with results

At minimum, report:

- output and units;
- baseline/reference population;
- explainer and masker;
- sample count and selection;
- output index/name;
- additivity error or applicable approximation diagnostics;
- known correlated/grouped features;
- whether results are local, aggregated, or cohort-specific;
- a clear non-causal statement.

## Common Tasks

### Global and local analysis

Use global plots to locate important patterns, scatter plots to inspect those patterns, and local plots to investigate selected rows. Do not select only visually dramatic rows without documenting the selection rule.

### Multiclass models

Set `output_names` where possible, inspect `explanation.output_names`, and slice an output before plotting:

```python
class_exp = explanation[..., "class_name"]
# or
class_exp = explanation[..., class_index]
```

Never average signed attributions across classes. For cross-class comparison, preserve the same model, rows, background, output space, and aggregation.

### Cohorts, subgroup analysis, and fairness

SHAP can compare how a model uses features across cohorts, but this is not a fairness test. A protected feature with small SHAP magnitude does not rule out proxy discrimination, and removing a protected feature does not establish fairness. Pair attribution analysis with performance, calibration, error-rate, and domain-appropriate fairness metrics.

See [references/workflows.md](references/workflows.md) for cohort construction, model comparison, error analysis, log-loss explanations, monitoring, and production records.

### Text and images

Use domain maskers rather than treating tokens or pixels as ordinary independent columns:

- `shap.maskers.Text(tokenizer)` with `PartitionExplainer` for token groups;
- `shap.maskers.Image(...)` with `PartitionExplainer` for image regions;
- restrict expensive multi-output models with `outputs=...`.

Read [references/modalities.md](references/modalities.md) for current examples and output-shape guidance.

## Troubleshooting Order

1. Print Python, SHAP, model-library, NumPy, and framework versions.
2. Verify the model receives exactly the same transformed columns, order, dtype, and missing-value representation used during fitting.
3. Print `values.shape`, `base_values.shape`, `data.shape`, `feature_names`, and `output_names`.
4. Confirm the selected output and output units.
5. Recompute predictions on the same rows in the same order.
6. Test a smaller batch and representative background.
7. Only then investigate package-specific compatibility or approximation settings.

Use [references/troubleshooting.md](references/troubleshooting.md) for additivity failures, shape mismatches, categorical features, pipelines, deep-learning frameworks, plotting, and performance.

## Bundled Script

Run a deterministic, self-contained tabular example that writes importance data, metadata, and plots:

```bash
uv run --no-project --python 3.12 --with "shap[plots]==0.52.0" \
  skills/shap/scripts/tabular_report.py --output-dir /tmp/shap-report
```

The script does not download data or deserialize models. Read it as a template, then replace the built-in dataset and model while preserving output selection and additivity validation.

## Reference Map

| File | Load when |
|---|---|
| [references/explainers.md](references/explainers.md) | Selecting or configuring explainers |
| [references/data-maskers.md](references/data-maskers.md) | Choosing background data, masking semantics, or feature groups |
| [references/plots.md](references/plots.md) | Selecting, composing, or saving visualizations |
| [references/workflows.md](references/workflows.md) | Running audits, comparisons, cohorts, monitoring, or production workflows |
| [references/modalities.md](references/modalities.md) | Explaining text, images, or deep models |
| [references/migration.md](references/migration.md) | Updating legacy SHAP code or supporting older Python |
| [references/theory.md](references/theory.md) | Explaining estimands, guarantees, dependence, interactions, and limitations |
| [references/troubleshooting.md](references/troubleshooting.md) | Diagnosing runtime, shape, additivity, and compatibility problems |

## Primary Sources

- Documentation: https://shap.readthedocs.io/en/latest/
- API reference: https://shap.readthedocs.io/en/latest/api.html
- Release notes: https://shap.readthedocs.io/en/latest/release_notes.html
- Repository: https://github.com/shap/shap
