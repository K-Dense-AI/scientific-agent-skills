# Text, Images, and Deep Models

Structured inputs require structured maskers. Token deletion, image inpainting, and neural-network reference activations define different explanation games; do not reduce them to ordinary independent tabular columns without justification.

## General Pattern

1. Define a batched model callable with named outputs.
2. Choose a masker that produces valid model inputs.
3. Restrict outputs and evaluation rows before expensive computation.
4. Inspect result shapes.
5. Validate output reconstruction when the explainer supports it.
6. Run masking and baseline sensitivity checks.

```python
explainer = shap.Explainer(
    model_fn,
    masker,
    output_names=output_names,
    seed=7,
)
explanation = explainer(
    inputs,
    max_evals=evaluation_budget,
    outputs=selected_outputs,
)
```

## Text Classification

Use the model's tokenizer:

```python
masker = shap.maskers.Text(tokenizer)
explainer = shap.Explainer(
    model_fn,
    masker,
    algorithm="partition",
    output_names=class_names,
    seed=7,
)

all_outputs = explainer(texts)
class_exp = all_outputs[..., class_index]
shap.plots.text(class_exp)
```

The model callable should accept a batch of strings and return a 2-D numeric array `(batch, outputs)`.

```python
def model_fn(text_batch):
    encoded = tokenizer(
        list(text_batch),
        padding=True,
        truncation=True,
        return_tensors="pt",
    ).to(device)

    with torch.inference_mode():
        logits = model(**encoded).logits

    return logits.detach().cpu().numpy()
```

Decide whether to explain:

- logits/log-odds, where additive evidence is often easier to interpret;
- probabilities, which stakeholders may understand but couple classes through normalization;
- another scalar score.

State the choice in every plot.

### Transformers pipelines

SHAP provides `shap.models.TransformersPipeline`:

```python
wrapped = shap.models.TransformersPipeline(
    classifier_pipeline,
    rescale_to_logits=True,
)
masker = shap.maskers.Text(classifier_pipeline.tokenizer)
explainer = shap.Explainer(wrapped, masker, algorithm="partition")
explanation = explainer(texts)
```

`rescale_to_logits=True` changes the explained output. Do not compare these values directly with probability-space explanations.

### Text masking choices

Check:

- tokenizer special tokens;
- subword splitting;
- mask token;
- whether consecutive masked tokens are collapsed;
- maximum sequence length and truncation;
- normalization and whitespace behavior;
- language-specific token boundaries.

SHAP can merge tokens hierarchically for display. A displayed phrase attribution may be a grouped coalition, not the sum from an independent-token game.

### Generative and sequence-to-sequence models

SHAP includes model wrappers such as:

- `TeacherForcing`;
- `TextGeneration`;
- `TopKLM`.

Generation explanations are target- and decoding-dependent. Record:

- generated or fixed target sequence;
- teacher-forcing setup;
- decoding parameters;
- top-k output selection;
- tokenizer/model revision.

Do not describe one generation explanation as a general explanation of the language model.

## Image Classification

`shap.maskers.Image` requires OpenCV (`cv2`), which is not installed by the `plots` extra. Add an OpenCV build compatible with the project's platform and dependency lock before using image maskers.

Wrap preprocessing inside the model callable so masked images receive the same transformations:

```python
def image_model_fn(image_batch):
    prepared = preprocess(image_batch.copy())
    return model(prepared)
```

Choose an image masker:

```python
masker = shap.maskers.Image(
    "inpaint_telea",
    shape=image_shape,
)

explainer = shap.Explainer(
    image_model_fn,
    masker,
    output_names=class_names,
    seed=7,
)

explanation = explainer(
    images,
    max_evals=500,
    batch_size=50,
    outputs=shap.Explanation.argsort.flip[:3],
)

shap.plots.image(explanation)
```

The current constructor also accepts blur specifications or constant mask values. Compare plausible alternatives:

```python
inpaint = shap.maskers.Image("inpaint_telea", image_shape)
blur = shap.maskers.Image("blur(32,32)", image_shape)
zero = shap.maskers.Image(0, image_shape)
```

These answer different questions:

- inpainting replaces a region using nearby pixels;
- blur removes high-frequency detail while retaining coarse structure;
- a constant value creates a fixed visual baseline.

None guarantees an in-distribution counterfactual.

### Output selection

Image classifiers may have thousands of outputs. Use:

```python
outputs=shap.Explanation.argsort.flip[:k]
```

The selected outputs can vary by row. Preserve `output_indexes`/`output_names` and never assume position zero refers to the same class for every image when ranked outputs are used.

### Interpreting image overlays

Attribution overlays:

- explain a model score under a region-masking game;
- do not identify objects with segmentation accuracy;
- do not prove the model "looked at" a region causally;
- can change with resize, crop, normalization, and masker.

Test:

- multiple maskers;
- nearby images/augmentations;
- different evaluation budgets;
- class-output selection;
- consistency with predictive errors.

## PyTorch Deep Models

Before constructing the explainer, switch the PyTorch `nn.Module` to evaluation mode with its standard `eval` method. This disables training behavior such as dropout; it is not Python's built-in code-evaluation function.

```python
background = training_tensor[background_indices].to(device)
to_explain = test_tensor[:batch_size].to(device)

explainer = shap.DeepExplainer(model, background)
values = explainer.shap_values(to_explain, check_additivity=True)
```

For layer-input attribution:

```python
explainer = shap.DeepExplainer(
    (model, model.feature_extractor.target_layer),
    background,
)
```

Requirements:

- model inputs match background tensor structure;
- output is scalar per row or the multi-output shape is handled explicitly;
- all relevant operations have supported attribution rules;
- dropout/batch normalization are in inference mode.

Do not disable `check_additivity` merely to suppress unsupported-operation failures.

## TensorFlow/Keras Deep Models

```python
background = X_train[background_indices]
to_explain = X_test[:batch_size]

explainer = shap.DeepExplainer(model, background)
values = explainer.shap_values(to_explain, check_additivity=True)
```

SHAP 0.46 added NumPy 2, Keras 3, and TensorFlow 2.16 compatibility. Later versions may still have architecture-specific limitations. Verify installed TensorFlow/Keras versions against SHAP release notes and test a minimal batch.

For graph-specific use, TensorFlow may accept an `(input_tensors, output_tensor)` pair. The selected output tensor should be one-dimensional per sample.

## `GradientExplainer`

Expected gradients can be an alternative when DeepExplainer lacks an operator rule:

```python
explainer = shap.GradientExplainer(
    model,
    background,
    batch_size=50,
    local_smoothing=0,
)
values = explainer.shap_values(
    to_explain,
    nsamples=200,
    rseed=7,
)
```

Report:

- background;
- `nsamples`;
- seed;
- smoothing;
- selected output;
- whether values were stable at a larger sample count.

## Output Shapes

Since SHAP 0.45:

- one input, one output: `(samples, *input_shape)`;
- one input, multiple outputs: `(samples, *input_shape, outputs)`;
- multiple inputs: a list with one array per model input.

For `DeepExplainer(ranked_outputs=k)`, the return is `(values, indexes)`. The indexes tell which outputs were selected for each row.

Always inspect rather than branch on a remembered version:

```python
if isinstance(values, list):
    print([value.shape for value in values])
else:
    print(values.shape)
```

## Genomics and Other Sequences

Define the attribution unit:

- nucleotide or amino acid;
- one-hot channel;
- k-mer;
- motif;
- position window;
- assay channel.

Independent one-hot channels can create invalid bases. Prefer a masker or grouping that preserves valid sequence states. For motif-level claims, aggregate or test motifs explicitly and validate across background sequences.

For genomic models, background choice can represent:

- genomic distribution;
- dinucleotide-shuffled controls;
- matched GC/content cohorts;
- experimentally defined controls.

Each implies a different baseline and scientific question.

## Multiple Inputs

For models with multiple inputs, use a compatible list/composite masker or framework explainer:

```python
values = deep_explainer.shap_values([input_a, input_b])
```

Do not sum values across inputs unless they share the same additive output and the aggregation is documented. Keep names and shapes per input.

## Performance

- Explain a small, predeclared row subset first.
- Restrict outputs.
- Batch model calls.
- Keep background modest and test convergence.
- Increase `max_evals`/`nsamples` only after validating shape and semantics.
- Measure peak accelerator memory.
- Avoid silently falling back to CPU.

Approximation variance and model stochasticity are different. Put the model in deterministic inference mode before estimating explainer variability.

## Privacy

Text and image plots can reproduce sensitive input content. Before export:

- redact direct identifiers;
- avoid embedding full clinical notes or faces when unnecessary;
- separate row identifiers from plot artifacts;
- restrict report access;
- review HTML/JavaScript force or text outputs for embedded raw values.

## Sources

- Text examples: https://shap.readthedocs.io/en/latest/text_examples.html
- Image examples: https://shap.readthedocs.io/en/latest/image_examples.html
- Genomic examples: https://shap.readthedocs.io/en/latest/genomic_examples.html
- Text masker: https://shap.readthedocs.io/en/latest/generated/shap.maskers.Text.html
- Image masker: https://shap.readthedocs.io/en/latest/generated/shap.maskers.Image.html
- DeepExplainer: https://shap.readthedocs.io/en/latest/generated/shap.DeepExplainer.html
- GradientExplainer: https://shap.readthedocs.io/en/latest/generated/shap.GradientExplainer.html
- TransformersPipeline: https://shap.readthedocs.io/en/latest/generated/shap.models.TransformersPipeline.html
