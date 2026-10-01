# Scanpy 1.12.4 review and representation boundaries

Reviewed 2026-10-01. Local tests use Python 3.13, Scanpy 1.12.4 and AnnData
0.13.4. Official stable docs and the installed release source were inspected
for every Scanpy API family used by the toolkit, assets and references.
There are no remote analysis/authentication/pagination endpoints in these scripts.
Package installation and fetching example datasets can use the network; the tests
use local synthetic inputs and no patient data or atlas downloads.

## Invariants to preserve

| Operation | Input | Stored/returned result |
| --- | --- | --- |
| QC/Scrublet | Identified raw counts; capture/library batch for doublets | QC/doublet columns in `obs`; filtered cells remain counts |
| `normalize_total`, `log1p` | Counts, then normalized values | X is log-normalized; `counts` is an independent original count copy |
| `highly_variable_genes` | Log values for seurat/cell_ranger; counts for v3/v3_paper | Boolean `var.highly_variable`; v3 uses scikit-misc; batch tie ordering differs between v3 flavors |
| PCA | Selected HVGs, optionally scaled | `obsm.X_pca`, `varm.PCs`, `uns.pca`; ARPACK components < min(cells, selected genes) |
| Neighbors | Explicit representation and available component count | Pairwise distances/connectivities in `obsp`, parameters in `uns.neighbors` |
| UMAP/Leiden | Neighbor graph | Visualization in `obsm.X_umap`; categorical clusters in `obs`; neither validates cell identity |
| Marker ranking | Log-normalized X/layer/raw explicitly selected | `uns.rank_genes_groups`; `get.rank_genes_groups_df` returns scores and method-dependent statistics |
| Aggregation | Raw-count layer, biological sample x cell type | `layers['sum']`, with `X is None`; grouped annotation contains contributing-cell counts |

`.raw` snapshots X and var, not layers, and does not mean raw counts. Cell slices
subset `.raw` cells; gene slices leave its original gene axis. The scripts use
`adata.raw = adata.copy()` before scaling to prevent shared-array mutation. AnnData
0.13 includes the unnamed X key (`None`) when iterating layers; filter for named
strings where listing extra layers. A view is not an independent copy. Backed `r+`
persists supported X changes only, not arbitrary annotation edits; write a new
file after deliberate `.to_memory()` conversion and close the backing file.

The full pipeline computes on an HVG copy but transfers aligned PCA loadings,
embeddings, graph and parameters to the full-gene object. `--subset-hvg` explicitly
shrinks *all* layers: keep the full-gene checkpoint for pseudobulk. Never reconstruct
missing raw counts from `.raw` or normalized values. CSV/Matrix Market readers need
known orientation and cell/gene identifiers; bare MTX carries neither identifier
list. `.h5` is assumed 10x HDF5, not arbitrary HDF5. Loom needs loompy.

## Statistical and plotting interpretation

`rank_genes_groups` defaults to `reference='rest'`; named reference groups and
`groups` control the comparison, not the donor dependence. BH adjustment is over
tested genes per contrast. t/Wilcoxon p-values do not account for selection of
clusters from the same data or donor-level dependence. Logistic regression is a
marker ranking without equivalent p-values or log fold changes. Scanpy log-fold
changes are approximations computed from mean log expression, not a pseudobulk
negative-binomial model. Do not rank scaled residuals or corrected expression as
if it were log-normalized expression.

The pseudobulk CLI requires the count layer, rejects missing grouping values,
keeps stable opaque profile IDs to prevent underscore collisions, and checks
that transferred condition/donor covariates are constant within each profile.
It exports genes x profiles; transpose for PyDESeq2's samples x genes API.
Preserve identifiers as strings when reading CSV and align rows by IDs. Fit each
cell type separately with adequate independent biological replicates and a
full-rank design; a sample x cell-type table does not multiply the donor count.
Missing cell types are not zero-count biological replicates. Cell-count and
library-size filtering decisions need study-specific justification.

Scanpy 1.12 deprecates plotting `save=` but still supports it; toolkit suffixes
retain distinct filenames. Global autosave alone can overwrite repeated plots.
For exact exported figures use `return_fig=True` for embedding plots, then
`Figure.savefig`; composite DotPlot/MatrixPlot/StackedViolin instead return plot
objects with their own `.savefig()` when `return_fig=True`. `show=False` alone
has function-specific return types, not a universal Figure contract. Dot size
is detection fraction; dot color is mean expression; `standard_scale` rescales
for display and changes the interpretation. Neighbor edges are not a PAGA
partition graph, and cluster heatmaps are not automatically ordered by pseudotime.

## Optional branches and current upstream references

- [Release notes](https://scanpy.readthedocs.io/en/stable/release-notes/index.html):
  1.12.4 released 2026-08-27; Python >=3.12; deprecated Louvain/plot `save` remain.
- [HVG](https://scanpy.readthedocs.io/en/stable/generated/scanpy.pp.highly_variable_genes.html),
  [PCA](https://scanpy.readthedocs.io/en/stable/generated/scanpy.pp.pca.html),
  [neighbors](https://scanpy.readthedocs.io/en/stable/generated/scanpy.pp.neighbors.html),
  [Leiden](https://scanpy.readthedocs.io/en/stable/generated/scanpy.tl.leiden.html).
- [Marker ranking](https://scanpy.readthedocs.io/en/stable/generated/scanpy.tl.rank_genes_groups.html),
  [aggregation](https://scanpy.readthedocs.io/en/stable/generated/scanpy.get.aggregate.html),
  [gene scoring](https://scanpy.readthedocs.io/en/stable/generated/scanpy.tl.score_genes.html).
- [AnnData raw](https://anndata.readthedocs.io/en/stable/generated/anndata.AnnData.raw.html),
  [backed I/O](https://anndata.readthedocs.io/en/stable/generated/anndata.io.read_h5ad.html),
  [released source](https://github.com/scverse/anndata/tree/0.13.4).
- [Harmony](https://scanpy.readthedocs.io/en/stable/generated/scanpy.external.pp.harmony_integrate.html)
  changes `X_pca_harmony`, not X. Scanpy 1.12.4 still transposes `Z_corr`,
  but [harmonypy 2.0.2](https://github.com/slowkow/harmonypy) returns cells x PCs.
  The wrapper failed a native shape check; toolkit integration calls
  `harmonypy.run_harmony` directly, validates shape/finiteness, and stores
  `Z_corr` without transposition. Rebuild neighbors explicitly on it. 
  [BBKNN](https://scanpy.readthedocs.io/en/stable/generated/scanpy.external.pp.bbknn.html)
  replaces the neighbor graph; running ordinary neighbors afterward discards it.
  The CLI explicitly selects exact cKDTree (`approx=False, use_faiss=False`):
  native Annoy 1.17.3 returned too few neighbors on the tested macOS ARM/NumPy
  2.5 fixture. This is an observed backend limitation, not a universal BBKNN failure.
  ComBat changes X, may densify, and needs >=2 cells per batch; retain uncorrected
  log expression/raw counts for markers/DE. Integration cannot resolve perfectly
  confounded batch and condition. Optional Harmony/BBKNN runtime validation is
  separately reported; ordinary native tests do not establish integration quality.
- [DPT](https://scanpy.readthedocs.io/en/stable/generated/scanpy.tl.dpt.html) requires
  neighbors, diffusion components and a justified biological root. An arbitrary
  cluster zero is only an illustrative placeholder; pseudotime is not elapsed time.
- [ingest](https://scanpy.readthedocs.io/en/stable/generated/scanpy.tl.ingest.html)
  requires the same ordered gene axis and compatible preprocessing in query and
  reference, with reference neighbors/PCA/UMAP as requested. No atlas mapping was
  executed in this refresh.
- [R conversion](r_interop.md): official signatures were checked, but R system
  installation/Seurat/zellkonverter/SeuratDisk conversions were not run. zellkonverter
  manages its own supported Python environment; do not assume the local Scanpy
  environment is used. An unspecified X_name selects the first assay, not necessarily
  counts, so the example now requires a counts assay explicitly.

Dask, alternative file formats, optional integrations and trajectories each need
representative-data checks before production use. Small synthetic native tests
validate software contracts; they establish no biological annotation, batch
correction quality, calibrated DE error rate or cross-tool statistical equivalence.
