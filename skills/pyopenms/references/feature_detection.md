# Feature detection and linking (pyOpenMS 3.6.0)

## Inputs and tolerances

Both bundled detectors select centroided MS1, sort spectra by RT and peaks by
m/z, and preserve the original experiment. Profile data are rejected; unknown
type requires independently justified `--assume-centroided`. A sorted spectrum
is not necessarily centroided. DIA/ion mobility, polarity mixtures and real
instrument-specific feature performance need separate validation.

`detect_features_metabo.py` uses `mass_error_ppm`. The peptide detector uses
`mass_trace:mz_tolerance`, an **absolute m/z** tolerance, exposed as
`--mz-tol-da`. Do not substitute a ppm conversion at one arbitrary m/z. RT values
and widths are seconds; feature intensities depend on the generating algorithm,
so record whether integrated area, fitted area or apex intensity is represented.
Charge zero is unknown, and quality scores are algorithm-specific, not q-values.

## Metabolomics bindings

```python
import pyopenms as ms
# exp must already contain sorted centroided MS1 data.
mtd = ms.MassTraceDetection()
p = mtd.getDefaults()
p.setValue("mass_error_ppm", 10.0)
p.setValue("noise_threshold_int", 1000.0)
mtd.setParameters(p)
traces = mtd.run(exp, 0)  # 0 means no maximum trace count

epd = ms.ElutionPeakDetection()
p = epd.getDefaults()
p.setValue("width_filtering", "fixed")
epd.setParameters(p)
split_traces = epd.detectPeaks(traces)

ffm = ms.FeatureFindingMetabo()
p = ffm.getDefaults()
p.setValue("isotope_filtering_model", "metabolites (5% RMS)")
p.setValue("remove_single_traces", "true")
p.setValue("charge_lower_bound", 1)
p.setValue("charge_upper_bound", 3)
ffm.setParameters(p)
features = ms.FeatureMap()
ffm.run(split_traces, features)  # fills features; auxiliary outputs are returned
features.setUniqueIds()
ms.FeatureXMLFile().store("features.featureXML", features)
```

These are the 3.6 signatures. The older output-list calls to `run`/`detectPeaks`
raise `TypeError`. A synthetic 41-scan Gaussian isotope envelope yields one
feature and three mass traces in native regression tests; this confirms data
flow, not correct isotope grouping for every metabolite. Removing single traces
can discard valid low-abundance or unusual isotope signals. Select parameters
using pooled QC, blanks and known compounds rather than maximizing feature count.

## Peptide detector

```python
exp.sortSpectra(True)
exp.updateRanges()
algo = ms.FeatureFinderAlgorithmPicked()
p = algo.getDefaults()
p.setValue("mass_trace:mz_tolerance", 0.004)
p.setValue("isotopic_pattern:charge_low", 1)
p.setValue("isotopic_pattern:charge_high", 4)
features = ms.FeatureMap()
algo.run(exp, features, p, ms.FeatureMap())
features.setUniqueIds()
```

The synthetic native test produces a feature from a designed isotope envelope.
Peptide-like isotope distributions and chromatographic shape assumptions are
not general guarantees for metabolites. Inspect `getDefaults()` separately for
mass trace, isotope-pattern and seed tolerances; changing one does not set all.

## Align, then link

```bash
python scripts/align_link_quantify.py one.featureXML two.featureXML --rt-tol 20 --mz-tol 10 --mz-unit ppm --out-prefix study
python scripts/consensus_to_matrix.py study.consensusXML --out quant.csv --long quant_long.csv
```

File-dependent CLI templates: synthetic feature-map tests cover linking,
alignment selection, table metadata/intensities and median normalization. Choose
an informative reference map; the script selects the largest map. Alignment
failure stops processing unless explicitly overridden with `--allow-unaligned`.
Do not report an unaligned study as aligned. Verify landmarks, residual RT
errors, retention order, match density and extreme transformations.

`MapAlignmentAlgorithmPoseClustering.setReference(reference)` and
`align(sample, trafo)` fit the transform;
`MapAlignmentTransformer.transformRetentionTimes(sample, trafo, True)` applies
it. Save raw and aligned coordinates and the fitted transformations in a
production workflow. The bundled CLI currently exports final consensus/results,
not standalone transformation files.

`FeatureGroupingAlgorithmQT` takes a list of feature maps and output
`ConsensusMap`. `distance_RT:max_difference` is seconds;
`distance_MZ:max_difference` requires an explicit `ppm`/`Da` unit. Column headers
must match input map order and carry unique sample names. Linking by m/z and RT
does not identify a molecule; isobars and incorrect charge assignments can link.

## Quantification output

`ConsensusMap.get_intensity_df()` returns features by samples;
`get_metadata_df()` returns lowercase `rt`, `mz`, `charge`, `quality`, etc.
The scripts combine rows positionally and emit a `consensus_id` that is a
**table row index**, not the stable OpenMS unique feature ID. Keep the consensusXML
as the provenance artifact. Check unique sample filenames before analysis.
Missing handles are not measured zero abundance; inspect the exported missing
value convention and model missingness before imputation.

Median or quantile normalization assumes comparable distributions and can erase
true global differences. Use standards, dilution checks, technical QC, blank
signals and batch metadata to justify it. Within-scan TIC normalization is a
different operation. These scripts do not provide absolute concentration or
isobaric reporter-ion quantification.

## Inspect features and annotations

```python
for feature in features:
    print(feature.getRT(), feature.getMZ(), feature.getIntensity(), feature.getCharge())
    points = feature.getConvexHull().getHullPoints()
    print(len(points))  # not points.size()
```

Subordinates represent algorithm-specific hierarchy; do not assume every
subordinate is an isotope. `IDMapper` annotates features using existing IDs;
its presence does not replace identification confidence control.

Source: [OpenMS 3.6 release changes](https://openms.de/documentation/html/ChangeLog.html),
[feature tutorial](https://pyopenms.readthedocs.io/en/latest/user_guide/feature_detection.html)
(check its version banner), and installed 3.6.0 signatures/defaults.
