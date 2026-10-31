# Core workflow

This pattern targets PyDESeq2 0.5.4. The small native regression fixtures execute
these APIs; paths and scientific metadata must be supplied for the actual study.
For robust CSV loading and validation, use the bundled driver. This example starts
with **validated** `counts_df` (samples × genes) and exactly aligned `metadata`,
with nonmissing `condition` containing only `control` and `treated`.

```python
import numpy as np
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats
from pydeseq2.default_inference import DefaultInference

assert counts_df.index.is_unique and counts_df.columns.is_unique
assert metadata.index.is_unique and counts_df.index.equals(metadata.index)
assert metadata['condition'].notna().all()
assert set(metadata['condition']) == {'control', 'treated'}
values = counts_df.to_numpy()
assert np.isfinite(values).all() and (values >= 0).all()
assert (values == np.floor(values)).all() and (values.sum(axis=1) > 0).all()
# Deliberate sample exclusions precede this prespecified example gene prefilter.
counts_df = counts_df.loc[:, counts_df.sum(axis=0) >= 10].copy()
assert counts_df.shape[1] > 0 and (counts_df.sum(axis=1) > 0).all()
metadata = metadata.copy()
metadata['condition'] = pd.Categorical(metadata['condition'], categories=['control', 'treated'])

inference = DefaultInference(n_cpus=1)
dds = DeseqDataSet(counts=counts_df, metadata=metadata, design='~condition',
                   refit_cooks=True, inference=inference)
X = dds.obsm['design_matrix']
assert X.index.equals(counts_df.index)
assert np.linalg.matrix_rank(X.to_numpy()) == X.shape[1] < X.shape[0]
dds.deseq2()
assert np.isfinite(dds.obs['size_factors']).all()
assert (dds.obs['size_factors'] > 0).all()

alpha = 0.05
contrast = ['condition', 'treated', 'control']
ds = DeseqStats(dds, contrast=contrast, alpha=alpha, inference=inference)
ds.summary()
wald_results = ds.results_df.copy(deep=True)
wald_results.to_csv('results_unshrunken.csv')

# Optional shrinkage: this simple reference-coded comparison is a single coefficient.
coeff = 'condition[T.treated]'
vector = np.asarray(dds.contrast(column='condition', baseline='control', group_to_compare='treated'))
unit = np.zeros(X.shape[1])
unit[X.columns.get_loc(coeff)] = 1
assert np.allclose(vector, unit)
ds.lfc_shrink(coeff=coeff)
ds.results_df.to_csv('results_shrunken.csv')
wald_results.loc[wald_results.padj < alpha].to_csv('significant_genes.csv')
dds.to_picklable_anndata().write_h5ad('dds_result.h5ad')
```

`dds.deseq2()` estimates size factors, gene-wise/trend/MAP dispersions and LFCs,
then computes Cook diagnostics and eligible replacement/refitting. It does not
perform the contrast test; `DeseqStats.summary()` does that.

The significance CSV above deliberately uses unshrunk effects. The standalone
CLI's significant CSV uses its current effect estimates; both use the preserved
Wald p-values. Label outputs clearly when communicating them.

`dds.varm['LFC']` remains natural-log model coefficients. Results tables report
log2 effects; compare after dividing coefficients by `np.log(2)`. Keep original
counts, full results, formula, contrast, thresholds, versions, exclusions and
normalization choices. H5AD preserves arrays/annotations but does not reconstruct
the Python model's formulaic machinery; retain the original analysis code.

Source: [official minimal workflow](https://pydeseq2.readthedocs.io/en/stable/auto_examples/plot_minimal_pydeseq2_pipeline.html).
