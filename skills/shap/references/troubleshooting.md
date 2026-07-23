# SHAP Troubleshooting

Diagnose SHAP problems from environment and semantics outward. Do not start by disabling checks or changing tolerances.

## Minimal Diagnostic Packet

Run without printing environment variables:

```python
import importlib.metadata
import platform
from pathlib import Path

import numpy as np
import shap

print("Python:", platform.python_version())
print("SHAP:", shap.__version__)
print("NumPy:", np.__version__)
print("SHAP import path:", Path(shap.__file__).resolve())

for package in [
    "pandas",
    "scikit-learn",
    "xgboost",
    "lightgbm",
    "catboost",
    "tensorflow",
    "keras",
    "torch",
]:
    try:
        print(f"{package}:", importlib.metadata.version(package))
    except importlib.metadata.PackageNotFoundError:
        pass
```

For an explanation:

```python
print("values:", np.shape(explanation.values))
print("base_values:", np.shape(explanation.base_values))
print("data:", np.shape(explanation.data))
print("feature_names:", explanation.feature_names)
print("output_names:", explanation.output_names)
print("model input:", X_eval.shape)
```

Do not include sensitive row values in a public bug report.

## Installation and Import Problems

SHAP 0.52.0 requires Python 3.12+ and NumPy 2+.

```bash
uv run python --version
uv pip show shap
uv pip tree
```

If Python 3.11 is required, pin SHAP 0.51.0. For Python 3.9/3.10, 0.49.1 is the final compatible line; upgrading Python is preferable.

### Wrong module imported

Never name a local script or directory:

- `shap.py`;
- `numpy.py`;
- `pandas.py`;
- `xgboost.py`;
- `lightgbm.py`;
- `joblib.py`;
- `sklearn.py`.

Local files can shadow installed packages. Verify:

```python
from pathlib import Path
import shap

print(Path(shap.__file__).resolve())
```

The path should point into the intended environment's installed package, not the project working directory.

After renaming a shadowing module, remove only its corresponding local `__pycache__` entries and restart Python.

## Shape Problems

### Old list logic fails

Since 0.45, one-input multi-output explainers return an array with outputs last:

```python
class_exp = explanation[..., class_index]
```

Do not use:

```python
class_exp = explanation[class_index]  # selects a sample
```

### Plot expects 2-D values

Select an output:

```python
print(explanation.values.shape)
single_output = explanation[..., output_index]
assert single_output.values.ndim == 2
shap.plots.beeswarm(single_output)
```

### Waterfall expects one row

```python
single_output = explanation[..., output_index]
shap.plots.waterfall(single_output[row_index])
```

### Feature count mismatch

Check:

```python
assert explanation.values.shape[1] == X_eval.shape[1]
assert len(explanation.feature_names) == X_eval.shape[1]
```

Likely causes:

- preprocessing was applied to only one of background/evaluation data;
- columns are reordered;
- one-hot categories differ;
- the model receives a NumPy array while names came from a different DataFrame;
- an identifier/target column was accidentally included.

## Additivity Failures

An additivity failure means the selected SHAP values do not reconstruct the selected output within expected tolerance.

### Diagnostic order

1. Confirm rows and order match.
2. Confirm transformed columns, order, dtype, missingness, and sparse/dense form match model fitting.
3. Confirm model artifact and explainer refer to the same fitted model.
4. Confirm output index and units.
5. Recompute on one row.
6. Use an explicit, representative background.
7. Upgrade/downgrade only after checking model-library compatibility notes.
8. Test a minimal model/dataset reproducer.

Explicit check for one tabular output:

```python
values = np.asarray(explanation.values)
base = np.asarray(explanation.base_values)
reconstructed = base + values.sum(axis=1)

error = reconstructed - expected_output
print("max abs error:", np.max(np.abs(error)))
print("mean abs error:", np.mean(np.abs(error)))
```

### Common output mismatch

For an XGBoost classifier, default TreeExplainer output may be a raw margin:

```python
raw_margin = model.predict(dmatrix, output_margin=True)
```

Comparing raw-margin SHAP reconstruction to `predict_proba` will fail conceptually even if both implementations are correct.

For probability explanations, configure:

```python
explainer = shap.TreeExplainer(
    model,
    data=background,
    feature_perturbation="interventional",
    model_output="probability",
)
```

### Do not immediately disable checks

`check_additivity=False` is appropriate only after:

- identifying a documented numerical or model-library limitation;
- quantifying the discrepancy;
- confirming it is acceptable for the use case;
- recording the decision.

It is not a fix for huge, non-finite, or wrong-unit values.

## Tree Model Problems

### Categorical splits

Support differs across XGBoost, LightGBM, CatBoost, and scikit-learn categorical configurations. SHAP 0.49 added categorical-split support in the C++ library, and 0.52 tightened unsupported categorical handling in GPU/sklearn paths.

If an error mentions categorical splits:

1. capture SHAP and model-library versions;
2. test CPU `TreeExplainer`;
3. test one row;
4. verify model-native prediction works on the same frame;
5. consult the current release notes and open issues.

Do not convert categories to arbitrary integer codes merely to silence the explainer; that can change model semantics.

### Nullable pandas dtypes

SHAP 0.52 fixed a TreeExplainer crash with pandas nullable dtypes. If constrained to an older release, convert only after checking that missing values and category semantics remain identical:

```python
print(X_eval.dtypes)
```

Prefer upgrading within the project's compatibility window.

### Missing values

Verify:

- training and explanation use the same missing-value sentinel;
- background includes realistic missingness;
- the model's default missing branch is preserved;
- CPU/GPU outputs agree on a small fixture.

### Path-dependent NaNs

Small or inconsistent path-dependent backgrounds/model counts can cause failures in older versions. SHAP 0.51 included a path-dependent NaN fix. Reproduce on the latest compatible patch before working around it.

## Pipeline Problems

### DataFrame lost inside callable

A model-agnostic masker may call the model with an array. If the pipeline requires column names:

```python
columns = raw_background.columns.tolist()

def model_fn(array):
    frame = pd.DataFrame(array, columns=columns)
    return pipeline.predict_proba(frame)
```

This is safe only when all columns can be reconstructed without losing categorical dtypes. Prefer a masker/callable path that preserves DataFrames.

### Transformed names are wrong

```python
names = preprocessor.get_feature_names_out()
X_eval_t = preprocessor.transform(X_eval)
assert X_eval_t.shape[1] == len(names)
```

Inspect the transformer version and fitted categories. Do not borrow names from a separately fitted preprocessor.

### Sparse matrices

Model-agnostic explainers can become expensive or densify data. Test memory on a small batch. Keep sparse input only if the selected explainer and model callable support it end to end.

## DeepExplainer Problems

### Unsupported operation / additivity assertion

Likely causes:

- unsupported framework operator;
- multiple outputs not sliced as expected;
- stochastic training mode;
- custom layer;
- model returns a tuple/dictionary;
- background and input structures differ.

PyTorch:

First switch the PyTorch `nn.Module` to evaluation mode with its standard `eval` method. This is a framework state change, not Python's built-in code-evaluation function.

```python
with torch.inference_mode():
    output = model(test_batch)
print(output.shape)
```

If gradients are needed by the explainer, do not wrap the explainer call itself in `torch.inference_mode()`.

Try:

1. a scalar-output wrapper;
2. one input row;
3. a smaller background;
4. `GradientExplainer`;
5. `PartitionExplainer` with a model callable.

Document changed semantics when switching explainers.

### Device mismatch

Ensure model, background, and explained tensors use the same device and compatible dtype:

```python
device = next(model.parameters()).device
background = background.to(device)
to_explain = to_explain.to(device)
```

Move returned values to CPU only after explanation.

### Ranked outputs

`ranked_outputs=k` returns values and indexes:

```python
values, indexes = explainer.shap_values(
    X,
    ranked_outputs=3,
)
```

Use `indexes` to label each row. Do not assume rank one is the same class across rows.

## Text and Image Problems

### Tokenizer mismatch

Use the exact tokenizer revision paired with the model. Check truncation, padding, special tokens, and mask token.

### Image preprocessing mismatch

The model callable must apply the same resize, channel order, range, and normalization used in validation:

```python
def model_fn(images):
    return model(preprocess(images.copy()))
```

### Explanations change drastically with masker

This may be expected. Blur, inpainting, constants, and token masking define different hidden-feature operations. Report a sensitivity analysis instead of selecting one silently.

## Plotting Problems

### Plot does not display

For scripts:

```python
ax = shap.plots.beeswarm(explanation, show=False)
ax.figure.savefig("beeswarm.png", dpi=200, bbox_inches="tight")
plt.close(ax.figure)
```

For JavaScript force plots in notebooks:

```python
shap.plots.initjs()
shap.plots.force(local_exp)
```

Use `matplotlib=True` for a static force plot.

### Overlapping or blank saved plots

Capture and close each figure before creating another:

```python
ax = shap.plots.bar(explanation, show=False)
figure = ax.figure
figure.savefig("bar.png", bbox_inches="tight")
plt.close(figure)
```

### Colors or feature values missing

Check `explanation.data` and `display_data`. Values-only objects cannot color by original feature values.

## Performance Problems

Estimate cost before a large run:

```text
evaluation rows
× model evaluations per row
× background rows per masked evaluation
× model latency
```

Reduce cost in this order:

1. explain a predeclared row subset;
2. restrict outputs;
3. use a specialized explainer;
4. reduce background after convergence testing;
5. batch model calls;
6. reduce permutations/evaluation budget with an accuracy check;
7. use hierarchical partitioning when scientifically defensible.

Do not subset only after viewing which explanations look interesting.

## Serialization Problems

Model and explainer pickle/joblib/cloudpickle artifacts can execute code when loaded. Only load artifacts produced by a trusted pipeline and stored with integrity controls.

For long-lived systems, prefer:

- versioned model registry artifacts;
- immutable background data identifiers;
- code/config that rebuilds the explainer;
- smoke tests for predictions and additivity;
- explicit dependency locks.

Do not accept an uploaded explainer file from an untrusted user.

## Minimal Bug Reproducer

A useful issue report contains:

- package versions;
- platform and Python version;
- minimal synthetic/public data;
- model construction;
- background construction;
- explainer construction;
- one failing row;
- input/output shapes;
- full exception;
- expected model output and reconstructed output.

Remove credentials, environment variables, private paths, and sensitive data.

## Sources

- SHAP release notes: https://shap.readthedocs.io/en/latest/release_notes.html
- TreeExplainer API: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html
- DeepExplainer API: https://shap.readthedocs.io/en/latest/generated/shap.DeepExplainer.html
- Plot API: https://shap.readthedocs.io/en/latest/api.html#plots
- SHAP GitHub issues: https://github.com/shap/shap/issues
