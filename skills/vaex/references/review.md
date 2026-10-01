# Release review and verification

Reviewed 2026-10-01 against current primary documentation, PyPI release metadata and
released source. This skill documents Vaex 4.19.0/core 4.19.0, HDF5 0.15.0, viz 0.6.0
and ML 0.19.0. The core wheel requires Python `>=3.9,<3.13`; meta-package version and
upload date alone do not establish interpreter or NumPy support.

## Native evidence

Python 3.12.10 on macOS ARM; NumPy 2.5.3, pandas 2.3.3, PyArrow 25.0.1,
Matplotlib 3.11.2, scikit-learn 1.9.1, Dask 2024.8.2, Numba 0.68.0,
XGBoost 3.4.1, LightGBM 4.7.0, CatBoost 1.2.10, cachetools 7.2.0.
Dependencies were installed in a separate environment, never the project environment.

The repository suite executes 23 runnable Python documentation blocks and additional
behavior checks (18 tests total): numerical expressions, filters/nulls/NaNs, population
variance, approximate percentiles, explicit grouped aggregators, grid orientation and
upper-edge exclusion, extracted joins with duplicate keys, async reductions, bounded
pandas conversion, cache controls, five local file formats, HDF5 group append, scalers,
encoders, PCA/projections, KMeans, sklearn full/incremental fits, three boosting adapters,
probability class axis, trusted model-state transfer without importing the training
filter, vectorized apply, and numerical Dask-array conversion. Histogram/scatter/grid
PNGs were rendered and visually checked for axes, labels, transposition and cropping.

The heatmap failure with current Matplotlib was reproduced: Vaex calls removed
`matplotlib.cm.get_cmap`. The documented fallback uses Vaex's bounded grid aggregation
and native Matplotlib `pcolormesh`; no monkeypatch or legacy plotting claim is made.
CatBoost's default Probability output was also observed on an RMSE-trained model;
regression checks explicitly use `RawFormulaVal`.

These tiny checks establish API mechanics and numerical invariants, not billion-row
performance, memory peaks, statistical calibration, model convergence or scientific validity.
Approximate percentiles need not match NumPy's interpolation convention. No data
were obtained from external scientific datasets and no cloud/server write occurred.

## Source-only boundaries

The installed contents of 23 core, HDF5, viz and ML modules were compared byte-for-byte
with the official `v4.19.0` tag and matched. Additional current server 0.10.0 and
Jupyter 0.9.0 wheel sources were inspected for commands/accessors. Their optional
integrations remain illustrative:

- S3/GCS filesystem handling and authentication-option routing were inspected;
  no authenticated cloud reads/writes, Azure integration or provider endpoint was tested.
- Vaex server uses `vaex server` and a named WebSocket DataFrame URL. No running
  server, TLS/auth deployment or Python-client round trip was validated. The skill
  does not invent REST endpoints or pagination semantics.
- Widget accessor names were checked in Jupyter source; no notebook frontend was tested.
- TensorFlow `KerasModel.fit` is intentionally unimplemented; inference-wrapper source
  was checked but no TensorFlow installation/training/inference/serialization was run.
- FITS/vaex-astro, arbitrary external HDF5 schemas, large remote data and other
  platforms remain unexecuted. Use small representative round trips before production use.

## Primary sources

- [Core 4.19.0 metadata and wheels](https://pypi.org/project/vaex-core/4.19.0/)
- [Vaex 4.19.0 meta-package](https://pypi.org/project/vaex/4.19.0/)
- [ML 0.19.0](https://pypi.org/project/vaex-ml/0.19.0/)
- [HDF5 0.15.0](https://pypi.org/project/vaex-hdf5/0.15.0/)
- [Viz 0.6.0](https://pypi.org/project/vaex-viz/0.6.0/)
- [Official tagged source](https://github.com/vaexio/vaex/tree/v4.19.0/packages)
- [API reference](https://vaex.io/docs/api.html)
- [I/O guide](https://vaex.io/docs/guides/io.html)
- [Missing values](https://vaex.io/docs/guides/missing_or_invalid_data.html)
- [Async execution](https://vaex.io/docs/guides/async.html)
- [Caching](https://vaex.io/docs/guides/caching.html)
- [Dask arrays](https://vaex.io/docs/guides/dask.html)
- [ML tutorial](https://vaex.io/docs/tutorial_ml.html)
- [Server guide](https://vaex.io/docs/guides/server.html)
- [Notebook integration](https://vaex.io/docs/tutorial_jupyter.html)
- [Matplotlib 3.9 API removals](https://matplotlib.org/stable/api/prev_api_changes/api_changes_3.9.0.html)

Earlier references mixed pandas/NumPy conventions with unsupported Vaex calls.
This refresh preserves the six existing capability areas, consolidates repeated
examples and removes unsupported APIs rather than claiming them as untested recipes.
