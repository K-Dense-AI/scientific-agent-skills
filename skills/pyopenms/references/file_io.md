# File I/O (pyOpenMS 3.6.0)

The bundled scripts use local files; they do not fetch vendor data or databases.
Native tests cover tiny synthetic mzML, chromatogram, featureXML, consensusXML,
idXML, FASTA, MGF and local TSV examples. Instrument conversion, mzIdentML/pepXML,
TraML, and large-file throughput remain untested here.

## mzML and indexed access

```python
import pyopenms as ms
exp = ms.MSExperiment()
ms.MzMLFile().load("sample.mzML", exp)
print(exp.getNrSpectra(), exp.getNrChromatograms())
writer = ms.MzMLFile()
options = writer.getOptions()
options.setWriteIndex(True)
options.setCompression(True)
writer.setOptions(options)
writer.store("indexed.mzML", exp)

on_disk = ms.OnDiscMSExperiment()
if not on_disk.openFile("indexed.mzML"):
    raise ValueError("An indexed mzML is required")
for i in range(on_disk.getNrSpectra()):
    spec = on_disk.getSpectrum(i)
    # RT is seconds; get_peaks() yields m/z and intensity arrays.
```

`IndexedMzMLFileLoader.load(filename, on_disk)` is an alternative loader; it
requires an `OnDiscMSExperiment` output argument. The loader itself is not a
spectrum container. Preserve a known indexed input for lazy reading; converting
an unindexed input via `MSExperiment` first still loads the full input in memory.
`CachedmzML.store(path, exp)` and `CachedmzML.load(path, cached)` are available for
local binary caches, which require their paired metadata files and disk space.

## Format-specific I/O

```python
proteins, peptides = ms.IdXMLFile().load("search.idXML")
ms.IdXMLFile().store("copy.idXML", proteins, peptides)
# The output-argument form also works:
proteins = []
peptides = ms.PeptideIdentificationList()
ms.IdXMLFile().load("search.idXML", proteins, peptides)

features = ms.FeatureMap()
ms.FeatureXMLFile().load("features.featureXML", features)
consensus = ms.ConsensusMap()
ms.ConsensusXMLFile().load("study.consensusXML", consensus)
entries = []
ms.FASTAFile().load("database.fasta", entries)
```

For untested formats, inspect installed signatures before adapting:
`help(ms.MzIdentMLFile.load)`, `help(ms.PepXMLFile.load)`,
`help(ms.TraMLFile.load)`. pepXML is a general peptide-identification exchange
format, not an X! Tandem-only format. An `MSPFile.load` call requires a
`PeptideIdentificationList` and `MSExperiment` (or `AnnotatedMSRun`), not a list
of spectra.

## Metadata and loss

Use `exp.getInstrument()`, `exp.getSample()`, and `exp.getSourceFiles()` to inspect
provenance. `MSChromatogram.get_peaks()` gives time in seconds and intensity;
`getNativeID()` identifies stored traces, but a stored TIC need not be present
or equal to the sum of the MS1 peaks retained after conversion.

`convert_format.py` preserves experiment metadata when filtering spectra, and
retains synchronized peak arrays using `MSSpectrum.select(indices)`. Its RT and
intensity filters apply to spectra only. Chromatograms pass through unchanged
unless `--ms-level` is selected, when they are omitted.

MGF exports tandem spectra and loses much mzML metadata, chromatograms, and
other acquisition information; mzXML also cannot represent all mzML metadata.
Round-trip counts alone do not establish lossless conversion. Keep the original
file, conversion program/version/options, native IDs, charge/polarity, source
metadata, and calibration state. Native vendor-reader availability in OpenMS
3.6 does not establish that any particular vendor file works in this wheel.

## mzTab

Use the producing algorithm's populated `MzTab`/`MzTabM` with the corresponding
writer. A title plus empty rows is not a complete report. When changing a copied
metadata object, explicitly call `mztab.setMetaData(metadata)` before storing.
Retain candidate multiplicity, adduct assumptions and database provenance.

Source: [OpenMS release changes](https://openms.de/documentation/html/ChangeLog.html)
and installed pyOpenMS 3.6.0 binding signatures; the older
[mzML tutorial](https://pyopenms.readthedocs.io/en/latest/user_guide/mzml_files.html)
may show different output-argument conventions.
