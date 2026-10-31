---
name: scvelo
description: Performs RNA velocity analysis with scVelo from spliced and unspliced single-cell RNA counts. Fits deterministic or dynamical models, examines gene phase portraits, builds velocity graphs, estimates relative latent time, and ranks velocity-associated genes. Use for directional trajectory hypotheses and kinetic-model diagnostics alongside Scanpy; velocity alone does not establish cell fate or causal drivers.
license: BSD-3-Clause
compatibility: Requires Python 3.13 for the tested stack with scvelo 0.3.4, scanpy 1.12.4, anndata 0.13.4, numpy 2.5.3 and pandas 2.3.3. Loom import requires loompy. Local H5AD analysis needs no network or credentials. The default stochastic solver is incompatible with NumPy 2.
metadata:
  version: "2.0"
  skill-author: Kuan-lin Huang
  last-reviewed: "2026-10-01"
---

# scVelo RNA Velocity

## When to use

Use for kinetic analysis of aligned spliced/unspliced RNA counts, directional
trajectory hypotheses, gene-level phase portraits, and dynamical latent time.
Use the [model reference](references/velocity_models.md) for assumptions,
transition probabilities, and an optional CellRank handoff.

RNA velocity estimates an expression derivative under a model. Smooth arrows
are not observed cell movement, lineage tracing, causal drivers, or proof of
future fate. The dynamical estimator is not automatically more accurate than
a steady-state estimator on every dataset.

## Tested environment and compatibility

The maintained workflow targets scVelo **0.3.4**, Scanpy **1.12.4**, AnnData
**0.13.4**, NumPy **2.5.3**, pandas **2.3.3**, SciPy **1.18.1**, Matplotlib
**3.11.2**, and loompy **3.0.8** on Python 3.13. Use an isolated environment:

```bash
uv venv --python 3.13 .venv-velocity
uv pip install --python .venv-velocity/bin/python \
  scvelo==0.3.4 scanpy==1.12.4 anndata==0.13.4 numpy==2.5.3 \
  pandas==2.3.3 scipy==1.18.1 matplotlib==3.11.2 loompy==3.0.8
```

The packages above were resolved from cache and tested in an isolated `uv`
environment; shell paths above use POSIX syntax. Installation requires network
access unless packages are cached. No API key is required.

- **Deterministic and dynamical models:** native synthetic fitting, graphs,
  relative times, plots and H5AD round trips are tested on this stack.
- **Stochastic model:** scVelo 0.3.4's default GLS scalar assignment fails with
  NumPy 2. Scanpy 1.12 requires NumPy 2, so installing `numpy<2` beside current
  Scanpy is not a solution. A separately validated legacy Scanpy/NumPy environment
  is required; that legacy stack was not executed in this review. The helper
  rejects this combination before modifying data, without changing the model.
- **pandas 3:** scVelo 0.3.4 dynamical fitting and some plots use operations no
  longer supported by pandas 3. Keep the explicit pandas pin.
- The upstream stable tutorial still contains removed `scv.read` and older
  preprocessing calls. Check the [0.3.4 source](https://github.com/theislab/scvelo/tree/v0.3.4)
  when a tutorial disagrees with the installed API.

## Input contract

1. Obtain spliced and unspliced counts from a velocity-aware quantifier. Keep
   quantifier/version, reference annotation, counting mode, sample IDs and cell
   barcode mapping. Upstream quantification is outside the bundled script.
2. Supply **cells by genes** matrices in `adata.layers['spliced']` and
   `adata.layers['unspliced']`, with identical cell/gene ordering and unique IDs.
   Counts must be finite and nonnegative; fractional count estimates are allowed.
   Never use logged, scaled, residualized, or batch-corrected values as counts.
   Numerical inspection alone cannot establish that data are raw.
3. Inspect per-library/cluster coverage, doublets, ambient RNA, zero-count cells,
   and annotation compatibility before fitting. Preserve the original full-gene
   count file. Retained-gene backups do not preserve filtered-out genes.
4. Resolve barcode prefixes and gene identifiers explicitly when combining
   files. Do not silently strip library IDs, intersect away most cells, or make
   duplicated biological IDs unique without understanding why they repeat.

Read H5AD through AnnData. scVelo 0.3.4 has no `scv.read` or `scv.DataFrame`:

```python
import anndata as ad
adata = ad.read_h5ad("velocity_counts.h5ad")
```

For legacy loom input use `ad.io.read_loom('counts.loom', X_name='spliced',
sparse=True)`. AnnData 0.13 deprecates loom; convert to H5AD for further work.
Its `layers[None]` aliases `X`: do not delete it or iterate all layers as if every
key were a string. The helper accesses only named velocity layers. Native loom
reading and exact, reordered metadata alignment are covered by the tests;
AnnData 0.13 `write_loom` is not used.

## Run the maintained workflow

The [bundled script](scripts/rna_velocity_workflow.py) accepts local files and
never downloads a demonstration dataset on startup:

```bash
MPLBACKEND=Agg .venv-velocity/bin/python scripts/rna_velocity_workflow.py \
  velocity_counts.h5ad --mode dynamical --groupby clusters \
  --n-top-genes 2000 --n-neighbors 30 --n-jobs 1 --output-dir velocity_results

# Import a loom and align its raw counts to an existing annotation file:
MPLBACKEND=Agg .venv-velocity/bin/python scripts/rna_velocity_workflow.py \
  counts.loom --processed-h5ad annotated.h5ad --groupby clusters \
  --mode deterministic --output-dir velocity_check
```

Run these from the skill directory. Input filenames and biological annotations
are illustrative; the same CLI and functions are tested on small generated
kinetic fixtures. Omit `--groupby` when annotations are unavailable. Use
`--no-plots` for analysis without computing UMAP.

The helper performs these steps:

1. Validate layers, IDs, model compatibility and grouping; refuse previously
   generated moments/velocity so preprocessing cannot silently run twice.
2. Back up retained raw layers as `spliced_counts` and `unspliced_counts` and
   rebuild `X` from raw spliced counts. Filter genes and normalize `X` and the
   two count layers on a linear scale.
3. Apply `sc.pp.log1p` **only to X**, select highly variable genes with Scanpy,
   and rebuild PCA and neighbors after subsetting. Reusing stale PCA/neighbors
   from an unrelated feature set can silently change the velocity model.
4. Compute `Ms` and `Mu` with `scv.pp.moments(adata, n_neighbors=None)` from the
   explicit Scanpy graph. Moments are dense: budget memory for multiple
   cells-by-genes arrays, not only the sparse input.
5. For dynamical mode, call `recover_dynamics(var_names='all')` on the selected
   genes before `velocity(mode='dynamical')`; otherwise fit the selected model.
   Require usable genes and a nonempty velocity graph.
6. Compute velocity coherence and velocity pseudotime; add latent time only for
   dynamical fits. Rank velocity-associated genes only with at least two groups
   and at least two cells per group. Record/warn about nonfinite or constant
   time/coherence outputs in `uns['velocity_workflow']['diagnostics']`; a
   constant pseudotime does not support a trajectory ordering. Ranking is exploratory.
7. For plots, recompute UMAP from the rebuilt graph, project velocities, save
   PNGs directly to the requested directory, then save H5AD with package versions
   and selected parameters. Existing labels remain annotations, not validated
   cell identities.

The Python function mutates its argument in place; pass `adata.copy()` to keep
the original object. The CLI writes to `output_dir/adata_velocity.h5ad`.
Version 2 changes the former helper's behavior deliberately: raw layer geometry
is rebuilt, missing requested labels are errors, and plots/parallelism can be
controlled explicitly. Runtime depends on cells, genes and fit difficulty;
there is no universal 10–30 minute expectation.

## Inspect the evidence before interpretation

After a dynamical run (dataset-specific gene selection is illustrative):

```python
import pandas as pd
import scvelo as scv

# Candidate kinetic genes, not experimentally established drivers.
candidates = adata.var['fit_likelihood'].dropna().nlargest(6).index.tolist()
scv.pl.velocity(adata, var_names=candidates, basis='umap', show=False)

# This ranks group-associated velocities, not causal influence or condition DE.
scv.tl.rank_velocity_genes(adata, groupby='clusters', min_corr=0.3)
ranked = pd.DataFrame(adata.uns['rank_velocity_genes']['names'])

scv.tl.velocity_confidence(adata)
scv.pl.scatter(adata, color=['velocity_length', 'velocity_confidence'], show=False)
```

Inspect spliced-versus-unspliced phase portraits, coverage across induction and
repression, fitted parameters, failed/NaN fits, and branch-specific kinetics.
Check sensitivity to gene set, neighbors, subsampling and model assumptions.
Use time-course labels, perturbations, lineage tracing or labeling experiments
as independent directional evidence where available. A plausible UMAP alone
cannot validate a fit, and tuning until arrows match a desired story is not a
validation strategy.

There is no general minimum of 2,000 cells, universal unspliced fraction, or
rule that root cells must have the highest unspliced/spliced ratio. Coverage of
relevant kinetic states and measurement quality matter. Negative velocity can
represent repression or model misspecification; it is not by itself evidence
that layers were swapped.

## Output interpretation

| Field | Interpretation |
| --- | --- |
| `layers['velocity']` | Model-estimated derivative in processed gene-expression space |
| `var['velocity_genes']` | Genes selected for the velocity graph; distinct from all HVGs |
| `layers['Ms']`, `layers['Mu']` | Neighbor-averaged linear-scale spliced/unspliced expression |
| `layers['fit_t']` | Gene-specific fitted time coordinates, dynamical model only |
| `var['fit_alpha/beta/gamma']` | Fitted rates on the model's inferred scale; not calibrated physical rates |
| `var['fit_likelihood']` | Relative model-fit diagnostic; not a posterior probability of biological truth |
| `uns['velocity_graph']` | Sparse positive cosine correlations for candidate transitions; not row-stochastic |
| `obsm['velocity_umap']` | Projected vectors, only after embedding computation/plotting |
| `obs['velocity_pseudotime']` | Graph-based relative ordering |
| `obs['latent_time']` | Coupled dynamical ordering; normally scaled 0–1, not elapsed hours |
| `obs['velocity_length']` | Processed-space vector magnitude; not physical cell speed |
| `obs['velocity_confidence']` | Neighbor velocity coherence, not calibrated uncertainty |

For fate probabilities use an explicitly normalized transition kernel and a
validated terminal-state definition; see the optional CellRank example in the
reference. PAGA requires optional igraph and compatible Scanpy internals; it is
not part of the tested core workflow or a substitute for fate inference.

## Troubleshooting

| Problem | Action |
| --- | --- |
| Missing or mismatched layers | Revisit quantification and explicit ID alignment; X cannot substitute for unspliced counts |
| Very few velocity genes | Inspect depth, state coverage and phase portraits before altering thresholds |
| Smooth but implausible arrows | Check model assumptions, batch geometry and individual genes; compare independent evidence |
| Nonfinite fit or empty graph | Stop interpretation and investigate degenerate features/coverage |
| Excessive memory or fitting time | Use a justified gene set and `n_jobs=1`; account for dense moments and fit arrays |
| Stochastic failure on NumPy 2 | Use a separately validated compatible legacy stack or explicitly reconsider the model |
| pandas `unique` error in fit/plot | Use the tested pandas 2.3.3 pin |

## Sources and verification scope

Reviewed 2026-10-01 against the [released source](https://github.com/theislab/scvelo/tree/v0.3.4),
[API](https://scvelo.readthedocs.io/en/latest/api.html),
[kinetic-model caveats](https://scvelo.readthedocs.io/en/latest/perspectives/Perspectives.html),
and [AnnData loom reader](https://anndata.readthedocs.io/en/stable/generated/anndata.io.read_loom.html).
The main paper is [Bergen et al., 2020](https://doi.org/10.1038/s41587-020-0591-3).
Synthetic execution tests verify software contracts and file/figure production;
they do not establish biological accuracy, identifiability or dataset-specific
parameter recovery. Optional CellRank/PAGA analyses remain source-reviewed,
illustrative extensions. No authenticated remote service is used.
