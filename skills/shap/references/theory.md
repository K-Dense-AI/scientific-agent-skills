# SHAP Theory and Interpretation

SHAP applies Shapley-style credit allocation to model explanations. The numerical result is defined by more than the fitted model: it also depends on the model output, background distribution, masking rule, and any coalition constraints.

## Additive Explanation

For one scalar model output and one row `x`, SHAP constructs an additive decomposition:

```text
f_explained(x) = base_value + sum_i phi_i(x)
```

- `f_explained` is the exact output selected for explanation.
- `base_value` is the expected output under the explainer's reference game.
- `phi_i` is the attribution assigned to feature `i`.

For modern tabular `shap.Explanation` objects:

```python
reconstructed = explanation.base_values + explanation.values.sum(axis=1)
```

The equation is meaningful only when the output units are known. A raw margin, probability, log loss, and logit are different quantities.

## Cooperative-Game Formulation

Let `F` be the set of features and `v(S)` the value assigned to coalition `S`. A Shapley value for feature `i` is:

```text
phi_i =
  sum over S subset of F \ {i}
  [ |S|! (|F|-|S|-1)! / |F|! ]
  * [v(S union {i}) - v(S)]
```

This averages the marginal contribution of `i` over all feature orderings.

In machine learning, defining `v(S)` is the hard part because a model normally requires all inputs. The masker and background distribution specify how hidden features are integrated or imputed.

## What the Axioms Mean

Classic Shapley values satisfy:

- **Efficiency:** all feature values sum to the coalition payoff difference.
- **Symmetry:** interchangeable players receive equal credit.
- **Dummy/null player:** a player with no marginal contribution receives zero.
- **Additivity:** values for combined games are sums of values for component games.

The SHAP paper describes related properties for additive feature-attribution methods:

- **Local accuracy:** the additive explanation reconstructs the selected output.
- **Missingness:** absent simplified inputs receive zero attribution under the formulation.
- **Consistency:** if a feature's marginal contribution increases for every coalition, its attribution does not decrease.

These are mathematical allocation properties. They do **not** mean:

- ethical or legal fairness;
- causal correctness;
- robustness to distribution shift;
- truthfulness of the fitted model;
- stability under a different background or masker.

Avoid calling SHAP values "fair" without specifying that the term refers only to a cooperative-game allocation axiom.

## The Value Function Is Part of the Result

Common tabular games include:

### Marginal/interventional game

Hidden features are sampled from a background distribution independently of the observed features.

Conceptually:

```text
v(S) = E_background[f(x_S, X_not_S)]
```

Advantages:

- clear reference population;
- preserves the dummy property with respect to direct model use;
- straightforward model-agnostic masking.

Limitations:

- can evaluate unrealistic combinations;
- can be sensitive to the selected background;
- "interventional" in the API name does not make the resulting predictive explanation a causal effect.

### Conditional game

Hidden features are drawn from a distribution conditional on observed features:

```text
v(S) = E[f(X) | X_S = x_S]
```

Advantages:

- can stay closer to the observed data manifold;
- incorporates statistical dependence.

Limitations:

- requires estimating conditional distributions;
- can assign credit to a feature the model does not directly use;
- dependence can be mistaken for causation;
- estimates can be unstable in sparse regions.

### Partitioned game

Only coalitions compatible with a hierarchy are considered. The resulting allocations are Owen values.

Advantages:

- respects semantic or statistical groups;
- makes structured high-dimensional problems more tractable;
- reduces arbitrary competition among related features.

Limitation: the hierarchy is an assumption and changes the game.

There is no universal answer to "the SHAP value" without specifying the game.

## Background and Baseline

The base value is the reference-game expectation, not automatically:

- the overall target mean;
- the model intercept;
- class prevalence;
- a neutral patient/customer;
- a decision threshold.

Different backgrounds can change:

- base values;
- signed local attributions;
- mean absolute global rankings;
- cohort comparisons.

Treat background sensitivity as a substantive analysis, not just a runtime check.

## Output Scale

SHAP values use the additive scale selected by the explainer.

Examples:

- regression prediction in target units;
- binary tree margin in log-odds;
- class probability;
- per-row log loss;
- transformed output under a link function.

A display transform such as `link="logit"` on a force plot changes labels, not the computed SHAP game. If probability-space additivity is required for supported trees, configure `TreeExplainer(model_output="probability", feature_perturbation="interventional", data=...)`.

Do not compare mean absolute SHAP magnitudes across models or outputs on different scales.

## Local and Global Quantities

Local attribution:

```text
phi_i(x)
```

Global mean absolute attribution:

```text
E_x[abs(phi_i(x))]
```

Mean absolute attribution:

- discards direction;
- depends on the evaluated sample distribution;
- is not normalized predictive performance;
- is not a causal effect size.

Mean signed attribution can cancel heterogeneous effects. Plot the distribution before summarizing.

## Exact and Approximate Algorithms

Unconstrained exact Shapley computation grows exponentially with feature count. SHAP uses model-specific algorithms or sampling:

- **Tree SHAP:** exploits tree structure and is exact for the selected tree game.
- **Linear SHAP:** closed-form or transformation-based allocation for supported linear games.
- **ExactExplainer:** optimized enumeration for small or hierarchically constrained inputs.
- **PermutationExplainer:** averages forward/reverse feature orderings.
- **KernelExplainer:** estimates values through a weighted linear regression over coalitions.
- **DeepExplainer:** combines DeepLIFT-style rules with multiple background samples.
- **GradientExplainer:** uses expected gradients.
- **PartitionExplainer:** exploits a coalition hierarchy.

"Exact" always means exact under a specified output, background, masker, and coalition game.

## Interaction Values

Tree SHAP can decompose attribution into a symmetric interaction matrix.

For one row:

- diagonal entries are main effects;
- off-diagonal entries are pairwise interaction allocations;
- each row sums to that feature's ordinary SHAP value;
- the full matrix sums to the prediction difference from baseline.

```python
interaction = explainer.shap_interaction_values(X_eval)
```

An interaction value describes non-additivity in the fitted model under the chosen game. It does not prove biological, physical, or causal interaction.

Scatter-plot vertical dispersion is only a clue; compute or test interactions before labeling them.

## Correlation and Credit Sharing

When two features contain similar information, multiple allocations can be defensible:

- marginal values emphasize direct functional use by the model;
- conditional values share credit through dependence;
- grouped values assign credit to the coalition.

Instability across folds, seeds, backgrounds, or equivalent model fits is evidence that individual attribution is not uniquely supported by the problem. Report grouped results or sensitivity rather than selecting one convenient ranking.

## SHAP Is Not Causal

SHAP makes predictive relationships visible. A positive attribution does not imply that increasing the feature would increase the real-world outcome.

Confounding, mediation, reverse causality, selection bias, and feature redundancy can all make predictive patterns unsuitable for intervention.

Use causal language only when:

- the model and estimand are explicitly causal;
- identification assumptions are stated;
- data collection supports those assumptions;
- the SHAP use is integrated into that causal analysis.

Even then, describe exactly what quantity is attributed.

## SHAP Is Not a Fairness Certificate

Attribution can help investigate:

- whether a model directly uses a protected feature;
- whether potential proxies have large or heterogeneous attributions;
- how explanation distributions differ across groups;
- which features contribute to errors or loss.

It cannot alone establish:

- demographic parity;
- equalized odds/opportunity;
- calibration by group;
- absence of proxy discrimination;
- individual fairness;
- compliant recourse.

Protected-feature attribution can be small while proxies drive disparities. Conditional attributions can also assign protected-feature credit even when the model does not directly consume it. Pair SHAP with outcome, error, calibration, threshold, and data-quality analyses.

## SHAP Is Not Recourse

A waterfall answers "how this model output is allocated relative to this reference." It does not answer:

- which feature can feasibly be changed;
- what the outcome would be after intervention;
- whether downstream features would change;
- what the minimal safe action is.

Use dedicated counterfactual/recourse methods with feasibility and causal constraints.

## Uncertainty and Stability

A standard SHAP plot usually shows point estimates, not uncertainty.

Sources of variation include:

- model fitting sample and seed;
- hyperparameters;
- background sample;
- evaluation cohort;
- approximation seed and budget;
- conditional-distribution estimation;
- preprocessing and feature grouping.

Useful stability analyses:

1. bootstrap or cross-fit the model;
2. repeat background sampling;
3. repeat approximation seeds;
4. compare rankings and signed distributions;
5. report intervals or rank stability;
6. separate model uncertainty from explainer approximation uncertainty.

## Comparisons With Other Importance Measures

### Permutation importance

Measures predictive performance degradation after shuffling a feature.

- global, metric-dependent;
- can be distorted by correlated features;
- does not decompose individual predictions.

### Split/gain importance

Summarizes how a tree used features during fitting.

- fast;
- can favor high-cardinality or frequently split features;
- does not provide local output decomposition.

### Linear coefficients

Describe change per input unit on the model's linear scale.

- depend on feature scale and parameterization;
- do not include how far a row is from the reference.

### Partial dependence

Averages predictions while varying a feature.

- describes an average response surface;
- can evaluate off-manifold combinations;
- does not allocate each individual prediction.

These answer different questions. Agreement is reassuring but not proof; disagreement should trigger an assumptions review.

## Interpretation Checklist

Before making a claim:

- [ ] Name the model output and units.
- [ ] Define background and masking semantics.
- [ ] Identify the selected row/cohort and sampling rule.
- [ ] Verify additivity where applicable.
- [ ] State whether estimates are exact or approximate.
- [ ] Check correlation and grouping sensitivity.
- [ ] Separate local from global claims.
- [ ] Avoid causal, fairness, and recourse claims without separate evidence.
- [ ] Report model performance and relevant uncertainty.

## Sources

- Lundberg & Lee (2017), "A Unified Approach to Interpreting Model Predictions": https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html
- Lundberg et al. (2020), "From local explanations to global understanding with explainable AI for trees": https://www.nature.com/articles/s42256-019-0138-9
- SHAP introduction: https://shap.readthedocs.io/en/latest/example_notebooks/overviews/An%20introduction%20to%20explainable%20AI%20with%20Shapley%20values.html
- Causal interpretation caution: https://shap.readthedocs.io/en/latest/example_notebooks/overviews/Be%20careful%20when%20interpreting%20predictive%20models%20in%20search%20of%20causal%20insights.html
- Explaining quantitative fairness measures: https://shap.readthedocs.io/en/latest/example_notebooks/overviews/Explaining%20quantitative%20measures%20of%20fairness.html
- Janzing, Minorics & Blöbaum (2020), "Feature relevance quantification in explainable AI: A causal problem": https://proceedings.mlr.press/v108/janzing20a.html
