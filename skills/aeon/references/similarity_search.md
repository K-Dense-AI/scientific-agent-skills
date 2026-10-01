# Similarity Search

Aeon 1.6 reorganized this experimental module. Use `MASS` and `NaiveSubsequenceSearch` from `aeon.similarity_search.subsequence`, and `SimHashIndexANN` or `NaiveSeriesSearch` from `aeon.similarity_search.whole_series`. The earlier `MassSNN`, `DummySNN`, `StompMotif`, and `RandomProjectionIndexANN` names are not public APIs in this release.

## Exact subsequence search

`fit` stores a collection shaped `(n_cases, n_channels, n_timepoints)`. A query is a single series shaped `(n_channels, length)`. `predict` returns indices first, distances second; each index row identifies `(case_index, window_start)`.

```python
import numpy as np
from aeon.similarity_search.subsequence import MASS

rng = np.random.default_rng(42)
X = rng.normal(size=(4, 1, 80))
query = X[0, :, 10:30].copy()
searcher = MASS(length=20, normalize=True).fit(X)
indices, distances = searcher.predict(query, k=3, X_index=(0, 10))
profiles = searcher.compute_distance_profile(query)
assert profiles.shape == (4, 61)
```

`MASS` uses Euclidean distance, optionally after z-normalizing each window; `normalize=False` is the default. It supports equal-length univariate/multivariate collections without missing values. Use `NaiveSubsequenceSearch` for supported alternative distances and as a correctness baseline.

Search controls:

- `X_index=(case, start)` excludes the query's own location and surrounding exclusion zone when it is part of the fitted collection.
- `allow_trivial_matches=False` suppresses nearby returned matches; it does not identify the query location automatically.
- `exclusion_factor=0.5` sets the exclusion radius to `int(length * exclusion_factor)` on either side. Set from domain knowledge, especially for periodic signals.
- `dist_threshold=value` limits matches to that distance. Fewer than `k` matches, including none, may be returned.
- `compute_distance_profile(query)` returns all window distances without applying query self-exclusion. Do not interpret its minimum as a nontrivial match without masking the query region.

Choose window length from expected event duration and validate several plausible lengths. There is no generally valid percentage of total recording length.

## Approximate whole-series search

```python
from aeon.similarity_search.whole_series import SimHashIndexANN

ann = SimHashIndexANN(n_tables=20, n_bits_per_table=4, random_state=42)
ann.fit(X)
indices, scores = ann.predict(X[0], k=3)
```

Queries must match the fitted channel count and whole-series length. These returned "distances" are **reciprocals of hash-table collision counts**, not Euclidean or cosine distances. Smaller values mean more collisions. The same stored series is eligible as a neighbor, and ties can prevent it being first. The index can return fewer than `k` candidates. Larger `n_tables` generally raises recall; larger `n_bits_per_table` reduces candidate counts. Measure recall against `NaiveSeriesSearch` on representative queries. `SimHashIndexANN` does not accept `X_index` or `dist_threshold`.

## Motifs and discords through a matrix profile

`MatrixProfileTransformer` in the series-transformations module wraps STUMPY and requires `stumpy`. It returns one nearest-neighbor distance per subsequence, with length `len(y) - window_length + 1`. Use the returned array: the transformer does not expose a populated nearest-neighbor-index attribute.

```python
import numpy as np
from aeon.transformations.series import MatrixProfileTransformer
from aeon.similarity_search.subsequence import MASS

rng = np.random.default_rng(42)
y = rng.normal(size=160)
y[100:120] = y[20:40]  # synthetic repeated motif
window = 20
profile = MatrixProfileTransformer(window_length=window).fit_transform(y)
start = int(np.argmin(profile))
discord_start = int(np.argmax(profile))

# Locate a nontrivial partner of the low-distance subsequence.
searcher = MASS(length=window, normalize=True).fit(y[None, None, :])
partners, distances = searcher.predict(
    y[None, start:start + window], k=1, X_index=(0, start),
    exclusion_factor=0.5,
)
```

A low profile value suggests a repeated pattern; a high value suggests a discord. These are candidates to inspect, not supervised labels. STUMPY's matrix-profile exclusion convention and the explicit MASS search exclusion radius differ; choose and document a consistent exclusion policy for a formal motif benchmark. For timepoint anomaly scores use `STOMP` as described in [anomaly_detection.md](anomaly_detection.md).

Sources: [current API](https://www.aeon-toolkit.org/en/stable/api_reference/similarity_search.html), [MASS](https://www.aeon-toolkit.org/en/stable/api_reference/auto_generated/aeon.similarity_search.subsequence.MASS.html), [SimHashIndexANN](https://www.aeon-toolkit.org/en/stable/api_reference/auto_generated/aeon.similarity_search.whole_series.SimHashIndexANN.html). All examples above were exercised with aeon 1.6 on synthetic data.
