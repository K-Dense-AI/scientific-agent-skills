# Data structures (pyOpenMS 3.6.0)

## Spectra, chromatograms and copy semantics

```python
import pyopenms as ms
spec = ms.MSSpectrum()
spec.setRT(60.0)  # seconds, not minutes
spec.setMSLevel(1)
spec.setType(ms.SpectrumSettings.SpectrumType.CENTROID)
spec.set_peaks(([100.0, 200.0], [10.0, 20.0]))
exp = ms.MSExperiment()
exp.addSpectrum(spec)

copy = exp.getSpectrum(0)
copy.select([1])  # also filters associated peak arrays
exp.setSpectra([copy])  # explicit writeback
mz, intensity = exp[0].get_peaks()
assert list(mz) == [200.0]
```

`MSExperiment` stores spectra and chromatograms separately. `len(exp)` concerns
spectra; inspect `getNrChromatograms()` too. `getSpectrum()` and indexing return
copies in this binding; do not rely on iteration to mutate stored peaks.
`set_peaks()` changes the peak arrays but does not synchronize associated
float/integer/string arrays; prefer `select` for peak removal.

`MSChromatogram.get_peaks()` returns time in seconds and intensity. Precursor
metadata in a chromatogram is not proof of an analyte identity. MS2 precursor
m/z and charge come from `getPrecursors()`; the list may be empty or contain
multiple entries. Charge zero means unknown. Keep collision energy, isolation
windows, polarity and ion mobility metadata when they matter. Empty spectra and
traces need explicit handling before min/max/argmax operations.

`MSExperiment(exp)` makes a copy. Experiment metadata are available through
`getInstrument()`, `getSample()`, `getSourceFiles()`, and
`getExperimentalSettings()`. Preserve native IDs and source provenance when
rewriting files.

## Features and consensus

A `Feature` carries RT, m/z, intensity, charge, quality, hulls and optional
subordinates/identifications. Hull coordinates are `(RT seconds, m/z)`; use
`len(feature.getConvexHull().getHullPoints())`. Subordinates are algorithm-defined,
not invariably isotope peaks. Overall quality is not a calibrated probability.

```python
features = ms.FeatureMap()
f = ms.Feature()
f.setRT(60.0)
f.setMZ(200.0)
f.setIntensity(1000.0)
f.setCharge(1)
features.push_back(f)
features.setUniqueIds()
features.setPrimaryMSRunPath(["run.mzML"])
print(features.getPrimaryMSRunPath())  # list[str]
print(features.get_df()[["rt", "mz", "intensity", "charge"]])
```

`getUniqueId()` is an object identifier, not a count. `FeatureMap.size()` is the
number of features. Preserve source IDs when joining data. `ConsensusFeature`
contains handles with `getMapIndex()`, `getUniqueId()` and the original
feature coordinates/intensity. Absent handles mean missing observations.

`ConsensusMap.getColumnHeaders()` returns the map-index/sample mapping. Modify
it then call `setColumnHeaders(headers)` explicitly. `get_intensity_df()` and
`get_metadata_df()` are the focused exports; row identities/sample names must
be checked before joining. Positional concatenation avoids duplicate-index joins
but the output row number is not a persistent scientific identifier.

## Identification containers

Use `PeptideIdentificationList` with `push_back` for mutable peptide IDs.
`IdXMLFile.load(path)` returns proteins plus peptide IDs in 3.6; output-argument
loading also remains supported. A peptide ID has a search-run identifier, score
type/direction, optional RT/m/z, and hits. Hits have sequences, charge, score,
rank, protein evidence and metadata. Read `getScoreType()` and
`isHigherScoreBetter()`; do not assume scores or mass-error meta keys have a
universal meaning. `MS:1002252` is not a generic ppm-error key.

`ProteinIdentification` describes a search run and protein hits/groups, not one
protein. `getSearchParameters()` includes database, enzyme, modifications and
tolerance units. Use the identification reference for FDR semantics.

## Chemistry and parameters

```python
seq = ms.AASequence.fromString("PEPTIDEM(Oxidation)K")
print(seq.getMonoWeight(), seq.getAverageWeight(), seq.getFormula().toString())
formula = ms.EmpiricalFormula("C6H12O6")
print(formula.getMonoWeight())  # neutral mass in Da
pattern = formula.getIsotopeDistribution(ms.CoarseIsotopePatternGenerator(4))
print([(p.getMZ(), p.getIntensity()) for p in pattern.getContainer()])

algorithm = ms.FeatureFindingMetabo()
params = algorithm.getDefaults()
for key in params.keys():
    print(key, params.getValue(key), params.getDescription(key))
params.setValue("charge_lower_bound", 1)
algorithm.setParameters(params)
```

The neutral-formula isotope container uses mass coordinates; do not label them
charged m/z without applying the intended adduct/charge. Coarse isotope patterns
are theoretical natural-abundance models; labeling/enrichment needs its own
model. Mass and average mass are different quantities. Unknown/ambiguous sequence
residues or modifications need deliberate treatment rather than silently
substituting a standard residue.

In 3.6 `Param.keys()` returns strings and typed parameter values may be booleans.
String values `"true"`/`"false"` remain accepted for the bundled algorithms.
Use installed defaults and descriptions to establish allowed names and units;
setting an unused or misspelled parameter does not establish algorithm behavior.

Sources: [3.6 release changes](https://openms.de/documentation/html/ChangeLog.html),
[wheel metadata](https://pypi.org/project/pyopenms/3.6.0/), and native 3.6.0
object/round-trip checks. The examples above are covered by synthetic checks;
they do not validate real acquisition metadata or scientific inference.
