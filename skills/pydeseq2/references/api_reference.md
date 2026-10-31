# PyDESeq2 0.5.4 API and verification notes

Reviewed 2026-10-01 against the published release, official stable documentation,
`v0.5.4` source and a local native runtime. This is a focused contract reference,
not a complete replacement for upstream documentation.

## Installation and tested scope

The [current release](https://pypi.org/project/pydeseq2/0.5.4/) is 0.5.4 and requires
Python >=3.11. Its dependency floor includes AnnData >=0.11, NumPy >=2,
pandas >=2.2, SciPy >=1.12, scikit-learn >=1.4, formulaic >=1.0.2, and
formulaic-contrasts >=0.2.0. Dependency floors are not a claim that every later
combination was tested. AnnData 0.13.4 requires Python >=3.12.

The native review used Python 3.13.3, PyDESeq2 0.5.4, AnnData 0.13.4,
pandas 3.0.6, NumPy 2.5.1, SciPy 1.18.1, scikit-learn 1.9.1,
formulaic 1.2.2, formulaic-contrasts 1.0.0, and Matplotlib 3.11.2.
Tests cover synthetic numerical/input/contrast contracts and real H5AD round-trips.
They do not establish R/Python numerical equivalence, real biological calibration,
large-data memory performance, or all inference backends/platforms.

## `DeseqDataSet`

```python
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference

dds = DeseqDataSet(
    counts=counts_df, metadata=metadata, design='~condition',
    fit_type='parametric', size_factors_fit_type='ratio',
    refit_cooks=True, min_replicates=7,
    inference=DefaultInference(n_cpus=1), low_memory=False,
)
dds.deseq2()  # required before constructing DeseqStats
```

- `counts`: samples × genes nonnegative integer DataFrame; `metadata` has matching
  sample rows. Alternatively use `adata=` with counts in `.X` and annotations in
  `.obs`; do not also supply counts/metadata. Sparse input is not a guarantee of a
  sparse complete fit. Validate/densify a small matrix intentionally.
- `design`: formula string or explicit design DataFrame. The older `design_factors`,
  `continuous_factors`, and `ref_level` parameters are deprecated. Formulaic uses
  numeric variables continuously; set categorical dtype/reference levels explicitly.
- `fit_type`: `'parametric'` or `'mean'`; the former can fall back with a warning.
- `size_factors_fit_type`: `'ratio'`, `'poscounts'`, or `'iterative'`.
  `control_genes` selects gene indexers, with the release-specific caveats in the
  [workflow guide](workflow_guide.md).
- `refit_cooks`: eligible count replacement and refitting; not sample deletion.
  `min_replicates` defaults to seven.
- `n_cpus` can be set directly or on `DefaultInference`; reuse a bounded inference
  object for fitting/testing. `quiet=True` reduces routine messages, not all warnings.

Methods:

| Method | Contract |
| --- | --- |
| `deseq2(fit_type=None)` | Fit normalization, dispersions, LFCs and Cook diagnostics/refits; updates in place. |
| `fit_size_factors(fit_type=None, control_genes=None)` | Normalize only; check positive finite factors. |
| `cond(**kwargs)` | Formula-based condition vector; unspecified factors use defaults/baselines. |
| `contrast(column, baseline, group_to_compare)` | Formula-based simple pairwise contrast vector. |
| `plot_dispersions(log=True, save_path=None, **kwargs)` | Plot gene-wise, fitted and final dispersions. |
| `vst(use_design=False, fit_type=None)` | Fits/applies VST and stores `layers['vst_counts']`. |
| `vst_fit(use_design=False)` / `vst_transform(counts=None)` | Separate fitted transformation and application; held-out use needs method-specific validation. |
| `to_picklable_anndata()` | Plain AnnData snapshot; converts formulaic design matrix to DataFrame. |

## AnnData layout after fitting

| Field | Meaning |
| --- | --- |
| `X` | Input sample × gene counts. |
| `obs['size_factors']` | One positive normalization factor per sample. |
| `obsm['design_matrix']` | Sample × coefficient design matrix. |
| `layers['normed_counts']` | Counts divided by sample factors; not TPM or VST. |
| `layers['cooks']` | Sample × gene Cook diagnostic matrix, if retained. |
| `var['genewise_dispersions']`, `['fitted_dispersions']`, `['MAP_dispersions']`, `['dispersions']` | Gene-wise/trend/MAP/final estimates. |
| `varm['LFC']` | Gene × coefficient estimates in **natural log**, not log2. |
| `var['_LFC_converged']` and other underscore fields | Useful release-specific diagnostic flags; not a stable cross-version schema. |
| `uns` | Shared trend/prior parameters; contents depend on method/fallback. |

`DeseqStats.results_df` is stored on the statistics object, not automatically in
this AnnData. Save the result CSVs separately. An H5AD snapshot cannot recreate
formulaic contrasts or resume every estimator method simply by reading it back.

## `DeseqStats`

```python
from pydeseq2.ds import DeseqStats

ds = DeseqStats(dds, contrast=['condition', 'treated', 'control'], alpha=0.05,
                cooks_filter=True, independent_filter=True, n_cpus=1)
ds.summary()
```

`contrast` is mandatory: a three-string list `[factor, numerator, denominator]`
or a 1D NumPy vector with one entry per design column. Check finite entries,
nonzero contrast and biological estimability. Numeric vectors should be NumPy
arrays, not numeric Python lists interpreted as factor contrasts.

`lfc_null=0.0` is in log2 units. `alt_hypothesis=None` gives the usual two-sided
Wald test. `'greaterAbs'`, `'lessAbs'`, `'greater'`, and `'less'` specify different
alternatives; choose deliberately. `summary(lfc_null=..., alt_hypothesis=...)`
can replace the hypothesis and rerun testing, but do so on an unshrunken object.
`prior_LFC_var` is an optional ridge prior and is distinct from apeGLM shrinkage.

`summary()` updates `results_df` with `baseMean`, `log2FoldChange`, `lfcSE`,
`stat`, `pvalue`, and `padj`. `baseMean` is the mean normalized count across all
samples, not either condition's mean. Original LFC and SE are log2 values;
`stat` is dimensionless. The usual zero-null two-sided statistic is signed.
Cook/independent filtering can produce missing p-values/adjusted p-values.

`lfc_shrink(coeff, adapt=True)` selects a **single column name** from the LFC
matrix and uses an apeGLM-style heavy-tailed prior. It mutates `ds.LFC`, `ds.SE`,
and the table's `log2FoldChange` and `lfcSE`, keeping existing `stat`, `pvalue`,
and `padj`. The source writes the selected coefficient to the table even when
it differs from the original contrast. Check that the exact contrast is the
positive unit vector for that coefficient, or relevel/refit/use unshrunk results.
NaN/infinite shrinkage estimates can leave individual original estimates in place;
inspect warnings and `_LFC_shrink_converged` instead of assuming universal success.

## Preprocessing and upstream example data

`pydeseq2.preprocessing` provides `deseq2_norm(counts)` returning
`(normalized_counts, size_factors)`, plus `deseq2_norm_fit(counts)` and
`deseq2_norm_transform(counts, logmeans, filtered_genes)`. It does not perform the
skill's manual sample exclusions or gene prefilter. Its ratio-only utilities do
not automatically select an alternative method when geometric means are unusable.

```python
from pydeseq2.utils import load_example_data

example_counts = load_example_data(modality='raw_counts', dataset='synthetic', debug=False)
example_metadata = load_example_data(modality='metadata', dataset='synthetic', debug=False)
```

Each call returns **one DataFrame**, not a tuple. With no packaged `datasets/`
directory, 0.5.4 downloads public CSVs using unauthenticated GET from
`https://raw.githubusercontent.com/owkin/PyDESeq2/main/datasets/synthetic/`
(`test_counts.csv` or `test_metadata.csv`; source inserts an extra slash).
There is no request body, API version, token or pagination. It transposes the
count CSV. This moving `main` data source is unsuitable as a pinned benchmark;
retain a versioned fixture/checksum for reproducibility. `debug=True` is unreliable
for raw counts in this release: the source tries to sample 100 rows after first
sampling ten. Use `debug=False` and subset both modalities explicitly if needed.

No hosted analysis service or authenticated scientific endpoint is needed for a
local fit. Network example loading is a tiny public-data check, not a validation
of a scientific dataset or remote computation.

## Sources

- [Official dataset API](https://pydeseq2.readthedocs.io/en/stable/api/docstrings/pydeseq2.dds.DeseqDataSet.html)
- [Official statistics API](https://pydeseq2.readthedocs.io/en/stable/api/docstrings/pydeseq2.ds.DeseqStats.html)
- [Release metadata and requirements](https://pydeseq2.readthedocs.io/en/stable/usage/requirements.html)
- [Tagged dataset implementation](https://github.com/scverse/PyDESeq2/blob/v0.5.4/pydeseq2/dds.py)
- [Tagged statistics implementation](https://github.com/scverse/PyDESeq2/blob/v0.5.4/pydeseq2/ds.py)
- [Tagged utilities and example loader](https://github.com/scverse/PyDESeq2/blob/v0.5.4/pydeseq2/utils.py)
- [Tagged preprocessing](https://github.com/scverse/PyDESeq2/blob/v0.5.4/pydeseq2/preprocessing.py)
