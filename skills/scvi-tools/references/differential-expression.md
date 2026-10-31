# Differential expression and abundance

Source-reviewed for scvi-tools 1.5.1. Examples are illustrative and require trained
models and validated group metadata. CPU synthetic checks exercised SCVI change-mode
DE and TOTALVI RNA/protein selection; other DE/DA workflows remain source-reviewed.

## Define the biological unit first

SCVI DE compares cell populations under the fitted generative model. Cells from the
same donor are not independent biological replicates. Increasing posterior sample
count reduces Monte Carlo error; it does not create replication, repair confounding,
or compensate for absent rare cell types. Condition-level inference generally needs
replicate-aware methods, for example sums of **measured counts** by donor and cell
type followed by a suitable count-model design. A call to
`model.differential_expression` does not aggregate pseudobulk samples.

Record the gene universe, QC, selected cells, replicate counts, covariates and
estimand. The model can only test its registered features. Marker discovery on
clusters learned from the same cells is exploratory.

## SCVI posterior DE

```python
import numpy as np

# Positive LFC means higher expression in group1 (treated).
de = model.differential_expression(
    groupby="condition", group1="treated", group2="control",
    mode="change", delta=np.log2(1.5), test_mode="two",
    fdr_target=0.05, batch_correction=False,
    n_samples_overall=5000,
)
up = de.loc[de["is_de_fdr_0.05"] & (de["lfc_mean"] > 0)]
up = up.sort_values("lfc_mean", ascending=False)
```

- SCVI's inherited RNA API defaults to `mode='vanilla'`; set the mode explicitly.
  `vanilla` compares `h1 > h2` with `h1 <= h2`, not an exact-zero point null.
- `change` computes an effect distribution, with default change function
  `log2(h1 + offset) - log2(h2 + offset)`. The offset may be estimated from data;
  the method is not pseudocount-free.
- `delta` sets the relevant effect threshold. `test_mode='two'` combines both
  tails; the underlying default `'three'` uses the larger directional posterior
  probability. State the choice when interpreting `proba_de`.
- Use `n_samples_overall`, not `n_samples`, for the generic SCVI DE posterior
  comparison. Specialized models such as RESOLVI have additional sampling arguments.
- `bayes_factor` is a **natural-log posterior odds** quantity in this
  implementation. It is neither an unlogged Bayes factor nor a p-value.
- `proba_de` and `proba_not_de` are model posterior quantities. FDR selection
  controls posterior expected FDP under this model, not unconditional frequentist
  error or donor-level confounding.
- The output includes `lfc_mean`, `lfc_median`, `lfc_std`, `scale1`, `scale2`
  and the FDR column matching the requested target. `lfc_min`/`lfc_max` describe
  sampled extrema, not a confidence interval. Request `cred_interval_lvls=[0.95]`
  for posterior credible summaries and inspect actual returned column names.
  Raw-count statistics, when enabled, use names such as `raw_mean1`,
  `raw_mean2`, `non_zeros_proportion1` and `non_zeros_proportion2`.

Never apply Benjamini-Hochberg or Bonferroni to `1/(bayes_factor+1)` or plot that
quantity as a p-value. An effect-versus-posterior-evidence plot is valid if its
axis explicitly says `proba_de` or log posterior odds:

```python
import matplotlib.pyplot as plt
plt.scatter(de["lfc_mean"], de["proba_de"], s=8)
plt.xlabel("Posterior mean log2 fold change (group1 - group2)")
plt.ylabel("Posterior probability of relevant change")
```

## Group masks and batch conditioning

`groupby` is optional when explicit cell masks/indices are supplied. With
`group2=None`, the comparison is against the remaining cells. Avoid accidental
whole-dataset controls when the intended comparison is within a cell type.

```python
in_lung = adata.obs["tissue"].eq("lung")
idx1 = (in_lung & adata.obs["cell_type"].eq("T cells")).to_numpy()
idx2 = (in_lung & adata.obs["cell_type"].eq("B cells")).to_numpy()
assert idx1.any() and idx2.any() and not (idx1 & idx2).any()
de_subset = model.differential_expression(
    idx1=idx1, idx2=idx2, mode="change", delta=0.5,
    n_samples_overall=5000, batch_correction=False,
)
```

`batch_correction=False` is the 1.5.1 default and uses observed batches. It does
**not** restrict the compared cells to one batch; use masks for that. With
`True`, specify scientifically supported `batchid1`/`batchid2` or understand the
all-batch marginalization. Identical batch sets support matched conditioning;
partially overlapping unequal batch sets trigger an upstream warning and are not
reliably handled. Cross-batch predictions remain extrapolations when biology and
batch are confounded. Check sensitivity to batch treatment rather than assuming
registration automatically makes every DE call corrected.

## Other modalities have different return contracts

**TOTALVI** returns RNA and protein features in one DE DataFrame:

```python
joint_de = totalvi_model.differential_expression(
    groupby="cell_type", group1="T cells", group2="B cells",
    mode="change", delta=0.5,
)
```

There is no `protein_expression=True` switch. In 1.5.1, use `use_field=["rna"]`
or `use_field=["protein"]` to select a modality; protein result names have a
`_protein` suffix. Preserve feature provenance and names to avoid collisions.
Its normalized-expression method returns `(rna, protein)`.

**PEAKVI / MULTIVI** use `differential_accessibility`. The default accessibility
`delta=0.05` is an absolute probability difference, not an RNA log2 fold-change.
`effect_size` is `scale2 - scale1` in PEAKVI, reversing the RNA LFC direction.
Read the returned fields; do not blindly apply the RNA interpretation.

**METHYLVI** uses `differential_methylation` and returns a dictionary keyed by
methylation context; the effect concerns methylation probability differences,
not expression. **MRVI** has a separate sample-covariate DE API; see the
[multimodal reference](models-multimodal.md).

## Differential abundance is a separate estimand

In the generic `VAEMixin` API, specify `sample_key`, not DE-style groups:

```python
model.differential_abundance(sample_key="sample")
log_probs = model.adata.obsm["da_log_probs"]
```

For an ordinary AnnData-backed model, this method stores a cells-by-samples log
probability DataFrame and returns `None`. It is a latent-density diagnostic,
not automatically a donor-level condition test or a cell-count composition model.
MRVI and CYTOVI expose different abundance signatures and outputs.

Sources: [RNA API source](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/base/_rnamixin.py),
[DE computation](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/base/_differential.py),
[DE results and FDP](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/base/_de_core.py),
[TOTALVI](https://docs.scvi-tools.org/en/stable/api/reference/scvi.model.TOTALVI.html),
[PEAKVI source](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/_peakvi.py),
[abundance API](https://github.com/scverse/scvi-tools/blob/1.5.1/src/scvi/model/base/_vaemixin.py).
