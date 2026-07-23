# SHAP Plotting

This reference uses the SHAP 0.52 plotting API. Prefer `shap.plots.*` functions that consume `shap.Explanation` objects. Legacy functions such as `summary_plot`, `dependence_plot`, and top-level `force_plot` remain relevant to old code but lose metadata and should not anchor a new workflow.

## Validate Before Plotting

For every plot:

```python
print("values:", explanation.values.shape)
print("base_values:", np.shape(explanation.base_values))
print("data:", np.shape(explanation.data))
print("features:", explanation.feature_names)
print("outputs:", explanation.output_names)
```

For multi-output tabular data, select one output:

```python
class_exp = explanation[..., class_index]
# or, when output names are populated:
class_exp = explanation[..., "class_name"]
```

Most tabular plots expect either:

- one local row: `(features,)`; or
- many rows: `(samples, features)`.

Passing `(samples, features, outputs)` without selecting an output is a common source of misleading or failed plots.

## Plot Selection

| Question | Plot | Input |
|---|---|---|
| Which features have the greatest average absolute attribution? | `bar` | multi-row `Explanation` |
| What are the direction, spread, and observed values of attributions? | `beeswarm` | multi-row `Explanation` |
| How does one row move from baseline to output? | `waterfall` | one-row `Explanation` |
| How does attribution vary with a feature value? | `scatter` | one feature column |
| Are there sample-level explanation patterns? | `heatmap` | multi-row `Explanation` |
| How do cohorts compare descriptively? | `bar` | `Cohorts` or dictionary |
| Which tokens or regions contribute? | `text`, `image` | modality-specific `Explanation` |
| Is an interactive additive layout useful? | `force` | one or multiple rows |
| How do cumulative paths differ? | `decision` | arrays plus base value |

No plot proves causality or fairness. A plot is an aggregation of attributions under a model, output, background, and masker.

## Global Bar Plot

```python
ax = shap.plots.bar(
    explanation,
    max_display=20,
    show=False,
)
ax.set_title("Mean absolute SHAP value")
ax.figure.tight_layout()
ax.figure.savefig("shap-bar.png", dpi=200, bbox_inches="tight")
plt.close(ax.figure)
```

A multi-row explanation is aggregated by mean absolute attribution. A single row creates a local bar plot.

### Cohort bar plot

```python
cohorts = explanation.cohorts(group_labels)
ax = shap.plots.bar(cohorts.abs.mean(0), max_display=15, show=False)
ax.figure.savefig("shap-cohorts.png", dpi=200, bbox_inches="tight")
plt.close(ax.figure)
```

Alternatively:

```python
ax = shap.plots.bar(
    {
        "Group A": explanation[group_labels == "A"],
        "Group B": explanation[group_labels == "B"],
    },
    show=False,
)
```

Use one shared explainer and background for direct cohort comparison. Include sample counts and uncertainty; different mean magnitudes can reflect feature distributions, performance, or model behavior.

### Feature clustering

```python
clustering = shap.utils.hclust(X_background, y_background)
ax = shap.plots.bar(
    explanation,
    clustering=clustering,
    clustering_cutoff=0.5,
    show=False,
)
```

`hclust(X, y)` uses outcome-redundancy information and can be expensive. Do not compute it using held-out labels if that would contaminate the analysis.

## Beeswarm Plot

```python
ax = shap.plots.beeswarm(
    explanation,
    max_display=20,
    alpha=0.7,
    s=12,
    group_remaining_features=True,
    show=False,
)
ax.figure.savefig("shap-beeswarm.png", dpi=200, bbox_inches="tight")
plt.close(ax.figure)
```

Current 0.52 controls include:

- `order`: default `explanation.abs.mean(0)`;
- `clustering` and `cluster_threshold`;
- `ax`;
- `log_scale`;
- `color_bar`;
- `s` for marker size;
- `plot_size`;
- `group_remaining_features`.

Interpretation:

- horizontal position: signed attribution in the explained output's units;
- color: observed feature value when numeric display data are available;
- vertical density/jitter: observations, not uncertainty;
- row order: an aggregation rule, not causal importance.

Useful alternatives:

```python
# Highlight features with rare large effects.
shap.plots.beeswarm(
    explanation,
    order=explanation.abs.max(0),
)

# Absolute magnitude only; direction is intentionally removed.
shap.plots.beeswarm(
    explanation.abs,
    color="shap_red",
)
```

Do not interpret red as "risk" or blue as "protective" without first defining output and units.

## Waterfall Plot

```python
ax = shap.plots.waterfall(
    explanation[row_index],
    max_display=15,
    show=False,
)
ax.figure.savefig("shap-waterfall.png", dpi=200, bbox_inches="tight")
plt.close(ax.figure)
```

Input must be one-dimensional. A waterfall shows how values move from the selected background's base value to the selected output for one row.

Report:

- why the row was selected;
- baseline population and value;
- output name and units;
- final model output;
- whether omitted features were grouped.

Never describe the arrows as what would happen if a person changed a feature. They decompose a predictive output; they are not recourse or intervention estimates.

## Scatter Plot

```python
ax = shap.plots.scatter(
    explanation[:, "age"],
    color=explanation[:, "bmi"],
    alpha=0.5,
    x_jitter="auto",
    show=False,
)
ax.figure.savefig("shap-age-scatter.png", dpi=200, bbox_inches="tight")
plt.close(ax.figure)
```

If `color=explanation` is passed, SHAP selects a likely interaction color automatically:

```python
shap.plots.scatter(explanation[:, "age"], color=explanation)
```

Vertical spread at one x-value can arise from:

- interactions;
- correlated features;
- heterogeneous subgroups;
- approximation noise;
- model discontinuities.

It does not by itself prove an interaction or causal effect.

Current scatter features include categorical support, automatic jitter, percentile axis limits, a histogram, one-feature `ax` support, and overlay curves:

```python
shap.plots.scatter(
    explanation[:, "age"],
    xmin="percentile(1)",
    xmax="percentile(99)",
    hist=True,
)
```

## Heatmap

```python
subset = explanation[:200]
ax = shap.plots.heatmap(
    subset,
    max_display=20,
    instance_order=subset.sum(1),
    show=False,
)
ax.figure.savefig("shap-heatmap.png", dpi=200, bbox_inches="tight")
plt.close(ax.figure)
```

Heatmaps are useful for sample-level patterns but can invite over-interpretation of visual clusters. Record:

- row sampling and ordering;
- any clustering method;
- output and baseline;
- whether colors share a fixed scale across panels.

Use a subset for readability, but choose it before viewing explanations or document the selection rule.

## Violin Plot

```python
shap.plots.violin(
    explanation.values,
    features=explanation.data,
    feature_names=explanation.feature_names,
    max_display=20,
)
```

The violin API retains array-oriented parameters. Prefer beeswarm for the richest modern `Explanation` workflow; use violin when density is more important than individual points.

## Force Plot

The current API recommends passing an `Explanation`:

```python
shap.plots.force(explanation[row_index])
```

This returns a JavaScript visualization by default. Initialize notebook JavaScript if required:

```python
shap.plots.initjs()
```

For a static local plot:

```python
shap.plots.force(
    explanation[row_index],
    matplotlib=True,
    show=False,
)
plt.gcf().savefig("shap-force.png", dpi=200, bbox_inches="tight")
plt.close(plt.gcf())
```

Use `link="logit"` only as a display transform when the additive values are in log-odds. It does not recompute probability-space SHAP values.

Stacked force plots can accept multiple rows but become hard to audit. Prefer heatmaps or cohort summaries for large samples.

## Decision Plot

Decision plots retain an array-oriented API:

```python
shap.plots.decision(
    base_value,
    values,
    features=X_display,
    feature_names=feature_names,
    highlight=highlight_rows,
    show=False,
)
```

Before plotting, select one output and ensure a compatible scalar base value. Use decision plots for cumulative path comparison, not as a default multiclass plot.

## Text Plot

```python
shap.plots.text(text_explanation)
```

For multi-output text:

```python
class_text = text_explanation[..., "anger"]
shap.plots.text(class_text)
```

Token merging and tokenizer special tokens affect presentation. Preserve the tokenizer and masker configuration.

## Image Plot

```python
shap.plots.image(image_explanation)
```

Legacy examples may use `shap.image_plot`; prefer `shap.plots.image` for current code. Select only the outputs that were actually explained and label them explicitly.

Image overlays show attribution under a masking method; they are not object localization or segmentation ground truth.

## Group Difference and Monitoring

`shap.plots.group_difference` plots differences in mean SHAP values between two groups. It is descriptive and should be paired with confidence intervals or resampling when decisions depend on the difference.

`shap.plots.monitoring` visualizes attribution behavior over an ordered axis. For production drift, store numeric summaries and statistical checks as the source of truth; use the plot as a diagnostic.

## Saving Figures Reliably

Most modern matplotlib-backed plots return an `Axes` when `show=False`:

```python
def save_axes(ax, path):
    figure = ax.figure
    figure.tight_layout()
    figure.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(figure)
```

If a plot does not return an axis, capture the current figure immediately:

```python
shap.plots.heatmap(explanation, show=False)
figure = plt.gcf()
figure.savefig("plot.png", dpi=200, bbox_inches="tight")
plt.close(figure)
```

Do not call another plotting function before capturing the figure.

## Publication and Accessibility

- Put output units in the x-axis label or caption.
- Define the baseline population in the caption.
- Include sample size and aggregation.
- Use direct labels in addition to color.
- Avoid red/green-only encodings.
- Keep consistent axis limits for panels intended for comparison.
- Export vector formats (`.svg` or `.pdf`) when journal workflows allow.
- Do not expose identifiers or sensitive raw values in local plot labels.

## Common Failures

### "Waterfall requires a scalar explanation"

Select one row and one output:

```python
shap.plots.waterfall(explanation[row_index, ..., output_index])
```

For tabular data, the clearer sequence is:

```python
class_exp = explanation[..., output_index]
shap.plots.waterfall(class_exp[row_index])
```

### Missing feature names

Use a DataFrame through preprocessing where possible, or pass `feature_names` when creating the explainer. Verify order before assigning names manually.

### No colors in beeswarm

Color requires usable feature data in `explanation.data` or `display_data`. An explanation built from values alone cannot recover original feature values.

### Figures overlap in loops

Use `show=False`, save the returned axis/figure, and close it every iteration.

### Plot and prediction disagree

Check output selection and units. For example, raw XGBoost margins are not probabilities. Reconstruct the exact explained output before changing plot settings.

## Sources

- Plot API: https://shap.readthedocs.io/en/latest/api.html#plots
- Beeswarm: https://shap.readthedocs.io/en/latest/generated/shap.plots.beeswarm.html
- Bar: https://shap.readthedocs.io/en/latest/generated/shap.plots.bar.html
- Waterfall: https://shap.readthedocs.io/en/latest/generated/shap.plots.waterfall.html
- Scatter: https://shap.readthedocs.io/en/latest/generated/shap.plots.scatter.html
- Force: https://shap.readthedocs.io/en/latest/generated/shap.plots.force.html
- Plot examples: https://shap.readthedocs.io/en/latest/api_examples.html#plots
