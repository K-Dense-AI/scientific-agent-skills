# Similarity and Scores (matchms 0.33.1)

Use this reference to select a similarity class, interpret its output, extract
top hits, or scale a comparison. The authoritative API is
[`matchms.similarity`](https://matchms.readthedocs.io/en/latest/api/matchms.similarity.html).

## Core Calculation

```python
from matchms import calculate_scores
from matchms.similarity import CosineGreedy

metric = CosineGreedy(tolerance=0.02)
scores = calculate_scores(
    references=reference_spectra,
    queries=query_spectra,
    similarity_function=metric,
    array_type="numpy",
    is_symmetric=False,
)
```

Set `is_symmetric=True` only when references and queries are the same collection
in the same order and the metric is symmetric.

## Understand the Output Before Indexing

`Scores.scores` is a `sparsestack.StackedSparseArray`, not a plain two-dimensional
NumPy array. Its shape is `(n_references, n_queries, n_score_fields)`.

Cosine-family methods produce two fields:

```python
print(scores.score_names)
# ('CosineGreedy_score', 'CosineGreedy_matches')

similarities = scores.to_array("CosineGreedy_score")
matched_peaks = scores.to_array("CosineGreedy_matches")
```

Scalar methods such as `FlashSimilarity`, `PrecursorMzMatch`, and
`FingerprintSimilarity` produce one field named after the class.

### Top hits for one query

```python
score_name = "CosineGreedy_score"
matches_name = "CosineGreedy_matches"

ranked = scores.scores_by_query(query_spectrum, name=score_name, sort=True)
for reference, value in ranked[:10]:
    print(
        reference.get("spectrum_id"),
        float(value[score_name]),
        int(value[matches_name]),
    )
```

The first tuple item is the actual reference `Spectrum`, not an integer index.
The second item can be a structured NumPy record containing every score field.

### Iterate stored pairs

```python
for reference, query, values in scores:
    print(reference.get("id"), query.get("id"), values)
```

Iteration covers stored coordinates. After sparse filtering, that may be only a
subset of the Cartesian product.

## Peak-Based Cosine Methods

All cosine classes below use:

```text
tolerance=0.1, mz_power=0.0, intensity_power=1.0
```

unless noted otherwise. Tolerance is in daltons for these classes.

### `CosineGreedy`

Greedily assigns candidate peak pairs within tolerance.

Use for:

- routine spectral-library comparisons;
- a transparent baseline;
- moderate collections where exact assignment is not essential.

Output fields: `CosineGreedy_score`, `CosineGreedy_matches`.

### `CosineHungarian`

Uses optimal assignment rather than greedy assignment.

Use for:

- benchmarking peak-assignment effects;
- smaller datasets;
- cases where greedy ambiguity materially affects results.

It is computationally more expensive than `CosineGreedy`.

### `CosineLinear`

Added in 0.33.0 as a linear-scaling cosine implementation.

Use when:

- cosine is the intended metric;
- matrix size makes assignment cost important; and
- you have benchmarked agreement and runtime on representative spectra.

Output fields: `CosineLinear_score`, `CosineLinear_matches`.

## Modified Cosine

Modified cosine allows unshifted peak matches and matches shifted by the
difference in precursor m/z. Both spectra need valid `precursor_mz`.

### `ModifiedCosineGreedy`

```python
from matchms.similarity import ModifiedCosineGreedy

metric = ModifiedCosineGreedy(tolerance=0.02)
```

This is the current name for the implementation formerly called
`ModifiedCosine`. It uses greedy assignment.

### `ModifiedCosineHungarian`

```python
from matchms.similarity import ModifiedCosineHungarian

metric = ModifiedCosineHungarian(tolerance=0.02)
```

Use for exact modified-cosine assignment in benchmarks or method development.
It is slower than the greedy variant.

Do not infer that a shifted match proves a specific chemical transformation.
Inspect precursor delta, adduct/charge compatibility, shifted peaks, and
orthogonal annotations.

## Neutral-Loss Cosine

```python
from matchms.similarity import NeutralLossesCosine

metric = NeutralLossesCosine(
    tolerance=0.02,
    ignore_peaks_above_precursor=True,
)
```

`NeutralLossesCosine` computes losses from `precursor_mz - fragment_mz`.
Both spectra require precursor m/z. Do not call the removed `add_losses()`
filter; losses are computed on demand in current matchms.

Output fields: `NeutralLossesCosine_score`,
`NeutralLossesCosine_matches`.

## Fast Matrix-Oriented Methods

### `BlinkCosine`

BLINK-style approximate cosine:

```python
from matchms.similarity import BlinkCosine

metric = BlinkCosine(
    tolerance=0.01,
    bin_width=0.001,
    min_relative_intensity=0.01,
    top_k=None,
    batch_size=1024,
    sparse_score_min=0.0,
)
```

Important parameters include peak preprocessing, precursor cropping, batch
size, and sparse score minimum. Output contains a float32 score and matched-peak
count. Validate approximation behavior against `CosineGreedy` on a subset
before changing production workflows.

### `FlashSimilarity`

Fast matrix scoring based on the Flash Entropy approach:

```python
from matchms.similarity import FlashSimilarity

entropy = FlashSimilarity(
    score_type="spectral_entropy",
    matching_mode="fragment",
    tolerance=0.02,
)

fast_modified_cosine = FlashSimilarity(
    score_type="cosine",
    matching_mode="hybrid",
    tolerance=0.02,
)
```

Current choices:

- `score_type`: `spectral_entropy` or `cosine`
- `matching_mode`: `fragment`, `neutral_loss`, or `hybrid`
- optional preprocessing: precursor removal, noise cutoff, peak merging, dtype,
  and identity precursor tolerance

`pair()` exists but emits a warning because it is not the optimized use. Call
`calculate_scores()` so matchms uses the matrix path. Flash output is a scalar
field named `FlashSimilarity`, not a score/matches pair.

### `BinnedEmbeddingSimilarity`

```python
from matchms.similarity import BinnedEmbeddingSimilarity

metric = BinnedEmbeddingSimilarity(
    similarity="cosine",
    max_mz=1005,
    bin_width=1.0,
    intensity_power=1.0,
)
```

This creates fixed-width binned spectral embeddings. Bin width controls both
resolution and dimensionality. The class also supports approximate-neighbor
indexing through the current PyNNDescent backend; use it only after checking
recall against exact neighbors.

## Candidate and Metadata Matches

These methods are useful as gates or additional evidence. They are not
substitutes for peak-pattern similarity.

### `PrecursorMzMatch`

```python
from matchms.similarity import PrecursorMzMatch

absolute = PrecursorMzMatch(tolerance=0.02, tolerance_type="Dalton")
relative = PrecursorMzMatch(tolerance=10, tolerance_type="ppm")
```

Output field: `PrecursorMzMatch` (boolean).

### `ParentMassMatch`

```python
from matchms.similarity import ParentMassMatch

metric = ParentMassMatch(tolerance=0.02)
```

Requires `parent_mass`. Output field: `ParentMassMatch` (boolean). The current
constructor does not expose a ppm mode.

### `MetadataMatch`

```python
from matchms.similarity import MetadataMatch

same_mode = MetadataMatch(field="ionmode", matching_type="equal_match")
near_rt = MetadataMatch(
    field="retention_time",
    matching_type="difference",
    tolerance=0.2,
)
```

Current matching types are `equal_match` and `difference`. Older examples that
use `matching_type="exact"` are invalid.

### `IntersectMz`

`IntersectMz(scaling=1.0)` is a simple m/z-intersection score useful in tests or
specialized workflows. It is not a drop-in replacement for tolerance-aware,
intensity-weighted spectral scoring.

## Molecular Fingerprint Similarity

`FingerprintSimilarity` compares molecular fingerprints derived from known
structures. It therefore measures structure similarity, not spectral
similarity.

```python
from matchms import Fingerprints, calculate_scores
from matchms.similarity import FingerprintSimilarity

fp_store = Fingerprints(
    fingerprint_algorithm="morgan2",
    fingerprint_method="bit",
    nbits=2048,
)
fp_store.compute_fingerprints(spectra)

usable = []
for spectrum in spectra:
    fingerprint = fp_store.get_fingerprint_by_spectrum(spectrum)
    if fingerprint is not None:
        spectrum.set("fingerprint", fingerprint)
        usable.append(spectrum)

scores = calculate_scores(
    usable,
    usable,
    FingerprintSimilarity(similarity_measure="jaccard"),
    is_symmetric=True,
)
```

Similarity measures are `jaccard`, `dice`, and `cosine`.

The old `add_fingerprint()` filter still satisfies the 0.33.1
`FingerprintSimilarity` interface, but it is marked for removal in matchms 1.0.
The `Fingerprints` bridge above avoids calling that deprecated filter while
remaining compatible with the current similarity class.

## Efficient Precursor-Gated Search

Filter score coordinates before calculating an expensive spectral metric:

```python
from matchms import calculate_scores
from matchms.similarity import ModifiedCosineGreedy, PrecursorMzMatch

scores = calculate_scores(
    references,
    queries,
    PrecursorMzMatch(tolerance=10, tolerance_type="ppm"),
    array_type="sparse",
)
scores.filter_by_range(name="PrecursorMzMatch", low=0.5)
scores.calculate(
    ModifiedCosineGreedy(tolerance=0.02),
    array_type="sparse",
    join_type="left",
)
```

After `filter_by_range`, the second calculation can operate on retained
coordinates. Confirm `scores.score_names` and stored-coordinate counts after
each stage. An overly narrow precursor gate can remove valid analogs or
different adducts.

The `Pipeline` class formalizes the same pattern and can persist a YAML
workflow. See `workflows.md`.

## Filtering and Exporting Scores

```python
print(scores.score_names)

scores.filter_by_range(
    name="ModifiedCosineGreedy_score",
    low=0.6,
    above_operator=">=",
)

dense = scores.to_array("ModifiedCosineGreedy_score")
coo = scores.to_coo("ModifiedCosineGreedy_score")
scores.to_json("scores.json")
```

`filter_by_range()` mutates the stored score coordinates. Preserve an unfiltered
copy or serialize first when alternative thresholds must be compared.

Dense arrays require memory proportional to
`n_references * n_queries`. A sparse container is most useful only when a mask
or score threshold leaves relatively few stored pairs.

## Combining Metrics

Do not directly index `scores.scores[j, i]` and assume a scalar. Extract named
layers:

```python
cosine = scores.to_array("CosineGreedy_score")
matches = scores.to_array("CosineGreedy_matches")
```

If combining metrics:

- define whether missing/filtered pairs are zero, missing, or excluded;
- normalize only when score semantics justify it;
- fit or justify weights on an appropriate validation set;
- avoid leaking query identities into tuning;
- retain each component score in the output; and
- report the exact formula and package version.

## Interpretation Checklist

- Was identical preprocessing applied to references and queries?
- Is the tolerance appropriate for the instrument and calibration?
- Are precursor m/z, charge, ion mode, and adduct metadata valid?
- How many peaks matched, and what fraction of each spectrum do they represent?
- Is the hit driven by one dominant/common fragment?
- Are collision energy and acquisition conditions comparable?
- Is the query actually present in the searched library?
- Was the threshold validated on representative positives and negatives?
- Has the top hit been inspected with a mirror plot?

A high score ranks a candidate under a chosen metric. It does not, by itself,
establish compound identity.
