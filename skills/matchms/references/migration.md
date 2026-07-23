# Migration to matchms 0.33.1

Use this guide when adapting code written for older matchms releases or the
official tutorial notebooks last revised in 2024.

## Release Timeline That Affects This Skill

### 0.27.0 (2024-07-10)

- `add_losses()` was removed.
- Neutral losses moved to on-demand computation through `spectrum.losses` and
  `spectrum.compute_losses(...)`.
- public names and parameters began changing from `spectrums` to `spectra`;
  compatibility spellings were deprecated.
- Python support moved to 3.9-3.12 at that release.

### 0.29.x-0.30.x (2025)

- importers gained broader `pathlib.Path`/MGF file-like support and writer
  behavior was revised.
- NumPy 2 became the supported baseline.
- Python 3.13 support was added.

### 0.31.0 (2025-10-06)

- `FlashSimilarity` and `BlinkCosine` were added.
- `normalize_intensities(..., scaling=(low, high))` gained min-max scaling.
- `add_precursor_formula` and
  `remove_peaks_relative_to_precursor_mz` were added.

### 0.32.0 (2026-03-04)

- `ModifiedCosine` was renamed to `ModifiedCosineGreedy`.
- `ModifiedCosineHungarian` was added for exact assignment.

### 0.33.0-0.33.1 (2026-05-12 to 2026-06-08)

- `CosineLinear` was added.
- v1 cleanup/deprecation work began, including migration away from
  `add_fingerprint()`.
- Python 3.14 support was added.

## Required Code Changes

### Modified cosine class

Old:

```python
from matchms.similarity import ModifiedCosine

metric = ModifiedCosine(tolerance=0.02)
```

Current greedy behavior:

```python
from matchms.similarity import ModifiedCosineGreedy

metric = ModifiedCosineGreedy(tolerance=0.02)
```

Current exact assignment:

```python
from matchms.similarity import ModifiedCosineHungarian

metric = ModifiedCosineHungarian(tolerance=0.02)
```

Update score field names too:

```text
ModifiedCosine_score   -> ModifiedCosineGreedy_score
ModifiedCosine_matches -> ModifiedCosineGreedy_matches
```

### Neutral losses

Old:

```python
from matchms.filtering import add_losses

spectrum = add_losses(spectrum)
```

Current:

```python
losses = spectrum.losses
custom_losses = spectrum.compute_losses(
    loss_mz_from=5.0,
    loss_mz_to=200.0,
)
```

`NeutralLossesCosine` computes the needed losses directly; do not pre-add them.

### `SpectrumProcessor`

Old:

```python
processor = SpectrumProcessor(
    [
        normalize_intensities,
        lambda spectrum: select_by_relative_intensity(
            spectrum,
            intensity_from=0.01,
        ),
    ]
)
processed = [processor(spectrum) for spectrum in spectra]
```

Current:

```python
processor = SpectrumProcessor(
    [
        normalize_intensities,
        (select_by_relative_intensity, {"intensity_from": 0.01}),
    ]
)
processed, report = processor.process_spectra(
    spectra,
    progress_bar=False,
    create_report=False,
)
```

For one spectrum, call `processor.process_spectrum(spectrum)`.

The aggregate `default_filters` callable is not registered in
`SpectrumProcessor`'s built-in filter order. Run it before the processor or
expand its nine component filters; otherwise it is treated as custom and moved
after registered filters.

### Score access

Old assumptions:

```python
reference_index, score = scores.scores_by_query(query, sort=True)[0]
reference = references[reference_index]
numeric = scores.scores[j, i]
```

Current:

```python
score_name = "CosineGreedy_score"
reference, value = scores.scores_by_query(
    query,
    name=score_name,
    sort=True,
)[0]

numeric = float(value[score_name])
matches = int(value["CosineGreedy_matches"])
matrix = scores.to_array(score_name)
```

`Scores.scores` is a layered sparse container. Always inspect
`scores.score_names`.

### Metadata matching

Old:

```python
MetadataMatch(field="ionmode", matching_type="exact")
```

Current:

```python
MetadataMatch(field="ionmode", matching_type="equal_match")
```

Current matching types are `equal_match` and `difference`.

### High-peak requirement

Old:

```python
require_minimum_number_of_high_peaks(
    spectrum,
    n_required=5,
    intensity_threshold=0.05,
)
```

Current:

```python
require_minimum_number_of_high_peaks(
    spectrum,
    no_peaks=5,
    intensity_percent=5.0,
)
```

`intensity_percent` is expressed as a percentage.

### Top-k peak filter

Old examples may use a `ratio_desired` argument. Current:

```python
remove_peaks_outside_top_k(
    spectrum,
    k=6,
    mz_window=50,
)
```

For global peak-count reduction, use
`reduce_to_number_of_peaks(n_required=..., n_max=..., ratio_desired=...)`.

### Precursor upper bound

Old:

```python
require_precursor_below_mz(spectrum, maximum_accepted_mz=1000)
```

Current:

```python
require_precursor_mz(
    spectrum,
    minimum_accepted_mz=10.0,
    maximum_mz=1000.0,
)
```

`require_precursor_below_mz()` is deprecated.

### Parent-mass repair names

Older examples may refer to:

```text
repair_parent_mass_is_mol_wt
repair_adduct_based_on_smiles
```

Current public helpers include:

```text
repair_parent_mass_is_molar_mass
repair_adduct_and_parent_mass_based_on_smiles
repair_adduct_based_on_parent_mass
repair_parent_mass_from_smiles
```

Review semantics and supply required `mass_tolerance` arguments rather than
performing a mechanical rename.

### Fingerprints

Old:

```python
spectra = [add_fingerprint(spectrum, fingerprint_type="morgan2")
           for spectrum in spectra]
```

`add_fingerprint()` still works in 0.33.1 but is marked for removal in matchms
1.0. Forward-oriented preparation:

```python
from matchms import Fingerprints

fp_store = Fingerprints(
    fingerprint_algorithm="morgan2",
    fingerprint_method="bit",
    nbits=2048,
)
fp_store.compute_fingerprints(spectra)
```

Current `FingerprintSimilarity` still reads a `"fingerprint"` spectrum field.
When that class is needed in 0.33.1, bridge the store explicitly:

```python
for spectrum in spectra:
    fingerprint = fp_store.get_fingerprint_by_spectrum(spectrum)
    if fingerprint is not None:
        spectrum.set("fingerprint", fingerprint)
```

### Installation

Old:

```bash
uv pip install matchms[chemistry]
```

Current:

```bash
uv pip install "matchms==0.33.1"
```

The 0.33.1 package metadata has no `chemistry` extra and includes RDKit as a
regular dependency.

### Spectrum serialization

Old:

```python
from matchms.exporting import save_as_pickle

save_as_pickle(spectra, "spectra.pkl")
```

Current public pattern:

```python
from matchms.exporting import save_spectra

save_spectra(spectra, "trusted-cache.pickle")
```

`save_as_pickle` is not exported in 0.33.1. The generic writer recognizes
`.pickle`, not `.pkl`. Prefer portable MGF/MSP/JSON for exchanged data, and
never load untrusted pickle.

### Generic I/O and overwrite behavior

Prefer:

```python
from matchms.exporting import save_spectra
from matchms.importing import load_spectra

spectra = list(load_spectra("input.mgf"))
save_spectra(spectra, "output.msp")
```

`save_spectra()` refuses an existing output unless appending MGF/MSP data.
Direct `save_as_mgf()` and `save_as_msp()` default to append mode, so specify
write mode explicitly when bypassing the generic writer.

## Deprecated Compatibility Names

Replace these even if 0.33.1 still accepts some of them:

```text
spectrums             -> spectra
process_spectrums()   -> process_spectra()
import_spectrums()    -> import_spectra()
spectrums_queries     -> spectra_queries
spectrums_references  -> spectra_references
```

Do not suppress deprecation warnings globally; they are migration signals for
the forthcoming 1.0 API.

## Tutorial Caveat

The separate `matchms-docs` user-guide repository was last revised on
2024-06-13. Its pipeline/filtering explanations remain useful, but the tutorial
still contains examples using `ModifiedCosine` and older spelling. Prefer the
current Read the Docs API and release notes for symbol names and signatures.

## Migration Verification

After migration:

1. print `matchms.__version__` and confirm 0.33.1;
2. run imports with deprecation warnings visible;
3. inspect `processor.processing_steps`;
4. compare spectrum counts before/after processing;
5. print `scores.score_names`;
6. test one known spectrum pair and one query/library search;
7. compare old and new result rankings on a representative subset;
8. verify serialized outputs by reopening them; and
9. document any score changes caused by algorithm renaming, filtering, or
   dependency updates.
