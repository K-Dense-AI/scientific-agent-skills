# Filtering and Spectrum Processing (matchms 0.33.1)

Use this reference when building or debugging metadata-cleaning, peak-processing,
or quality-control pipelines. The authoritative API is the matchms
[`filtering` package](https://matchms.readthedocs.io/en/latest/api/matchms.filtering.html).

## Filter Contract

Most matchms filters:

- accept one `Spectrum` as the first argument;
- return a `Spectrum` or `None`;
- default to `clone=True`, so direct calls usually return a modified copy;
- use `None` to indicate that a `require_*` condition failed; and
- should be assigned back when called directly.

```python
spectrum = normalize_intensities(spectrum)
spectrum = require_minimum_number_of_peaks(spectrum, n_required=5)
if spectrum is None:
    # The spectrum failed a quality requirement.
    ...
```

Do not continue passing `None` through ordinary filters. `SpectrumProcessor`
stops the chain and discards rejected spectra for you.

## Prefer `SpectrumProcessor`

`SpectrumProcessor` accepts:

- a built-in filter name such as `"normalize_intensities"`;
- a callable such as `normalize_intensities`; or
- `(filter, parameter_dict)`, where `filter` can be a name or callable.

Built-in filters are automatically sorted into matchms's required filter order.
Custom filters are appended unless an explicit position is supplied with
`parse_and_add_filter()`.

```python
from matchms import SpectrumProcessor
from matchms.filtering import (
    default_filters,
    normalize_intensities,
    remove_peaks_relative_to_precursor_mz,
    require_minimum_number_of_peaks,
    require_precursor_mz,
    select_by_mz,
    select_by_relative_intensity,
)

# Run the aggregate metadata harmonizer before SpectrumProcessor. If included as
# one callable inside the processor, it is treated as custom and placed last.
spectra = [default_filters(spectrum) for spectrum in spectra]

processor = SpectrumProcessor(
    [
        (require_precursor_mz, {"minimum_accepted_mz": 50.0, "maximum_mz": 1500.0}),
        normalize_intensities,
        (remove_peaks_relative_to_precursor_mz, {"offset_to_precursor": -1.6}),
        (select_by_mz, {"mz_from": 20.0, "mz_to": 1500.0}),
        (select_by_relative_intensity, {"intensity_from": 0.01}),
        (require_minimum_number_of_peaks, {"n_required": 5}),
    ]
)

cleaned, report = processor.process_spectra(
    spectra,
    progress_bar=False,
    create_report=False,
)
print(processor.processing_steps)
```

Important current behavior:

- `SpectrumProcessor` is **not callable**.
- Use `processor.process_spectrum(spectrum)` for one spectrum.
- Use `processor.process_spectra(spectra)` for a list.
- `process_spectra()` returns `(processed_spectra, processing_report)`.
- With `create_report=False`, the processor clones each input once and disables
  per-filter cloning where supported.
- With `create_report=True`, filters are cloned step by step to measure changes.
  The aggregate `default_filters` function is not in the processor's built-in
  order registry and does not expose a `clone` parameter. If passed directly,
  it is placed after registered filters and detailed reporting logs a warning.
  Run it before the processor or expand it into the nine filters below.
- `process_spectrums()` is a deprecated spelling.

## What `default_filters()` Does

In 0.33.1, `default_filters()` applies exactly:

1. `make_charge_int`
2. `add_compound_name`
3. `derive_adduct_from_name`
4. `derive_formula_from_name`
5. `clean_compound_name`
6. `interpret_pepmass`
7. `add_precursor_mz`
8. `derive_ionmode`
9. `correct_charge`

It does **not** normalize peaks, add retention fields, harmonize structural
identifiers, require precursor metadata, or enforce peak-count quality. Add
those steps explicitly.

## Peak Processing

### Normalize and select peaks

- `normalize_intensities(spectrum_in, clone=True, scaling=None)` — normalize to
  maximum intensity 1 by default; pass `scaling=(low, high)` for min-max scaling.
- `select_by_intensity(spectrum_in, intensity_from=10.0, intensity_to=200.0,
  clone=True)` — keep an absolute intensity interval.
- `select_by_relative_intensity(spectrum_in, intensity_from=0.0,
  intensity_to=1.0, clone=True)` — keep a fraction-of-maximum interval.
- `select_by_mz(spectrum_in, mz_from=0.0, mz_to=1000.0, clone=True)` — crop the
  fragment m/z interval.

Normalize before using relative-intensity thresholds.

### Reduce and clean peaks

- `reduce_to_number_of_peaks(spectrum_in, n_required=0, n_max=inf,
  ratio_desired=None, clone=True)` — keep the most intense peaks within count
  constraints.
- `remove_noise_below_frequent_intensities(spectrum_in,
  min_count_of_frequent_intensities=5, noise_level_multiplier=2.0, clone=True)`
  — estimate and remove repeated low-intensity noise.
- `remove_peaks_around_precursor_mz(spectrum_in, mz_tolerance=17, clone=True)`
  — remove peaks within a precursor-centered exclusion window.
- `remove_peaks_relative_to_precursor_mz(spectrum_in,
  offset_to_precursor=-1.6, clone=True)` — remove peaks above a cutoff relative
  to precursor m/z.
- `remove_peaks_outside_top_k(spectrum_in, k=6, mz_window=50, clone=True)` —
  retain peaks that lie near one of the `k` most intense local peaks.
- `remove_profiled_spectra(spectrum_in, mz_window=0.5, clone=True)` — reject
  spectra likely to contain profile-mode rather than centroided data.

These defaults are starting points, not instrument-independent truth. Record
chosen windows and thresholds.

### Peak quality requirements

- `require_minimum_number_of_peaks(spectrum_in, n_required=10,
  ratio_required=None, clone=True)`
- `require_maximum_number_of_peaks(spectrum_in,
  maximum_number_of_fragments=1000, clone=True)`
- `require_minimum_number_of_high_peaks(spectrum_in, no_peaks=5,
  intensity_percent=2.0, clone=True)`

Older examples commonly use invalid
`require_minimum_number_of_high_peaks(n_required=..., intensity_threshold=...)`
arguments. In 0.33.1 the names are `no_peaks` and `intensity_percent`, where the
latter is a percentage rather than a 0-1 fraction.

## Precursor, Adduct, Charge, and Ion Mode

- `interpret_pepmass(spectrum_in, clone=True)`
- `add_precursor_mz(spectrum_in, clone=True)`
- `add_parent_mass(spectrum_in, estimate_from_adduct=True,
  overwrite_existing_entry=False, estimate_from_charge=True, clone=True)`
- `add_precursor_formula(spectrum_in, clone=True)`
- `make_charge_int(spectrum_in, clone=True)`
- `correct_charge(spectrum_in, clone=True)`
- `clean_adduct(spectrum_in, clone=True)`
- `derive_adduct_from_name(spectrum_in, remove_adduct_from_name=True,
  clone=True)`
- `derive_ionmode(spectrum_in, clone=True)`
- `require_correct_ionmode(spectrum_in, ion_mode_to_keep)`
- `require_matching_adduct_and_ionmode(spectrum)`
- `require_matching_adduct_precursor_mz_parent_mass(spectrum, tolerance=0.1)`
- `require_precursor_mz(spectrum_in, minimum_accepted_mz=10.0,
  maximum_mz=None, clone=True)`

`require_precursor_below_mz()` is deprecated. Use
`require_precursor_mz(maximum_mz=...)`.

Modified-cosine and neutral-loss scoring require a valid `precursor_mz`.
Parent-mass matching additionally requires a valid `parent_mass`.

## Compound Names, Formulae, and Structures

### Name and formula processing

- `add_compound_name(spectrum_in, clone=True)`
- `clean_compound_name(spectrum_in, clone=True)`
- `derive_formula_from_name(spectrum_in, remove_formula_from_name=True,
  clone=True)`
- `derive_formula_from_smiles(spectrum_in, overwrite=True, clone=True)`
- `require_compound_name(spectrum)`
- `require_formula(spectrum)`

### SMILES, InChI, and InChIKey

- `derive_inchi_from_smiles(spectrum_in, clone=True)`
- `derive_inchikey_from_inchi(spectrum_in, clone=True)`
- `derive_smiles_from_inchi(spectrum_in, clone=True)`
- `harmonize_undefined_inchi(...)`
- `harmonize_undefined_inchikey(...)`
- `harmonize_undefined_smiles(...)`
- `repair_inchi_inchikey_smiles(spectrum_in, clone=True)`
- `repair_not_matching_annotation(spectrum_in, clone=True)`
- `require_valid_annotation(spectrum)`

`derive_annotation_from_compound_name()` can query PubChem. It introduces
network dependence, name ambiguity, and external-service variability; cache or
export the resulting annotations and retain provenance.

### Structure/mass repair

Current repair helpers include:

- `repair_adduct_and_parent_mass_based_on_smiles`
- `repair_adduct_based_on_parent_mass`
- `repair_parent_mass_from_smiles`
- `repair_parent_mass_is_molar_mass`
- `repair_parent_mass_match_smiles_wrapper`
- `repair_smiles_of_salts`
- `require_parent_mass_match_smiles`

Several require an explicit `mass_tolerance`. Do not silently "repair" library
annotations without preserving original fields and logging the rule used.

## Retention and MS-Level Metadata

- `add_retention_time(spectrum_in, clone=True)`
- `add_retention_index(spectrum_in, clone=True)`
- `require_retention_time(spectrum_in, minimum_rt=None, maximum_rt=None,
  clone=True)`
- `require_retention_index(spectrum_in, clone=True)`
- `require_correct_ms_level(spectrum, required_ms_level=2)`

Retention time and retention index are not interchangeable. Record units and
the chromatographic method before using either as a matching constraint.

## Fingerprints

`add_fingerprint()` still works in 0.33.1, but it is marked for removal in
matchms 1.0. Prefer the top-level `Fingerprints` class:

```python
from matchms import Fingerprints

fingerprints = Fingerprints(
    fingerprint_algorithm="morgan2",
    fingerprint_method="bit",
    nbits=2048,
)
fingerprints.compute_fingerprints(spectra)
```

`Fingerprints` maps valid InChIKeys to fingerprints and needs a valid InChIKey
plus SMILES or InChI. In 0.33.1, `FingerprintSimilarity` still reads a
`"fingerprint"` field from each spectrum, so bridge deliberately when that
legacy similarity class is needed:

```python
for spectrum in spectra:
    fingerprint = fingerprints.get_fingerprint_by_spectrum(spectrum)
    if fingerprint is not None:
        spectrum.set("fingerprint", fingerprint)
```

Do not describe fingerprint similarity as spectral similarity.

## Custom Filters

A custom filter should accept a spectrum first and return a spectrum or `None`:

```python
def require_fragment(spectrum_in, fragment_mz, tolerance=0.02):
    if spectrum_in is None:
        return None
    if any(abs(mz - fragment_mz) <= tolerance for mz in spectrum_in.peaks.mz):
        return spectrum_in
    return None


processor.parse_and_add_filter(
    (require_fragment, {"fragment_mz": 184.0733, "tolerance": 0.01})
)
```

Avoid mutation unless it is intentional and documented. If the custom filter
modifies a spectrum, either implement a `clone` parameter consistently or clone
inside the function.

## Reproducibility Checklist

- Save `processor.processing_steps`.
- Record matchms and Python versions.
- Record whether metadata harmonization was enabled at import.
- Apply identical peak filters to query and reference collections.
- Preserve counts before and after every requirement filter.
- Preserve original metadata before repair/enrichment.
- Record network calls and external annotation sources.
- Test a few spectra with expected pass/fail behavior before batch processing.
