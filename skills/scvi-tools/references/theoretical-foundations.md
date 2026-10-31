# Interpreting the probabilistic model

Reviewed against scvi-tools 1.5.1. These are interpretation rules, not guarantees
that a particular trained model is scientifically adequate.

## Likelihood and variational inference

For latent state `z`, observed data `x` and technical covariates `s`, an encoder
approximates `q(z | x, s)` and the decoder models `p(x | z, s)`. The simplified
objective is

```text
ELBO = E_q[log p(x | z, s)] - KL(q(z | x, s) || p(z))
```

Additional latent variables and losses depend on the model. The neural-network
weights are usually point estimates, so posterior draws do not capture every
source of parameter, preprocessing, reference or sampling uncertainty. Optimizing
this nonconvex objective does not guarantee a global optimum or calibrated biology.

SCVI commonly uses negative binomial counts with `Var(x)=mu+mu^2/theta`, or a
zero-inflated NB mixture. A zero-inflation parameter is a mixture probability;
it cannot by itself identify technical dropout versus biological absence.
High sparsity does not prove that ZINB is preferable to NB. Compare suitable
likelihoods using held-out fit, posterior predictive checks and domain knowledge.
AUTOZI tests evidence for additional zero inflation under its assumptions; it does
not label every zero's biological origin.

Do not generalize the count likelihood to all scvi-tools models. PeakVI uses
Bernoulli accessibility; methylation models use methylated/coverage counts;
SysVI and CytoVI operate on appropriately transformed continuous values; VeloVI
uses preprocessed spliced/unspliced abundances and kinetic assumptions.

## Integration and identifiability

Conditioning the decoder on batch encourages removal of nuisance variation from
`z`; it does not mathematically force a batch-invariant latent space. Complete
batch/condition confounding prevents identification of their separate effects.
Validate both mixing among comparable cell states and preservation of cell-type,
condition, donor and trajectory structure that should remain.

Covariates are model inputs, not a list of everything available in `.obs`.
Library-size handling is already part of RNA models. Additional depth, tissue,
condition or donor covariates can change the estimand or remove wanted signal.
Continuous covariates must have appropriate scale; registration does not promise
automatic standardization.

`transform_batch` decodes a fitted cell state under a different registered batch.
This is model-based counterfactual decoding. It is not an identified causal
intervention, nor evidence that the model predicts unobserved drug responses.

## Transfer, samples and spatial structure

scArches performs model-specific architectural surgery with selective parameter
freezing; it is not simply "freeze the encoder, train the decoder." Use
`prepare_query_anndata`/`load_query_data` and inspect their freeze options. Query
feature order, count scale, covariates and reference coverage matter. A classifier
can confidently mislabel a cell type missing from its reference; evaluate rejection
and uncertainty with held-out biological samples.

MRVI uses sample-unaware `u` and sample-aware `z` representations with learned
sample-conditioned transformations. It is not defined by the generic additive
formula `z_shared + z_sample` or a simple normal random-intercept hierarchy.
Sample distances and multivariate comparisons depend on sample support and design.

DestVI deconvolves spatial expression with a labeled CondSCVI reference and
continuous within-type states. Spatial coordinates do not automatically imply a
spatial autocorrelation prior; validate proportions against independent tissue
information. Tangram mapping is an optimization over cell-to-location assignment
weights, not proof of the physical location of an individual sequenced cell.

## Posterior contrasts

For RNA change-mode DE, positive LFC means group1 over group2. The returned
`bayes_factor` is on the natural-log posterior-odds scale. Posterior FDP selection
is conditional on the fitted model and hypotheses; it is not a conversion to
frequentist p-values. More posterior samples reduce simulation noise, not
biological uncertainty from a small number of donors. See
[differential-expression.md](differential-expression.md) for exact API choices.

The logged `elbo_validation` training metric is a loss (lower is better), while
`get_elbo()` returns an ELBO (higher is better). Compare the same metric on the
same held-out cells/features; a training curve alone does not establish convergence,
identifiability, generalization or successful integration.

Sources: [variational inference](https://docs.scvi-tools.org/en/stable/user_guide/background/variational_inference.html),
[SCVI](https://docs.scvi-tools.org/en/stable/user_guide/models/scvi.html),
[AUTOZI](https://docs.scvi-tools.org/en/stable/user_guide/models/autozi.html),
[SysVI assumptions](https://github.com/scverse/scvi-tools/blob/1.5.1/docs/user_guide/models/sysvi.md),
[MrVI](https://docs.scvi-tools.org/en/stable/user_guide/models/mrvi.html),
[DestVI](https://docs.scvi-tools.org/en/stable/user_guide/models/destvi.html),
[transfer implementation](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/base/_archesmixin.py).
