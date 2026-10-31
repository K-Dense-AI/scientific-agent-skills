# Proteomics and Metabolomics Formats

**Reviewed:** 2026-09-30
**Executable scope:** No omics-native standard is parsed by bundled scripts.
Rectangular CSV/TSV result exports can use the general tabular CLIs after the
schema, units, and missing/censoring codes are confirmed.

## Exact capability boundary

| Format | Bundled native inspection | Status |
|---|---|---|
| mzML/mzXML, vendor RAW | No | Reference-only MS tooling; see `spectroscopy_analytical_formats.md` |
| mzIdentML (`.mzid`, `.mzIdentML`) | No | Reference-only PSI schema/CV-aware tooling |
| mzTab 1.0 / mzTab-M 2.0 | No | Reference-only version-aware validator; generic TSV parsing is insufficient |
| pepXML/protXML | No | Reference-only search/inference-aware parser |
| featureXML/consensusXML/idXML | No | Reference-only OpenMS tooling |
| Rectangular `.csv`/`.tsv` feature or abundance table | General scripts | Bounded aggregate tabular EDA, no omics semantics |
| `.h5`/`.hdf5` | Generic metadata only | No payload values or convention validation |
| `.h5ad`, `.loom` | No semantic support | See bioinformatics reference |
| Pickled models/results | **Never** | Request non-executable export |

Unknown formats fail closed. No format is identified from free-text metadata or
content guessing.

## mzML and raw spectra

mzML is a HUPO-PSI standard for spectra/chromatograms; use PSI-aware tooling.
Vendor RAW extensions are ambiguous and often require vendor libraries or
conversion. Preserve originals and record converter, version, options, and
checksums.

For spectral EDA, inventory:

- acquisition method, instrument, polarity, MS levels, scan modes, precursor
  isolation/activation, resolution, and centroid/profile status;
- run order, batches, blanks, pooled QC, standards, carryover, drift, and
  calibration;
- spectrum/chromatogram counts, retention/mobility ranges, m/z coverage, TIC/
  BPC, peak counts, and missing/corrupt scans; and
- processing history, controlled-vocabulary terms, source files, and units.

Do not automatically centroid, denoise, recalibrate, align, peak-pick, or
discard spectra.

## Identification formats

### mzIdentML

mzIdentML represents peptide/protein identification results, scores, search
parameters, databases, modifications, and links to spectra using controlled
vocabularies. Validate the schema and CV mapping with PSI-aware tooling.

Check:

- search engine/version, sequence database/version, decoy strategy, enzyme,
  tolerances, fixed/variable modifications, and spectrum references;
- score direction/meaning, rank, charge, mass error, peptide-spectrum matches,
  peptides, proteins, and protein groups;
- target/decoy and FDR method at each reported level; and
- ambiguity from shared peptides, indistinguishable proteins, and inference.

A score threshold is not automatically a validated FDR threshold. Do not
recompute or reinterpret confidence without the method and decoy design.

### pepXML/protXML

These formats are Trans-Proteomic Pipeline conventions. Use Pyteomics or TPP
tools with the generating software/version known. Preserve search-engine,
PeptideProphet/ProteinProphet, modification, decoy, and inference context.

## mzTab and mzTab-M

HUPO-PSI lists:

- mzTab 1.0.0 as the final proteomics release (accepted June 2014); and
- mzTab-M 2.0.0 as the final metabolomics/small-molecule release (accepted
  March 2019).

mzTab-M 2.1.0 is listed as draft, not a final standard. Do not silently treat
it as 2.0. The draft has moved to the separate
[HUPO-PSI/mzTab-M repository](https://github.com/HUPO-PSI/mzTab-M); the released
2.0 materials remain in HUPO-PSI/mzTab.

Although mzTab is tab-delimited, it has section-specific row types, metadata,
controlled vocabulary, optional columns, and null conventions. The generic
rectangular TSV scanner is not a validator and will reject legitimate
non-rectangular section structure. Use the PSI specification/reference
validator, then export a controlled rectangular analysis table if needed.

## Rectangular quantitative tables

Common outputs contain features/peptides/proteins/metabolites in rows and
samples in columns, or long-form measurements. Before using general CLIs,
create a data dictionary that records:

- row entity and identifier namespace/version;
- sample/subject/specimen, condition, batch, injection order, and QC role;
- abundance scale (raw intensity, area, count, ratio, normalized/logged);
- zero, missing, censored, filtered, not-identified, and not-quantified codes;
- normalization, transformation, imputation, roll-up, and batch correction
  already applied;
- internal standards, dilution, LOD/LOQ, blank subtraction, and detection
  frequency; and
- peptide-to-protein or feature-to-metabolite ambiguity.

Do not assume zeros are measured zeros. Missingness is often abundance-,
feature-, batch-, or identification-dependent and may be non-random.

### Safe commands

```bash
python scripts/tabular_profile.py abundance.csv \
  --root /approved/project \
  --missing-token NA \
  --max-rows 100000

python scripts/missingness_leakage_audit.py abundance.csv \
  --root /approved/project \
  --group-column condition \
  --entity-column subject_id \
  --split-column split \
  --time-column acquisition_time

python scripts/distribution_sensitivity.py abundance.csv \
  --root /approved/project \
  --column intensity
```

The column arguments are exact local identifiers; output tokenizes them unless
`--reveal-identifiers` is explicit. Values and subject/sample identifiers are
not emitted.

## Missingness, censoring, and limits

Separate at least:

- structurally absent/not applicable;
- not detected;
- detected below quantitation;
- failed identification or confidence filter;
- failed extraction/integration;
- filtered during preprocessing;
- saturated/above range; and
- genuinely missing metadata.

Preserve flags and limits in separate columns. Do not automatically replace
non-detects with zero, half-minimum, LOD/2, or a random draw. Report missing/
censored fractions by feature, sample, condition, batch, and run order, and
compare conclusions across scientifically justified handling strategies.

## Distribution and outlier sensitivity

For abundance tables:

- inspect sample totals/detection rates and feature detection frequency;
- compare raw-scale and scientifically justified log/variance-stabilizing
  diagnostics without overwriting raw data;
- compare mean/SD with median/IQR/MAD and leave-one-sample/batch sensitivity;
- investigate outliers against blank/QC/internal-standard performance,
  acquisition order, contamination, carryover, and sample handling; and
- preserve excluded samples/features with reasons and show sensitivity.

PCA/clustering can reveal structure but is not proof of batch, identity, or
biological separation. Fit transformations and feature selection on training
data only.

## Design, leakage, and inference

1. Define the independent experimental unit; technical injections, spectra,
   peptides, or features are usually not independent subjects.
2. Preserve subject/sample pairing, repeated measures, batches, sites, and
   acquisition order.
3. Split by subject/specimen/batch/time before normalization, imputation,
   feature selection, PCA, or model tuning.
4. Ensure spectra/peptides/features derived from one sample do not cross
   train/test boundaries.
5. Distinguish QC, blank, pooled, calibrator, and biological samples.
6. Treat identification/feature discovery and differential testing as separate
   selection stages when assessing error rates.
7. Define the hypothesis family (features, contrasts, endpoints) and report
   effect sizes/uncertainty plus an appropriate FWER/FDR method.
8. Label discoveries from EDA as exploratory and confirm on independent data.
9. Do not make biomarker, diagnostic, mechanism, exposure, or causal claims
   from descriptive patterns.

## HDF5 and related containers

The generic HDF5 inspector reports only bounded hierarchy/dataset metadata. It
does not:

- read spectra, abundance matrices, annotations, or attributes;
- follow soft/external links or external dataset storage;
- validate mzMLb, H5AD, Loom, or vendor schemas; or
- invoke filter plugins for dataset decompression.

Use the convention's official reader/validator for semantics. NumPy object
arrays and all pickle-based objects are rejected.

## Authoritative sources

Current parser APIs and format guidance reviewed 2026-09-30. Historical
methodology citations are retained as source context.

- HUPO-PSI, [mzML specification/status](https://www.psidev.info/mzml)
  (mzML 1.1.0 long-term stable).
- HUPO-PSI, [mzIdentML](https://www.psidev.info/mzidentml).
- HUPO-PSI, [mzTab specifications](https://www.psidev.info/mztab-specifications)
  (page updated 2024-04-19; mzTab 1.0.0 final, mzTab-M 2.0.0 final,
  mzTab-M 2.1.0 draft).
- HUPO-PSI, [mzTab repository and released specifications](https://github.com/HUPO-PSI/mzTab).
- Hoffmann et al. (2019), [mzTab-M 2.0](https://doi.org/10.1021/acs.analchem.8b04310),
  published 2019-01-28.
- Pyteomics, [formats documentation](https://pyteomics.readthedocs.io/en/latest/).
- OpenMS, [recognized file types](https://openms.de/documentation/structOpenMS_1_1FileTypes.html).
- US EPA, [Detection Limits Best Practices Guide](https://www.epa.gov/system/files/documents/2025-09/wqxdetectionlimitsbestpracticesguide_final.pdf),
  dated August 2025.
- FDA/ICH E9(R1), [sensitivity analysis guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e9r1-statistical-principles-clinical-trials-addendum-estimands-and-sensitivity-analysis-clinical),
  final May 2021.
- Benjamini and Hochberg (1995), [FDR control](https://academic.oup.com/jrsssb/article/57/1/289/7035855).
- scikit-learn, [data leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html).
