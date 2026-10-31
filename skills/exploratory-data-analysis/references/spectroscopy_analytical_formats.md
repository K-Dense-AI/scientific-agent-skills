# Spectroscopy and Analytical Chemistry Formats

**Reviewed:** 2026-09-30
**Executable scope:** No spectroscopy-native parser is bundled. General
CSV/TSV/JSON/NumPy/HDF5 inspectors apply only when a file is truly one of those
registered formats and do not add spectroscopy semantics.

## Capability boundary

| Format | Bundled native inspection | Status |
|---|---|---|
| mzML/mzXML, MGF | No | Reference-only MS tooling |
| JCAMP-DX (`.jdx`, `.dx`) | No | Reference-only technique/version-aware parser |
| SPC and vendor spectroscopy binaries | No | Reference-only producer-specific parser |
| Vendor `.raw`, `.d`, `.fid`, `.dat`, `.out` | No | Ambiguous suffix/path; producer and format must be confirmed |
| CSV/TSV exports | General tabular scripts | Bounded aggregates only after delimiter, units, axes, and missing codes are confirmed |
| NPY/NPZ/HDF5 exports | General container scripts | Structural/bounded numeric inspection only; no instrument semantics |

Unknown formats fail closed. Directory-based acquisitions are rejected by the
regular-file CLIs. No archive or compressed stream is unpacked.

## mzML and related mass-spectrometry formats

HUPO-PSI identifies mzML 1.1.0 as the long-term stable format; its index schema
and controlled vocabulary continue to receive compatible updates. mzML is XML
with encoded binary arrays and controlled-vocabulary metadata. The current
official links use main schema 1.1.1 and optional indexed wrapper 1.1.3; distinguish
the stable specification from schema revision numbers. The IM-MS/DIA proposal
updated August 2026 has not yet entered the PSI Document Process. A generic XML
parser is not sufficient. Use a local validator: PSI reports the former online
validators no longer function.

Use pinned pymzML, Pyteomics, OpenMS, or ProteoWizard tooling and inspect:

- schema/version, controlled-vocabulary terms, source files, checksums, and
  conversion software;
- run/instrument configuration, polarity, scan modes, MS levels, isolation,
  activation, and data processing;
- spectrum/chromatogram counts, retention/mobility time, m/z and intensity
  array lengths, precision, compression, and units;
- profile versus centroid data, TIC/BPC, calibration, lock mass, blanks, pooled
  QC, standards, carryover, drift, and batch order; and
- truncated scans, empty arrays, non-finite values, and metadata consistency.

Do not describe mzXML, mzData, mzMLb, or vendor RAW as equivalent to mzML.
Conversion can alter metadata, precision, centroiding, and compression; record
the converter/version/options and retain the original.

## JCAMP-DX

IUPAC describes JCAMP-DX as a family of standards for spectral data exchange.
It has technique- and version-specific specifications (IR, NMR, MS, IMS, and
others). Choose the applicable published recommendation instead of assuming
all JCAMP files share one interchangeable schema.

Before parsing, identify the technique and specification/version. Validate:

- label/value records and required metadata;
- X/Y units, first/last X, point count, spacing, factors, and encoded numeric
  representation;
- NTUPLES versus simpler XY forms;
- page/block boundaries and compound/instrument identifiers; and
- whether data are absorbance, transmittance, counts, complex NMR, peaks, or
  continuous spectra.

Metadata and comments are untrusted and should not be copied into a report.
The generic tabular scanner is not a JCAMP parser.

## NMR data

`.fid`, Bruker directory layouts, Varian/Agilent layouts, processed spectra,
and NMR exchange files require producer-aware tooling such as nmrglue. Record:

- vendor/software/version and complete acquisition directory;
- nucleus, field strength, spectral width, dwell time, point count, quadrature,
  digital filter, scans, temperature, pulse sequence, and reference;
- raw FID versus processed spectrum, apodization, zero filling, Fourier
  transform, phase, baseline, referencing, and solvent suppression;
- dimensional axes/units and whether data are real, imaginary, magnitude, or
  complex; and
- sample preparation, concentration, pH, replicates, and batch/order.

Peak picking, integration, baseline correction, phase correction, alignment,
binning, and normalization are transformations. Preserve raw data and report
parameter sensitivity; do not apply them automatically.

## Optical, vibrational, and diffraction spectra

SPC, OPUS, WDF, SPE, instrument `.raw`, `.dat`, and text exports are
producer/variant dependent. Confirm:

- physical X axis (wavelength, wavenumber, energy, angle, time) and units;
- Y quantity (counts, intensity, absorbance, transmittance, reflectance) and
  calibration;
- point order/spacing, detector/channel, exposure/accumulations, resolution,
  slit/grating/laser/source, and polarization;
- background/reference/dark correction and all processing already applied; and
- maps, time series, replicate spectra, and spatial coordinates.

For XRD, crystallographic CIF/MTZ/HKL are also reference-only and need
crystallography-aware validation. A `.cif` suffix is ambiguous between
small-molecule CIF and PDBx/mmCIF.

## Chromatography and thermal/electrochemical exports

Generic CSV/TSV can contain retention time, temperature, potential, wavelength,
or another independent axis. The general scripts can profile the table only
after the data dictionary confirms:

- axis and signal columns, units, ordering, spacing, and replicate layout;
- blanks, calibration standards, internal standards, dilution factors,
  injection order, batch, and sample identifiers;
- LOD/LOQ, saturation, censoring qualifiers, and negative/zero handling; and
- whether peaks/integrals are raw, manually edited, or software-derived.

Do not infer an axis from monotonic values or a column name. Do not
automatically smooth, baseline-correct, align, integrate, normalize, subtract
blanks, or delete peaks.

## Safe bounded tabular workflow

For an approved values-only export:

```bash
python scripts/tabular_profile.py spectrum.csv \
  --root /approved/project \
  --max-rows 100000

python scripts/missingness_leakage_audit.py spectrum.csv \
  --root /approved/project \
  --group-column sample_group \
  --entity-column sample_id \
  --split-column split \
  --time-column acquisition_time

python scripts/distribution_sensitivity.py spectrum.csv \
  --root /approved/project \
  --column intensity
```

Use only pseudonymous column roles in shared commands/logs. The outputs contain
aggregates and tokens, not spectra or identifiers.

## Analytical EDA rigor

1. Define the independent unit: scan, injection, spectrum, sample, batch,
   subject, instrument, site, or experiment.
2. Preserve raw acquisition files and processing audit trails.
3. Record calibration, units, standards, blanks, internal standards,
   acquisition order, maintenance, software, and method versions.
4. Keep non-detects, below-LOQ values, saturation, missing scans, failed QC, and
   true zeros distinct. Preserve qualifier and limit fields.
5. Compare raw and processed summaries and sensitivity to baseline, smoothing,
   peak picking, alignment, integration, normalization, and transformations.
6. Investigate outliers against calibration, instrument state, carryover, and
   sample handling; do not delete automatically.
7. Split independent samples/batches/time before learned preprocessing. Never
   fit normalization or feature selection on test data.
8. Account for repeated spectra, technical replicates, correlated wavelengths/
   peaks, and many comparisons.
9. Label discovered peaks/patterns as exploratory and confirm independently.
10. Do not make identity, purity, mechanism, exposure, diagnostic, or causal
    claims from EDA alone.

## Detection limits and censoring

EPA guidance treats non-detects/over-detects as censored observations carrying
partial information and recommends preserving detection condition and limit
type rather than forcing a numeric result. Apply the same principle to
instrumental assays:

- keep measured value, qualifier, limit type, and limit value in distinct
  fields;
- do not replace censored values automatically with zero, LOD/2, or LOQ;
- summarize the censoring fraction by group/batch/time;
- choose a model appropriate to censoring and scientific design; and
- report sensitivity to plausible assumptions.

## Authoritative sources

Current parser APIs and format guidance reviewed 2026-09-30. Historical
methodology citations are retained as source context.

- HUPO-PSI, [mzML specification/status](https://www.psidev.info/mzml)
  (mzML 1.1.0 long-term stable; current schema/CV links and 2026 IM-MS/DIA
  proposal status).
- HUPO-PSI, [mzML GitHub specification repository](https://github.com/HUPO-PSI/mzML).
- IUPAC, [JCAMP-DX digital standard family](https://iupac.org/what-we-do/digital-standards/jcamp-dx/)
  (page dated 2021-08-03; finalized technique-specific standards).
- IUPAC, [JCAMP-DX 5.01 recommendation](https://doi.org/10.1351/pac199971081549).
- nmrglue, [current documentation](https://nmrglue.readthedocs.io/en/latest/).
- US EPA, [Detection Limits Best Practices Guide](https://www.epa.gov/system/files/documents/2025-09/wqxdetectionlimitsbestpracticesguide_final.pdf),
  dated August 2025.
- NIST/SEMATECH, [Exploratory Data Analysis](https://www.itl.nist.gov/div898/handbook/eda/eda.htm).
- FDA/ICH E9(R1), [estimands and sensitivity analysis](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e9r1-statistical-principles-clinical-trials-addendum-estimands-and-sensitivity-analysis-clinical),
  final guidance May 2021.
