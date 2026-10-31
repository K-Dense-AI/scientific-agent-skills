# SHAP Explainers

This reference targets SHAP 0.52.0. Prefer the callable interface (`explanation = explainer(X)`) so results retain values, baselines, data, feature names, and output names in a `shap.Explanation`.

## Selection Checklist

Before choosing an explainer, answer:

1. What exact callable or model output is being explained?
2. Is the model natively supported by a specialized explainer?
3. What does "missing" mean for each input feature?
4. Are features independent, correlated, grouped, sequential, or spatial?
5. How many model evaluations are affordable per row?
6. Is the output scalar or multi-output?
7. Is an exact result required under the chosen game, or is a sampled estimate acceptable?

## Recommended Decision Path

| Model/input | First choice | Alternative | Main risk |
|---|---|---|---|
| Supported tree ensemble | `TreeExplainer` | `GPUTreeExplainer` (experimental) | Output units and feature-dependence semantics |
| Linear model | `LinearExplainer` | `ExactExplainer` | Correlation assumptions |
| Small tabular feature set | `ExactExplainer` | `PermutationExplainer` | Exponential cost without a partition tree |
| General tabular callable | `PermutationExplainer` | `PartitionExplainer`, `KernelExplainer` | Evaluation cost and off-manifold masks |
| Hierarchically grouped inputs | `PartitionExplainer` | `PermutationExplainer` with `Partition` masker | Attributions are Owen values for the constrained game |
| Differentiable TensorFlow/PyTorch model | `DeepExplainer` or `GradientExplainer` | `PartitionExplainer` | Operator support, background, and output shape |
| Text or image callable | `PartitionExplainer` with domain masker | Framework-specific deep explainer | Masking semantics dominate interpretation |

## `shap.Explainer`

`shap.Explainer` combines a model, masker, link, and algorithm. With `algorithm="auto"`, it returns a compatible specialized subclass.

```python
explainer = shap.Explainer(
    model,
    masker=background,
    algorithm="auto",
    output_names=output_names,
    feature_names=feature_names,
    seed=7,
)
explanation = explainer(X_eval)
```

The 0.52.0 selector advertises `auto`, `permutation`, `partition`, `tree`, `linear`, `deep`, `exact`, and `additive`. However, its `algorithm="deep"` dispatch forwards unsupported keywords to `DeepExplainer` and raises `TypeError`; construct `shap.DeepExplainer(model, background)` directly. `auto` is not a general framework detector.

Use the auto-selector when:

- the model/masker pair is conventional;
- default output semantics are acceptable;
- no algorithm-specific parameter is needed.

Instantiate the specialized class when:

- tree `model_output` or `feature_perturbation` must be explicit;
- a particular approximation or evaluation budget is part of the analysis;
- a framework-specific deep model requires a precise input/layer form.

Passing a background matrix is shorthand for a standard tabular masker. Prefer an explicit masker when its semantics need to appear in an audit record.

## `TreeExplainer`

Common constructor arguments (the deprecated `approximate` parameter and unused link controls are intentionally omitted):

```python
shap.TreeExplainer(
    model,
    data=None,
    model_output="raw",
    feature_perturbation="auto",
    feature_names=None,
)
```

Supported families include XGBoost, LightGBM, CatBoost, PySpark trees, and most scikit-learn tree models. Support varies by model version and categorical configuration, so test a small batch after dependency changes.

### Feature perturbation

`feature_perturbation` defines how hidden features are integrated:

- `"interventional"` requires background data. Runtime scales approximately linearly with background size.
- `"tree_path_dependent"` uses training counts stored in tree leaves and does not require a separate background.
- `"auto"` uses interventional semantics when `data` is supplied and tree-path-dependent semantics otherwise. This has been the default since 0.47.

These options answer different questions and can allocate credit differently for dependent features. Neither turns an ordinary predictive model into a causal model.

### Output space

`model_output` can be:

- `"raw"`: model-specific raw tree output;
- `"probability"`: transformed probability output;
- `"log_loss"`: a model-specific loss transform; for supported binary margin models this is negative log likelihood, while squared-error objectives use squared loss;
- a supported model method name such as `"predict_proba"`.

`"probability"` and `"log_loss"` currently require `feature_perturbation="interventional"` and background data.

Raw output is model-dependent:

- regression commonly uses the predicted target value;
- XGBoost binary classification commonly uses a margin/log-odds value;
- scikit-learn tree classifiers commonly expose one probability output per class.

Always inspect shape and verify the additive reconstruction against the exact model output.

### Calling and validation

```python
explainer = shap.TreeExplainer(
    model,
    data=background,
    feature_perturbation="interventional",
    model_output="probability",
)
all_outputs = explainer(X_eval)
class_exp = all_outputs[..., class_index]

reconstructed = class_exp.base_values + class_exp.values.sum(axis=1)
expected = model.predict_proba(X_eval)[:, class_index]
np.testing.assert_allclose(reconstructed, expected, rtol=1e-5, atol=1e-6)
```

The built-in tree additivity check applies to raw output paths; explicitly validate probability and loss reconstructions. Loss baselines can be label-dependent callables: see the concrete loss workflow in [workflows.md](workflows.md). A bare DataFrame background is capped at 100 rows; retain a larger selected sample with `data=shap.maskers.Independent(background, max_samples=len(background))` and record the effective size.

### Approximate tree values

Do not pass `approximate` to the constructor. If the speed/quality trade-off is intentional:

```python
approx_exp = explainer(X_eval, approximate=True)
```

This uses a single-ordering approximation associated with Saabas values. It does not retain the consistency guarantee of Tree SHAP and can over-weight lower tree splits. Label the result as approximate.

### Interaction values

Use a separate **raw, tree-path-dependent** explainer for supported tree interactions:

```python
interaction_explainer = shap.TreeExplainer(
    model, feature_perturbation="tree_path_dependent", model_output="raw",
)
interaction = interaction_explainer.shap_interaction_values(X_eval)
ordinary = interaction_explainer(X_eval)
np.testing.assert_allclose(interaction.sum(axis=2), ordinary.values, atol=1e-6)
```

Probability/log-loss explainers reject interaction calls. The interventional C++ path does not implement interactions and can emit zeros with a warning; never interpret those as absent interactions. Compare against ordinary values from this same path-dependent game, not an earlier interventional explanation. Each symmetric off-diagonal cell carries half the pair contribution.

Shapes:

- one output: `(samples, features, features)`;
- multiple outputs: `(samples, features, features, outputs)`.

Since 0.45, multiple outputs use a NumPy array rather than a list. Interaction computation can be much larger than ordinary explanations; subset rows and features deliberately.

### GPU tree explainer

`GPUTreeExplainer` is experimental and requires a source build with CUDA support. Validate parity against CPU `TreeExplainer`, especially for missing values, multiclass baselines, and categorical splits.

## `LinearExplainer`

Use for linear or logistic models:

```python
masker = shap.maskers.Independent(background)
explainer = shap.LinearExplainer(model, masker)
explanation = explainer(X_eval)
```

With independent/interventional masking, a linear attribution is related to:

```text
coefficient_i * (x_i - reference_mean_i)
```

For correlation-aware allocation, use an `Impute` masker:

```python
masker = shap.maskers.Impute(background, method="linear")
explainer = shap.LinearExplainer(model, masker)
```

For logistic regression, these linear attributions reconstruct `model.decision_function(X_eval)` in log-odds units, not `predict_proba` or predicted class labels. Explain a probability callable with a model-agnostic method when probability-space attribution is required.

Correlation-aware values share credit among correlated inputs and can assign attribution to a feature that the fitted model does not directly use. This is a property of the conditional game, not evidence of a direct model coefficient or causal effect. SHAP 0.52 warns when the estimated covariance matrix is singular.

## `ExactExplainer`

`ExactExplainer` enumerates coalitions with optimizations:

```python
masker = shap.maskers.Independent(background)
explainer = shap.ExactExplainer(model_fn, masker)
explanation = explainer(X_eval)
```

Use it for:

- small feature spaces;
- correctness checks against an approximate explainer;
- partition games where the hierarchy sharply reduces evaluation cost.

Avoid it for unconstrained high-dimensional inputs.

## `PermutationExplainer`

`PermutationExplainer` is the general modern model-agnostic default:

```python
masker = shap.maskers.Independent(background, max_samples=100)
explainer = shap.PermutationExplainer(
    model_fn,
    masker,
    feature_names=feature_names,
    seed=7,
)

minimum_budget = 2 * len(feature_names) + 1
explanation = explainer(
    X_eval,
    max_evals=minimum_budget * 10,
    error_bounds=True,
)
```

One forward/reverse pass guarantees additivity and is exact for models with interactions no higher than second order. Repeating random permutations improves estimates for higher-order interactions.

Cost scales with:

- evaluation rows;
- feature count;
- number of permutations;
- background rows;
- model latency.

Batch the model callable where possible. Preserve the seed and budget. `error_bounds=True` estimates variation across sampled paths; it is not a confidence interval for model correctness or biological effects.

## Links and output units

For a probability callable, a supported model-agnostic link changes the additive units:

```python
explainer = shap.Explainer(
    probability_fn, background, algorithm="permutation",
    link=shap.links.logit, seed=7,
)
exp = explainer(X_eval, max_evals=(2 * X_eval.shape[1] + 1) * 5)
np.testing.assert_allclose(
    exp.base_values + exp.values.sum(axis=1),
    shap.links.logit(probability_fn(X_eval)), atol=1e-6,
)
```

This fragment assumes a scalar probability strictly between 0 and 1. Check finiteness on masked inputs too; exact endpoints make log-odds infinite. With default link linearization, the baseline is `logit(mean(background probabilities))`, not the mean background logit. Record `linearize_link`; applying a link inside the model callable defines a different game. This is distinct from the force plot's display-only link. `TreeExplainer`'s link constructor arguments are unused in 0.52.0; configure its supported `model_output` instead.

## `PartitionExplainer`

`PartitionExplainer` follows a hierarchical clustering of input features:

```python
masker = shap.maskers.Partition(
    background,
    max_samples=100,
    clustering="correlation",
)
explainer = shap.PartitionExplainer(
    model_fn,
    masker,
    output_names=output_names,
)
explanation = explainer(X_eval, max_evals=1000)
```

With a partition tree, the values are Owen values for a constrained cooperative game. This is useful when:

- groups should enter a coalition together;
- correlated tabular inputs should be organized hierarchically;
- tokens or image regions have natural structure;
- unconstrained exact enumeration is too expensive.

Do not call partition values equivalent to unconstrained Shapley values without noting the changed game.

## `KernelExplainer`

Kernel SHAP fits a weighted linear surrogate over sampled coalitions:

```python
explainer = shap.KernelExplainer(
    model_fn,
    background,
    link="identity",
    feature_names=feature_names,
)
legacy_values = explainer.shap_values(
    X_eval, nsamples="auto", l1_reg="num_features(10)",
)
```

Use it when:

- maintaining a validated Kernel SHAP analysis;
- a specific identity/logit link behavior is required;
- another explainer cannot represent the model/masker combination.

`KernelExplainer(X)` also returns an `Explanation`, but its 0.52.0 call signature only exposes `l1_reg` and `silent`; use `.shap_values(..., nsamples=...)` for an explicit sampling budget. The default `l1_reg="num_features(10)"` selects at most ten features (changed in 0.47), so omitted features are not evidence of zero model use. Choose and record regularization; `l1_reg=0` removes this selection when the sampled system is sufficiently determined.

For new general tabular work, consider `PermutationExplainer` for its direct evaluation-budget control.

Kernel SHAP can be slow and may create unrealistic masked samples. Summarizing background data changes the estimand as well as runtime.

## `DeepExplainer`

Deep SHAP approximates attributions for supported differentiable TensorFlow and PyTorch models.

Before constructing a PyTorch explainer, switch the `nn.Module` to evaluation mode using its standard `eval` method. This is a PyTorch state change, not Python's built-in code-evaluation function.

PyTorch:

```python
explainer = shap.DeepExplainer(model, background_tensor)
values = explainer.shap_values(test_tensor)
```

TensorFlow/Keras:

```python
explainer = shap.DeepExplainer(model, background_array)
values = explainer.shap_values(test_array)
```

Model forms:

- TensorFlow: a model, or an `(inputs, output)` tensor pair with a single-dimensional output;
- PyTorch: an `nn.Module`, or `(model, layer)` to attribute the selected layer's input.

Background cost is linear in sample count. Official guidance describes roughly 100 samples as a useful estimate and 1000 as a more accurate but costlier estimate; test convergence for the actual model.

Output shapes since 0.45:

- one input, one output: inspect for `(samples, *input_shape)` **or a final singleton output axis**; the 0.52.0 PyTorch Deep implementation stacks even a single output;
- one input, multiple outputs: `(samples, *input_shape, outputs)`;
- multiple inputs: a list, one array per input.

Pass `ranked_outputs=k` to `.shap_values(...)`, not the constructor. It returns both values and selected output indexes. Never assume a binary model returns a two-element list.

For PyTorch, return `(batch, outputs)`, including `(batch, 1)` for a scalar-output wrapper; a squeezed `(batch,)` result fails the Deep backend's output-axis handling. Deep explainers support only known operators and architecture patterns. Additivity failures can indicate unsupported operations rather than a tolerance problem.

## `GradientExplainer`

`GradientExplainer` implements expected gradients, an extension of integrated gradients:

```python
explainer = shap.GradientExplainer(
    model,
    background_tensor,
    batch_size=50,
    local_smoothing=0,
)
values = explainer.shap_values(test_tensor, nsamples=200, rseed=7)
```

Use it when:

- the model is differentiable;
- DeepExplainer lacks an operator rule;
- expected-gradients semantics are appropriate.

It remains an approximation. Report `nsamples`, seed, background, and any smoothing.

## Other Public Explainers

- `AdditiveExplainer`: first-order additive models with an `Independent` masker; do not use for models containing interaction terms.
- `SamplingExplainer`: Shapley sampling/IME-style approximation; mainly relevant to existing workflows.
- `CoalitionExplainer`: custom coalition-tree workflows using Winter (recursive Owen) values; its `partition_tree` contract is separate from `PartitionExplainer`, and text/image inputs are not implemented. Treat a new application as illustrative until checked against 0.52.0 source and a tiny known game.
- `shap.explainers.other.*`: wrappers and diagnostic baselines, not the default for a SHAP audit.

## Multi-Output Handling

Modern tabular explanations normally put outputs on the final axis:

```python
print(explanation.values.shape)
print(explanation.output_names)

one_output = explanation[..., output_index]
# If output_names were supplied:
one_output = explanation[..., list(explanation.output_names).index("output_name")]
```

In 0.52.0, `Explainer(..., algorithm="permutation", output_names=...)` may discard those names during subclass dispatch. Set `explanation.output_names` from the verified model mapping after checking output count. Avoid ellipsis plus a string index, which can raise `IndexError`; resolve the name to an integer as above.

For ranked deep outputs, use the returned indexes; they can differ by sample.

Do not:

- use `explanation[output_index]` to select a class (that selects a row);
- average signed values across outputs;
- compare output magnitudes in different units;
- pass a 3-D multi-output tabular explanation directly to a plot requiring `(samples, features)`.

## Sources

- Explainer API: https://shap.readthedocs.io/en/latest/generated/shap.Explainer.html
- TreeExplainer: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html
- PermutationExplainer: https://shap.readthedocs.io/en/latest/generated/shap.PermutationExplainer.html
- PartitionExplainer: https://shap.readthedocs.io/en/latest/generated/shap.PartitionExplainer.html
- DeepExplainer: https://shap.readthedocs.io/en/latest/generated/shap.DeepExplainer.html
- API reference: https://shap.readthedocs.io/en/latest/api.html

- Released source / upstream contract: https://github.com/shap/shap/blob/v0.52.0/shap/explainers/_explainer.py
- Released source / upstream contract: https://github.com/shap/shap/blob/v0.52.0/shap/explainers/_kernel.py
- Released source / upstream contract: https://github.com/shap/shap/blob/v0.52.0/shap/explainers/_tree.py
