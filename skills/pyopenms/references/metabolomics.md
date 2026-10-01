# Metabolomics (pyOpenMS 3.6.0)

## Workflow and inference limits

1. Inspect conversion, polarity, charge, isotope selection and centroid metadata.
2. Use `detect_features_metabo.py` on centroided MS1. Tune ppm/noise/width/isotope
   assumptions against QC and blanks; retain raw signals and parameters.
3. Align/link comparable runs with `align_link_quantify.py`, then export
   `consensus_to_matrix.py`. Check RT residuals and sample-map identities.
4. Optionally group adduct families and annotate accurate-mass candidates.
5. Assess blank/QC/batch effects and missingness before statistical comparison.
6. Confirm structural claims with orthogonal evidence (MS/MS, standards and RT).

One detected feature, one adduct family, and one metabolite are different units.
A mass match alone does not resolve structural isomers. The native checks use
synthetic spectra, adduct pairs and a one-compound local database, not real
metabolomics samples or an authenticated external service.

## Adduct deconvolution

```bash
python scripts/detect_adducts.py features.featureXML --out-features adducts.featureXML --out-consensus groups.consensusXML
python scripts/detect_adducts.py negative.featureXML --negative
```

`MetaboliteFeatureDeconvolution.compute(input_map, output_map, groups, edges)`
uses `potential_adducts` entries such as `H:+:0.4`, `Na:+:0.25`, or
`H-2O-1:0:0.05`. Syntax is `Elements:Charge:Probability`; signs encode charge,
negative element counts encode losses. This differs from AccurateMassSearch's
`M+H;1+` syntax. Do not require probabilities of compoundable adduct/loss entries
to sum to one. Set `negative_mode` for negative ions and choose plausible adducts
for the solvent, sample and instrument. The CLI charge limits are positive
magnitudes; in negative mode it passes signed bounds `-max` through `-min` to
the native algorithm as well as setting `negative_mode`.

Inspect `dc_charge_adducts` when present and the group/edge maps. Do not assume
invented generic `adduct`/`neutral_mass` meta keys exist. Group membership is an
inference dependent on tolerance, coelution, charge and plausible ion chemistry.

## Accurate-mass search: local database contract

`AccurateMassSearchEngine` reads local tables; there is no REST endpoint,
authentication or pagination. The tested macOS 3.6.0 wheel includes
`CHEMISTRY/HMDBMappingFile.tsv` and `CHEMISTRY/HMDB2StructMapping.tsv`. Locate them
with `ms.File.getOpenMSDataPath()`, inspect headers and preserve checksums; bundled
data are a snapshot, not a promise of current HMDB completeness or licensing for
redistribution. The CLI accepts explicit database files and resolves relative
paths against the working directory.

Mapping TSV format:

```text
database_name	Example
database_version	1
180.0633903828	C6H12O6	EXAMPLE_GLUCOSE
```

Structure TSV has exactly four tab-separated columns and no header:
identifier, name, SMILES, InChI. Identifiers must match the mapping file; provide
real strings or `null` where appropriate. A mass value of zero asks OpenMS to
calculate it from the formula. Preserve version metadata and multiple candidate
rows; do not combine unrelated versions of mapping and structure files.

```bash
python scripts/accurate_mass_search.py features.featureXML --ppm 5 --db-mapping compounds.tsv --db-struct structures.tsv --out-mztab candidates.mzTab --csv candidates.csv
```

The bundled adduct files use patterns like `M+H;1+` and `M-H;1-`. Tolerance is a
window around observed m/z, with `mass_error_unit=ppm` or `Da`. Neutral mass,
observed m/z, theoretical adduct m/z and their error must remain distinct. A
proton-only custom formula `M = mz - proton_mass` is valid only for `[M+H]+`.
`AccurateMassSearchEngine.run` accepts `FeatureMap` or `ConsensusMap` with `MzTab`;
`FeatureMap` also supports `MzTabM`. This script writes legacy mzTab and extracts
its small-molecule table without claiming identification-level FDR.

## GNPS and SIRIUS export

`GNPSMGFFile.store(consensus_path, list_of_mzml_paths, output_mgf)` requires
feature MS2 annotations carrying **`map_index` and `spectrum_index`**, with
matching identification-run identifiers preserved by consensusXML I/O. Supply
indexed mzML in the same map order; indices must still point to original MS2
spectra. RT alignment/filtering/reordering can invalidate an index relationship.
The plain MS1 consensus produced by the bundled linker lacks these annotations.
Annotate MS2-to-feature links using a validated feature mapping workflow first;
the exporter rejects a consensus with no such links.

`SiriusExportAlgorithm.run([mzml_path], [featurexml_path], out_ms, out_info)`
uses lists of **strings**, not encoded bytes. FeatureXML is optional. Source-file
format and native-spectrum-ID metadata can be required; do not fabricate them
for instrument data. Export creation does not validate the downstream SIRIUS
version, formulas/structures, credentials, or a GNPS job submission. No external
GNPS/SIRIUS service or engine is invoked by these scripts.

## Study QC

Use explicit sample metadata for blanks, pooled QC, standards and biological
replicates; do not infer groups from filename substrings. Choose replicate
numbers through study design/power analysis, not a universal minimum. Quantile
normalization and half-minimum imputation are assumptions, not safe defaults.
QC CV needs enough nonmissing replicate measurements and a positive mean;
blank ratios require a justified detection floor, not an arbitrary added 1.
The sum of detected feature intensities is a feature-total abundance statistic,
not the instrument's TIC. Evaluate trends with injection order and preserve
missing values separately from measured zeros.

Sources: [AccurateMassSearch release implementation](https://github.com/OpenMS/OpenMS/blob/5d5cbff4053b281763a1a79bf69e81c27967cfdf/src/openms/source/ANALYSIS/ID/AccurateMassSearchEngine.cpp),
[GNPS exporter source](https://github.com/OpenMS/OpenMS/blob/5d5cbff4053b281763a1a79bf69e81c27967cfdf/src/openms/source/FORMAT/GNPSMGFFile.cpp),
[SIRIUS exporter source](https://github.com/OpenMS/OpenMS/blob/5d5cbff4053b281763a1a79bf69e81c27967cfdf/src/openms/source/ANALYSIS/ID/SiriusExportAlgorithm.cpp).
